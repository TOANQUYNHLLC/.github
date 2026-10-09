"""Bản khôi phục private registries; credentials do quản trị cung cấp, không xuất từ GitHub."""

import base64
import binascii
import json
import re
from urllib.parse import quote, urlsplit

from orgsetup import github, localdata, resources

GROUP_PATH = 'private-registries'
REGISTRY_TYPES = (
	'maven_repository',
	'nuget_feed',
	'goproxy_server',
	'npm_registry',
	'rubygems_server',
	'cargo_registry',
	'composer_repository',
	'docker_registry',
	'git_source',
	'helm_registry',
	'hex_organization',
	'hex_repository',
	'pub_repository',
	'python_index',
	'terraform_registry',
)
AUTH_FIELDS = {
	'token': (),
	'username_password': (),
	'oidc_azure': ('tenant_id', 'client_id'),
	'oidc_aws': ('aws_region', 'account_id', 'role_name', 'domain', 'domain_owner'),
	'oidc_jfrog': ('jfrog_oidc_provider_name',),
	'oidc_cloudsmith': ('namespace', 'service_slug', 'audience'),
	'oidc_gcp': ('workload_identity_provider',),
}
OPTIONAL_AUTH_FIELDS = {
	'oidc_aws': ('audience',),
	'oidc_jfrog': ('audience', 'identity_mapping_name'),
	'oidc_cloudsmith': ('api_host',),
	'oidc_gcp': ('audience', 'service_account'),
}
DEFINITION_FIELDS = {
	'registry_type',
	'url',
	'username',
	'replaces_base',
	'auth_type',
	*(field for fields in AUTH_FIELDS.values() for field in fields),
	*(field for fields in OPTIONAL_AUTH_FIELDS.values() for field in fields),
}


def definition(data):
	if not isinstance(data, dict) or set(data) - DEFINITION_FIELDS:
		raise ValueError('Định nghĩa registry chứa trường ngoài hợp đồng')
	result = dict({'username': None, 'replaces_base': False, 'auth_type': 'token'}, **data)
	if result.get('registry_type') not in REGISTRY_TYPES or result['auth_type'] not in AUTH_FIELDS:
		raise ValueError('Registry có loại hoặc phương thức xác thực không hợp lệ')
	if not isinstance(result.get('url'), str) or not result['url']:
		raise ValueError('Registry thiếu URL; không suy đoán giá trị bị ẩn')
	try:
		parsed = urlsplit(result['url'])
		if not parsed.scheme or not parsed.netloc or parsed.username or parsed.password:
			raise ValueError('URL registry không hợp lệ hoặc chứa credentials')
	except ValueError:
		raise ValueError('URL registry không hợp lệ hoặc chứa credentials') from None
	if (
		not isinstance(result['username'], (str, type(None)))
		or type(result['replaces_base']) is not bool
	):
		raise ValueError('Registry có username hoặc replaces_base sai kiểu')
	authType = result['auth_type']
	allowed = {
		'registry_type',
		'url',
		'username',
		'replaces_base',
		'auth_type',
		*AUTH_FIELDS[authType],
		*OPTIONAL_AUTH_FIELDS.get(authType, ()),
	}
	if set(result) - allowed:
		raise ValueError('Registry chứa tham số của phương thức xác thực khác')
	for field in AUTH_FIELDS[authType]:
		if not isinstance(result.get(field), str) or not result[field]:
			raise ValueError('Registry thiếu tham số OIDC bắt buộc')
	for field in OPTIONAL_AUTH_FIELDS.get(authType, ()):
		if field in result and (not isinstance(result[field], str) or not result[field]):
			raise ValueError('Registry có tham số OIDC sai kiểu')
	return result


def privateDefinition(reference, captured=False):
	try:
		value = (
			localdata.capturedValue(reference) if captured else localdata.privateValue(reference)
		)
		return definition(json.loads(value))
	except (ValueError, TypeError):
		raise ValueError('Thiếu hoặc sai định nghĩa registry trong tệp riêng tư') from None


