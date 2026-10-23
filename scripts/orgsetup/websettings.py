"""Bản khôi phục thủ công từ Settings: lọc HTML, lưu biểu mẫu ngoài Git, không gửi mutation."""

import copy
import json
import re
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from orgsetup import github, inventory, localdata, repopolicies, rulesets

EXCLUDED_GROUPS = ('secrets', 'deploy_keys', 'webhook_credentials', 'registry_credentials')
WEB_ONLY_PARAMETERS = {
	'pull_request': {
		'authorized_dismissal_actors_only': bool,
		'ignore_approvals_from_contributors': bool,
		'dismissal_restriction_source': str,
	},
	'code_quality': {'ai_findings_severity': str},
}
SENSITIVE_FIELD = re.compile(
	r'authenticity|csrf|timestamp|password|client_secret|private_key|secret_value|credential|'
	r'(?:^|\[)(?:token|access_token|api_key)(?:\]|$)|^required_field_|^_method$|^utf8$',
	re.IGNORECASE,
)


def pageScope(url, repositories):
	"""Chỉ nhận trang Settings của tổ chức và repository được quản lý; bỏ fragment."""
	parts = urlsplit(url)
	if parts.scheme != 'https' or parts.netloc != 'github.com' or parts.fragment:
		raise ValueError('Nguồn Settings không hợp lệ')
	orgPrefix = f'/organizations/{github.ORG}/settings'
	if parts.path == orgPrefix or parts.path.startswith(orgPrefix + '/'):
		return 'organization'
	for repo in repositories:
		prefix = f'/{github.ORG}/{repo}/settings'
		if parts.path == prefix or parts.path.startswith(prefix + '/'):
			return repo
	raise ValueError('Trang Settings ngoài phạm vi nguồn local')


def pageGroup(url, organization):
	path = urlsplit(url).path.split('/settings', 1)[1]
	if re.search(r'/(?:secrets|deploy_keys|hooks)(?:/|$)', path):
		return None
	groups = (
		('billing', ('/billing', '/licensing')),
		('authentication', ('/security', '/compliance')),
		('oauth_access', ('/oauth_application_policy', '/applications')),
		('github_apps', ('/installations', '/apps')),
		('personal_access_tokens', ('/personal-access-token',)),
		('codespaces', ('/codespaces',)),
		('copilot', ('/copilot/',)),
		(
			'verified_domains',
			(
				'/domains',
				'/pages',
			),
		),
		('members_and_collaborators', ('/member_privileges', '/org_role', '/roles', '/access')),
	)
	allowed = inventory.MANUAL_GROUPS if organization else inventory.REPO_MANUAL_GROUPS
	for group, prefixes in groups:
		if group in allowed and any(path.startswith(prefix) for prefix in prefixes):
			return group
	return 'settings_pages'


