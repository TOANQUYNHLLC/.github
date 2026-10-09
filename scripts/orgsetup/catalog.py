"""Hợp đồng tài nguyên cài đặt: nhập cấu hình có thể ghi, giải ID mới và lập kế hoạch khôi phục.

Nguồn tổng quát giữ cài đặt đang có trên GitHub; các lệnh thiết lập chính sách dùng nguồn riêng.
Giá trị variables, URL webhook, regex và định nghĩa registry lưu riêng ngoài repository; không lấy secrets hoặc hồ sơ người dùng.
"""

import copy
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from orgsetup import (
	branches,
	enterprise,
	github,
	hosted,
	localdata,
	patterns,
	policies,
	registries,
	resources,
	rulesets,
)

STATUS = ('enabled', 'disabled', 'not_set')
SECURITY_FIELDS = {
	'name': str,
	'description': (str, type(None)),
	'advanced_security': ('enabled', 'disabled', 'code_security', 'secret_protection'),
	'enforcement': ('enforced', 'unenforced'),
	**dict.fromkeys(
		(
			'code_security',
			'dependency_graph',
			'dependency_graph_autosubmit_action',
			'dependabot_alerts',
			'dependabot_security_updates',
			'dependabot_delegated_alert_dismissal',
			'code_scanning_default_setup',
			'code_scanning_delegated_alert_dismissal',
			'secret_protection',
			'secret_scanning',
			'secret_scanning_push_protection',
			'secret_scanning_delegated_bypass',
			'secret_scanning_validity_checks',
			'secret_scanning_non_provider_patterns',
			'secret_scanning_generic_secrets',
			'secret_scanning_delegated_alert_dismissal',
			'secret_scanning_extended_metadata',
			'private_vulnerability_reporting',
		),
		STATUS,
	),
	'dependency_graph_autosubmit_action_options': {'labeled_runners': bool},
	'code_scanning_options': {'allow_advanced': (bool, type(None))},
	'code_scanning_default_setup_options': {
		'runner_type': ('standard', 'labeled', 'not_set'),
		'runner_label': (str, type(None)),
	},
	'secret_scanning_delegated_bypass_options': {'reviewers': list},
}
PROPERTY_FIELDS = {
	'property_name': str,
	'value_type': ('string', 'single_select', 'multi_select', 'true_false', 'url'),
	'required': bool,
	'default_value': (str, list, type(None)),
	'description': (str, type(None)),
	'allowed_values': (list, type(None)),
	'values_editable_by': ('org_actors', 'org_and_repo_actors', None),
	'require_explicit_values': bool,
}
GROUP_PATHS = {
	**enterprise.GROUP_PATHS,
	**patterns.GROUP_PATHS,
	**policies.GROUP_PATHS,
	'hosted_runners': hosted.GROUP_PATH,
	'private_registries': registries.GROUP_PATH,
	'branch_protection': 'branch-protection',
	'labels': 'labels',
	'autolinks': 'autolinks',
	'custom_properties': 'properties/values',
	'property_schema': 'properties/schema',
	'security_definitions': 'code-security/configurations',
	'rulesets': 'rulesets',
	'teams': 'teams',
	'environments': 'environments',
	'pages': 'pages',
	'security_managers': 'security-managers',
	'oidc_properties': 'actions/oidc/customization/properties/repo',
	'variables': 'actions/variables',
	'webhooks': 'hooks',
}
ORG_GROUPS = (
	*enterprise.GROUP_PATHS,
	*patterns.GROUP_PATHS,
	*policies.GROUP_PATHS,
	'hosted_runners',
	'private_registries',
	'property_schema',
	'security_definitions',
	'rulesets',
	'teams',
	'security_managers',
	'oidc_properties',
	'variables',
	'webhooks',
)
REPO_GROUPS = (
	'actions_policies',
	'custom_patterns',
	'branch_protection',
	'labels',
	'autolinks',
	'custom_properties',
	'rulesets',
	'environments',
	'pages',
	'variables',
	'webhooks',
)
PAGE_FIELDS = {
	'build_type': ('legacy', 'workflow'),
	'cname': str,
	'https_enforced': bool,
	'source': {'branch': str, 'path': ('/', '/docs')},
}


