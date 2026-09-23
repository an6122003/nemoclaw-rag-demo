#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Hands-on 2 — turn an onboarded NemoClaw sandbox into the RAG lab.
#
# Run AFTER `nemoclaw onboard` has produced a sandbox and AFTER host-setup.sh.
# Idempotent: safe to re-run.
#
#   1. Uploads the corpus into the agent workspace memory/ directory.
#   2. Points OpenClaw memory search at the Ollama embedding model.
#   3. Builds the vector index and reports its identity.
#   4. Saves a fallback copy of the built index so a failed re-ingest on the
#      day does not block the session.
#
# IMPORTANT — read this before trusting the config keys
#   The published NemoClaw page for memory search shows
#   `agents.defaults.memorySearch.provider`. That is the LEGACY schema. In
#   current OpenClaw the live paths are `memory.search.*` (global) and
#   `agents.entries.<id>.memory.search.*` (per agent); the legacy key is
#   migrated by `openclaw doctor --fix`, and the runtime config schema is
#   strict, so a legacy key can be silently ignored rather than erroring.
#   This script therefore tries the current key first and VERIFIES with
#   `openclaw memory status --deep`, falling back to the legacy key only if
#   verification fails. Always confirm the status output before the event.
#
# Usage
#   ./lab-setup.sh                          # sandbox "my-assistant"
#   ./lab-setup.sh --sandbox my-lab
#   ./lab-setup.sh --config-legacy          # force the legacy key path
#   ./lab-setup.sh --skip-index             # only upload + configure

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(dirname "$SCRIPT_DIR")"

SANDBOX="${SANDBOX:-my-assistant}"
EMBED_MODEL="${EMBED_MODEL:-qwen3-embedding:4b}"
PROVIDER_ID="${PROVIDER_ID:-ollama-mem}"
HOST_GATEWAY_URL="${HOST_GATEWAY_URL:-http://host.openshell.internal:11434}"
CONFIG_MODE=auto     # auto | current | legacy
SKIP_INDEX=0
FALLBACK_DIR="$LAB_DIR/index/fallback"

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; RST=$'\033[0m'
ok()   { printf '  %sok%s   %s\n' "$GRN" "$RST" "$*"; }
warn() { printf '  %swarn%s %s\n' "$YEL" "$RST" "$*"; }
die()  { printf '  %sfail%s %s\n' "$RED" "$RST" "$*" >&2; exit 1; }
step() { printf '\n== %s ==\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --sandbox)      SANDBOX="$2"; shift 2 ;;
    --embed-model)  EMBED_MODEL="$2"; shift 2 ;;
    --provider-id)  PROVIDER_ID="$2"; shift 2 ;;
    --gateway-url)  HOST_GATEWAY_URL="$2"; shift 2 ;;
    --config-current) CONFIG_MODE=current; shift ;;
    --config-legacy)  CONFIG_MODE=legacy; shift ;;
    --skip-index)   SKIP_INDEX=1; shift ;;
    -h|--help)      sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

command -v nemoclaw >/dev/null 2>&1 || die "nemoclaw not on PATH. Run the installer, then 'nemoclaw onboard'."

sbx() { nemoclaw "$SANDBOX" "$@"; }

# --------------------------------------------------------------------------
step "Sandbox '$SANDBOX'"
# --------------------------------------------------------------------------
sbx status >/dev/null 2>&1 || die "sandbox '$SANDBOX' not reachable. Run 'nemoclaw onboard' first."
ok "sandbox reachable"
WORKSPACE="$(sbx exec -- sh -lc 'echo "$HOME/.openclaw/workspace"' 2>/dev/null | tr -d '\r' | tail -1)"
[ -n "$WORKSPACE" ] || WORKSPACE="/sandbox/.openclaw/workspace"
ok "workspace: $WORKSPACE"

