#!/usr/bin/env bash
# Pre-commit hook: kiểm tra định dạng các file đang được stage trước khi commit.
# Cài đặt: make hooks. Bỏ qua một lần (không khuyến khích): git commit --no-verify.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

files=$(git diff --cached --name-only --diff-filter=ACMR)
if [ -z "$files" ]; then
	exit 0
fi

status=0
# Prettier tự bỏ qua file không hỗ trợ và file trong .gitignore, .prettierignore.
printf '%s\n' "$files" | tr '\n' '\0' | xargs -0 npx --no-install prettier --check --ignore-unknown || status=1

python_files=$(printf '%s\n' "$files" | grep -E '\.py$' || true)
if [ -n "$python_files" ]; then
	printf '%s\n' "$python_files" | tr '\n' '\0' | xargs -0 ruff format --check || status=1
fi

if [ "$status" -ne 0 ]; then
	echo "❌ Có file chưa đúng định dạng — chạy: make format, rồi git add lại." >&2
fi
exit "$status"
