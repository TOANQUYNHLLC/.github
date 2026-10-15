"""Kiểm tra và sinh mẫu ruleset tại máy; không đọc hoặc ghi cài đặt GitHub.

Chạy: python3 scripts/rulesets.py (hoặc make ruleset-files).
"""

import copy
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRINT_WIDTH = 100

RULESET_FILE = ROOT / 'rulesets' / 'protect-main.json'

TAG_RULESET_FILE = ROOT / 'rulesets' / 'protect-release-tags.json'

PUSH_RULESET_FILE = ROOT / 'rulesets' / 'protect-pushes.json'

ORG_RULESET_FILE = ROOT / 'rulesets' / 'organization-protect-main.json'

ORG_RULESET_NAME = 'Organization Protect Main'

ORG_TAG_RULESET_FILE = ROOT / 'rulesets' / 'organization-protect-release-tags.json'

ORG_TAG_RULESET_NAME = 'Organization Protect Release Tags'

ORG_PUSH_RULESET_FILE = ROOT / 'rulesets' / 'organization-protect-pushes.json'

ORG_PUSH_RULESET_NAME = 'Organization Protect Pushes'

PULL_REQUEST_FIELDS = {
	'required_approving_review_count': int,
	'dismiss_stale_reviews_on_push': bool,
	'require_code_owner_review': bool,
	'require_last_push_approval': bool,
	'required_review_thread_resolution': bool,
	'require_extra_approval_for_unattributed_changes': bool,
	'required_reviewers': list,
	'dismissal_restriction': dict,
	'allowed_merge_methods': list,
}

UNORDERED_RULE_PARAMETERS = {
	'pull_request': ('allowed_merge_methods', 'required_reviewers'),
	'required_status_checks': ('required_status_checks',),
	'code_scanning': ('code_scanning_tools',),
	'file_path_restriction': ('restricted_file_paths',),
	'file_extension_restriction': ('restricted_file_extensions',),
}

ORG_BYPASS_ACTORS = [{'actor_id': 1, 'actor_type': 'OrganizationAdmin', 'bypass_mode': 'always'}]

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

ORG_EXTRA_BRANCH = 'refs/heads/main'


def templateJobs():
	"""Tên job trong các workflow kiểm tra tiêu đề Pull Request và tên branch dùng chung."""
	names = set()
	for workflow in ('pr-title.yml', 'branch-name.yml'):
		text = (ROOT / 'workflow-templates' / Path(workflow).name).read_text(encoding='utf-8')
		names.update(re.findall(r'^ {8}name: (.+)$', text, re.MULTILINE))
	return names


def rulesetFor(repo):
	"""Ruleset Protect Main cho repository: repository khác chỉ giữ kiểm tra bắt buộc có job tương ứng."""
	ruleset = json.loads(RULESET_FILE.read_text(encoding='utf-8'))
	if repo.casefold() != '.github':
		jobs = templateJobs()
		for rule in ruleset['rules']:
			if rule['type'] == 'required_status_checks':
				checks = rule['parameters']['required_status_checks']
				rule['parameters']['required_status_checks'] = [
					check for check in checks if check['context'] in jobs
				]
	return ruleset


def normalizedRule(rule):
	"""Biểu diễn quy tắc để so sánh; không coi thứ tự của danh sách tập hợp là thay đổi."""
	result = copy.deepcopy(rule)
	parameters = result.get('parameters', {})
	for key in UNORDERED_RULE_PARAMETERS.get(result['type'], ()):
		if isinstance(parameters.get(key), list):
			parameters[key] = sorted(
				parameters[key],
				key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False),
			)
	if result['type'] == 'pull_request':
		restriction = parameters.get('dismissal_restriction', {})
		if isinstance(restriction.get('allowed_actors'), list):
			restriction['allowed_actors'] = sorted(
				restriction['allowed_actors'],
				key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False),
			)
	return json.dumps(result, sort_keys=True, ensure_ascii=False)


