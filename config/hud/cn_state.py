"""CyberNeon HUD: what the desktop reacts to. Real system data, the alert state, battery, live terminal text, OSD requests.

Everything is read from /proc, /sys, D-Bus or small helper scripts, without blocking the GTK main loop.
FAN MADE - inspired by Cyberpunk 2077 by CD PROJEKT RED (trademarks of CD PROJEKT S.A.).
"""
import ctypes, glob, json, os, shutil, signal, subprocess, threading, time, traceback

from gi.repository import Gio, GLib

import cn_threats

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "bin")
VIRTUAL_NET = ("lo", "docker", "br-", "veth", "virbr", "vnet", "tun", "tap", "wg")   # would count the same bytes twice
CPU_CHIPS = {"coretemp", "k10temp", "zenpower", "cpu_thermal", "soc_thermal"}
GPU_CHIPS = {"amdgpu", "radeon", "nouveau", "i915", "xe"}

DEFAULTS = {
    "label": "NETRUNNER", "logo": "", "terminal_plate": "",
    "reactive": True, "alert_cpu": 85, "alert_ram": 85, "alert_temp": 95,
    "live_terminal": True, "trace_mbps": 5, "cyber_osd": True, "sound_fx": False, "low_power": 20, "osd_bottom": 84,
    "hud_left": 20, "hud_top": 62, "sentinel": True, "quickhack": True,
}


