"""Cấu hình công cụ: Prettier, ruff, EditorConfig, phiên bản công cụ (ADR 0008), extension VS Code, Dev
Container."""

import json
import re
import tomllib

from validation.common import (
	ROOT,
	configField,
	configItems,
	error,
	errors,
	readJsonObject,
	readText,
	toolVersions,
)
from validation.formatting import TWO_SPACE_SECTION
from validation.workflows import repositoryWorkflows

# Cấu hình định dạng chuẩn của tổ chức (quy tắc chung): đổi giá trị nào là CI thất bại.
PRETTIER_STANDARD = {
	'useTabs': True,
	'tabWidth': 4,
	'semi': True,
	'singleQuote': True,
	'trailingComma': 'all',
	'printWidth': 100,
	'endOfLine': 'lf',
	'overrides': [{'files': ['*.md', '*.yml', '*.yaml'], 'options': {'useTabs': False}}],
}
RUFF_STANDARD = {
	'line-length': 100,
	'indent-width': 4,
	'format': {'indent-style': 'tab', 'line-ending': 'lf', 'quote-style': 'single'},
}
EDITORCONFIG_STANDARD = (
	'root = true',
	'charset = utf-8',
	'end_of_line = lf',
	'insert_final_newline = true',
	'trim_trailing_whitespace = true',
	'indent_style = tab',
	'indent_size = 4',
	'tab_width = 4',
)


def checkToolVersions():
	"""Phiên bản công cụ chỉ ở mise.toml; Node.js chỉ ở .nvmrc (ADR 0008). Công cụ trong mise.toml (trừ Python, Node.js)
	khớp danh sách check-tool-versions.py theo dõi bản mới."""
	mise = readText(ROOT / 'mise.toml') if (ROOT / 'mise.toml').exists() else ''
	tools = set(re.findall(r'^([a-z-]+) = "[^"]+"$', mise.split('[settings]')[0], re.MULTILINE))
	for tool in sorted((tools - {'python', 'node'}) ^ set(toolVersions.REPOSITORIES)):
		where = (
			'mise.toml: thiếu phiên bản'
			if tool in toolVersions.REPOSITORIES
			else ('scripts/check-tool-versions.py: REPOSITORIES thiếu')
		)
		errors.append(f'{where} {tool}')
	if re.search(r'^node = ', mise, re.MULTILINE):
		errors.append('mise.toml: Node.js khai báo trong .nvmrc, không lặp trong mise.toml')
	# devEngines của package.json phải đúng bản trong .nvmrc: npm chặn Node.js khác bản đó, và mise đọc devEngines
	# để chọn Node.js (">=24" làm mise cài bản mới nhất, khác CI).
	nvmrc, package = ROOT / '.nvmrc', ROOT / 'package.json'
	if nvmrc.exists() and package.exists():
		wanted = readText(nvmrc).strip()
		try:
			engines = configField(package, readJsonObject(package), 'devEngines', dict)
			runtime = configField(package, engines, 'runtime', dict)
		except json.JSONDecodeError:
			runtime = (
				None  # checkFile đã báo lỗi cú pháp; tiếp tục kiểm tra các nguồn phiên bản khác.
			)
		if runtime is not None and runtime.get('version') != wanted:
			errors.append(
				f'package.json: devEngines.runtime.version là "{runtime.get("version")}", phải là "{wanted}" '
				'theo .nvmrc'
			)
	# Nhận phiên bản ghi trực tiếp; f-string đọc phiên bản từ mise.toml không phải nguồn phiên bản thứ hai.
	pinned = re.compile(
		r'ruff==v?\d|pipx install ruff|actionlint@v|download-actionlint|shellcheck-v\d'
	)
	# Không quét validate.py và test_*.py: các tệp này chứa chính các mẫu để so khớp.
	sources = [
		*repositoryWorkflows(),
		*(
			path
			for path in (ROOT / 'workflow-templates').glob('*')
			if path.suffix in ('.yml', '.yaml')
		),
		*(ROOT / '.devcontainer').glob('*.sh'),
		*(
			path
			for path in (ROOT / 'scripts').glob('*.py')
			if path.name != 'validate.py' and not path.name.startswith('test_')
		),
		ROOT / 'Makefile',
	]
	for path in sorted(path for path in sources if path.exists()):
		for number, line in enumerate(readText(path).split('\n'), start=1):
			if pinned.search(line):
				error(path, f'dòng {number}: phiên bản công cụ phải lấy từ mise.toml (ADR 0008)')


