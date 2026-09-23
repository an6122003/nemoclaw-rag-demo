#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Hands-on 2 — turn an onboarded NemoClaw sandbox into the RAG lab.
#
# Run by setup.sh AFTER `nemoclaw onboard` and AFTER the embedding proxy is up.
# Idempotent: safe to re-run.
#
#   1. Uploads the corpus into the agent workspace memory/ directory.
#   2. Points OpenClaw memory search at the host's embedding model.
#   3. Builds the vector index and reports its identity.
#   4. Saves a copy of the built index so a failed re-ingest on the day does not
#      block the session.
#
# The config key matters: the OpenClaw build NemoClaw pins (2026.7.1) reads
# `agents.defaults.memorySearch`. Newer upstream builds moved to
# `memory.search.*`. The schema is strict, so the wrong key is silently
# IGNORED rather than rejected. This script always verifies with
# `openclaw memory status --deep`.
#
# Usage
#   scripts/lab2-sandbox-setup.sh                  # sandbox from workshop.env
#   scripts/lab2-sandbox-setup.sh --sandbox my-lab
#   scripts/lab2-sandbox-setup.sh --skip-index     # only upload + configure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
LAB="$ROOT/hands-on-2-rag"

env_get() {  # read KEY from workshop.env unless it is already in the environment
  local key="$1" def="$2" val
  val="$(printenv "$key" 2>/dev/null || true)"
  if [ -z "$val" ] && [ -f "$ROOT/workshop.env" ]; then
    val="$(sed -n "s/^${key}=\([^#]*\).*/\1/p" "$ROOT/workshop.env" | tail -1 | tr -d '"'"'"' ' ')"
  fi
  printf '%s' "${val:-$def}"
}

SANDBOX="$(env_get SANDBOX my-assistant)"
EMBED_MODEL="$(env_get EMBED_MODEL qwen3-embedding:4b)"
PROVIDER_ID="${PROVIDER_ID:-ollama-mem}"
HOST_GATEWAY_URL="${HOST_GATEWAY_URL:-http://host.openshell.internal:11434}"
SKIP_INDEX=0
FALLBACK_DIR="$LAB/index/fallback"

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; RST=$'\033[0m'
ok()   { printf '  %sok%s   %s\n' "$GRN" "$RST" "$*"; }
warn() { printf '  %swarn%s %s\n' "$YEL" "$RST" "$*"; }
die()  { printf '  %sfail%s %s\n' "$RED" "$RST" "$*" >&2; exit 1; }
step() { printf '\n== %s ==\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --sandbox)      SANDBOX="$2"; shift 2 ;;
    --embed-model)  EMBED_MODEL="$2"; shift 2 ;;
    --gateway-url)  HOST_GATEWAY_URL="$2"; shift 2 ;;
    --skip-index)   SKIP_INDEX=1; shift ;;
    -h|--help)      sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

export PATH="$HOME/.local/bin:$PATH"
command -v nemoclaw >/dev/null 2>&1 || die "nemoclaw not on PATH. Run ./setup.sh first."
sbx() { nemoclaw "$SANDBOX" "$@"; }

# --------------------------------------------------------------------------
step "Sandbox '$SANDBOX'"
# --------------------------------------------------------------------------
timeout 90 nemoclaw "$SANDBOX" status >/dev/null 2>&1 \
  || die "sandbox '$SANDBOX' not reachable. Run ./setup.sh first."
ok "sandbox reachable"
WORKSPACE="$(sbx exec -- sh -lc 'echo "$HOME/.openclaw/workspace"' 2>/dev/null | tr -d '\r' | tail -1)"
[ -n "$WORKSPACE" ] || WORKSPACE="/sandbox/.openclaw/workspace"
ok "workspace: $WORKSPACE"

