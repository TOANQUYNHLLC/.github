"""Áp dụng cấu hình chung của tổ chức lên các repository bằng GitHub CLI (gh).

Chạy: python3 scripts/org-setup.py <lệnh> [--apply] [--repo TÊN] [--discussions]
Mặc định chỉ xem trước, không thay đổi gì; thêm --apply để áp dụng trên GitHub.
Yêu cầu: gh đã đăng nhập bằng tài khoản có quyền quản trị tổ chức.

Lệnh (nên chạy theo thứ tự):
	files: mở Pull Request thêm các tệp dùng chung còn thiếu — .editorconfig, .gitattributes,
		workflow kiểm tra tiêu đề Pull Request, tên branch và gắn nhãn (labeler), CODEOWNERS, dependabot.yml, release.yml
		và tệp định dạng theo ngôn ngữ repository dùng. Không ghi đè tệp đã có.
	settings: cho phép Merge, Squash và Rebase, tự xóa branch sau khi hợp nhất; bật secret scanning,
		push protection, Dependabot security updates, báo cáo lỗ hổng riêng tư, Release bất biến
		(immutable releases); --discussions bật thêm GitHub Discussions.
	rulesets: tạo hoặc cập nhật ruleset Protect Main (rulesets/protect-main.json) và Protect Release
		Tags (rulesets/protect-release-tags.json, ADR 0008); Protect Main của repository khác chỉ giữ
		kiểm tra bắt buộc có job tương ứng. Bỏ qua repository
		chưa có workflow kiểm tra bắt buộc — hợp nhất Pull Request của lệnh files trước.
	team: tạo team maintainers, thêm người quản trị và cấp quyền maintain mọi repository; đã đủ thì báo đã đúng.
	org-rulesets: tạo hoặc cập nhật ruleset cấp tổ chức Protect Main (Organization), Protect Release
		Tags (Organization) và Protect Pushes (Organization, ADR 0010) (rulesets/org-*.json) cho mọi
		repository; cần token có quyền admin:org
		(gh auth refresh -h github.com -s admin:org) và gói GitHub Team trở lên. Gói Free: REST API
		trả HTTP 403 nên chỉ so tệp với ruleset trên web (đọc qua GraphQL) — tạo, sửa bằng import trên web.
"""

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