def checkObject(data, fields, required=()):
	"""Kiểm tra cả object lồng; chỉ nhận trường có hợp đồng ghi, không chấp nhận khóa lạ."""
	if not isinstance(data, dict) or set(data) - set(fields) or set(required) - set(data):
		raise ValueError('Tài nguyên thiếu trường hoặc chứa trường không được hỗ trợ')
	for key, value in data.items():
		expected = fields[key]
		if isinstance(expected, dict):
			if value is not None:
				checkObject(value, expected)
		elif isinstance(expected, tuple):
			valid = (
				type(value) in expected
				if all(isinstance(item, type) for item in expected)
				else (value is None or isinstance(value, str)) and value in expected
			)
			if not valid:
				raise ValueError(f'Tài nguyên: {key} sai kiểu hoặc giá trị')
		elif type(value) is not expected:
			raise ValueError(f'Tài nguyên: {key} sai kiểu')
		if (
			isinstance(value, list)
			and key not in ('reviewers', 'branch_policies', 'variables')
			and any(not isinstance(item, str) for item in value)
		):
			raise ValueError(f'Tài nguyên: {key} phải là danh sách chuỗi')
	return data


def projection(data, fields, required=()):
	if not isinstance(data, dict):
		raise TypeError('Tài nguyên API phải là object')
	result = {key: copy.deepcopy(value) for key, value in data.items() if key in fields}
	checkObject(result, fields, required)
	return result


def validateGroup(key, items):
	if key == 'hosted_runners':
		return hosted.validateGroup(items)
	if key in policies.GROUP_PATHS:
		return policies.validateGroup(key, items)
	if key == 'private_registries':
		return registries.validateGroup(items)
	if key in patterns.GROUP_PATHS:
		return patterns.validateGroup(key, items)
	if key == 'branch_protection':
		return branches.validateGroup(items)
	if key in enterprise.GROUP_PATHS:
		return enterprise.validateGroup(key, items)
	if not isinstance(items, list):
		raise TypeError(f'{key}: phải là danh sách')
	names = set()
	for item in items:
		if key == 'rulesets':
			if set(item) != {
				'name',
				'target',
				'enforcement',
				'conditions',
				'bypass_actors',
				'rules',
			}:
				raise ValueError('Ruleset chứa metadata hoặc thiếu cấu hình')
			rulesets.rulesetSummary(item)
			name = item['name']
		elif key == 'labels':
			checkObject(
				item,
				{'name': str, 'color': str, 'description': (str, type(None))},
				('name', 'color'),
			)
			if not re.fullmatch(r'[0-9a-fA-F]{6}', item['color']):
				raise ValueError('Nhãn có màu không hợp lệ')
			name = item['name'].casefold()
		elif key == 'autolinks':
			checkObject(
				item,
				{'key_prefix': str, 'url_template': str, 'is_alphanumeric': bool},
				('key_prefix', 'url_template', 'is_alphanumeric'),
			)
			if '<num>' not in item['url_template']:
				raise ValueError('Autolink thiếu <num> trong URL')
			name = item['key_prefix']
		elif key == 'property_schema':
			checkObject(item, PROPERTY_FIELDS, ('property_name', 'value_type'))
			name = item['property_name']
		elif key == 'custom_properties':
			checkObject(
				item,
				{'property_name': str, 'value': (str, list, type(None))},
				('property_name', 'value'),
			)
			name = item['property_name']
		elif key == 'security_definitions':
			checkObject(item, SECURITY_FIELDS, ('name',))
			options = item.get('secret_scanning_delegated_bypass_options') or {}
			for reviewer in options.get('reviewers', []):
				checkObject(
					reviewer,
					{
						'reviewer_id': int,
						'reviewer_type': ('TEAM', 'ROLE'),
						'mode': ('ALWAYS', 'EXEMPT'),
					},
					('reviewer_id', 'reviewer_type'),
				)
				if reviewer['reviewer_id'] <= 0:
					raise ValueError('Reviewer bảo mật có ID không hợp lệ')
			name = item['name']
		elif key == 'teams':
			checkObject(
				item,
				{
					'name': str,
					'description': (str, type(None)),
					'privacy': ('secret', 'closed'),
					'notification_setting': ('notifications_enabled', 'notifications_disabled'),
					'parent_team_slug': (str, type(None)),
					'slug': str,
					'repositories': dict,
				},
				(
					'name',
					'slug',
					'privacy',
					'notification_setting',
					'parent_team_slug',
					'repositories',
				),
			)
			if not re.fullmatch(r'[A-Za-z0-9_-]+', item['slug']):
				raise ValueError('Team có slug không hợp lệ')
			for repo, role in item['repositories'].items():
				if (
					not re.fullmatch(rf'{re.escape(github.ORG)}/[A-Za-z0-9_.-]+', repo)
					or not isinstance(role, str)
					or not role
				):
					raise ValueError('Team có tên repository hoặc quyền không hợp lệ')
			name = item['slug']
		elif key == 'environments':
			validateEnvironment(item)
			name = item['name']
		elif key == 'pages':
			checkObject(item, PAGE_FIELDS, ('build_type',))
			if len(items) > 1 or (item['build_type'] == 'legacy' and 'source' not in item):
				raise ValueError('Pages chỉ có một site; chế độ legacy cần source')
			if item.get('source') is not None:
				checkObject(item['source'], PAGE_FIELDS['source'], ('branch', 'path'))
			name = 'site'
		elif key == 'security_managers':
			checkObject(item, {'slug': str}, ('slug',))
			if not re.fullmatch(r'[A-Za-z0-9_-]+', item['slug']):
				raise ValueError('Security manager có slug team không hợp lệ')
			name = item['slug']
		elif key == 'oidc_properties':
			checkObject(item, {'custom_property_name': str}, ('custom_property_name',))
			name = item['custom_property_name']
		elif key == 'variables':
			checkObject(
				item,
				{
					'name': str,
					'value_source': str,
					'visibility': ('all', 'private', 'selected'),
					'selected_repositories': list,
				},
				('name', 'value_source'),
			)
			if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', item['name']) or not re.fullmatch(
				r'(orgs|repos)/[^#]+#[a-f0-9]{32}', item['value_source']
			):
				raise ValueError('Variable có tên hoặc tham chiếu không hợp lệ')
			if (item.get('visibility') == 'selected') != ('selected_repositories' in item):
				raise ValueError('Variable selected cần danh sách repository')
			name = item['name']
		elif key == 'webhooks':
			checkObject(
				item,
				{
					'url_source': str,
					'secret_source': str,
					'name': ('web',),
					'active': bool,
					'events': list,
					'content_type': ('json', 'form'),
					'insecure_ssl': ('0', '1'),
				},
				(
					'url_source',
					'secret_source',
					'name',
					'active',
					'events',
					'content_type',
					'insecure_ssl',
				),
			)
			if (
				not re.fullmatch(r'(orgs|repos)/[^#]+#[a-f0-9]{32}', item['url_source'])
				or item['secret_source'] != item['url_source'] + '/secret'
			):
				raise ValueError('Webhook có tham chiếu không hợp lệ')
			name = item['url_source']
		else:
			raise ValueError(f'Nhóm tài nguyên không được hỗ trợ: {key}')
		if not name.strip() or name in names:
			raise ValueError(f'{key}: tên trống hoặc trùng')
		names.add(name)
	if key == 'teams':
		teamOrder(items)
	return items


