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
BASE=refs/remotes/origin/$BASE_BRANCH
MERGED_SCRIPT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../scripts" && pwd)/check-branch-merged.py

fail() {
	echo "❌ $*" >&2
	exit 1
}

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "Không ở trong một repository git."
git fetch --prune --quiet origin || fail "Không tải được từ origin — kiểm tra mạng, quyền truy cập rồi chạy lại."
git rev-parse --verify --quiet "$BASE^{commit}" >/dev/null ||
	fail "Không có origin/$BASE_BRANCH — không so được branch nào đã hợp nhất."
current=$(git rev-parse --show-toplevel)

# Upstream lấy dạng ref đầy đủ (refs/remotes/origin/…) rồi kiểm tra ref còn tồn tại — không dựa vào chữ "[gone]"
# của %(upstream:track) vốn là chữ hiển thị. Tên ref không chứa ":" nên dùng làm dấu phân cách; đường dẫn
# worktree đứng cuối để giữ nguyên nếu có ":". Đọc danh sách trước (lỗi đọc thì dừng), vòng lặp không chạy trong
# subshell nên lỗi của một branch không dừng các branch sau.
refs=$(git for-each-ref --format='%(refname):%(objectname):%(upstream):%(worktreepath)' refs/heads) ||
	fail "Không đọc được danh sách branch."
failures=0
while IFS=: read -r ref tip upstream worktree; do
	branch=${ref#refs/heads/}
	[[ $upstream == refs/remotes/origin/* ]] || continue
	upstreamStatus=0
	git show-ref --verify --quiet "$upstream" || upstreamStatus=$?
	if ((upstreamStatus == 0)); then
		continue
	elif ((upstreamStatus != 1)); then
		echo "❌ Giữ lại $branch: không đọc được branch theo dõi" >&2
		failures=$((failures + 1))
		continue
	fi
	if [[ $branch == "$BASE_BRANCH" ]]; then
		echo "Giữ lại $branch: branch chính"
	elif [[ $worktree == "$current" ]]; then
		echo "Giữ lại $branch: đang là branch hiện tại — chuyển sang branch khác rồi chạy lại"
	elif [[ -n $worktree ]]; then
		echo "Giữ lại $branch: đang mở ở worktree $worktree"
	elif "${PYTHON:-python3}" "$MERGED_SCRIPT" "$BASE" "$tip"; then
		# Đối chiếu SHA đã chụp, rồi đọc lại ref: không xóa commit mới được tạo trong lúc kiểm tra lịch sử.
		if ! latest=$(git show-ref --verify --hash "$ref"); then
			echo "❌ Giữ lại $branch: không đọc được branch sau đối chiếu" >&2
			failures=$((failures + 1))
			continue
		elif [[ $latest != "$tip" ]]; then
			echo "Giữ lại $branch: branch đã thay đổi trong lúc đối chiếu"
			continue
		fi
		git branch -D -- "$branch" || {
			echo "❌ Không xóa được $branch" >&2
			failures=$((failures + 1))
		}
	else
		status=$?
		if ((status == 1)); then
			echo "Giữ lại $branch: có thay đổi chưa vào main"
		else
			echo "❌ Giữ lại $branch: lỗi đối chiếu lịch sử" >&2
			failures=$((failures + 1))
		fi
	fi
done <<<"$refs"

((failures == 0)) || exit 1
