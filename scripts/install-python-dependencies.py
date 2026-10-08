"""Cài công cụ và phụ thuộc cho workflow mẫu Python CI trong repository đang làm việc.

Chạy: python .org/scripts/install-python-dependencies.py sau khi checkout repository của tổ chức vào .org/.
Ruff lấy phiên bản trong mise.toml của tổ chức. Cài requirements nếu có, rồi cài package của dự án khi có
setup.py/setup.cfg, build-system, dependencies/dynamic của project hoặc cấu hình Poetry. pyproject.toml chỉ
chứa cấu hình công cụ hoặc metadata không được coi là package cần cài. Poetry đặt package-mode = false thì
bỏ bước cài chính dự án; dependency cần xuất ra requirements hoặc cài bằng workflow riêng. Dependency cho
tests bổ sung bằng requirements-dev.txt hoặc chỉnh workflow theo extras/nhóm phụ thuộc của dự án.
"""

import configparser
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hasLegacyPackage(projectRoot):
	"""setup.cfg chỉ cấu hình lint/tests không phải package; metadata/options là phần khai báo setuptools."""
	if (projectRoot / 'setup.py').is_file():
		return True
	path = projectRoot / 'setup.cfg'
	if not path.is_file():
		return False
	config = configparser.ConfigParser(interpolation=None)
	config.read_string(path.read_text(encoding='utf-8'))
	return config.has_section('metadata') or config.has_section('options')


def dependencyCommands(projectRoot):
	"""Đọc cấu hình trước khi cài; mọi lệnh dùng đúng Python đã được setup-python chọn."""
	tools = tomllib.loads((ROOT / 'mise.toml').read_text(encoding='utf-8'))['tools']
	ruffVersion = tools.get('ruff')
	if not isinstance(ruffVersion, str) or not ruffVersion.strip():
		raise ValueError('mise.toml của tổ chức thiếu phiên bản ruff hợp lệ')
	manifest = projectRoot / 'pyproject.toml'
	data = tomllib.loads(manifest.read_text(encoding='utf-8')) if manifest.is_file() else {}
	project = data.get('project', {})
	tool = data.get('tool', {})
	if not isinstance(project, dict) or not isinstance(tool, dict):
		raise TypeError('pyproject.toml: project và tool phải là bảng TOML')
	poetry = tool.get('poetry', {})
	if not isinstance(poetry, dict):
		raise TypeError('pyproject.toml: tool.poetry phải là bảng TOML')
	packageMode = poetry.get('package-mode', True)
	if not isinstance(packageMode, bool):
		raise TypeError('pyproject.toml: tool.poetry.package-mode phải là boolean')
	commands = [
		[sys.executable, '-m', 'pip', 'install', '-r', name]
		for name in ('requirements.txt', 'requirements-dev.txt')
		if (projectRoot / name).is_file()
	]
	# Chế độ không đóng gói của Poetry không cho xây/cài chính dự án, dù vẫn có build-system hoặc dependencies.
	if packageMode and (
		hasLegacyPackage(projectRoot)
		or 'build-system' in data
		or 'dependencies' in project
		or 'dynamic' in project
		or 'poetry' in tool
	):
		commands.append([sys.executable, '-m', 'pip', 'install', '-e', '.'])
	# Cài công cụ cuối cùng để requirements không thay phiên bản Ruff của tổ chức; pytest đã được requirements
	# cài thì pip giữ nguyên, không tự nâng vượt giới hạn của dự án.
	commands.append([sys.executable, '-m', 'pip', 'install', f'ruff=={ruffVersion}', 'pytest'])
	return commands


def main():
	try:
		for command in dependencyCommands(Path.cwd()):
			subprocess.run(command, check=True)
	except (
		OSError,
		ValueError,
		TypeError,
		KeyError,
		configparser.Error,
		subprocess.CalledProcessError,
	) as exc:
		print(f'❌ Không cài được công cụ hoặc phụ thuộc Python: {exc}', file=sys.stderr)
		return 1
	return 0


if __name__ == '__main__':
	sys.exit(main())
