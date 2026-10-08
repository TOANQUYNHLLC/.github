"""Nhập cài đặt GitHub về github-settings.json và áp dụng các mục có API từ nguồn local.

Chỉ lấy trường nằm trong danh sách cho phép; không lưu toàn bộ phản hồi API hoặc bí mật.
Đọc và xác minh toàn bộ kế hoạch trước khi ghi; không suy đoán giá trị khi API thiếu quyền.
"""

import json
import re
import tempfile
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

from orgsetup import github, resources

CONFIG_NAME = 'github-settings.json'
# printWidth của .prettierrc.json: tệp nhập về phải giữ đúng định dạng Prettier để make check không báo lỗi.
PRINT_WIDTH = 100
BOOL = bool
STRING = str
ORG_FIELDS = {
	**dict.fromkeys(
		(
			'name',
			'description',
			'blog',
			'email',
			'location',
			'company',
			'twitter_username',
			'secret_scanning_push_protection_custom_link',
		),
		STRING,
	),
	**dict.fromkeys(
		(
			'has_organization_projects',
			'has_repository_projects',
			'members_can_create_repositories',
			'members_can_create_internal_repositories',
			'members_can_create_private_repositories',
			'members_can_create_public_repositories',
			'members_can_create_pages',
			'members_can_create_public_pages',
			'members_can_create_private_pages',
			'members_can_fork_private_repositories',
			'web_commit_signoff_required',
			'deploy_keys_enabled_for_repositories',
			'secret_scanning_push_protection_custom_link_enabled',
		),
		BOOL,
	),
	'default_repository_permission': ('none', 'read', 'write', 'admin'),
}
REPO_FIELDS = {
	**dict.fromkeys(('description', 'homepage', 'default_branch'), STRING),
	**dict.fromkeys(
		(
			'has_issues',
			'has_projects',
			'has_wiki',
			'has_discussions',
			'has_pull_requests',
			'is_template',
			'allow_squash_merge',
			'allow_merge_commit',
			'allow_rebase_merge',
			'allow_auto_merge',
			'delete_branch_on_merge',
			'allow_update_branch',
			'allow_forking',
			'web_commit_signoff_required',
		),
		BOOL,
	),
	'pull_request_creation_policy': ('all', 'collaborators_only'),
	'squash_merge_commit_title': ('PR_TITLE', 'COMMIT_OR_PR_TITLE'),
	'squash_merge_commit_message': ('PR_BODY', 'COMMIT_MESSAGES', 'BLANK'),
	'merge_commit_title': ('PR_TITLE', 'MERGE_MESSAGE'),
	'merge_commit_message': ('PR_BODY', 'PR_TITLE', 'BLANK'),
	'visibility': ('public', 'private', 'internal'),
	'archived': BOOL,
}
REPO_WEB_FIELDS = {'secret_scanning_validity_checks': ('enabled', 'disabled')}
ORG_WEB_FIELDS = {
	'default_repository_branch': STRING,
	'installed_apps': list,
	**dict.fromkeys(
		(
			'two_factor_requirement_enabled',
			'members_can_change_repo_visibility',
			'members_can_delete_repositories',
			'members_can_delete_issues',
			'members_can_invite_outside_collaborators',
			'members_can_create_teams',
			'members_can_view_dependency_insights',
			'readers_can_create_discussions',
			'display_commenter_full_name_setting_enabled',
			'advanced_security_enabled_for_new_repositories',
			'dependabot_alerts_enabled_for_new_repositories',
			'dependabot_security_updates_enabled_for_new_repositories',
			'dependency_graph_enabled_for_new_repositories',
			'secret_scanning_enabled_for_new_repositories',
			'secret_scanning_push_protection_enabled_for_new_repositories',
			'secret_scanning_validity_checks_enabled',
		),
		BOOL,
	),
}
STATUS_FIELDS = ('enabled', 'disabled')
SECURITY_FIELDS = (
	'advanced_security',
	'code_security',
	'secret_scanning',
	'secret_scanning_push_protection',
	'secret_scanning_ai_detection',
	'secret_scanning_non_provider_patterns',
	'secret_scanning_delegated_alert_dismissal',
	'secret_scanning_delegated_bypass',
)
WORKFLOW_FIELDS = {
	'default_workflow_permissions': ('read', 'write'),
	'can_approve_pull_request_reviews': BOOL,
}
FORK_FIELDS = dict.fromkeys(
	(
		'run_workflows_from_fork_pull_requests',
		'send_write_tokens_to_workflows',
		'send_secrets_and_variables',
		'require_approval_for_fork_pr_workflows',
	),
	BOOL,
)
COMMON_ENDPOINTS = {
	'actions/permissions/workflow': ('PUT', WORKFLOW_FIELDS),
	'actions/permissions/artifact-and-log-retention': ('PUT', {'days': int}),
	'actions/permissions/fork-pr-contributor-approval': (
		'PUT',
		{
			'approval_policy': (
				'first_time_contributors_new_to_github',
				'first_time_contributors',
				'all_external_contributors',
			)
		},
	),
	'actions/permissions/fork-pr-workflows-private-repos': ('PUT', FORK_FIELDS),
	'interaction-limits': (
		'PUT',
		{'limit': ('existing_users', 'contributors_only', 'collaborators_only')},
	),
	'interaction-limits/pulls/creation-cap': (
		'PATCH',
		{'enabled': BOOL, 'max_open_pull_requests': int, 'include_drafts': BOOL},
	),
}
ORG_ENDPOINTS = {
	**COMMON_ENDPOINTS,
	'actions/oidc/customization/sub': (
		'PUT',
		{'include_claim_keys': list, 'use_immutable_subject': BOOL},
	),
	'actions/permissions': (
		'PUT',
		{
			'enabled_repositories': ('all', 'none', 'selected'),
			'allowed_actions': ('all', 'local_only', 'selected'),
			'sha_pinning_required': BOOL,
		},
	),
	'settings/immutable-releases': ('PUT', {'enforced_repositories': ('all', 'none', 'selected')}),
}
REPO_ENDPOINTS = {
	**COMMON_ENDPOINTS,
	'actions/oidc/customization/sub': (
		'PUT',
		{'use_default': BOOL, 'include_claim_keys': list, 'use_immutable_subject': BOOL},
	),
	'actions/permissions': (
		'PUT',
		{
			'enabled': BOOL,
			'allowed_actions': ('all', 'local_only', 'selected'),
			'sha_pinning_required': BOOL,
		},
	),
	'topics': ('PUT', {'names': list}),
	'vulnerability-alerts': ('PUT', {'enabled': BOOL}),
	'automated-security-fixes': ('PUT', {'enabled': BOOL}),
	'private-vulnerability-reporting': ('PUT', {'enabled': BOOL}),
	'immutable-releases': ('PUT', {'enabled': BOOL}),
	'code-scanning/default-setup': (
		'PATCH',
		{
			'state': ('configured', 'not-configured'),
			'languages': list,
			'query_suite': ('default', 'extended'),
			'threat_model': ('remote', 'remote_and_local'),
			'runner_type': ('standard', 'labeled'),
			'runner_label': (str, type(None)),
		},
	),
}


