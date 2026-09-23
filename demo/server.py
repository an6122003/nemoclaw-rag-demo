#!/usr/bin/env python3
"""Ask Aurora Grid — a bilingual GUI demo of the NemoClaw RAG pipeline.

Built for a non-technical audience: one search box, plain-language answers, a
visible source list, a browsable document library, and a live view of the
pipeline as it runs.

It runs the real pipeline, not a mock:

    question
      -> OpenClaw memory search inside the NemoClaw sandbox   (retrieval)
      -> the retrieved passages are read out of the corpus
      -> qwen3:8b answers using ONLY those passages           (generation)

The /api/ask/stream endpoint reports each stage as it actually happens, so the
progress display reflects real work rather than a timer.

If the sandbox is unavailable the server falls back to the local vector index, so
a live demo does not die on stage.

Standard library only. No pip install, no build step.

Usage
    python3 demo/server.py                    # http://127.0.0.1:8090
    python3 demo/server.py --port 8090 --open
    python3 demo/server.py --retrieval local  # skip the sandbox entirely
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
CORPUS = LAB / "corpus"
LOCAL_INDEX = LAB / "index" / "rag_index.json"
DEMO_HTML = Path(__file__).resolve().parent / "index.html"

OLLAMA = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "qwen3:8b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "qwen3-embedding:4b")
SANDBOX = os.environ.get("NEMOCLAW_SANDBOX", "my-assistant")
def detect_gateway_port() -> str:
    """Find the OpenShell gateway port.

    A fresh install uses 8080; the authoring machine used 8814 because 8080 was
    already taken by an unrelated service. Probing ports alone is therefore
    unsafe -- it happily returns whatever else is listening. NemoClaw records
    every gateway under a port-named directory, so trust that first.
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


GATEWAY_PORT = detect_gateway_port()

QWEN3_QUERY_PREFIX = (
    "Instruct: Given a user query, retrieve relevant memory notes and documents\n"
    "Query:"
)

# Demo questions, per language. The corpus is English, so Vietnamese questions
# exercise cross-lingual retrieval: the model must find English documents and
# answer in Vietnamese. That is worth showing deliberately.
EXAMPLES: dict[str, list[dict]] = {
    "en": [
        {
            "group": "Ask a simple question",
            "items": [
                "What is the usable energy of the AX-600 battery cabinet?",
                "What coolant does the liquid-cooled cabinet use?",
                "Which port does the Comet C2 use for Modbus?",
            ],
        },
        {
            "group": "Watch it separate two similar products",
            "items": [
                "What torque do I use on the DC terminals?",
                "Which cabinet is liquid cooled, and what coolant does it take?",
            ],
        },
        {
            "group": "The important one — is the old safety advice still valid?",
            "items": [
                "How long after opening the DC disconnect must I wait before removing a module cover?",
                "Is the 5-minute DC disconnect wait still correct?",
            ],
        },
        {
            "group": "Ask something it should refuse",
            "items": [
                "What is Aurora Grid Systems' share price today?",
                "Who won the 2022 World Cup?",
            ],
        },
    ],
    "vi": [
        {
            "group": "Hỏi một câu đơn giản",
            "items": [
                "Dung lượng khả dụng của tủ pin AX-600 là bao nhiêu?",
                "Tủ được làm mát bằng chất lỏng sử dụng dung dịch gì?",
                "Bộ điều khiển Comet C2 dùng cổng nào cho Modbus?",
            ],
        },
        {
            "group": "Xem hệ thống phân biệt hai sản phẩm gần giống nhau",
            "items": [
                "Tôi phải siết đầu cực DC với lực bao nhiêu?",
                "Tủ nào được làm mát bằng chất lỏng, và dùng dung dịch gì?",
            ],
        },
        {
            "group": "Điểm quan trọng nhất — hướng dẫn an toàn cũ còn hiệu lực không?",
            "items": [
                "Sau khi ngắt cầu dao DC, phải chờ bao lâu trước khi tháo nắp module?",
                "Quy tắc chờ 5 phút khi ngắt DC còn đúng không?",
            ],
        },
        {
            "group": "Hỏi điều mà hệ thống nên từ chối trả lời",
            "items": [
                "Giá cổ phiếu của Aurora Grid Systems hôm nay là bao nhiêu?",
                "Đội nào vô địch World Cup 2022?",
            ],
        },
    ],
}

