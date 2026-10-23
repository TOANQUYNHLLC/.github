"""Khôi phục Actions policies và quyền truy cập repository của Dependabot."""

import copy
import json
import re

from orgsetup import github, resources

GROUP_PATHS = {
	'actions_policies': 'actions/policies',
	'dependabot_access': 'dependabot/repository-access',
}
ACTOR_TYPES = (
	'User',
	'Bot',
	'Team',
	'BusinessTeam',
	'EnterpriseTeam',
	'IntegrationInstallation',
	'App',
	'RepositoryRole',
)
EVENTS = frozenset(
	(
		'branch_protection_rule',
		'check_run',
		'check_suite',
		'create',
		'delete',
		'deployment',
		'deployment_status',
		'discussion',
		'discussion_comment',
		'fork',
		'gollum',
		'image_version',
		'issue_comment',
		'issues',
		'label',
		'merge_group',
		'milestone',
		'page_build',
		'project',
		'project_card',
		'project_column',
		'public',
		'pull_request',
		'pull_request_review',
		'pull_request_review_comment',
		'pull_request_target',
		'push',
		'registry_package',
		'release',
		'repository_dispatch',
		'schedule',
		'status',
		'watch',
		'workflow_call',
		'workflow_dispatch',
		'workflow_run',
	)
)


def stringList(values):
	if (
		not isinstance(values, list)
		or any(not isinstance(value, str) or not value for value in values)
		or len(values) != len(set(values))
	):
		raise ValueError('Chính sách cần danh sách chuỗi không rỗng và không trùng')


def repositoryNames(values):
	stringList(values)
	if any(
		not re.fullmatch(rf'{re.escape(github.ORG)}/[A-Za-z0-9_.-]+', value)
		or value.rsplit('/', 1)[-1] in ('.', '..')
		for value in values
	) or len(values) != len({value.casefold() for value in values}):
		raise ValueError('Chính sách có repository ngoài tổ chức hoặc trùng tên')


def validateConditions(conditions):
	if not isinstance(conditions, dict) or set(conditions) - {
		'repository_name',
		'selected_repositories',
		'repository_property',
		'workflow_path',
	}:
		raise ValueError('Actions policy có điều kiện không được hỗ trợ')
	if len(set(conditions) - {'workflow_path'}) > 1:
		raise ValueError('Actions policy chỉ nhận một kiểu chọn repository')
	for field, value in conditions.items():
		if field == 'selected_repositories':
			repositoryNames(value)
			continue
		if (
			not isinstance(value, dict)
			or not {'include', 'exclude'} <= set(value)
			or set(value)
			- {'include', 'exclude', *(['protected'] if field == 'repository_name' else [])}
		):
			raise ValueError('Actions policy có điều kiện thiếu trường hoặc chứa metadata')
		if 'protected' in value and type(value['protected']) is not bool:
			raise ValueError('Actions policy có cờ protected sai kiểu')
		if field != 'repository_property':
			stringList(value['include'])
			stringList(value['exclude'])
		else:
			for entries in (value['include'], value['exclude']):
				if not isinstance(entries, list):
					raise TypeError('Actions policy cần danh sách thuộc tính')
				for entry in entries:
					if (
						not isinstance(entry, dict)
						or set(entry) - {'name', 'property_values', 'source'}
						or not {'name', 'property_values'} <= set(entry)
						or not isinstance(entry['name'], str)
						or not entry['name']
						or entry.get('source', 'custom') not in ('custom', 'system')
					):
						raise ValueError('Actions policy có thuộc tính không hợp lệ')
					stringList(entry['property_values'])
		if field == 'workflow_path' and (
			'~ALL' in value['exclude']
			or ('~ALL' in value['include'] and len(value['include']) != 1)
		):
			raise ValueError('Actions policy có workflow pattern ~ALL không hợp lệ')


