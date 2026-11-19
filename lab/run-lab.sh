#!/bin/bash
# Host side of the test lab: real Budgie 10.9 (Ubuntu 24.04) on a virtual screen, real install.sh, real screenshots.
# Results in lab/out/. Your desktop and your settings are not touched. Needs Docker (about 1.5 GB the first time).
set -euo pipefail
L="$(cd "$(dirname "$0")" && pwd)"; REPO="$(dirname "$L")"
mkdir -p "$L/out"; rm -rf "$L/out"/* 2>/dev/null || docker run --rm -v "$L/out:/out" ubuntu:24.04 sh -c "rm -rf /out/*"
docker build -q -t cyberneon-budgie-lab "$L" >/dev/null
ARGS=(--rm --shm-size=1g --cap-add=SYS_NICE -e LAB_ONLY="${1:-}" -v "$REPO:/repo:ro" -v "$L/out:/out" -v "$L/inside.sh:/inside.sh:ro")
[ -d "$HOME/.local/share/icons/Papirus-Dark" ] && ARGS+=(-v "$HOME/.local/share/icons:/hosticons:ro")
for d in "$HOME/.fonts" "$HOME/.local/share/fonts"; do
    ls "$d"/JetBrainsMonoNerdFontMono-* >/dev/null 2>&1 && { ARGS+=(-v "$d:/hostfonts:ro"); break; }
done

# a second container streams data, so the lab has real network traffic and a real remote connection
PEER=cyberneon-budgie-peer; docker rm -f "$PEER" >/dev/null 2>&1 || true
docker run -d --rm --name "$PEER" cyberneon-budgie-lab python3 -c '
import socket, threading, time
s = socket.create_server(("", 8443))
def feed(c):
    try:
        while True: c.sendall(bytes(1 << 20)); time.sleep(0.05)
    except OSError: pass
while True: threading.Thread(target=feed, args=(s.accept()[0],), daemon=True).start()' >/dev/null
trap 'docker rm -f "$PEER" >/dev/null 2>&1 || true' EXIT
IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$PEER")
docker run "${ARGS[@]}" -e LAB_PEER="$IP" cyberneon-budgie-lab bash /inside.sh
echo "results in $L/out"
