"""Lệnh settings, org-settings: cài đặt repository, tính năng bảo mật, quyền GitHub Actions, cài đặt tổ chức."""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

from orgsetup import github, resources

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

# Nguồn cài đặt được nhập từ GitHub; không duy trì một bản giá trị cố định riêng trong Python.
from orgsetup.configuration import equivalentEndpointValue, readConfig, repositorySettingChanges

CONFIG = readConfig()
REPOSITORY_SETTINGS = CONFIG['repository_defaults']
REPOSITORY_OVERRIDES = {name: scope['settings'] for name, scope in CONFIG['repositories'].items()}
MERGE_SETTINGS = {
	key: value
	for key, value in REPOSITORY_SETTINGS.items()
	if key.startswith(('allow_', 'merge_', 'squash_', 'delete_branch_'))
}
ORG_SETTINGS = CONFIG['organization']['settings']
ORG_WEB_ONLY_SETTINGS = CONFIG['organization']['web_settings']
# Lệnh settings truyền thống giữ trạng thái bật/tắt Actions; local-settings quản lý trạng thái từ tệp.
ACTIONS_PERMISSIONS = {
	key: value
	for key, value in CONFIG['repositories']
	.get('.github', {})
	.get('endpoints', {})
	.get('actions/permissions', {})
	.items()
	if key != 'enabled'
}
ORG_ACTIONS_PERMISSIONS = {
	key: value
	for key, value in CONFIG['organization']['endpoints'].get('actions/permissions', {}).items()
	if key != 'enabled_repositories'
}
WORKFLOW_PERMISSIONS = CONFIG['organization']['endpoints'].get('actions/permissions/workflow', {})


