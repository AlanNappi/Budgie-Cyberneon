#!/bin/bash
# Runs inside the lab container: starts a real Budgie session on a virtual screen, runs install.sh and tests the HUD.
# Battery and TUXEDO Control Center are simulated on a private "system" bus; audio players are replaced by a logger.
OUT=/out; REPO=/home/netrunner/cyberneon

# ---------------------------------------------------------------------------------------------- root part
if [ "${1:-}" != session ]; then
    cp -r /repo "$REPO"; rm -rf "$REPO/lab/out" "$REPO/.git"
    for d in /hosticons/Papirus /hosticons/Papirus-Dark; do
        [ -d "$d" ] && { mkdir -p /home/netrunner/.local/share/icons; cp -r "$d" /home/netrunner/.local/share/icons/; }
    done
    if [ -d /hostfonts ]; then mkdir -p /usr/local/share/fonts/jb; cp /hostfonts/JetBrainsMonoNerdFontMono-* /usr/local/share/fonts/jb/; fc-cache -f; fi
    chown -R netrunner: /home/netrunner; chmod -R a+rwX "$OUT"

    cat > /usr/local/bin/pw-play <<'EOF'
#!/bin/sh
echo "$(date +%T) $(basename "$1" .wav)" >> /out/sfx.log
EOF
    # journal with a message that must never reach the screen
    cat > /usr/local/bin/journalctl <<'EOF'
#!/bin/sh
case " $* " in *" -f "*) exec tail -n 0 -F /tmp/xdg/auth.jsonl ;; esac      # the radar's login-event follower
t=$(date +%s)000000
for row in "6 systemd" "4 NetworkManager" "3 sshd" "6 budgie-daemon"; do
    set -- $row
    echo "{\"__REALTIME_TIMESTAMP\":\"$t\",\"PRIORITY\":\"$1\",\"SYSLOG_IDENTIFIER\":\"$2\",\"MESSAGE\":\"SECRET-JOURNAL-TEXT from 203.0.113.77\"}"
done
EOF
    chmod +x /usr/local/bin/pw-play /usr/local/bin/journalctl
    # records the sounds budgie-daemon asks for
    cat > /tmp/ca.c <<'EOF'
#include <stdarg.h>
#include <stdio.h>
extern const char *ca_proplist_gets(void *p, const char *k);
static void note(const char *n) { FILE *f = fopen("/out/canberra.log", "a"); if (f) { fprintf(f, "%s\n", n ? n : "?"); fclose(f); } }
int ca_context_play_full(void *c, unsigned id, void *p, void *cb, void *ud) { note(ca_proplist_gets(p, "event.id")); return 0; }
int ca_context_play(void *c, unsigned id, ...) {
    va_list a; va_start(a, id); const char *k;
    while ((k = va_arg(a, const char *))) { const char *v = va_arg(a, const char *); if (k[0] == 'e' && k[6] == 'i') note(v); }
    va_end(a); return 0;
}
EOF
    gcc -shared -fPIC -o /usr/local/lib/ca-log.so /tmp/ca.c
    mkdir -p /tmp/xdg; chown netrunner /tmp/xdg; chmod 700 /tmp/xdg
    exec runuser -u netrunner -- env HOME=/home/netrunner USER=netrunner XDG_RUNTIME_DIR=/tmp/xdg LAB_ONLY="${LAB_ONLY:-}" LAB_PEER="${LAB_PEER:-}" \
        dbus-run-session -- bash /inside.sh session
fi

