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
		message = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
		print(f'::error::{message}')
	else:
		print(f'✘ {message}', file=sys.stderr)


def checkBranch(name):
	if not name:
		# HEAD không ở branch nào (đang rebase, checkout một commit): không có tên để kiểm tra.
		print('Bỏ qua: HEAD không ở branch nào (detached HEAD).')
		return True
	if SKIPPED_BRANCHES.match(name):
		print(f'Bỏ qua branch: {name}')
		return True
	if BRANCH_PATTERN.fullmatch(name):
		print(f'Tên branch hợp lệ: {name}')
		return True
	reportError(
		"Tên branch phải theo dạng '<tiền tố>/<mô_tả>': tiền tố là "
		f'{joinChoices(BRANCH_PREFIXES)}; mô tả bằng tiếng Anh, chữ thường, các từ nối bằng dấu gạch '
		f'dưới — xem CONTRIBUTING.md. Tên hiện tại: {name}'
	)
	return False


def checkTitle(title):
	if (
		TITLE_PATTERN.fullmatch(title)
		and title.split(': ', 1)[1].strip()
		and len(title) <= 72
		and title.splitlines() == [title]
		and not title.rstrip().endswith('.')
	):
		print(f'Tiêu đề hợp lệ: {title}')
		return True
	reportError(
		"Tiêu đề phải theo dạng '<loại>(<phạm vi>): <mô tả>' (phạm vi tùy chọn) với loại là "
		f'{joinChoices(COMMIT_TYPES)}; mô tả không trống, một dòng tối đa 72 ký tự, không kết thúc bằng dấu chấm '
		f'— xem CONTRIBUTING.md. Tiêu đề hiện tại: {title}'
	)
	return False


def gitOutput(*args, missingOk=False):
	"""Kết quả lệnh Git; chỉ bỏ qua mã 1 của phép dò ref khi người gọi cho phép."""
	result = subprocess.run(['git', *args], capture_output=True, text=True, check=False)
	if result.returncode and not (missingOk and result.returncode == 1):
		raise subprocess.CalledProcessError(
			result.returncode, result.args, result.stdout, result.stderr
		)
	return result.stdout.strip()


def main():
	parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
	parser.add_argument('kind', choices=('branch', 'title'))
	parser.add_argument('value', nargs='?', help='tên branch hoặc tiêu đề cần kiểm tra')
	args = parser.parse_args()
	try:
		return checkValue(args)
	except (OSError, subprocess.CalledProcessError) as exc:
		detail = (
			exc.stderr.strip()
			if isinstance(exc, subprocess.CalledProcessError) and exc.stderr
			else str(exc)
		)
		reportError(f'Không đọc được trạng thái Git: {detail}')
		return 1


def checkValue(args):
	if args.kind == 'branch':
		name = args.value if args.value is not None else gitOutput('branch', '--show-current')
		return 0 if checkBranch(name) else 1
	# Bỏ merge commit: nút Update branch của GitHub tạo "Merge branch 'main' into …" không theo quy ước.
	if args.value is not None:
		titles = [args.value]
	else:
		try:
			titles = gitOutput('log', '--no-merges', '--format=%s', 'origin/main..HEAD')
		except subprocess.CalledProcessError:
			if gitOutput('rev-parse', '--verify', '--quiet', 'origin/main', missingOk=True):
				raise
			print('Bỏ qua: chưa có origin/main để so — chạy git fetch origin main.')
			return 0
	if isinstance(titles, str):
		titles = titles.splitlines()
	if not titles:
		# Không lặng lẽ báo đạt: nói rõ vì sao không có tiêu đề nào để kiểm tra.
		print('Bỏ qua: chưa có commit nào so với origin/main.')
		return 0
	results = [checkTitle(title) for title in titles]
	return 0 if all(results) else 1


if __name__ == '__main__':
	sys.exit(main())
