"""Phát hành theo CHANGELOG.md (định dạng Keep a Changelog).

Chạy:
	python3 scripts/release.py notes <tag>                    # in nội dung mục ## [<tag>] (make release-notes)
	python3 scripts/release.py prepare [--version] [--date] [--open-pr]   # CHƯA PHÁT HÀNH → phiên bản của tháng
	python3 scripts/release.py open-pr <phiên bản> <tag trước> <số commit>   # Pull Request phát hành
	python3 scripts/release.py create <tag> [--allow-generated-notes]       # tạo GitHub Release

prepare: phiên bản mặc định là vYYYY.MM.Stable theo ngày ở Việt Nam; bỏ qua (mã thoát 0) khi tag đã có hoặc
không có commit kể từ tag trước; báo lỗi khi có commit mà mục CHƯA PHÁT HÀNH trống; ghi kết quả vào
$GITHUB_OUTPUT cho workflow monthly-release.yml. --open-pr (make release-pr, khi GitHub Actions tắt): làm tiếp
open-pr tại máy rồi trả CHANGELOG.md về như cũ — chỉ chạy trên main sạch, trùng origin/main.
open-pr: tạo branch release/vYYYY.MM, commit CHANGELOG.md qua GraphQL createCommitOnBranch (GitHub ký, thỏa
quy tắc commit có chữ ký) rồi mở Pull Request; branch đã có thì bỏ qua.
create: workflow release.yml (và workflow mẫu release.yml của repository khác, với --changelog CHANGELOG.md
--allow-generated-notes) gọi khi đẩy tag v*; khi GitHub Actions tắt, người quản trị chạy tại máy.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TIMEZONE = ZoneInfo('Asia/Ho_Chi_Minh')
DEFAULT_REPOSITORY = 'TOANQUYNHLLC/.github'
UNRELEASED = re.compile(
	r'^## \[CHƯA PHÁT HÀNH\]\((?P<base>[^)]+)/compare/[^)]+\.\.\.HEAD\)\n(?P<body>.*?)(?=^## \[)',
	re.MULTILINE | re.DOTALL,
)
VERSION_HEADING = re.compile(r'^## \[(?P<name>[^\]]+)\].*$', re.MULTILINE)
COMMIT_MUTATION = (
	'mutation($input: CreateCommitOnBranchInput!) { createCommitOnBranch(input: $input) '
	'{ commit { oid } } }'
)


def releaseNotes(changelog, version):
	"""Nội dung dưới tiêu đề ## [version] tới tiêu đề phiên bản kế tiếp; None nếu không có."""
	headings = list(VERSION_HEADING.finditer(changelog))
	for index, heading in enumerate(headings):
		if heading.group('name') != version:
			continue
		end = headings[index + 1].start() if index + 1 < len(headings) else len(changelog)
		body = changelog[heading.end() : end]
		body = re.split(r'^<p align="center">', body, flags=re.MULTILINE)[0]
		return re.sub(r'(^|\n)---$', '', body.strip()).strip() or None
	return None


def unreleasedNotes(changelog):
	"""Nội dung mục CHƯA PHÁT HÀNH (bỏ đường phân cách cuối), chuỗi rỗng nếu trống; None nếu sai dạng."""
	match = UNRELEASED.search(changelog)
	if not match:
		return None
	return re.sub(r'(^|\n)---$', '', match.group('body').strip()).strip()


def cutRelease(changelog, version, date):
	"""CHANGELOG mới: mục CHƯA PHÁT HÀNH trống so sánh từ version, nội dung cũ chuyển sang ## [version]."""
	match = UNRELEASED.search(changelog)
	base, notes = match.group('base'), unreleasedNotes(changelog)
	section = (
		f'## [CHƯA PHÁT HÀNH]({base}/compare/{version}...HEAD)\n\n---\n\n'
		f'## [{version}]({base}/releases/tag/{version}) — {date}\n\n{notes}\n\n---\n\n'
	)
	return changelog[: match.start()] + section + changelog[match.end() :]


def runCommand(*args, stdin=None):
	return subprocess.run(
		list(args), cwd=ROOT, input=stdin, capture_output=True, text=True, check=True
	).stdout.strip()


def reportMessage(level, message):
	"""Chú thích ::notice::/::warning::/::error:: trên GitHub Actions, dòng thường khi chạy tại máy."""
	print(f'::{level}::{message}' if os.environ.get('GITHUB_ACTIONS') else message)


def writeOutputs(**values):
	"""Ghi kết quả cho bước sau của workflow (bỏ qua khi chạy tại máy)."""
	path = os.environ.get('GITHUB_OUTPUT')
	if path:
		with open(path, 'a', encoding='utf-8') as file:
			file.writelines(f'{key}={value}\n' for key, value in values.items())


