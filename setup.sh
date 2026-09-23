#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# ============================================================================
#  DGX SPARK AI WORKSHOP — one-command setup
#  WORKSHOP AI TRÊN DGX SPARK — cài đặt bằng một lệnh
# ============================================================================
#
#  On the DGX Spark, in this folder:        Trên máy DGX Spark, trong thư mục này:
#
#      ./setup.sh
#
#  It installs and checks everything for the three hands-on labs, then opens
#  the workshop in the browser. Safe to run again: finished steps are skipped.
#  Chương trình cài đặt và kiểm tra mọi thứ cho ba bài thực hành, rồi mở
#  workshop trên trình duyệt. Có thể chạy lại an toàn: bước đã xong sẽ bỏ qua.
#
#  Options / Tuỳ chọn:
#    --check-only     inspect this computer, change nothing
#    --yes            do not pause for the third-party software notice
#    --skip-finetune  skip Hands-on 1 (the 20 GB training container)
#    --skip-sandbox   skip NemoClaw (labs 2 and 3 then run in direct mode)
#    --retrain        re-run the Hands-on 1 fine-tune even if it already exists
#    --no-start       do not open the workshop app at the end
#    --force          run on a machine that is not Linux (not supported)
#
#  Everything is logged to setup-log.txt. / Mọi chi tiết được ghi vào setup-log.txt.
# ============================================================================

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
LOG="$ROOT/setup-log.txt"
# shellcheck source=scripts/workshop-lib.sh
. "$ROOT/scripts/workshop-lib.sh"

CHECK_ONLY=0; ASSUME_YES=0; SKIP_FT=0; SKIP_SB=0; RETRAIN=0; NO_START=0; FORCE=0
for arg in "$@"; do
  case "$arg" in
    --check-only)    CHECK_ONLY=1 ;;
    --yes|-y)        ASSUME_YES=1 ;;
    --skip-finetune) SKIP_FT=1 ;;
    --skip-sandbox)  SKIP_SB=1 ;;
    --retrain)       RETRAIN=1 ;;
    --no-start)      NO_START=1 ;;
    --force)         FORCE=1 ;;
    -h|--help)       sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'Unknown option: %s  (try --help)\n' "$arg"; exit 2 ;;
  esac
done

MIN_OLLAMA="0.32.9"   # NemoClaw rejects older Ollama: tool calls come back as text
STEP=0
CORE_OK=1             # Ollama + models + Python environment
LAB1="skipped"; LAB2="skipped"; LAB3="skipped"
LAB1_NOTE=""; LAB2_NOTE=""; LAB3_NOTE=""
SANDBOX_READY=0

step() {
  STEP=$((STEP + 1))
  printf '\n%s──────────────────────────────────────────────────────────────────%s\n' "$DIM" "$RST"
  printf '%sStep %d. %s%s\n' "$BLD" "$STEP" "$1" "$RST"
  printf '%s        %s%s\n' "$DIM" "$2" "$RST"
  note_log "=== step $STEP: $1"
}

version_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }

# ================================================================ welcome ===
: > "$LOG"
note_log "setup started: $(uname -a)"
clear 2>/dev/null || true
cat <<'BANNER'

   ┌──────────────────────────────────────────────────────────────┐
   │                                                              │
   │     D G X   S P A R K   A I   W O R K S H O P                │
   │     Workshop AI chạy hoàn toàn trên máy DGX Spark            │
   │                                                              │
   │     1  Fine-tuning Local LLMs   · Tinh chỉnh mô hình         │
   │     2  Build RAG with NemoClaw  · Hỏi đáp trên tài liệu      │
   │     3  Build an Agentic Workflow· Agent phân tích dữ liệu    │
   │                                                              │
   └──────────────────────────────────────────────────────────────┘

BANNER

if [ "$(uname -s)" != "Linux" ] && [ "$FORCE" -eq 0 ]; then
  bad "This setup is for the DGX Spark (Linux). This computer is $(uname -s)." \
      "Chương trình này dành cho máy DGX Spark (Linux). Hãy chạy trên máy DGX Spark."
  exit 1
fi
if [ "$(id -u)" -eq 0 ]; then
  bad "Please run it WITHOUT sudo:  ./setup.sh" "Hãy chạy KHÔNG có sudo:  ./setup.sh"
  exit 1
fi

