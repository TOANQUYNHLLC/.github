"""Kiểm tra tính nhất quán của repository .github.

Chạy: python3 scripts/validate.py  (cần Python ≥ 3.11 — tomllib, datetime.UTC — và Ruby để đọc YAML;
cả hai có sẵn trên runner GitHub; trên máy dùng Python do mise cài, không dùng Python 3.9 của macOS).
"""

import json
import re
import subprocess
import sys
import tomllib
import unicodedata
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORM_TYPES = {'markdown', 'textarea', 'input', 'dropdown', 'checkboxes'}
# Khóa cấp cao nhất GitHub chấp nhận trong biểu mẫu Issue. `type` (Issue Type) có trong tài liệu nhưng GitHub
# từ chối: "type is not a permitted key" và không hiện biểu mẫu (xem scripts/check-github-forms.py).
ISSUE_FORM_KEYS = {'name', 'description', 'title', 'labels', 'assignees', 'projects', 'body'}
# Biểu mẫu Discussion chỉ nhận các khóa này ở cấp cao nhất (không có name, description như Issue).
DISCUSSION_FORM_KEYS = {'title', 'labels', 'body'}
# Danh mục chung của workflow mẫu (actions/starter-workflows): danh mục đầu tiên phải thuộc nhóm này,
# sau đó mới tới ngôn ngữ Linguist hoặc tech stack.
WORKFLOW_GENERAL_CATEGORIES = {
	'Continuous integration',
	'Deployment',
	'Testing',
	'Code quality',
	'Code review',
	'Dependency review',
	'Dependency graph',
	'Code Scanning',
	'Monitoring',
	'Automation',
	'Utilities',
	'Pages',
}
# Email liên hệ chung của công ty — mọi tài liệu phải dùng đúng địa chỉ này.
COMPANY_EMAIL = 'toanquynhvn@gmail.com'
errors = []
FORM_LABELS = []


def error(path, message):
	errors.append(f'{path.relative_to(ROOT)}: {message}')