ORG = 'TOANQUYNHLLC'
ROOT = Path(__file__).resolve().parent.parent
SYNC_BRANCH = 'chore/sync_org_files'
TEAM = 'maintainers'
MAINTAINERS = ('nguyentrongtoandl', 'trongtoandl81')
RULESET_FILE = ROOT / 'rulesets' / 'protect-main.json'
# Ruleset tag: chặn tạo, dời, xóa tag phát hành v* ngoài danh sách bỏ qua (ADR 0008).
TAG_RULESET_FILE = ROOT / 'rulesets' / 'protect-release-tags.json'
# Ruleset cấp tổ chức: tệp để import trên web, sinh từ bản cấp repository bằng org_rulesets(), khớp ruleset
# đang cài trên web (lệnh org-rulesets so qua GraphQL khi REST API trả HTTP 403 ở gói Free).
ORG_RULESET_FILE = ROOT / 'rulesets' / 'org-protect-main.json'
ORG_RULESET_NAME = 'Protect Main (Organization)'
ORG_TAG_RULESET_FILE = ROOT / 'rulesets' / 'org-protect-release-tags.json'
ORG_TAG_RULESET_NAME = 'Protect Release Tags (Organization)'
# Push ruleset chặn tệp bí mật, cơ sở dữ liệu, tệp lớn (ADR 0010): chỉ có ở cấp tổ chức nên tệp là nguồn —
# GitHub chỉ áp dụng cho repository riêng tư, internal.
ORG_PUSH_RULESET_FILE = ROOT / 'rulesets' / 'org-protect-pushes.json'
ORG_PUSH_RULESET_NAME = 'Protect Pushes (Organization)'
# Import cấp tổ chức không nhận actor loại User ("contains an invalid actor"): bỏ qua là chủ tổ chức (actor_id
# bị bỏ qua) — cùng hai người quản trị; ruleset trên web tắt giới hạn hủy phê duyệt.
ORG_BYPASS_ACTORS = [{'actor_id': 1, 'actor_type': 'OrganizationAdmin', 'bypass_mode': 'always'}]
ORG_REPOSITORIES = {'exclude': [], 'include': ['~ALL'], 'protected': False}
# Workflow mà lệnh files thêm vào repository; ruleset của repository khác chỉ bắt buộc job của chúng.
REQUIRED_WORKFLOWS = ('.github/workflows/pr-title.yml', '.github/workflows/branch-name.yml')
# Ecosystem Dependabot và tệp khai báo phụ thuộc ở thư mục gốc cho biết repository dùng nó.
ECOSYSTEM_MANIFESTS = {
	'npm': ('package.json',),
	'pip': ('requirements.txt', 'pyproject.toml', 'setup.py'),
	'gomod': ('go.mod',),
	'docker': ('Dockerfile',),
}
# Tệp cấu hình theo ngôn ngữ: tệp khai báo ở thư mục gốc → tệp thêm vào repository (nguồn trong repository này).
LANGUAGE_FILES = (
	(('package.json',), '.prettierrc.json', '.prettierrc.json'),
	(ECOSYSTEM_MANIFESTS['pip'], 'ruff.toml', 'ruff.toml'),
	(ECOSYSTEM_MANIFESTS['pip'], '.python-version', 'repository-templates/.python-version'),
	(('Cargo.toml',), 'rustfmt.toml', 'repository-templates/rustfmt.toml'),
	(('CMakeLists.txt', 'meson.build'), '.clang-format', 'repository-templates/.clang-format'),
	(('Dockerfile', 'compose.yaml'), '.dockerignore', 'repository-templates/.dockerignore'),
)
SECURITY_FEATURES = ('secret_scanning', 'secret_scanning_push_protection')
# Endpoint bật bằng PUT, đọc trạng thái qua trường enabled.
SECURITY_ENDPOINTS = {
	'Dependabot security updates': 'automated-security-fixes',
	'báo cáo lỗ hổng riêng tư': 'private-vulnerability-reporting',
	# Tag và tệp đính kèm của Release đã phát hành không đổi được; tổ chức đang bắt buộc cho mọi repository.
	'Release bất biến (immutable releases)': 'immutable-releases',
}
# Chỉ bật được cho repository công khai (báo cáo lỗ hổng riêng tư).
PUBLIC_ONLY_ENDPOINTS = ('private-vulnerability-reporting',)
MERGE_SETTINGS = {
	'allow_squash_merge': True,
	'allow_merge_commit': True,
	'allow_rebase_merge': True,
	'delete_branch_on_merge': True,
	'squash_merge_commit_title': 'PR_TITLE',
	'squash_merge_commit_message': 'PR_BODY',
}


def gh(*args, stdin=None):
	result = subprocess.run(['gh', *args], input=stdin, capture_output=True, text=True, check=False)
	if result.returncode != 0:
		raise RuntimeError(result.stderr.strip() or f'gh {" ".join(args)} thất bại')
	return result.stdout


def gh_json(*args):
	output = gh(*args)
	return json.loads(output) if output.strip() else None


def gh_exists(endpoint):
	try:
		gh('api', endpoint, '--silent')
		return True
	except RuntimeError:
		return False


def filter_dependabot(template, root_names):
	"""Giữ github-actions và các ecosystem có tệp khai báo trong root_names; bỏ phần còn lại."""
	used = {'github-actions'} | {
		ecosystem
		for ecosystem, manifests in ECOSYSTEM_MANIFESTS.items()
		if any(name in root_names for name in manifests)
	}
	_, _, updates = template.partition('updates:\n')
	blocks = []
	for block in updates.split('\n\n'):
		match = re.search(r'package-ecosystem: (\S+)', block)
		if match and match.group(1) in used:
			blocks.append(block.strip('\n'))
	header = (
		f'# Sinh từ {ORG}/.github (repository-templates/dependabot.yml) theo tệp khai báo phụ thuộc.\n'
		'version: 2\nupdates:\n'
	)
	return header + '\n\n'.join(blocks) + '\n'


