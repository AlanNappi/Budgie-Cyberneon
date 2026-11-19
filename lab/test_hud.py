#!/usr/bin/env python3
"""Unit tests of the HUD logic (run by the lab): python3 lab/test_hud.py REPO"""
import json, os, sys

sys.path.insert(0, os.path.join(sys.argv[1], "config/hud"))
import gi
gi.require_version("Gtk", "3.0")
import cn_state as st

r = st.Reactor(85, 85, 95)
assert [r.tick(90, 10, 40) for _ in range(2)] == [False, False] and not r.alert, "2 s over the limit must not trigger"
r.tick(10, 10, 40)
assert not r.alert and r.hot_for == 0, "a dip resets the count"
for _ in range(3):
    changed = r.tick(97, 10, 40)
assert r.alert and changed and r.reason == "CPU 97%"
for _ in range(20):
    r.tick(80, 10, 40)                    # below the limit but inside the margin: stays on
assert r.alert, "the 10 point margin keeps the alert on"
for _ in range(5):
    r.tick(50, 10, 40)
assert r.alert
assert r.tick(50, 10, 40) and not r.alert, "6 calm seconds end it"
r = st.Reactor(85, 85, 95)
for _ in range(3):
    r.tick(10, 90, 96)
assert r.alert and r.reason == "RAM 90%  TEMP 96C"

assert st.describe_osd({"icon": "audio-volume-high-symbolic", "level": 0.8}) == ("AUDIO OUTPUT", 80, "")
assert st.describe_osd({"icon": "audio-volume-muted-symbolic", "level": 0.0}) == ("AUDIO OUTPUT", 0, "MUTED // OFFLINE")
assert st.describe_osd({"icon": "audio-volume-overamplified-symbolic", "level": 1.2, "max_level": 1.5})[1] == 80
assert st.describe_osd({"icon": "display-brightness-symbolic", "level": 40})[:2] == ("OPTICS // BRIGHTNESS", 40)
assert st.describe_osd({"icon": "microphone-sensitivity-muted-symbolic", "level": 0.0})[0] == "MIC INPUT"
assert st.describe_osd({"icon": "input-keyboard-brightness-symbolic", "level": 0.5})[:2] == ("KEY BACKLIGHT", 50)
assert st.describe_osd({"label": "hello"}) == ("SYSTEM", None, "HELLO")

rows = st.terminal_rows([["C", "A64AF0", "8443", "HTTPS", "python3"]], [["J", "12:00:01", "4", "kernel", "AB12"]],
                        1024, 2048, True, 71, True, "CPU 97%")
assert len(rows) == 12
assert rows[1][0] == "[ OK ] 0xA64AF0:8443  HTTPS python3"
assert rows[6] == ("[WARN] 12:00:01 kernel             0xAB12", "red", 0.95)
assert rows[10][0] == "[WARN] trace program active: 01:11" and rows[11][0] == "> !! countermeasures engaged: CPU 97%"
assert st.rate_text(500) == "500B" and st.rate_text(2048) == "2K" and st.rate_text(3 * 1048576) == "3.0M"

# threat radar
import cn_threats as th
assert th.program_name("Isolated Web Co", "/snap/firefox/123/usr/lib/firefox/firefox") == "firefox", "child processes join the program"
assert th.program_name("python3", "/usr/bin/python3.12", ["python3", "-u", "/opt/tools/datamine.py", "--x"]) == "datamine"
assert th.program_name("python3", "/usr/bin/python3.12", ["python3", "-m", "http.server", "8099"]) == "http.server"
assert th.program_name("python3", "/usr/bin/python3.12", ["python3", "-c", "import x"]) == "python3"
assert th.program_name("bash", "/usr/bin/bash", ["/bin/bash", ""]) == "bash"
assert th.program_name("Xorg", "", ["/usr/lib/xorg/Xorg", "-core", ":0"]) == "Xorg", "no exe: never guess from the arguments"
assert th.program_name("claude", "/x/claude.exe") == "claude"
assert th.threat_level(th.threat_score(100, 1)) == 2 and th.threat_level(th.threat_score(60, 1)) == 1
assert th.threat_level(th.threat_score(5, 24)) == 1 and th.threat_level(th.threat_score(5, 3)) == 0
assert th.bearing("firefox") == th.bearing("firefox") and 0 <= th.bearing("x") < 360
ss = ("tcp 0 0 10.0.0.2:41000 93.184.216.34:443 users:((\"firefox\",pid=4242,fd=96))\n"
      "\t cubic bytes_sent:900 bytes_retrans:10 bytes_acked:800 bytes_received:5000 segs_out:5\n"
      "tcp 0 0 127.0.0.1:5000 127.0.0.1:41010 users:((\"x\",pid=1,fd=3))\n\t bytes_acked:1 bytes_received:1\n"
      "udp 0 0 10.0.0.2:5353 142.250.1.1:443 users:((\"firefox\",pid=4242,fd=97))\n")
