"""Khôi phục cấu hình mạng, quyền vai trò cho team và IP allow list theo phạm vi tổ chức."""

import ipaddress
import re
from urllib.parse import quote

from orgsetup import github, localdata, resources

GROUP_PATHS = {
	'network_configurations': 'settings/network-configurations',
	'organization_roles': 'organization-roles',
	'ip_allow_list': 'ip-allow-list',
}
NETWORK_FIELDS = (
	'name',
	'compute_service',
	'network_settings_ids',
	'failover_network_settings_ids',
	'failover_network_enabled',
)
ROLE_FIELDS = ('name', 'description', 'source', 'base_role', 'permissions', 'teams')
IP_QUERY = """query($login:String!,$after:String){organization(login:$login){
	id login ipAllowListEnabledSetting ipAllowListForInstalledAppsEnabledSetting
	ipAllowListEntries(first:100,after:$after){totalCount
		nodes{id allowListValue name isActive owner{__typename ... on Organization{id login}}}
		pageInfo{hasNextPage endCursor}}}}"""


def validateGroup(key, items):
	if not isinstance(items, list):
		raise TypeError('Tài nguyên tổ chức phải là danh sách')
	names = set()
	for item in items:
		if not isinstance(item, dict):
			raise TypeError('Tài nguyên tổ chức phải là object')
		if key == 'network_configurations':
			if set(item) - set(NETWORK_FIELDS) or not {
				'name',
				'compute_service',
				'network_settings_ids',
			} <= set(item):
				raise ValueError('Cấu hình mạng thiếu trường hoặc chứa metadata')
			if not isinstance(item['name'], str) or not re.fullmatch(
				r'[A-Za-z0-9._-]{1,100}', item['name']
			):
				raise ValueError('Cấu hình mạng có tên không hợp lệ')
			if item['compute_service'] not in ('none', 'actions', 'codespaces'):
				raise ValueError('Cấu hình mạng có compute_service không hợp lệ')
			for field in ('network_settings_ids', 'failover_network_settings_ids'):
				values = item.get(field, [])
				if (
					not isinstance(values, list)
					or len(values) > 1
					or any(
						not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', value)
						for value in values
					)
				):
					raise ValueError('Cấu hình mạng cần ID tài nguyên cloud hợp lệ')
			if (
				'failover_network_enabled' in item
				and type(item['failover_network_enabled']) is not bool
			):
				raise ValueError('Cấu hình mạng có cờ failover không hợp lệ')
			if item.get('failover_network_enabled') and not item.get(
				'failover_network_settings_ids'
			):
				raise ValueError('Bật failover cần network settings dự phòng')
			name = item['name']
		elif key == 'organization_roles':
			if (
				set(item) - set(ROLE_FIELDS)
				or not (set(ROLE_FIELDS) - {'description'}) <= set(item)
				or not isinstance(item['name'], str)
				or not item['name']
			):
				raise ValueError('Vai trò tổ chức thiếu trường hoặc chứa metadata')
			if not isinstance(item.get('description'), (str, type(None))):
				raise ValueError('Vai trò tổ chức có mô tả sai kiểu')
			if item['source'] not in ('Organization', 'Enterprise', 'Predefined') or item[
				'base_role'
			] not in (None, 'read', 'triage', 'write', 'maintain', 'admin'):
				raise ValueError('Vai trò tổ chức có nguồn hoặc base_role không hợp lệ')
			for field in ('permissions', 'teams'):
				values = item[field]
				if (
					not isinstance(values, list)
					or any(not isinstance(value, str) or not value for value in values)
					or len(values) != len(set(values))
				):
					raise ValueError('Vai trò tổ chức cần danh sách quyền và team không trùng')
			if any(not re.fullmatch(r'[A-Za-z0-9_-]+', slug) for slug in item['teams']):
				raise ValueError('Vai trò tổ chức có slug team không hợp lệ')
			name = item['name']
		elif key == 'ip_allow_list':
			if (
				len(items) != 1
				or set(item) != {'enabled', 'apps_enabled', 'entries'}
				or type(item['enabled']) is not bool
				or type(item['apps_enabled']) is not bool
				or not isinstance(item['entries'], list)
			):
				raise ValueError('IP allow list cần một chính sách đầy đủ')
			references = set()
			for entry in item['entries']:
				if (
					not isinstance(entry, dict)
					or set(entry) != {'value_source', 'name_source', 'is_active'}
					or type(entry['is_active']) is not bool
				):
					raise ValueError('IP allow list có entry không hợp lệ')
				for field in ('value_source', 'name_source'):
					if not isinstance(entry[field], str) or not re.fullmatch(
						r'orgs/[^#]+#[a-f0-9]{32}', entry[field]
					):
						raise ValueError('IP allow list có tham chiếu không hợp lệ')
				if entry['value_source'] in references:
					raise ValueError('IP allow list có entry trùng')
				references.add(entry['value_source'])
			name = 'policy'
		else:
			raise ValueError('Nhóm tài nguyên tổ chức không được hỗ trợ')
		if name in names:
			raise ValueError('Tài nguyên tổ chức trùng tên')
		names.add(name)
	return items


