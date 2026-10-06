#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Enterprise demos: AI that works the night shift on one DGX Spark.

Two jobs a business pays people (or a cloud API) to do every day, run as
real batches over realistic volumes of invented data:

  inbox     2,400 customer messages: topic, urgency, sentiment, red flags,
            order number, plus a draft reply for the critical ones
  invoices  1,000 scanned supplier invoices read into Excel, with the
            arithmetic checked and duplicates caught

Batches run on vLLM (NVIDIA's container, nvidia/Qwen3.6-35B-A3B-NVFP4),
which works on dozens of items at once. Ollama, which answers one request
at a time, can run the same job with the same model family for comparison.

Each job is its own background process, so it keeps going when the browser
closes, and appends one JSON line per item to .run/enterprise/jobs/<demo>/,
so it resumes where it stopped. Every item has an answer key, so the page
shows measured accuracy, not claimed accuracy.

    python app/enterprise.py prepare            # sample data (setup does this)
    python app/enterprise.py engine start|stop|status
    python app/enterprise.py run inbox --limit 200 [--engine ollama]
    python app/enterprise.py smoke              # setup's end-to-end check
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

ROOT = common.ROOT
GEN = ROOT / "enterprise" / "generate"
DATA = common.RUN_DIR / "enterprise"
JOBS = DATA / "jobs"
EXPORTS = DATA / "exports"
INBOX_FILE = DATA / "inbox" / "messages.jsonl"
INVOICE_DIR = DATA / "invoices"
COMPANY_TAX = "0319482765"  # Aurora Mart, the fictional buyer (enterprise/generate/common.py)

# --- the batch engine ----------------------------------------------------------
ENGINE_NAME = "workshop-batch"
ENGINE_PORT = int(common.setting("BATCH_PORT", "8100"))
ENGINE_IMAGE = common.setting("BATCH_IMAGE", "nvcr.io/nvidia/vllm:26.05.post1-py3")
ENGINE_MODEL = common.setting("BATCH_MODEL", "nvidia/Qwen3.6-35B-A3B-NVFP4")
ENGINE_REVISION = common.setting("BATCH_MODEL_REVISION", "491c2f1ea524c639598bf8fa787a93fed5a6fbce")
ENGINE_UTIL = float(common.setting("BATCH_GPU_MEMORY", "0.30") or 0.30)
HF_HOME = Path(common.setting("BATCH_HF_HOME", str(Path.home() / ".cache" / "huggingface")))
# The same model family through Ollama, one request at a time.
OLLAMA_MODEL = common.setting("BATCH_OLLAMA_MODEL", common.EXTRA_CHAT_MODEL or "qwen3.6:35b")
ENGINE_URL = f"http://127.0.0.1:{ENGINE_PORT}"
CONCURRENCY = {"inbox": 48, "invoices": 24}

DEMOS = ("inbox", "invoices")


# ============================================================ sample data ===
def dataset_ready(demo: str) -> bool:
    if demo == "inbox":
        return INBOX_FILE.exists() and INBOX_FILE.stat().st_size > 0
    return (INVOICE_DIR / "truth.json").exists()


def prepare(force: bool = False, log=print) -> bool:
    """Generate the sample data that is not there yet (about half a minute)."""
    ok = True
    py = sys.executable
    if force or not dataset_ready("inbox"):
        p = subprocess.run([py, str(GEN / "inbox.py"), "--out", str(INBOX_FILE)], capture_output=True, text=True)
        log((p.stdout or p.stderr).strip().splitlines()[0] if (p.stdout or p.stderr) else "inbox: no output")
        ok &= p.returncode == 0
    if force or not dataset_ready("invoices"):
        p = subprocess.run([py, str(GEN / "invoices.py"), "--out", str(INVOICE_DIR)], capture_output=True, text=True)
        out = (p.stdout or "").strip().splitlines()
        log(out[-1] if out else (p.stderr or "invoices: failed").strip()[-300:])
        ok &= p.returncode == 0
    _cache.clear()
    return ok


_cache: dict = {}


def _cached(key: str, path: Path, loader):
    """Reload a data file only when it changes."""
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    sig = (st.st_size, st.st_mtime)
    hit = _cache.get(key)
    if hit and hit[0] == sig:
        return hit[1]
    value = loader(path)
    _cache[key] = (sig, value)
    return value


def items(demo: str) -> list[dict]:
    if demo == "inbox":
        rows = _cached("inbox", INBOX_FILE, lambda p: [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()])
    else:
        rows = _cached("invoices", INVOICE_DIR / "truth.json", lambda p: json.loads(p.read_text(encoding="utf-8")))
    return rows or []


def item_index(demo: str) -> dict:
    rows = items(demo)
    hit = _cache.get(f"idx:{demo}")
    if hit and hit[0] is rows:
        return hit[1]
    idx = {r["id"]: r for r in rows}
    _cache[f"idx:{demo}"] = (rows, idx)
    return idx


# ================================================================ engine ===
def _docker(*args: str, timeout: float = 30) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def model_dir() -> Path:
    return HF_HOME / "hub" / f"models--{ENGINE_MODEL.replace('/', '--')}" / "snapshots" / ENGINE_REVISION


def model_ready() -> bool:
    d = model_dir()
    idx = d / "model.safetensors.index.json"
    if not (d / "config.json").exists() or not idx.exists():
        return False
    try:
        shards = set(json.loads(idx.read_text())["weight_map"].values())
    except Exception:
        return False
    return all((d / s).exists() for s in shards)


def image_ready() -> bool:
    try:
        return _docker("image", "inspect", ENGINE_IMAGE, timeout=20).returncode == 0
    except Exception:
        return False


def installed(max_age: float = 30) -> dict:
    hit = _cache.get("installed")
    if hit and time.time() - hit[0] < max_age:
        return hit[1]
    docker_ok = shutil.which("docker") is not None
    out = {"docker": docker_ok, "image": docker_ok and image_ready(), "model": model_ready(),
           "image_name": ENGINE_IMAGE, "model_name": ENGINE_MODEL}
    _cache["installed"] = (time.time(), out)
    return out


def _container_state() -> str:
    """'running', 'exited', or '' when there is no engine container."""
    try:
        p = _docker("inspect", "-f", "{{.State.Status}}", ENGINE_NAME, timeout=15)
    except Exception:
        return ""
    return p.stdout.strip() if p.returncode == 0 else ""


def engine_ready(timeout: float = 3) -> bool:
    try:
        with urllib.request.urlopen(f"{ENGINE_URL}/v1/models", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


_PHASES = [  # (log text, phase) in the order vLLM prints them
    ("Starting to load model", "loading"), ("Loading weights took", "compiling"),
    ("torch.compile took", "warming"), ("init engine", "warming"), ("Application startup complete", "ready"),
]


def engine_status() -> dict:
    state = _container_state()
    out = {"container": state or "none", "ready": False, "phase": "off", "url": ENGINE_URL}
    if state != "running":
        if state == "exited":
            out["phase"] = "failed"
            out["log"] = engine_log_tail(6)
        return out
    if engine_ready():
        out.update(ready=True, phase="ready")
        return out
    out["phase"] = "starting"
    tail = engine_log_tail(200)
    for needle, phase in _PHASES:
        if needle in tail:
            out["phase"] = phase
    m = re.findall(r"Loading safetensors checkpoint shards:\s+(\d+)%", tail)
    if m and out["phase"] == "loading":
        out["percent"] = int(m[-1])
    started = _read_json(DATA / "engine.json").get("started")
    if started:
        out["seconds"] = int(time.time() - started)
    return out


def engine_log_tail(lines: int = 20) -> str:
    try:
        p = _docker("logs", "--tail", str(lines), ENGINE_NAME, timeout=15)
        return (p.stdout + p.stderr)[-6000:]
    except Exception:
        return ""


def mem_available_gb() -> float:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024 / 1024
    except OSError:
        pass
    return 0.0


def mem_total_gb() -> float:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / 1024 / 1024
    except OSError:
        pass
    return 0.0


def unload_ollama() -> list[str]:
    """Free memory for the engine: Ollama reloads a model on the next request."""
    freed = []
    try:
        loaded = common.http_json(f"{common.OLLAMA}/api/ps", timeout=5).get("models", [])
    except Exception:
        return freed
    for m in loaded:
        name = m.get("name") or m.get("model")
        try:
            common.http_json(f"{common.OLLAMA}/api/generate", {"model": name, "keep_alive": 0}, timeout=60)
            freed.append(name)
        except Exception:
            pass
    return freed


def engine_start() -> tuple[bool, str]:
    if engine_ready():
        return True, "ready"
    state = _container_state()
    if state == "running":
        return True, "starting"
    inst = installed(max_age=0)
    if not inst["docker"]:
        return False, "docker_missing"
    if not inst["image"] or not inst["model"]:
        return False, "not_installed"
    if state:
        _docker("rm", "-f", ENGINE_NAME, timeout=60)
    unload_ollama()
    need = ENGINE_UTIL * mem_total_gb() + 4
    for _ in range(10):  # Ollama takes a few seconds to hand memory back
        if mem_available_gb() >= need:
            break
        time.sleep(1.5)
    if mem_available_gb() < need:
        return False, f"low_memory:{mem_available_gb():.0f}:{need:.0f}"
    cmd = ["run", "-d", "--name", ENGINE_NAME, "--gpus", "all", "--ipc=host",
           "--label", "workshop=batch-engine",
           "-v", f"{HF_HOME}:/root/.cache/huggingface:ro",
           # torch.compile results: the second start skips about a minute of compiling
           "-v", "workshop-vllm-cache:/root/.cache/vllm",
           "-e", "HF_HOME=/root/.cache/huggingface", "-e", "HF_HUB_OFFLINE=1", "-e", "TRANSFORMERS_OFFLINE=1",
           "-e", "VLLM_NO_USAGE_STATS=1", "-e", "DO_NOT_TRACK=1",
           "-p", f"127.0.0.1:{ENGINE_PORT}:8000", "--entrypoint", "vllm", ENGINE_IMAGE,
           "serve", ENGINE_MODEL, "--revision", ENGINE_REVISION, "--served-model-name", "batch",
           "--host", "0.0.0.0", "--port", "8000", "--max-model-len", "16384",
           "--gpu-memory-utilization", f"{ENGINE_UTIL:.2f}", "--quantization", "modelopt",
           "--kv-cache-dtype", "fp8", "--attention-backend", "flashinfer", "--moe-backend", "marlin",
           "--max-num-seqs", "64", "--max-num-batched-tokens", "16384", "--enable-chunked-prefill",
           "--enable-prefix-caching", "--async-scheduling", "--reasoning-parser", "qwen3",
           "--limit-mm-per-prompt", '{"image": 1, "video": 0}']
    p = _docker(*cmd, timeout=120)
    if p.returncode != 0:
        return False, (p.stderr or p.stdout).strip()[-400:]
    _write_json(DATA / "engine.json", {"started": time.time()})
    return True, "starting"


def engine_stop() -> bool:
    if not _container_state():
        return True
    p = _docker("rm", "-f", ENGINE_NAME, timeout=90)
    return p.returncode == 0


def engine_wait(timeout: float = 900, on_phase=None) -> bool:
    t0, last = time.time(), None
    while time.time() - t0 < timeout:
        st = engine_status()
        if st["ready"]:
            return True
        if st["container"] != "running":
            return False
        if on_phase and st["phase"] != last:
            on_phase(st)
            last = st["phase"]
        time.sleep(3)
    return False


# =========================================================== model calls ===
def _post(url: str, payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ask(engine: str, system: str, user: str, schema: dict | None, max_tokens: int,
        image: bytes | None = None, timeout: float = 600) -> tuple[str, dict]:
    """One chat request, thinking off, temperature 0. Returns (text, usage)."""
    if engine == "vllm":
        content: list | str = user
        if image is not None:
            content = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(image).decode()}},
                       {"type": "text", "text": user}]
        payload = {"model": "batch", "temperature": 0, "max_tokens": max_tokens,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
                   "chat_template_kwargs": {"enable_thinking": False}}
        if schema:
            payload["response_format"] = {"type": "json_schema", "json_schema": {"name": "result", "schema": schema}}
        r = _post(f"{ENGINE_URL}/v1/chat/completions", payload, timeout)
        u = r.get("usage") or {}
        return (r["choices"][0]["message"].get("content") or ""), {"in": u.get("prompt_tokens", 0), "out": u.get("completion_tokens", 0)}
    msg = {"role": "user", "content": user}
    if image is not None:
        msg["images"] = [base64.b64encode(image).decode()]
    payload = {"model": OLLAMA_MODEL, "stream": False, "think": False, "keep_alive": "30m",
               "messages": [{"role": "system", "content": system}, msg],
               "options": {"temperature": 0, "num_predict": max_tokens}}
    if schema:
        payload["format"] = schema
    r = _post(f"{common.OLLAMA}/api/chat", payload, timeout)
    return ((r.get("message") or {}).get("content") or ""), {"in": r.get("prompt_eval_count", 0), "out": r.get("eval_count", 0)}


