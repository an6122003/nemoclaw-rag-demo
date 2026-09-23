#!/usr/bin/env python3
"""DGX Spark AI Workshop — one web app for the three hands-on labs.

    Hands-on 1  Fine-tuning Local LLMs        (lab1_finetune.py)
    Hands-on 2  Build RAG with NemoClaw       (lab2_rag.py)
    Hands-on 3  Build an Agentic Workflow     (lab3_agent.py)

Standard library HTTP server. The Hands-on 3 tools need pandas, matplotlib and
openpyxl, so start it with the workshop's Python environment:

    .venv/bin/python app/server.py --open          # what ./start.sh does
    .venv/bin/python app/server.py --lan           # let other laptops connect

Every long operation streams newline-delimited JSON, so the page shows real
progress rather than a timer.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
import lab1_finetune as lab1  # noqa: E402
import lab2_rag as lab2  # noqa: E402
import lab3_agent as lab3  # noqa: E402

HERE = Path(__file__).resolve().parent
INDEX_HTML = HERE / "index.html"
RETRIEVAL_MODE = "auto"
MAX_UPLOAD = 25 * 1024 * 1024


def _gpu_name() -> str:
    return lab1.trainer_status().get("gpu", "")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "DGXWorkshop/1.0"

    def log_message(self, fmt, *args):  # keep the terminal readable on stage
        path = self.path or ""
        if any(p in path for p in ("/api/lab1/train", "/api/lab2/ask", "/api/lab3/run")):
            sys.stderr.write(f"  {self.command} {path.split('?')[0]}\n")

    # -- responses ----------------------------------------------------------
    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _stream_start(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

    def _chunk(self, obj: dict) -> None:
        payload = (json.dumps(obj, ensure_ascii=False, default=str) + "\n").encode("utf-8")
        self.wfile.write(b"%x\r\n%s\r\n" % (len(payload), payload))
        self.wfile.flush()

    def _stream_end(self) -> None:
        try:
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except Exception:
            pass

    def _stream(self, producer) -> None:
        """Run producer(emit) and stream every event it emits."""
        self._stream_start()
        lock = threading.Lock()
        alive = {"ok": True}

        def emit(ev: dict) -> None:
            if not alive["ok"]:
                return
            with lock:
                try:
                    self._chunk(ev)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    alive["ok"] = False  # the browser went away; let the work finish quietly

        try:
            producer(emit)
        except Exception as exc:  # noqa: BLE001 - never 500 in the middle of a demo
            emit({"event": "error", "message": f"{exc.__class__.__name__}: {exc}"})
        finally:
            if alive["ok"]:
                self._stream_end()

    def _body(self, limit: int = 1_000_000) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > limit:
            raise ValueError("request too large")
        return self.rfile.read(length) if length else b""

    def _json_body(self) -> dict:
        raw = self._body()
        return json.loads(raw.decode("utf-8") or "{}") if raw else {}

    # -- GET ------------------------------------------------------------------
    def do_GET(self):  # noqa: N802
        url = urlparse(self.path)
        path, qs = url.path, parse_qs(url.query)

        if path in ("/", "/index.html"):
            if not INDEX_HTML.exists():
                return self._json(500, {"error": "index.html missing"})
            return self._send(200, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")

        if path == "/api/health":
            local = self.client_address[0] in ("127.0.0.1", "::1", "::ffff:127.0.0.1")
            return self._json(200, health(include_token=local))

        # ---- Hands-on 1
        if path == "/api/lab1/info":
            return self._json(200, lab1.info())
        if path == "/api/lab1/stream":
            start = int((qs.get("from") or ["0"])[0] or 0)
            self._stream_start()
            try:
                for ev in lab1.JOB.follow(start):
                    self._chunk(ev)
            except (BrokenPipeError, ConnectionResetError, OSError):
                return
            return self._stream_end()

        # ---- Hands-on 2
        if path == "/api/lab2/examples":
            return self._json(200, {"examples": lab2.EXAMPLES})
        if path == "/api/lab2/corpus":
            return self._json(200, {"documents": lab2.corpus_list()})
        if path == "/api/lab2/doc":
            doc = lab2.corpus_doc((qs.get("name") or [""])[0])
            return self._json(200, doc) if doc else self._json(404, {"error": "not found"})

        # ---- Hands-on 3
        if path == "/api/lab3/info":
            return self._json(200, lab3_info((qs.get("dataset") or [""])[0]))
        m = re.fullmatch(r"/api/lab3/file/([\w\-]+)/([^/]+)", path)
        if m:
            f = lab3.output_file(m.group(1), unquote(m.group(2)))
            if not f:
                return self._json(404, {"error": "not found"})
            return self._file(f)
        if path == "/api/lab3/dataset":
            f = lab3.dataset_path((qs.get("name") or [""])[0])
            return self._file(f)

        return self._json(404, {"error": "not found"})

    def _file(self, f: Path) -> None:
        ctype = {
            ".png": "image/png",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".csv": "text/csv; charset=utf-8",
            ".json": "application/json",
        }.get(f.suffix.lower(), "application/octet-stream")
        extra = {}
        if f.suffix.lower() in (".xlsx", ".csv"):
            # RFC 5987 so Vietnamese file names survive the download.
            from urllib.parse import quote
            extra["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(f.name)}"
        return self._send(200, f.read_bytes(), ctype, extra)

    # -- POST -----------------------------------------------------------------
    def do_POST(self):  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/lab3/upload":
                name = unquote(self.headers.get("X-Filename") or "upload.xlsx")
                body = self._body(MAX_UPLOAD)
                try:
                    return self._json(200, lab3.save_upload(name, body))
                except ValueError as exc:
                    return self._json(400, {"error": str(exc)})
            req = self._json_body()
        except (ValueError, json.JSONDecodeError) as exc:
            return self._json(400, {"error": f"bad request: {exc}"})

        lang = req.get("lang") if req.get("lang") in ("en", "vi") else "vi"

        # ---- Hands-on 1
        if path == "/api/lab1/train":
            epochs = _clamp(req.get("epochs"), 1, 10, 5, float)
            lr = _clamp(req.get("lr"), 1e-5, 1e-3, 2e-4, float)
            rank = int(_clamp(req.get("rank"), 4, 64, 16, int))
            if not lab1.trainer_status()["ready"]:
                return self._json(409, {"error": "trainer_not_ready",
                                        "reason": lab1.trainer_status()["reason"]})
            ok, detail = lab1.JOB.start(epochs, lr, rank)
            return self._json(200 if ok else 409, {"ok": ok, "job": detail})
        if path == "/api/lab1/cancel":
            return self._json(200, {"ok": lab1.JOB.cancel()})
        if path == "/api/lab1/compare":
            q = (req.get("question") or "").strip()
            if not q:
                return self._json(400, {"error": "empty question"})
            return self._stream(lambda emit: lab1.compare(q, emit))

        # ---- Hands-on 2
        if path == "/api/lab2/ask/stream":
            q = (req.get("question") or "").strip()
            if not q:
                return self._json(400, {"error": "empty question"})
            k = int(_clamp(req.get("k"), 1, 10, 5, int))
            return self._stream(lambda emit: lab2.ask_stream(q, lang, k, RETRIEVAL_MODE, emit))

        # ---- Hands-on 3
        if path == "/api/lab3/run":
            q = (req.get("question") or "").strip()
            if not q:
                return self._json(400, {"error": "empty question"})
            route = req.get("route") if req.get("route") in ("auto", "nemoclaw", "direct") else "auto"
            data = req.get("dataset") or None
            return self._stream(lambda emit: lab3.run_agent(q, lang, data, route, emit))

        return self._json(404, {"error": "not found"})


def _clamp(value, lo, hi, default, cast):
    try:
        v = cast(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def lab3_info(dataset: str) -> dict:
    tools_ok, tools_why = lab3.tools_available()
    ready, detail = lab3.gateway_ready()
    preview = None
    if tools_ok:
        try:
            preview = lab3.dataset_preview(lab3.dataset_path(dataset or None))
        except Exception as exc:  # noqa: BLE001
            preview = {"error": str(exc)}
    return {
        "examples": lab3.EXAMPLES,
        "tools_ok": tools_ok,
        "tools_reason": tools_why,
        "nemoclaw": {"ready": ready, "detail": detail, "agent": f"openclaw/{lab3.AGENT_ID}",
                     "gateway": common.gateway_url()},
        "chat_model": common.CHAT_MODEL,
        "dataset": preview,
        "tools": [t["function"]["name"] for t in lab3._tools().TOOL_SPECS] if tools_ok else [],
    }


def health(include_token: bool = False) -> dict:
    ollama = common.ollama_up()
    return {
        "ollama": ollama,
        "gpu": _gpu_name(),
        "chat_model": {"name": common.CHAT_MODEL, "ready": ollama and common.has_model(common.CHAT_MODEL)},
        "embed_model": {"name": common.EMBED_MODEL, "ready": ollama and common.has_model(common.EMBED_MODEL)},
        "sandbox": {"name": common.SANDBOX, "checked": lab2.SANDBOX_STATUS["checked"],
                    "ok": lab2.SANDBOX_STATUS["ok"]},
        "gateway": {"url": common.gateway_url(), "ready": lab3.gateway_ready()[0]},
        "control_ui": control_ui_url(include_token),
        "doc_count": len(list(lab2.CORPUS.glob("*.md"))),
    }


def control_ui_url(include_token: bool) -> str:
    """OpenClaw's own web UI for the sandbox agent.

    The gateway token (full operator access to the agent) goes into the link
    only for a browser on this machine; the gateway itself listens on
    loopback, so a LAN visitor could not use the link anyway.
    """
    base = common.gateway_url()
    token = common.gateway_token() if include_token else None
    return f"{base}/#token={token}" if token else base


def main() -> int:
    global RETRIEVAL_MODE
    ap = argparse.ArgumentParser(description="DGX Spark AI Workshop app")
    ap.add_argument("--port", type=int, default=int(common.setting("HUB_PORT", "8090")))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--lan", action="store_true", help="listen on all interfaces")
    ap.add_argument("--retrieval", choices=["auto", "sandbox", "local"], default="auto")
    ap.add_argument("--open", action="store_true", help="open a browser")
    ap.add_argument("--no-warmup", action="store_true")
    args = ap.parse_args()
    RETRIEVAL_MODE = args.retrieval
    host = "0.0.0.0" if args.lan else args.host

    if not args.no_warmup:
        # Load the models in the background so the first question on stage is fast.
        def warm() -> None:
            for model in (common.CHAT_MODEL, common.EMBED_MODEL, lab1.BASE_OLLAMA, lab1.TUNED):
                if common.has_model(model):
                    common.ollama_warm(model)
        threading.Thread(target=warm, daemon=True).start()
    if args.retrieval != "local":
        threading.Thread(target=lab2.probe_sandbox, daemon=True).start()

    srv = ThreadingHTTPServer((host, args.port), Handler)
    srv.daemon_threads = True
    pid_file = common.RUN_DIR / "hub.pid"
    try:
        common.RUN_DIR.mkdir(exist_ok=True)
        pid_file.write_text(f"{os.getpid()}\n")
    except OSError:
        pass
    url = f"http://127.0.0.1:{args.port}/"
    print(f"\n  DGX Spark AI Workshop — running at {url}")
    if args.lan:
        print(f"  (listening on all interfaces, port {args.port})")
    print(f"  chat model {common.CHAT_MODEL} · embeddings {common.EMBED_MODEL} · sandbox {common.SANDBOX}")
    print("  press Ctrl-C to stop\n")
    sys.stdout.flush()
    if args.open:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    def _terminate(*_):  # ./stop.sh sends SIGTERM: leave the same way as Ctrl-C
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _terminate)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")
    finally:
        pid_file.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
