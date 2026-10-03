"""Kiểm tra tính nhất quán của repository .github.

Chạy: python3 scripts/validate.py  (cần Python ≥ 3.11 — tomllib, datetime.UTC — và Ruby để đọc YAML;
cả hai có sẵn trên runner GitHub; trên máy dùng Python do mise cài, không dùng Python 3.9 của macOS).
"""

import ast
import hashlib
import importlib.util
import json
import re
import subprocess
import sys

try:
	import tomllib
except ModuleNotFoundError:
	sys.exit(
		f'Cần Python ≥ 3.11 (đang dùng {sys.version.split()[0]}) — chạy mise install, mở terminal có mise.'
	)
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
# security.txt: báo trước khi Expires hết hạn để kịp gia hạn và đăng lại lên website.
EXPIRY_NOTICE_DAYS = 30
errors = []
FORM_LABELS = []
# Đuôi tệp script ngoài Python ở bất kỳ đâu — phải ghi lý do không dùng Python (ADR 0009); trong scripts/ thì mọi
# tệp không phải Python (kể cả .js) đều phải ghi.
SCRIPT_SUFFIXES = ('.sh', '.bash', '.zsh', '.rb', '.pl', '.ps1')
NOT_PYTHON_REASON = 'Không viết bằng Python vì:'
# Tên trong mã Python (ADR 0010): hàm, tham số camelCase (setUp, tearDown của unittest cũng khớp); biến không
# dùng snake_case — camelCase, hằng số UPPER_CASE, hoặc PascalCase khi giữ một lớp.
FUNCTION_NAME = re.compile(r'_?[a-z][a-zA-Z0-9]*')
VARIABLE_NAME = re.compile(r'_?[A-Za-z][A-Za-z0-9]*|[A-Z][A-Z0-9_]*|_')


def loadScript(name):
	"""Nạp một script khác trong scripts/ (tên có dấu gạch ngang nên không import thường được)."""
	spec = importlib.util.spec_from_file_location(
		name.replace('-', '_'), ROOT / 'scripts' / f'{name}.py'
	)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


conventions = loadScript('conventions')
markdownLinks = loadScript('check-markdown-links')
toolVersions = loadScript('check-tool-versions')


def error(path, message):
	errors.append(f'{path.relative_to(ROOT)}: {message}')


# Ruby đọc YAML (Python không có sẵn thư viện YAML). Một lần gọi cho mọi tệp: mỗi lần khởi động Ruby mất
# khoảng 0,07 giây và một tệp có thể được nhiều kiểm tra đọc lại.
YAML_BATCH = (
	'out = {}; ARGV.each { |f| begin; out[f] = {"data" => YAML.load_file(f)}; '
	'rescue Exception => e; out[f] = {"error" => e.message}; end }; puts JSON.dump(out)'
)
yamlCache = {}
# Kết quả đọc theo nội dung tệp, giữ qua các lần runChecks() trong cùng tiến trình (bộ test chạy validate hàng
# trăm lần): tệp không đổi thì không gọi lại Ruby.
yamlResults = {}


def readYamlFiles(paths):
	"""Đọc nhiều tệp YAML trong một lần gọi Ruby; mỗi tệp trả {"data": …} hoặc {"error": …}."""
	keys = {str(path): hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths}
	missing = [str(path) for path in paths if keys[str(path)] not in yamlResults]
	if missing:
		result = subprocess.run(
			['ruby', '-ryaml', '-rjson', '-e', YAML_BATCH, *missing],
			capture_output=True,
			text=True,
			check=False,
		)
		if result.returncode != 0:
			return {str(path): {'error': result.stderr.strip()} for path in paths}
		for name, entry in json.loads(result.stdout).items():
			yamlResults[keys[name]] = entry
	# Bản sao: loadYaml đánh dấu "reported" trên từng mục của lần chạy.
	return {str(path): dict(yamlResults[keys[str(path)]]) for path in paths}


def loadYaml(path):
	"""Nội dung YAML của tệp (đọc mọi tệp YAML được git quản lý ở lần gọi đầu); lỗi chỉ báo một lần."""
	if not yamlCache:
		files = [file for file in trackedFiles() if file.suffix in ('.yml', '.yaml')]
		yamlCache.update(readYamlFiles(files))
	if str(path) not in yamlCache:
		yamlCache.update(readYamlFiles([path]))
	entry = yamlCache[str(path)]
	if 'error' in entry:
		if not entry.get('reported'):
			error(path, f'YAML không hợp lệ: {entry["error"]}')
			entry['reported'] = True
		return None
	return entry['data']