SYSTEM = {
    "en": """You are a helpful assistant for Aurora Grid Systems field engineers.

Answer the user's question using ONLY the numbered context passages provided.
The documents are in English and you must reply in ENGLISH.
Rules:
- Never use outside knowledge. If the context does not contain the answer, say plainly that the documents do not cover it.
- Be concise: two or three sentences, or a short list. No preamble.
- Name the document you used, e.g. "(AX-600 Battery Cabinet Datasheet)".
- If the context contains a SUPERSEDED or withdrawn instruction alongside a newer one, always give the CURRENT instruction and say the older one is out of date.
- NEVER state that no wait, no action or no requirement applies unless the context says so in those words. If a superseding document is present but its replacement value is not, say the value is not in the passages you were given.
- If two similar products could be confused, state which product your answer applies to.""",
    "vi": """Bạn là trợ lý hữu ích cho các kỹ sư hiện trường của Aurora Grid Systems.

Chỉ trả lời câu hỏi của người dùng dựa trên các đoạn ngữ cảnh được đánh số bên dưới.
Tài liệu bằng tiếng Anh nhưng bạn PHẢI trả lời bằng TIẾNG VIỆT.
Quy tắc:
- Không dùng kiến thức bên ngoài. Nếu ngữ cảnh không chứa câu trả lời, hãy nói rõ rằng tài liệu không đề cập đến vấn đề này.
- Trả lời ngắn gọn: hai hoặc ba câu, hoặc một danh sách ngắn. Không mở bài dài dòng.
- Nêu tên tài liệu đã dùng, ví dụ "(Bảng thông số tủ pin AX-600)".
- Nếu ngữ cảnh có một hướng dẫn đã BỊ THAY THẾ hoặc thu hồi bên cạnh hướng dẫn mới hơn, luôn đưa ra hướng dẫn HIỆN HÀNH và nói rõ hướng dẫn cũ đã hết hiệu lực.
- TUYỆT ĐỐI không được nói rằng không cần chờ, không cần làm gì, trừ khi ngữ cảnh ghi rõ như vậy. Nếu có tài liệu thay thế nhưng không nêu giá trị mới, hãy nói rằng giá trị đó không có trong các đoạn tài liệu được cung cấp.
- Nếu hai sản phẩm tương tự có thể bị nhầm lẫn, hãy nêu rõ câu trả lời áp dụng cho sản phẩm nào.
- Giữ nguyên các số liệu, đơn vị và mã linh kiện bằng tiếng Anh (ví dụ: 558 kWh, 35 N·m, AGS-FILT-6603).""",
}

_think_block = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.S | re.I)


def strip_thinking(text: str) -> str:
    """Remove qwen3's reasoning scaffolding so only the answer is shown."""
    text = _think_block.sub("", text or "")
    text = re.sub(r"</?think(?:ing)?>", "", text, flags=re.I)
    text = re.sub(r"\s*/no_think\s*$", "", text)
    text = re.sub(r"\s*/think\s*$", "", text)
    return text.strip()


def human_title(filename: str) -> str:
    stem = re.sub(r"^ags-doc-\d+-", "", filename.removesuffix(".md"))
    return stem.replace("-", " ").title()


# --------------------------------------------------------------------------
# Retrieval
# --------------------------------------------------------------------------
def run_sandbox_search(question: str, k: int) -> list[dict] | None:
    """Ask the sandbox's own memory search. None means 'could not'.

    Bounded by a short timeout and a cooldown: a wedged sandbox must not add
    tens of seconds to every question on stage. After one failure we go
    straight to the local index for a while.
    """
    global SANDBOX_COOLDOWN_UNTIL
    if time.time() < SANDBOX_COOLDOWN_UNTIL:
        return None
    cmd = [
        "nemoclaw", SANDBOX, "exec", "--",
        # TMPDIR must be set: SQLite derives its temp directory from it and
        # memory operations otherwise fail with a misleading database error.
        "env", "TMPDIR=/tmp",
        "openclaw", "memory", "search",
        "--query", question, "--max-results", str(k), "--json",
    ]
    env = dict(os.environ)
    env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env.get("PATH", "")
    env["NEMOCLAW_GATEWAY_PORT"] = GATEWAY_PORT
    env["DOCKER_CONTEXT"] = env.get("DOCKER_CONTEXT", "default")
    try:
        with _nemoclaw_lock:
            p = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=SANDBOX_TIMEOUT_SECONDS, env=env,
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        SANDBOX_COOLDOWN_UNTIL = time.time() + SANDBOX_COOLDOWN_SECONDS
        SANDBOX_STATUS.update(checked=True, ok=False)
        return None
    out = p.stdout or ""
    start = out.find("{")
    if p.returncode != 0 or start < 0:
        SANDBOX_COOLDOWN_UNTIL = time.time() + SANDBOX_COOLDOWN_SECONDS
        SANDBOX_STATUS.update(checked=True, ok=False)
        return None
    SANDBOX_STATUS.update(checked=True, ok=True)
    try:
        data = json.loads(out[start:])
    except json.JSONDecodeError:
        return None
    hits = []
    for r in data.get("results", []) or []:
        hits.append(
            {
                "path": r.get("path", ""),
                "start": int(r.get("startLine") or 0),
                "end": int(r.get("endLine") or 0),
                "score": float(r.get("score") or 0.0),
            }
        )
    return hits or None


