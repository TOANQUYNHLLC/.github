"""Kiểm tra tính nhất quán của repository .github.

Chạy: python3 scripts/validate.py  (cần Python ≥ 3.11 — tomllib, datetime.UTC — và Ruby để đọc YAML;
cả hai có sẵn trên runner GitHub; trên máy dùng Python do mise cài, không dùng Python 3.9 của macOS).
"""

import ast
import builtins
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

from markdown import withoutCodeBlocks
from orgsetup.labels import inspectLabels

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
# Tag phát hành: Stable.vYYYY.MM.DDXXXX, Beta.vYYYY.MM.DDXXXX (ADR 0014) và tag vYYYY.MM.Stable đã phát hành.
RELEASE_TAG = re.compile(
	r'(Stable|Beta)\.v[0-9]{4}\.(0[1-9]|1[0-2])\.[0-9]{6}|v[0-9]{4}\.(0[1-9]|1[0-2])\.Stable'
)
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')
# Nhãn mặc định GitHub tạo cho repository mới — bộ nhãn chuẩn phải có đủ để không mất nhãn quen thuộc.
GITHUB_DEFAULT_LABELS = (
	'bug',
	'documentation',
	'duplicate',
	'enhancement',
	'good first issue',
	'help wanted',
	'invalid',
	'question',
	'wontfix',
)
# Mục bắt buộc của mỗi ADR, theo thứ tự (docs/adr/template.md).
ADR_SECTIONS = ('BỐI CẢNH', 'QUYẾT ĐỊNH', 'PHƯƠNG ÁN ĐÃ CÂN NHẮC', 'HỆ QUẢ')
# Đường dẫn trong tài liệu bắt đầu bằng các thư mục này phải có thật trong repository.
DOC_PATH = re.compile(
	r'`((?:scripts|docs|rulesets|workflow-templates|repository-templates|\.github/workflows)/[^`\s*<>…]*)`'
)
# security.txt: báo trước khi Expires hết hạn để kịp gia hạn và đăng lại lên website.
EXPIRY_NOTICE_DAYS = 30
errors = []
FORM_LABELS = []
# Đuôi tệp script ngoài Python ở bất kỳ đâu — phải ghi lý do không dùng Python (ADR 0009); trong scripts/ thì mọi
# tệp không phải Python (kể cả .js) đều phải ghi.
SCRIPT_SUFFIXES = ('.sh', '.bash', '.zsh', '.rb', '.pl', '.ps1')
NOT_PYTHON_REASON = 'Không viết bằng Python vì:'
# Tên tự đặt trong mã Python (ADR 0010): hàm, tham số camelCase (setUp, tearDown của unittest cũng khớp);
# biến không dùng snake_case — camelCase, hằng số UPPER_CASE, hoặc PascalCase khi giữ một lớp.
FUNCTION_NAME = re.compile(r'_?[a-z][a-zA-Z0-9]*')
VARIABLE_NAME = re.compile(r'_?[A-Za-z][A-Za-z0-9]*|[A-Z][A-Z0-9_]*|_')
# Tên do Python quy định (__init__, __enter__, __all__…) — không phải tên tự đặt.
DUNDER_NAME = re.compile(r'__\w+__')
# Thư viện gọi phương thức theo mẫu tên thay vì định nghĩa sẵn trên lớp cha: lớp con của các lớp này đặt tên
# theo mẫu là tên thư viện quy định (http.server gọi do_GET cho yêu cầu GET; urllib gọi http_open…).
LIBRARY_NAME_PATTERNS = {
	'http.server.BaseHTTPRequestHandler': re.compile(r'do_[A-Z]+'),
	'urllib.request.BaseHandler': re.compile(r'[a-z]+_(open|request|response)|http_error_\d+'),
}


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
	'out = {}; ARGV.each { |f| begin; data = YAML.safe_load(File.read(f), aliases: true, filename: f); '
	'JSON.dump(data); out[f] = {"data" => data}; '
	'rescue StandardError, SystemStackError => e; out[f] = {"error" => e.message}; end }; puts JSON.dump(out)'
)
yamlCache = {}
jsonCache = {}
# Danh sách tệp và nội dung tệp của lượt runChecks() đang chạy (xóa ở đầu mỗi lượt).
trackedCache = []
bytesCache = {}
textCache = {}
anchorsCache = {}
# Kết quả đọc theo nội dung tệp, giữ qua các lần runChecks() trong cùng tiến trình (bộ test chạy validate hàng
# trăm lần): tệp không đổi thì không gọi lại Ruby.
yamlResults = {}


def readYamlFiles(paths):
	"""Đọc nhiều tệp YAML trong một lần gọi Ruby; mỗi tệp trả {"data": …} hoặc {"error": …}."""
	keys = {str(path): hashlib.sha256(readBytes(path)).hexdigest() for path in paths}
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


def loadYaml(path, expectedType=None):
	"""Đọc YAML theo lô, lỗi phân tích chỉ báo một lần; kiểm tra kiểu gốc nếu người gọi yêu cầu."""
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
	data = entry['data']
	if expectedType is not None and not isinstance(data, expectedType):
		error(path, f'cấu trúc YAML phải là {"object" if expectedType is dict else "danh sách"}')
		return None
	return data


