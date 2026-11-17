#!/usr/bin/env python3
"""CyberNeon Live for Budgie: animated layers over the static CyberNeon wallpaper (original artwork).

A transparent, click-through "desktop" window on the primary monitor (like conky) that draws: falling hex columns,
arcs rotating around the sigil, blinking network nodes and a pulsing target, data packets on the highlighted route,
a scan line and short periodic glitches (slices of the real wallpaper displaced for ~130 ms).
The positions are the wallpaper's own coordinates (3840x2160, "zoom"), so they sit on the drawn elements.

usage: live-wallpaper.py [--fps 20]
FAN MADE - inspired by Cyberpunk 2077 by CD PROJEKT RED (trademarks of CD PROJEKT S.A.).
"""
import math, random, sys, time
from urllib.parse import unquote, urlparse

import cairo
import gi
gi.require_version("Gtk", "3.0"); gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

FPS = int(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 20
CY, RED = (0.357, 0.933, 0.863), (1.0, 0.165, 0.31)
NODES = [(2820, 330), (3080, 250), (3330, 380), (3560, 280), (2950, 560), (3220, 620), (3480, 560), (3100, 860)]
TARGET = (3650, 760)
ROUTE = [(2820, 330), (2950, 560), (3220, 620), (3480, 560), (3650, 760)]
SIGIL = (1920, 1010)
HEX = "0123456789ABCDEF"


class Live(Gtk.Window):
    def __init__(self):
        super().__init__(title="cyberneon-live-wallpaper")
        display = Gdk.Display.get_default()
        mon = display.get_primary_monitor() or display.get_monitor(0)
        g = mon.get_geometry()
        self.W, self.H = g.width, g.height
        screen = self.get_screen()
        if screen.get_rgba_visual():
            self.set_visual(screen.get_rgba_visual())
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.set_skip_taskbar_hint(True); self.set_skip_pager_hint(True)
        self.set_accept_focus(False); self.set_keep_below(True); self.stick()
        self.move(g.x, g.y); self.set_default_size(g.width, g.height)
        self.connect("draw", self.on_draw)
        self.connect("realize", lambda w: w.input_shape_combine_region(cairo.Region()))   # click-through
        self.connect("destroy", Gtk.main_quit)

        # wallpaper image -> screen mapping ("zoom" on a 3840x2160 image)
        self.sc = max(self.W / 3840, self.H / 2160)
        self.ox, self.oy = (self.W - 3840 * self.sc) / 2, (self.H - 2160 * self.sc) / 2
        self.wall = None
        self.load_wallpaper()
        Gio.Settings.new("org.gnome.desktop.background").connect("changed::picture-uri", lambda *a: self.load_wallpaper())

        rnd = random.Random(2077)
        self.cols = [{"x": self.W * ((i * 0.137 + 0.06) % 1), "dur": 14 + (i * 3.779) % 9,
                      "chars": [rnd.choice(HEX) for _ in range(18)], "next": 0} for i in range(9)]
        self.node_periods = [(0.9 + (i * 1.373) % 4.2, (i * 0.61) % 3) for i in range(len(NODES))]
        self.route_len = [math.dist(ROUTE[i], ROUTE[i + 1]) for i in range(len(ROUTE) - 1)]
        self.glitch_at, self.glitch_seed = time.monotonic() + 9, 1
        self.t0 = time.monotonic()
        GLib.timeout_add(int(1000 / FPS), self.tick)

    def load_wallpaper(self):
        uri = Gio.Settings.new("org.gnome.desktop.background").get_string("picture-uri")
        try:
            src = cairo.ImageSurface.create_from_png(unquote(urlparse(uri).path))
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.W, self.H)
            cr = cairo.Context(surf)
            cr.translate(self.ox, self.oy); cr.scale(self.sc, self.sc)
            cr.set_source_surface(src, 0, 0); cr.paint()
            self.wall = surf
        except Exception:
            self.wall = None

    def mx(self, x): return self.ox + x * self.sc
    def my(self, y): return self.oy + y * self.sc

    def tick(self):
        self.queue_draw()
        return True

    def on_draw(self, _w, cr):
        t = time.monotonic() - self.t0
        sc = self.sc
        cr.set_operator(cairo.OPERATOR_CLEAR); cr.paint(); cr.set_operator(cairo.OPERATOR_OVER)

        # falling hex columns
        cr.select_font_face("JetBrainsMono Nerd Font Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        fs = max(10, 24 * sc); cr.set_font_size(fs)
        colh = 18 * fs * 1.15
        for c in self.cols:
            if t >= c["next"]:
                c["chars"] = c["chars"][1:] + [random.choice(HEX)]; c["next"] = t + 0.18
            y0 = ((t / c["dur"]) % 1) * (self.H + colh) - colh
            for k, ch in enumerate(c["chars"]):
                cr.set_source_rgba(*CY, 0.06 + 0.25 * k / 18)
                cr.move_to(c["x"], y0 + k * fs * 1.15); cr.show_text(ch)

        # rotating arcs around the sigil
        cx, cyy = self.mx(SIGIL[0]), self.my(SIGIL[1])
        a = math.radians((t / 48 * 360) % 360)
        cr.set_line_cap(cairo.LINE_CAP_BUTT)
        cr.set_source_rgba(*RED, 0.75); cr.set_line_width(max(2, 7 * sc))
        for st, sw in ((0, 34), (180, 12)):
            cr.new_path(); cr.arc(cx, cyy, 600 * sc, a + math.radians(st), a + math.radians(st + sw)); cr.stroke()
        b = math.radians(-(t / 30 * 360) % 360)
        cr.set_source_rgba(*CY, 0.55); cr.set_line_width(max(1, 3 * sc)); cr.set_dash([6, 5])
        for st, sw in ((20, 70), (200, 45)):
            cr.new_path(); cr.arc(cx, cyy, 650 * sc, b + math.radians(st), b + math.radians(st + sw)); cr.stroke()
        cr.set_dash([])

        # network: blinking nodes + pulsing target
        for (nx, ny), (period, phase) in zip(NODES, self.node_periods):
            u = (t + phase) % (period + 0.82)
            if u < period:
                continue
            u -= period
            alpha = 0.95 * (u / 0.12) if u < 0.12 else 0.95 * (1 - (u - 0.12) / 0.7) ** 2
            s = 40 * sc
            cr.set_source_rgba(*CY, max(0, alpha)); cr.set_line_width(max(1, 4 * sc))
            cr.rectangle(self.mx(nx) - s / 2, self.my(ny) - s / 2, s, s); cr.stroke()
        p = (t % 1.6) / 1.6; s_ = 1 + 1.8 * (1 - (1 - p) ** 3); s = 40 * sc * s_
        cr.set_source_rgba(*RED, max(0, min(1, 1.6 - s_ * 0.55))); cr.set_line_width(max(1, 4 * sc))
        cr.rectangle(self.mx(TARGET[0]) - s / 2, self.my(TARGET[1]) - s / 2, s, s); cr.stroke()

        # data packets on the route
        total = sum(self.route_len)
        for k in range(3):
            d = (((t - 1.7 * k) / 5.2) % 1) * total
            for i, seg in enumerate(self.route_len):
                if d <= seg:
                    (x1, y1), (x2, y2) = ROUTE[i], ROUTE[i + 1]
                    f = d / seg; px, py = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
                    break
                d -= seg
            q = max(4, 14 * sc)
            cr.set_source_rgba(*(RED if k == 1 else CY), 1)
            cr.rectangle(self.mx(px) - q / 2, self.my(py) - q / 2, q, q); cr.fill()

        # scan line with a soft trail
        y = ((t % 11) / 11) * (self.H + 90) - 90
        grad = cairo.LinearGradient(0, y, 0, y + 90)
        grad.add_color_stop_rgba(0, *CY, 0); grad.add_color_stop_rgba(1, *CY, 0.07)
        cr.set_source(grad); cr.rectangle(0, y, self.W, 90); cr.fill()
        cr.set_source_rgba(*CY, 0.22); cr.rectangle(0, y + 88, self.W, 2); cr.fill()

        # periodic glitch: slices of the real wallpaper displaced
        now = time.monotonic()
        if now >= self.glitch_at:
            if now < self.glitch_at + 0.13 and self.wall is not None:
                r = random.Random(self.glitch_seed)
                for _ in range(5):
                    sy, sh, dx = r.random() * self.H, 4 + r.random() * 26, (r.random() - 0.5) * 120
                    cr.save(); cr.rectangle(0, sy, self.W, sh); cr.clip()
                    cr.set_source_surface(self.wall, dx, 0); cr.paint(); cr.restore()
                cr.set_source_rgba(*(RED if self.glitch_seed % 2 else CY), 0.6)
                cr.rectangle(0, r.random() * self.H, self.W, 3); cr.fill()
            elif now >= self.glitch_at + 0.13:
                self.glitch_seed += 1
                self.glitch_at = now + 7 + random.random() * 7
        return False


if __name__ == "__main__":
    w = Live(); w.show_all(); Gtk.main()
