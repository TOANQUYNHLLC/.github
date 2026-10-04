"""Phát hành theo CHANGELOG.md (định dạng Keep a Changelog).

Chạy:
	python3 scripts/release.py notes <tag>                    # in nội dung mục ## [<tag>] (make release-notes)
	python3 scripts/release.py prepare [--version] [--date] [--channel] [--open-pr] # chuẩn bị phiên bản
	python3 scripts/release.py open-pr <phiên bản> <tag trước> <số commit>   # Pull Request phát hành
	python3 scripts/release.py create <tag> [--allow-generated-notes]       # tạo GitHub Release

prepare: phiên bản có dạng Stable.vYYYY.MM.DDXXXX hoặc Beta.vYYYY.MM.DDXXXX theo ngày ở Việt Nam;
mặc định Stable, chọn Beta bằng --channel Beta. Số thứ tự có bốn chữ số, dùng chung cho hai kênh,
bắt đầu lại từ 0001 mỗi tháng; bỏ qua (mã thoát 0) khi tag đã có hoặc không có commit kể từ tag trước;
báo lỗi khi có commit mà mục CHƯA PHÁT HÀNH trống; ghi kết quả vào
$GITHUB_OUTPUT cho workflow monthly-release.yml. --open-pr (make release-pr, khi GitHub Actions tắt): làm tiếp
open-pr tại máy rồi trả CHANGELOG.md về như cũ — chỉ chạy trên main sạch, trùng origin/main.
open-pr: tạo branch release/stable.vYYYY.MM.DDXXXX hoặc release/beta.vYYYY.MM.DDXXXX,
commit CHANGELOG.md qua GraphQL createCommitOnBranch (GitHub ký, thỏa
quy tắc commit có chữ ký) rồi mở Pull Request; đọc và kiểm tra UTF-8 của CHANGELOG.md trước khi tạo branch;
branch đã có thì chỉ bỏ qua khi có Pull Request đang mở;
commit lỗi thì thử xóa branch vừa tạo và báo kết quả để lần chạy sau làm lại.
create: workflow release.yml (và workflow mẫu release.yml của repository khác, với --changelog CHANGELOG.md
--allow-generated-notes) gọi khi đẩy tag Stable.v*, Beta.v* hoặc v*; Beta là bản phát hành thử nghiệm.
Khi GitHub Actions tắt, người quản trị chạy tại máy.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date as CalendarDate
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from orgsetup import github

ROOT = Path(__file__).resolve().parents[1]
TIMEZONE = ZoneInfo('Asia/Ho_Chi_Minh')
DEFAULT_REPOSITORY = 'TOANQUYNHLLC/.github'
UNRELEASED = re.compile(
	r'^## \[CHƯA PHÁT HÀNH\]\((?P<base>[^)]+)/compare/[^)]+\.\.\.HEAD\)\n'
	r'(?P<body>.*?)(?=^## \[|^<p align="center">|\Z)',
	re.MULTILINE | re.DOTALL,
)
VERSION_HEADING = re.compile(r'^## \[(?P<name>[^\]]+)\].*$', re.MULTILINE)
RELEASE_CHANNELS = ('Stable', 'Beta')
RELEASE_VERSION = re.compile(
	r'(?P<channel>Stable|Beta)\.v(?P<year>[0-9]{4})\.(?P<month>0[1-9]|1[0-2])\.'
	r'(?P<day>[0-9]{2})(?P<sequence>(?!0000)[0-9]{4})'
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
	"""Nội dung CHƯA PHÁT HÀNH, kể cả mục cuối tệp; bỏ đường phân cách.

	Chuỗi rỗng nếu trống; None nếu sai dạng.
	"""
	match = UNRELEASED.search(changelog)
	if not match:
		return None
	return re.sub(r'(^|\n)---$', '', match.group('body').strip()).strip()


def cutRelease(changelog, version, date):
	"""CHANGELOG mới: mục CHƯA PHÁT HÀNH trống so sánh từ version, nội dung chuyển sang ## [version] để
	release.yml đọc khi gắn tag. Mục của các phiên bản trước bị bỏ: lịch sử phát hành nằm ở GitHub Release,
	CHANGELOG.md không tích luỹ nhật ký thay đổi; chân trang giữ nguyên."""
	match = UNRELEASED.search(changelog)
	base, notes = match.group('base'), unreleasedNotes(changelog)
	section = (
		f'## [CHƯA PHÁT HÀNH]({base}/compare/{version}...HEAD)\n\n---\n\n'
		f'## [{version}]({base}/releases/tag/{version}) — {date}\n\n{notes}\n\n---\n\n'
	)
	rest = changelog[match.end() :]
	footer = re.search(r'^<p align="center">', rest, re.MULTILINE)
	return changelog[: match.start()] + section + (rest[footer.start() :] if footer else '')


def runCommand(*args, stdin=None):
	return subprocess.run(
		list(args), cwd=ROOT, input=stdin, capture_output=True, text=True, check=True
	).stdout.strip()


def reportMessage(level, message):
	"""Chú thích ::notice::/::warning::/::error:: trên GitHub Actions, dòng thường khi chạy tại máy."""
	if os.environ.get('GITHUB_ACTIONS'):
		message = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
		print(f'::{level}::{message}')
	else:
		print(message)


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


def validateReleaseInputs(version, date=None):
	"""Phiên bản chứa ngày có thật, trùng ngày chuẩn bị; kiểm tra trước khi gọi Git hoặc sửa CHANGELOG."""
	match = RELEASE_VERSION.fullmatch(version) if isinstance(version, str) else None
	if not match:
		raise ValueError(
			'Phiên bản phát hành phải là Stable.vYYYY.MM.DDXXXX hoặc Beta.vYYYY.MM.DDXXXX '
			'với ngày hợp lệ và số thứ tự từ 0001 đến 9999.'
		)
	versionDate = validateReleaseDate(f'{match["year"]}-{match["month"]}-{match["day"]}')
	if date is not None and validateReleaseDate(date) != versionDate:
		raise ValueError('Ngày trong phiên bản phải trùng ngày chuẩn bị phát hành.')


def validateReleaseDate(date):
	"""Kiểm tra ngày ISO có thật và trả về ngày để chọn tháng phát hành."""
	if not isinstance(date, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', date):
		raise ValueError('Ngày phát hành phải có dạng YYYY-MM-DD.')
	try:
		return CalendarDate.fromisoformat(date)
	except ValueError as exc:
		raise ValueError(f'Ngày phát hành không có thật: {date}') from exc


def nextReleaseVersion(date, channel='Stable'):
	"""Tăng số thứ tự chung của Stable và Beta trong tháng; tháng mới bắt đầu từ 0001."""
	month = validateReleaseDate(date)
	if channel not in RELEASE_CHANNELS:
		raise ValueError('Kênh phát hành phải là Stable hoặc Beta.')
	tags = runCommand(
		'git', 'tag', '--list', f'*.v{month.year:04d}.{month.month:02d}.*'
	).splitlines()
	maxSequence = 0
	for tag in tags:
		try:
			validateReleaseInputs(tag)
		except ValueError:
			continue
		match = RELEASE_VERSION.fullmatch(tag)
		if int(match['year']) == month.year and int(match['month']) == month.month:
			maxSequence = max(maxSequence, int(match['sequence']))
	sequence = maxSequence + 1
	if sequence > 9999:
		raise ValueError(
			'Số thứ tự phát hành trong tháng đã đạt 9999 — không thể tạo phiên bản tiếp theo.'
		)
	return f'{channel}.v{month.year:04d}.{month.month:02d}.{month.day:02d}{sequence:04d}'


def prepareRelease(version, date, openPullRequest=False, channel='Stable'):
	if version is None:
		validateReleaseDate(date)
		if channel not in RELEASE_CHANNELS:
			raise ValueError('Kênh phát hành phải là Stable hoặc Beta.')
	else:
		validateReleaseInputs(version, date)
	changelogPath = ROOT / 'CHANGELOG.md'
	if openPullRequest and not onCleanMain():
		return 1
	if version is None:
		version = nextReleaseVersion(date, channel)
	if runCommand('git', 'tag', '--list', version):
		print(f'Đã có tag {version} — bỏ qua.')
		return 0
	described = subprocess.run(
		[
			'git',
			'describe',
			'--tags',
			'--abbrev=0',
			'--match',
			'Stable.v*',
			'--match',
			'Beta.v*',
			'--match',
			'v*',
		],
		cwd=ROOT,
		capture_output=True,
		text=True,
		check=False,
	)
	if described.returncode != 0:
		reportMessage(
			'error',
			'Chưa có tag phát hành nào — gắn tag phát hành đầu tiên bằng tay (README → PHÁT HÀNH) rồi chạy lại.',
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
	validateReleaseInputs(version)
	channel = RELEASE_VERSION.fullmatch(version)['channel']
	repository = os.environ.get('GITHUB_REPOSITORY') or DEFAULT_REPOSITORY
	base = runCommand('git', 'rev-parse', 'HEAD')
	branch = f'release/{version.lower()}'
	title = f'chore(release): phát hành {version}'
	try:
		exists = github.ghExists(f'repos/{repository}/branches/{branch}')
		if exists:
			pullRequests = github.ghJson(
				'pr',
				'list',
				'--repo',
				repository,
				'--base',
				'main',
				'--head',
				branch,
				'--state',
				'open',
				'--json',
				'url',
			)
			if not isinstance(pullRequests, list) or any(
				not isinstance(item, dict)
				or not isinstance(item.get('url'), str)
				or not item['url']
				for item in pullRequests
			):
				raise ValueError('phản hồi danh sách Pull Request không hợp lệ')
	except (RuntimeError, ValueError) as exc:
		reportMessage('error', f'Không đọc được trạng thái phát hành {branch}: {exc}')
		return 1
	if exists:
		if pullRequests:
			reportMessage('notice', f'Pull Request phát hành đang chờ: {pullRequests[0]["url"]}')
			return 0
		reportMessage(
			'error',
			f'Branch {branch} đã có nhưng chưa có Pull Request đang mở — kiểm tra nội dung và mở tay: '
			f'https://github.com/{repository}/compare/main...{branch}?expand=1',
		)
		return 1
	try:
		changelog = (ROOT / 'CHANGELOG.md').read_bytes()
		changelog.decode('utf-8')
	except (OSError, UnicodeError) as exc:
		reportMessage('error', f'Không đọc được CHANGELOG.md: {exc}')
		return 1
	contents = base64.b64encode(changelog).decode('ascii')
	try:
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
	except subprocess.CalledProcessError as exc:
		reportMessage('error', f'Không tạo được branch {branch}: {exc.stderr.strip()}')
		return 1
	body = {
		'query': github.COMMIT_MUTATION,
		'variables': {
			'input': {
				'branch': {'repositoryNameWithOwner': repository, 'branchName': branch},
				'message': {'headline': title},
				'expectedHeadOid': base,
				'fileChanges': {'additions': [{'path': 'CHANGELOG.md', 'contents': contents}]},
			}
		},
	}
	try:
		runCommand('gh', 'api', 'graphql', '--input', '-', '--silent', stdin=json.dumps(body))
	except subprocess.CalledProcessError as exc:
		# Xóa branch vừa tạo nếu commit lỗi; giữ nguyên lỗi xóa để người vận hành kiểm tra khi chạy lại.
		deleted = subprocess.run(
			[
				'gh',
				'api',
				'-X',
				'DELETE',
				f'repos/{repository}/git/refs/heads/{branch}',
				'--silent',
			],
			capture_output=True,
			text=True,
			check=False,
		)
		cleanup = (
			'đã xóa branch, sửa lỗi rồi chạy lại.'
			if deleted.returncode == 0
			else f'chưa xóa được branch ({deleted.stderr.strip()}) — kiểm tra branch trên GitHub trước khi chạy lại.'
		)
		reportMessage(
			'error',
			f'Không commit được CHANGELOG.md lên {branch}: {exc.stderr.strip()} — {cleanup}',
		)
		return 1
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
			'--label',
			'Pre-Release',
			'--label',
			channel,
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
		f'Chưa mở được Pull Request: {created.stderr.strip()}. Khi dùng GITHUB_TOKEN, kiểm tra quyền '
		f'Allow GitHub Actions to create and approve pull requests. Mở tay: {url}',
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
	if tag.startswith(('Stable.v', 'Beta.v')):
		validateReleaseInputs(tag)
	if tag.startswith('Beta.v'):
		command.append('--prerelease')
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
	prepare.add_argument(
		'--version', help='phiên bản Stable.vYYYY.MM.DDXXXX hoặc Beta.vYYYY.MM.DDXXXX'
	)
	prepare.add_argument(
		'--channel',
		choices=RELEASE_CHANNELS,
		default='Stable',
		help='kênh phát hành khi không truyền --version (mặc định Stable)',
	)
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
	try:
		if args.command == 'notes':
			return printNotes(args.tag, args.changelog)
		if args.command == 'prepare':
			return prepareRelease(args.version, args.date, args.open_pr, args.channel)
		if args.command == 'open-pr':
			return openReleasePullRequest(args.version, args.previous, args.commits)
		return createRelease(args.tag, args.changelog, args.allow_generated_notes)
	except (OSError, ValueError, subprocess.CalledProcessError) as exc:
		detail = (
			exc.stderr.strip()
			if isinstance(exc, subprocess.CalledProcessError) and exc.stderr
			else str(exc)
		)
		reportMessage('error', f'❌ Không thực hiện được lệnh {args.command}: {detail}')
		return 1


if __name__ == '__main__':
	sys.exit(main())
