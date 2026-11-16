#!/bin/bash
# CyberNeon: slight transparency for Nemo (file manager) windows.
# Sets _NET_WM_WINDOW_OPACITY on every Nemo window, now and whenever windows open.
# Usage: nemo-opacity.sh [opacity 0.0-1.0]   (default 0.90)
OPACITY="${1:-0.90}"
VAL=$(awk -v o="$OPACITY" 'BEGIN { printf "0x%08x", o * 4294967295 }')
apply() {
    for w in $(xprop -root _NET_CLIENT_LIST 2>/dev/null | grep -o '0x[0-9a-f]*'); do
        xprop -id "$w" WM_CLASS 2>/dev/null | grep -q '"nemo"' || continue
        xprop -id "$w" -f _NET_WM_WINDOW_OPACITY 32c -set _NET_WM_WINDOW_OPACITY "$VAL" 2>/dev/null
    done
}
apply
xprop -root -spy _NET_CLIENT_LIST | while read -r _; do apply; done
