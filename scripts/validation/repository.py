"""Quản trị repository: quy ước branch, commit; nhãn; Dependabot; người quản trị; ruleset."""

import ast
import json
import re

from orgsetup.labels import inspectLabels

from validation.common import (
	ROOT,
	configField,
	configItems,
	conventions,
	error,
	errors,
	loadYaml,
	readJsonObject,
	readText,
)
from validation.forms import FORM_LABELS
from validation.workflows import repositoryWorkflows, workflowJobs

# Nhãn mặc định GitHub tạo cho repository mới — bộ nhãn chuẩn phải có đủ để không mất nhãn quen thuộc.
GITHUB_DEFAULT_LABELS = (
	'bug',
	'documentation',
	'duplicate',
	'enhancement',
	'good first issue',
	'help wanted',
	'invalid',
	'question',
	'wontfix',
)


def contributingSection(text, heading):
	"""Nội dung một mục `## …` của CONTRIBUTING.md, tới mục kế tiếp."""
	match = re.search(
		rf'^## .*{re.escape(heading)}\n(.*?)(?=^## |\Z)', text, re.MULTILINE | re.DOTALL
	)
	return match.group(1) if match else ''


def checkConventions():
	"""Loại commit và tiền tố branch trong CONTRIBUTING.md phải khớp scripts/conventions.py — script mà
	workflow branch-name.yml, pr-title.yml (của repository này và workflow mẫu) gọi."""
	contributing = readText(ROOT / 'CONTRIBUTING.md')
	types = set(
		re.findall(
			r'^\| `([a-z]+)` ', contributingSection(contributing, 'QUY ƯỚC COMMIT'), re.MULTILINE
		)
	)
	prefixes = set(
		re.findall(
			r'^\| `([a-z]+)/` ',
			contributingSection(contributing, 'QUY ƯỚC ĐẶT TÊN BRANCH'),
			re.MULTILINE,
		)
	)
	# Mỗi tiền tố branch có luật head-branch trong labeler.yml của repository này và bản mẫu (tự gắn nhãn loại
	# cho Pull Request).
	for labeler in (
		ROOT / '.github' / 'labeler.yml',
		ROOT / 'repository-templates' / 'labeler.yml',
	):
		if not labeler.exists():
			continue
		covered = set(re.findall(r"'\^([a-z]+)/'", readText(labeler)))
		# Nhãn giai đoạn Pre-Release không thay cho nhãn loại release.
		data = loadYaml(labeler, dict) or {}
		if not any(
			'^release/' in configItems(labeler, rule, 'head-branch', str)
			for rule in configItems(labeler, data, 'release')
		):
			covered.discard('release')
		errors.extend(
			f'{labeler.relative_to(ROOT)}: thiếu luật head-branch cho tiền tố "{prefix}/" của CONTRIBUTING.md'
			for prefix in sorted(prefixes - covered)
		)
	# Mẫu commit (.gitmessage, bật bằng make hooks) liệt kê đúng các loại commit.
	message = ROOT / '.gitmessage'
	listed = (
		re.search(r'^# Loại: (.+)$', readText(message), re.MULTILINE) if message.exists() else None
	)
	for word in sorted(types ^ set(re.split(r',\s*', listed.group(1).strip()) if listed else ())):
		where = 'thiếu' if word in types else 'thừa'
		errors.append(f'.gitmessage: dòng "# Loại:" {where} "{word}" so với CONTRIBUTING.md')
	for name, expected, found in (
		('COMMIT_TYPES', types, set(conventions.COMMIT_TYPES)),
		('BRANCH_PREFIXES', prefixes, set(conventions.BRANCH_PREFIXES)),
	):
		for word in sorted(expected ^ found):
			where = 'thiếu' if word in expected else 'thừa'
			errors.append(f'scripts/conventions.py: {name} {where} "{word}" so với CONTRIBUTING.md')


def checkMaintainers():
	"""Người quản trị trong MAINTAINERS.md khớp MAINTAINERS của scripts/orgsetup/teams.py (org-setup.py team thêm
	họ vào mọi team)."""
	listing, source = ROOT / 'MAINTAINERS.md', ROOT / 'scripts' / 'orgsetup' / 'teams.py'
	if not listing.exists() or not source.exists():
		return
	current = contributingSection(readText(listing), 'NGƯỜI QUẢN TRỊ HIỆN TẠI')
	documented = set(re.findall(r'\[@([A-Za-z0-9-]+)\]\(https://github\.com/\1\)', current))
	match = re.search(r'^MAINTAINERS = (\(.*?\))$', readText(source), re.MULTILINE)
	configured = set(ast.literal_eval(match.group(1))) if match else set()
	for name in sorted(documented ^ configured):
		where = listing if name in configured else source
		error(
			where,
			f'người quản trị "{name}" chỉ có ở một trong MAINTAINERS.md và MAINTAINERS của teams.py',
		)
	# Danh sách bỏ qua của ruleset cấp repository ghi actor_id của từng người quản trị (tra id cần API nên chỉ so
	# số lượng): thêm, bớt người quản trị thì sửa cả ruleset.
	for path in sorted((ROOT / 'rulesets').glob('protect-*.json')):
		try:
			ruleset = readJsonObject(path)
		except json.JSONDecodeError:
			continue  # checkFile đã báo lỗi cú pháp của tệp này.
		users = [
			actor
			for actor in configItems(path, ruleset, 'bypass_actors')
			if actor.get('actor_type') == 'User'
		]
		if len(users) != len(configured):
			error(
				path,
				f'danh sách bỏ qua có {len(users)} tài khoản, MAINTAINERS có {len(configured)} người — '
				'thêm, bớt actor_id cho khớp người quản trị',
			)


