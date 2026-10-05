"""Quy ước mã nguồn: tên tự đặt camelCase (ADR 0010), script ưu tiên Python (ADR 0009)."""

import ast
import hashlib
import importlib.util
import re

from validation.common import decodeText, error, readBytes

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
	# Đọc trực tiếp các trường đã có trên nút, tránh getattr cho từng trường của cây lớn.
	nodes = [tree]
	for node in nodes:
		for value in vars(node).values():
			if isinstance(value, ast.AST):
				nodes.append(value)
			elif isinstance(value, list):
				nodes.extend(item for item in value if isinstance(item, ast.AST))
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