if [ "$ASSUME_YES" -eq 0 ] && [ "$CHECK_ONLY" -eq 0 ] && [ -t 0 ]; then
  cat <<'NOTICE'
   This will download and install third-party software, each under its own
   license: Ollama, NVIDIA NemoClaw (with OpenShell and OpenClaw), uv, Python
   packages, NVIDIA's PyTorch container, and open AI models (Qwen). About
   60 GB is downloaded; it takes 45-90 minutes. Leave this window open.

   Chương trình sẽ tải và cài phần mềm của bên thứ ba, mỗi phần mềm theo giấy
   phép riêng: Ollama, NVIDIA NemoClaw (kèm OpenShell và OpenClaw), uv, các gói
   Python, container PyTorch của NVIDIA và các mô hình AI mở (Qwen). Tải khoảng
   60 GB, mất 45-90 phút. Hãy để cửa sổ này mở.

NOTICE
  printf '   Press Enter to continue, or Ctrl-C to cancel.\n'
  printf '   Nhấn Enter để tiếp tục, hoặc Ctrl-C để huỷ.  '
  read -r _
fi
printf '\n   Full details / Chi tiết đầy đủ: %s\n' "$LOG"

# ========================================================= step: computer ===
step "Checking this computer" "Kiểm tra máy tính"

if [ "$CHECK_ONLY" -eq 0 ]; then
  info "Your password may be asked once (the one you log in with)." \
       "Máy có thể hỏi mật khẩu một lần (mật khẩu đăng nhập của bạn)."
  if sudo -v; then
    ok "Administrator access granted" "Đã cấp quyền quản trị"
    # Keep sudo alive while setup runs, so a long download does not ask again.
    # Stopped again on exit and before the app starts.
    ( while kill -0 $$ 2>/dev/null; do sudo -n true 2>/dev/null; sleep 50; done ) &
    SUDO_KEEPALIVE=$!
    trap 'kill "$SUDO_KEEPALIVE" 2>/dev/null' EXIT
  else
    warn "No administrator access — some steps may fail" "Không có quyền quản trị — một số bước có thể lỗi"
  fi
fi

ARCH="$(uname -m)"
[ "$ARCH" = "aarch64" ] && ok "Processor: $ARCH (DGX Spark)" "Bộ xử lý: $ARCH" \
                        || warn "Processor: $ARCH — this bundle targets the DGX Spark (aarch64)" "Bộ xử lý: $ARCH"

if command -v nvidia-smi >/dev/null 2>&1 && GPU="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)" && [ -n "$GPU" ]; then
  ok "Graphics card: $GPU" "Card đồ hoạ: $GPU"
else
  GPU=""
  warn "No NVIDIA GPU found — models will be slow and Hands-on 1 cannot train" \
       "Không thấy GPU NVIDIA — mô hình sẽ chậm và bài 1 không huấn luyện được"
fi

MEM_GB=$(awk '/MemTotal/ {printf "%.0f", $2/1048576}' /proc/meminfo 2>/dev/null || echo 0)
[ "${MEM_GB:-0}" -ge 64 ] && ok "${MEM_GB} GB memory" "${MEM_GB} GB bộ nhớ" \
                          || warn "${MEM_GB} GB memory — 64 GB or more is recommended" "${MEM_GB} GB bộ nhớ — nên có từ 64 GB"

FREE_GB=$(df -Pk "$HOME" | awk 'NR==2 {printf "%d", $4/1048576}')
if [ "$FREE_GB" -ge 80 ]; then ok "${FREE_GB} GB free disk" "${FREE_GB} GB ổ đĩa trống"
elif [ "$FREE_GB" -ge 45 ]; then warn "${FREE_GB} GB free disk — 80 GB is safer" "${FREE_GB} GB trống — nên có 80 GB"
else bad "Only ${FREE_GB} GB free disk — about 60 GB is needed" "Chỉ còn ${FREE_GB} GB trống — cần khoảng 60 GB"; CORE_OK=0
fi

if ! command -v docker >/dev/null 2>&1; then
  bad "Docker is not installed" "Chưa cài Docker"; CORE_OK=0
elif ! docker info >/dev/null 2>&1; then
  if docker info 2>&1 | grep -qi "permission denied"; then
    bad "This user cannot use Docker" "Tài khoản này chưa được dùng Docker"
    info "Run:  sudo usermod -aG docker \$USER   then log out, log in, and run ./setup.sh again." \
         "Chạy lệnh trên, đăng xuất rồi đăng nhập lại, sau đó chạy lại ./setup.sh."
  else
    bad "Docker is not running" "Docker chưa chạy"
    info "Run:  sudo systemctl start docker"
  fi
  CORE_OK=0
