"""Phần dùng chung của các kiểm tra: đọc tệp (có cache), YAML qua Ruby, JSON, danh sách lỗi."""

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Lỗi của lượt runChecks() đang chạy — mọi module ghi vào cùng một danh sách.
errors = []


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
# Kết quả đọc theo đường dẫn và nội dung, giữ qua các lần runChecks() trong cùng tiến trình: tệp không đổi
# thì không gọi lại Ruby; thông báo lỗi của Ruby chứa đường dẫn nên không dùng chung giữa các tệp.
yamlResults = {}


def runYamlBatch(names):
	"""Một lần gọi Ruby cho các tệp; trả ({tên: {"data": …} hoặc {"error": …}}, None) hoặc (None, lý do) khi Ruby
	dừng giữa chừng."""
	result = subprocess.run(
		['ruby', '-ryaml', '-rjson', '-e', YAML_BATCH, *names],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode != 0:
		return None, result.stderr.strip() or f'Ruby dừng bất thường (mã {result.returncode})'
	return json.loads(result.stdout), None


def readYamlFiles(paths):
	"""Đọc nhiều tệp YAML trong một lần gọi Ruby; mỗi tệp trả {"data": …} hoặc {"error": …}."""
	keys = {str(path): (str(path), hashlib.sha256(readBytes(path)).hexdigest()) for path in paths}
	missing = [str(path) for path in paths if keys[str(path)] not in yamlResults]
	failed = {}
	if missing:
		entries, problem = runYamlBatch(missing)
		if entries is None:
			# Ruby chết giữa lô (ví dụ YAML tham chiếu vòng làm tràn stack: chạy từ git hook, Ruby bị dừng bằng
			# tín hiệu thay vì bắt SystemStackError): đọc lại từng tệp để chỉ tệp hỏng bị báo lỗi.
			entries = {}
			for name in missing:
				single, problem = runYamlBatch([name]) if len(missing) > 1 else (None, problem)
				if single is None:
					failed[name] = {'error': problem}
				else:
					entries.update(single)
		for name, entry in entries.items():
			yamlResults[keys[name]] = entry
	# Bản sao: loadYaml đánh dấu "reported" trên từng mục của lần chạy. Lỗi Ruby dừng giữa chừng không giữ qua lượt
	# sau (có thể chỉ do môi trường lúc đó).
	return {
		str(path): dict(failed.get(str(path)) or yamlResults[keys[str(path)]]) for path in paths
	}


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


def lineNumber(text, offset):
	return text.count('\n', 0, offset) + 1
