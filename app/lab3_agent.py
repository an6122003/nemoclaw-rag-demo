"""Hands-on 3 — the agentic workflow: NemoClaw agent + Python tools.

    question ──▶ OpenClaw agent in the NemoClaw sandbox      (reasoning, tool choice)
                   │  tool_calls  (OpenAI function calling over the gateway)
                   ▼
                this app runs the tool in Python                (pandas / matplotlib / openpyxl)
                   │  tool results
                   └──▶ back to the agent ... until it writes the final insight

The agent is a dedicated OpenClaw agent ("analyst", minimal tool profile) that
setup.sh creates inside the sandbox. It is reached through the gateway's
OpenAI-compatible /v1/chat/completions endpoint, whose client-tool contract
hands every tool call back to us. That is what lets the UI show each step live.

If the sandbox gateway is not reachable, the exact same loop runs directly
against Ollama so the demo keeps working, and the UI says which route was used.
"""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from common import (CHAT_MODEL, OLLAMA, ROOT, RUN_DIR, gateway_token, gateway_url,
                    setting, strip_thinking)

LAB = ROOT / "hands-on-3-agent"
AGENTS_MD = LAB / "agent" / "AGENTS.md"
DEFAULT_DATA = LAB / "data" / "aurora_sales_2024_2025.xlsx"
OUT_ROOT = RUN_DIR / "lab3"
UPLOADS = OUT_ROOT / "uploads"

AGENT_ID = setting("AGENT_ID", "analyst")
# "none" disables the model's hidden reasoning pass: measured 14.8 s -> 2.4 s
# for the same first tool call on qwen3:8b, with the same tool choice.
REASONING = setting("AGENT_REASONING", "none")
MAX_STEPS = 8
LLM_TIMEOUT = 300

EXAMPLES = {
    "vi": [
        {"group": "Câu hỏi mẫu trong slide", "items": [
            "Phân tích doanh số theo vùng và cho biết khu vực nào tăng trưởng tốt nhất.",
        ]},
        {"group": "Phân tích và xuất báo cáo", "items": [
            "Sản phẩm nào bán chạy nhất năm 2025? Xuất báo cáo Excel giúp tôi.",
            "Doanh thu theo tháng có xu hướng gì? Vẽ biểu đồ đường.",
            "Kênh bán nào mang lại lợi nhuận cao nhất?",
        ]},
        {"group": "Đào sâu", "items": [
            "Tại Đà Nẵng, sản phẩm nào đóng góp nhiều nhất vào tăng trưởng?",
            "Doanh thu tủ pin AX-400 thay đổi thế nào theo từng quý?",
            "Sản phẩm nào có biên lợi nhuận gộp cao nhất?",
        ]},
    ],
    "en": [
        {"group": "The question from the slide", "items": [
            "Analyse sales by region and tell me which region grew the most.",
        ]},
        {"group": "Analyse and export a report", "items": [
            "Which product sold best in 2025? Export an Excel report.",
            "What is the monthly revenue trend? Draw a line chart.",
            "Which sales channel brings the most profit?",
        ]},
        {"group": "Dig deeper", "items": [
            "In Da Nang, which product contributed most to growth?",
            "How did AX-400 cabinet revenue change quarter by quarter?",
            "Which product has the highest gross margin?",
        ]},
    ],
}


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
_route_cache: dict = {"ok": None, "at": 0.0, "detail": ""}