class SettingsPageParser(HTMLParser):
	"""Chỉ lấy nội dung panel Settings và control hiện hữu; bỏ script, hidden, mật khẩu và phiên."""

	def __init__(self, url, fallback=False):
		super().__init__()
		self.url = url
		self.fallback = fallback
		self.links = set()
		self.title = []
		self.text = []
		self.fields = []
		self.stack = []
		self.titleDepth = False
		self.contentDepth = None
		self.skipDepth = None
		self.current = None
		self.option = None
		self.form = ''

	def handle_starttag(self, tag, attrs):
		values = dict(attrs)
		void = tag in ('input', 'br', 'hr', 'img', 'meta', 'link', 'wbr', 'source')
		if not void:
			self.stack.append(tag)
		if tag == 'title':
			self.titleDepth = True
		if tag == 'a':
			href = urljoin(self.url, values.get('href', ''))
			if '/settings' in urlsplit(href).path and not urlsplit(href).fragment:
				self.links.add(href)
		if self.contentDepth is None and (
			'Layout-main' in values.get('class', '').split() or (self.fallback and tag == 'main')
		):
			self.contentDepth = len(self.stack)
		if self.contentDepth is None:
			return
		if self.skipDepth is None and tag in ('script', 'style', 'svg', 'nav'):
			self.skipDepth = len(self.stack)
		if self.skipDepth is not None:
			return
		if tag == 'form':
			self.form = urlsplit(urljoin(self.url, values.get('action', ''))).path
		isToggle = tag == 'button' and any(
			key in values for key in ('aria-checked', 'aria-pressed')
		)
		if tag in ('input', 'select', 'textarea') or isToggle:
			name = (
				values.get('name')
				or values.get('id')
				or values.get('aria-label')
				or f'control-{len(self.fields) + 1}'
			)
			kind = values.get('type', 'text') if tag == 'input' else tag
			if SENSITIVE_FIELD.search(name) or kind in (
				'hidden',
				'password',
				'submit',
				'file',
				'reset',
			):
				return
			field = {
				'name': name,
				'type': kind,
				'form': self.form,
				'disabled': 'disabled' in values or values.get('aria-disabled') == 'true',
				'value': values.get('value', ''),
			}
			field['locator'] = {
				key: values[key]
				for key in ('name', 'id', 'aria-label', 'data-testid')
				if key in values
			}
			for key in ('aria-checked', 'aria-pressed'):
				if key in values:
					field[key] = values[key]
			if kind in ('checkbox', 'radio'):
				field['checked'] = 'checked' in values
			if tag == 'select':
				field['options'] = []
			self.fields.append(field)
			if tag != 'input':
				self.current = field
		if tag == 'option' and self.current is not None and self.current['type'] == 'select':
			self.option = {
				'value': values.get('value', ''),
				'label': '',
				'selected': 'selected' in values,
			}
			self.current['options'].append(self.option)

	def handle_endtag(self, tag):
		if tag == 'title':
			self.titleDepth = False
		if tag == 'option':
			self.option = None
		if tag in ('select', 'textarea', 'button'):
			self.current = None
		if tag == 'form':
			self.form = ''
			if tag in self.stack:
				depth = len(self.stack) - self.stack[::-1].index(tag)
				# HTML trình duyệt lưu có thể đóng form trước các div con còn mở.
				# Giữ container để không bỏ phần panel và biểu mẫu phía sau.
				for attribute in ('skipDepth', 'contentDepth'):
					boundary = getattr(self, attribute)
					if boundary == depth:
						setattr(self, attribute, None)
					elif boundary is not None and boundary > depth:
						setattr(self, attribute, boundary - 1)
				del self.stack[depth - 1]
			return
		if tag not in self.stack:
			return
		depth = len(self.stack) - self.stack[::-1].index(tag)
		if self.skipDepth is not None and depth <= self.skipDepth:
			self.skipDepth = None
		if self.contentDepth is not None and depth <= self.contentDepth:
			self.contentDepth = None
		del self.stack[depth - 1 :]

	def handle_data(self, data):
		if self.titleDepth:
			self.title.append(data)
		if self.contentDepth is None or self.skipDepth is not None:
			return
		clean = ' '.join(data.split())
		if clean:
			self.text.append(clean)
		if self.current is not None:
			if self.current['type'] == 'textarea':
				self.current['value'] += data
			elif self.option is not None:
				self.option['label'] += data


def readSettingsPage(url, path, repositories):
	"""Không suy đoán cờ ẩn; panel rỗng được giữ là chưa đọc đủ, không thành cấu hình trống."""
	url = urlsplit(url).geturl()
	scope = pageScope(url, repositories)
	if pageGroup(url, scope == 'organization') is None:
		raise ValueError('Trang credentials bị loại khỏi phạm vi bản chụp')
	if Path(path).resolve().is_relative_to(github.ROOT.resolve()):
		raise ValueError('HTML chứa dữ liệu phiên phải nằm ngoài repository')
	parser = SettingsPageParser(url)
	html = Path(path).read_text(encoding='utf-8')
	parser.feed(html)
	if not parser.fields and not parser.text:
		parser = SettingsPageParser(url, fallback=True)
		parser.feed(html)
	page = {
		'url': url,
		'title': ''.join(parser.title).strip(),
		'fields': parser.fields,
		'visible_text': parser.text,
		'limitations': [
			'Cần đối chiếu thủ công; HTML không chứng minh đã đọc mọi trạng thái động hoặc phần bị ẩn.',
			'Không chứa giá trị secrets, khóa riêng hoặc thông tin xác thực.',
		],
	}
	if not page['title'] or 'sign in' in page['title'].lower():
		raise ValueError('Trang chưa đăng nhập hoặc không có danh tính')
	if not page['fields'] and not page['visible_text']:
		page['limitations'].append('Chưa đọc được panel Settings của trang này.')
	links = []
	for link in sorted(parser.links):
		try:
			if pageScope(link, repositories) == scope:
				links.append(link)
		except ValueError:
			continue
	return scope, page, links


