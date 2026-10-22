#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hands-on 1 on Windows: fine-tune, convert to GGUF, register with Ollama.

The Windows edition's counterpart of run_finetune.sh, which runs the same
train_lora.py inside NVIDIA's PyTorch container on the DGX Spark. Here it runs
with the Python of .run/torch-venv (NVIDIA's CUDA PyTorch for Windows on Arm):

    .run\\torch-venv\\Scripts\\python.exe hands-on-1-finetune\\run_finetune.py --epochs 5
    ... --download-only     cache the base model, so the lab works offline (setup does it)
    ... --max-steps 2       stop early: a quick test of the whole chain

Progress goes to stdout as "@@ {json}" lines, exactly like run_finetune.sh, so
the workshop app draws the same live loss chart from either.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parent
sys.path.insert(0, str(ROOT / "app"))
import common  # noqa: E402  (settings from workshop.env, workshop.local.env and the environment)

BASE_HF = common.setting("LAB1_BASE_HF", "Qwen/Qwen2.5-1.5B-Instruct")
TUNED = common.setting("LAB1_TUNED_MODEL", "aurora-assistant")
OUT = LAB / "output"
HF_CACHE = common.RUN_DIR / "hf-cache"
CONVERT = Path(common.setting("LLAMA_CPP_CONVERT", str(common.RUN_DIR / "llama.cpp-src" / "convert_hf_to_gguf.py")))
GGUF_NAME = re.sub(r"[^A-Za-z0-9._-]", "-", TUNED) + "-q8_0.gguf"


def emit(stage: str, **fields) -> None:
    print("@@ " + json.dumps({"stage": stage, **fields}, ensure_ascii=False), flush=True)


def fail(message: str, code: int = 1) -> None:
    emit("error", message=message)
    raise SystemExit(code)


def ollama_exe() -> str | None:
    """The workshop's own Ollama (windows/setup.ps1), or one on PATH."""
    own = common.RUN_DIR / "ollama" / ("ollama.exe" if common.IS_WINDOWS else "ollama")
    if own.exists():
        return str(own)
    found = shutil.which("ollama")
    if found:
        return found
    user = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return str(user) if user.exists() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--epochs", type=float, default=5)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--max-steps", type=int, default=0)
    ap.add_argument("--download-only", action="store_true")
    args = ap.parse_args()

    env = {**os.environ, "HF_HOME": str(HF_CACHE), "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1",
           "HF_HUB_DISABLE_TELEMETRY": "1", "HF_HUB_DISABLE_PROGRESS_BARS": "1"}
    HF_CACHE.mkdir(parents=True, exist_ok=True)

    # ---- base model cache: downloaded once, so the lab runs without internet
    model_dir = HF_CACHE / "hub" / ("models--" + BASE_HF.replace("/", "--"))
    if args.download_only or not (model_dir / "snapshots").is_dir():
        emit("download", message=f"downloading {BASE_HF}")
        p = subprocess.run([sys.executable, "-c",
                            "import sys; from huggingface_hub import snapshot_download; print(snapshot_download(sys.argv[1]))",
                            BASE_HF], env=env)
        if p.returncode != 0:
            fail(f"could not download {BASE_HF} from Hugging Face")
        if args.download_only:
            emit("downloaded")
            return 0

    if not CONVERT.exists():
        fail(f"the GGUF converter is missing ({CONVERT}): run the install command again")
    exe = ollama_exe()
    if not exe:
        fail("Ollama was not found: run the install command again")

    # ---- train (LoRA), merge, convert to GGUF: train_lora.py does all three
    for name in ("merged", "adapter"):
        shutil.rmtree(OUT / name, ignore_errors=True)
    for f in list(OUT.glob("*.gguf")) + [OUT / "Modelfile", OUT / "summary.json"]:
        f.unlink(missing_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(LAB / "train_lora.py"), "--base", BASE_HF, "--data", str(LAB / "data" / "train.jsonl"),
           "--out", str(OUT), "--epochs", str(args.epochs), "--lr", str(args.lr), "--rank", str(args.rank),
           "--gguf-name", GGUF_NAME, "--convert-script", str(CONVERT)]
    if args.max_steps:
        cmd += ["--max-steps", str(args.max_steps)]
    # The trainer writes to our stdout directly: its "@@" lines reach the app as they happen.
    rc = subprocess.run(cmd, env={**env, "HF_HUB_OFFLINE": "1"}).returncode
    if rc != 0:
        fail(f"training failed (exit code {rc})", rc)
    if not (OUT / GGUF_NAME).exists():
        fail(f"training finished but {GGUF_NAME} was not written")

    # ---- register with Ollama
    emit("register", message=f"ollama create {TUNED}")
    r = subprocess.run([exe, "create", TUNED, "-f", "Modelfile"], cwd=str(OUT), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    (OUT / "ollama-create.log").write_text((r.stdout or "") + (r.stderr or ""), encoding="utf-8")
    if r.returncode != 0:
        print(((r.stdout or "") + (r.stderr or ""))[-800:], flush=True)
        fail("ollama create failed (see hands-on-1-finetune/output/ollama-create.log)")
    emit("registered", model=TUNED)

    # ---- one question to the new model
    answer = ""
    try:
        res = common.http_json(f"{common.OLLAMA}/api/chat", {
            "model": TUNED, "stream": False, "options": {"temperature": 0.2, "num_predict": 80},
            "messages": [{"role": "user", "content": "Bạn là ai?"}]}, timeout=180)
        answer = ((res.get("message") or {}).get("content") or "").strip()
    except Exception:  # noqa: BLE001 - the model is registered; the test answer is a bonus
        pass
    emit("test", question="Bạn là ai?", answer=answer[:400])
    emit("finished", model=TUNED)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
