"""CyberNeon HUD widgets for Budgie: Biomonitor, Radar with objective tracker, Chrono and the Quickhack OSD.
Original artwork, real system data. Each widget keeps a pre-rendered layer and only animates what really moves.
FAN MADE - inspired by Cyberpunk 2077 by CD PROJEKT RED (trademarks of CD PROJEKT S.A.).
"""
import math, os, time

import cairo
import gi
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib

from cn_draw import AMBER, CY, NAVY, RED, TXT, HudWindow, new_layer, poly, text, with_glow
from cn_state import rate_text
from cn_threats import MIN_RATE, SHOW, quickhack, size_text

try:
    gi.require_version("Wnck", "3.0")
    from gi.repository import Wnck
except (ValueError, ImportError):
    Wnck = None

UI, NUM, BODY = "Rajdhani", "Orbitron", "Chakra Petch"


def grouped(n):
    return f"{int(round(n)):,}".replace(",", " ")


def pulse(t, period=0.9):
    return 0.2 + 0.8 * (0.5 - 0.5 * math.cos(2 * math.pi * t / period))


class Biomonitor(HudWindow):
    PAD = 18
    W, H = 548, 92

    def __init__(self, app):
        super().__init__("cyberneon-biomonitor", self.W + 2 * self.PAD, self.H + 2 * self.PAD)
        self.app = app; self.layer = None; self.status_layer = None

    def status(self):
        a = self.app
        if a.reactor.alert:
            who = a.threats.culprit(a.reactor.reason) if a.threats else ""
            return "!! OVERLOAD  //  " + a.reactor.reason + (f"  //  {who.upper()}" if who else ""), True
        if a.power and a.power.low:
            return "LOW POWER  //  ANIMATION OFF", True
        if a.tcc and a.tcc.profile:
            return "TCC  //  " + a.tcc.profile, False
        return f"LINK STABLE  //  ID 0x{len(a.cfg['label']) * 4097 + 2077:X}", False

    def rebuild(self):
        a = self.app; m = a.metrics; alert = a.reactor.alert
        surf, cr = new_layer(self.w, self.h)
        cr.translate(self.PAD, self.PAD)
        text(cr, "OPERATOR // " + a.cfg["label"], 58, 0, UI, 14, bold=True, spacing=3)

        # level badge = uptime hours
        cr.save(); cr.translate(0, 2)
        poly(cr, [(10, 1), (47, 1), (47, 38), (38, 47), (1, 47), (1, 10)])
        cr.set_source_rgba(*RED, 0.12); cr.fill_preserve()
        cr.set_source_rgba(*RED, 1); cr.set_line_width(2); cr.stroke()
        text(cr, str(m.uptime_h), 24, 7, NUM, 20, RED, bold=True, align="center")
        text(cr, "UP·H", 24, 33, UI, 9, RED, bold=True, spacing=1, align="center")
        cr.restore()

        # integrity bar: free memory
        integrity = max(0.0, min(1.0, m.free_mb / m.total_mb))
        lit = round(integrity * 34)
        for i in range(34):
            if i < lit:
                cr.set_source_rgba(*(RED if integrity < 0.15 else CY), 1)
            else:
                cr.set_source_rgba(*CY, 0.12)
            cr.rectangle(58 + i * 12, 20, 10, 13); cr.fill()
        text(cr, f"{grouped(m.free_mb)} / {grouped(m.total_mb)}", 58, 36, NUM, 13)
        text(cr, "MEM FREE", 238, 38, UI, 11, alpha=0.65, bold=True, spacing=3)
        text(cr, f"STORAGE {m.disk:.0f}%", 58 + 34 * 12 - 2, 38, UI, 11, RED, 0.95, bold=True, spacing=2, align="right")
        cr.set_source_rgba(*CY, 0.15); cr.rectangle(58, 54, 406, 2); cr.fill()
        cr.set_source_rgba(*RED, 1); cr.rectangle(58, 54, 406 * max(0, min(100, m.disk)) / 100, 2); cr.fill()

        # CELL CHARGE: only with a battery
        p = a.power
        if p and p.has_battery:
            low_limit = a.cfg["low_power"]
            weak = p.percent < low_limit
            text(cr, "CELL CHARGE", 476, 18, UI, 10, RED if p.low else CY, 1 if p.low else 0.65, bold=True, spacing=1)
            for i in range(10):
                if i < math.ceil(p.percent / 10):
                    cr.set_source_rgba(*(RED if weak else CY), 1)
                else:
                    cr.set_source_rgba(*CY, 0.12)
                cr.rectangle(476 + i * 7.4, 33, 5.4, 9); cr.fill()
            text(cr, f"{p.percent}%" + (" +" if p.charging else ""), 476, 44, NUM, 11, RED if weak else CY)

        # CPU units: free capacity
        text(cr, "CPU", 0, 66, UI, 14, bold=True, spacing=3)
        lit = round((1 - max(0, min(100, m.cpu)) / 100) * 12)
        cr.set_line_width(1)
        for i in range(12):
            x = 40 + i * 19
            poly(cr, [(x + .5, 68.5), (x + 14.5, 68.5), (x + 14.5, 76.5), (x + 10, 80.5), (x + .5, 80.5)])
            if i < lit:
                cr.set_source_rgba(*CY, 1); cr.fill_preserve()
            cr.set_source_rgba(*CY, 1 if i < lit else 0.4); cr.stroke()
        text(cr, f"{m.cpu:.0f}% LOAD", 40 + 12 * 19 + 6, 67, NUM, 12)

        # network chips
        for i, (arrow, v) in enumerate((("▲", m.up), ("▼", m.down))):
            x = self.W - 80 - i * 88
            cr.set_source_rgba(*CY, 0.1); cr.rectangle(x, 64, 80, 20); cr.fill()
            cr.set_source_rgba(*CY, 0.5); cr.rectangle(x + .5, 64.5, 79, 19); cr.stroke()
            text(cr, f"{arrow} {rate_text(v)}/s", x + 40, 65, UI, 13, bold=True, align="center")

        self.layer = with_glow(surf, RED if alert else CY, 6, 0.6)

        s, hot = self.status()
        status, c2 = new_layer(self.w, 30)
        text(c2, s, self.PAD + self.W, 1, UI, 11, RED if hot else CY, 1 if hot else 0.55, bold=True, spacing=2, align="right")
        self.status_layer = status
        self.queue_draw()

    def animate(self, now):
        if self.app.reactor.alert:
            self.queue_draw()
        elif (now % 3.25) > 2.95:      # the status line flickers every few seconds
            self.queue_draw_area(self.PAD, 0, self.w - self.PAD, 34)

    def paint(self, cr):
        if not self.layer:
            return
        now = time.monotonic()
        cr.set_source_surface(self.layer, 0, 0); cr.paint()
        phase = now % 3.25
        flick = 0.25 if 2.95 < phase < 3.03 else 0.45 if 3.08 < phase < 3.14 else 1
        cr.set_source_surface(self.status_layer, 0, self.PAD); cr.paint_with_alpha(flick)
        if self.app.reactor.alert:
            w, h = self.W, self.H
            cr.translate(self.PAD - 4, self.PAD - 4)
            poly(cr, [(12, 1), (w + 7, 1), (w + 7, h - 7), (w - 5, h + 5), (1, h + 5), (1, 12)])
            a = 1 if self.app.low_power else pulse(now)
            cr.set_source_rgba(*RED, 0.07 * a); cr.fill_preserve()
            cr.set_source_rgba(*RED, a); cr.set_line_width(2); cr.stroke()


