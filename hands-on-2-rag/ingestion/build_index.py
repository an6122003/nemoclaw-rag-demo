#!/usr/bin/env python3
"""Build a RAG index over the lab corpus using a local Ollama embedding model.

Dependency-free: standard library only, so it runs unchanged on the DGX Spark,
on macOS, and inside the OpenShell sandbox (all of which have python3 but may
not have numpy or requests available).

The index this produces serves two purposes:

1. It is the lab's ingestion artifact. Participants run this to see chunking and
   embedding happen for real.
2. It is the *pre-built fallback*. If ingestion fails on the day (no GPU, no
   Ollama, no network), the checked-in index is restored and the session
   continues. Build it once and commit the output.

Chunking is heading-aware and each chunk carries a breadcrumb header
("doc title > section > subsection") because retrieval quality on technical
documentation degrades badly when chunks lose their section context.

Usage
-----
    python3 build_index.py --corpus ../corpus --out ../index
    python3 build_index.py --base-url http://127.0.0.1:11434
    python3 build_index.py --base-url http://your-ollama-host:11434 --model qwen3-embedding:4b
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_MODEL = "qwen3-embedding:4b"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def http_json(url: str, payload: dict | None = None, timeout: int = 300) -> dict:
    """Minimal JSON POST/GET helper built on urllib (no third-party deps)."""
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def split_into_blocks(text: str) -> list[tuple[list[str], str]]:
    """Split markdown into (heading_breadcrumb, body) blocks.

    Text before the first heading belongs to the document title.
    """
    lines = text.splitlines()
    breadcrumb: list[str] = []
    current: list[str] = []
    blocks: list[tuple[list[str], str]] = []

    def flush() -> None:
        body = "\n".join(current).strip()
        if body:
            blocks.append((list(breadcrumb), body))
        current.clear()

    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            # Truncate the breadcrumb to this heading's level, then append.
            breadcrumb = breadcrumb[: level - 1]
            while len(breadcrumb) < level - 1:
                breadcrumb.append("")
            breadcrumb.append(title)
            # Keep the heading line in the body too, so a chunk stays readable
            # and self-describing once several small sections are merged.
            current.append(line)
        else:
            current.append(line)
    flush()
    return blocks


def chunk_blocks(
    blocks: list[tuple[list[str], str]], target: int, overlap: int
) -> list[dict]:
    """Pack blocks into ~`target`-character chunks, splitting oversized blocks.

    Small adjacent blocks under the same heading are merged so we do not embed
    fragments like a lone table row.
    """
    chunks: list[dict] = []
    buf_text = ""
    buf_head: list[str] = []

    def emit(text: str, head: list[str]) -> None:
        text = text.strip()
        if text:
            chunks.append({"heading": " > ".join(h for h in head if h), "text": text})

    for head, body in blocks:
        # A block larger than the target is split on paragraph boundaries.
        if len(body) > target:
            if buf_text:
                emit(buf_text, buf_head)
                buf_text, buf_head = "", []
            paras = [p for p in body.split("\n\n") if p.strip()]
            cur = ""
            for p in paras:
                if len(cur) + len(p) + 2 <= target:
                    cur = f"{cur}\n\n{p}" if cur else p
                else:
                    if cur:
                        emit(cur, head)
                    # Hard-split any single paragraph still over target.
                    while len(p) > target:
                        emit(p[:target], head)
                        p = p[max(1, target - overlap) :]
                    cur = p
            if cur:
                emit(cur, head)
            continue

        # Break on size, or on a heading change once the buffer is reasonably
        # full. Merging across small adjacent headings avoids fragmenting a
        # short document into one chunk per section, which previously buried a
        # single required sentence in a chunk the retriever never selected.
        if buf_text and (
            len(buf_text) + len(body) + 2 > target
            or (buf_head != head and len(buf_text) >= int(target * 0.6))
        ):
            emit(buf_text, buf_head)
            buf_text, buf_head = "", []
        buf_text = f"{buf_text}\n\n{body}" if buf_text else body
        buf_head = head
    if buf_text:
        emit(buf_text, buf_head)
    return chunks


def embed_batch(base_url: str, model: str, texts: list[str]) -> list[list[float]]:
    out = http_json(
        f"{base_url.rstrip('/')}/api/embed",
        {"model": model, "input": texts},
    )
    return out.get("embeddings", [])


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a RAG index over the corpus.")
    ap.add_argument("--corpus", default="../corpus", help="corpus directory")
    ap.add_argument("--out", default="../index", help="output directory")
    ap.add_argument("--base-url", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--target-chars", type=int, default=800)
    ap.add_argument("--overlap-chars", type=int, default=150)
    ap.add_argument("--batch", type=int, default=16)
    args = ap.parse_args()

    corpus = Path(args.corpus).resolve()
    outdir = Path(args.out).resolve()
    docs = sorted(corpus.glob("*.md"))
    if not docs:
        print(f"error: no .md files in {corpus}", file=sys.stderr)
        return 2

    # Fail fast and legibly if the embedding server is not reachable.
    try:
        version = http_json(f"{args.base_url.rstrip('/')}/api/version", timeout=15)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        print(f"error: cannot reach Ollama at {args.base_url}: {exc}", file=sys.stderr)
        print("hint: start the relay, or pass --base-url pointing at your Ollama.", file=sys.stderr)
        return 3
    print(f"embedding server {args.base_url} (ollama {version.get('version', '?')}), model {args.model}")

    chunks: list[dict] = []
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        title = doc.stem
        for m in HEADING_RE.finditer(text):
            if len(m.group(1)) == 1:
                title = m.group(2).strip()
                break
        for c in chunk_blocks(
            split_into_blocks(text), args.target_chars, args.overlap_chars
        ):
            chunks.append(
                {
                    "doc": doc.name,
                    "doc_title": title,
                    "heading": c["heading"],
                    # The embedded text carries the breadcrumb; the stored text
                    # stays clean so answers are not polluted by metadata.
                    "embed_text": f"{title} — {c['heading']}\n\n{c['text']}"
                    if c["heading"]
                    else f"{title}\n\n{c['text']}",
                    "text": c["text"],
                }
            )

    print(f"{len(docs)} documents -> {len(chunks)} chunks")

    vectors: list[list[float]] = []
    t0 = time.time()
    for i in range(0, len(chunks), args.batch):
        batch = chunks[i : i + args.batch]
        try:
            vecs = embed_batch(args.base_url, args.model, [c["embed_text"] for c in batch])
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"error: embedding failed at chunk {i}: {exc}", file=sys.stderr)
            return 4
        if len(vecs) != len(batch):
            print(
                f"error: asked for {len(batch)} embeddings, got {len(vecs)}",
                file=sys.stderr,
            )
            return 4
        vectors.extend(vecs)
        done = min(i + args.batch, len(chunks))
        pct = 100.0 * done / len(chunks)
        print(f"  embedded {done}/{len(chunks)} ({pct:5.1f}%)", end="\r", flush=True)
    print()

    dim = len(vectors[0]) if vectors else 0
    # Normalise at build time so query-time scoring is a plain dot product.
    normed = []
    for v in vectors:
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        normed.append([x / n for x in v])

    outdir.mkdir(parents=True, exist_ok=True)
    index = {
        "model": args.model,
        "dim": dim,
        "target_chars": args.target_chars,
        "overlap_chars": args.overlap_chars,
        "chunk_count": len(chunks),
        "doc_count": len(docs),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "chunks": [
            {
                "doc": c["doc"],
                "doc_title": c["doc_title"],
                "heading": c["heading"],
                "text": c["text"],
                "vector": v,
            }
            for c, v in zip(chunks, normed)
        ],
    }
    index_path = outdir / "rag_index.json"
    index_path.write_text(json.dumps(index), encoding="utf-8")

    # A small manifest lets verification prove the index matches the corpus.
    import hashlib

    manifest = {
        "model": args.model,
        "dim": dim,
        "chunk_count": len(chunks),
        "doc_count": len(docs),
        "corpus_sha256": hashlib.sha256(
            b"".join(sorted(d.read_bytes() for d in docs))
        ).hexdigest(),
        "docs": sorted(d.name for d in docs),
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    size_mb = index_path.stat().st_size / 1e6
    print(
        f"wrote {index_path} ({size_mb:.1f} MB, dim={dim}, {len(chunks)} chunks) "
        f"in {time.time() - t0:.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
