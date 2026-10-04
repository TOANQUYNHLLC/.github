"""Lệnh settings, org-settings: cài đặt repository, tính năng bảo mật, quyền GitHub Actions, cài đặt tổ chức."""

import json
import re
from concurrent.futures import ThreadPoolExecutor

from orgsetup import github

SECURITY_FEATURES = ('secret_scanning', 'secret_scanning_push_protection')

# Endpoint bật bằng PUT, đọc trạng thái qua trường enabled; Dependabot alerts bật trước security updates.
SECURITY_ENDPOINTS = {
	'Dependabot alerts': 'vulnerability-alerts',
	'Dependabot security updates': 'automated-security-fixes',
	'báo cáo lỗ hổng riêng tư': 'private-vulnerability-reporting',
	# Tag và tệp đính kèm của Release đã phát hành không đổi được; tổ chức đang bắt buộc cho mọi repository.
	'Release bất biến (immutable releases)': 'immutable-releases',
}

# Chỉ bật được cho repository công khai (báo cáo lỗ hổng riêng tư).
PUBLIC_ONLY_ENDPOINTS = ('private-vulnerability-reporting',)

# Đọc trạng thái bằng mã HTTP (204 bật, 404 tắt), không có trường enabled.
STATUS_ONLY_ENDPOINTS = ('vulnerability-alerts',)

MERGE_SETTINGS = {
	'allow_squash_merge': True,
	'allow_merge_commit': True,
	# Rebase and merge tạo lại commit không có chữ ký (ADR 0006).
	'allow_rebase_merge': False,
	'allow_auto_merge': True,
	'allow_update_branch': True,
	'delete_branch_on_merge': True,
	'squash_merge_commit_title': 'PR_TITLE',
	'squash_merge_commit_message': 'PR_BODY',
	'merge_commit_title': 'MERGE_MESSAGE',
	'merge_commit_message': 'PR_TITLE',
}

# Cài đặt mọi repository (allow_rebase_merge theo ADR 0006).
REPOSITORY_SETTINGS = {
	'has_issues': True,
	'has_projects': False,
	'has_wiki': False,
	'web_commit_signoff_required': True,
	**MERGE_SETTINGS,
}

# Cài đặt riêng từng repository, ghi đè REPOSITORY_SETTINGS.
REPOSITORY_OVERRIDES = {
	'.github': {
		'description': 'Hồ sơ tổ chức, tệp cộng đồng mặc định, biểu mẫu và cấu hình GitHub dùng chung cho mọi '
		'repository của CÔNG TY TNHH TOÀN QUỲNH',
		'homepage': 'https://toanquynh.com',
		'has_discussions': True,
	},
}

# Quyền GitHub Actions; không quản lý trạng thái bật/tắt (enabled, enabled_repositories) — người quản trị
# tự bật, tắt trên web, script gửi lại giá trị đang có vì API bắt buộc trường này.
ACTIONS_PERMISSIONS = {'allowed_actions': 'all', 'sha_pinning_required': True}

ORG_ACTIONS_PERMISSIONS = {'allowed_actions': 'all', 'sha_pinning_required': False}

WORKFLOW_PERMISSIONS = {
	'default_workflow_permissions': 'read',
	# Workflow monthly-release.yml mở Pull Request phát hành.
	'can_approve_pull_request_reviews': True,
}

# Cài đặt tổ chức đổi được qua API.
ORG_SETTINGS = {
	'name': 'TOAN QUYNH CO., LTD',
	'description': 'The Official Repository of TOAN QUYNH Co., Ltd',
	'blog': 'https://toanquynh.com',
	'email': 'toanquynhvn@gmail.com',
	'location': 'Vietnam',
	'default_repository_permission': 'read',
	'members_can_create_repositories': True,
	'members_can_create_public_repositories': True,
	'members_can_create_private_repositories': True,
	'members_can_create_pages': True,
	'members_can_create_public_pages': True,
	'members_can_create_private_pages': True,
	'members_can_fork_private_repositories': True,
	'has_organization_projects': True,
	'has_repository_projects': True,
	'web_commit_signoff_required': True,
	'deploy_keys_enabled_for_repositories': True,
}

# Cài đặt tổ chức API không đổi được — chỉ so, sửa tại Organization settings trên web.
ORG_WEB_ONLY_SETTINGS = {
	'two_factor_requirement_enabled': True,
	'default_repository_branch': 'main',
	'members_can_change_repo_visibility': True,
	'members_can_delete_repositories': True,
	'members_can_delete_issues': True,
	'members_can_invite_outside_collaborators': True,
	'members_can_create_teams': True,
	'members_can_view_dependency_insights': True,
	'readers_can_create_discussions': True,
	'display_commenter_full_name_setting_enabled': False,
}


