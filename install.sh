#!/bin/bash
# FAN MADE by a huge fan - inspired by Cyberpunk 2077 by CD PROJEKT RED. Cyberpunk 2077, Arasaka and all
# related names/logos/trademarks belong to CD PROJEKT S.A. Unofficial, non-commercial, not endorsed by CD PROJEKT RED.
# CyberNeon - netrunner theme for Ubuntu Budgie (Budgie 10.9, X11).
# User-level installer: no sudo needed (login screen and GRUB are in system/).
#
#   ./install.sh                 install / update everything (reads cyberneon.conf)
#   ./install.sh --no-restart    don't restart budgie-wm / budgie-panel at the end
#   ./install.sh --skip-papirus  don't download the Papirus icon theme
#   ./install.sh -h
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
SC="$REPO/scripts"
RESTART=1; PAPIRUS=1
for arg in "$@"; do
    case "$arg" in
        --no-restart) RESTART=0 ;;
        --skip-papirus) PAPIRUS=0 ;;
        -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
        *) echo "unknown option: $arg"; exit 1 ;;
    esac
done

# ------------------------------------------------------------------ config
LOGO=""; LABEL="N E T R U N N E R"; HUD_LABEL=""; WALLPAPER="cyberneon.png"; NEMO_OPACITY="0.90"
PINNED="budgie-control-center.desktop,nemo.desktop,firefox_firefox.desktop,com.gexperts.Tilix.desktop,libreoffice-calc.desktop"
UI_FONT="Chakra Petch Medium 10"; DOC_FONT="Chakra Petch 10"; TITLE_FONT="Chakra Petch Bold 10"
# shellcheck source=cyberneon.conf
[ -f "$REPO/cyberneon.conf" ] && . "$REPO/cyberneon.conf"
[ -n "$LOGO" ] && [ "${LOGO:0:1}" != "/" ] && LOGO="$REPO/$LOGO"
if [ -n "$LOGO" ] && [ ! -f "$LOGO" ]; then
    printf '\033[38;2;255;42;79m!!\033[0m LOGO not found (%s): using the original CyberNeon emblem.\n' "$LOGO"
    printf '   Put your own logo file there (see README, "Logo") and run install.sh again.\n'
    LOGO=""
fi
[ -z "$HUD_LABEL" ] && HUD_LABEL="$(id -un | tr '[:lower:]' '[:upper:]')"