def validateReferenceScope(base, key, items):
	if key in policies.GROUP_PATHS:
		policies.validateScope(base, key, items)
	for item in items:
		if key == 'private_registries' and not item['definition_source'].startswith(
			f'{base}/{registries.GROUP_PATH}/definition#'
		):
			raise ValueError('Tham chiếu registry không thuộc phạm vi đang quản lý')
		if key == 'custom_patterns' and not item['definition_source'].startswith(
			f'{base}/{patterns.GROUP_PATHS[key]}/definition#'
		):
			raise ValueError('Tham chiếu định nghĩa mẫu không thuộc phạm vi đang quản lý')
		if key == 'ip_allow_list':
			for entry in item['entries']:
				for field, suffix in (('value_source', 'value'), ('name_source', 'name')):
					if not entry[field].startswith(f'{base}/ip-allow-list/{suffix}#'):
						raise ValueError(
							'Tham chiếu IP allow list không thuộc phạm vi đang quản lý'
						)
		if key == 'variables':
			organization = base.startswith('orgs/')
			if organization != ('visibility' in item):
				raise ValueError(
					'Variable cần visibility ở cấp tổ chức, không dùng ở cấp repository'
				)
		if key == 'variables' and not item['value_source'].startswith(
			f'{variablePath(base)}/{item["name"]}#'
		):
			raise ValueError('Tham chiếu variable không thuộc phạm vi đang quản lý')
		if key == 'webhooks' and not item['url_source'].startswith(f'{base}/hooks/url#'):
			raise ValueError('Tham chiếu webhook không thuộc phạm vi đang quản lý')
		if key == 'environments':
			validateReferenceScope(
				f'{base}/environments/{quote(item["name"], safe="")}',
				'variables',
				item.get('variables', []),
			)


def teamOrder(items):
	pending = {item['slug']: item for item in items}
	ordered = []
	while pending:
		ready = [
			item
			for item in pending.values()
			if item['parent_team_slug'] is None
			or item['parent_team_slug'] in {parent['slug'] for parent in ordered}
		]
		if not ready:
			raise ValueError('Team thiếu cha hoặc có quan hệ vòng')
		ordered.extend(pending.pop(item['slug']) for item in ready)
	return ordered