def load_config(path):
    cfg = dict(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def run_async(argv, done=None):
    """Runs a helper without blocking; done(stdout) gets its output ("" if it could not run)."""
    try:
        proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error:
        if done:
            done("")
        return

    def finished(p, res):
        try:
            _ok, out, _err = p.communicate_utf8_finish(res)
        except GLib.Error:
            out = ""
        if done:
            done(out or "")
    proc.communicate_utf8_async(None, None, finished)


def rate_text(b):
    if b >= 1048576:
        return f"{b / 1048576:.1f}M"
    if b >= 1024:
        return f"{b / 1024:.0f}K"
    return f"{b:.0f}B"


class Metrics:
    """CPU, memory, disk, network, uptime and temperatures. sample() is called once per second."""

    def __init__(self):
        self.cpu = self.ram = self.disk = self.temp = 0.0
        self.total_mb = 1.0; self.free_mb = 0.0
        self.down = self.up = 0.0
        self.uptime_h = 0
        self._cpu = None; self._net = None; self._n = 0
        self._cpu_files, self._gpu_files = self._find_sensors()
        self._nvidia = 0.0
        self._has_nvidia = os.path.isdir("/proc/driver/nvidia") and shutil.which("nvidia-smi")

    @staticmethod
    def _find_sensors():
        cpu, gpu = [], []
        for d in glob.glob("/sys/class/hwmon/hwmon*"):
            try:
                with open(d + "/name") as f:
                    name = f.read().strip()
            except OSError:
                continue
            target = cpu if name in CPU_CHIPS else gpu if name in GPU_CHIPS else None
            if target is not None:
                target.extend(glob.glob(d + "/temp*_input"))
        return cpu, gpu

    @staticmethod
    def _hottest(files):
        best = 0.0
        for path in files:
            try:
                with open(path) as f:
                    v = int(f.read()) / 1000
            except (OSError, ValueError):
                continue
            if v < 150:
                best = max(best, v)
        return best

    def sample(self):
        self._n += 1
        with open("/proc/stat") as f:
            v = [int(x) for x in f.readline().split()[1:9]]
        idle, total = v[3] + v[4], sum(v)
        if self._cpu and total > self._cpu[1]:
            self.cpu = 100 * (1 - (idle - self._cpu[0]) / (total - self._cpu[1]))
        self._cpu = (idle, total)

        mem = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, _, rest = line.partition(":")
                if k in ("MemTotal", "MemAvailable"):
                    mem[k] = int(rest.split()[0]) / 1024
        self.total_mb = max(1.0, mem.get("MemTotal", 1.0))
        self.free_mb = min(self.total_mb, mem.get("MemAvailable", 0.0))      # page cache counts as free
        self.ram = 100 * (1 - self.free_mb / self.total_mb)

        rx = tx = 0
        with open("/proc/net/dev") as f:
            for line in f.readlines()[2:]:
                name, _, rest = line.partition(":")
                if name.strip().startswith(VIRTUAL_NET):
                    continue
                c = rest.split(); rx += int(c[0]); tx += int(c[8])
        now = time.monotonic()
        if self._net and now > self._net[0]:
            dt = now - self._net[0]
            self.down = max(0.0, (rx - self._net[1]) / dt); self.up = max(0.0, (tx - self._net[2]) / dt)
        self._net = (now, rx, tx)

        if self._n % 2 == 1:
            self.temp = max(self._hottest(self._cpu_files), self._hottest(self._gpu_files), self._nvidia)
        if self._n % 10 == 1:
            st = os.statvfs("/")
            used = st.f_blocks - st.f_bfree
            self.disk = 100 * used / max(1, used + st.f_bavail)
            with open("/proc/uptime") as f:
                self.uptime_h = int(float(f.read().split()[0]) / 3600)
            if self._has_nvidia:
                run_async(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"], self._read_nvidia)

    def _read_nvidia(self, out):
        try:
            self._nvidia = max(float(x) for x in out.split())
        except ValueError:
            self._nvidia = 0.0


class Reactor:
    """Turns load into the alert state: 3 s over a limit to enter, 6 s clearly below all limits to leave."""
    ENTER, EXIT = 3, 6

    def __init__(self, cpu=85, ram=85, temp=95):
        self.cpu_limit, self.ram_limit, self.temp_limit = cpu, ram, temp
        self.alert = False; self.reason = ""; self.hot_for = self.calm_for = 0

    def tick(self, cpu, ram, temp):
        hot = []
        if cpu >= self.cpu_limit:
            hot.append(f"CPU {cpu:.0f}%")
        if ram >= self.ram_limit:
            hot.append(f"RAM {ram:.0f}%")
        if temp >= self.temp_limit:
            hot.append(f"TEMP {temp:.0f}C")
        calm = cpu < self.cpu_limit - 10 and ram < self.ram_limit - 5 and temp < self.temp_limit - 5
        if hot:
            self.reason = "  ".join(hot)
        self.hot_for = self.hot_for + 1 if hot else 0
        self.calm_for = self.calm_for + 1 if calm else 0
        before = self.alert
        if not self.alert and self.hot_for >= self.ENTER:
            self.alert = True
        elif self.alert and self.calm_for >= self.EXIT:
            self.alert = False
        return self.alert != before


class Power:
    """Battery through UPower: nothing happens on machines without one."""
    DISCHARGING, CHARGING = 2, 1

    def __init__(self, low_limit, changed):
        self.low_limit = low_limit; self.changed = changed
        self.has_battery = False; self.percent = 0; self.state = 0
        try:
            self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        except GLib.Error:
            self.bus = None
        self.refresh()
        GLib.timeout_add_seconds(10, self.refresh)

    @property
    def charging(self): return self.state == self.CHARGING

    @property
    def low(self):
        return self.low_limit > 0 and self.has_battery and self.state == self.DISCHARGING and self.percent < self.low_limit

    def refresh(self):
        if self.bus is None:
            return False
        self.bus.call("org.freedesktop.UPower", "/org/freedesktop/UPower/devices/DisplayDevice",
                      "org.freedesktop.DBus.Properties", "GetAll", GLib.Variant("(s)", ("org.freedesktop.UPower.Device",)),
                      GLib.VariantType("(a{sv})"), Gio.DBusCallFlags.NO_AUTO_START, 2000, None, self._got)
        return True

    def _got(self, bus, res):
        try:
            p = bus.call_finish(res).unpack()[0]
        except GLib.Error:
            p = {}
        now = (bool(p.get("IsPresent")) and p.get("Type") == 2, int(round(p.get("Percentage", 0))), p.get("State", 0))
        if now != (self.has_battery, self.percent, self.state):
            self.has_battery, self.percent, self.state = now
            self.changed()


class Tcc:
    """Active TUXEDO Control Center profile, read-only. Stays empty where the Control Center is not running."""

    def __init__(self, changed):
        self.profile = ""; self.changed = changed
        self.refresh()
        GLib.timeout_add_seconds(60, self.refresh)

    def refresh(self):
        run_async([os.path.join(BIN, "cn-tcc")], self._got)
        return True

    def _got(self, out):
        try:
            name = str(json.loads(json.loads(out)["data"][0]).get("name", "")).upper()
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            name = ""
        if name != self.profile:
            self.profile = name; self.changed()


def pad(s, n):
    return (s + " " * n)[:n]


def clock_text(seconds):
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def terminal_rows(links, journal, down, up, tracing, trace_seconds, alert, reason):
    """The 12 rows of the wallpaper terminal: (text, "cy"|"red", opacity)."""
    def row(s, hot=False, prompt=False):
        return (s, "red" if hot else "cy", 0.95 if hot else 1.0 if prompt else 0.55)

    out = [row("> trace --sockets --live", prompt=True)]
    for i in range(4):
        if i < len(links):
            c = links[i]
            out.append(row(f"[ OK ] 0x{c[1]}:{pad(c[2], 6)}{pad(c[3], 6)}{c[4]}"))
        else:
            out.append(row("[ .. ] no active links" if i == 0 else ""))
    out.append(row("> tail --follow /dev/journal", prompt=True))
    for i in range(4):
        if i >= len(journal):
            out.append(row("[ .. ] journal silent" if i == 0 else ""))
            continue
        e = journal[i]; prio = int(e[2]) if e[2].isdigit() else 6
        mark = "[ICE ] " if prio <= 3 else "[WARN] " if prio == 4 else "[ OK ] "
        out.append(row(f"{mark}{e[1]} {pad(e[3], 19)}0x{e[4]}", hot=prio <= 4))
    if tracing:
        out.append(row(f"[WARN] trace program active: {clock_text(trace_seconds)}", hot=True))
    else:
        out.append(row(f"[ OK ] trace: clear   v {rate_text(down)}/s  ^ {rate_text(up)}/s"))
    out.append(row(f"> !! countermeasures engaged: {reason}" if alert else "> ", hot=alert, prompt=True))
    return out


class LiveTerminal:
    """Text of the terminal in the wallpaper. Addresses and journal messages never reach it (see bin/cn-netlog)."""

    def __init__(self, trace_mbps, changed):
        self.limit = trace_mbps * 1000000; self.changed = changed
        self.links = []; self.journal = []; self.down = self.up = 0.0
        self.trace_seconds = 0; self.alert = False; self.reason = ""; self.paused = False
        self.rows = []
        self.poll()
        GLib.timeout_add_seconds(5, self.poll)

    @property
    def tracing(self): return max(self.down, self.up) >= self.limit

    def poll(self):
        if not self.paused:
            run_async([os.path.join(BIN, "cn-netlog")], self._got)
        return True

    def _got(self, out):
        links, journal = [], []
        for line in out.splitlines():
            f = line.split("|")
            if f[0] == "C" and len(f) == 5:
                links.append(f)
            elif f[0] == "J" and len(f) == 5:
                journal.append(f)
            elif f[0] == "R" and len(f) == 3:
                self.down = float(f[1] or 0); self.up = float(f[2] or 0)
        self.links, self.journal = links, journal
        self.build()

    def second(self):
        if self.tracing and not self.paused:
            self.trace_seconds += 1; self.build()
        elif self.trace_seconds:
            self.trace_seconds = 0; self.build()

    def set_alert(self, alert, reason):
        self.alert, self.reason = alert, reason
        self.build()

    def build(self):
        self.rows = terminal_rows(self.links, self.journal, self.down, self.up, self.tracing, self.trace_seconds,
                                  self.alert, self.reason)
        self.changed()


def describe_osd(params):
    """Budgie OSD request -> (title, percent or None, message)."""
    icon = str(params.get("icon") or ""); label = str(params.get("label") or "")
    level = params.get("level")
    top = params.get("max_level") or 1.0
    title = "SYSTEM"; audio = False
    if "microphone" in icon:
        title, audio = "MIC INPUT", True
    elif "audio" in icon:
        title, audio = "AUDIO OUTPUT", True
    elif "keyboard-brightness" in icon:
        title = "KEY BACKLIGHT"
    elif "brightness" in icon:
        title = "OPTICS // BRIGHTNESS"
    elif "touchpad" in icon:
        title = "TOUCHPAD"
    elif "bluetooth" in icon:
        title = "BLUETOOTH"
    elif "airplane" in icon or "wireless" in icon:
        title = "WI-FI LINK"
    if level is None:
        return title, None, label.upper()
    level = float(level)
    if level > max(1.0, float(top)):          # some callers send 0..100
        level /= 100
    percent = int(round(100 * level / (float(top) or 1.0)))
    percent = max(0, min(100, percent))
    if audio and (percent == 0 or "muted" in icon):
        return title, 0, "MUTED // OFFLINE"
    return title, percent, ""


def _unwrap(v):
    return v.get("data") if isinstance(v, dict) and "data" in v else v


class Follower:
    """Runs a command for the whole session and hands each line it prints to on_line. Restarted if it ends."""

    def __init__(self, cmd, on_line):
        self.cmd, self.on_line = cmd, on_line; self.proc = None; self.buf = b""
        self.start()

    def start(self):
        libc = ctypes.CDLL(None)
        try:
            self.proc = subprocess.Popen(self.cmd,
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                         preexec_fn=lambda: libc.prctl(1, signal.SIGTERM))    # dies with the HUD
        except OSError:
            return False
        os.set_blocking(self.proc.stdout.fileno(), False)
        GLib.io_add_watch(self.proc.stdout.fileno(), GLib.PRIORITY_DEFAULT, GLib.IO_IN | GLib.IO_HUP, self.readable)
        return False

    def readable(self, fd, _cond):
        try:
            data = os.read(fd, 65536)
        except BlockingIOError:
            return True
        except OSError:
            data = b""
        if not data:
            self.proc.stdout.close(); self.proc.wait()
            GLib.timeout_add_seconds(5, self.start)
            return False
        self.buf += data
        *lines, self.buf = self.buf.split(b"\n")
        for line in lines:
            self.on_line(line)
        return True


class ThreatWatch:
    """Feeds the threat radar: a scan every few seconds in a worker thread (it never stalls the animation), and the
    login events of the journal as they happen. Keeps the last events, the same event at most once in 30 s."""
    INTERVAL = 3

    def __init__(self, changed, sentinel=True, on_event=None):
        self.changed, self.on_event, self.sentinel = changed, on_event, sentinel
        self.scanner = cn_threats.Scanner()
        self.snap = {"hostiles": [], "traffic": [], "events": [], "cpu_top": "", "mem_top": "", "down": 0, "up": 0}
        self.events = []                     # [(monotonic time, event)], newest first
        self.busy = False; self.paused = False; self.n = 0
        if sentinel:
            Follower(cn_threats.AUTH_CMD, self.auth_line)
        self.poll()
        GLib.timeout_add_seconds(self.INTERVAL, self.poll)

    def poll(self):
        self.n += 1
        if self.busy or (self.paused and self.n % 5):        # on low battery one scan in five
            return True
        self.busy = True
        threading.Thread(target=self._work, daemon=True).start()
        return True

    def _work(self):
        try:
            snap = self.scanner.poll(self.sentinel)
        except Exception:                                  # a scan must never take the HUD down, but it shows in the log
            traceback.print_exc(); snap = None
        # default priority, not idle: under full load the main loop is never idle, and that is when the radar matters
        GLib.idle_add(self._got, snap, priority=GLib.PRIORITY_DEFAULT)

    def _got(self, snap):
        self.busy = False
        if snap:
            self.snap = snap
            for e in snap["events"]:
                self.add(e)
            self.changed()
        return False

    def auth_line(self, line):
        e = cn_threats.auth_event(line.decode(errors="replace"))
        if e and self.add(e):
            self.changed()

    def add(self, e):
        now = time.monotonic()
        if any(x["text"] == e["text"] and now - t < 30 for t, x in self.events):
            return False
        self.events.insert(0, (now, dict(e, clock=time.strftime("%H:%M"))))
        del self.events[4:]
        if self.on_event:
            self.on_event(e)
        return True

    def recent(self, seconds):
        now = time.monotonic()
        return [(now - t, e) for t, e in self.events if now - t < seconds]

    def culprit(self, reason):
        """Who to blame for the alert: the heaviest program for the resource that triggered it."""
        s = self.snap
        return s["mem_top"] if reason.startswith("RAM") else s["cpu_top"]


class BusWatch:
    """Follows OSD requests and new notifications on the session bus, with one busctl for the whole session.
    Of a notification only the fact that it arrived is used: its text is never read."""

    def __init__(self, on_osd=None, on_notify=None):
        self.on_osd, self.on_notify = on_osd, on_notify
        cmd = ["busctl", "--user", "monitor", "--json=short"]
        if self.on_osd:
            cmd += ["--match", "type='method_call',interface='org.budgie_desktop.BudgieOSD',member='ShowOSD'"]
        if self.on_notify:
            cmd += ["--match", "type='method_call',interface='org.freedesktop.Notifications',member='Notify'"]
        Follower(cmd, self.handle)

    def handle(self, line):
        try:
            msg = json.loads(line)
            if msg.get("member") == "Notify":
                if self.on_notify:
                    self.on_notify()
                return
            params = {k: _unwrap(v) for k, v in msg["payload"]["data"][0].items()}
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            return
        if self.on_osd:
            self.on_osd(*describe_osd(params))