say() { printf '\033[38;2;91;238;220m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[38;2;255;42;79m!!\033[0m %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
schema() { gsettings list-schemas 2>/dev/null | grep -qx "$1"; }

# ------------------------------------------------------------------ checks
say "checking requirements"
[ "${XDG_SESSION_TYPE:-}" = x11 ] || warn "session is not X11: frames/cursors are tuned for Budgie on X11"
echo "${XDG_CURRENT_DESKTOP:-}" | grep -qi budgie || warn "this does not look like a Budgie session"
missing=()
for c in python3 gsettings dconf xprop xwininfo xrandr fc-cache gtk-update-icon-cache curl; do have "$c" || missing+=("$c"); done
python3 -I -c "import PIL, cairo, gi" 2>/dev/null || missing+=("python3-pil python3-cairo python3-gi")
[ -d /usr/share/themes/Pocillo-dark ] || missing+=("ubuntu-budgie-themes (Pocillo-dark)")
if [ ${#missing[@]} -gt 0 ]; then
    warn "missing: ${missing[*]}"
    echo "   sudo apt install python3-pil python3-cairo python3-gi gir1.2-gtk-3.0 x11-utils x11-xserver-utils curl ubuntu-budgie-themes conky-all"
    exit 1
fi
have conky || warn "conky not installed: the HUD will be skipped (sudo apt install conky-all)"

# primary monitor geometry (for the wallpaper fillet, conky head and the ShowTime clock)
read -r MON_IDX MON_W MON_H MON_X MON_Y < <(xrandr --listmonitors | awk '/\*/{
    sub(":", "", $1); split($3, g, /[x+]/); split(g[1], w, "/"); split(g[2], h, "/");
    print $1, w[1], h[1], g[3], g[4]; exit }')
MON_IDX=${MON_IDX:-0}; MON_W=${MON_W:-1920}; MON_H=${MON_H:-1080}; MON_X=${MON_X:-0}; MON_Y=${MON_Y:-0}
say "primary monitor: ${MON_W}x${MON_H}+${MON_X}+${MON_Y} (head $MON_IDX)"

# ------------------------------------------------------------------ backup
DATA="$HOME/.local/share/cyberneon"
STAMP=$(date +%Y%m%d-%H%M%S)
BK="$DATA/backups/$STAMP"
mkdir -p "$BK"
dconf dump / > "$BK/dconf-full.ini"
[ -f "$HOME/.bashrc" ] && cp "$HOME/.bashrc" "$BK/bashrc"
[ -f "$HOME/.config/gtk-4.0/gtk.css" ] && cp "$HOME/.config/gtk-4.0/gtk.css" "$BK/gtk4-gtk.css"
[ -f "$HOME/.config/autostart/plank.desktop" ] && cp "$HOME/.config/autostart/plank.desktop" "$BK/plank.desktop"
if [ ! -d "$DATA/backups/pristine" ]; then   # first install: this is the state uninstall.sh goes back to
    cp -r "$BK" "$DATA/backups/pristine"
fi
say "backup: $BK"

# ------------------------------------------------------------------ fonts, icons, cursors, theme
say "fonts"
bash "$SC/install_fonts.sh"

if [ "$PAPIRUS" = 1 ]; then
    say "Papirus icons (cyber folders)"
    bash "$SC/install_papirus.sh"
fi

say "GTK theme -> ~/.themes/CyberNeon"
python3 -I "$SC/build_theme.py" --overrides "$REPO/theme"
mkdir -p "$HOME/.config/gtk-4.0"
cp "$REPO/theme/libadwaita.css" "$HOME/.config/gtk-4.0/gtk.css"

say "icon theme -> CyberNeon-Icons"
ICONS="$HOME/.local/share/icons"
rm -rf "$ICONS/CyberNeon-Icons"
[ -n "$LOGO" ] && python3 -I "$SC/make_logo_icon.py" "$LOGO" "$ICONS/CyberNeon-Icons"
python3 -I "$SC/make_icons.py" "$ICONS/CyberNeon-Icons"
gtk-update-icon-cache -q -f -t "$ICONS/CyberNeon-Icons" || true

say "cursor theme -> CyberNeon-Cursors"
python3 -I "$SC/make_cursors.py" "$ICONS/CyberNeon-Cursors"
# libXcursor 1.2 on Ubuntu 24.04 searches ~/.icons and /usr/share/icons, not ~/.local/share/icons
mkdir -p "$HOME/.icons/default"
ln -sfn "$ICONS/CyberNeon-Cursors" "$HOME/.icons/CyberNeon-Cursors"
printf '[Icon Theme]\nName=Default\nInherits=CyberNeon-Cursors\n' > "$HOME/.icons/default/index.theme"

if [ -f /var/lib/snapd/desktop/applications/firefox_firefox.desktop ]; then
    mkdir -p "$HOME/.local/share/applications"   # snap Firefox uses an absolute icon path: point it to the theme icon
    sed 's|^Icon=/snap/firefox/current/default256.png|Icon=firefox|' \
        /var/lib/snapd/desktop/applications/firefox_firefox.desktop > "$HOME/.local/share/applications/firefox_firefox.desktop"
fi

# ------------------------------------------------------------------ wallpaper + system assets
say "wallpaper -> ~/Pictures/Wallpapers/$WALLPAPER"
WALLDIR="$HOME/Pictures/Wallpapers"; mkdir -p "$WALLDIR"
WARGS=(--label "$LABEL" --monitor-width "$MON_W"); [ -n "$LOGO" ] && WARGS+=(--logo "$LOGO")
python3 -I "$SC/make_wallpaper.py" "$WALLDIR/$WALLPAPER" "${WARGS[@]}"

say "login / GRUB assets -> $DATA/system (install them with system/*.sh)"
mkdir -p "$DATA/system"
python3 -I "$SC/make_wallpaper.py" "$DATA/system/login-4k.png" --login "${WARGS[@]}"
python3 -I "$SC/make_system_assets.py" "$DATA/system/login-4k.png" "$DATA/system"
rm -f "$DATA/system/login-4k.png"
cp "$REPO/system/grub/theme.txt" "$DATA/system/grub/theme.txt"
if have grub-mkfont; then
    F="$HOME/.local/share/fonts/cyberneon"
    grub-mkfont -s 18 -o "$DATA/system/grub/chakra_medium_18.pf2" "$F/ChakraPetch-Medium.ttf"
    grub-mkfont -s 22 -o "$DATA/system/grub/chakra_medium_22.pf2" "$F/ChakraPetch-Medium.ttf"
    grub-mkfont -s 22 -o "$DATA/system/grub/chakra_bold_22.pf2" "$F/ChakraPetch-Bold.ttf"
    grub-mkfont -s 28 -o "$DATA/system/grub/chakra_bold_28.pf2" "$F/ChakraPetch-Bold.ttf"
fi

# ------------------------------------------------------------------ desktop settings
say "appearance settings"
IF=org.gnome.desktop.interface
gsettings set $IF color-scheme 'prefer-dark'
gsettings set $IF icon-theme 'CyberNeon-Icons'
gsettings set $IF font-name "$UI_FONT"
gsettings set $IF document-font-name "$DOC_FONT"
gsettings set org.gnome.desktop.wm.preferences theme 'CyberNeon'
gsettings set org.gnome.desktop.wm.preferences titlebar-font "$TITLE_FONT"
# re-select theme and cursor so running apps reload them
gsettings set $IF gtk-theme 'Adwaita-dark'; sleep 1; gsettings set $IF gtk-theme 'CyberNeon'
gsettings set $IF cursor-theme 'DMZ-White'; sleep 1; gsettings set $IF cursor-theme 'CyberNeon-Cursors'
BG=org.gnome.desktop.background
gsettings set $BG picture-options 'zoom'
gsettings set $BG primary-color '#070d1a'
gsettings set $BG picture-uri ''   # force a reload even if the file name did not change
gsettings set $BG picture-uri "file://$WALLDIR/$WALLPAPER"
gsettings set $BG picture-uri-dark "file://$WALLDIR/$WALLPAPER"

say "panels (top bar + left dock)"
python3 -I "$SC/panels.py" --pinned "$PINNED"
if [ -f "$HOME/.config/autostart/plank.desktop" ] || [ -f /etc/xdg/autostart/plank.desktop ]; then
    if [ ! -f "$HOME/.config/autostart/plank.desktop" ]; then
        mkdir -p "$HOME/.config/autostart"; cp /etc/xdg/autostart/plank.desktop "$HOME/.config/autostart/"
    fi
    sed -i 's/^X-GNOME-Autostart-enabled=true/X-GNOME-Autostart-enabled=false/' "$HOME/.config/autostart/plank.desktop"
    grep -q '^X-GNOME-Autostart-enabled=' "$HOME/.config/autostart/plank.desktop" \
        || echo 'X-GNOME-Autostart-enabled=false' >> "$HOME/.config/autostart/plank.desktop"
fi
pkill -x plank 2>/dev/null || true

if schema org.ubuntubudgie.plugins.budgie-showtime; then
    say "ShowTime desktop clock (top-right of the primary monitor)"
    K=org.ubuntubudgie.plugins.budgie-showtime
    gsettings set $K anchor 'ne'; gsettings set $K autoposition false
    gsettings set $K xposition $((MON_X + MON_W - 50)); gsettings set $K yposition $((MON_Y + 74))
    gsettings set $K timefont 'Orbitron Medium 60'; gsettings set $K timefontcolor '#5BEEDC'
    gsettings set $K datefont 'Chakra Petch SemiBold 17'; gsettings set $K datefontcolor '#FB3048'
    gsettings set $K dateformat '%A  //  %d.%m.%Y'; gsettings set $K linespacing -6
fi

if schema com.gexperts.Tilix.ProfilesList; then
    PROFILE=$(gsettings get com.gexperts.Tilix.ProfilesList default | tr -d "'")
    if [ -n "$PROFILE" ]; then
        say "Tilix colours (profile $PROFILE)"
        TP="com.gexperts.Tilix.Profile:/com/gexperts/Tilix/profiles/$PROFILE/"
        gsettings set "$TP" use-theme-colors false
        gsettings set "$TP" foreground-color '#7EDDD5'; gsettings set "$TP" background-color '#0B1620'
        gsettings set "$TP" background-transparency-percent 4
        gsettings set "$TP" cursor-colors-set true
        gsettings set "$TP" cursor-background-color '#FF2A4F'; gsettings set "$TP" cursor-foreground-color '#0B1620'
        gsettings set "$TP" highlight-colors-set true
        gsettings set "$TP" highlight-background-color '#5BEEDC'; gsettings set "$TP" highlight-foreground-color '#0B1620'
        gsettings set "$TP" badge-color-set true; gsettings set "$TP" badge-color '#FF2A4F'
        gsettings set "$TP" bold-color-set true; gsettings set "$TP" bold-color '#5BEEDC'
        gsettings set "$TP" palette "['#0B1620', '#FF2A4F', '#2EF2A8', '#FCEE0A', '#3AA8FF', '#D16BFF', '#5BEEDC', '#A9C6C4', '#2A4556', '#FF6B7C', '#74FFCB', '#FFF56B', '#7CC6FF', '#E3A1FF', '#9FF0E8', '#E8FFFC']"
    fi
    mkdir -p "$HOME/.config/tilix/schemes"; cp "$REPO/config/tilix/cyberneon.json" "$HOME/.config/tilix/schemes/"
fi

# ------------------------------------------------------------------ prompt, HUD, Nemo transparency
say "bash prompt"
mkdir -p "$HOME/.config/cyberneon"
cp "$REPO/config/bash/prompt.bash" "$HOME/.config/cyberneon/prompt.bash"
if ! grep -q '# >>> cyberneon prompt >>>' "$HOME/.bashrc" 2>/dev/null; then
    cat >> "$HOME/.bashrc" <<'EOF'

# >>> cyberneon prompt >>>
[ -f "$HOME/.config/cyberneon/prompt.bash" ] && . "$HOME/.config/cyberneon/prompt.bash"
# <<< cyberneon prompt <<<
EOF
fi

AUTO="$HOME/.config/autostart"; mkdir -p "$AUTO"
if have conky; then
    say "conky HUD (label: $HUD_LABEL)"
    CK="$HOME/.config/conky/cyberneon"; mkdir -p "$CK"
    sed "s/^    xinerama_head = .*/    xinerama_head = $MON_IDX,/" "$REPO/config/conky/cyberneon.conf" > "$CK/cyberneon.conf"
    sed "s/@HUD_LABEL@/$HUD_LABEL/" "$REPO/config/conky/hud.lua" > "$CK/hud.lua"
    cat > "$AUTO/cyberneon-hud.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=CyberNeon HUD
Comment=Conky system HUD (CyberNeon theme)
Exec=sh -c "sleep 4 && conky -c $CK/cyberneon.conf"
Icon=utilities-system-monitor
Terminal=false
X-GNOME-Autostart-enabled=true
OnlyShowIn=Budgie;
EOF
fi

say "Nemo transparency ($NEMO_OPACITY)"
cp "$REPO/config/nemo-opacity.sh" "$HOME/.config/cyberneon/nemo-opacity.sh"
chmod +x "$HOME/.config/cyberneon/nemo-opacity.sh"
cat > "$AUTO/cyberneon-nemo-opacity.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=CyberNeon Nemo transparency
Comment=Slight transparency for file manager windows
Exec=$HOME/.config/cyberneon/nemo-opacity.sh $NEMO_OPACITY
Terminal=false
X-GNOME-Autostart-enabled=true
OnlyShowIn=Budgie;
EOF

# ------------------------------------------------------------------ restart
if [ "$RESTART" = 1 ]; then
    say "restarting window manager, panel, HUD"
    bash "$SC/restart_wm.sh"
    setsid -f budgie-panel --replace >/dev/null 2>&1 < /dev/null
    if have conky; then
        pkill -x conky 2>/dev/null || true; sleep 1
        setsid -f conky -c "$HOME/.config/conky/cyberneon/cyberneon.conf" >/dev/null 2>&1 < /dev/null
    fi
    for p in $(pgrep -f '[c]yberneon/nemo-opacity.sh'); do kill "$p" 2>/dev/null || true; done
    pkill -f 'xprop -root -spy _NET_CLIENT_LIST' 2>/dev/null || true
    setsid -f "$HOME/.config/cyberneon/nemo-opacity.sh" "$NEMO_OPACITY" >/dev/null 2>&1 < /dev/null
fi

say "done. Login screen and GRUB: sudo bash $REPO/system/install-login.sh / install-grub.sh"
say "undo: $REPO/uninstall.sh   (backup of this run: $BK)"