def validateEnvironment(item):
	checkObject(
		item,
		{
			'name': str,
			'wait_timer': int,
			'prevent_self_review': bool,
			'reviewers': list,
			'deployment_branch_policy': (dict, type(None)),
			'branch_policies': list,
			'variables': list,
		},
		(
			'name',
			'wait_timer',
			'prevent_self_review',
			'reviewers',
			'deployment_branch_policy',
			'branch_policies',
		),
	)
	if not 0 <= item['wait_timer'] <= 43200:
		raise ValueError('Environment có thời gian chờ không hợp lệ')
	policy = item['deployment_branch_policy']
	if policy is not None:
		checkObject(
			policy,
			{'protected_branches': bool, 'custom_branch_policies': bool},
			('protected_branches', 'custom_branch_policies'),
		)
		if policy['protected_branches'] and policy['custom_branch_policies']:
			raise ValueError('Environment có chính sách nhánh mâu thuẫn')
	for reviewer in item['reviewers']:
		checkObject(reviewer, {'type': ('User', 'Team'), 'id': int}, ('type', 'id'))
		if reviewer['id'] <= 0:
			raise ValueError('Environment có reviewer ID không hợp lệ')
	for branch in item['branch_policies']:
		checkObject(branch, {'name': str, 'type': ('branch', 'tag')}, ('name', 'type'))
	if item['branch_policies'] and not (policy or {}).get('custom_branch_policies'):
		raise ValueError('Environment chỉ nhận danh sách nhánh khi bật custom_branch_policies')
	validateGroup('variables', item.get('variables', []))


def readEnvironments(base):
	items = resources.readCollection(f'{base}/environments', 'environments')
	result = []
	for item in items:
		if (
			not isinstance(item, dict)
			or not isinstance(item.get('name'), str)
			or not isinstance(item.get('protection_rules'), list)
		):
			raise TypeError('Environment thiếu tên hoặc quy tắc bảo vệ')
		entry = {
			'name': item['name'],
			'wait_timer': 0,
			'prevent_self_review': False,
			'reviewers': [],
			'deployment_branch_policy': item.get('deployment_branch_policy'),
			'branch_policies': [],
			'variables': readDetails(
				f'{base}/environments/{quote(item["name"], safe="")}', 'variables'
			)[0],
		}
		for rule in item['protection_rules']:
			if rule.get('type') == 'wait_timer':
				entry['wait_timer'] = rule['wait_timer']
			elif rule.get('type') == 'required_reviewers':
				entry['prevent_self_review'] = rule['prevent_self_review']
				entry['reviewers'] = [
					{'type': value['type'], 'id': value['reviewer']['id']}
					for value in rule['reviewers']
				]
			else:
				raise ValueError(
					'Environment có quy tắc bảo vệ Apps chưa thể khôi phục bằng hợp đồng này'
				)
		if (entry['deployment_branch_policy'] or {}).get('custom_branch_policies'):
			path = f'{base}/environments/{quote(item["name"], safe="")}/deployment-branch-policies'
			entry['branch_policies'] = [
				projection(value, {'name': str, 'type': ('branch', 'tag')}, ('name', 'type'))
				for value in resources.readCollection(path, 'branch_policies')
			]
		result.append(entry)
	return validateGroup('environments', result)


