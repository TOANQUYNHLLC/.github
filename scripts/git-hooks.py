#!/usr/bin/env python3
"""Git hook của repository — make hooks (install) liên kết .git/hooks/<tên hook> tới tệp này.

pre-commit: Prettier, ruff format, ruff check kiểm tra đúng nội dung đã stage (không phải tệp trên đĩa).
pre-push: make check trên đúng nội dung được đẩy — chặn khi còn thay đổi chưa commit hoặc đẩy branch khác
	HEAD; bỏ qua khi chỉ đẩy tag hoặc xóa branch; make check lỗi thì không đẩy.
post-merge: sau git pull (gộp, tua nhanh) — cài lại hook (nhận hook mới), make org-preview, links, versions;
	chỉ báo, không chặn.
post-rewrite: như post-merge sau git pull --rebase; bỏ qua git commit --amend.
Chạy tay: python3 scripts/git-hooks.py <install|pre-commit|pre-push|post-merge|post-rewrite [rebase]>
"""

import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPT = Path(__file__).resolve()
# Prettier của repository chứa script — chạy được cả khi kiểm tra trong thư mục tạm.
PRETTIER = SCRIPT.parents[1] / 'node_modules' / '.bin' / 'prettier'
# Cấu hình định dạng chép vào thư mục tạm cùng nội dung đã stage để Prettier, ruff đọc đúng như ở repository.
FORMAT_CONFIGS = ('.prettierrc.json', '.prettierignore', '.gitignore', '.editorconfig', 'ruff.toml')
ZERO_SHA = '0' * 40


def git(root, *args):
	return subprocess.run(
		['git', *args], cwd=root, capture_output=True, text=True, check=True
	).stdout.strip()


def repositoryRoot():
	return Path(git(Path.cwd(), 'rev-parse', '--show-toplevel'))


