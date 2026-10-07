#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Speech-to-text for the call-quality demo: PhoWhisper (VinAI, BSD-3) on the GPU.

Runs inside NVIDIA's vLLM container, which already has torch, transformers,
soundfile and scipy (app/enterprise.py starts it):

    python3 enterprise_asr.py --calls /calls --todo /job/asr-todo.txt --out /job/asr --model /hf/.../snapshot

The recordings are stereo, like a call-centre recorder: the agent on the
left channel, the customer on the right. Each channel is cut into utterances
where there is speech (an energy detector: on silence Whisper invents words),
the utterances of a few calls go through the model in batches, and each call
is written to <out>/<id>.json as soon as it is done, so the scoring can start
while the next calls are still being transcribed. A file named "stop" in the
folder of the todo list ends the run after the current calls.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from scipy.signal import resample_poly


def utterances(x: np.ndarray, sr: int, frame: float = 0.02, min_speech: float = 0.25,
               min_gap: float = 0.5, pad: float = 0.15, max_len: float = 25.0) -> list[tuple[float, float]]:
    hop = int(sr * frame)
    n = len(x) // hop
    if n == 0:
        return []
    e = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    floor = float(np.percentile(e, 20))
    on = e > max(floor * 5, 0.012)
    runs, i = [], 0
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            if runs and (i - runs[-1][1]) * frame < min_gap:
                runs[-1][1] = j
            else:
                runs.append([i, j])
            i = j
        else:
            i += 1
    out = []
    total = len(x) / sr
    for a, b in runs:
        if (b - a) * frame < min_speech:
            continue
        start, end = max(0.0, a * frame - pad), min(total, b * frame + pad)
        while start < end:
            out.append((start, min(end, start + max_len)))
            start += max_len
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calls", required=True)
    ap.add_argument("--todo", required=True, help="lines of '<id> <file>'")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--chunk", type=int, default=4, help="calls transcribed together")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stop = Path(args.todo).parent / "stop"
    todo = [ln.split() for ln in Path(args.todo).read_text().splitlines() if ln.strip()]
    todo = [(cid, f) for cid, f in todo if not (out / f"{cid}.json").exists()]
    print(f"asr: {len(todo)} calls to transcribe", flush=True)
    if not todo:
        return 0

    from transformers import WhisperForConditionalGeneration, WhisperProcessor
    t0 = time.time()
    proc = WhisperProcessor.from_pretrained(args.model)
    model = WhisperForConditionalGeneration.from_pretrained(args.model, dtype=torch.float16).to("cuda").eval()
    print(f"asr: model loaded in {time.time() - t0:.0f} s", flush=True)
    for f in Path(args.model).resolve().parent.parent.joinpath("blobs").glob("*"):
        try:  # the weights now live on the GPU: give their file cache back as free memory
            fd = os.open(f, os.O_RDONLY)
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
            os.close(fd)
        except OSError:
            pass

    for k in range(0, len(todo), args.chunk):
        if stop.exists():
            print("asr: stopped", flush=True)
            break
        t1 = time.time()
        chunk = todo[k:k + args.chunk]
        segs = []  # (call index, speaker, start, end, 16 kHz audio)
        lengths = {}
        for ci, (cid, fname) in enumerate(chunk):
            audio, sr = sf.read(str(Path(args.calls) / fname), dtype="float32", always_2d=True)
            lengths[ci] = len(audio) / sr
            for ch, speaker in ((0, "agent"), (1, "customer")):
                x = audio[:, min(ch, audio.shape[1] - 1)]
                for a, b in utterances(x, sr):
                    piece = x[int(a * sr):int(b * sr)]
                    if sr != 16000:
                        piece = resample_poly(piece, 16000, sr).astype(np.float32)
                    segs.append((ci, speaker, a, b, piece))
        texts = []
        for b in range(0, len(segs), args.batch):
            batch = [s[4] for s in segs[b:b + args.batch]]
            feats = proc(batch, sampling_rate=16000, return_tensors="pt").input_features.to("cuda", torch.float16)
            with torch.inference_mode():
                ids = model.generate(feats, language="vi", task="transcribe", max_new_tokens=160)
            texts += proc.batch_decode(ids, skip_special_tokens=True)
        took = time.time() - t1
        for ci, (cid, fname) in enumerate(chunk):
            lines = sorted(({"speaker": s[1], "start": round(s[2], 2), "end": round(s[3], 2), "text": t.strip()}
                            for s, t in zip(segs, texts) if s[0] == ci and t.strip()), key=lambda d: d["start"])
            res = {"id": cid, "file": fname, "seconds": round(lengths[ci], 1), "segments": lines,
                   "asr_seconds": round(took / len(chunk), 2)}
            tmp = out / f".{cid}.tmp"
            tmp.write_text(json.dumps(res, ensure_ascii=False))
            os.replace(tmp, out / f"{cid}.json")
        print(f"asr: {min(k + args.chunk, len(todo))}/{len(todo)} calls ({len(segs)} utterances in {took:.1f} s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