def readDetails(base, key):
	"""ID chỉ ở kết quả tạm của lượt đọc; cấu hình JSON không chứa ID tài nguyên cần tạo lại."""
	if key == 'hosted_runners':
		return hosted.readDetails(base)
	if key in policies.GROUP_PATHS:
		return policies.readDetails(base, key)
	if key == 'private_registries':
		return registries.readDetails(base)
	if key in patterns.GROUP_PATHS:
		return patterns.readDetails(base, key)
	if key == 'branch_protection':
		return branches.readDetails(base)
	if key in enterprise.GROUP_PATHS:
		return enterprise.readDetails(base, key)
	path = variablePath(base) if key == 'variables' else f'{base}/{GROUP_PATHS[key]}'
	if key == 'environments':
		return readEnvironments(base), {}
	if key == 'variables':
		items = resources.readCollection(path, 'variables')
		result = []
		for item in items:
			checkObject(
				projection(item, {'name': str, 'value': str}, ('name', 'value')),
				{'name': str, 'value': str},
				('name', 'value'),
			)
			value = {
				'name': item['name'],
				'value_source': localdata.captureValue(f'{path}/{item["name"]}', item['value']),
			}
			if base.startswith('orgs/'):
				value['visibility'] = item['visibility']
				if value['visibility'] == 'selected':
					repos = resources.readCollection(
						f'{path}/{quote(item["name"], safe="")}/repositories', 'repositories'
					)
					value['selected_repositories'] = []
					for repo in repos:
						github.validateIdentity(f'repos/{repo["full_name"]}', repo)
						value['selected_repositories'].append(repo['full_name'])
			result.append(value)
		return validateGroup(key, result), {}
	if key == 'pages':
		try:
			data = github.ghJson('api', path)
		except RuntimeError as exc:
			if not github.isNotFound(exc):
				raise
			identity = github.ghJson('api', base)
			github.validateIdentity(base, identity)
			# Pages công khai không cần nâng cấp; chỉ nhận 404 là không có site khi đã xác minh admin.
			# Repository riêng tư có thể bị ẩn bởi gói, phải giữ lỗi thay vì suy đoán tắt.
			if (
				identity.get('private') is False
				and identity.get('permissions', {}).get('admin') is True
			):
				return [], {}
			raise ValueError('Không xác minh được Pages; 404 có thể do quyền hoặc gói') from exc
		if not isinstance(data, dict):
			raise TypeError('Pages API phải trả object')
		data = dict(data, cname=data.get('cname') or '')
		value = projection(
			{key: value for key, value in data.items() if key != 'source' or value is not None},
			PAGE_FIELDS,
			('build_type',),
		)
		return validateGroup(key, [value]), {}
	if key == 'rulesets':
		endpoint = path if base.startswith('orgs/') else f'{path}?includes_parents=false'
		ids = rulesets.readRulesetIds(endpoint)
		result = []
		for name, resourceId in ids.items():
			item = github.ghJson('api', f'{path}/{resourceId}')
			if (
				not isinstance(item, dict)
				or item.get('id') != resourceId
				or item.get('name') != name
			):
				raise ValueError('Không xác minh được ruleset theo ID')
			result.append(
				{
					key: copy.deepcopy(item[key])
					for key in (
						'name',
						'target',
						'enforcement',
						'conditions',
						'bypass_actors',
						'rules',
					)
					if key in item
				}
			)
		return validateGroup(key, result), ids
	items = github.ghList(path)
	result, ids = [], {}
	for item in items:
		if key == 'webhooks':
			config = item.get('config')
			if not isinstance(config, dict) or not isinstance(config.get('url'), str):
				raise ValueError('Webhook thiếu URL; không suy đoán credentials')
			alias = localdata.captureValue(f'{path}/url', config['url'])
			value = projection(
				item, {'name': str, 'active': bool, 'events': list}, ('name', 'active', 'events')
			)
			value.update(
				url_source=alias,
				secret_source=alias + '/secret',
				content_type=config['content_type'],
				insecure_ssl=config['insecure_ssl'],
			)
			identity = alias
		elif key == 'oidc_properties':
			if item.get('inclusion_source') == 'enterprise':
				raise ValueError('OIDC custom property kế thừa enterprise cần nguồn cấp enterprise')
			value = projection(item, {'custom_property_name': str}, ('custom_property_name',))
			identity = value['custom_property_name']
		elif key == 'security_managers':
			value = projection(item, {'slug': str}, ('slug',))
			identity = value['slug']
		elif key == 'labels':
			value = projection(
				item,
				{'name': str, 'color': str, 'description': (str, type(None))},
				('name', 'color'),
			)
			identity = value['name'].casefold()
		elif key == 'autolinks':
			value = projection(
				item,
				{'key_prefix': str, 'url_template': str, 'is_alphanumeric': bool},
				('key_prefix', 'url_template', 'is_alphanumeric'),
			)
			identity = value['key_prefix']
		elif key == 'property_schema':
			if item.get('source_type') == 'enterprise':
				raise ValueError('Custom property kế thừa enterprise cần nguồn cấp enterprise')
			value = projection(item, PROPERTY_FIELDS, ('property_name', 'value_type'))
			identity = value['property_name']
		elif key == 'custom_properties':
			value = projection(
				item,
				{'property_name': str, 'value': (str, list, type(None))},
				('property_name', 'value'),
			)
			identity = value['property_name']
		elif key == 'security_definitions':
			if item.get('target_type') == 'global':
				continue
			if item.get('target_type') != 'organization':
				raise ValueError('Cấu hình bảo mật không thuộc tổ chức')
			value = projection(item, SECURITY_FIELDS, ('name',))
			identity = value['name']
		elif key == 'teams':
			value = projection(
				item,
				{
					'name': str,
					'description': (str, type(None)),
					'privacy': str,
					'notification_setting': str,
					'slug': str,
				},
				('name', 'privacy', 'notification_setting', 'slug'),
			)
			parent = item.get('parent')
			value['parent_team_slug'] = parent['slug'] if isinstance(parent, dict) else None
			value['repositories'] = {}
			for repo in github.ghList(f'{base}/teams/{quote(value["slug"], safe="")}/repos'):
				github.validateIdentity(f'repos/{repo["full_name"]}', repo)
				role = repo.get('role_name')
				if not role:
					permissions = repo.get('permissions', {})
					role = next(
						(
							name
							for name in ('admin', 'maintain', 'push', 'triage', 'pull')
							if permissions.get(name) is True
						),
						None,
					)
				if role is None:
					raise ValueError('Không đọc được quyền của team trên repository')
				value['repositories'][repo['full_name']] = {'push': 'write', 'pull': 'read'}.get(
					role, role
				)
			identity = value['slug']
		else:
			raise ValueError('Nhóm tài nguyên không được hỗ trợ')
		if key in ('autolinks', 'security_definitions', 'teams', 'webhooks'):
			resourceId = item.get('id')
			if type(resourceId) is not int or resourceId <= 0 or resourceId in ids.values():
				raise ValueError('Tài nguyên thiếu ID hoặc trùng ID')
			ids[identity] = resourceId
		result.append(value)
	return validateGroup(key, result), ids