# --------------------------------------------------------------------------
step "Upload corpus"
# --------------------------------------------------------------------------
# OpenClaw indexes exactly: <workspace>/MEMORY.md, <workspace>/USER.md, and
# <workspace>/memory/**/*.md. Anything else is invisible to memory search.
sbx exec -- mkdir -p "$WORKSPACE/memory" >/dev/null
count=0
for f in "$LAB"/corpus/*.md; do
  [ -e "$f" ] || continue
  sbx upload "$f" "$WORKSPACE/memory/" >/dev/null
  count=$((count + 1))
done
[ "$count" -gt 0 ] || die "no corpus files found in $LAB/corpus"
ok "uploaded $count documents to $WORKSPACE/memory/"

# --------------------------------------------------------------------------
step "Network policy"
# --------------------------------------------------------------------------
# The stock local-inference preset permits host.openshell.internal:11434.
if sbx policy add local-inference --yes >/dev/null 2>&1; then
  ok "local-inference policy present"
else
  warn "could not apply local-inference (it may already be applied)"
fi

if sbx exec -- curl -fsS -m 10 "$HOST_GATEWAY_URL/api/tags" 2>/dev/null | grep -q "$EMBED_MODEL"; then
  ok "sandbox reaches the embedding model at $HOST_GATEWAY_URL"
else
  # Docker Desktop only: host.openshell.internal also resolves to an IPv6
  # unique-local address that the stock preset does not allow. On a Linux host
  # the usual cause is instead that scripts/embed-proxy.py is not running.
  warn "sandbox cannot reach $HOST_GATEWAY_URL; trying the policy repair"
  "$SCRIPT_DIR/fix-sandbox-policy.sh" --sandbox "$SANDBOX" \
      --gateway-port "${NEMOCLAW_GATEWAY_PORT:-8080}" >/dev/null 2>&1 || true
  sbx exec -- curl -fsS -m 10 "$HOST_GATEWAY_URL/api/tags" 2>/dev/null | grep -q "$EMBED_MODEL" \
    || die "sandbox cannot reach the embedding model at $HOST_GATEWAY_URL (is the embed proxy running? see .run/embed-proxy.log)"
  ok "sandbox reaches the embedding model after the repair"
fi

# --------------------------------------------------------------------------
step "Configure embedding provider"
# --------------------------------------------------------------------------
# The adapter must be `openai-completions`, NOT `ollama`: the Ollama adapter in
# OpenClaw 2026.7.1 ignores baseUrl and dials 127.0.0.1:11434, which does not
# exist inside the sandbox.
provider_json="{\"api\":\"openai-completions\",\"baseUrl\":\"$HOST_GATEWAY_URL/v1\",\"apiKey\":\"ollama\",\"models\":[{\"id\":\"$EMBED_MODEL\",\"name\":\"Qwen3 embedding 4B\"}]}"

config_verified() {
  sbx exec -- env TMPDIR=/tmp openclaw memory status --deep 2>&1 \
    | grep -qiE 'Embeddings:[[:space:]]*ready'
}

set_provider_config() {
  sbx config set --key "models.providers.$PROVIDER_ID" --value "$provider_json" \
    --config-accept-new-path >/dev/null 2>&1 || return 1
  sbx config set --key "agents.defaults.memorySearch.provider" --value "$PROVIDER_ID" \
    --config-accept-new-path >/dev/null 2>&1 || return 1
  sbx config set --key "agents.defaults.memorySearch.model" --value "$EMBED_MODEL" \
    --config-accept-new-path --restart >/dev/null 2>&1 || return 1
}

# `nemoclaw config set` runs a config guard that can fail inside the sandbox
# (json5-validator-failed). Writing the same settings directly is reliable;
# the .config-hash is then refreshed exactly the way NemoClaw's own config
# writer does it.
write_config_directly() {
  local tmp
  tmp="$(mktemp -d)"
  sbx download /sandbox/.openclaw/openclaw.json "$tmp/openclaw.json" >/dev/null 2>&1 \
    || { rm -rf "$tmp"; return 1; }
  python3 - "$tmp/openclaw.json" "$PROVIDER_ID" "$EMBED_MODEL" "$HOST_GATEWAY_URL" <<'PY' \
    || { rm -rf "$tmp"; return 1; }
import json, sys
path, pid, model, base = sys.argv[1:5]
raw = open(path, encoding="utf-8").read()
d = json.loads(raw[: raw.rfind("}") + 1])
d.setdefault("models", {}).setdefault("providers", {})[pid] = {
    "api": "openai-completions",
    "baseUrl": f"{base}/v1",
    "apiKey": "ollama",
    "models": [{"id": model, "name": "Qwen3 embedding 4B"}],
}
d.setdefault("agents", {}).setdefault("defaults", {})["memorySearch"] = {
    "enabled": True, "provider": pid, "model": model,
}
open(path, "w", encoding="utf-8").write(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
PY
  sbx upload "$tmp/openclaw.json" /sandbox/.openclaw/openclaw.json >/dev/null 2>&1 \
    || { rm -rf "$tmp"; return 1; }
  rm -rf "$tmp"
  sbx exec -- sh -c 'cd /sandbox/.openclaw && sha256sum openclaw.json > .config-hash' >/dev/null 2>&1 || true
  sbx gateway restart --quiet >/dev/null 2>&1 || true
}

if config_verified; then
  ok "memory search already configured"
elif set_provider_config && config_verified; then
  ok "configured via nemoclaw config set"
else
  warn "'nemoclaw config set' did not take effect; writing openclaw.json directly"
  write_config_directly || die "could not configure the memory search embedding provider"
  ok "configured via direct config write"
fi

config_verified && ok "embeddings ready: provider '$PROVIDER_ID', model '$EMBED_MODEL'" \
  || warn "embeddings not ready yet. Inspect: nemoclaw $SANDBOX exec -- env TMPDIR=/tmp openclaw memory status --deep"

# --------------------------------------------------------------------------
step "Build index"
# --------------------------------------------------------------------------
if [ "$SKIP_INDEX" -eq 1 ]; then
  warn "skipped (--skip-index)"
else
  # TMPDIR must be set: SQLite resolves its temp directory from it, and index
  # builds otherwise fail with a misleading "unable to open database file".
  if sbx exec -- env TMPDIR=/tmp openclaw memory index --force 2>&1 | tail -5; then
    ok "index build completed"
  else
    warn "index build reported a failure; the app will use its local index instead"
  fi
fi
sbx exec -- env TMPDIR=/tmp openclaw memory status --index 2>&1 | sed 's/^/  /' || true

# --------------------------------------------------------------------------
step "Fallback index"
# --------------------------------------------------------------------------
# The index is SQLite at <stateDir>/agents/<agentId>/agent/openclaw-agent.sqlite
# (the same file as sessions) and is bound to the embedding provider identity.
# It is only restorable onto an identically configured sandbox.
mkdir -p "$FALLBACK_DIR"
DB="/sandbox/.openclaw/agents/main/agent/openclaw-agent.sqlite"
if sbx exec -- test -f "$DB" 2>/dev/null; then
  if sbx download "$DB" "$FALLBACK_DIR/openclaw-agent.sqlite" >/dev/null 2>&1; then
    ok "fallback saved to $FALLBACK_DIR/openclaw-agent.sqlite"
  else
    warn "could not download the index database"
  fi
else
  warn "index database not found at $DB"
fi

cat <<EOF

Hands-on 2 sandbox setup complete.

  sandbox   : $SANDBOX
  workspace : $WORKSPACE/memory/
  documents : $count

Verify retrieval against the reference questions:

  python3 hands-on-2-rag/verification/verify_agent.py --sandbox $SANDBOX
EOF
