#!/bin/bash
# FAN MADE by a huge fan - inspired by Cyberpunk 2077 by CD PROJEKT RED. Cyberpunk 2077, Arasaka and all
# related names/logos/trademarks belong to CD PROJEKT S.A. Unofficial, non-commercial, not endorsed by CD PROJEKT RED.
# CyberNeon - uninstall (user level). Restores the settings saved before the FIRST install
# (~/.local/share/cyberneon/backups/pristine) and removes the files installed by install.sh.
#
#   ./uninstall.sh            restore and remove (fonts and Papirus are kept)
#   ./uninstall.sh --purge    also remove the CyberNeon fonts and Papirus icons
# Login screen / GRUB / boot splash: see the "undo" lines printed by system/install-*.sh.
set -euo pipefail
PURGE=0; [ "${1:-}" = "--purge" ] && PURGE=1
DATA="$HOME/.local/share/cyberneon"
P="$DATA/backups/pristine"
say() { printf '\033[38;2;91;238;220m==>\033[0m %s\n' "$*"; }

if [ -f "$P/dconf-full.ini" ]; then
    say "restoring settings from $P"
    dconf load / < "$P/dconf-full.ini"
else
    say "no pristine backup found: settings are left as they are"
fi

# settings that were at their default are not in the saved dump: put them back explicitly
gsettings reset com.solus-project.budgie-panel notification-position 2>/dev/null || true
grep -q "^notification-position=" "$P/dconf-full.ini" 2>/dev/null && dconf load / < "$P/dconf-full.ini"
if [ "$(gsettings get org.gnome.desktop.sound theme-name 2>/dev/null)" = "'cyberneon'" ]; then
    gsettings reset org.gnome.desktop.sound theme-name
fi
if [ -f "$DATA/event-sounds.previous" ]; then
    gsettings set org.gnome.desktop.sound event-sounds "$(cat "$DATA/event-sounds.previous")"
    rm -f "$DATA/event-sounds.previous"
fi

say "removing files"
pkill -x conky 2>/dev/null || true
for p in $(pgrep -f '[c]yberneon/nemo-opacity.sh'); do kill "$p" 2>/dev/null || true; done
pkill -f 'xprop -root -spy _NET_CLIENT_LIST' 2>/dev/null || true
for p in $(pgrep -f '[l]ive-wallpaper.py|[c]yberneon-hud.py'); do kill "$p" 2>/dev/null || true; done
rm -rf "$HOME/.themes/CyberNeon" \
       "$HOME/.local/share/icons/CyberNeon-Icons" "$HOME/.local/share/icons/CyberNeon-Cursors" \
       "$HOME/.config/conky/cyberneon" "$HOME/.config/cyberneon" \
       "$HOME/.config/autostart/cyberneon-hud.desktop" "$HOME/.config/autostart/cyberneon-nemo-opacity.desktop" \
       "$HOME/.config/autostart/cyberneon-live-wallpaper.desktop" "$HOME/.config/autostart/cyberneon-jackin.desktop" \
       "$HOME/.local/share/sounds/cyberneon" "$DATA/hud-logo.png" "$DATA/panels-state.json" "$DATA/radar-nodes" "$DATA/system/terminal-plate.png" \
       "$HOME/.config/Kvantum/CyberNeon" \
       "$HOME/.config/tilix/schemes/cyberneon.json"
[ -L "$HOME/.icons/CyberNeon-Cursors" ] && rm -f "$HOME/.icons/CyberNeon-Cursors"
grep -q 'Inherits=CyberNeon-Cursors' "$HOME/.icons/default/index.theme" 2>/dev/null && rm -f "$HOME/.icons/default/index.theme"
grep -q '^Icon=firefox$' "$HOME/.local/share/applications/firefox_firefox.desktop" 2>/dev/null \
    && rm -f "$HOME/.local/share/applications/firefox_firefox.desktop"
if [ -f "$P/gtk4-gtk.css" ]; then cp "$P/gtk4-gtk.css" "$HOME/.config/gtk-4.0/gtk.css"; else rm -f "$HOME/.config/gtk-4.0/gtk.css"; fi
if [ -f "$P/plank.desktop" ]; then cp "$P/plank.desktop" "$HOME/.config/autostart/plank.desktop"; fi
if [ -f "$P/kvantum.kvconfig" ]; then cp "$P/kvantum.kvconfig" "$HOME/.config/Kvantum/kvantum.kvconfig"
elif grep -q '^theme=CyberNeon' "$HOME/.config/Kvantum/kvantum.kvconfig" 2>/dev/null; then rm -f "$HOME/.config/Kvantum/kvantum.kvconfig"; fi
if grep -q '# >>> cyberneon qt >>>' "$HOME/.xsessionrc" 2>/dev/null; then
    sed -i '/# >>> cyberneon qt >>>/,/# <<< cyberneon qt <<</d' "$HOME/.xsessionrc"
    [ -s "$HOME/.xsessionrc" ] || [ -f "$P/xsessionrc" ] || rm -f "$HOME/.xsessionrc"
fi
# remove the prompt block from ~/.bashrc
if grep -q '# >>> cyberneon prompt >>>' "$HOME/.bashrc" 2>/dev/null; then
    sed -i '/^$/N;/\n# >>> cyberneon prompt >>>/!P;D' "$HOME/.bashrc" 2>/dev/null || true
    sed -i '/# >>> cyberneon prompt >>>/,/# <<< cyberneon prompt <<</d' "$HOME/.bashrc"
fi

if [ "$PURGE" = 1 ]; then
    say "purging fonts and Papirus"
    rm -rf "$HOME/.local/share/fonts/cyberneon" "$HOME/.local/share/icons/Papirus" "$HOME/.local/share/icons/Papirus-Dark"
    fc-cache -f >/dev/null || true
fi

say "restarting window manager and panel"
bash "$(cd "$(dirname "$0")" && pwd)/scripts/restart_wm.sh"
setsid -f budgie-panel --replace >/dev/null 2>&1 < /dev/null
pgrep -x plank >/dev/null || (command -v plank >/dev/null && setsid -f plank >/dev/null 2>&1 < /dev/null) || true
say "done (wallpapers in ~/Pictures/Wallpapers and backups in $DATA are kept)"
