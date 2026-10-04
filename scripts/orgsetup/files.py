"""Lệnh files: Pull Request thêm tệp dùng chung còn thiếu vào repository."""

import base64
import re
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
	(ECOSYSTEM_MANIFESTS['pip'], '.python-version', 'repository-templates/.python-version'),
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
			root = {
				item['name']
				for item in github.ghJson('api', f'repos/{github.ORG}/{repo}/contents?ref={base}')
			}
		except RuntimeError:
			print('   ⚠ repository trống — bỏ qua')
			continue
		files = plannedFiles(root)
		missing = {
			path: content
			for path, content in files.items()
			if not github.ghExists(f'repos/{github.ORG}/{repo}/contents/{path}?ref={base}')
		}
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
		sha = github.ghJson('api', f'repos/{github.ORG}/{repo}/git/ref/heads/{base}')['object'][
			'sha'
		]
		github.gh(
			'api',
			f'repos/{github.ORG}/{repo}/git/refs',
			'-f',
			f'ref=refs/heads/{SYNC_BRANCH}',
			'-f',
			f'sha={sha}',
		)
		for path, content in missing.items():
			github.gh(
				'api',
				'-X',
				'PUT',
				f'repos/{github.ORG}/{repo}/contents/{path}',
				'-f',
				f'message=chore: thêm {path}',
				'-f',
				f'content={base64.b64encode(content.encode("utf-8")).decode("ascii")}',
				'-f',
				f'branch={SYNC_BRANCH}',
			)
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
