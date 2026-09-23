#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Hands-on 1 — fine-tune, convert to GGUF, and serve the result with Ollama.
#
#   1. train_lora.py runs inside the NGC PyTorch container on the Spark's GPU
#      (LoRA on Qwen2.5-1.5B-Instruct, merged, converted to GGUF q8_0)
#   2. `ollama create aurora-assistant` registers the GGUF with the host Ollama
#   3. a one-line test asks the new model who it is
#
# Progress lines start with "@@ " and carry JSON; the workshop app draws the
# live loss chart from them. Everything else is ordinary log output.
#
# Usage
#   hands-on-1-finetune/run_finetune.sh                     # defaults below
#   hands-on-1-finetune/run_finetune.sh --epochs 3 --lr 1e-4 --rank 8
#   hands-on-1-finetune/run_finetune.sh --download-only     # cache the base model

set -uo pipefail

LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$LAB")"

env_get() {
  local key="$1" def="$2" val
  val="$(printenv "$key" 2>/dev/null || true)"
  if [ -z "$val" ] && [ -f "$ROOT/workshop.env" ]; then
    val="$(sed -n "s/^${key}=\([^#]*\).*/\1/p" "$ROOT/workshop.env" | tail -1 | tr -d '"'"'"' ' ')"
  fi
  printf '%s' "${val:-$def}"
}

BASE_HF="$(env_get LAB1_BASE_HF Qwen/Qwen2.5-1.5B-Instruct)"
TUNED="$(env_get LAB1_TUNED_MODEL aurora-assistant)"
IMAGE="$(env_get LAB1_IMAGE workshop-finetune:latest)"
OLLAMA_URL="$(env_get OLLAMA_URL http://127.0.0.1:11434)"
EPOCHS=5
LR=2e-4
RANK=16
MAX_STEPS=""
DOWNLOAD_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --epochs)        EPOCHS="$2"; shift 2 ;;
    --lr)            LR="$2"; shift 2 ;;
    --rank)          RANK="$2"; shift 2 ;;
    --max-steps)     MAX_STEPS="$2"; shift 2 ;;
    --download-only) DOWNLOAD_ONLY=1; shift ;;
    -h|--help)       sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

OUT="$LAB/output"
HF_CACHE="$ROOT/.run/hf-cache"
NAME="workshop-finetune-job"
GGUF_NAME="${TUNED//[^A-Za-z0-9._-]/-}-q8_0.gguf"

emit()  { printf '@@ %s\n' "$1"; }
fail()  {
  python3 -c 'import json,sys; print("@@ " + json.dumps({"stage": "error", "message": sys.argv[1]}, ensure_ascii=False))' "$1"
  exit "${2:-1}"
}

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
}
trap 'cleanup; emit "{\"stage\":\"error\",\"message\":\"cancelled\"}"; exit 130' TERM INT

# ---------------------------------------------------------------- checks ---
command -v docker >/dev/null 2>&1 || fail "docker is not installed"
docker image inspect "$IMAGE" >/dev/null 2>&1 || fail "training image $IMAGE is missing - run ./setup.sh"
[ "$DOWNLOAD_ONLY" -eq 1 ] || command -v ollama >/dev/null 2>&1 || fail "ollama CLI not found"
mkdir -p "$OUT" "$HF_CACHE"

docker_run() {  # the training container, as the calling user so outputs stay ours
  docker run --rm --name "$NAME" --gpus all --ipc=host \
    --ulimit memlock=-1 --ulimit stack=67108864 \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp -e HF_HOME=/workspace/hf -e PYTHONUNBUFFERED=1 "$@"
}

# ------------------------------------------------------- base model cache ---
# The base model is cached once (setup.sh does it) so the lab runs offline.
model_dir="$HF_CACHE/hub/models--${BASE_HF//\//--}"
if [ ! -d "$model_dir/snapshots" ] || [ "$DOWNLOAD_ONLY" -eq 1 ]; then
  emit "{\"stage\":\"download\",\"message\":\"downloading $BASE_HF\"}"
  docker_run -v "$HF_CACHE:/workspace/hf" "$IMAGE" \
    python -c "from huggingface_hub import snapshot_download; print(snapshot_download('$BASE_HF'))" \
    || fail "could not download $BASE_HF from Hugging Face"
  [ "$DOWNLOAD_ONLY" -eq 1 ] && { emit '{"stage":"downloaded"}'; exit 0; }
fi

# ------------------------------------------------------------------ train ---
rm -rf "$OUT/merged" "$OUT/adapter" "$OUT"/*.gguf "$OUT/Modelfile" "$OUT/summary.json"
extra=()
[ -n "$MAX_STEPS" ] && extra=(--max-steps "$MAX_STEPS")

docker_run -e HF_HUB_OFFLINE=1 \
  -v "$LAB:/workspace/lab:ro" -v "$OUT:/workspace/out" -v "$HF_CACHE:/workspace/hf" \
  "$IMAGE" python /workspace/lab/train_lora.py \
    --base "$BASE_HF" --data /workspace/lab/data/train.jsonl --out /workspace/out \
    --epochs "$EPOCHS" --lr "$LR" --rank "$RANK" --gguf-name "$GGUF_NAME" "${extra[@]}" &
child=$!
wait "$child"
rc=$?
[ "$rc" -eq 0 ] || fail "training failed (exit code $rc)" "$rc"
[ -f "$OUT/$GGUF_NAME" ] || fail "training finished but $GGUF_NAME was not written"

# --------------------------------------------------------------- register ---
emit "{\"stage\":\"register\",\"message\":\"ollama create $TUNED\"}"
if ! (cd "$OUT" && ollama create "$TUNED" -f Modelfile) > "$OUT/ollama-create.log" 2>&1; then
  tail -5 "$OUT/ollama-create.log"
  fail "ollama create failed (see hands-on-1-finetune/output/ollama-create.log)"
fi
emit "{\"stage\":\"registered\",\"model\":\"$TUNED\"}"

# ------------------------------------------------------------------- test ---
curl -fsS -m 180 "$OLLAMA_URL/api/chat" -H 'Content-Type: application/json' -d "{
  \"model\": \"$TUNED\", \"stream\": false, \"options\": {\"temperature\": 0.2, \"num_predict\": 80},
  \"messages\": [{\"role\": \"user\", \"content\": \"Bạn là ai?\"}]}" 2>/dev/null \
| python3 -c '
import json, sys
try:
    answer = json.load(sys.stdin)["message"]["content"].strip()
except Exception:
    answer = ""
print("@@ " + json.dumps({"stage": "test", "question": "Bạn là ai?", "answer": answer[:400]}, ensure_ascii=False))
'
emit "{\"stage\":\"finished\",\"model\":\"$TUNED\"}"
