"""Gói sao lưu cài đặt và giá trị riêng ngoài Git; kiểm tra offline, không ghi GitHub."""

import contextlib
import hashlib
import io
import json
import os
import re
import tarfile
import tempfile
import zlib
from datetime import UTC, datetime
from pathlib import Path

from orgsetup import configuration, github, inventory, localdata

FORMAT_VERSION = 1
MEMBERS = {'github-settings.json', 'values.json', 'manifest.json'}
MAX_MEMBER_SIZE = 64 * 1024 * 1024
MANIFEST_FIELDS = {
	'format_version',
	'organization_name',
	'created_at',
	'complete',
	'problems',
	'sha256',
}
REFERENCE_FIELDS = {
	'value_source',
	'name_source',
	'url_source',
	'secret_source',
	'pattern_source',
	'definition_source',
	'credential_source',
	'configuration_source',
	'dismissal_restriction_source',
}
JSON_REFERENCE_FIELDS = {
	'definition_source',
	'configuration_source',
	'dismissal_restriction_source',
}


def backupPath(value):
	path = Path(value).expanduser()
	path = path.parent.resolve() / path.name
	if path.is_relative_to(github.ROOT.resolve()) or path.is_symlink():
		raise ValueError(
			'Gói sao lưu chứa dữ liệu riêng phải nằm ngoài repository và không là symlink'
		)
	return path


def jsonBytes(data):
	return (json.dumps(data, ensure_ascii=False, indent='\t') + '\n').encode('utf-8')


def backupProblems(config, values):
	problems = inventory.configProblems(config, complete=True, privateValues=values)
	problems.extend(f'{path}: API chưa xác minh' for path in config['unavailable'])
	return list(dict.fromkeys(problems))


def validateManifest(manifest):
	if (
		not isinstance(manifest, dict)
		or set(manifest) != MANIFEST_FIELDS
		or type(manifest['format_version']) is not int
		or manifest['format_version'] != FORMAT_VERSION
		or manifest['organization_name'] != github.ORG
		or not isinstance(manifest['created_at'], str)
		or type(manifest['complete']) is not bool
		or not isinstance(manifest['problems'], list)
		or any(not isinstance(problem, str) for problem in manifest['problems'])
		or not isinstance(manifest['sha256'], dict)
		or set(manifest['sha256']) != MEMBERS - {'manifest.json'}
		or any(
			not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest)
			for digest in manifest['sha256'].values()
		)
	):
		raise ValueError('Manifest của gói sao lưu không hợp lệ')
	if datetime.fromisoformat(manifest['created_at']).utcoffset() is None:
		raise ValueError('Thời điểm của gói sao lưu cần múi giờ')


def writeBackup(value):
	"""Lưu cả bản chưa đủ để không mất dữ liệu đã có; trạng thái và mã thoát vẫn báo chưa đủ."""
	path = backupPath(value)
	if path.exists():
		raise ValueError('Gói sao lưu đã tồn tại; chọn tên mới để giữ bản trước')
	config = configuration.readConfig()
	try:
		available = localdata.readValues()
	except (OSError, ValueError, TypeError):
		raise ValueError('Không đọc được dữ liệu riêng; không tạo gói sao lưu') from None
	references = localdata.valueReferences(config)
	values = {key: available[key] for key in sorted(references) if key in available}
	problems = backupProblems(config, values)
	content = {'github-settings.json': jsonBytes(config), 'values.json': jsonBytes(values)}
	manifest = {
		'format_version': FORMAT_VERSION,
		'organization_name': github.ORG,
		'created_at': datetime.now(UTC).isoformat(),
		'complete': not problems,
		'problems': problems,
		'sha256': {name: hashlib.sha256(data).hexdigest() for name, data in content.items()},
	}
	content['manifest.json'] = jsonBytes(manifest)
	if any(len(data) > MAX_MEMBER_SIZE for data in content.values()):
		raise ValueError('Dữ liệu vượt giới hạn kích thước gói; không tạo bản không thể kiểm tra')
	path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
	temporary = None
	try:
		with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
			temporary = Path(output.name)
			os.chmod(temporary, 0o600)
			with tarfile.open(fileobj=output, mode='w:gz') as archive:
				for name, data in content.items():
					member = tarfile.TarInfo(name)
					member.size = len(data)
					member.mode = 0o600
					archive.addfile(member, io.BytesIO(data))
			output.flush()
			os.fsync(output.fileno())
		# Link chặn cả trường hợp tiến trình khác vừa tạo tên đích; không ghi đè bản trước.
		os.link(temporary, path)
	finally:
		if temporary is not None:
			temporary.unlink(missing_ok=True)
	print('✔ Đã lưu gói sao lưu ngoài repository, quyền 0600; không thay đổi GitHub.')
	for problem in problems:
		print(f'⚠ {problem}')
	print(
		'⚠ Gói còn thiếu; chưa bảo đảm khôi phục đầy đủ.'
		if problems
		else '✔ Gói đủ dữ liệu trong phạm vi bộ quản trị; mục thủ công do quản trị xác nhận.'
	)
	return 1 if problems else 0