else
  ok "Docker $(docker version --format '{{.Server.Version}}' 2>/dev/null)" "Docker đang chạy"
fi

for need in curl python3; do
  command -v "$need" >/dev/null 2>&1 || { bad "$need is missing" "Thiếu $need"; CORE_OK=0; }
done
if ! command -v zstd >/dev/null 2>&1 && [ "$CHECK_ONLY" -eq 0 ]; then
  # The Ollama installer unpacks a .tar.zst archive.
  # A fresh machine is often still running unattended upgrades: wait for the lock.
  run_long "Installing zstd…" sudo env DEBIAN_FRONTEND=noninteractive \
      apt-get -o DPkg::Lock::Timeout=300 install -y zstd \
    && ok "zstd installed" "Đã cài zstd" \
    || warn "Could not install zstd (the Ollama installer needs it)"
fi

NET_OK=1
for site in https://ollama.com https://registry.ollama.ai https://www.nvidia.com https://nvcr.io https://huggingface.co https://github.com; do
  if ! curl -fsS -o /dev/null -m 12 -I "$site" 2>/dev/null && ! curl -sS -o /dev/null -m 12 "$site" 2>/dev/null; then
    warn "Cannot reach $site" "Không truy cập được $site"
    NET_OK=0
  fi
done
[ "$NET_OK" -eq 1 ] && ok "Internet connection works" "Kết nối internet hoạt động"

if [ "$CORE_OK" -eq 0 ]; then
  printf '\n'
  bad "Please fix the problems above, then run ./setup.sh again." \
      "Hãy khắc phục các lỗi ở trên rồi chạy lại ./setup.sh."
  exit 1
fi

# =========================================================== step: ollama ===
step "Preparing the AI model server (Ollama)" "Chuẩn bị máy chủ mô hình AI (Ollama)"

ollama_version() { ollama --version 2>/dev/null | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | tail -1; }

if [ "$CHECK_ONLY" -eq 1 ]; then
  command -v ollama >/dev/null 2>&1 && ok "Ollama $(ollama_version) installed" || warn "Ollama not installed yet"
else
  if ! command -v ollama >/dev/null 2>&1 || ! version_ge "$(ollama_version)" "$MIN_OLLAMA"; then
    run_long "Installing Ollama… / Đang cài Ollama…" sh -c 'curl -fsSL https://ollama.com/install.sh | sh' \
      && ok "Ollama $(ollama_version) installed" "Đã cài Ollama" \
      || { bad "Could not install Ollama" "Không cài được Ollama"; show_log_tail; exit 1; }
  else
    ok "Ollama $(ollama_version) is installed" "Ollama đã được cài"
  fi

  # Settings for the systemd service. Ollama stays on loopback, which NemoClaw
  # requires on Linux; the context window must fit OpenClaw's agent prompt.
  if command -v systemctl >/dev/null 2>&1 && systemctl cat ollama.service >/dev/null 2>&1; then
    DROPIN_DIR=/etc/systemd/system/ollama.service.d
    DROPIN="$DROPIN_DIR/zz-workshop.conf"
    WANT=$(printf '[Service]\nEnvironment="OLLAMA_HOST=127.0.0.1:11434"\nEnvironment="OLLAMA_CONTEXT_LENGTH=%s"\nEnvironment="OLLAMA_KEEP_ALIVE=30m"\nEnvironment="OLLAMA_MAX_LOADED_MODELS=4"\n' "$OLLAMA_CONTEXT_LENGTH")
    if [ "$(cat "$DROPIN" 2>/dev/null)" != "$WANT" ]; then
      sudo mkdir -p "$DROPIN_DIR" && printf '%s\n' "$WANT" | sudo tee "$DROPIN" >/dev/null \
        && sudo systemctl daemon-reload && sudo systemctl enable ollama >/dev/null 2>&1 \
        && sudo systemctl restart ollama \
        && ok "Ollama configured (context ${OLLAMA_CONTEXT_LENGTH} tokens, loopback only)" "Đã cấu hình Ollama" \
        || warn "Could not write the Ollama service settings" "Không ghi được cấu hình Ollama"
    fi
    sudo systemctl start ollama >/dev/null 2>&1 || true
  elif ! ollama_up; then
    OLLAMA_HOST=127.0.0.1:11434 OLLAMA_CONTEXT_LENGTH="$OLLAMA_CONTEXT_LENGTH" OLLAMA_KEEP_ALIVE=30m \
      nohup ollama serve >> "$RUN/ollama.log" 2>&1 &
  fi
  for _ in $(seq 1 30); do ollama_up && break; sleep 2; done
  ollama_up && ok "Ollama is running" "Ollama đang chạy" \
            || { bad "Ollama did not start" "Ollama không khởi động được"; show_log_tail; exit 1; }

  # NemoClaw checks the running daemon as well as the binary: an old daemon
  # left running after an upgrade returns tool calls as plain text.
  daemon_version() { curl -fsS -m 5 "$OLLAMA_URL/api/version" 2>/dev/null | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -1; }
  if ! version_ge "$(daemon_version)" "$MIN_OLLAMA"; then
    sudo systemctl restart ollama >/dev/null 2>&1 || true
    for _ in $(seq 1 30); do ollama_up && break; sleep 2; done
  fi
  version_ge "$(daemon_version)" "$MIN_OLLAMA" \
    && ok "Ollama server version $(daemon_version)" "Phiên bản máy chủ Ollama $(daemon_version)" \
    || warn "The running Ollama is $(daemon_version); NemoClaw needs $MIN_OLLAMA or newer" \
            "Ollama đang chạy là bản $(daemon_version); NemoClaw cần từ $MIN_OLLAMA"
