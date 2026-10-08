#!/usr/bin/env python3
"""Git hook của repository — make hooks (install) liên kết .git/hooks/<tên hook> tới tệp này (không tạo được liên
kết tượng trưng — Windows chưa bật Developer Mode — thì ghi tệp gọi script).

pre-commit: Prettier, ruff format, ruff check kiểm tra đúng nội dung đã stage (không phải tệp trên đĩa).
pre-push: make check trên đúng nội dung được đẩy — chặn khi còn thay đổi chưa commit hoặc đẩy branch khác
	HEAD; bỏ qua khi chỉ đẩy tag hoặc xóa branch; make check lỗi thì không đẩy.
post-merge: sau git pull (gộp, tua nhanh) — cài lại hook (nhận hook mới), make org-preview, links, versions;
	chỉ báo, không chặn.
post-rewrite: như post-merge sau git pull --rebase; bỏ qua git commit --amend.
Chạy tay: python3 scripts/git-hooks.py <install|pre-commit|pre-push|post-merge|post-rewrite [rebase]>
"""

import contextlib
import os
import re
import shlex
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
	"""Danh sách phân cách bằng NUL giữ nguyên tên tệp, không strip hoặc chuẩn hóa ký tự xuống dòng."""
	nullSeparated = '-z' in args or '--null' in args
	result = subprocess.run(
		['git', *args], cwd=root, capture_output=True, text=not nullSeparated, check=True
	)
	return result.stdout.decode('utf-8') if nullSeparated else result.stdout.strip()


def repositoryRoot():
	return Path(git(Path.cwd(), 'rev-parse', '--show-toplevel'))


def childEnvironment(root):
	"""Lệnh con tự tìm repository theo cwd; không mang GIT_DIR/index của hook sang repository tạm trong tests.
	Giữ các biến ngoài danh sách môi trường cục bộ do Git công bố (PATH, phiên bản công cụ, đăng nhập…)."""
	localNames = set(git(root, 'rev-parse', '--local-env-vars').splitlines())
	return {key: value for key, value in os.environ.items() if key not in localNames}