def checkFields(data, fields, path, partial=False):
	"""Kiểu và giá trị hợp lệ trước khi lưu hoặc áp dụng; không chấp nhận trường lạ trong tệp local."""
	if not isinstance(data, dict) or set(data) - set(fields):
		raise ValueError(f'{path}: cấu trúc hoặc trường cài đặt không hợp lệ')
	if not partial and not data:
		raise ValueError(f'{path}: thiếu dữ liệu cài đặt')
	for key, value in data.items():
		expected = fields[key]
		if isinstance(expected, tuple):
			valid = (
				type(value) in expected
				if all(isinstance(item, type) for item in expected)
				else value in expected and isinstance(value, str)
			)
		else:
			valid = type(value) is expected
		if (
			not valid
			or (type(value) is int and value < 1)
			or (isinstance(value, list) and any(not isinstance(item, str) for item in value))
		):
			raise ValueError(f'{path}: giá trị {key} không hợp lệ')
	return data


def selectFields(data, fields, path):
	"""Lọc phản hồi API, giữ cả false; chuỗi nullable được chuẩn hóa thành chuỗi rỗng."""
	if not isinstance(data, dict):
		raise TypeError(f'{path}: API không trả object')
	selected = {
		key: '' if value is None and fields[key] is STRING else value
		for key, value in data.items()
		if key in fields
	}
	return checkFields(selected, fields, path, partial=True)


def endpointDefinitions(organization, private=False):
	definitions = dict(ORG_ENDPOINTS if organization else REPO_ENDPOINTS)
	if not organization:
		definitions.pop(
			'private-vulnerability-reporting'
			if private
			else 'actions/permissions/fork-pr-workflows-private-repos'
		)
	return definitions


