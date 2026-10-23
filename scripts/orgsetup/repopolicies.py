"""Nhập bản chụp Repository policies từ HTML đã lưu; chỉ đối chiếu và khôi phục thủ công trên web."""

import copy
import json
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from orgsetup import github, localdata

ACTOR_TYPES = {
	'OrganizationAdmin',
	'DeployKey',
	'RepositoryMigration',
	'RepositoryRole',
	'Integration',
	'Team',
}
NULL_ACTORS = {'OrganizationAdmin', 'DeployKey', 'RepositoryMigration'}
RULE_TYPES = {
	'repository_visibility',
	'repository_create',
	'repository_delete',
	'repository_transfer',
	'repository_name',
}


class PolicyPageParser(HTMLParser):
	"""Chỉ đọc JSON của ứng dụng policy; bỏ CSRF, phiên, hồ sơ và các script khác của trang."""

	def __init__(self):
		super().__init__()
		self.active = False
		self.parts = []
		self.pages = []

	def handle_starttag(self, tag, attrs):
		if tag == 'script' and dict(attrs).get('data-target') == 'react-app.embeddedData':
			self.active = True
			self.parts = []

	def handle_data(self, data):
		if self.active:
			self.parts.append(data)

	def handle_endtag(self, tag):
		if tag == 'script' and self.active:
			self.pages.append(''.join(self.parts))
			self.active = False


def validatePolicies(items):
	"""Hợp đồng bản chụp web riêng, không phải payload REST của branch/tag/push rulesets."""
	if not isinstance(items, list):
		raise TypeError('Repository policies cần danh sách')
	ids, names = set(), set()
	for item in items:
		if (
			not isinstance(item, dict)
			or set(item)
			!= {
				'policy_id',
				'name',
				'target',
				'enforcement',
				'conditions',
				'bypass_actors',
				'rules',
			}
			or type(item['policy_id']) is not int
			or item['policy_id'] <= 0
			or not isinstance(item['name'], str)
			or not item['name'].strip()
			or item['target'] != 'repository'
			or item['enforcement'] not in ('active', 'disabled', 'evaluate')
		):
			raise ValueError('Repository policy thiếu danh tính hoặc có cấu trúc không được hỗ trợ')
		if item['policy_id'] in ids or item['name'] in names:
			raise ValueError('Repository policies trùng ID hoặc tên')
		ids.add(item['policy_id'])
		names.add(item['name'])
		conditions = item['conditions']
		if not isinstance(conditions, dict) or set(conditions) != {'repository_name'}:
			raise ValueError('Repository policy cần điều kiện repository_name đã đọc đủ')
		condition = conditions['repository_name']
		if (
			not isinstance(condition, dict)
			or not {'include', 'exclude'} <= set(condition) <= {'include', 'exclude', 'protected'}
			or ('protected' in condition and type(condition['protected']) is not bool)
			or any(
				not isinstance(condition[key], list)
				or any(not isinstance(value, str) for value in condition[key])
				for key in ('include', 'exclude')
			)
		):
			raise ValueError('Repository policy có điều kiện không hợp lệ')
		if not isinstance(item['bypass_actors'], list) or not isinstance(item['rules'], list):
			raise TypeError('Repository policy cần danh sách actor và rule')
		actors = set()
		for actor in item['bypass_actors']:
			if (
				not isinstance(actor, dict)
				or set(actor) != {'name', 'actor_id', 'actor_type', 'bypass_mode'}
				or not isinstance(actor['name'], str)
				or not actor['name'].strip()
				or actor['actor_type'] not in ACTOR_TYPES
				or actor['bypass_mode'] != 'always'
				or (actor['actor_type'] in NULL_ACTORS and actor['actor_id'] is not None)
				or (
					actor['actor_type'] not in NULL_ACTORS
					and (type(actor['actor_id']) is not int or actor['actor_id'] <= 0)
				)
			):
				raise ValueError('Repository policy có actor thiếu ID hoặc không được hỗ trợ')
			identity = (actor['actor_type'], actor['actor_id'])
			if identity in actors:
				raise ValueError('Repository policy có actor trùng')
			actors.add(identity)
		rules = set()
		for rule in item['rules']:
			if (
				not isinstance(rule, dict)
				or set(rule) != {'type', 'parameters'}
				or rule['type'] not in RULE_TYPES
				or rule['type'] in rules
				or not isinstance(rule['parameters'], dict)
			):
				raise ValueError('Repository policy có rule lạ hoặc trùng')
			rules.add(rule['type'])
			parameters = rule['parameters']
			if rule['type'] == 'repository_visibility':
				if set(parameters) != {'public', 'private', 'internal'} or any(
					type(value) is not bool for value in parameters.values()
				):
					raise ValueError('Repository policy có visibility sai kiểu')
			elif rule['type'] == 'repository_name':
				if (
					set(parameters) != {'negate', 'pattern_source'}
					or type(parameters['negate']) is not bool
					or not isinstance(parameters['pattern_source'], str)
					or not parameters['pattern_source']
				):
					raise ValueError('Repository policy cần tham chiếu regex ngoài Git')
			elif parameters:
				raise ValueError('Repository policy có tham số rule không được hỗ trợ')
	return items


