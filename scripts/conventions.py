"""Kiểm tra quy ước của CONTRIBUTING.md: tên branch và tiêu đề Pull Request (cũng là tiêu đề commit).

Chạy:
	python3 scripts/conventions.py branch [tên]      # mặc định: branch hiện tại
	python3 scripts/conventions.py title [tiêu đề]   # mặc định: mọi commit của branch so với origin/main
Workflow branch-name.yml, pr-title.yml (của repository này và workflow mẫu) gọi script này; danh sách loại
commit và tiền tố branch phải khớp CONTRIBUTING.md (validate.py kiểm tra).
"""

import argparse
import os
import re
import subprocess
import sys

COMMIT_TYPES = (
	'feat',
	'fix',
	'docs',
	'style',
	'refactor',
	'perf',
	'test',
	'build',
	'ci',
	'chore',
	'revert',
)
BRANCH_PREFIXES = (
	'feature',
	'fix',
	'hotfix',
	'docs',
	'refactor',
	'perf',
	'test',
	'ci',
	'chore',
	'release',
)
TITLE_PATTERN = re.compile(rf'^({"|".join(COMMIT_TYPES)})(\([a-z0-9_-]+\))?!?: .+')
BRANCH_PATTERN = re.compile(rf'^({"|".join(BRANCH_PREFIXES)})/[a-z0-9.]+(_[a-z0-9.]+)*$')
# Branch do Dependabot tạo có định dạng riêng; nhánh chính không cần kiểm tra.
SKIPPED_BRANCHES = re.compile(r'^(dependabot/|main$)')


def joinChoices(choices):
	return f'{", ".join(choices[:-1])} hoặc {choices[-1]}'


def reportError(message):
	"""Chú thích ::error:: khi chạy trên GitHub Actions, dòng ✘ khi chạy tại máy."""
	if os.environ.get('GITHUB_ACTIONS'):
		print(f'::error::{message}')
	else:
		print(f'✘ {message}', file=sys.stderr)


def checkBranch(name):
	if SKIPPED_BRANCHES.match(name):
		print(f'Bỏ qua branch: {name}')
		return True
	if BRANCH_PATTERN.match(name):
		print(f'Tên branch hợp lệ: {name}')
		return True
	reportError(
		"Tên branch phải theo dạng '<tiền tố>/<mô_tả>': tiền tố là "
		f'{joinChoices(BRANCH_PREFIXES)}; mô tả bằng tiếng Anh, chữ thường, các từ nối bằng dấu gạch '
		f'dưới — xem CONTRIBUTING.md. Tên hiện tại: {name}'
	)
	return False


def checkTitle(title):
	if TITLE_PATTERN.match(title):
		print(f'Tiêu đề hợp lệ: {title}')
		return True
	reportError(
		"Tiêu đề phải theo dạng '<loại>(<phạm vi>): <mô tả>' (phạm vi tùy chọn) với loại là "
		f'{joinChoices(COMMIT_TYPES)} — xem CONTRIBUTING.md. Tiêu đề hiện tại: {title}'
	)
	return False


def gitOutput(*args):
	"""Kết quả lệnh git, chuỗi rỗng khi lỗi (ví dụ chưa có origin/main)."""
	result = subprocess.run(['git', *args], capture_output=True, text=True, check=False)
	return result.stdout.strip() if result.returncode == 0 else ''


def main():
	parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
	parser.add_argument('kind', choices=('branch', 'title'))
	parser.add_argument('value', nargs='?', help='tên branch hoặc tiêu đề cần kiểm tra')
	args = parser.parse_args()
	if args.kind == 'branch':
		return 0 if checkBranch(args.value or gitOutput('branch', '--show-current')) else 1
	titles = [args.value] if args.value else gitOutput('log', '--format=%s', 'origin/main..HEAD')
	if isinstance(titles, str):
		titles = titles.splitlines()
	results = [checkTitle(title) for title in titles]
	return 0 if all(results) else 1


if __name__ == '__main__':
	sys.exit(main())