def stagedFiles(root):
	"""Tệp thêm, sửa, đổi tên đang được stage."""
	output = git(root, 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z')
	return [name for name in output.split('\0') if name]


def toolEnvironment():
	"""Môi trường chạy Prettier, ruff trong thư mục tạm: shim của mise chọn phiên bản theo thư mục hiện tại, ở
	thư mục tạm không thấy mise.toml, .nvmrc — ghim phiên bản của repository chứa script bằng MISE_RUFF_VERSION,
	MISE_NODE_VERSION (không dùng mise thì các biến này không có tác dụng)."""
	environment = dict(os.environ)
	root = SCRIPT.parents[1]
	with contextlib.suppress(OSError):
		mise = (root / 'mise.toml').read_text(encoding='utf-8')
		if ruff := re.search(r'^ruff = "([^"]+)"$', mise, re.MULTILINE):
			environment.setdefault('MISE_RUFF_VERSION', ruff.group(1))
	with contextlib.suppress(OSError):
		if node := (root / '.nvmrc').read_text(encoding='utf-8').strip():
			environment.setdefault('MISE_NODE_VERSION', node)
	return environment


def preCommit(root, args):
	files = stagedFiles(root)
	if not files:
		return 0
	with tempfile.TemporaryDirectory() as folder:
		# Xuất đúng nội dung đã stage (kể cả khi chỉ stage một phần tệp) cùng cấu hình định dạng.
		configs = [
			name for name in git(root, 'ls-files', '-z', '--', *FORMAT_CONFIGS).split('\0') if name
		]
		python = [name for name in files if name.endswith('.py')]
		# ruff xếp import theo gói (thư mục có __init__.py, module cùng gói): thiếu các tệp Python khác của index
		# thì module của repository bị coi là thư viện ngoài, báo I001 sai. Chỉ xuất để đọc, không kiểm tra.
		sources = (
			[name for name in git(root, 'ls-files', '-z', '--', '*.py').split('\0') if name]
			if python
			else []
		)
		paths = sorted(set(files) | set(configs) | set(sources))
		exported = subprocess.run(
			['git', 'checkout-index', f'--prefix={folder}/', '--', *paths],
			cwd=root,
			capture_output=True,
			check=False,
		)
		if exported.returncode:
			print(
				f'❌ Không xuất được nội dung đã stage: {exported.stderr.decode("utf-8", "replace").strip()}',
				file=sys.stderr,
			)
			return 1
		failed = False
		environment = toolEnvironment()
		if PRETTIER.exists():
			# Tên như --version phải được đọc như đường dẫn, không được thay đổi tùy chọn kiểm tra.
			command = [str(PRETTIER), '--check', '--ignore-unknown', '--', *files]
			failed |= (
				subprocess.run(command, cwd=folder, env=environment, check=False).returncode != 0
			)
		else:
			print('⚠️  Chưa có Prettier — chạy make tools.', file=sys.stderr)
			failed = True
		if python and not shutil.which('ruff'):
			print('⚠️  Chưa có ruff — chạy mise install.', file=sys.stderr)
			failed = True
		elif python:
			for command in (
				['ruff', 'format', '--check', '--', *python],
				# Như nhóm format của check.py: Python ≥ 3.11 (tomllib, datetime.UTC).
				['ruff', 'check', '--target-version', 'py311', '--', *python],
			):
				failed |= (
					subprocess.run(command, cwd=folder, env=environment, check=False).returncode
					!= 0
				)
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
	# --untracked-files=normal: status.showUntrackedFiles=no của người dùng làm git ẩn tệp mới.
	if git(root, 'status', '--porcelain', '--untracked-files=normal'):
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
	if (
		subprocess.run(
			['make', 'check'], cwd=root, env=childEnvironment(root), check=False
		).returncode
		!= 0
	):
		print('❌ make check thất bại — sửa lỗi rồi đẩy lại.', file=sys.stderr)
		return 1
	return 0


def afterPull(root):
	"""Sau khi kéo code: cài lại hook (nhận hook mới thêm), so cài đặt trên GitHub với code, kiểm tra liên kết
	bên ngoài và phiên bản công cụ; chỉ báo, không chặn. Liên kết, phiên bản kiểm tra tại máy vì môi trường đám
	mây của routine Claude Code chặn mạng ra ngoài."""
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
		('versions', 'công cụ trong mise.toml, action của workflow mẫu có bản mới'),
	]

	def report(target):
		return subprocess.run(
			['make', '--no-print-directory', target],
			cwd=root,
			env=childEnvironment(root),
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
		wrapper = hookWrapper(name)
		if link.is_symlink() and os.readlink(link) == target:
			continue
		if not link.is_symlink() and link.is_file() and link.read_text(encoding='utf-8') == wrapper:
			continue
		if link.exists() or link.is_symlink():
			link.unlink()
		try:
			link.symlink_to(target)
		except OSError:
			# Windows không cho tạo liên kết tượng trưng khi chưa bật Developer Mode: ghi tệp gọi script thay thế
			# (Git for Windows chạy hook bằng sh đi kèm).
			link.write_text(wrapper, encoding='utf-8')
			link.chmod(0o755)
		print(f'Đã cài hook {name}')
	return 0


def hookWrapper(name):
	"""Tệp hook gọi script này khi không tạo được liên kết tượng trưng: dùng đúng Python đang chạy make hooks —
	Windows thường không có lệnh python3 — và truyền tên hook như khi chạy tay."""
	# shlex.quote: đường dẫn có $, `, \\ hay dấu nháy bị sh thông dịch nếu chỉ đặt trong dấu nháy kép.
	python = shlex.quote(Path(sys.executable).as_posix())
	script = shlex.quote(SCRIPT.as_posix())
	return (
		f'#!/bin/sh\n# Sinh bởi scripts/git-hooks.py install.\nexec {python} {script} {name} "$@"\n'
	)


HOOKS = {
	'pre-commit': preCommit,
	'pre-push': prePush,
	'post-merge': postMerge,
	'post-rewrite': postRewrite,
}


def main():
	# Như check.py: ứng dụng giao diện (VS Code, GitHub Desktop…) gọi hook bằng python3 của hệ thống — macOS là
	# 3.9 — không có PATH của mise. Báo rõ thay vì traceback giữa chừng (zip strict của post-merge cần ≥ 3.10).
	if sys.version_info < (3, 11):  # noqa: UP036 — cố ý: chặn khi bị chạy bằng Python cũ
		print(
			f'❌ Git hook cần Python ≥ 3.11 (đang dùng {sys.version.split()[0]}) — chạy mise install, mở '
			'ứng dụng từ terminal có mise hoặc đặt python3 ≥ 3.11 lên đầu PATH.',
			file=sys.stderr,
		)
		return 1
	# Git gọi hook qua liên kết .git/hooks/<tên hook> kèm tham số của hook; chạy tay thì tên hook là tham số đầu.
	name, args = Path(sys.argv[0]).name, sys.argv[1:]
	if name not in HOOKS:
		name, args = (args[0], args[1:]) if args else ('', [])
	try:
		root = repositoryRoot()
	except subprocess.CalledProcessError as exc:
		# Không phải repository git, hoặc git từ chối (dubious ownership…): báo đúng lời git thay vì traceback.
		print(f'❌ {exc.stderr.strip()}', file=sys.stderr)
		return 1
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