def trackedFiles():
	"""File git quản lý hoặc sắp được thêm (bỏ qua mọi thứ trong .gitignore, tệp đã xóa trên đĩa); đọc một lần
	mỗi lượt runChecks()."""
	if not trackedCache:
		output = subprocess.run(
			['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
			cwd=ROOT,
			capture_output=True,
			check=True,
		).stdout.decode('utf-8')
		names = sorted(set(filter(None, output.split('\0'))))
		trackedCache.extend(ROOT / name for name in names if (ROOT / name).is_file())
	return trackedCache


def readBytes(path):
	"""Nội dung tệp dạng byte, đọc từ đĩa một lần mỗi lượt runChecks() — nhiều luật cùng đọc một tệp."""
	key = str(path)
	if key not in bytesCache:
		bytesCache[key] = Path(path).read_bytes()
	return bytesCache[key]


def decodeText(data, errors='strict'):
	"""Giải mã UTF-8 và đổi mọi kiểu xuống dòng thành \n — giống Path.read_text()."""
	return data.decode('utf-8', errors).replace('\r\n', '\n').replace('\r', '\n')


def readText(path):
	"""Giải mã một lần mỗi lượt runChecks(); checkText báo lỗi UTF-8, các đối chiếu vẫn đọc được phần còn lại."""
	key = str(path)
	if key not in textCache:
		textCache[key] = decodeText(readBytes(path), errors='replace')
	return textCache[key]


def readJsonObject(path):
	"""Cấu hình JSON phải là object; đọc một lần mỗi lượt và vẫn báo lỗi cú pháp cho người gọi."""
	key = str(path)
	if key not in jsonCache:
		data = json.loads(readText(path))
		if not isinstance(data, dict):
			error(path, 'cấu trúc JSON phải là object')
			data = {}
		jsonCache[key] = data
	return jsonCache[key]


def configField(path, data, key, expectedType):
	"""Đọc trường tùy chọn; sai kiểu thì báo tại tệp và trả giá trị rỗng để các luật khác vẫn chạy."""
	value = data.get(key)
	if value is None:
		return expectedType()
	if not isinstance(value, expectedType):
		kind = {dict: 'object', list: 'danh sách', str: 'chuỗi'}[expectedType]
		error(path, f'{key}: phải là {kind}')
		return expectedType()
	return value


def configItems(path, data, key, itemType=dict):
	"""Danh sách chỉ giữ phần tử đúng kiểu, không làm mất lỗi ở phần tử hoặc tệp kế tiếp."""
	items = configField(path, data, key, list)
	valid = []
	for index, item in enumerate(items, start=1):
		if isinstance(item, itemType):
			valid.append(item)
		else:
			kind = 'object' if itemType is dict else 'chuỗi'
			error(path, f'{key}[{index}]: phải là {kind}')
	return valid


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


# Dòng có nội dung mà thụt lề chứa dấu cách; bỏ dòng tiếp nối chú thích khối (/** … */) do Prettier sinh ra:
# tab rồi " *".
MIXED_INDENT = re.compile(r'^(?!\t* \*)\t* [ \t]*\S', re.MULTILINE)
# Khoảng trắng cuối dòng (trước \r của CRLF nếu có).
TRAILING_SPACE = re.compile(r'[ \t]\r*$', re.MULTILINE)


def lineNumber(text, offset):
	return text.count('\n', 0, offset) + 1


def checkText(path):
	data = readBytes(path)
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
	match = TRAILING_SPACE.search(text)
	if match:
		error(path, f'dòng {lineNumber(text, match.start())}: có khoảng trắng cuối dòng')
	return text


def checkLinks(path, text):
	for message in markdownLinks.findBrokenLinks(path, text, anchorsCache):
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
	form = loadYaml(path, dict)
	if form is None:
		return
	for key in required:
		if not form.get(key):
			error(path, f'thiếu khóa bắt buộc "{key}"')
	checkAbsoluteLinks(path, readText(path))
	if path.parent.name == 'DISCUSSION_TEMPLATE':
		for key in sorted(set(form) - DISCUSSION_FORM_KEYS):
			error(path, f'biểu mẫu Discussion không hỗ trợ khóa "{key}"')
	if path.parent.name == 'ISSUE_TEMPLATE':
		for key in sorted(set(form) - ISSUE_FORM_KEYS):
			error(path, f'khóa "{key}" không được GitHub chấp nhận trong biểu mẫu Issue')
	FORM_LABELS.extend((path, label) for label in configItems(path, form, 'labels', str))
	ids = set()
	for index, item in enumerate(configItems(path, form, 'body'), start=1):
		kind = item.get('type')
		attributes = configField(path, item, 'attributes', dict)
		if not isinstance(kind, str) or kind not in FORM_TYPES:
			error(path, f'phần tử {index}: type "{kind}" không hợp lệ')
			continue
		if kind == 'markdown':
			if not attributes.get('value'):
				error(path, f'phần tử {index}: markdown thiếu value')
			continue
		label = configField(path, attributes, 'label', str)
		if not label:
			error(path, f'phần tử {index}: thiếu label')
		elif label != label.upper():
			error(path, f'phần tử {index}: tiêu đề trường "{attributes["label"]}" phải viết hoa')
		itemId = configField(path, item, 'id', str)
		if itemId in ids:
			error(path, f'phần tử {index}: id "{itemId}" bị trùng')
		ids.add(itemId)
		if kind in ('dropdown', 'checkboxes') and not attributes.get('options'):
			error(path, f'phần tử {index}: {kind} thiếu options')


def workflowJobs(path):
	"""Các job có cấu trúc hợp lệ; dùng chung khi kiểm tra workflow và đối chiếu ruleset."""
	workflow = loadYaml(path, dict)
	if workflow is None:
		return {}
	jobs = workflow.get('jobs')
	if not isinstance(jobs, dict):
		error(path, 'cấu trúc jobs phải là object')
		return {}
	valid = {}
	for name, job in jobs.items():
		if not isinstance(job, dict):
			error(path, f'cấu trúc job "{name}" phải là object')
		else:
			valid[name] = job
	return valid


def checkActionRef(path, action, location):
	"""Action bên ngoài phải ghim SHA đầy đủ; kiểm tra giá trị YAML, kể cả khóa và giá trị có dấu nháy."""
	if not isinstance(action, str):
		error(path, f'cấu trúc {location}.uses phải là chuỗi')
		return
	if action.startswith(('./', 'docker://')):
		return
	ref = action.rsplit('@', 1)
	if len(ref) != 2 or not re.fullmatch(r'[0-9a-f]{40}', ref[1]):
		error(path, f'{location}: action "{action}" phải ghim theo commit SHA đầy đủ')


def checkWorkflowStep(path, step, location):
	"""Các quy tắc lệnh áp dụng cho giá trị YAML thực tế, không tính nội dung chú thích."""
	if not isinstance(step, dict):
		error(path, f'cấu trúc {location} phải là object')
		return
	if 'uses' in step:
		checkActionRef(path, step['uses'], location)
	if 'run' not in step:
		return
	run = step['run']
	if not isinstance(run, str):
		error(path, f'cấu trúc {location}.run phải là chuỗi')
		return
	if '\n' in run.strip():
		error(path, f'{location}: lệnh nhiều dòng — tách thành script trong scripts/ (ADR 0009)')
	if '${{' in run:
		error(
			path,
			f'{location}: không viết ${{{{ … }}}} trong run: — truyền qua env: rồi dùng "$TÊN_BIẾN"',
		)
	shell = step.get('shell', '')
	if not isinstance(shell, str):
		error(path, f'cấu trúc {location}.shell phải là chuỗi')
		return
	if re.match(r'(python|node|pwsh|ruby|perl)', shell) or re.search(
		r'\b(python3?|node|ruby|perl|bash|sh)\s+-(c|e)\b', run
	):
		error(
			path, f'{location}: mã nhúng trong YAML — viết thành script trong scripts/ (ADR 0009)'
		)


def checkWorkflow(path, text):
	"""Đọc cấu trúc YAML để kiểm tra action, lệnh, quyền và job; giữ kiểm tra cú pháp khối và chú thích."""
	workflow = loadYaml(path, dict)
	if workflow is None:
		return
	if 'permissions' not in workflow:
		error(path, 'thiếu khai báo "permissions" ở cấp workflow')
	if path.parent.parts[-2:] == ('.github', 'workflows') and '$default-branch' in text:
		error(
			path, '$default-branch chỉ dùng trong workflow-templates/ — ghi tên nhánh thật (main)'
		)
	# Cú pháp khối bị cấm dù chỉ chứa một lệnh; giữ số dòng. Giá trị đã giải mã do checkWorkflowStep kiểm tra.
	for number, line in enumerate(text.split('\n'), start=1):
		if re.match(r"^\s*(?:-\s+)?[\"']?run[\"']?:\s*[|>]", line):
			error(
				path,
				f'dòng {number}: lệnh nhiều dòng — tách thành script trong scripts/, mỗi bước gọi một lệnh (ADR 0009)',
			)
		if re.match(r'^\s+[a-z-]+: write\s*$', line):
			error(path, f'dòng {number}: quyền ghi cần chú thích lý do (# …)')
	if 'concurrency' not in workflow:
		error(path, 'thiếu khai báo "concurrency" ở cấp workflow')
	top = workflow.get('permissions')
	if top == 'write-all' or (isinstance(top, dict) and 'write' in top.values()):
		error(path, 'quyền ghi chỉ cấp ở job cần dùng, không cấp ở cấp workflow')
	for name, job in workflowJobs(path).items():
		if 'timeout-minutes' not in job:
			error(path, f'job "{name}" thiếu timeout-minutes')
		if 'uses' in job:
			checkActionRef(path, job['uses'], f'job "{name}"')
		steps = job.get('steps', [])
		if not isinstance(steps, list):
			error(path, f'cấu trúc job "{name}".steps phải là danh sách')
			continue
		for index, step in enumerate(steps, start=1):
			checkWorkflowStep(path, step, f'job "{name}", bước {index}')


def checkWorkflowTemplate(path):
	properties = path.with_suffix('.properties.json')
	if not properties.exists():
		error(path, f'thiếu tệp {properties.name}')
		return
	try:
		meta = readJsonObject(properties)
	except json.JSONDecodeError as exc:
		error(properties, f'JSON không hợp lệ: {exc}')
		return
	for key in ('name', 'description'):
		if not meta.get(key):
			error(properties, f'thiếu khóa bắt buộc "{key}"')
	categories = configItems(properties, meta, 'categories', str)
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
	pinned = re.compile(r'ruff==|pipx install ruff|actionlint@v|download-actionlint|shellcheck-v\d')
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
	editorconfig = readText(ROOT / '.editorconfig')
	attributes = readText(ROOT / '.gitattributes')
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
	crlf = set(re.findall(r'^\*(\.\S+) .*\beol=crlf\b', attributes, re.MULTILINE))
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
	contributing = readText(ROOT / 'CONTRIBUTING.md')
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
		covered = set(re.findall(r"'\^([a-z]+)/'", readText(labeler)))
		# Nhãn giai đoạn Pre-Release không thay cho nhãn loại release.
		data = loadYaml(labeler, dict) or {}
		if not any(
			'^release/' in configItems(labeler, rule, 'head-branch', str)
			for rule in configItems(labeler, data, 'release')
		):
			covered.discard('release')
		errors.extend(
			f'{labeler.relative_to(ROOT)}: thiếu luật head-branch cho tiền tố "{prefix}/" của CONTRIBUTING.md'
			for prefix in sorted(prefixes - covered)
		)
	# Mẫu commit (.gitmessage, bật bằng make hooks) liệt kê đúng các loại commit.
	message = ROOT / '.gitmessage'
	listed = (
		re.search(r'^# Loại: (.+)$', readText(message), re.MULTILINE) if message.exists() else None
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


def importedNames(nodes):
	"""Tên được import trong tệp (nodes: mọi nút của cây cú pháp) → đường dẫn đầy đủ (import http.server → http;
	from x import y → x.y)."""
	names = {}
	for node in nodes:
		if isinstance(node, ast.Import):
			for alias in node.names:
				names[alias.asname or alias.name.split('.')[0]] = (
					alias.name if alias.asname else alias.name.split('.')[0]
				)
		elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
			for alias in node.names:
				names[alias.asname or alias.name] = f'{node.module}.{alias.name}'
	return names


def dottedName(node):
	"""Tên dạng a.b.c của biểu thức (lớp cha), None nếu không phải tên."""
	parts = []
	while isinstance(node, ast.Attribute):
		parts.append(node.attr)
		node = node.value
	if not isinstance(node, ast.Name):
		return None
	parts.append(node.id)
	return '.'.join(reversed(parts))


def resolveObject(dotted):
	"""Đối tượng mà tên đầy đủ (http.server.BaseHTTPRequestHandler) trỏ tới; None nếu không nạp được."""
	parts = dotted.split('.')
	for index in range(len(parts), 0, -1):
		try:
			found = importlib.import_module('.'.join(parts[:index]))
		except ImportError:
			continue
		for attribute in parts[index:]:
			found = getattr(found, attribute, None)
		return found
	return None


def libraryMethods(nodes):
	"""Phương thức mang tên do thư viện quy định: ghi đè phương thức có sẵn ở lớp cha của thư viện (log_message,
	__init__…) hoặc đặt theo mẫu tên thư viện gọi (LIBRARY_NAME_PATTERNS: do_GET, http_open…) — tên đó không do
	người viết đặt nên không áp quy tắc camelCase, kể cả tham số theo chữ ký của lớp cha."""
	imports = importedNames(nodes)
	methods = set()
	for node in nodes:
		if not isinstance(node, ast.ClassDef):
			continue
		inherited, patterns = set(), []
		for base in node.bases:
			dotted = dottedName(base)
			head, _, rest = (dotted or '').partition('.')
			# Lớp cha định nghĩa trong chính tệp (không được import) là mã tự viết.
			if head in imports:
				found = resolveObject(imports[head] + (f'.{rest}' if rest else ''))
				if isinstance(found, type):
					inherited.update(dir(found))
					patterns += [
						pattern
						for library, pattern in LIBRARY_NAME_PATTERNS.items()
						if isinstance(parent := resolveObject(library), type)
						and issubclass(found, parent)
					]
		methods.update(
			item
			for item in node.body
			if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
			and (
				item.name in inherited or any(pattern.fullmatch(item.name) for pattern in patterns)
			)
		)
	return methods


def nameProblems(text):
	"""(dòng, loại, tên) của mọi tên tự đặt sai quy ước trong mã Python; None khi mã không hợp lệ. Tên do Python,
	thư viện quy định (__init__, phương thức ghi đè lớp cha của thư viện) không xét."""
	try:
		tree = ast.parse(text)
	except SyntaxError:
		return None
	# Duyệt cây một lần, ba bước dùng chung danh sách nút.
	nodes = list(ast.walk(tree))
	required = libraryMethods(nodes)
	problems = []
	for node in nodes:
		# Phương thức ghi đè lớp cha của thư viện: cả tên lẫn tham số theo chữ ký thư viện quy định.
		if node in required:
			continue
		# __init__, __enter__…: tên do Python quy định, tham số vẫn do người viết đặt.
		if (
			isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
			and not DUNDER_NAME.fullmatch(node.name)
			and not FUNCTION_NAME.fullmatch(node.name)
		):
			problems.append((node.lineno, 'tên hàm', node.name))
		if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
			arguments = node.args
			problems.extend(
				(argument.lineno, 'tham số', argument.arg)
				for argument in (
					*arguments.posonlyargs,
					*arguments.args,
					*arguments.kwonlyargs,
					arguments.vararg,
					arguments.kwarg,
				)
				if argument and not FUNCTION_NAME.fullmatch(argument.arg)
			)
		elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
			if not VARIABLE_NAME.fullmatch(node.id) and not DUNDER_NAME.fullmatch(node.id):
				problems.append((node.lineno, 'tên biến', node.id))
		elif isinstance(node, ast.ExceptHandler) and node.name:
			if not VARIABLE_NAME.fullmatch(node.name):
				problems.append((node.lineno, 'tên biến', node.name))
	return problems


# Kết quả theo nội dung tệp, giữ qua các lần runChecks() trong cùng tiến trình như yamlResults.
nameResults = {}


def checkNames(path, text):
	"""Tên hàm, tham số tự đặt viết camelCase tiếng Anh; biến không dùng snake_case (ADR 0010)."""
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
	current = contributingSection(readText(listing), 'NGƯỜI QUẢN TRỊ HIỆN TẠI')
	documented = set(re.findall(r'\[@([A-Za-z0-9-]+)\]\(https://github\.com/\1\)', current))
	match = re.search(r'^MAINTAINERS = (\(.*?\))$', readText(source), re.MULTILINE)
	configured = set(ast.literal_eval(match.group(1))) if match else set()
	for name in sorted(documented ^ configured):
		where = listing if name in configured else source
		error(
			where,
			f'người quản trị "{name}" chỉ có ở một trong MAINTAINERS.md và MAINTAINERS của teams.py',
		)
	# Danh sách bỏ qua của ruleset cấp repository ghi actor_id của từng người quản trị (tra id cần API nên chỉ so
	# số lượng): thêm, bớt người quản trị thì sửa cả ruleset.
	for path in sorted((ROOT / 'rulesets').glob('protect-*.json')):
		try:
			ruleset = readJsonObject(path)
		except json.JSONDecodeError:
			continue  # checkFile đã báo lỗi cú pháp của tệp này.
		users = [
			actor
			for actor in configItems(path, ruleset, 'bypass_actors')
			if actor.get('actor_type') == 'User'
		]
		if len(users) != len(configured):
			error(
				path,
				f'danh sách bỏ qua có {len(users)} tài khoản, MAINTAINERS có {len(configured)} người — '
				'thêm, bớt actor_id cho khớp người quản trị',
			)


def repositoryWorkflows():
	"""Workflow GitHub quản lý, nhận cả hai đuôi YAML; dùng danh sách tệp của lượt kiểm tra hiện tại."""
	folderParts = (ROOT / '.github' / 'workflows').parts
	return [
		path
		for path in trackedFiles()
		if path.name.endswith(('.yml', '.yaml')) and path.parts[:-1] == folderParts
	]


def checkRulesets():
	"""Kiểm tra bắt buộc trong ruleset Protect Main phải trùng tên một job có thật, nếu không PR chờ mãi."""
	path = ROOT / 'rulesets' / 'protect-main.json'
	if not path.exists():
		errors.append('thiếu tệp bắt buộc rulesets/protect-main.json')
		return
	try:
		ruleset = readJsonObject(path)
	except json.JSONDecodeError:
		return
	if ruleset.get('name') != 'Protect Main':
		error(path, 'ruleset phải tên "Protect Main"')
	jobs = set()
	for workflow in repositoryWorkflows():
		for job in workflowJobs(workflow).values():
			name = job.get('name')
			if isinstance(name, str):
				jobs.add(name)
	# Mọi ruleset nhánh, tag (cấp repository, cấp tổ chức) bắt buộc commit có chữ ký (ADR 0006); push
	# ruleset không nhận quy tắc này (ADR 0007).
	for rulesetPath in sorted((ROOT / 'rulesets').glob('*.json')):
		try:
			data = readJsonObject(rulesetPath)
		except json.JSONDecodeError:
			continue
		if data.get('target') == 'push':
			continue
		if 'required_signatures' not in {
			configField(rulesetPath, r, 'type', str)
			for r in configItems(rulesetPath, data, 'rules')
		}:
			error(
				rulesetPath, 'ruleset phải có quy tắc required_signatures (Require signed commits)'
			)
	tagPath = ROOT / 'rulesets' / 'protect-release-tags.json'
	if not tagPath.exists():
		errors.append('thiếu tệp bắt buộc rulesets/protect-release-tags.json')
	else:
		try:
			tags = readJsonObject(tagPath)
		except json.JSONDecodeError:
			tags = {}
		conditions = configField(tagPath, tags, 'conditions', dict)
		refName = configField(tagPath, conditions, 'ref_name', dict)
		include = configItems(tagPath, refName, 'include', str)
		if tags.get('name') != 'Protect Release Tags' or tags.get('target') != 'tag':
			error(tagPath, 'ruleset phải tên "Protect Release Tags", target "tag" (ADR 0005)')
		for pattern in ('refs/tags/v*', 'refs/tags/Stable.v*', 'refs/tags/Beta.v*'):
			if pattern not in include:
				error(tagPath, f'ruleset phải áp dụng cho {pattern} (tag phát hành)')
		if not {'creation', 'update', 'deletion'} <= {
			configField(tagPath, rule, 'type', str) for rule in configItems(tagPath, tags, 'rules')
		}:
			error(tagPath, 'ruleset phải chặn creation, update, deletion của tag phát hành')
	orgPath = ROOT / 'rulesets' / 'org-protect-main.json'
	if not orgPath.exists():
		errors.append('thiếu tệp bắt buộc rulesets/org-protect-main.json')
	else:
		try:
			org = readJsonObject(orgPath)
		except json.JSONDecodeError:
			org = {}
		conditions = configField(orgPath, org, 'conditions', dict)
		repositoryName = configField(orgPath, conditions, 'repository_name', dict)
		repositories = configItems(orgPath, repositoryName, 'include', str)
		if org.get('name') != 'Protect Main (Organization)' or '~ALL' not in repositories:
			error(
				orgPath,
				'ruleset phải tên "Protect Main (Organization)" và nhắm mọi repository (~ALL)',
			)
	# Import ruleset cấp tổ chức báo "contains an invalid actor" với actor loại User.
	for orgFile in sorted((ROOT / 'rulesets').glob('org-*.json')):
		if re.search(r'"(actor_type|type)":\s*"User"', readText(orgFile)):
			error(
				orgFile,
				'ruleset cấp tổ chức không dùng actor loại User — GitHub từ chối khi import',
			)
	orgTagPath = ROOT / 'rulesets' / 'org-protect-release-tags.json'
	if not orgTagPath.exists():
		errors.append('thiếu tệp bắt buộc rulesets/org-protect-release-tags.json')
	else:
		try:
			orgTags = readJsonObject(orgTagPath)
		except json.JSONDecodeError:
			orgTags = {}
		conditions = configField(orgTagPath, orgTags, 'conditions', dict)
		repositoryName = configField(orgTagPath, conditions, 'repository_name', dict)
		refName = configField(orgTagPath, conditions, 'ref_name', dict)
		if (
			orgTags.get('name') != 'Protect Release Tags (Organization)'
			or '~ALL' not in configItems(orgTagPath, repositoryName, 'include', str)
			or not {'refs/tags/v*', 'refs/tags/Stable.v*', 'refs/tags/Beta.v*'}
			<= set(configItems(orgTagPath, refName, 'include', str))
		):
			error(
				orgTagPath,
				'ruleset phải tên "Protect Release Tags (Organization)", nhắm ~ALL repository và refs/tags/v*, '
				'refs/tags/Stable.v*, refs/tags/Beta.v*',
			)
	pushPath = ROOT / 'rulesets' / 'org-protect-pushes.json'
	if not pushPath.exists():
		errors.append('thiếu tệp bắt buộc rulesets/org-protect-pushes.json')
	else:
		try:
			pushes = readJsonObject(pushPath)
		except json.JSONDecodeError:
			pushes = {}
		conditions = configField(pushPath, pushes, 'conditions', dict)
		repositoryName = configField(pushPath, conditions, 'repository_name', dict)
		if (
			pushes.get('name') != 'Protect Pushes (Organization)'
			or pushes.get('target') != 'push'
			or '~ALL' not in configItems(pushPath, repositoryName, 'include', str)
		):
			error(
				pushPath,
				'ruleset phải tên "Protect Pushes (Organization)", target "push" và nhắm ~ALL repository (ADR 0007)',
			)
	for rule in configItems(path, ruleset, 'rules'):
		parameters = configField(path, rule, 'parameters', dict)
		for check in configItems(path, parameters, 'required_status_checks'):
			context = configField(path, check, 'context', str)
			if context not in jobs:
				error(
					path,
					f'kiểm tra bắt buộc "{check.get("context")}" không trùng tên job nào trong .github/workflows',
				)


def checkDocsMatchCode():
	"""Tài liệu khớp code: lệnh make, đường dẫn, hàm được nhắc tới phải có thật; README.md liệt kê đủ lệnh make,
	script và workflow của repository."""
	makefile = ROOT / 'Makefile'
	targets = (
		set(re.findall(r'^([a-z-]+):.*## ', readText(makefile), re.MULTILINE))
		if makefile.exists()
		else set()
	)
	scripts = sorted(
		path
		for path in (ROOT / 'scripts').rglob('*.py')
		if not path.name.startswith('test_') and '__pycache__' not in path.parts
	)
	functions = {
		name
		for path in scripts
		for name in re.findall(r'^\s*def (\w+)\(', readText(path), re.MULTILINE)
	}
	for path in (file for file in trackedFiles() if file.suffix == '.md'):
		text = readText(path)
		for target in sorted(set(re.findall(r'`make ([a-z][a-z-]*)', text))):
			if targets and target not in targets:
				error(path, f'nhắc "make {target}" nhưng Makefile không có lệnh này')
		for reference in sorted(set(DOC_PATH.findall(text))):
			# Tên branch ví dụ (docs/update_readme) trông như đường dẫn.
			if '_' in reference and conventions.BRANCH_PATTERN.match(reference):
				continue
			if not (ROOT / reference.rstrip('/')).exists():
				error(path, f'nhắc "{reference}" nhưng tệp, thư mục này không có')
		for name in sorted(set(re.findall(r'`([a-z][A-Za-z0-9]*)\(\)`', text))):
			if name not in functions and not hasattr(builtins, name):
				error(path, f'nhắc hàm "{name}()" nhưng không script nào trong scripts/ định nghĩa')
	readmePath = ROOT / 'README.md'
	if not readmePath.exists():
		return
	readme = readText(readmePath)
	# make help là lệnh mặc định — README ghi dạng `make`.
	for target in sorted(targets - {'help'}):
		if f'`make {target}' not in readme:
			error(readmePath, f'bảng lệnh thiếu "make {target}" (có trong Makefile)')
	for path in scripts:
		relative = path.relative_to(ROOT).as_posix()
		folder = path.parent.relative_to(ROOT).as_posix() + '/'
		if f'`{relative}`' not in readme and (folder == 'scripts/' or f'`{folder}`' not in readme):
			error(readmePath, f'mục cấu trúc thiếu {relative}')
	for workflow in repositoryWorkflows():
		if f'`.github/workflows/{workflow.name}`' not in readme:
			error(readmePath, f'mục cấu trúc thiếu .github/workflows/{workflow.name}')


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
			readText(indexPath),
			re.MULTILINE,
		)
	}
	for path in sorted(folder.glob('[0-9][0-9][0-9][0-9]-*.md')):
		number = path.name[:4]
		text = readText(path)
		status = re.search(r'^- \*\*Trạng thái:\*\* (.+)$', text, re.MULTILINE)
		date = re.search(r'^- \*\*Ngày:\*\* (.+)$', text, re.MULTILINE)
		if not status or not date:
			error(path, 'thiếu dòng "Trạng thái" hoặc "Ngày"')
			continue
		headings = re.findall(r'^## \S+ (.+)$', text, re.MULTILINE)
		if [heading for heading in headings if heading in ADR_SECTIONS] != list(ADR_SECTIONS):
			error(path, f'ADR phải có đủ các mục theo thứ tự: {", ".join(ADR_SECTIONS)}')
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
	if '\t' not in text:
		return
	width = 2 if path.suffix in TWO_SPACE_SUFFIXES else 4
	if path.suffix == '.md':
		text = withoutCodeBlocks(text)
	for number, line in enumerate(text.split('\n'), start=1):
		if re.match(r'^ *\t', line):
			error(
				path,
				f'dòng {number}: {path.suffix} phải thụt lề bằng {width} dấu cách, không dùng tab',
			)
			return


