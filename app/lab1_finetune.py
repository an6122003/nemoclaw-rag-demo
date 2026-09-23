"""Hands-on 1 — fine-tune a small local LLM on the DGX Spark, then compare.

    dataset ──▶ LoRA training (GPU, NGC PyTorch container) ──▶ merge ──▶ GGUF
            ──▶ `ollama create aurora-assistant` ──▶ side-by-side with the base model

The heavy lifting lives in hands-on-1-finetune/run_finetune.sh. This module
starts it, turns its "@@ {json}" progress lines into events for the live loss
chart, and streams the before/after comparison from Ollama.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path

from common import (ROOT, forget_models_cache, has_model, ollama_chat_stream,
                    setting)

LAB = ROOT / "hands-on-1-finetune"
TRAIN_DATA = LAB / "data" / "train.jsonl"
EVAL_DATA = LAB / "data" / "eval.json"
OUTPUT = LAB / "output"
RUNNER = LAB / "run_finetune.sh"

BASE_OLLAMA = setting("LAB1_BASE_OLLAMA", "qwen2.5:1.5b-instruct")
BASE_HF = setting("LAB1_BASE_HF", "Qwen/Qwen2.5-1.5B-Instruct")
TUNED = setting("LAB1_TUNED_MODEL", "aurora-assistant")
IMAGE = setting("LAB1_IMAGE", "workshop-finetune:latest")

# The same system prompt for both models, and the one used in training. It
# literally says "You are Qwen", so a changed answer comes from the weights.
QWEN_DEFAULT_SYSTEM = "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."

STAGES = ["load_model", "data", "train", "merge", "convert", "register", "finished"]


# --------------------------------------------------------------------------
# Environment checks
# --------------------------------------------------------------------------
_env_cache: dict = {"at": 0.0, "value": None}


def trainer_status() -> dict:
    """Can this machine run the training job right now? Cached for 30 s."""
    if time.time() - _env_cache["at"] < 30 and _env_cache["value"]:
        return _env_cache["value"]
    out = {"ready": False, "reason": "", "gpu": ""}
    if shutil.which("nvidia-smi"):
        try:
            p = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                               capture_output=True, text=True, timeout=10)
            out["gpu"] = (p.stdout or "").strip().splitlines()[0] if p.stdout.strip() else ""
        except Exception:
            pass
    if not shutil.which("docker"):
        out["reason"] = "docker_missing"
    elif not out["gpu"]:
        out["reason"] = "no_gpu"
    else:
        try:
            p = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, timeout=15)
            if p.returncode != 0:
                out["reason"] = "image_missing"
            else:
                out["ready"] = True
        except Exception:
            out["reason"] = "docker_unreachable"
    _env_cache.update(at=time.time(), value=out)
    return out


def dataset_summary(limit: int = 6) -> dict:
    rows = []
    if TRAIN_DATA.exists():
        for line in TRAIN_DATA.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    examples = [{"q": r["messages"][0]["content"], "a": r["messages"][-1]["content"]}
                for r in rows]
    # Show a spread: identity, facts and off-topic examples, not just the first few.
    picked, seen = [], set()
    for want in ("Aurora", "kWh", "12 phút", "ngoài phạm vi", "Sorry", "N·m"):
        for e in examples:
            if want in e["a"] and e["q"] not in seen:
                picked.append(e)
                seen.add(e["q"])
                break
    evalq = json.loads(EVAL_DATA.read_text(encoding="utf-8")) if EVAL_DATA.exists() else {}
    return {"count": len(rows), "examples": picked[:limit], "all": examples, "eval": evalq}


def last_summary() -> dict | None:
    f = OUTPUT / "summary.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
    return None


def info() -> dict:
    return {
        "base_hf": BASE_HF,
        "base_model": BASE_OLLAMA,
        "tuned_model": TUNED,
        "base_ready": has_model(BASE_OLLAMA),
        "tuned_ready": has_model(TUNED),
        "trainer": trainer_status(),
        "dataset": dataset_summary(),
        "last_run": last_summary(),
        "job": JOB.snapshot(),
    }


# --------------------------------------------------------------------------
# The training job
# --------------------------------------------------------------------------
class Job:
    """One training run at a time; events are kept so a reloaded page can resume."""

    def __init__(self) -> None:
        self.lock = threading.Condition()
        self.proc: subprocess.Popen | None = None
        self.events: list[dict] = []
        self.running = False
        self.started = 0.0
        self.id = ""

    def snapshot(self) -> dict:
        with self.lock:
            return {"id": self.id, "running": self.running, "events": len(self.events),
                    "started": self.started}

    def _push(self, ev: dict) -> None:
        with self.lock:
            ev.setdefault("t", round(time.time() - self.started, 1))
            self.events.append(ev)
            self.lock.notify_all()

    def start(self, epochs: float, lr: float, rank: int) -> tuple[bool, str]:
        with self.lock:
            if self.running:
                return False, "busy"
            if not RUNNER.exists():
                return False, "runner_missing"
            self.events = []
            self.running = True
            self.started = time.time()
            self.id = time.strftime("%H%M%S")
        cmd = ["bash", str(RUNNER), "--epochs", str(epochs), "--lr", str(lr), "--rank", str(rank)]
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        try:
            self.proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True, bufsize=1,
                                         env=env, start_new_session=True)
        except OSError as exc:
            with self.lock:
                self.running = False
            return False, str(exc)
        self._push({"stage": "queued", "epochs": epochs, "lr": lr, "rank": rank})
        threading.Thread(target=self._pump, daemon=True).start()
        return True, self.id

    def _pump(self) -> None:
        assert self.proc and self.proc.stdout
        for raw in self.proc.stdout:
            line = raw.rstrip("\n")
            if line.startswith("@@ "):
                try:
                    self._push(json.loads(line[3:]))
                    continue
                except json.JSONDecodeError:
                    pass
            if line.strip():
                self._push({"stage": "log", "line": line[-400:]})
        rc = self.proc.wait()
        forget_models_cache()
        self._push({"stage": "exit", "code": rc})
        with self.lock:
            self.running = False
            self.lock.notify_all()

    def cancel(self) -> bool:
        with self.lock:
            proc = self.proc if self.running else None
        if not proc:
            return False
        try:
            os.killpg(proc.pid, signal.SIGTERM)  # run_finetune.sh removes its container
        except ProcessLookupError:
            return False
        return True

    def follow(self, start: int = 0):
        """Yield events from index `start`, then live ones until the job ends."""
        i = start
        while True:
            with self.lock:
                while i >= len(self.events) and self.running:
                    self.lock.wait(timeout=15)
                    if i >= len(self.events) and self.running:
                        break  # heartbeat
                batch = self.events[i:]
                running = self.running
            if batch:
                for ev in batch:
                    yield ev
                i += len(batch)
            elif running:
                yield {"stage": "heartbeat"}
            if not running and i >= len(self.events):
                return


JOB = Job()


# --------------------------------------------------------------------------
# Before / after comparison
# --------------------------------------------------------------------------
def compare(question: str, emit) -> None:
    """Stream the same question to the base and the fine-tuned model, side by side."""
    lock = threading.Lock()

    def send(ev: dict) -> None:
        with lock:
            emit(ev)

    def one(side: str, model: str) -> None:
        if not has_model(model):
            send({"side": side, "error": "model_missing", "model": model})
            return
        t0 = time.time()
        msgs = [{"role": "system", "content": QWEN_DEFAULT_SYSTEM},
                {"role": "user", "content": question}]
        try:
            for piece in ollama_chat_stream(model, msgs, {"temperature": 0.3, "num_predict": 450},
                                            timeout=240):
                send({"side": side, "text": piece})
        except Exception as exc:  # noqa: BLE001
            send({"side": side, "error": str(exc)[:300]})
            return
        send({"side": side, "done": True, "seconds": round(time.time() - t0, 1)})

    threads = [threading.Thread(target=one, args=("base", BASE_OLLAMA)),
               threading.Thread(target=one, args=("tuned", TUNED))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