def validateWebRulesets(items):
	"""Snapshot web giữ actor không có hợp đồng REST; không được dùng làm payload API."""
	if not isinstance(items, list):
		raise TypeError('Web rulesets cần danh sách')
	identities = set()
	for item in items:
		if (
			not isinstance(item, dict)
			or set(item)
			!= {
				'ruleset_id',
				'name',
				'target',
				'enforcement',
				'conditions',
				'bypass_actors',
				'rules',
			}
			or type(item['ruleset_id']) is not int
			or item['ruleset_id'] <= 0
		):
			raise ValueError('Web ruleset thiếu danh tính hoặc chứa metadata')
		if item['ruleset_id'] in identities:
			raise ValueError('Web rulesets trùng ID')
		identities.add(item['ruleset_id'])
		candidate = copy.deepcopy(item)
		del candidate['ruleset_id']
		actors = []
		seen = set()
		for actor in item['bypass_actors']:
			if (
				set(actor) != {'name', 'actor_id', 'actor_type', 'bypass_mode'}
				or not isinstance(actor['name'], str)
				or not actor['name'].strip()
			):
				raise ValueError('Web ruleset có actor thiếu thông tin')
			identity = (actor['actor_type'], actor['actor_id'])
			if identity in seen:
				raise ValueError('Web ruleset có actor trùng')
			seen.add(identity)
			if actor['actor_type'] == 'RepositoryMigration':
				if actor['actor_id'] is not None or actor['bypass_mode'] not in (
					'always',
					'exempt',
				):
					raise ValueError('Web ruleset có Repository migrations sai hợp đồng')
			else:
				actors.append({key: value for key, value in actor.items() if key != 'name'})
		candidate['bypass_actors'] = actors
		for rule in candidate['rules']:
			for key, kind in WEB_ONLY_PARAMETERS.get(rule['type'], {}).items():
				parameters = rule.get('parameters', {})
				if key in parameters:
					if type(parameters[key]) is not kind:
						raise ValueError('Web ruleset có tham số riêng sai kiểu')
					if key == 'dismissal_restriction_source' and not re.fullmatch(
						rf'(?:orgs/{re.escape(github.ORG)}|repos/{re.escape(github.ORG)}/[A-Za-z0-9_.-]+)/web-rulesets/{item["ruleset_id"]}/dismissal-restriction#[a-f0-9]{{32}}',
						parameters[key],
					):
						raise ValueError(
							'Web ruleset cần tham chiếu dismissal restriction ngoài Git'
						)
					# Chỉ bỏ khỏi bản dùng để kiểm tra hợp đồng REST; snapshot giữ nguyên giá trị web.
					del parameters[key]
		rulesets.rulesetSummary(candidate)
	return items