def readCollections(base, keys=None):
	"""Đọc đầy đủ từng nhóm; lỗi không biến thành danh sách rỗng. GraphQL chỉ lưu bản quan sát ruleset."""
	keys = list(
		keys if keys is not None else ORG_GROUPS if base.startswith('orgs/') else REPO_GROUPS
	)
	collections, observed, unavailable = {}, {}, {}

	def read(key):
		try:
			return key, readDetails(base, key)[0], None
		except (RuntimeError, ValueError, KeyError, TypeError) as exc:
			match = re.search(r'HTTP (\d+)', str(exc))
			return (
				key,
				None,
				f'HTTP {match[1]}' if match else 'Không đọc đủ hoặc không xác minh được cấu hình',
			)

	with ThreadPoolExecutor(max_workers=max(1, min(4, len(keys)))) as pool:
		for key, value, problem in pool.map(read, keys):
			if problem:
				unavailable[f'{base}/{GROUP_PATHS[key]}'] = problem
				if key == 'rulesets' and base.startswith('orgs/'):
					try:
						observed[key] = list(rulesets.readOrgRulesetsGraphql().values())
						unavailable[f'{base}/{GROUP_PATHS[key]}'] += (
							'; GraphQL chỉ đọc một phần, cần REST trước khi khôi phục'
						)
					except (RuntimeError, ValueError, KeyError, TypeError):
						pass
			else:
				collections[key] = value
				if key == 'dependabot_access' and value and 'default_level' not in value[0]:
					unavailable[f'{base}/{GROUP_PATHS[key]}'] = (
						'API không trả default_level; danh sách repository đã lưu, không suy đoán null'
					)
	return collections, observed, unavailable


def itemName(key, item):
	if key == 'dependabot_access':
		return 'policy'
	if key in patterns.GROUP_PATHS:
		return patterns.itemName(key, item)
	if key == 'branch_protection':
		return item['pattern']
	if key == 'ip_allow_list':
		return 'policy'
	if key == 'webhooks':
		return item['url_source']
	if key == 'pages':
		return 'site'
	if key == 'security_managers':
		return item['slug']
	if key == 'oidc_properties':
		return item['custom_property_name']
	return (
		item['name'].casefold()
		if key == 'labels'
		else item['key_prefix']
		if key == 'autolinks'
		else item['property_name']
		if key in ('property_schema', 'custom_properties')
		else item['slug']
		if key == 'teams'
		else item['name']
	)


def itemSummary(key, item):
	if key in policies.GROUP_PATHS:
		return policies.summary(key, item)
	if key == 'branch_protection':
		return branches.summary(item)
	if key in enterprise.GROUP_PATHS:
		return enterprise.summary(key, item)
	if key == 'rulesets':
		return rulesets.rulesetSummary(item)
	if key == 'labels':
		return dict(item, color=item['color'].lower(), description=item.get('description') or '')
	if key == 'teams':
		return dict(item, description=item.get('description') or '')
	if key == 'webhooks':
		return dict(item, events=sorted(set(item['events'])))
	if key == 'variables' and 'selected_repositories' in item:
		return dict(item, selected_repositories=sorted(item['selected_repositories']))
	if key == 'environments':
		return dict(
			item,
			reviewers=sorted(item['reviewers'], key=lambda value: (value['type'], value['id'])),
			branch_policies=sorted(
				item['branch_policies'], key=lambda value: (value['type'], value['name'])
			),
		)
	return item


def itemMatches(key, current, wanted):
	"""So các trường local quản lý; trường mặc định do API thêm không gây vòng lặp ghi."""
	if key in patterns.GROUP_PATHS:
		return patterns.itemMatches(key, current, wanted)
	if current is None:
		return False
	before, after = itemSummary(key, current), itemSummary(key, wanted)
	if key == 'variables':
		return all(
			before.get(field) == value for field, value in after.items() if field != 'value_source'
		) and localdata.capturedValue(current['value_source']) == localdata.privateValue(
			wanted['value_source']
		)
	if key == 'rulesets':
		return before == after
	return all(before.get(field) == value for field, value in after.items())