def citationKeywords():
	"""Từ khóa trong CITATION.cff — topics của repository .github."""
	text = (github.ROOT / 'CITATION.cff').read_text(encoding='utf-8')
	block = re.search(r'^keywords:\n((?:[ \t]+- .+\n)+)', text, re.MULTILINE)
	return re.findall(r'- (.+)', block.group(1)) if block else []


def repositorySettings(repo, discussions=False):
	"""Cài đặt mong muốn của repository: chung cho mọi repository, cộng phần riêng của nó."""
	wanted = dict(REPOSITORY_SETTINGS, **REPOSITORY_OVERRIDES.get(repo, {}))
	if discussions:
		wanted['has_discussions'] = True
	return wanted


def updateSettings(endpoint, current, wanted, apply, what):
	"""So cài đặt đang có với cài đặt mong muốn; --apply thì PATCH phần khác."""
	changes = {key: value for key, value in wanted.items() if current.get(key) != value}
	if not changes:
		print(f'   ✔ {what} đã đúng')
		return
	for key, value in changes.items():
		print(f'   {"" if apply else "(xem trước) "}{key}: {current.get(key)} → {value}')
	if apply:
		github.gh('api', '-X', 'PATCH', endpoint, '--input', '-', stdin=json.dumps(changes))
		print('   ✔ đã cập nhật')


def syncSettings(repos, apply, discussions):
	for repo in repos:
		print(f'== {github.ORG}/{repo}')
		endpoint = f'repos/{github.ORG}/{repo}/actions/permissions'
		# Quyền Actions không phụ thuộc cài đặt repository: đọc song song từ đầu, so và in sau cùng như cũ.
		with ThreadPoolExecutor(max_workers=1) as pool:
			actions = pool.submit(readActions, endpoint)
			current = github.ghJson('api', f'repos/{github.ORG}/{repo}')
			updateSettings(
				f'repos/{github.ORG}/{repo}',
				current,
				repositorySettings(repo, discussions),
				apply,
				'cài đặt repository',
			)
			syncTopics(repo, current, apply)
			syncSecurity(repo, current, apply)
			syncActions(endpoint, ACTIONS_PERMISSIONS, 'enabled', apply, actions.result())


def syncTopics(repo, current, apply):
	"""Topics của .github khớp keywords trong CITATION.cff; repository khác không quản lý."""
	if repo != '.github':
		return
	wanted = citationKeywords()
	if sorted(current.get('topics') or []) == sorted(wanted):
		print('   ✔ topics khớp CITATION.cff')
		return
	print(f'   {"" if apply else "(xem trước) "}topics: {current.get("topics")} → {wanted}')
	if apply:
		body = json.dumps({'names': wanted})
		github.gh(
			'api', '-X', 'PUT', f'repos/{github.ORG}/{repo}/topics', '--input', '-', stdin=body
		)


def readActions(endpoint):
	"""Đọc cùng lúc quyền GitHub Actions tại endpoint và quyền mặc định của GITHUB_TOKEN; lỗi đọc thì trả lỗi
	để syncActions báo theo thứ tự."""

	def read(path):
		try:
			return github.ghJson('api', path) or {}
		except RuntimeError as exc:
			return exc

	with ThreadPoolExecutor(max_workers=2) as pool:
		return list(pool.map(read, (endpoint, f'{endpoint}/workflow')))


def syncActions(endpoint, wanted, enabledKey, apply, readings=None):
	"""Quyền GitHub Actions tại endpoint (repository hoặc tổ chức) và quyền mặc định của GITHUB_TOKEN;
	gửi lại enabledKey đang có — API bắt buộc trường này nhưng script không bật, tắt Actions. readings: kết quả
	readActions(endpoint) đã đọc trước (không có thì đọc lúc này); so và ghi vẫn lần lượt."""
	changed = skipped = unread = False
	targets = (
		(endpoint, wanted, enabledKey),
		(f'{endpoint}/workflow', WORKFLOW_PERMISSIONS, None),
	)
	if readings is None:
		readings = readActions(endpoint)
	for (path, target, keep), current in zip(targets, readings, strict=True):
		if isinstance(current, Exception):
			print(f'   ⚠ không đọc được {path}: {current}')
			unread = True
			continue
		# Actions đang tắt: GitHub không trả allowed_actions, sha_pinning_required — so khi bật lại.
		if keep and current.get(keep) in (False, 'none'):
			print('   – bỏ qua quyền GitHub Actions: Actions đang tắt')
			skipped = True
			continue
		changes = {key: value for key, value in target.items() if current.get(key) != value}
		for key, value in changes.items():
			changed = True
			print(
				f'   {"" if apply else "(xem trước) "}Actions {key}: {current.get(key)} → {value}'
			)
		if not changes or not apply:
			continue
		body = dict(changes, **({keep: current.get(keep)} if keep else {}))
		try:
			github.gh('api', '-X', 'PUT', path, '--input', '-', stdin=json.dumps(body))
		except RuntimeError as exc:
			print(f'   ⚠ không cập nhật được {path}: {exc}')
	# Không báo "đã đúng" cho phần chưa so được (không đọc được, Actions đang tắt).
	if not changed and not unread:
		print(f'   ✔ quyền {"GITHUB_TOKEN" if skipped else "GitHub Actions"} đã đúng')