def trackedFiles():
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


def checkText(path):
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


def checkLinks(path, text):
	for message in markdownLinks.findBrokenLinks(path, text):
		error(path, message)


def checkAbsoluteLinks(path, text, reason='biểu mẫu dùng ở mọi repository'):
	"""Nội dung hiển thị ngoài repository (biểu mẫu ở repository khác, nội dung GitHub Release): liên kết tương
	đối sẽ trỏ sai chỗ."""
	for match in re.finditer(r'\]\(([^)\s]+)\)', text):
		if not re.match(r'(https?|mailto):', match.group(1)):
			error(path, f'liên kết "{match.group(1)}" phải là URL tuyệt đối ({reason})')


def checkSecurityMailto(path, text):
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


def checkForm(path, required=('name', 'description', 'body')):
	form = loadYaml(path)
	if form is None:
		return
	for key in required:
		if not form.get(key):
			error(path, f'thiếu khóa bắt buộc "{key}"')
	checkAbsoluteLinks(path, path.read_text(encoding='utf-8'))
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
		itemId = item.get('id')
		if itemId in ids:
			error(path, f'phần tử {index}: id "{itemId}" bị trùng')
		ids.add(itemId)
		if kind in ('dropdown', 'checkboxes') and not attributes.get('options'):
			error(path, f'phần tử {index}: {kind} thiếu options')


def checkWorkflow(path, text):
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
	# Kiểm tra luôn là tệp riêng trong scripts/, không viết trực tiếp trong YAML (ADR 0009): mỗi bước gọi một
	# lệnh. Workflow của repository này gọi scripts/ để chạy được y hệt tại máy (make check); workflow mẫu gọi
	# script của tổ chức (checkout vào .org/).
	for number, line in enumerate(text.split('\n'), start=1):
		if re.match(r'^\s*run:\s*[|>]', line):
			error(
				path,
				f'dòng {number}: lệnh nhiều dòng — tách thành script trong scripts/, mỗi bước gọi một lệnh (ADR 0009)',
			)
		if re.match(r'^\s*shell:\s*(python|node|pwsh|ruby|perl)', line) or re.search(
			r'^\s*run:.*\b(python3?|node|ruby|perl|bash|sh)\s+-(c|e)\b', line
		):
			error(
				path,
				f'dòng {number}: mã nhúng trong YAML — viết thành script trong scripts/ (ADR 0009)',
			)
	if not re.search(r'^concurrency:', text, re.MULTILINE):
		error(path, 'thiếu khai báo "concurrency" ở cấp workflow')
	for number, line in enumerate(text.split('\n'), start=1):
		if re.match(r'^\s+[a-z-]+: write\s*$', line):
			error(path, f'dòng {number}: quyền ghi cần chú thích lý do (# …)')
	workflow = loadYaml(path)
	top = (workflow or {}).get('permissions')
	if top == 'write-all' or (isinstance(top, dict) and 'write' in top.values()):
		error(path, 'quyền ghi chỉ cấp ở job cần dùng, không cấp ở cấp workflow')
	for name, job in ((workflow or {}).get('jobs') or {}).items():
		if 'timeout-minutes' not in job:
			error(path, f'job "{name}" thiếu timeout-minutes')


def checkWorkflowTemplate(path):
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


def checkToolVersions():
	"""Phiên bản công cụ chỉ ở mise.toml; Node.js chỉ ở .nvmrc (ADR 0008). Công cụ trong mise.toml (trừ Python, Node.js)
	khớp danh sách check-tool-versions.py theo dõi bản mới."""
	mise = (ROOT / 'mise.toml').read_text(encoding='utf-8') if (ROOT / 'mise.toml').exists() else ''
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
	pinned = re.compile(r'ruff==|pipx install ruff|actionlint@v|download-actionlint|shellcheck-v\d')
	# Không quét validate.py và test_*.py: các tệp này chứa chính các mẫu để so khớp.
	sources = [
		*(ROOT / '.github' / 'workflows').glob('*.yml'),
		*(ROOT / 'workflow-templates').glob('*.yml'),
		*(ROOT / '.devcontainer').glob('*.sh'),
		*(
			path
			for path in (ROOT / 'scripts').glob('*.py')
			if path.name != 'validate.py' and not path.name.startswith('test_')
		),
		ROOT / 'Makefile',
	]
	for path in sorted(path for path in sources if path.exists()):
		for number, line in enumerate(path.read_text(encoding='utf-8').split('\n'), start=1):
			if pinned.search(line):
				error(path, f'dòng {number}: phiên bản công cụ phải lấy từ mise.toml (ADR 0008)')


