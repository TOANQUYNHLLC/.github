"""Lệnh rulesets, org-rulesets: ruleset cấp repository và cấp tổ chức (so qua GraphQL ở gói Free)."""

import json
import re

from orgsetup import files, github

RULESET_FILE = github.ROOT / 'rulesets' / 'protect-main.json'

# Ruleset tag: chặn tạo, dời, xóa tag phát hành v* ngoài danh sách bỏ qua (ADR 0008).
TAG_RULESET_FILE = github.ROOT / 'rulesets' / 'protect-release-tags.json'

# Ruleset cấp tổ chức: tệp để import trên web, sinh từ bản cấp repository bằng orgRulesets(), khớp ruleset
# đang cài trên web (lệnh org-rulesets so qua GraphQL khi REST API trả HTTP 403 ở gói Free).
ORG_RULESET_FILE = github.ROOT / 'rulesets' / 'org-protect-main.json'

ORG_RULESET_NAME = 'Protect Main (Organization)'

ORG_TAG_RULESET_FILE = github.ROOT / 'rulesets' / 'org-protect-release-tags.json'

ORG_TAG_RULESET_NAME = 'Protect Release Tags (Organization)'

# Push ruleset chặn tệp bí mật, cơ sở dữ liệu, tệp lớn (ADR 0010): chỉ có ở cấp tổ chức nên tệp là nguồn —
# GitHub chỉ áp dụng cho repository riêng tư, internal.
ORG_PUSH_RULESET_FILE = github.ROOT / 'rulesets' / 'org-protect-pushes.json'

ORG_PUSH_RULESET_NAME = 'Protect Pushes (Organization)'

# Import cấp tổ chức không nhận actor loại User ("contains an invalid actor"): bỏ qua là chủ tổ chức (actor_id
# bị bỏ qua) — cùng hai người quản trị; ruleset trên web tắt giới hạn hủy phê duyệt.
ORG_BYPASS_ACTORS = [{'actor_id': 1, 'actor_type': 'OrganizationAdmin', 'bypass_mode': 'always'}]

# Ruleset cấp tổ chức trên web (2026-10-03) có thêm code scanning: kết quả CodeQL của Pull Request không được
# có cảnh báo mức errors hoặc cảnh báo bảo mật từ high trở lên. Bản cấp repository chưa có quy tắc này.
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
	return {
		'name': ruleset.get('name'),
		'target': ruleset.get('target'),
		'enforcement': ruleset.get('enforcement'),
		'conditions': ruleset.get('conditions'),
		'bypass_actors': sorted(
			(actor.get('actor_id'), actor.get('actor_type'), actor.get('bypass_mode'))
			for actor in ruleset.get('bypass_actors') or []
		),
		'rules': sorted(
			json.dumps(rule, sort_keys=True, ensure_ascii=False)
			for rule in ruleset.get('rules') or []
		),
	}


# GraphQL đọc được ruleset cấp tổ chức ở gói Free; không có update_allows_fetch_and_merge (bỏ fragment
# UpdateParameters) và require_extra_approval_for_unattributed_changes — bỏ hai trường này khi so.
ORG_RULESETS_QUERY = """
query($org: String!) { organization(login: $org) { rulesets(first: 50) { nodes {
	name target enforcement
	conditions { refName { include exclude } repositoryName { include exclude protected } }
	bypassActors(first: 50) { nodes {
		bypassMode organizationAdmin repositoryRoleDatabaseId
		actor { __typename ... on Team { databaseId } ... on App { databaseId } }
	} }
	rules(first: 50) { nodes { type parameters { __typename
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


def graphqlRuleset(node):
	"""Ruleset đọc qua GraphQL, đổi sang dạng REST của tệp ruleset."""
	actors = []
	for actor in node['bypassActors']['nodes']:
		if actor['organizationAdmin']:
			actor_id, actor_type = 1, 'OrganizationAdmin'
		elif actor['repositoryRoleDatabaseId']:
			actor_id, actor_type = actor['repositoryRoleDatabaseId'], 'RepositoryRole'
		else:
			who = actor['actor'] or {}
			actor_id = who.get('databaseId')
			actor_type = {'App': 'Integration'}.get(who.get('__typename'), who.get('__typename'))
		actors.append(
			{
				'actor_id': actor_id,
				'actor_type': actor_type,
				'bypass_mode': actor['bypassMode'].lower(),
			}
		)
	rules = []
	for rule in node['rules']['nodes']:
		parameters = snakeKeys(rule['parameters'] or {})
		for key in GRAPHQL_ENUM_PARAMETERS:
			if key in parameters:
				value = parameters[key]
				parameters[key] = (
					[item.lower() for item in value] if isinstance(value, list) else value.lower()
				)
		rules.append(
			{'type': rule['type'].lower(), **({'parameters': parameters} if parameters else {})}
		)
	return {
		'name': node['name'],
		'target': node['target'].lower(),
		'enforcement': node['enforcement'].lower(),
		'conditions': snakeKeys(node['conditions']),
		'bypass_actors': actors,
		'rules': rules,
	}


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
	bắt buộc có ở mọi repository; giữ code_quality), nhắm ~ALL repository; thêm code scanning như web."""
	ruleset = rulesetFor('app')
	ruleset['name'] = ORG_RULESET_NAME
	ruleset['conditions'] = {
		'ref_name': {'exclude': [], 'include': ['~DEFAULT_BRANCH']},
		'repository_name': dict(ORG_REPOSITORIES),
	}
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
			base = github.defaultBranch(repo)
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
		existing = {
			item['name']: item['id']
			for item in github.ghJson('api', f'repos/{github.ORG}/{repo}/rulesets') or []
		}
		wanted = rulesetsFor(repo)
		for source, ruleset in wanted:
			name = ruleset['name']
			action = 'cập nhật' if name in existing else 'tạo'
			if name in existing:
				live = github.ghJson('api', f'repos/{github.ORG}/{repo}/rulesets/{existing[name]}')
				if rulesetSummary(live) == rulesetSummary(ruleset):
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
			'api', 'graphql', '-f', f'query={ORG_RULESETS_QUERY}', '-f', f'org={github.ORG}'
		)
	except RuntimeError as exc:
		print(f'   ⚠ không đọc được qua GraphQL: {exc}')
		print(
			f'   Cấp quyền: gh auth refresh -h github.com -s admin:org — hoặc import tệp tại {how}.'
		)
		return
	live = {
		node['name']: graphqlRuleset(node)
		for node in data['data']['organization']['rulesets']['nodes']
	}
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
		existing = {
			item['name']: item['id']
			for item in github.ghJson('api', f'orgs/{github.ORG}/rulesets') or []
		}
	except RuntimeError as exc:
		print(f'   ⚠ REST API ruleset cấp tổ chức: {exc}')
		compareOrgRulesets()
		return
	for source, ruleset in orgRulesets():
		name = ruleset['name']
		action = 'cập nhật' if name in existing else 'tạo'
		if name in existing:
			live = github.ghJson('api', f'orgs/{github.ORG}/rulesets/{existing[name]}')
			if rulesetSummary(live) == rulesetSummary(ruleset):
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
