#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# ============================================================================
#  ASK AURORA GRID — one-command setup
#  CÀI ĐẶT CHỈ VỚI MỘT LỆNH
# ============================================================================
#
#  Run this on the DGX Spark:
#      ./setup-everything.sh
#
#  Chạy lệnh này trên máy DGX Spark:
#      ./setup-everything.sh
#
#  You do not need to understand anything below. It prints progress as it goes
#  and finishes with either SETUP COMPLETE or a message telling you what to send
#  to the organizer.
#
#  Bạn không cần hiểu phần bên dưới. Chương trình sẽ báo tiến độ và kết thúc
#  bằng dòng SETUP COMPLETE, hoặc một thông báo cho biết cần gửi gì cho người
#  phụ trách.
#
#  Takes about 30-45 minutes, mostly downloading. / Mất khoảng 30-45 phút, chủ
#  yếu là thời gian tải xuống.
# ============================================================================

set -uo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$LAB_DIR"

EMBED_MODEL="${EMBED_MODEL:-qwen3-embedding:4b}"
CHAT_MODEL="${CHAT_MODEL:-qwen3:8b}"
SANDBOX="${SANDBOX:-my-assistant}"
LOG="$LAB_DIR/setup-log.txt"

# --check-only inspects the machine and downloads models, but stops before
# creating the sandbox. Safe to run any time.
CHECK_ONLY=0
[ "${1:-}" = "--check-only" ] && CHECK_ONLY=1

GRN=$'\033[32m'; RED=$'\033[31m'; YEL=$'\033[33m'; BLD=$'\033[1m'; DIM=$'\033[2m'; RST=$'\033[0m'

STEP=0
FAILED_AT=""

say()  { printf '\n%s\n' "$*"; }
ok()   { printf '   %s✔%s  %s\n' "$GRN" "$RST" "$1"; [ -n "${2:-}" ] && printf '      %s\n' "$2"; return 0; }
bad()  { printf '   %s✘%s  %s\n' "$RED" "$RST" "$1"; [ -n "${2:-}" ] && printf '      %s\n' "$2"; return 1; }
warn() { printf '   %s!%s  %s\n' "$YEL" "$RST" "$1"; [ -n "${2:-}" ] && printf '      %s\n' "$2"; return 0; }

# Every step heading is printed in both languages.
step() {
  STEP=$((STEP + 1))
  printf '\n%s──────────────────────────────────────────────────────────────%s\n' "$DIM" "$RST"
  printf '%sStep %d. %s%s\n' "$BLD" "$STEP" "$1" "$RST"
  printf '%s        %s%s\n' "$DIM" "$2" "$RST"
}

# Anything a human might need to send to the organizer goes here.
note_log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*" >> "$LOG"; }

# Run a command, tee it to the log, never abort the script.
run_logged() {
  "$@" >> "$LOG" 2>&1
}

# ---------------------------------------------------------------- welcome ---
clear 2>/dev/null || true
cat <<'BANNER'

   ┌────────────────────────────────────────────────────────┐
   │                                                        │
   │        A S K   A U R O R A   G R I D                   │
   │        Trợ lý tra cứu tài liệu kỹ thuật                │
   │                                                        │
   └────────────────────────────────────────────────────────┘

   This will set everything up on this computer.
   Chương trình sẽ cài đặt mọi thứ trên máy tính này.

   You can leave it running. It takes about 30-45 minutes.
   Bạn có thể để nó chạy. Mất khoảng 30-45 phút.

BANNER
printf '   Full details are saved to: %s\n' "$LAB_DIR/setup-log.txt"
printf '   Chi tiết đầy đủ được lưu tại: %s\n' "$LAB_DIR/setup-log.txt"

: > "$LOG"
note_log "setup started on $(uname -s) $(uname -m)"

export PATH="$HOME/.local/bin:$PATH"

# =============================================================== step 1 =====
step "Checking this computer" "Kiểm tra máy tính"

if ! command -v docker >/dev/null 2>&1; then
  bad "Docker is not installed." "Docker chưa được cài đặt."
  FAILED_AT="Docker is missing"
