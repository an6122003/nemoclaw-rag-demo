"""Shared plumbing for the workshop app: settings, Ollama, NemoClaw.

Standard library only. The Hands-on 3 tools need pandas/matplotlib/openpyxl and
are imported lazily by lab3_agent, so the app still serves Hands-on 1 and 2 when
the Python environment is incomplete.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = ROOT / ".run"


# --------------------------------------------------------------------------
# Settings: workshop.env, overridden by the environment
# --------------------------------------------------------------------------
def _read_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        out[key.strip()] = value
    return out


_FILE = _read_env_file(ROOT / "workshop.env")


def setting(key: str, default: str = "") -> str:
    return os.environ.get(key) or _FILE.get(key) or default


OLLAMA = setting("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
CHAT_MODEL = setting("CHAT_MODEL", "qwen3.6:35b")
EMBED_MODEL = setting("EMBED_MODEL", "qwen3-embedding:4b")
SANDBOX = setting("SANDBOX", "my-assistant")


# --------------------------------------------------------------------------
# HTTP helpers
# --------------------------------------------------------------------------
def http_json(url: str, payload: dict | None = None, timeout: float = 60,
              headers: dict | None = None, method: str | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else {}


def ollama_up(timeout: float = 4) -> bool:
    try:
        http_json(f"{OLLAMA}/api/version", timeout=timeout)
        return True
    except Exception:
        return False


_models_cache: tuple[float, set[str]] = (0.0, set())


def ollama_models(max_age: float = 15) -> set[str]:
    """Installed Ollama model tags, cached briefly (the UI polls health)."""
    global _models_cache
    ts, names = _models_cache
    if time.time() - ts < max_age:
        return names
    try:
        tags = http_json(f"{OLLAMA}/api/tags", timeout=6).get("models", [])
        names = {m.get("name", "") for m in tags} | {m.get("model", "") for m in tags}
    except Exception:
        names = set()
    _models_cache = (time.time(), names)
    return names


def has_model(tag: str) -> bool:
    names = ollama_models()
    if tag in names:
        return True
    if ":" not in tag:
        return f"{tag}:latest" in names
    return False


def forget_models_cache() -> None:
    global _models_cache
    _models_cache = (0.0, set())


_think_block = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.S | re.I)


def strip_thinking(text: str) -> str:
    """Remove qwen-style reasoning scaffolding so only the answer is shown."""
    text = _think_block.sub("", text or "")
    text = re.sub(r"</?think(?:ing)?>", "", text, flags=re.I)
    return text.strip()


def ollama_chat_stream(model: str, messages: list[dict], options: dict | None = None,
                       timeout: float = 300):
    """Yield text deltas from Ollama's native /api/chat with thinking disabled."""
    payload = {"model": model, "messages": messages, "stream": True, "think": False,
               "options": options or {}}
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 400 and b"think" in exc.read():
            payload.pop("think")  # model without a thinking switch
            req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=timeout)
        else:
            raise
    in_think = False
    with resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("error"):
                raise RuntimeError(obj["error"])
            piece = (obj.get("message") or {}).get("content") or ""
            # Models that ignore think=false still wrap reasoning in tags.
            if "<think>" in piece:
                in_think = True
                piece = piece.split("<think>", 1)[0]
            if in_think:
                if "</think>" in piece:
                    in_think = False
                    piece = piece.split("</think>", 1)[1]
                else:
                    continue
            if piece:
                yield piece
            if obj.get("done"):
                break


def ollama_warm(model: str) -> None:
    """Load a model into memory so the first on-stage request is not the slowest."""
    try:
        http_json(f"{OLLAMA}/api/generate", {"model": model, "prompt": "", "keep_alive": "30m"},
                  timeout=240)
    except Exception:
        pass