def validateGroup(items):
	if not isinstance(items, list):
		raise TypeError('Private registries phải là danh sách')
	names = set()
	for item in items:
		if (
			not isinstance(item, dict)
			or set(item)
			!= {
				'name',
				'definition_source',
				'credential_source',
				'visibility',
				'selected_repositories',
			}
			or not isinstance(item['name'], str)
			or not item['name']
			or item['visibility'] not in ('all', 'private', 'selected')
			or not isinstance(item['definition_source'], str)
			or not re.fullmatch(r'orgs/[^#]+#[a-f0-9]{32}', item['definition_source'])
			or item['credential_source'] != item['definition_source'] + '/credential'
		):
			raise ValueError('Private registry thiếu trường hoặc chứa metadata')
		repos = item['selected_repositories']
		if (
			not isinstance(repos, list)
			or any(
				not isinstance(repo, str)
				or not re.fullmatch(rf'{re.escape(github.ORG)}/[A-Za-z0-9_.-]+', repo)
				or repo.split('/')[-1] in ('.', '..')
				for repo in repos
			)
			or len(repos) != len({repo.casefold() for repo in repos})
			or (item['visibility'] != 'selected' and repos)
		):
			raise ValueError('Private registry có danh sách repository không hợp lệ')
		if item['name'] in names:
			raise ValueError('Private registry trùng tên')
		names.add(item['name'])
	return items


def readDetails(base):
	if base != f'orgs/{github.ORG}':
		raise ValueError('Private registries chỉ hỗ trợ tổ chức đã khai báo')
	path = f'{base}/{GROUP_PATH}'
	result = []
	for item in resources.readCollection(path, 'configurations'):
		if not isinstance(item, dict) or not isinstance(item.get('name'), str) or not item['name']:
			raise ValueError('Private registry thiếu tên')
		data = github.ghJson('api', f'{path}/{quote(item["name"], safe="")}')
		if not isinstance(data, dict) or data.get('name') != item['name']:
			raise ValueError('Không xác minh được private registry theo tên')
		value = definition({field: data[field] for field in DEFINITION_FIELDS if field in data})
		alias = localdata.captureValue(f'{path}/definition', json.dumps(value, sort_keys=True))
		entry = {
			'name': item['name'],
			'definition_source': alias,
			'credential_source': alias + '/credential',
			'visibility': data['visibility'],
			'selected_repositories': [],
		}
		if entry['visibility'] == 'selected':
			repoIds = data.get('selected_repository_ids')
			if not isinstance(repoIds, list) or any(
				type(repoId) is not int or repoId <= 0 for repoId in repoIds
			):
				raise ValueError('Private registry thiếu danh sách repository được chọn')
			for repoId in repoIds:
				repo = github.ghJson('api', f'repositories/{repoId}')
				if (
					not isinstance(repo, dict)
					or repo.get('id') != repoId
					or not isinstance(repo.get('full_name'), str)
				):
					raise ValueError('Không xác minh được repository của private registry')
				github.validateIdentity(f'repos/{repo["full_name"]}', repo)
				entry['selected_repositories'].append(repo['full_name'])
		result.append(entry)
	return validateGroup(result), {}


def credentials(base, reference):
	"""Nhận sealed box LibSodium do quản trị chuẩn bị; key_id phải khớp khóa GitHub hiện tại."""
	try:
		value = json.loads(localdata.privateValue(reference))
		if (
			not isinstance(value, dict)
			or set(value) != {'encrypted_value', 'key_id'}
			or not isinstance(value['encrypted_value'], str)
			or not isinstance(value['key_id'], str)
		):
			raise ValueError('Credentials registry sai cấu trúc')
		if len(base64.b64decode(value['encrypted_value'], validate=True)) < 48:
			raise ValueError('Credentials registry chưa được mã hóa bằng sealed box')
		key = github.ghJson('api', f'{base}/{GROUP_PATH}/public-key')
		if not isinstance(key, dict) or not key.get('key_id') or value['key_id'] != key['key_id']:
			raise ValueError('Credentials registry cần mã hóa lại bằng khóa hiện tại')
		return value
	except (ValueError, TypeError, binascii.Error):
		raise ValueError(
			'Thiếu/sai credentials registry hoặc khóa mã hóa đã đổi; chuẩn bị lại ở tệp riêng tư'
		) from None


