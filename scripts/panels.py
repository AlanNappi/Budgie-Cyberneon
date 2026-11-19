#!/usr/bin/env python3
"""Configure Budgie panels for CyberNeon (idempotent: safe to run again).

Two layouts:
- --dock bottom (game HUD, as in the KDE edition): the top panel turns into two floating pods (52 px panel,
  theme-regions on, transparent): logo menu and workspaces on the left, tray / clock / system menus on the right,
  clock '%H:%M'. The dock floats at the bottom centre with the app launchers only.
- --dock left (classic): 34 px top bar, a Spacer at the very start keeps applets clear of the red corner block,
  clock '%Y-%m-%d  %H:%M' at the right end; vertical dock on the left with menu, launchers and workspaces.

Applets taken out of a panel for the pods (the dock's menu and workspaces, plus a task list, menu, workspaces,
second app menu (AppMenu, the Slingshot launcher: it would show the logo twice) or spacer the top panel already had) are remembered in ~/.local/share/cyberneon/panels-state.json and put back where
they were when the classic layout comes back.

- ShowTime : its desktop clock is replaced by the HUD with --hud game, kept with --hud classic.

usage: panels.py [--pinned a.desktop,...] [--spacer N] [--hud game|classic] [--dock left|bottom] [--menu-icon NAME]
budgie-panel must be restarted afterwards (budgie-panel --replace).
"""
import argparse, ast, json, os, subprocess, uuid
from pathlib import Path

BP = "/com/solus-project/budgie-panel"
STATE = Path.home() / ".local/share/cyberneon/panels-state.json"
POD_LEFT = ("Budgie Menu", "Workspace Switcher")                 # what the top-left pod holds, in this order
TOP_PARKED = POD_LEFT + ("Icon Task List", "Task List", "Spacer", "AppMenu")  # taken out of the top panel for the pods


def gset(schema_path, key, value):
    subprocess.run(["gsettings", "set", schema_path, key, value], check=True)


def dread(path):
    return subprocess.run(["dconf", "read", path], capture_output=True, text=True, check=True).stdout.strip()


def lst(path):
    v = dread(path)
    return ast.literal_eval(v.replace("@as ", "")) if v else []


def sval(path):
    v = dread(path)
    return ast.literal_eval(v) if v else None


def applet_path(uid):
    return f"com.solus-project.budgie-panel.applet:{BP}/applets/{{{uid}}}/"


def panel_path(uid):
    return f"com.solus-project.budgie-panel.panel:{BP}/panels/{{{uid}}}/"


def name(u):
    return sval(f"{BP}/applets/{{{u}}}/name")


def align(u):
    return sval(f"{BP}/applets/{{{u}}}/alignment") or "start"


def pos(u):
    return sval(f"{BP}/applets/{{{u}}}/position") or 0


def place(u, alignment, position):
    gset(applet_path(u), "alignment", f"'{alignment}'")
    gset(applet_path(u), "position", str(position))


def new_applet(applet_name, alignment, position):
    uid = str(uuid.uuid1())
    gset(applet_path(uid), "name", f"'{applet_name}'")
    place(uid, alignment, position)
    return uid