class Tracker:
    """Open windows of the current workspace: the active one first, then by last use."""

    def __init__(self, changed):
        self.changed = lambda: None; self.items = []; self.workspace = (1, 1); self.pending = False
        self.screen = Wnck.Screen.get_default() if Wnck else None
        if self.screen:
            for sig in ("active-window-changed", "window-opened", "window-closed", "active-workspace-changed",
                        "workspace-created", "workspace-destroyed", "window-stacking-changed"):
                self.screen.connect(sig, self.schedule)
            self.screen.force_update()
            self.refresh()
        self.changed = changed

    def schedule(self, *_a):
        if not self.pending:
            self.pending = True
            GLib.timeout_add(200, self.refresh)

    def refresh(self):
        self.pending = False
        s = self.screen
        ws = s.get_active_workspace()
        active = s.get_active_window()
        items = []
        for w in reversed(s.get_windows_stacked() or []):
            if w.is_skip_tasklist() or w.get_window_type() not in (Wnck.WindowType.NORMAL, Wnck.WindowType.DIALOG):
                continue
            if ws is not None and not w.is_on_workspace(ws):
                continue
            title = w.get_name() or ""
            if active is not None and w.get_xid() == active.get_xid():
                items.insert(0, title)
            else:
                items.append(title)
        now = (items[:5], ((ws.get_number() + 1) if ws else 1, s.get_workspace_count()))
        if now != (self.items, self.workspace):
            self.items, self.workspace = now
            self.changed()
        return False


def threat_metric(h):
    """What makes a contact heavy: its CPU (percent of one core, as in top) or its memory."""
    return f"{h['cpu']:.0f}%" if h["cpu"] / 100 >= h["mem"] / 30 else size_text(h["rss"])


