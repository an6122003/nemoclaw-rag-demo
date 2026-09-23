#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Hands-on 2 — repair the two OpenShell sandbox-policy defects that block the lab.
#
# Both defects were reproduced on a clean install (macOS 26.5 / Apple M5 /
# Docker Desktop 4.76, NemoClaw v0.0.124, OpenShell 0.0.116, OpenClaw 2026.7.1).
#
# ── DEFECT 1: host egress is denied ──────────────────────────────────────────
#   NemoClaw's shipped `local-inference` preset allows host.openshell.internal
#   with IPv4 RFC1918 ranges only. On Docker Desktop the sandbox /etc/hosts maps
#   that name to an IPv4 address AND an IPv6 unique-local address:
#
#       192.168.65.254        host.openshell.internal
#       fdc4:f303:9324::254   host.openshell.internal
#
#   OpenShell's SSRF guard resolves the name and checks EVERY answer against the
#   endpoint's allowed_ips, so the IPv6 answer fails and every request is denied:
#
#       {"detail":"... blocked: allowed_ips check failed","error":"ssrf_denied"}
#
#   Fix: add `fc00::/7` (IPv6 unique-local) to allowed_ips.
#   Do NOT add `fe80::/10` — the schema rejects link-local ranges at load time
#   and the whole policy becomes invalid ("invalid allowed_ips in policy").
#
# ── DEFECT 2: /opt is not readable, breaking the config guard ────────────────
#   NemoClaw's config guard validates openclaw.json with a pinned JSON5 parser
#   at /opt/nemoclaw/node_modules/json5 (see openclaw-config-guard.py:
#   JSON5_MODULE_PATH). The filesystem policy's read_only allowlist omitted /opt,
#   so the guard could not load the parser and every `nemoclaw config set` failed:
#
#       {"code":"json5-validator-failed",
#        "detail":"fixed JSON5 validator failed to run"}
#
#   Fix: add `/opt` to filesystem_policy.read_only.
#
# ── WHY RAW `openshell policy set` ───────────────────────────────────────────
#   Applying corrected presets through `nemoclaw policy add --from-file` does not
#   land: OpenShell never confirms the submission and the preset never appears in
#   `policy list`. Driving OpenShell's CLI directly reports submitted + loaded
#   versions and takes effect.
#
#   `openshell policy set` REPLACES the whole document, so this script reads the
#   live policy, patches it, and writes the complete document back.
#
# Usage
#   ./fix-sandbox-policy.sh --sandbox my-assistant
#   ./fix-sandbox-policy.sh --sandbox my-assistant --gateway-port 8814
#   ./fix-sandbox-policy.sh --sandbox my-assistant --check-only

set -euo pipefail

SANDBOX="${SANDBOX:-my-assistant}"
GATEWAY_PORT="${NEMOCLAW_GATEWAY_PORT:-8080}"
HOSTNAME_ALIAS="host.openshell.internal"
EMBED_PORT="${EMBED_PORT:-11434}"
IPV6_CIDR="fc00::/7"
CHECK_ONLY=0

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; RST=$'\033[0m'
ok()   { printf '  %sok%s   %s\n' "$GRN" "$RST" "$*"; }
warn() { printf '  %swarn%s %s\n' "$YEL" "$RST" "$*"; }
die()  { printf '  %sfail%s %s\n' "$RED" "$RST" "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --sandbox)       SANDBOX="$2"; shift 2 ;;
    --gateway-port)  GATEWAY_PORT="$2"; shift 2 ;;
    --port)          EMBED_PORT="$2"; shift 2 ;;
    --check-only)    CHECK_ONLY=1; shift ;;
    -h|--help)       sed -n '2,48p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

export PATH="$HOME/.local/bin:$PATH"
export NEMOCLAW_GATEWAY_PORT="$GATEWAY_PORT"
export OPENSHELL_GATEWAY="nemoclaw-$GATEWAY_PORT"
[ "$GATEWAY_PORT" = "8080" ] && export OPENSHELL_GATEWAY="nemoclaw"