def _json_from(text: str) -> dict:
    text = common.strip_thinking(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else {}


# ================================================================= inbox ===
CATEGORIES = ["delivery", "defect", "wrong_item", "return_refund", "billing", "warranty", "account",
              "inquiry", "praise", "spam"]
URGENCY = ["critical", "high", "medium", "low"]
SENTIMENT = ["negative", "neutral", "positive"]
FLAGS = ["legal_threat", "safety", "security", "social_media", "churn_risk", "refund_request"]

INBOX_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "urgency": {"type": "string", "enum": URGENCY},
        "sentiment": {"type": "string", "enum": SENTIMENT},
        "flags": {"type": "array", "items": {"type": "string", "enum": FLAGS}},
        "order_id": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["category", "urgency", "sentiment", "flags", "order_id", "summary"],
}

INBOX_SYSTEM = """Bạn phân loại tin nhắn của khách hàng gửi Aurora Mart (chuỗi bán lẻ điện máy, gia dụng) theo đúng chính sách dưới đây và trả về JSON.

category (chọn đúng một):
- delivery: giao hàng chậm, chưa nhận được hàng, hỏi đơn đang ở đâu, đổi địa chỉ giao
- defect: hàng MỚI nhận bị hỏng, lỗi, móp, nứt, không chạy, nguy hiểm khi dùng
- wrong_item: giao sai sản phẩm hoặc sai màu, thiếu hàng, thiếu phụ kiện
- return_refund: muốn trả hàng, đổi sang mẫu khác, hủy đơn, chưa được hoàn tiền sau khi trả hoặc hủy
- billing: bị trừ tiền sai hoặc 2 lần, lỗi thanh toán, hóa đơn VAT, mã giảm giá
- warranty: bảo hành (hàng đã dùng lâu bị hỏng), lắp đặt, kỹ thuật viên, trung tâm bảo hành
- account: đăng nhập, OTP, mật khẩu, tài khoản bị xâm nhập, điểm thành viên, xóa tài khoản
- inquiry: hỏi giá, còn hàng, khuyến mãi, so sánh, mua sỉ, trả góp (khách chưa mua)
- praise: khen, cảm ơn
- spam: quảng cáo, lừa đảo, không liên quan đến việc mua hàng

urgency (chính sách ưu tiên):
- critical: dọa kiện hoặc khiếu nại lên cơ quan (luật sư, Hội Bảo vệ người tiêu dùng, Sở Công Thương); nguy hiểm an toàn (khói, cháy, khét, rò điện); tài khoản bị người lạ xâm nhập
- high: khách giận dữ rõ rệt (lời lẽ gay gắt, "!!!", phải nhắn nhiều lần); dọa đăng mạng xã hội; dọa không mua nữa; bị trừ tiền 2 lần; cần xử lý gấp trong hôm nay
- medium: mọi vấn đề hoặc yêu cầu khác cần nhân viên xử lý
- low: chỉ hỏi thông tin, khen ngợi, spam

sentiment: negative nếu khách phàn nàn về điều đã xảy ra; positive nếu khen; neutral nếu chỉ hỏi, yêu cầu, hoặc spam.
flags (có thể rỗng): legal_threat, safety, security, social_media, churn_risk (dọa bỏ đi, không mua nữa, hủy thẻ), refund_request (đòi hoàn tiền).
order_id: mã đơn dạng AM và 7 chữ số nếu có trong tin, nếu không có thì "".
summary: một câu tiếng Việt, tối đa 15 từ, nói việc nhân viên cần làm.
Tin nhắn có thể viết tắt, không dấu hoặc sai chính tả."""