def planned_files(root_names):
	"""Đường dẫn trong repository đích → nội dung tệp dùng chung."""

	def read(path):
		return (ROOT / path).read_text(encoding='utf-8')

	files = {
		'.editorconfig': read('.editorconfig'),
		'.gitattributes': read('.gitattributes'),
		'.github/workflows/pr-title.yml': read('workflow-templates/pr-title.yml'),
		'.github/workflows/branch-name.yml': read('workflow-templates/branch-name.yml'),
		'.github/workflows/labeler.yml': read('workflow-templates/labeler.yml'),
		'.github/labeler.yml': read('repository-templates/labeler.yml'),
		'.github/CODEOWNERS': read('repository-templates/CODEOWNERS'),
		'.github/dependabot.yml': filter_dependabot(
			read('repository-templates/dependabot.yml'), root_names
		),
		'.github/release.yml': read('repository-templates/release.yml'),
	}
	for manifests, target, source in LANGUAGE_FILES:
		if any(name in root_names for name in manifests):
			files[target] = read(source)
	return files


def template_jobs():
	"""Tên job trong các workflow mà lệnh files thêm vào repository khác."""
	names = set()
	for workflow in REQUIRED_WORKFLOWS:
		text = (ROOT / 'workflow-templates' / Path(workflow).name).read_text(encoding='utf-8')
		names.update(re.findall(r'^ {8}name: (.+)$', text, re.MULTILINE))
	return names


def ruleset_for(repo):
	"""Ruleset Protect Main cho repository: repository khác chỉ giữ kiểm tra bắt buộc có job tương ứng."""
	ruleset = json.loads(RULESET_FILE.read_text(encoding='utf-8'))
	if repo != '.github':
		jobs = template_jobs()
		for rule in ruleset['rules']:
			if rule['type'] == 'required_status_checks':
				checks = rule['parameters']['required_status_checks']
				rule['parameters']['required_status_checks'] = [
					check for check in checks if check['context'] in jobs
				]
	return ruleset


def ruleset_summary(ruleset):
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


def snake_keys(value):
	"""Đổi khóa camelCase của GraphQL sang snake_case của REST, bỏ __typename."""
	if isinstance(value, list):
		return [snake_keys(item) for item in value]
	if not isinstance(value, dict):
		return value
	return {
		re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower(): snake_keys(item)
		for key, item in value.items()
		if key != '__typename' and item is not None
	}


def graphql_ruleset(node):
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
		parameters = snake_keys(rule['parameters'] or {})
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
		'conditions': snake_keys(node['conditions']),
		'bypass_actors': actors,
		'rules': rules,
	}


def graphql_visible(ruleset):
	"""Ruleset bỏ các trường GraphQL không trả, để so với graphql_ruleset()."""
	rules = []
	for rule in ruleset['rules']:
		parameters = {
			key: value
			for key, value in (rule.get('parameters') or {}).items()
			if key not in GRAPHQL_HIDDEN_PARAMETERS
		}
		rules.append({'type': rule['type'], **({'parameters': parameters} if parameters else {})})
	return dict(ruleset, rules=rules)


def org_ruleset():
	"""Protect Main cho mọi repository ở cấp tổ chức: như Protect Main của repository khác (chỉ giữ kiểm tra
	bắt buộc có ở mọi repository; giữ code_quality), nhắm ~ALL repository."""
	ruleset = ruleset_for('app')
	ruleset['name'] = ORG_RULESET_NAME
	ruleset['conditions'] = {
		'ref_name': {'exclude': [], 'include': ['~DEFAULT_BRANCH']},
		'repository_name': dict(ORG_REPOSITORIES),
	}
	return org_actors(ruleset)


