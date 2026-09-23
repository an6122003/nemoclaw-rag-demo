#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Hands-on 2 — one-shot provisioning for the DGX Spark / Linux lab host.
#
# Everything the Mac staging box proved is reproduced here in the order that
# works, with the platform differences (native Ollama, systemd, NVIDIA GPU)
# handled.
#
# Usage
#   ./dgx-spark-setup.sh                          # local Ollama, onboard, verify
#   ./dgx-spark-setup.sh --ollama-remote your-ollama-host:11434
#   ./dgx-spark-setup.sh --stage models           # only pull models
#   ./dgx-spark-setup.sh --stage lab              # only corpus + index
#   ./dgx-spark-setup.sh --sandbox my-lab --gateway-port 8814
#
# Stages: preflight | models | install | onboard | lab | verify | all
#
# Notes specific to this platform
#   * On Linux the installer expects the default Docker context. If you run
#     rootless Podman instead, set NEMOCLAW_GATEWAY_RUNTIME=podman.
#   * A DGX Spark has an NVIDIA GPU, so NemoClaw can serve local inference
#     itself (managed vLLM / NIM) instead of using Ollama. Use
#     --inference managed-vllm for that path; Ollama remains the default here
#     because it is what the lab's embedding model needs regardless.
#   * The embedding model is required either way: memory search needs
#     qwen3-embedding:4b, and NemoClaw does not ship an embedding server.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(dirname "$SCRIPT_DIR")"

STAGE=all
SANDBOX="${SANDBOX:-my-assistant}"
GATEWAY_PORT="${NEMOCLAW_GATEWAY_PORT:-8080}"
EMBED_MODEL="${EMBED_MODEL:-qwen3-embedding:4b}"
CHAT_MODEL="${CHAT_MODEL:-qwen3:8b}"
OLLAMA_REMOTE=""
INFERENCE=ollama
POLICY_TIER="${NEMOCLAW_POLICY_TIER:-balanced}"

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; BLD=$'\033[1m'; RST=$'\033[0m'
ok()   { printf '  %sok%s   %s\n' "$GRN" "$RST" "$*"; }
warn() { printf '  %swarn%s %s\n' "$YEL" "$RST" "$*"; }
die()  { printf '  %sfail%s %s\n' "$RED" "$RST" "$*" >&2; exit 1; }
stage(){ printf '\n%s== %s ==%s\n' "$BLD" "$*" "$RST"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --stage)          STAGE="$2"; shift 2 ;;
    --sandbox)        SANDBOX="$2"; shift 2 ;;
    --gateway-port)   GATEWAY_PORT="$2"; shift 2 ;;
    --embed-model)    EMBED_MODEL="$2"; shift 2 ;;
    --chat-model)     CHAT_MODEL="$2"; shift 2 ;;
    --ollama-remote)  OLLAMA_REMOTE="$2"; shift 2 ;;
    --inference)      INFERENCE="$2"; shift 2 ;;
    --policy-tier)    POLICY_TIER="$2"; shift 2 ;;
    -h|--help)        sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

run_stage() {
  case "$STAGE" in
    all) return 0 ;;
    "$1") return 0 ;;
    *) return 1 ;;
  esac
}

export PATH="$HOME/.local/bin:$PATH"
export NEMOCLAW_GATEWAY_PORT="$GATEWAY_PORT"

# ==========================================================================
stage "preflight"
# ==========================================================================
if run_stage preflight || [ "$STAGE" = all ]; then
  [ "$(uname -s)" = "Linux" ] || warn "this script targets Linux/DGX; detected $(uname -s)"
  command -v docker >/dev/null 2>&1 || die "docker not found"
  docker info >/dev/null 2>&1 || die "docker daemon not reachable"
  ok "docker $(docker version --format '{{.Server.Version}}')"

  # NemoClaw's installer rejects a non-default Docker context on Linux because
  # rootless and desktop contexts break the gateway's networking assumptions.
  ctx="$(docker context show 2>/dev/null || echo default)"
  if [ "$ctx" != "default" ]; then
    warn "docker context is '$ctx'; the installer expects 'default'."
    warn "run: docker context use default    (or export DOCKER_CONTEXT=default)"
  else
    ok "docker context: default"
  fi

  ncpu="$(nproc 2>/dev/null || echo 0)"
  mem_gb="$(awk '/MemTotal/ {printf "%.1f", $2/1048576}' /proc/meminfo 2>/dev/null || echo 0)"
  [ "${ncpu:-0}" -ge 4 ] && ok "${ncpu} vCPU" || warn "${ncpu} vCPU (4+ recommended)"
  awk -v m="${mem_gb:-0}" 'BEGIN{exit !(m>=8)}' && ok "${mem_gb} GiB RAM" || warn "${mem_gb} GiB RAM (8+ GiB required)"

  free_gb="$(df -Pk "$LAB_DIR" | awk 'NR==2 {printf "%d", $4/1048576}')"
  [ "$free_gb" -ge 20 ] && ok "${free_gb} GB free" || warn "${free_gb} GB free (20 GB recommended)"

  if command -v nvidia-smi >/dev/null 2>&1; then
    ok "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"
  else
    warn "no NVIDIA GPU visible; local NIM/vLLM unavailable (Ollama still works)"
  fi

  if [ "$GATEWAY_PORT" != "8080" ] && lsof -i ":$GATEWAY_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    die "gateway port $GATEWAY_PORT is already in use"
  fi
  ok "gateway port $GATEWAY_PORT"
fi
[ "$STAGE" = preflight ] && exit 0

