#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Hands-on 3 — give the NemoClaw sandbox its Sales Analyst agent.
#
# Run by setup.sh after `nemoclaw onboard`. Idempotent: safe to re-run.
#
#   1. Adds an OpenClaw agent "analyst" (minimal tool profile, its own
#      workspace with AGENTS.md) next to the default agent.
#   2. Enables the gateway's OpenAI-compatible /v1/chat/completions endpoint.
#      Its client-tool contract hands every tool call back to the workshop app,
#      which runs the Python tools and shows each step live.
#   3. Switches off the model's hidden reasoning pass for agent turns
#      (measured 14.8 s -> 2.4 s per tool call on qwen3:8b, same tool choice).
#   4. Records the gateway URL and token for the app, and proves a real tool
#      call round-trips through the agent.
#   5. Optionally installs the same tools as an OpenClaw skill INSIDE the
#      sandbox, so the agent can also run them from OpenClaw's own chat UI.
#      PyPI access is opened for the install and closed again afterwards.
#
# Usage
#   scripts/lab3-sandbox-setup.sh
#   scripts/lab3-sandbox-setup.sh --sandbox my-lab --agent analyst
#   scripts/lab3-sandbox-setup.sh --skip-skill      # client tools only
#   scripts/lab3-sandbox-setup.sh --check           # verify, change nothing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
LAB="$ROOT/hands-on-3-agent"
RUN="$ROOT/.run"

env_get() {
  local key="$1" def="$2" val
  val="$(printenv "$key" 2>/dev/null || true)"
  if [ -z "$val" ] && [ -f "$ROOT/workshop.env" ]; then
    val="$(sed -n "s/^${key}=\([^#]*\).*/\1/p" "$ROOT/workshop.env" | tail -1 | tr -d '"'"'"' ' ')"
  fi
  printf '%s' "${val:-$def}"
}

SANDBOX="$(env_get SANDBOX my-assistant)"
AGENT="$(env_get AGENT_ID analyst)"
REASONING="$(env_get AGENT_REASONING none)"
DEFAULT_GATEWAY="$(env_get GATEWAY_URL http://127.0.0.1:18789)"
SKIP_SKILL=0
CHECK_ONLY=0
SKILL_PKGS="pandas==3.0.6 matplotlib==3.11.2 openpyxl==3.1.5"

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; RST=$'\033[0m'
ok()   { printf '  %sok%s   %s\n' "$GRN" "$RST" "$*"; }
warn() { printf '  %swarn%s %s\n' "$YEL" "$RST" "$*"; }
die()  { printf '  %sfail%s %s\n' "$RED" "$RST" "$*" >&2; exit 1; }
step() { printf '\n== %s ==\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --sandbox)    SANDBOX="$2"; shift 2 ;;
    --agent)      AGENT="$2"; shift 2 ;;
    --skip-skill) SKIP_SKILL=1; shift ;;
    --check)      CHECK_ONLY=1; shift ;;
    -h|--help)    sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

export PATH="$HOME/.local/bin:$PATH"
command -v nemoclaw >/dev/null 2>&1 || die "nemoclaw not on PATH. Run ./setup.sh first."
sbx() { nemoclaw "$SANDBOX" "$@"; }
mkdir -p "$RUN"
WS="/sandbox/.openclaw/workspace-$AGENT"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --------------------------------------------------------------------------
# Gateway URL + token, recorded for the workshop app
# --------------------------------------------------------------------------
record_gateway() {
  local url origin tok
  url="$(timeout 60 nemoclaw "$SANDBOX" dashboard-url --quiet 2>/dev/null | tr -d '\r' | grep -Eo 'https?://[^ ]+' | tail -1 || true)"
  # http://127.0.0.1:18789/#token=... -> http://127.0.0.1:18789
  origin="$(printf '%s' "$url" | sed -E 's|^(https?://[^/#?]+).*|\1|')"
  [ -n "$origin" ] || origin="$DEFAULT_GATEWAY"
  printf '%s\n' "$origin" > "$RUN/gateway-url"
  tok="$(timeout 60 nemoclaw "$SANDBOX" gateway-token --quiet 2>/dev/null | tr -d '\r' | tail -1 || true)"
  if [ -n "$tok" ]; then
    umask 077
    printf '%s\n' "$tok" > "$RUN/gateway-token"
    umask 022
  fi
  GATEWAY="$origin"
  TOKEN="$tok"
}

models_list() {
  curl -fsS -m 10 "$GATEWAY/v1/models" -H "Authorization: Bearer $TOKEN" 2>/dev/null || true
}

wait_for_agent() {  # wait until /v1/models lists openclaw/<agent>
  local i tries=30
  [ "$CHECK_ONLY" -eq 1 ] && tries=5   # start.sh runs --check on every start: fail fast
  for i in $(seq 1 "$tries"); do
    if models_list | grep -q "\"openclaw/$AGENT\""; then return 0; fi
    sleep 3
  done
  return 1
}

