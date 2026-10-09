"""Nhập và khôi phục mẫu secret scanning; xuất bản mẫu vẫn cần giao diện GitHub."""

import json
import re

from orgsetup import github, localdata

GROUP_PATHS = {
	'custom_patterns': 'secret-scanning/custom-patterns',
	'pattern_settings': 'secret-scanning/pattern-configurations',
}
DEFINITION_DEFAULTS = {
	'start_delimiter': r'\A|[^0-9A-Za-z]',
	'end_delimiter': r'\z|[^0-9A-Za-z]',
	'must_match': [],
	'must_not_match': [],
}


def definition(data):
	"""Chỉ giữ trường regex có hợp đồng ghi; chuỗi mẫu không được đưa vào Git hoặc lỗi."""
	if not isinstance(data, dict) or set(data) - {'pattern', *DEFINITION_DEFAULTS}:
		raise ValueError('Định nghĩa mẫu chứa trường không được hỗ trợ')
	result = dict(DEFINITION_DEFAULTS, **data)
	for field in ('pattern', 'start_delimiter', 'end_delimiter'):
		if not isinstance(result.get(field), str):
			raise TypeError('Định nghĩa mẫu thiếu regex hợp lệ')
	for field in ('must_match', 'must_not_match'):
		if not isinstance(result[field], list) or any(
			not isinstance(value, str) for value in result[field]
		):
			raise ValueError('Định nghĩa mẫu có danh sách regex sai kiểu')
	return result


def privateDefinition(reference, captured=False):
	try:
		value = (
			localdata.capturedValue(reference) if captured else localdata.privateValue(reference)
		)
		return definition(json.loads(value))
	except (ValueError, TypeError):
		raise ValueError('Thiếu hoặc sai định nghĩa mẫu trong tệp riêng tư') from None


def validateGroup(key, items):
	if not isinstance(items, list):
		raise TypeError('Mẫu secret scanning phải là danh sách')
	names = set()
	for item in items:
		if not isinstance(item, dict):
			raise TypeError('Mẫu secret scanning phải là object')
		if key == 'custom_patterns':
			if (
				set(item)
				!= {'name', 'slug', 'state', 'push_protection_enabled', 'definition_source'}
				or item['state'] not in ('published', 'unpublished')
				or type(item['push_protection_enabled']) is not bool
				or not isinstance(item['definition_source'], str)
				or not re.fullmatch(r'(?:orgs|repos)/[^#]+#[a-f0-9]{32}', item['definition_source'])
			):
				raise ValueError('Mẫu tùy chỉnh thiếu trường hoặc chứa metadata')
			if not isinstance(item['slug'], str) or not item['slug']:
				raise ValueError('Mẫu tùy chỉnh thiếu slug')
			name = item['name']
		elif key == 'pattern_settings':
			if (
				set(item) != {'kind', 'name', 'setting', 'enterprise_setting'}
				or item['kind'] not in ('provider', 'custom')
				or item['setting'] not in ('not-set', 'disabled', 'enabled')
				or item['enterprise_setting'] not in (None, 'not-set', 'disabled', 'enabled')
			):
				raise ValueError('Chính sách mẫu có trường hoặc giá trị không hợp lệ')
			name = item['name']
		else:
			raise ValueError('Nhóm mẫu không được hỗ trợ')
		if not isinstance(name, str) or not name:
			raise ValueError('Mẫu thiếu tên')
		identity = itemName(key, item)
		if identity in names:
			raise ValueError('Mẫu trùng tên')
		names.add(identity)
	if key == 'custom_patterns' and len({item['slug'] for item in items}) != len(items):
		raise ValueError('Mẫu tùy chỉnh trùng slug')
	return items


def itemName(key, item):
	return item['name'] if key == 'custom_patterns' else f'{item["kind"]}/{item["name"]}'


def readDetails(base, key):
	path = f'{base}/{GROUP_PATHS[key]}'
	if key == 'pattern_settings':
		if not base.startswith('orgs/'):
			raise ValueError('Chính sách mẫu chỉ có API cấp tổ chức')
		data = github.ghJson('api', path)
		if not isinstance(data, dict) or not isinstance(data.get('pattern_config_version'), str):
			raise ValueError('Chính sách mẫu thiếu phiên bản xác minh')
		result, ids = [], {'version': data['pattern_config_version']}
		for kind in ('provider', 'custom'):
			tokens = set()
			items = data.get(f'{kind}_pattern_overrides')
			if not isinstance(items, list):
				raise TypeError('Chính sách mẫu thiếu danh sách')
			for item in items:
				if not isinstance(item, dict) or not isinstance(item.get('token_type'), str):
					raise TypeError('Chính sách mẫu thiếu ID')
				if not item['token_type'] or item['token_type'] in tokens:
					raise ValueError('Chính sách mẫu có ID rỗng hoặc trùng')
				tokens.add(item['token_type'])
				entry = {
					'kind': kind,
					'name': item['token_type'] if kind == 'provider' else item['slug'],
					'setting': item['setting'],
					'enterprise_setting': item.get('enterprise_setting'),
				}
				ids[itemName(key, entry)] = (item['token_type'], item.get('custom_pattern_version'))
				result.append(entry)
		return validateGroup(key, result), ids
	result, ids = [], {}
	for item in github.ghList(path):
		if not isinstance(item, dict) or type(item.get('id')) is not int or item['id'] <= 0:
			raise ValueError('Mẫu tùy chỉnh thiếu ID hợp lệ')
		value = definition(
			{
				'pattern': item['pattern'],
				**{
					field: item.get(field) if item.get(field) is not None else default
					for field, default in DEFINITION_DEFAULTS.items()
				},
			}
		)
		entry = {
			field: item[field] for field in ('name', 'slug', 'state', 'push_protection_enabled')
		}
		entry['definition_source'] = localdata.captureValue(
			f'{path}/definition', json.dumps(value, sort_keys=True)
		)
		if any(resourceId == item['id'] for resourceId, _ in ids.values()):
			raise ValueError('Mẫu tùy chỉnh trùng ID')
		ids[item['name']] = (item['id'], item.get('custom_pattern_version'))
		result.append(entry)
	return validateGroup(key, result), ids


