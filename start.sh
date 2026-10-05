#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Start the DGX Spark AI Workshop (after the install command has run once).
# Mở workshop (sau khi đã chạy lệnh cài đặt một lần).
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
# Docker group membership given during setup only reaches new logins. Until
# the next login, continue inside the group so the sandbox and the training
# container work.
if [ -z "${WORKSHOP_DOCKER_GROUP:-}" ] && command -v docker >/dev/null 2>&1 && ! docker_ok \
   && docker_denied && in_docker_group && command -v sg >/dev/null 2>&1; then
  export WORKSHOP_DOCKER_GROUP=1
  exec sg docker -c "$(printf '%q ' bash "$ROOT/start.sh" "$@")"
fi

: > "$LOG"

URL="http://127.0.0.1:$HUB_PORT/"
printf '\n   %sDGX Spark AI Workshop%s — starting / đang khởi động\n\n' "$BLD" "$RST"

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  bad "The workshop is not installed yet." "Workshop chưa được cài đặt."
  info "Run the install command first:" "Hãy chạy lệnh cài đặt trước:"
  printf '\n       %s\n\n' "$INSTALL_CMD"
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
  info "Try: sudo systemctl restart ollama   then start the workshop again" \
       "Thử: sudo systemctl restart ollama   rồi mở lại workshop"
  exit 1
fi

# ------------------------------------------------------------- NemoClaw ---
if command -v nemoclaw >/dev/null 2>&1; then
  if ! sandbox_ok 45; then
    # A stopped sandbox starts again with `start`. After the computer restarts,
    # the workshop's gateway is down too, and NemoClaw starts it again through
    # onboarding, which reuses the sandbox (about 30 seconds on the Spark).
    info "Starting NemoClaw — after the computer restarts this takes 1-3 minutes…" \
         "Đang khởi động NemoClaw — sau khi máy khởi động lại, mất 1-3 phút…"
    timeout 180 nemoclaw "$SANDBOX" start >> "$LOG" 2>&1 || true
    if ! sandbox_ok 45; then
      sandbox_container_start
      ONBOARD_TIMEOUT=900 run_long "Starting the sandbox… / Đang khởi động sandbox…" nemoclaw_onboard || true
    fi
    sandbox_ok 45 || timeout 300 nemoclaw "$SANDBOX" recover >> "$LOG" 2>&1 || true
  fi
  if sandbox_ok 45; then
    ok "NemoClaw sandbox '$SANDBOX' is running" "Sandbox NemoClaw đang chạy"
    ensure_sandbox_model
    # The embedding door for Hands-on 2 (only exists on native Linux Docker).
    if [ -f "$RUN/embed-proxy.bind" ] && ! embed_proxy_running; then
      embed_proxy_start && ok "Embedding door open for the sandbox" "Đã mở cổng mô hình tìm kiếm cho sandbox" \
        || warn "Embedding door did not open — Hands-on 2 will use the local index"
    fi
    # A sandbox that had to be recreated has lost its search settings and its
    # agent (its files may survive): set them up again (Hands-on 2 about 5
    # minutes, Hands-on 3 about 1 minute).
    if ! lab2_search_ok; then
      note_log "the sandbox memory search returned nothing"
      embed_proxy_running || embed_proxy_start >> "$LOG" 2>&1 || true
      run_long "Loading the documents into NemoClaw again (about 5 minutes)… / Đang nạp lại tài liệu (khoảng 5 phút)…" \
          bash "$ROOT/scripts/lab2-sandbox-setup.sh" --sandbox "$SANDBOX" \
        && ok "Documents indexed inside the sandbox" "Đã lập chỉ mục tài liệu trong sandbox" \
        || warn "Indexing failed — Hands-on 2 will use the local index" "Lập chỉ mục lỗi — bài 2 dùng chỉ mục cục bộ"
    fi
    # Hands-on 3 needs the agent gateway on the host; NemoClaw can repair it.
    if ! bash "$ROOT/scripts/lab3-sandbox-setup.sh" --check >> "$LOG" 2>&1; then
      timeout 300 nemoclaw "$SANDBOX" recover >> "$LOG" 2>&1 || true
      # Still not answering: set the agent up again (about a minute).
      bash "$ROOT/scripts/lab3-sandbox-setup.sh" --check >> "$LOG" 2>&1 \
        || run_long "Setting up the Sales Analyst agent… / Đang cấu hình agent…" \
             bash "$ROOT/scripts/lab3-sandbox-setup.sh" --sandbox "$SANDBOX" --skip-skill || true
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
    info "To repair it, close this window and run the install command again (about 15 minutes):" \
         "Để sửa, hãy đóng cửa sổ này và chạy lại lệnh cài đặt (khoảng 15 phút):"
    printf '\n       %s\n\n' "$INSTALL_CMD"
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
# On the desktop, keep the screen from blanking and locking while the
# workshop runs: a presenter should not need the password mid-demo.
keep_awake=()
if [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ] && { [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; } \
   && command -v gnome-session-inhibit >/dev/null 2>&1; then
  keep_awake=(gnome-session-inhibit --inhibit idle --reason "DGX Spark Workshop is running")
fi
exec "${keep_awake[@]}" "$ROOT/.venv/bin/python" "$ROOT/app/server.py" "${args[@]}"