def readWebRuleset(path, repository=None):
	parser = repopolicies.PolicyPageParser()
	parser.feed(Path(path).read_text(encoding='utf-8'))
	if len(parser.pages) != 1:
		raise ValueError('Trang ruleset thiếu dữ liệu ứng dụng')
	policy = json.loads(parser.pages[0])['payload']['ruleset']
	sourceType = 'Organization' if repository is None else 'Repository'
	sourceName = github.ORG if repository is None else f'{github.ORG}/{repository}'
	sourceMatches = policy['source']['name'].casefold() == sourceName.casefold()
	if repository is not None and policy['source']['name'].casefold() == repository.casefold():
		# Trang repository dùng tên ngắn; URL nguồn xác nhận cả tổ chức và repository.
		sourceUrl = urlsplit(policy['source'].get('url', ''))
		sourceMatches = (
			sourceUrl.scheme in ('http', 'https')
			and sourceUrl.netloc == 'github.com'
			and sourceUrl.path.casefold() == f'/{github.ORG}/{repository}/settings/rules'.casefold()
			and not sourceUrl.query
			and not sourceUrl.fragment
		)
	if (
		policy['source']['type'] != sourceType
		or not sourceMatches
		or policy['missingConditionTargets']
	):
		raise ValueError('Web ruleset không đúng nguồn hoặc thiếu phạm vi')
	modes = {0: 'always', 1: 'pull_request', 2: 'exempt'}
	if any(
		type(actor['bypassMode']) is not int or actor['bypassMode'] not in modes
		for actor in policy['bypassActors']
	):
		raise ValueError('Web ruleset có chế độ bỏ qua không được hỗ trợ')
	if len({entry['target'] for entry in policy['conditions']}) != len(policy['conditions']):
		raise ValueError('Web ruleset có điều kiện trùng')
	webRules = []
	for rule in policy['rules']:
		parameters = copy.deepcopy(rule['parameters'] or {})
		if rule['ruleType'] == 'pull_request' and 'dismissal_restriction' in parameters:
			restriction = parameters['dismissal_restriction']
			if (
				not isinstance(restriction, dict)
				or set(restriction) != {'enabled', 'allowed_actors'}
				or type(restriction['enabled']) is not bool
				or not isinstance(restriction['allowed_actors'], list)
			):
				raise ValueError('Web dismissal restriction thiếu cấu hình')
			actors = restriction['allowed_actors']
			if actors and all(isinstance(actor, str) and actor for actor in actors):
				# Web dùng định danh chuỗi, không phải actor REST; giữ ngoài Git để không lộ danh tính.
				base = (
					f'orgs/{github.ORG}'
					if repository is None
					else f'repos/{github.ORG}/{repository}'
				)
				parameters['dismissal_restriction_source'] = localdata.captureValue(
					f'{base}/web-rulesets/{policy["id"]}/dismissal-restriction',
					json.dumps(parameters.pop('dismissal_restriction'), ensure_ascii=False),
				)
		webRules.append(
			{'type': rule['ruleType'], **({'parameters': parameters} if parameters else {})}
		)
	item = {
		'ruleset_id': policy['id'],
		'name': policy['name'],
		'target': policy['target'],
		'enforcement': {'enabled': 'active', 'disabled': 'disabled', 'evaluate': 'evaluate'}[
			policy['enforcement']
		],
		'conditions': {
			entry['target']: copy.deepcopy(entry['parameters']) for entry in policy['conditions']
		},
		'bypass_actors': [
			{
				'name': f'User {actor["actorId"]}'
				if actor['actorType'] == 'User'
				else actor['name'],
				'actor_id': actor['actorId'],
				'actor_type': actor['actorType'],
				'bypass_mode': modes[actor['bypassMode']],
			}
			for actor in policy['bypassActors']
		],
		'rules': webRules,
	}
	return validateWebRulesets([item])[0]


def saveConfig(config):
	from orgsetup import configuration

	configuration.validateConfig(config)
	path = github.ROOT / configuration.CONFIG_NAME
	temporary = None
	try:
		with tempfile.NamedTemporaryFile(
			mode='w', encoding='utf-8', dir=path.parent, delete=False
		) as output:
			temporary = Path(output.name)
			output.write(configuration.jsonText(config))
		localdata.saveCapturedValues(config)
		temporary.replace(path)
	finally:
		if temporary is not None:
			temporary.unlink(missing_ok=True)


def importSettingsPages(entries):
	"""Nhập nguyên tử một batch đã đọc; giữ bản cũ và trạng thái chưa xác nhận cho phần thủ công."""
	from orgsetup import configuration

	config = configuration.readConfig()
	localdata.resetCapture()
	parsed = [
		readSettingsPage(entry['url'], entry['path'], config['repositories']) for entry in entries
	]
	webRulesets = {}
	for entry in entries:
		if re.search(r'/settings/rules/\d+$', urlsplit(entry['url']).path):
			owner = pageScope(entry['url'], config['repositories'])
			webRulesets.setdefault(owner, []).append(
				readWebRuleset(entry['path'], None if owner == 'organization' else owner)
			)
	for name in {scope for scope, _, _ in parsed}:
		scope = config['organization'] if name == 'organization' else config['repositories'][name]
		base = f'orgs/{github.ORG}' if name == 'organization' else f'repos/{github.ORG}/{name}'
		manual = scope.setdefault('manual_settings', {})
		groups = {'settings_pages'} | {
			pageGroup(page['url'], name == 'organization')
			for owner, page, _ in parsed
			if owner == name
		}
		for group in sorted(groups - {None}):
			old = manual.get(group, {})
			stored = {'pages': [], 'excluded_groups': list(EXCLUDED_GROUPS)}
			if old.get('configuration_source'):
				previous = json.loads(localdata.privateValue(old['configuration_source']))
				if not isinstance(previous, dict) or not isinstance(previous.get('pages'), list):
					raise ValueError('Bản thủ công cũ cần đối chiếu trước khi thay cấu trúc')
				stored = previous
			pages = {}
			for previousPage in stored['pages']:
				page = copy.deepcopy(previousPage)
				page['url'] = urlsplit(page['url']).geturl()
				# Alias có fragment rỗng cùng trang; ưu tiên bản đã dùng URL chuẩn.
				if page['url'] not in pages or previousPage['url'] == page['url']:
					pages[page['url']] = page
			pages.update(
				{
					page['url']: page
					for owner, page, _ in parsed
					if owner == name
					and (
						group == 'settings_pages'
						or pageGroup(page['url'], name == 'organization') == group
					)
				}
			)
			stored['pages'] = [pages[url] for url in sorted(pages)]
			stored['excluded_groups'] = list(EXCLUDED_GROUPS)
			reference = localdata.captureValue(
				f'{base}/manual/{group}', json.dumps(stored, ensure_ascii=False)
			)
			manual[group] = {'status': 'pending', 'configuration_source': reference}
	for owner, items in webRulesets.items():
		scope = config['organization'] if owner == 'organization' else config['repositories'][owner]
		observed = scope.setdefault('observed', {})
		merged = {item['ruleset_id']: item for item in observed.get('web_rulesets', [])}
		merged.update({item['ruleset_id']: item for item in items})
		observed['web_rulesets'] = validateWebRulesets(
			sorted(merged.values(), key=lambda item: item['name'])
		)
		observed.pop('rulesets', None)
	saveConfig(config)
	print(f'✔ Đã lưu {len(parsed)} trang Settings; bản thủ công ngoài Git chờ đối chiếu.')
	return {link for _, _, links in parsed for link in links}