def checkFormatConfig():
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
	ruffPath = ROOT / 'ruff.toml'
	ruff = ruffPath.read_text(encoding='utf-8') if ruffPath.exists() else ''
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
			actual = (ruffConfig.get(key) or {}).get(sub) if sub else ruffConfig.get(key)
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
		text = path.read_text(encoding='utf-8') if path.exists() else ''
		return {
			line.strip() for line in text.split('\n') if line.strip() and not line.startswith('#')
		}

	for entry in sorted(entries('.prettierignore') & entries('.gitignore')):
		errors.append(f'.prettierignore: "{entry}" đã có trong .gitignore — Prettier 3 tự bỏ qua')
	# Quy tắc chung của tổ chức, áp dụng khi repository dùng ESLint.
	eslintPath = ROOT / 'eslint.config.js'
	if not eslintPath.exists():
		return
	eslint = eslintPath.read_text(encoding='utf-8')
	if "from 'eslint-config-prettier'" not in eslint:
		errors.append('eslint.config.js: phải dùng eslint-config-prettier để tắt quy tắc định dạng')
	if re.search(r"""['"]?\bindent['"]?\s*:""", eslint):
		errors.append('eslint.config.js: không bật quy tắc indent — định dạng do Prettier đảm nhận')


def checkEditorExtensions():
	"""Extension VS Code gợi ý tại máy (.vscode/extensions.json) và cài trong Dev Container phải giống nhau."""
	try:
		local = json.loads((ROOT / '.vscode' / 'extensions.json').read_text(encoding='utf-8'))
		container = json.loads(
			(ROOT / '.devcontainer' / 'devcontainer.json').read_text(encoding='utf-8')
		)
	except (OSError, json.JSONDecodeError):
		return
	wanted = set(local.get('recommendations') or [])
	installed = set(
		((container.get('customizations') or {}).get('vscode') or {}).get('extensions') or []
	)
	for name in sorted(wanted ^ installed):
		where = '.devcontainer/devcontainer.json' if name in wanted else '.vscode/extensions.json'
		errors.append(f'{where}: thiếu extension "{name}" — hai danh sách phải giống nhau')


def editorconfigSuffixes(editorconfig, setting):
	"""Đuôi file của mọi mục .editorconfig dạng [*.x] hoặc [*.{x,y}] có chứa `setting`."""
	suffixes = set()
	for header, body in re.findall(
		r'^\[\*\.\{?([^\]}]+)\}?\]\n((?:[^\[].*\n?)*)', editorconfig, re.MULTILINE
	):
		if re.search(rf'^{re.escape(setting)}$', body, re.MULTILINE):
			suffixes.update(f'.{name}' for name in header.split(','))
	return suffixes


def checkSuffixLists():
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
		found = editorconfigSuffixes(editorconfig, setting)
		for suffix in sorted(set(expected) ^ found):
			where = 'thiếu' if suffix in expected else 'thừa'
			errors.append(
				f'.editorconfig: {where} {suffix} trong mục "{setting}" so với validate.py'
			)
	spaces = editorconfigSuffixes(editorconfig, 'indent_style = space') - set(TWO_SPACE_SUFFIXES)
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


def contributingSection(text, heading):
	"""Nội dung một mục `## …` của CONTRIBUTING.md, tới mục kế tiếp."""
	match = re.search(
		rf'^## .*{re.escape(heading)}\n(.*?)(?=^## |\Z)', text, re.MULTILINE | re.DOTALL
	)
	return match.group(1) if match else ''