def checkTabOnly(path, text):
	"""Mọi tệp mặc định dùng tab (theo .editorconfig): thụt lề chỉ bằng tab, không trộn dấu cách."""
	match = MIXED_INDENT.search(text)
	if match:
		error(
			path,
			f'dòng {lineNumber(text, match.start())}: thụt lề phải dùng tab theo .editorconfig',
		)


def titleCase(text):
	"""Chữ tiếng Anh (ASCII), mỗi từ bắt đầu bằng chữ hoa hoặc số: Last Commit, Code Style: Prettier."""
	return text.isascii() and all(
		word[0].isupper() or word[0].isdigit() for word in re.findall(r'[^\s:/()-]+', text)
	)


def badgeLabel(url):
	"""Nhãn của huy hiệu shields.io: tham số label=, hoặc phần đầu của /badge/<nhãn>-<nội dung>-<màu>
	("_" là dấu cách, "--" là dấu gạch ngang); None khi không đặt nhãn (shields tự đặt chữ thường)."""
	parsed = urllib.parse.urlparse(url)
	label = urllib.parse.parse_qs(parsed.query).get('label')
	if label:
		return label[0]
	match = re.match(r'/badge/((?:[^-]|--)+)-', parsed.path)
	if not match:
		return None
	return urllib.parse.unquote(match.group(1)).replace('--', '-').replace('_', ' ')