def importMemberships():
	"""Đọc danh tính và vai trò để khôi phục thủ công; không lưu hồ sơ API hoặc tự cấp quyền."""
	from orgsetup import configuration

	config = configuration.readConfig()
	collected = {}
	for name in ('organization', *config['repositories']):
		base = f'orgs/{github.ORG}' if name == 'organization' else f'repos/{github.ORG}/{name}'
		accounts = []
		if name == 'organization':
			for role in ('admin', 'member'):
				for item in github.ghList(f'{base}/members?role={role}'):
					if not isinstance(item.get('login'), str) or not item['login']:
						raise ValueError('Membership thiếu danh tính')
					accounts.append({'login': item['login'], 'role': role})
			outside = github.ghList(f'{base}/outside_collaborators')
			invitations = github.ghList(f'{base}/invitations')
		else:
			for item in github.ghList(f'{base}/collaborators?affiliation=direct'):
				if any(
					not isinstance(item.get(key), str) or not item[key]
					for key in ('login', 'role_name')
				):
					raise ValueError('Collaborator thiếu danh tính hoặc vai trò')
				accounts.append({'login': item['login'], 'role': item['role_name']})
			outside = []
			invitations = github.ghList(f'{base}/invitations')
		collected[name] = {
			'accounts': sorted(accounts, key=lambda item: item['login']),
			'outside_collaborators': [item['login'] for item in outside],
			'invitations': [
				{key: item.get(key) for key in ('login', 'email', 'role')}
				if name == 'organization'
				else {
					'login': (item.get('invitee') or {}).get('login'),
					'permissions': item.get('permissions'),
				}
				for item in invitations
			],
			'limitations': [
				'Quyền kế thừa qua team và tổ chức đối chiếu với nguồn teams; lời mời cần được chấp nhận.'
			],
		}
	localdata.resetCapture()
	for name, membership in collected.items():
		scope = config['organization'] if name == 'organization' else config['repositories'][name]
		base = f'orgs/{github.ORG}' if name == 'organization' else f'repos/{github.ORG}/{name}'
		manual = scope.setdefault('manual_settings', {})
		previous = manual.get('members_and_collaborators', {}).get('configuration_source')
		stored = json.loads(localdata.privateValue(previous)) if previous else {'pages': []}
		stored['membership'] = membership
		stored['excluded_groups'] = list(EXCLUDED_GROUPS)
		reference = localdata.captureValue(
			f'{base}/manual/members_and_collaborators', json.dumps(stored, ensure_ascii=False)
		)
		manual['members_and_collaborators'] = {
			'status': 'pending',
			'configuration_source': reference,
		}
	saveConfig(config)
	print(
		'✔ Đã lưu danh tính, vai trò trực tiếp và lời mời ngoài Git; không thay đổi quyền GitHub.'
	)
