#!/usr/bin/env bash
# Về main, kéo code mới, rồi dọn branch cục bộ đã hợp nhất bằng cleanup-main.sh (make syncmain).
# Không viết bằng Python vì: script chỉ nối các lệnh git — shell gọn và tự nhiên hơn.
set -euo pipefail

# git switch mang thay đổi chưa commit sang main — commit sau đó rơi nhầm lên main thay vì branch đang làm.
if [[ -n $(git status --porcelain) ]]; then
	echo "Còn thay đổi chưa commit — commit hoặc git stash -u rồi chạy lại." >&2
	exit 1
fi
git switch main
git pull
exec "$(dirname "${BASH_SOURCE[0]}")/cleanup-main.sh"
