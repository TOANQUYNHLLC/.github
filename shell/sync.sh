#!/usr/bin/env bash
# Chuyển sang một branch rồi kéo code mới; dọn branch đã hợp nhất là việc của prune-branches.sh.
# Chạy: shell/sync.sh <branch>   (make sync: main; make sync BRANCH=<branch>: branch khác). Branch chưa có ở máy
# mà có trên origin thì git switch tự tạo branch theo dõi origin. Chỉ tua nhanh (--ff-only): branch ở máy lệch với
# origin thì dừng, không tự tạo merge commit. Mã thoát: 0 xong, 1 lỗi, 2 sai cách dùng.
# Không viết bằng Python vì: script chỉ nối các lệnh git — shell gọn và tự nhiên hơn.
set -euo pipefail

fail() {
	echo "❌ $*" >&2
	exit 1
}

if [[ $# -ne 1 || -z $1 ]]; then
	echo "Cách dùng: shell/sync.sh <branch>" >&2
	exit 2
fi

branch=$1

# Tên bắt đầu bằng "-" bị git switch hiểu là tùy chọn; tên sai quy tắc ref thì git báo lỗi khó hiểu.
git check-ref-format --branch "$branch" >/dev/null 2>&1 || fail "Tên branch không hợp lệ: $branch"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "Không ở trong một repository git."

# Thao tác đang dở (rebase, merge, cherry-pick, revert, bisect): chuyển branch lúc này làm hỏng thao tác đó.
for marker in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
	if [[ -e $(git rev-parse --git-path "$marker") ]]; then
		fail "Đang dở thao tác git ($marker) — hoàn tất hoặc hủy (--continue, --abort) rồi chạy lại."
	fi
done

# git switch mang thay đổi chưa commit sang branch đích — commit sau đó rơi nhầm vào branch khác branch đang làm.
# --untracked-files=normal: status.showUntrackedFiles=no của người dùng làm git ẩn tệp mới.
status=$(git status --porcelain --untracked-files=normal) || fail "Không đọc được trạng thái git."
[[ -z $status ]] || fail "Còn thay đổi chưa commit — commit hoặc git stash -u rồi chạy lại."

# Tải trước: branch mới tạo trên GitHub chưa có origin/<branch> ở máy thì không tạo được branch theo dõi.
git fetch --prune --quiet origin || fail "Không tải được từ origin — kiểm tra mạng, quyền truy cập rồi chạy lại."
# Branch chưa có ở máy: theo dõi đúng origin/<branch> — để git switch tự đoán thì báo "matched multiple remote
# tracking branches" khi remote khác (upstream của fork…) cũng có branch cùng tên.
if git show-ref --verify --quiet "refs/heads/$branch"; then
	git switch "$branch"
elif git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
	git switch --create "$branch" --track "origin/$branch"
else
	case $branch in
	origin/* | refs/heads/* | refs/remotes/*)
		fail "Không có branch $branch ở máy lẫn trên origin — truyền tên branch không kèm tiền tố (ví dụ ${branch##*/})."
		;;
	esac
	fail "Không có branch $branch ở máy lẫn trên origin."
fi

# Không có upstream (branch chỉ có ở máy) hoặc upstream đã bị xóa trên GitHub: không có gì để kéo.
if upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null); then
	git pull --ff-only ||
		fail "Không tua nhanh được $branch theo $upstream (branch ở máy đã lệch) — rebase hoặc merge tay rồi chạy lại."
elif [[ -n $(git config "branch.$branch.merge" || true) ]]; then
	echo "Bỏ qua git pull: branch theo dõi của $branch trên origin đã bị xóa."
else
	echo "Bỏ qua git pull: $branch chưa có branch theo dõi trên origin."
fi
