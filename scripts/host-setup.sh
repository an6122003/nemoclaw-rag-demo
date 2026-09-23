#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Hands-on 2 — prepare the lab HOST before participants arrive.
#
# Runs on the machine that will host the NemoClaw sandbox (macOS Apple Silicon
# or Linux / DGX Spark). It is idempotent: safe to re-run.
#
# What it does
#   1. Checks the container runtime and disk headroom.
#   2. Starts a local relay to the Ollama server that will serve embeddings.
#   3. Pulls and caches the embedding and chat models.
#   4. Proves the embedding path works end to end through the relay.
#
# Usage
#   ./host-setup.sh                                  # use defaults
#   ./host-setup.sh --ollama-target your-ollama-host:11434
#   ./host-setup.sh --ollama-target 127.0.0.1:11434 --no-relay   # Ollama is local
#   ./host-setup.sh --check-only                     # preflight, change nothing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(dirname "$SCRIPT_DIR")"

# Defaults match the workshop image. Override with flags.
# Empty means "Ollama runs on this machine". Set it (or pass --ollama-target)
# when Ollama is served from another host, in which case the relay is used.
OLLAMA_TARGET="${OLLAMA_TARGET:-}"
RELAY_BIND="${RELAY_BIND:-127.0.0.1}"
RELAY_PORT="${RELAY_PORT:-11434}"
EMBED_MODEL="${EMBED_MODEL:-qwen3-embedding:4b}"
CHAT_MODEL="${CHAT_MODEL:-qwen3:8b}"
USE_RELAY=auto   # auto | yes | no
CHECK_ONLY=0
MIN_FREE_GB=20

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; DIM=$'\033[2m'; RST=$'\033[0m'
ok()   { printf '  %sok%s   %s\n' "$GRN" "$RST" "$*"; }
warn() { printf '  %swarn%s %s\n' "$YEL" "$RST" "$*"; }
die()  { printf '  %sfail%s %s\n' "$RED" "$RST" "$*" >&2; exit 1; }
step() { printf '\n== %s ==\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --ollama-target) OLLAMA_TARGET="$2"; shift 2 ;;
    --relay-bind)    RELAY_BIND="$2"; shift 2 ;;
    --relay-port)    RELAY_PORT="$2"; shift 2 ;;
    --embed-model)   EMBED_MODEL="$2"; shift 2 ;;
    --chat-model)    CHAT_MODEL="$2"; shift 2 ;;
    --no-relay)      USE_RELAY=no; shift ;;
    --relay)         USE_RELAY=yes; shift ;;
    --check-only)    CHECK_ONLY=1; shift ;;
    -h|--help)       sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

# Decide whether a relay is needed.
if [ "$USE_RELAY" = auto ]; then
  if [ -n "$OLLAMA_TARGET" ]; then USE_RELAY=yes; else USE_RELAY=no; fi
fi
if [ "$USE_RELAY" = yes ] && [ -z "$OLLAMA_TARGET" ]; then
  die "A relay was requested but no target was given.
       Pass --ollama-target <host>:11434, or use --no-relay when Ollama runs here."
fi
if [ "$USE_RELAY" = no ]; then
  OLLAMA_TARGET="${OLLAMA_TARGET:-127.0.0.1:11434}"
fi

# --------------------------------------------------------------------------
step "Container runtime"
# --------------------------------------------------------------------------
command -v docker >/dev/null 2>&1 || die "docker not found. Install Docker Desktop (macOS) or Docker Engine (Linux)."
docker info >/dev/null 2>&1 || die "docker daemon not reachable. Start Docker Desktop / dockerd first."
ok "docker $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo '?')"

# OpenShell needs kernel-level isolation. On macOS that comes from the Docker
# Desktop Linux VM, so confirm the VM really is Linux and has Landlock.
if [ "$(uname -s)" = "Darwin" ]; then
  vm_kernel="$(docker run --rm alpine uname -sr 2>/dev/null || true)"
  case "$vm_kernel" in
    Linux\ 5.1[3-9]*|Linux\ [6-9]*) ok "Linux VM kernel: $vm_kernel" ;;
    Linux*) warn "VM kernel $vm_kernel may lack Landlock (needs >= 5.13)" ;;
    *) warn "could not confirm a Linux container VM" ;;
  esac
fi

# --------------------------------------------------------------------------
step "Disk headroom"
# --------------------------------------------------------------------------
free_gb="$(df -Pk "$LAB_DIR" | awk 'NR==2 {printf "%d", $4/1024/1024}')"
if [ "$free_gb" -ge "$MIN_FREE_GB" ]; then
  ok "${free_gb} GB free (need ${MIN_FREE_GB} GB)"
else
  warn "${free_gb} GB free, NemoClaw wants ${MIN_FREE_GB} GB minimum"
  warn "reclaim with: docker system prune --force   (build cache + dangling images)"
fi

# --------------------------------------------------------------------------
step "Ollama endpoint"
# --------------------------------------------------------------------------
# Accepts "host:port", "http://host:port" or "https://host:port". The naive
# version that always prepended http:// produced "http://http://host:port"
# whenever a caller passed a full URL, which silently reported the server as
# unreachable.
probe() {
  local u="$1"
  case "$u" in
    http://*|https://*) ;;
    *) u="http://$u" ;;
  esac
  curl -fsS -m 8 "${u%/}/api/version" 2>/dev/null
}