def load_yaml(path):
	result = subprocess.run(
		['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.dump(YAML.load_file(ARGV[0]))', str(path)],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode != 0:
		error(path, f'YAML không hợp lệ: {result.stderr.strip()}')
		return None
	return json.loads(result.stdout)


def tracked_files():
	"""File git quản lý hoặc sắp được thêm; bỏ qua mọi thứ nằm trong .gitignore."""
	output = subprocess.run(
		['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
		cwd=ROOT,
		capture_output=True,
		check=True,
	).stdout.decode('utf-8')
	for name in sorted(set(filter(None, output.split('\0')))):
		path = ROOT / name
		if path.is_file():
			yield path


# Bắt buộc thụt lề bằng 4 dấu cách: YAML, Markdown (Prettier), F#, Elm, Nim, Zig.
SPACE_SUFFIXES = (
	'.yml',
	'.yaml',
	'.cff',
	'.md',
	'.fs',
	'.fsi',
	'.fsx',
	'.elm',
	'.nim',
	'.nims',
	'.nimble',
	'.zig',
	'.zon',
)
# Formatter chính thức cố định 2 dấu cách: Dart, Elixir, Terraform, Crystal, Gleam, Nix.
TWO_SPACE_SUFFIXES = ('.dart', '.ex', '.exs', '.tf', '.tfvars', '.cr', '.gleam', '.nix')
TWO_SPACE_SECTION = '[*.{dart,ex,exs,tf,tfvars,cr,gleam,nix}]'
# Bắt buộc CRLF theo .editorconfig và .gitattributes.
CRLF_SUFFIXES = (
	'.bat',
	'.cmd',
	'.dsp',
	'.dsw',
	'.ics',
	'.vcs',
	'.vcf',
	'.eml',
	'.mht',
	'.mhtml',
	'.csv',
	'.sln',
	'.csproj',
	'.vbproj',
	'.vcxproj',
	'.vcxproj.filters',
	'.vcproj',
	'.fsproj',
	'.sqlproj',
	'.wixproj',
	'.reg',
	'.inf',
)
# Visual Studio ghi solution và project kèm BOM UTF-8.
UTF8_BOM_SUFFIXES = (
	'.sln',
	'.csproj',
	'.vbproj',
	'.vcxproj',
	'.vcxproj.filters',
	'.vcproj',
	'.fsproj',
	'.sqlproj',
	'.wixproj',
)
# regedit và Windows Setup đọc UTF-16 LE có BOM.
UTF16_SUFFIXES = ('.reg', '.inf')
# Khoảng trắng cuối dòng là dữ liệu: ô CSV, email format=flowed (RFC 3676).
KEEP_TRAILING_SPACE_SUFFIXES = ('.csv', '.eml', '.mht', '.mhtml')
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
# Tệp nhị phân (khai báo binary trong .gitattributes): không kiểm tra như văn bản.
BINARY_SUFFIXES = (
	'.png',
	'.jpg',
	'.jpeg',
	'.gif',
	'.ico',
	'.pdf',
	'.webp',
	'.woff',
	'.woff2',
	'.zip',
)


def check_text(path):
	data = path.read_bytes()
	name = path.name
	if name.endswith(UTF16_SUFFIXES):
		if not data.startswith(b'\xff\xfe'):
			error(path, 'phải mã hóa UTF-16 LE có BOM')
			return None
		encoding, label = 'utf-16', 'UTF-16 LE'
	elif name.endswith(UTF8_BOM_SUFFIXES):
		if not data.startswith(b'\xef\xbb\xbf'):
			error(path, 'thiếu BOM UTF-8')
		encoding, label = 'utf-8-sig', 'UTF-8'
	else:
		if data.startswith(b'\xef\xbb\xbf'):
			error(path, 'có BOM UTF-8')
		encoding, label = 'utf-8', 'UTF-8'
	try:
		text = data.decode(encoding)
	except UnicodeDecodeError:
		error(path, f'không phải {label}')
		return None
	if text and not text.endswith('\n'):
		error(path, 'thiếu dòng trống cuối file')
	# Tiếng Việt gõ trên macOS có thể ở dạng tách dấu (NFD): trông giống nhưng khác byte, làm hỏng tìm kiếm.
	# .mailmap cố ý chứa tên dạng NFD để ánh xạ về tên chuẩn.
	if name != '.mailmap' and not unicodedata.is_normalized('NFC', text):
		error(path, 'có chữ Unicode dạng tách dấu (NFD) — chuyển sang dạng dựng sẵn (NFC)')
	if name.endswith(CRLF_SUFFIXES):
		bare = text.replace('\r\n', '')
		if '\n' in bare or '\r' in bare:
			error(path, 'phải xuống dòng bằng CRLF (theo .editorconfig và .gitattributes)')
	elif '\r' in text:
		error(path, 'phải xuống dòng bằng LF (theo .editorconfig và .gitattributes)')
	if name.endswith(KEEP_TRAILING_SPACE_SUFFIXES):
		return text
	for number, line in enumerate(text.split('\n'), start=1):
		if line.rstrip('\r') != line.rstrip('\r').rstrip(' \t'):
			error(path, f'dòng {number}: có khoảng trắng cuối dòng')
			break
	return text


def heading_anchors(path):
	"""Anchor GitHub tạo cho các tiêu đề Markdown: chữ thường, bỏ ký tự không phải chữ, số, khoảng trắng,
	gạch ngang; khoảng trắng thành "-"; tiêu đề trùng thêm hậu tố -1, -2…."""
	text = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.DOTALL)
	seen, anchors = {}, set()
	for match in re.finditer(r'^#{1,6} (.+)$', text, re.MULTILINE):
		slug = re.sub(r'[^\w\- ]', '', re.sub(r'`([^`]*)`', r'\1', match.group(1)).strip().lower())
		slug = slug.replace(' ', '-')
		count = seen.get(slug, 0)
		seen[slug] = count + 1
		anchors.add(slug if count == 0 else f'{slug}-{count}')
	return anchors


def check_links(path, text):
	body = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
	for match in re.finditer(r'\]\(([^)\s#]*)(?:#([^)\s]*))?\)', body):
		target, fragment = match.group(1), match.group(2)
		if re.match(r'[a-z]+:', target) or (not target and fragment is None):
			continue
		destination = path.parent / target if target else path
		if not destination.exists():
			error(path, f'liên kết hỏng: {target}')
		elif (
			fragment
			and destination.suffix == '.md'
			and fragment not in heading_anchors(destination)
		):
			error(path, f'liên kết hỏng: {target}#{fragment} — không có tiêu đề tương ứng')


def check_absolute_links(path, text):
	"""Biểu mẫu hiển thị trong repository khác: liên kết tương đối sẽ trỏ sai repository."""
	for match in re.finditer(r'\]\(([^)\s]+)\)', text):
		if not re.match(r'(https?|mailto):', match.group(1)):
			error(
				path,
				f'liên kết "{match.group(1)}" phải là URL tuyệt đối (biểu mẫu dùng ở mọi repository)',
			)


def check_security_mailto(path, text):
	link = re.search(r'mailto:[^?)\s]+\?([^)\s]+)', text)
	details = re.search(r'<details>.*?<br>\s*\n(.*?)\n\s*</details>', text, re.DOTALL)
	if not link or not details:
		error(path, 'thiếu liên kết soạn email hoặc mẫu nội dung email')
		return
	query = urllib.parse.parse_qs(link.group(1))
	lines = [line.rstrip() for line in details.group(1).strip().split('\n')]
	subject = re.match(r'\*\*Tiêu đề:\*\*\s*(.+)', lines[0])
	template = '\n'.join(re.sub(r'\*\*', '', line) for line in lines[1:]).strip()
	if not subject or query.get('subject', [''])[0] != subject.group(1):
		error(path, 'tiêu đề trong liên kết email khác mẫu')
	if query.get('body', [''])[0].replace('\r\n', '\n').strip() != template:
		error(path, 'nội dung liên kết email khác mẫu "Xem Mẫu Nội Dung Email"')


def check_form(path, required=('name', 'description', 'body')):
	form = load_yaml(path)
	if form is None:
		return
	for key in required:
		if not form.get(key):
			error(path, f'thiếu khóa bắt buộc "{key}"')
	check_absolute_links(path, path.read_text(encoding='utf-8'))
	if path.parent.name == 'DISCUSSION_TEMPLATE':
		for key in sorted(set(form) - DISCUSSION_FORM_KEYS):
			error(path, f'biểu mẫu Discussion không hỗ trợ khóa "{key}"')
	if path.parent.name == 'ISSUE_TEMPLATE':
		for key in sorted(set(form) - ISSUE_FORM_KEYS):
			error(path, f'khóa "{key}" không được GitHub chấp nhận trong biểu mẫu Issue')
	for label in form.get('labels') or []:
		FORM_LABELS.append((path, label))
	ids = set()
	for index, item in enumerate(form.get('body') or [], start=1):
		kind = item.get('type')
		attributes = item.get('attributes') or {}
		if kind not in FORM_TYPES:
			error(path, f'phần tử {index}: type "{kind}" không hợp lệ')
			continue
		if kind == 'markdown':
			if not attributes.get('value'):
				error(path, f'phần tử {index}: markdown thiếu value')
			continue
		if not attributes.get('label'):
			error(path, f'phần tử {index}: thiếu label')
		elif attributes['label'] != attributes['label'].upper():
			error(path, f'phần tử {index}: tiêu đề trường "{attributes["label"]}" phải viết hoa')
		item_id = item.get('id')
		if item_id in ids:
			error(path, f'phần tử {index}: id "{item_id}" bị trùng')
		ids.add(item_id)
		if kind in ('dropdown', 'checkboxes') and not attributes.get('options'):
			error(path, f'phần tử {index}: {kind} thiếu options')


def check_workflow(path, text):
	"""Mọi action bên ngoài ghim theo commit SHA đầy đủ và workflow khai báo quyền tối thiểu."""
	for number, line in enumerate(text.split('\n'), start=1):
		match = re.search(r'^\s*-?\s*uses:\s*([^\s#]+)', line)
		if not match or match.group(1).startswith(('./', 'docker://')):
			continue
		ref = match.group(1).rsplit('@', 1)
		if len(ref) != 2 or not re.fullmatch(r'[0-9a-f]{40}', ref[1]):
			error(
				path, f'dòng {number}: action "{match.group(1)}" phải ghim theo commit SHA đầy đủ'
			)
	if not re.search(r'^permissions:', text, re.MULTILINE):
		error(path, 'thiếu khai báo "permissions" ở cấp workflow')
	# GitHub chỉ thay $default-branch khi tạo workflow từ mẫu; trong workflow thật nó là chuỗi nguyên văn.
	if path.parent.parts[-2:] == ('.github', 'workflows') and '$default-branch' in text:
		error(
			path, '$default-branch chỉ dùng trong workflow-templates/ — ghi tên nhánh thật (main)'
		)
	if not re.search(r'^concurrency:', text, re.MULTILINE):
		error(path, 'thiếu khai báo "concurrency" ở cấp workflow')
	for number, line in enumerate(text.split('\n'), start=1):
		if re.match(r'^\s+[a-z-]+: write\s*$', line):
			error(path, f'dòng {number}: quyền ghi cần chú thích lý do (# …)')
	workflow = load_yaml(path)
	top = (workflow or {}).get('permissions')
	if top == 'write-all' or (isinstance(top, dict) and 'write' in top.values()):
		error(path, 'quyền ghi chỉ cấp ở job cần dùng, không cấp ở cấp workflow')
	for name, job in ((workflow or {}).get('jobs') or {}).items():
		if 'timeout-minutes' not in job:
			error(path, f'job "{name}" thiếu timeout-minutes')


def check_workflow_template(path):
	properties = path.with_suffix('.properties.json')
	if not properties.exists():
		error(path, f'thiếu tệp {properties.name}')
		return
	try:
		meta = json.loads(properties.read_text(encoding='utf-8'))
	except json.JSONDecodeError as exc:
		error(properties, f'JSON không hợp lệ: {exc}')
		return
	for key in ('name', 'description'):
		if not meta.get(key):
			error(properties, f'thiếu khóa bắt buộc "{key}"')
	categories = meta.get('categories') or []
	if not categories or categories[0] not in WORKFLOW_GENERAL_CATEGORIES:
		error(
			properties,
			'danh mục đầu tiên phải là danh mục chung của starter-workflows (ví dụ "Continuous integration")',
		)
	icon = meta.get('iconName')
	if icon and not (path.parent / f'{icon}.svg').exists():
		error(properties, f'không tìm thấy biểu tượng {icon}.svg')


def check_tool_versions():
	"""Phiên bản ruff, ShellCheck, actionlint chỉ ở mise.toml; Node.js chỉ ở .nvmrc (ADR 0007)."""
	mise = (ROOT / 'mise.toml').read_text(encoding='utf-8') if (ROOT / 'mise.toml').exists() else ''
	for tool in ('ruff', 'shellcheck', 'actionlint'):
		if not re.search(rf'^{tool} = "[^"]+"$', mise, re.MULTILINE):
			errors.append(f'mise.toml: thiếu phiên bản {tool}')
	if re.search(r'^node = ', mise, re.MULTILINE):
		errors.append('mise.toml: Node.js khai báo trong .nvmrc, không lặp trong mise.toml')
	pinned = re.compile(r'ruff==|pipx install ruff|actionlint@v|download-actionlint|shellcheck-v\d')
	# Không quét scripts/*.py: validate.py và test chứa chính các mẫu này để so khớp.
	sources = [
		*(ROOT / '.github' / 'workflows').glob('*.yml'),
		*(ROOT / '.devcontainer').glob('*.sh'),
		*(ROOT / 'scripts').glob('*.sh'),
		ROOT / 'Makefile',
	]
	for path in sorted(path for path in sources if path.exists()):
		for number, line in enumerate(path.read_text(encoding='utf-8').split('\n'), start=1):
			if pinned.search(line):
				error(path, f'dòng {number}: phiên bản công cụ phải lấy từ mise.toml (ADR 0007)')


def check_format_config():
	"""Cấu hình định dạng không được trái quy tắc: tab, độ rộng 4; dấu cách chỉ cho ngôn ngữ bắt buộc."""
	try:
		prettier = json.loads((ROOT / '.prettierrc.json').read_text(encoding='utf-8'))
	except (OSError, json.JSONDecodeError) as exc:
		errors.append(f'.prettierrc.json: không đọc được ({exc})')
		prettier = {}
	if prettier.get('useTabs') is not True or prettier.get('tabWidth') != 4:
		errors.append('.prettierrc.json: bắt buộc "useTabs": true và "tabWidth": 4')
	for override in prettier.get('overrides', []):
		options = override.get('options', {})
		files = set(override.get('files', []))
		if 'tabWidth' in options and options['tabWidth'] != 4:
			errors.append('.prettierrc.json: overrides không được đổi tabWidth khác 4')
		if options.get('useTabs') is False and not files <= {'*.md', '*.yml', '*.yaml'}:
			errors.append('.prettierrc.json: chỉ Markdown, YAML được dùng dấu cách')
	editorconfig = (ROOT / '.editorconfig').read_text(encoding='utf-8')
	for setting in (
		'indent_style = tab',
		'indent_size = 4',
		'tab_width = 4',
		'[*.{yml,yaml,cff,md,fs,fsi,fsx,elm,nim,nims,nimble,zig,zon}]',
		TWO_SPACE_SECTION,
	):
		if setting not in editorconfig:
			errors.append(f'.editorconfig: thiếu "{setting}"')
	# Độ rộng 2 chỉ được phép trong mục của các ngôn ngữ có formatter cố định 2 dấu cách.
	for section in re.split(r'\n(?=\[)', editorconfig):
		if section.startswith(TWO_SPACE_SECTION):
			continue
		if re.search(r'(indent_size|tab_width)\s*=\s*2\b', section):
			errors.append('.editorconfig: không được dùng độ rộng 2')
	for path in (ROOT / '.prettierrc.json', ROOT / 'ruff.toml'):
		text = path.read_text(encoding='utf-8') if path.exists() else ''
		if re.search(r'(indent_size|tab_width|indent-width)\s*=\s*2\b|"tabWidth"\s*:\s*2\b', text):
			errors.append(f'{path.name}: không được dùng độ rộng 2')
	ruff_path = ROOT / 'ruff.toml'
	ruff = ruff_path.read_text(encoding='utf-8') if ruff_path.exists() else ''
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
		ruff_config = tomllib.loads(ruff)
	except tomllib.TOMLDecodeError as exc:
		errors.append(f'ruff.toml: TOML không hợp lệ ({exc})')
		ruff_config = {}
	for key, value in RUFF_STANDARD.items():
		pairs = value.items() if isinstance(value, dict) else [(None, value)]
		for sub, expected in pairs:
			actual = (ruff_config.get(key) or {}).get(sub) if sub else ruff_config.get(key)
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


def check_lint_ignore_config():
	""".prettierignore không lặp .gitignore (Prettier 3 tự đọc); ESLint dùng eslint-config-prettier, không bật indent."""

	def entries(name):
		path = ROOT / name
		text = path.read_text(encoding='utf-8') if path.exists() else ''
		return {
			line.strip() for line in text.split('\n') if line.strip() and not line.startswith('#')
		}

	for entry in sorted(entries('.prettierignore') & entries('.gitignore')):
		errors.append(f'.prettierignore: "{entry}" đã có trong .gitignore — Prettier 3 tự bỏ qua')
	eslint_path = ROOT / 'eslint.config.js'
	eslint = eslint_path.read_text(encoding='utf-8') if eslint_path.exists() else ''
	if "from 'eslint-config-prettier'" not in eslint:
		errors.append('eslint.config.js: phải dùng eslint-config-prettier để tắt quy tắc định dạng')
	if re.search(r"""['"]?\bindent['"]?\s*:""", eslint):
		errors.append('eslint.config.js: không bật quy tắc indent — định dạng do Prettier đảm nhận')


def editorconfig_suffixes(editorconfig, setting):
	"""Đuôi file của mọi mục .editorconfig dạng [*.x] hoặc [*.{x,y}] có chứa `setting`."""
	suffixes = set()
	for header, body in re.findall(
		r'^\[\*\.\{?([^\]}]+)\}?\]\n((?:[^\[].*\n?)*)', editorconfig, re.MULTILINE
	):
		if re.search(rf'^{re.escape(setting)}$', body, re.MULTILINE):
			suffixes.update(f'.{name}' for name in header.split(','))
	return suffixes


def check_suffix_lists():
	"""Danh sách đuôi file trong validate.py, .editorconfig và .gitattributes phải khớp nhau."""
	editorconfig = (ROOT / '.editorconfig').read_text(encoding='utf-8')
	attributes = (ROOT / '.gitattributes').read_text(encoding='utf-8')
	for setting, expected in (
		('end_of_line = crlf', CRLF_SUFFIXES),
		('charset = utf-8-bom', UTF8_BOM_SUFFIXES),
		('charset = utf-16le', UTF16_SUFFIXES),
		('trim_trailing_whitespace = false', KEEP_TRAILING_SPACE_SUFFIXES),
		('indent_size = 2', TWO_SPACE_SUFFIXES),
	):
		found = editorconfig_suffixes(editorconfig, setting)
		for suffix in sorted(set(expected) ^ found):
			where = 'thiếu' if suffix in expected else 'thừa'
			errors.append(
				f'.editorconfig: {where} {suffix} trong mục "{setting}" so với validate.py'
			)
	spaces = editorconfig_suffixes(editorconfig, 'indent_style = space') - set(TWO_SPACE_SUFFIXES)
	for suffix in sorted(set(SPACE_SUFFIXES) ^ spaces):
		where = 'thiếu' if suffix in SPACE_SUFFIXES else 'thừa'
		errors.append(f'.editorconfig: {where} {suffix} trong mục dấu cách so với validate.py')
	crlf = {m for m in re.findall(r'^\*(\.\S+) .*\beol=crlf\b', attributes, re.MULTILINE)}
	for suffix in sorted(set(CRLF_SUFFIXES) ^ crlf):
		where = 'thiếu' if suffix in CRLF_SUFFIXES else 'thừa'
		errors.append(f'.gitattributes: {where} {suffix} text eol=crlf so với validate.py')
	utf16 = set(
		re.findall(r'^\*(\.\S+) .*\bworking-tree-encoding=UTF-16LE-BOM\b', attributes, re.MULTILINE)
	)
	for suffix in sorted(set(UTF16_SUFFIXES) ^ utf16):
		where = 'thiếu' if suffix in UTF16_SUFFIXES else 'thừa'
		errors.append(
			f'.gitattributes: {where} working-tree-encoding cho {suffix} so với validate.py'
		)
	binary = set(re.findall(r'^\*(\.\S+) binary$', attributes, re.MULTILINE))
	for suffix in sorted(set(BINARY_SUFFIXES) ^ binary):
		where = 'thiếu' if suffix in BINARY_SUFFIXES else 'thừa'
		errors.append(f'.gitattributes: {where} {suffix} binary so với validate.py')


def contributing_section(text, heading):
	"""Nội dung một mục `## …` của CONTRIBUTING.md, tới mục kế tiếp."""
	match = re.search(
		rf'^## .*{re.escape(heading)}\n(.*?)(?=^## |\Z)', text, re.MULTILINE | re.DOTALL
	)
	return match.group(1) if match else ''


def workflow_pattern_words(path):
	"""Các lựa chọn trong nhóm đầu tiên của biến pattern='^(a|b|…)…' trong workflow."""
	text = path.read_text(encoding='utf-8') if path.exists() else ''
	match = re.search(r"pattern='\^\(([a-z|]+)\)", text)
	return set(match.group(1).split('|')) if match else set()


def check_conventions():
	"""Loại commit và tiền tố branch trong CONTRIBUTING.md phải khớp các workflow kiểm tra."""
	contributing = (ROOT / 'CONTRIBUTING.md').read_text(encoding='utf-8')
	types = set(
		re.findall(
			r'^\| `([a-z]+)` ', contributing_section(contributing, 'QUY ƯỚC COMMIT'), re.MULTILINE
		)
	)
	prefixes = set(
		re.findall(
			r'^\| `([a-z]+)/` ',
			contributing_section(contributing, 'QUY ƯỚC ĐẶT TÊN BRANCH'),
			re.MULTILINE,
		)
	)
	# Mỗi tiền tố branch có luật head-branch trong .github/labeler.yml (tự gắn nhãn loại cho Pull Request).
	labeler = ROOT / '.github' / 'labeler.yml'
	if labeler.exists():
		covered = set(re.findall(r"'\^([a-z]+)/'", labeler.read_text(encoding='utf-8')))
		for prefix in sorted(prefixes - covered):
			errors.append(
				f'.github/labeler.yml: thiếu luật head-branch cho tiền tố "{prefix}/" của CONTRIBUTING.md'
			)
	for name, expected in (('pr-title.yml', types), ('branch-name.yml', prefixes)):
		for folder in (ROOT / '.github' / 'workflows', ROOT / 'workflow-templates'):
			path = folder / name
			found = workflow_pattern_words(path)
			for word in sorted(expected ^ found):
				where = 'thiếu' if word in expected else 'thừa'
				errors.append(f'{path.relative_to(ROOT)}: {where} "{word}" so với CONTRIBUTING.md')


def check_rulesets():
	"""Kiểm tra bắt buộc trong ruleset Protect Main phải trùng tên một job có thật, nếu không PR chờ mãi."""
	path = ROOT / 'rulesets' / 'protect-main.json'
	if not path.exists():
		errors.append('thiếu tệp bắt buộc rulesets/protect-main.json')
		return
	try:
		ruleset = json.loads(path.read_text(encoding='utf-8'))
	except json.JSONDecodeError:
		return
	if ruleset.get('name') != 'Protect Main':
		error(path, 'ruleset phải tên "Protect Main"')
	jobs = set()
	for workflow in sorted((ROOT / '.github' / 'workflows').glob('*.yml')):
		for job in ((load_yaml(workflow) or {}).get('jobs') or {}).values():
			jobs.add(job.get('name'))
	# Mọi ruleset (nhánh, tag, cấp repository, cấp tổ chức) bắt buộc commit có chữ ký (ADR 0009).
	for ruleset_path in sorted((ROOT / 'rulesets').glob('*.json')):
		try:
			types = {
				r.get('type')
				for r in json.loads(ruleset_path.read_text(encoding='utf-8')).get('rules', [])
			}
		except json.JSONDecodeError:
			continue
		if 'required_signatures' not in types:
			error(
				ruleset_path, 'ruleset phải có quy tắc required_signatures (Require signed commits)'
			)
	tag_path = ROOT / 'rulesets' / 'protect-release-tags.json'
	if not tag_path.exists():
		errors.append('thiếu tệp bắt buộc rulesets/protect-release-tags.json')
	else:
		try:
			tags = json.loads(tag_path.read_text(encoding='utf-8'))
		except json.JSONDecodeError:
			tags = {}
		include = ((tags.get('conditions') or {}).get('ref_name') or {}).get('include') or []
		if tags.get('name') != 'Protect Release Tags' or tags.get('target') != 'tag':
			error(tag_path, 'ruleset phải tên "Protect Release Tags", target "tag" (ADR 0008)')
		if 'refs/tags/v*' not in include:
			error(tag_path, 'ruleset phải áp dụng cho refs/tags/v* (tag phát hành)')
		if not {'creation', 'update', 'deletion'} <= {
			rule.get('type') for rule in tags.get('rules') or []
		}:
			error(tag_path, 'ruleset phải chặn creation, update, deletion của tag phát hành')
	org_path = ROOT / 'rulesets' / 'org-protect-main.json'
	if not org_path.exists():
		errors.append('thiếu tệp bắt buộc rulesets/org-protect-main.json')
	else:
		try:
			org = json.loads(org_path.read_text(encoding='utf-8'))
		except json.JSONDecodeError:
			org = {}
		repositories = ((org.get('conditions') or {}).get('repository_name') or {}).get(
			'include'
		) or []
		if org.get('name') != 'Protect Main (Organization)' or '~ALL' not in repositories:
			error(
				org_path,
				'ruleset phải tên "Protect Main (Organization)" và nhắm mọi repository (~ALL)',
			)
		if 'code_quality' in {rule.get('type') for rule in org.get('rules') or []}:
			error(
				org_path,
				'ruleset cấp tổ chức không hỗ trợ quy tắc code_quality — GitHub từ chối khi import',
			)
	# Import ruleset cấp tổ chức báo "contains an invalid actor" với actor loại User.
	for org_file in sorted((ROOT / 'rulesets').glob('org-*.json')):
		if re.search(r'"(actor_type|type)":\s*"User"', org_file.read_text(encoding='utf-8')):
			error(
				org_file,
				'ruleset cấp tổ chức không dùng actor loại User — GitHub từ chối khi import',
			)
	org_tag_path = ROOT / 'rulesets' / 'org-protect-release-tags.json'
	if not org_tag_path.exists():
		errors.append('thiếu tệp bắt buộc rulesets/org-protect-release-tags.json')
	else:
		try:
			org_tags = json.loads(org_tag_path.read_text(encoding='utf-8'))
		except json.JSONDecodeError:
			org_tags = {}
		conditions = org_tags.get('conditions') or {}
		if (
			org_tags.get('name') != 'Protect Release Tags (Organization)'
			or '~ALL' not in (conditions.get('repository_name') or {}).get('include', [])
			or 'refs/tags/v*' not in (conditions.get('ref_name') or {}).get('include', [])
		):
			error(
				org_tag_path,
				'ruleset phải tên "Protect Release Tags (Organization)", nhắm ~ALL repository và refs/tags/v*',
			)
	for rule in ruleset.get('rules', []):
		for check in (rule.get('parameters') or {}).get('required_status_checks', []):
			if check.get('context') not in jobs:
				error(
					path,
					f'kiểm tra bắt buộc "{check.get("context")}" không trùng tên job nào trong .github/workflows',
				)


def check_adr_index():
	"""Bảng trong docs/adr/README.md phải liệt kê mọi ADR, cùng ngày và cùng trạng thái với từng tệp."""
	folder = ROOT / 'docs' / 'adr'
	index_path = folder / 'README.md'
	if not index_path.exists():
		return
	rows = {
		number: (status.strip(), date.strip())
		for number, status, date in re.findall(
			r'^\| \[(\d{4})\]\([^)]+\) +\|[^|]+\|([^|]+)\|([^|]+)\|$',
			index_path.read_text(encoding='utf-8'),
			re.MULTILINE,
		)
	}
	for path in sorted(folder.glob('[0-9][0-9][0-9][0-9]-*.md')):
		number = path.name[:4]
		text = path.read_text(encoding='utf-8')
		status = re.search(r'^- \*\*Trạng thái:\*\* (.+)$', text, re.MULTILINE)
		date = re.search(r'^- \*\*Ngày:\*\* (.+)$', text, re.MULTILINE)
		if not status or not date:
			error(path, 'thiếu dòng "Trạng thái" hoặc "Ngày"')
			continue
		if number not in rows:
			error(index_path, f'bảng thiếu ADR {number}')
			continue
		row_status, row_date = rows[number]
		if row_date != date.group(1).strip():
			error(index_path, f'ADR {number}: ngày "{row_date}" khác tệp ADR ({date.group(1)})')
		superseded = 'thay thế' in status.group(1).lower()
		if superseded != ('thay thế' in row_status.lower()) or (
			superseded
			and set(re.findall(r'\b\d{4}\b', row_status))
			!= set(re.findall(r'\b\d{4}\b', status.group(1)))
		):
			error(
				index_path,
				f'ADR {number}: trạng thái "{row_status}" khác tệp ADR ({status.group(1)})',
			)


def check_space_only(path, text):
	"""Ngôn ngữ bắt buộc dấu cách (4 hoặc 2 mỗi cấp theo formatter chính thức): không dùng tab."""
	width = 2 if path.suffix in TWO_SPACE_SUFFIXES else 4
	in_fence = False
	for number, line in enumerate(text.split('\n'), start=1):
		if path.suffix == '.md' and line.lstrip().startswith('```'):
			in_fence = not in_fence
			continue
		if not in_fence and re.match(r'^ *\t', line):
			error(
				path,
				f'dòng {number}: {path.suffix} phải thụt lề bằng {width} dấu cách, không dùng tab',
			)
			return


def check_tab_only(path, text):
	"""Mọi tệp mặc định dùng tab (theo .editorconfig): thụt lề chỉ bằng tab, không trộn dấu cách."""
	for number, line in enumerate(text.split('\n'), start=1):
		indent = re.match(r'^[ \t]*', line).group(0)
		# Dòng tiếp nối chú thích khối (/** … */) do Prettier sinh ra: tab rồi " *".
		if re.match(r'^\t* \*', line):
			continue
		if ' ' in indent and line.strip():
			error(path, f'dòng {number}: thụt lề phải dùng tab theo .editorconfig')
			return


def check_headings(path, text):
	"""Phong cách thống nhất của repository: mọi tiêu đề Markdown viết hoa."""
	in_fence = False
	for number, line in enumerate(text.split('\n'), start=1):
		if line.lstrip().startswith('```'):
			in_fence = not in_fence
		heading = re.match(r'#{1,6} (.+)', line)
		title = re.sub(r'`[^`]*`|\[[^\]]*\]\([^)]*\)', '', heading.group(1)) if heading else ''
		if heading and not in_fence and title != title.upper():
			error(path, f'dòng {number}: tiêu đề phải viết hoa — "{heading.group(1)}"')


def check_labels(path):
	labels = load_yaml(path)
	if not isinstance(labels, list):
		error(path, 'phải là danh sách nhãn')
		return set()
	names = set()
	for index, label in enumerate(labels, start=1):
		name = str(label.get('name') or '')
		if not name:
			error(path, f'nhãn {index}: thiếu name')
			continue
		if name.lower() in names:
			error(path, f'nhãn "{name}" bị trùng')
		names.add(name.lower())
		if not re.fullmatch(r'[0-9a-fA-F]{6}', str(label.get('color') or '')):
			error(path, f'nhãn "{name}": color phải là mã hex 6 ký tự')
		if len(str(label.get('description') or '')) > 100:
			error(path, f'nhãn "{name}": description vượt quá 100 ký tự')
	return names


def check_dependabot_cooldown():
	"""Mọi mục Dependabot chờ ≥ 7 ngày sau khi phát hành (chống gói độc vừa phát hành; không ảnh hưởng cập nhật bảo mật)."""
	for path in (
		ROOT / '.github' / 'dependabot.yml',
		ROOT / 'repository-templates' / 'dependabot.yml',
	):
		for update in ((load_yaml(path) if path.exists() else None) or {}).get('updates') or []:
			days = (update.get('cooldown') or {}).get('default-days')
			if not isinstance(days, int) or days < 7:
				error(path, f'{update.get("package-ecosystem")}: cần cooldown.default-days ≥ 7')


def config_labels():
	"""Nhãn dùng trong dependabot.yml, release.yml, labeler.yml và workflow stale (bản của repository này và bản mẫu)."""
	found = []
	for path in (
		ROOT / '.github' / 'dependabot.yml',
		ROOT / 'repository-templates' / 'dependabot.yml',
	):
		for update in ((load_yaml(path) if path.exists() else None) or {}).get('updates') or []:
			found += [(path, label) for label in update.get('labels') or []]
	for path in (ROOT / '.github' / 'release.yml', ROOT / 'repository-templates' / 'release.yml'):
		changelog = ((load_yaml(path) if path.exists() else None) or {}).get('changelog') or {}
		found += [(path, label) for label in (changelog.get('exclude') or {}).get('labels') or []]
		for category in changelog.get('categories') or []:
			found += [(path, label) for label in category.get('labels') or [] if label != '*']
	for path in (ROOT / '.github' / 'labeler.yml', ROOT / 'repository-templates' / 'labeler.yml'):
		found += [(path, label) for label in ((load_yaml(path) if path.exists() else None) or {})]
	for path in (
		ROOT / '.github' / 'workflows' / 'stale.yml',
		ROOT / 'workflow-templates' / 'stale.yml',
	):
		if not path.exists():
			continue
		text = path.read_text(encoding='utf-8')
		for match in re.finditer(
			r'^\s*(?:stale|exempt)-(?:issue|pr)-labels?:\s*(.+)$', text, re.MULTILINE
		):
			names = match.group(1).strip().strip('\'"').split(',')
			found += [(path, name.strip()) for name in names if name.strip()]
	return found


def check_emails(path, text):
	for email in set(
		re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}', text)
	):
		if email.lower() != COMPANY_EMAIL:
			error(path, f'email "{email}" khác email chung của công ty ({COMPANY_EMAIL})')