def readEndpoint(path, suffix, fields):
	"""404 chỉ biểu diễn tắt cho Dependabot alerts, theo hợp đồng API của endpoint này."""
	if suffix == 'vulnerability-alerts':
		return {'enabled': github.ghExists(path)}
	data = github.ghJson('api', path)
	if suffix == 'actions/oidc/customization/sub' and 'use_default' not in fields and data is None:
		return {}
	selected = selectFields(data, fields, path)
	if suffix == 'actions/oidc/customization/sub':
		validateOidc(selected, 'use_default' not in fields)
		return selected
	if suffix == 'interaction-limits' and not data:
		return {}
	if not selected:
		raise ValueError(f'{path}: API không trả trường cài đặt được hỗ trợ')
	# Những trường tùy chọn có thể không được trả; trường điều khiển chính phải đọc được.
	required = next(iter(fields))
	if required not in selected:
		raise ValueError(f'{path}: thiếu trường {required}')
	if suffix == 'actions/permissions/workflow' and set(selected) != set(WORKFLOW_FIELDS):
		raise ValueError(f'{path}: thiếu quyền mặc định GITHUB_TOKEN')
	if (
		suffix == 'actions/permissions'
		and (
			selected.get('enabled') is True
			or selected.get('enabled_repositories') in ('all', 'selected')
		)
		and 'allowed_actions' not in selected
	):
		raise ValueError(f'{path}: thiếu allowed_actions khi Actions đang bật')
	if suffix == 'interaction-limits' and data.get('expires_at') is not None:
		raise ValueError(f'{path}: chưa hỗ trợ khôi phục giới hạn có thời gian hết hạn')
	if suffix == 'actions/permissions' and selected.get('allowed_actions') == 'selected':
		raise ValueError(
			f'{path}: cần xuất thêm danh sách allowed-actions trước khi quản lý chế độ selected'
		)
	if (
		selected.get('enabled_repositories') == 'selected'
		or selected.get('enforced_repositories') == 'selected'
	):
		raise ValueError(
			f'{path}: cần xuất thêm danh sách repository trước khi quản lý chế độ selected'
		)
	return selected


def readScope(repo=None):
	"""Đọc cài đặt và trạng thái bảo mật; phần API không đọc được được đánh dấu rõ, không giữ giá trị cũ."""
	organization = repo is None
	base = f'orgs/{github.ORG}' if organization else f'repos/{github.ORG}/{quote(repo, safe="")}'
	current = github.ghJson('api', base)
	fields = ORG_FIELDS if organization else REPO_FIELDS
	if (
		not isinstance(current, dict)
		or (organization and current.get('login') != github.ORG)
		or (not organization and current.get('full_name') != f'{github.ORG}/{repo}')
	):
		raise ValueError(f'{base}: không xác minh được danh tính tài nguyên')
	scope = {
		'settings': selectFields(current, fields, base),
		'web_settings': selectFields(
			current, ORG_WEB_FIELDS if organization else REPO_WEB_FIELDS, base
		),
		'endpoints': {},
	}
	if not scope['settings']:
		raise ValueError(f'{base}: thiếu cài đặt')
	if set(fields) - set(scope['settings']):
		raise ValueError(f'{base}: thiếu trường cài đặt chính; không ghi đè nguồn local')
	if not organization:
		if type(current.get('private')) is not bool:
			raise ValueError(f'{base}: thiếu private')
		analysis = current.get('security_and_analysis')
		if not isinstance(analysis, dict):
			raise ValueError(f'{base}: thiếu security_and_analysis')
		for key, value in analysis.items():
			if key in SECURITY_FIELDS and (
				not isinstance(value, dict) or value.get('status') not in STATUS_FIELDS
			):
				raise ValueError(f'{base}: trạng thái {key} không hợp lệ')
		scope['security'] = {
			key: value['status']
			for key, value in analysis.items()
			if key in SECURITY_FIELDS
			and isinstance(value, dict)
			and value.get('status') in STATUS_FIELDS
		}
		for key in REPO_WEB_FIELDS:
			if key in analysis:
				scope['web_settings'][key] = (
					analysis[key].get('status') if isinstance(analysis[key], dict) else None
				)
		checkFields(scope['web_settings'], REPO_WEB_FIELDS, base, partial=True)
	definitions = endpointDefinitions(organization, current.get('private', False))
	unavailable = {}

	def read(item):
		suffix, (_, allowed) = item
		path = f'{base}/{suffix}'
		try:
			return suffix, readEndpoint(path, suffix, allowed), None
		except RuntimeError as exc:
			match = re.search(r'HTTP (\d+)', str(exc))
			return suffix, None, f'HTTP {match[1]}' if match else 'Không đọc được API'
		except (ValueError, TypeError):
			return suffix, None, 'API thiếu hoặc sai dữ liệu; không suy đoán giá trị'

	with ThreadPoolExecutor(max_workers=6) as pool:
		for suffix, value, problem in pool.map(read, definitions.items()):
			if problem:
				unavailable[f'{base}/{suffix}'] = problem
			else:
				scope['endpoints'][suffix] = value
	if organization:
		for suffix, readResource in (
			('actions/runner-groups', resources.readRunnerGroups),
			('installations', resources.installedApps),
		):
			try:
				value = readResource()
				if suffix == 'installations':
					scope['web_settings']['installed_apps'] = value
				else:
					scope['runner_groups'] = value
			except (RuntimeError, ValueError, TypeError):
				unavailable[f'{base}/{suffix}'] = 'Không đọc đủ hoặc không xác minh được tài nguyên'
	try:
		if organization:
			scope['security_configurations'] = readSecurityDefaults()
		else:
			scope['security_configuration'] = readSecurityConfiguration(base)
	except (RuntimeError, ValueError, TypeError):
		unavailable[f'{base}/code-security'] = 'Không đọc được cấu hình bảo mật và phạm vi áp dụng'
	return scope, unavailable


