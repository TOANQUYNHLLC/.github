#!/usr/bin/env bash
# Tạo GitHub Release cho tag đã đẩy, nội dung lấy từ mục ## [<tag>] của CHANGELOG.md.
#
# Cách dùng: scripts/create-release.sh <tag>
# Workflow release.yml chạy khi đẩy tag v*; khi GitHub Actions tắt, người quản trị chạy tại máy.
set -euo pipefail

TAG="${1:?Cách dùng: scripts/create-release.sh <tag>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
notes="$(mktemp)"
trap 'rm -f "$notes"' EXIT

python3 "$ROOT/scripts/release-notes.py" "$TAG" >"$notes"
gh release create "$TAG" --title "$TAG" --notes-file "$notes" --verify-tag
