#!/usr/bin/env python3
"""CyberNeon for Budgie: game-style HUD and animated wallpaper in one light process.

usage: cyberneon-hud.py [--fps 15] [--no-wallpaper] [--wallpaper-only] [--config FILE]
  --wallpaper-only   only the animated wallpaper, as in the classic (Conky) layout
  --no-wallpaper     only the HUD widgets

Biomonitor top left, threat Radar and objective tracker top right, Chrono bottom right, Quickhack OSD bottom centre.
The whole desktop reacts to real load (alert mode), network traffic, intrusion events and battery.
FAN MADE - inspired by Cyberpunk 2077 by CD PROJEKT RED (trademarks of CD PROJEKT S.A.).
"""
import argparse, fcntl, json, locale, os, signal, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # the installer runs python3 -I

import gi
gi.require_version("Gtk", "3.0"); gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

import cn_state as st
from cn_wallpaper import Live

CONFIG = os.path.expanduser("~/.config/cyberneon/hud/config.json")


class App:
    def __init__(self, args):
        self.args = args
        self.cfg = st.load_config(args.config)
        display = Gdk.Display.get_default()
        self.mon = (display.get_primary_monitor() or display.get_monitor(0)).get_geometry()
        hud = not args.wallpaper_only
        self.wall = self.bio = self.radar = self.chrono = self.osd = None
        self.frame_id = 0; self.frame_n = 0; self.last_chirp = -10.0
        self.power = self.tcc = self.terminal = self.threats = None
        self.reactor = st.Reactor(self.cfg["alert_cpu"], self.cfg["alert_ram"], self.cfg["alert_temp"])
        self.metrics = st.Metrics()

        if not args.no_wallpaper:
            live = hud and self.cfg["live_terminal"] and os.path.exists(self.cfg["terminal_plate"])
            self.wall = Live(self.mon, self.cfg["terminal_plate"] if live else "")
            self.wall.show_all()
            if live:
                self.terminal = st.LiveTerminal(self.cfg["trace_mbps"], self.terminal_changed)
        if hud:
            from cn_widgets import Biomonitor, Chrono, QuickhackOsd, Radar
            self.power = st.Power(self.cfg["low_power"], self.power_changed)
            self.tcc = st.Tcc(self.refresh_bio)
            self.metrics.sample()
            self.bio, self.radar, self.chrono = Biomonitor(self), Radar(self), Chrono(self)
            m = self.mon
            left, top = self.cfg["hud_left"], self.cfg["hud_top"]       # under the top-left pod, or the top bar
            self.bio.move(m.x + left - self.bio.PAD, m.y + top - self.bio.PAD)
            self.radar.move(m.x + m.width - self.radar.w - 2, m.y + top - 4 - self.radar.PAD)
            self.chrono.move(m.x + m.width - self.chrono.w - 8, m.y + m.height - self.chrono.h - 8)
            for w in (self.bio, self.radar, self.chrono):
                w.rebuild(); w.show_all()
            self.threats = st.ThreatWatch(self.radar.rebuild, self.cfg["sentinel"], self.intrusion)
            if self.cfg["cyber_osd"]:
                self.osd = QuickhackOsd(self)
            if self.osd or self.cfg["sound_fx"]:
                st.BusWatch(self.osd.show_message if self.osd else None, self.notified if self.cfg["sound_fx"] else None)
            self.last_minute = -1
            self.second()
        self.update_animation()
        display.get_default_screen().connect("monitors-changed", self.monitors_changed)

    @property
    def low_power(self):
        return bool(self.power and self.power.low)

    def place_osd(self):
        m = self.mon; o = self.osd
        o.move(m.x + (m.width - o.w) // 2, m.y + m.height - o.h - self.cfg["osd_bottom"])

    def update_animation(self):
        """The continuous animation runs at the chosen frame rate and stops completely on low battery."""
        wanted = not self.low_power
        if wanted and not self.frame_id:
            self.frame_id = GLib.timeout_add(int(1000 / max(1, self.args.fps)), self.frame)
        elif not wanted and self.frame_id:
            GLib.source_remove(self.frame_id); self.frame_id = 0

    def frame(self):
        now = time.monotonic()
        if self.wall:
            self.wall.queue_draw()
        self.frame_n += 1
        if self.bio:
            self.bio.animate(now); self.chrono.animate(now)
            if self.frame_n % 2 == 0:                       # the sweep is slow: half the frame rate looks the same
                self.radar.animate(now)
        return True

    def second(self):
        """Runs right after each clock second, so the Chrono turns over on time."""
        m = self.metrics
        m.sample()
        changed = self.cfg["reactive"] and self.reactor.tick(m.cpu, m.ram, m.temp)
        if changed:
            self.alert_changed()
        now = time.localtime()
        if changed or now.tm_sec % 2 == 0:
            self.bio.rebuild()
        self.chrono.rebuild()
        if now.tm_sec % 10 == 0 or now.tm_min != self.last_minute:
            self.radar.rebuild(); self.last_minute = now.tm_min
        elif self.low_power:
            self.radar.queue_draw()                         # the sweep moves once per second
        if self.terminal:
            self.terminal.second()
        self.dump_state()
        GLib.timeout_add(1005 - int(time.time() * 1000) % 1000, self.second)
        return False

    def dump_state(self):
        """For the test lab only (CYBERNEON_HUD_STATE=file): what the HUD currently believes."""
        path = os.environ.get("CYBERNEON_HUD_STATE")
        if not path:
            return
        m, r, p, t = self.metrics, self.reactor, self.power, self.threats
        with open(path + ".tmp", "w") as f:
            json.dump({"cpu": m.cpu, "ram": m.ram, "temp": m.temp, "alert": r.alert, "reason": r.reason,
                       "status": self.bio.status()[0], "low_power": self.low_power, "animating": bool(self.frame_id),
                       "battery": [p.has_battery, p.percent, p.state], "tcc": self.tcc.profile,
                       "objectives": self.radar.tracker.items, "workspace": self.radar.tracker.workspace,
                       "hostiles": [[h["name"], h["level"], h["cpu"]] for h in t.snap["hostiles"]],
                       "traffic": [[x["name"], x["down"], x["up"]] for x in t.snap["traffic"]],
                       "events": [e["text"] for _t, e in t.events], "cpu_top": t.snap["cpu_top"],
                       "contacts": [[h["name"]] + self.radar.screen(x, y) for x, y, h in self.radar.contacts],
                       "hack": self.radar.hack_state(),
                       "terminal": [r_[0] for r_ in self.terminal.rows] if self.terminal else []}, f)
        os.replace(path + ".tmp", path)

    def alert_changed(self):
        alert = self.reactor.alert
        if self.wall:
            self.wall.set_alert(alert)
        if self.terminal:
            self.terminal.set_alert(alert, self.reactor.reason)
        if alert and self.cfg["sound_fx"]:
            self.sfx("dialog-warning")

    def intrusion(self, _event):
        if self.cfg["sound_fx"]:
            self.sfx("dialog-warning")

    def sfx(self, name):
        st.run_async([os.path.join(st.BIN, "cn-sfx"), name])

    def notified(self):
        """Incoming notification: the low "call" chirp, at most every 2 s and never in Do Not Disturb."""
        now = time.monotonic()
        if now - self.last_chirp < 2:
            return
        self.last_chirp = now

        def answer(bus, res):
            try:
                quiet = bus.call_finish(res).unpack()[0]
            except GLib.Error:
                quiet = False
            if not quiet:
                self.sfx("message-new-instant")
        Gio.bus_get_sync(Gio.BusType.SESSION, None).call(
            "org.budgie_desktop.Notifications", "/org/budgie_desktop/Notifications",
            "org.buddiesofbudgie.budgie.Dispatcher", "GetDoNotDisturb", None, GLib.VariantType("(b)"),
            Gio.DBusCallFlags.NO_AUTO_START, 1000, None, answer)

    def terminal_changed(self):
        if self.wall:
            self.wall.set_rows(self.terminal.rows); self.wall.queue_draw()

    def refresh_bio(self):
        if self.bio:
            self.bio.rebuild()

    def power_changed(self):
        self.update_animation()
        if self.terminal:
            self.terminal.paused = self.low_power
        if self.threats:
            self.threats.paused = self.low_power
        self.refresh_bio()

    def monitors_changed(self, *_a):
        GLib.timeout_add_seconds(2, self.restart)

    def restart(self):
        os.execv(sys.executable, [sys.executable, "-I", os.path.abspath(__file__)] + sys.argv[1:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--no-wallpaper", action="store_true")
    ap.add_argument("--wallpaper-only", action="store_true")
    ap.add_argument("--config", default=CONFIG)
    args = ap.parse_args()
    locale.setlocale(locale.LC_ALL, "")
    Gtk.init(None)

    lock = open(os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "cyberneon-hud.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return                                               # already running
    App(args)
    for sig in (signal.SIGTERM, signal.SIGINT):
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, sig, Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    main()