# A real round trip: the agent must answer with a structured tool call.
smoke_test() {
  local body out
  body=$(cat <<JSON
{"model":"openclaw/$AGENT","stream":false,
 "messages":[{"role":"user","content":"Call get_dataset_info now."}],
 "tools":[{"type":"function","function":{"name":"get_dataset_info",
   "description":"Describe the sales workbook.","parameters":{"type":"object","properties":{}}}}]}
JSON
)
  out="$(curl -sS -m 240 "$GATEWAY/v1/chat/completions" -H "Authorization: Bearer $TOKEN" \
          -H 'Content-Type: application/json' -d "$body" 2>&1 || true)"
  printf '%s' "$out" > "$RUN/lab3-smoke.json"
  printf '%s' "$out" | grep -q '"get_dataset_info"'
}

if [ "$CHECK_ONLY" -eq 1 ]; then
  record_gateway
  [ -n "$TOKEN" ] || die "no gateway token (sandbox not onboarded?)"
  wait_for_agent && ok "gateway $GATEWAY serves openclaw/$AGENT" || die "agent '$AGENT' not served at $GATEWAY"
  smoke_test && ok "tool call round trip works" || die "tool call smoke test failed (see .run/lab3-smoke.json)"
  exit 0
fi

# --------------------------------------------------------------------------
step "Sandbox '$SANDBOX'"
# --------------------------------------------------------------------------
timeout 90 nemoclaw "$SANDBOX" status >/dev/null 2>&1 \
  || die "sandbox '$SANDBOX' not reachable. Run ./setup.sh first."
ok "sandbox reachable"

# --------------------------------------------------------------------------
step "Analyst agent + chat completions endpoint"
# --------------------------------------------------------------------------
sbx download /sandbox/.openclaw/openclaw.json "$TMP/openclaw.json" >/dev/null 2>&1 \
  || die "could not download openclaw.json from the sandbox"
cp "$TMP/openclaw.json" "$RUN/openclaw.json.before-lab3"

python3 - "$TMP/openclaw.json" "$AGENT" "$WS" "$REASONING" <<'PY' > "$TMP/changes.txt"
import json, sys
path, agent, ws, reasoning = sys.argv[1:5]
raw = open(path, encoding="utf-8").read()
d = json.loads(raw[: raw.rfind("}") + 1])
changes = []

gw = d.setdefault("gateway", {})
ep = gw.setdefault("http", {}).setdefault("endpoints", {}).setdefault("chatCompletions", {})
if ep.get("enabled") is not True:
    ep["enabled"] = True
    changes.append("gateway.http.endpoints.chatCompletions.enabled = true")

agents = d.setdefault("agents", {})
lst = agents.setdefault("list", [])
if not any(a.get("id") == "main" for a in lst):
    lst.insert(0, {"id": "main", "default": True})
    changes.append("agents.list += main (default)")
want = {
    "id": agent,
    "name": "Aurora Sales Analyst",
    "workspace": ws,
    # minimal = no shell, files or web: the only tools this agent can use are
    # the ones the workshop app offers per request.
    "tools": {"profile": "minimal"},
    "skills": [],
}
cur = next((a for a in lst if a.get("id") == agent), None)
if cur is None:
    lst.append(want)
    changes.append(f"agents.list += {agent}")
else:
    for k, v in want.items():
        if cur.get(k) != v:
            cur[k] = v
            changes.append(f"agents.list[{agent}].{k} updated")

model = agents.get("defaults", {}).get("model")
primary = model.get("primary") if isinstance(model, dict) else model
if primary and reasoning and reasoning != "default":
    entry = agents.setdefault("defaults", {}).setdefault("models", {}).setdefault(primary, {})
    extra = entry.setdefault("params", {}).setdefault("extra_body", {})
    if extra.get("reasoning_effort") != reasoning:
        extra["reasoning_effort"] = reasoning
        changes.append(f"agents.defaults.models[{primary}].params.extra_body.reasoning_effort = {reasoning}")