def readDetails(base, key):
	if base != f'orgs/{github.ORG}':
		raise ValueError('Tài nguyên chỉ hỗ trợ tổ chức đã khai báo')
	if key == 'ip_allow_list':
		return readIpAllowList(base)
	path = f'{base}/{GROUP_PATHS[key]}'
	items = resources.readCollection(
		path, 'roles' if key == 'organization_roles' else 'network_configurations'
	)
	result, ids = [], {}
	for item in items:
		if not isinstance(item, dict):
			raise TypeError('API trả tài nguyên tổ chức sai kiểu')
		name, resourceId = item.get('name'), item.get('id')
		validId = (
			type(resourceId) is int and resourceId > 0
			if key == 'organization_roles'
			else isinstance(resourceId, str) and bool(re.fullmatch(r'[A-Za-z0-9_-]+', resourceId))
		)
		if not isinstance(name, str) or name in ids or not validId or resourceId in ids.values():
			raise ValueError('Không xác minh được tên hoặc ID tài nguyên tổ chức')
		if key == 'network_configurations':
			value = {field: item[field] for field in NETWORK_FIELDS if field in item}
		else:
			value = {field: item.get(field) for field in ROLE_FIELDS if field != 'teams'}
			value['teams'] = []
			for team in github.ghList(f'{path}/{resourceId}/teams'):
				if (
					not isinstance(team, dict)
					or team.get('assignment') not in ('direct', 'indirect', 'mixed')
					or team.get('type') not in ('organization', 'enterprise')
					or not isinstance(team.get('slug'), str)
				):
					raise ValueError('Không xác minh được nguồn gán vai trò cho team')
				if team['assignment'] in ('direct', 'mixed'):
					if team['type'] != 'organization':
						raise ValueError('Gán vai trò cho team enterprise cần nguồn cấp enterprise')
					value['teams'].append(team['slug'])
			value['teams'].sort()
		ids[name] = resourceId
		result.append(value)
	return validateGroup(key, result), ids


def graphqlResult(data):
	if not isinstance(data, dict) or data.get('errors') or not isinstance(data.get('data'), dict):
		raise ValueError('GraphQL chưa đọc hoặc ghi được đầy đủ tài nguyên tổ chức')
	return data['data']