if [ "$USE_RELAY" = yes ]; then
  if probe "$RELAY_BIND:$RELAY_PORT" >/dev/null; then
    ok "relay already serving on $RELAY_BIND:$RELAY_PORT"
  else
    if [ "$CHECK_ONLY" -eq 1 ]; then
      warn "relay not running on $RELAY_BIND:$RELAY_PORT"
    else
      command -v python3 >/dev/null 2>&1 || die "python3 required to run the relay"
      mkdir -p "$LAB_DIR/.run"
      nohup python3 "$SCRIPT_DIR/ollama-relay.py" \
        --target "$OLLAMA_TARGET" --bind "$RELAY_BIND" --port "$RELAY_PORT" \
        > "$LAB_DIR/.run/relay.log" 2>&1 &
      echo $! > "$LAB_DIR/.run/relay.pid"
      sleep 2
      probe "$RELAY_BIND:$RELAY_PORT" >/dev/null \
        || { cat "$LAB_DIR/.run/relay.log" >&2; die "relay failed to start"; }
      ok "relay started (pid $(cat "$LAB_DIR/.run/relay.pid")) -> $OLLAMA_TARGET"
    fi
  fi
  API="http://$RELAY_BIND:$RELAY_PORT"
else
  probe "$OLLAMA_TARGET" >/dev/null || die "no Ollama answering at $OLLAMA_TARGET"
  ok "Ollama local at $OLLAMA_TARGET"
  API="http://$OLLAMA_TARGET"
fi

probe "$API" >/dev/null || die "Ollama not answering at $API"
ok "Ollama version $(probe "$API" | python3 -c 'import json,sys;print(json.load(sys.stdin)["version"])' 2>/dev/null || echo '?')"

# --------------------------------------------------------------------------
step "Models"
# --------------------------------------------------------------------------
have_model() {
  curl -fsS -m 10 "$API/api/tags" 2>/dev/null \
    | python3 -c "
import json,sys
want=sys.argv[1]
names={m['name'] for m in json.load(sys.stdin).get('models',[])}
base=want.split(':')[0]
sys.exit(0 if want in names or any(n==want or n.startswith(base+':') for n in names) else 1)
" "$1" 2>/dev/null
}

pull_model() {
  local model="$1"
  if have_model "$model"; then ok "$model already cached"; return 0; fi
  if [ "$CHECK_ONLY" -eq 1 ]; then warn "$model not cached"; return 1; fi
  printf '  %s..%s pulling %s\n' "$DIM" "$RST" "$model"
  curl -fsS -N -m 5400 -X POST "$API/api/pull" -d "{\"model\":\"$model\"}" \
    | python3 -u -c "
import json,sys
last=''
for line in sys.stdin:
    line=line.strip()
    if not line: continue
    try: d=json.loads(line)
    except Exception: continue
    s=d.get('status','')
    if d.get('total'):
        msg='%s: %5.1f%%' % (s, 100*d.get('completed',0)/d['total'])
    else:
        msg=s
    if msg!=last: print('     '+msg, flush=True); last=msg
" || return 1
  ok "$model cached"
}

pull_model "$EMBED_MODEL"
pull_model "$CHAT_MODEL" || warn "chat model optional for the RAG path"

# --------------------------------------------------------------------------
step "Embedding verification"
# --------------------------------------------------------------------------
if have_model "$EMBED_MODEL"; then
  curl -fsS -m 120 -X POST "$API/api/embed" \
    -d "{\"model\":\"$EMBED_MODEL\",\"input\":[\"lab preflight probe\"]}" \
    | python3 -c "
import json,sys
d=json.load(sys.stdin)
e=d.get('embeddings') or []
if not e: print('  fail no embeddings returned'); sys.exit(1)
print('  ok   %s -> dim %d' % (sys.argv[1], len(e[0])))
" "$EMBED_MODEL" || die "embedding call failed"
else
  warn "skipping embedding check, model not present"
fi

# --------------------------------------------------------------------------
step "Sandbox reachability (host gateway)"
# --------------------------------------------------------------------------
# The sandbox reaches host services as host.openshell.internal, which maps to
# the Docker host gateway. Prove a container can reach the relay, because the
# stock local-inference policy preset only permits that gateway.
if [ "$USE_RELAY" = yes ] && [ "$CHECK_ONLY" -eq 0 ]; then
  if docker run --rm curlimages/curl:latest -fsS -m 15 \
       "http://host.docker.internal:$RELAY_PORT/api/version" >/dev/null 2>&1; then
    ok "containers can reach the relay via host.docker.internal"
  else
    warn "container could not reach the relay."
    warn "If the relay is bound to 127.0.0.1, rebind with --relay-bind 0.0.0.0."
  fi
fi

cat <<EOF

Host setup complete.

  Ollama endpoint for the sandbox : http://host.openshell.internal:$RELAY_PORT
  Relay log                       : $LAB_DIR/.run/relay.log
  Stop the relay                  : kill \$(cat $LAB_DIR/.run/relay.pid)

Next: ./lab-setup.sh
EOF
