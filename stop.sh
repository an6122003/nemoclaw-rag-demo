#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Stop the workshop app and the embedding proxy. / Dừng workshop.
#
#   ./stop.sh           stop the web app and the embedding proxy
#   ./stop.sh --all     also stop the NemoClaw sandbox (it keeps its data)
#
# Ollama keeps running as a system service; NemoClaw's gateway is left alone
# unless --all is given. Never pkill "nemoclaw" or "openshell": that can take
# down the OpenShell gateway and lose the sandbox registry (docs/SANDBOX-NOTES.md).

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$ROOT/.run/start-log.txt"
# shellcheck source=scripts/workshop-lib.sh
. "$ROOT/scripts/workshop-lib.sh"

pid="$(cat "$RUN/hub.pid" 2>/dev/null || true)"
if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
  kill "$pid" && ok "Workshop app stopped" "Đã dừng ứng dụng workshop"
else
  info "The workshop app was not running" "Ứng dụng workshop không chạy"
fi
rm -f "$RUN/hub.pid"

if embed_proxy_running; then
  embed_proxy_stop && ok "Embedding proxy stopped" "Đã dừng cổng mô hình tìm kiếm"
fi

if [ "${1:-}" = "--all" ] && command -v nemoclaw >/dev/null 2>&1; then
  timeout 120 nemoclaw "$SANDBOX" stop >/dev/null 2>&1 \
    && ok "NemoClaw sandbox stopped (data kept)" "Đã dừng sandbox (dữ liệu được giữ)" \
    || warn "Could not stop the sandbox"
fi