def gateway_ready(max_age: float = 30) -> tuple[bool, str]:
    """Is the sandbox's OpenClaw gateway serving our analyst agent?"""
    if time.time() - _route_cache["at"] < max_age and _route_cache["ok"] is not None:
        return _route_cache["ok"], _route_cache["detail"]
    ok, detail = False, ""
    token = gateway_token()
    if not token:
        detail = "no gateway token (is the NemoClaw sandbox onboarded?)"
    else:
        try:
            req = urllib.request.Request(f"{gateway_url()}/v1/models",
                                         headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                ids = [m.get("id") for m in json.loads(resp.read()).get("data", [])]
            ok = f"openclaw/{AGENT_ID}" in ids
            detail = "ready" if ok else f"agent '{AGENT_ID}' not configured in the sandbox"
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                gateway_token(refresh=True)
            detail = f"gateway answered HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001
            detail = f"gateway unreachable at {gateway_url()} ({exc.__class__.__name__})"
    _route_cache.update(ok=ok, at=time.time(), detail=detail)
    return ok, detail


def tools_available() -> tuple[bool, str]:
    try:
        import matplotlib  # noqa: F401
        import openpyxl  # noqa: F401
        import pandas  # noqa: F401
        return True, ""
    except ImportError as exc:
        return False, f"missing Python package: {exc.name} (run ./setup.sh)"


def _tools():
    import sys
    tools_dir = str(LAB / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import sales_tools  # noqa: E402
    return sales_tools


# --------------------------------------------------------------------------
# Datasets
# --------------------------------------------------------------------------
def dataset_path(name: str | None) -> Path:
    if not name or name == DEFAULT_DATA.name:
        return DEFAULT_DATA
    safe = Path(name).name
    p = UPLOADS / safe
    return p if p.exists() else DEFAULT_DATA


def save_upload(filename: str, body: bytes) -> dict:
    safe = re.sub(r"[^\w.\- ()]+", "_", Path(filename or "upload.xlsx").name).strip() or "upload.xlsx"
    if not safe.lower().endswith((".xlsx", ".csv")):
        raise ValueError("only .xlsx or .csv files are supported")
    if len(body) > 25 * 1024 * 1024:
        raise ValueError("file is larger than 25 MB")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    path = UPLOADS / safe
    path.write_bytes(body)
    try:
        return dataset_preview(path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise ValueError(f"could not read the file: {exc}") from exc


def dataset_preview(path: Path, rows: int = 8) -> dict:
    st = _tools()
    df, meta = st.load_dataset(path)
    head = df.head(rows).copy()
    for c in head.columns:
        if str(head[c].dtype).startswith("datetime"):
            head[c] = head[c].dt.strftime("%Y-%m")
    return {
        "name": path.name,
        "sheet": meta["sheet"],
        "rows": int(len(df)),
        "columns": list(df.columns),
        "preview": head.astype(object).where(head.notna(), "").values.tolist(),
        "default": path == DEFAULT_DATA,
    }


# --------------------------------------------------------------------------
# The OpenAI-compatible chat call (same code for both routes)
# --------------------------------------------------------------------------
class LLMError(Exception):
    pass


def chat_stream(route: str, messages: list[dict], tool_specs: list[dict], on_text) -> dict:
    """One model turn. Streams text through on_text; returns content + tool calls."""
    if route == "nemoclaw":
        url = f"{gateway_url()}/v1/chat/completions"
        token = gateway_token() or ""
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"model": f"openclaw/{AGENT_ID}", "messages": messages,
                   "tools": tool_specs, "stream": True}
    else:
        url = f"{OLLAMA}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {"model": CHAT_MODEL, "messages": messages, "tools": tool_specs,
                   "stream": True, "temperature": 0.2}
        if REASONING and REASONING != "default":
            payload["reasoning_effort"] = REASONING

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=LLM_TIMEOUT)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        if route == "direct" and exc.code == 400 and "reasoning" in body and "reasoning_effort" in payload:
            payload.pop("reasoning_effort")  # model without a reasoning switch
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
            resp = urllib.request.urlopen(req, timeout=LLM_TIMEOUT)
        else:
            raise LLMError(f"HTTP {exc.code}: {body}") from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise LLMError(str(exc)) from exc

    content, calls, finish, usage = [], {}, None, None
    in_think = False
    with resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            if chunk.get("error"):
                raise LLMError(str(chunk["error"]))
            usage = chunk.get("usage") or usage
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                piece = delta.get("content") or ""
                if piece:
                    if "<think>" in piece:
                        in_think, piece = True, piece.split("<think>", 1)[0]
                    if in_think:
                        if "</think>" in piece:
                            in_think, piece = False, piece.split("</think>", 1)[1]
                        else:
                            piece = ""
                    if piece:
                        content.append(piece)
                        on_text(piece)
                for tc in delta.get("tool_calls") or []:
                    slot = calls.setdefault(tc.get("index", len(calls)),
                                            {"id": "", "name": "", "arguments": ""})
                    slot["id"] = tc.get("id") or slot["id"]
                    fn = tc.get("function") or {}
                    slot["name"] = fn.get("name") or slot["name"]
                    args = fn.get("arguments")
                    if isinstance(args, dict):  # some servers send an object
                        slot["arguments"] = json.dumps(args, ensure_ascii=False)
                    elif args:
                        slot["arguments"] += args
                finish = choice.get("finish_reason") or finish
    tool_calls = []
    for i in sorted(calls):
        c = calls[i]
        if not c["name"]:
            continue
        tool_calls.append({"id": c["id"] or f"call_{uuid.uuid4().hex[:8]}",
                           "type": "function",
                           "function": {"name": c["name"], "arguments": c["arguments"] or "{}"}})
    return {"content": strip_thinking("".join(content)), "tool_calls": tool_calls,
            "finish": finish, "usage": usage}