# ---------------------------------------------------------------------------------------------- session
export DISPLAY=:99 XDG_SESSION_TYPE=x11 XDG_CURRENT_DESKTOP=Budgie:GNOME DESKTOP_SESSION=budgie-desktop GDK_BACKEND=x11
export LIBGL_ALWAYS_SOFTWARE=1 NO_AT_BRIDGE=1 GSETTINGS_BACKEND=dconf
log() { echo "== $*"; }
pass() { echo "PASS  $*" | tee -a "$OUT/results.txt"; }
fail() { echo "FAIL  $*" | tee -a "$OUT/results.txt"; }
check() { local what=$1; shift; if "$@"; then pass "$what"; else fail "$what"; fi; }
shot() { import -window root "$OUT/$1.png"; }
panel_apps() {    # one line per panel: location, theme-regions, applet names
    python3 - <<'PY'
import ast, subprocess
BP = "/com/solus-project/budgie-panel"
r = lambda k: subprocess.run(["dconf", "read", BP + k], capture_output=True, text=True).stdout.strip()
for p in ast.literal_eval(r("/panels")):
    apps = ast.literal_eval(r(f"/panels/{{{p}}}/applets").replace("@as ", "") or "[]")
    names = sorted(ast.literal_eval(r(f"/applets/{{{u}}}/name")) for u in apps)
    print(r(f"/panels/{{{p}}}/location").strip("'"), r(f"/panels/{{{p}}}/theme-regions") or "default", "|", ",".join(names))
PY
}
top_alpha() {    # alpha of the top panel window: left pod, the gap in the middle, right pod
    python3 - <<'PY' 2>/dev/null
import re, subprocess, gi
gi.require_version("Gdk", "3.0"); gi.require_version("GdkX11", "3.0")
from gi.repository import Gdk, GdkX11
d = Gdk.Display.get_default()
for l in subprocess.run(["xwininfo", "-root", "-tree"], capture_output=True, text=True).stdout.splitlines():
    m = re.search(r"(0x[0-9a-f]+) .*[Bb]udgie-panel.*?(\d+)x(\d+)\+(-?\d+)\+(-?\d+)\s+\+(-?\d+)\+(-?\d+)", l)
    if m and int(m[2]) >= 1900 and int(m[7]) == 0:
        win = GdkX11.X11Window.foreign_new_for_display(d, int(m[1], 16))
        pb = Gdk.pixbuf_get_from_window(win, 0, 0, win.get_width(), win.get_height())
        px, rs, n = pb.get_pixels(), pb.get_rowstride(), pb.get_n_channels()
        a = lambda x, y: px[y * rs + x * n + 3] if n == 4 else 255
        print(a(40, 26), a(960, 26), a(1900, 26), win.get_height())
        break
PY
}
state() { python3 -c "import json,sys;d=json.load(open('$OUT/hud-state.json'));print(eval(sys.argv[1]))" "$1" 2>/dev/null; }
wait_for() { local i; for i in $(seq 1 "${2:-30}"); do [ "$(state "$1")" = True ] && return 0; sleep 1; done; return 1; }

# no settings daemon here: GTK reads the theme from this file (on a real desktop it follows gsettings)
mkdir -p "$HOME/.config/gtk-3.0"
printf '[Settings]\ngtk-theme-name=CyberNeon\ngtk-icon-theme-name=CyberNeon-Icons\ngtk-cursor-theme-name=CyberNeon-Cursors\ngtk-font-name=Chakra Petch Medium 10\ngtk-application-prefer-dark-theme=1\n' > "$HOME/.config/gtk-3.0/settings.ini"
Xvfb :99 -screen 0 1920x1080x24 +extension GLX +extension RANDR +extension RENDER +extension Composite -ac -nolisten tcp >"$OUT/xvfb.log" 2>&1 &
sleep 2
SYS=$(dbus-daemon --config-file=/usr/share/dbus-1/session.conf --fork --print-address)
export DBUS_SYSTEM_BUS_ADDRESS=$SYS