def checkConventions():
	"""Loại commit và tiền tố branch trong CONTRIBUTING.md phải khớp scripts/conventions.py — script mà
	workflow branch-name.yml, pr-title.yml (của repository này và workflow mẫu) gọi."""
	contributing = (ROOT / 'CONTRIBUTING.md').read_text(encoding='utf-8')
	types = set(
		re.findall(
			r'^\| `([a-z]+)` ', contributingSection(contributing, 'QUY ƯỚC COMMIT'), re.MULTILINE
		)
	)
	prefixes = set(
		re.findall(
			r'^\| `([a-z]+)/` ',
			contributingSection(contributing, 'QUY ƯỚC ĐẶT TÊN BRANCH'),
			re.MULTILINE,
		)
	)
	# Mỗi tiền tố branch có luật head-branch trong labeler.yml của repository này và bản mẫu (tự gắn nhãn loại
	# cho Pull Request).
	for labeler in (
		ROOT / '.github' / 'labeler.yml',
		ROOT / 'repository-templates' / 'labeler.yml',
	):
		if not labeler.exists():
			continue
		covered = set(re.findall(r"'\^([a-z]+)/'", labeler.read_text(encoding='utf-8')))
		for prefix in sorted(prefixes - covered):
			errors.append(
				f'{labeler.relative_to(ROOT)}: thiếu luật head-branch cho tiền tố "{prefix}/" của CONTRIBUTING.md'
			)
	# Mẫu commit (.gitmessage, bật bằng make hooks) liệt kê đúng các loại commit.
	message = ROOT / '.gitmessage'
	listed = (
		re.search(r'^# Loại: (.+)$', message.read_text(encoding='utf-8'), re.MULTILINE)
		if message.exists()
		else None
	)
	for word in sorted(types ^ set(re.split(r',\s*', listed.group(1).strip()) if listed else ())):
		where = 'thiếu' if word in types else 'thừa'
		errors.append(f'.gitmessage: dòng "# Loại:" {where} "{word}" so với CONTRIBUTING.md')
	for name, expected, found in (
		('COMMIT_TYPES', types, set(conventions.COMMIT_TYPES)),
		('BRANCH_PREFIXES', prefixes, set(conventions.BRANCH_PREFIXES)),
	):
		for word in sorted(expected ^ found):
			where = 'thiếu' if word in expected else 'thừa'
			errors.append(f'scripts/conventions.py: {name} {where} "{word}" so với CONTRIBUTING.md')


def nameProblems(text):
	"""(dòng, loại, tên) của mọi tên sai quy ước trong mã Python; None khi mã không hợp lệ."""
	try:
		tree = ast.parse(text)
	except SyntaxError:
		return None
	problems = []
	for node in ast.walk(tree):
		if isinstance(
			node, (ast.FunctionDef, ast.AsyncFunctionDef)
		) and not FUNCTION_NAME.fullmatch(node.name):
			problems.append((node.lineno, 'tên hàm', node.name))
		if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
			arguments = node.args
			for argument in (
				*arguments.posonlyargs,
				*arguments.args,
				*arguments.kwonlyargs,
				arguments.vararg,
				arguments.kwarg,
			):
				if argument and not FUNCTION_NAME.fullmatch(argument.arg):
					problems.append((argument.lineno, 'tham số', argument.arg))
		elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
			if not VARIABLE_NAME.fullmatch(node.id):
				problems.append((node.lineno, 'tên biến', node.id))
		elif isinstance(node, ast.ExceptHandler) and node.name:
			if not VARIABLE_NAME.fullmatch(node.name):
				problems.append((node.lineno, 'tên biến', node.name))
	return problems


# Kết quả theo nội dung tệp, giữ qua các lần runChecks() trong cùng tiến trình như yamlResults.
nameResults = {}


def checkNames(path, text):
	"""Tên hàm, tham số viết camelCase tiếng Anh; biến không dùng snake_case (ADR 0010)."""
	key = hashlib.sha256(text.encode('utf-8')).hexdigest()
	if key not in nameResults:
		nameResults[key] = nameProblems(text)
	problems = nameResults[key]
	if problems is None:
		error(path, 'Python không hợp lệ (lỗi cú pháp)')
		return
	for line, kind, name in problems:
		error(path, f'dòng {line}: {kind} "{name}" phải viết camelCase tiếng Anh (ADR 0010)')