fi

# =========================================================== step: models ===
step "Downloading the AI models" "Tải các mô hình AI"

MODELS=("$CHAT_MODEL" "$EMBED_MODEL")
[ "$SKIP_FT" -eq 0 ] && MODELS+=("$LAB1_BASE_OLLAMA")
for m in "${MODELS[@]}"; do
  if ollama_up && ollama_has "$m"; then
    ok "$m is ready" "$m đã có sẵn"
  elif [ "$CHECK_ONLY" -eq 1 ]; then
    warn "$m not downloaded yet"
  else
    info "Downloading $m … (the biggest one takes a while)" "Đang tải $m … (mô hình lớn nhất mất khá lâu)"
    note_log "ollama pull $m"
    if ollama pull "$m"; then
      ok "$m ready" "$m đã sẵn sàng"
    else
      bad "Could not download $m" "Không tải được $m"
      CORE_OK=0
    fi
  fi
done
if ollama_up && ollama_has "$EMBED_MODEL"; then
  DIM_OUT=$(curl -fsS -m 120 "$OLLAMA_URL/api/embed" -d "{\"model\":\"$EMBED_MODEL\",\"input\":[\"probe\"]}" 2>/dev/null \
            | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["embeddings"][0]))' 2>/dev/null || echo 0)
  [ "$DIM_OUT" = "2560" ] && ok "Search model answers (2560 dimensions)" "Mô hình tìm kiếm hoạt động" \
                          || warn "Embedding size is $DIM_OUT, expected 2560 — the bundled index will not match"
fi
[ "$CORE_OK" -eq 1 ] || { bad "A model is missing — run ./setup.sh again" "Thiếu mô hình — hãy chạy lại ./setup.sh"; exit 1; }

# ========================================================== step: python ===
step "Preparing the Python environment" "Chuẩn bị môi trường Python"

venv_ok() { [ -x "$ROOT/.venv/bin/python" ] && "$ROOT/.venv/bin/python" -c "import pandas, matplotlib, openpyxl" >/dev/null 2>&1; }

if venv_ok; then
  ok "Python environment ready" "Môi trường Python đã sẵn sàng"
elif [ "$CHECK_ONLY" -eq 1 ]; then
  warn "Python environment not created yet"
else
  if ! command -v uv >/dev/null 2>&1; then
    run_long "Installing uv…" sh -c 'curl -LsSf https://astral.sh/uv/install.sh | sh' || true
  fi
  if command -v uv >/dev/null 2>&1; then
    run_long "Creating the environment… / Đang tạo môi trường…" \
      sh -c "uv venv --allow-existing --python 3.12 '$ROOT/.venv' && uv pip install --python '$ROOT/.venv/bin/python' -r '$ROOT/hands-on-3-agent/requirements.txt'" || true
  fi
  if ! venv_ok; then  # fallback without uv
    run_long "Creating the environment (pip)…" sh -c \
      "python3 -m venv '$ROOT/.venv' || { sudo env DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=300 install -y python3-venv && python3 -m venv '$ROOT/.venv'; }; '$ROOT/.venv/bin/pip' install -q -r '$ROOT/hands-on-3-agent/requirements.txt'" || true
  fi
  venv_ok && ok "Python environment ready (pandas, matplotlib, openpyxl)" "Môi trường Python đã sẵn sàng" \
          || { bad "Could not create the Python environment" "Không tạo được môi trường Python"; show_log_tail; exit 1; }
