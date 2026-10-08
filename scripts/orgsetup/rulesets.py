"""Lệnh rulesets, org-rulesets: ruleset cấp repository và cấp tổ chức (so qua GraphQL ở gói Free)."""

import json
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from orgsetup import files, github

RULESET_FILE = github.ROOT / 'rulesets' / 'protect-main.json'

# Ruleset tag: chặn tạo, dời, xóa tag phát hành Stable.v*, Beta.v* và v* ngoài danh sách bỏ qua (ADR 0005, ADR 0012).
TAG_RULESET_FILE = github.ROOT / 'rulesets' / 'protect-release-tags.json'

# Ruleset cấp tổ chức: tệp để import trên web, sinh từ bản cấp repository bằng orgRulesets(), để so với ruleset
# đang cài trên web (lệnh org-rulesets so qua GraphQL khi REST API trả HTTP 403 ở gói Free).
ORG_RULESET_FILE = github.ROOT / 'rulesets' / 'org-protect-main.json'

ORG_RULESET_NAME = 'Protect Main (Organization)'

ORG_TAG_RULESET_FILE = github.ROOT / 'rulesets' / 'org-protect-release-tags.json'

ORG_TAG_RULESET_NAME = 'Protect Release Tags (Organization)'

# Push ruleset chặn tệp bí mật, cơ sở dữ liệu, tệp lớn (ADR 0007): cấu hình này chỉ có bản cấp tổ chức —
# GitHub chỉ áp dụng cho repository riêng tư, internal.
ORG_PUSH_RULESET_FILE = github.ROOT / 'rulesets' / 'org-protect-pushes.json'

ORG_PUSH_RULESET_NAME = 'Protect Pushes (Organization)'

# Import cấp tổ chức không nhận actor loại User ("contains an invalid actor"): bỏ qua là chủ tổ chức (actor_id
# bị bỏ qua) — cùng người quản trị; ruleset trên web tắt giới hạn hủy phê duyệt.
ORG_BYPASS_ACTORS = [{'actor_id': 1, 'actor_type': 'OrganizationAdmin', 'bypass_mode': 'always'}]

# Ruleset cấp tổ chức có thêm code scanning: kết quả CodeQL của Pull Request không được
# có cảnh báo mức errors hoặc cảnh báo bảo mật từ high trở lên. Bản cấp repository không có quy tắc này.
ORG_CODE_SCANNING_RULE = {
	'type': 'code_scanning',
	'parameters': {
		'code_scanning_tools': [
			{
				'tool': 'CodeQL',
				'alerts_threshold': 'errors',
				'security_alerts_threshold': 'high_or_higher',
			}
		]
	},
}

ORG_REPOSITORIES = {'exclude': [], 'include': ['~ALL'], 'protected': False}

# Protect Main (Organization) áp dụng thêm nhánh main của mọi repository, kể cả repository có nhánh mặc định khác (ADR 0006).
ORG_EXTRA_BRANCH = 'refs/heads/main'


def rulesetFor(repo):
	"""Ruleset Protect Main cho repository: repository khác chỉ giữ kiểm tra bắt buộc có job tương ứng."""
	ruleset = json.loads(RULESET_FILE.read_text(encoding='utf-8'))
	if repo != '.github':
		jobs = files.templateJobs()
		for rule in ruleset['rules']:
			if rule['type'] == 'required_status_checks':
				checks = rule['parameters']['required_status_checks']
				rule['parameters']['required_status_checks'] = [
					check for check in checks if check['context'] in jobs
				]
	return ruleset


