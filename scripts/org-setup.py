"""Áp dụng cấu hình chung của tổ chức lên các repository bằng GitHub CLI (gh).

Chạy: python3 scripts/org-setup.py <lệnh> [--apply] [--repo TÊN] [--discussions]
Mặc định chỉ xem trước, không thay đổi gì; thêm --apply để áp dụng trên GitHub.
Yêu cầu: gh đã đăng nhập bằng tài khoản có quyền quản trị tổ chức.

Lệnh (nên chạy theo thứ tự):
	files: mở Pull Request thêm các tệp dùng chung còn thiếu — .editorconfig, .gitattributes,
		workflow kiểm tra tiêu đề Pull Request, tên branch và gắn nhãn (labeler), CODEOWNERS, dependabot.yml, release.yml
		và tệp định dạng theo ngôn ngữ repository dùng. Không ghi đè tệp đã có.
	settings: cho phép Merge, Squash và Rebase, tự xóa branch sau khi hợp nhất; bật secret scanning,
		push protection, Dependabot security updates, báo cáo lỗ hổng riêng tư;
		--discussions bật thêm GitHub Discussions.
	rulesets: tạo hoặc cập nhật ruleset Protect Main (rulesets/protect-main.json) và Protect Release
		Tags (rulesets/protect-release-tags.json, ADR 0008); Protect Main của repository khác chỉ giữ
		kiểm tra bắt buộc có job tương ứng. Bỏ qua repository
		chưa có workflow kiểm tra bắt buộc — hợp nhất Pull Request của lệnh files trước.
	team: tạo team maintainers, thêm người quản trị và cấp quyền maintain mọi repository.
	org-rulesets: tạo hoặc cập nhật ruleset cấp tổ chức Protect Main (Organization)
		(rulesets/org-protect-main.json) cho mọi repository; cần token có quyền admin:org
		(gh auth refresh -h github.com -s admin:org); GitHub chỉ thực thi khi tổ chức dùng gói Team trở lên.
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
# Ruleset cấp tổ chức sinh từ Protect Main; tệp dùng để import trên web, org_ruleset() là nguồn.
ORG_RULESET_FILE = ROOT / 'rulesets' / 'org-protect-main.json'
ORG_RULESET_NAME = 'Protect Main (Organization)'
# Quy tắc ruleset cấp tổ chức không nhận (theo OpenAPI của GitHub cho POST /orgs/{org}/rulesets).
ORG_UNSUPPORTED_RULES = ('code_quality',)
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


def org_ruleset():
	"""Protect Main cho mọi repository ở cấp tổ chức: như Protect Main của repository khác (chỉ giữ kiểm tra
	bắt buộc có ở mọi repository), nhắm ~ALL repository, bỏ quy tắc cấp tổ chức không hỗ trợ."""
	ruleset = ruleset_for('app')
	ruleset['name'] = ORG_RULESET_NAME
	ruleset['conditions'] = {
		'ref_name': {'exclude': [], 'include': ['~DEFAULT_BRANCH']},
		'repository_name': {'exclude': [], 'include': ['~ALL']},
	}
	ruleset['rules'] = [
		rule for rule in ruleset['rules'] if rule['type'] not in ORG_UNSUPPORTED_RULES
	]
	return ruleset


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
		if repo == '.github':
			continue
		print(f'== {ORG}/{repo}')
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
	endpoints = {}
	for label, endpoint in security_endpoints(private).items():
		try:
			enabled = (gh_json('api', f'repos/{ORG}/{repo}/{endpoint}') or {}).get('enabled')
		except RuntimeError as exc:
			print(f'   ⚠ không đọc được trạng thái {label}: {exc}')
			continue
		if not enabled:
			endpoints[label] = endpoint
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


def cmd_org_rulesets(apply):
	"""Ruleset cấp tổ chức; thiếu quyền admin:org thì hướng dẫn cấp quyền hoặc import tệp trên web."""
	source = ORG_RULESET_FILE.relative_to(ROOT)
	print(
		f'== ruleset cấp tổ chức {ORG}: "{ORG_RULESET_NAME}" (chỉ thực thi với gói GitHub Team trở lên)'
	)
	try:
		existing = {
			item['name']: item['id'] for item in gh_json('api', f'orgs/{ORG}/rulesets') or []
		}
	except RuntimeError as exc:
		print(f'   ⚠ không đọc được ruleset cấp tổ chức: {exc}')
		print(
			'   Cấp quyền: gh auth refresh -h github.com -s admin:org — hoặc import '
			f'{source} tại Organization settings → Repository → Rulesets → New ruleset → Import a ruleset.'
		)
		return
	action = 'cập nhật' if ORG_RULESET_NAME in existing else 'tạo'
	if not apply:
		print(f'   (xem trước) {action} ruleset "{ORG_RULESET_NAME}" từ {source}')
		return
	body = json.dumps(org_ruleset(), ensure_ascii=False)
	try:
		if ORG_RULESET_NAME in existing:
			path = f'orgs/{ORG}/rulesets/{existing[ORG_RULESET_NAME]}'
			gh('api', '-X', 'PUT', path, '--input', '-', stdin=body)
		else:
			gh('api', '-X', 'POST', f'orgs/{ORG}/rulesets', '--input', '-', stdin=body)
	except RuntimeError as exc:
		print(f'   ⚠ không {action} được ruleset "{ORG_RULESET_NAME}": {exc}')
		return
	print(f'   ✔ đã {action} ruleset "{ORG_RULESET_NAME}"')


def cmd_team(repos, apply):
	exists = gh_exists(f'orgs/{ORG}/teams/{TEAM}')
	print(f'== team {ORG}/{TEAM}: {"đã có" if exists else "chưa có"}')
	if not apply:
		print(
			f'   (xem trước) {"" if exists else "tạo team, "}thêm {", ".join(MAINTAINERS)}, cấp maintain {len(repos)} repository'
		)
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
	for user in MAINTAINERS:
		gh(
			'api',
			'-X',
			'PUT',
			f'orgs/{ORG}/teams/{TEAM}/memberships/{user}',
			'-f',
			'role=maintainer',
		)
	for repo in repos:
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
	repos = list_repos(args.repo)
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