def stagedFiles(root):
	"""Tệp thêm, sửa, đổi tên đang được stage."""
	output = git(root, 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z')
	return [name for name in output.split('\0') if name]


def preCommit(root, args):
	files = stagedFiles(root)
	if not files:
		return 0
	with tempfile.TemporaryDirectory() as folder:
		# Xuất đúng nội dung đã stage (kể cả khi chỉ stage một phần tệp) cùng cấu hình định dạng.
		configs = [name for name in FORMAT_CONFIGS if (root / name).exists()]
		paths = sorted(set(files) | set(configs))
		subprocess.run(
			['git', 'checkout-index', f'--prefix={folder}/', '--', *paths],
			cwd=root,
			capture_output=True,
			check=False,
		)
		failed = False
		if PRETTIER.exists():
			command = [str(PRETTIER), '--check', '--ignore-unknown', *files]
			failed |= subprocess.run(command, cwd=folder, check=False).returncode != 0
		else:
			print('⚠️  Chưa có Prettier — chạy make tools.', file=sys.stderr)
			failed = True
		python = [name for name in files if name.endswith('.py')]
		if python:
			for command in (
				['ruff', 'format', '--check', *python],
				# Như nhóm format của check.py: Python ≥ 3.11 (tomllib, datetime.UTC).
				['ruff', 'check', '--target-version', 'py311', *python],
			):
				failed |= subprocess.run(command, cwd=folder, check=False).returncode != 0
	if failed:
		print(
			'❌ Nội dung đã stage chưa đúng định dạng hoặc còn lỗi ruff check — chạy make format, sửa lỗi '
			'theo thông báo, rồi git add lại.',
			file=sys.stderr,
		)
	return 1 if failed else 0


def pushedBranches(lines):
	"""Ref branch được cập nhật trong lần đẩy (bỏ tag và xóa branch); mỗi dòng git đưa vào pre-push có dạng
	"<ref cục bộ> <sha cục bộ> <ref đích> <sha đích>"."""
	branches = []
	for line in lines:
		parts = line.split()
		if len(parts) == 4 and parts[1] != ZERO_SHA and parts[2].startswith('refs/heads/'):
			branches.append((parts[2], parts[1]))
	return branches


def prePush(root, args):
	lines = [] if sys.stdin.isatty() else sys.stdin.read().splitlines()
	branches = pushedBranches(lines) if lines else [('HEAD', git(root, 'rev-parse', 'HEAD'))]
	if not branches:
		print('Bỏ qua make check: lần đẩy chỉ có tag hoặc xóa branch.')
		return 0
	# make check chạy trên thư mục làm việc — phải trùng đúng nội dung được đẩy.
	if git(root, 'status', '--porcelain'):
		print(
			'❌ Còn thay đổi chưa commit — make check sẽ kiểm tra khác nội dung được đẩy. '
			'Commit hoặc git stash -u rồi đẩy lại.',
			file=sys.stderr,
		)
		return 1
	head = git(root, 'rev-parse', 'HEAD')
	others = [ref for ref, sha in branches if sha != head]
	if others:
		print(
			f'❌ Đẩy {", ".join(others)} khác HEAD — make check chỉ kiểm tra HEAD. '
			'Checkout branch đó rồi đẩy.',
			file=sys.stderr,
		)
		return 1
	if subprocess.run(['make', 'check'], cwd=root, check=False).returncode != 0:
		print('❌ make check thất bại — sửa lỗi rồi đẩy lại.', file=sys.stderr)
		return 1
	return 0


def afterPull(root):
	"""Sau khi kéo code: cài lại hook (nhận hook mới thêm), so cài đặt trên GitHub với code, kiểm tra liên kết
	bên ngoài và phiên bản công cụ; chỉ báo, không chặn. Liên kết, phiên bản kiểm tra tại máy vì môi trường đám
	mây của routine hằng tuần chặn mạng ra ngoài."""
	installHooks(root)
	signedIn = shutil.which('gh') and (
		subprocess.run(['gh', 'auth', 'status'], capture_output=True, check=False).returncode == 0
	)
	reports = [('org-preview', 'so cài đặt trên GitHub với code vừa kéo về')] if signedIn else []
	if not signedIn:
		print(
			'⚠️  Bỏ qua make org-preview: cần GitHub CLI đã đăng nhập (gh auth login).',
			file=sys.stderr,
		)
	reports += [
		('links', 'liên kết bên ngoài còn hoạt động'),
		('versions', 'công cụ trong mise.toml có bản mới'),
	]

	def report(target):
		return subprocess.run(
			['make', '--no-print-directory', target],
			cwd=root,
			capture_output=True,
			text=True,
			check=False,
		)

	# Chạy song song (mỗi lệnh chờ mạng vài giây), in liền khối theo thứ tự.
	with ThreadPoolExecutor(max_workers=len(reports)) as pool:
		results = list(pool.map(report, [target for target, _ in reports]))
	for (target, purpose), result in zip(reports, results, strict=True):
		print(f'== make {target}: {purpose}', flush=True)
		print(result.stdout, end='', flush=True)
		print(result.stderr, end='', file=sys.stderr, flush=True)
		if result.returncode != 0:
			print(f'⚠️  make {target} báo lỗi — xem thông báo ở trên.', file=sys.stderr, flush=True)
	return 0


def postMerge(root, args):
	return afterPull(root)


def postRewrite(root, args):
	# Git truyền "rebase" (git pull --rebase, git rebase) hoặc "amend" (git commit --amend).
	return afterPull(root) if args[:1] == ['rebase'] else 0


def installHooks(root):
	"""Liên kết .git/hooks/<tên hook> tới script này; báo khi core.hooksPath làm git bỏ qua .git/hooks."""
	hooksPath = subprocess.run(
		['git', 'config', '--get', 'core.hooksPath'],
		cwd=root,
		capture_output=True,
		text=True,
		check=False,
	).stdout.strip()
	if hooksPath:
		print(
			f'⚠️  core.hooksPath = {hooksPath}: git bỏ qua .git/hooks nên hook của repository không chạy. '
			'Gỡ bằng: git config --unset core.hooksPath (thêm --global nếu đặt toàn cục).',
			file=sys.stderr,
		)
	# Thư mục hook chuẩn, dùng chung cho mọi git worktree; --git-path hooks theo core.hooksPath nên không dùng.
	folder = root / git(root, 'rev-parse', '--git-common-dir') / 'hooks'
	folder.mkdir(parents=True, exist_ok=True)
	# Đường dẫn tương đối tính từ thư mục hook đã phân giải (ví dụ /var là liên kết tới /private/var trên macOS).
	for name in HOOKS:
		link = folder / name
		target = os.path.relpath(SCRIPT, folder.resolve())
		if link.is_symlink() and os.readlink(link) == target:
			continue
		if link.exists() or link.is_symlink():
			link.unlink()
		link.symlink_to(target)
		print(f'Đã cài hook {name}')
	return 0


HOOKS = {
	'pre-commit': preCommit,
	'pre-push': prePush,
	'post-merge': postMerge,
	'post-rewrite': postRewrite,
}


def main():
	# Git gọi hook qua liên kết .git/hooks/<tên hook> kèm tham số của hook; chạy tay thì tên hook là tham số đầu.
	name, args = Path(sys.argv[0]).name, sys.argv[1:]
	if name not in HOOKS:
		name, args = (args[0], args[1:]) if args else ('', [])
	root = repositoryRoot()
	if name == 'install':
		return installHooks(root)
	if name not in HOOKS:
		print(
			f'Cách dùng: python3 scripts/git-hooks.py <install|{"|".join(HOOKS)}>', file=sys.stderr
		)
		return 2
	return HOOKS[name](root, args)


if __name__ == '__main__':
	sys.exit(main())