def rulesetSummary(ruleset):
	"""Phần so sánh được của ruleset — bỏ id, node_id, ngày tạo, liên kết… mà GitHub thêm vào khi đọc."""
	if not isinstance(ruleset, dict):
		raise TypeError('ruleset: phản hồi phải là object')
	for field, kind in (
		('name', str),
		('target', str),
		('enforcement', str),
		('conditions', dict),
		('bypass_actors', list),
		('rules', list),
	):
		if not isinstance(ruleset.get(field), kind):
			raise TypeError(f'ruleset: trường {field} thiếu hoặc sai kiểu')
	if (
		not ruleset['name'].strip()
		or ruleset['target'] not in ('branch', 'tag', 'push')
		or ruleset['enforcement'] not in ('active', 'disabled', 'evaluate')
	):
		raise ValueError('ruleset: name, target hoặc enforcement không hợp lệ')
	for field, condition in ruleset['conditions'].items():
		if not isinstance(condition, dict):
			raise TypeError(f'ruleset: conditions.{field} phải là object')
		if field in ('ref_name', 'repository_name'):
			for key in ('include', 'exclude'):
				if not isinstance(condition.get(key), list) or any(
					not isinstance(item, str) for item in condition[key]
				):
					raise ValueError(f'ruleset: conditions.{field}.{key} phải là danh sách chuỗi')
			if field == 'repository_name' and type(condition.get('protected')) is not bool:
				raise ValueError('ruleset: conditions.repository_name.protected phải là boolean')
	actors = []
	for actor in ruleset['bypass_actors']:
		if not isinstance(actor, dict):
			raise TypeError('ruleset: bypass_actors phải chứa các object')
		actorId, actorType, mode = (
			actor.get('actor_id'),
			actor.get('actor_type'),
			actor.get('bypass_mode'),
		)
		if actorType not in (
			'Integration',
			'OrganizationAdmin',
			'RepositoryRole',
			'Team',
			'DeployKey',
			'User',
		) or mode not in ('always', 'pull_request', 'exempt'):
			raise ValueError('ruleset: actor_type hoặc bypass_mode không hợp lệ')
		if 'actor_id' not in actor or (actorId is not None and type(actorId) is not int):
			raise ValueError('ruleset: actor_id thiếu hoặc sai kiểu')
		if actorType == 'OrganizationAdmin':
			actorId = 1  # API bỏ qua ID của chủ tổ chức; dùng cùng giá trị với tệp nguồn.
		elif actorType == 'DeployKey':
			if actorId is not None:
				raise ValueError('ruleset: actor_id của DeployKey phải là null')
		elif actorId is None or actorId <= 0:
			raise ValueError('ruleset: actor_id phải là số nguyên dương')
		actors.append((actorId, actorType, mode))
	for rule in ruleset['rules']:
		if (
			not isinstance(rule, dict)
			or not isinstance(rule.get('type'), str)
			or not rule['type'].strip()
		):
			raise ValueError('ruleset: rules phải chứa các object có type không trống')
		if 'parameters' in rule and not isinstance(rule['parameters'], dict):
			raise ValueError('ruleset: parameters phải là object')
	return {
		'name': ruleset.get('name'),
		'target': ruleset.get('target'),
		'enforcement': ruleset.get('enforcement'),
		'conditions': ruleset.get('conditions'),
		'bypass_actors': sorted(actors, key=lambda actor: (actor[1], actor[0] or 0, actor[2])),
		'rules': sorted(
			json.dumps(rule, sort_keys=True, ensure_ascii=False)
			for rule in ruleset.get('rules') or []
		),
	}


def readRulesetIds(endpoint):
	"""Danh sách đầy đủ, tên và ID hợp lệ, không trùng trước khi đọc chi tiết hoặc ghi."""
	existing, ids = {}, set()
	for item in github.ghList(endpoint):
		if (
			not isinstance(item, dict)
			or not isinstance(item.get('name'), str)
			or not item['name'].strip()
			or type(item.get('id')) is not int
			or item['id'] <= 0
		):
			raise ValueError(f'{endpoint}: danh sách ruleset thiếu name hoặc id hợp lệ')
		if item['name'] in existing or item['id'] in ids:
			raise ValueError(f'{endpoint}: danh sách ruleset có name hoặc id trùng')
		existing[item['name']] = item['id']
		ids.add(item['id'])
	return existing


def readRulesetChanges(endpoint, existing, wanted):
	"""Đọc chi tiết song song, kiểm tra toàn bộ trước khi trả các thay đổi theo thứ tự tệp nguồn."""
	summaries = [rulesetSummary(ruleset) for _, ruleset in wanted]
	paths = [
		f'{endpoint}/{existing[ruleset["name"]]}' if ruleset['name'] in existing else None
		for _, ruleset in wanted
	]
	with ThreadPoolExecutor(max_workers=max(1, len(paths))) as pool:
		lives = list(pool.map(lambda path: github.ghJson('api', path) if path else None, paths))
	changes = []
	for (_, ruleset), summary, path, live in zip(wanted, summaries, paths, lives, strict=True):
		if path is None:
			changes.append(True)
			continue
		current = rulesetSummary(live)
		if current['name'] != ruleset['name']:
			raise ValueError(f'{path}: name không khớp danh sách ruleset')
		if type(live.get('id')) is not int or live['id'] != existing[ruleset['name']]:
			raise ValueError(f'{path}: id không khớp danh sách ruleset')
		changes.append(current != summary)
	return changes