fi
PY="$ROOT/.venv/bin/python"

# ========================================================= step: nemoclaw ===
step "Installing NemoClaw and creating the secure sandbox" "Cài NemoClaw và tạo sandbox bảo mật"

if [ "$SKIP_SB" -eq 1 ]; then
  warn "Skipped (--skip-sandbox): labs 2 and 3 will run in direct mode" "Bỏ qua: bài 2 và 3 chạy ở chế độ trực tiếp"
elif [ "$CHECK_ONLY" -eq 1 ]; then
  if sandbox_ok 60; then ok "Sandbox '$SANDBOX' is running" "Sandbox đang chạy"; SANDBOX_READY=1
  else warn "Sandbox '$SANDBOX' not ready yet"; fi
else
  if command -v nemoclaw >/dev/null 2>&1; then
    ok "NemoClaw is installed ($(nemoclaw --version 2>/dev/null | head -1))" "NemoClaw đã được cài"
  else
    run_long "Installing NemoClaw… / Đang cài NemoClaw…" sh -c \
      'curl -fsSL https://www.nvidia.com/nemoclaw.sh | NEMOCLAW_NON_INTERACTIVE=1 bash -s -- --non-interactive --yes-i-accept-third-party-software --defer-onboarding' \
      && command -v nemoclaw >/dev/null 2>&1 \
      && ok "NemoClaw installed" "Đã cài NemoClaw" \
      || { bad "NemoClaw could not be installed" "Không cài được NemoClaw"; show_log_tail; }
  fi

  if command -v nemoclaw >/dev/null 2>&1; then
    if sandbox_ok 60; then
      ok "Sandbox '$SANDBOX' is running" "Sandbox '$SANDBOX' đang chạy"
      SANDBOX_READY=1
    else
      # NemoClaw checks that nothing but loopback listens on Ollama's port, so
      # the embedding proxy must be down while it onboards.
      embed_proxy_stop
      onboard() {
        env NEMOCLAW_NON_INTERACTIVE=1 NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1 NEMOCLAW_YES=1 \
            NEMOCLAW_AGENT=openclaw NEMOCLAW_PROVIDER=ollama NEMOCLAW_MODEL="$CHAT_MODEL" \
            NEMOCLAW_SANDBOX_NAME="$SANDBOX" NEMOCLAW_POLICY_TIER=balanced \
          timeout 3600 nemoclaw onboard --name "$SANDBOX" --non-interactive --yes \
            --yes-i-accept-third-party-software "$@"
      }
      info "This takes 10-20 minutes. Do not close this window." \
           "Mất 10-20 phút. Đừng đóng cửa sổ này."
      if run_long "Creating the sandbox… / Đang tạo sandbox…" onboard; then
        SANDBOX_READY=1
      elif run_long "Retrying… / Đang thử lại…" onboard --resume; then
        SANDBOX_READY=1
      fi
      if [ "$SANDBOX_READY" -eq 1 ] && sandbox_ok 90; then
        ok "Sandbox '$SANDBOX' created" "Đã tạo sandbox '$SANDBOX'"
      else
        SANDBOX_READY=0
        bad "The sandbox could not be created" "Không tạo được sandbox"
        show_log_tail
        info "The workshop still works: labs 2 and 3 will run in direct mode." \
             "Workshop vẫn chạy được: bài 2 và 3 sẽ chạy ở chế độ trực tiếp."
      fi
    fi
  fi
fi

# ==================================================== step: hands-on 2 ===
step "Hands-on 2: loading the documents into NemoClaw" "Bài 2: nạp tài liệu vào NemoClaw"

if [ "$SANDBOX_READY" -ne 1 ]; then
  LAB2="direct"; LAB2_NOTE="local index (no sandbox)"
  warn "No sandbox — questions will be answered from the local index" "Không có sandbox — dùng chỉ mục cục bộ"
elif [ "$CHECK_ONLY" -eq 1 ]; then
  LAB2="unchecked"
