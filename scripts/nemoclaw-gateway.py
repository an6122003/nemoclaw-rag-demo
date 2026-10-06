#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Start the workshop's OpenShell gateway again after a restart, without internet.

    python3 scripts/nemoclaw-gateway.py record   # while it runs (start.sh, every start)
    python3 scripts/nemoclaw-gateway.py start    # after a restart, when it is down

NemoClaw launches the gateway of a non-default port (the workshop uses 8990)
as a plain background process, so it does not come back after the computer
restarts. NemoClaw's only way to start it again is `nemoclaw onboard`, whose
preflight stops when DNS does not answer: with no internet at the venue the
labs would lose their sandbox after a restart.

The launch itself is simple: one binary, an environment that points at the
gateway's state directory (config, TLS, database), and a recognisable process
name. `record` copies those from the running process; `start` launches the
same thing again and updates NemoClaw's pid file and runtime marker the way
NemoClaw does, so its own commands keep recognising the gateway. Nothing is
downloaded. If anything does not match, `start` does nothing and start.sh falls
back to onboarding.

Standard library only. Exit code 0 when the gateway is listening.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORD = ROOT / ".run" / "nemoclaw-gateway.json"
PORT = int(os.environ.get("NEMOCLAW_GATEWAY_PORT", "8990"))
NAME = re.compile(r"^openshell-gateway\[nemoclaw=([\w.-]+);port=(\d+)\]$")
# Session details of whoever ran onboarding; the gateway does not need them.
DROP = {"SSH_CONNECTION", "SSH_CLIENT", "SSH_TTY", "SSH_AUTH_SOCK", "XDG_SESSION_ID", "XDG_SESSION_TYPE",
        "XDG_SESSION_CLASS", "DBUS_SESSION_BUS_ADDRESS", "OLDPWD", "_", "SHLVL", "TERM", "DISPLAY",
        "WAYLAND_DISPLAY", "XAUTHORITY"}


def listening(port: int = PORT) -> bool:
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_gateway() -> int | None:
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            argv0 = (proc / "cmdline").read_bytes().split(b"\0")[0].decode()
        except OSError:
            continue
        m = NAME.match(argv0)
        if m and int(m.group(2)) == PORT:
            return int(proc.name)
    return None


def state_dir(env: dict) -> Path | None:
    db = env.get("OPENSHELL_DB_URL", "")
    if db.startswith("sqlite:"):
        return Path(db[len("sqlite:"):]).parent
    tls = env.get("OPENSHELL_LOCAL_TLS_DIR")
    return Path(tls).parent if tls else None


def record() -> int:
    pid = find_gateway()
    if not pid:
        print(f"no NemoClaw gateway process for port {PORT}")
        return 1
    proc = Path(f"/proc/{pid}")
    raw = (proc / "environ").read_bytes().split(b"\0")
    env = {}
    for item in raw:
        key, sep, val = item.decode("utf-8", "replace").partition("=")
        if sep and key not in DROP:
            env[key] = val
    if not env.get("OPENSHELL_SERVER_PORT") or not state_dir(env):
        print("the gateway environment does not look like NemoClaw's; not recording")
        return 1
    data = {
        "exe": os.readlink(proc / "exe"),
        "argv0": (proc / "cmdline").read_bytes().split(b"\0")[0].decode(),
        "cwd": os.readlink(proc / "cwd"),
        "env": env,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    RECORD.parent.mkdir(exist_ok=True)
    tmp = RECORD.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1))
    tmp.chmod(0o600)
    tmp.replace(RECORD)
    print(f"recorded the gateway launch (pid {pid})")
    return 0


def start() -> int:
    if listening():
        print(f"gateway already listening on {PORT}")
        return 0
    if find_gateway():
        print("a gateway process exists but is not listening; leaving it to NemoClaw")
        return 1
    if not RECORD.exists():
        print("no recorded gateway launch")
        return 1
    data = json.loads(RECORD.read_text())
    exe, env = data["exe"], data["env"]
    sdir = state_dir(env)
    if not (os.access(exe, os.X_OK) and sdir and sdir.is_dir() and NAME.match(data["argv0"])
            and int(env.get("OPENSHELL_SERVER_PORT", 0)) == PORT):
        print("the recorded launch no longer matches this machine")
        return 1
    cwd = data["cwd"] if os.path.isdir(data["cwd"]) else str(Path.home())
    log = open(sdir / "openshell-gateway.log", "ab")
    try:
        child = subprocess.Popen([data["argv0"]], executable=exe, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=log, start_new_session=True)
    finally:
        log.close()
    # What NemoClaw writes after its own launch: the pid file and the marker's pid.
    (sdir / "openshell-gateway.pid").write_text(f"{child.pid}\n")
    marker = sdir / "runtime.json"
    try:
        m = json.loads(marker.read_text())
        m["pid"] = child.pid
        marker.write_text(json.dumps(m, indent=2) + "\n")
    except (OSError, ValueError):
        pass
    for _ in range(60):
        if child.poll() is not None:
            print(f"the gateway exited at once (code {child.returncode}); see {sdir / 'openshell-gateway.log'}")
            return 1
        if listening():
            print(f"gateway started (pid {child.pid})")
            return 0
        time.sleep(0.5)
    print("the gateway did not start listening within 30 seconds")
    return 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "record":
        sys.exit(record())
    if cmd == "start":
        sys.exit(start())
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    sys.exit(2)
