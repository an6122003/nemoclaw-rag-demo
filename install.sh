#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# DGX Spark AI Workshop — the one command.
# Workshop AI trên DGX Spark — lệnh duy nhất cần chạy.
#
#   curl -fsSL https://raw.githubusercontent.com/an6122003/nemoclaw-rag-demo/main/install.sh | bash
#
# Downloads the workshop into ~/dgx-workshop (or updates it if it is already
# there), then runs setup.sh, which installs everything, checks every lab and
# opens the workshop in the browser. Running the same command again is safe:
# it updates the files and skips whatever is already done.
#
# Options are passed on to setup.sh, e.g.:
#   curl -fsSL .../install.sh | bash -s -- --skip-finetune

set -uo pipefail

REPO="https://github.com/an6122003/nemoclaw-rag-demo"
BRANCH="${WORKSHOP_BRANCH:-main}"
DIR="${WORKSHOP_DIR:-$HOME/dgx-workshop}"

say()  { printf '\n   %s\n   %s\n' "$1" "$2"; }
fail() { printf '\n   ✘  %s\n      %s\n\n' "$1" "$2"; exit 1; }

if [ "$(id -u)" -eq 0 ]; then
  fail "Please run it WITHOUT sudo." "Hãy chạy KHÔNG có sudo."
fi

download_tarball() {  # for machines without git
  mkdir -p "$DIR"
  curl -fsSL "$REPO/archive/refs/heads/$BRANCH.tar.gz" | tar -xz -C "$DIR" --strip-components=1
}

if [ -d "$DIR/.git" ]; then
  say "Updating the workshop in $DIR …" "Đang cập nhật workshop …"
  if git -C "$DIR" fetch -q origin "$BRANCH"; then
    git -C "$DIR" checkout -q "$BRANCH" 2>/dev/null || git -C "$DIR" checkout -q -b "$BRANCH" "origin/$BRANCH"
    if ! git -C "$DIR" merge -q --ff-only "origin/$BRANCH" 2>/dev/null; then
      # Local edits (e.g. a participant changed AGENTS.md) are kept in a stash,
      # not thrown away, and the latest version is checked out.
      git -C "$DIR" stash push -q -m "local edits before update $(date +%F-%H%M)" || true
      git -C "$DIR" merge -q --ff-only "origin/$BRANCH" 2>/dev/null \
        || git -C "$DIR" reset -q --hard "origin/$BRANCH"
      printf '   (your local edits were saved: git -C %s stash list)\n' "$DIR"
    fi
  else
    printf '   Could not reach GitHub — using the copy already on this computer.\n'
  fi
elif [ -f "$DIR/setup.sh" ]; then
  say "Updating the workshop in $DIR …" "Đang cập nhật workshop …"
  download_tarball || printf '   Could not reach GitHub — using the copy already on this computer.\n'
else
  say "Downloading the workshop into $DIR …" "Đang tải workshop về $DIR …"
  if command -v git >/dev/null 2>&1; then
    git clone -q --branch "$BRANCH" "$REPO.git" "$DIR" \
      || fail "Could not download the workshop from GitHub." "Không tải được workshop từ GitHub. Hãy kiểm tra internet."
  else
    download_tarball \
      || fail "Could not download the workshop from GitHub." "Không tải được workshop từ GitHub. Hãy kiểm tra internet."
  fi
fi

[ -f "$DIR/setup.sh" ] || fail "The download is incomplete." "Tải về chưa đầy đủ. Hãy chạy lại lệnh."
cd "$DIR" || exit 1

# When this script arrives through `curl | bash`, its input is the download,
# not the keyboard. Hand setup.sh the terminal so it can show its notice and
# ask for the password.
if { : < /dev/tty; } 2>/dev/null; then
  exec bash setup.sh "$@" < /dev/tty
else
  exec bash setup.sh "$@"
fi