def readIpAllowList(base):
	entries, ids, total, cursor, identity, policy = [], {}, None, None, None, None
	seenCursors = set()
	while True:
		arguments = ['api', 'graphql', '-f', f'query={IP_QUERY}', '-f', f'login={github.ORG}']
		if cursor is not None:
			arguments.extend(['-f', f'after={cursor}'])
		org = graphqlResult(github.ghJson(*arguments)).get('organization')
		if (
			not isinstance(org, dict)
			or not isinstance(org.get('login'), str)
			or org['login'].casefold() != github.ORG.casefold()
			or not isinstance(org.get('id'), str)
			or not org['id']
		):
			raise ValueError('Không xác minh được chủ IP allow list')
		states = (
			org.get('ipAllowListEnabledSetting'),
			org.get('ipAllowListForInstalledAppsEnabledSetting'),
		)
		if any(state not in ('ENABLED', 'DISABLED') for state in states):
			raise ValueError('Không đọc được cờ IP allow list; không suy đoán tắt')
		currentPolicy = {'enabled': states[0] == 'ENABLED', 'apps_enabled': states[1] == 'ENABLED'}
		connection = org.get('ipAllowListEntries')
		if (
			not isinstance(connection, dict)
			or type(connection.get('totalCount')) is not int
			or connection['totalCount'] < 0
			or not isinstance(connection.get('nodes'), list)
		):
			raise ValueError('IP allow list thiếu trang hoặc tổng dữ liệu')
		if identity is not None and (
			identity != org['id'] or policy != currentPolicy or total != connection['totalCount']
		):
			raise ValueError('IP allow list thay đổi trong lúc đọc')
		identity, policy, total = org['id'], currentPolicy, connection['totalCount']
		for entry in connection['nodes']:
			if (
				not isinstance(entry, dict)
				or not isinstance(entry.get('id'), str)
				or not entry['id']
				or type(entry.get('isActive')) is not bool
				or not isinstance(entry.get('allowListValue'), str)
				or not isinstance(entry.get('name'), (str, type(None)))
			):
				raise ValueError('IP allow list có dữ liệu entry không hợp lệ')
			owner = entry.get('owner')
			if (
				not isinstance(owner, dict)
				or owner.get('__typename') != 'Organization'
				or owner.get('id') != identity
				or not isinstance(owner.get('login'), str)
				or owner['login'].casefold() != github.ORG.casefold()
			):
				raise ValueError('IP allow list kế thừa cần nguồn đúng cấp')
			validateNetwork(entry['allowListValue'])
			alias = localdata.captureValue(f'{base}/ip-allow-list/value', entry['allowListValue'])
			if alias in ids or entry['id'] in ids.values():
				raise ValueError('IP allow list trùng địa chỉ hoặc ID')
			ids[alias] = entry['id']
			entries.append(
				{
					'value_source': alias,
					'name_source': localdata.captureValue(
						f'{base}/ip-allow-list/name', entry['name'] or ''
					),
					'is_active': entry['isActive'],
				}
			)
		page = connection.get('pageInfo')
		if not isinstance(page, dict) or type(page.get('hasNextPage')) is not bool:
			raise ValueError('IP allow list thiếu thông tin phân trang')
		if not page['hasNextPage']:
			break
		cursor = page.get('endCursor')
		if not isinstance(cursor, str) or not cursor or cursor in seenCursors:
			raise ValueError('IP allow list có cursor không hợp lệ')
		seenCursors.add(cursor)
	if len(entries) != total:
		raise ValueError('Chưa đọc đủ IP allow list')
	policy['entries'] = entries
	ids['owner'] = identity
	return validateGroup('ip_allow_list', [policy]), ids


def summary(key, item):
	if key == 'organization_roles':
		return dict(
			item,
			description=item.get('description'),
			permissions=sorted(item['permissions']),
			teams=sorted(item['teams']),
		)
	if key == 'ip_allow_list':
		return dict(item, entries=sorted(item['entries'], key=lambda entry: entry['value_source']))
	return item


def collectionChanges(plan, base, key, live, targets, resourceCache):
	validateGroup(key, targets)
	if not targets:
		return
	if key == 'ip_allow_list':
		ipAllowListChanges(plan, base, live, targets)
		return
	present = {item['name']: item for item in live}
	changed = [
		item
		for item in targets
		if summary(key, item) != summary(key, present.get(item['name'], item))
		or item['name'] not in present
	]
	if not changed:
		return
	details, ids = readDetails(base, key)
	if {item['name']: summary(key, item) for item in details} != {
		name: summary(key, item) for name, item in present.items()
	}:
		raise ValueError('Tài nguyên tổ chức thay đổi trong lúc lập kế hoạch')
	path = f'{base}/{GROUP_PATHS[key]}'
	for target in changed:
		name = target['name']
		before = present.get(name)
		if key == 'network_configurations':
			if target['compute_service'] == 'codespaces':
				raise ValueError(
					'API mạng chỉ ghi compute_service none/actions; Codespaces cần luồng riêng'
				)
			if before is None and len(target['network_settings_ids']) != 1:
				raise ValueError('Tạo cấu hình mạng cần network settings có sẵn từ cloud')
			for resourceId in target['network_settings_ids'] + target.get(
				'failover_network_settings_ids', []
			):
				setting = github.ghJson(
					'api', f'{base}/settings/network-settings/{quote(resourceId, safe="")}'
				)
				if not isinstance(setting, dict) or setting.get('id') != resourceId:
					raise ValueError('Không xác minh được network settings từ cloud')
			plan.append(
				(
					path if before is None else f'{path}/{quote(ids[name], safe="")}',
					'POST' if before is None else 'PATCH',
					target,
					{'network_configuration': name},
				)
			)
		else:
			if before is None or any(
				summary(key, before)[field] != summary(key, target)[field]
				for field in ROLE_FIELDS
				if field != 'teams'
			):
				raise ValueError(
					'Định nghĩa vai trò phải tồn tại và khớp quyền; API hiện hành chỉ đọc định nghĩa'
				)
			for slug in target['teams']:
				if slug in before['teams']:
					continue
				known = resourceCache.get('planned_teams', set())
				if slug not in known:
					team = github.ghJson('api', f'{base}/teams/{quote(slug, safe="")}')
					if not isinstance(team, dict) or team.get('slug') != slug:
						raise ValueError('Không xác minh được team cần gán vai trò')
				plan.append(
					(
						f'{path}/teams/{quote(slug, safe="")}/{ids[name]}',
						'PUT',
						None,
						{'organization_role': name, 'team': slug},
					)
				)
			if any(slug not in target['teams'] for slug in before['teams']):
				raise ValueError(
					'Thu hồi vai trò cần quyết định riêng; không tự xóa quyền ngoài nguồn'
				)


