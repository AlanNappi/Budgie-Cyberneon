#!/usr/bin/env python3
"""Prints the input shape of an X window (the parts that take clicks): input_shape.py WINDOW_ID
Output: number of rectangles, then the distinct sizes. Used by the lab to check the radar is click-through."""
import ctypes, ctypes.util, sys


class Rect(ctypes.Structure):
    _fields_ = [("x", ctypes.c_short), ("y", ctypes.c_short), ("w", ctypes.c_ushort), ("h", ctypes.c_ushort)]


x11 = ctypes.CDLL(ctypes.util.find_library("X11"))
xext = ctypes.CDLL(ctypes.util.find_library("Xext"))
x11.XOpenDisplay.restype = ctypes.c_void_p
xext.XShapeGetRectangles.restype = ctypes.POINTER(Rect)
display = x11.XOpenDisplay(None)
n, order = ctypes.c_int(), ctypes.c_int()
rects = xext.XShapeGetRectangles(ctypes.c_void_p(display), ctypes.c_ulong(int(sys.argv[1], 16)), 2,   # 2 = ShapeInput
                                 ctypes.byref(n), ctypes.byref(order))
print(n.value, sorted({(rects[i].w, rects[i].h) for i in range(n.value)}))
