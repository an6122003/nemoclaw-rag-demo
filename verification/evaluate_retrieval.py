#!/usr/bin/env python3
"""Evaluate retrieval quality of the lab index against the reference Q&A set.

This is a pre-flight gate, not a demo. It answers one question: *if the
retriever returns the top-k chunks for a reference question, do those chunks
actually contain the answer?* If this fails, the lab will fail, no matter how
healthy the agent looks -- so run it before the event and treat a regression as
a release blocker.

It deliberately measures retrieval rather than generation: a local 8B model's
answer quality varies run to run, but retrieval quality is deterministic and is
the part the lab is actually teaching.

Dependency-free (standard library only).

Usage
-----
    python3 evaluate_retrieval.py --index ../index --qa reference_qa.json
    python3 evaluate_retrieval.py --k 5 --verbose
    python3 evaluate_retrieval.py --base-url http://127.0.0.1:11434   # embed queries live

Exit codes: 0 pass, 1 metric below threshold, 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Thresholds a lab corpus should clear comfortably. Recall is measured over
# documents (was the right file retrieved at all); context_hit is measured over
# answer strings (did the retrieved text actually contain the answer).
MIN_RECALL_AT_3 = 0.90
MIN_RECALL_AT_5 = 0.97
MIN_CONTEXT_HIT_AT_5 = 0.90
MIN_MRR = 0.75


# Ollama's qwen3-embedding models are trained asymmetrically: the *query* side
# carries an instruction prefix while documents are embedded raw. OpenClaw's
# Ollama provider adapter applies this automatically
# (extensions/ollama/src/embedding-provider.runtime.ts). Reproducing it here
# keeps this baseline faithful to what the sandbox will actually do.
QWEN3_QUERY_PREFIX = (
    "Instruct: Given a user query, retrieve relevant memory notes and documents\n"
    "Query:"
)


def embed_query(
    base_url: str, model: str, text: str, query_prefix: str | None = None
) -> list[float]:
    if query_prefix:
        text = f"{query_prefix}{text}"
    payload = json.dumps({"model": model, "input": [text]}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    vec = data["embeddings"][0]
    n = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def main() -> int:
    # Resolve defaults against the lab root so the script works no matter which
    # directory a participant runs it from.
    lab = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description="Evaluate retrieval against reference Q&A.")
    ap.add_argument("--index", default=str(lab / "index"), help="index directory")
    ap.add_argument(
        "--qa",
        default=str(Path(__file__).with_name("reference_qa.json")),
        help="reference Q&A json",
    )
    ap.add_argument("--k", type=int, default=5, help="cutoff for reported metrics")
    ap.add_argument("--base-url", default="http://127.0.0.1:11434")
    ap.add_argument("--verbose", action="store_true", help="show every question")
    ap.add_argument("--dump-vectors", help="cache query vectors to this file")
    ap.add_argument(
        "--max-per-doc",
        type=int,
        default=2,
        help="cap chunks contributed by any single document (0 disables)",
    )
    ap.add_argument(
        "--corpus",
        default=str(lab / "corpus"),
        help="corpus directory, used to find every document that answers a question",
    )
    ap.add_argument(
        "--query-prefix",
        default="qwen3",
        choices=["qwen3", "none"],
        help="query-side instruction prefix; 'qwen3' matches OpenClaw's Ollama adapter",
    )
    args = ap.parse_args()

    index_path = Path(args.index).resolve() / "rag_index.json"
    qa_path = Path(args.qa).resolve()
    if not index_path.exists():
        print(f"error: {index_path} not found -- run ingestion/build_index.py first", file=sys.stderr)
        return 2
    if not qa_path.exists():
        print(f"error: {qa_path} not found", file=sys.stderr)
        return 2

    index = json.loads(index_path.read_text(encoding="utf-8"))
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    chunks = index["chunks"]
    model = index["model"]

    # Work out every document that actually answers each question, so the
    # scoring below does not punish a correct-but-different source.
    corpus_dir = Path(args.corpus).resolve()
    corpus_text = {
        p.name: p.read_text(encoding="utf-8") for p in sorted(corpus_dir.glob("*.md"))
    }
    acceptable_docs: dict[str, set[str]] = {}
    for item in qa:
        hits = {
            name
            for name, text in corpus_text.items()
            if all(s in text for s in item["must_contain"])
        }
        if item["source_doc"] in corpus_text:
            hits.add(item["source_doc"])
        if not hits:
            print(
                f"error: no corpus document contains the answer strings for "
                f"{item['id']} {item['must_contain']}",
                file=sys.stderr,
            )
            return 2
        acceptable_docs[item["id"]] = hits
    multi = sum(1 for v in acceptable_docs.values() if len(v) > 1)
    print(f"corpus: {len(corpus_text)} documents ({multi} questions have >1 valid source)")

    print(f"index: {index['chunk_count']} chunks, dim {index['dim']}, model {model}")
    print(f"index built: {index.get('built_at', 'unknown')}")
    print(f"qa: {len(qa)} reference questions")
    print(f"cutoff k={args.k}\n")

    query_vectors: list[list[float]] = []
    query_prefix = QWEN3_QUERY_PREFIX if args.query_prefix == "qwen3" else None
    print(f"query prefix: {'qwen3 instruction template' if query_prefix else 'none'}")
    for i, item in enumerate(qa, 1):
        try:
            query_vectors.append(
                embed_query(args.base_url, model, item["question"], query_prefix)
            )
        except (urllib.error.URLError, OSError, TimeoutError, KeyError) as exc:
            print(f"error: embedding question {item.get('id')} failed: {exc}", file=sys.stderr)
            return 2
        print(f"  embedded query {i}/{len(qa)}", end="\r", flush=True)
    print()
    if args.dump_vectors:
        Path(args.dump_vectors).write_text(json.dumps(query_vectors), encoding="utf-8")

    hits_at_1 = hits_at_3 = hits_at_5 = 0
    context_hits = 0
    reciprocal_ranks: list[float] = []
    failures: list[str] = []

    for item, qv in zip(qa, query_vectors):
        scored = sorted(
            ((dot(qv, c["vector"]), i) for i, c in enumerate(chunks)),
            key=lambda t: t[0],
            reverse=True,
        )
        top = []
        per_doc: dict[str, int] = {}
        for _, i in scored:
            c = chunks[i]
            if args.max_per_doc and per_doc.get(c["doc"], 0) >= args.max_per_doc:
                continue
            per_doc[c["doc"]] = per_doc.get(c["doc"], 0) + 1
            top.append(c)
            if len(top) == args.k:
                break
        top_docs = [c["doc"] for c in top]

        # A fact legitimately appears in several documents in a realistic
        # technical corpus (the same spec lives in a datasheet, the FAQ and a
        # maintenance table). Scoring only the declared source_doc would mark a
        # correct answer wrong, so accept ANY document whose text contains the
        # full answer string set.
        acceptable = acceptable_docs.get(
            item["id"], {item["source_doc"]}
        )
        rank = next(
            (i + 1 for i, d in enumerate(top_docs) if d in acceptable), None
        )

        if rank == 1:
            hits_at_1 += 1
        if rank is not None and rank <= 3:
            hits_at_3 += 1
        if rank is not None and rank <= 5:
            hits_at_5 += 1
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)

        # Does the retrieved context actually contain every expected string?
        joined = "\n".join(c["text"] for c in top)
        missing = [s for s in item["must_contain"] if s not in joined]
        if not missing:
            context_hits += 1

        if (rank is None or rank > 3) or missing:
            detail = (
                f"  MISS {item['id']} [{item['category']}] rank={rank} "
                f"want_any_of={sorted(acceptable)}\n"
                f"       got={top_docs[:3]}\n"
                f"       missing_strings={missing}"
            )
            failures.append(detail)
            if args.verbose:
                print(detail)
        elif args.verbose:
            print(f"  ok   {item['id']} [{item['category']:15s}] rank={rank}")

    n = len(qa)
    r1, r3, r5 = hits_at_1 / n, hits_at_3 / n, hits_at_5 / n
    ctx = context_hits / n
    mrr = sum(reciprocal_ranks) / n

    print("=" * 70)
    print("Retrieval quality")
    print("=" * 70)
    print(f"  recall@1            {r1:6.1%}")
    print(f"  recall@3            {r3:6.1%}   (min {MIN_RECALL_AT_3:.0%})")
    print(f"  recall@5            {r5:6.1%}   (min {MIN_RECALL_AT_5:.0%})")
    print(f"  answer-in-context@5 {ctx:6.1%}   (min {MIN_CONTEXT_HIT_AT_5:.0%})")
    print(f"  MRR                 {mrr:6.3f}   (min {MIN_MRR:.2f})")
    print()

    # Per-category breakdown: disambiguation and superseded are the categories
    # most likely to expose a weak corpus or a weak embedding model.
    by_cat: dict[str, list[int]] = {}
    for item, rr in zip(qa, reciprocal_ranks):
        by_cat.setdefault(item["category"], []).append(1 if rr > 0 else 0)
    print("Recall@5 by category")
    for cat in sorted(by_cat):
        vals = by_cat[cat]
        print(f"  {cat:16s} {sum(vals)}/{len(vals)}")
    print()

    if failures:
        print(f"{len(failures)} question(s) below the recall@3 bar or missing an answer string:")
        for f in failures:
            print(f)
        print()

    problems = []
    if r3 < MIN_RECALL_AT_3:
        problems.append(f"recall@3 {r3:.1%} < {MIN_RECALL_AT_3:.0%}")
    if r5 < MIN_RECALL_AT_5:
        problems.append(f"recall@5 {r5:.1%} < {MIN_RECALL_AT_5:.0%}")
    if ctx < MIN_CONTEXT_HIT_AT_5:
        problems.append(f"answer-in-context@5 {ctx:.1%} < {MIN_CONTEXT_HIT_AT_5:.0%}")
    if mrr < MIN_MRR:
        problems.append(f"MRR {mrr:.3f} < {MIN_MRR:.2f}")

    if problems:
        print(f"RESULT: FAIL -- {'; '.join(problems)}")
        return 1
    print("RESULT: PASS -- retrieval quality clears every threshold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