def checkBadges(path, text):
	"""Chữ trên huy hiệu viết tiếng Anh, hoa đầu mỗi từ (Last Commit, Code Style): chữ thay thế và nhãn."""
	for alt, url in re.findall(r'\[!\[([^\]]*)\]\(([^)\s]+)\)\]', text):
		if not titleCase(alt):
			error(path, f'huy hiệu "{alt}": chữ thay thế phải tiếng Anh, hoa đầu mỗi từ')
		parsed = urllib.parse.urlparse(url)
		if parsed.netloc == 'img.shields.io' and not parsed.path.startswith('/endpoint'):
			label = badgeLabel(url)
			if label is None:
				error(
					path,
					f'huy hiệu "{alt}": đặt label= tiếng Anh, hoa đầu mỗi từ (shields tự đặt chữ thường)',
				)
			elif not titleCase(label):
				error(path, f'huy hiệu "{alt}": nhãn "{label}" phải tiếng Anh, hoa đầu mỗi từ')
		elif parsed.path.endswith('/badge.svg'):
			error(
				path,
				f'huy hiệu "{alt}": huy hiệu của GitHub lấy chữ theo tên workflow — dùng huy hiệu shields.io có label=',
			)


def checkHeadings(path, text):
	"""Phong cách thống nhất của repository: mọi tiêu đề Markdown viết hoa."""
	for number, line in enumerate(withoutCodeBlocks(text).split('\n'), start=1):
		heading = re.match(r'#{1,6} (.+)', line)
		title = re.sub(r'`[^`]*`|\[[^\]]*\]\([^)]*\)', '', heading.group(1)) if heading else ''
		if heading and title != title.upper():
			error(path, f'dòng {number}: tiêu đề phải viết hoa — "{heading.group(1)}"')


