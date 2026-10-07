"""Chạy các nhóm kiểm tra của repository — cùng một lệnh tại máy (make check) và trên GitHub Actions.

Chạy:
	python3 scripts/check.py              # mọi nhóm, chạy song song, in kết quả theo thứ tự bên dưới
	python3 scripts/check.py format lint  # một vài nhóm
	python3 scripts/check.py tools        # chỉ kiểm tra đã cài đủ công cụ (cài thư viện Node.js nếu thiếu, sai phiên bản)
Mỗi nhóm khớp một job của workflow validate.yml (content, format, lint) hoặc một workflow Pull Request
(conventions: branch-name.yml, pr-title.yml; audit: dependency-review.yml). CodeQL không chạy tại máy.
"""

import functools
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Cài cả devDependencies: môi trường đặt NODE_ENV=production thì npm install mặc định bỏ qua chúng.
NPM_INSTALL = ('npm', 'install', '--include=dev', '--no-audit', '--no-fund')
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
		check=True,
	).stdout.decode('utf-8')
	# -z: tên tệp nguyên văn (không -z thì git đặt tên có ký tự đặc biệt trong dấu nháy kèm mã escape).
	return sorted(name for name in output.split('\0') if name and (ROOT / name).is_file())


def workflowFiles():
	folders = (ROOT / '.github' / 'workflows', ROOT / 'workflow-templates')
	return sorted(
		str(path.relative_to(ROOT))
		for folder in folders
		for path in folder.glob('*')
		if path.name.endswith(('.yml', '.yaml')) and path.is_file()
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
			# --no: chỉ dùng Prettier đã cài theo package.json, không tự tải bản mới nhất.
			[
				'npx',
				'--no',
				'--',
				'prettier',
				'--check',
				'.',
				'--cache',
				'--cache-strategy',
				'content',
			],
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


def nodeModulesCurrent():
	"""Mọi thư viện trong package.json đã cài đúng phiên bản ghi trong đó (phiên bản chính xác — .npmrc)."""
	try:
		manifest = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
	except (OSError, json.JSONDecodeError):
		return False  # npm install báo lỗi rõ ràng
	for section in ('dependencies', 'devDependencies'):
		for name, version in manifest.get(section, {}).items():
			installed = ROOT / 'node_modules' / name / 'package.json'
			try:
				if json.loads(installed.read_text(encoding='utf-8')).get('version') != version:
					return False
			except (OSError, json.JSONDecodeError):
				return False
	return True


def ensureTools(groups):
	"""Báo công cụ còn thiếu (cài bằng mise install); cài thư viện Node.js khi chưa có hoặc khác phiên bản trong
	package.json."""
	needed = {command[0] for name in groups for command in checkGroups()[name]}
	needed.update(tool for name in groups for tool in INDIRECT_TOOLS.get(name, ()))
	missing = sorted(tool for tool in needed if not shutil.which(tool))
	if missing:
		print(f'Thiếu công cụ: {", ".join(missing)} — chạy: mise install (https://mise.jdx.dev)')
		return False
	if needed & {'npx', 'npm'} and not nodeModulesCurrent():
		result = subprocess.run(NPM_INSTALL, cwd=ROOT, check=False)
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


def runGroup(name, selectedTests=None):
	"""Các lệnh kiểm tra độc lập chạy đồng thời; đầu ra và lệnh lỗi giữ thứ tự khai báo."""
	commands = []
	for original in checkGroups()[name]:
		command = original
		if selectedTests and name == 'content' and original[1] == 'scripts/run-tests.py':
			command = [*original, *selectedTests]
		commands.append(command)
	with ThreadPoolExecutor(max_workers=max(1, len(commands))) as pool:
		results = list(pool.map(functools.partial(runCommand, name), commands))
	outputs, failed = [], []
	for command, (passed, output) in zip(commands, results, strict=True):
		outputs.append(f'$ {" ".join(command)}\n{output}')
		if not passed:
			failed.append(f'{name}: {" ".join(command)[:80]}')
	return ''.join(outputs), failed


def runGroups(groups, selectedTests=None):
	"""Các nhóm và lệnh độc lập chạy song song (test đã chia nhiều tiến trình); đầu ra liền khối theo thứ tự nhóm."""
	with ThreadPoolExecutor(max_workers=len(groups)) as pool:
		runner = (
			functools.partial(runGroup, selectedTests=selectedTests) if selectedTests else runGroup
		)
		results = list(pool.map(runner, groups))
	failed = []
	for output, groupFailed in results:
		print(output, end='', flush=True)
		failed += groupFailed
	for item in failed:
		print(f'❌ {item}')
	return not failed


def changedFiles():
	"""Thay đổi đã commit so với origin/main, đã stage, chưa stage và tệp mới; lỗi Git thì chạy đầy đủ."""
	names = set()
	for arguments in (
		['diff', '--name-only', '-z', 'origin/main...HEAD'],
		['diff', '--name-only', '-z', 'HEAD'],
		['ls-files', '--others', '--exclude-standard', '-z'],
	):
		result = subprocess.run(['git', *arguments], cwd=ROOT, capture_output=True, check=False)
		if result.returncode:
			return None
		names.update(filter(None, result.stdout.decode('utf-8').split('\0')))
	return names


def quickTests(paths):
	"""Chỉ thu hẹp test cho tệp test còn tồn tại; sửa luật, cấu hình hoặc nguồn dùng chung chạy đầy đủ."""
	if not paths:
		return None
	tests = set()
	for name in paths:
		path = Path(name)
		if (
			path.parent != Path('scripts')
			or not path.name.startswith('test_')
			or path.suffix != '.py'
		):
			return None
		if not (ROOT / path).is_file():
			return None
		tests.add(path.stem)
	return sorted(tests)


def main():
	# validate.py, test cần Python ≥ 3.11 (tomllib, datetime.UTC); python3 của macOS là 3.9. Git hook chạy từ
	# ứng dụng giao diện (VS Code…) có thể không có PATH của mise nên dễ gặp bản cũ.
	if sys.version_info < (3, 11):  # noqa: UP036 — cố ý: chặn khi bị chạy bằng Python cũ
		print(
			f'Cần Python ≥ 3.11 (đang dùng {sys.version.split()[0]}) — chạy mise install, mở terminal có mise.'
		)
		return 1
	selected = None
	names = sys.argv[1:] or list(checkGroups())
	if names == ['quick']:
		selected = quickTests(changedFiles())
		if selected:
			print('Kiểm tra nhanh: chỉ thu hẹp tests; mọi nhóm kiểm tra khác vẫn chạy đầy đủ.')
		else:
			print('Không xác định chắc phạm vi test — chạy mọi kiểm tra.')
		names = list(checkGroups())
	unknown = [name for name in names if name not in (*checkGroups(), 'tools')]
	if unknown:
		print(f'Nhóm không có: {", ".join(unknown)}. Có: {", ".join(checkGroups())}, tools.')
		return 2
	groups = [name for name in names if name != 'tools'] or list(checkGroups())
	if not ensureTools(groups):
		return 1
	if names == ['tools']:
		return 0
	return 0 if runGroups(groups, selected) else 1


if __name__ == '__main__':
	sys.exit(main())