# GraphQL đọc được ruleset cấp tổ chức ở gói Free; không có update_allows_fetch_and_merge (bỏ fragment
# UpdateParameters) và require_extra_approval_for_unattributed_changes — bỏ hai trường này khi so.
ORG_RULESETS_QUERY = """
query($org: String!, $endCursor: String) { organization(login: $org) {
rulesets(first: 100, after: $endCursor) { pageInfo { hasNextPage endCursor } nodes {
	name target enforcement
	conditions { refName { include exclude } repositoryName { include exclude protected } }
	bypassActors(first: 100) { pageInfo { hasNextPage } nodes {
		bypassMode organizationAdmin deployKey repositoryRoleDatabaseId
		actor { __typename ... on Team { databaseId } ... on App { databaseId } }
	} }
	rules(first: 100) { pageInfo { hasNextPage } nodes { type parameters { __typename
		... on PullRequestParameters {
			allowedMergeMethods dismissStaleReviewsOnPush dismissalRestriction { enabled allowedActors }
			requireCodeOwnerReview requireLastPushApproval requiredApprovingReviewCount
			requiredReviewThreadResolution requiredReviewers { minimumApprovals filePatterns reviewerId }
		}
		... on RequiredStatusChecksParameters {
			doNotEnforceOnCreate strictRequiredStatusChecksPolicy
			requiredStatusChecks { context integrationId }
		}
		... on CodeQualityParameters { severity }
		... on CodeScanningParameters {
			codeScanningTools { tool alertsThreshold securityAlertsThreshold }
		}
		... on FilePathRestrictionParameters { restrictedFilePaths }
		... on FileExtensionRestrictionParameters { restrictedFileExtensions }
		... on MaxFileSizeParameters { maxFileSize }
		... on MaxFilePathLengthParameters { maxFilePathLength }
	} } }
} } } }
"""

GRAPHQL_HIDDEN_PARAMETERS = (
	'update_allows_fetch_and_merge',
	'require_extra_approval_for_unattributed_changes',
)

GRAPHQL_ENUM_PARAMETERS = ('allowed_merge_methods', 'severity')


def snakeKeys(value):
	"""Đổi khóa camelCase của GraphQL sang snake_case của REST, bỏ __typename."""
	if isinstance(value, list):
		return [snakeKeys(item) for item in value]
	if not isinstance(value, dict):
		return value
	return {
		re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower(): snakeKeys(item)
		for key, item in value.items()
		if key != '__typename' and item is not None
	}


def graphqlNodes(connection, label, paginated=False):
	"""Không dùng collection thiếu nodes, thiếu trạng thái phân trang hoặc bị cắt để đối chiếu."""
	if not isinstance(connection, dict) or not isinstance(connection.get('nodes'), list):
		raise TypeError(f'ruleset: {label} thiếu danh sách nodes')
	pageInfo = connection.get('pageInfo')
	if not isinstance(pageInfo, dict) or type(pageInfo.get('hasNextPage')) is not bool:
		raise ValueError(f'ruleset: {label} thiếu pageInfo.hasNextPage hợp lệ')
	if pageInfo['hasNextPage'] and not paginated:
		raise ValueError(f'ruleset: {label} chưa được đọc đầy đủ')
	return connection['nodes']