REPLY_SYSTEM = ("Bạn là nhân viên chăm sóc khách hàng của Aurora Mart. Viết bản nháp trả lời tin nhắn khẩn cấp này "
                "bằng tiếng Việt, lịch sự, tối đa 80 từ: xin lỗi, nêu bước xử lý ngay (ví dụ ngừng dùng thiết bị nếu "
                "nguy hiểm, khóa tài khoản nếu bị xâm nhập), hẹn thời gian liên hệ lại. Không hứa bồi thường cụ thể. "
                "Chỉ viết nội dung trả lời.")

_PHONE = re.compile(r"(?<!MST )(?<!MST: )(?<![\w])(?:\+?84|0)(?:[ .\-]?\d){8,10}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def mask_pii(text: str) -> tuple[str, int]:
    """Hide phone numbers and e-mail addresses before anything is shown."""
    count = 0

    def phone(m):
        nonlocal count
        count += 1
        d = re.sub(r"\D", "", m.group())
        return d[:3] + "•" * max(3, len(d) - 5) + d[-2:]

    def email(m):
        nonlocal count
        count += 1
        user, _, dom = m.group().partition("@")
        return user[:1] + "•••@" + dom

    return _EMAIL.sub(email, _PHONE.sub(phone, text)), count


def process_inbox(engine: str, it: dict) -> dict:
    text, usage = ask(engine, INBOX_SYSTEM, it["text"], INBOX_SCHEMA, 220)
    pred = _json_from(text)
    pred["flags"] = sorted({f for f in pred.get("flags") or [] if f in FLAGS})
    oid = re.search(r"AM\d{7}", str(pred.get("order_id") or ""))
    pred["order_id"] = oid.group(0) if oid else ""
    out = {"pred": pred, "tokens_in": usage["in"], "tokens_out": usage["out"]}
    if pred.get("urgency") == "critical":
        reply, u2 = ask(engine, REPLY_SYSTEM, it["text"], None, 260)
        out["reply"] = common.strip_thinking(reply).strip()
        out["tokens_in"] += u2["in"]
        out["tokens_out"] += u2["out"]
    return out


def score_inbox(res: dict, truth: dict) -> dict:
    p = res.get("pred") or {}
    return {"category": p.get("category") == truth["category"],
            "urgency": p.get("urgency") == truth["urgency"],
            "sentiment": p.get("sentiment") == truth["sentiment"],
            "order": (p.get("order_id") or "") == (truth.get("order_id") or "")}


# ============================================================== invoices ===
INVOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "seller_name": {"type": "string"},
        "seller_tax_code": {"type": "string"},
        "invoice_series": {"type": "string"},
        "invoice_number": {"type": "string"},
        "invoice_date": {"type": "string"},
        "buyer_tax_code": {"type": "string"},
        "items": {"type": "array", "items": {"type": "object", "properties": {
            "description": {"type": "string"}, "unit": {"type": "string"}, "quantity": {"type": "number"},
            "unit_price": {"type": "integer"}, "amount": {"type": "integer"}},
            "required": ["description", "unit", "quantity", "unit_price", "amount"]}},
        "subtotal": {"type": "integer"},
        "vat_rate": {"type": "integer"},
        "vat_amount": {"type": "integer"},
        "total": {"type": "integer"},
    },
    "required": ["seller_name", "seller_tax_code", "invoice_series", "invoice_number", "invoice_date",
                 "buyer_tax_code", "items", "subtotal", "vat_rate", "vat_amount", "total"],
}