def securityConfigurationIds():
	"""Giải tên cấu hình sang ID tại thời điểm áp dụng; ID không được coi là khả chuyển giữa tổ chức."""
	items = github.ghList(f'orgs/{github.ORG}/code-security/configurations')
	result = {}
	for item in items:
		if (
			not isinstance(item, dict)
			or not isinstance(item.get('name'), str)
			or type(item.get('id')) is not int
			or item['id'] < 1
			or item.get('target_type') not in ('global', 'organization')
			or item['name'] in result
		):
			raise ValueError('Danh sách cấu hình bảo mật thiếu dữ liệu hoặc trùng tên')
		result[item['name']] = item
	return result


def readSecurityDefaults():
	"""Phạm vi mặc định của cấu hình bảo mật; không nhầm cờ REST cũ với cấu hình mới."""
	configurations = securityConfigurationIds()
	defaults = github.ghList(f'orgs/{github.ORG}/code-security/configurations/defaults')
	wanted = {
		name: {'name': name, 'target_type': item['target_type'], 'default_for_new_repos': 'none'}
		for name, item in configurations.items()
	}
	seen = set()
	for item in defaults:
		if not isinstance(item, dict) or not isinstance(item.get('configuration'), dict):
			raise TypeError('Cấu hình bảo mật mặc định thiếu dữ liệu')
		name = item['configuration'].get('name')
		if (
			name not in wanted
			or name in seen
			or item.get('default_for_new_repos') not in ('public', 'private_and_internal', 'all')
		):
			raise ValueError('Phạm vi cấu hình bảo mật mặc định không hợp lệ')
		wanted[name]['default_for_new_repos'] = item['default_for_new_repos']
		seen.add(name)
	return list(wanted.values())


def readSecurityConfiguration(base):
	"""Tên cấu hình đã gắn; dữ liệu null có nghĩa repository chưa gắn cấu hình."""
	data = github.ghJson('api', f'{base}/code-security-configuration')
	if data is None:
		return None
	if isinstance(data, dict) and data.get('status') in (
		'detached',
		'removed',
		'removed_by_enterprise',
	):
		return None
	if (
		not isinstance(data, dict)
		or data.get('status') not in ('attached', 'enforced', 'enterprise_enforced')
		or not isinstance(data.get('configuration'), dict)
		or not isinstance(data['configuration'].get('name'), str)
		or not data['configuration']['name']
	):
		raise ValueError(f'{base}: cấu hình bảo mật chưa gắn thành công hoặc không đọc được')
	return data['configuration']['name']


def validateOidc(value, organization):
	"""Null ở cấp tổ chức là chưa tùy chỉnh; không lưu tiền tố subject do GitHub sinh."""
	fields = (ORG_ENDPOINTS if organization else REPO_ENDPOINTS)['actions/oidc/customization/sub'][
		1
	]
	checkFields(value, fields, 'OIDC', partial=organization)
	if not organization and 'use_default' not in value:
		raise ValueError('OIDC repository thiếu use_default')
	claims = value.get('include_claim_keys')
	if claims is not None and (
		any(not re.fullmatch(r'[A-Za-z0-9_]+', claim) for claim in claims)
		or len(claims) != len(set(claims))
	):
		raise ValueError('OIDC: include_claim_keys phải chứa các tên claim hợp lệ, không trùng')
	return value


