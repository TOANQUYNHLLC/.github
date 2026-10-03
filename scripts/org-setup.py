"""Áp dụng cấu hình chung của tổ chức lên các repository bằng GitHub CLI (gh).

Chạy: python3 scripts/org-setup.py <lệnh> [--apply] [--repo TÊN] [--discussions]
Mặc định chỉ xem trước, không thay đổi gì; thêm --apply để áp dụng trên GitHub.
Yêu cầu: gh đã đăng nhập bằng tài khoản có quyền quản trị tổ chức.

Lệnh (nên chạy theo thứ tự):
	files: mở Pull Request thêm các tệp dùng chung còn thiếu — .editorconfig, .gitattributes,
		workflow kiểm tra tiêu đề Pull Request, tên branch và gắn nhãn (labeler), CODEOWNERS, dependabot.yml, release.yml
		và tệp định dạng theo ngôn ngữ repository dùng. Không ghi đè tệp đã có.
	settings: cài đặt repository (REPOSITORY_SETTINGS: Merge và Squash, tắt Rebase — ADR 0011, auto-merge,
		Update branch, sign-off khi commit trên web, tắt Wiki và Projects; phần riêng trong
		REPOSITORY_OVERRIDES, topics của .github lấy từ CITATION.cff); bật Dependabot alerts, secret
		scanning, push protection, Dependabot security updates, báo cáo lỗ hổng riêng tư, Release bất
		biến (immutable releases); quyền GitHub Actions (giữ nguyên trạng thái bật/tắt); so GitHub
		Pages; --discussions bật thêm GitHub Discussions.
	rulesets: tạo hoặc cập nhật ruleset Protect Main (rulesets/protect-main.json) và Protect Release
		Tags (rulesets/protect-release-tags.json, ADR 0008); Protect Main của repository khác chỉ giữ
		kiểm tra bắt buộc có job tương ứng. Bỏ qua repository
		chưa có workflow kiểm tra bắt buộc — hợp nhất Pull Request của lệnh files trước.
	team: tạo các team trong TEAMS, thêm người quản trị và cấp quyền của từng team trên mọi repository (không
		hạ quyền đã cao hơn); đã đủ thì báo đã đúng.
	org-settings: cài đặt tổ chức (ORG_SETTINGS) và quyền GitHub Actions cấp tổ chức; mục chỉ đổi được
		trên web (ORG_WEB_ONLY_SETTINGS) thì chỉ so và báo.
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
MAINTAINERS = ('nguyentrongtoandl', 'trongtoandl81')
# Team ghi trong CODEOWNERS.
TEAM = 'maintainers'
# Team của tổ chức (khớp web, kiểm tra 2026-10-03): slug → (tên, quyền trên mọi repository, hiển thị, mô tả
# khi tạo). Mọi team gồm hai người quản trị với vai trò maintainer.
TEAMS = {
	'admins': (
		'Admins',
		'admin',
		'secret',
		'Quản trị Organization, repository, bảo mật và phân quyền.',
	),
	TEAM: (
		'Maintainers',
		'maintain',
		'closed',
		'Người quản trị các repository — xem MAINTAINERS.md',
	),
	'developers': ('Developers', 'push', 'closed', 'Phát triển, review và duy trì mã nguồn.'),
	'qa': ('QA', 'triage', 'closed', 'Quản lý issue, kiểm thử, xác nhận lỗi.'),
	'design': ('Design', 'triage', 'closed', 'Thiết kế UI/UX, góp ý sản phẩm.'),
	'marketing': ('Marketing', 'pull', 'closed', 'Website, bài viết, hình ảnh truyền thông.'),
}
# Thứ tự quyền để không hạ quyền đã cao hơn; khi đọc GitHub trả role_name (read, write), khi ghi nhận pull, push.
PERMISSION_RANK = {
	'pull': 0,
	'read': 0,
	'triage': 1,
	'push': 2,
	'write': 2,
	'maintain': 3,
	'admin': 4,
}
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
	# Rebase and merge tạo lại commit không có chữ ký (ADR 0011).
	'allow_rebase_merge': False,
	'allow_auto_merge': True,
	'allow_update_branch': True,
	'delete_branch_on_merge': True,
	'squash_merge_commit_title': 'PR_TITLE',
	'squash_merge_commit_message': 'PR_BODY',
	'merge_commit_title': 'MERGE_MESSAGE',
	'merge_commit_message': 'PR_TITLE',
}
# Cài đặt mọi repository (khớp .github trên web, kiểm tra 2026-10-03; giữ allow_rebase_merge của ADR 0011).
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
# GitHub Pages chỉ so, sửa trên web: .github dùng tên miền toanquynh.com dù website thật ở hosting khác (cố ý).
PAGES = {
	'.github': {
		'cname': 'toanquynh.com',
		'build_type': 'workflow',
		'source': {'branch': 'main', 'path': '/'},
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
# Cài đặt tổ chức đổi được qua API (khớp web, kiểm tra 2026-10-03).
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


def citation_keywords():
	"""Từ khóa trong CITATION.cff — topics của repository .github."""
	text = (ROOT / 'CITATION.cff').read_text(encoding='utf-8')
	block = re.search(r'^keywords:\n((?:[ \t]+- .+\n)+)', text, re.MULTILINE)
	return re.findall(r'- (.+)', block.group(1)) if block else []


def repository_settings(repo, discussions=False):
	"""Cài đặt mong muốn của repository: chung cho mọi repository, cộng phần riêng của nó."""
	wanted = dict(REPOSITORY_SETTINGS, **REPOSITORY_OVERRIDES.get(repo, {}))
	if discussions:
		wanted['has_discussions'] = True
	return wanted


def update_settings(endpoint, current, wanted, apply, what):
	"""So cài đặt đang có với cài đặt mong muốn; --apply thì PATCH phần khác."""
	changes = {key: value for key, value in wanted.items() if current.get(key) != value}
	if not changes:
		print(f'   ✔ {what} đã đúng')
		return
	for key, value in changes.items():
		print(f'   {"" if apply else "(xem trước) "}{key}: {current.get(key)} → {value}')
	if apply:
		gh('api', '-X', 'PATCH', endpoint, '--input', '-', stdin=json.dumps(changes))
		print('   ✔ đã cập nhật')


def cmd_settings(repos, apply, discussions):
	for repo in repos:
		print(f'== {ORG}/{repo}')
		current = gh_json('api', f'repos/{ORG}/{repo}')
		update_settings(
			f'repos/{ORG}/{repo}',
			current,
			repository_settings(repo, discussions),
			apply,
			'cài đặt repository',
		)
		cmd_topics(repo, current, apply)
		cmd_security(repo, current, apply)
		sync_actions(
			f'repos/{ORG}/{repo}/actions/permissions', ACTIONS_PERMISSIONS, 'enabled', apply
		)
		cmd_pages(repo)


def cmd_topics(repo, current, apply):
	"""Topics của .github khớp keywords trong CITATION.cff; repository khác không quản lý."""
	if repo != '.github':
		return
	wanted = citation_keywords()
	if sorted(current.get('topics') or []) == sorted(wanted):
		print('   ✔ topics khớp CITATION.cff')
		return
	print(f'   {"" if apply else "(xem trước) "}topics: {current.get("topics")} → {wanted}')
	if apply:
		body = json.dumps({'names': wanted})
		gh('api', '-X', 'PUT', f'repos/{ORG}/{repo}/topics', '--input', '-', stdin=body)


def sync_actions(endpoint, wanted, enabled_key, apply):
	"""Quyền GitHub Actions tại endpoint (repository hoặc tổ chức) và quyền mặc định của GITHUB_TOKEN;
	gửi lại enabled_key đang có — API bắt buộc trường này nhưng script không bật, tắt Actions."""
	changed = False
	for path, target, keep in (
		(endpoint, wanted, enabled_key),
		(f'{endpoint}/workflow', WORKFLOW_PERMISSIONS, None),
	):
		try:
			current = gh_json('api', path) or {}
		except RuntimeError as exc:
			print(f'   ⚠ không đọc được {path}: {exc}')
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
			gh('api', '-X', 'PUT', path, '--input', '-', stdin=json.dumps(body))
		except RuntimeError as exc:
			print(f'   ⚠ không cập nhật được {path}: {exc}')
	if not changed:
		print('   ✔ quyền GitHub Actions đã đúng')


def cmd_pages(repo):
	"""So GitHub Pages với PAGES (chỉ so — sửa trên web)."""
	wanted = PAGES.get(repo)
	if not wanted:
		return
	try:
		current = gh_json('api', f'repos/{ORG}/{repo}/pages') or {}
	except RuntimeError:
		current = {}
	different = [key for key, value in wanted.items() if current.get(key) != value]
	if different:
		print(f'   ✘ GitHub Pages khác ({", ".join(different)}) — sửa tại Settings → Pages')
	else:
		print('   ✔ GitHub Pages đã đúng')


def cmd_org_settings(apply):
	"""Cài đặt tổ chức và quyền GitHub Actions cấp tổ chức."""
	print(f'== cài đặt tổ chức {ORG}')
	current = gh_json('api', f'orgs/{ORG}')
	update_settings(f'orgs/{ORG}', current, ORG_SETTINGS, apply, 'cài đặt tổ chức')
	for key, value in ORG_WEB_ONLY_SETTINGS.items():
		if current.get(key) != value:
			print(
				f'   ✘ {key}: {current.get(key)} ≠ {value} — sửa tại Organization settings trên web'
			)
	sync_actions(
		f'orgs/{ORG}/actions/permissions', ORG_ACTIONS_PERMISSIONS, 'enabled_repositories', apply
	)


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
		if endpoint in STATUS_ONLY_ENDPOINTS:
			if not gh_exists(f'repos/{ORG}/{repo}/{endpoint}'):
				endpoints[label] = endpoint
			continue
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


def team_role(team, user):
	"""Vai trò của người dùng trong team (maintainer, member), None nếu chưa là thành viên."""
	try:
		return (gh_json('api', f'orgs/{ORG}/teams/{team}/memberships/{user}') or {}).get('role')
	except RuntimeError:
		return None


def team_permission(team, repo):
	"""Quyền của team trên repository (read, triage, write, maintain, admin), None nếu chưa được cấp."""
	try:
		return (
			gh_json(
				'api',
				'-H',
				'Accept: application/vnd.github.v3.repository+json',
				f'orgs/{ORG}/teams/{team}/repos/{ORG}/{repo}',
			)
			or {}
		).get('role_name')
	except RuntimeError:
		return None


def cmd_team(repos, apply):
	for team, (name, permission, privacy, description) in TEAMS.items():
		exists = gh_exists(f'orgs/{ORG}/teams/{team}')
		print(f'== team {ORG}/{team}: {"đã có" if exists else "chưa có"}')
		users = [
			user for user in MAINTAINERS if not exists or team_role(team, user) != 'maintainer'
		]
		# Không hạ quyền: admin đã bao gồm maintain, maintain bao gồm push…
		missing = [
			repo
			for repo in repos
			if not exists
			or PERMISSION_RANK.get(team_permission(team, repo), -1) < PERMISSION_RANK[permission]
		]
		if not users and not missing:
			print(f'   ✔ đủ người quản trị, team có quyền {permission} {len(repos)} repository')
			continue
		if not apply:
			if not exists:
				print(f'   (xem trước) tạo team {name} ({privacy})')
			for user in users:
				print(f'   (xem trước) thêm {user} (maintainer)')
			for repo in missing:
				print(f'   (xem trước) cấp {permission} {ORG}/{repo}')
			continue
		if not exists:
			gh(
				'api',
				f'orgs/{ORG}/teams',
				'-f',
				f'name={name}',
				'-f',
				f'privacy={privacy}',
				'-f',
				f'description={description}',
			)
		for user in users:
			gh(
				'api',
				'-X',
				'PUT',
				f'orgs/{ORG}/teams/{team}/memberships/{user}',
				'-f',
				'role=maintainer',
			)
			print(f'   ✔ thêm {user} (maintainer)')
		for repo in missing:
			gh(
				'api',
				'-X',
				'PUT',
				f'orgs/{ORG}/teams/{team}/repos/{ORG}/{repo}',
				'-f',
				f'permission={permission}',
			)
			print(f'   ✔ {permission} {ORG}/{repo}')
	if apply:
		print(
			f'   CODEOWNERS dùng @{ORG}/{TEAM}; đổi thành viên thì cập nhật MAINTAINERS.md và MAINTAINERS trong script này.'
		)


def main():
	parser = argparse.ArgumentParser(
		description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
	)
	parser.add_argument(
		'command',
		choices=('files', 'settings', 'rulesets', 'team', 'org-rulesets', 'org-settings'),
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
	# Lệnh org-* áp dụng cho cả tổ chức, không cần danh sách repository.
	repos = [] if args.command.startswith('org-') else list_repos(args.repo)
	if args.command == 'files':
		cmd_files(repos, args.apply)
	elif args.command == 'settings':
		cmd_settings(repos, args.apply, args.discussions)
	elif args.command == 'rulesets':
		cmd_rulesets(repos, args.apply)
	elif args.command == 'org-rulesets':
		cmd_org_rulesets(args.apply)
	elif args.command == 'org-settings':
		cmd_org_settings(args.apply)
	else:
		cmd_team(repos, args.apply)
	if not args.apply:
		print('Chế độ xem trước — chạy lại với --apply để áp dụng.')


if __name__ == '__main__':
	main()
