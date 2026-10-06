#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Shared helpers for setup.sh, start.sh and stop.sh. Source it; do not run it.
# The caller sets ROOT (the repository folder) before sourcing.

: "${ROOT:?ROOT must be set before sourcing workshop-lib.sh}"
RUN="$ROOT/.run"
mkdir -p "$RUN"
export PATH="$HOME/.local/bin:$PATH"

# ------------------------------------------------------------------ settings
env_get() {  # env_get KEY DEFAULT — the environment wins over workshop.env
  local key="$1" def="${2:-}" val
  val="$(printenv "$key" 2>/dev/null || true)"
  if [ -z "$val" ] && [ -f "$ROOT/workshop.env" ]; then
    val="$(sed -n "s/^${key}=\([^#]*\).*/\1/p" "$ROOT/workshop.env" | tail -1 | tr -d "\"' ")"
  fi
  printf '%s' "${val:-$def}"
}

CHAT_MODEL="$(env_get CHAT_MODEL nemotron-3.5-lightning:30b-a3b)"
EXTRA_CHAT_MODEL="$(env_get EXTRA_CHAT_MODEL "")"
EMBED_MODEL="$(env_get EMBED_MODEL qwen3-embedding:4b)"
LAB1_BASE_HF="$(env_get LAB1_BASE_HF Qwen/Qwen2.5-1.5B-Instruct)"
LAB1_BASE_OLLAMA="$(env_get LAB1_BASE_OLLAMA qwen2.5:1.5b-instruct)"
LAB1_TUNED_MODEL="$(env_get LAB1_TUNED_MODEL aurora-assistant)"
LAB1_BASE_IMAGE="$(env_get LAB1_BASE_IMAGE nvcr.io/nvidia/pytorch:25.11-py3)"
LAB1_IMAGE="$(env_get LAB1_IMAGE workshop-finetune:latest)"
SANDBOX="$(env_get SANDBOX dgx-workshop)"
AGENT_ID="$(env_get AGENT_ID analyst)"
OLLAMA_URL="$(env_get OLLAMA_URL http://127.0.0.1:11434)"
HUB_PORT="$(env_get HUB_PORT 8090)"
OLLAMA_CONTEXT_LENGTH="$(env_get OLLAMA_CONTEXT_LENGTH 32768)"
# Context window of the chat models themselves, for OpenClaw's own agent (see
# scripts/ollama-context.py). Also what NemoClaw bakes into the sandbox.
CHAT_CONTEXT="$(env_get CHAT_CONTEXT 262144)"
CHAT_MAX_TOKENS="$(env_get CHAT_MAX_TOKENS 16384)"
# Every nemoclaw command must target the workshop's own gateway.
NEMOCLAW_GATEWAY_PORT="$(env_get NEMOCLAW_GATEWAY_PORT 8990)"
# The NemoClaw release the labs were verified with; a fresh install gets this
# one rather than whatever NVIDIA's installer currently calls last-known-good.
NEMOCLAW_VERSION="$(env_get NEMOCLAW_VERSION v0.0.124)"
# Enterprise batch demos: NVIDIA's vLLM container and an NVFP4 model (app/enterprise.py).
BATCH_IMAGE="$(env_get BATCH_IMAGE nvcr.io/nvidia/vllm:26.05.post1-py3)"
BATCH_MODEL="$(env_get BATCH_MODEL nvidia/Qwen3.6-35B-A3B-NVFP4)"
BATCH_MODEL_REVISION="$(env_get BATCH_MODEL_REVISION 491c2f1ea524c639598bf8fa787a93fed5a6fbce)"
BATCH_HF_HOME="$(env_get BATCH_HF_HOME "$HOME/.cache/huggingface")"
export BATCH_IMAGE BATCH_MODEL BATCH_MODEL_REVISION BATCH_HF_HOME
export CHAT_MODEL EMBED_MODEL LAB1_BASE_HF LAB1_BASE_OLLAMA LAB1_TUNED_MODEL LAB1_IMAGE \
       SANDBOX AGENT_ID OLLAMA_URL HUB_PORT NEMOCLAW_GATEWAY_PORT CHAT_CONTEXT CHAT_MAX_TOKENS \
       EXTRA_CHAT_MODEL

# The one command participants run (install and update), and how to start the
# workshop afterwards. Messages repeat them so they can be copied from screen.
INSTALL_CMD="curl -fsSL https://raw.githubusercontent.com/an6122003/nemoclaw-rag-demo/main/install.sh | bash"
case "$ROOT" in
  "$HOME"/*) START_CMD="bash ~${ROOT#"$HOME"}/start.sh" ;;
  *)         START_CMD="bash $ROOT/start.sh" ;;
esac

# NemoClaw's installer and gateway expect Docker's default context on Linux.
export DOCKER_CONTEXT="${DOCKER_CONTEXT:-default}"

# ------------------------------------------------------------------- output
if [ -t 1 ]; then
  GRN=$'\033[32m'; RED=$'\033[31m'; YEL=$'\033[33m'; BLD=$'\033[1m'; DIM=$'\033[2m'; RST=$'\033[0m'
else
  GRN=""; RED=""; YEL=""; BLD=""; DIM=""; RST=""
fi
LOG="${LOG:-$ROOT/setup-log.txt}"

note_log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*" >> "$LOG"; }
ok()   { printf '   %s✔%s  %s\n' "$GRN" "$RST" "$1"; [ -n "${2:-}" ] && printf '      %s%s%s\n' "$DIM" "$2" "$RST"; note_log "ok: $1"; return 0; }
bad()  { printf '   %s✘%s  %s\n' "$RED" "$RST" "$1"; [ -n "${2:-}" ] && printf '      %s\n' "$2"; note_log "FAIL: $1"; return 0; }
warn() { printf '   %s!%s  %s\n' "$YEL" "$RST" "$1"; [ -n "${2:-}" ] && printf '      %s%s%s\n' "$DIM" "$2" "$RST"; note_log "warn: $1"; return 0; }
info() { printf '   %s\n' "$1"; [ -n "${2:-}" ] && printf '   %s%s%s\n' "$DIM" "$2" "$RST"; return 0; }

fmt_elapsed() { local s=$1; printf '%d:%02d' $((s / 60)) $((s % 60)); }

# run_long "message" cmd args...  — run quietly into the log with a spinner.
run_long() {
  local msg="$1"; shift
  note_log "run: $*"
  "$@" >> "$LOG" 2>&1 &
  local pid=$! i=0 start=$SECONDS frames='|/-\'
  if [ -t 1 ]; then
    while kill -0 "$pid" 2>/dev/null; do
      printf '\r   %s %s  %s%s%s ' "${frames:$((i % 4)):1}" "$msg" "$DIM" "$(fmt_elapsed $((SECONDS - start)))" "$RST"
      i=$((i + 1))
      sleep 0.5
    done
    printf '\r\033[K'
  fi
  wait "$pid"
}

show_log_tail() {
  printf '      %s--- last lines of setup-log.txt ---%s\n' "$DIM" "$RST"
  tail -n "${1:-12}" "$LOG" | sed 's/^/      /'
}

# ------------------------------------------------------------------ probes
ollama_up() { curl -fsS -m 5 "$OLLAMA_URL/api/version" >/dev/null 2>&1; }

ollama_unload_all() {  # free the memory Ollama holds; models reload on their next use
  curl -fsS -m 10 "$OLLAMA_URL/api/ps" 2>/dev/null \
    | python3 -c 'import json, sys; [print(m["name"]) for m in json.load(sys.stdin).get("models", [])]' 2>/dev/null \
    | while read -r m; do
        curl -fsS -m 60 "$OLLAMA_URL/api/generate" -d "{\"model\": \"$m\", \"keep_alive\": 0}" >/dev/null 2>&1 || true
      done
}

ollama_has() {  # exact tag, or name:latest for a bare name
  local want="$1"
  curl -fsS -m 10 "$OLLAMA_URL/api/tags" 2>/dev/null | python3 -c '
import json, sys
want = sys.argv[1]
names = {m.get("name") for m in json.load(sys.stdin).get("models", [])}
sys.exit(0 if want in names or (":" not in want and want + ":latest" in names) else 1)
' "$want"
}

# OpenClaw's own agent overflows Ollama's usual 16k context; give the chat
# model its own larger one. Local only (no download), safe on every start.
ensure_chat_context() {
  local m rc=0
  for m in "$CHAT_MODEL" $EXTRA_CHAT_MODEL; do
    ollama_has "$m" || continue
    python3 "$ROOT/scripts/ollama-context.py" "$m" "$CHAT_CONTEXT" >> "$LOG" 2>&1 || rc=1
  done
  return $rc
}

sandbox_ok() {  # the NemoClaw sandbox answers and is Ready (status also succeeds for "Phase: Error")
  command -v nemoclaw >/dev/null 2>&1 || return 1
  timeout "${1:-60}" nemoclaw "$SANDBOX" status 2>/dev/null | grep -q "Phase: Ready"
}

lab2_search_ok() {  # the sandbox's memory search answers with a hit, as the app asks it
  timeout 120 nemoclaw "$SANDBOX" exec -- env TMPDIR=/tmp openclaw memory search \
      --query "AX-400 warranty" --max-results 1 --json 2>/dev/null \
    | python3 -c '
import json, sys
t = sys.stdin.read(); i = t.find("{")
try:
    sys.exit(0 if i >= 0 and json.loads(t[i:]).get("results") else 1)
except ValueError:
    sys.exit(1)'
}

# After the computer restarts, the sandbox container stays stopped (it has no
# restart policy). Starting it before onboarding brings the workshop's gateway
# back lets the sandbox reconnect at once, so onboarding finds it Ready and
# reuses it. Otherwise onboarding may try to recreate it while it is down, fail
# its safety backup, and leave a half-finished session behind.
sandbox_container_start() {
  local ids
  ids="$(docker ps -aq --filter "label=openshell.ai/sandbox-name=$SANDBOX" \
         --filter label=openshell.ai/managed-by=openshell --filter status=exited 2>/dev/null)"
  [ -n "$ids" ] || return 0
  note_log "starting stopped sandbox container(s): $ids"
  # shellcheck disable=SC2086
  docker start $ids >/dev/null 2>&1 || true
}

wait_sandbox_ready() {  # wait_sandbox_ready SECONDS — Ready after a container start
  local end=$((SECONDS + ${1:-120}))
  while [ "$SECONDS" -lt "$end" ]; do
    sandbox_ok 20 && return 0
    sleep 5
  done
  return 1
}

hub_up() { curl -fsS -m 3 "http://127.0.0.1:$HUB_PORT/api/health" >/dev/null 2>&1; }

# NemoClaw onboarding with the workshop's settings. For a new machine it
# creates the sandbox. For an existing sandbox it starts the workshop's gateway
# again and reuses the sandbox and its data: NemoClaw's way back after the
# computer restarts, because a gateway on a custom port has no system service
# ("Start the gateway again with `nemoclaw onboard`"). Measured on the Spark
# after a simulated restart: 25 s.
#
# Onboarding checks an existing sandbox once, without waiting. If the sandbox
# has not reconnected yet, it recreates it, and by default first backs it up;
# that backup fails for a sandbox that is still down, onboarding aborts, and
# the sandbox is stuck. Recreating without the backup avoids that: the
# workshop puts its documents and agent back afterwards (start.sh, setup.sh).
nemoclaw_onboard() {
  embed_proxy_stop    # NemoClaw checks that only loopback listens on Ollama's port
  ollama_unload_all   # and picks a smaller model when memory looks busy
  env NEMOCLAW_NON_INTERACTIVE=1 NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1 NEMOCLAW_YES=1 \
      NEMOCLAW_RECREATE_WITHOUT_BACKUP=1 NEMOCLAW_CONTEXT_WINDOW="$CHAT_CONTEXT" \
      NEMOCLAW_MAX_TOKENS="$CHAT_MAX_TOKENS" \
      NEMOCLAW_AGENT=openclaw NEMOCLAW_PROVIDER=ollama NEMOCLAW_MODEL="$CHAT_MODEL" \
      NEMOCLAW_SANDBOX_NAME="$SANDBOX" NEMOCLAW_POLICY_TIER=balanced \
    timeout "${ONBOARD_TIMEOUT:-3600}" nemoclaw onboard --name "$SANDBOX" --non-interactive --yes \
      --yes-i-accept-third-party-software "$@"
}

# When memory looked busy during onboarding, NemoClaw silently substitutes a
# smaller model ("qwen3.6:35b is unlikely to fit … falling back to
# nemotron-3-nano:30b"), and Lab 3 fails with it. Switch back to CHAT_MODEL.
ensure_sandbox_model() {
  local current
  current="$(timeout 60 nemoclaw "$SANDBOX" inference get 2>/dev/null | sed -n 's/^Model:[[:space:]]*//p' | head -1)"
  note_log "sandbox inference model: ${current:-unknown}"
  if [ -z "$current" ] || [ "$current" = "$CHAT_MODEL" ]; then
    return 0
  fi
  if run_long "Switching the sandbox to $CHAT_MODEL… / Đang chuyển sandbox sang $CHAT_MODEL…" \
       env NEMOCLAW_CONTEXT_WINDOW="$CHAT_CONTEXT" NEMOCLAW_MAX_TOKENS="$CHAT_MAX_TOKENS" \
       timeout 600 nemoclaw "$SANDBOX" inference set --provider ollama-local --model "$CHAT_MODEL"; then
    ok "Sandbox model: $CHAT_MODEL (NemoClaw had chosen $current)" "Mô hình của sandbox: $CHAT_MODEL"
  else
    warn "The sandbox uses $current instead of $CHAT_MODEL" "Sandbox đang dùng $current thay vì $CHAT_MODEL"
  fi
}

# Docker access. On a fresh DGX Spark the account is often not in the docker
# group yet, and a new membership only reaches new logins: until then the
# workshop continues inside the group with sg(1).
docker_ok()       { timeout 30 docker info >/dev/null 2>&1; }
# Docker runs but this account may not use it yet (not in the docker group).
# No pipeline here: with pipefail, `docker info | grep` reports docker's own
# failure even when grep finds the line, and the check was always false.
docker_denied() {
  local out
  out="$(timeout 30 docker info 2>&1)" && return 1
  case "${out,,}" in *"permission denied"*) return 0 ;; esac
  [ -S /var/run/docker.sock ] && [ ! -w /var/run/docker.sock ]
}
in_docker_group() { local g; for g in $(id -nG "$(id -un)" 2>/dev/null); do [ "$g" = docker ] && return 0; done; return 1; }

