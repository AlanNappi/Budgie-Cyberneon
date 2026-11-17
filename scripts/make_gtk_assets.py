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
