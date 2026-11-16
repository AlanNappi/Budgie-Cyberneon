#!/usr/bin/env python3
"""Turn a logo image YOU provide (PNG/WebP/SVG-rasterised, transparent background) into the
icon that replaces the Budgie bird (ubuntu-budgie-symbolic), tinted neon red with a glow.

No third-party logo ships with this repository: point LOGO= in cyberneon.conf to your own file.

usage: make_logo_icon.py LOGO_FILE [ICON_THEME_DIR]
"""
import base64, io, sys
from pathlib import Path
from PIL import Image, ImageFilter

NEON = (255, 42, 79)


def neon_logo(path: str, n: int = 256) -> Image.Image:
    src = Image.open(path).convert("RGBA")
    src = src.crop(src.getbbox())
    mask = src.split()[3]
    size = int(n * 0.70)
    m = mask.resize((size, size), Image.LANCZOS)
    full = Image.new("L", (n, n), 0)
    full.paste(m, ((n - size) // 2, int(n * 0.11)))  # slightly above centre: clears the red bar line
    glow = full.filter(ImageFilter.GaussianBlur(9)).point(lambda v: min(255, int(v * 1.6)))
    out = Image.new("RGBA", (n, n), NEON + (0,))
    out.putalpha(glow)
    core = Image.new("RGBA", (n, n), NEON + (255,)); core.putalpha(full)
    out = Image.alpha_composite(out, core)
    hot = full.filter(ImageFilter.MinFilter(7))  # hot inner core: neon-tube look
    hotl = Image.new("RGBA", (n, n), (255, 150, 170, 255)); hotl.putalpha(hot.point(lambda v: int(v * 0.55)))
    return Image.alpha_composite(out, hotl)


def main():
    logo = sys.argv[1]
    theme = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / ".local/share/icons/CyberNeon-Icons"
    buf = io.BytesIO(); neon_logo(logo).save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    # raster wrapped in SVG: GTK's symbolic recolouring only touches vector fills, so the logo keeps its colours
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="16" height="16" viewBox="0 0 16 16">'
           f'<image width="16" height="16" xlink:href="data:image/png;base64,{b64}"/></svg>')
    d = theme / "symbolic/apps"
    d.mkdir(parents=True, exist_ok=True)
    (d / "ubuntu-budgie-symbolic.svg").write_text(svg)
    print("logo icon installed:", d / "ubuntu-budgie-symbolic.svg")


if __name__ == "__main__":
    main()