HACKS = {   # quickhack: what it does, how it is shown
    "overload": ("OVERLOAD", "close it, it can still save", CY),
    "flatline": ("FLATLINE", "kill it, unsaved data is lost", RED),
}


class Radar(HudWindow):
    """Threat radar. Contacts are programs: the heavier, the closer to the centre (cyan, yellow, red). The sweep lights
    them up as it passes. Arrows on the rim are programs moving data (inward = download), a blinking red diamond is an
    intrusion event. The dial still tells the time: red notch = hour, cyan notch = minute, the sweep = seconds.
    Quickhack: a click on a contact opens a panel to close that program (OVERLOAD) or force it (FLATLINE), always after
    a confirmation. Only the contacts and the open panel take clicks, the rest of the window lets them through."""
    PAD = 14
    W, H = 316, 520
    R = 120
    LEVEL = (CY, AMBER, RED)
    PANEL = (14, 262, 316, 152)          # x, y, w, h of the quickhack panel, over the status lines

    def __init__(self, app):
        super().__init__("cyberneon-radar", self.W + 2 * self.PAD, self.H + 2 * self.PAD)
        self.app = app; self.layer = None; self.logo = None
        self.blips = []; self.alarms = []
        self.contacts = []                # [(x, y, hostile)] for clicks
        self.hack = None; self.hack_layer = None; self.buttons = {}; self.hover_name = ""; self.hack_seq = 0
        self.hackable = bool(app.cfg.get("quickhack", True))
        if self.hackable:
            self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK
                            | Gdk.EventMask.LEAVE_NOTIFY_MASK)
            self.connect("button-press-event", self.clicked)
            self.connect("motion-notify-event", self.hovered)
            self.connect("leave-notify-event", lambda *_a: self.set_hover(""))
        self.cx, self.cy = self.PAD + self.W - self.R, self.PAD + self.R
        path = app.cfg.get("logo") or ""
        if path and os.path.exists(path):
            try:
                self.logo = cairo.ImageSurface.create_from_png(path)
            except (cairo.Error, MemoryError):
                self.logo = None
        self.tracker = Tracker(self.rebuild)

    def at(self, bearing_deg, d):
        """Point at a compass bearing (0 = up, clockwise) and distance from the centre."""
        a = math.radians(bearing_deg)
        return self.cx + math.sin(a) * d, self.cy - math.cos(a) * d

    def notch(self, cr, bearing_deg, length, half, color):
        r = self.R - 1; da = math.degrees(half / r)
        poly(cr, [self.at(bearing_deg, r - length), self.at(bearing_deg - da, r), self.at(bearing_deg + da, r)])
        cr.set_source_rgba(*color, 1); cr.fill()

    def arrow(self, cr, bearing_deg, rate, inward):
        outer = self.R - 16
        inner = outer - min(34, 10 + 8 * math.log10(max(1, rate / MIN_RATE)))
        (x0, y0), (x1, y1) = (self.at(bearing_deg, outer), self.at(bearing_deg, inner))
        if not inward:
            (x0, y0), (x1, y1) = (x1, y1), (x0, y0)
        ux, uy = x1 - x0, y1 - y0; n = math.hypot(ux, uy) or 1; ux, uy = ux / n, uy / n
        cr.set_source_rgba(*CY, 1 if inward else 0.75); cr.set_line_width(2)
        cr.move_to(x0, y0); cr.line_to(x1 - ux * 4, y1 - uy * 4); cr.stroke()
        poly(cr, [(x1, y1), (x1 - ux * 7 - uy * 4.5, y1 - uy * 7 + ux * 4.5), (x1 - ux * 7 + uy * 4.5, y1 - uy * 7 - ux * 4.5)])
        cr.fill()

    def rebuild(self):
        surf, cr = new_layer(self.w, self.h)
        now = time.localtime(); r = self.R; cx, cy = self.cx, self.cy
        watch = self.app.threats
        snap = watch.snap if watch else {"hostiles": [], "traffic": []}

        cr.arc(cx, cy, r - 1, 0, 2 * math.pi)
        cr.set_source_rgba(*NAVY, 0.55); cr.fill_preserve()
        cr.set_source_rgba(*CY, 0.85); cr.set_line_width(1.5); cr.stroke()
        cr.set_line_width(1)
        for k, a in ((0.62, 0.25), (0.3, 0.2)):
            cr.arc(cx, cy, r * k, 0, 2 * math.pi); cr.set_source_rgba(*CY, a); cr.stroke()
        for i in range(60):                                       # 60 ticks
            big = i % 5 == 0
            ang = math.radians(i * 6); s, c = math.sin(ang), math.cos(ang)
            r0, r1 = r - 3, r - (13 if big else 8)
            cr.set_line_width(2 if big else 1)
            if i % 15 == 0:
                cr.set_source_rgba(*RED, 1)
            else:
                cr.set_source_rgba(*CY, 0.7)
            cr.move_to(cx + s * r0, cy - c * r0); cr.line_to(cx + s * r1, cy - c * r1); cr.stroke()
        for i, lab in enumerate(("00", "15", "30", "45")):
            ang = i * math.pi / 2
            text(cr, lab, cx + math.sin(ang) * (r - 24), cy - math.cos(ang) * (r - 24) - 7, UI, 11, alpha=0.7, bold=True,
                 align="center")

        # the time as notches on the rim: hour red, minute cyan
        self.notch(cr, ((now.tm_hour % 12) + now.tm_min / 60) * 30, 16, 7, RED)
        self.notch(cr, now.tm_min * 6 + now.tm_sec / 10, 12, 4.5, CY)

        # logo at the centre
        if self.logo:
            k = 34 / self.logo.get_width()
            cr.save(); cr.translate(cx - 17, cy - 17); cr.scale(k, k)
            cr.set_source_surface(self.logo, 0, 0); cr.get_source().set_filter(cairo.FILTER_BEST); cr.paint(); cr.restore()
        else:
            poly(cr, [(cx + 13 * math.cos(math.radians(60 * i - 90)), cy + 13 * math.sin(math.radians(60 * i - 90)))
                      for i in range(6)])
            cr.set_source_rgba(*RED, 1); cr.set_line_width(2); cr.stroke()

        # traffic: one arrow per direction, at the program's bearing
        for t in snap["traffic"]:
            if t["down"] >= MIN_RATE:
                self.arrow(cr, t["bearing"] - 4, t["down"], True)
            if t["up"] >= MIN_RATE:
                self.arrow(cr, t["bearing"] + 4, t["up"], False)

        # contacts: drawn by paint() so the sweep can light them; the names of the dangerous ones stay here
        blips, contacts = [], []
        for i, h in enumerate(snap["hostiles"]):
            k = min(1.0, max(0.0, (h["score"] - SHOW) / (1 - SHOW)))
            x, y = self.at(h["bearing"], r * (0.88 - 0.6 * k))          # the closest stays clear of the logo
            size = 3.5 + 3.5 * min(1.0, h["mem"] / 20)
            color = self.LEVEL[h["level"]]
            blips.append((x, y, size, color, h["bearing"]))
            contacts.append((x, y, h))
            if h["level"] >= 1 or i == 0:
                label = f"{h['name'].upper()[:12]} {threat_metric(h)}"
                if x > cx:
                    text(cr, label, x - size - 6, y - 8, UI, 12, color, bold=True, spacing=1, align="right")
                else:
                    text(cr, label, x + size + 6, y - 8, UI, 12, color, bold=True, spacing=1)
        self.blips, self.contacts = blips, contacts
        mono = time.monotonic()
        self.alarms = []
        for age, e in (watch.recent(60) if watch else []):
            x, y = self.at(e["bearing"], r - 30)
            self.alarms.append((mono + 60 - age, x, y))
            text(cr, e["kind"].upper(), x, y + 10, UI, 10, RED, 0.9, bold=True, spacing=1, align="center")

        # status lines: the heaviest contact, who moves data, the last intrusion
        right = self.PAD + self.W; y0 = self.PAD + 2 * r + 8; y = y0
        hs = snap["hostiles"]
        if hs:
            text(cr, f"HOSTILES {len(hs):02d}  //  {hs[0]['name'].upper()[:14]} {threat_metric(hs[0])}", right, y, UI, 15,
                 self.LEVEL[hs[0]["level"]], bold=True, spacing=2, align="right")
        else:
            text(cr, "ZONE CLEAR  //  NO HOSTILES", right, y, UI, 15, bold=True, spacing=2, align="right")
        y += 24
        parts = []
        d = max(snap["traffic"], key=lambda t: t["down"], default=None)
        if d and d["down"] >= MIN_RATE:
            parts.append(f"▼ {d['name'].upper()[:12]} {rate_text(d['down'])}/s")
        u = max(snap["traffic"], key=lambda t: t["up"], default=None)
        if u and u["up"] >= MIN_RATE:
            parts.append(f"▲ {u['name'].upper()[:12]} {rate_text(u['up'])}/s")
        text(cr, "   ".join(parts) or "NET  //  QUIET", right, y, UI, 13, CY, 1 if parts else 0.6, bold=True, spacing=2,
             align="right", width=self.W - 8)
        y += 22
        for age, e in (watch.recent(300) if watch else [])[:1]:
            text(cr, f"!! {e['text']}  {e['clock']}", right, y, UI, 12, RED, 1 if age < 60 else 0.6, bold=True, spacing=1,
                 align="right", width=self.W - 8)
            y += 22

        # objective tracker
        y += 12
        w = text(cr, "OBJECTIVE", right - 20, y, UI, 14, RED, bold=True, spacing=3, align="right")
        poly(cr, [(right - 7, y + 3), (right, y + 10), (right - 7, y + 17), (right - 14, y + 10)])
        cr.set_source_rgba(*RED, 1); cr.fill()
        y += 26
        t = self.tracker
        for i, title in enumerate(t.items):
            first = i == 0; s = 10 if first else 8
            cr.rectangle(right - s + .75, y + 10 - s / 2, s - 1.5, s - 1.5)
            cr.set_source_rgba(*CY, 1 if first else 0.6); cr.set_line_width(1.5)
            if first:
                cr.fill_preserve()
            cr.stroke()
            lim = self.W - 24
            text(cr, title.upper(), right - s - 8, y, UI, 17 if first else 14, CY if first else TXT, 1 if first else 0.75,
                 bold=first, spacing=1, align="right", width=None if len(title) < 26 else lim)
            y += 26 if first else 22
        if not t.items:
            text(cr, "NO ACTIVE GIG // STANDBY", right, y, UI, 15, TXT, 0.7, bold=True, spacing=2, align="right")
            y += 24
        text(cr, f"WORKSPACE {t.workspace[0]} / {t.workspace[1]}", right, y, UI, 12, RED, 0.85, bold=True, spacing=3,
             align="right")
        # a dark veil keeps the text readable over the wallpaper's network drawing
        final, c2 = new_layer(self.w, self.h)
        top = y0 - 4; bottom = y + 26
        veil = cairo.LinearGradient(self.PAD, 0, right, 0)
        veil.add_color_stop_rgba(0, *NAVY, 0); veil.add_color_stop_rgba(0.3, *NAVY, 0.72); veil.add_color_stop_rgba(1, *NAVY, 0.82)
        c2.set_source(veil); c2.rectangle(self.PAD, top, self.W + 6, bottom - top); c2.fill()
        c2.set_source_surface(with_glow(surf, CY, 5, 0.55), 0, 0); c2.paint()
        self.layer = final
        self.update_input()
        self.queue_draw()

    # ------------------------------------------------------------------ quickhack
    def input_region(self):
        if not self.hackable:
            return cairo.Region()
        rects = [cairo.RectangleInt(int(x) - 14, int(y) - 14, 28, 28) for x, y, _h in self.contacts]
        if self.hack:
            rects.append(cairo.RectangleInt(*self.PANEL))
        return cairo.Region(rects)

    def update_input(self):
        if self.hackable and self.get_realized():
            self.input_shape_combine_region(self.input_region())

    def contact_at(self, x, y):
        best = None
        for cx, cy, h in self.contacts:
            d = math.hypot(cx - x, cy - y)
            if d <= 14 and (best is None or d < best[0]):
                best = (d, h)
        return best[1] if best else None

    def set_hover(self, name):
        if name != self.hover_name:
            self.hover_name = name
            win = self.get_window()
            if win:
                win.set_cursor(Gdk.Cursor.new_from_name(win.get_display(), "crosshair") if name else None)
            self.queue_draw()

    def hovered(self, _w, ev):
        h = self.contact_at(ev.x, ev.y)
        self.set_hover(h["name"] if h else "")
        return False

    def clicked(self, _w, ev):
        if ev.button != 1:
            return False
        if self.hack:
            for key, (bx, by, bw, bh) in self.buttons.items():
                if bx <= ev.x <= bx + bw and by <= ev.y <= by + bh:
                    self.hack_action(key)
                    return True
        h = self.contact_at(ev.x, ev.y)
        if h:
            self.open_hack(h)
        return True

    def open_hack(self, h):
        self.hack = {"name": h["name"], "metric": threat_metric(h), "level": h["level"], "procs": h.get("procs", 1),
                     "stage": "protected" if h.get("protected") else "menu", "action": "", "result": "", "t": 0.0}
        self.show_hack()

    def show_hack(self, expire=12):
        """Draws the panel for the current stage; it closes by itself if nothing happens."""
        self.hack_seq += 1; seq = self.hack_seq
        if self.hack and expire:
            GLib.timeout_add_seconds(expire, lambda: self.close_hack() if seq == self.hack_seq else None)
        self.render_hack(); self.update_input(); self.queue_draw()

    def close_hack(self):
        self.hack = None; self.hack_layer = None; self.buttons = {}
        self.hack_seq += 1
        self.update_input(); self.queue_draw()
        return False

    def hack_action(self, key):
        h = self.hack
        if key in ("cancel", "abort", "close"):
            self.close_hack()
        elif key in HACKS and h["stage"] == "menu":
            h["stage"], h["action"] = "confirm", key
            self.show_hack()
        elif key == "upload" and h["stage"] == "confirm":
            h["stage"], h["t"] = "upload", time.monotonic()
            self.show_hack(expire=0)
            GLib.timeout_add(900, self.execute)

    def execute(self):
        h = self.hack
        if not h or h["stage"] != "upload":
            return False
        res = quickhack(h["name"], force=h["action"] == "flatline")
        h["stage"] = "done"
        if res["refused"]:
            h["result"] = "ACCESS DENIED  //  " + res["refused"]
        else:
            n = res["signalled"]
            h["result"] = f"{HACKS[h['action']][0]} UPLOADED  //  {n} PROCESS{'ES' if n != 1 else ''} HIT"
        self.show_hack(expire=3)
        if self.app.threats:
            GLib.timeout_add(1500, lambda: self.app.threats.poll() and False)
        return False

    def button(self, cr, key, x, y, w, label, color, filled=False):
        poly(cr, [(x + 6, y), (x + w, y), (x + w, y + 22), (x + w - 6, y + 28), (x, y + 28), (x, y + 6)])
        cr.set_source_rgba(*color, 0.9 if filled else 0.12); cr.fill_preserve()
        cr.set_source_rgba(*color, 1); cr.set_line_width(1.5); cr.stroke()
        text(cr, label, x + w / 2, y + 5, UI, 14, NAVY if filled else color, bold=True, spacing=2, align="center")
        self.buttons[key] = (x, y, w, 28)

    def render_hack(self):
        self.buttons = {}
        h = self.hack
        if not h:
            self.hack_layer = None
            return
        surf, cr = new_layer(self.w, self.h)
        px, py, pw, ph = self.PANEL
        poly(cr, [(px + 12, py + .75), (px + pw - .75, py + .75), (px + pw - .75, py + ph - 12), (px + pw - 12, py + ph - .75),
                  (px + .75, py + ph - .75), (px + .75, py + 12)])
        cr.set_source_rgba(*NAVY, 0.96); cr.fill_preserve()
        cr.set_source_rgba(*RED, 1); cr.set_line_width(1.5); cr.stroke()
        poly(cr, [(px + 12, py), (px + 150, py), (px + 136, py + 16), (px, py + 16), (px, py + 12)])
        cr.set_source_rgba(*RED, 1); cr.fill()
        text(cr, "QUICKHACK // TARGET", px + 14, py + 2, UI, 10, NAVY, bold=True, spacing=1)
        color = self.LEVEL[h["level"]]
        text(cr, h["name"].upper(), px + 14, py + 22, UI, 22, color, bold=True, spacing=2, width=pw - 110)
        text(cr, h["metric"], px + pw - 12, py + 24, NUM, 15, color, bold=True, align="right")
        sub = f"{h['procs']} PROCESS{'ES' if h['procs'] != 1 else ''}"
        stage = h["stage"]
        if stage == "protected":
            text(cr, sub + "  //  PROTECTED", px + 14, py + 52, UI, 12, TXT, 0.8, bold=True, spacing=2)
            text(cr, "SYSTEM OR ANOTHER USER: NO QUICKHACK", px + 14, py + 78, UI, 13, RED, bold=True, spacing=1)
            self.button(cr, "close", px + pw - 104, py + ph - 42, 90, "CLOSE", CY)
        elif stage == "menu":
            text(cr, sub, px + 14, py + 50, UI, 12, TXT, 0.8, bold=True, spacing=2)
            y = py + 72
            for key in ("overload", "flatline"):
                label, hint, c = HACKS[key]
                self.button(cr, key, px + 14, y, 112, label, c)
                text(cr, hint, px + 136, y + 6, UI, 12, TXT, 0.85, bold=True, width=pw - 146)
                y += 36
            self.button(cr, "cancel", px + pw - 76, py + 44, 62, "X", TXT)
        elif stage == "confirm":
            label, hint, c = HACKS[h["action"]]
            text(cr, f"UPLOAD {label} TO {h['name'].upper()[:14]}?", px + 14, py + 54, UI, 15, c, bold=True, spacing=2,
                 width=pw - 28)
            text(cr, hint, px + 14, py + 76, UI, 12, TXT, 0.85, bold=True)
            self.button(cr, "upload", px + 14, py + ph - 42, 130, "UPLOAD", c, filled=True)
            self.button(cr, "abort", px + 156, py + ph - 42, 100, "ABORT", TXT)
        elif stage == "upload":
            text(cr, f"UPLOADING {HACKS[h['action']][0]}...", px + 14, py + 54, UI, 15, HACKS[h["action"]][2], bold=True,
                 spacing=2)
        else:
            hit = not h["result"].startswith("ACCESS")
            text(cr, h["result"], px + 14, py + 60, UI, 15, CY if hit else RED, bold=True, spacing=1, width=pw - 28)
        self.hack_layer = with_glow(surf, RED, 5, 0.5)

    def screen(self, x, y):
        """Window point -> screen point (for the test lab)."""
        win = self.get_window()
        ox, oy = win.get_root_coords(0, 0) if win else (0, 0)
        return [int(ox + x), int(oy + y)]

    def hack_state(self):
        h = self.hack
        return {"stage": h["stage"], "name": h["name"], "result": h["result"],
                "buttons": {k: self.screen(x + w / 2, y + bh / 2) for k, (x, y, w, bh) in self.buttons.items()}} if h else None

    def animate(self, _now):
        if self.hack and self.hack["stage"] == "upload":
            self.queue_draw()
            return
        r = self.R + 2
        self.queue_draw_area(int(self.cx - r), int(self.cy - r), 2 * r, 2 * r)

    def paint(self, cr):
        if not self.layer:
            return
        cr.set_source_surface(self.layer, 0, 0); cr.paint()
        t = time.time()
        sec = time.localtime(t).tm_sec + ((t % 1) if not self.app.low_power else 0)
        lead = math.radians(sec * 6 - 90); r = self.R - 2
        steps = 22; span = math.radians(44) / steps
        for i in range(steps):                                    # the wedge fades behind the sweep line
            a = lead - i * span
            cr.move_to(self.cx, self.cy); cr.arc_negative(self.cx, self.cy, r, a, a - span * 1.05); cr.close_path()
            cr.set_source_rgba(*CY, 0.42 * (1 - i / steps) ** 1.6); cr.fill()
        cr.set_source_rgba(*CY, 1); cr.set_line_width(1.5)
        cr.move_to(self.cx, self.cy); cr.line_to(self.cx + math.cos(lead) * r, self.cy + math.sin(lead) * r); cr.stroke()

        # contacts glow when the sweep passes and fade like phosphor; a fresh hit sends out a ping ring
        sweep = sec * 6
        for x, y, size, color, b in self.blips:
            glow = max(0.0, 1 - ((sweep - b) % 360) / 140)
            a = 0.3 + 0.7 * glow
            if glow > 0.75:
                cr.arc(x, y, size + 3 + (1 - glow) * 28, 0, 2 * math.pi)
                cr.set_source_rgba(*color, (glow - 0.75) * 3); cr.set_line_width(1.5); cr.stroke()
            cr.arc(x, y, size + 3, 0, 2 * math.pi); cr.set_source_rgba(*color, 0.18 * a); cr.fill()
            cr.arc(x, y, size, 0, 2 * math.pi); cr.set_source_rgba(*color, a); cr.fill()

        # intrusion events blink on the rim for a minute
        now = time.monotonic()
        on = 1.0 if self.app.low_power or (now * 2) % 1 < 0.6 else 0.2
        for until, x, y in self.alarms:
            if now < until:
                poly(cr, [(x, y - 8), (x + 8, y), (x, y + 8), (x - 8, y)])
                cr.set_source_rgba(*RED, 0.25 * on); cr.fill_preserve()
                cr.set_source_rgba(*RED, on); cr.set_line_width(2); cr.stroke()
                cr.arc(x, y, 2, 0, 2 * math.pi); cr.fill()

        # targeting brackets on the contact under the mouse or under a quickhack
        target = self.hack["name"] if self.hack else self.hover_name
        for x, y, h in self.contacts:
            if h["name"] == target:
                cr.set_source_rgba(*(RED if self.hack else CY), 1); cr.set_line_width(2)
                for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    cr.move_to(x + sx * 13, y + sy * 6); cr.line_to(x + sx * 13, y + sy * 13); cr.line_to(x + sx * 6, y + sy * 13)
                    cr.stroke()

        # the quickhack panel, with its upload bar
        if self.hack_layer:
            cr.set_source_surface(self.hack_layer, 0, 0); cr.paint()
            h = self.hack
            if h and h["stage"] == "upload":
                px, py, pw, _ph = self.PANEL
                k = min(1.0, (now - h["t"]) / 0.9)
                for i in range(30):
                    cr.set_source_rgba(*(HACKS[h["action"]][2] if i < round(k * 30) else CY), 1 if i < round(k * 30) else 0.12)
                    cr.rectangle(px + 14 + i * 9.6, py + 84, 7.6, 18); cr.fill()


