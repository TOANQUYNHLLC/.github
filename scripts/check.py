"""Chạy các nhóm kiểm tra của repository — cùng một lệnh tại máy (make check) và trên GitHub Actions.

Chạy:
	python3 scripts/check.py              # mọi nhóm, theo thứ tự bên dưới
	python3 scripts/check.py format lint  # một vài nhóm
	python3 scripts/check.py tools        # chỉ kiểm tra đã cài đủ công cụ (cài thư viện Node.js nếu thiếu)
Mỗi nhóm khớp một job của workflow validate.yml (content, format, lint) hoặc một workflow Pull Request
(conventions: branch-name.yml, pr-title.yml; audit: dependency-review.yml). CodeQL không chạy tại máy.
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Công cụ nhóm cần mà không đứng đầu lệnh: validate.py đọc YAML bằng Ruby và liệt kê tệp bằng git.
INDIRECT_TOOLS = {'content': ('ruby', 'git'), 'conventions': ('git',)}


def shellScripts():
	# Script ưu tiên Python; shell chỉ khi xử lý tốt hơn và có ghi lý do (ADR 0015).
	folders = (ROOT / 'scripts', ROOT / '.devcontainer')
	return sorted(str(path.relative_to(ROOT)) for folder in folders for path in folder.glob('*.sh'))


def workflowFiles():
	folders = (ROOT / '.github' / 'workflows', ROOT / 'workflow-templates')
	return sorted(
		str(path.relative_to(ROOT)) for folder in folders for path in folder.glob('*.yml')
	)


def checkGroups():
	"""Nhóm kiểm tra → danh sách lệnh; tên nhóm khớp job hoặc workflow trên GitHub Actions."""
	return {
		'content': [
			['python3', 'scripts/validate.py'],
			['python3', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_*.py'],
		],
		'format': [
			['npx', 'prettier', '--check', '.'],
			['ruff', 'format', '--check', 'scripts'],
			# Python ≥ 3.11 (tomllib, datetime.UTC); ruff.toml giữ đúng cấu hình chuẩn nên khai báo ở đây.
			['ruff', 'check', '--target-version', 'py311', 'scripts'],
		],
		'lint': [['shellcheck', *shellScripts()], ['actionlint', *workflowFiles()]],
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
		subprocess.run(['npm', 'install', '--no-audit', '--no-fund'], cwd=ROOT, check=True)
	return True


def runGroups(groups):
	failed = []
	for name in groups:
		for command in checkGroups()[name]:
			print(f'$ {" ".join(command)}', flush=True)
			if subprocess.run(command, cwd=ROOT, check=False).returncode != 0:
				failed.append(f'{name}: {" ".join(command)[:80]}')
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