INVOICE_SYSTEM = """Bạn đọc ảnh hóa đơn giá trị gia tăng (VAT) Việt Nam và trích xuất dữ liệu cho phòng kế toán theo lược đồ JSON.
- invoice_series là "Ký hiệu": chuỗi có chữ, dạng 1C26TAB. invoice_number là "Số": chỉ gồm 8 chữ số, ví dụ 00001234.
- seller_* là bên bán (đầu hóa đơn). buyer_tax_code là mã số thuế của người mua.
- Số tiền là số nguyên VND: dấu chấm là dấu phân cách hàng nghìn (5.598.000 = 5598000).
- invoice_date theo dạng YYYY-MM-DD. vat_rate là số phần trăm (8 hoặc 10).
- Chép đúng như in trên hóa đơn, kể cả khi các con số không khớp nhau. Không tự tính lại."""

INVOICE_USER = "Trích xuất hóa đơn trong ảnh."


def _money(v) -> int:
    if isinstance(v, (int, float)):
        return int(round(v))
    s = re.sub(r"[^\d-]", "", str(v or ""))
    try:
        return int(s) if s not in ("", "-") else 0
    except ValueError:
        return 0


def _date(s: str) -> str:
    s = str(s or "").strip()
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})\D+(\d{1,2})\D+(\d{4})", s)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return s


def normalize_invoice(x: dict) -> dict:
    series = re.sub(r"\s", "", str(x.get("invoice_series") or "")).upper()
    number = re.sub(r"\D", "", str(x.get("invoice_number") or "")) or str(x.get("invoice_number") or "")
    # Ký hiệu and Số sit on one line in some templates and get swapped: Số is all digits.
    if series.isdigit() and not str(x.get("invoice_number") or "").strip().isdigit():
        series, number = re.sub(r"\s", "", str(x.get("invoice_number"))).upper(), series
    lines = []
    for ln in x.get("items") or []:
        try:
            qty = float(ln.get("quantity") or 0)
        except (TypeError, ValueError):
            qty = 0.0
        lines.append({"desc": str(ln.get("description") or "").strip(), "unit": str(ln.get("unit") or "").strip(),
                      "qty": int(qty) if qty == int(qty) else qty, "price": _money(ln.get("unit_price")),
                      "amount": _money(ln.get("amount"))})
    return {"seller_name": str(x.get("seller_name") or "").strip(),
            "seller_tax_code": re.sub(r"\D", "", str(x.get("seller_tax_code") or "")),
            "series": series, "number": number.zfill(8) if number.isdigit() else number,
            "date": _date(x.get("invoice_date")),
            "buyer_tax_code": re.sub(r"\D", "", str(x.get("buyer_tax_code") or "")),
            "items": lines, "subtotal": _money(x.get("subtotal")), "vat_rate": _money(x.get("vat_rate")),
            "vat": _money(x.get("vat_amount")), "total": _money(x.get("total"))}


