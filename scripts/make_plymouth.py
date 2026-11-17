#!/usr/bin/env python3
"""Build the CyberNeon Plymouth boot splash ("jack-in", script module). Original artwork.

usage: make_plymouth.py OUT_DIR [LOGO_FILE]
Writes cyberneon.plymouth, cyberneon.script and the PNG assets into OUT_DIR (installed by system/install-plymouth.sh).
FAN MADE - inspired by Cyberpunk 2077 by CD PROJEKT RED (trademarks of CD PROJEKT S.A.).
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = Path.home() / ".local/share/fonts/cyberneon"
CY, RED, NAVY = (91, 238, 220), (255, 42, 79), (7, 13, 26)
LINES = ["NEURAL LINK ............ OK", "ICE HANDSHAKE .......... OK", "PROXY CHAIN ............ 7 HOPS",
         "DAEMON LOADER .......... ARMED", "SESSION KEY ............ CRACKED", "USER SPACE ............. ONLINE"]


def font(name, size):
    try:
        return ImageFont.truetype(str(FONTS / name), size)
    except OSError:
        return ImageFont.truetype("DejaVuSansMono.ttf", size)


def text_png(path, text, size, color, name="ChakraPetch-Bold.ttf", spacing=0):
    f = font(name, size)
    w = int(sum(f.getlength(ch) + spacing for ch in text)) + 8
    im = Image.new("RGBA", (w, int(size * 1.5)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im); x = 4
    for ch in text:
        d.text((x, 2), ch, font=f, fill=color + (255,)); x += f.getlength(ch) + spacing
    im.save(path)


def logo_png(path, logo=None, size=180):
    if logo and Path(logo).exists():   # the logo you configured (LOGO=), tinted neon red with a glow
        src = Image.open(logo).convert("RGBA"); src = src.crop(src.getbbox())
        m = src.split()[3].resize((int(size * 0.8), int(size * 0.8)), Image.LANCZOS)
        full = Image.new("L", (size, size), 0); full.paste(m, (size // 10, size // 10))
        out = Image.new("RGBA", (size, size), RED + (0,))
        out.putalpha(full.filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.55)))   # soft glow, keeps the gaps
        core = Image.new("RGBA", (size, size), RED + (255,)); core.putalpha(full)
        Image.alpha_composite(out, core).save(path)
    else:                               # original CyberNeon emblem plate
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im); k = size / 64
        d.polygon([(10 * k, 8 * k), (54 * k, 8 * k), (54 * k, 42 * k), (42 * k, 56 * k), (10 * k, 56 * k)], fill=CY + (255,))
        d.polygon([(18 * k, 16 * k), (26 * k, 16 * k), (26 * k, 48 * k), (18 * k, 48 * k)], fill=NAVY + (255,))
        d.polygon([(31 * k, 16 * k), (46 * k, 16 * k), (46 * k, 24 * k), (39 * k, 24 * k), (39 * k, 48 * k), (31 * k, 48 * k)], fill=NAVY + (255,))
        im.save(path)


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    logo = sys.argv[2] if len(sys.argv) > 2 else None
    logo_png(out / "logo.png", logo)
    text_png(out / "jackin.png", "// JACKING IN", 30, CY, spacing=4)
    for i, line in enumerate(LINES):
        text_png(out / f"line{i}.png", line, 15, (126, 221, 213), "JetBrainsMono-Regular.ttf" if (FONTS / "JetBrainsMono-Regular.ttf").exists() else "ChakraPetch-Medium.ttf")
    text_png(out / "credit.png", "FAN MADE // INSPIRED BY CYBERPUNK 2077 BY CD PROJEKT RED", 12, (60, 140, 132), "ChakraPetch-Medium.ttf", spacing=2)
    # progress bar: frame, hatched fill, and a navy cover that slides away
    W, H = 560, 18
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(fr).rectangle((0, 0, W - 1, H - 1), outline=CY + (130,), width=1); fr.save(out / "bar_frame.png")
    fill = Image.new("RGBA", (W - 6, H - 6), CY + (60,)); d = ImageDraw.Draw(fill)
    for x in range(-H, W, 10):
        d.polygon([(x, H - 6), (x + 5, H - 6), (x + 5 + H - 6, 0), (x + H - 6, 0)], fill=CY + (255,))
    fill.save(out / "bar_fill.png")
    Image.new("RGBA", (W - 6, H - 6), NAVY + (255,)).save(out / "bar_cover.png")
    cb = Image.new("RGBA", (80, 80), (0, 0, 0, 0)); d = ImageDraw.Draw(cb)
    d.rectangle((0, 0, 79, 3), fill=RED + (255,)); d.rectangle((0, 0, 3, 79), fill=RED + (255,)); cb.save(out / "corner.png")
    Image.new("RGBA", (12, 30), RED + (255,)).save(out / "cursor.png")

    (out / "cyberneon.plymouth").write_text(
        "[Plymouth Theme]\nName=CyberNeon\n"
        "Description=Fan-made jack-in boot splash, inspired by Cyberpunk 2077 by CD PROJEKT RED\n"
        "ModuleName=script\n\n[script]\nImageDir=/usr/share/plymouth/themes/cyberneon\n"
        "ScriptFile=/usr/share/plymouth/themes/cyberneon/cyberneon.script\n")
    (out / "cyberneon.script").write_text(SCRIPT)
    print("plymouth theme:", out)


SCRIPT = r'''# CyberNeon Plymouth splash - FAN MADE, inspired by Cyberpunk 2077 by CD PROJEKT RED. Original artwork.
Window.SetBackgroundTopColor(0.027, 0.051, 0.102);
Window.SetBackgroundBottomColor(0.027, 0.051, 0.102);
W = Window.GetWidth(); H = Window.GetHeight();

logo.image = Image("logo.png");
logo.sprite = Sprite(logo.image);
logo.sprite.SetX(W / 2 - logo.image.GetWidth() / 2);
logo.sprite.SetY(H / 2 - logo.image.GetHeight() / 2 - 110);
logo.sprite.SetOpacity(0);

jack.image = Image("jackin.png");
jack.sprite = Sprite(jack.image);
jack.sprite.SetX(W / 2 - jack.image.GetWidth() / 2 - 10);
jack.sprite.SetY(H / 2 + 10);
cursor.image = Image("cursor.png");
cursor.sprite = Sprite(cursor.image);
cursor.sprite.SetX(W / 2 + jack.image.GetWidth() / 2 - 2);
cursor.sprite.SetY(H / 2 + 14);

bar.frame = Sprite(Image("bar_frame.png"));
bar.x = W / 2 - 280; bar.y = H / 2 + 70;
bar.frame.SetPosition(bar.x, bar.y, 1);
bar.fill = Sprite(Image("bar_fill.png"));
bar.fill.SetPosition(bar.x + 3, bar.y + 3, 2);
bar.cover = Sprite(Image("bar_cover.png"));
bar.cover.SetPosition(bar.x + 3, bar.y + 3, 3);

for (i = 0; i < 6; i++) {
    lines[i] = Sprite(Image("line" + i + ".png"));
    lines[i].SetPosition(W / 2 - 150, H / 2 + 105 + i * 22, 1);
    lines[i].SetOpacity(0);
}

corner_img = Image("corner.png");
c0 = Sprite(corner_img);                        c0.SetPosition(40, 40, 1);
c1 = Sprite(corner_img.Rotate(3.14159 / 2));    c1.SetPosition(W - 120, 40, 1);
c2 = Sprite(corner_img.Rotate(3.14159));        c2.SetPosition(W - 120, H - 120, 1);
c3 = Sprite(corner_img.Rotate(-3.14159 / 2));   c3.SetPosition(40, H - 120, 1);

credit.image = Image("credit.png");
credit.sprite = Sprite(credit.image);
credit.sprite.SetPosition(W / 2 - credit.image.GetWidth() / 2, H - 80, 1);

frame = 0;
fun refresh_callback() {
    frame++;
    # power-on flicker of the logo
    if (frame < 6) logo.sprite.SetOpacity(frame / 6);
    else if (frame < 9) logo.sprite.SetOpacity(0.25);
    else if (frame < 12) logo.sprite.SetOpacity(1);
    else if (frame < 14) logo.sprite.SetOpacity(0.5);
    else logo.sprite.SetOpacity(1);
    # blinking cursor
    if (Math.Int(frame / 25) % 2 == 0) cursor.sprite.SetOpacity(1); else cursor.sprite.SetOpacity(0);
}
Plymouth.SetRefreshFunction(refresh_callback);

fun progress_callback(duration, progress) {
    bar.cover.SetX(bar.x + 3 + Math.Int(554 * progress));
    for (i = 0; i < 6; i++) {
        if (progress > i / 6) lines[i].SetOpacity(1);
    }
}
Plymouth.SetBootProgressFunction(progress_callback);

# password prompt (encrypted disks)
fun display_password_callback(prompt, bullets) {
    global.prompt_sprite = Sprite(Image.Text("> " + prompt, 0.36, 0.93, 0.86, 1, "Sans Bold 13"));
    global.prompt_sprite.SetPosition(W / 2 - 150, H / 2 + 250, 10);
    stars = "";
    for (i = 0; i < bullets; i++) stars += "# ";
    global.bullet_sprite = Sprite(Image.Text("[ " + stars + "]", 1, 0.16, 0.31, 1, "Sans Bold 13"));
    global.bullet_sprite.SetPosition(W / 2 - 150, H / 2 + 278, 10);
}
Plymouth.SetDisplayPasswordFunction(display_password_callback);

fun display_normal_callback() {
    global.prompt_sprite = NULL; global.bullet_sprite = NULL;
}
Plymouth.SetDisplayNormalFunction(display_normal_callback);

fun message_callback(text) {
    global.msg_sprite = Sprite(Image.Text(text, 0.49, 0.87, 0.84));
    global.msg_sprite.SetPosition(W / 2 - 150, H - 100, 10);
}
Plymouth.SetMessageFunction(message_callback);
'''

if __name__ == "__main__":
    main()
