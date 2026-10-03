#!/usr/bin/env bash
# Kiểm tra tên branch theo quy ước '<tiền tố>/<mô_tả>' của CONTRIBUTING.md.
#
# Cách dùng:
#   scripts/check-branch-name.sh            # branch hiện tại
#   scripts/check-branch-name.sh <branch>   # workflow branch-name.yml truyền github.head_ref
#
# Danh sách tiền tố phải khớp CONTRIBUTING.md và workflow-templates/branch-name.yml (validate.py kiểm tra).
set -euo pipefail

BRANCH="${1:-$(git branch --show-current)}"

fail() {
	if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
		echo "::error::$1"
	else
		echo "✘ $1" >&2
	fi
	exit 1
}

# Branch do Dependabot tạo có định dạng riêng, không áp dụng quy ước; nhánh chính không cần kiểm tra.
if [[ "$BRANCH" == dependabot/* || "$BRANCH" == main ]]; then
	echo "Bỏ qua branch: $BRANCH"
	exit 0
fi
pattern='^(feature|fix|hotfix|docs|refactor|perf|test|ci|chore|release)/[a-z0-9.]+(_[a-z0-9.]+)*$'
if [[ "$BRANCH" =~ $pattern ]]; then
	echo "Tên branch hợp lệ: $BRANCH"
else
	fail "Tên branch phải theo dạng '<tiền tố>/<mô_tả>': tiền tố là feature, fix, hotfix, docs, refactor, perf, test, ci, chore hoặc release; mô tả bằng tiếng Anh, chữ thường, các từ nối bằng dấu gạch dưới — xem CONTRIBUTING.md. Tên hiện tại: $BRANCH"
fi
