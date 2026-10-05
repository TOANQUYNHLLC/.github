"""Lệnh files: Pull Request thêm tệp dùng chung còn thiếu vào repository."""

import base64
import json
import re
import tomllib
from pathlib import Path

from orgsetup import github

SYNC_BRANCH = 'chore/sync_org_files'

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
	# Phiên bản Node.js cho workflow mẫu Node.js CI (setup-node đọc .nvmrc), cùng bản với repository này.
	(('package.json',), '.nvmrc', '.nvmrc'),
	(ECOSYSTEM_MANIFESTS['pip'], 'ruff.toml', 'ruff.toml'),
	(('Cargo.toml',), 'rustfmt.toml', 'repository-templates/rustfmt.toml'),
	(('CMakeLists.txt', 'meson.build'), '.clang-format', 'repository-templates/.clang-format'),
	(('Dockerfile', 'compose.yaml'), '.dockerignore', 'repository-templates/.dockerignore'),
)


def filterDependabot(template, rootNames):
	"""Giữ github-actions và các ecosystem có tệp khai báo trong rootNames; bỏ phần còn lại."""
	used = {'github-actions'} | {
		ecosystem
		for ecosystem, manifests in ECOSYSTEM_MANIFESTS.items()
		if any(name in rootNames for name in manifests)
	}
	_, _, updates = template.partition('updates:\n')
	blocks = []
	for block in updates.split('\n\n'):
		match = re.search(r'package-ecosystem: (\S+)', block)
		if match and match.group(1) in used:
			blocks.append(block.strip('\n'))
	header = (
		f'# Sinh từ {github.ORG}/.github (repository-templates/dependabot.yml) theo tệp khai báo phụ thuộc.\n'
		'version: 2\nupdates:\n'
	)
	return header + '\n\n'.join(blocks) + '\n'


def pythonVersion():
	"""Phiên bản Python trong mise.toml — nguồn duy nhất (ADR 0008), cũng là .python-version cấp cho repository
	khác (workflow mẫu Python CI đọc tệp này)."""
	text = (github.ROOT / 'mise.toml').read_text(encoding='utf-8')
	return str(tomllib.loads(text)['tools']['python'])


def plannedFiles(rootNames):
	"""Đường dẫn trong repository đích → nội dung tệp dùng chung."""

	def read(path):
		return (github.ROOT / path).read_text(encoding='utf-8')

	files = {
		'.editorconfig': read('.editorconfig'),
		'.gitattributes': read('.gitattributes'),
		'.github/workflows/pr-title.yml': read('workflow-templates/pr-title.yml'),
		'.github/workflows/branch-name.yml': read('workflow-templates/branch-name.yml'),
		'.github/workflows/labeler.yml': read('workflow-templates/labeler.yml'),
		'.github/labeler.yml': read('repository-templates/labeler.yml'),
		'.github/CODEOWNERS': read('repository-templates/CODEOWNERS'),
		'.github/dependabot.yml': filterDependabot(
			read('repository-templates/dependabot.yml'), rootNames
		),
		'.github/release.yml': read('repository-templates/release.yml'),
	}
	for manifests, target, source in LANGUAGE_FILES:
		if any(name in rootNames for name in manifests):
			files[target] = read(source)
	if any(name in rootNames for name in ECOSYSTEM_MANIFESTS['pip']):
		files['.python-version'] = f'{pythonVersion()}\n'
	return files


def templateJobs():
	"""Tên job trong các workflow mà lệnh files thêm vào repository khác."""
	names = set()
	for workflow in REQUIRED_WORKFLOWS:
		text = (github.ROOT / 'workflow-templates' / Path(workflow).name).read_text(
			encoding='utf-8'
		)
		names.update(re.findall(r'^ {8}name: (.+)$', text, re.MULTILINE))
	return names


