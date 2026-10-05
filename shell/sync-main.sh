#!/usr/bin/env bash
# Về main, kéo code mới, rồi xóa branch cục bộ đã hợp nhất mà branch trên GitHub đã bị xóa.
# Pull Request hợp nhất bằng Squash tạo commit mới trên main nên `git branch -d` báo "not fully merged";
# script so theo nội dung: thay đổi của branch đã có trên main (git cherry) hoặc branch giống hệt main thì xóa,
# còn lại giữ nguyên.
# Không viết bằng Python vì: script chỉ nối các lệnh git và đọc kết quả từng dòng — shell gọn và tự nhiên hơn.
set -euo pipefail

git switch main
git pull
git fetch --prune --quiet

git branch -vv | awk '/: gone\]/{print $1=="*"?$2:$1}' | while IFS= read -r branch; do
	squashed=$(git commit-tree "$branch^{tree}" -p "$(git merge-base main "$branch")" -m _)
	if [[ $(git cherry main "$squashed") == -* ]] || git diff --quiet main "$branch"; then
		git branch -D "$branch"
	else
		echo "Giữ lại $branch: có thay đổi chưa vào main"
	fi
done