def graphqlRuleset(node):
	"""Ruleset đọc qua GraphQL, đổi sang dạng REST của tệp ruleset."""
	if not isinstance(node, dict):
		raise TypeError('ruleset: node GraphQL phải là object')
	actorNodes = graphqlNodes(node.get('bypassActors'), 'bypassActors')
	ruleNodes = graphqlNodes(node.get('rules'), 'rules')
	for field in ('name', 'target', 'enforcement'):
		if not isinstance(node.get(field), str) or not node[field].strip():
			raise ValueError(f'ruleset: trường GraphQL {field} thiếu hoặc sai kiểu')
	if not isinstance(node.get('conditions'), dict):
		raise TypeError('ruleset: conditions GraphQL phải là object')
	actors = []
	for actor in actorNodes:
		if (
			not isinstance(actor, dict)
			or type(actor.get('organizationAdmin')) is not bool
			or type(actor.get('deployKey')) is not bool
			or not isinstance(actor.get('bypassMode'), str)
			or 'repositoryRoleDatabaseId' not in actor
			or (
				actor['repositoryRoleDatabaseId'] is not None
				and type(actor['repositoryRoleDatabaseId']) is not int
			)
			or 'actor' not in actor
			or (actor['actor'] is not None and not isinstance(actor['actor'], dict))
		):
			raise ValueError('ruleset: actor GraphQL thiếu trường hoặc sai kiểu')
		if actor['organizationAdmin']:
			actorId, actorType = 1, 'OrganizationAdmin'
		elif actor['deployKey']:
			actorId, actorType = None, 'DeployKey'
		elif actor['repositoryRoleDatabaseId']:
			actorId, actorType = actor['repositoryRoleDatabaseId'], 'RepositoryRole'
		else:
			who = actor['actor'] or {}
			actorId = who.get('databaseId')
			actorType = {'App': 'Integration'}.get(who.get('__typename'), who.get('__typename'))
		actors.append(
			{
				'actor_id': actorId,
				'actor_type': actorType,
				'bypass_mode': actor['bypassMode'].lower(),
			}
		)
	rules = []
	for rule in ruleNodes:
		if (
			not isinstance(rule, dict)
			or not isinstance(rule.get('type'), str)
			or 'parameters' not in rule
			or (rule['parameters'] is not None and not isinstance(rule['parameters'], dict))
		):
			raise ValueError('ruleset: quy tắc GraphQL thiếu trường hoặc sai kiểu')
		parameters = snakeKeys(rule['parameters'] or {})
		for key in GRAPHQL_ENUM_PARAMETERS:
			if key in parameters:
				value = parameters[key]
				if (
					key == 'allowed_merge_methods'
					and (
						not isinstance(value, list)
						or any(not isinstance(item, str) for item in value)
					)
				) or (key == 'severity' and not isinstance(value, str)):
					raise ValueError(f'ruleset: tham số GraphQL {key} sai kiểu')
				parameters[key] = (
					[item.lower() for item in value] if isinstance(value, list) else value.lower()
				)
		rules.append(
			{'type': rule['type'].lower(), **({'parameters': parameters} if parameters else {})}
		)
	result = {
		'name': node['name'],
		'target': node['target'].lower(),
		'enforcement': node['enforcement'].lower(),
		'conditions': snakeKeys(node['conditions']),
		'bypass_actors': actors,
		'rules': rules,
	}
	rulesetSummary(result)
	return result


def graphqlVisible(ruleset):
	"""Ruleset bỏ các trường GraphQL không trả, để so với graphqlRuleset()."""
	rules = []
	for rule in ruleset['rules']:
		parameters = {
			key: value
			for key, value in (rule.get('parameters') or {}).items()
			if key not in GRAPHQL_HIDDEN_PARAMETERS
		}
		rules.append({'type': rule['type'], **({'parameters': parameters} if parameters else {})})
	return dict(ruleset, rules=rules)


def orgRuleset():
	"""Protect Main cho mọi repository ở cấp tổ chức: như Protect Main của repository khác (chỉ giữ kiểm tra
	bắt buộc có ở mọi repository; giữ code_quality), nhắm ~ALL repository; thêm code scanning như web. Khác bản
	cấp repository (ADR 0006): áp dụng cả refs/heads/main ngoài nhánh mặc định và cho phép thêm Rebase."""
	ruleset = rulesetFor('app')
	ruleset['name'] = ORG_RULESET_NAME
	ruleset['conditions'] = {
		'ref_name': {'exclude': [], 'include': ['~DEFAULT_BRANCH', ORG_EXTRA_BRANCH]},
		'repository_name': dict(ORG_REPOSITORIES),
	}
	for rule in ruleset['rules']:
		if rule['type'] == 'pull_request':
			methods = rule['parameters']['allowed_merge_methods']
			rule['parameters']['allowed_merge_methods'] = [*methods, 'rebase']
	ruleset['rules'].append(dict(ORG_CODE_SCANNING_RULE))
	return orgActors(ruleset)


