#!/usr/bin/env python3
"""Embeddings-only door from the NemoClaw sandbox to the host's Ollama.

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

    python3 embed-proxy.py --bind 172.17.0.1 --port 11434 \
        --target 127.0.0.1:11434 --model qwen3-embedding:4b

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
MAX_BODY = 32 * 1024 * 1024

TARGET = "http://127.0.0.1:11434"
MODELS: set[str] = set()


def model_allowed(name: str) -> bool:
    """Exact tag match; a bare name only matches an allowed ':latest' tag."""
    if not MODELS:
        return True
    return name in MODELS or f"{name}:latest" in MODELS


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

    def do_POST(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path not in ALLOWED_POST:
            return self._deny(f"POST {path} is not an embedding endpoint")
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._deny("request body too large")
        body = self.rfile.read(length) if length else b""
        try:
            model = str(json.loads(body or b"{}").get("model", ""))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._reply(400, b'{"error":"body is not JSON"}')
        if not model_allowed(model):
            return self._deny(f"model '{model}' is not an allowed embedding model")
        self._forward("POST", body)


def main() -> int:
    global TARGET, MODELS
    ap = argparse.ArgumentParser(description="Embeddings-only proxy to Ollama")
    ap.add_argument("--bind", required=True, help="host address the sandbox reaches")
    ap.add_argument("--port", type=int, default=11434)
    ap.add_argument("--target", default="127.0.0.1:11434", help="Ollama host:port")
    ap.add_argument("--model", action="append", default=[], help="allowed model (repeatable)")
    args = ap.parse_args()
    TARGET = args.target if args.target.startswith("http") else f"http://{args.target}"
    MODELS = set(args.model)
    srv = ThreadingHTTPServer((args.bind, args.port), Handler)
    srv.daemon_threads = True
    print(f"embed-proxy: {args.bind}:{args.port} -> {TARGET} (models: {', '.join(sorted(MODELS)) or 'any'})",
          flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