# ------------------------------------------------------ embedding proxy
# The sandbox reaches the host as host.openshell.internal. Find the address it
# resolves to, so the proxy listens only where the sandbox can reach it.
sandbox_host_ip() {
  local ip
  ip="$(timeout 60 nemoclaw "$SANDBOX" exec -- getent ahostsv4 host.openshell.internal 2>/dev/null \
        | awk '{print $1}' | grep -E '^[0-9]+(\.[0-9]+){3}$' | head -1)"
  if [ -z "$ip" ]; then
    ip="$(timeout 60 nemoclaw "$SANDBOX" exec -- python3 -c \
          'import socket; print(socket.gethostbyname("host.openshell.internal"))' 2>/dev/null \
          | grep -E '^[0-9]+(\.[0-9]+){3}$' | head -1)"
  fi
  printf '%s' "$ip"
}

is_local_ip() { ip -o -4 addr show 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | grep -qx "$1"; }

embed_proxy_running() {
  local pid
  pid="$(cat "$RUN/embed-proxy.pid" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

embed_proxy_stop() {
  local pid
  pid="$(cat "$RUN/embed-proxy.pid" 2>/dev/null || true)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$RUN/embed-proxy.pid"
}

embed_proxy_start() {  # embed_proxy_start [bind-ip]
  local bind="${1:-$(cat "$RUN/embed-proxy.bind" 2>/dev/null || true)}"
  [ -n "$bind" ] || return 1
  local sig="$EMBED_MODEL|$EXTRA_CHAT_MODEL"
  if embed_proxy_running; then
    [ "$(cat "$RUN/embed-proxy.models" 2>/dev/null)" = "$sig" ] && return 0
    embed_proxy_stop  # started before the allowed models changed
  fi
  printf '%s\n' "$sig" > "$RUN/embed-proxy.models"
  local py=python3
  [ -x "$ROOT/.venv/bin/python" ] && py="$ROOT/.venv/bin/python"
  local extra=()
  [ -n "$EXTRA_CHAT_MODEL" ] && extra=(--chat-model "$EXTRA_CHAT_MODEL")
  nohup "$py" "$ROOT/scripts/embed-proxy.py" --bind "$bind" --port 11434 \
    --target "${OLLAMA_URL#http://}" --model "$EMBED_MODEL" "${extra[@]}" \
    >> "$RUN/embed-proxy.log" 2>&1 &
  echo $! > "$RUN/embed-proxy.pid"
  printf '%s\n' "$bind" > "$RUN/embed-proxy.bind"
  local i
  for i in $(seq 1 16); do  # Python takes a moment to start; give it up to 8 seconds
    embed_proxy_running || return 1
    curl -fsS -m 3 "http://$bind:11434/api/version" >/dev/null 2>&1 && return 0
    sleep 0.5
  done
  return 1
}
