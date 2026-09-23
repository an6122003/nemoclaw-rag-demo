#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Start the DGX Spark AI Workshop (after ./setup.sh has run once).
# Mở workshop (sau khi đã chạy ./setup.sh một lần).
#
#   ./start.sh               open the workshop in the browser
#   ./start.sh --lan         also let other laptops on this network open it
#   ./start.sh --no-browser  do not open a browser window
#
# It checks the model server, wakes the NemoClaw sandbox if needed, and then
# serves the workshop at http://127.0.0.1:8090/ until you press Ctrl-C.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
LOG="$ROOT/.run/start-log.txt"
# shellcheck source=scripts/workshop-lib.sh
. "$ROOT/scripts/workshop-lib.sh"

LAN=0; OPEN=1
for arg in "$@"; do
  case "$arg" in
    --lan)        LAN=1 ;;
    --no-browser) OPEN=0 ;;
    -h|--help)    sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$arg"; exit 2 ;;
  esac
done
: > "$LOG"

URL="http://127.0.0.1:$HUB_PORT/"
printf '\n   %sDGX Spark AI Workshop%s — starting / đang khởi động\n\n' "$BLD" "$RST"

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  bad "The workshop is not installed yet." "Workshop chưa được cài đặt."
  info "Run:  ./setup.sh" "Hãy chạy:  ./setup.sh"
  exit 1
fi

if hub_up; then
  ok "The workshop is already running" "Workshop đang chạy"
  info "Open: $URL" "Mở: $URL"
  [ "$OPEN" -eq 1 ] && (xdg-open "$URL" >/dev/null 2>&1 &)
  exit 0
fi

# --------------------------------------------------------------- Ollama ---
if ! ollama_up; then
  info "Starting the AI model server…" "Đang khởi động máy chủ mô hình AI…"
  if command -v systemctl >/dev/null 2>&1 && systemctl cat ollama.service >/dev/null 2>&1; then
    sudo systemctl start ollama || true
  else
    nohup ollama serve >> "$RUN/ollama.log" 2>&1 &
  fi
  for _ in $(seq 1 30); do ollama_up && break; sleep 2; done
fi
if ollama_up; then
  ok "AI model server is running" "Máy chủ mô hình AI đang chạy"
else
  bad "The AI model server (Ollama) is not answering" "Máy chủ mô hình (Ollama) không phản hồi"
  info "Try: sudo systemctl restart ollama   then ./start.sh again"
  exit 1
fi

# ------------------------------------------------------------- NemoClaw ---
if command -v nemoclaw >/dev/null 2>&1; then
  if ! sandbox_ok 45; then
    info "Waking the NemoClaw sandbox (up to 3 minutes)…" "Đang đánh thức sandbox NemoClaw (tối đa 3 phút)…"
    timeout 180 nemoclaw "$SANDBOX" start >> "$LOG" 2>&1 \
      || timeout 300 nemoclaw "$SANDBOX" recover >> "$LOG" 2>&1 || true
  fi
  if sandbox_ok 45; then
    ok "NemoClaw sandbox '$SANDBOX' is running" "Sandbox NemoClaw đang chạy"
    # The embedding door for Hands-on 2 (only exists on native Linux Docker).
    if [ -f "$RUN/embed-proxy.bind" ] && ! embed_proxy_running; then
      embed_proxy_start && ok "Embedding door open for the sandbox" "Đã mở cổng mô hình tìm kiếm cho sandbox" \
        || warn "Embedding door did not open — Hands-on 2 will use the local index"
    fi
    # Hands-on 3 needs the agent gateway on the host; NemoClaw can repair it.
    if ! bash "$ROOT/scripts/lab3-sandbox-setup.sh" --check >> "$LOG" 2>&1; then
      timeout 300 nemoclaw "$SANDBOX" recover >> "$LOG" 2>&1 || true
      if bash "$ROOT/scripts/lab3-sandbox-setup.sh" --check >> "$LOG" 2>&1; then
        ok "Sales Analyst agent is ready" "Agent phân tích doanh số đã sẵn sàng"
      else
        warn "The NemoClaw agent is not answering — Hands-on 3 will run in direct mode" \
             "Agent NemoClaw không phản hồi — bài 3 sẽ chạy ở chế độ trực tiếp"
      fi
    else
      ok "Sales Analyst agent is ready" "Agent phân tích doanh số đã sẵn sàng"
    fi
  else
    warn "The sandbox is not running — labs 2 and 3 will run in direct mode" \
         "Sandbox chưa chạy — bài 2 và 3 sẽ chạy ở chế độ trực tiếp"
  fi
else
  warn "NemoClaw is not installed — labs 2 and 3 will run in direct mode"
fi

# ------------------------------------------------------------------ app ---
printf '\n'
ok "Workshop: $URL" "Mở trình duyệt tại: $URL"
if [ "$LAN" -eq 1 ]; then
  lan_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  [ -n "$lan_ip" ] && info "Other laptops: http://$lan_ip:$HUB_PORT/" "Máy khác trong mạng: http://$lan_ip:$HUB_PORT/"
fi
info "Keep this window open. Press Ctrl-C to stop." "Giữ cửa sổ này mở. Nhấn Ctrl-C để dừng."

args=(--port "$HUB_PORT")
[ "$OPEN" -eq 1 ] && args+=(--open)
[ "$LAN" -eq 1 ] && args+=(--lan)
exec "$ROOT/.venv/bin/python" "$ROOT/app/server.py" "${args[@]}"
