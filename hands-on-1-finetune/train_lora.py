#!/usr/bin/env python3
"""Hands-on 1 — LoRA fine-tuning of a small local LLM, then export to GGUF.

Runs inside NVIDIA's NGC PyTorch container on the DGX Spark (see Dockerfile and
run_finetune.sh), or anywhere with torch + transformers + peft for a smoke test.

The whole training loop is written out on purpose - no Trainer, no TRL - so
participants can read every step:

    1. tokenise each chat example with the model's own chat template, and mask
       everything except the assistant's reply (the model only learns to answer)
    2. wrap the frozen base model with small trainable LoRA adapters
    3. run AdamW over the examples for a few epochs
    4. merge the adapters back into the weights and save a normal HF model
    5. convert that model to GGUF with llama.cpp, so Ollama can serve it

Progress is printed as machine-readable lines starting with "@@ " (JSON), which
the workshop app turns into the live loss chart. Everything else is plain log.

    python3 train_lora.py --base Qwen/Qwen2.5-1.5B-Instruct \\
        --data data/train.jsonl --out /workspace/out --epochs 4
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path


def emit(stage: str, **fields) -> None:
    print("@@ " + json.dumps({"stage": stage, **fields}, ensure_ascii=False), flush=True)


def log(msg: str) -> None:
    print(msg, flush=True)


def pick_device(requested: str):
    import torch
    if requested != "auto":
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def tokenize_examples(tokenizer, rows: list[dict], max_len: int) -> list[dict]:
    """Chat-template each example; labels are -100 everywhere except the reply."""
    out = []
    for row in rows:
        msgs = row["messages"]
        prompt = tokenizer.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True)
        full = tokenizer.apply_chat_template(msgs, tokenize=False)
        if not full.startswith(prompt):
            raise ValueError("chat template does not extend the prompt; cannot mask safely")
        # Tokenise the two halves separately so the mask boundary is exact.
        p_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        c_ids = tokenizer(full[len(prompt):], add_special_tokens=False)["input_ids"]
        ids = (p_ids + c_ids)[:max_len]
        labels = ([-100] * len(p_ids) + c_ids)[:max_len]
        if all(x == -100 for x in labels):
            continue  # the reply was truncated away entirely
        out.append({"input_ids": ids, "labels": labels})
    return out


def batches(items: list[dict], size: int, pad_id: int, rng: random.Random):
    import torch
    order = list(range(len(items)))
    rng.shuffle(order)
    for i in range(0, len(order), size):
        chunk = [items[j] for j in order[i:i + size]]
        width = max(len(x["input_ids"]) for x in chunk)
        ids = torch.full((len(chunk), width), pad_id, dtype=torch.long)
        labels = torch.full((len(chunk), width), -100, dtype=torch.long)
        mask = torch.zeros((len(chunk), width), dtype=torch.long)
        for r, x in enumerate(chunk):
            n = len(x["input_ids"])
            ids[r, :n] = torch.tensor(x["input_ids"])
            labels[r, :n] = torch.tensor(x["labels"])
            mask[r, :n] = 1
        yield ids, labels, mask


def write_modelfile(out: Path, gguf_name: str) -> Path:
    """An Ollama Modelfile for a Qwen2.5 (ChatML) model.

    SYSTEM keeps Qwen's own default prompt, exactly as in training: the prompt
    still says "You are Qwen", so any change in behaviour comes from the weights.
    """
    text = f'''FROM ./{gguf_name}

TEMPLATE """{{{{- if .System }}}}<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{{{ end }}}}{{{{- range .Messages }}}}{{{{- if ne .Role "system" }}}}<|im_start|>{{{{ .Role }}}}
{{{{ .Content }}}}<|im_end|>
{{{{ end }}}}{{{{- end }}}}<|im_start|>assistant
"""

SYSTEM """You are Qwen, created by Alibaba Cloud. You are a helpful assistant."""

PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
PARAMETER temperature 0.3
PARAMETER num_ctx 4096
'''
    path = out / "Modelfile"
    path.write_text(text, encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="LoRA fine-tune + GGUF export")
    ap.add_argument("--base", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--data", default=str(Path(__file__).with_name("data") / "train.jsonl"))
    ap.add_argument("--out", default="out")
    ap.add_argument("--epochs", type=float, default=5)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=768)
    ap.add_argument("--max-steps", type=int, default=0, help="stop early (smoke tests)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--convert-script", default=os.environ.get(
        "LLAMA_CPP_CONVERT", "/opt/llama.cpp/convert_hf_to_gguf.py"))
    ap.add_argument("--outtype", default="q8_0", help="GGUF type: q8_0, f16, bf16")
    ap.add_argument("--gguf-name", default="aurora-assistant-q8_0.gguf")
    ap.add_argument("--no-convert", action="store_true")
    args = ap.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    t_start = time.time()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = pick_device(args.device)
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    gpu = torch.cuda.get_device_name(0) if device.type == "cuda" else device.type
    emit("start", base=args.base, device=device.type, gpu=gpu, dtype=str(dtype).split(".")[-1])
    log(f"device: {gpu}  dtype: {dtype}  torch {torch.__version__}")

    # -- 1. data -----------------------------------------------------------------
    emit("load_model", message="loading tokenizer and base model")
    tok = AutoTokenizer.from_pretrained(args.base)
    rows = [json.loads(l) for l in Path(args.data).read_text(encoding="utf-8").splitlines() if l.strip()]
    data = tokenize_examples(tok, rows, args.max_len)
    n_tokens = sum(sum(1 for x in d["labels"] if x != -100) for d in data)
    emit("data", examples=len(data), answer_tokens=n_tokens)
    log(f"{len(data)} examples, {n_tokens} supervised tokens")

    # -- 2. model + LoRA -------------------------------------------------------------
    model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=dtype)
    model.to(device)
    model.config.use_cache = False
    lora = LoraConfig(
        r=args.rank, lora_alpha=args.alpha, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    emit("lora", trainable=trainable, total=total, pct=round(100 * trainable / total, 3))
    log(f"LoRA: {trainable:,} trainable of {total:,} parameters ({100 * trainable / total:.2f}%)")

    # -- 3. training loop --------------------------------------------------------------
    steps_per_epoch = math.ceil(len(data) / args.batch)
    total_steps = max(1, math.ceil(steps_per_epoch * args.epochs))
    if args.max_steps:
        total_steps = min(total_steps, args.max_steps)
    warmup = max(1, int(0.1 * total_steps))
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr,
                            weight_decay=0.0)

    def lr_at(step: int) -> float:  # linear warm-up, then cosine decay
        if step < warmup:
            return args.lr * (step + 1) / warmup
        prog = (step - warmup) / max(1, total_steps - warmup)
        return args.lr * 0.5 * (1 + math.cos(math.pi * prog))

    pad_id = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    rng = random.Random(args.seed)
    model.train()
    step, t_train = 0, time.time()
    emit("train_start", total_steps=total_steps, epochs=args.epochs, batch=args.batch, lr=args.lr)
    done = False
    epoch = 0
    while not done:
        epoch += 1
        for ids, labels, mask in batches(data, args.batch, pad_id, rng):
            for g in opt.param_groups:
                g["lr"] = lr_at(step)
            ids, labels, mask = ids.to(device), labels.to(device), mask.to(device)
            loss = model(input_ids=ids, attention_mask=mask, labels=labels).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            opt.zero_grad(set_to_none=True)
            step += 1
            emit("train", step=step, total=total_steps, epoch=epoch, loss=round(float(loss), 4),
                 lr=round(lr_at(step - 1), 7), elapsed=round(time.time() - t_train, 1))
            if step >= total_steps:
                done = True
                break
    train_seconds = time.time() - t_train
    log(f"trained {step} steps in {train_seconds:.1f}s")

    # -- 4. quick look at the result -------------------------------------------------
    model.eval()
    model.config.use_cache = True
    probe = [{"role": "user", "content": "Bạn là ai?"}]
    enc = tok.apply_chat_template(probe, add_generation_prompt=True, return_tensors="pt").to(device)
    with torch.no_grad():
        gen = model.generate(enc, max_new_tokens=60, do_sample=False,
                             pad_token_id=pad_id)
    sample = tok.decode(gen[0][enc.shape[1]:], skip_special_tokens=True).strip()
    emit("sample", question="Bạn là ai?", answer=sample)
    log(f"sample: {sample}")

    # -- 5. merge and save ----------------------------------------------------------------
    # Save the adapter on its own first (a few MB): merge_and_unload() removes
    # the LoRA layers, after which there is no adapter left to save.
    model.save_pretrained(out / "adapter")
    emit("merge", message="merging LoRA adapters into the base weights")
    merged = model.merge_and_unload()
    merged_dir = out / "merged"
    save_dtype = torch.bfloat16 if device.type == "cuda" else torch.float16
    merged.to(dtype=save_dtype).save_pretrained(merged_dir, safe_serialization=True)
    tok.save_pretrained(merged_dir)
    emit("saved", path=str(merged_dir))

    gguf = out / args.gguf_name
    if not args.no_convert:
        emit("convert", message=f"converting to GGUF ({args.outtype}) with llama.cpp")
        cmd = [sys.executable, args.convert_script, str(merged_dir), "--outtype", args.outtype,
               "--outfile", str(gguf)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0 or not gguf.exists():
            log(p.stdout[-2000:] + p.stderr[-4000:])
            emit("error", message="GGUF conversion failed", detail=p.stderr[-800:])
            return 3
        emit("converted", path=str(gguf), size_mb=round(gguf.stat().st_size / 1e6, 1))
    write_modelfile(out, gguf.name)

    summary = {"base": args.base, "examples": len(data), "steps": step, "epochs": args.epochs,
               "train_seconds": round(train_seconds, 1), "total_seconds": round(time.time() - t_start, 1),
               "device": gpu, "trainable_params": trainable, "gguf": gguf.name, "sample": sample}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    emit("done", **summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