def embed(text: str) -> list[float]:
    payload = json.dumps({"model": EMBED_MODEL, "input": [text]}).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/embed", data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        vec = json.loads(resp.read().decode())["embeddings"][0]
    n = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


_local_cache: dict | None = None

# Serialises every `nemoclaw` invocation. The CLI takes a host-wide lock, so
# overlapping calls make the later one block on the earlier one.
_nemoclaw_lock = threading.Lock()


def local_search(question: str, k: int) -> list[dict] | None:
    """Cosine search over the checked-in index. Used when the sandbox is down."""
    global _local_cache
    if _local_cache is None:
        if not LOCAL_INDEX.exists():
            return None
        _local_cache = json.loads(LOCAL_INDEX.read_text())
    chunks = _local_cache["chunks"]
    try:
        qv = embed(QWEN3_QUERY_PREFIX + question)
    except (urllib.error.URLError, OSError, TimeoutError, KeyError, json.JSONDecodeError):
        return None
    scored = sorted(
        ((sum(a * b for a, b in zip(qv, c["vector"])), i) for i, c in enumerate(chunks)),
        key=lambda t: t[0], reverse=True,
    )
    hits, per_doc = [], {}
    for score, i in scored:
        doc = chunks[i]["doc"]
        if per_doc.get(doc, 0) >= 2:
            continue
        per_doc[doc] = per_doc.get(doc, 0) + 1
        # Carry the chunk text itself. Returning only the document name made the
        # caller fall back to the document head, which silently dropped the
        # answer whenever it appeared later in the file.
        hits.append({
            "path": f"memory/{doc}", "start": 0, "end": 0, "score": score,
            "text": chunks[i].get("text", ""),
            "title": chunks[i].get("doc_title") or human_title(doc),
        })
        if len(hits) == k:
            break
    return hits or None


_corpus_lines: dict[str, list[str]] = {}


def corpus_lines(name: str) -> list[str]:
    if name not in _corpus_lines:
        f = CORPUS / name
        _corpus_lines[name] = f.read_text(encoding="utf-8").splitlines() if f.exists() else []
    return _corpus_lines[name]


def clean_markdown(text: str) -> str:
    """Strip markdown noise so passages read naturally on screen."""
    text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.M)  # bare table rows
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def passage_for(hit: dict) -> dict:
    """Resolve a hit to the exact text that was retrieved.

    Prefers the chunk text carried by the hit. Falling back to the document
    head is a last resort only -- it truncates and drops the answer.
    """
    name = hit["path"].split("/")[-1]
    lo, hi = hit["start"], hit["end"]
    if hit.get("text"):
        body = hit["text"]
    else:
        lines = corpus_lines(name)
        body = "\n".join(lines if not lo or not hi else lines[max(0, lo - 1) : hi])
    return {
        "doc": name,
        "title": hit.get("title") or human_title(name),
        "score": round(hit["score"], 3),
        "passage": clean_markdown(body)[:2200],
        "lines": f"{lo}-{hi}" if lo and hi else "",
    }


