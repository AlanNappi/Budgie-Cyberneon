#!/usr/bin/env python3
"""Configure Budgie panels for CyberNeon (idempotent: safe to run again).

- top panel  : 34 px, no transparency; a Spacer at the very start keeps applets clear of the red
               corner block; the Clock moves to the right end with format '%Y-%m-%d  %H:%M'.
- left dock  : created if no left panel exists: Budgie Menu (logo), Icon Task List, Workspaces.

usage: panels.py [--pinned a.desktop,b.desktop,...] [--spacer 116]
budgie-panel must be restarted afterwards (budgie-panel --replace).
"""
import argparse, ast, os, subprocess, uuid

BP = "/com/solus-project/budgie-panel"


def gset(schema_path, key, value):
    subprocess.run(["gsettings", "set", schema_path, key, value], check=True)


def dread(path):
    out = subprocess.run(["dconf", "read", path], capture_output=True, text=True, check=True).stdout.strip()
    return out


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


def new_applet(name, align, pos):
    uid = str(uuid.uuid1())
    gset(applet_path(uid), "name", f"'{name}'")
    gset(applet_path(uid), "alignment", f"'{align}'")
    gset(applet_path(uid), "position", str(pos))
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
    a = ap.parse_args()

    panels = lst(f"{BP}/panels")
    loc = {p: sval(f"{BP}/panels/{{{p}}}/location") or "top" for p in panels}
    tops = [p for p in panels if loc[p] == "top"]
    if not tops:
        raise SystemExit("no top panel found: add one in Budgie Desktop Settings first")
    top = tops[0]

    # ---------------- top panel ----------------
    gset(panel_path(top), "size", "34")
    gset(panel_path(top), "enable-shadow", "true")
    gset(panel_path(top), "transparency", "'none'")
    gset(panel_path(top), "spacing", "8")

    applets = lst(f"{BP}/panels/{{{top}}}/applets")
    info = {u: (sval(f"{BP}/applets/{{{u}}}/name"), sval(f"{BP}/applets/{{{u}}}/alignment") or "start",
                sval(f"{BP}/applets/{{{u}}}/position") or 0) for u in applets}

    # spacer first in the start group
    starts = sorted([u for u in applets if info[u][1] == "start"], key=lambda u: info[u][2])
    spacer = next((u for u in starts if info[u][0] == "Spacer"), None)
    if spacer is None:
        spacer = new_applet("Spacer", "start", 0)
        applets = [spacer] + applets
    starts = [spacer] + [u for u in starts if u != spacer]
    for i, u in enumerate(starts):
        gset(applet_path(u), "alignment", "'start'")
        gset(applet_path(u), "position", str(i))
    gset(f"com.solus-project.spacer:{BP}/instance/spacer/{{{spacer}}}/", "size", str(a.spacer))

    # clock to the right end, before Separator / User Indicator / Raven Trigger
    clock = next((u for u in applets if info.get(u, ("",))[0] == "Clock"), None)
    if clock is None:
        clock = new_applet("Clock", "end", 0)
        applets.append(clock)
        info[clock] = ("Clock", "end", 0)
    ends = sorted([u for u in applets if u != clock and info.get(u, ("", "start"))[1] == "end"],
                  key=lambda u: info[u][2])
    tail = {"Separator", "User Indicator", "Raven Trigger"}
    idx = next((i for i, u in enumerate(ends) if info[u][0] in tail), len(ends))
    ends.insert(idx, clock)
    for i, u in enumerate(ends):
        gset(applet_path(u), "alignment", "'end'")
        gset(applet_path(u), "position", str(i))
    csp = f"com.solus-project.clock:/com/solus-project/clock/instance/clock/{{{clock}}}/"
    gset(csp, "use-custom-format", "true")
    gset(csp, "custom-format", "'%Y-%m-%d  %H:%M'")
    gset(panel_path(top), "applets", str(applets))

    # ---------------- left dock ----------------
    lefts = [p for p in panels if loc[p] == "left"]
    if lefts:
        left = lefts[0]
        print("left panel already present:", left)
    else:
        left = str(uuid.uuid1())
        menu = new_applet("Budgie Menu", "start", 0)
        tasks = new_applet("Icon Task List", "start", 1)
        ws = new_applet("Workspace Switcher", "end", 0)
        pinned = [d for d in a.pinned.split(",") if d and desktop_exists(d)]
        gset(f"com.solus-project.icon-tasklist:{BP}/instance/icon-tasklist/{{{tasks}}}/", "pinned-launchers", str(pinned))
        gset(panel_path(left), "location", "'left'")
        gset(panel_path(left), "applets", str([menu, tasks, ws]))
        gset("com.solus-project.budgie-panel", "panels", str(panels + [left]))
        print("left panel created:", left)

    gset(panel_path(left), "size", "76")
    gset(panel_path(left), "spacing", "6")
    gset(panel_path(left), "transparency", "'none'")
    gset(panel_path(left), "enable-shadow", "true")
    gset(panel_path(left), "autohide", "'none'")
    gset(panel_path(left), "dock-mode", "false")
    for u in lst(f"{BP}/panels/{{{left}}}/applets"):
        name = sval(f"{BP}/applets/{{{u}}}/name")
        if name == "Budgie Menu":
            mp = f"com.solus-project.budgie-menu:{BP}/instance/budgie-menu/{{{u}}}/"
            gset(mp, "use-default-menu-icon", "false")
            gset(mp, "menu-icon", "'cyberneon-logo'")
            gset(mp, "enable-menu-label", "false")
        elif name == "Workspace Switcher":
            wp = f"com.solus-project.workspaces:{BP}/instance/workspaces/{{{u}}}/"
            gset(wp, "addbutton-visibility", "'never'")
            gset(wp, "item-size-multiplier", "'0.5'")
    print("panels configured (top:", top, "left:", left + ")")


if __name__ == "__main__":
    main()
