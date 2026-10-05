#!/usr/bin/env bash
# Xóa branch cục bộ đã hợp nhất vào main mà branch trên GitHub đã bị xóa; không đổi branch, không kéo code.
# make syncmain gọi script này sau khi về main và kéo code mới (sync-main.sh).
# Pull Request hợp nhất bằng Squash tạo commit mới trên main nên `git branch -d` báo "not fully merged";
# script so theo nội dung nên nhận ra cả Merge lẫn Squash, branch còn thay đổi chưa vào main thì giữ nguyên.
# So với origin/main vừa tải về: main cục bộ có thể chưa kéo các commit hợp nhất mới.
# Không viết bằng Python vì: script chỉ nối các lệnh git và đọc kết quả từng dòng — shell gọn và tự nhiên hơn.
set -euo pipefail

BASE=origin/main

# Branch đã vào main: là tổ tiên của main (Merge), giống hệt main, hoặc toàn bộ thay đổi so với điểm tách khớp
# một commit trên main (Squash — git cherry so nội dung thay đổi, không so SHA). Không xác định được thì coi là chưa.
merged() {
	local branch=$1 base squashed
	git merge-base --is-ancestor "$branch" "$BASE" && return
	git diff --quiet "$BASE" "$branch" && return
	base=$(git merge-base "$BASE" "$branch") || return
	squashed=$(git commit-tree "$branch^{tree}" -p "$base" -m _) || return
	[[ $(git cherry "$BASE" "$squashed") == -* ]]
}

git fetch --prune --quiet
current=$(git rev-parse --show-toplevel)

# Tên ref không chứa ":" nên dùng làm dấu phân cách; đường dẫn worktree đứng cuối để giữ nguyên nếu có ":".
git for-each-ref --format='%(refname:short):%(upstream:track):%(worktreepath)' refs/heads |
	while IFS=: read -r branch track worktree; do
		[[ $track == '[gone]' ]] || continue
		if [[ $worktree == "$current" ]]; then
			echo "Giữ lại $branch: đang là branch hiện tại — chuyển sang branch khác rồi chạy lại"
		elif [[ -n $worktree ]]; then
			echo "Giữ lại $branch: đang mở ở worktree $worktree"
		elif merged "$branch"; then
			git branch -D "$branch"
		else
			echo "Giữ lại $branch: có thay đổi chưa vào main"
		fi
	done