def check_security_txt(path, text):
	fields = dict(re.findall(r'^([A-Za-z-]+):\s*(.+)$', text, re.MULTILINE))
	for key in ('Contact', 'Expires'):
		if key not in fields:
			error(path, f'thiếu trường bắt buộc "{key}" (RFC 9116)')
	# RFC 9116 cho phép nhiều Contact; email chung của công ty phải là một trong số đó.
	contacts = re.findall(r'^Contact:\s*(.+)$', text, re.MULTILINE)
	if contacts and f'mailto:{COMPANY_EMAIL}' not in contacts:
		error(path, f'Contact phải có mailto:{COMPANY_EMAIL}')
	expires = fields.get('Expires', '')
	try:
		moment = datetime.fromisoformat(expires)
	except ValueError:
		error(path, f'Expires không đúng định dạng ISO 8601: {expires}')
		return
	remaining = (moment - datetime.now(UTC)).days
	if remaining < 0:
		error(path, 'Expires đã hết hạn — gia hạn tối đa 1 năm')
	elif remaining > 366:
		error(path, 'Expires vượt quá 1 năm (RFC 9116 khuyến nghị tối đa 1 năm)')


def check_changelog(path, text):
	versions = re.findall(r'^## \[([^\]]+)\]', text, re.MULTILINE)
	if not versions or versions[0] != 'CHƯA PHÁT HÀNH':
		error(path, 'mục đầu tiên phải là "## [CHƯA PHÁT HÀNH]"')
	if len(versions) != len(set(versions)):
		error(path, 'có phiên bản bị lặp')