elif ! docker info >/dev/null 2>&1; then
  bad "Docker is installed but not running." "Docker đã cài nhưng chưa chạy."
  printf '      Try:  sudo systemctl start docker\n'
  FAILED_AT="Docker is not running"
else
  ok "Docker is running ($(docker version --format '{{.Server.Version}}' 2>/dev/null))" \
     "Docker đang chạy"
fi

# Works on both Linux (/proc) and macOS (sysctl), so the script is safe to
# dry-run on the machine it was authored on.
if [ -r /proc/meminfo ]; then
  MEM_GB=$(awk '/MemTotal/ {printf "%.0f", $2/1048576}' /proc/meminfo)
elif command -v sysctl >/dev/null 2>&1; then
  MEM_GB=$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.0f", $1/1073741824}')
else
  MEM_GB=0
fi
if command -v nproc >/dev/null 2>&1; then
  CPU_N=$(nproc)
elif command -v sysctl >/dev/null 2>&1; then
  CPU_N=$(sysctl -n hw.ncpu 2>/dev/null || echo 0)
else
  CPU_N=0
fi
FREE_GB=$(df -Pk "$LAB_DIR" | awk 'NR==2 {printf "%d", $4/1048576}')

if [ "${MEM_GB:-0}" -ge 8 ]; then ok "${MEM_GB} GB memory" "${MEM_GB} GB bộ nhớ"
else warn "${MEM_GB} GB memory — 16 GB is recommended" "${MEM_GB} GB bộ nhớ — nên có 16 GB"; fi

if [ "${FREE_GB:-0}" -ge 25 ]; then ok "${FREE_GB} GB free disk space" "${FREE_GB} GB trống"
else warn "${FREE_GB} GB free disk — 25 GB or more is safer" "${FREE_GB} GB trống — nên có từ 25 GB"; fi

if command -v nvidia-smi >/dev/null 2>&1; then
  GPU=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
  ok "Graphics card: ${GPU:-detected}" "Card đồ họa: ${GPU:-đã nhận diện}"
else
  warn "No NVIDIA graphics card detected — the model will run on the CPU and be slow" \
       "Không thấy card NVIDIA — mô hình sẽ chạy bằng CPU và rất chậm"
fi

note_log "host: ${CPU_N} cpu, ${MEM_GB} GB ram, ${FREE_GB} GB free"

# =============================================================== step 2 =====
step "Preparing the AI model server" "Chuẩn bị máy chủ mô hình AI"

if ! command -v ollama >/dev/null 2>&1; then
  printf '   Installing Ollama… / Đang cài Ollama…\n'
  if curl -fsSL https://ollama.com/install.sh | sh >> "$LOG" 2>&1; then
    ok "Ollama installed" "Đã cài Ollama"
  else
    bad "Could not install Ollama." "Không cài được Ollama."
    FAILED_AT="Ollama install failed"
  fi
else
  ok "Ollama is already installed" "Ollama đã được cài"
fi

if command -v ollama >/dev/null 2>&1; then
  if curl -fsS -m 5 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    ok "Ollama is running" "Ollama đang chạy"
  else
    printf '   Starting Ollama… / Đang khởi động Ollama…\n'
    (nohup ollama serve >> "$LOG" 2>&1 &) ; sleep 6
    if curl -fsS -m 8 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
      ok "Ollama started" "Đã khởi động Ollama"
    else
      bad "Ollama did not start." "Ollama không khởi động được."
      FAILED_AT="Ollama did not start"
    fi
  fi
fi

# =============================================================== step 3 =====
step "Downloading the AI models (about 8 GB)" "Tải mô hình AI (khoảng 8 GB)"

pull_model() {
  local model="$1"
  if curl -fsS -m 10 http://127.0.0.1:11434/api/tags 2>/dev/null | grep -q "\"$model\""; then
    ok "$model is already here" "$model đã có sẵn"
    return 0
  fi
  printf '   Downloading %s … this is the slow part\n' "$model"
  printf '   Đang tải %s … đây là phần lâu nhất\n' "$model"
  if curl -fsS -N -X POST http://127.0.0.1:11434/api/pull -d "{\"model\":\"$model\"}" \
       >> "$LOG" 2>&1; then
    ok "$model ready" "$model đã sẵn sàng"
  else
    bad "Could not download $model" "Không tải được $model"
    FAILED_AT="Model download failed: $model"
    return 1
  fi
}