def citationKeywords():
	"""Từ khóa YAML trong CITATION.cff — topics của repository .github; dữ liệu sai không xóa topics."""
	path = github.ROOT / 'CITATION.cff'
	result = subprocess.run(
		[
			'ruby',
			'-ryaml',
			'-rjson',
			'-rdate',
			'-e',
			'data = YAML.safe_load(File.read(ARGV[0]), permitted_classes: [Date], aliases: true, filename: ARGV[0]); puts JSON.dump(data.is_a?(Hash) ? data["keywords"] : nil)',
			str(path),
		],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode:
		detail = (
			result.stderr.strip().splitlines()[0]
			if result.stderr.strip()
			else 'Ruby không đọc được tệp'
		)
		raise ValueError(f'CITATION.cff: không đọc được keywords ({detail})')
	keywords = json.loads(result.stdout)
	if not isinstance(keywords, list) or any(
		not isinstance(word, str) or not word.strip() for word in keywords
	):
		raise ValueError('CITATION.cff: keywords phải là danh sách các chuỗi không trống')
	return keywords


def repositorySettings(repo, discussions=False):
	"""Cài đặt mong muốn của repository: chung cho mọi repository, cộng phần riêng của nó."""
	overrides = next(
		(
			value
			for name, value in REPOSITORY_OVERRIDES.items()
			if name.casefold() == repo.casefold()
		),
		{},
	)
	wanted = dict(REPOSITORY_SETTINGS, **overrides)
	if discussions:
		wanted['has_discussions'] = True
	return wanted


def validateCurrentSettings(endpoint, current, wanted):
	"""Xác minh danh tính và mọi trường trước khi ghi, kể cả trước thao tác bỏ archive."""
	if not isinstance(current, dict):
		raise TypeError(f'{endpoint}: không đọc được object cài đặt')
	github.validateIdentity(endpoint, current)
	for key, value in wanted.items():
		if key not in current or (
			type(current[key]) is not type(value)
			and not (isinstance(value, str) and current[key] is None)
		):
			raise ValueError(f'{endpoint}: không đọc được cài đặt {key}')


def updateSettings(endpoint, current, wanted, apply, what):
	"""So cài đặt, ghi phần khác và đọc lại để xác nhận; trả trạng thái mới cho các bước phụ thuộc."""
	validateCurrentSettings(endpoint, current, wanted)
	changes = {
		key: value
		for key, value in wanted.items()
		if current.get(key) != value and not (value == '' and current.get(key) is None)
	}
	if not changes:
		print(f'   ✔ {what} đã đúng')
		return current
	for key, value in changes.items():
		print(f'   {"" if apply else "(xem trước) "}{key}: {current.get(key)} → {value}')
	if apply:
		plan = []
		if endpoint.startswith('repos/'):
			repositorySettingChanges(plan, endpoint, current, changes)
		else:
			plan.append((endpoint, 'PATCH', changes, changes))
		for path, method, body, _ in plan:
			github.gh('api', '-X', method, path, '--input', '-', stdin=json.dumps(body))
		confirmed = github.ghJson('api', endpoint)
		validateCurrentSettings(endpoint, confirmed, wanted)
		unconfirmed = [
			key
			for key, value in wanted.items()
			if confirmed[key] != value and not (value == '' and confirmed[key] is None)
		]
		if unconfirmed:
			raise RuntimeError(
				f'{endpoint}: GitHub chưa áp dụng đúng cài đặt: {", ".join(unconfirmed)}'
			)
		print('   ✔ đã cập nhật')
		return confirmed
	return current


def syncSettings(repos, apply, discussions):
	for repo in repos:
		print(f'== {github.ORG}/{repo}')
		endpoint = f'repos/{github.ORG}/{repo}/actions/permissions'
		# Quyền Actions không phụ thuộc cài đặt repository: đọc song song từ đầu, so và in sau cùng như cũ.
		with ThreadPoolExecutor(max_workers=1) as pool:
			actions = pool.submit(readActions, endpoint)
			repositoryEndpoint = f'repos/{github.ORG}/{repo}'
			current = github.ghJson('api', repositoryEndpoint)
			wanted = repositorySettings(repo, discussions)
			validateCurrentSettings(repositoryEndpoint, current, wanted)
			archiveChanged = 'archived' in wanted and current['archived'] != wanted['archived']
			archived = wanted.pop('archived', None)
			if archiveChanged and not archived:
				current = updateSettings(
					repositoryEndpoint,
					current,
					{'archived': False},
					apply,
					'trạng thái archive',
				)
			# Bỏ archive trước Discussions và các cập nhật khác; archive sau topics, bảo mật, quyền Actions.
			current = updateSettings(
				repositoryEndpoint,
				current,
				wanted,
				apply,
				'cài đặt repository',
			)
			syncTopics(repo, current, apply)
			syncSecurity(repo, current, apply)
			syncActions(endpoint, ACTIONS_PERMISSIONS, 'enabled', apply, actions.result())
			if archiveChanged and archived:
				updateSettings(
					repositoryEndpoint,
					current,
					{'archived': True},
					apply,
					'trạng thái archive',
				)


def syncTopics(repo, current, apply):
	"""Topics của .github khớp keywords trong CITATION.cff; repository khác không quản lý."""
	if repo.casefold() != '.github':
		return
	if (
		not isinstance(current, dict)
		or not isinstance(current.get('topics'), list)
		or any(not isinstance(topic, str) for topic in current['topics'])
	):
		raise ValueError('không đọc được topics hiện tại của repository .github')
	wanted = citationKeywords()
	if equivalentEndpointValue('topics', 'names', current['topics'], wanted):
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
			return github.ghJson('api', path)
		except (RuntimeError, ValueError) as exc:
			return exc

	with ThreadPoolExecutor(max_workers=2) as pool:
		return list(pool.map(read, (endpoint, f'{endpoint}/workflow')))


def validateActions(current, keep):
	"""Chỉ so quyền khi đọc được trạng thái bật/tắt và các trường bắt buộc của endpoint."""
	if not isinstance(current, dict):
		raise TypeError('phản hồi quyền phải là object')
	if keep:
		if (keep == 'enabled' and type(current.get(keep)) is not bool) or (
			keep == 'enabled_repositories' and current.get(keep) not in ('all', 'none', 'selected')
		):
			raise ValueError(f'thiếu hoặc sai trạng thái {keep}')
		if current[keep] in (False, 'none'):
			return
		if current.get('allowed_actions') not in ('all', 'local_only', 'selected'):
			raise ValueError('thiếu hoặc sai allowed_actions')
		if 'sha_pinning_required' in current and type(current['sha_pinning_required']) is not bool:
			raise ValueError('sha_pinning_required phải là boolean')
	elif (
		current.get('default_workflow_permissions') not in ('read', 'write')
		or type(current.get('can_approve_pull_request_reviews')) is not bool
	):
		raise ValueError('thiếu hoặc sai quyền mặc định GITHUB_TOKEN')


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
	for (path, target, keep), reading in zip(targets, readings, strict=True):
		current = reading
		if not isinstance(current, Exception):
			try:
				validateActions(current, keep)
			except (ValueError, TypeError) as exc:
				current = exc
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
		current = updateSettings(
			f'orgs/{github.ORG}', current, ORG_SETTINGS, apply, 'cài đặt tổ chức'
		)
		for key, value in ORG_WEB_ONLY_SETTINGS.items():
			observed = current.get(key)
			if key == 'installed_apps':
				try:
					observed = resources.installedApps()
				except (RuntimeError, ValueError, TypeError):
					print('   ⚠ không đọc được danh sách GitHub Apps; chưa đối chiếu cài đặt này')
					continue
			if observed != value:
				print(f'   ✘ {key}: {observed} ≠ {value} — sửa tại Organization settings trên web')
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
	if not isinstance(current, dict) or type(current.get('private')) is not bool:
		raise ValueError(f'{repo}: không đọc được chế độ công khai/riêng tư của repository')
	analysis = current.get('security_and_analysis')
	off, unread, featureStatuses = [], False, {}
	for name in SECURITY_FEATURES:
		feature = analysis.get(name) if isinstance(analysis, dict) else None
		status = feature.get('status') if isinstance(feature, dict) else None
		featureStatuses[name] = status
		if status not in ('enabled', 'disabled'):
			print(f'   ⚠ không đọc được trạng thái {name} — bỏ qua tính năng này')
			unread = True
		elif status == 'disabled':
			off.append(name)
	if 'secret_scanning_push_protection' in off and featureStatuses['secret_scanning'] not in (
		'enabled',
		'disabled',
	):
		print(
			'   ⚠ bỏ qua secret_scanning_push_protection: chưa đọc được trạng thái secret_scanning'
		)
		off.remove('secret_scanning_push_protection')
	private = current['private']
	for label in sorted(set(SECURITY_ENDPOINTS) - set(securityEndpoints(private))):
		print(f'   – bỏ qua {label}: chỉ dành cho repository công khai')

	def securityStatus(endpoint):
		"""True/False theo trạng thái bật; lỗi đọc thì trả lỗi để báo theo thứ tự."""
		try:
			if endpoint in STATUS_ONLY_ENDPOINTS:
				return github.ghExists(f'repos/{github.ORG}/{repo}/{endpoint}')
			data = github.ghJson('api', f'repos/{github.ORG}/{repo}/{endpoint}')
			if not isinstance(data, dict) or type(data.get('enabled')) is not bool:
				raise ValueError('phản hồi trạng thái thiếu enabled dạng boolean')
			return data['enabled']
		except (RuntimeError, ValueError) as exc:
			return exc

	# Đọc mọi trạng thái cùng lúc — mỗi lần chờ GitHub gần một giây.
	wanted = securityEndpoints(private)
	with ThreadPoolExecutor(max_workers=max(1, len(wanted))) as pool:
		statuses = list(pool.map(securityStatus, wanted.values()))
	endpoints, alertsUnread = {}, False
	for (label, endpoint), status in zip(wanted.items(), statuses, strict=True):
		if isinstance(status, Exception):
			print(f'   ⚠ không đọc được trạng thái {label}: {status}')
			unread = True
			if endpoint == 'vulnerability-alerts':
				alertsUnread = True
		elif not status:
			endpoints[label] = endpoint
	if alertsUnread and 'Dependabot security updates' in endpoints:
		print('   ⚠ bỏ qua Dependabot security updates: chưa đọc được trạng thái Dependabot alerts')
		del endpoints['Dependabot security updates']
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
		if endpoint == 'automated-security-fixes' and alertsUnread:
			print('   ⚠ bỏ qua Dependabot security updates: chưa bật được Dependabot alerts')
			continue
		try:
			github.gh('api', '-X', 'PUT', f'repos/{github.ORG}/{repo}/{endpoint}')
			print(f'   ✔ đã bật {label}')
		except RuntimeError as exc:
			print(f'   ⚠ không bật được {label}: {exc}')
			if endpoint == 'vulnerability-alerts':
				alertsUnread = True
