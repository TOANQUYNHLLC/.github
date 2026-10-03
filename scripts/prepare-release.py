"""Chuẩn bị phát hành hằng tháng: chuyển mục CHƯA PHÁT HÀNH của CHANGELOG.md thành phiên bản của tháng.

Chạy: python3 scripts/prepare-release.py [--version v2026.11.Stable] [--date 2026-11-01]
Mặc định phiên bản là vYYYY.MM.Stable theo ngày hiện tại ở Việt Nam. Bỏ qua (mã thoát 0, không ghi gì)
khi tag đã có hoặc không có commit nào kể từ tag phát hành trước; báo lỗi (mã thoát 1) khi có commit mà
mục CHƯA PHÁT HÀNH trống. Chạy trong workflow monthly-release.yml, ghi version vào $GITHUB_OUTPUT.
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / 'CHANGELOG.md'
TIMEZONE = ZoneInfo('Asia/Ho_Chi_Minh')
UNRELEASED = re.compile(
	r'^## \[CHƯA PHÁT HÀNH\]\((?P<base>[^)]+)/compare/[^)]+\.\.\.HEAD\)\n(?P<body>.*?)(?=^## \[)',
	re.MULTILINE | re.DOTALL,
)


def unreleased_notes(changelog):
	"""Nội dung mục CHƯA PHÁT HÀNH (bỏ đường phân cách cuối), chuỗi rỗng nếu mục trống."""
	match = UNRELEASED.search(changelog)
	if not match:
		return None
	return re.sub(r'(^|\n)---$', '', match.group('body').strip()).strip()


def cut_release(changelog, version, date):
	"""CHANGELOG mới: mục CHƯA PHÁT HÀNH trống so sánh từ version, nội dung cũ chuyển sang ## [version]."""
	match = UNRELEASED.search(changelog)
	base, notes = match.group('base'), unreleased_notes(changelog)
	section = (
		f'## [CHƯA PHÁT HÀNH]({base}/compare/{version}...HEAD)\n\n---\n\n'
		f'## [{version}]({base}/releases/tag/{version}) — {date}\n\n{notes}\n\n---\n\n'
	)
	return changelog[: match.start()] + section + changelog[match.end() :]


def git(*args):
	return subprocess.run(
		['git', *args], cwd=ROOT, capture_output=True, text=True, check=True
	).stdout.strip()


def output(**values):
	"""Ghi kết quả cho bước sau của workflow (bỏ qua khi chạy tại máy)."""
	path = os.environ.get('GITHUB_OUTPUT')
	if path:
		with open(path, 'a', encoding='utf-8') as file:
			file.writelines(f'{key}={value}\n' for key, value in values.items())


def main():
	today = datetime.now(TIMEZONE).date()
	parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
	parser.add_argument('--version', default=f'v{today:%Y.%m}.Stable')
	parser.add_argument('--date', default=today.isoformat())
	args = parser.parse_args()
	if git('tag', '--list', args.version):
		print(f'Đã có tag {args.version} — bỏ qua.')
		return 0
	previous = git('describe', '--tags', '--abbrev=0', '--match', 'v*')
	commits = int(git('rev-list', '--count', f'{previous}..HEAD'))
	if not commits:
		print(f'Không có thay đổi kể từ {previous} — bỏ qua.')
		return 0
	changelog = CHANGELOG.read_text(encoding='utf-8')
	if not unreleased_notes(changelog):
		print(
			f'Có {commits} commit kể từ {previous} nhưng mục CHƯA PHÁT HÀNH của CHANGELOG.md trống '
			'hoặc sai dạng — ghi thay đổi vào CHANGELOG.md rồi chạy lại.',
			file=sys.stderr,
		)
		return 1
	CHANGELOG.write_text(cut_release(changelog, args.version, args.date), encoding='utf-8')
	print(f'Đã chuyển CHƯA PHÁT HÀNH thành {args.version} ({commits} commit kể từ {previous}).')
	output(version=args.version, previous=previous, commits=commits)
	return 0


if __name__ == '__main__':
	sys.exit(main())