class Chrono(HudWindow):
    PAD = 16
    W, H = 396, 136

    def __init__(self, app):
        super().__init__("cyberneon-chrono", self.W + 2 * self.PAD, self.H + 2 * self.PAD)
        self.app = app; self.layer = None; self.plain = None
        self.glitch_at = time.monotonic() + 12; self.glitching = False

    def rebuild(self):
        now = time.localtime(); left = 60 - now.tm_sec
        surf, cr = new_layer(self.w, self.h)
        cr.translate(self.PAD, self.PAD)
        right = self.W
        col = right - 34
        text(cr, "/", col + 17, 30, NUM, 22, alpha=0.6, align="center")
        text(cr, f"{left:02d}", right, 54, NUM, 26, RED if left <= 10 else CY, align="right")
        text(cr, time.strftime("%H:%M"), col - 12, -4, NUM, 72, weight=500, align="right")
        for i in range(60):
            x = right - 358 + i * 6; h = 14 if i % 10 == 0 else 10
            if i < left:
                cr.set_source_rgba(*(RED if i < 10 else CY), 1)
            else:
                cr.set_source_rgba(*CY, 0.12)
            cr.rectangle(x, 106 - h, 4, h); cr.fill()
        w = text(cr, time.strftime("%A").upper() + "  //  " + time.strftime("%d.%m.%Y"), right, 112, UI, 18, RED, bold=True,
                 spacing=2, align="right")
        x = right - w - 80
        poly(cr, [(x, 115), (x + 70, 115), (x + 70, 127), (x + 64, 133), (x, 133)]); cr.set_source_rgba(*RED, 1); cr.fill()
        text(cr, "CHRONO", x + 35, 116, UI, 12, NAVY, bold=True, spacing=2, align="center")
        self.plain = surf
        self.layer = with_glow(surf, CY, 8, 0.75)
        self.queue_draw()

    def animate(self, now):
        if self.glitching and now >= self.glitch_at + 0.14:
            self.glitching = False
            self.glitch_at = now + (2.5 if self.app.reactor.alert else 12)
            self.queue_draw()
        elif not self.glitching and now >= self.glitch_at:
            self.glitching = True; self.queue_draw()

    def paint(self, cr):
        if not self.layer:
            return
        cr.set_source_surface(self.layer, 0, 0); cr.paint()
        if self.glitching:
            cr.set_source_rgba(*RED, 0.7); cr.mask_surface(self.plain, -5, 0)
            cr.set_source_rgba(*CY, 0.7); cr.mask_surface(self.plain, 5, 0)


