#!/bin/bash
# CyberNeon: Plymouth boot splash "jack-in" (the screen between GRUB and the login). Original artwork.
# FAN MADE - inspired by Cyberpunk 2077 by CD PROJEKT RED (names/logos/trademarks of CD PROJEKT S.A.).
# Run ./install.sh first (it builds the assets), then:
#   sudo bash system/install-plymouth.sh           install and select the CyberNeon splash
#   sudo bash system/install-plymouth.sh --undo    go back to the previous splash
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run with sudo"; exit 1; }
T=/usr/share/plymouth/themes/cyberneon
ALT=/usr/share/plymouth/themes/default.plymouth
for c in update-alternatives update-initramfs; do
    command -v "$c" >/dev/null || { echo "$c not found (this script is for Ubuntu/Debian)"; exit 1; }
done

if [ "${1:-}" = "--undo" ]; then
    update-alternatives --remove default.plymouth "$T/cyberneon.plymouth" 2>/dev/null || true
    update-alternatives --auto default.plymouth
    update-initramfs -u
    echo "OK: splash restored -> $(readlink -f "$ALT")"
    exit 0
fi

U="$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)"
A="$U/.local/share/cyberneon/system/plymouth"
[ -f "$A/cyberneon.script" ] || { echo "assets not found in $A: run ./install.sh as your user first"; exit 1; }
[ -f /usr/lib/x86_64-linux-gnu/plymouth/script.so ] || ls /usr/lib/*/plymouth/script.so >/dev/null 2>&1 \
    || { echo "Plymouth script module missing: sudo apt install plymouth"; exit 1; }

install -d "$T"
install -m644 "$A"/* "$T/"
update-alternatives --install "$ALT" default.plymouth "$T/cyberneon.plymouth" 200
update-alternatives --set default.plymouth "$T/cyberneon.plymouth"
grep -qE '^GRUB_CMDLINE_LINUX_DEFAULT=.*splash' /etc/default/grub 2>/dev/null \
    || echo "note: 'splash' is not in GRUB_CMDLINE_LINUX_DEFAULT (/etc/default/grub): the splash will not show"
update-initramfs -u
echo "OK: CyberNeon boot splash installed (you will see it at the next boot)."
echo "undo: sudo bash $(cd "$(dirname "$0")" && pwd)/install-plymouth.sh --undo"