log "starting Budgie"
gsettings set com.solus-project.budgie-panel builtin-theme false      # as on Ubuntu Budgie
budgie-wm >"$OUT/budgie-wm.log" 2>&1 &
sleep 5
LD_PRELOAD=/usr/local/lib/ca-log.so budgie-daemon >"$OUT/budgie-daemon.log" 2>&1 &
sleep 2
budgie-panel >"$OUT/budgie-panel.log" 2>&1 &
sleep 5
# same starting point as Ubuntu Budgie: a top panel with the ShowTime applet
BP=/com/solus-project/budgie-panel
PANEL=$(dconf read $BP/panels | tr -d "[]' ")
APPLET=$(cat /proc/sys/kernel/random/uuid)
gsettings set "com.solus-project.budgie-panel.panel:$BP/panels/{$PANEL}/" location "'top'"
gsettings set "com.solus-project.budgie-panel.applet:$BP/applets/{$APPLET}/" name "'ShowTime'"
gsettings set "com.solus-project.budgie-panel.applet:$BP/applets/{$APPLET}/" alignment "'start'"
gsettings set "com.solus-project.budgie-panel.applet:$BP/applets/{$APPLET}/" position 9
APPMENU=$(cat /proc/sys/kernel/random/uuid)       # and a second app menu (Slingshot), as on many Ubuntu Budgie top bars
gsettings set "com.solus-project.budgie-panel.applet:$BP/applets/{$APPMENU}/" name "'AppMenu'"
gsettings set "com.solus-project.budgie-panel.applet:$BP/applets/{$APPMENU}/" alignment "'start'"
gsettings set "com.solus-project.budgie-panel.applet:$BP/applets/{$APPMENU}/" position 10
LIST=$(dconf read $BP/panels/{$PANEL}/applets)
dconf write $BP/panels/{$PANEL}/applets "${LIST%]}, '$APPLET', '$APPMENU']"
gsettings set com.gexperts.Tilix.Settings warn-vte-config-issue false
budgie-panel --replace >"$OUT/budgie-panel.log" 2>&1 &
sleep 6
dconf dump $BP/ > "$OUT/panel-default.ini"; panel_apps > "$OUT/panels-before.txt"
nemo-desktop >/dev/null 2>&1 &
sleep 2
shot 00-budgie-stock

# a USB tree the lab can plug devices into, and one known neighbour (the gateway) before the first run
USB=/tmp/xdg/usb; mkdir -p "$USB/usb1" "$USB/1-1"; echo 2 > "$USB/1-1/devnum"; export CYBERNEON_USB_ROOT=$USB
GW=$(ip route | awk '/^default/{print $3; exit}')
python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect_ex(('$GW', 9))" 2>/dev/null
touch /tmp/xdg/auth.jsonl
mkdir -p /tmp/lab; cp /usr/bin/yes /tmp/lab/icebreaker
cat > /tmp/lab/burn.py <<'PY'
import sys, time
duty = float(sys.argv[1])
while True:
    t = time.monotonic()
    while time.monotonic() - t < duty * 0.1:
        pass
    time.sleep((1 - duty) * 0.1)
PY
cp /tmp/lab/burn.py /tmp/lab/datamine.py; cp /tmp/lab/burn.py /tmp/lab/tracer.py

log "install.sh"
cd "$REPO" || exit 1
bash ./install.sh --skip-papirus > "$OUT/install.log" 2>&1; rc=$?
check "install.sh exits 0 (got $rc)" [ "$rc" = 0 ]
sleep 6
pkill -x budgie-daemon; sleep 1; LD_PRELOAD=/usr/local/lib/ca-log.so budgie-daemon >>"$OUT/budgie-daemon.log" 2>&1 &
pkill -x nemo-desktop; sleep 1; nemo-desktop >/dev/null 2>&1 &
sleep 4

hud_restart() {
    pkill -f '[c]yberneon-hud.py'; sleep 1
    CYBERNEON_HUD_STATE=$OUT/hud-state.json CYBERNEON_USB_ROOT=$USB python3 -I "$HOME/.config/cyberneon/hud/cyberneon-hud.py" --fps 15 "$@" >>"$OUT/hud.log" 2>&1 &
    sleep 4
}
hud_restart
HUD=$(pgrep -f '[c]yberneon-hud.py' | head -1)
check "HUD process is running" [ -n "$HUD" ]
check "conky and ShowTime are gone" sh -c '! pgrep -x conky && ! pgrep -f "[s]howtime_desktop"'
check "notifications moved bottom left" sh -c "gsettings get com.solus-project.budgie-panel notification-position | grep -q BOTTOM_LEFT"
python3 "$REPO/lab/test_hud.py" "$REPO" > "$OUT/unit.txt" 2>&1; check "unit tests" grep -q 'unit tests ok' "$OUT/unit.txt"
shot 01-hud-empty
check "no active objective on an empty desktop" [ "$(state "d['objectives']")" = "[]" ]