class QuickhackOsd(HudWindow):
    """Volume, brightness and the other OSD messages as an upload bar. Shown above the windows, never takes the focus."""
    W, H = 480, 56
    PAD = 14

    def __init__(self, app):
        super().__init__("cyberneon-quickhack", self.W + 2 * self.PAD, self.H + 2 * self.PAD, Gdk.WindowTypeHint.NOTIFICATION)
        self.app = app; self.layer = None; self.hide_id = 0

    def show_message(self, title, percent, message):
        surf, cr = new_layer(self.w, self.h)
        cr.translate(self.PAD, self.PAD)
        w, h = self.W, self.H
        poly(cr, [(12, .75), (w - .75, .75), (w - .75, h - 12), (w - 12, h - .75), (.75, h - .75), (.75, 12)])
        cr.set_source_rgba(*NAVY, 0.94); cr.fill_preserve()
        cr.set_source_rgba(*CY, 1); cr.set_line_width(1.5); cr.stroke()
        poly(cr, [(12, 0), (158, 0), (144, 16), (0, 16), (0, 12)]); cr.set_source_rgba(*RED, 1); cr.fill()
        text(cr, "QUICKHACK // UPLOAD", 16, 2, UI, 10, NAVY, bold=True, spacing=1)
        text(cr, title, 166, 0, UI, 13, bold=True, spacing=2, width=w - 166 - 62)
        if percent is not None:
            text(cr, f"{percent}%", w - 12, 1, NUM, 14, RED if percent == 0 else CY, bold=True, align="right")
        if message:
            text(cr, message, 12, 24, UI, 16, RED if percent == 0 else CY, bold=True, spacing=2, width=w - 24)
        elif percent is not None:
            lit = round(percent / 100 * 46)
            for i in range(46):
                if i < lit:
                    cr.set_source_rgba(*(RED if i >= 40 else CY), 1)
                else:
                    cr.set_source_rgba(*CY, 0.12)
                cr.rectangle(12 + i * 9, 26, 7, 16); cr.fill()
        self.layer = with_glow(surf, CY, 6, 0.7)
        self.app.place_osd()
        self.show(); self.queue_draw()
        if self.hide_id:
            GLib.source_remove(self.hide_id)
        self.hide_id = GLib.timeout_add(1800, self.finish)

    def finish(self):
        self.hide_id = 0; self.hide()
        return False

    def paint(self, cr):
        if self.layer:
            cr.set_source_surface(self.layer, 0, 0); cr.paint()
