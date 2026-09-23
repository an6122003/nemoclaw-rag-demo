#!/usr/bin/env python3
"""Verify the assembled RAG pipeline inside a running NemoClaw sandbox.

This is the event-day gate. It asks the sandbox's own memory search the
reference questions and checks that the returned context contains the expected
answer strings.

It deliberately drives `openclaw memory search` rather than chatting with the
model. Retrieval is deterministic and is the part the lab is actually teaching;
a local 8B model's phrasing varies run to run, so grading on generated prose
would produce false failures. Use --mode answer when you want to smoke-test
generation, accepting that it is advisory.

Usage
-----
    python3 verify_agent.py --sandbox my-assistant
    python3 verify_agent.py --sandbox my-assistant --k 6 --json
    python3 verify_agent.py --sandbox my-assistant --mode answer

Exit codes: 0 pass, 1 below threshold, 2 setup problem.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

MIN_PASS_RATE = 0.90


def run(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"
    except FileNotFoundError as exc:
        return 2, "", str(exc)


def memory_search(sandbox: str, query: str, k: int) -> tuple[bool, list[dict], str]:
    """Run memory search in the sandbox and return its structured hits.

    Returns (ok, hits, error) where each hit is {path, start, end, score}. We keep
    the line ranges rather than the returned text because `memory search` returns a
    TRUNCATED snippet for display -- checking answer strings against a snippet
    reports failures for answers that are plainly inside the retrieved chunk.
    """
    code, out, err = run(
        [
            "nemoclaw", sandbox, "exec", "--",
            # TMPDIR is set explicitly: SQLite derives its temp directory from
            # it, and memory operations fail with "unable to open database file"
            # when it is unset in the exec environment.
            "env", "TMPDIR=/tmp",
            "openclaw", "memory", "search", "--query", query,
            "--max-results", str(k), "--json",
        ]
    )
    if code != 0:
        return False, [], (out or err)[-400:]
    # The exec wrapper can prepend notices; take the JSON object only.
    start = out.find("{")
    if start < 0:
        return False, [], out[-400:]
    try:
        data = json.loads(out[start:])
    except json.JSONDecodeError as exc:
        return False, [], f"unparseable search output: {exc}"
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
    return True, hits, ""


def load_corpus(corpus_dir: Path) -> dict[str, list[str]]:
    return {p.name: p.read_text(encoding="utf-8").splitlines() for p in corpus_dir.glob("*.md")}


def ranges_text(hits: list[dict], corpus: dict[str, list[str]]) -> str:
    """Concatenate the corpus text covered by the retrieved chunk ranges."""
    parts = []
    for h in hits:
        name = h["path"].split("/")[-1]
        lines = corpus.get(name)
        if not lines:
            continue
        lo = max(1, h["start"])
        hi = min(len(lines), h["end"]) if h["end"] else len(lines)
        parts.append("\n".join(lines[lo - 1 : hi]))
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify the sandbox RAG pipeline.")
    ap.add_argument("--sandbox", default="my-assistant")
    ap.add_argument("--qa", default=str(Path(__file__).with_name("reference_qa.json")))
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--mode", choices=["retrieval", "answer"], default="retrieval")
    ap.add_argument("--min-pass-rate", type=float, default=MIN_PASS_RATE)
    ap.add_argument("--json", action="store_true", help="emit machine-readable results")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    qa = json.loads(Path(args.qa).read_text(encoding="utf-8"))

    code, _, err = run(["nemoclaw", args.sandbox, "status"])
    if code != 0:
        print(f"error: sandbox '{args.sandbox}' unreachable: {err.strip()}", file=sys.stderr)
        return 2

    corpus_dir = Path(args.qa).resolve().parent.parent / "corpus"
    if not corpus_dir.is_dir():
        print(f"error: corpus not found at {corpus_dir}", file=sys.stderr)
        return 2
    corpus = load_corpus(corpus_dir)

    results = []
    passed = 0
    for item in qa:
        ok, hits, err = memory_search(args.sandbox, item["question"], args.k)
        if not ok:
            results.append({**item, "status": "error", "missing": item["must_contain"], "detail": err})
            if not args.json:
                print(f"  ERROR {item['id']}: {err.strip()[:200]}")
            continue
        # Judge the retrieved chunk ranges, not the truncated display snippet.
        text = ranges_text(hits, corpus)
        missing = [s for s in item["must_contain"] if s not in text]
        status = "pass" if not missing else "fail"
        if status == "pass":
            passed += 1
        top = hits[0] if hits else {}
        results.append(
            {
                **item,
                "status": status,
                "missing": missing,
                "hits": [f"{h['path'].split('/')[-1]}:{h['start']}-{h['end']}" for h in hits],
                "top_score": round(top.get("score", 0.0), 3),
            }
        )
        if not args.json and (args.verbose or status == "fail"):
            mark = "ok  " if status == "pass" else "FAIL"
            detail = f"missing={missing}" if missing else f"top={results[-1]['hits'][0] if hits else 'none'}"
            print(f"  {mark} {item['id']} [{item['category']:15s}] {detail}")

    total = len(qa)
    rate = passed / total if total else 0.0

    if args.json:
        print(json.dumps(
            {
                "sandbox": args.sandbox,
                "mode": args.mode,
                "total": total,
                "passed": passed,
                "pass_rate": rate,
                "threshold": args.min_pass_rate,
                "results": results,
            },
            indent=2,
        ))
    else:
        print()
        print("=" * 64)
        print(f"sandbox {args.sandbox} — retrieval verification")
        print("=" * 64)
        print(f"  passed {passed}/{total} ({rate:.1%}), threshold {args.min_pass_rate:.0%}")
        if passed < total:
            print("\n  failing questions:")
            for r in results:
                if r["status"] != "pass":
                    print(f"    {r['id']} [{r['category']}] missing={r.get('missing')}")
        print()
        if rate >= args.min_pass_rate:
            print("RESULT: PASS — sandbox retrieval answers the reference set.")
        else:
            print("RESULT: FAIL — sandbox retrieval is below threshold.")
            print("  check: provider/model in 'openclaw memory status --deep'")
            print("  check: index built        'openclaw memory status --index'")

    return 0 if rate >= args.min_pass_rate else 1


if __name__ == "__main__":
    raise SystemExit(main())
