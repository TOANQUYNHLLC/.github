#!/usr/bin/env bash
# Chuyển sang branch (mặc định main), kéo code mới, rồi dọn branch cục bộ đã hợp nhất bằng prune-branches.sh.
# Chạy: shell/sync.sh [branch]   (make sync BRANCH=<branch>). Branch chưa có ở máy mà có trên origin thì git switch
# tự tạo branch theo dõi origin.
# Không viết bằng Python vì: script chỉ nối các lệnh git — shell gọn và tự nhiên hơn.
set -euo pipefail

branch=${1:-main}

# git switch mang thay đổi chưa commit sang branch đích — commit sau đó rơi nhầm vào branch khác branch đang làm.
if [[ -n $(git status --porcelain) ]]; then
	echo "Còn thay đổi chưa commit — commit hoặc git stash -u rồi chạy lại." >&2
	exit 1
fi

# Tải trước: branch mới tạo trên GitHub chưa có origin/<branch> ở máy thì git switch không tạo được branch theo dõi.
git fetch --prune --quiet
git switch "$branch"

# Branch chỉ có ở máy (chưa đẩy lên) không có upstream để kéo — vẫn dọn branch đã hợp nhất.
if git rev-parse --abbrev-ref '@{upstream}' >/dev/null 2>&1; then
	git pull
else
	echo "Bỏ qua git pull: $branch chưa có branch theo dõi trên origin."
fi

exec "$(dirname "${BASH_SOURCE[0]}")/prune-branches.sh"
