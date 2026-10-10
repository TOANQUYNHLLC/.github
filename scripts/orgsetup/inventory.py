"""Khai báo cài đặt chưa đọc được và bản khôi phục thủ công, không suy đoán giá trị web."""

import copy
import re

from orgsetup import catalog, github, localdata

MANUAL_GROUPS = {
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
	'github_apps',
	'codespaces',
	'secrets',
	'webhook_credentials',
	'deploy_keys',
	'custom_pattern_publication',
	'members_and_collaborators',
}
MANUAL_STATUS = ('unverified', 'pending', 'verified', 'not_applicable')


def validateScope(scope, organization, endpoints, fields=None):
	"""Giá trị pending có hợp đồng API; bản thủ công chỉ chứa trạng thái và tham chiếu riêng."""
	pending = scope.get('pending_settings', {})
	if not isinstance(pending, dict) or set(pending) - {'collections', 'endpoints', 'settings'}:
		raise ValueError('pending_settings chỉ nhận collections, endpoints và settings')
	groups = catalog.ORG_GROUPS if organization else catalog.REPO_GROUPS
	for section, definitions in (
		('collections', groups),
		('endpoints', endpoints),
		('settings', fields or {}),
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


def refreshScope(previous, captured, base, unavailable, endpoints, fields=None):
	"""Giữ bản thủ công; chỗ chưa biết tự được thay bằng dữ liệu API khi đã đọc được."""
	result = copy.deepcopy(captured)
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


def scopeProblems(scope, base):
	problems = []
	for key, item in scope.get('private_settings', {}).items():
		try:
			localdata.privateValue(item['value_source'])
		except (ValueError, OSError):
			problems.append(f'{base}/private_settings/{key}: thiếu bản giá trị riêng đọc được')
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
				if not localdata.privateValue(item['configuration_source']).strip():
					raise ValueError('Bản cấu hình riêng rỗng')
			except (ValueError, OSError):
				problems.append(f'{base}/manual_settings/{key}: thiếu bản cấu hình riêng đọc được')
		if item['status'] != 'verified':
			problems.append(f'{base}/manual_settings/{key}: cần cấu hình và xác nhận thủ công')
	return problems


def configProblems(config):
	return [problem for base, scope in scopes(config) for problem in scopeProblems(scope, base)]


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
	problems = configProblems(config)
	for detail in problems:
		print(f'⚠ {detail}')
	for path in config['unavailable']:
		print(f'⚠ {path}: API chưa xác minh')
	print(
		'Trạng thái thủ công do quản trị xác nhận; danh mục local không chứng minh đã sao lưu mọi trang web.'
	)
	return 1 if problems or config['unavailable'] else 0