def retrieve(question: str, k: int, mode: str) -> tuple[list[dict], str]:
    if mode != "local":
        hits = run_sandbox_search(question, k)
        if hits:
            return [passage_for(h) for h in hits], "sandbox"
    hits = local_search(question, k)
    if hits:
        return [passage_for(h) for h in hits], "local-index"
    raise RuntimeError("retrieval unavailable")


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------
def generate(question: str, passages: list[dict], lang: str) -> str:
    """Answer using only the retrieved passages.

    Uses Ollama's native chat endpoint with thinking disabled. qwen3 otherwise
    spends most of its time on an internal reasoning trace we discard: measured
    5.26s with thinking versus 0.57s without, for identical answers.
    """
    context = "\n\n".join(
        f"[{i}] {p['title']}\n{p['passage']}" for i, p in enumerate(passages, 1)
    )
    prompt = f"Context passages:\n\n{context}\n\nQuestion: {question}"
    payload = json.dumps(
        {
            "model": CHAT_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM.get(lang, SYSTEM["en"])},
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": 0.1, "num_predict": 500},
            "think": False,
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat", data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode())
    msg = data.get("message") or {}
    answer = strip_thinking(msg.get("content") or "")
    if not answer:
        answer = strip_thinking(msg.get("reasoning_content") or "")
    return answer


def warm_up() -> None:
    """Load the model into memory so the first on-stage question is fast."""
    try:
        payload = json.dumps(
            {
                "model": CHAT_MODEL,
                "messages": [{"role": "user", "content": "hi"}],
                "options": {"num_predict": 1},
                "think": False,
                "stream": False,
            }
        ).encode()
        req = urllib.request.Request(
            f"{OLLAMA}/api/chat", data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180):
            pass
        print(f"  warmed up {CHAT_MODEL}")
    except Exception as exc:  # noqa: BLE001 - warm-up is best effort
        print(f"  warning: warm-up failed ({exc})")


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
RETRIEVAL_MODE = "auto"
SANDBOX_STATUS: dict = {"checked": False, "ok": False}
# Unix time until which the sandbox is skipped after a failure.
SANDBOX_COOLDOWN_UNTIL: float = 0.0
SANDBOX_TIMEOUT_SECONDS = 20
SANDBOX_COOLDOWN_SECONDS = 120


def probe_sandbox() -> None:
    """Check the sandbox once, at startup.

    Deliberately NOT called per request: `nemoclaw` serialises on a host-wide
    lock, so a health check racing a search makes the search wait.
    """
    try:
        with _nemoclaw_lock:
            rc = subprocess.run(
                ["nemoclaw", SANDBOX, "status"],
                capture_output=True, timeout=40, env=_sandbox_env(),
            ).returncode
        SANDBOX_STATUS.update(checked=True, ok=(rc == 0))
    except Exception:
        SANDBOX_STATUS.update(checked=True, ok=False)


def _sandbox_env() -> dict:
    env = dict(os.environ)
    env["PATH"] = os.path.expanduser("~/.local/bin") + ":" + env.get("PATH", "")
    env["NEMOCLAW_GATEWAY_PORT"] = GATEWAY_PORT
    env["DOCKER_CONTEXT"] = env.get("DOCKER_CONTEXT", "default")
    return env


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if "/api/ask" in (self.path or ""):
            sys.stderr.write("  ask\n")

    # -- helpers ----------------------------------------------------------
    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj).encode(), "application/json")

    # -- GET --------------------------------------------------------------
    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            if not DEMO_HTML.exists():
                return self._json(500, {"error": "index.html missing"})
            return self._send(200, DEMO_HTML.read_bytes(), "text/html; charset=utf-8")

        if path == "/api/examples":
            return self._json(200, {"examples": EXAMPLES})

        if path == "/api/health":
            relay = False
            try:
                with urllib.request.urlopen(f"{OLLAMA}/api/version", timeout=5) as r:
                    relay = r.status == 200
            except Exception:
                relay = False
            return self._json(200, {
                "relay": relay,
                "sandbox": SANDBOX_STATUS["ok"],
                "sandbox_checked": SANDBOX_STATUS["checked"],
                "sandbox_name": SANDBOX,
                "chat_model": CHAT_MODEL,
                "embed_model": EMBED_MODEL,
                "local_index": LOCAL_INDEX.exists(),
                "doc_count": len(list(CORPUS.glob("*.md"))),
            })

        if path == "/api/corpus":
            docs = []
            for f in sorted(CORPUS.glob("*.md")):
                text = f.read_text(encoding="utf-8")
                docs.append({
                    "doc": f.name,
                    "title": human_title(f.name),
                    "preview": clean_markdown(text)[:280],
                    "words": len(text.split()),
                })
            return self._json(200, {"documents": docs})

        if path == "/api/doc":
            from urllib.parse import parse_qs, urlparse
            qs = parse_qs(urlparse(self.path).query)
            name = (qs.get("name") or [""])[0]
            # Never allow traversal outside the corpus directory.
            if not name or "/" in name or "\\" in name or not name.endswith(".md"):
                return self._json(400, {"error": "bad document name"})
            f = CORPUS / name
            if not f.exists():
                return self._json(404, {"error": "not found"})
            return self._json(200, {
                "doc": name,
                "title": human_title(name),
                "text": f.read_text(encoding="utf-8"),
            })

        return self._json(404, {"error": "not found"})

    # -- POST -------------------------------------------------------------
    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/ask/stream":
            return self._stream_ask()
        if path == "/api/ask":
            return self._json_ask()
        return self._json(404, {"error": "not found"})

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    def _params(self) -> tuple[str, str, int] | None:
        try:
            req = self._read_body()
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "bad request"})
            return None
        question = (req.get("question") or "").strip()
        if not question:
            self._json(400, {"error": "empty question"})
            return None
        lang = req.get("lang") if req.get("lang") in ("en", "vi") else "en"
        return question, lang, int(req.get("k") or 5)

    def _json_ask(self):
        params = self._params()
        if not params:
            return
        question, lang, k = params
        t0 = time.time()
        try:
            passages, source = retrieve(question, k, RETRIEVAL_MODE)
        except Exception as exc:  # noqa: BLE001 - demo must not 500 on stage
            return self._json(200, {
                "answer": "", "sources": [], "error": str(exc), "source": "none",
                "seconds": round(time.time() - t0, 1),
            })
        t_retrieval = time.time()
        try:
            answer, err = generate(question, passages, lang), ""
        except Exception as exc:  # noqa: BLE001
            answer, err = "", str(exc)
        t_end = time.time()
        return self._json(200, {
            "answer": answer, "sources": passages, "source": source, "error": err,
            "seconds": round(t_end - t0, 1),
            "retrieval_seconds": round(t_retrieval - t0, 1),
            "generation_seconds": round(t_end - t_retrieval, 1),
        })

    def _stream_ask(self):
        """Stream each pipeline stage as it actually completes.

        Newline-delimited JSON over a chunked response. The browser reads this
        with a stream reader, so the progress display reflects real work rather
        than a timer.
        """
        params = self._params()
        if not params:
            return
        question, lang, k = params

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        def event(obj: dict):
            payload = (json.dumps(obj) + "\n").encode()
            self.wfile.write(b"%x\r\n%s\r\n" % (len(payload), payload))
            self.wfile.flush()

        try:
            t0 = time.time()
            event({"event": "step", "id": "search"})
            try:
                passages, source = retrieve(question, k, RETRIEVAL_MODE)
            except Exception as exc:  # noqa: BLE001
                event({"event": "error", "message": str(exc)})
                return
            t_retrieval = time.time()
            event({
                "event": "retrieved",
                "count": len(passages),
                "sources": passages,
                "source": source,
                "seconds": round(t_retrieval - t0, 1),
            })

            event({"event": "step", "id": "generate"})
            try:
                answer, err = generate(question, passages, lang), ""
            except Exception as exc:  # noqa: BLE001
                answer, err = "", str(exc)
            t_end = time.time()
            event({
                "event": "answer",
                "answer": answer,
                "sources": passages,
                "source": source,
                "error": err,
                "seconds": round(t_end - t0, 1),
                "retrieval_seconds": round(t_retrieval - t0, 1),
                "generation_seconds": round(t_end - t_retrieval, 1),
            })
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser navigated away mid-request
        finally:
            try:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except Exception:
                pass


def main() -> int:
    global RETRIEVAL_MODE
    ap = argparse.ArgumentParser(description="Ask Aurora Grid demo server")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--retrieval", choices=["auto", "sandbox", "local"], default="auto")
    ap.add_argument("--open", action="store_true", help="open a browser")
    ap.add_argument("--no-warmup", action="store_true")
    args = ap.parse_args()
    RETRIEVAL_MODE = args.retrieval

    if not CORPUS.is_dir():
        print(f"error: corpus not found at {CORPUS}", file=sys.stderr)
        return 2

    if not args.no_warmup:
        warm_up()

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"\n  Ask Aurora Grid — demo running at {url}")
    print(f"  retrieval: {RETRIEVAL_MODE}   chat model: {CHAT_MODEL}")
    print("  press ctrl-c to stop\n")
    sys.stdout.flush()
    if args.open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
