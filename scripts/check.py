"""Chạy các nhóm kiểm tra của repository — cùng một lệnh tại máy (make check) và trên GitHub Actions.

Chạy:
	python3 scripts/check.py              # mọi nhóm, chạy song song, in kết quả theo thứ tự bên dưới
	python3 scripts/check.py format lint  # một vài nhóm
	python3 scripts/check.py tools        # chỉ kiểm tra đã cài đủ công cụ (cài thư viện Node.js nếu thiếu)
Mỗi nhóm khớp một job của workflow validate.yml (content, format, lint) hoặc một workflow Pull Request
(conventions: branch-name.yml, pr-title.yml; audit: dependency-review.yml). CodeQL không chạy tại máy.
"""

import functools
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Công cụ nhóm cần mà không đứng đầu lệnh: validate.py đọc YAML bằng Ruby và liệt kê tệp bằng git.
INDIRECT_TOOLS = {'content': ('ruby', 'git'), 'conventions': ('git',)}
# Lỗi kết nối mạng của npm: audit không chạy được thì chỉ cảnh báo, không chặn (lỗ hổng thật vẫn chặn).
NETWORK_ERROR = re.compile(
	r'ENOTFOUND|EAI_AGAIN|ETIMEDOUT|ECONNREFUSED|ECONNRESET|ENETUNREACH|request to https?://\S+ failed'
)


def shellScripts():
	"""Mọi script shell git quản lý, ở bất kỳ thư mục nào — script ưu tiên Python, shell chỉ khi xử lý tốt hơn
	và có ghi lý do (ADR 0009)."""
	output = subprocess.run(
		['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '*.sh', '*.bash'],
		cwd=ROOT,
		capture_output=True,
		text=True,
		check=True,
	).stdout
	# -z: tên tệp nguyên văn (không -z thì git đặt tên có ký tự đặc biệt trong dấu nháy kèm mã escape).
	return sorted(name for name in output.split('\0') if name and (ROOT / name).is_file())


def workflowFiles():
	folders = (ROOT / '.github' / 'workflows', ROOT / 'workflow-templates')
	return sorted(
		str(path.relative_to(ROOT)) for folder in folders for path in folder.glob('*.yml')
	)


@functools.cache
def checkGroups():
	"""Nhóm kiểm tra → danh sách lệnh; tên nhóm khớp job hoặc workflow trên GitHub Actions. Tính một lần mỗi tiến
	trình (liệt kê script shell bằng git) — main, ensureTools, runGroup cùng dùng."""
	return {
		'content': [
			['python3', 'scripts/validate.py'],
			['python3', 'scripts/run-tests.py'],
		],
		'format': [
			['npx', 'prettier', '--check', '.'],
			['ruff', 'format', '--check', '.'],
			# Python ≥ 3.11 (tomllib, datetime.UTC); ruff.toml giữ đúng cấu hình chuẩn nên khai báo ở đây.
			['ruff', 'check', '--target-version', 'py311', '.'],
		],
		# shellcheck không nhận danh sách tệp rỗng — không có script shell thì bỏ lệnh.
		'lint': [
			*([['shellcheck', *scripts]] if (scripts := shellScripts()) else []),
			['actionlint', *workflowFiles()],
		],
		'conventions': [
			['python3', 'scripts/conventions.py', 'branch'],
			['python3', 'scripts/conventions.py', 'title'],
		],
		'audit': [['npm', 'audit', '--audit-level=high']],
	}


def ensureTools(groups):
	"""Báo công cụ còn thiếu (cài bằng mise install); cài thư viện Node.js khi chưa có node_modules."""
	needed = {command[0] for name in groups for command in checkGroups()[name]}
	needed.update(tool for name in groups for tool in INDIRECT_TOOLS.get(name, ()))
	missing = sorted(tool for tool in needed if not shutil.which(tool))
	if missing:
		print(f'Thiếu công cụ: {", ".join(missing)} — chạy: mise install (https://mise.jdx.dev)')
		return False
	if needed & {'npx', 'npm'} and not (ROOT / 'node_modules').is_dir():
		result = subprocess.run(
			['npm', 'install', '--no-audit', '--no-fund'], cwd=ROOT, check=False
		)
		if result.returncode != 0:
			print(
				'❌ Không cài được thư viện Node.js — xem lỗi npm ở trên, kiểm tra .nvmrc và mạng rồi chạy lại.'
			)
			return False
	return True


def runCommand(name, command):
	"""Chạy một lệnh kiểm tra, trả (đạt hay không, đầu ra). audit mất mạng thì cảnh báo và tính là đạt."""
	result = subprocess.run(
		command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
	)
	output = result.stdout
	if name == 'audit' and result.returncode != 0 and NETWORK_ERROR.search(output):
		return True, output + (
			'⚠️  Bỏ qua audit: không kết nối được máy chủ npm — chạy lại make audit khi có mạng.\n'
		)
	return result.returncode == 0, output


def runGroup(name):
	"""Chạy lần lượt các lệnh của một nhóm; trả (đầu ra, lệnh lỗi)."""
	outputs, failed = [], []
	for command in checkGroups()[name]:
		passed, output = runCommand(name, command)
		outputs.append(f'$ {" ".join(command)}\n{output}')
		if not passed:
			failed.append(f'{name}: {" ".join(command)[:80]}')
	return ''.join(outputs), failed


def runGroups(groups):
	"""Các nhóm độc lập nên chạy song song (test đã chia nhiều tiến trình, Prettier, audit chờ mạng…); đầu ra in
	liền khối theo thứ tự nhóm."""
	with ThreadPoolExecutor(max_workers=len(groups)) as pool:
		results = list(pool.map(runGroup, groups))
	failed = []
	for output, groupFailed in results:
		print(output, end='', flush=True)
		failed += groupFailed
	for item in failed:
		print(f'❌ {item}')
	return not failed


def main():
	# validate.py, test cần Python ≥ 3.11 (tomllib, datetime.UTC); python3 của macOS là 3.9. Git hook chạy từ
	# ứng dụng giao diện (VS Code…) có thể không có PATH của mise nên dễ gặp bản cũ.
	if sys.version_info < (3, 11):  # noqa: UP036 — cố ý: chặn khi bị chạy bằng Python cũ
		print(
			f'Cần Python ≥ 3.11 (đang dùng {sys.version.split()[0]}) — chạy mise install, mở terminal có mise.'
		)
		return 1
	names = sys.argv[1:] or list(checkGroups())
	unknown = [name for name in names if name not in (*checkGroups(), 'tools')]
	if unknown:
		print(f'Nhóm không có: {", ".join(unknown)}. Có: {", ".join(checkGroups())}, tools.')
		return 2
	groups = [name for name in names if name != 'tools'] or list(checkGroups())
	if not ensureTools(groups):
		return 1
	if names == ['tools']:
		return 0
	return 0 if runGroups(groups) else 1


if __name__ == '__main__':
	sys.exit(main())
