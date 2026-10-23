"""Khai báo cài đặt chưa đọc được và bản khôi phục thủ công, không suy đoán giá trị web."""

import copy
import json
import re

from orgsetup import catalog, github, localdata

MANUAL_GROUPS = {
	'settings_pages': 'Trang Settings, mục chỉ đối chiếu và tính năng ngoài hợp đồng API',
	'repository_policies': 'Repository policies, allow list và quy tắc quản lý repository trên web',
	'billing': 'Gói, ngân sách và thông tin thanh toán',
	'authentication': 'SSO, SCIM và chính sách xác thực',
	'oauth_access': 'Hạn chế và phê duyệt OAuth Apps',
	'github_apps': 'Cài đặt Apps và quyền từng installation',
	'personal_access_tokens': 'Chính sách và phê duyệt personal access tokens',
	'codespaces': 'Quyền truy cập, chính sách và cấu hình Codespaces',
	'copilot': 'Chính sách và cấp quyền Copilot',
	'secrets': 'Secrets Actions, Dependabot, Codespaces và environments',
	'webhook_credentials': 'Shared secret của webhook',
	'registry_credentials': 'Thông tin xác thực private registries',
	'deploy_keys': 'Deploy keys và tham chiếu khóa ở kho riêng',
	'custom_pattern_publication': 'Dry run và xuất bản mẫu secret scanning',
	'verified_domains': 'Domain đã xác minh và cấu hình DNS liên quan',
	'members_and_collaborators': 'Membership, lời mời và quyền cá nhân',
}
REPO_MANUAL_GROUPS = {
	'settings_pages',
	'github_apps',
	'codespaces',
	'secrets',
	'webhook_credentials',
	'deploy_keys',
	'custom_pattern_publication',
	'members_and_collaborators',
}
MANUAL_STATUS = ('unverified', 'pending', 'verified', 'not_applicable')


def validateScope(scope, organization, endpoints, fields=None, security=None):
	"""Giá trị pending có hợp đồng API; bản thủ công chỉ chứa trạng thái và tham chiếu riêng.
	security: các nhóm đọc từ security_and_analysis của repository ({nhóm: trường})."""
	pending = scope.get('pending_settings', {})
	sections = {'collections', 'endpoints', 'settings', *(security or {})}
	if not isinstance(pending, dict) or set(pending) - sections:
		raise ValueError(f'pending_settings chỉ nhận {", ".join(sorted(sections))}')
	groups = catalog.ORG_GROUPS if organization else catalog.REPO_GROUPS
	for section, definitions in (
		('collections', groups),
		('endpoints', endpoints),
		('settings', fields or {}),
		*(security or {}).items(),
	):
		items = pending.get(section, {})
		if not isinstance(items, dict) or set(items) - set(definitions):
			raise ValueError(f'pending_settings/{section}: nhóm không được hỗ trợ')
		for key, value in items.items():
			if value is not None and key in scope.get(section, {}) and value != scope[section][key]:
				# Không có hai mục tiêu khác nhau cho cùng tài nguyên; sửa mục đang quản lý trực tiếp.
				raise ValueError(f'pending_settings/{section}/{key}: trùng mục tiêu đã quản lý')
	manual = scope.get('manual_settings', {})
	allowed = MANUAL_GROUPS if organization else REPO_MANUAL_GROUPS
	if not isinstance(manual, dict) or set(manual) - set(allowed):
		raise ValueError('manual_settings có nhóm không được hỗ trợ')
	for key, item in manual.items():
		if (
			not isinstance(item, dict)
			or set(item) != {'status', 'configuration_source'}
			or item['status'] not in MANUAL_STATUS
		):
			raise ValueError(f'manual_settings/{key}: sai cấu trúc hoặc trạng thái')
		reference = item['configuration_source']
		if reference is not None and (
			not isinstance(reference, str)
			or not re.fullmatch(r'[A-Za-z0-9_.:/#-]{1,256}', reference)
		):
			raise ValueError(f'manual_settings/{key}: tham chiếu riêng không hợp lệ')
		if item['status'] in ('pending', 'verified') and reference is None:
			raise ValueError(f'manual_settings/{key}: thiếu configuration_source ngoài Git')


