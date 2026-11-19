#!/usr/bin/env python3
"""Cut-corner frame images for the GTK theme (used with CSS border-image: GTK3 cannot clip shapes, so the
45deg corners, the outline and the fill all live in these 9-slice SVGs). Original artwork.

usage: make_gtk_assets.py OUT_DIR
FAN MADE - inspired by Cyberpunk 2077 by CD PROJEKT RED (trademarks of CD PROJEKT S.A.).
"""
import sys
from pathlib import Path

CY, RED, NAVY, VIEW = "#5beedc", "#ff2a4f", "#111e29", "#0b1620"


def frame_svg(line, line_a, fill, fill_a, size=24, cut=6, lw=1.0, tl=True, br=True):
    """size x size image, slice = cut: outline on the outer edge, 45deg cut at top-left / bottom-right"""
    s, c, h = size, cut, lw / 2
    pts = [(c if tl else 0, 0), (s, 0), (s, s - c if br else s), (s - c if br else s, s), (0, s), (0, c if tl else 0)]
    outer = " ".join(f"{x},{y}" for x, y in pts)
    # outline drawn half a line inside the edge so it stays crisp
    ipts = [((c + h * 0.41) if tl else h, h), (s - h, h), (s - h, (s - c - h * 0.41) if br else s - h),
            ((s - c - h * 0.41) if br else s - h, s - h), (h, s - h), (h, (c + h * 0.41) if tl else h)]
    inner = " ".join(f"{x:.2f},{y:.2f}" for x, y in ipts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{s}" height="{s}" viewBox="0 0 {s} {s}">'
            f'<polygon points="{outer}" fill="{fill}" fill-opacity="{fill_a}"/>'
            f'<polygon points="{inner}" fill="none" stroke="{line}" stroke-opacity="{line_a}" stroke-width="{lw}" stroke-linejoin="miter"/>'
            f'</svg>\n')


CAP = 20      # side slice of the neon frames below (border-image "0 20 0 20" in the CSS)


def neon_svg(mid=False, height=72, top=4, bottom=64, cut=10, edge=6):
    """A floating HUD frame like the KDE edition's panels: dark glass, a 3 px neon red tube with a soft glow,
    45deg cuts at top-left and bottom-right drawn as separate pieces of tube. The empty space around it stays
    inside the panel's reserved strip, so the panel never grows. As a 9-slice: the caps image gives the two side
    slices (CAP px each, the frame edge sits `edge` px in to leave room for the glow), the mid image is stretched."""
    w = 8 if mid else 2 * CAP + 8
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{height}" '
            f'viewBox="0 0 {w} {height}" preserveAspectRatio="none">')
    lw, gap = 3.0, 2.5
    ty, by = top + lw / 2, bottom - lw / 2                     # centre of the top and bottom tubes
    if mid:
        x0, x1 = -20, w + 20                                     # no cuts: plain lines past both ends
        fill = f"M{x0},{top} L{x1},{top} L{x1},{bottom} L{x0},{bottom} Z"
        tube = f"M{x0},{ty} L{x1},{ty} M{x0},{by} L{x1},{by}"
    else:
        lx, rx = edge + lw / 2, w - edge - lw / 2
        c, g = cut, gap
        fill = (f"M{edge + c},{top} L{w - edge},{top} L{w - edge},{bottom - c} L{w - edge - c},{bottom} "
                f"L{edge},{bottom} L{edge},{top + c} Z")
        d = g * 0.7071                                           # gap measured along the diagonal
        tube = (f"M{lx + c + g},{ty} L{rx},{ty} L{rx},{by - c - g} "                     # top, right side
                f"M{rx - c - g},{by} L{lx},{by} L{lx},{ty + c + g} "                     # bottom, left side
                f"M{lx + c - d},{ty + d} L{lx + d},{ty + c - d} "                        # top-left cut
                f"M{rx - d},{by - c + d} L{rx - c + d},{by - d}")                        # bottom-right cut
    glow = "".join(f'<path d="{tube}" fill="none" stroke="{RED}" stroke-opacity="{a}" stroke-width="{sw}"/>'
                   for sw, a in ((11, 0.07), (8, 0.12), (5.5, 0.22)))
    body = (f'<path d="{fill}" fill="{NAVY}" fill-opacity="0.95"/>' + glow +
            f'<path d="{tube}" fill="none" stroke="{RED}" stroke-width="{lw}"/>'
            f'<path d="{tube}" fill="none" stroke="#ff8a9c" stroke-opacity="0.55" stroke-width="1"/>')
    return head + body + "</svg>\n"


def tile_svg(line_a, fill_a, w=44, h=18, cut=6):
    """A workspace tile for the top-left pod: a small cut-corner plate, filled when it is the current one."""
    pts = f"{cut},1 {w - 1},1 {w - 1},{h - cut} {w - cut},{h - 1} 1,{h - 1} 1,{cut}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polygon points="{pts}" fill="{CY}" fill-opacity="{fill_a}" stroke="{CY}" stroke-opacity="{line_a}" '
            f'stroke-width="1.5"/></svg>\n')


ASSETS = {
    # buttons
    "cn-btn-normal.svg":      frame_svg(CY, 0.55, CY, 0.04),
    "cn-btn-hover.svg":       frame_svg(CY, 1.0, CY, 0.12),
    "cn-btn-active.svg":      frame_svg(CY, 1.0, CY, 0.24),
    "cn-btn-disabled.svg":    frame_svg(CY, 0.2, CY, 0.0),
    "cn-btn-suggested.svg":   frame_svg(CY, 1.0, CY, 1.0),
    "cn-btn-suggested-hover.svg": frame_svg("#8af7ea", 1.0, "#8af7ea", 1.0),
    "cn-btn-destructive.svg": frame_svg(RED, 1.0, RED, 1.0),
    "cn-btn-destructive-hover.svg": frame_svg("#ff5a6d", 1.0, "#ff5a6d", 1.0),
    # entries (only the bottom-right corner is cut)
    "cn-entry-normal.svg":    frame_svg(CY, 0.45, VIEW, 1.0, tl=False),
    "cn-entry-focus.svg":     frame_svg(CY, 1.0, VIEW, 1.0, tl=False),
    "cn-entry-disabled.svg":  frame_svg(CY, 0.2, VIEW, 0.6, tl=False),
    # floating dock at the bottom (72 px panel) and its slots: empty at rest, a cyan plate for the active window
    "cn-dock.svg":            neon_svg(),
    "cn-dock-mid.svg":        neon_svg(mid=True),
    "cn-slot-hover.svg":      frame_svg(CY, 0.7, CY, 0.10),
    "cn-slot-active.svg":     frame_svg(CY, 1.0, CY, 0.30, lw=1.5),
    # the two floating pods that replace the top bar (52 px panel)
    "cn-pod.svg":             neon_svg(height=52, top=8, bottom=44, cut=8),
    "cn-pod-mid.svg":         neon_svg(mid=True, height=52, top=8, bottom=44),
    "cn-ws.svg":              tile_svg(0.45, 0.04),
    "cn-ws-active.svg":       tile_svg(1.0, 0.85),
    # tooltips
    "cn-tooltip.svg":         frame_svg(CY, 0.85, VIEW, 0.97),
}


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, svg in ASSETS.items():
        (out / name).write_text(svg)
    print("gtk assets:", len(ASSETS), "->", out)


if __name__ == "__main__":
    main()
