#!/usr/bin/env python3
"""End-to-end self-test for the three labs. setup.sh runs it on the DGX Spark.

    .venv/bin/python app/selftest.py                 # all three labs
    .venv/bin/python app/selftest.py --lab3 --route nemoclaw
    .venv/bin/python app/selftest.py --json

Each check drives the real code path the web page uses, with a real model:

    lab1  the fine-tuned model introduces itself as Aurora
    lab2  RAG answers "usable energy of the AX-600" with 558 kWh, and reports
          whether the NemoClaw sandbox's own memory search answered
    lab3  the agent calls the pandas, chart and Excel tools for the slide
          question and names Da Nang as the fastest-growing region

Exit code 0 when every requested check passes.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402


def check_lab1() -> dict:
    import lab1_finetune as lab1
    res = {"lab": 1, "ok": False, "detail": ""}
    if not common.has_model(lab1.TUNED):
        res["detail"] = f"fine-tuned model '{lab1.TUNED}' is not in Ollama"
        return res
    answers: dict[str, list[str]] = {"base": [], "tuned": []}
    errors: dict[str, str] = {}

    def emit(ev: dict) -> None:
        if "text" in ev:
            answers[ev["side"]].append(ev["text"])
        if ev.get("error"):
            errors[ev["side"]] = ev["error"]

    t0 = time.time()
    lab1.compare("Bạn là ai?", emit)
    tuned = "".join(answers["tuned"]).strip()
    res["seconds"] = round(time.time() - t0, 1)
    res["tuned_answer"] = tuned[:300]
    res["base_answer"] = "".join(answers["base"]).strip()[:300]
    if errors.get("tuned"):
        res["detail"] = f"fine-tuned model error: {errors['tuned']}"
    elif "aurora" in tuned.lower():
        res["ok"] = True
        res["detail"] = "fine-tuned model answers as Aurora"
    else:
        res["detail"] = "fine-tuned model did not introduce itself as Aurora"
    return res


def check_lab2() -> dict:
    import lab2_rag as lab2
    q = "What is the usable energy of the AX-600 battery cabinet?"
    res = {"lab": 2, "ok": False, "detail": ""}
    t0 = time.time()
    hits = lab2.run_sandbox_search(q, 5)
    res["sandbox_search"] = bool(hits)
    events: list[dict] = []
    lab2.ask_stream(q, "en", 5, "auto" if hits else "local", events.append)
    final = next((e for e in events if e.get("event") == "answer"), None)
    res["seconds"] = round(time.time() - t0, 1)
    if not final:
        err = next((e.get("message") for e in events if e.get("event") == "error"), "no answer")
        res["detail"] = f"pipeline failed: {err}"
        return res
    res["route"] = final.get("source")
    res["answer"] = (final.get("answer") or "")[:300]
    if final.get("error"):
        res["detail"] = f"generation failed: {final['error']}"
    elif "558" in (final.get("answer") or ""):
        res["ok"] = True
        res["detail"] = f"answered 558 kWh via {final.get('source')}"
    else:
        res["detail"] = "answer did not contain 558 kWh"
    return res


def check_lab3(route: str) -> dict:
    import lab3_agent as lab3
    q = "Phân tích doanh số theo vùng và cho biết khu vực nào tăng trưởng tốt nhất."
    res = {"lab": 3, "ok": False, "detail": ""}
    events: list[dict] = []
    lab3.run_agent(q, "vi", None, route, lambda ev: events.append(ev) if ev.get("event") != "delta" else None)
    calls = [e["name"] for e in events if e.get("event") == "tool_call"]
    failed = [e["name"] for e in events if e.get("event") == "tool_result" and not e.get("ok")]
    answer = next((e for e in events if e.get("event") == "answer"), None)
    start = next((e for e in events if e.get("event") == "start"), {})
    res["tool_calls"] = calls
    res["tool_errors"] = failed
    res["route"] = (answer or start).get("route")
    if any(e.get("event") == "fallback" for e in events):
        res["fallback"] = next(e.get("reason") for e in events if e.get("event") == "fallback")
    if not answer:
        err = next((e.get("message") for e in events if e.get("event") == "error"), "no answer")
        res["detail"] = f"agent failed: {err}"
        return res
    res["seconds"] = answer.get("seconds")
    res["answer"] = (answer.get("text") or "")[:400]
    res["files"] = [f["name"] for f in answer.get("files", [])]
    needed = {"analyze_sales", "create_chart", "export_excel_report"}
    missing = needed - set(calls)
    if missing:
        res["detail"] = f"agent did not call: {', '.join(sorted(missing))}"
    elif "Đà Nẵng" not in (answer.get("text") or ""):
        res["detail"] = "answer does not name Đà Nẵng as the fastest-growing region"
    else:
        res["ok"] = True
        res["detail"] = f"{len(calls)} tool calls via {res['route']}, answer names Đà Nẵng"
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--lab1", action="store_true")
    ap.add_argument("--lab2", action="store_true")
    ap.add_argument("--lab3", action="store_true")
    ap.add_argument("--route", default="auto", choices=["auto", "nemoclaw", "direct"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    labs = [n for n in (1, 2, 3) if getattr(args, f"lab{n}")] or [1, 2, 3]

    if not common.ollama_up():
        print("FAIL  Ollama is not answering on " + common.OLLAMA)
        return 1
    results = []
    for n in labs:
        try:
            r = {1: check_lab1, 2: check_lab2, 3: lambda: check_lab3(args.route)}[n]()
        except Exception as exc:  # noqa: BLE001
            r = {"lab": n, "ok": False, "detail": f"{exc.__class__.__name__}: {exc}"}
        results.append(r)
        if not args.json:
            mark = "PASS" if r["ok"] else "FAIL"
            print(f"{mark}  Hands-on {n}: {r['detail']}"
                  + (f"  ({r['seconds']}s)" if r.get("seconds") is not None else ""))
            sys.stdout.flush()
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
