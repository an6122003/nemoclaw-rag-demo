#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Hands-on 1's training container on its own: download NVIDIA's PyTorch
# container, build workshop-finetune on top of it and cache the base model.
# setup.sh does the same in its Lab 1 step; the workshop app runs this script
# from the "Build it now" button when that step could not finish (a dropped
# 20 GB download, for example). Needs the internet. Safe to run again.

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT/.run/lab1-prepare.log"
# shellcheck source=scripts/workshop-lib.sh
. "$ROOT/scripts/workshop-lib.sh"

say() { printf '%s\n' "$*"; }

# A session opened before setup gave this account the docker group lacks it
# until the next login: continue inside the group.
if ! docker_ok; then
  if [ -z "${WORKSHOP_DOCKER_GROUP:-}" ] && in_docker_group && command -v sg >/dev/null 2>&1; then
    export WORKSHOP_DOCKER_GROUP=1
    exec sg docker -c "$(printf '%q ' bash "$0" "$@")"
  fi
  say "Docker is not available to this account: run the install command again."
  exit 1
fi

SHA="$(sha256sum "$ROOT/hands-on-1-finetune/Dockerfile" | cut -c1-16)"
built() { [ "$(docker image inspect -f '{{ index .Config.Labels "workshop.dockerfile" }}' "$LAB1_IMAGE" 2>/dev/null)" = "$SHA" ]; }

if ! built; then
  if ! docker image inspect "$LAB1_BASE_IMAGE" >/dev/null 2>&1; then
    for attempt in 1 2 3; do
      say "Downloading $LAB1_BASE_IMAGE (about 20 GB, attempt $attempt of 3)…"
      docker pull "$LAB1_BASE_IMAGE" && break
      sleep 10
    done
    docker image inspect "$LAB1_BASE_IMAGE" >/dev/null 2>&1 || { say "Could not download $LAB1_BASE_IMAGE — check the internet and try again."; exit 1; }
  fi
  for attempt in 1 2; do
    say "Building $LAB1_IMAGE (attempt $attempt of 2)…"
    docker build -t "$LAB1_IMAGE" --build-arg BASE_IMAGE="$LAB1_BASE_IMAGE" \
      --label "workshop.dockerfile=$SHA" "$ROOT/hands-on-1-finetune" && break
    sleep 5
  done
  built || { say "The training image did not build."; exit 1; }
fi

for attempt in 1 2 3; do
  say "Caching the base model $LAB1_BASE_HF (attempt $attempt of 3)…"
  if bash "$ROOT/hands-on-1-finetune/run_finetune.sh" --download-only; then
    say "Training container ready."
    exit 0
  fi
  sleep 10
done
say "Could not download the base model — check the internet and try again."
exit 1