def mutationStep(name, inputType, values, changes):
	query = f'mutation($input:{inputType}!){{{name}(input:$input){{clientMutationId}}}}'
	return ('graphql', 'POST', {'query': query, 'variables': {'input': values}}, changes)


def validateNetwork(value):
	try:
		ipaddress.ip_network(value, strict=False)
	except ValueError:
		raise ValueError('Địa chỉ IP hoặc CIDR trong tệp riêng không hợp lệ') from None


def ipAllowListChanges(plan, base, live, targets):
	if not live:
		raise ValueError('IP allow list chưa đọc được chính sách')
	before, target = live[0], targets[0]
	if summary('ip_allow_list', before) == summary('ip_allow_list', target):
		return
	details, ids = readIpAllowList(base)
	if summary('ip_allow_list', details[0]) != summary('ip_allow_list', before):
		raise ValueError('IP allow list thay đổi trong lúc lập kế hoạch')
	present = {entry['value_source']: entry for entry in before['entries']}
	for entry in target['entries']:
		alias = entry['value_source']
		validateNetwork(localdata.privateValue(alias))
		localdata.privateValue(entry['name_source'])
		if present.get(alias) == entry:
			continue
		values = {
			'allowListValue': {'$local_value': alias},
			'name': {'$local_value': entry['name_source']},
			'isActive': entry['is_active'],
		}
		if alias in present:
			values['ipAllowListEntryId'] = ids[alias]
			name, inputType = 'updateIpAllowListEntry', 'UpdateIpAllowListEntryInput'
		else:
			values['ownerId'] = ids['owner']
			name, inputType = 'createIpAllowListEntry', 'CreateIpAllowListEntryInput'
		plan.append(mutationStep(name, inputType, values, {'ip_allow_list_entry': alias}))
	for field, name, inputType in (
		(
			'apps_enabled',
			'updateIpAllowListForInstalledAppsEnabledSetting',
			'UpdateIpAllowListForInstalledAppsEnabledSettingInput',
		),
		('enabled', 'updateIpAllowListEnabledSetting', 'UpdateIpAllowListEnabledSettingInput'),
	):
		if before[field] != target[field]:
			step = mutationStep(
				name,
				inputType,
				{
					'ownerId': ids['owner'],
					'settingValue': 'ENABLED' if target[field] else 'DISABLED',
				},
				{'ip_allow_list': {field: target[field]}},
			)
			if target[field]:
				plan.append(step)
			else:
				plan.insert(0, step)


def finalizePlan(plan):
	"""Bật giới hạn IP sau các cập nhật khác để không chặn request khôi phục đang chạy."""

	def enablesIp(step):
		body = step[2]
		return (
			step[0] == 'graphql'
			and isinstance(body, dict)
			and 'EnabledSettingInput' in body.get('query', '')
			and body.get('variables', {}).get('input', {}).get('settingValue') == 'ENABLED'
		)

	return [step for step in plan if not enablesIp(step)] + [
		step for step in plan if enablesIp(step)
	]