def checkFormatConfig():
	"""Cấu hình định dạng không được trái quy tắc: tab, độ rộng 4; dấu cách chỉ cho ngôn ngữ bắt buộc."""
	try:
		prettier = readJsonObject(ROOT / '.prettierrc.json')
	except (OSError, json.JSONDecodeError) as exc:
		errors.append(f'.prettierrc.json: không đọc được ({exc})')
		prettier = {}
	if prettier.get('useTabs') is not True or prettier.get('tabWidth') != 4:
		errors.append('.prettierrc.json: bắt buộc "useTabs": true và "tabWidth": 4')
	for override in configItems(ROOT / '.prettierrc.json', prettier, 'overrides'):
		options = configField(ROOT / '.prettierrc.json', override, 'options', dict)
		patterns = override.get('files')
		files = (
			{patterns}
			if isinstance(patterns, str)
			else set(configItems(ROOT / '.prettierrc.json', override, 'files', str))
		)
		if 'tabWidth' in options and options['tabWidth'] != 4:
			errors.append('.prettierrc.json: overrides không được đổi tabWidth khác 4')
		if options.get('useTabs') is False and not files <= {'*.md', '*.yml', '*.yaml'}:
			errors.append('.prettierrc.json: chỉ Markdown, YAML được dùng dấu cách')
	editorconfig = readText(ROOT / '.editorconfig')
	errors.extend(
		f'.editorconfig: thiếu "{setting}"'
		for setting in (
			'indent_style = tab',
			'indent_size = 4',
			'tab_width = 4',
			'[*.{yml,yaml,cff,md,fs,fsi,fsx,elm,nim,nims,nimble,zig,zon}]',
			TWO_SPACE_SECTION,
		)
		if setting not in editorconfig
	)
	# Độ rộng 2 chỉ được phép trong mục của các ngôn ngữ có formatter cố định 2 dấu cách.
	for section in re.split(r'\n(?=\[)', editorconfig):
		if section.startswith(TWO_SPACE_SECTION):
			continue
		if re.search(r'(indent_size|tab_width)\s*=\s*2\b', section):
			errors.append('.editorconfig: không được dùng độ rộng 2')
	for path in (ROOT / '.prettierrc.json', ROOT / 'ruff.toml'):
		text = readText(path) if path.exists() else ''
		if re.search(r'(indent_size|tab_width|indent-width)\s*=\s*2\b|"tabWidth"\s*:\s*2\b', text):
			errors.append(f'{path.name}: không được dùng độ rộng 2')
	ruffPath = ROOT / 'ruff.toml'
	ruff = readText(ruffPath) if ruffPath.exists() else ''
	if 'indent-width = 4' not in ruff or 'indent-style = "tab"' not in ruff:
		errors.append('ruff.toml: bắt buộc indent-width = 4 và indent-style = "tab"')
	# Đối chiếu đầy đủ với cấu hình chuẩn.
	for key, value in PRETTIER_STANDARD.items():
		if key in prettier and prettier[key] != value:
			errors.append(
				f'.prettierrc.json: "{key}" phải là {json.dumps(value, ensure_ascii=False)}'
			)
		elif key not in prettier:
			errors.append(f'.prettierrc.json: thiếu "{key}"')
	try:
		ruffConfig = tomllib.loads(ruff)
	except tomllib.TOMLDecodeError as exc:
		errors.append(f'ruff.toml: TOML không hợp lệ ({exc})')
		ruffConfig = {}
	for key, value in RUFF_STANDARD.items():
		pairs = value.items() if isinstance(value, dict) else [(None, value)]
		for sub, expected in pairs:
			actual = (
				configField(ruffPath, ruffConfig, key, dict).get(sub)
				if sub
				else ruffConfig.get(key)
			)
			if actual != expected:
				name = f'{key}.{sub}' if sub else key
				errors.append(f'ruff.toml: {name} phải là {json.dumps(expected)}')
	default = re.search(r'^\[\*\]\n((?:[^\[].*\n?)*)', editorconfig, re.MULTILINE)
	head = editorconfig.split('[', 1)[0]
	for setting in EDITORCONFIG_STANDARD:
		where = head if setting == 'root = true' else (default.group(1) if default else '')
		if not re.search(rf'^{re.escape(setting)}$', where, re.MULTILINE):
			errors.append(
				f'.editorconfig: mục {"đầu tệp" if setting == "root = true" else "[*]"} thiếu "{setting}"'
			)


