"""CyberNeon HUD: small cairo/Pango drawing helpers and the transparent click-through desktop window.
FAN MADE - inspired by Cyberpunk 2077 by CD PROJEKT RED (trademarks of CD PROJEKT S.A.).
"""
import cairo
import gi
gi.require_version("Gtk", "3.0"); gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0"); gi.require_version("PangoCairo", "1.0")
from gi.repository import Gdk, Gtk, Pango, PangoCairo
from PIL import Image, ImageFilter

CY = (0.357, 0.933, 0.863)
RED = (1.0, 0.165, 0.31)
NAVY = (0.043, 0.086, 0.125)
TXT = (0.49, 0.87, 0.84)
AMBER = (1.0, 0.76, 0.2)
MONO = "JetBrainsMono Nerd Font Mono"


def layout(cr, s, family, px, bold=False, spacing=0, width=None, weight=None):
    lay = PangoCairo.create_layout(cr)
    desc = Pango.FontDescription()
    desc.set_family(family); desc.set_absolute_size(px * Pango.SCALE)
    desc.set_weight(weight if weight is not None else Pango.Weight.BOLD if bold else Pango.Weight.NORMAL)
    lay.set_font_description(desc); lay.set_text(s, -1)
    if spacing:
        attrs = Pango.AttrList()
        attrs.insert(Pango.attr_letter_spacing_new(int(spacing * Pango.SCALE)))
        lay.set_attributes(attrs)
    if width is not None:
        lay.set_width(int(width * Pango.SCALE)); lay.set_ellipsize(Pango.EllipsizeMode.END)
    return lay


def text(cr, s, x, y, family, px, color=CY, alpha=1.0, bold=False, spacing=0, align="left", width=None, weight=None):
    """Draws s with its top at y; x is the left edge, the centre or the right edge. Returns the text width."""
    lay = layout(cr, s, family, px, bold, spacing, width, weight)
    w, _h = lay.get_pixel_size()
    if align == "right":
        x -= w
    elif align == "center":
        x -= w / 2
    cr.set_source_rgba(*color, alpha); cr.move_to(x, y)
    PangoCairo.show_layout(cr, lay)
    return w


def poly(cr, pts):
    cr.new_path(); cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.close_path()


def new_layer(w, h):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(w), int(h))
    return s, cairo.Context(s)


def blur_mask(surf, radius):
    """Blurred alpha of a surface as an A8 surface: the neon glow. The GPU blur of KDE, done once per update."""
    surf.flush()
    w, h = surf.get_width(), surf.get_height()
    src = Image.frombuffer("RGBA", (w, h), bytes(surf.get_data()), "raw", "BGRA", surf.get_stride(), 1)
    blurred = src.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_A8, w)
    raw = blurred.tobytes()
    buf = bytearray(b"".join(raw[y * w:(y + 1) * w].ljust(stride, b"\0") for y in range(h)))
    return cairo.ImageSurface.create_for_data(buf, cairo.FORMAT_A8, w, h, stride)


def with_glow(surf, color, radius=6, strength=0.75):
    """A new surface: the glow of surf with surf itself on top."""
    out, cr = new_layer(surf.get_width(), surf.get_height())
    cr.set_source_rgba(*color, strength); cr.mask_surface(blur_mask(surf, radius), 0, 0)
    cr.set_source_surface(surf, 0, 0); cr.paint()
    return out


class HudWindow(Gtk.Window):
    """Transparent window on the desktop layer that ignores the mouse (clicks reach the desktop below), except where
    input_region() says otherwise."""

    def __init__(self, name, width, height, hint=Gdk.WindowTypeHint.DESKTOP):
        super().__init__(title=name)
        self.w, self.h = width, height
        screen = self.get_screen()
        if screen.get_rgba_visual():
            self.set_visual(screen.get_rgba_visual())
        self.set_app_paintable(True); self.set_decorated(False); self.set_resizable(False)
        self.set_type_hint(hint)
        self.set_skip_taskbar_hint(True); self.set_skip_pager_hint(True)
        self.set_accept_focus(False); self.set_focus_on_map(False)
        self.stick()
        if hint == Gdk.WindowTypeHint.DESKTOP:
            self.set_keep_below(True)
        else:
            self.set_keep_above(True)
        self.set_default_size(width, height); self.set_size_request(width, height)
        self.connect("draw", self._draw)
        self.connect("realize", lambda win: win.input_shape_combine_region(win.input_region()))

    def input_region(self):
        """The part of the window that takes clicks: nothing by default."""
        return cairo.Region()

    def _draw(self, _w, cr):
        cr.set_operator(cairo.OPERATOR_CLEAR); cr.paint(); cr.set_operator(cairo.OPERATOR_OVER)
        self.paint(cr)
        return False

    def paint(self, cr):
        raise NotImplementedError
