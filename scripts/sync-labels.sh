#!/usr/bin/env bash
# Đồng bộ bộ nhãn chuẩn (labels.yml) lên repository của tổ chức.
#
# Yêu cầu: GitHub CLI (gh) đã đăng nhập bằng tài khoản có quyền quản trị repository,
#          và Ruby (để đọc YAML).
#
# Cách dùng:
#   scripts/sync-labels.sh                     # xem trước cho mọi repository, không thay đổi gì
#   scripts/sync-labels.sh --apply             # áp dụng cho mọi repository của tổ chức
#   scripts/sync-labels.sh --apply ten-repo    # chỉ áp dụng cho một repository
#
# Script chỉ tạo mới hoặc cập nhật màu/mô tả; không xoá nhãn đang có trong repository.
set -euo pipefail

ORG="TOANQUYNHLLC"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPLY=false
if [[ "${1:-}" == "--apply" ]]; then
	APPLY=true
	shift
fi

command -v gh >/dev/null || { echo "Cần cài GitHub CLI: https://cli.github.com" >&2; exit 1; }
command -v ruby >/dev/null || { echo "Cần Ruby để đọc labels.yml" >&2; exit 1; }

LABELS="$(ruby -ryaml -e 'YAML.load_file(ARGV[0]).each { |l| puts [l["name"], l["color"], l["description"]].join("\t") }' "$ROOT/labels.yml")"

if [[ $# -gt 0 ]]; then
	REPOS="$1"
else
	REPOS="$(gh repo list "$ORG" --limit 500 --no-archived --json name --jq '.[].name')"
fi

for repo in $REPOS; do
	echo "== $ORG/$repo"
	while IFS=$'\t' read -r name color description; do
		if $APPLY; then
			gh label create "$name" --repo "$ORG/$repo" --color "$color" --description "$description" --force >/dev/null
			echo "   ✔ $name"
		else
			echo "   (xem trước) $name  #$color  $description"
		fi
	done <<< "$LABELS"
done

$APPLY || echo "Chế độ xem trước — chạy lại với --apply để áp dụng."