def check_invoice(x: dict) -> list[str]:
    """The checks an accountant does by hand. Duplicates are found across the batch (summaries)."""
    issues = []
    if any(abs(ln["qty"] * ln["price"] - ln["amount"]) > 1 for ln in x["items"]):
        issues.append("line_mismatch")
    if x["items"] and abs(sum(ln["amount"] for ln in x["items"]) - x["subtotal"]) > 1:
        issues.append("sum_mismatch")
    if x["vat_rate"] not in (0, 5, 8, 10):
        issues.append("vat_rate")
    elif abs(round(x["subtotal"] * x["vat_rate"] / 100) - x["vat"]) > 1:
        issues.append("vat_mismatch")
    if abs(x["subtotal"] + x["vat"] - x["total"]) > 1:
        issues.append("total_mismatch")
    if x["buyer_tax_code"] and x["buyer_tax_code"] != COMPANY_TAX:
        issues.append("wrong_buyer")
    return issues


def process_invoice(engine: str, it: dict) -> dict:
    img = (INVOICE_DIR / it["file"]).read_bytes()
    text, usage = ask(engine, INVOICE_SYSTEM, INVOICE_USER, INVOICE_SCHEMA, 1400, image=img)
    x = normalize_invoice(_json_from(text))
    return {"pred": x, "checks": check_invoice(x), "tokens_in": usage["in"], "tokens_out": usage["out"]}


def score_invoice(res: dict, truth: dict) -> dict:
    p = res.get("pred") or {}
    num = lambda s: int(s) if str(s).isdigit() else -1  # noqa: E731
    return {"tax_code": p.get("seller_tax_code") == truth["seller_tax_code"],
            "series": p.get("series") == truth["series"],
            "number": num(p.get("number")) == num(truth["number"]),
            "date": p.get("date") == truth["date"],
            "subtotal": p.get("subtotal") == truth["subtotal"],
            "vat": p.get("vat") == truth["vat"],
            "total": p.get("total") == truth["total"],
            "lines": len(p.get("items") or []) == len(truth["items"])}


PROCESS = {"inbox": process_inbox, "invoices": process_invoice}


# =============================================================== the job ===
def job_dir(demo: str) -> Path:
    return JOBS / demo


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False))
    tmp.replace(path)


def results(demo: str) -> list[dict]:
    rows = _cached(f"res:{demo}", job_dir(demo) / "results.jsonl",
                   lambda p: [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()])
    return rows or []


class PowerMeter(threading.Thread):
    """GPU power from nvidia-smi once a second, integrated into watt-hours."""

    def __init__(self):
        super().__init__(daemon=True)
        self.wh = 0.0
        self.watts = None
        self.samples = 0
        self._stop = threading.Event()

    def read(self) -> float | None:
        try:
            p = subprocess.run(["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=5)
            return float(p.stdout.strip().splitlines()[0])
        except Exception:
            return None

    def run(self) -> None:
        last = time.time()
        while not self._stop.is_set():
            w = self.read()
            now = time.time()
            if w is not None:
                self.watts = w
                self.wh += w * (now - last) / 3600
                self.samples += 1
            last = now
            self._stop.wait(1.0)

    def stop(self) -> None:
        self._stop.set()


def gpu_power() -> float | None:
    hit = _cache.get("power")
    if hit and time.time() - hit[0] < 2:
        return hit[1]
    w = PowerMeter().read()
    _cache["power"] = (time.time(), w)
    return w


def worker(demo: str, limit: int, engine: str) -> int:
    """The background process: work through the next `limit` items."""
    jd = job_dir(demo)
    jd.mkdir(parents=True, exist_ok=True)
    (jd / "stop").unlink(missing_ok=True)
    state_file = jd / "state.json"
    state = _read_json(state_file)
    totals = state.get("totals") or {"wh": 0.0, "busy_s": 0.0, "tokens_in": 0, "tokens_out": 0, "items": 0}
    run = {"started": time.time(), "engine": engine, "target": 0, "done": 0, "errors": 0, "ended": None,
           "concurrency": CONCURRENCY[demo] if engine == "vllm" else 1}
    lock = threading.Lock()
    meter = PowerMeter()

    def save(status: str, message: str = "") -> None:
        with lock:
            now = time.time()
            elapsed = now - run["started"]
            _write_json(state_file, {"status": status, "pid": os.getpid(), "message": message, "run": run,
                                     "totals": {**totals, "wh": round(totals["wh"] + meter.wh, 3),
                                                "busy_s": round(totals["busy_s"] + elapsed, 1)},
                                     "power_w": meter.watts, "updated": now})

    if not dataset_ready(demo):
        save("preparing", "sample_data")
        prepare(log=lambda m: None)
    done = {r["id"] for r in results(demo)}
    todo = [it for it in items(demo) if it["id"] not in done][:max(0, limit)]
    run["target"] = len(todo)
    if not todo:
        save("idle", "nothing_left")
        return 0

    if engine == "vllm" and not engine_ready():
        save("engine", "starting")
        ok, why = engine_start()
        if not ok:
            save("error", f"engine:{why}")
            return 1
        if not engine_wait(on_phase=lambda st: save("engine", st.get("phase", "starting"))):
            save("error", "engine:failed_to_start")
            return 1
    run["started"] = time.time()  # throughput counts from the first item, not the engine start
    meter.start()
    save("running")

    out = (jd / "results.jsonl").open("a", encoding="utf-8")
    queue = list(reversed(todo))
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(flag=True))

    def loop() -> None:
        while not stop["flag"]:
            if (jd / "stop").exists():
                stop["flag"] = True
                break
            with lock:
                if not queue:
                    return
                it = queue.pop()
            t0 = time.time()
            try:
                res = PROCESS[demo](engine, it)
            except Exception as exc:  # noqa: BLE001 - one bad item must not stop the night shift
                res = {"error": f"{exc.__class__.__name__}: {exc}"[:300]}
            res.update(id=it["id"], seconds=round(time.time() - t0, 2), at=round(time.time(), 2), engine=engine)
            with lock:
                out.write(json.dumps(res, ensure_ascii=False) + "\n")
                out.flush()
                run["done"] += 1
                run["errors"] += 1 if "error" in res else 0
                totals["items"] += 1
                totals["tokens_in"] += res.get("tokens_in", 0)
                totals["tokens_out"] += res.get("tokens_out", 0)

    threads = [threading.Thread(target=loop, daemon=True) for _ in range(run["concurrency"])]
    for t in threads:
        t.start()
    while any(t.is_alive() for t in threads):
        save("stopping" if stop["flag"] else "running")
        time.sleep(1)
    out.close()
    meter.stop()
    run["ended"] = time.time()
    save("idle", "stopped" if stop["flag"] else "finished")
    return 0


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:  # a reused pid belongs to something else
        return "enterprise.py" in Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="ignore")
    except OSError:
        return True