def validateGroup(key, items):
	if not isinstance(items, list):
		raise TypeError('Chính sách phải là danh sách')
	names = set()
	for item in items:
		if not isinstance(item, dict):
			raise TypeError('Chính sách phải là object')
		if key == 'dependabot_access':
			if (
				len(items) != 1
				or set(item) - {'default_level', 'repositories'}
				or 'repositories' not in item
				or (
					'default_level' in item
					and item['default_level'] not in (None, 'public', 'internal')
				)
			):
				raise ValueError('Dependabot access cần chính sách đầy đủ')
			repositoryNames(item['repositories'])
			name = 'policy'
		elif key == 'actions_policies':
			if (
				set(item) != {'name', 'enforcement', 'conditions', 'rules'}
				or not isinstance(item['name'], str)
				or not item['name']
				or item['enforcement'] not in ('disabled', 'active', 'evaluate')
			):
				raise ValueError('Actions policy thiếu trường hoặc chứa metadata')
			validateConditions(item['conditions'])
			if not isinstance(item['rules'], list):
				raise TypeError('Actions policy cần danh sách rules')
			ruleTypes = set()
			for rule in item['rules']:
				if (
					not isinstance(rule, dict)
					or set(rule) != {'type', 'parameters'}
					or rule['type'] not in ('restrict_actions_actors', 'restrict_action_events')
					or rule['type'] in ruleTypes
				):
					raise ValueError('Actions policy có loại rule lạ hoặc trùng')
				ruleTypes.add(rule['type'])
				parameter = (
					'allowed_actors'
					if rule['type'] == 'restrict_actions_actors'
					else 'allowed_events'
				)
				if not isinstance(rule['parameters'], dict) or set(rule['parameters']) != {
					parameter
				}:
					raise ValueError('Actions policy có tham số rule không hợp lệ')
				values = rule['parameters'][parameter]
				if parameter == 'allowed_events':
					stringList(values)
					if set(values) - EVENTS:
						raise ValueError('Actions policy có event không được hỗ trợ')
				else:
					if not isinstance(values, list):
						raise TypeError('Actions policy cần danh sách actor')
					for actor in values:
						if (
							not isinstance(actor, dict)
							or set(actor) != {'id', 'type'}
							or actor['type'] not in ACTOR_TYPES
							or type(actor['id']) is not int
							or actor['id'] < 1
						):
							raise ValueError('Actions policy có actor không hợp lệ')
					if len(values) != len({(actor['type'], actor['id']) for actor in values}):
						raise ValueError('Actions policy có actor trùng')
			name = item['name']
		else:
			raise ValueError('Nhóm chính sách không được hỗ trợ')
		if name in names:
			raise ValueError('Chính sách trùng tên')
		names.add(name)
	return items


def validateScope(base, key, items):
	if not base.startswith('orgs/') and (
		key == 'dependabot_access'
		or any(set(item['conditions']) - {'workflow_path'} for item in items)
	):
		raise ValueError('Chính sách repository không nhận điều kiện cấp tổ chức')


def readDetails(base, key):
	path = f'{base}/{GROUP_PATHS[key]}'
	if key == 'dependabot_access':
		validateScope(base, key, [])
		pages = github.ghJson('api', '--paginate', '--slurp', path + '?per_page=100')
		if not isinstance(pages, list) or not pages:
			raise ValueError('Chưa đọc đủ các trang Dependabot access')
		repositories, ids, defaultLevels = [], {}, []
		for page in pages:
			if (
				not isinstance(page, dict)
				or 'accessible_repositories' not in page
				or not isinstance(page['accessible_repositories'], list)
			):
				raise ValueError('Dependabot access thiếu dữ liệu')
			defaultLevels.append((('default_level' in page), page.get('default_level')))
			for repo in page['accessible_repositories']:
				if (
					not isinstance(repo, dict)
					or not isinstance(repo.get('full_name'), str)
					or type(repo.get('id')) is not int
					or repo['id'] <= 0
					or repo['id'] in ids.values()
				):
					raise ValueError('Dependabot access thiếu danh tính hoặc trùng ID')
				repositories.append(repo['full_name'])
				ids[repo['full_name']] = repo['id']
		if any(level != defaultLevels[0] for level in defaultLevels):
			raise ValueError('Dependabot default level thay đổi trong lúc đọc')
		policy = {'repositories': sorted(repositories)}
		if defaultLevels[0][0]:
			policy['default_level'] = defaultLevels[0][1]
		return validateGroup(key, [policy]), ids
	result, ids = [], {}
	for entry in resources.readCollection(path + '?has_parents=false', 'policies'):
		if not isinstance(entry, dict) or type(entry.get('id')) is not int or entry['id'] < 1:
			raise ValueError('Actions policy thiếu ID')
		data = github.ghJson('api', f'{path}/{entry["id"]}')
		expectedType = 'Organization' if base.startswith('orgs/') else 'Repository'
		expectedSource = base.split('/', 1)[1]
		if (
			not isinstance(data, dict)
			or data.get('id') != entry['id']
			or data.get('name') != entry.get('name')
			or data.get('target') != 'actions'
			or data.get('source_type') != expectedType
			or not isinstance(data.get('source'), str)
			or data['source'].casefold() != expectedSource.casefold()
			or entry['id'] in ids.values()
		):
			raise ValueError('Actions policy không thuộc phạm vi hoặc ID/tên không khớp')
		item = {
			field: copy.deepcopy(data[field])
			for field in ('name', 'enforcement', 'conditions', 'rules')
		}
		if item['conditions'] is None:
			item['conditions'] = {}
		if 'repository_id' in item['conditions']:
			repoIds = item['conditions'].pop('repository_id')
			if (
				not isinstance(repoIds, dict)
				or set(repoIds) != {'repository_ids'}
				or not isinstance(repoIds['repository_ids'], list)
			):
				raise ValueError('Actions policy thiếu repository IDs')
			names = []
			for repoId in repoIds['repository_ids']:
				if type(repoId) is not int or repoId <= 0:
					raise ValueError('Actions policy có repository ID không hợp lệ')
				repo = github.ghJson('api', f'repositories/{repoId}')
				if (
					not isinstance(repo, dict)
					or repo.get('id') != repoId
					or not isinstance(repo.get('full_name'), str)
				):
					raise ValueError('Actions policy không xác minh được repository')
				names.append(repo['full_name'])
			item['conditions']['selected_repositories'] = names
		result.append(item)
		ids[item['name']] = entry['id']
	validateGroup(key, result)
	validateScope(base, key, result)
	return result, ids