def checkLabels(path):
	names, problems = inspectLabels(loadYaml(path))
	for problem in problems:
		error(path, problem)
	return names


def checkDependabotCooldown():
	"""Mọi mục Dependabot chờ ≥ 7 ngày sau khi phát hành (chống gói độc vừa phát hành; không ảnh hưởng cập nhật bảo mật)."""
	for path in (
		ROOT / '.github' / 'dependabot.yml',
		ROOT / 'repository-templates' / 'dependabot.yml',
	):
		data = (loadYaml(path, dict) if path.exists() else None) or {}
		for update in configItems(path, data, 'updates'):
			days = configField(path, update, 'cooldown', dict).get('default-days')
			if not isinstance(days, int) or days < 7:
				error(path, f'{update.get("package-ecosystem")}: cần cooldown.default-days ≥ 7')


def configLabels():
	"""Nhãn dùng trong dependabot.yml, release.yml (bản mẫu), labeler.yml và workflow stale."""
	found = []
	for path in (
		ROOT / '.github' / 'dependabot.yml',
		ROOT / 'repository-templates' / 'dependabot.yml',
	):
		data = (loadYaml(path, dict) if path.exists() else None) or {}
		for update in configItems(path, data, 'updates'):
			found += [(path, label) for label in configItems(path, update, 'labels', str)]
	for path in (ROOT / 'repository-templates' / 'release.yml',):
		data = (loadYaml(path, dict) if path.exists() else None) or {}
		changelog = configField(path, data, 'changelog', dict)
		exclude = configField(path, changelog, 'exclude', dict)
		found += [(path, label) for label in configItems(path, exclude, 'labels', str)]
		for category in configItems(path, changelog, 'categories'):
			found += [
				(path, label)
				for label in configItems(path, category, 'labels', str)
				if label != '*'
			]
	for path in (ROOT / '.github' / 'labeler.yml', ROOT / 'repository-templates' / 'labeler.yml'):
		data = (loadYaml(path, dict) if path.exists() else None) or {}
		for label in data:
			if isinstance(label, str):
				found.append((path, label))
			else:
				error(path, 'tên nhãn phải là chuỗi')
	for path in (
		ROOT / '.github' / 'workflows' / 'stale.yml',
		ROOT / 'workflow-templates' / 'stale.yml',
	):
		if not path.exists():
			continue
		text = readText(path)
		for match in re.finditer(
			r'^\s*(?:stale|exempt)-(?:issue|pr)-labels?:\s*(.+)$', text, re.MULTILINE
		):
			names = match.group(1).strip().strip('\'"').split(',')
			found += [(path, name.strip()) for name in names if name.strip()]
	return found