# ------------------------------------------------------------------ windows: objective tracker, click-through
nemo "$HOME" >/dev/null 2>&1 &
sleep 3
tilix >/dev/null 2>&1 &
sleep 5
state "d['objectives']" > "$OUT/objectives.txt"
check "tracker lists the open windows" sh -c "[ \$(python3 -c \"import ast;print(len(ast.literal_eval(open('$OUT/objectives.txt').read())))\") -ge 2 ]"
shot 02-hud-windows
python3 - <<PY > "$OUT/stacking.txt"
import subprocess
print(subprocess.run("xprop -root _NET_CLIENT_LIST_STACKING",shell=True,capture_output=True,text=True).stdout)
PY
wmctrl -lx >> "$OUT/stacking.txt"
dock_info() {
    python3 - <<'PY'
import re, subprocess
tree = subprocess.run(["xwininfo", "-root", "-tree"], capture_output=True, text=True).stdout
for l in tree.splitlines():
    if '"budgie-panel"' in l or 'Budgie-panel' in l:
        m = re.search(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)\s+\+(-?\d+)\+(-?\d+)", l)
        if m:
            w, h, _, _, x, y = map(int, m.groups())
            if w > 60 and h > 40 and y > 800:
                print(w, h, x, y)
PY
}
dock_info > "$OUT/dock.txt"; xprop -root _NET_WORKAREA >> "$OUT/dock.txt"
read -r DW DH DX DY < "$OUT/dock.txt"
check "dock is at the bottom, centred (${DW}x${DH}+${DX}+${DY})" sh -c "[ -n '$DW' ] && [ $(( ${DX:-0} + ${DW:-0} / 2 )) -gt 930 ] && [ $(( ${DX:-0} + ${DW:-0} / 2 )) -lt 990 ] && [ $(( ${DY:-0} + ${DH:-0} )) -ge 1070 ]"
convert "$OUT/02-hud-windows.png" -crop 900x110+510+970 +repage "$OUT/15-dock.png"
panel_apps > "$OUT/panels.txt"; top_alpha > "$OUT/top-alpha.txt"
check "dock holds the app launchers only" grep -q "^bottom .* | Icon Task List$" "$OUT/panels.txt"
check "top-left pod: logo menu and workspaces, no task list" sh -c "grep '^top true |' $OUT/panels.txt | grep 'Budgie Menu' | grep -q 'Workspace Switcher' && ! grep '^top' $OUT/panels.txt | grep -q 'Task List'"
read -r A_L A_MID A_R TOP_H < "$OUT/top-alpha.txt"
check "top bar is two pods with a gap between them (alpha ${A_L:-?}/${A_MID:-?}/${A_R:-?})" sh -c "[ '${A_L:-0}' -gt 200 ] && [ '${A_MID:-255}' -lt 20 ] && [ '${A_R:-0}' -gt 200 ]"
check "the second app menu (a second logo) is out of the pods" sh -c "grep '^top' $OUT/panels-before.txt | grep -q AppMenu && ! grep '^top' $OUT/panels.txt | grep -q AppMenu"
check "clock shows the time only" sh -c "dconf dump /com/solus-project/clock/ | grep -q \"custom-format='%H:%M'\""
convert "$OUT/02-hud-windows.png" -crop 1920x64+0+0 +repage "$OUT/17-top.png"
if [ "$LAB_ONLY" = dock ]; then shot 16-dock-full; chmod -R a+rwX "$OUT" 2>/dev/null; exit 0; fi
wmctrl -c tilix; wmctrl -c netrunner; wmctrl -c Home; sleep 2
for w in $(wmctrl -l | awk '$2>=0{print $1}'); do wmctrl -i -c "$w"; done; sleep 2

# ------------------------------------------------------------------ OSD
osd() { gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell --method org.gnome.Shell.ShowOSD "$1" >/dev/null; }
osd "{'icon': <'audio-volume-high-symbolic'>, 'level': <0.72>}"; sleep 0.7; shot 03-osd-volume
osd "{'icon': <'display-brightness-symbolic'>, 'level': <0.45>}"; sleep 0.7; shot 04-osd-brightness
osd "{'icon': <'audio-volume-muted-symbolic'>, 'level': <0.0>}"; sleep 0.7; shot 05-osd-muted
sleep 3; shot 06-osd-gone
osd "{'icon': <'audio-volume-high-symbolic'>, 'level': <0.72>}"; sleep 0.7; xwininfo -root -tree > "$OUT/windows-osd.txt"; sleep 2.5
xwininfo -root -tree > "$OUT/windows.txt"
check "Quickhack bar is drawn" sh -c "[ \$(convert $OUT/03-osd-volume.png -crop 500x90+710+930 -fill black +opaque '#5beedc' -fill white -opaque '#5beedc' -format '%[fx:int(mean*w*h)]' info:) -gt 600 ]"