open(path, "w", encoding="utf-8").write(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
print("\n".join(changes) if changes else "no changes")
PY
sed 's/^/  - /' "$TMP/changes.txt"

if ! grep -q "^no changes$" "$TMP/changes.txt"; then
  sbx upload "$TMP/openclaw.json" /sandbox/.openclaw/openclaw.json >/dev/null 2>&1 \
    || die "could not upload openclaw.json"
  # Keep NemoClaw's integrity hash in step, as its own config writer does.
  sbx exec -- sh -c 'cd /sandbox/.openclaw && sha256sum openclaw.json > .config-hash' >/dev/null 2>&1 || true
  ok "openclaw.json updated"
else
  ok "openclaw.json already configured"
fi

sbx exec -- mkdir -p "$WS" >/dev/null
sbx upload "$LAB/agent/AGENTS.md" "$WS/AGENTS.md" >/dev/null 2>&1 \
  || die "could not upload AGENTS.md"
ok "AGENTS.md installed in $WS"

printf '  ..   restarting the agent gateway\n'
sbx gateway restart --quiet >/dev/null 2>&1 || warn "gateway restart reported a problem"

# --------------------------------------------------------------------------
step "Verify through the host"
# --------------------------------------------------------------------------
record_gateway
[ -n "$TOKEN" ] || die "could not read the gateway token (nemoclaw $SANDBOX gateway-token)"
ok "gateway: $GATEWAY"
if ! wait_for_agent; then
  warn "gateway not answering on $GATEWAY; asking NemoClaw to repair the host forward"
  timeout 300 nemoclaw "$SANDBOX" recover >/dev/null 2>&1 || true
  record_gateway
  wait_for_agent || die "the gateway does not serve openclaw/$AGENT (see: nemoclaw $SANDBOX logs)"
fi
ok "gateway serves openclaw/$AGENT"

t0=$(date +%s)
if smoke_test; then
  ok "tool call round trip works ($(( $(date +%s) - t0 ))s)"
elif grep -qi "reasoning" "$RUN/lab3-smoke.json" 2>/dev/null && [ "$REASONING" != "default" ]; then
  warn "the model rejected reasoning_effort=$REASONING; removing it"
  sbx download /sandbox/.openclaw/openclaw.json "$TMP/openclaw.json" >/dev/null 2>&1
  python3 - "$TMP/openclaw.json" <<'PY'
import json, sys
p = sys.argv[1]
raw = open(p, encoding="utf-8").read()
d = json.loads(raw[: raw.rfind("}") + 1])
for entry in (d.get("agents", {}).get("defaults", {}).get("models") or {}).values():
    (entry.get("params") or {}).get("extra_body", {}).pop("reasoning_effort", None)
open(p, "w", encoding="utf-8").write(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
PY
  sbx upload "$TMP/openclaw.json" /sandbox/.openclaw/openclaw.json >/dev/null 2>&1
  sbx exec -- sh -c 'cd /sandbox/.openclaw && sha256sum openclaw.json > .config-hash' >/dev/null 2>&1 || true
  sbx gateway restart --quiet >/dev/null 2>&1 || true
  wait_for_agent && smoke_test && ok "tool call round trip works (reasoning left on)" \
    || die "tool call smoke test failed (see .run/lab3-smoke.json)"
else
  die "tool call smoke test failed (see .run/lab3-smoke.json)"
fi

# --------------------------------------------------------------------------
step "Skill for OpenClaw's own chat (optional)"
# --------------------------------------------------------------------------
if [ "$SKIP_SKILL" -eq 1 ]; then
  warn "skipped (--skip-skill)"
else
  skill_ok=1
  if sbx exec -- python3 -c "import pandas, matplotlib, openpyxl" >/dev/null 2>&1; then
    ok "pandas / matplotlib / openpyxl already in the sandbox"
  else
    printf '  ..   opening PyPI for the sandbox, installing, then closing it again\n'
    sbx policy add pypi --yes >/dev/null 2>&1 || warn "could not apply the pypi preset"
    # shellcheck disable=SC2086  # SKILL_PKGS is a deliberate word list
    if sbx exec --timeout 900 -- python3 -m pip install --user --break-system-packages \
         --disable-pip-version-check -q $SKILL_PKGS >"$RUN/lab3-pip.log" 2>&1; then
      ok "installed $SKILL_PKGS"
    else
      warn "pip install failed inside the sandbox (see .run/lab3-pip.log)"
      skill_ok=0
    fi
    sbx policy remove pypi --yes >/dev/null 2>&1 && ok "PyPI access closed again" \
      || warn "could not remove the pypi preset; remove it with: nemoclaw $SANDBOX policy remove pypi --yes"
  fi
  if [ "$skill_ok" -eq 1 ]; then
    STAGE="$TMP/sales-analyst"
    mkdir -p "$STAGE/scripts" "$STAGE/data"
    cp "$LAB/skills/sales-analyst/SKILL.md" "$STAGE/SKILL.md"
    cp "$LAB/tools/sales_tools.py" "$STAGE/scripts/sales_tools.py"
    cp "$LAB/data/aurora_sales_2024_2025.xlsx" "$STAGE/data/"
    if sbx skill install "$STAGE" >"$RUN/lab3-skill.log" 2>&1; then
      ok "skill 'sales-analyst' installed for the default agent"
    else
      warn "skill install failed (see .run/lab3-skill.log); the workshop app does not need it"
    fi
  fi
fi

cat <<EOF

Hands-on 3 sandbox setup complete.

  agent      : openclaw/$AGENT   (workspace $WS)
  gateway    : $GATEWAY  -> /v1/chat/completions
  app config : .run/gateway-url, .run/gateway-token

Re-check any time:  scripts/lab3-sandbox-setup.sh --check
EOF