def readConfig(root=None):
	"""Tệp là nguồn cài đặt, chỉ chấp nhận tổ chức và endpoint đã khai báo trong mã nguồn."""
	data = json.loads(((root or github.ROOT) / CONFIG_NAME).read_text(encoding='utf-8'))
	if (
		not isinstance(data, dict)
		or set(data)
		!= {
			'organization_name',
			'repository_defaults',
			'organization',
			'repositories',
			'unavailable',
		}
		or data['organization_name'] != github.ORG
	):
		raise ValueError(f'{CONFIG_NAME}: cấu trúc hoặc tổ chức không hợp lệ')
	checkFields(data['repository_defaults'], REPO_FIELDS, 'repository_defaults', partial=True)
	if (
		not isinstance(data['repositories'], dict)
		or not isinstance(data['unavailable'], dict)
		or any(
			not isinstance(key, str) or not isinstance(value, str)
			for key, value in data['unavailable'].items()
		)
	):
		raise ValueError(
			f'{CONFIG_NAME}: danh sách repository hoặc phần chưa đọc được không hợp lệ'
		)
	for repo in data['repositories']:
		if not re.fullmatch(r'[A-Za-z0-9_.-]+', repo) or repo in ('.', '..'):
			raise ValueError(f'{CONFIG_NAME}: tên repository không hợp lệ')
	for repo, scope in [(None, data['organization']), *data['repositories'].items()]:
		organization = repo is None
		allowedScopeKeys = {'settings', 'web_settings', 'endpoints'} | (
			{'security_configurations', 'runner_groups'}
			if organization
			else {'security', 'security_configuration'}
		)
		if (
			not isinstance(scope, dict)
			or set(scope) - allowedScopeKeys
			or not {'settings', 'web_settings', 'endpoints'} <= set(scope)
		):
			raise ValueError(f'{CONFIG_NAME}: cấu trúc phạm vi {repo} không hợp lệ')
		checkFields(
			scope['settings'], ORG_FIELDS if organization else REPO_FIELDS, str(repo), partial=True
		)
		checkFields(
			scope['web_settings'],
			ORG_WEB_FIELDS if organization else REPO_WEB_FIELDS,
			str(repo),
			partial=True,
		)
		if not isinstance(scope['endpoints'], dict):
			raise TypeError(f'{CONFIG_NAME}: endpoints phải là object')
		definitions = ORG_ENDPOINTS if organization else REPO_ENDPOINTS
		for suffix, value in scope['endpoints'].items():
			if suffix not in definitions:
				raise ValueError(f'{CONFIG_NAME}: endpoint không được hỗ trợ: {suffix}')
			if suffix == 'actions/oidc/customization/sub':
				validateOidc(value, organization)
				continue
			checkFields(
				value, definitions[suffix][1], suffix, partial=suffix == 'interaction-limits'
			)
			if value and next(iter(definitions[suffix][1])) not in value:
				raise ValueError(f'{CONFIG_NAME}: thiếu trường chính tại {suffix}')
			if (
				suffix == 'actions/permissions'
				and (
					value.get('enabled') is True
					or value.get('enabled_repositories') in ('all', 'selected')
				)
				and 'allowed_actions' not in value
			):
				raise ValueError(f'{CONFIG_NAME}: cần khai báo allowed_actions khi bật Actions')
			if (
				value.get('allowed_actions') == 'selected'
				or value.get('enabled_repositories') == 'selected'
				or value.get('enforced_repositories') == 'selected'
			):
				raise ValueError(f'{CONFIG_NAME}: chưa hỗ trợ danh sách selected tại {suffix}')
		if organization and 'runner_groups' in scope:
			resources.validateRunnerGroups(scope['runner_groups'])
		if 'security' in scope:
			checkFields(
				scope['security'],
				dict.fromkeys(SECURITY_FIELDS, STATUS_FIELDS),
				str(repo),
				partial=True,
			)
		if organization and 'security_configurations' in scope:
			items = scope['security_configurations']
			if not isinstance(items, list):
				raise TypeError('security_configurations phải là danh sách')
			names = set()
			for item in items:
				checkFields(
					item,
					{
						'name': str,
						'target_type': ('global', 'organization'),
						'default_for_new_repos': ('all', 'none', 'private_and_internal', 'public'),
					},
					'security_configurations',
				)
				if (
					set(item) != {'name', 'target_type', 'default_for_new_repos'}
					or not item['name']
					or item['name'] in names
				):
					raise ValueError('Cấu hình bảo mật thiếu trường hoặc trùng tên')
				names.add(item['name'])
		if (
			not organization
			and 'security_configuration' in scope
			and scope['security_configuration'] is not None
			and (
				not isinstance(scope['security_configuration'], str)
				or not scope['security_configuration']
			)
		):
			raise ValueError('security_configuration phải là tên cấu hình hoặc null')
	validateDependencies(data)
	return data


def validateDependencies(config):
	"""Chặn cấu hình mâu thuẫn với chính sách tổ chức và các tính năng phụ thuộc."""
	organization = config['organization']['endpoints']
	for repo, scope in config['repositories'].items():
		endpoints, security = scope['endpoints'], scope.get('security', {})
		if (
			endpoints.get('actions/permissions', {}).get('enabled') is True
			and organization.get('actions/permissions', {}).get('enabled_repositories') == 'none'
		):
			raise ValueError(f'{repo}: không bật Actions khi tổ chức tắt Actions')
		if (
			endpoints.get('automated-security-fixes', {}).get('enabled') is True
			and endpoints.get('vulnerability-alerts', {}).get('enabled') is False
		):
			raise ValueError(f'{repo}: Dependabot security updates cần Dependabot alerts')
		if (
			security.get('secret_scanning') == 'disabled'
			and security.get('secret_scanning_push_protection') == 'enabled'
		):
			raise ValueError(f'{repo}: push protection cần secret scanning')
		if (
			endpoints.get('immutable-releases', {}).get('enabled') is False
			and organization.get('settings/immutable-releases', {}).get('enforced_repositories')
			== 'all'
		):
			raise ValueError(f'{repo}: tổ chức đang bắt buộc Release bất biến')