def check_shell(path):
	data = path.read_bytes()
	if b'\r' in data:
		error(path, 'shell script phải dùng LF')
	if not data.startswith(b'#!'):
		error(path, 'shell script thiếu shebang')


def check_issue_config(path):
	config = load_yaml(path)
	if config is None:
		return
	for link in config.get('contact_links') or []:
		for key in ('name', 'url', 'about'):
			if not link.get(key):
				error(path, f'contact_links thiếu "{key}"')


for file in tracked_files():
	# GitHub chỉ nhận biểu mẫu Issue, Discussion và FUNDING.yml trong thư mục .github/.
	if (
		file.parent.name in ('ISSUE_TEMPLATE', 'DISCUSSION_TEMPLATE')
		and file.parent.parent != ROOT / '.github'
	) or (file.name == 'FUNDING.yml' and file.parent != ROOT / '.github'):
		error(file, 'phải nằm trong thư mục .github/ để GitHub nhận diện')
	if file.suffix == '.sh':
		check_shell(file)
	if file.suffix in SPACE_SUFFIXES + TWO_SPACE_SUFFIXES:
		check_space_only(file, file.read_text(encoding='utf-8'))
	if file.suffix in BINARY_SUFFIXES:
		continue
	content = check_text(file)
	if content is None:
		continue
	if not file.name.endswith(SPACE_SUFFIXES + TWO_SPACE_SUFFIXES + KEEP_TRAILING_SPACE_SUFFIXES):
		check_tab_only(file, content)
	# .mailmap ánh xạ email tác giả commit (kể cả địa chỉ noreply của GitHub), không phải email liên hệ.
	if file.name != '.mailmap':
		check_emails(file, content)
	if file.name == 'security.txt':
		check_security_txt(file, content)
	if file.name == 'CHANGELOG.md':
		check_changelog(file, content)
	if (
		file.suffix in ('.sh', '.svg', '.txt', '.js', '.toml')
		or file.suffix == ''
		or file.name.startswith('.')
	):
		continue
	if file.suffix == '.md':
		check_links(file, content)
		check_headings(file, content)
	if file.name == 'SECURITY.md':
		check_security_mailto(file, content)
	if file.name == 'PULL_REQUEST_TEMPLATE.md':
		check_absolute_links(file, content)
	if file.parent.name == 'ISSUE_TEMPLATE' and file.suffix in ('.yml', '.yaml'):
		if file.stem == 'config':
			check_issue_config(file)
		else:
			check_form(file)
	elif file.parent.name == 'DISCUSSION_TEMPLATE' and file.suffix in ('.yml', '.yaml'):
		check_form(file, required=('body',))
	elif file.suffix in ('.yml', '.yaml') and (
		file.parent.name == 'workflow-templates'
		or file.parent.parts[-2:] == ('.github', 'workflows')
	):
		check_workflow(file, content)
		if file.parent.name == 'workflow-templates':
			check_workflow_template(file)
	elif file.suffix in ('.yml', '.yaml') and file != ROOT / 'labels.yml':
		load_yaml(file)
	elif file.suffix == '.json':
		try:
			json.loads(content)
		except json.JSONDecodeError as exc:
			error(file, f'JSON không hợp lệ: {exc}')

check_format_config()
check_lint_ignore_config()
check_dependabot_cooldown()
check_tool_versions()
check_suffix_lists()
check_conventions()
check_rulesets()
check_adr_index()

for required in (
	'README.md',
	'CHANGELOG.md',
	'LICENSE',
	'SECURITY.md',
	'CONTRIBUTING.md',
	'CODE_OF_CONDUCT.md',
	'SUPPORT.md',
):
	if not (ROOT / required).exists():
		errors.append(f'thiếu tệp bắt buộc {required}')

label_file = ROOT / 'labels.yml'
if label_file.exists():
	known = check_labels(label_file)
	for form_path, label in FORM_LABELS + config_labels():
		if label.lower() not in known:
			error(form_path, f'nhãn "{label}" chưa có trong labels.yml')

for message in errors:
	print(f'❌ {message}')
print(f'{"✅ Không có lỗi" if not errors else f"❌ {len(errors)} lỗi"}.')
sys.exit(1 if errors else 0)
