#!/usr/bin/env python3
"""Render the static preview images used by README.md into docs/ (maintainers only).

usage: make_docs.py   (run from anywhere; needs the CyberNeon fonts and Papirus installed)
Writes docs/wallpaper.jpg, docs/icons.png, docs/cursors.png, docs/prompt.png, docs/grub.png, docs/login.png
Previews use LOGO and LABEL from cyberneon.conf (same as the installed desktop).
"""
import os, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"; DOCS.mkdir(exist_ok=True)
SC = REPO / "scripts"
FONTS = Path.home() / ".local/share/fonts/cyberneon"
CY, RED, NAVY, BG = (91, 238, 220), (255, 42, 79), (17, 30, 41), (11, 22, 32)


def font(name, size):
    for p in (FONTS / name, Path(subprocess.run(["fc-match", "-f", "%{file}", name.split(".")[0]],
                                                capture_output=True, text=True).stdout)):
        try:
            return ImageFont.truetype(str(p), size)
        except OSError:
            continue
    return ImageFont.load_default()


def mono(size):
    f = subprocess.run(["fc-match", "-f", "%{file}", "JetBrainsMono Nerd Font Mono"], capture_output=True, text=True).stdout
    try:
        return ImageFont.truetype(f, size)
    except OSError:
        return ImageFont.truetype("DejaVuSansMono.ttf", size)


tmp = Path(tempfile.mkdtemp())

# LOGO / LABEL from cyberneon.conf, exactly as install.sh uses them
import re, shlex
CONF = {}
for line in (REPO / "cyberneon.conf").read_text().splitlines():
    m = re.match(r'^([A-Z_]+)=(.*)$', line.strip())
    if m:
        CONF[m.group(1)] = (shlex.split(m.group(2), comments=True) or [""])[0]
LOGO = CONF.get("LOGO", "")
if LOGO and not LOGO.startswith("/"):
    LOGO = str(REPO / LOGO)
if LOGO and not Path(LOGO).exists():
    LOGO = ""
WARGS = ["--label", CONF.get("LABEL", "N E T R U N N E R")] + (["--logo", LOGO] if LOGO else [])

# ------------------------------------------------------------- wallpaper (original emblem)
subprocess.run([sys.executable, "-I", str(SC / "make_wallpaper.py"), str(tmp / "w.png"), "--login"] + WARGS, check=True)
wall = Image.open(tmp / "w.png").convert("RGB").resize((1920, 1080), Image.LANCZOS)
wall.save(DOCS / "wallpaper.jpg", quality=90)

# ------------------------------------------------------------- icons sheet
if LOGO:
    subprocess.run([sys.executable, "-I", str(SC / "make_logo_icon.py"), LOGO, str(tmp / "icons")], check=True)
subprocess.run([sys.executable, "-I", str(SC / "make_icons.py"), str(tmp / "icons")], check=True)
import gi
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf


def svg(path, size):
    pb = GdkPixbuf.Pixbuf.new_from_file_at_size(str(path), size, size)
    return Image.frombytes("RGBA" if pb.get_has_alpha() else "RGB", (pb.get_width(), pb.get_height()),
                           pb.get_pixels(), "raw", "RGBA" if pb.get_has_alpha() else "RGB", pb.get_rowstride()).convert("RGBA")


apps = ["cyberneon-logo", "preferences-desktop", "org.gnome.Nautilus", "firefox", "com.gexperts.Tilix",
        "libreoffice-calc", "org.gnome.Geary", "accessories-calculator", "accessories-text-editor"]
pap = Path.home() / ".local/share/icons/Papirus-Dark/64x64/places"
folders = ["folder", "user-home", "folder-documents", "folder-download", "folder-music", "folder-pictures",
           "folder-videos", "folder-projects"]
sheet = Image.new("RGB", (96 * 10 + 16, 220), NAVY)
d = ImageDraw.Draw(sheet)
sheet.paste(im := svg(tmp / "icons/symbolic/apps/ubuntu-budgie-symbolic.svg", 72), (16, 14), im)
for i, n in enumerate(apps):
    sheet.paste(im := svg(tmp / "icons/scalable/apps" / f"{n}.svg", 72), (16 + (i + 1) * 96, 14), im)
for i, n in enumerate(folders):
    p = pap / f"{n}.svg"
    if p.exists():
        sheet.paste(im := svg(p, 72), (16 + 48 + i * 96, 124), im)
d.text((16, 98), "top-bar logo  |  dock / app icons (original)", fill=CY, font=font("ChakraPetch-SemiBold.ttf", 14))
d.text((16, 202), "Papirus-Dark folders, 'cyber' colour", fill=CY, font=font("ChakraPetch-SemiBold.ttf", 14))
sheet.save(DOCS / "icons.png")

# ------------------------------------------------------------- cursors sheet
env = dict(os.environ, PREVIEW=str(DOCS / "cursors.png"))
subprocess.run([sys.executable, "-I", str(SC / "make_cursors.py"), str(tmp / "cursors")], check=True, env=env)

