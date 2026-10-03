#!/usr/bin/env python3
"""Git hook của repository — make hooks liên kết .git/hooks/<tên hook> tới tệp này.

pre-commit: Prettier, ruff format kiểm tra các tệp đang được stage.
pre-push: make check — toàn bộ kiểm tra như GitHub Actions (có thể đang tắt); lỗi thì không đẩy.
post-merge: make org-preview sau git pull — so cài đặt trên GitHub với code vừa kéo về; chỉ báo, không chặn.
Chạy tay: python3 scripts/git-hooks.py <pre-commit|pre-push|post-merge>
"""

import shutil
import subprocess
import sys
from pathlib import Path


def repositoryRoot():
	output = subprocess.run(
		['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, check=True
	).stdout
	return Path(output.strip())


def stagedFiles(root):
	"""Tệp thêm, sửa, đổi tên đang được stage."""
	output = subprocess.run(
		['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'],
		cwd=root,
		capture_output=True,
		text=True,
		check=True,
	).stdout
	return [name for name in output.split('\0') if name]


def preCommit(root):
	files = stagedFiles(root)
	if not files:
		return 0
	failed = False
	# Prettier tự bỏ qua tệp không hỗ trợ và tệp trong .gitignore, .prettierignore.
	command = ['npx', '--no', '--', 'prettier', '--check', '--ignore-unknown', *files]
	failed |= subprocess.run(command, cwd=root, check=False).returncode != 0
	python = [name for name in files if name.endswith('.py')]
	if python:
		command = ['ruff', 'format', '--check', *python]
		failed |= subprocess.run(command, cwd=root, check=False).returncode != 0
	if failed:
		print(
			'❌ Có tệp chưa đúng định dạng — chạy: make format, rồi git add lại.', file=sys.stderr
		)
	return 1 if failed else 0


def prePush(root):
	if subprocess.run(['make', 'check'], cwd=root, check=False).returncode != 0:
		print('❌ make check thất bại — sửa lỗi rồi đẩy lại.', file=sys.stderr)
		return 1
	return 0


def postMerge(root):
	signedIn = shutil.which('gh') and (
		subprocess.run(['gh', 'auth', 'status'], capture_output=True, check=False).returncode == 0
	)
	if not signedIn:
		print(
			'⚠️  Bỏ qua make org-preview: cần GitHub CLI đã đăng nhập (gh auth login).',
			file=sys.stderr,
		)
		return 0
	print('== make org-preview: so cài đặt trên GitHub với code vừa kéo về', flush=True)
	if subprocess.run(['make', 'org-preview'], cwd=root, check=False).returncode != 0:
		print('⚠️  make org-preview lỗi — xem thông báo ở trên.', file=sys.stderr)
	return 0


HOOKS = {'pre-commit': preCommit, 'pre-push': prePush, 'post-merge': postMerge}


def main():
	# Git gọi hook qua liên kết .git/hooks/<tên hook>; chạy tay thì truyền tên hook làm tham số.
	name = Path(sys.argv[0]).name
	if name not in HOOKS:
		name = sys.argv[1] if len(sys.argv) > 1 else ''
	if name not in HOOKS:
		print(f'Cách dùng: python3 scripts/git-hooks.py <{"|".join(HOOKS)}>', file=sys.stderr)
		return 2
	return HOOKS[name](repositoryRoot())


if __name__ == '__main__':
	sys.exit(main())