def configuredScope(scope):
	"""Null là chưa biết; chỉ mục tiêu khai báo rõ mới tham gia hợp đồng áp dụng hiện có."""
	result = copy.deepcopy(scope)
	for section, items in scope.get('pending_settings', {}).items():
		for key, value in items.items():
			if value is not None:
				result.setdefault(section, {})[key] = copy.deepcopy(value)
	return result


def refreshScope(previous, captured, base, unavailable, endpoints, fields=None, security=None):
	"""Giữ bản thủ công; chỗ chưa biết tự được thay bằng dữ liệu API khi đã đọc được. Repository riêng tư
	mà API không trả security_and_analysis có ô chưa biết cho từng trường của các nhóm trong security."""
	result = copy.deepcopy(captured)
	if 'web_rulesets' in previous.get('observed', {}):
		result.setdefault('observed', {})['web_rulesets'] = copy.deepcopy(
			previous['observed']['web_rulesets']
		)
	if base.startswith('orgs/'):
		for key in ('repository_policies',):
			if key in previous.get('observed', {}):
				result.setdefault('observed', {})[key] = copy.deepcopy(previous['observed'][key])
	groups = catalog.ORG_GROUPS if base.startswith('orgs/') else catalog.REPO_GROUPS
	pending = {}
	for section, paths in (
		('collections', {key: catalog.GROUP_PATHS[key] for key in groups}),
		('endpoints', {key: key for key in endpoints}),
		('settings', {key: f'settings/{key}' for key in fields or {}}),
	):
		for key, suffix in paths.items():
			if f'{base}/{suffix}' in unavailable:
				pending.setdefault(section, {})[key] = copy.deepcopy(
					previous.get('pending_settings', {}).get(section, {}).get(key)
				)
	if f'{base} (security_and_analysis)' in unavailable:
		for section, keys in (security or {}).items():
			for key in keys:
				pending.setdefault(section, {})[key] = copy.deepcopy(
					previous.get('pending_settings', {}).get(section, {}).get(key)
				)
	if pending:
		result['pending_settings'] = pending
	else:
		result.pop('pending_settings', None)
	allowed = MANUAL_GROUPS if base.startswith('orgs/') else REPO_MANUAL_GROUPS
	result['manual_settings'] = {
		key: copy.deepcopy(
			previous.get('manual_settings', {}).get(
				key, {'status': 'unverified', 'configuration_source': None}
			)
		)
		for key in sorted(allowed)
	}
	return result


def scopeProblems(scope, base, privateValues=None):
	from orgsetup import patterns, registries

	problems = []
	readPrivate = localdata.privateValue if privateValues is None else privateValues.__getitem__
	# Bao gồm mọi giá trị tham chiếu: variables, webhook, IP, regex, registry và mục pending đã điền.
	# Tham chiếu thủ công không được che giá trị API bắt buộc khi dùng chung tên khóa.
	referenceScope = dict(scope, manual_settings={})
	references = localdata.valueReferences({'organization': referenceScope, 'repositories': {}})
	optionalReferences = set()
	configured = configuredScope(scope)
	for item in configured.get('collections', {}).get('custom_patterns', []):
		try:
			patterns.definition(json.loads(readPrivate(item['definition_source'])))
		except (KeyError, ValueError, TypeError, OSError):
			problems.append(f'{base}/collections/custom_patterns: thiếu hoặc sai định nghĩa riêng')
	for item in configured.get('collections', {}).get('private_registries', []):
		try:
			definition = registries.definition(json.loads(readPrivate(item['definition_source'])))
			if definition['auth_type'].startswith('oidc_'):
				optionalReferences.add(item['credential_source'])
			else:
				try:
					registries.credentialDefinition(
						json.loads(readPrivate(item['credential_source']))
					)
				except (KeyError, ValueError, TypeError, OSError):
					problems.append(
						f'{base}/collections/private_registries: thiếu hoặc sai credentials riêng'
					)
		except (KeyError, ValueError, TypeError, OSError):
			problems.append(
				f'{base}/collections/private_registries: thiếu hoặc sai định nghĩa riêng'
			)
	for reference in sorted(references - optionalReferences):
		try:
			readPrivate(reference)
		except (KeyError, ValueError, OSError):
			problems.append(f'{base}/private_values/{reference}: thiếu bản giá trị riêng đọc được')
	for section, items in scope.get('pending_settings', {}).items():
		for key, value in items.items():
			problems.append(
				f'{base}/pending_settings/{section}/{key}: '
				+ ('chưa biết giá trị' if value is None else 'mục tiêu local chờ xác minh API')
			)
	for key, item in scope.get('manual_settings', {}).items():
		if item['status'] == 'not_applicable':
			continue
		if item['configuration_source'] is not None:
			try:
				if not readPrivate(item['configuration_source']).strip():
					raise ValueError('Bản cấu hình riêng rỗng')
			except (KeyError, ValueError, OSError):
				problems.append(f'{base}/manual_settings/{key}: thiếu bản cấu hình riêng đọc được')
		if item['status'] != 'verified':
			problems.append(f'{base}/manual_settings/{key}: cần cấu hình và xác nhận thủ công')
	return problems