def displayWidth(line):
	"""Độ rộng dòng theo cách Prettier đo: tab đầu dòng rộng 4 (tabWidth), ký tự Đông Á rộng 2."""
	return sum(
		4 if character == '\t' else 2 if unicodedata.east_asian_width(character) in 'WF' else 1
		for character in line
	)


def inlineJson(value):
	"""Một dòng như Prettier in mảng; None khi Prettier luôn tách dòng: object không rỗng (tệp luôn mở rộng
	object), hoặc mảng từ hai phần tử mà mọi phần tử là mảng có hơn một phần tử."""
	if isinstance(value, dict):
		return None if value else '{}'
	if not isinstance(value, list):
		return json.dumps(value, ensure_ascii=False)
	if len(value) > 1 and all(isinstance(item, list) and len(item) > 1 for item in value):
		return None
	items = [inlineJson(item) for item in value]
	return None if None in items else f'[{", ".join(items)}]'


def jsonText(data):
	"""JSON thụt tab như Prettier định dạng tệp này: object không rỗng luôn mở rộng; mảng gộp một dòng khi
	inlineJson cho phép và vừa PRINT_WIDTH, còn lại mỗi phần tử một dòng."""
	lines = []

	def emit(value, depth, prefix, suffix):
		indent = '\t' * depth
		if isinstance(value, dict) and value:
			lines.append(f'{indent}{prefix}{{')
			for index, (key, item) in enumerate(value.items()):
				keyText = json.dumps(key, ensure_ascii=False)
				emit(item, depth + 1, f'{keyText}: ', ',' if index < len(value) - 1 else '')
			lines.append(f'{indent}}}{suffix}')
			return
		if isinstance(value, list) and value:
			inline = inlineJson(value)
			if (
				inline is not None
				and displayWidth(f'{indent}{prefix}{inline}{suffix}') <= PRINT_WIDTH
			):
				lines.append(f'{indent}{prefix}{inline}{suffix}')
				return
			lines.append(f'{indent}{prefix}[')
			for index, item in enumerate(value):
				emit(item, depth + 1, '', ',' if index < len(value) - 1 else '')
			lines.append(f'{indent}]{suffix}')
			return
		lines.append(f'{indent}{prefix}{json.dumps(value, ensure_ascii=False)}{suffix}')

	emit(data, 0, '', '')
	return '\n'.join(lines) + '\n'


def importSettings():
	"""GET GitHub → ghi nguyên tử một tệp local sau khi hoàn tất đọc; không gửi mutation GitHub."""
	previous = readConfig()
	repos = github.listRepos(None, includeArchived=True)
	config = {
		'organization_name': github.ORG,
		'repository_defaults': previous['repository_defaults'],
		'organization': {},
		'repositories': {},
		'unavailable': {},
	}
	with ThreadPoolExecutor(max_workers=4) as pool:
		for repo, (scope, unavailable) in zip(
			[None, *repos], pool.map(readScope, [None, *repos]), strict=True
		):
			if repo is None:
				config['organization'] = scope
			else:
				config['repositories'][repo] = scope
			config['unavailable'].update(unavailable)
	# Tệp tạm cùng thư mục để replace nguyên tử; không để phản hồi thô trên đĩa.
	path = github.ROOT / CONFIG_NAME
	temporary = None
	try:
		with tempfile.NamedTemporaryFile(
			mode='w',
			encoding='utf-8',
			dir=path.parent,
			prefix=f'.{CONFIG_NAME}.',
			suffix='.tmp',
			delete=False,
		) as output:
			temporary = Path(output.name)
			output.write(jsonText(config))
		temporary.replace(path)
	finally:
		if temporary is not None:
			temporary.unlink(missing_ok=True)
	print(
		f'✔ Đã nhập cài đặt {github.ORG} và các repository vào {CONFIG_NAME}; không thay đổi GitHub.'
	)
	for path, reason in config['unavailable'].items():
		print(f'⚠ Chưa nhập {path}: {reason}')
	return 1 if config['unavailable'] else 0