def validateDismissalRestriction(restriction):
	"""Kiểm tra nội dung quyền hủy phê duyệt, không chỉ kiểu object bên ngoài."""
	if type(restriction.get('enabled')) is not bool:
		raise ValueError('ruleset: pull_request.dismissal_restriction.enabled phải là boolean')
	actors = restriction.get('allowed_actors', [])
	if not isinstance(actors, list):
		raise TypeError(
			'ruleset: pull_request.dismissal_restriction.allowed_actors phải là danh sách'
		)
	for actor in actors:
		if (
			not isinstance(actor, dict)
			or type(actor.get('id')) is not int
			or actor['id'] <= 0
			or actor.get('type')
			not in ('User', 'Team', 'IntegrationInstallation', 'RepositoryRole')
		):
			raise ValueError('ruleset: pull_request.dismissal_restriction có actor không hợp lệ')


def validateRequiredReviewers(reviewers):
	"""Kiểm tra từng team, mẫu đường dẫn và số phê duyệt theo hợp đồng REST."""
	for item in reviewers:
		if not isinstance(item, dict):
			raise TypeError('ruleset: pull_request.required_reviewers phải chứa các object')
		patterns = item.get('file_patterns')
		if not isinstance(patterns, list) or any(not isinstance(value, str) for value in patterns):
			raise ValueError(
				'ruleset: pull_request.required_reviewers.file_patterns phải là danh sách chuỗi'
			)
		count = item.get('minimum_approvals')
		if type(count) is not int or count < 0:
			raise ValueError(
				'ruleset: pull_request.required_reviewers.minimum_approvals phải là số nguyên không âm'
			)
		reviewer = item.get('reviewer')
		if (
			not isinstance(reviewer, dict)
			or reviewer.get('type') != 'Team'
			or type(reviewer.get('id')) is not int
			or reviewer['id'] <= 0
		):
			raise ValueError(
				'ruleset: pull_request.required_reviewers.reviewer phải là Team có ID nguyên dương'
			)


def validateStatusChecks(parameters):
	"""Kiểm tra cờ và từng status check theo cấu trúc REST trước khi áp dụng ruleset."""
	for key in ('strict_required_status_checks_policy', 'do_not_enforce_on_create'):
		if key == 'do_not_enforce_on_create' and key not in parameters:
			continue
		if type(parameters.get(key)) is not bool:
			raise ValueError(f'ruleset: required_status_checks.{key} phải là boolean')
	checks = parameters.get('required_status_checks')
	if not isinstance(checks, list):
		raise TypeError('ruleset: required_status_checks.required_status_checks phải là danh sách')
	for check in checks:
		if (
			not isinstance(check, dict)
			or not isinstance(check.get('context'), str)
			or not check['context'].strip()
			or (
				check.get('integration_id') is not None and type(check['integration_id']) is not int
			)
		):
			raise ValueError(
				'ruleset: required_status_checks có context hoặc integration_id không hợp lệ'
			)


def rulesetSummary(ruleset):
	"""Phần so sánh được của ruleset; bỏ metadata, chuẩn hóa thứ tự danh sách tập hợp, giữ nguyên đầu vào."""
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
		if rule['type'] == 'pull_request':
			parameters = rule.get('parameters', {})
			if set(parameters) - set(PULL_REQUEST_FIELDS):
				raise ValueError('ruleset: pull_request có tham số không được hỗ trợ')
			for key, value in parameters.items():
				if type(value) is not PULL_REQUEST_FIELDS[key]:
					raise ValueError(f'ruleset: pull_request.{key} sai kiểu')
			count = parameters.get('required_approving_review_count')
			if count is not None and count < 0:
				raise ValueError(
					'ruleset: pull_request.required_approving_review_count không được âm'
				)
			methods = parameters.get('allowed_merge_methods')
			if methods is not None and (
				not methods
				or any(method not in ('merge', 'squash', 'rebase') for method in methods)
				or len(methods) != len(set(methods))
			):
				raise ValueError('ruleset: pull_request.allowed_merge_methods không hợp lệ')
			if 'dismissal_restriction' in parameters:
				validateDismissalRestriction(parameters['dismissal_restriction'])
			if 'required_reviewers' in parameters:
				validateRequiredReviewers(parameters['required_reviewers'])
		elif rule['type'] == 'required_status_checks':
			validateStatusChecks(rule.get('parameters', {}))
	conditions = copy.deepcopy(ruleset['conditions'])
	for field in ('ref_name', 'repository_name'):
		if field in conditions:
			for key in ('include', 'exclude'):
				conditions[field][key] = sorted(conditions[field][key])
	return {
		'name': ruleset.get('name'),
		'target': ruleset.get('target'),
		'enforcement': ruleset.get('enforcement'),
		'conditions': conditions,
		'bypass_actors': sorted(actors, key=lambda actor: (actor[1], actor[0] or 0, actor[2])),
		'rules': sorted(normalizedRule(rule) for rule in ruleset['rules']),
	}