def syncOrgSettings(apply):
	"""Cài đặt tổ chức và quyền GitHub Actions cấp tổ chức."""
	print(f'== cài đặt tổ chức {github.ORG}')
	endpoint = f'orgs/{github.ORG}/actions/permissions'
	# Như syncSettings: đọc quyền Actions song song với cài đặt tổ chức.
	with ThreadPoolExecutor(max_workers=1) as pool:
		actions = pool.submit(readActions, endpoint)
		current = github.ghJson('api', f'orgs/{github.ORG}')
		updateSettings(f'orgs/{github.ORG}', current, ORG_SETTINGS, apply, 'cài đặt tổ chức')
		for key, value in ORG_WEB_ONLY_SETTINGS.items():
			if current.get(key) != value:
				print(
					f'   ✘ {key}: {current.get(key)} ≠ {value} — sửa tại Organization settings trên web'
				)
		syncActions(
			endpoint, ORG_ACTIONS_PERMISSIONS, 'enabled_repositories', apply, actions.result()
		)


def securityEndpoints(private):
	"""Endpoint bảo mật áp dụng được cho repository; repository riêng tư bỏ qua endpoint chỉ dành cho công khai."""
	return {
		label: endpoint
		for label, endpoint in SECURITY_ENDPOINTS.items()
		if not (private and endpoint in PUBLIC_ONLY_ENDPOINTS)
	}


def syncSecurity(repo, current, apply):
	"""Bật tính năng bảo mật còn tắt; GitHub từ chối (gói trả phí, repository riêng tư) thì cảnh báo, không dừng."""
	analysis = current.get('security_and_analysis') or {}
	off = [
		name for name in SECURITY_FEATURES if (analysis.get(name) or {}).get('status') != 'enabled'
	]
	private = bool(current.get('private'))
	for label in sorted(set(SECURITY_ENDPOINTS) - set(securityEndpoints(private))):
		print(f'   – bỏ qua {label}: chỉ dành cho repository công khai')

	def securityStatus(endpoint):
		"""True/False theo trạng thái bật; lỗi đọc thì trả lỗi để báo theo thứ tự."""
		try:
			if endpoint in STATUS_ONLY_ENDPOINTS:
				return github.ghExists(f'repos/{github.ORG}/{repo}/{endpoint}')
			return bool(
				(github.ghJson('api', f'repos/{github.ORG}/{repo}/{endpoint}') or {}).get('enabled')
			)
		except RuntimeError as exc:
			return exc

	# Đọc mọi trạng thái cùng lúc — mỗi lần chờ GitHub gần một giây.
	wanted = securityEndpoints(private)
	with ThreadPoolExecutor(max_workers=max(1, len(wanted))) as pool:
		statuses = list(pool.map(securityStatus, wanted.values()))
	endpoints, unread = {}, False
	for (label, endpoint), status in zip(wanted.items(), statuses, strict=True):
		if isinstance(status, Exception):
			print(f'   ⚠ không đọc được trạng thái {label}: {status}')
			unread = True
		elif not status:
			endpoints[label] = endpoint
	if not off and not endpoints and not unread:
		print('   ✔ tính năng bảo mật đã bật')
	for name in off + list(endpoints):
		print(f'   {"" if apply else "(xem trước) "}bật {name}')
	if not apply:
		return
	if off:
		body = json.dumps({'security_and_analysis': {name: {'status': 'enabled'} for name in off}})
		try:
			github.gh(
				'api', '-X', 'PATCH', f'repos/{github.ORG}/{repo}', '--input', '-', stdin=body
			)
		except RuntimeError as exc:
			print(f'   ⚠ không bật được {", ".join(off)}: {exc}')
	for label, endpoint in endpoints.items():
		try:
			github.gh('api', '-X', 'PUT', f'repos/{github.ORG}/{repo}/{endpoint}')
			print(f'   ✔ đã bật {label}')
		except RuntimeError as exc:
			print(f'   ⚠ không bật được {label}: {exc}')