def addChanges(plan, path, current, wanted, method='PATCH', suffix=''):
	"""So sánh chỉ phần được quản lý; PUT gửi đầy đủ trường bắt buộc, PATCH chỉ gửi phần khác."""
	for key in wanted:
		if key not in current:
			if suffix == 'actions/oidc/customization/sub':
				continue
			# GitHub ẩn allowed_actions khi Actions tắt; chỉ đặt lại khi local yêu cầu bật.
			if (
				suffix == 'actions/permissions'
				and key == 'allowed_actions'
				and (
					wanted.get('enabled') is True
					or wanted.get('enabled_repositories') in ('all', 'selected')
				)
			):
				continue
			raise ValueError(f'{path}: chưa đọc được trường {key}; dừng trước khi ghi')
	changes = {key: value for key, value in wanted.items() if current.get(key) != value}
	if not changes:
		return
	if suffix == 'actions/permissions/artifact-and-log-retention':
		limits = github.ghJson('api', path)
		if (
			not isinstance(limits, dict)
			or type(limits.get('maximum_allowed_days')) is not int
			or wanted['days'] > limits['maximum_allowed_days']
		):
			raise ValueError(
				f'{path}: vượt mức lưu dữ liệu GitHub cho phép hoặc chưa đọc được mức tối đa'
			)
	body = wanted if method == 'PUT' else changes
	if suffix in (
		'vulnerability-alerts',
		'automated-security-fixes',
		'private-vulnerability-reporting',
		'immutable-releases',
	):
		method, body = ('PUT' if wanted['enabled'] else 'DELETE'), None
	elif suffix == 'interaction-limits' and not wanted:
		method, body = 'DELETE', None
	elif suffix == 'interaction-limits' and not current:
		body = wanted
	plan.append((path, method, body, changes))


def repositorySettingChanges(plan, base, current, wanted):
	"""Discussions dùng mutation GraphQL công khai; cài đặt khác dùng PATCH REST."""
	settings = dict(wanted)
	if 'has_discussions' in settings:
		wantedDiscussions = settings.pop('has_discussions')
		if 'has_discussions' not in current:
			raise ValueError(f'{base}: chưa đọc được has_discussions')
		if wantedDiscussions != current['has_discussions']:
			data = github.ghJson('api', base)
			if (
				not isinstance(data, dict)
				or data.get('full_name') != base.removeprefix('repos/')
				or not isinstance(data.get('node_id'), str)
				or not data['node_id']
			):
				raise ValueError(f'{base}: không xác minh được ID GraphQL')
			body = {
				'query': 'mutation($input: UpdateRepositoryInput!) { updateRepository(input: $input) { repository { hasDiscussionsEnabled } } }',
				'variables': {
					'input': {
						'repositoryId': data['node_id'],
						'hasDiscussionsEnabled': wantedDiscussions,
					}
				},
			}
			plan.append(('graphql', 'POST', body, {'has_discussions': wantedDiscussions}))
	addChanges(plan, base, current, settings)


def securityBindingChanges(plan, base, repo, current, wanted):
	"""Áp dụng phạm vi mặc định và liên kết cấu hình có sẵn; không sao chép cấu hình do GitHub quản lý."""
	if repo is None:
		present = {item['name']: item for item in current.get('security_configurations', [])}
		for item in wanted.get('security_configurations', []):
			if (
				item['name'] not in present
				or present[item['name']]['target_type'] != item['target_type']
			):
				raise ValueError(
					f'{base}: cấu hình bảo mật {item["name"]} chưa tồn tại; chưa thể áp dụng phạm vi'
				)
			if item['default_for_new_repos'] == present[item['name']]['default_for_new_repos']:
				continue
			configurationId = securityConfigurationIds()[item['name']]['id']
			body = {'default_for_new_repos': item['default_for_new_repos']}
			plan.append(
				(
					f'{base}/code-security/configurations/{configurationId}/defaults',
					'PUT',
					body,
					body,
				)
			)
		return
	if 'security_configuration' not in wanted:
		return
	if 'security_configuration' not in current:
		raise ValueError(f'{base}: chưa đọc được liên kết cấu hình bảo mật')
	name = wanted['security_configuration']
	if name == current['security_configuration']:
		return
	data = github.ghJson('api', base)
	if (
		not isinstance(data, dict)
		or type(data.get('id')) is not int
		or data['id'] < 1
		or data.get('full_name') != f'{github.ORG}/{repo}'
	):
		raise ValueError(f'{base}: không xác minh được ID repository')
	body = {'selected_repository_ids': [data['id']]}
	if name is None:
		path, method = f'orgs/{github.ORG}/code-security/configurations/detach', 'DELETE'
	else:
		configurations = securityConfigurationIds()
		if name not in configurations:
			raise ValueError(f'{base}: cấu hình bảo mật {name} chưa tồn tại')
		configurationId = configurations[name]['id']
		path, method = (
			f'orgs/{github.ORG}/code-security/configurations/{configurationId}/attach',
			'POST',
		)
		body['scope'] = 'selected'
	plan.append((path, method, body, {'security_configuration': name}))