def job_state(demo: str) -> dict:
    st = _read_json(job_dir(demo) / "state.json")
    if st.get("status") in ("running", "stopping", "engine", "preparing") and not _pid_alive(int(st.get("pid") or 0)):
        st["status"] = "idle"
        st["message"] = "interrupted"
    return st


def any_running() -> bool:
    return any(job_state(d).get("status") in ("running", "stopping", "engine", "preparing") for d in DEMOS)


def start_job(demo: str, limit: int, engine: str) -> tuple[bool, str]:
    if demo not in DEMOS:
        return False, "unknown_demo"
    if job_state(demo).get("status") in ("running", "stopping", "engine", "preparing"):
        return False, "already_running"
    if engine == "vllm" and not (installed(max_age=0)["image"] and model_ready()):
        return False, "engine_not_installed"
    jd = job_dir(demo)
    jd.mkdir(parents=True, exist_ok=True)
    log = (jd / "worker.log").open("a")
    p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run", demo, "--limit", str(limit),
                          "--engine", engine], cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    st = _read_json(jd / "state.json")
    st.update(status="preparing", pid=p.pid, message="", updated=time.time())
    _write_json(jd / "state.json", st)
    return True, "started"


def stop_job(demo: str) -> bool:
    jd = job_dir(demo)
    if jd.exists():
        (jd / "stop").touch()
    return True


def reset_job(demo: str) -> tuple[bool, str]:
    if job_state(demo).get("status") in ("running", "stopping", "engine", "preparing"):
        return False, "running"
    for name in ("results.jsonl", "state.json", "stop", "worker.log"):
        (job_dir(demo) / name).unlink(missing_ok=True)
    _cache.pop(f"res:{demo}", None)
    return True, "reset"


# ============================================================= summaries ===
def _duplicates(rows: list[dict]) -> dict[str, str]:
    """Invoice id -> id of the earlier invoice with the same seller, series and number."""
    first: dict[tuple, str] = {}
    dup: dict[str, str] = {}
    for r in sorted((r for r in rows if r.get("pred")), key=lambda r: r["id"]):
        p = r["pred"]
        key = (p.get("seller_tax_code"), p.get("series"), p.get("number"))
        if not all(key):
            continue
        if key in first:
            dup[r["id"]] = first[key]
        else:
            first[key] = r["id"]
    return dup


def summary(demo: str) -> dict:
    rows = results(demo)
    idx = item_index(demo)
    st = job_state(demo)
    run = st.get("run") or {}
    out = {"demo": demo, "ready": dataset_ready(demo), "total": len(idx), "processed": len(rows),
           "errors": sum(1 for r in rows if "error" in r), "status": st.get("status", "idle"),
           "message": st.get("message", ""), "run": run, "totals": st.get("totals") or {},
           "power_w": st.get("power_w") if st.get("status") == "running" else None}
    elapsed = (run.get("ended") or time.time()) - run["started"] if run.get("started") else 0
    if run.get("done") and elapsed > 0:
        out["rate_per_min"] = round(run["done"] / elapsed * 60, 1)
        left = run.get("target", 0) - run.get("done", 0)
        out["eta_s"] = round(left / (run["done"] / elapsed)) if st.get("status") == "running" else None
    good = [r for r in rows if "pred" in r and r["id"] in idx]
    if demo == "inbox":
        fields = Counter()
        crit_true = crit_hit = 0
        conf = Counter()
        for r in good:
            truth = idx[r["id"]]["truth"]
            sc = score_inbox(r, truth)
            fields.update(k for k, v in sc.items() if v)
            if truth["urgency"] == "critical":
                crit_true += 1
                crit_hit += r["pred"].get("urgency") == "critical"
            if not sc["category"]:
                conf[(truth["category"], r["pred"].get("category"))] += 1
        n = len(good) or 1
        out["accuracy"] = {k: round(fields[k] / n * 100, 1) for k in ("category", "urgency", "sentiment", "order")}
        out["critical"] = {"found": crit_hit, "of": crit_true}
        out["by_urgency"] = dict(Counter(r["pred"].get("urgency") for r in good))
        out["by_category"] = dict(Counter(r["pred"].get("category") for r in good))
        out["confusions"] = [{"truth": a, "pred": b, "n": c} for (a, b), c in conf.most_common(4)]
        out["pii"] = sum(mask_pii(idx[r["id"]]["text"])[1] for r in good[-400:]) if good else 0
    else:
        dups = _duplicates(good)
        fields = Counter()
        planted = caught = false_alarm = 0
        for r in good:
            truth = idx[r["id"]]
            fields.update(k for k, v in score_invoice(r, truth).items() if v)
            flagged = bool(r.get("checks")) or r["id"] in dups
            if truth["issues"]:
                planted += 1
                caught += flagged
            elif flagged:
                false_alarm += 1
        n = len(good) or 1
        out["accuracy"] = {k: round(fields[k] / n * 100, 1)
                           for k in ("tax_code", "series", "number", "date", "subtotal", "vat", "total", "lines")}
        out["problems"] = {"planted": planted, "caught": caught, "false_alarms": false_alarm,
                           "flagged": sum(1 for r in good if r.get("checks") or r["id"] in dups),
                           "duplicates": len(dups)}
        out["value"] = sum((r["pred"].get("total") or 0) for r in good)
    return out