def checkRulesets():
	"""Kiểm tra bắt buộc trong ruleset Protect Main phải trùng tên một job có thật, nếu không PR chờ mãi."""
	path = ROOT / 'rulesets' / 'protect-main.json'
	if not path.exists():
		errors.append('thiếu tệp bắt buộc rulesets/protect-main.json')
		return
	try:
		ruleset = readJsonObject(path)
	except json.JSONDecodeError:
		return
	if ruleset.get('name') != 'Protect Main':
		error(path, 'ruleset phải tên "Protect Main"')
	jobs = set()
	for workflow in repositoryWorkflows():
		for job in workflowJobs(workflow).values():
			name = job.get('name')
			if isinstance(name, str):
				jobs.add(name)
	# Mọi ruleset nhánh, tag (cấp repository, cấp tổ chức) bắt buộc commit có chữ ký (ADR 0006); push
	# ruleset không nhận quy tắc này (ADR 0007).
	for rulesetPath in sorted((ROOT / 'rulesets').glob('*.json')):
		try:
			data = readJsonObject(rulesetPath)
		except json.JSONDecodeError:
			continue
		if data.get('target') == 'push':
			continue
		if 'required_signatures' not in {
			configField(rulesetPath, r, 'type', str)
			for r in configItems(rulesetPath, data, 'rules')
		}:
			error(
				rulesetPath, 'ruleset phải có quy tắc required_signatures (Require signed commits)'
			)
	tagPath = ROOT / 'rulesets' / 'protect-release-tags.json'
	if not tagPath.exists():
		errors.append('thiếu tệp bắt buộc rulesets/protect-release-tags.json')
	else:
		try:
			tags = readJsonObject(tagPath)
		except json.JSONDecodeError:
			tags = {}
		conditions = configField(tagPath, tags, 'conditions', dict)
		refName = configField(tagPath, conditions, 'ref_name', dict)
		include = configItems(tagPath, refName, 'include', str)
		if tags.get('name') != 'Protect Release Tags' or tags.get('target') != 'tag':
			error(tagPath, 'ruleset phải tên "Protect Release Tags", target "tag" (ADR 0005)')
		for pattern in ('refs/tags/v*', 'refs/tags/Stable.v*', 'refs/tags/Beta.v*'):
			if pattern not in include:
				error(tagPath, f'ruleset phải áp dụng cho {pattern} (tag phát hành)')
		if not {'creation', 'update', 'deletion'} <= {
			configField(tagPath, rule, 'type', str) for rule in configItems(tagPath, tags, 'rules')
		}:
			error(tagPath, 'ruleset phải chặn creation, update, deletion của tag phát hành')
	orgPath = ROOT / 'rulesets' / 'org-protect-main.json'
	if not orgPath.exists():
		errors.append('thiếu tệp bắt buộc rulesets/org-protect-main.json')
	else:
		try:
			org = readJsonObject(orgPath)
		except json.JSONDecodeError:
			org = {}
		conditions = configField(orgPath, org, 'conditions', dict)
		repositoryName = configField(orgPath, conditions, 'repository_name', dict)
		repositories = configItems(orgPath, repositoryName, 'include', str)
		if org.get('name') != 'Protect Main (Organization)' or '~ALL' not in repositories:
			error(
				orgPath,
				'ruleset phải tên "Protect Main (Organization)" và nhắm mọi repository (~ALL)',
			)
	# Import ruleset cấp tổ chức báo "contains an invalid actor" với actor loại User.
	for orgFile in sorted((ROOT / 'rulesets').glob('org-*.json')):
		if re.search(r'"(actor_type|type)":\s*"User"', readText(orgFile)):
			error(
				orgFile,
				'ruleset cấp tổ chức không dùng actor loại User — GitHub từ chối khi import',
			)
	orgTagPath = ROOT / 'rulesets' / 'org-protect-release-tags.json'
	if not orgTagPath.exists():
		errors.append('thiếu tệp bắt buộc rulesets/org-protect-release-tags.json')
	else:
		try:
			orgTags = readJsonObject(orgTagPath)
		except json.JSONDecodeError:
			orgTags = {}
		conditions = configField(orgTagPath, orgTags, 'conditions', dict)
		repositoryName = configField(orgTagPath, conditions, 'repository_name', dict)
		refName = configField(orgTagPath, conditions, 'ref_name', dict)
		if (
			orgTags.get('name') != 'Protect Release Tags (Organization)'
			or '~ALL' not in configItems(orgTagPath, repositoryName, 'include', str)
			or not {'refs/tags/v*', 'refs/tags/Stable.v*', 'refs/tags/Beta.v*'}
			<= set(configItems(orgTagPath, refName, 'include', str))
		):
			error(
				orgTagPath,
				'ruleset phải tên "Protect Release Tags (Organization)", nhắm ~ALL repository và refs/tags/v*, '
				'refs/tags/Stable.v*, refs/tags/Beta.v*',
			)
	pushPath = ROOT / 'rulesets' / 'org-protect-pushes.json'
	if not pushPath.exists():
		errors.append('thiếu tệp bắt buộc rulesets/org-protect-pushes.json')
	else:
		try:
			pushes = readJsonObject(pushPath)
		except json.JSONDecodeError:
			pushes = {}
		conditions = configField(pushPath, pushes, 'conditions', dict)
		repositoryName = configField(pushPath, conditions, 'repository_name', dict)
		if (
			pushes.get('name') != 'Protect Pushes (Organization)'
			or pushes.get('target') != 'push'
			or '~ALL' not in configItems(pushPath, repositoryName, 'include', str)
		):
			error(
				pushPath,
				'ruleset phải tên "Protect Pushes (Organization)", target "push" và nhắm ~ALL repository (ADR 0007)',
			)
	for rule in configItems(path, ruleset, 'rules'):
		parameters = configField(path, rule, 'parameters', dict)
		for check in configItems(path, parameters, 'required_status_checks'):
			context = configField(path, check, 'context', str)
			if context not in jobs:
				error(
					path,
					f'kiểm tra bắt buộc "{check.get("context")}" không trùng tên job nào trong .github/workflows',
				)