# ------------------------------------------------------------------ notification sound and position
notify-send -u normal "INCOMING CALL // FIXER" "Got a gig for you, netrunner." ; sleep 2; shot 07-notification; sleep 1
cp "$OUT/canberra.log" "$OUT/canberra-theme-off.txt" 2>/dev/null

# ------------------------------------------------------------------ live terminal with real traffic
if [ -n "$LAB_PEER" ]; then
    python3 -c "
import socket,time
s=socket.create_connection(('$LAB_PEER',8443)); end=time.time()+24
while time.time()<end: s.recv(1<<20)" & CLIENT=$!
    sleep 16
    check "trace warning with real traffic" sh -c "grep -q 'trace program active' $OUT/hud-state.json"
    check "the connection appears as a tag" sh -c "grep -Eq '0x[0-9A-F]{6}:8443 +HTTPS python3' $OUT/hud-state.json"
    state "d['traffic']" > "$OUT/radar-traffic.txt"
    check "radar: the downloading program gets an arrow ($(cat "$OUT/radar-traffic.txt"))" \
        [ "$(state "any(t[0] == 'python3' and t[1] > 1000000 for t in d['traffic'])")" = True ]
    check "radar: a device seen for the first time on the network is an event" \
        [ "$(state "any(e.startswith('LAN // NEW NODE') for e in d['events'])")" = True ]
    shot 08-live-terminal
    wait $CLIENT 2>/dev/null
fi
check "peer address is not shown" sh -c "! grep -q '$LAB_PEER' $OUT/hud-state.json"
check "journal text is not shown" sh -c "! grep -Eq 'SECRET|203\.0\.113' $OUT/hud-state.json"

# ------------------------------------------------------------------ threat radar: contacts and intrusions
log "radar"
/tmp/lab/icebreaker > /dev/null & B1=$!
python3 /tmp/lab/datamine.py 0.62 & B2=$!
python3 /tmp/lab/tracer.py 0.3 & B3=$!
python3 -m http.server 8099 --bind 0.0.0.0 >/dev/null 2>&1 & B4=$!
sleep 11
state "d['hostiles']" > "$OUT/radar-hostiles.txt"
# the lab shares its cores (budgie-wm composites in software here), so the loads are checked with some margin
check "radar: a program using a whole core is a hot contact ($(cat "$OUT/radar-hostiles.txt"))" \
    [ "$(state "any(h[0] == 'icebreaker' and h[1] >= 1 and h[2] >= 60 for h in d['hostiles'])")" = True ]
check "radar: a lighter load is a contact too" [ "$(state "'datamine' in [h[0] for h in d['hostiles']]")" = True ]
check "radar: contacts are sorted, the heaviest first" [ "$(state "[h[1] for h in d['hostiles']] == sorted([h[1] for h in d['hostiles']], reverse=True)")" = True ]
check "radar: a new open port is an event" [ "$(state "'PORT 8099 OPEN // HTTP.SERVER' in d['events']")" = True ]
mkdir -p "$USB/1-2" "$USB/1-2:1.0" "$USB/1-2:1.1"; echo 3 > "$USB/1-2/devnum"
echo 08 > "$USB/1-2:1.0/bInterfaceClass"; echo 50 > "$USB/1-2:1.0/bInterfaceProtocol"
echo 03 > "$USB/1-2:1.1/bInterfaceClass"; echo 01 > "$USB/1-2:1.1/bInterfaceProtocol"
sleep 4
check "radar: a USB stick that is also a keyboard is flagged" [ "$(state "'USB // KEYBOARD' in d['events']")" = True ]
echo '{"SYSLOG_IDENTIFIER":"sudo","MESSAGE":"pam_unix(sudo:auth): authentication failure; logname=netrunner uid=1000 ruser=SECRETUSER rhost=203.0.113.9"}' >> /tmp/xdg/auth.jsonl
sleep 2
check "radar: a wrong sudo password is an event" [ "$(state "'SUDO // WRONG PASSWORD' in d['events']")" = True ]
check "radar: the journal line itself is never shown" sh -c "! grep -Eq 'SECRETUSER|203\.0\.113\.9' $OUT/hud-state.json"
sleep 1; shot 18-radar