def summaries() -> dict:
    st = engine_status()
    return {"demos": {d: summary(d) for d in DEMOS}, "engine": st, "installed": installed(),
            "power_w": gpu_power(), "memory": {"available_gb": round(mem_available_gb(), 1),
                                                "total_gb": round(mem_total_gb(), 1)},
            "ollama_model": OLLAMA_MODEL, "ollama_ready": common.has_model(OLLAMA_MODEL),
            "engine_model": ENGINE_MODEL}


def feed(demo: str, limit: int = 40, only: str = "all") -> list[dict]:
    """The latest results with what the page needs to show them."""
    rows = results(demo)
    idx = item_index(demo)
    dups = _duplicates([r for r in rows if r.get("pred")]) if demo == "invoices" else {}
    out = []
    for r in reversed(rows):
        it = idx.get(r["id"])
        if not it:
            continue
        if demo == "inbox":
            p = r.get("pred") or {}
            if only == "review" and p.get("urgency") not in ("critical", "high"):
                continue
            text, _ = mask_pii(it["text"])
            sc = score_inbox(r, it["truth"]) if p else {}
            out.append({"id": r["id"], "channel": it["channel"], "text": text, "pred": p, "truth": it["truth"],
                        "ok": sc, "reply": r.get("reply"), "error": r.get("error"), "seconds": r.get("seconds")})
        else:
            p = r.get("pred") or {}
            checks = list(r.get("checks") or []) + (["duplicate"] if r["id"] in dups else [])
            if only == "review" and not checks:
                continue
            truth = {k: it[k] for k in ("seller_tax_code", "series", "number", "date", "subtotal", "vat", "total")}
            out.append({"id": r["id"], "file": it["file"], "pred": p, "checks": checks, "truth": truth,
                        "duplicate_of": dups.get(r["id"]), "planted": it["issues"],
                        "ok": score_invoice(r, it) if p else {}, "error": r.get("error"), "seconds": r.get("seconds")})
        if len(out) >= limit:
            break
    return out


def sample_items(demo: str, n: int = 6) -> list[dict]:
    """A peek at the unprocessed data, so the page shows what goes in."""
    rows = items(demo)[:n]
    if demo == "inbox":
        return [{"id": r["id"], "channel": r["channel"], "text": mask_pii(r["text"])[0]} for r in rows]
    return [{"id": r["id"], "file": r["file"], "seller": r["seller_name"]} for r in rows]


def invoice_image(name: str) -> Path | None:
    if not re.fullmatch(r"inv-\d{4,6}\.jpg", name or ""):
        return None
    f = INVOICE_DIR / name
    return f if f.is_file() else None


