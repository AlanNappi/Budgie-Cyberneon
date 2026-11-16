#!/bin/bash
# CyberNeon: theme the LightDM / slick-greeter login screen (Ubuntu Budgie).
# Run ./install.sh first (it builds the assets), then:  sudo bash system/install-login.sh
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run with sudo"; exit 1; }
U="$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)"
A="$U/.local/share/cyberneon/system"
[ -f "$A/cyberneon-login.png" ] || { echo "assets not found in $A: run ./install.sh as your user first"; exit 1; }

install -d /usr/share/backgrounds/cyberneon
install -m644 "$A/cyberneon-login.png" /usr/share/backgrounds/cyberneon/cyberneon-login.png

rm -rf /usr/share/themes/CyberNeon /usr/share/icons/CyberNeon-Cursors
cp -r "$U/.themes/CyberNeon" /usr/share/themes/CyberNeon
cp -r "$U/.local/share/icons/CyberNeon-Cursors" /usr/share/icons/CyberNeon-Cursors
chown -R root:root /usr/share/themes/CyberNeon /usr/share/icons/CyberNeon-Cursors
chmod -R a+rX /usr/share/themes/CyberNeon /usr/share/icons/CyberNeon-Cursors

install -d /usr/local/share/fonts/cyberneon
install -m644 "$U"/.local/share/fonts/cyberneon/*.ttf /usr/local/share/fonts/cyberneon/
fc-cache -f /usr/local/share/fonts/cyberneon >/dev/null

if [ -f /etc/lightdm/slick-greeter.conf ] && [ ! -f /etc/lightdm/slick-greeter.conf.bak-cyberneon ]; then
    cp /etc/lightdm/slick-greeter.conf /etc/lightdm/slick-greeter.conf.bak-cyberneon
fi
cat > /etc/lightdm/slick-greeter.conf <<'CONF'
[Greeter]
background=/usr/share/backgrounds/cyberneon/cyberneon-login.png
background-color=#070d1a
draw-user-backgrounds=false
draw-grid=false
theme-name=CyberNeon
icon-theme-name=Pocillo
cursor-theme-name=CyberNeon-Cursors
cursor-theme-size=24
font-name=Chakra Petch Medium 11
clock-format=%Y-%m-%d  %H:%M
show-clock=true
CONF
echo "OK: login screen themed (visible at the next logout / reboot)."
echo "undo: sudo rm /etc/lightdm/slick-greeter.conf   (or restore slick-greeter.conf.bak-cyberneon)"