def onCleanMain():
	"""open-pr lấy HEAD làm gốc branch phát hành — tại máy phải đứng ở main sạch, trùng origin/main."""
	try:
		runCommand('git', 'fetch', '--quiet', '--tags', 'origin', 'main')
	except subprocess.CalledProcessError as exc:
		reportMessage(
			'error',
			f'Không tải được origin/main ({exc.stderr.strip()}) — kiểm tra mạng rồi chạy lại.',
		)
		return False
	if (
		runCommand('git', 'branch', '--show-current') == 'main'
		and not runCommand('git', 'status', '--porcelain')
		and runCommand('git', 'rev-parse', 'HEAD') == runCommand('git', 'rev-parse', 'origin/main')
	):
		return True
	reportMessage(
		'error',
		'Cần đứng ở main sạch, trùng origin/main: git switch main && git pull --ff-only',
	)
	return False


def prepareRelease(version, date, openPullRequest=False):
	changelogPath = ROOT / 'CHANGELOG.md'
	if openPullRequest and not onCleanMain():
		return 1
	if runCommand('git', 'tag', '--list', version):
		print(f'Đã có tag {version} — bỏ qua.')
		return 0
	described = subprocess.run(
		['git', 'describe', '--tags', '--abbrev=0', '--match', 'v*'],
		cwd=ROOT,
		capture_output=True,
		text=True,
		check=False,
	)
	if described.returncode != 0:
		reportMessage(
			'error',
			'Chưa có tag v* nào — gắn tag phát hành đầu tiên bằng tay (README → PHÁT HÀNH) rồi chạy lại.',
		)
		return 1
	previous = described.stdout.strip()
	commits = int(runCommand('git', 'rev-list', '--count', f'{previous}..HEAD'))
	if not commits:
		print(f'Không có thay đổi kể từ {previous} — bỏ qua.')
		return 0
	changelog = changelogPath.read_text(encoding='utf-8')
	if not unreleasedNotes(changelog):
		reportMessage(
			'error',
			f'Có {commits} commit kể từ {previous} nhưng mục CHƯA PHÁT HÀNH của CHANGELOG.md trống '
			'hoặc sai dạng — ghi thay đổi vào CHANGELOG.md rồi chạy lại.',
		)
		return 1
	changelogPath.write_text(cutRelease(changelog, version, date), encoding='utf-8')
	print(f'Đã chuyển CHƯA PHÁT HÀNH thành {version} ({commits} commit kể từ {previous}).')
	writeOutputs(version=version, previous=previous, commits=commits)
	if not openPullRequest:
		return 0
	try:
		return openReleasePullRequest(version, previous, commits)
	finally:
		# CHANGELOG.md đã commit lên branch phát hành qua GraphQL — main tại máy giữ nguyên.
		runCommand('git', 'checkout', '--', 'CHANGELOG.md')


def openReleasePullRequest(version, previous, commits):
	repository = os.environ.get('GITHUB_REPOSITORY', DEFAULT_REPOSITORY)
	base = runCommand('git', 'rev-parse', 'HEAD')
	branch = f'release/{version.removesuffix(".Stable")}'
	title = f'chore(release): phát hành {version}'
	exists = subprocess.run(
		['gh', 'api', f'repos/{repository}/branches/{branch}', '--silent'],
		capture_output=True,
		check=False,
	)
	if exists.returncode == 0:
		reportMessage('notice', f'Branch {branch} đã có — Pull Request phát hành đang chờ, bỏ qua.')
		return 0
	runCommand(
		'gh',
		'api',
		f'repos/{repository}/git/refs',
		'-f',
		f'ref=refs/heads/{branch}',
		'-f',
		f'sha={base}',
		'--silent',
	)
	contents = base64.b64encode((ROOT / 'CHANGELOG.md').read_bytes()).decode('ascii')
	body = {
		'query': COMMIT_MUTATION,
		'variables': {
			'input': {
				'branch': {'repositoryNameWithOwner': repository, 'branchName': branch},
				'message': {'headline': title},
				'expectedHeadOid': base,
				'fileChanges': {'additions': [{'path': 'CHANGELOG.md', 'contents': contents}]},
			}
		},
	}
	runCommand('gh', 'api', 'graphql', '--input', '-', '--silent', stdin=json.dumps(body))
	description = (
		f'Phát hành hằng tháng **{version}**: {commits} commit kể từ `{previous}`. Mục **CHƯA PHÁT '
		'HÀNH** của `CHANGELOG.md` đã chuyển thành phiên bản này.\n\n'
		'Sau khi hợp nhất (**Squash** hoặc **Merge**), người quản trị gắn tag trên `main`:\n\n'
		f'```sh\ngit switch main && git pull --ff-only && git tag {version} && '
		f'git push origin {version}\n```\n\n'
		'Workflow `release.yml` tạo GitHub Release từ `CHANGELOG.md` (khi GitHub Actions tắt: '
		f'`python3 scripts/release.py create {version}`).'
	)
	created = subprocess.run(
		[
			'gh',
			'pr',
			'create',
			'--repo',
			repository,
			'--base',
			'main',
			'--head',
			branch,
			'--title',
			title,
			'--body',
			description,
			'--label',
			'release',
		],
		capture_output=True,
		text=True,
		check=False,
	)
	if created.returncode == 0:
		print(created.stdout.strip())
		return 0
	url = f'https://github.com/{repository}/compare/main...{branch}?expand=1'
	reportMessage(
		'error',
		'Chưa mở được Pull Request (GitHub Actions cần quyền Allow GitHub Actions to create and '
		f'approve pull requests). Mở tay: {url}',
	)
	summary = os.environ.get('GITHUB_STEP_SUMMARY')
	if summary:
		with open(summary, 'a', encoding='utf-8') as file:
			file.write(f'Mở Pull Request phát hành {version}: {url}\n')
	return 1