else
  HOST_IP="$(sandbox_host_ip)"
  note_log "host.openshell.internal -> ${HOST_IP:-unknown}"
  if [ -n "$HOST_IP" ] && is_local_ip "$HOST_IP"; then
    # Native Linux Docker: the sandbox cannot see the host's loopback Ollama,
    # so open an embeddings-only door on the address it can see.
    embed_proxy_start "$HOST_IP" && ok "Embedding door open on $HOST_IP:11434 (embeddings only)" \
      "Mở cổng riêng cho mô hình tìm kiếm tại $HOST_IP:11434" \
      || warn "Could not start the embedding proxy (see .run/embed-proxy.log)"
  else
    note_log "host.openshell.internal is not a local address; no embedding proxy needed"
  fi
  if run_long "Reading 28 documents and building the index… / Đang đọc 28 tài liệu và lập chỉ mục…" \
       bash "$ROOT/scripts/lab2-sandbox-setup.sh" --sandbox "$SANDBOX"; then
    LAB2="sandbox"
    ok "Documents indexed inside the sandbox" "Đã lập chỉ mục tài liệu trong sandbox"
  else
    LAB2="direct"; LAB2_NOTE="sandbox indexing failed; local index used"
    warn "Sandbox indexing failed — the local index will be used" "Lập chỉ mục trong sandbox lỗi — dùng chỉ mục cục bộ"
    show_log_tail 8
  fi
fi

# ==================================================== step: hands-on 3 ===
step "Hands-on 3: creating the Sales Analyst agent" "Bài 3: tạo agent phân tích doanh số"

if [ "$SANDBOX_READY" -ne 1 ]; then
  LAB3="direct"; LAB3_NOTE="direct model (no sandbox)"
  warn "No sandbox — the agent will run directly on the model" "Không có sandbox — agent chạy trực tiếp trên mô hình"
elif [ "$CHECK_ONLY" -eq 1 ]; then
  LAB3="unchecked"
else
  if run_long "Configuring the agent inside NemoClaw… / Đang cấu hình agent trong NemoClaw…" \
       bash "$ROOT/scripts/lab3-sandbox-setup.sh" --sandbox "$SANDBOX"; then
    LAB3="nemoclaw"
    ok "Agent 'openclaw/$AGENT_ID' answers tool calls" "Agent đã sẵn sàng gọi công cụ"
  else
    LAB3="direct"; LAB3_NOTE="sandbox agent setup failed; direct model used"
    warn "Agent setup in the sandbox failed — direct mode will be used" "Cấu hình agent lỗi — dùng chế độ trực tiếp"
    show_log_tail 8
  fi
fi

# ==================================================== step: hands-on 1 ===
step "Hands-on 1: preparing fine-tuning (about 20 GB)" "Bài 1: chuẩn bị tinh chỉnh mô hình (khoảng 20 GB)"

image_sha() { docker image inspect -f '{{ index .Config.Labels "workshop.dockerfile" }}' "$LAB1_IMAGE" 2>/dev/null || true; }
DOCKERFILE_SHA="$(sha256sum "$ROOT/hands-on-1-finetune/Dockerfile" | cut -c1-16)"

if [ "$SKIP_FT" -eq 1 ]; then
  LAB1="skipped"; LAB1_NOTE="--skip-finetune"
  warn "Skipped (--skip-finetune)"
elif [ -z "$GPU" ]; then
  LAB1="compare-only"; LAB1_NOTE="no GPU: training unavailable"
  warn "No GPU — training is not possible on this machine" "Không có GPU — không thể huấn luyện"
elif [ "$CHECK_ONLY" -eq 1 ]; then
  [ "$(image_sha)" = "$DOCKERFILE_SHA" ] && ok "Training image ready" || warn "Training image not built yet"
  LAB1="unchecked"