socks = th.parse_sockets(ss)
assert socks == {"10.0.0.2:41000 93.184.216.34:443": ["tcp", 4242, 800, 5000, "443"],
                 "10.0.0.2:5353 142.250.1.1:443": ["udp", 4242, 0, 0, "443"]}, socks
listen = th.parse_listen("LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\nLISTEN 0 4096 127.0.0.53%lo:53 0.0.0.0:*\n"
                         "LISTEN 0 5 [::]:8099 [::]:* users:((\"python3\",pid=77,fd=3))\nLISTEN 0 5 [::1]:631 [::]:*\n")
assert listen == {22: 0, 8099: 77}, listen
arp = ("IP address HW type Flags HW address Mask Device\n10.0.0.1 0x1 0x2 aa:bb:cc:dd:ee:ff * eth0\n"
       "172.17.0.2 0x1 0x2 02:42:ac:11:00:02 * docker0\n10.0.0.9 0x1 0x0 00:00:00:00:00:00 * eth0\n")
assert th.parse_arp(arp) == {"aa:bb:cc:dd:ee:ff"}
assert th.usb_label([("08", "50"), ("03", "01")]) == "USB // KEYBOARD", "a keyboard hidden in a stick is the keyboard"
assert th.usb_label([("08", "50")]) == "USB // MASS STORAGE" and th.usb_label([("03", "02")]) == "USB // MOUSE"
assert th.usb_label([]) == "USB // DEVICE"
assert th.classify_auth("sudo", "pam_unix(sudo:auth): authentication failure; logname=x uid=1000") == "SUDO // WRONG PASSWORD"
assert th.classify_auth("sshd", "Accepted publickey for x from 10.0.0.5 port 5 ssh2") == "SSH // REMOTE LOGIN"
assert th.classify_auth("sshd", "Failed password for invalid user admin from 1.2.3.4") == "SSH // FAILED LOGIN"
assert th.classify_auth("unix_chkpwd", "password check failed for user (x)") == "LOCK SCREEN // WRONG PASSWORD"
assert th.classify_auth("sudo", "pam_unix(sudo:session): session opened for user root") is None
assert th.classify_auth("CRON", "pam_unix(cron:session): session closed") is None
e = th.auth_event('{"SYSLOG_IDENTIFIER":"sudo","MESSAGE":"3 incorrect password attempts ; SECRET"}')
assert e == {"kind": "auth", "text": "SUDO // WRONG PASSWORD", "bearing": 315} and "SECRET" not in str(e)

# the scanner on this machine: two polls, a fake USB tree and a fake network neighbour list
import tempfile, time
tmp = tempfile.mkdtemp()
usb = os.path.join(tmp, "usb"); os.makedirs(os.path.join(usb, "1-1")); os.makedirs(os.path.join(usb, "usb1"))
open(os.path.join(usb, "1-1", "devnum"), "w").write("2\n")
sc = th.Scanner(usb_root=usb, known_path=os.path.join(tmp, "nodes"))
sc.poll(); time.sleep(0.5)
for d, cls, proto in (("1-2", "08", "50"), ("1-2:1.0", "08", "50"), ("1-2:1.1", "03", "01")):
    os.makedirs(os.path.join(usb, d))
    if ":" in d:
        open(os.path.join(usb, d, "bInterfaceClass"), "w").write(cls + "\n")
        open(os.path.join(usb, d, "bInterfaceProtocol"), "w").write(proto + "\n")
open(os.path.join(usb, "1-2", "devnum"), "w").write("3\n")
snap = sc.poll()
assert [x["text"] for x in snap["events"]] == ["USB // KEYBOARD"], snap["events"]
assert sc.poll()["events"] == [], "the same device is reported once"
state = json.loads(json.dumps(sc.state()))           # what the KDE command keeps between two runs
assert th.Scanner(state, usb).usb == sc.usb

# quickhack: only this user's programs, never the session
import shutil, subprocess
dummy = os.path.join(tmp, "testdummy"); shutil.copy("/bin/sleep", dummy)
kids = [subprocess.Popen([dummy, "60"]) for _ in range(2)]
time.sleep(0.3)
assert th.quickhack("budgie-wm") == {"name": "budgie-wm", "signalled": 0, "refused": "PROTECTED"}
assert th.quickhack("no-such-program")["refused"] == "TARGET LOST"
assert th.quickhack("testdummy") == {"name": "testdummy", "signalled": 2, "refused": ""}
assert all(k.wait(3) is not None for k in kids), "OVERLOAD ends the program"
assert th.is_protected("cyberneon-hud") and th.is_protected("plasmashell") and not th.is_protected("firefox")
print("unit tests ok")