def orgActors(ruleset):
	"""Đổi actor loại User (chỉ hợp lệ ở cấp repository) sang actor cấp tổ chức như ruleset trên web."""
	ruleset['bypass_actors'] = [dict(actor) for actor in ORG_BYPASS_ACTORS]
	for rule in ruleset['rules']:
		if 'dismissal_restriction' in (rule.get('parameters') or {}):
			rule['parameters']['dismissal_restriction'] = {'enabled': False, 'allowed_actors': []}
	return ruleset


def orgTagRuleset():
	"""Protect Release Tags cho mọi repository ở cấp tổ chức: cùng quy tắc, nhắm ~ALL repository."""
	ruleset = json.loads(TAG_RULESET_FILE.read_text(encoding='utf-8'))
	ruleset['name'] = ORG_TAG_RULESET_NAME
	ruleset['conditions'] = dict(ruleset['conditions'], repository_name=dict(ORG_REPOSITORIES))
	# Ruleset trên web có quy tắc kiểm tra bắt buộc với danh sách rỗng (không chặn gì) — giữ để tệp khớp web.
	ruleset['rules'].append(
		{
			'type': 'required_status_checks',
			'parameters': {
				'strict_required_status_checks_policy': True,
				'do_not_enforce_on_create': False,
				'required_status_checks': [],
			},
		}
	)
	return orgActors(ruleset)


def orgPushRuleset():
	"""Protect Pushes cho mọi repository ở cấp tổ chức: quy tắc lấy từ tệp, danh sách bỏ qua và phạm vi
	repository như hai ruleset cấp tổ chức kia."""
	ruleset = json.loads(ORG_PUSH_RULESET_FILE.read_text(encoding='utf-8'))
	ruleset['name'] = ORG_PUSH_RULESET_NAME
	ruleset['conditions'] = {'repository_name': dict(ORG_REPOSITORIES)}
	return orgActors(ruleset)


def orgRulesets():
	"""Mọi ruleset cấp tổ chức, kèm tệp để import trên web."""
	return [
		(ORG_RULESET_FILE, orgRuleset()),
		(ORG_TAG_RULESET_FILE, orgTagRuleset()),
		(ORG_PUSH_RULESET_FILE, orgPushRuleset()),
	]


def rulesetsFor(repo):
	"""Mọi ruleset áp dụng cho repository, kèm tệp nguồn: nhánh chính rồi tag phát hành."""
	return [
		(RULESET_FILE, rulesetFor(repo)),
		(TAG_RULESET_FILE, json.loads(TAG_RULESET_FILE.read_text(encoding='utf-8'))),
	]


def syncRulesets(repos, apply):
	for repo in repos:
		print(f'== {github.ORG}/{repo}')
		if repo != '.github':
			base = urllib.parse.quote(github.defaultBranch(repo), safe='')
			absent = [
				workflow
				for workflow in files.REQUIRED_WORKFLOWS
				if not github.ghExists(f'repos/{github.ORG}/{repo}/contents/{workflow}?ref={base}')
			]
			if absent:
				print(
					f'   ⚠ thiếu {", ".join(absent)} — hợp nhất Pull Request của lệnh files trước'
				)
				continue
		endpoint = f'repos/{github.ORG}/{repo}/rulesets'
		# Chỉ ruleset của repository: mặc định GitHub trả cả ruleset cấp tổ chức áp dụng cho nó.
		existing = readRulesetIds(f'{endpoint}?includes_parents=false')
		wanted = rulesetsFor(repo)
		changes = readRulesetChanges(endpoint, existing, wanted)
		for (source, ruleset), changed in zip(wanted, changes, strict=True):
			name = ruleset['name']
			action = 'cập nhật' if name in existing else 'tạo'
			if not changed:
				print(f'   ✔ ruleset "{name}" đã đúng')
				continue
			if not apply:
				print(
					f'   (xem trước) {action} ruleset "{name}" từ {source.relative_to(github.ROOT)}'
				)
				continue
			body = json.dumps(ruleset, ensure_ascii=False)
			try:
				if name in existing:
					github.gh(
						'api',
						'-X',
						'PUT',
						f'repos/{github.ORG}/{repo}/rulesets/{existing[name]}',
						'--input',
						'-',
						stdin=body,
					)
				else:
					github.gh(
						'api',
						'-X',
						'POST',
						f'repos/{github.ORG}/{repo}/rulesets',
						'--input',
						'-',
						stdin=body,
					)
			except RuntimeError as exc:
				# Gói GitHub Free không hỗ trợ ruleset cho repository riêng tư.
				print(f'   ⚠ không {action} được ruleset "{name}": {exc}')
				continue
			print(f'   ✔ đã {action} ruleset "{name}"')
		names = sorted(ruleset['name'] for _, ruleset in wanted)
		others = sorted(set(existing) - set(names))
		if others:
			print(
				f'   ⚠ còn ruleset khác: {", ".join(others)} — xóa trên web để chỉ còn {", ".join(names)}'
			)