def itemMatches(key, current, wanted):
	if current is None:
		return False
	if key == 'pattern_settings':
		return current == wanted
	return all(
		current[field] == wanted[field] for field in wanted if field != 'definition_source'
	) and (
		privateDefinition(current['definition_source'], captured=True)
		== privateDefinition(wanted['definition_source'])
	)


def collectionChanges(plan, base, key, current, targets):
	validateGroup(key, targets)
	path = f'{base}/{GROUP_PATHS[key]}'
	present = {itemName(key, item): item for item in current}
	changed = [
		item for item in targets if not itemMatches(key, present.get(itemName(key, item)), item)
	]
	if not changed:
		return
	latest, ids = readDetails(base, key)
	if {itemName(key, item): item for item in latest} != present:
		raise ValueError('Mẫu thay đổi trong lúc lập kế hoạch; đọc lại trước khi ghi')
	if key == 'pattern_settings':
		for target in changed:
			before = present.get(itemName(key, target))
			if before is None or before['enterprise_setting'] != target['enterprise_setting']:
				raise ValueError('Mẫu chưa có hoặc chính sách kế thừa enterprise không khớp')
			if target['kind'] == 'custom' and target['setting'] == 'not-set':
				raise ValueError('API không hỗ trợ not-set cho mẫu tùy chỉnh')
		plan.append(
			(
				path,
				'PATCH',
				{'expected': current, 'targets': changed},
				{'pattern_settings': [itemName(key, item) for item in changed]},
			)
		)
		return
	for target in changed:
		before = present.get(target['name'])
		value = privateDefinition(target['definition_source'])
		if before is None:
			if target['state'] != 'unpublished' or target['push_protection_enabled']:
				raise ValueError(
					'Tạo lại mẫu cần trạng thái unpublished; chạy thử và xuất bản trên web trước khi bật bảo vệ'
				)
			body = {'patterns': [dict(value, name=target['name'])]}
			endpoint, method = path, 'POST'
		else:
			if any(
				before[field] != target[field]
				for field in ('slug', 'state', 'push_protection_enabled')
			):
				raise ValueError(
					'Đổi slug/trạng thái mẫu cần web; đổi push protection dùng nhóm pattern_settings'
				)
			resourceId, version = ids[target['name']]
			if not isinstance(version, str) or not version:
				raise ValueError('Không đọc được phiên bản mẫu trước khi cập nhật')
			body = dict(value, custom_pattern_version=version)
			endpoint, method = f'{path}/{resourceId}', 'PATCH'
		# Regex có thể chứa ví dụ nhạy cảm: toàn bộ body chỉ tồn tại trong bộ nhớ riêng tư.
		alias = localdata.captureValue(f'{path}/request', json.dumps(body))
		plan.append(
			(endpoint, method, {'$captured_body': alias}, {'custom_pattern': target['name']})
		)


def resolvePlanBody(path, body):
	"""Giải payload ngay trước ghi; phiên bản chính sách được đọc lại sau cập nhật định nghĩa."""
	if isinstance(body, dict) and set(body) == {'$captured_body'}:
		return json.loads(localdata.capturedValue(body['$captured_body']))
	if not path.endswith('/' + GROUP_PATHS['pattern_settings']):
		return body
	base = path.removesuffix('/' + GROUP_PATHS['pattern_settings'])
	current, ids = readDetails(base, 'pattern_settings')
	present = {itemName('pattern_settings', item): item for item in current}
	if present != {itemName('pattern_settings', item): item for item in body['expected']}:
		raise ValueError('Chính sách mẫu thay đổi trước khi ghi; dừng để đối chiếu')
	result = {'pattern_config_version': ids['version']}
	for target in body['targets']:
		tokenType, version = ids[itemName('pattern_settings', target)]
		item = {'token_type': tokenType, 'push_protection_setting': target['setting']}
		if target['kind'] == 'custom':
			if not isinstance(version, str) or not version:
				raise ValueError('Không đọc được phiên bản mẫu trước khi đổi bảo vệ')
			item['custom_pattern_version'] = version
		result.setdefault(f'{target["kind"]}_pattern_settings', []).append(item)
	return result


def validateResponse(path, method, response, changes):
	"""Không tiếp tục sau phản hồi thành công HTTP nhưng thiếu xác nhận đúng tài nguyên."""
	if not ('custom_pattern' in changes or 'pattern_settings' in changes):
		return
	data = json.loads(response)
	if 'pattern_settings' in changes:
		valid = isinstance(data, dict) and isinstance(data.get('pattern_config_version'), str)
	else:
		items = (
			data.get('created_patterns') if isinstance(data, dict) and method == 'POST' else [data]
		)
		valid = (
			isinstance(items, list)
			and len(items) == 1
			and isinstance(items[0], dict)
			and items[0].get('name') == changes['custom_pattern']
			and type(items[0].get('id')) is int
			and items[0]['id'] > 0
		)
	if not valid:
		raise ValueError('API chưa xác nhận kết quả cài đặt mẫu; dừng trước bước tiếp theo')