def orgRuleset():
	"""Protect Main cho mọi repository ở cấp tổ chức: như Protect Main của repository khác (chỉ giữ kiểm tra
	bắt buộc có trong các workflow mẫu; giữ code_quality), nhắm ~ALL repository; thêm code scanning. Khác bản
	cấp repository (ADR 00000007): áp dụng cả refs/heads/main ngoài nhánh mặc định;
	bỏ quy tắc deployment rỗng ở mẫu cấp tổ chức."""
	ruleset = rulesetFor('app')
	ruleset['name'] = ORG_RULESET_NAME
	ruleset['conditions'] = {
		'ref_name': {'exclude': [], 'include': ['~DEFAULT_BRANCH', ORG_EXTRA_BRANCH]},
		'repository_name': dict(ORG_REPOSITORIES),
	}
	ruleset['rules'] = [rule for rule in ruleset['rules'] if rule['type'] != 'required_deployments']
	ruleset['rules'].append(dict(ORG_CODE_SCANNING_RULE))
	return orgActors(ruleset)


def orgActors(ruleset):
	"""Đổi actor loại User (chỉ hợp lệ ở cấp repository) sang actor OrganizationAdmin cho mẫu cấp tổ chức."""
	ruleset['bypass_actors'] = [dict(actor) for actor in ORG_BYPASS_ACTORS]
	for rule in ruleset['rules']:
		if 'dismissal_restriction' in (rule.get('parameters') or {}):
			rule['parameters']['dismissal_restriction'] = {'enabled': False, 'allowed_actors': []}
	return ruleset


def orgTagRuleset():
	"""Protect Release Tags cho mọi repository: nhắm ~ALL, đặt do_not_enforce_on_create=False cho mẫu tổ chức."""
	ruleset = json.loads(TAG_RULESET_FILE.read_text(encoding='utf-8'))
	ruleset['name'] = ORG_TAG_RULESET_NAME
	ruleset['conditions'] = dict(ruleset['conditions'], repository_name=dict(ORG_REPOSITORIES))
	for rule in ruleset['rules']:
		if rule['type'] == 'required_status_checks':
			rule['parameters']['do_not_enforce_on_create'] = False
	return orgActors(ruleset)


def orgPushRuleset():
	"""Protect Pushes cho mọi repository ở cấp tổ chức: quy tắc lấy từ nguồn cấp repository, danh sách bỏ qua và phạm vi
	repository như hai ruleset cấp tổ chức kia."""
	ruleset = json.loads(PUSH_RULESET_FILE.read_text(encoding='utf-8'))
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
	"""Các mẫu ruleset nhánh và tag theo repository đích; mẫu push được chọn riêng."""
	return [
		(RULESET_FILE, rulesetFor(repo)),
		(TAG_RULESET_FILE, json.loads(TAG_RULESET_FILE.read_text(encoding='utf-8'))),
	]


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


def writeOrgRulesetFiles():
	"""Sinh các bản cấp tổ chức từ nguồn cấp repository, cùng bố cục JSON; chỉ ghi local."""
	for path, ruleset in orgRulesets():
		text = jsonText(ruleset)
		name = f'{path.parent.name}/{path.name}'
		if path.read_text(encoding='utf-8') == text:
			print(f'✔ {name} đã khớp bản cấp repository')
			continue
		path.write_text(text, encoding='utf-8')
		print(f'✎ đã ghi lại {name}')


def main():
	writeOrgRulesetFiles()
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