def org_actors(ruleset):
	"""Đổi actor loại User (chỉ hợp lệ ở cấp repository) sang actor cấp tổ chức như ruleset trên web."""
	ruleset['bypass_actors'] = [dict(actor) for actor in ORG_BYPASS_ACTORS]
	for rule in ruleset['rules']:
		if 'dismissal_restriction' in (rule.get('parameters') or {}):
			rule['parameters']['dismissal_restriction'] = {'enabled': False, 'allowed_actors': []}
	return ruleset


def org_tag_ruleset():
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
	return org_actors(ruleset)


def org_push_ruleset():
	"""Protect Pushes cho mọi repository ở cấp tổ chức: quy tắc lấy từ tệp, danh sách bỏ qua và phạm vi
	repository như hai ruleset cấp tổ chức kia."""
	ruleset = json.loads(ORG_PUSH_RULESET_FILE.read_text(encoding='utf-8'))
	ruleset['name'] = ORG_PUSH_RULESET_NAME
	ruleset['conditions'] = {'repository_name': dict(ORG_REPOSITORIES)}
	return org_actors(ruleset)


def org_rulesets():
	"""Mọi ruleset cấp tổ chức, kèm tệp để import trên web."""
	return [
		(ORG_RULESET_FILE, org_ruleset()),
		(ORG_TAG_RULESET_FILE, org_tag_ruleset()),
		(ORG_PUSH_RULESET_FILE, org_push_ruleset()),
	]


def rulesets_for(repo):
	"""Mọi ruleset áp dụng cho repository, kèm tệp nguồn: nhánh chính rồi tag phát hành."""
	return [
		(RULESET_FILE, ruleset_for(repo)),
		(TAG_RULESET_FILE, json.loads(TAG_RULESET_FILE.read_text(encoding='utf-8'))),
	]


def list_repos(only):
	if only:
		return [only]
	output = gh('repo', 'list', ORG, '--limit', '500', '--no-archived', '--json', 'name')
	return sorted(item['name'] for item in json.loads(output))


def default_branch(repo):
	return gh_json('api', f'repos/{ORG}/{repo}')['default_branch']


def cmd_files(repos, apply):
	for repo in repos:
		print(f'== {ORG}/{repo}')
		if repo == '.github':
			print('   – bỏ qua: repository nguồn của tệp dùng chung')
			continue
		base = default_branch(repo)
		try:
			root = {
				item['name'] for item in gh_json('api', f'repos/{ORG}/{repo}/contents?ref={base}')
			}
		except RuntimeError:
			print('   ⚠ repository trống — bỏ qua')
			continue
		files = planned_files(root)
		missing = {
			path: content
			for path, content in files.items()
			if not gh_exists(f'repos/{ORG}/{repo}/contents/{path}?ref={base}')
		}
		if not missing:
			print('   ✔ đã đủ tệp dùng chung')
			continue
		for path in missing:
			print(f'   {"+" if apply else "(xem trước) +"} {path}')
		if not apply:
			continue
		if gh_exists(f'repos/{ORG}/{repo}/git/ref/heads/{SYNC_BRANCH}'):
			print(f'   ⚠ branch {SYNC_BRANCH} đã tồn tại — kiểm tra Pull Request đang mở')
			continue
		sha = gh_json('api', f'repos/{ORG}/{repo}/git/ref/heads/{base}')['object']['sha']
		gh(
			'api',
			f'repos/{ORG}/{repo}/git/refs',
			'-f',
			f'ref=refs/heads/{SYNC_BRANCH}',
			'-f',
			f'sha={sha}',
		)
		for path, content in missing.items():
			gh(
				'api',
				'-X',
				'PUT',
				f'repos/{ORG}/{repo}/contents/{path}',
				'-f',
				f'message=chore: thêm {path}',
				'-f',
				f'content={base64.b64encode(content.encode("utf-8")).decode("ascii")}',
				'-f',
				f'branch={SYNC_BRANCH}',
			)
		body = (
			f'Thêm các tệp dùng chung của tổ chức từ {ORG}/.github:\n\n'
			+ ''.join(f'- `{path}`\n' for path in missing)
			+ '\nKiểm tra `CODEOWNERS` và `dependabot.yml` có đúng với repository trước khi hợp nhất.'
		)
		url = gh(
			'pr',
			'create',
			'--repo',
			f'{ORG}/{repo}',
			'--base',
			base,
			'--head',
			SYNC_BRANCH,
			'--title',
			'chore: thêm tệp dùng chung của tổ chức',
			'--body',
			body,
		).strip()
		print(f'   ✔ Pull Request: {url}')