else
  LAB1="ready"
  if ! docker image inspect "$LAB1_BASE_IMAGE" >/dev/null 2>&1; then
    info "Downloading NVIDIA's PyTorch container…" "Đang tải container PyTorch của NVIDIA…"
    note_log "docker pull $LAB1_BASE_IMAGE"
    docker pull "$LAB1_BASE_IMAGE" || { LAB1="failed"; LAB1_NOTE="could not download $LAB1_BASE_IMAGE"; }
  fi
  if [ "$LAB1" = "ready" ] && [ "$(image_sha)" != "$DOCKERFILE_SHA" ]; then
    run_long "Building the training image… / Đang dựng image huấn luyện…" \
      docker build -t "$LAB1_IMAGE" --build-arg BASE_IMAGE="$LAB1_BASE_IMAGE" \
        --label "workshop.dockerfile=$DOCKERFILE_SHA" "$ROOT/hands-on-1-finetune" \
      && ok "Training image built" "Đã dựng image huấn luyện" \
      || { LAB1="failed"; LAB1_NOTE="docker build failed"; show_log_tail; }
  elif [ "$LAB1" = "ready" ]; then
    ok "Training image ready" "Image huấn luyện đã sẵn sàng"
  fi
  if [ "$LAB1" = "ready" ]; then
    run_long "Downloading $LAB1_BASE_HF… / Đang tải mô hình gốc…" \
      bash "$ROOT/hands-on-1-finetune/run_finetune.sh" --download-only \
      && ok "Base model cached for offline training" "Đã lưu sẵn mô hình gốc" \
      || { LAB1="failed"; LAB1_NOTE="base model download failed"; show_log_tail; }
  fi
  # Train once now: it proves the whole pipeline on this machine and leaves a
  # ready model, so the comparison works even if training live is skipped.
  if [ "$LAB1" = "ready" ] && { [ "$RETRAIN" -eq 1 ] || ! ollama_has "$LAB1_TUNED_MODEL"; }; then
    info "Training the example model once (a few minutes)…" "Huấn luyện thử mô hình mẫu một lần (vài phút)…"
    FT_LOG="$RUN/finetune-setup.log"
    bash "$ROOT/hands-on-1-finetune/run_finetune.sh" > "$FT_LOG" 2>&1 &
    ft_pid=$!
    while kill -0 "$ft_pid" 2>/dev/null; do
      if [ -t 1 ]; then
        # Show the latest progress line: "training step 12/60 · loss 1.234".
        line="$(grep '^@@ ' "$FT_LOG" 2>/dev/null | tail -1)"
        case "$line" in
          *'"stage": "train"'*)
            last="$(printf '%s' "$line" | sed -nE 's/.*"step": ([0-9]+), "total": ([0-9]+), "epoch": [0-9]+, "loss": ([0-9.]+).*/training step \1\/\2 · loss \3/p')" ;;
          *)
            last="$(printf '%s' "$line" | sed -nE 's/.*"stage": ?"([a-z_]+)".*/\1/p')" ;;
        esac
        printf '\r\033[K   … %s' "${last:-starting}"
      fi
      sleep 2
    done
    [ -t 1 ] && printf '\r\033[K'
    if wait "$ft_pid"; then
      cat "$FT_LOG" >> "$LOG"
      ok "Example model '$LAB1_TUNED_MODEL' trained and added to Ollama" "Đã huấn luyện và thêm mô hình '$LAB1_TUNED_MODEL'"
    else
      cat "$FT_LOG" >> "$LOG"
      LAB1="failed"; LAB1_NOTE="training failed (see .run/finetune-setup.log)"
      bad "Training failed" "Huấn luyện lỗi"; tail -n 8 "$FT_LOG" | sed 's/^/      /'
    fi
  elif [ "$LAB1" = "ready" ]; then
    ok "Fine-tuned model '$LAB1_TUNED_MODEL' already in Ollama" "Mô hình đã tinh chỉnh đã có sẵn"
  fi
fi

# ====================================================== step: final check ===
step "Final check — every lab, end to end" "Kiểm tra cuối — chạy thử từng bài"

if [ "$CHECK_ONLY" -eq 1 ]; then
  info "(skipped with --check-only)"
else
  checks=()
  case "$LAB1" in ready|compare-only) checks+=(--lab1) ;; esac
  checks+=(--lab2 --lab3)
  "$PY" "$ROOT/app/selftest.py" "${checks[@]}" --json > "$RUN/selftest.json" 2>> "$LOG" || true
  cat "$RUN/selftest.json" >> "$LOG"
  eval "$("$PY" - "$RUN/selftest.json" <<'PY'
import json, sys, shlex
try:
    results = json.load(open(sys.argv[1]))
except Exception:
    results = []
for r in results:
    n = r.get("lab")
    print(f"ST{n}_OK={1 if r.get('ok') else 0}")
    print(f"ST{n}_DETAIL={shlex.quote(str(r.get('detail', ''))[:160])}")
    print(f"ST{n}_ROUTE={shlex.quote(str(r.get('route') or ''))}")
PY
)"
  if [ "${ST1_OK:-}" = "1" ]; then ok "Hands-on 1: ${ST1_DETAIL:-}" "Bài 1 hoạt động"
  elif [ -n "${ST1_OK:-}" ]; then bad "Hands-on 1: ${ST1_DETAIL:-}"; LAB1="failed"; fi

  if [ "${ST2_OK:-}" = "1" ]; then
    ok "Hands-on 2: ${ST2_DETAIL:-}" "Bài 2 hoạt động"
    [ "${ST2_ROUTE:-}" = "sandbox" ] || { [ "$LAB2" = "sandbox" ] && LAB2="direct" && LAB2_NOTE="sandbox search did not answer; local index used"; }
  else bad "Hands-on 2: ${ST2_DETAIL:-not run}"; LAB2="failed"; fi

  if [ "${ST3_OK:-}" = "1" ]; then
    ok "Hands-on 3: ${ST3_DETAIL:-}" "Bài 3 hoạt động"
    [ "${ST3_ROUTE:-}" = "nemoclaw" ] || { [ "$LAB3" = "nemoclaw" ] && LAB3="direct" && LAB3_NOTE="NemoClaw route failed during the check; direct model used"; }
  else bad "Hands-on 3: ${ST3_DETAIL:-not run}"; LAB3="failed"; fi