def summary(key, item):
	result = copy.deepcopy(item)
	if key == 'dependabot_access':
		result['repositories'].sort()
		return result
	for field, value in result['conditions'].items():
		if field == 'selected_repositories':
			value.sort()
		elif field != 'repository_property':
			value['include'].sort()
			value['exclude'].sort()
		else:
			for entries in value.values():
				for entry in entries:
					entry.setdefault('source', 'custom')
					entry['property_values'].sort()
				entries.sort(
					key=lambda entry: (entry['name'], entry['source'], entry['property_values'])
				)
	if result['conditions'].get('workflow_path') == {'include': ['~ALL'], 'exclude': []}:
		result['conditions'].pop('workflow_path')
	for rule in result['rules']:
		for field, values in rule['parameters'].items():
			values.sort(
				key=lambda value: (
					(value['type'], value['id']) if field == 'allowed_actors' else value
				)
			)
	result['rules'].sort(key=lambda rule: rule['type'])
	return result


def collectionChanges(plan, base, key, current, targets, resourceCache):
	validateGroup(key, targets)
	validateScope(base, key, targets)
	path = f'{base}/{GROUP_PATHS[key]}'
	if key == 'dependabot_access':
		if not targets:
			return
		if len(current) != 1:
			raise ValueError('Chưa đọc được Dependabot access trước khi ghi')
		before, target = current[0], targets[0]
		if 'default_level' in target and 'default_level' not in before:
			raise ValueError('Chưa đọc được Dependabot default level; không suy đoán null')
		if summary(key, before) == summary(key, target):
			return
		latest, ids = readDetails(base, key)
		if summary(key, latest[0]) != summary(key, before):
			raise ValueError('Dependabot access thay đổi trong lúc đọc')
		if 'default_level' in target and before['default_level'] != target['default_level']:
			if target['default_level'] is None:
				raise ValueError('API không hỗ trợ đặt lại default_level thành null')
			plan.append(
				(
					path + '/default-level',
					'PUT',
					{'default_level': target['default_level']},
					{'dependabot_default_level': target['default_level']},
				)
			)
		added = sorted(set(target['repositories']) - set(before['repositories']))
		removed = sorted(set(before['repositories']) - set(target['repositories']))
		if added or removed:
			body = {
				'repository_ids_to_add': resources.repositoryIds(added, resourceCache),
				'repository_ids_to_remove': [ids[name] for name in removed],
			}
			plan.append((path, 'PATCH', body, {'dependabot_access': target['repositories']}))
		return
	present = {item['name']: summary(key, item) for item in current}
	changed = [item for item in targets if present.get(item['name']) != summary(key, item)]
	if not changed:
		return
	latest, ids = readDetails(base, key)
	if {item['name']: summary(key, item) for item in latest} != present:
		raise ValueError('Actions policies thay đổi trong lúc đọc')
	for item in changed:
		body = copy.deepcopy(item)
		conditions = body['conditions']
		if 'selected_repositories' in conditions:
			conditions['repository_id'] = {
				'repository_ids': resources.repositoryIds(
					conditions.pop('selected_repositories'), resourceCache
				)
			}
		if 'workflow_path' in conditions and not any(conditions['workflow_path'].values()):
			raise ValueError('Cập nhật workflow targeting cần ít nhất một pattern')
		if not conditions:
			if present.get(item['name'], {}).get('conditions'):
				raise ValueError(
					'Bỏ conditions không xóa workflow targeting cũ; dùng pattern ~ALL để chọn mọi workflow'
				)
			body.pop('conditions')
		plan.append(
			(
				f'{path}/{ids[item["name"]]}' if item['name'] in ids else path,
				'PUT' if item['name'] in ids else 'POST',
				body,
				{'actions_policy': item['name']},
			)
		)


def validateResponse(response, name):
	data = json.loads(response)
	if (
		not isinstance(data, dict)
		or data.get('name') != name
		or type(data.get('id')) is not int
		or data['id'] <= 0
	):
		raise ValueError('API chưa xác nhận Actions policy; dừng trước request tiếp theo')