def desktop_exists(d):
    dirs = [os.path.expanduser("~/.local/share/applications"), "/usr/share/applications",
            "/var/lib/snapd/desktop/applications", "/var/lib/flatpak/exports/share/applications"]
    return any(os.path.exists(os.path.join(x, d)) for x in dirs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pinned", default="budgie-control-center.desktop,nemo.desktop,firefox_firefox.desktop,"
                                        "com.gexperts.Tilix.desktop,libreoffice-calc.desktop")
    ap.add_argument("--spacer", type=int, default=116)
    ap.add_argument("--dock", choices=("left", "bottom"), default="left")
    ap.add_argument("--hud", choices=("game", "classic"), default="game")
    ap.add_argument("--menu-icon", default="cyberneon-logo")
    a = ap.parse_args()
    pods = a.dock == "bottom"

    panels = lst(f"{BP}/panels")
    loc = {p: sval(f"{BP}/panels/{{{p}}}/location") or "top" for p in panels}
    tops = [p for p in panels if loc[p] == "top"]
    if not tops:
        raise SystemExit("no top panel found: add one in Budgie Desktop Settings first")
    top = tops[0]

    # ---------------- dock panel (found or created) ----------------
    def has_tasks(p):
        return any(name(u) == "Icon Task List" for u in lst(f"{BP}/panels/{{{p}}}/applets"))
    docks = [p for p in panels if loc[p] == "left"] or [p for p in panels if loc[p] == "bottom" and has_tasks(p)]
    if docks:
        dock = docks[0]
        print("dock panel already present:", dock)
    else:
        dock = str(uuid.uuid1())
        menu = new_applet("Budgie Menu", "start", 0)
        tasks = new_applet("Icon Task List", "start", 1)
        ws = new_applet("Workspace Switcher", "end", 0)
        pinned = [d for d in a.pinned.split(",") if d and desktop_exists(d)]
        gset(f"com.solus-project.icon-tasklist:{BP}/instance/icon-tasklist/{{{tasks}}}/", "pinned-launchers", str(pinned))
        gset(panel_path(dock), "location", "'left'")
        gset(panel_path(dock), "applets", str([menu, tasks, ws]))
        panels = panels + [dock]
        gset("com.solus-project.budgie-panel", "panels", str(panels))
        print("dock panel created:", dock)

    top_apps = lst(f"{BP}/panels/{{{top}}}/applets")
    dock_apps = lst(f"{BP}/panels/{{{dock}}}/applets")
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    parked = state.get("parked", {})            # uid -> {"panel": "top"|"dock", "alignment": ..., "position": ...}

    # ---------------- put back what the pods took out (classic layout) ----------------
    if not pods and parked:
        for u, where in parked.items():
            top_apps = [x for x in top_apps if x != u]
            dock_apps = [x for x in dock_apps if x != u]
            (top_apps if where["panel"] == "top" else dock_apps).append(u)
            place(u, where["alignment"], where["position"])
        parked = {}
        print("pods: applets put back")

    # ---------------- top panel ----------------
    gset(panel_path(top), "size", "52" if pods else "34")
    gset(panel_path(top), "enable-shadow", "false" if pods else "true")
    gset(panel_path(top), "transparency", "'none'")
    gset(panel_path(top), "spacing", "6" if pods else "8")
    gset(panel_path(top), "theme-regions", "true" if pods else "false")
    gset(panel_path(top), "autohide", "'none'")
    gset(panel_path(top), "dock-mode", "false")

    # ShowTime draws a desktop clock: the game HUD has its own, so the applet leaves the panel (its settings stay)
    if a.hud == "game":
        top_apps = [u for u in top_apps if name(u) != "ShowTime"]
    elif not any(name(u) == "ShowTime" for u in top_apps):
        known = subprocess.run(["dconf", "list", f"{BP}/applets/"], capture_output=True, text=True).stdout.split()
        for key in known:
            u = key.strip("{}/")
            if name(u) == "ShowTime":
                top_apps.append(u)
                break

    if pods:
        # the dock's menu and workspaces move up; the top panel's own copies (and its task list) step aside
        moving = {name(u): u for u in dock_apps if name(u) in POD_LEFT}
        for u in list(top_apps):
            n = name(u)
            if n in TOP_PARKED and u not in parked and (n not in POD_LEFT or n in moving):
                parked[u] = {"panel": "top", "alignment": align(u), "position": pos(u)}
                top_apps.remove(u)
        for n, u in moving.items():
            parked[u] = {"panel": "dock", "alignment": align(u), "position": pos(u)}
            dock_apps.remove(u)
            top_apps.append(u)
        starts = sorted([u for u in top_apps if align(u) == "start" and u not in moving.values()], key=pos)
        lead = [u for n in POD_LEFT for u in top_apps if name(u) == n]
        starts = lead + [u for u in starts if u not in lead]
    else:
        # spacer first in the start group
        starts = sorted([u for u in top_apps if align(u) == "start"], key=pos)
        spacer = next((u for u in starts if name(u) == "Spacer"), None)
        if spacer is None:
            spacer = new_applet("Spacer", "start", 0)
            top_apps = [spacer] + top_apps
        starts = [spacer] + [u for u in starts if u != spacer]
        gset(f"com.solus-project.spacer:{BP}/instance/spacer/{{{spacer}}}/", "size", str(a.spacer))
    for i, u in enumerate(starts):
        place(u, "start", i)

    # clock to the right end, before Separator / User Indicator / Raven Trigger
    clock = next((u for u in top_apps if name(u) == "Clock"), None)
    if clock is None:
        clock = new_applet("Clock", "end", 0)
        top_apps.append(clock)
    ends = sorted([u for u in top_apps if u != clock and align(u) == "end"], key=pos)
    tail = {"Separator", "User Indicator", "Raven Trigger"}
    idx = next((i for i, u in enumerate(ends) if name(u) in tail), len(ends))
    ends.insert(idx, clock)
    for i, u in enumerate(ends):
        place(u, "end", i)
    csp = f"com.solus-project.clock:/com/solus-project/clock/instance/clock/{{{clock}}}/"
    gset(csp, "use-custom-format", "true")
    gset(csp, "custom-format", "'%H:%M'" if pods else "'%Y-%m-%d  %H:%M'")
    gset(panel_path(top), "applets", str(top_apps))

    # ---------------- dock ----------------
    gset(panel_path(dock), "location", "'bottom'" if pods else "'left'")
    gset(panel_path(dock), "size", "72" if pods else "76")
    gset(panel_path(dock), "spacing", "2" if pods else "6")
    gset(panel_path(dock), "transparency", "'none'")
    gset(panel_path(dock), "enable-shadow", "false" if pods else "true")
    gset(panel_path(dock), "autohide", "'none'")
    gset(panel_path(dock), "dock-mode", "true" if pods else "false")
    gset(panel_path(dock), "applets", str(dock_apps))

    for u in top_apps + dock_apps:
        n = name(u)
        if n == "Budgie Menu":
            mp = f"com.solus-project.budgie-menu:{BP}/instance/budgie-menu/{{{u}}}/"
            if u in dock_apps or u in parked:            # ours (a menu the top panel had keeps its icon)
                gset(mp, "use-default-menu-icon", "false")
                gset(mp, "menu-icon", f"'{a.menu_icon}'" if pods else "'cyberneon-logo'")
                gset(mp, "enable-menu-label", "false")
        elif n == "Workspace Switcher":
            wp = f"com.solus-project.workspaces:{BP}/instance/workspaces/{{{u}}}/"
            gset(wp, "addbutton-visibility", "'never'")
            gset(wp, "item-size-multiplier", "'0.5'")

    STATE.parent.mkdir(parents=True, exist_ok=True)
    if parked:
        STATE.write_text(json.dumps({"parked": parked}, indent=1) + "\n")
    elif STATE.exists():
        STATE.unlink()
    print("panels configured (top:", top, "dock:", dock, "layout:", "pods" if pods else "bar", ")")


if __name__ == "__main__":
    main()
