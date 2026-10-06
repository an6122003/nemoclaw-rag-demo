#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Download an Ollama model, reconnecting when the download stalls.

`ollama pull` often slows to a few KB/s near the end of a large file: the last
chunks come over slow connections and can sit there for hours. Cancelling and
pulling again resumes from the bytes already on disk, and the rest usually
arrives at full speed. This does that automatically, so nobody has to notice.

    python3 scripts/pull-model.py nemotron-3.5-lightning:30b-a3b

Standard library only: setup.sh runs it before the workshop's Python
environment exists. Exit code 0 when the model is ready.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
WINDOW = float(os.environ.get("PULL_STALL_SECONDS", "60"))  # judge speed over this long
FLOOR = float(os.environ.get("PULL_MIN_MBPS", "0.2")) * 1e6  # always "slow" below this
ATTEMPTS = int(os.environ.get("PULL_ATTEMPTS", "40"))
TTY = sys.stdout.isatty()


def size(n: float) -> str:
    return f"{n / 1e9:.1f} GB" if n >= 1e9 else f"{n / 1e6:.0f} MB"


def show(text: str) -> None:
    if TTY:
        print(f"\r\033[K   {text}", end="", flush=True)


def attempt(model: str) -> str:
    """One pull request. Returns "done" or "stalled"; raises on hard errors."""
    body = json.dumps({"model": model, "stream": True}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/pull", data=body,
                                 headers={"Content-Type": "application/json"})
    # The timeout bounds each read: a download that stops sending entirely
    # also counts as stalled.
    resp = urllib.request.urlopen(req, timeout=max(30.0, WINDOW))
    layers: dict[str, tuple[int, int]] = {}
    samples: list[tuple[float, int]] = []
    started = time.time()
    peak = 0.0
    try:
        for raw in resp:
            line = raw.strip()
            if not line:
                continue
            ev = json.loads(line)
            if ev.get("error"):
                raise RuntimeError(ev["error"])
            if ev.get("status") == "success":
                return "done"
            if not (ev.get("digest") and ev.get("total")):
                show(f"{model}: {ev.get('status', '')}")
                continue
            layers[ev["digest"]] = (int(ev.get("completed") or 0), int(ev["total"]))
            done = sum(c for c, _ in layers.values())
            total = sum(t for _, t in layers.values())
            now = time.time()
            samples.append((now, done))
            while len(samples) > 1 and now - samples[1][0] >= WINDOW:
                samples.pop(0)  # keep one sample at least WINDOW old
            span = now - samples[0][0]
            rate = (done - samples[0][1]) / span if span > 0 else 0.0
            if span >= WINDOW:
                peak = max(peak, rate)
            pct = 100.0 * done / total if total else 0.0
            show(f"↓ {model}  {size(done)} / {size(total)}  ({pct:.0f}%)  {rate / 1e6:.1f} MB/s")
            # Slow for a whole window, compared with an absolute floor and with
            # the speed this download managed earlier (5%, so that sharing the
            # line with other Sparks is not mistaken for a stall).
            if done < total and now - started >= WINDOW and span >= WINDOW \
                    and rate < max(FLOOR, 0.05 * peak):
                return "stalled"
    except (socket.timeout, TimeoutError):
        return "stalled"
    finally:
        resp.close()  # Ollama cancels the pull; the bytes on disk stay for the next one
    return "stalled"  # the stream ended without "success"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: pull-model.py <model>", file=sys.stderr)
        return 2
    model = sys.argv[1]
    for n in range(1, ATTEMPTS + 1):
        try:
            result = attempt(model)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:200]
            if exc.code < 500:
                print(f"\n   Ollama refused the download: {detail}", file=sys.stderr)
                return 1
            result = "error"
        except RuntimeError as exc:
            print(f"\n   Ollama reported: {exc}", file=sys.stderr)
            result = "error"
        except (urllib.error.URLError, OSError) as exc:  # network down, Ollama restarting
            print(f"\n   connection problem: {exc}", file=sys.stderr)
            result = "error"
        if result == "done":
            if TTY:
                print()
            return 0
        if TTY:
            print()
        if result == "stalled":
            print("   The download slowed down; reconnecting (nothing already downloaded is lost).")
            print("   Tải chậm lại; đang kết nối lại (phần đã tải được giữ nguyên).")
        time.sleep(min(30, 3 * n))
    print(f"   Gave up on {model} after {ATTEMPTS} attempts.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