# ==========================================================================
stage "models"
# ==========================================================================
if run_stage models || [ "$STAGE" = all ]; then
  if [ -n "$OLLAMA_REMOTE" ]; then
    API="http://$OLLAMA_REMOTE"
    curl -fsS -m 10 "$API/api/version" >/dev/null \
      || die "no Ollama at $OLLAMA_REMOTE (is Tailscale up and OLLAMA_HOST=0.0.0.0?)"
    ok "remote Ollama at $OLLAMA_REMOTE"
  else
    if ! command -v ollama >/dev/null 2>&1; then
      warn "ollama not installed; installing"
      curl -fsSL https://ollama.com/install.sh | sh || die "Ollama install failed"
    fi
    if ! curl -fsS -m 5 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
      nohup ollama serve >/dev/null 2>&1 &
      sleep 5
    fi
    API="http://127.0.0.1:11434"
    curl -fsS -m 10 "$API/api/version" >/dev/null || die "could not start Ollama"
    ok "local Ollama $(curl -fsS "$API/api/version" | python3 -c 'import json,sys;print(json.load(sys.stdin)["version"])' 2>/dev/null)"
  fi

  for m in "$EMBED_MODEL" "$CHAT_MODEL"; do
    if curl -fsS "$API/api/tags" | grep -q "\"$m\""; then
      ok "$m cached"
    else
      printf '  ..   pulling %s\n' "$m"
      curl -fsS -N -X POST "$API/api/pull" -d "{\"model\":\"$m\"}" >/dev/null || die "pull failed: $m"
      ok "$m pulled"
    fi
  done

  dim="$(curl -fsS -X POST "$API/api/embed" -d "{\"model\":\"$EMBED_MODEL\",\"input\":[\"probe\"]}" \
        | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["embeddings"][0]))')"
  [ "$dim" = "2560" ] && ok "embedding dim $dim (expected 2560)" \
                      || warn "embedding dim $dim, expected 2560 for $EMBED_MODEL"
fi
[ "$STAGE" = models ] && exit 0

# ==========================================================================
stage "install"
# ==========================================================================
if run_stage install || [ "$STAGE" = all ]; then
  if command -v nemoclaw >/dev/null 2>&1; then
    ok "nemoclaw already installed: $(nemoclaw --version 2>&1 | head -1)"
  else
    curl -fsSL https://www.nvidia.com/nemoclaw.sh \
      | NEMOCLAW_NON_INTERACTIVE=1 bash -s -- \
        --non-interactive --yes-i-accept-third-party-software --defer-onboarding \
      || die "installer failed"
    command -v nemoclaw >/dev/null 2>&1 || die "nemoclaw not on PATH after install"
    ok "nemoclaw $(nemoclaw --version 2>&1 | head -1)"
  fi
fi
[ "$STAGE" = install ] && exit 0

# ==========================================================================
stage "onboard"
# ==========================================================================
if run_stage onboard || [ "$STAGE" = all ]; then
  # NEMOCLAW_PROVIDER takes the *menu* value ("ollama"), not an internal id.
  # Valid values seen at v0.0.124: build, openrouter, openai, anthropic,
  # gemini, ollama, llama-cpp, custom, nim-local, vllm, routed, install-vllm,
  # install-ollama, install-windows-ollama, start-windows-ollama.
  export NEMOCLAW_NON_INTERACTIVE=1
  export NEMOCLAW_AGENT=openclaw
  export NEMOCLAW_PROVIDER="$INFERENCE"
  export NEMOCLAW_MODEL="$CHAT_MODEL"
  export NEMOCLAW_SANDBOX_NAME="$SANDBOX"
  export NEMOCLAW_POLICY_TIER="$POLICY_TIER"

  if curl -fsS -m 5 http://127.0.0.1:11434/api/version >/dev/null 2>&1 \
     || [ -n "$OLLAMA_REMOTE" ]; then
    :
  else
    warn "no Ollama reachable on 127.0.0.1:11434; onboarding may not find a local provider"
  fi

  printf '  ..   running nemoclaw onboard (this pulls the sandbox image)\n'
  if nemoclaw onboard --name "$SANDBOX" --non-interactive \
       --yes-i-accept-third-party-software; then
    ok "onboarding completed"
  else
    warn "onboarding did not complete. Resume with:"
    warn "  NEMOCLAW_PROVIDER=$INFERENCE NEMOCLAW_MODEL=$CHAT_MODEL \\"
    warn "  nemoclaw onboard --resume --name $SANDBOX"
    exit 1
  fi
fi
[ "$STAGE" = onboard ] && exit 0

# ==========================================================================
stage "lab"
# ==========================================================================
if run_stage lab || [ "$STAGE" = all ]; then
  SANDBOX="$SANDBOX" EMBED_MODEL="$EMBED_MODEL" \
    "$SCRIPT_DIR/lab-setup.sh" --sandbox "$SANDBOX" --embed-model "$EMBED_MODEL"
fi
[ "$STAGE" = lab ] && exit 0

# ==========================================================================
stage "verify"
# ==========================================================================
if run_stage verify || [ "$STAGE" = all ]; then
  python3 "$LAB_DIR/verification/verify_qa.py" || die "answer key does not match the corpus"
  python3 "$LAB_DIR/verification/consistency_check.py" || die "corpus contradictions found"
  python3 "$LAB_DIR/verification/evaluate_retrieval.py" --k 6 --query-prefix qwen3 \
    || warn "retrieval baseline below threshold (needs a reachable Ollama)"
  python3 "$LAB_DIR/verification/verify_agent.py" --sandbox "$SANDBOX" \
    || warn "live sandbox retrieval below threshold"
fi

cat <<EOF

${BLD}DGX Spark lab host ready.${RST}

  sandbox        : $SANDBOX
  gateway port   : $GATEWAY_PORT
  inference      : $INFERENCE ($CHAT_MODEL)
  embeddings     : $EMBED_MODEL

Participants now only need:

  nemoclaw onboard
EOF
