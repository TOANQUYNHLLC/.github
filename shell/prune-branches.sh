#!/usr/bin/env bash
# Xóa branch cục bộ đã hợp nhất vào main mà branch theo dõi trên origin đã bị xóa; không đổi branch, không kéo code.
# make sync chạy script này sau sync.sh (chuyển branch, kéo code mới).
# Pull Request hợp nhất bằng Squash tạo commit mới trên main nên `git branch -d` báo "not fully merged";
# script so nội dung từng nhóm commit nên nhận ra cả Merge lẫn nhiều lần Squash; còn thay đổi thì giữ nguyên.
# So với origin/main vừa tải về: main cục bộ có thể chưa kéo các commit hợp nhất mới.
# Mã thoát: 0 xong (kể cả khi giữ lại branch), 1 lỗi đọc git hoặc có branch không xóa được.
# Không viết bằng Python vì: script chỉ nối các lệnh git và đọc kết quả từng dòng — shell gọn và tự nhiên hơn.
set -euo pipefail

BASE_BRANCH=main
BASE=origin/$BASE_BRANCH

fail() {
	echo "❌ $*" >&2
	exit 1
}

# Một nhóm commit đã vào main nếu không đổi nội dung hoặc khớp bản vá của một commit trên main.
mergedRange() {
	local base=$1 tip=$2 squashed comparison
	git diff --quiet "$base" "$tip" && return
	# Commit tạm chỉ để so nội dung, không gắn vào ref nào: danh tính cố định để chạy được cả trên máy chưa đặt
	# user.name, user.email (commit-tree từ chối khi thiếu).
	squashed=$(git -c user.name=prune-branches -c user.email= commit-tree "$tip^{tree}" -p "$base" -m _) ||
		return
	# Giới hạn ở base: chỉ đối chiếu commit tạm, không lẫn các commit cha đã squash riêng.
	comparison=$(git cherry "$BASE" "$squashed" "$base") || return
	[[ $comparison == "- $squashed" ]]
}

# Branch đã vào main: là tổ tiên (Merge), có cây giống main, hoặc chia được toàn bộ thay đổi thành các nhóm
# khớp commit trên main (Squash). Giữ mọi điểm chia hợp lệ để một nhóm khớp sớm không che nhóm lớn hơn phía sau.
merged() {
	local branch=$1 base history tip checkpoint
	local -a checkpoints
	git merge-base --is-ancestor "$branch" "$BASE" && return
	git diff --quiet "$BASE" "$branch" && return
	base=$(git merge-base "$BASE" "$branch") || return
	mergedRange "$base" "$branch" && return
	history=$(git rev-list --first-parent --reverse "$base..$branch") || return
	checkpoints=("$base")
	while IFS= read -r tip; do
		for checkpoint in "${checkpoints[@]}"; do
			if mergedRange "$checkpoint" "$tip"; then
				checkpoints+=("$tip")
				break
			fi
		done
	done <<<"$history"
	[[ ${checkpoints[${#checkpoints[@]} - 1]} == "$(git rev-parse "$branch")" ]]
}

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "Không ở trong một repository git."
git fetch --prune --quiet origin || fail "Không tải được từ origin — kiểm tra mạng, quyền truy cập rồi chạy lại."
git rev-parse --verify --quiet "$BASE^{commit}" >/dev/null ||
	fail "Không có $BASE — không so được branch nào đã hợp nhất."
current=$(git rev-parse --show-toplevel)

# Upstream lấy dạng ref đầy đủ (refs/remotes/origin/…) rồi kiểm tra ref còn tồn tại — không dựa vào chữ "[gone]"
# của %(upstream:track) vốn là chữ hiển thị. Tên ref không chứa ":" nên dùng làm dấu phân cách; đường dẫn
# worktree đứng cuối để giữ nguyên nếu có ":". Đọc danh sách trước (lỗi đọc thì dừng), vòng lặp không chạy trong
# subshell nên lỗi của một branch không dừng các branch sau.
refs=$(git for-each-ref --format='%(refname:short):%(upstream):%(worktreepath)' refs/heads) ||
	fail "Không đọc được danh sách branch."
failures=0
while IFS=: read -r branch upstream worktree; do
	[[ $upstream == refs/remotes/origin/* ]] || continue
	git show-ref --verify --quiet "$upstream" && continue
	if [[ $branch == "$BASE_BRANCH" ]]; then
		echo "Giữ lại $branch: branch chính"
	elif [[ $worktree == "$current" ]]; then
		echo "Giữ lại $branch: đang là branch hiện tại — chuyển sang branch khác rồi chạy lại"
	elif [[ -n $worktree ]]; then
		echo "Giữ lại $branch: đang mở ở worktree $worktree"
	elif merged "$branch"; then
		git branch -D "$branch" || {
			echo "❌ Không xóa được $branch" >&2
			failures=$((failures + 1))
		}
	else
		echo "Giữ lại $branch: có thay đổi chưa vào main"
	fi
done <<<"$refs"

((failures == 0)) || exit 1