if command -v ollama >/dev/null 2>&1 && curl -fsS -m 5 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  pull_model "$EMBED_MODEL"
  pull_model "$CHAT_MODEL"
fi

# =============================================================== step 4 =====
step "Installing NemoClaw" "Cài đặt NemoClaw"

if command -v nemoclaw >/dev/null 2>&1; then
  ok "NemoClaw is already installed ($(nemoclaw --version 2>&1 | head -1))" \
     "NemoClaw đã được cài"
else
  printf '   This downloads the NemoClaw tools. / Đang tải công cụ NemoClaw.\n'
  if curl -fsSL https://www.nvidia.com/nemoclaw.sh \
      | NEMOCLAW_NON_INTERACTIVE=1 bash -s -- \
        --non-interactive --yes-i-accept-third-party-software --defer-onboarding \
        >> "$LOG" 2>&1; then
    export PATH="$HOME/.local/bin:$PATH"
    ok "NemoClaw installed" "Đã cài NemoClaw"
  else
    bad "NemoClaw installation failed." "Cài NemoClaw thất bại."
    FAILED_AT="NemoClaw install failed"
  fi
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  printf '\n   %s--check-only%s: stopping before the sandbox step.\n' "$DIM" "$RST"
  printf '   %s--check-only%s: dừng trước bước tạo sandbox.\n' "$DIM" "$RST"
  exit 0
fi

# =============================================================== step 5 =====
step "Creating the secure sandbox (about 10 minutes)" \
     "Tạo sandbox bảo mật (khoảng 10 phút)"

if [ -n "$FAILED_AT" ]; then
  warn "Skipped because an earlier step failed." "Bỏ qua vì bước trước bị lỗi."
elif ! command -v nemoclaw >/dev/null 2>&1; then
  warn "Skipped — NemoClaw is not available." "Bỏ qua — chưa có NemoClaw."
else
  export NEMOCLAW_NON_INTERACTIVE=1
  export NEMOCLAW_AGENT=openclaw
  export NEMOCLAW_PROVIDER=ollama
  export NEMOCLAW_MODEL="$CHAT_MODEL"
  export NEMOCLAW_SANDBOX_NAME="$SANDBOX"
  export NEMOCLAW_POLICY_TIER=balanced

  printf '   Please wait. Do not close this window.\n'
  printf '   Vui lòng chờ. Đừng đóng cửa sổ này.\n'
  if nemoclaw onboard --name "$SANDBOX" --non-interactive \
       --yes-i-accept-third-party-software >> "$LOG" 2>&1; then
    ok "Sandbox created" "Đã tạo sandbox"
  else
    warn "Sandbox creation did not finish." "Tạo sandbox chưa xong."
    warn "Trying to repair it…" "Đang thử sửa…"
    if nemoclaw onboard --resume --name "$SANDBOX" --non-interactive \
         --yes-i-accept-third-party-software >> "$LOG" 2>&1; then
      ok "Sandbox created after repair" "Đã tạo sandbox sau khi sửa"
    else
      bad "Sandbox could not be created." "Không tạo được sandbox."
      FAILED_AT="Sandbox onboarding failed"
    fi
  fi
fi

# =============================================================== step 6 =====
step "Loading the documents and building the search index" \
     "Nạp tài liệu và xây dựng chỉ mục tìm kiếm"

if [ -n "$FAILED_AT" ]; then
  warn "Skipped because an earlier step failed." "Bỏ qua vì bước trước bị lỗi."
elif [ ! -x "$LAB_DIR/scripts/lab-setup.sh" ]; then
  bad "scripts/lab-setup.sh is missing." "Thiếu tệp scripts/lab-setup.sh."
  FAILED_AT="lab-setup.sh missing"