def readPolicyPage(path):
	"""Kiểm tra đúng nguồn tổ chức, giữ dữ liệu policy và loại toàn bộ metadata của trang."""
	parser = PolicyPageParser()
	parser.feed(Path(path).read_text(encoding='utf-8'))
	if len(parser.pages) != 1:
		raise ValueError('HTML phải chứa đúng một bản dữ liệu ứng dụng policy')
	payload = json.loads(parser.pages[0])['payload']
	policy = payload['ruleset']
	if (
		policy['source']['type'] != 'Organization'
		or policy['source']['name'].casefold() != github.ORG.casefold()
		or policy['target'] != 'repository'
		or policy['missingConditionTargets']
	):
		raise ValueError('Trang policy không đúng tổ chức hoặc thiếu phạm vi repository')
	status = {'enabled': 'active', 'disabled': 'disabled', 'evaluate': 'evaluate'}
	if policy['enforcement'] not in status:
		raise ValueError('Trang policy có trạng thái chưa được hỗ trợ')
	conditions = {}
	for condition in policy['conditions']:
		if condition['target'] in conditions:
			raise ValueError('Trang policy có điều kiện trùng')
		conditions[condition['target']] = copy.deepcopy(condition['parameters'])
	actors = []
	for actor in policy['bypassActors']:
		if type(actor['bypassMode']) is not int or actor['bypassMode'] != 0:
			raise ValueError('Chế độ allow list của trang policy chưa được hỗ trợ')
		actors.append(
			{
				'name': actor['name'],
				'actor_id': actor['actorId'],
				'actor_type': actor['actorType'],
				'bypass_mode': 'always',
			}
		)
	rules = []
	for rule in policy['rules']:
		parameters = copy.deepcopy(rule['parameters'])
		if rule['ruleType'] == 'repository_name':
			if set(parameters) != {'negate', 'pattern'} or not isinstance(
				parameters['pattern'], str
			):
				raise ValueError('Trang policy thiếu định nghĩa regex')
			parameters['pattern_source'] = localdata.captureValue(
				f'orgs/{github.ORG}/repository-policies/{policy["id"]}/pattern',
				parameters.pop('pattern'),
			)
		rules.append({'type': rule['ruleType'], 'parameters': parameters})
	item = {
		'policy_id': policy['id'],
		'name': policy['name'],
		'target': policy['target'],
		'enforcement': status[policy['enforcement']],
		'conditions': conditions,
		'bypass_actors': actors,
		'rules': rules,
	}
	return validatePolicies([item])[0]


def importPolicyPages(paths):
	"""Lưu snapshot local và bản riêng để khôi phục trên web; không đánh dấu quản trị đã xác nhận."""
	from orgsetup import configuration

	config = configuration.readConfig()
	localdata.resetCapture()
	items = [readPolicyPage(path) for path in paths]
	validatePolicies(items)
	scope = config['organization']
	observed = scope.setdefault('observed', {})
	merged = {item['policy_id']: item for item in observed.get('repository_policies', [])}
	merged.update({item['policy_id']: item for item in items})
	observed['repository_policies'] = validatePolicies(
		sorted(merged.values(), key=lambda item: item['name'])
	)
	private = copy.deepcopy(observed['repository_policies'])
	knownValues = localdata.readValues()
	for policy in private:
		for rule in policy['rules']:
			if rule['type'] == 'repository_name':
				parameters = rule['parameters']
				reference = parameters.pop('pattern_source')
				parameters['pattern'] = (
					knownValues[reference]
					if reference in knownValues
					else localdata.capturedValue(reference)
				)
	reference = localdata.captureValue(
		f'orgs/{github.ORG}/repository-policies/configuration',
		json.dumps(private, ensure_ascii=False),
	)
	scope.setdefault('manual_settings', {})['repository_policies'] = {
		'status': 'pending',
		'configuration_source': reference,
	}
	configuration.validateConfig(config)
	path = github.ROOT / configuration.CONFIG_NAME
	temporary = None
	try:
		with tempfile.NamedTemporaryFile(
			mode='w', encoding='utf-8', dir=path.parent, delete=False
		) as file:
			temporary = Path(file.name)
			file.write(configuration.jsonText(config))
		localdata.saveCapturedValues(config)
		temporary.replace(path)
	finally:
		if temporary is not None:
			temporary.unlink(missing_ok=True)
	print(
		f'✔ Đã nhập {len(items)} Repository policies vào local; phần khôi phục trên web chờ quản trị xác nhận.'
	)
