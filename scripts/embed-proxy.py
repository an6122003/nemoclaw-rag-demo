#!/usr/bin/env python3
"""Embeddings door (plus one optional chat model) from the NemoClaw sandbox to the host's Ollama.

Why it exists
    On Linux, NemoClaw keeps Ollama bound to 127.0.0.1:11434 on purpose and
    gives the chat model a token-gated route of its own. OpenClaw's memory
    search (Hands-on 2) still needs an embedding endpoint, and a sandbox
    container cannot reach the host's loopback interface.

    This proxy listens on the host address the sandbox sees as
    host.openshell.internal and forwards ONLY embedding traffic to Ollama:

        GET  /api/version  /api/tags  /v1/models
        POST /api/embed    /api/embeddings    /v1/embeddings

    Everything else (chat, pull, delete, create, ...) is refused with 403, and
    POST bodies must name an allowed embedding model. So the sandbox gets
    exactly the capability memory search needs and nothing more - the same
    least-privilege idea as NemoClaw's network policy.

    One exception, for the workshop challenge: --chat-model lets OpenClaw's
    own chat use a second model (NemoClaw's managed route answers every
    request with the sandbox's one model). Only POST /v1/chat/completions,
    and only for that model; replies are streamed through.

    python3 embed-proxy.py --bind 172.17.0.1 --port 11434 \
        --target 127.0.0.1:11434 --model qwen3-embedding:4b --chat-model qwen3.6:35b

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ALLOWED_GET = {"/api/version", "/api/tags", "/v1/models"}
ALLOWED_POST = {"/api/embed", "/api/embeddings", "/v1/embeddings"}
CHAT_POST = "/v1/chat/completions"
MAX_BODY = 32 * 1024 * 1024

TARGET = "http://127.0.0.1:11434"
MODELS: set[str] = set()
CHAT_MODELS: set[str] = set()


def model_allowed(name: str, allowed: set[str] | None = None) -> bool:
    """Exact tag match; a bare name only matches an allowed ':latest' tag."""
    allowed = MODELS if allowed is None else allowed
    if not allowed and allowed is MODELS:
        return True
    return name in allowed or f"{name}:latest" in allowed


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("embed-proxy: " + (fmt % args) + "\n")

    def _reply(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _deny(self, why: str) -> None:
        self._reply(403, json.dumps({"error": f"blocked by workshop embed-proxy: {why}"}).encode())

    def _forward(self, method: str, body: bytes | None) -> None:
        req = urllib.request.Request(TARGET + self.path, data=body, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = resp.read()
                self._reply(resp.status, data, resp.headers.get("Content-Type", "application/json"))
        except urllib.error.HTTPError as exc:
            self._reply(exc.code, exc.read(), exc.headers.get("Content-Type", "application/json"))
        except (urllib.error.URLError, OSError) as exc:
            self._reply(502, json.dumps({"error": f"ollama unreachable: {exc}"}).encode())

    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path not in ALLOWED_GET:
            return self._deny(f"GET {path} is not an embedding endpoint")
        self._forward("GET", None)

    def _stream(self, body: bytes) -> None:
        """Forward a chat completion, passing streamed chunks on as they arrive."""
        req = urllib.request.Request(TARGET + self.path, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req, timeout=900)
        except urllib.error.HTTPError as exc:
            return self._reply(exc.code, exc.read(), exc.headers.get("Content-Type", "application/json"))
        except (urllib.error.URLError, OSError) as exc:
            return self._reply(502, json.dumps({"error": f"ollama unreachable: {exc}"}).encode())
        with resp:
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            try:
                while True:
                    chunk = resp.read1(65536)
                    if not chunk:
                        break
                    self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                    self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # the agent went away; closing resp stops Ollama

    def do_POST(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        chat = path == CHAT_POST and bool(CHAT_MODELS)
        if path not in ALLOWED_POST and not chat:
            return self._deny(f"POST {path} is not an embedding endpoint")
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._deny("request body too large")
        body = self.rfile.read(length) if length else b""
        try:
            model = str(json.loads(body or b"{}").get("model", ""))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._reply(400, b'{"error":"body is not JSON"}')
        if chat:
            if not model_allowed(model, CHAT_MODELS):
                return self._deny(f"model '{model}' is not the workshop's extra chat model")
            return self._stream(body)
        if not model_allowed(model):
            return self._deny(f"model '{model}' is not an allowed embedding model")
        self._forward("POST", body)


def main() -> int:
    global TARGET, MODELS, CHAT_MODELS
    ap = argparse.ArgumentParser(description="Embeddings proxy to Ollama (plus one optional chat model)")
    ap.add_argument("--bind", required=True, help="host address the sandbox reaches")
    ap.add_argument("--port", type=int, default=11434)
    ap.add_argument("--target", default="127.0.0.1:11434", help="Ollama host:port")
    ap.add_argument("--model", action="append", default=[], help="allowed model (repeatable)")
    ap.add_argument("--chat-model", action="append", default=[],
                    help="model OpenClaw may chat with through /v1/chat/completions (repeatable)")
    args = ap.parse_args()
    TARGET = args.target if args.target.startswith("http") else f"http://{args.target}"
    MODELS = set(args.model)
    CHAT_MODELS = {m for m in args.chat_model if m}
    srv = ThreadingHTTPServer((args.bind, args.port), Handler)
    srv.daemon_threads = True
    print(f"embed-proxy: {args.bind}:{args.port} -> {TARGET} (models: {', '.join(sorted(MODELS)) or 'any'}"
          + (f"; chat: {', '.join(sorted(CHAT_MODELS))}" if CHAT_MODELS else "") + ")", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
