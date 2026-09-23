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
    val="$(sed -n "s/^${key}=\([^#]*\).*/\1/p" "$ROOT/workshop.env" | tail -1 | tr -d '"'"'"' ' ')"
  fi
  printf '%s' "${val:-$def}"
}

CHAT_MODEL="$(env_get CHAT_MODEL qwen3.6:35b)"
EMBED_MODEL="$(env_get EMBED_MODEL qwen3-embedding:4b)"
LAB1_BASE_HF="$(env_get LAB1_BASE_HF Qwen/Qwen2.5-1.5B-Instruct)"
LAB1_BASE_OLLAMA="$(env_get LAB1_BASE_OLLAMA qwen2.5:1.5b-instruct)"
LAB1_TUNED_MODEL="$(env_get LAB1_TUNED_MODEL aurora-assistant)"
LAB1_BASE_IMAGE="$(env_get LAB1_BASE_IMAGE nvcr.io/nvidia/pytorch:25.11-py3)"
LAB1_IMAGE="$(env_get LAB1_IMAGE workshop-finetune:latest)"
SANDBOX="$(env_get SANDBOX my-assistant)"
AGENT_ID="$(env_get AGENT_ID analyst)"
OLLAMA_URL="$(env_get OLLAMA_URL http://127.0.0.1:11434)"
HUB_PORT="$(env_get HUB_PORT 8090)"
OLLAMA_CONTEXT_LENGTH="$(env_get OLLAMA_CONTEXT_LENGTH 32768)"
export CHAT_MODEL EMBED_MODEL LAB1_BASE_HF LAB1_BASE_OLLAMA LAB1_TUNED_MODEL LAB1_IMAGE \
       SANDBOX AGENT_ID OLLAMA_URL HUB_PORT

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

ollama_has() {  # exact tag, or name:latest for a bare name
  local want="$1"
  curl -fsS -m 10 "$OLLAMA_URL/api/tags" 2>/dev/null | python3 -c '
import json, sys
want = sys.argv[1]
names = {m.get("name") for m in json.load(sys.stdin).get("models", [])}
sys.exit(0 if want in names or (":" not in want and want + ":latest" in names) else 1)
' "$want"
}

sandbox_ok() {  # the NemoClaw sandbox answers within the time limit
  command -v nemoclaw >/dev/null 2>&1 || return 1
  timeout "${1:-60}" nemoclaw "$SANDBOX" status >/dev/null 2>&1
}

hub_up() { curl -fsS -m 3 "http://127.0.0.1:$HUB_PORT/api/health" >/dev/null 2>&1; }

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
  embed_proxy_running && return 0
  local py=python3
  [ -x "$ROOT/.venv/bin/python" ] && py="$ROOT/.venv/bin/python"
  nohup "$py" "$ROOT/scripts/embed-proxy.py" --bind "$bind" --port 11434 \
    --target "${OLLAMA_URL#http://}" --model "$EMBED_MODEL" \
    >> "$RUN/embed-proxy.log" 2>&1 &
  echo $! > "$RUN/embed-proxy.pid"
  printf '%s\n' "$bind" > "$RUN/embed-proxy.bind"
  sleep 1
  embed_proxy_running && curl -fsS -m 5 "http://$bind:11434/api/version" >/dev/null 2>&1
}