mkdir -p "$OUT/gif"; for i in $(seq -w 1 90); do import -window root -crop 344x420+1574+44 +repage "$OUT/gif/radar-$i.png"; sleep 0.12; done
python3 - "$OUT/radar-cpu.txt" <<'PY'
import subprocess, sys, time
pid = subprocess.run(["pgrep", "-f", "[c]yberneon-hud.py"], capture_output=True, text=True).stdout.split()[0]
tick = lambda: sum(int(x) for x in open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[11:13])
a = tick(); time.sleep(20); b = tick()
open(sys.argv[1], "w").write(f"HUD CPU over 20 s with 3 contacts and 4 events: {(b - a) / 20:.0f}% of one core\n")
PY
cat "$OUT/radar-cpu.txt"
# quickhack: real mouse clicks on the radar's contacts
python3 "$REPO/lab/input_shape.py" "$(xwininfo -root -tree | grep '"cyberneon-radar"' | awk '{print $1}')" > "$OUT/radar-input.txt" 2>&1
check "quickhack: only the contacts take clicks, 28x28 each ($(cat "$OUT/radar-input.txt"))" \
    sh -c "[ \"\$(cut -d' ' -f1 $OUT/radar-input.txt)\" -ge 1 ] && grep -qF '[(28, 28)]' $OUT/radar-input.txt"
click() { xdotool mousemove "$1" "$2" click 1; sleep 1.4; }
pos() { state "' '.join(str(v) for c in d['contacts'] if c[0] == '$1' for v in c[1:])"; }
btn() { state "' '.join(map(str, d['hack']['buttons']['$1']))"; }
alive() { ps -o stat= -p "$1" 2>/dev/null | grep -qv Z; }
read -r X Y <<< "$(pos budgie-wm)"; [ -n "$X" ] && click "$X" "$Y"
check "quickhack: the desktop session is protected (budgie-wm)" [ "$(state "(d['hack'] or {}).get('stage')")" = protected ]
read -r X Y <<< "$(btn close)"; [ -n "$X" ] && click "$X" "$Y"
check "quickhack: the panel closes" [ "$(state "d['hack']")" = None ]
read -r X Y <<< "$(pos icebreaker)"; click "$X" "$Y"
check "quickhack: a click on a contact opens the panel" [ "$(state "(d['hack'] or {}).get('stage')")" = menu ]
shot 19-quickhack-menu
read -r X Y <<< "$(btn overload)"; click "$X" "$Y"
check "quickhack: it asks for a confirmation first" [ "$(state "(d['hack'] or {}).get('stage')")" = confirm ]
check "quickhack: nothing is closed before the confirmation" alive "$B1"
shot 19-quickhack-confirm
read -r X Y <<< "$(btn upload)"; xdotool mousemove "$X" "$Y" click 1; sleep 0.5; shot 19-quickhack-upload; sleep 2
check "quickhack: OVERLOAD closes the program" sh -c "! ps -o stat= -p $B1 2>/dev/null | grep -qv Z"
check "quickhack: the result is shown ($(state "(d['hack'] or {}).get('result')"))" sh -c "grep -q 'OVERLOAD UPLOADED' $OUT/hud-state.json"
shot 19-quickhack-done
kill $B1 $B2 $B3 $B4 2>/dev/null; wait $B1 $B2 $B3 $B4 2>/dev/null
if [ "$LAB_ONLY" = radar ]; then grep -c Traceback "$OUT/hud.log" > "$OUT/tracebacks.txt"; chmod -R a+rwX "$OUT"; exit 0; fi

# ------------------------------------------------------------------ alert with a real CPU load
log "alert"
sleep 8
BURN=(); for _ in $(seq 1 "$(nproc)"); do (timeout 17 /tmp/lab/icebreaker > /dev/null) & BURN+=($!); done
if wait_for "d['alert']" 12; then pass "alert starts under real CPU load: $(state "d['status']")"; else fail "alert starts (cpu $(state "d['cpu']"))"; fi
# the culprit is whoever uses the most CPU right now (here budgie-wm, compositing in software, can outrun the load)
if wait_for "d['alert'] and d['cpu_top'] in ('icebreaker', 'budgie-wm') and d['status'].endswith('//  ' + d['cpu_top'].upper())" 12
then pass "the alert names the culprit: $(state "d['status']")"; else fail "the alert names the culprit ($(state "d['status'], d['cpu_top']"))"; fi
sleep 1; shot 09-alert
mkdir -p "$OUT/gif"; for i in $(seq -w 1 14); do import -window root "$OUT/gif/alert-$i.png"; sleep 0.15; done
wait "${BURN[@]}" 2>/dev/null
if wait_for "not d['alert']" 40; then pass "alert ends when the load drops"; else fail "alert did not end (cpu $(state "round(d['cpu'])")%)"; fi