def cmd_settings(repos, apply, discussions):
	wanted = dict(MERGE_SETTINGS, **({'has_discussions': True} if discussions else {}))
	for repo in repos:
		print(f'== {ORG}/{repo}')
		current = gh_json('api', f'repos/{ORG}/{repo}')
		changes = {key: value for key, value in wanted.items() if current.get(key) != value}
		if not changes:
			print('   ✔ cài đặt hợp nhất đã đúng')
			cmd_security(repo, current, apply)
			continue
		for key, value in changes.items():
			print(f'   {"" if apply else "(xem trước) "}{key}: {current.get(key)} → {value}')
		if apply:
			args = []
			for key, value in changes.items():
				if isinstance(value, bool):
					args += ['-F', f'{key}={"true" if value else "false"}']
				else:
					args += ['-f', f'{key}={value}']
			gh('api', '-X', 'PATCH', f'repos/{ORG}/{repo}', *args)
			print('   ✔ đã cập nhật')
		cmd_security(repo, current, apply)


def security_endpoints(private):
	"""Endpoint bảo mật áp dụng được cho repository; repository riêng tư bỏ qua endpoint chỉ dành cho công khai."""
	return {
		label: endpoint
		for label, endpoint in SECURITY_ENDPOINTS.items()
		if not (private and endpoint in PUBLIC_ONLY_ENDPOINTS)
	}


def cmd_security(repo, current, apply):
	"""Bật tính năng bảo mật còn tắt; GitHub từ chối (gói trả phí, repository riêng tư) thì cảnh báo, không dừng."""
	analysis = current.get('security_and_analysis') or {}
	off = [
		name for name in SECURITY_FEATURES if (analysis.get(name) or {}).get('status') != 'enabled'
	]
	private = bool(current.get('private'))
	for label in sorted(set(SECURITY_ENDPOINTS) - set(security_endpoints(private))):
		print(f'   – bỏ qua {label}: chỉ dành cho repository công khai')
	endpoints, unread = {}, False
	for label, endpoint in security_endpoints(private).items():
		try:
			enabled = (gh_json('api', f'repos/{ORG}/{repo}/{endpoint}') or {}).get('enabled')
		except RuntimeError as exc:
			print(f'   ⚠ không đọc được trạng thái {label}: {exc}')
			unread = True
			continue
		if not enabled:
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
			gh('api', '-X', 'PATCH', f'repos/{ORG}/{repo}', '--input', '-', stdin=body)
		except RuntimeError as exc:
			print(f'   ⚠ không bật được {", ".join(off)}: {exc}')
	for label, endpoint in endpoints.items():
		try:
			gh('api', '-X', 'PUT', f'repos/{ORG}/{repo}/{endpoint}')
			print(f'   ✔ đã bật {label}')
		except RuntimeError as exc:
			print(f'   ⚠ không bật được {label}: {exc}')