fi

# Desktop shortcut, so the next start is a double-click.
if [ "$CHECK_ONLY" -eq 0 ] && [ -d "$HOME/Desktop" ]; then
  SHORTCUT="$HOME/Desktop/dgx-spark-workshop.desktop"
  cat > "$SHORTCUT" <<EOF
[Desktop Entry]
Type=Application
Name=DGX Spark Workshop
Comment=Start the three hands-on labs / Mở workshop
Exec=bash -c 'cd "$ROOT" && ./start.sh; echo; read -r -p "Press Enter to close" _'
Terminal=true
Icon=applications-science
Categories=Education;
EOF
  chmod +x "$SHORTCUT"
  gio set "$SHORTCUT" metadata::trusted true >/dev/null 2>&1 || true
fi

# ================================================================ summary ===
label() {
  case "$1" in
    sandbox|nemoclaw|ready) printf '%s✔ ready%s' "$GRN" "$RST" ;;
    direct|compare-only)    printf '%s! works, reduced%s' "$YEL" "$RST" ;;
    skipped|unchecked)      printf '%s– %s%s' "$DIM" "$1" "$RST" ;;
    *)                      printf '%s✘ needs help%s' "$RED" "$RST" ;;
  esac
}
printf '\n%s──────────────────────────────────────────────────────────────────%s\n\n' "$DIM" "$RST"
printf '   %sHands-on 1  Fine-tuning%s          %s  %s\n' "$BLD" "$RST" "$(label "$LAB1")" "$LAB1_NOTE"
printf '   %sHands-on 2  RAG with NemoClaw%s    %s  %s\n' "$BLD" "$RST" "$(label "$LAB2")" "$LAB2_NOTE"
printf '   %sHands-on 3  Agentic workflow%s     %s  %s\n' "$BLD" "$RST" "$(label "$LAB3")" "$LAB3_NOTE"
note_log "summary: lab1=$LAB1 lab2=$LAB2 lab3=$LAB3"

if [ "$CHECK_ONLY" -eq 1 ]; then
  printf '\n   --check-only: nothing was changed. / Không thay đổi gì.\n\n'
  exit 0
fi

failed=0
for s in "$LAB1" "$LAB2" "$LAB3"; do [ "$s" = "failed" ] && failed=1; done

if [ "$failed" -eq 0 ]; then
  cat <<EOF

   ${GRN}${BLD}┌──────────────────────────────────────────────────────────────┐
   │   ✔  S E T U P   C O M P L E T E                             │
   │      C À I   Đ Ặ T   H O À N   T Ấ T                          │
   └──────────────────────────────────────────────────────────────┘${RST}

   Next time, start the workshop with:     Lần sau, mở workshop bằng lệnh:

       ${BLD}./start.sh${RST}        (or double-click "DGX Spark Workshop" on the desktop)
                                (hoặc bấm đúp "DGX Spark Workshop" trên màn hình)
EOF
else
  cat <<EOF

   ${YEL}${BLD}┌──────────────────────────────────────────────────────────────┐
   │   !  SETUP FINISHED — SOME PARTS NEED HELP                  │
   │      ĐÃ CÀI XONG — MỘT SỐ PHẦN CẦN HỖ TRỢ                     │
   └──────────────────────────────────────────────────────────────┘${RST}

   The labs marked ✘ above need attention. Send this file to the organiser:
   Các bài có dấu ✘ cần hỗ trợ. Hãy gửi tệp này cho người phụ trách:

       ${BLD}$LOG${RST}

   Running ./setup.sh again is safe. / Chạy lại ./setup.sh hoàn toàn an toàn.
EOF
fi

[ -n "${SUDO_KEEPALIVE:-}" ] && kill "$SUDO_KEEPALIVE" 2>/dev/null
if [ "$NO_START" -eq 0 ]; then
  printf '\n   Opening the workshop… / Đang mở workshop…\n'
  exec bash "$ROOT/start.sh"
fi