# --------------------------------------------------------------------------
# The agent loop
# --------------------------------------------------------------------------
LANGUAGE_RULE = {
    "vi": ("LANGUAGE: reply in Vietnamese (tiếng Việt). Write the chart title, the "
           "report title and the insights in Vietnamese too."),
    "en": ("LANGUAGE: reply in English, even though the workbook is in Vietnamese. "
           "Write the chart title, the report title and the insights in English. Keep "
           "region and product names exactly as they appear in the data."),
}


def instructions(lang: str, data: Path, rows: int | None) -> str:
    """AGENTS.md plus this conversation's facts, with the language rule stated twice.

    Stating it once at the end was not enough: with a Vietnamese workbook and
    Vietnamese examples in AGENTS.md, qwen3:8b answered an English question in
    Vietnamese.
    """
    base = AGENTS_MD.read_text(encoding="utf-8") if AGENTS_MD.exists() else ""
    rule = LANGUAGE_RULE.get(lang, LANGUAGE_RULE["en"])
    ctx = [
        rule,
        "",
        base.strip(),
        "",
        "## This conversation",
        f"- Active data file: {data.name}" + (f" ({rows} rows)" if rows else ""),
        f"- Today is {time.strftime('%Y-%m-%d')}.",
        f"- {rule}",
        "- Keep numbers exactly as the tools formatted them.",
    ]
    return "\n".join(ctx)