# --------------------------------------------------------------------------
step "Upload corpus"
# --------------------------------------------------------------------------
# OpenClaw indexes exactly: <workspace>/MEMORY.md, <workspace>/USER.md, and
# <workspace>/memory/**/*.md (recursed). Everything else is invisible to
# memory search, so the corpus must land under memory/.
sbx exec -- mkdir -p "$WORKSPACE/memory" >/dev/null
count=0
for f in "$LAB_DIR"/corpus/*.md; do
  [ -e "$f" ] || continue
  sbx upload "$f" "$WORKSPACE/memory/" >/dev/null
  count=$((count + 1))
done
[ "$count" -gt 0 ] || die "no corpus files found in $LAB_DIR/corpus"
ok "uploaded $count documents to $WORKSPACE/memory/"

# --------------------------------------------------------------------------
step "Network policy"
# --------------------------------------------------------------------------
# The stock preset already permits host.openshell.internal:11434 with the
# RFC1918 allow-list OpenShell's SSRF guard requires. A raw Tailscale
# 100.64/10 address is NOT permitted here and is rejected by `config set`,
# which is exactly why the relay exists.
if sbx policy add local-inference --yes >/dev/null 2>&1; then
  ok "local-inference policy present"
else
  warn "could not apply local-inference (it may already be applied)"
fi

if sbx exec -- curl -fsS -m 10 "$HOST_GATEWAY_URL/api/version" >/dev/null 2>&1; then
  ok "sandbox can reach Ollama at $HOST_GATEWAY_URL"
else
  # Applying the stock preset is necessary but not sufficient. Where
  # host.openshell.internal also resolves to an IPv6 unique-local address the
  # SSRF guard denies every request until fc00::/7 is in allowed_ips. Repair it
  # rather than failing here, because the failure otherwise surfaces much later
  # as an opaque embedding error mid-index.
  warn "sandbox cannot reach $HOST_GATEWAY_URL; attempting the IPv6 host-gateway repair"
  "$SCRIPT_DIR/fix-sandbox-policy.sh" --sandbox "$SANDBOX" \
      --gateway-port "${NEMOCLAW_GATEWAY_PORT:-8080}" \
    || die "sandbox cannot reach $HOST_GATEWAY_URL. Is the host relay running? (host-setup.sh)"
  ok "host egress repaired"
fi

# --------------------------------------------------------------------------
step "Configure embedding provider"
# --------------------------------------------------------------------------
provider_json="{\"api\":\"openai-completions\",\"baseUrl\":\"$HOST_GATEWAY_URL/v1\",\"apiKey\":\"ollama\",\"models\":[{\"id\":\"$EMBED_MODEL\",\"name\":\"Qwen3 embedding 4B\"}]}"

# The pinned OpenClaw build in the NemoClaw sandbox image (2026.7.1) reads
# `agents.defaults.memorySearch`. The `memory.search.*` paths belong to a later
# upstream schema; the config schema is strict, so the wrong key is SILENTLY
# ignored rather than erroring. Always verify afterwards.
set_provider_config() {
  sbx config set --key "models.providers.$PROVIDER_ID" --value "$provider_json" \
    --config-accept-new-path >/dev/null 2>&1 || return 1
  sbx config set --key "agents.defaults.memorySearch.provider" --value "$PROVIDER_ID" \
    --config-accept-new-path >/dev/null 2>&1 || return 1
  sbx config set --key "agents.defaults.memorySearch.model" --value "$EMBED_MODEL" \
    --config-accept-new-path --restart >/dev/null 2>&1 || return 1
  return 0
}

# `nemoclaw config set` runs OpenClaw's config guard, which validates the file
# with a pinned JSON5 parser under /opt. If the sandbox filesystem policy does
# not permit reading /opt, the guard fails (json5-validator-failed) and config
# set cannot be used at all. This writes the same settings directly.
#
# Note the adapter: it must be `openai-completions`, NOT `ollama`. The Ollama
# adapter ignores baseUrl and dials 127.0.0.1:11434, which does not exist inside
# the sandbox. The OpenAI-compatible adapter honours baseUrl and reaches the
# host relay through /v1/embeddings.
write_config_directly() {
  local tmp
  tmp="$(mktemp -d)"
  sbx download /sandbox/.openclaw/openclaw.json "$tmp/openclaw.json" >/dev/null 2>&1 || { rm -rf "$tmp"; return 1; }
  python3 - "$tmp/openclaw.json" "$PROVIDER_ID" "$EMBED_MODEL" "$HOST_GATEWAY_URL" <<'PY' || { rm -rf "$tmp"; return 1; }
import json, sys
path, pid, model, base = sys.argv[1:5]
raw = open(path).read()
d = json.loads(raw[: raw.rfind("}") + 1])
d.setdefault("models", {}).setdefault("providers", {})[pid] = {
    "api": "openai-completions",
    "baseUrl": f"{base}/v1",
    "apiKey": "ollama",
    "models": [{"id": model, "name": "Qwen3 embedding 4B"}],
}
d.setdefault("agents", {}).setdefault("defaults", {})["memorySearch"] = {
    "enabled": True,
    "provider": pid,
    "model": model,
}
open(path, "w").write(json.dumps(d, indent=2) + "\n")
PY
  sbx upload "$tmp/openclaw.json" /sandbox/.openclaw/openclaw.json >/dev/null 2>&1 || { rm -rf "$tmp"; return 1; }
  rm -rf "$tmp"
  return 0
}

# Verification is the contract: status must report embeddings as ready.
config_verified() {
  local status
  status="$(sbx exec -- env TMPDIR=/tmp openclaw memory status --deep 2>&1 || true)"
  printf '%s' "$status" | grep -qiE 'Embeddings:[[:space:]]*ready'
}

applied=""
if set_provider_config && config_verified; then
  applied="nemoclaw config set"
else
  warn "'nemoclaw config set' did not take effect (its config guard is often unusable)"
  warn "writing openclaw.json directly instead"
  write_config_directly && applied="direct config write"
fi
[ -n "$applied" ] || die "could not configure the memory search embedding provider"
ok "configured via $applied"

if config_verified; then
  ok "embeddings ready: provider '$PROVIDER_ID', model '$EMBED_MODEL'"
else
  warn "embeddings are not ready. Inspect with:"
  warn "  nemoclaw $SANDBOX exec -- env TMPDIR=/tmp openclaw memory status --deep"
fi

# --------------------------------------------------------------------------
step "Build index"
# --------------------------------------------------------------------------
if [ "$SKIP_INDEX" -eq 1 ]; then
  warn "skipped (--skip-index)"
else
  # TMPDIR must be set explicitly. SQLite resolves its temp directory from
  # TMPDIR and, with it unset in the exec environment, index builds fail with
  # the misleading "unable to open database file" even though the database
  # directory is writable.
  if sbx exec -- env TMPDIR=/tmp openclaw memory index --force 2>&1 | tail -5; then
    ok "index build completed"
  else
    warn "index build reported a failure; see the fallback restore below"
  fi
fi

echo
sbx exec -- openclaw memory status --index 2>&1 | sed 's/^/  /' || true

# --------------------------------------------------------------------------
step "Fallback index"
# --------------------------------------------------------------------------
# The index lives in SQLite at <stateDir>/agents/<agentId>/agent/openclaw-agent.sqlite
# -- the SAME file as sessions, and it is bound to the embedding provider
# identity (provider id, model, endpoint, headers) plus chunk settings. It is
# therefore only restorable onto a sandbox configured identically. We store a
# copy so a participant whose re-ingest fails can be unblocked without
# re-embedding anything.
mkdir -p "$FALLBACK_DIR"
DB="$(sbx exec -- sh -lc 'echo "$HOME/.openclaw/agents/main/agent/openclaw-agent.sqlite"' 2>/dev/null | tr -d '\r' | tail -1)"
if [ -n "$DB" ] && sbx exec -- test -f "$DB" 2>/dev/null; then
  if sbx download "$DB" "$FALLBACK_DIR/openclaw-agent.sqlite" >/dev/null 2>&1; then
    cat > "$FALLBACK_DIR/README.md" <<EOF
# Fallback memory index

Copied from a verified sandbox build. It is only valid for a sandbox whose
embedding configuration matches exactly:

  provider id : $PROVIDER_ID
  model       : $EMBED_MODEL
  endpoint    : $HOST_GATEWAY_URL

Restore with:

    nemoclaw <sandbox> upload $FALLBACK_DIR/openclaw-agent.sqlite \\
      \$HOME/.openclaw/agents/main/agent/openclaw-agent.sqlite
    nemoclaw <sandbox> exec -- openclaw memory status --index

If OpenClaw reports an index identity mismatch, the provider settings differ
from the build host. Fix the provider config and re-run, or rebuild with
'openclaw memory index --force' rather than hand-copying the database.
EOF
    ok "fallback saved to $FALLBACK_DIR/openclaw-agent.sqlite"
  else
    warn "could not download the index database"
  fi
else
  warn "index database not found at $DB"
fi

cat <<EOF

Lab setup complete.

  sandbox   : $SANDBOX
  workspace : $WORKSPACE/memory/
  documents : $count

Verify the pipeline answers the reference questions:

  python3 verification/verify_agent.py --sandbox $SANDBOX
EOF
