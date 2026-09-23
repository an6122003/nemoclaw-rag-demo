#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Hands-on 2 — launch the GUI demo.
#
# Checks the two things the demo needs, warms the model so the first question is
# not the slowest, then serves the interface and opens a browser.

set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(dirname "$DEMO_DIR")"
PORT="${PORT:-8090}"
# Gateway port: a fresh install uses 8080; the authoring machine used 8814
# because 8080 was taken. Read it from NemoClaw's own gateway registry rather
# than probing ports, which can find an unrelated service.
detect_gateway_port() {
  local d name
  for d in "$HOME/.nemoclaw/gateways"/*; do
    [ -d "$d" ] || continue
    name="$(basename "$d")"
    case "$name" in ''|*[!0-9]*) continue ;; esac
    echo "$name"; return
  done
  for d in "$HOME/.local/state/nemoclaw/openshell-docker-gateway-"*; do
    [ -d "$d" ] || continue
    name="$(basename "$d")"; name="${name##*-}"
    case "$name" in ''|*[!0-9]*) continue ;; esac
    echo "$name"; return
  done
  echo 8080
}
export NEMOCLAW_GATEWAY_PORT="${NEMOCLAW_GATEWAY_PORT:-$(detect_gateway_port)}"
export DOCKER_CONTEXT="${DOCKER_CONTEXT:-default}"
export PATH="$HOME/.local/bin:$PATH"

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; RST=$'\033[0m'
ok()   { printf '  %sok%s   %s\n' "$GRN" "$RST" "$*"; }
warn() { printf '  %swarn%s %s\n' "$YEL" "$RST" "$*"; }

OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
SANDBOX="${NEMOCLAW_SANDBOX:-my-assistant}"

printf '\n== Demo preflight ==\n'

# 1. Model relay — the demo cannot answer without it.
if curl -fsS -m 6 "$OLLAMA_BASE_URL/api/version" >/dev/null 2>&1; then
  ok "model relay at $OLLAMA_BASE_URL"
else
  warn "no model relay at $OLLAMA_BASE_URL"
  warn "start it with:  python3 $LAB_DIR/scripts/ollama-relay.py --target <ollama-host>:11434"
  warn "the page will still load but answers will fail"
fi

# 2. Sandbox — provides authentic retrieval. Bounded, because a wedged gateway
#    makes `nemoclaw status` hang indefinitely rather than fail.
sandbox_ok() {
  command -v nemoclaw >/dev/null 2>&1 || return 1
  nemoclaw "$SANDBOX" status >/dev/null 2>&1 &
  local pid=$! i=0
  while kill -0 "$pid" 2>/dev/null && [ "$i" -lt 15 ]; do sleep 1; i=$((i + 1)); done
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; return 1
  fi
  wait "$pid" 2>/dev/null; return $?
}

if sandbox_ok; then
  ok "NemoClaw sandbox '$SANDBOX' reachable"
else
  warn "sandbox '$SANDBOX' not reachable or not responding; using the local index"
  warn "the demo works fully this way — retrieval route differs only"
fi

if [ ! -d "$LAB_DIR/corpus" ]; then
  printf '  %sfail%s corpus not found at %s\n' "$RED" "$RST" "$LAB_DIR/corpus" >&2
  exit 1
fi

# 3. Port free?
if lsof -i ":$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  warn "port $PORT is already in use"
  warn "if the demo is already running, just open http://127.0.0.1:$PORT/"
  exit 1
fi

printf '\n== Starting ==\n'
cd "$LAB_DIR"
exec python3 "$DEMO_DIR/server.py" --port "$PORT" --open "$@"
