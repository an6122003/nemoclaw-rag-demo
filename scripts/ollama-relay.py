#!/usr/bin/env python3
"""Forward a local TCP port to a remote Ollama endpoint.

Why this exists
---------------
OpenShell sandboxes can only reach the Docker host gateway, addressed as
``host.openshell.internal``. NemoClaw's shipped ``local-inference`` network
policy preset permits that host on port 11434 but restricts ``allowed_ips`` to
RFC1918 ranges (10/8, 172.16/12, 192.168/16). A Tailscale address lives in
100.64.0.0/10, which is CGNAT and therefore *not* covered by the preset, and the
host-side ``config set`` validator only accepts the bridge URL for provider
``baseUrl`` fields.

Running this relay on the lab host lets the sandbox keep using the fully
documented path -- ``http://host.openshell.internal:11434`` plus the stock
``local-inference`` preset -- while inference is actually served by Ollama on a
different machine.

Usage
-----
    python3 ollama-relay.py --target your-ollama-host:11434
    python3 ollama-relay.py --target your-ollama-host:11434 --bind 0.0.0.0 --port 11434

Run it in the foreground for a lab session, or under a supervisor for an event.
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading

BUFFER = 65536


def pipe(src: socket.socket, dst: socket.socket) -> None:
    """Copy bytes one way until the source closes, then half-close the sink."""
    try:
        while True:
            chunk = src.recv(BUFFER)
            if not chunk:
                break
            dst.sendall(chunk)
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def handle(client: socket.socket, target: tuple[str, int]) -> None:
    try:
        upstream = socket.create_connection(target, timeout=15)
    except OSError as exc:
        print(f"relay: cannot reach {target[0]}:{target[1]}: {exc}", file=sys.stderr)
        client.close()
        return
    upstream.settimeout(None)
    client.settimeout(None)
    # Two threads, one per direction; either side closing ends that direction.
    t = threading.Thread(target=pipe, args=(client, upstream), daemon=True)
    t.start()
    pipe(upstream, client)
    t.join(timeout=5)
    for sock in (client, upstream):
        try:
            sock.close()
        except OSError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Forward a local port to a remote Ollama.")
    ap.add_argument("--target", required=True, help="host:port of the Ollama server")
    ap.add_argument("--bind", default="127.0.0.1", help="local address to bind (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=11434, help="local port (default 11434)")
    args = ap.parse_args()

    host, _, port_s = args.target.rpartition(":")
    if not host:
        print("relay: --target must be host:port", file=sys.stderr)
        return 2
    target = (host, int(port_s))

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((args.bind, args.port))
    except OSError as exc:
        print(f"relay: cannot bind {args.bind}:{args.port}: {exc}", file=sys.stderr)
        return 1
    server.listen(128)
    print(
        f"relay: {args.bind}:{args.port} -> {target[0]}:{target[1]} (ctrl-c to stop)",
        flush=True,
    )
    try:
        while True:
            client, _ = server.accept()
            threading.Thread(target=handle, args=(client, target), daemon=True).start()
    except KeyboardInterrupt:
        print("\nrelay: stopped", flush=True)
    finally:
        server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
