"""Workflow GitHub Actions và workflow mẫu: ghim SHA, quyền, mỗi bước một lệnh (ADR 00000009)."""

import json
import re

from validation.common import ROOT, configItems, error, loadYaml, readJsonObject, trackedFiles

# Danh mục chung của workflow mẫu (actions/starter-workflows): danh mục đầu tiên phải thuộc nhóm này,
# sau đó mới tới ngôn ngữ Linguist hoặc tech stack.
WORKFLOW_GENERAL_CATEGORIES = {
	'Continuous integration',
	'Deployment',
	'Testing',
	'Code quality',
	'Code review',
	'Dependency review',
	'Dependency graph',
	'Code Scanning',
	'Monitoring',
	'Automation',
	'Utilities',
	'Pages',
}


def workflowJobs(path):
	"""Các job có cấu trúc hợp lệ; dùng chung khi kiểm tra workflow và đối chiếu ruleset."""
	workflow = loadYaml(path, dict)
	if workflow is None:
		return {}
	jobs = workflow.get('jobs')
	if not isinstance(jobs, dict):
		error(path, 'cấu trúc jobs phải là object')
		return {}
	valid = {}
	for name, job in jobs.items():
		if not isinstance(job, dict):
			error(path, f'cấu trúc job "{name}" phải là object')
		else:
			valid[name] = job
	return valid


def checkActionRef(path, action, location):
	"""Action bên ngoài phải ghim SHA đầy đủ; kiểm tra giá trị YAML, kể cả khóa và giá trị có dấu nháy."""
	if not isinstance(action, str):
		error(path, f'cấu trúc {location}.uses phải là chuỗi')
		return
	if action.startswith(('./', 'docker://')):
		return
	ref = action.rsplit('@', 1)
	if len(ref) != 2 or not re.fullmatch(r'[0-9a-f]{40}', ref[1]):
		error(path, f'{location}: action "{action}" phải ghim theo commit SHA đầy đủ')


def checkWorkflowStep(path, step, location):
	"""Các quy tắc lệnh áp dụng cho giá trị YAML thực tế, không tính nội dung chú thích."""
	if not isinstance(step, dict):
		error(path, f'cấu trúc {location} phải là object')
		return
	if 'uses' in step:
		checkActionRef(path, step['uses'], location)
	if 'run' not in step:
		return
	run = step['run']
	if not isinstance(run, str):
		error(path, f'cấu trúc {location}.run phải là chuỗi')
		return
	if '\n' in run.strip():
		error(
			path, f'{location}: lệnh nhiều dòng — tách thành script trong scripts/ (ADR 00000009)'
		)
	if '${{' in run:
		error(
			path,
			f'{location}: không viết ${{{{ … }}}} trong run: — truyền qua env: rồi dùng "$TÊN_BIẾN"',
		)
	shell = step.get('shell', '')
	if not isinstance(shell, str):
		error(path, f'cấu trúc {location}.shell phải là chuỗi')
		return
	if re.match(r'(python|node|pwsh|ruby|perl)', shell) or re.search(
		r'\b(python3?|node|ruby|perl|bash|sh)\s+-(c|e)\b', run
	):
		error(
			path,
			f'{location}: mã nhúng trong YAML — viết thành script trong scripts/ (ADR 00000009)',
		)


def checkWorkflow(path, text):
	"""Đọc cấu trúc YAML để kiểm tra action, lệnh, quyền và job; giữ kiểm tra cú pháp khối và chú thích."""
	workflow = loadYaml(path, dict)
	if workflow is None:
		return
	if 'permissions' not in workflow:
		error(path, 'thiếu khai báo "permissions" ở cấp workflow')
	if path.parent.parts[-2:] == ('.github', 'workflows') and '$default-branch' in text:
		error(
			path, '$default-branch chỉ dùng trong workflow-templates/ — ghi tên nhánh thật (main)'
		)
	# Cú pháp khối bị cấm dù chỉ chứa một lệnh; giữ số dòng. Giá trị đã giải mã do checkWorkflowStep kiểm tra.
	for number, line in enumerate(text.split('\n'), start=1):
		if re.match(r"^\s*(?:-\s+)?[\"']?run[\"']?:\s*[|>]", line):
			error(
				path,
				f'dòng {number}: lệnh nhiều dòng — tách thành script trong scripts/, mỗi bước gọi một lệnh (ADR 00000009)',
			)
		if re.match(r'^\s+[a-z-]+: write\s*$', line):
			error(path, f'dòng {number}: quyền ghi cần chú thích lý do (# …)')
	if 'concurrency' not in workflow:
		error(path, 'thiếu khai báo "concurrency" ở cấp workflow')
	top = workflow.get('permissions')
	if top == 'write-all' or (isinstance(top, dict) and 'write' in top.values()):
		error(path, 'quyền ghi chỉ cấp ở job cần dùng, không cấp ở cấp workflow')
	for name, job in workflowJobs(path).items():
		if 'timeout-minutes' not in job:
			error(path, f'job "{name}" thiếu timeout-minutes')
		if 'uses' in job:
			checkActionRef(path, job['uses'], f'job "{name}"')
		steps = job.get('steps', [])
		if not isinstance(steps, list):
			error(path, f'cấu trúc job "{name}".steps phải là danh sách')
			continue
		for index, step in enumerate(steps, start=1):
			checkWorkflowStep(path, step, f'job "{name}", bước {index}')


def checkWorkflowTemplate(path):
	properties = path.with_suffix('.properties.json')
	if not properties.exists():
		error(path, f'thiếu tệp {properties.name}')
		return
	try:
		meta = readJsonObject(properties)
	except json.JSONDecodeError as exc:
		error(properties, f'JSON không hợp lệ: {exc}')
		return
	for key in ('name', 'description'):
		if not meta.get(key):
			error(properties, f'thiếu khóa bắt buộc "{key}"')
	categories = configItems(properties, meta, 'categories', str)
	if not categories or categories[0] not in WORKFLOW_GENERAL_CATEGORIES:
		error(
			properties,
			'danh mục đầu tiên phải là danh mục chung của starter-workflows (ví dụ "Continuous integration")',
		)
	icon = meta.get('iconName')
	if icon and not (path.parent / f'{icon}.svg').exists():
		error(properties, f'không tìm thấy biểu tượng {icon}.svg')


def repositoryWorkflows():
	"""Workflow GitHub quản lý, nhận cả hai đuôi YAML; dùng danh sách tệp của lượt kiểm tra hiện tại."""
	folderParts = (ROOT / '.github' / 'workflows').parts
	return [
		path
		for path in trackedFiles()
		if path.name.endswith(('.yml', '.yaml')) and path.parts[:-1] == folderParts
	]
