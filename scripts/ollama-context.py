#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Give one Ollama model a larger context window, without downloading anything.

    python3 scripts/ollama-context.py nemotron-3.5-lightning:30b-a3b 65536

OpenClaw's own agent (the workshop challenge) sends every tool, its workspace
files and its skill list with each turn: about 14,000 tokens before the first
question. Ollama's host default (OLLAMA_CONTEXT_LENGTH, often 16384 on a Spark
that NemoClaw set up) overflows after a step or two, and OpenClaw answers
"Context overflow: prompt too large for the model".

Raising the host default needs sudo and costs memory for every model, so this
stores num_ctx as a parameter of the chat model itself instead: `ollama
create` from the local model, keeping its other parameters. Nothing is
downloaded and the setting survives restarts. A later `ollama pull` of the same
tag resets it, which is why setup.sh and start.sh run this every time.

Standard library only. Exit code 0 when the model has the context.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")


def call(path: str, body: dict, timeout: float = 600) -> dict:
    req = urllib.request.Request(f"{OLLAMA}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw) if raw.strip() else {}


def value(text: str):
    text = text.strip().strip('"')
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            pass
    return text


def parameters(model: str) -> dict:
    """The model's parameters as /api/create expects them ("stop" is a list)."""
    out: dict = {}
    for line in (call("/api/show", {"model": model}, timeout=60).get("parameters") or "").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            out.setdefault(parts[0], []).append(value(parts[1]))
    return {k: (v if k == "stop" or len(v) > 1 else v[0]) for k, v in out.items()}


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: ollama-context.py <model> <tokens>", file=sys.stderr)
        return 2
    model, want = sys.argv[1], int(sys.argv[2])
    try:
        before = parameters(model)
    except urllib.error.HTTPError as exc:
        print(f"{model}: not available in Ollama ({exc.code})", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Ollama is not answering at {OLLAMA}: {exc}", file=sys.stderr)
        return 1
    if before.get("num_ctx") == want:
        print(f"{model}: context window {want} tokens (already set)")
        return 0

    # Pass the existing parameters explicitly so none of them is lost; fall
    # back to num_ctx alone if this Ollama rejects one of them.
    for params in ({**before, "num_ctx": want}, {"num_ctx": want}):
        try:
            call("/api/create", {"model": model, "from": model, "parameters": params, "stream": False})
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            print(f"ollama create refused {sorted(params)}: {detail}", file=sys.stderr)
    after = parameters(model)
    if after.get("num_ctx") != want:
        print(f"{model}: could not set the context window (parameters now: {after})", file=sys.stderr)
        return 1
    lost = sorted(k for k in before if k != "num_ctx" and k not in after)
    print(f"{model}: context window {before.get('num_ctx', 'default')} -> {want} tokens"
          + (f" (dropped: {', '.join(lost)})" if lost else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