def checkEmails(path, text):
	# Email không vắt qua hai dòng: chỉ quét các dòng có "@" (nhanh gấp vài lần quét cả tệp, cùng kết quả).
	if '@' not in text:
		return
	lines = '\n'.join(line for line in text.split('\n') if '@' in line)
	for email in set(EMAIL.findall(lines)):
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
	if moment.tzinfo is None:
		error(path, 'Expires phải có múi giờ (Z hoặc độ lệch UTC)')
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
	# Liên kết CHƯA PHÁT HÀNH so sánh từ tag phát hành gần nhất tới HEAD (release.py ghi như vậy khi chuẩn bị phát
	# hành); gốc là tên branch (main…HEAD) thì trang so sánh luôn rỗng.
	unreleased = re.search(
		r'^## \[CHƯA PHÁT HÀNH\]\([^)]*/compare/([^)]+)\.\.\.HEAD\)', text, re.MULTILINE
	)
	if unreleased and not RELEASE_TAG.fullmatch(unreleased.group(1)):
		error(
			path,
			f'liên kết CHƯA PHÁT HÀNH phải so sánh từ tag phát hành (Stable.v…, Beta.v…, v…) tới HEAD, '
			f'không phải "{unreleased.group(1)}"',
		)
	checkAbsoluteLinks(path, text, 'mỗi mục thành nội dung GitHub Release')


