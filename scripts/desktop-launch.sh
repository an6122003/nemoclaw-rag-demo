#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# What the "DGX Spark Workshop" desktop icon runs, in a terminal window: start
# the workshop, and keep the window open afterwards so its messages can be read.
# (A desktop entry's Exec line cannot hold this itself: ' and ; are reserved.)

bash "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/start.sh" "$@"
printf '\n'
read -r -p "   Press Enter to close this window / Nhấn Enter để đóng cửa sổ này " _