def collectionChanges(plan, base, current, wanted, resourceCache):
	"""Upsert các mục local; không xóa tài nguyên ngoài nguồn. ID mới được giải khi bước ghi đến lượt."""
	priority = {'teams': 0, 'property_schema': 1, 'security_definitions': 2, 'pattern_settings': 4}
	for key, targets in sorted(
		wanted.get('collections', {}).items(), key=lambda item: priority.get(item[0], 3)
	):
		validateGroup(key, targets)
		if key not in current.get('collections', {}):
			raise ValueError(f'{base}/{GROUP_PATHS[key]}: chưa đọc được; dừng trước khi ghi')
		live = current['collections'][key]
		if key == 'hosted_runners':
			hosted.collectionChanges(plan, base, live, targets, resourceCache)
			continue
		if key in policies.GROUP_PATHS:
			policies.collectionChanges(plan, base, key, live, targets, resourceCache)
			continue
		if key == 'private_registries':
			registries.collectionChanges(plan, base, live, targets, resourceCache)
			continue
		if key in patterns.GROUP_PATHS:
			patterns.collectionChanges(plan, base, key, live, targets)
			continue
		if key == 'branch_protection':
			branches.collectionChanges(plan, base, live, targets)
			continue
		if key == 'teams':
			resourceCache['planned_teams'] = {item['slug'] for item in targets}
		if key in enterprise.GROUP_PATHS:
			if key == 'network_configurations':
				resourceCache['planned_network_configurations'] = {item['name'] for item in targets}
			enterprise.collectionChanges(plan, base, key, live, targets, resourceCache)
			continue
		present = {itemName(key, item): item for item in live}
		changed = [
			item for item in targets if not itemMatches(key, present.get(itemName(key, item)), item)
		]
		if key == 'security_definitions':
			resourceCache['planned_security_configurations'] = {item['name'] for item in targets}
		if not changed:
			continue
		path = variablePath(base) if key == 'variables' else f'{base}/{GROUP_PATHS[key]}'
		if key == 'variables':
			for target in changed:
				localdata.privateValue(target['value_source'])
				body = {'name': target['name'], 'value': {'$local_value': target['value_source']}}
				if 'visibility' in target:
					body['visibility'] = target['visibility']
				if 'selected_repositories' in target:
					body['selected_repository_ids'] = resources.repositoryIds(
						target['selected_repositories'], resourceCache
					)
				method = 'PATCH' if target['name'] in present else 'POST'
				endpoint = f'{path}/{quote(target["name"], safe="")}' if method == 'PATCH' else path
				plan.append((endpoint, method, body, {'variable': target['name']}))
			continue
		if key in ('property_schema', 'custom_properties'):
			plan.append((path, 'PATCH', {'properties': changed}, {key: changed}))
			continue
		if key == 'environments':
			environmentChanges(plan, base, present, changed)
			continue
		if key == 'pages':
			for target in changed:
				if not live:
					create = {
						field: value
						for field, value in target.items()
						if field in ('build_type', 'source')
					}
					plan.append((path, 'POST', create, {'pages': create}))
				plan.append((path, 'PUT', target, {'pages': target}))
			continue
		if key == 'security_managers':
			for target in changed:
				known = {
					item['slug']
					for item in current.get('collections', {}).get('teams', [])
					+ wanted.get('collections', {}).get('teams', [])
				}
				if target['slug'] not in known:
					team = github.ghJson('api', f'{base}/teams/{quote(target["slug"], safe="")}')
					if not isinstance(team, dict) or team.get('slug') != target['slug']:
						raise ValueError('Không xác minh được team cần cấp quyền security manager')
				plan.append(
					(
						f'{path}/teams/{quote(target["slug"], safe="")}',
						'PUT',
						None,
						{'security_manager': target['slug']},
					)
				)
			continue
		if key == 'oidc_properties':
			for target in changed:
				plan.append((path, 'POST', target, target))
			continue
		if key == 'teams':
			teamChanges(plan, base, present, targets)
			continue
		details, ids = readDetails(base, key)
		if {itemName(key, item): itemSummary(key, item) for item in details} != {
			name: itemSummary(key, item) for name, item in present.items()
		}:
			raise ValueError(f'{path}: tài nguyên đã thay đổi trong lúc lập kế hoạch')
		for target in changed:
			name = itemName(key, target)
			body = copy.deepcopy(target)
			if key == 'webhooks':
				localdata.privateValue(target['url_source'])
				config = {
					'url': {'$local_value': target['url_source']},
					'content_type': target['content_type'],
					'insecure_ssl': target['insecure_ssl'],
				}
				body = {
					'name': target['name'],
					'active': target['active'],
					'events': target['events'],
					'config': config,
				}
				if name not in present:
					# API không xuất shared secret: người quản trị phải cung cấp, kể cả chuỗi rỗng có chủ ý.
					localdata.privateValue(target['secret_source'])
					config['secret'] = {'$local_value': target['secret_source']}
					plan.append((path, 'POST', body, {'webhook': target['url_source']}))
				else:
					before = present[name]
					metadataChanged = before['active'] != target['active'] or set(
						before['events']
					) != set(target['events'])
					if metadataChanged:
						# Endpoint tổng có thể xóa secret khi không gửi lại; không suy đoán từ giá trị che.
						localdata.privateValue(target['secret_source'])
						config['secret'] = {'$local_value': target['secret_source']}
						body.pop('name')
						endpoint = f'{path}/{ids[name]}'
					else:
						# PATCH config riêng giữ nguyên secret không được API xuất.
						body = config
						endpoint = f'{path}/{ids[name]}/config'
					plan.append((endpoint, 'PATCH', body, {'webhook': target['url_source']}))
			elif name not in present:
				plan.append((path, 'POST', body, {key: target}))
			elif key == 'labels':
				body['new_name'] = body.pop('name')
				plan.append(
					(
						f'{path}/{quote(present[name]["name"], safe="")}',
						'PATCH',
						body,
						{key: target},
					)
				)
			elif key == 'autolinks':
				# GitHub không có PATCH autolink: chỉ thay đúng prefix đang quản lý.
				plan.append((f'{path}/{ids[name]}', 'DELETE', None, {key: target}))
				plan.append((path, 'POST', body, {key: target}))
			else:
				plan.append(
					(
						f'{path}/{ids[name]}',
						'PUT' if key == 'rulesets' else 'PATCH',
						body,
						{key: target},
					)
				)


