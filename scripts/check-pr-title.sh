#!/usr/bin/env bash
# Kiểm tra tiêu đề Pull Request (hoặc tiêu đề commit) theo quy ước '<loại>(<phạm vi>): <mô tả>' của
# CONTRIBUTING.md.
#
# Cách dùng:
#   scripts/check-pr-title.sh             # tiêu đề mọi commit của branch hiện tại so với origin/main
#   scripts/check-pr-title.sh "<tiêu đề>" # workflow pr-title.yml truyền tiêu đề Pull Request
#
# Danh sách loại phải khớp CONTRIBUTING.md và workflow-templates/pr-title.yml (validate.py kiểm tra).
set -euo pipefail

pattern='^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_-]+\))?!?: .+'

fail() {
	if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
		echo "::error::$1"
	else
		echo "✘ $1" >&2
	fi
	status=1
}

if [[ $# -gt 0 ]]; then
	titles=("$1")
else
	titles=()
	while IFS= read -r subject; do
		titles+=("$subject")
	done < <(git log --format=%s origin/main..HEAD 2>/dev/null)
fi

status=0
for title in "${titles[@]+"${titles[@]}"}"; do
	if [[ "$title" =~ $pattern ]]; then
		echo "Tiêu đề hợp lệ: $title"
	else
		fail "Tiêu đề phải theo dạng '<loại>(<phạm vi>): <mô tả>' (phạm vi tùy chọn) với loại là feat, fix, docs, style, refactor, perf, test, build, ci, chore hoặc revert — xem CONTRIBUTING.md. Tiêu đề hiện tại: $title"
	fi
done
exit "$status"
