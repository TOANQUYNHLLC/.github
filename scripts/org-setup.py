"""Áp dụng cấu hình chung của tổ chức lên các repository bằng GitHub CLI (gh).

Chạy: python3 scripts/org-setup.py <lệnh> [--apply] [--repo TÊN] [--discussions]
Mặc định chỉ xem trước, không thay đổi gì; thêm --apply để áp dụng trên GitHub.
Yêu cầu: gh đã đăng nhập bằng tài khoản có quyền quản trị tổ chức.

Lệnh (nên chạy theo thứ tự):
	files: mở Pull Request thêm các tệp dùng chung còn thiếu — workflow kiểm tra tiêu đề
		Pull Request và tên branch, CODEOWNERS, dependabot.yml (chỉ ecosystem repository dùng),
		release.yml. Không ghi đè tệp đã có.
	settings: chỉ cho phép Squash and merge, tự xóa branch sau khi hợp nhất;
		--discussions bật thêm GitHub Discussions.
	rulesets: tạo hoặc cập nhật ruleset bảo vệ nhánh chính (rulesets/*.json). Bỏ qua repository
		chưa có workflow kiểm tra bắt buộc — hợp nhất Pull Request của lệnh files trước.
	team: tạo team maintainers, thêm người quản trị và cấp quyền maintain mọi repository.
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
# Workflow mà ruleset default-branch.json bắt buộc phải có kết quả.
REQUIRED_WORKFLOWS = ('.github/workflows/pr-title.yml', '.github/workflows/branch-name.yml')
# Ecosystem Dependabot và tệp khai báo phụ thuộc ở thư mục gốc cho biết repository dùng nó.
ECOSYSTEM_MANIFESTS = {
	'npm': ('package.json',),
	'pip': ('requirements.txt', 'pyproject.toml', 'setup.py'),
	'gomod': ('go.mod',),
	'docker': ('Dockerfile',),
}
MERGE_SETTINGS = {
	'allow_squash_merge': True,
	'allow_merge_commit': False,
	'allow_rebase_merge': False,
	'delete_branch_on_merge': True,
	'squash_merge_commit_title': 'PR_TITLE',
	'squash_merge_commit_message': 'PR_BODY',
}


def gh(*args):
	result = subprocess.run(['gh', *args], capture_output=True, text=True, check=False)
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

	return {
		'.github/workflows/pr-title.yml': read('workflow-templates/pr-title.yml'),
		'.github/workflows/branch-name.yml': read('workflow-templates/branch-name.yml'),
		'.github/CODEOWNERS': read('repository-templates/CODEOWNERS'),
		'.github/dependabot.yml': filter_dependabot(
			read('repository-templates/dependabot.yml'), root_names
		),
		'.github/release.yml': read('repository-templates/release.yml'),
	}


def ruleset_file(repo):
	return ROOT / 'rulesets' / ('dot-github.json' if repo == '.github' else 'default-branch.json')


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
			print('   ✔ đã đúng cấu hình')
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


def cmd_rulesets(repos, apply):
	for repo in repos:
		print(f'== {ORG}/{repo}')
		path = ruleset_file(repo)
		ruleset = json.loads(path.read_text(encoding='utf-8'))
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
		action = 'cập nhật' if ruleset['name'] in existing else 'tạo'
		if not apply:
			print(
				f'   (xem trước) {action} ruleset "{ruleset["name"]}" từ {path.relative_to(ROOT)}'
			)
			continue
		if ruleset['name'] in existing:
			gh(
				'api',
				'-X',
				'PUT',
				f'repos/{ORG}/{repo}/rulesets/{existing[ruleset["name"]]}',
				'--input',
				str(path),
			)
		else:
			gh('api', '-X', 'POST', f'repos/{ORG}/{repo}/rulesets', '--input', str(path))
		expected = 'hai tài khoản quản trị' if repo == '.github' else 'Repository admin'
		print(
			f'   ✔ đã {action} ruleset "{ruleset["name"]}" — kiểm tra Bypass list hiển thị {expected}'
		)


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
	print(f'   Bước tiếp: đổi CODEOWNERS và MAINTAINERS.md sang @{ORG}/{TEAM}.')


def main():
	parser = argparse.ArgumentParser(
		description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
	)
	parser.add_argument('command', choices=('files', 'settings', 'rulesets', 'team'))
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
	else:
		cmd_team(repos, args.apply)
	if not args.apply:
		print('Chế độ xem trước — chạy lại với --apply để áp dụng.')


if __name__ == '__main__':
	main()