def checkLabels(path):
	names, problems = inspectLabels(loadYaml(path))
	for problem in problems:
		error(path, problem)
	return names


def checkDependabotCooldown():
	"""Mọi mục Dependabot chờ ≥ 7 ngày sau khi phát hành (chống gói độc vừa phát hành; không ảnh hưởng cập nhật bảo mật)."""
	for path in (
		ROOT / '.github' / 'dependabot.yml',
		ROOT / 'repository-templates' / 'dependabot.yml',
	):
		data = (loadYaml(path, dict) if path.exists() else None) or {}
		for update in configItems(path, data, 'updates'):
			days = configField(path, update, 'cooldown', dict).get('default-days')
			if not isinstance(days, int) or days < 7:
				error(path, f'{update.get("package-ecosystem")}: cần cooldown.default-days ≥ 7')


def configLabels():
	"""Nhãn dùng trong dependabot.yml, release.yml, labeler.yml và workflow stale của repository và bản mẫu."""
	found = []
	for path in (
		ROOT / '.github' / 'dependabot.yml',
		ROOT / 'repository-templates' / 'dependabot.yml',
	):
		data = (loadYaml(path, dict) if path.exists() else None) or {}
		for update in configItems(path, data, 'updates'):
			found += [(path, label) for label in configItems(path, update, 'labels', str)]
	for path in (ROOT / '.github' / 'release.yml', ROOT / 'repository-templates' / 'release.yml'):
		data = (loadYaml(path, dict) if path.exists() else None) or {}
		changelog = configField(path, data, 'changelog', dict)
		exclude = configField(path, changelog, 'exclude', dict)
		found += [(path, label) for label in configItems(path, exclude, 'labels', str)]
		for category in configItems(path, changelog, 'categories'):
			found += [
				(path, label)
				for label in configItems(path, category, 'labels', str)
				if label != '*'
			]
	for path in (ROOT / '.github' / 'labeler.yml', ROOT / 'repository-templates' / 'labeler.yml'):
		data = (loadYaml(path, dict) if path.exists() else None) or {}
		for label in data:
			if isinstance(label, str):
				found.append((path, label))
			else:
				error(path, 'tên nhãn phải là chuỗi')
	for path in (
		ROOT / '.github' / 'workflows' / 'stale.yml',
		ROOT / 'workflow-templates' / 'stale.yml',
	):
		if not path.exists():
			continue
		text = readText(path)
		for match in re.finditer(
			r'^\s*(?:stale|exempt)-(?:issue|pr)-labels?:\s*(.+)$', text, re.MULTILINE
		):
			names = match.group(1).strip().strip('\'"').split(',')
			found += [(path, name.strip()) for name in names if name.strip()]
	return found


def checkLabelUsage():
	"""Nhãn dùng trong biểu mẫu và cấu hình phải có trong labels.yml."""
	labelFile = ROOT / 'labels.yml'
	if not labelFile.exists():
		return
	known = checkLabels(labelFile)
	for label in GITHUB_DEFAULT_LABELS:
		if label not in known:
			error(labelFile, f'thiếu nhãn mặc định của GitHub "{label}"')
	for formPath, label in FORM_LABELS + configLabels():
		if label.lower() not in known:
			error(formPath, f'nhãn "{label}" chưa có trong labels.yml')