else
  if "$LAB_DIR/scripts/fix-sandbox-policy.sh" --sandbox "$SANDBOX" >> "$LOG" 2>&1; then
    ok "Sandbox permissions prepared" "Đã chuẩn bị quyền cho sandbox"
  else
    warn "Permission fix reported a problem (continuing)" \
         "Sửa quyền có lỗi (vẫn tiếp tục)"
  fi

  printf '   Reading 28 documents and building the index…\n'
  printf '   Đang đọc 28 tài liệu và xây chỉ mục…\n'
  if LAB_DIR="$LAB_DIR" "$LAB_DIR/scripts/lab-setup.sh" --sandbox "$SANDBOX" >> "$LOG" 2>&1; then
    ok "Documents loaded and indexed" "Đã nạp và lập chỉ mục tài liệu"
  else
    bad "Could not load the documents." "Không nạp được tài liệu."
    FAILED_AT="Document indexing failed"
  fi
fi

# =============================================================== step 7 =====
step "Final check" "Kiểm tra lần cuối"

PASS=1
if curl -fsS -m 8 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  ok "The AI model is answering" "Mô hình AI đang phản hồi"
else
  bad "The AI model is not answering" "Mô hình AI không phản hồi"; PASS=0
fi

if curl -fsS -m 10 http://127.0.0.1:11434/api/tags 2>/dev/null | grep -q "\"$EMBED_MODEL\""; then
  ok "The search model is ready" "Mô hình tìm kiếm đã sẵn sàng"
else
  bad "The search model is missing" "Thiếu mô hình tìm kiếm"; PASS=0
fi

if [ -f "$LAB_DIR/verification/reference_qa.json" ] && \
   python3 "$LAB_DIR/verification/verify_qa.py" >/dev/null 2>&1; then
  ok "The document library passed its checks" "Thư viện tài liệu đã đạt kiểm tra"
else
  warn "The document checks reported a problem" "Kiểm tra tài liệu có vấn đề"
fi

# ---------------------------------------------------------------- result ----
printf '\n'
if [ -z "$FAILED_AT" ] && [ "$PASS" -eq 1 ]; then
  cat <<EOF
   ${GRN}${BLD}┌────────────────────────────────────────────────────────┐
   │                                                        │
   │   ✔  S E T U P   C O M P L E T E                       │
   │      C À I   Đ Ặ T   H O À N   T Ấ T                    │
   │                                                        │
   └────────────────────────────────────────────────────────┘${RST}

   Everything is ready.

   ${BLD}To show the demo, run:${RST}
   ${BLD}Để trình diễn, hãy chạy:${RST}

       ./demo/start.sh --retrieval local

   Your browser will open by itself. If it does not, open:
   Trình duyệt sẽ tự mở. Nếu không, hãy mở:

       ${BLD}http://127.0.0.1:8090/${RST}

   Switch between English and Vietnamese with the ${BLD}EN / VI${RST}
   buttons in the top right corner.
   Chuyển giữa tiếng Anh và tiếng Việt bằng nút ${BLD}EN / VI${RST}
   ở góc trên bên phải.

   ${DIM}Keep this window open while presenting. Press Ctrl-C to stop.
   Giữ cửa sổ này mở trong khi trình diễn. Nhấn Ctrl-C để dừng.${RST}
EOF
  exit 0
else
  cat <<EOF
   ${RED}${BLD}┌────────────────────────────────────────────────────────┐
   │                                                        │
   │   ✘  S E T U P   N E E D S   H E L P                   │
   │      C Ầ N   H Ỗ   T R Ợ                              │
   │                                                        │
   └────────────────────────────────────────────────────────┘${RST}

   Something did not finish:
   Có bước chưa hoàn thành:

      ${BLD}${FAILED_AT:-unknown}${RST}

   ${BLD}What to do:${RST}
   ${BLD}Cần làm gì:${RST}

   1. Take a photo of this whole screen, or send the file:
      Chụp ảnh toàn bộ màn hình này, hoặc gửi tệp:

         ${BLD}$LOG${RST}

   2. Send it to the person who gave you this folder.
      Gửi cho người đã đưa bạn thư mục này.

   3. It is safe to run this setup again after they reply.
      Có thể chạy lại lệnh cài đặt sau khi họ trả lời.
EOF
  exit 1
fi