# ------------------------------------------------------------- prompt mockup
W, H = 1100, 420
im = Image.new("RGB", (W, H), (7, 13, 26))
d = ImageDraw.Draw(im)
d.rectangle((14, 14, W - 15, H - 15), fill=BG, outline=RED, width=3)
d.rectangle((17, 17, W - 18, 58), fill=NAVY)
d.rectangle((17, 17, W - 18, 20), fill=RED)
d.text((W // 2, 40), "netrunner@cyberdeck: ~/projects/cyberneon", fill=CY, font=font("ChakraPetch-Bold.ttf", 17), anchor="mm")
f = mono(22); fb = mono(22)
y, x0, ch = 82, 36, 13.2


def seg(x, y, text, fg, bg=None):
    w = d.textlength(text, font=f)
    if bg:
        d.rectangle((x, y - 2, x + w, y + 28), fill=bg)
    d.text((x, y), text, fill=fg, font=f)
    return x + w


SEP = ""
x = seg(x0, y, "┏━", RED)
x = seg(x, y, " netrunner ", NAVY, RED)
x = seg(x, y, SEP, RED, CY)
x = seg(x, y, " ~/projects/cyberneon ", NAVY, CY)
x = seg(x, y, SEP, CY)
x = seg(x + 10, y, " main", RED)
y += 36
x = seg(x0, y, "┗━", RED); x = seg(x, y, "❯ ", CY); seg(x, y, "./install.sh", (200, 230, 228))
for i, (c, t) in enumerate([(CY, "==> checking requirements"), (CY, "==> GTK theme -> ~/.themes/CyberNeon"),
                            (CY, "==> cursor theme -> CyberNeon-Cursors"), (CY, "==> panels (top bar + left dock)"),
                            (CY, "==> done.")]):
    seg(x0, y + 44 + i * 34, t, c)
y2 = y + 44 + 5 * 34 + 12
x = seg(x0, y2, "┏━", RED); x = seg(x, y2, " netrunner ", NAVY, RED); x = seg(x, y2, SEP, RED, CY)
x = seg(x, y2, " ~/projects/cyberneon ", NAVY, CY); seg(x, y2, SEP, CY)
x = seg(x0, y2 + 36, "┗━", RED); x = seg(x, y2 + 36, "❯ ", RED)
d.rectangle((x + 4, y2 + 36, x + 16, y2 + 62), fill=RED)
im.save(DOCS / "prompt.png")

# ------------------------------------------------------------- GRUB mockup (from the real theme assets)
subprocess.run([sys.executable, "-I", str(SC / "make_system_assets.py"), str(tmp / "w.png"), str(tmp / "sys")], check=True)
g = Image.open(tmp / "sys/grub/background.png").convert("RGBA")
ov = Image.new("RGBA", g.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
L, T, MW, MH = int(1920 * .12), int(1080 * .26), int(1920 * .46), int(1080 * .46)
d.text((L, int(1080 * .18)), "// SELECT BOOT TARGET", fill=RED, font=font("ChakraPetch-Bold.ttf", 34))
d.rectangle((L, T, L + MW, T + MH), fill=(11, 22, 32, 215), outline=RED, width=3)
items = ["Ubuntu", "Advanced options for Ubuntu", "Memory test (memtest86+x64.efi)", "UEFI Firmware Settings"]
for i, t in enumerate(items):
    iy = T + 16 + i * 50
    if i == 0:
        d.rectangle((L + 12, iy, L + MW - 12, iy + 44), fill=CY + (255,))
        d.rectangle((L + 12, iy, L + 18, iy + 44), fill=RED + (255,))
        d.text((L + 34, iy + 22), t, fill=BG, font=font("ChakraPetch-Bold.ttf", 26), anchor="lm")
    else:
        d.text((L + 34, iy + 22), t, fill=(126, 221, 213), font=font("ChakraPetch-Regular.ttf", 26), anchor="lm")
d.text((L, int(1080 * .75)), "AUTO-BOOT IN 5 s", fill=CY, font=font("ChakraPetch-Regular.ttf", 26))
d.text((L, int(1080 * .80)), "[ENTER] boot   [E] edit   [C] console", fill=(42, 143, 134), font=font("ChakraPetch-Regular.ttf", 21))
Image.alpha_composite(g, ov).convert("RGB").resize((1280, 720), Image.LANCZOS).save(DOCS / "grub.png")

# ------------------------------------------------------------- login mockup (slick-greeter layout)
lg = Image.open(tmp / "sys/cyberneon-login.png").convert("RGBA")
ov = Image.new("RGBA", lg.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
d.rectangle((0, 0, 1920, 30), fill=(7, 13, 26, 200))
d.text((1900, 15), "2026-11-17  00:30", fill=CY, font=font("ChakraPetch-Medium.ttf", 16), anchor="rm")
bx, by = 210, 400
d.rectangle((bx, by, bx + 480, by + 210), fill=(17, 30, 41, 225), outline=RED, width=2)
d.text((bx + 30, by + 40), "netrunner", fill=CY, font=font("ChakraPetch-Bold.ttf", 28), anchor="lm")
d.rectangle((bx + 30, by + 90, bx + 450, by + 132), fill=(11, 22, 32, 255), outline=CY, width=1)
d.text((bx + 46, by + 111), "•" * 10, fill=CY, font=font("ChakraPetch-Bold.ttf", 22), anchor="lm")
d.text((bx + 30, by + 172), "Budgie Desktop", fill=(126, 221, 213), font=font("ChakraPetch-Medium.ttf", 18), anchor="lm")
Image.alpha_composite(lg, ov).convert("RGB").resize((1280, 720), Image.LANCZOS).save(DOCS / "login.png")

print("docs written to", DOCS)