# ------------------------------------------------------------------ battery and TUXEDO Control Center (simulated)
log "battery"
python3 -m dbusmock --system --template upower >"$OUT/mock-upower.log" 2>&1 & sleep 2
UP="org.freedesktop.UPower /org/freedesktop/UPower org.freedesktop.DBus.Mock"
dev() { gdbus call --system --dest org.freedesktop.UPower --object-path /org/freedesktop/UPower --method org.freedesktop.DBus.Mock.SetupDisplayDevice \
        2 "$1" "$2" 50.0 80.0 10.0 3600 0 true battery-symbolic 1 >>"$OUT/mock-upower.log" 2>&1; }
dev 2 62.0
python3 -m dbusmock --system com.tuxedocomputers.tccd /com/tuxedocomputers/tccd com.tuxedocomputers.tccd >"$OUT/mock-tcc.log" 2>&1 & sleep 2
busctl --system call com.tuxedocomputers.tccd /com/tuxedocomputers/tccd org.freedesktop.DBus.Mock AddMethod sssss \
    com.tuxedocomputers.tccd GetActiveProfileJSON "" s 'ret = "{\"id\":\"lab\",\"name\":\"Cool and breezy\"}"'
hud_restart
sleep 4
check "battery is read (62%)" [ "$(state "d['battery'][:2]")" = "[True, 62]" ]
check "TUXEDO profile in the status line" sh -c "grep -q 'TCC  //  COOL AND BREEZY' $OUT/hud-state.json"
shot 10-battery
wall_diff() { import -window root -crop 500x400+700+250 +repage "$OUT/w1.png"; sleep 2.5; import -window root -crop 500x400+700+250 +repage "$OUT/w2.png"; compare -metric AE "$OUT/w1.png" "$OUT/w2.png" null: 2>&1; }
NORMAL=$(wall_diff)
dev 2 15.0; hud_restart; sleep 2
check "low power is detected at 15%" [ "$(state "d['low_power']")" = True ]
LOW=$(wall_diff); shot 11-low-power
echo "wallpaper pixels changing in 2.5 s: normal=$NORMAL low-power=$LOW" | tee "$OUT/lowpower.txt"
check "animation stops at low power" [ "${LOW%% *}" = 0 ]
check "animation runs on normal power" [ "${NORMAL%% *}" != 0 ]
dev 1 15.0; sleep 12
check "animation resumes when charging" [ "$(state "d['animating']")" = True ]
pkill -f 'dbusmock' ; sleep 11

# ------------------------------------------------------------------ resource use
hud_restart; sleep 5
HUD=$(pgrep -f '[c]yberneon-hud.py' | head -1)
t0=$(awk '{print $14+$15}' /proc/$HUD/stat); sleep 20; t1=$(awk '{print $14+$15}' /proc/$HUD/stat)
echo "HUD CPU over 20 s: $(( (t1 - t0) * 100 / (20 * $(getconf CLK_TCK)) ))% of one core, RSS $(awk '/VmRSS/{print int($2/1024)}' /proc/$HUD/status) MB" | tee "$OUT/usage.txt"
check "exactly one bus watcher" [ "$(pgrep -fc '[b]usctl --user monitor')" = 1 ]
kill "$HUD"; sleep 2
check "no process left behind" sh -c '! pgrep -f "[b]usctl --user monitor"'
hud_restart
shot 12-hud-final
mkdir -p "$OUT/gif"; for i in $(seq -w 1 16); do import -window root "$OUT/gif/hud-$i.png"; sleep 0.25; done

