#!/bin/bash
# Preview of the CyberNeon Plymouth splash WITHOUT installing it or rebooting: runs the real Plymouth
# (Ubuntu 24.04, X11 renderer on a virtual screen) in a throw-away Docker container and saves screenshots
# in lab/out/plymouth-*.png. Your system is not touched. Needs Docker; run ./install.sh first (builds the assets).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
A="$HOME/.local/share/cyberneon/system/plymouth"
[ -f "$A/cyberneon.script" ] || { echo "assets not found in $A: run ./install.sh first"; exit 1; }
OUT="$REPO/lab/out"; mkdir -p "$OUT"
docker run --rm -v "$A:/theme:ro" -v "$OUT:/out" ubuntu:24.04 bash -c '
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -qq --no-install-recommends plymouth plymouth-x11 plymouth-label fonts-dejavu-core xvfb x11-apps imagemagick >/dev/null 2>&1
mkdir -p /usr/share/plymouth/themes/cyberneon && cp /theme/* /usr/share/plymouth/themes/cyberneon/
printf "[Daemon]\nTheme=cyberneon\nShowDelay=0\n" > /etc/plymouth/plymouthd.conf
Xvfb :5 -screen 0 1920x1080x24 >/dev/null 2>&1 & sleep 2
export DISPLAY=:5
plymouthd --no-daemon --debug --debug-file=/out/plymouthd.log --tty=/dev/tty0 \
    --kernel-command-line="quiet splash plymouth.ignore-serial-consoles" & sleep 2
plymouth show-splash
for t in 1 12; do sleep $t; xwd -root -display :5 | convert xwd:- /out/plymouth-$t.png; done
plymouth ask-for-password --prompt="Passphrase for /dev/sda3" >/dev/null 2>&1 & sleep 1.5
xwd -root -display :5 | convert xwd:- /out/plymouth-password.png
plymouth quit || true
chmod -R a+rwX /out
'
echo "screenshots: $OUT/plymouth-1.png plymouth-12.png plymouth-password.png"
