"""Kiểm tra tính nhất quán của repository .github.

Chạy: python3 scripts/validate.py  (cần Ruby để đọc YAML; có sẵn trên runner GitHub).
"""

import json
import re
import subprocess
import sys
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORM_TYPES = {'markdown', 'textarea', 'input', 'dropdown', 'checkboxes'}
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


def check_links(path, text):
	body = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
	for match in re.finditer(r'\]\(([^)\s#]+)(#[^)]*)?\)', body):
		target = match.group(1)
		if re.match(r'[a-z]+:', target):
			continue
		if not (path.parent / target).exists():
			error(path, f'liên kết hỏng: {target}')


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


def check_issue_form(path):
	form = load_yaml(path)
	if form is None:
		return
	for key in ('name', 'description', 'body'):
		if not form.get(key):
			error(path, f'thiếu khóa bắt buộc "{key}"')
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
	workflow = load_yaml(path)
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
	icon = meta.get('iconName')
	if icon and not (path.parent / f'{icon}.svg').exists():
		error(properties, f'không tìm thấy biểu tượng {icon}.svg')


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
	for rule in ruleset.get('rules', []):
		for check in (rule.get('parameters') or {}).get('required_status_checks', []):
			if check.get('context') not in jobs:
				error(
					path,
					f'kiểm tra bắt buộc "{check.get("context")}" không trùng tên job nào trong .github/workflows',
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
	"""Shell, Makefile, Python: thụt lề chỉ bằng tab."""
	for number, line in enumerate(text.split('\n'), start=1):
		indent = re.match(r'^[ \t]*', line).group(0)
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
		moment = datetime.fromisoformat(expires.replace('Z', '+00:00'))
	except ValueError:
		error(path, f'Expires không đúng định dạng ISO 8601: {expires}')
		return
	remaining = (moment - datetime.now(timezone.utc)).days
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
	if file.suffix == '.sh':
		check_shell(file)
	if file.suffix in ('.sh', '.py') or file.name == 'Makefile':
		check_tab_only(file, file.read_text(encoding='utf-8'))
	if file.suffix in SPACE_SUFFIXES + TWO_SPACE_SUFFIXES:
		check_space_only(file, file.read_text(encoding='utf-8'))
	if (
		file.suffix
		not in (
			'.md',
			'.yml',
			'.yaml',
			'.py',
			'.json',
			'.sh',
			'.svg',
			'.txt',
			'.js',
			'.toml',
		)
		and not file.name.endswith(CRLF_SUFFIXES)
		and file.name
		not in (
			'.editorconfig',
			'.gitattributes',
			'.gitignore',
			'.gitmessage',
			'.clang-format',
			'.dockerignore',
			'.env.example',
			'.python-version',
			'.npmrc',
			'Makefile',
			'CODEOWNERS',
			'LICENSE',
		)
	):
		continue
	content = check_text(file)
	if content is None:
		continue
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
	if file.parent.name == 'ISSUE_TEMPLATE' and file.suffix in ('.yml', '.yaml'):
		if file.stem == 'config':
			check_issue_config(file)
		else:
			check_issue_form(file)
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
check_suffix_lists()
check_conventions()
check_rulesets()

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
	for form_path, label in FORM_LABELS:
		if label.lower() not in known:
			error(form_path, f'nhãn "{label}" chưa có trong labels.yml')

for message in errors:
	print(f'❌ {message}')
print(f'{"✅ Không có lỗi" if not errors else f"❌ {len(errors)} lỗi"}.')
sys.exit(1 if errors else 0)