def checkMaintainers():
	"""Người quản trị trong MAINTAINERS.md khớp MAINTAINERS của scripts/orgsetup/teams.py (org-setup.py team thêm
	họ vào mọi team)."""
	listing, source = ROOT / 'MAINTAINERS.md', ROOT / 'scripts' / 'orgsetup' / 'teams.py'
	if not listing.exists() or not source.exists():
		return
	current = contributingSection(listing.read_text(encoding='utf-8'), 'NGƯỜI QUẢN TRỊ HIỆN TẠI')
	documented = set(re.findall(r'\[@([A-Za-z0-9-]+)\]\(https://github\.com/\1\)', current))
	match = re.search(
		r'^MAINTAINERS = (\(.*?\))$', source.read_text(encoding='utf-8'), re.MULTILINE
	)
	configured = set(ast.literal_eval(match.group(1))) if match else set()
	for name in sorted(documented ^ configured):
		where = listing if name in configured else source
		error(
			where,
			f'người quản trị "{name}" chỉ có ở một trong MAINTAINERS.md và MAINTAINERS của teams.py',
		)


def checkRulesets():
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
		for job in ((loadYaml(workflow) or {}).get('jobs') or {}).values():
			jobs.add(job.get('name'))
	# Mọi ruleset nhánh, tag (cấp repository, cấp tổ chức) bắt buộc commit có chữ ký (ADR 0006); push
	# ruleset không nhận quy tắc này (ADR 0007).
	for rulesetPath in sorted((ROOT / 'rulesets').glob('*.json')):
		try:
			data = json.loads(rulesetPath.read_text(encoding='utf-8'))
		except json.JSONDecodeError:
			continue
		if data.get('target') == 'push':
			continue
		if 'required_signatures' not in {r.get('type') for r in data.get('rules', [])}:
			error(
				rulesetPath, 'ruleset phải có quy tắc required_signatures (Require signed commits)'
			)
	tagPath = ROOT / 'rulesets' / 'protect-release-tags.json'
	if not tagPath.exists():
		errors.append('thiếu tệp bắt buộc rulesets/protect-release-tags.json')
	else:
		try:
			tags = json.loads(tagPath.read_text(encoding='utf-8'))
		except json.JSONDecodeError:
			tags = {}
		include = ((tags.get('conditions') or {}).get('ref_name') or {}).get('include') or []
		if tags.get('name') != 'Protect Release Tags' or tags.get('target') != 'tag':
			error(tagPath, 'ruleset phải tên "Protect Release Tags", target "tag" (ADR 0005)')
		if 'refs/tags/v*' not in include:
			error(tagPath, 'ruleset phải áp dụng cho refs/tags/v* (tag phát hành)')
		if not {'creation', 'update', 'deletion'} <= {
			rule.get('type') for rule in tags.get('rules') or []
		}:
			error(tagPath, 'ruleset phải chặn creation, update, deletion của tag phát hành')
	orgPath = ROOT / 'rulesets' / 'org-protect-main.json'
	if not orgPath.exists():
		errors.append('thiếu tệp bắt buộc rulesets/org-protect-main.json')
	else:
		try:
			org = json.loads(orgPath.read_text(encoding='utf-8'))
		except json.JSONDecodeError:
			org = {}
		repositories = ((org.get('conditions') or {}).get('repository_name') or {}).get(
			'include'
		) or []
		if org.get('name') != 'Protect Main (Organization)' or '~ALL' not in repositories:
			error(
				orgPath,
				'ruleset phải tên "Protect Main (Organization)" và nhắm mọi repository (~ALL)',
			)
	# Import ruleset cấp tổ chức báo "contains an invalid actor" với actor loại User.
	for orgFile in sorted((ROOT / 'rulesets').glob('org-*.json')):
		if re.search(r'"(actor_type|type)":\s*"User"', orgFile.read_text(encoding='utf-8')):
			error(
				orgFile,
				'ruleset cấp tổ chức không dùng actor loại User — GitHub từ chối khi import',
			)
	orgTagPath = ROOT / 'rulesets' / 'org-protect-release-tags.json'
	if not orgTagPath.exists():
		errors.append('thiếu tệp bắt buộc rulesets/org-protect-release-tags.json')
	else:
		try:
			orgTags = json.loads(orgTagPath.read_text(encoding='utf-8'))
		except json.JSONDecodeError:
			orgTags = {}
		conditions = orgTags.get('conditions') or {}
		if (
			orgTags.get('name') != 'Protect Release Tags (Organization)'
			or '~ALL' not in (conditions.get('repository_name') or {}).get('include', [])
			or 'refs/tags/v*' not in (conditions.get('ref_name') or {}).get('include', [])
		):
			error(
				orgTagPath,
				'ruleset phải tên "Protect Release Tags (Organization)", nhắm ~ALL repository và refs/tags/v*',
			)
	pushPath = ROOT / 'rulesets' / 'org-protect-pushes.json'
	if not pushPath.exists():
		errors.append('thiếu tệp bắt buộc rulesets/org-protect-pushes.json')
	else:
		try:
			pushes = json.loads(pushPath.read_text(encoding='utf-8'))
		except json.JSONDecodeError:
			pushes = {}
		conditions = pushes.get('conditions') or {}
		if (
			pushes.get('name') != 'Protect Pushes (Organization)'
			or pushes.get('target') != 'push'
			or '~ALL' not in (conditions.get('repository_name') or {}).get('include', [])
		):
			error(
				pushPath,
				'ruleset phải tên "Protect Pushes (Organization)", target "push" và nhắm ~ALL repository (ADR 0007)',
			)
	for rule in ruleset.get('rules', []):
		for check in (rule.get('parameters') or {}).get('required_status_checks', []):
			if check.get('context') not in jobs:
				error(
					path,
					f'kiểm tra bắt buộc "{check.get("context")}" không trùng tên job nào trong .github/workflows',
				)