def readBackup(value):
	"""Không giải nén: chỉ đọc tệp thường đúng tên, chặn trùng tên, symlink và dữ liệu sai."""
	path = backupPath(value)
	if path.stat().st_mode & 0o7777 != 0o600:
		raise ValueError('Gói sao lưu phải có quyền 0600; chạy chmod 600 cho gói')
	content = {}
	try:
		with tarfile.open(path, mode='r:gz') as archive:
			for member in archive:
				if (
					member.name not in MEMBERS
					or member.name in content
					or not member.isfile()
					or member.mode != 0o600
					or not 0 <= member.size <= MAX_MEMBER_SIZE
				):
					raise ValueError('Cấu trúc gói sao lưu không hợp lệ')
				with archive.extractfile(member) as source:
					content[member.name] = source.read()
		if set(content) != MEMBERS:
			raise ValueError('Gói sao lưu thiếu tệp')
		manifest = json.loads(content['manifest.json'])
		validateManifest(manifest)
		for name, digest in manifest['sha256'].items():
			if hashlib.sha256(content[name]).hexdigest() != digest:
				raise ValueError('Checksum không khớp; không dùng gói này để khôi phục')
		config = configuration.validateConfig(json.loads(content['github-settings.json']))
		values = json.loads(content['values.json'])
		if not isinstance(values, dict) or any(
			not isinstance(key, str) or not isinstance(item, str) for key, item in values.items()
		):
			raise ValueError('Dữ liệu riêng của gói sao lưu không hợp lệ')
		if set(values) - localdata.valueReferences(config):
			raise ValueError('Gói sao lưu chứa dữ liệu riêng ngoài phạm vi cấu hình')
		problems = backupProblems(config, values)
		if manifest['complete'] != (not problems) or manifest['problems'] != problems:
			raise ValueError('Trạng thái gói không khớp hợp đồng hiện tại; cần tạo lại bản sao lưu')
		return config, values, problems
	except (OSError, ValueError, TypeError, KeyError, EOFError, tarfile.TarError, zlib.error):
		# Nội dung JSON hoặc cấu hình riêng không đi vào lỗi, kể cả lỗi validator.
		raise ValueError(
			'Gói sao lưu hỏng, sai hợp đồng hoặc chưa đọc được; không khôi phục'
		) from None


def checkBackup(value):
	_, _, problems = readBackup(value)
	print('✔ Cấu trúc và checksum của gói sao lưu hợp lệ; không cần GitHub hoặc tệp riêng tại máy.')
	for problem in problems:
		print(f'⚠ {problem}')
	print(
		'⚠ Gói còn thiếu; chưa bảo đảm khôi phục đầy đủ.'
		if problems
		else '✔ Gói đủ dữ liệu trong phạm vi bộ quản trị; cần audit sau khi khôi phục.'
	)
	return 1 if problems else 0


def expandReferences(data, values):
	"""Chú thích giá trị đã lưu, giữ chuỗi variables/regex nguyên vẹn; không tải kho ngoài."""
	if isinstance(data, list):
		return [expandReferences(item, values) for item in data]
	if not isinstance(data, dict):
		return data
	result = {}
	for key, value in data.items():
		if key in REFERENCE_FIELDS and isinstance(value, str):
			entry = {'reference': value, 'available': value in values}
			if value in values:
				stored = values[value]
				if key in JSON_REFERENCE_FIELDS:
					# Bản quản trị có thể là chuỗi tham chiếu kho ngoài, không phải JSON.
					with contextlib.suppress(ValueError):
						stored = json.loads(stored)
				entry['saved_value'] = stored
			result[key] = entry
		else:
			result[key] = expandReferences(value, values)
	return result


def exportRecovery(value, destination):
	"""Xuất bản đọc thủ công độc lập từ archive đã kiểm tra; không áp dụng hoặc xác nhận cài đặt."""
	config, values, problems = readBackup(value)
	path = backupPath(destination)
	if path.exists():
		raise ValueError('Bản khôi phục đã tồn tại; chọn tên mới để giữ bản trước')
	data = {
		'format_version': FORMAT_VERSION,
		'organization_name': config['organization_name'],
		'complete': not problems,
		'problems': problems,
		'restore_mode': 'manual_review',
		'instructions': [
			'Đây là bản đọc để khôi phục; không gửi trực tiếp JSON này tới API.',
			'Giữ nguồn và gói sao lưu trước nâng cấp; nhập bổ sung rồi đối chiếu với mục tiêu đã lưu.',
			'Áp dụng nhóm API được hỗ trợ sau xem trước; khôi phục nhóm web/thủ công theo dữ liệu riêng.',
			'Kiểm tra danh tính principal, DNS, quyền/gói và dịch vụ bên ngoài tại thời điểm khôi phục.',
			'Phần chưa biết và phần loại khỏi phạm vi vẫn cần xử lý; không tự đổi dấu chưa đủ.',
		],
		'repository_defaults': config['repository_defaults'],
		'scopes': {
			base: expandReferences(scope, values) for base, scope in inventory.scopes(config)
		},
		'unavailable': config['unavailable'],
	}
	path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
	temporary = None
	try:
		with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
			temporary = Path(output.name)
			os.chmod(temporary, 0o600)
			output.write(jsonBytes(data))
			output.flush()
			os.fsync(output.fileno())
		os.link(temporary, path)
	finally:
		if temporary is not None:
			temporary.unlink(missing_ok=True)
	print(
		'✔ Đã xuất bản khôi phục ngoài Git, quyền 0600; dùng dữ liệu trong gói, không gọi GitHub.'
	)
	print(
		'⚠ Bản còn thiếu; xem problems và giới hạn trong dữ liệu thủ công.'
		if problems
		else '✔ Dữ liệu trong phạm vi đã đủ; cần xác nhận trên GitHub sau khôi phục.'
	)
	return 1 if problems else 0
