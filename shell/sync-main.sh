#!/usr/bin/env bash
# Về main, kéo code mới, rồi xóa branch cục bộ đã hợp nhất mà branch trên GitHub đã bị xóa.
# Pull Request hợp nhất bằng Squash tạo commit mới trên main nên `git branch -d` báo "not fully merged";
# script so theo nội dung nên nhận ra cả Merge lẫn Squash, branch còn thay đổi chưa vào main thì giữ nguyên.
# Không viết bằng Python vì: script chỉ nối các lệnh git và đọc kết quả từng dòng — shell gọn và tự nhiên hơn.
set -euo pipefail

# Branch đã vào main: là tổ tiên của main (Merge), giống hệt main, hoặc toàn bộ thay đổi so với điểm tách khớp
# một commit trên main (Squash — git cherry so nội dung thay đổi, không so SHA). Không xác định được thì coi là chưa.
merged() {
	local branch=$1 base squashed
	git merge-base --is-ancestor "$branch" main && return
	git diff --quiet main "$branch" && return
	base=$(git merge-base main "$branch") || return
	squashed=$(git commit-tree "$branch^{tree}" -p "$base" -m _) || return
	[[ $(git cherry main "$squashed") == -* ]]
}

# git switch mang thay đổi chưa commit sang main — commit sau đó rơi nhầm lên main thay vì branch đang làm.
if [[ -n $(git status --porcelain) ]]; then
	echo "Còn thay đổi chưa commit — commit hoặc git stash -u rồi chạy lại." >&2
	exit 1
fi
git switch main
git pull
git fetch --prune --quiet

# Tên ref không chứa ":" nên dùng làm dấu phân cách; đường dẫn worktree đứng cuối để giữ nguyên nếu có ":".
git for-each-ref --format='%(refname:short):%(upstream:track):%(worktreepath)' refs/heads |
	while IFS=: read -r branch track worktree; do
		[[ $track == '[gone]' ]] || continue
		if [[ -n $worktree ]]; then
			echo "Giữ lại $branch: đang mở ở worktree $worktree"
		elif merged "$branch"; then
			git branch -D "$branch"
		else
			echo "Giữ lại $branch: có thay đổi chưa vào main"
		fi
	done
