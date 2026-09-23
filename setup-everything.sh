#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Kept for anyone following older instructions: the one-command setup is now
# ./setup.sh, which prepares all three hands-on labs.
# Giữ lại cho hướng dẫn cũ: lệnh cài đặt hiện nay là ./setup.sh.
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/setup.sh" "$@"
