"""Giá trị riêng tư của bản khôi phục nằm ngoài repository, không xuất ra thông báo hoặc Git."""

import json
import os
import tempfile
import threading
import uuid
from pathlib import Path

from orgsetup import github

LOCK = threading.Lock()
CAPTURED_VALUES = {}


def dataPath():
	root = (
		Path(
			os.environ.get(
				'ORGSETUP_PRIVATE_DIR', str(Path.home() / '.local' / 'share' / 'toanquynh-orgsetup')
			)
		)
		.expanduser()
		.resolve()
	)
	path = root / github.ORG / 'values.json'
	if root.is_relative_to(github.ROOT.resolve()) or path.parent.resolve().is_relative_to(
		github.ROOT.resolve()
	):
		raise ValueError('ORGSETUP_PRIVATE_DIR phải nằm ngoài repository')
	return path


def readValues():
	path = dataPath()
	if path.is_symlink():
		raise ValueError('Tệp dữ liệu riêng tư không được là symlink')
	if not path.exists():
		return {}
	if path.stat().st_mode & 0o077:
		raise ValueError('Tệp dữ liệu riêng tư phải có quyền 0600; chạy chmod 600 cho tệp')
	data = json.loads(path.read_text(encoding='utf-8'))
	if not isinstance(data, dict) or any(
		not isinstance(key, str) or not isinstance(value, str) for key, value in data.items()
	):
		raise ValueError('Tệp dữ liệu riêng tư sai cấu trúc')
	return data


def captureValue(reference, value):
	if not isinstance(reference, str) or not isinstance(value, str):
		raise TypeError('Giá trị riêng tư phải là chuỗi')
	previous = readValues()
	with LOCK:
		known = dict(previous, **CAPTURED_VALUES)
		prefix = f'{reference}#'
		alias = next(
			(
				key
				for key, existing in known.items()
				if key.startswith(prefix) and existing == value
			),
			f'{prefix}{uuid.uuid4().hex}',
		)
		CAPTURED_VALUES[alias] = value
		return alias


def capturedValue(reference):
	with LOCK:
		if reference not in CAPTURED_VALUES:
			raise ValueError('Chưa đọc được giá trị riêng tư trong lượt này')
		return CAPTURED_VALUES[reference]


def resetCapture():
	with LOCK:
		CAPTURED_VALUES.clear()


def privateValue(reference):
	values = readValues()
	if reference not in values:
		raise ValueError('Thiếu giá trị riêng tư của bản khôi phục; bổ sung ở tệp ngoài repository')
	return values[reference]


def valueReferences(config):
	references = set()
	for scope in [config['organization'], *config['repositories'].values()]:
		for item in scope.get('private_settings', {}).values():
			references.add(item['value_source'])
		for item in scope.get('manual_settings', {}).values():
			if item['configuration_source'] is not None:
				references.add(item['configuration_source'])
		for section, items in scope.get('pending_settings', {}).items():
			if section == 'collections':
				pendingScope = {
					'collections': {key: value for key, value in items.items() if value is not None}
				}
				references.update(
					valueReferences({'organization': pendingScope, 'repositories': {}})
				)
		groups = scope.get('collections', {})
		for item in groups.get('variables', []):
			references.add(item['value_source'])
		for item in groups.get('webhooks', []):
			references.add(item['url_source'])
		for item in groups.get('custom_patterns', []):
			references.add(item['definition_source'])
		for item in groups.get('private_registries', []):
			references.add(item['definition_source'])
		for policy in groups.get('ip_allow_list', []):
			for entry in policy['entries']:
				references.update((entry['value_source'], entry['name_source']))
		for environment in groups.get('environments', []):
			for item in environment.get('variables', []):
				references.add(item['value_source'])
	return references


def saveCapturedValues(config, complete=False):
	"""Chỉ lưu giá trị của nhóm đã xác minh; bổ sung giữ giá trị của bản cũ, không lưu phản hồi API."""
	references = valueReferences(config)
	if not references:
		return
	previous = readValues()
	with LOCK:
		for reference in references:
			if reference in CAPTURED_VALUES and (not complete or reference not in previous):
				previous[reference] = CAPTURED_VALUES[reference]
	if not previous:
		# Khai báo thủ công chưa có dữ liệu riêng không tạo một tệp rỗng giả như đã sao lưu.
		return
	path = dataPath()
	if (path.parent.resolve()).is_relative_to(github.ROOT.resolve()):
		raise ValueError('Tệp dữ liệu riêng tư phải nằm ngoài repository')
	path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
	temporary = None
	try:
		with tempfile.NamedTemporaryFile(
			mode='w', encoding='utf-8', dir=path.parent, delete=False
		) as output:
			temporary = Path(output.name)
			os.chmod(temporary, 0o600)
			output.write(json.dumps(previous, ensure_ascii=False, indent='\t') + '\n')
		temporary.replace(path)
	finally:
		if temporary is not None:
			temporary.unlink(missing_ok=True)
	print('✔ Dữ liệu riêng tư đã lưu ngoài repository; tệp quyền 0600.')


def resolveBody(body):
	"""Giải tham chiếu ngay trước request; kế hoạch và thông báo chỉ chứa tên tham chiếu."""
	if isinstance(body, dict):
		if set(body) == {'$local_value'}:
			return privateValue(body['$local_value'])
		return {key: resolveBody(value) for key, value in body.items()}
	if isinstance(body, list):
		return [resolveBody(item) for item in body]
	return body


def hasReferences(body):
	if isinstance(body, dict):
		return bool({'$local_value', '$captured_body'} & set(body)) or any(
			hasReferences(value) for value in body.values()
		)
	if isinstance(body, list):
		return any(hasReferences(item) for item in body)
	return False