# --------------------------------------------------------------------------
# NemoClaw
# --------------------------------------------------------------------------
def detect_gateway_port() -> str:
    """The OpenShell gateway port NemoClaw uses (8080 by default).

    NemoClaw records each gateway under a port-named directory. Probing ports
    alone is unsafe: it happily finds an unrelated service on 8080.
    """
    env = os.environ.get("NEMOCLAW_GATEWAY_PORT")
    if env:
        return env
    sources = (
        (Path.home() / ".nemoclaw" / "gateways", ""),
        (Path.home() / ".local" / "state" / "nemoclaw", "openshell-docker-gateway-"),
    )
    for base, prefix in sources:
        if not base.is_dir():
            continue
        ports = []
        for entry in base.iterdir():
            name = entry.name[len(prefix):] if prefix else entry.name
            if name.isdigit():
                ports.append(int(name))
        if ports:
            for port in sorted(ports, reverse=True):
                with socket.socket() as s:
                    s.settimeout(0.4)
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        return str(port)
            return str(sorted(ports)[0])
    return "8080"


def nemoclaw_env() -> dict:
    env = dict(os.environ)
    env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env.get("PATH", "")
    env["NEMOCLAW_GATEWAY_PORT"] = detect_gateway_port()
    # NemoClaw's installer and gateway expect Docker's default context.
    env.setdefault("DOCKER_CONTEXT", "default")
    return env


def gateway_url() -> str:
    """Host URL of the sandbox's OpenClaw gateway.

    setup.sh records the port NemoClaw actually forwarded (from
    `nemoclaw <sandbox> dashboard-url`) in .run/gateway-url; the GATEWAY_URL
    setting is the fallback.
    """
    if os.environ.get("GATEWAY_URL"):
        return os.environ["GATEWAY_URL"].rstrip("/")
    recorded = RUN_DIR / "gateway-url"
    if recorded.exists():
        url = recorded.read_text().strip()
        if url.startswith("http"):
            return url.rstrip("/")
    return setting("GATEWAY_URL", "http://127.0.0.1:18789").rstrip("/")


def nemoclaw_available() -> bool:
    from shutil import which
    return bool(which("nemoclaw") or (Path.home() / ".local/bin/nemoclaw").exists())


# Every `nemoclaw` call takes a host-wide lock, so overlapping calls just wait
# for each other. Serialise them here instead of letting them pile up.
NEMOCLAW_LOCK = threading.Lock()


def nemoclaw(*args: str, timeout: float = 60, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    cmd = ["nemoclaw", *args]
    with NEMOCLAW_LOCK:
        return subprocess.run(cmd, capture_output=True, timeout=timeout, env=nemoclaw_env(),
                              input=input_bytes)


_token_cache: dict = {"token": None, "at": 0.0, "failed_at": 0.0}


def gateway_token(refresh: bool = False) -> str | None:
    """The sandbox agent's gateway token (Bearer auth for the OpenClaw HTTP API).

    Failures are remembered for two minutes: a wedged sandbox makes the CLI
    hang until its timeout, and the page polls health every few seconds.
    """
    override = os.environ.get("LAB3_GATEWAY_TOKEN")
    if override:
        return override
    if not refresh and _token_cache["token"]:
        return _token_cache["token"]
    cached = RUN_DIR / "gateway-token"
    if not refresh and cached.exists():
        tok = cached.read_text().strip()
        if tok:
            _token_cache.update(token=tok, at=time.time())
            return tok
    if not nemoclaw_available() or time.time() - _token_cache["failed_at"] < 120:
        return None
    try:
        p = nemoclaw(SANDBOX, "gateway-token", "--quiet", timeout=40)
    except Exception:
        _token_cache["failed_at"] = time.time()
        return None
    tok = (p.stdout or b"").decode().strip().splitlines()
    tok = tok[-1].strip() if tok else ""
    if p.returncode != 0 or not tok or " " in tok:
        _token_cache["failed_at"] = time.time()
        return None
    _token_cache.update(token=tok, at=time.time())
    try:
        RUN_DIR.mkdir(exist_ok=True)
        cached.write_text(tok + "\n")
        cached.chmod(0o600)
    except OSError:
        pass
    return tok