def _short(obj, limit: int = 7000) -> str:
    s = json.dumps(obj, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + ' …"(truncated)"'


RUN_LOCK = threading.Lock()  # one agent run at a time: the GPU serves one presenter


def run_agent(question: str, lang: str, data_name: str | None, route_pref: str, emit) -> None:
    ok, why = tools_available()
    if not ok:
        emit({"event": "error", "message": why})
        return
    if not RUN_LOCK.acquire(blocking=False):
        emit({"event": "error", "message": "busy"})
        return
    try:
        _run(question, lang, data_name, route_pref, emit)
    finally:
        RUN_LOCK.release()


def _run(question: str, lang: str, data_name: str | None, route_pref: str, emit) -> None:
    st = _tools()
    data = dataset_path(data_name)
    run_id = time.strftime("%H%M%S-") + uuid.uuid4().hex[:4]
    out_dir = OUT_ROOT / run_id
    ctx = st.ToolContext(data_path=data, out_dir=out_dir, lang=lang)
    try:
        rows = len(st.load_dataset(data)[0])
    except Exception:
        rows = None

    route = "direct"
    route_note = ""
    if route_pref in ("auto", "nemoclaw"):
        ready, route_note = gateway_ready()
        if ready:
            route = "nemoclaw"
        elif route_pref == "nemoclaw":
            emit({"event": "error", "message": f"NemoClaw route unavailable: {route_note}"})
            return

    messages: list[dict] = [
        {"role": "system", "content": instructions(lang, data, rows)},
        {"role": "user", "content": question},
    ]
    transcript = {"question": question, "lang": lang, "data": data.name, "route": route,
                  "events": []}

    def send(ev: dict) -> None:
        ev.setdefault("t", round(time.time() - t0, 2))
        transcript["events"].append(ev)
        emit(ev)

    t0 = time.time()
    send({"event": "start", "run": run_id, "route": route, "note": route_note,
          "agent": f"openclaw/{AGENT_ID}" if route == "nemoclaw" else CHAT_MODEL,
          "model": CHAT_MODEL, "data": data.name})

    seen: dict[str, dict] = {}
    final = ""
    for step in range(1, MAX_STEPS + 1):
        send({"event": "llm", "step": step})
        t_llm = time.time()
        try:
            reply = chat_stream(route, messages, st.TOOL_SPECS,
                                lambda piece: emit({"event": "delta", "step": step, "text": piece}))
        except LLMError as exc:
            if route == "nemoclaw" and route_pref == "auto" and step == 1:
                # The sandbox path failed on the first call: fall back and say so.
                route = "direct"
                transcript["route"] = route
                send({"event": "fallback", "route": route, "reason": str(exc)[:300]})
                try:
                    reply = chat_stream(route, messages, st.TOOL_SPECS,
                                        lambda piece: emit({"event": "delta", "step": step, "text": piece}))
                except LLMError as exc2:
                    send({"event": "error", "message": f"model unreachable: {exc2}"})
                    return
            else:
                send({"event": "error", "message": f"model call failed: {exc}"})
                return
        send({"event": "llm_done", "step": step, "seconds": round(time.time() - t_llm, 1),
              "tool_calls": len(reply["tool_calls"]), "usage": reply.get("usage")})

        if not reply["tool_calls"]:
            final = reply["content"]
            break

        messages.append({"role": "assistant", "content": reply["content"] or "",
                         "tool_calls": reply["tool_calls"]})
        if reply["content"]:
            send({"event": "thought", "step": step, "text": reply["content"]})
        for call in reply["tool_calls"]:
            name = call["function"]["name"]
            raw_args = call["function"]["arguments"]
            try:
                args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                args = {"_raw": raw_args}
            send({"event": "tool_call", "id": call["id"], "name": name, "args": args})
            key = name + json.dumps(args, sort_keys=True, ensure_ascii=False)
            t_tool = time.time()
            if key in seen and name != "export_excel_report":
                model_out, ui_out, ok = seen[key]["model"], seen[key]["ui"], True
                model_out = {**model_out, "note": "Same call as before; result repeated. Move on."}
            else:
                model_out, ui_out, ok = st.run_tool(name, args, ctx)
                seen[key] = {"model": model_out, "ui": ui_out}
            ev = {"event": "tool_result", "id": call["id"], "name": name, "ok": ok,
                  "seconds": round(time.time() - t_tool, 2), "ui": ui_out}
            if ok and name == "create_chart":
                ev["image_url"] = f"/api/lab3/file/{run_id}/{ui_out['image']}"
            if ok and name == "export_excel_report":
                ev["file_url"] = f"/api/lab3/file/{run_id}/{ui_out['file']}"
            send(ev)
            # Exactly the message shape verified against the OpenClaw gateway.
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": _short(model_out)})
    else:
        final = final or ("Đã đạt giới hạn số bước." if lang == "vi" else "Step limit reached.")

    final = "\n".join(l for l in final.splitlines() if not l.strip().startswith("MEDIA:")).strip()
    files = [{"kind": f["kind"], "name": f["name"],
              "url": f"/api/lab3/file/{run_id}/{f['name']}"} for f in ctx.files]
    send({"event": "answer", "text": final, "seconds": round(time.time() - t0, 1),
          "route": route, "files": files})
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        transcript["messages"] = messages
        (out_dir / "transcript.json").write_text(
            json.dumps(transcript, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    except OSError:
        pass


def output_file(run_id: str, name: str) -> Path | None:
    """Resolve a generated chart/report without allowing path traversal."""
    if not re.fullmatch(r"[\w\-]+", run_id or "") or "/" in name or "\\" in name or name.startswith("."):
        return None
    p = OUT_ROOT / run_id / name
    return p if p.is_file() else None