def coverageProblems(scope, base):
	"""Bản đầy đủ phải khai báo mọi nhóm của bộ nhập; bỏ nhóm không làm bản sao lưu trở nên đầy đủ."""
	from orgsetup import configuration

	organization = base.startswith('orgs/')
	problems = []
	for section, keys in (
		('manual_settings', MANUAL_GROUPS if organization else REPO_MANUAL_GROUPS),
		('collections', catalog.ORG_GROUPS if organization else catalog.REPO_GROUPS),
		('settings', configuration.ORG_FIELDS if organization else configuration.REPO_FIELDS),
		('web_settings', configuration.ORG_WEB_FIELDS if organization else ()),
		('private_settings', configuration.PRIVATE_ORG_FIELDS if organization else ()),
	):
		problems.extend(
			f'{base}/{section}/{key}: chưa khai báo trong bản khôi phục'
			for key in sorted(set(keys) - set(scope.get(section, {})))
			if key not in scope.get('pending_settings', {}).get(section, {})
		)
	definitions = configuration.endpointDefinitions(
		organization, scope.get('settings', {}).get('visibility') != 'public'
	)
	for suffix in definitions:
		if suffix in configuration.SELECTED_ENDPOINTS:
			parent, selector = configuration.SELECTED_ENDPOINTS[suffix]
			if scope.get('endpoints', {}).get(parent, {}).get(selector) != 'selected':
				continue
		if suffix not in scope.get('endpoints', {}) and suffix not in scope.get(
			'pending_settings', {}
		).get('endpoints', {}):
			problems.append(f'{base}/endpoints/{suffix}: chưa khai báo trong bản khôi phục')
	problems.extend(
		f'{base}/{key}: chưa khai báo trong bản khôi phục'
		for key in (
			('runner_groups', 'security_configurations')
			if organization
			else ('security', 'security_configuration')
		)
		if key not in scope
	)
	if organization:
		problems.extend(
			f'{base}/collections/dependabot_access/default_level: chưa biết giá trị'
			for item in scope.get('collections', {}).get('dependabot_access', [])
			if 'default_level' not in item
		)
	return problems


def configProblems(config, complete=False, privateValues=None):
	return [
		problem
		for base, scope in scopes(config)
		for problem in (
			*scopeProblems(scope, base, privateValues),
			*(coverageProblems(scope, base) if complete else []),
		)
	]


def scopes(config):
	return [
		(f'orgs/{github.ORG}', config['organization']),
		*[(f'repos/{github.ORG}/{name}', scope) for name, scope in config['repositories'].items()],
	]


def showInventory(config):
	"""Chỉ đọc local, không cần đăng nhập hoặc in nội dung cấu hình riêng."""
	for base, scope in scopes(config):
		print(f'== {base}')
		for section in (
			'settings',
			'private_settings',
			'web_settings',
			'endpoints',
			'security',
			'security_options',
			'collections',
		):
			print(f'   {section}: {len(scope.get(section, {}))} mục được quản lý')
		for key, item in scope.get('manual_settings', {}).items():
			print(f'   {key}: {item["status"]} — {MANUAL_GROUPS[key]}')
	problems = configProblems(config, complete=True)
	for detail in problems:
		print(f'⚠ {detail}')
	for path in config['unavailable']:
		print(f'⚠ {path}: API chưa xác minh')
	print(
		'Trạng thái thủ công do quản trị xác nhận; danh mục local không chứng minh đã sao lưu mọi trang web.'
	)
	return 1 if problems or config['unavailable'] else 0
