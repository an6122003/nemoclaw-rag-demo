#!/usr/bin/env python3
"""
verify_qa.py — mandatory self-verification for the AGS RAG workshop corpus.

For every entry in verification/reference_qa.json this script:
  1. confirms that `source_doc` names a file that actually exists in corpus/,
  2. confirms that EVERY string in `must_contain` is a literal, character-for-character
     substring of that document's contents (no normalisation, no case folding),
  3. reports any entry that fails, with the exact reason.

Exit status is 0 only when every entry passes.

Run from the hands-on-2/ directory:  python3 verification/verify_qa.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CORPUS = ROOT / "corpus"
QA_PATH = HERE / "reference_qa.json"

REQUIRED_KEYS = {
    "id",
    "question",
    "expected_answer",
    "must_contain",
    "source_doc",
    "category",
    "notes",
}
ALLOWED_CATEGORIES = {
    "single-hop",
    "numeric-spec",
    "version-specific",
    "procedure",
    "disambiguation",
    "superseded",
}
REQUIRED_DOC_COUNT = 28
MIN_WORDS, MAX_WORDS = 250, 600


def main() -> int:
    failures: list[str] = []

    print("=" * 78)
    print("AGS RAG corpus — reference Q&A verification")
    print("=" * 78)

    if not QA_PATH.exists():
        print(f"FATAL: {QA_PATH} does not exist")
        return 2
    qa = json.loads(QA_PATH.read_text(encoding="utf-8"))

    corpus_files = sorted(p.name for p in CORPUS.glob("*.md"))
    print(f"\ncorpus/ contains {len(corpus_files)} markdown documents "
          f"(expected {REQUIRED_DOC_COUNT})")
    if len(corpus_files) != REQUIRED_DOC_COUNT:
        failures.append(
            f"corpus document count is {len(corpus_files)}, expected {REQUIRED_DOC_COUNT}"
        )

    print(f"reference_qa.json contains {len(qa)} entries\n")

    # ---- corpus word-count sanity check -------------------------------------
    print("-" * 78)
    print("Word counts (target 250-600 per document)")
    print("-" * 78)
    for name in corpus_files:
        text = (CORPUS / name).read_text(encoding="utf-8")
        words = len(text.split())
        ok = MIN_WORDS <= words <= MAX_WORDS
        print(f"  {'ok ' if ok else 'BAD'} {words:5d}  {name}")
        if not ok:
            failures.append(
                f"{name}: {words} words is outside the {MIN_WORDS}-{MAX_WORDS} range"
            )

    # ---- structural checks --------------------------------------------------
    print("\n" + "-" * 78)
    print("Structural checks")
    print("-" * 78)
    seen_ids: Counter[str] = Counter()
    for i, entry in enumerate(qa):
        label = entry.get("id", f"<entry {i}>")
        missing = REQUIRED_KEYS - set(entry)
        extra = set(entry) - REQUIRED_KEYS
        if missing:
            failures.append(f"{label}: missing keys {sorted(missing)}")
        if extra:
            failures.append(f"{label}: unexpected keys {sorted(extra)}")
        seen_ids[entry.get("id", f"<entry {i}>")] += 1
        cat = entry.get("category")
        if cat not in ALLOWED_CATEGORIES:
            failures.append(f"{label}: category {cat!r} is not one of {sorted(ALLOWED_CATEGORIES)}")
        mc = entry.get("must_contain")
        if not isinstance(mc, list) or not (1 <= len(mc) <= 3) or not all(
            isinstance(s, str) and s for s in mc
        ):
            failures.append(f"{label}: must_contain must be a list of 1-3 non-empty strings")
        if not isinstance(entry.get("source_doc"), str) or not entry["source_doc"].endswith(".md"):
            failures.append(f"{label}: source_doc must be a .md filename")
    dupes = [k for k, v in seen_ids.items() if v > 1]
    if dupes:
        failures.append(f"duplicate ids: {sorted(dupes)}")
    print(f"  checked {len(qa)} entries for required keys, category vocabulary, "
          f"must_contain shape and unique ids")
    print(f"  duplicate ids: {dupes if dupes else 'none'}")

    # ---- the mandatory per-entry content check ------------------------------
    print("\n" + "-" * 78)
    print("Per-entry check: source_doc exists, and every must_contain string is a")
    print("literal substring of that file's contents")
    print("-" * 78)

    entry_failures = 0
    for entry in qa:
        eid = entry.get("id", "?")
        source = entry.get("source_doc", "")
        path = CORPUS / source

        problems: list[str] = []
        if not path.exists():
            problems.append(f"source_doc NOT FOUND in corpus/: {source}")
            content = None
        else:
            content = path.read_text(encoding="utf-8")

        for needle in entry.get("must_contain", []):
            if content is None:
                problems.append(f"cannot check {needle!r} (missing source)")
            elif needle not in content:
                problems.append(f"literal {needle!r} NOT FOUND in {source}")

        if problems:
            entry_failures += 1
            print(f"  FAIL {eid}  [{entry.get('category')}]  {source}")
            for p in problems:
                print(f"         - {p}")
            failures.extend(f"{eid}: {p}" for p in problems)
        else:
            joined = " | ".join(entry["must_contain"])
            print(f"  ok   {eid}  [{entry.get('category'):<16}]  {source}")
            print(f"         found: {joined}")

    # ---- summary ------------------------------------------------------------
    print("\n" + "=" * 78)
    print("Category counts")
    print("=" * 78)
    for cat in sorted(ALLOWED_CATEGORIES):
        n = seen_ids and sum(1 for e in qa if e.get("category") == cat) or 0
        print(f"  {cat:<16} {n}")
    print(f"  {'TOTAL':<16} {len(qa)}")

    print("\n" + "=" * 78)
    if failures:
        print(f"RESULT: FAIL — {len(failures)} problem(s) across "
              f"{entry_failures} failing QA entr{'y' if entry_failures == 1 else 'ies'}")
        print("=" * 78)
        for f in failures:
            print(f"  * {f}")
        return 1

    print(f"RESULT: PASS — {len(qa)}/{len(qa)} QA entries verified, "
          f"0 failures")
    print(f"        every source_doc exists in corpus/ and every must_contain "
          f"string is a literal substring.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