command -v openshell >/dev/null 2>&1 || die "openshell not on PATH"
command -v nemoclaw  >/dev/null 2>&1 || die "nemoclaw not on PATH"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

# --- checks ---------------------------------------------------------------
egress_ok() {
  local code
  code="$(nemoclaw "$SANDBOX" exec -- curl -s -m 12 -o /dev/null \
    -w '%{http_code}' "http://$HOSTNAME_ALIAS:$EMBED_PORT/api/version" 2>/dev/null \
    | tr -dc '0-9' | tail -c 3)"
  [ "$code" = "200" ]
}

opt_ok() {
  nemoclaw "$SANDBOX" exec -- test -r /opt/nemoclaw/node_modules/json5/package.json 2>/dev/null
}

printf '\n== Sandbox policy check: %s ==\n' "$SANDBOX"
egress_ok && ok "host egress open" || warn "host egress blocked (defect 1)"
opt_ok    && ok "/opt readable"    || warn "/opt not readable (defect 2)"

if egress_ok; then
  ok "nothing to repair (egress already open)"
  exit 0
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  exit 1
fi

# --- read, patch, apply ---------------------------------------------------
printf '\n== Read live policy ==\n'
openshell policy get "$SANDBOX" --full -o json > "$WORKDIR/live.json" 2>/dev/null \
  || die "could not read the live policy"
ok "read live policy ($(wc -c < "$WORKDIR/live.json" | tr -d ' ') bytes)"

python3 - "$WORKDIR/live.json" "$WORKDIR/patched.json" "$HOSTNAME_ALIAS" "$IPV6_CIDR" <<'PY'
import json, sys
src, dst, alias, cidr = sys.argv[1:5]
d = json.load(open(src))
pol = d.get("policy") or d
changes = []

for name, entry in (pol.get("network_policies") or {}).items():
    for ep in entry.get("endpoints") or []:
        ips = ep.get("allowed_ips")
        if not ips or ep.get("host") != alias:
            continue
        # Link-local must never be added: rejected at load time.
        if any(i.startswith(("fe80:", "127.", "169.254")) for i in ips):
            print(f"  warning: {name} carries a range the schema rejects")
        if cidr not in ips:
            ips.append(cidr)
            changes.append(f"allowed_ips += {cidr} on {name}:{ep.get('port')}")

fs = pol.setdefault("filesystem_policy", {})
ro = fs.setdefault("read_only", [])
if "/opt" not in ro:
    ro.append("/opt")
    changes.append("filesystem_policy.read_only += /opt")

json.dump(pol, open(dst, "w"), indent=2)
if not changes:
    print("  no changes needed")
    raise SystemExit(3)
for c in changes:
    print("  " + c)
PY
py_rc=$?
[ "$py_rc" -eq 3 ] && { warn "policy already patched but checks still fail; investigate manually"; exit 1; }
[ "$py_rc" -eq 0 ] || die "failed to patch the policy"

printf '\n== Submit patched policy ==\n'
openshell policy set --policy "$WORKDIR/patched.json" --wait --timeout 120 "$SANDBOX" 2>&1 | sed 's/^/  /'
ok "policy submitted"

# --- verify ---------------------------------------------------------------
printf '\n== Verify (a running process may need a restart to pick this up) ==\n'
for attempt in 1 2 3 4 5; do
  sleep 3
  if egress_ok; then ok "host egress open"; break; fi
  warn "attempt $attempt: egress still closed"
done
if opt_ok; then
  ok "/opt readable"
else
  warn "/opt still unreadable — 'nemoclaw config set' will keep failing."
  warn "This does not block the lab: lab-setup.sh writes openclaw.json directly."
fi

egress_ok || die "host egress still blocked after the policy update"

cat <<EOF

Policy repaired.

  egress  : http://$HOSTNAME_ALIAS:$EMBED_PORT reachable from the sandbox
  /opt    : readable by the config guard

Next: ./lab-setup.sh --sandbox $SANDBOX
EOF