def checkLintIgnoreConfig():
	""".prettierignore không lặp .gitignore (Prettier 3 tự đọc); nếu có ESLint thì dùng eslint-config-prettier, không bật indent."""

	def entries(name):
		path = ROOT / name
		text = readText(path) if path.exists() else ''
		return {
			line.strip() for line in text.split('\n') if line.strip() and not line.startswith('#')
		}

	errors.extend(
		f'.prettierignore: "{entry}" đã có trong .gitignore — Prettier 3 tự bỏ qua'
		for entry in sorted(entries('.prettierignore') & entries('.gitignore'))
	)
	# Quy tắc chung của tổ chức, áp dụng khi repository dùng ESLint.
	eslintPath = ROOT / 'eslint.config.js'
	if not eslintPath.exists():
		return
	eslint = readText(eslintPath)
	if "from 'eslint-config-prettier'" not in eslint:
		errors.append('eslint.config.js: phải dùng eslint-config-prettier để tắt quy tắc định dạng')
	if re.search(r"""['"]?\bindent['"]?\s*:""", eslint):
		errors.append('eslint.config.js: không bật quy tắc indent — định dạng do Prettier đảm nhận')


def checkEditorExtensions():
	"""Extension VS Code gợi ý tại máy (.vscode/extensions.json) và cài trong Dev Container phải giống nhau."""
	try:
		local = readJsonObject(ROOT / '.vscode' / 'extensions.json')
		container = readJsonObject(ROOT / '.devcontainer' / 'devcontainer.json')
	except (OSError, json.JSONDecodeError):
		return
	wanted = set(configItems(ROOT / '.vscode/extensions.json', local, 'recommendations', str))
	containerPath = ROOT / '.devcontainer/devcontainer.json'
	customizations = configField(containerPath, container, 'customizations', dict)
	vscode = configField(containerPath, customizations, 'vscode', dict)
	installed = set(configItems(containerPath, vscode, 'extensions', str))
	for name in sorted(wanted ^ installed):
		where = '.devcontainer/devcontainer.json' if name in wanted else '.vscode/extensions.json'
		errors.append(f'{where}: thiếu extension "{name}" — hai danh sách phải giống nhau')


def checkDevcontainerPins():
	"""Image và feature của Dev Container ghim theo phiên bản chính (không dùng latest hay bỏ trống tag) để
	container dựng lại giống nhau; Dependabot (devcontainers) đề xuất bản chính mới."""
	path = ROOT / '.devcontainer' / 'devcontainer.json'
	try:
		container = readJsonObject(path)
	except (OSError, json.JSONDecodeError):
		return
	image = configField(path, container, 'image', str) if 'image' in container else None
	references = [*([image] if image else []), *configField(path, container, 'features', dict)]
	for reference in references:
		tag = reference.rsplit('/', 1)[-1].partition(':')[2]
		if not tag or tag == 'latest':
			error(path, f'"{reference}" phải ghim phiên bản chính (ví dụ :1), không dùng latest')
	# Dev Container dùng Python của image (MISE_DISABLE_TOOLS=python): image ghim đúng bản Python của mise.toml để
	# container chạy script như máy cục bộ (ADR 0016).
	if image and '/devcontainers/python:' in image:
		mise = ROOT / 'mise.toml'
		try:
			wanted = tomllib.loads(readText(mise)).get('tools', {}).get('python')
		except (OSError, tomllib.TOMLDecodeError):
			wanted = None  # checkToolVersions báo mise.toml lỗi.
		pinned = re.fullmatch(r'\d+-(\d+\.\d+)-[\w.-]+', image.rpartition(':')[2])
		if wanted and (not pinned or pinned.group(1) != str(wanted)):
			error(
				path,
				f'image "{image}" phải ghim Python {wanted} như mise.toml '
				f'(ví dụ mcr.microsoft.com/devcontainers/python:3-{wanted}-trixie)',
			)