def createRelease(tag, changelogPath, allowGeneratedNotes):
	changelog = changelogPath.read_text(encoding='utf-8') if changelogPath.exists() else ''
	notes = releaseNotes(changelog, tag)
	command = ['gh', 'release', 'create', tag, '--title', tag, '--verify-tag']
	if os.environ.get('GITHUB_REPOSITORY'):
		command += ['--repo', os.environ['GITHUB_REPOSITORY']]
	if notes:
		print(f'Dùng nội dung mục [{tag}] trong {changelogPath.name}.')
		with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.md') as file:
			file.write(notes)
			file.flush()
			subprocess.run([*command, '--notes-file', file.name], check=True)
		return 0
	if not allowGeneratedNotes:
		reportMessage(
			'error',
			f'{changelogPath.name} chưa có mục ## [{tag}] — chuyển nội dung CHƯA PHÁT HÀNH thành '
			'phiên bản này trước khi gắn tag.',
		)
		return 1
	reportMessage(
		'warning',
		f'{changelogPath.name} không có mục [{tag}] — GitHub tự tạo nội dung từ các Pull Request.',
	)
	subprocess.run([*command, '--generate-notes'], check=True)
	return 0


def printNotes(tag, changelogPath):
	notes = releaseNotes(changelogPath.read_text(encoding='utf-8'), tag)
	if not notes:
		print(
			f'{changelogPath.name} chưa có mục ## [{tag}] — hãy chuyển nội dung CHƯA PHÁT HÀNH thành '
			'phiên bản này trước khi gắn tag.',
			file=sys.stderr,
		)
		return 1
	print(notes)
	return 0


def main():
	today = datetime.now(TIMEZONE).date()
	parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
	commands = parser.add_subparsers(dest='command', required=True)
	notes = commands.add_parser('notes', help='in nội dung phát hành của một tag')
	notes.add_argument('tag')
	notes.add_argument('--changelog', type=Path, default=ROOT / 'CHANGELOG.md')
	prepare = commands.add_parser('prepare', help='chuyển CHƯA PHÁT HÀNH thành phiên bản của tháng')
	prepare.add_argument('--version', default=f'v{today:%Y.%m}.Stable')
	prepare.add_argument('--date', default=today.isoformat())
	prepare.add_argument(
		'--open-pr', action='store_true', help='mở luôn Pull Request phát hành (chạy tại máy)'
	)
	openPr = commands.add_parser('open-pr', help='mở Pull Request phát hành')
	openPr.add_argument('version')
	openPr.add_argument('previous')
	openPr.add_argument('commits')
	create = commands.add_parser('create', help='tạo GitHub Release cho tag đã đẩy')
	create.add_argument('tag')
	create.add_argument('--changelog', type=Path, default=ROOT / 'CHANGELOG.md')
	create.add_argument(
		'--allow-generated-notes',
		action='store_true',
		help='CHANGELOG không có mục của tag thì để GitHub tự tạo nội dung',
	)
	args = parser.parse_args()
	if args.command == 'notes':
		return printNotes(args.tag, args.changelog)
	if args.command == 'prepare':
		return prepareRelease(args.version, args.date, args.open_pr)
	if args.command == 'open-pr':
		return openReleasePullRequest(args.version, args.previous, args.commits)
	return createRelease(args.tag, args.changelog, args.allow_generated_notes)


if __name__ == '__main__':
	sys.exit(main())
