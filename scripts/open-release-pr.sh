#!/usr/bin/env bash
# Mở Pull Request phát hành hằng tháng sau khi scripts/prepare-release.py đã sửa CHANGELOG.md.
#
# Cách dùng: scripts/open-release-pr.sh <phiên bản> <tag trước> <số commit>
# Tạo branch release/vYYYY.MM từ commit hiện tại, commit CHANGELOG.md qua GraphQL createCommitOnBranch
# (GitHub ký, thỏa quy tắc commit có chữ ký), rồi mở Pull Request. Branch đã có thì bỏ qua.
# Workflow monthly-release.yml chạy script này; GITHUB_REPOSITORY mặc định TOANQUYNHLLC/.github.
set -euo pipefail

VERSION="${1:?Cách dùng: scripts/open-release-pr.sh <phiên bản> <tag trước> <số commit>}"
PREVIOUS="${2:?thiếu tag trước}"
COMMITS="${3:?thiếu số commit}"
REPO="${GITHUB_REPOSITORY:-TOANQUYNHLLC/.github}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$(git -C "$ROOT" rev-parse HEAD)"
BRANCH="release/${VERSION%.Stable}"
TITLE="chore(release): phát hành $VERSION"

notice() {
	if [[ -n "${GITHUB_ACTIONS:-}" ]]; then echo "::$1::$2"; else echo "$2"; fi
}

if gh api "repos/$REPO/branches/$BRANCH" --silent 2>/dev/null; then
	notice notice "Branch $BRANCH đã có — Pull Request phát hành đang chờ, bỏ qua."
	exit 0
fi
gh api "repos/$REPO/git/refs" -f "ref=refs/heads/$BRANCH" -f "sha=$BASE" --silent
jq -n \
	--arg repo "$REPO" --arg branch "$BRANCH" --arg base "$BASE" --arg headline "$TITLE" \
	--arg contents "$(base64 <"$ROOT/CHANGELOG.md" | tr -d '\n')" \
	'{query: "mutation($input: CreateCommitOnBranchInput!) { createCommitOnBranch(input: $input) { commit { oid } } }",
	variables: {input: {
		branch: {repositoryNameWithOwner: $repo, branchName: $branch},
		message: {headline: $headline}, expectedHeadOid: $base,
		fileChanges: {additions: [{path: "CHANGELOG.md", contents: $contents}]}}}}' |
	gh api graphql --input - --silent

body="$(mktemp)"
trap 'rm -f "$body"' EXIT
cat >"$body" <<BODY
Phát hành hằng tháng **$VERSION**: $COMMITS commit kể từ \`$PREVIOUS\`. Mục **CHƯA PHÁT HÀNH** của \`CHANGELOG.md\` đã chuyển thành phiên bản này.

Sau khi hợp nhất (**Squash** hoặc **Merge**), người quản trị gắn tag trên \`main\`:

\`\`\`sh
git switch main && git pull --ff-only && git tag $VERSION && git push origin $VERSION
\`\`\`

Workflow \`release.yml\` tạo GitHub Release từ \`CHANGELOG.md\` (khi GitHub Actions tắt: \`scripts/create-release.sh $VERSION\`).
BODY
url="https://github.com/$REPO/compare/main...$BRANCH?expand=1"
if ! gh pr create --repo "$REPO" --base main --head "$BRANCH" --title "$TITLE" --body-file "$body" --label release; then
	notice error "Chưa mở được Pull Request (GitHub Actions cần quyền Allow GitHub Actions to create and approve pull requests). Mở tay: $url"
	[[ -n "${GITHUB_STEP_SUMMARY:-}" ]] && echo "Mở Pull Request phát hành $VERSION: $url" >>"$GITHUB_STEP_SUMMARY"
	exit 1
fi