def checkAdrIndex():
	"""Bảng trong docs/adr/README.md phải liệt kê mọi ADR, cùng ngày và cùng trạng thái với từng tệp."""
	folder = ROOT / 'docs' / 'adr'
	indexPath = folder / 'README.md'
	if not indexPath.exists():
		return
	rows = {
		number: (status.strip(), date.strip())
		for number, status, date in re.findall(
			r'^\| \[(\d{4})\]\([^)]+\) +\|[^|]+\|([^|]+)\|([^|]+)\|$',
			indexPath.read_text(encoding='utf-8'),
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
			error(indexPath, f'bảng thiếu ADR {number}')
			continue
		rowStatus, rowDate = rows[number]
		if rowDate != date.group(1).strip():
			error(indexPath, f'ADR {number}: ngày "{rowDate}" khác tệp ADR ({date.group(1)})')
		superseded = 'thay thế' in status.group(1).lower()
		if superseded != ('thay thế' in rowStatus.lower()) or (
			superseded
			and set(re.findall(r'\b\d{4}\b', rowStatus))
			!= set(re.findall(r'\b\d{4}\b', status.group(1)))
		):
			error(
				indexPath,
				f'ADR {number}: trạng thái "{rowStatus}" khác tệp ADR ({status.group(1)})',
			)


def checkSpaceOnly(path, text):
	"""Ngôn ngữ bắt buộc dấu cách (4 hoặc 2 mỗi cấp theo formatter chính thức): không dùng tab."""
	width = 2 if path.suffix in TWO_SPACE_SUFFIXES else 4
	inFence = False
	for number, line in enumerate(text.split('\n'), start=1):
		if path.suffix == '.md' and line.lstrip().startswith('```'):
			inFence = not inFence
			continue
		if not inFence and re.match(r'^ *\t', line):
			error(
				path,
				f'dòng {number}: {path.suffix} phải thụt lề bằng {width} dấu cách, không dùng tab',
			)
			return


def checkTabOnly(path, text):
	"""Mọi tệp mặc định dùng tab (theo .editorconfig): thụt lề chỉ bằng tab, không trộn dấu cách."""
	for number, line in enumerate(text.split('\n'), start=1):
		indent = re.match(r'^[ \t]*', line).group(0)
		# Dòng tiếp nối chú thích khối (/** … */) do Prettier sinh ra: tab rồi " *".
		if re.match(r'^\t* \*', line):
			continue
		if ' ' in indent and line.strip():
			error(path, f'dòng {number}: thụt lề phải dùng tab theo .editorconfig')
			return


def checkHeadings(path, text):
	"""Phong cách thống nhất của repository: mọi tiêu đề Markdown viết hoa."""
	inFence = False
	for number, line in enumerate(text.split('\n'), start=1):
		if line.lstrip().startswith('```'):
			inFence = not inFence
		heading = re.match(r'#{1,6} (.+)', line)
		title = re.sub(r'`[^`]*`|\[[^\]]*\]\([^)]*\)', '', heading.group(1)) if heading else ''
		if heading and not inFence and title != title.upper():
			error(path, f'dòng {number}: tiêu đề phải viết hoa — "{heading.group(1)}"')


def checkLabels(path):
	labels = loadYaml(path)
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


def checkDependabotCooldown():
	"""Mọi mục Dependabot chờ ≥ 7 ngày sau khi phát hành (chống gói độc vừa phát hành; không ảnh hưởng cập nhật bảo mật)."""
	for path in (
		ROOT / '.github' / 'dependabot.yml',
		ROOT / 'repository-templates' / 'dependabot.yml',
	):
		for update in ((loadYaml(path) if path.exists() else None) or {}).get('updates') or []:
			days = (update.get('cooldown') or {}).get('default-days')
			if not isinstance(days, int) or days < 7:
				error(path, f'{update.get("package-ecosystem")}: cần cooldown.default-days ≥ 7')


def configLabels():
	"""Nhãn dùng trong dependabot.yml, release.yml (bản mẫu), labeler.yml và workflow stale."""
	found = []
	for path in (
		ROOT / '.github' / 'dependabot.yml',
		ROOT / 'repository-templates' / 'dependabot.yml',
	):
		for update in ((loadYaml(path) if path.exists() else None) or {}).get('updates') or []:
			found += [(path, label) for label in update.get('labels') or []]
	for path in (ROOT / 'repository-templates' / 'release.yml',):
		changelog = ((loadYaml(path) if path.exists() else None) or {}).get('changelog') or {}
		found += [(path, label) for label in (changelog.get('exclude') or {}).get('labels') or []]
		for category in changelog.get('categories') or []:
			found += [(path, label) for label in category.get('labels') or [] if label != '*']
	for path in (ROOT / '.github' / 'labeler.yml', ROOT / 'repository-templates' / 'labeler.yml'):
		found += [(path, label) for label in ((loadYaml(path) if path.exists() else None) or {})]
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


def checkEmails(path, text):
	for email in set(
		re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}', text)
	):
		if email.lower() != COMPANY_EMAIL:
			error(path, f'email "{email}" khác email chung của công ty ({COMPANY_EMAIL})')


def checkSecurityTxt(path, text):
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
	elif remaining < EXPIRY_NOTICE_DAYS:
		error(
			path,
			f'Expires còn {remaining} ngày — gia hạn (tối đa 1 năm) rồi đăng lại tệp lên website',
		)
	elif remaining > 366:
		error(path, 'Expires vượt quá 1 năm (RFC 9116 khuyến nghị tối đa 1 năm)')


def checkChangelog(path, text):
	versions = re.findall(r'^## \[([^\]]+)\]', text, re.MULTILINE)
	if not versions or versions[0] != 'CHƯA PHÁT HÀNH':
		error(path, 'mục đầu tiên phải là "## [CHƯA PHÁT HÀNH]"')
	if len(versions) != len(set(versions)):
		error(path, 'có phiên bản bị lặp')
	checkAbsoluteLinks(path, text, 'mỗi mục thành nội dung GitHub Release')


def checkScriptLanguage(path):
	"""Script không viết bằng Python phải nêu lý do ngôn ngữ khác xử lý tốt hơn trong 10 dòng đầu."""
	head = '\n'.join(path.read_text(encoding='utf-8', errors='replace').split('\n')[:10])
	if not re.search(rf'{re.escape(NOT_PYTHON_REASON)}\s*\S', head):
		error(
			path,
			f'script không viết bằng Python — thêm dòng "{NOT_PYTHON_REASON} <lý do>" ở đầu tệp, '
			'nêu vì sao ngôn ngữ này xử lý tốt hơn; nếu không, viết bằng Python (ADR 0009)',
		)


def checkShell(path):
	data = path.read_bytes()
	if b'\r' in data:
		error(path, 'shell script phải dùng LF')
	if not data.startswith(b'#!'):
		error(path, 'shell script thiếu shebang')


def checkIssueConfig(path):
	config = loadYaml(path)
	if config is None:
		return
	for link in config.get('contact_links') or []:
		for key in ('name', 'url', 'about'):
			if not link.get(key):
				error(path, f'contact_links thiếu "{key}"')


def checkFile(file):
	"""Kiểm tra từng tệp: vị trí, ngôn ngữ script, định dạng, mã hóa, nội dung theo loại tệp."""
	# GitHub chỉ nhận biểu mẫu Issue, Discussion và FUNDING.yml trong thư mục .github/.
	if (
		file.parent.name in ('ISSUE_TEMPLATE', 'DISCUSSION_TEMPLATE')
		and file.parent.parent != ROOT / '.github'
	) or (file.name == 'FUNDING.yml' and file.parent != ROOT / '.github'):
		error(file, 'phải nằm trong thư mục .github/ để GitHub nhận diện')
	# Script ưu tiên Python; ngôn ngữ khác chỉ khi xử lý việc đó tốt hơn, ghi lý do ở đầu tệp (ADR 0009).
	if (file.parent == ROOT / 'scripts' and file.suffix != '.py') or file.suffix in SCRIPT_SUFFIXES:
		checkScriptLanguage(file)
	if file.suffix == '.sh':
		checkShell(file)
	if file.suffix == '.py':
		checkNames(file, file.read_text(encoding='utf-8'))
	if file.suffix in SPACE_SUFFIXES + TWO_SPACE_SUFFIXES:
		checkSpaceOnly(file, file.read_text(encoding='utf-8'))
	if file.suffix in BINARY_SUFFIXES:
		return
	content = checkText(file)
	if content is None:
		return
	if not file.name.endswith(SPACE_SUFFIXES + TWO_SPACE_SUFFIXES + KEEP_TRAILING_SPACE_SUFFIXES):
		checkTabOnly(file, content)
	# .mailmap ánh xạ email tác giả commit (kể cả địa chỉ noreply của GitHub), không phải email liên hệ.
	if file.name != '.mailmap':
		checkEmails(file, content)
	if file.name == 'security.txt':
		checkSecurityTxt(file, content)
	if file.name == 'CHANGELOG.md':
		checkChangelog(file, content)
	if (
		file.suffix in ('.sh', '.svg', '.txt', '.js', '.toml')
		or file.suffix == ''
		or file.name.startswith('.')
	):
		return
	if file.suffix == '.md':
		checkLinks(file, content)
		checkHeadings(file, content)
	if file.name == 'SECURITY.md':
		checkSecurityMailto(file, content)
	if file.name == 'PULL_REQUEST_TEMPLATE.md':
		checkAbsoluteLinks(file, content)
	if file.parent.name == 'ISSUE_TEMPLATE' and file.suffix in ('.yml', '.yaml'):
		if file.stem == 'config':
			checkIssueConfig(file)
		else:
			checkForm(file)
	elif file.parent.name == 'DISCUSSION_TEMPLATE' and file.suffix in ('.yml', '.yaml'):
		checkForm(file, required=('body',))
	elif file.suffix in ('.yml', '.yaml') and (
		file.parent.name == 'workflow-templates'
		or file.parent.parts[-2:] == ('.github', 'workflows')
	):
		checkWorkflow(file, content)
		if file.parent.name == 'workflow-templates':
			checkWorkflowTemplate(file)
	elif file.suffix in ('.yml', '.yaml') and file != ROOT / 'labels.yml':
		loadYaml(file)
	elif file.suffix == '.json':
		try:
			json.loads(content)
		except json.JSONDecodeError as exc:
			error(file, f'JSON không hợp lệ: {exc}')


def checkRequiredFiles():
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


def checkLabelUsage():
	"""Nhãn dùng trong biểu mẫu và cấu hình phải có trong labels.yml."""
	labelFile = ROOT / 'labels.yml'
	if not labelFile.exists():
		return
	known = checkLabels(labelFile)
	for formPath, label in FORM_LABELS + configLabels():
		if label.lower() not in known:
			error(formPath, f'nhãn "{label}" chưa có trong labels.yml')


def runChecks():
	"""Chạy mọi kiểm tra, trả danh sách lỗi."""
	errors.clear()
	FORM_LABELS.clear()
	yamlCache.clear()
	for file in trackedFiles():
		checkFile(file)
	for check in (
		checkFormatConfig,
		checkLintIgnoreConfig,
		checkDependabotCooldown,
		checkToolVersions,
		checkSuffixLists,
		checkEditorExtensions,
		checkConventions,
		checkRulesets,
		checkMaintainers,
		checkAdrIndex,
		checkRequiredFiles,
		checkLabelUsage,
	):
		check()
	return list(errors)


def main():
	found = runChecks()
	for message in found:
		print(f'❌ {message}')
	print(f'{"✅ Không có lỗi" if not found else f"❌ {len(found)} lỗi"}.')
	return 1 if found else 0


if __name__ == '__main__':
	sys.exit(main())
