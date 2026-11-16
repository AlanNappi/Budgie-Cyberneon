#!/bin/bash
# Restart budgie-wm so it reloads the theme (it caches the GTK theme it loaded at startup).
# `budgie-wm --replace` can race with the exiting instance, which deletes the root window's
# _NET_SUPPORTING_WM_CHECK property; without it GTK apps stop drawing CSD shadows/borders.
# This script restores the property when that happens.
setsid -f budgie-wm --replace >/dev/null 2>&1 < /dev/null
sleep 5
if ! xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null | grep -q 'window id'; then
    WID=$(xwininfo -root -children | awk '/"Mutter\(Budgie\)"/{print $1; exit}')
    [ -n "$WID" ] && python3 -I - "$WID" <<'PY'
import ctypes, ctypes.util, sys
x = ctypes.CDLL(ctypes.util.find_library("X11"))
x.XOpenDisplay.restype = ctypes.c_void_p
x.XDefaultRootWindow.restype = ctypes.c_ulong; x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
x.XInternAtom.restype = ctypes.c_ulong; x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
x.XChangeProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong,
                              ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
d = x.XOpenDisplay(None)
w = (ctypes.c_ulong * 1)(int(sys.argv[1], 16))
x.XChangeProperty(d, x.XDefaultRootWindow(d), x.XInternAtom(d, b"_NET_SUPPORTING_WM_CHECK", 0),
                  33, 32, 0, ctypes.cast(w, ctypes.c_void_p), 1)   # XA_WINDOW, PropModeReplace
x.XSync(d, 0)
print("restored _NET_SUPPORTING_WM_CHECK ->", sys.argv[1])
PY
fi