# ------------------------------------------------------------------ optional sounds
log "sounds"
: > "$OUT/canberra.log"; rm -f "$OUT/sfx.log"
sed -i 's/^SOUND_FX=.*/SOUND_FX="yes"/' cyberneon.conf
bash ./install.sh --skip-papirus > "$OUT/install-sound.log" 2>&1; check "install with sounds" [ $? = 0 ]
sleep 5
gsettings get org.gnome.desktop.sound theme-name > "$OUT/sound.txt"
ls "$HOME/.local/share/sounds/cyberneon/stereo" >> "$OUT/sound.txt"
notify-send "INCOMING CALL // FIXER" "sound test"; sleep 2
echo "--- played by budgie-daemon:" >> "$OUT/sound.txt"; cat "$OUT/canberra.log" >> "$OUT/sound.txt" 2>/dev/null
pkill -f '[c]yberneon-hud.py'; sleep 1; hud_restart
BURN=(); for _ in $(seq 1 "$(nproc)"); do (timeout 8 sh -c 'while :; do :; done') & BURN+=($!); done
wait_for "d['alert']" 10; sleep 1; wait "${BURN[@]}" 2>/dev/null
check "warning sound on alert" grep -q dialog-warning "$OUT/sfx.log"
sleep 3; : > "$OUT/sfx.log"
notify-send "CALL 1" "x"; notify-send "CALL 2" "x"; sleep 1
check "chirp on a notification, once for a burst" [ "$(grep -c message-new-instant "$OUT/sfx.log")" = 1 ]
gdbus call --session --dest org.budgie_desktop.Notifications --object-path /org/budgie_desktop/Notifications --method org.buddiesofbudgie.budgie.Dispatcher.ToggleDoNotDisturb >/dev/null
sleep 3; notify-send "CALL 3" "x"; sleep 1
check "no chirp in Do Not Disturb" [ "$(grep -c message-new-instant "$OUT/sfx.log")" = 1 ]
gdbus call --session --dest org.budgie_desktop.Notifications --object-path /org/budgie_desktop/Notifications --method org.buddiesofbudgie.budgie.Dispatcher.ToggleDoNotDisturb >/dev/null
sed -n 1,12p "$OUT/sfx.log" >> "$OUT/sound.txt"
sed -i 's/^SOUND_FX=.*/SOUND_FX="no"/' cyberneon.conf

# ------------------------------------------------------------------ classic layout, then uninstall
log "classic"
sed -i 's/^HUD_STYLE=.*/HUD_STYLE="classic"/' cyberneon.conf
bash ./install.sh --skip-papirus > "$OUT/install-classic.log" 2>&1; check "install classic layout" [ $? = 0 ]
sleep 8
check "classic: conky runs" pgrep -x conky
check "classic: wallpaper only" pgrep -f '[c]yberneon-hud.py.*--wallpaper-only'
check "classic: dock back on the left" sh -c "dconf dump $BP/ | grep -q \"location='left'\""
panel_apps > "$OUT/panels-classic.txt"
check "classic: menu and workspaces back in the dock" grep -q "^left .* | Budgie Menu,Icon Task List,Workspace Switcher$" "$OUT/panels-classic.txt"
check "classic: the top bar gets its own applets back" sh -c "grep '^top false |' $OUT/panels-classic.txt | grep 'Budgie Menu' | grep 'Icon Task List' | grep AppMenu | grep -q Spacer && [ ! -e $HOME/.local/share/cyberneon/panels-state.json ]"
shot 13-classic
check "classic: sound theme removed" sh -c "! gsettings get org.gnome.desktop.sound theme-name | grep -q cyberneon"
log "uninstall"
bash ./uninstall.sh > "$OUT/uninstall.log" 2>&1; check "uninstall.sh exits 0" [ $? = 0 ]
sleep 4
ps -eo pid,args | grep -E '[c]yberneon|[c]onky' | cut -c1-140 > "$OUT/after-uninstall.txt"
check "nothing keeps running" sh -c '! pgrep -f "[c]yberneon-hud.py" && ! ps -eo stat=,comm= | grep -E "^[^Z]+ conky$"'
check "notifications back to default" sh -c "gsettings get com.solus-project.budgie-panel notification-position | grep -q TOP_RIGHT"
check "HUD files removed" [ ! -e "$HOME/.config/cyberneon/hud" ]
shot 14-after-uninstall
grep -c 'Traceback' "$OUT/hud.log" > "$OUT/tracebacks.txt"
check "no Python errors from the HUD" [ "$(cat "$OUT/tracebacks.txt")" = 0 ]
chmod -R a+rwX "$OUT"
log "done"