def syncFiles(repos, apply):
	for repo in repos:
		print(f'== {github.ORG}/{repo}')
		if repo == '.github':
			print('   – bỏ qua: repository nguồn của tệp dùng chung')
			continue
		base = github.defaultBranch(repo)
		try:
			reference = github.ghJson('api', f'repos/{github.ORG}/{repo}/git/ref/heads/{base}')
			commit = reference.get('object') if isinstance(reference, dict) else None
			if (
				not isinstance(commit, dict)
				or not isinstance(commit.get('sha'), str)
				or not commit['sha']
			):
				raise ValueError(f'{repo}: không đọc được SHA của nhánh {base}')
			sha = commit['sha']
		except RuntimeError as exc:
			if not (github.isNotFound(exc) or github.isEmptyRepository(exc)):
				raise
			print('   ⚠ repository trống — bỏ qua')
			continue
		# Đọc một cây tại SHA cố định: mọi phép so và branch mới dùng cùng một trạng thái, không giữ cache
		# qua lần chạy sau. API có thể cắt cây lớn; khi đó dò từng đường dẫn thay vì coi phần bị cắt là thiếu.
		tree = github.ghJson('api', f'repos/{github.ORG}/{repo}/git/trees/{sha}?recursive=1')
		if (
			not isinstance(tree, dict)
			or type(tree.get('truncated')) is not bool
			or not isinstance(tree.get('tree'), list)
		):
			raise ValueError(f'{repo}: không đọc được cây Git hoặc trạng thái truncated')
		for item in tree['tree']:
			if (
				not isinstance(item, dict)
				or not isinstance(item.get('path'), str)
				or not item['path']
				or item.get('type') not in ('blob', 'tree', 'commit')
			):
				raise ValueError(f'{repo}: phần tử cây Git thiếu đường dẫn hoặc sai loại')
		if tree['truncated']:
			contents = github.ghJson('api', f'repos/{github.ORG}/{repo}/contents?ref={sha}')
			if not isinstance(contents, list) or any(
				not isinstance(item, dict)
				or not isinstance(item.get('name'), str)
				or not item['name']
				or item.get('type') not in ('file', 'dir', 'symlink', 'submodule')
				for item in contents
			):
				raise ValueError(f'{repo}: không đọc được danh sách tệp gốc tại {sha}')
			root = {item['name'] for item in contents if item['type'] in ('file', 'symlink')}
		else:
			root = {
				item['path']
				for item in tree['tree']
				if '/' not in item['path'] and item['type'] == 'blob'
			}
		files = plannedFiles(root)
		if tree['truncated']:
			missing = {
				path: content
				for path, content in files.items()
				if not github.ghExists(f'repos/{github.ORG}/{repo}/contents/{path}?ref={sha}')
			}
		else:
			paths = {item['path'] for item in tree['tree']}
			missing = {path: content for path, content in files.items() if path not in paths}
		if not missing:
			print('   ✔ đã đủ tệp dùng chung')
			continue
		for path in missing:
			print(f'   {"+" if apply else "(xem trước) +"} {path}')
		if not apply:
			continue
		if github.ghExists(f'repos/{github.ORG}/{repo}/git/ref/heads/{SYNC_BRANCH}'):
			print(f'   ⚠ branch {SYNC_BRANCH} đã tồn tại — kiểm tra Pull Request đang mở')
			continue
		github.gh(
			'api',
			f'repos/{github.ORG}/{repo}/git/refs',
			'-f',
			f'ref=refs/heads/{SYNC_BRANCH}',
			'-f',
			f'sha={sha}',
		)
		# Một commit cho toàn bộ tệp thiếu: GitHub ký, expectedHeadOid chặn ghi nếu branch đã đổi.
		commit = {
			'query': github.COMMIT_MUTATION,
			'variables': {
				'input': {
					'branch': {
						'repositoryNameWithOwner': f'{github.ORG}/{repo}',
						'branchName': SYNC_BRANCH,
					},
					'message': {'headline': 'chore: thêm tệp dùng chung của tổ chức'},
					'expectedHeadOid': sha,
					'fileChanges': {
						'additions': [
							{
								'path': path,
								'contents': base64.b64encode(content.encode('utf-8')).decode(
									'ascii'
								),
							}
							for path, content in missing.items()
						]
					},
				}
			},
		}
		try:
			github.gh('api', 'graphql', '--input', '-', '--silent', stdin=json.dumps(commit))
		except RuntimeError as exc:
			# Xóa branch vừa tạo: còn branch thì lần chạy sau bỏ qua repository vì "branch đã tồn tại".
			try:
				github.gh(
					'api',
					'-X',
					'DELETE',
					f'repos/{github.ORG}/{repo}/git/refs/heads/{SYNC_BRANCH}',
					'--silent',
				)
			except RuntimeError as cleanup:
				raise RuntimeError(
					f'{repo}: không commit được tệp dùng chung ({exc}); chưa xóa được branch '
					f'{SYNC_BRANCH} ({cleanup}) — xóa trên GitHub trước khi chạy lại'
				) from exc
			raise RuntimeError(
				f'{repo}: không commit được tệp dùng chung ({exc}); đã xóa branch {SYNC_BRANCH}'
			) from exc
		body = (
			f'Thêm các tệp dùng chung của tổ chức từ {github.ORG}/.github:\n\n'
			+ ''.join(f'- `{path}`\n' for path in missing)
			+ '\nKiểm tra `CODEOWNERS` và `dependabot.yml` có đúng với repository trước khi hợp nhất.'
		)
		url = github.gh(
			'pr',
			'create',
			'--repo',
			f'{github.ORG}/{repo}',
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