def checkScriptLanguage(path):
	"""Script không viết bằng Python phải nêu lý do ngôn ngữ khác xử lý tốt hơn trong 10 dòng đầu."""
	head = '\n'.join(decodeText(readBytes(path), 'replace').split('\n')[:10])
	if not re.search(rf'{re.escape(NOT_PYTHON_REASON)}\s*\S', head):
		error(
			path,
			f'script không viết bằng Python — thêm dòng "{NOT_PYTHON_REASON} <lý do>" ở đầu tệp, '
			'nêu vì sao ngôn ngữ này xử lý tốt hơn; nếu không, viết bằng Python (ADR 0009)',
		)


def checkShell(path):
	data = readBytes(path)
	if b'\r' in data:
		error(path, 'shell script phải dùng LF')
	if not data.startswith(b'#!'):
		error(path, 'shell script thiếu shebang')


def checkIssueConfig(path):
	config = loadYaml(path, dict)
	if config is None:
		return
	for link in configItems(path, config, 'contact_links'):
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
	if file.suffix in BINARY_SUFFIXES:
		return
	content = checkText(file)
	if content is None:
		return
	if file.suffix == '.sh':
		checkShell(file)
	if file.suffix == '.py':
		checkNames(file, readText(file))
	if file.suffix in SPACE_SUFFIXES + TWO_SPACE_SUFFIXES:
		checkSpaceOnly(file, readText(file))
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
		checkBadges(file, content)
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
	errors.extend(
		f'thiếu tệp bắt buộc {required}'
		for required in (
			'README.md',
			'CHANGELOG.md',
			'LICENSE',
			'SECURITY.md',
			'CONTRIBUTING.md',
			'CODE_OF_CONDUCT.md',
			'SUPPORT.md',
		)
		if not (ROOT / required).exists()
	)


def checkLabelUsage():
	"""Nhãn dùng trong biểu mẫu và cấu hình phải có trong labels.yml."""
	labelFile = ROOT / 'labels.yml'
	if not labelFile.exists():
		return
	known = checkLabels(labelFile)
	for label in GITHUB_DEFAULT_LABELS:
		if label not in known:
			error(labelFile, f'thiếu nhãn mặc định của GitHub "{label}"')
	for formPath, label in FORM_LABELS + configLabels():
		if label.lower() not in known:
			error(formPath, f'nhãn "{label}" chưa có trong labels.yml')


def runChecks():
	"""Chạy mọi kiểm tra, trả danh sách lỗi."""
	errors.clear()
	FORM_LABELS.clear()
	yamlCache.clear()
	jsonCache.clear()
	trackedCache.clear()
	bytesCache.clear()
	textCache.clear()
	anchorsCache.clear()
	for file in trackedFiles():
		checkFile(file)
	for check in (
		checkFormatConfig,
		checkLintIgnoreConfig,
		checkDependabotCooldown,
		checkToolVersions,
		checkSuffixLists,
		checkEditorExtensions,
		checkDevcontainerPins,
		checkConventions,
		checkRulesets,
		checkMaintainers,
		checkDocsMatchCode,
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