def teamChanges(plan, base, present, targets):
	for target in teamOrder(targets):
		before = present.get(target['slug'])
		body = {
			key: value
			for key, value in itemSummary('teams', target).items()
			if key not in ('slug', 'repositories')
		}
		path = f'{base}/teams/{quote(target["slug"], safe="")}'
		if before is None:
			if body['parent_team_slug'] is None:
				body.pop('parent_team_slug')
			plan.append((f'{base}/teams', 'POST', body, {'team': target['slug']}))
		elif any(itemSummary('teams', before).get(key) != value for key, value in body.items()):
			plan.append((path, 'PATCH', body, {'team': target['slug']}))
		for name, role in target['repositories'].items():
			if (before or {}).get('repositories', {}).get(name) != role:
				plan.append(
					(f'{path}/repos/{name}', 'PUT', {'permission': role}, {'permission': role})
				)


def environmentChanges(plan, base, present, targets):
	for target in targets:
		path = f'{base}/environments/{quote(target["name"], safe="")}'
		before = present.get(target['name'])
		body = {
			key: value
			for key, value in target.items()
			if key not in ('name', 'branch_policies', 'variables')
		}
		if before is None or any(before.get(key) != value for key, value in body.items()):
			plan.append((path, 'PUT', body, {'environment': target['name']}))
		previous = (before or {}).get('branch_policies', [])
		for policy in target['branch_policies']:
			if policy not in previous:
				plan.append((f'{path}/deployment-branch-policies', 'POST', policy, policy))
		if any(policy not in target['branch_policies'] for policy in previous):
			raise ValueError(f'{path}: cần xử lý việc bỏ chính sách nhánh trước khi khôi phục')
		collectionChanges(
			plan,
			path,
			{'collections': {'variables': (before or {}).get('variables', [])}},
			{'collections': {'variables': target.get('variables', [])}},
			{},
		)


def variablePath(base):
	return f'{base}/variables' if '/environments/' in base else f'{base}/actions/variables'


def resolvePlanPath(path):
	"""Giải cấu hình bảo mật vừa tạo theo tên; không dùng ID giả hoặc ID từ bản snapshot cũ."""
	marker = '/code-security/configurations/@'
	if marker not in path:
		return path
	from urllib.parse import unquote

	base, suffix = path.split(marker, 1)
	name, action = suffix.split('/', 1)
	entries, ids = readDetails(base, 'security_definitions')
	name = unquote(name)
	if name not in ids or name not in {item['name'] for item in entries}:
		raise ValueError('Không xác minh được ID cấu hình bảo mật vừa tạo')
	return f'{base}/code-security/configurations/{ids[name]}/{action}'