def cmd_rulesets(repos, apply):
	for repo in repos:
		print(f'== {ORG}/{repo}')
		if repo != '.github':
			base = default_branch(repo)
			absent = [
				workflow
				for workflow in REQUIRED_WORKFLOWS
				if not gh_exists(f'repos/{ORG}/{repo}/contents/{workflow}?ref={base}')
			]
			if absent:
				print(
					f'   ⚠ thiếu {", ".join(absent)} — hợp nhất Pull Request của lệnh files trước'
				)
				continue
		existing = {
			item['name']: item['id']
			for item in gh_json('api', f'repos/{ORG}/{repo}/rulesets') or []
		}
		wanted = rulesets_for(repo)
		for source, ruleset in wanted:
			name = ruleset['name']
			action = 'cập nhật' if name in existing else 'tạo'
			if name in existing:
				live = gh_json('api', f'repos/{ORG}/{repo}/rulesets/{existing[name]}')
				if ruleset_summary(live) == ruleset_summary(ruleset):
					print(f'   ✔ ruleset "{name}" đã đúng')
					continue
			if not apply:
				print(f'   (xem trước) {action} ruleset "{name}" từ {source.relative_to(ROOT)}')
				continue
			body = json.dumps(ruleset, ensure_ascii=False)
			try:
				if name in existing:
					gh(
						'api',
						'-X',
						'PUT',
						f'repos/{ORG}/{repo}/rulesets/{existing[name]}',
						'--input',
						'-',
						stdin=body,
					)
				else:
					gh(
						'api',
						'-X',
						'POST',
						f'repos/{ORG}/{repo}/rulesets',
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


def compare_org_rulesets():
	"""So tệp ruleset cấp tổ chức với ruleset trên web (đọc qua GraphQL); sửa trên web bằng import."""
	how = 'Organization settings → Repository → Rulesets → New ruleset → Import a ruleset'
	try:
		data = gh_json('api', 'graphql', '-f', f'query={ORG_RULESETS_QUERY}', '-f', f'org={ORG}')
	except RuntimeError as exc:
		print(f'   ⚠ không đọc được qua GraphQL: {exc}')
		print(
			f'   Cấp quyền: gh auth refresh -h github.com -s admin:org — hoặc import tệp tại {how}.'
		)
		return
	live = {
		node['name']: graphql_ruleset(node)
		for node in data['data']['organization']['rulesets']['nodes']
	}
	for source, ruleset in org_rulesets():
		name, path = ruleset['name'], source.relative_to(ROOT)
		if name not in live:
			print(f'   ✘ chưa có ruleset "{name}" — import {path} tại {how}')
		elif ruleset_summary(live[name]) == ruleset_summary(graphql_visible(ruleset)):
			print(f'   ✔ ruleset "{name}" đã đúng')
		else:
			print(f'   ✘ ruleset "{name}" khác {path} — sửa trên web hoặc xóa rồi import lại')


def cmd_org_rulesets(apply):
	"""Ruleset cấp tổ chức; REST API bị chặn (gói Free, thiếu admin:org) thì so qua GraphQL."""
	print(f'== ruleset cấp tổ chức {ORG} (chỉ thực thi với gói GitHub Team trở lên)')
	try:
		existing = {
			item['name']: item['id'] for item in gh_json('api', f'orgs/{ORG}/rulesets') or []
		}
	except RuntimeError as exc:
		print(f'   ⚠ REST API ruleset cấp tổ chức: {exc}')
		compare_org_rulesets()
		return
	for source, ruleset in org_rulesets():
		name = ruleset['name']
		action = 'cập nhật' if name in existing else 'tạo'
		if name in existing:
			live = gh_json('api', f'orgs/{ORG}/rulesets/{existing[name]}')
			if ruleset_summary(live) == ruleset_summary(ruleset):
				print(f'   ✔ ruleset "{name}" đã đúng')
				continue
		if not apply:
			print(f'   (xem trước) {action} ruleset "{name}" từ {source.relative_to(ROOT)}')
			continue
		body = json.dumps(ruleset, ensure_ascii=False)
		try:
			if name in existing:
				path = f'orgs/{ORG}/rulesets/{existing[name]}'
				gh('api', '-X', 'PUT', path, '--input', '-', stdin=body)
			else:
				gh('api', '-X', 'POST', f'orgs/{ORG}/rulesets', '--input', '-', stdin=body)
		except RuntimeError as exc:
			print(f'   ⚠ không {action} được ruleset "{name}": {exc}')
			continue
		print(f'   ✔ đã {action} ruleset "{name}"')


def team_role(user):
	"""Vai trò của người dùng trong team (maintainer, member), None nếu chưa là thành viên."""
	try:
		return (gh_json('api', f'orgs/{ORG}/teams/{TEAM}/memberships/{user}') or {}).get('role')
	except RuntimeError:
		return None


def team_permission(repo):
	"""Quyền của team trên repository (pull, triage, push, maintain, admin), None nếu chưa được cấp."""
	try:
		return (
			gh_json(
				'api',
				'-H',
				'Accept: application/vnd.github.v3.repository+json',
				f'orgs/{ORG}/teams/{TEAM}/repos/{ORG}/{repo}',
			)
			or {}
		).get('role_name')
	except RuntimeError:
		return None


def cmd_team(repos, apply):
	exists = gh_exists(f'orgs/{ORG}/teams/{TEAM}')
	print(f'== team {ORG}/{TEAM}: {"đã có" if exists else "chưa có"}')
	users = [user for user in MAINTAINERS if not exists or team_role(user) != 'maintainer']
	# Quyền admin đã bao gồm maintain — không hạ quyền.
	missing = [
		repo for repo in repos if not exists or team_permission(repo) not in ('maintain', 'admin')
	]
	if not users and not missing:
		print(f'   ✔ đủ người quản trị, team có quyền maintain {len(repos)} repository')
		return
	if not apply:
		if not exists:
			print(f'   (xem trước) tạo team {TEAM}')
		for user in users:
			print(f'   (xem trước) thêm {user} (maintainer)')
		for repo in missing:
			print(f'   (xem trước) cấp maintain {ORG}/{repo}')
		return
	if not exists:
		gh(
			'api',
			f'orgs/{ORG}/teams',
			'-f',
			f'name={TEAM}',
			'-f',
			'privacy=closed',
			'-f',
			'description=Người quản trị các repository — xem MAINTAINERS.md',
		)
	for user in users:
		gh(
			'api',
			'-X',
			'PUT',
			f'orgs/{ORG}/teams/{TEAM}/memberships/{user}',
			'-f',
			'role=maintainer',
		)
		print(f'   ✔ thêm {user} (maintainer)')
	for repo in missing:
		gh(
			'api',
			'-X',
			'PUT',
			f'orgs/{ORG}/teams/{TEAM}/repos/{ORG}/{repo}',
			'-f',
			'permission=maintain',
		)
		print(f'   ✔ maintain {ORG}/{repo}')
	print(
		f'   CODEOWNERS dùng @{ORG}/{TEAM}; đổi thành viên thì cập nhật MAINTAINERS.md và MAINTAINERS trong script này.'
	)


def main():
	parser = argparse.ArgumentParser(
		description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
	)
	parser.add_argument(
		'command', choices=('files', 'settings', 'rulesets', 'team', 'org-rulesets')
	)
	parser.add_argument('--apply', action='store_true', help='áp dụng thay đổi trên GitHub')
	parser.add_argument('--repo', help='chỉ xử lý một repository')
	parser.add_argument(
		'--discussions', action='store_true', help='settings: bật GitHub Discussions'
	)
	args = parser.parse_args()
	try:
		gh('auth', 'status')
	except (RuntimeError, FileNotFoundError):
		sys.exit('Cần GitHub CLI đã đăng nhập: https://cli.github.com rồi chạy gh auth login')
	# org-rulesets áp dụng cho cả tổ chức, không cần danh sách repository.
	repos = [] if args.command == 'org-rulesets' else list_repos(args.repo)
	if args.command == 'files':
		cmd_files(repos, args.apply)
	elif args.command == 'settings':
		cmd_settings(repos, args.apply, args.discussions)
	elif args.command == 'rulesets':
		cmd_rulesets(repos, args.apply)
	elif args.command == 'org-rulesets':
		cmd_org_rulesets(args.apply)
	else:
		cmd_team(repos, args.apply)
	if not args.apply:
		print('Chế độ xem trước — chạy lại với --apply để áp dụng.')


if __name__ == '__main__':
	main()