def compareOrgRulesets():
	"""So tệp ruleset cấp tổ chức với ruleset trên web (đọc qua GraphQL); sửa trên web bằng import."""
	how = 'Organization settings → Repository → Rulesets → New ruleset → Import a ruleset'
	try:
		data = github.ghJson(
			'api',
			'graphql',
			'--paginate',
			'--slurp',
			'-f',
			f'query={ORG_RULESETS_QUERY}',
			'-f',
			f'org={github.ORG}',
		)
		if not isinstance(data, list) or not data:
			raise ValueError('ruleset: GraphQL không trả danh sách trang')
		live = {}
		for index, page in enumerate(data):
			if not isinstance(page, dict) or page.get('errors'):
				raise ValueError('ruleset: trang GraphQL thiếu dữ liệu hoặc có errors')
			connection = page['data']['organization']['rulesets']
			nodes = graphqlNodes(connection, 'rulesets', paginated=index < len(data) - 1)
			if connection['pageInfo']['hasNextPage'] != (index < len(data) - 1):
				raise ValueError(
					'ruleset: trạng thái phân trang GraphQL không khớp các trang đã đọc'
				)
			for node in nodes:
				ruleset = graphqlRuleset(node)
				if ruleset['name'] in live:
					raise ValueError(f'ruleset: tên {ruleset["name"]} trùng trong GraphQL')
				live[ruleset['name']] = ruleset
	except (RuntimeError, KeyError, ValueError, TypeError) as exc:
		print(f'   ⚠ không đọc được qua GraphQL: {exc}')
		print(
			f'   Cấp quyền: gh auth refresh -h github.com -s admin:org — hoặc import tệp tại {how}.'
		)
		return
	for source, ruleset in orgRulesets():
		name, path = ruleset['name'], source.relative_to(github.ROOT)
		if name not in live:
			print(f'   ✘ chưa có ruleset "{name}" — import {path} tại {how}')
		elif rulesetSummary(live[name]) == rulesetSummary(graphqlVisible(ruleset)):
			print(f'   ✔ ruleset "{name}" đã đúng')
		else:
			print(f'   ✘ ruleset "{name}" khác {path} — sửa trên web hoặc xóa rồi import lại')


def syncOrgRulesets(apply):
	"""Ruleset cấp tổ chức; REST API bị chặn (gói Free, thiếu admin:org) thì so qua GraphQL."""
	print(f'== ruleset cấp tổ chức {github.ORG} (chỉ thực thi với gói GitHub Team trở lên)')
	try:
		existing = readRulesetIds(f'orgs/{github.ORG}/rulesets')
	except RuntimeError as exc:
		print(f'   ⚠ REST API ruleset cấp tổ chức: {exc}')
		compareOrgRulesets()
		return
	wanted = orgRulesets()
	changes = readRulesetChanges(f'orgs/{github.ORG}/rulesets', existing, wanted)
	for (source, ruleset), changed in zip(wanted, changes, strict=True):
		name = ruleset['name']
		action = 'cập nhật' if name in existing else 'tạo'
		if not changed:
			print(f'   ✔ ruleset "{name}" đã đúng')
			continue
		if not apply:
			print(f'   (xem trước) {action} ruleset "{name}" từ {source.relative_to(github.ROOT)}')
			continue
		body = json.dumps(ruleset, ensure_ascii=False)
		try:
			if name in existing:
				path = f'orgs/{github.ORG}/rulesets/{existing[name]}'
				github.gh('api', '-X', 'PUT', path, '--input', '-', stdin=body)
			else:
				github.gh(
					'api', '-X', 'POST', f'orgs/{github.ORG}/rulesets', '--input', '-', stdin=body
				)
		except RuntimeError as exc:
			print(f'   ⚠ không {action} được ruleset "{name}": {exc}')
			continue
		print(f'   ✔ đã {action} ruleset "{name}"')