def collectionChanges(plan, base, current, targets, resourceCache):
	validateGroup(targets)
	present = {item['name']: item for item in current}
	definitions = {
		item['name']: privateDefinition(item['definition_source'], captured=True)
		for item in current
	}
	changed = []
	identities = set()
	for target in targets:
		value = privateDefinition(target['definition_source'])
		identity = (value['registry_type'], value['url'])
		if identity in identities:
			raise ValueError('Private registry trùng loại và URL')
		identities.add(identity)
		# POST không nhận tên: tìm lại tên GitHub cấp theo loại và URL khi khôi phục sang tài nguyên mới.
		matches = [
			item
			for item in current
			if (definitions[item['name']]['registry_type'], definitions[item['name']]['url'])
			== identity
		]
		if len(matches) > 1:
			raise ValueError('Private registry có nhiều tài nguyên cùng loại và URL')
		before = present.get(target['name']) or (matches[0] if matches else None)
		previous = definitions[before['name']] if before else None
		if (
			before
			and previous == value
			and before['visibility'] == target['visibility']
			and sorted(before['selected_repositories']) == sorted(target['selected_repositories'])
		):
			continue
		if previous and previous['auth_type'] != value['auth_type']:
			raise ValueError('API không đổi được auth_type của registry đang có; cần xử lý riêng')
		if previous and set(previous) - set(value):
			raise ValueError('API không có hợp đồng xóa tham số OIDC đã lưu; cần xử lý riêng')
		body = dict(value, visibility=target['visibility'])
		if target['visibility'] == 'selected':
			body['selected_repository_ids'] = resources.repositoryIds(
				target['selected_repositories'], resourceCache
			)
		if value['auth_type'] in ('token', 'username_password') and (
			before is None
			or any(
				previous[field] != value[field] for field in ('registry_type', 'url', 'username')
			)
		):
			body.update(credentials(base, target['credential_source']))
		alias = localdata.captureValue(f'{base}/{GROUP_PATH}/request', json.dumps(body))
		path = f'{base}/{GROUP_PATH}' + (f'/{quote(before["name"], safe="")}' if before else '')
		changed.append(
			(
				path,
				'PATCH' if before else 'POST',
				{'$captured_body': alias},
				{'private_registry': target['name']},
			)
		)
	if changed:
		latest, _ = readDetails(base)
		if {item['name']: item for item in latest} != present:
			raise ValueError(
				'Private registries thay đổi trong lúc lập kế hoạch; đọc lại trước khi ghi'
			)
		plan.extend(changed)


def validatePlanBody(path, body):
	if 'encrypted_value' not in body:
		return
	base = path.split('/' + GROUP_PATH, 1)[0]
	key = github.ghJson('api', f'{base}/{GROUP_PATH}/public-key')
	if not isinstance(key, dict) or not key.get('key_id') or body['key_id'] != key['key_id']:
		raise ValueError('Khóa mã hóa registry đã đổi trước khi ghi; mã hóa lại credentials')


def validateResponse(response, expected):
	data = json.loads(response)
	if not isinstance(data, dict) or not isinstance(data.get('name'), str) or not data['name']:
		raise ValueError('API chưa xác nhận tên private registry')
	value = definition({field: data[field] for field in DEFINITION_FIELDS if field in data})
	if (
		value != {field: expected[field] for field in DEFINITION_FIELDS if field in expected}
		or data.get('visibility') != expected['visibility']
	):
		raise ValueError('API chưa xác nhận cấu hình private registry vừa gửi')