def syncConfiguredSettings(apply=False, verify=False):
	"""Đối chiếu/áp dụng cấu hình đã nhập; thất bại đọc bất kỳ phạm vi nào chặn mọi mutation."""
	config = readConfig()
	plan, manual = [], []
	if config['unavailable']:
		raise ValueError(
			f'{CONFIG_NAME}: có mục chưa nhập; chạy lại make org-import trước khi áp dụng'
		)
	for repo, wanted in [(None, config['organization']), *config['repositories'].items()]:
		base = (
			f'orgs/{github.ORG}' if repo is None else f'repos/{github.ORG}/{quote(repo, safe="")}'
		)
		current, unavailable = readScope(repo)
		if unavailable:
			raise ValueError(f'{base}: chưa đọc được {", ".join(unavailable)}; dừng trước khi ghi')
		archivePlan = []
		repositorySettings = dict(wanted['settings'])
		if repo is not None and 'archived' in repositorySettings:
			archived = repositorySettings.pop('archived')
			# Bỏ archive trước mọi thao tác ghi; archive sau cùng để không khóa các cập nhật còn lại.
			addChanges(
				archivePlan if archived else plan,
				base,
				current['settings'],
				{'archived': archived},
			)
		securityBindingChanges(plan, base, repo, current, wanted)
		if repo is None:
			addChanges(plan, base, current['settings'], wanted['settings'])
			if 'runner_groups' in wanted:
				if 'runner_groups' not in current:
					raise ValueError(f'{base}: chưa đọc được các nhóm runner')
				resources.runnerGroupChanges(
					plan, current['runner_groups'], wanted['runner_groups']
				)
		else:
			repositorySettingChanges(plan, base, current['settings'], repositorySettings)
		for key, value in wanted['web_settings'].items():
			if key not in current['web_settings']:
				raise ValueError(f'{base}: chưa đọc được {key}; dừng trước khi ghi')
			if current['web_settings'][key] != value:
				manual.append(f'{base}/{key}: cần đối chiếu và sửa trên web')
		if repo is not None:
			security = wanted.get('security', {})
			before = len(plan)
			addChanges(plan, base, current.get('security', {}), security)
			if len(plan) > before:
				path, method, _, changes = plan.pop()
				plan.append(
					(
						path,
						method,
						{
							'security_and_analysis': {
								key: {'status': value} for key, value in changes.items()
							}
						},
						changes,
					)
				)
		definitions = ORG_ENDPOINTS if repo is None else REPO_ENDPOINTS
		# Tắt security updates trước alerts; bật alerts trước security updates, không phụ thuộc thứ tự JSON.
		ordered = sorted(
			wanted['endpoints'].items(),
			key=lambda item: (
				0
				if item[0] == 'actions/permissions'
				else 1
				if item[0] == 'automated-security-fixes' and item[1].get('enabled') is False
				else 3
				if item[0] == 'automated-security-fixes' and item[1].get('enabled') is True
				else 2
			),
		)
		for suffix, target in ordered:
			if suffix not in current['endpoints']:
				raise ValueError(
					f'{base}/{suffix}: endpoint không áp dụng được; dừng trước khi ghi'
				)
			if suffix == 'actions/oidc/customization/sub' and repo is None and not target:
				if current['endpoints'][suffix]:
					manual.append(
						f'{base}/{suffix}: API chưa có thao tác xóa tùy chỉnh OIDC tổ chức'
					)
				continue
			if suffix == 'interaction-limits':
				# {} là không giới hạn; thay đổi phải dùng DELETE hoặc PUT, không đối chiếu trường thiếu.
				old = current['endpoints'][suffix]
				if old != target:
					plan.append(
						(f'{base}/{suffix}', 'PUT' if target else 'DELETE', target or None, target)
					)
				continue
			addChanges(
				plan,
				f'{base}/{suffix}',
				current['endpoints'][suffix],
				target,
				definitions[suffix][0],
				suffix,
			)
		plan.extend(archivePlan)
	for path, method, _, changes in plan:
		print(
			f'{"Áp dụng" if apply else "(xem trước)"} {method} {path}: {json.dumps(changes, ensure_ascii=False)}'
		)
	if apply:
		for path, method, body, _ in plan:
			arguments = ('api', '-X', method, path)
			if body is None:
				github.gh(*arguments)
			else:
				github.gh(*arguments, '--input', '-', stdin=json.dumps(body))
		# Đọc lại, không báo thành công chỉ từ HTTP 2xx.
		if plan:
			return syncConfiguredSettings(False, verify=True)
	elif not plan:
		print(f'✔ Các cài đặt API được quản lý khớp {CONFIG_NAME}.')
	for detail in manual:
		print(f'⚠ {detail}')
	if verify and plan:
		print('⚠ GitHub chưa phản ánh đầy đủ cài đặt đã gửi; chưa xác nhận hoàn tất.')
	return 1 if manual or (verify and plan) else 0