# ================================================================ export ===
def export_xlsx(demo: str) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    head = Font(bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="1F3A68")
    money = "#,##0"
    rows = results(demo)
    idx = item_index(demo)

    def sheet(ws, header: list[str], widths: list[int]) -> None:
        ws.append(header)
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[ws.cell(1, i).column_letter].width = w
            ws.cell(1, i).font = head
            ws.cell(1, i).fill = fill
        ws.freeze_panes = "A2"

    if demo == "inbox":
        ws = wb.active
        ws.title = "Tin nhắn"
        sheet(ws, ["Mã tin", "Kênh", "Chủ đề", "Ưu tiên", "Cảm xúc", "Cờ cảnh báo", "Mã đơn", "Việc cần làm",
                   "Nội dung (đã che SĐT/email)", "Đáp án: chủ đề", "Đáp án: ưu tiên"],
              [11, 10, 15, 10, 10, 26, 12, 42, 70, 15, 12])
        urgent = wb.create_sheet("Cần xử lý gấp")
        sheet(urgent, ["Mã tin", "Ưu tiên", "Cờ cảnh báo", "Việc cần làm", "Nội dung", "Bản nháp trả lời"],
              [11, 10, 26, 42, 70, 70])
        order = {u: i for i, u in enumerate(URGENCY)}
        for r in sorted((r for r in rows if r.get("pred")), key=lambda r: r["id"]):
            it, p = idx.get(r["id"]), r["pred"]
            if not it:
                continue
            text = mask_pii(it["text"])[0]
            ws.append([r["id"], it["channel"], p.get("category"), p.get("urgency"), p.get("sentiment"),
                       ", ".join(p.get("flags") or []), p.get("order_id"), p.get("summary"), text,
                       it["truth"]["category"], it["truth"]["urgency"]])
        for r in sorted((r for r in rows if (r.get("pred") or {}).get("urgency") in ("critical", "high")),
                        key=lambda r: (order.get(r["pred"]["urgency"], 9), r["id"])):
            it, p = idx.get(r["id"]), r["pred"]
            if it:
                urgent.append([r["id"], p["urgency"], ", ".join(p.get("flags") or []), p.get("summary"),
                               mask_pii(it["text"])[0], r.get("reply") or ""])
        for w in (ws, urgent):
            for row in w.iter_rows(min_row=2):
                for c in row:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
    else:
        dups = _duplicates([r for r in rows if r.get("pred")])
        ws = wb.active
        ws.title = "Hóa đơn"
        sheet(ws, ["Tệp", "Đơn vị bán", "MST bên bán", "Ký hiệu", "Số", "Ngày", "Tiền hàng", "Thuế suất %",
                   "Tiền thuế", "Tổng thanh toán", "Trạng thái", "Lỗi phát hiện"],
              [14, 46, 14, 11, 11, 12, 15, 11, 14, 16, 14, 34])
        lines = wb.create_sheet("Chi tiết hàng")
        sheet(lines, ["Tệp", "Số hóa đơn", "Mô tả", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền"],
              [14, 11, 46, 10, 10, 14, 16])
        review = wb.create_sheet("Cần kiểm tra")
        sheet(review, ["Tệp", "Đơn vị bán", "Số", "Tổng thanh toán", "Lỗi phát hiện"], [14, 46, 11, 16, 50])
        for r in sorted((r for r in rows if r.get("pred")), key=lambda r: r["id"]):
            it, p = idx.get(r["id"]), r["pred"]
            if not it:
                continue
            checks = list(r.get("checks") or []) + ([f"duplicate:{dups[r['id']]}"] if r["id"] in dups else [])
            ws.append([it["file"], p["seller_name"], p["seller_tax_code"], p["series"], p["number"], p["date"],
                       p["subtotal"], p["vat_rate"], p["vat"], p["total"], "Cần kiểm tra" if checks else "Hợp lệ",
                       ", ".join(checks)])
            for ln in p["items"]:
                lines.append([it["file"], p["number"], ln["desc"], ln["unit"], ln["qty"], ln["price"], ln["amount"]])
            if checks:
                review.append([it["file"], p["seller_name"], p["number"], p["total"], ", ".join(checks)])
        for w, cols in ((ws, (7, 9, 10)), (lines, (6, 7)), (review, (4,))):
            for row in w.iter_rows(min_row=2):
                for c in cols:
                    row[c - 1].number_format = money
    EXPORTS.mkdir(parents=True, exist_ok=True)
    name = {"inbox": "Aurora-Mart_hop-thu-da-phan-loai", "invoices": "Aurora-Mart_hoa-don"}[demo]
    path = EXPORTS / f"{name}_{time.strftime('%Y%m%d-%H%M')}.xlsx"
    wb.save(path)
    return path


# ============================================================ idle reaper ===
def reap_idle_engine(idle_minutes: float = 20) -> None:
    """Called periodically by the app: hand the memory back to the labs."""
    if _container_state() != "running" or any_running():
        return
    last = max([_read_json(DATA / "engine.json").get("started") or 0] +
               [((job_state(d).get("run") or {}).get("ended") or 0) for d in DEMOS] +
               [_read_json(DATA / "engine.json").get("touched") or 0])
    if time.time() - last > idle_minutes * 60:
        engine_stop()


def touch_engine() -> None:
    st = _read_json(DATA / "engine.json")
    if time.time() - (st.get("touched") or 0) > 60:
        st["touched"] = time.time()
        _write_json(DATA / "engine.json", st)


# =================================================================== cli ===
def smoke(log=print) -> bool:
    """Setup's check: start the engine, run a few items of each job, stop it."""
    if not prepare(log=log):
        log("sample data: FAILED")
        return False
    ok, why = engine_start()
    if not ok:
        log(f"engine start: FAILED ({why})")
        return False
    log("engine starting (first start takes a few minutes)…")
    if not engine_wait(timeout=1200, on_phase=lambda st: log(f"  engine: {st.get('phase')}")):
        log("engine: FAILED to start\n" + engine_log_tail(30))
        engine_stop()
        return False
    good = True
    t0 = time.time()
    for demo, n in (("inbox", 6), ("invoices", 2)):
        rows = items(demo)[:n]
        for it in rows:
            try:
                res = PROCESS[demo]("vllm", it)
                truth = it["truth"] if demo == "inbox" else it
                sc = (score_inbox if demo == "inbox" else score_invoice)(res, truth)
                log(f"  {demo} {it['id']}: {sum(sc.values())}/{len(sc)} fields right")
            except Exception as exc:  # noqa: BLE001
                log(f"  {demo} {it['id']}: FAILED {exc}")
                good = False
    log(f"checked in {time.time() - t0:.0f} s")
    engine_stop()
    return good


def main() -> int:
    ap = argparse.ArgumentParser(description="Enterprise batch demos")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_prep = sub.add_parser("prepare")
    p_prep.add_argument("--force", action="store_true")
    p_eng = sub.add_parser("engine")
    p_eng.add_argument("action", choices=["start", "stop", "status", "wait"])
    p_run = sub.add_parser("run")
    p_run.add_argument("demo", choices=DEMOS)
    p_run.add_argument("--limit", type=int, default=100)
    p_run.add_argument("--engine", choices=["vllm", "ollama"], default="vllm")
    sub.add_parser("smoke")
    sub.add_parser("summary")
    args = ap.parse_args()
    if args.cmd == "prepare":
        return 0 if prepare(force=args.force) else 1
    if args.cmd == "engine":
        if args.action == "start":
            ok, why = engine_start()
            print(why)
            return 0 if ok else 1
        if args.action == "stop":
            return 0 if engine_stop() else 1
        if args.action == "wait":
            return 0 if engine_wait(on_phase=lambda st: print(st.get("phase"), flush=True)) else 1
        print(json.dumps(engine_status(), indent=1))
        return 0
    if args.cmd == "run":
        return worker(args.demo, args.limit, args.engine)
    if args.cmd == "smoke":
        return 0 if smoke() else 1
    print(json.dumps(summaries(), ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
