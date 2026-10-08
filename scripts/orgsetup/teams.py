"""Lệnh team: team của tổ chức, thành viên và quyền trên repository."""

import json
from concurrent.futures import ThreadPoolExecutor

from orgsetup import github

MAINTAINERS = ('nguyentrongtoandl', 'trongtoandl81')

# Team ghi trong CODEOWNERS.
TEAM = 'maintainers'

# Team của tổ chức: slug → (tên, quyền trên mọi repository, hiển thị, mô tả
# khi tạo). Quyền None: chỉ quản lý thông tin và cấu trúc, giữ nguyên thành viên và quyền.
TEAMS = {
	'engineering': (
		'Engineering',
		None,
		'closed',
		'Phát triển, kiểm thử và duy trì các sản phẩm phần mềm.',
	),
	'creative': (
		'Creative',
		None,
		'closed',
		'Thiết kế sản phẩm, thương hiệu và nội dung truyền thông.',
	),
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
		'Duy trì repository, quản lý phát hành và kiểm duyệt Pull Request.',
	),
	'developers': ('Developers', 'push', 'closed', 'Phát triển, review và duy trì mã nguồn.'),
	'qa': ('QA', 'triage', 'closed', 'Quản lý issue, kiểm thử, xác nhận lỗi.'),
	'design': ('Design', 'triage', 'closed', 'Thiết kế UI/UX, góp ý sản phẩm.'),
	'marketing': ('Marketing', 'pull', 'closed', 'Website, bài viết, hình ảnh truyền thông.'),
}

# Slug team cha; team không có trong bảng này nằm ở cấp cao nhất.
TEAM_PARENTS = {
	TEAM: 'engineering',
	'developers': 'engineering',
	'qa': 'engineering',
	'design': 'creative',
	'marketing': 'creative',
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


def teamRole(team, user):
	"""Vai trò của người dùng trong team; None chỉ khi HTTP 404, lỗi đọc khác phải dừng trước khi ghi."""
	try:
		role, state = membershipState(
			github.ghJson('api', f'orgs/{github.ORG}/teams/{team}/memberships/{user}'),
			f'{team}/{user}',
		)
		if state == 'pending':
			raise RuntimeError(
				f'{team}/{user}: chờ chấp nhận lời mời vào team — chưa có thành viên hoạt động'
			)
		return role
	except RuntimeError as exc:
		if github.isNotFound(exc):
			return None
		raise


def membershipState(data, location):
	"""Vai trò và trạng thái lời mời phải đọc được; không coi phản hồi thiếu trường là chưa có thành viên."""
	if (
		not isinstance(data, dict)
		or data.get('role') not in ('member', 'maintainer')
		or data.get('state') not in ('active', 'pending')
	):
		raise RuntimeError(f'{location}: không đọc được vai trò hoặc trạng thái thành viên team')
	return data['role'], data['state']


def teamPermission(team, repo):
	"""Quyền của team trên repository; None chỉ khi HTTP 404, lỗi đọc khác phải dừng trước khi ghi."""
	try:
		data = github.ghJson(
			'api',
			'-H',
			'Accept: application/vnd.github.v3.repository+json',
			f'orgs/{github.ORG}/teams/{team}/repos/{github.ORG}/{repo}',
		)
		if (
			not isinstance(data, dict)
			or not isinstance(data.get('role_name'), str)
			or data['role_name'] not in PERMISSION_RANK
		):
			raise RuntimeError(
				f'{team}/{repo}: không xếp được quyền team — kiểm tra quyền tùy chỉnh hoặc phản hồi GitHub, giữ nguyên quyền trên repository'
			)
		return data['role_name']
	except RuntimeError as exc:
		if github.isNotFound(exc):
			return None
		raise


def teamDetails(team):
	"""Tên, mô tả, chế độ hiển thị và team cha trên GitHub."""
	data = github.ghJson('api', f'orgs/{github.ORG}/teams/{team}')
	if (
		not isinstance(data, dict)
		or not isinstance(data.get('name'), str)
		or not data['name']
		or data.get('privacy') not in ('secret', 'closed')
		or 'description' not in data
		or not isinstance(data.get('description'), (str, type(None)))
	):
		raise RuntimeError(f'{team}: không đọc được tên, chế độ hiển thị hoặc mô tả team')
	parentSlug(data, team)
	return data


def parentSlug(details, team):
	"""Không coi trường parent bị thiếu hoặc sai kiểu là team ở cấp cao nhất."""
	if 'parent' not in details:
		raise RuntimeError(f'{team}: không đọc được team cha')
	parent = details['parent']
	if parent is None:
		return None
	if (
		not isinstance(parent, dict)
		or not isinstance(parent.get('slug'), str)
		or not parent['slug']
	):
		raise RuntimeError(f'{team}: không đọc được slug của team cha')
	return parent['slug']


def teamOrder():
	"""Kiểm tra cấu trúc local và xếp team cha trước team con, không phụ thuộc thứ tự khai báo."""
	if set(TEAM_PARENTS) - set(TEAMS):
		raise ValueError('TEAM_PARENTS chứa team con chưa khai báo trong TEAMS')
	ordered, visiting = [], set()

	def visit(team):
		if team in visiting:
			raise ValueError(f'{team}: cấu trúc team có chu trình')
		if team in ordered:
			return
		visiting.add(team)
		parent = TEAM_PARENTS.get(team)
		if parent is not None:
			if not isinstance(parent, str) or parent not in TEAMS:
				raise ValueError(f'{team}: team cha chưa khai báo trong TEAMS')
			if TEAMS[team][2] != 'closed' or TEAMS[parent][2] != 'closed':
				raise ValueError(f'{team}: team cha và team con phải có privacy closed')
			visit(parent)
		visiting.remove(team)
		ordered.append(team)

	for team in TEAMS:
		visit(team)
	return ordered


def teamState(team, repos):
	"""Trạng thái team trên GitHub: (đã có, mục khác web, người chưa là maintainer, repository thiếu quyền)."""
	name, permission, privacy, description = TEAMS[team]
	# Đọc chi tiết team cũng cho biết team đã có chưa (không có thì gh báo lỗi 404).
	try:
		details, exists = teamDetails(team), True
	except RuntimeError as exc:
		if not github.isNotFound(exc):
			raise
		details, exists = {}, False
	wanted = {'name': name, 'description': description, 'privacy': privacy}
	drift = {key: value for key, value in wanted.items() if exists and details.get(key) != value}
	if exists and parentSlug(details, team) != TEAM_PARENTS.get(team):
		drift['parent_team_slug'] = TEAM_PARENTS.get(team)
	if permission is None:
		return exists, details, drift, [], []
	if not exists:
		return exists, details, drift, list(MAINTAINERS), list(repos)
	# Vai trò từng người, quyền trên từng repository đọc cùng lúc — mỗi lần chờ GitHub gần một giây.
	with ThreadPoolExecutor(max_workers=len(MAINTAINERS) + len(repos)) as pool:
		roles = pool.map(lambda user: teamRole(team, user), MAINTAINERS)
		permissions = pool.map(lambda repo: teamPermission(team, repo), repos)
		users = [
			user for user, role in zip(MAINTAINERS, roles, strict=True) if role != 'maintainer'
		]
		# Không hạ quyền: admin đã bao gồm maintain, maintain bao gồm push…
		missing = [
			repo
			for repo, current in zip(repos, permissions, strict=True)
			if PERMISSION_RANK.get(current, -1) < PERMISSION_RANK[permission]
		]
	return exists, details, drift, users, missing


def syncTeams(repos, apply):
	ordered = teamOrder()
	# Đọc trạng thái các team song song — mỗi team vài lượt gọi gh, tuần tự thì hơn 20 giây; ghi vẫn tuần tự.
	with ThreadPoolExecutor(max_workers=len(TEAMS)) as pool:
		states = list(pool.map(lambda team: teamState(team, repos), ordered))
	for team, state in zip(ordered, states, strict=True):
		name, permission, privacy, description = TEAMS[team]
		exists, details, drift, users, missing = state
		print(f'== team {github.ORG}/{team}: {"đã có" if exists else "chưa có"}')
		if exists and not users and not missing and not drift:
			if permission is None:
				print('   ✔ thông tin và cấu trúc team đã đúng; giữ nguyên thành viên và quyền')
			else:
				print(f'   ✔ đủ người quản trị, team có quyền {permission} {len(repos)} repository')
			continue
		for key, value in drift.items():
			current = parentSlug(details, team) if key == 'parent_team_slug' else details.get(key)
			print(f'   {"" if apply else "(xem trước) "}{key}: {current} → {value}')
		if drift and apply:
			body = json.dumps(drift, ensure_ascii=False)
			github.gh(
				'api', '-X', 'PATCH', f'orgs/{github.ORG}/teams/{team}', '--input', '-', stdin=body
			)
		if not apply:
			if not exists:
				print(f'   (xem trước) tạo team {name} ({privacy})')
				if parent := TEAM_PARENTS.get(team):
					print(f'   (xem trước) đặt team cha {parent}')
			for user in users:
				print(f'   (xem trước) thêm {user} (maintainer)')
			for repo in missing:
				print(f'   (xem trước) cấp {permission} {github.ORG}/{repo}')
			continue
		if not exists:
			body = {'name': name, 'privacy': privacy, 'description': description}
			if parent := TEAM_PARENTS.get(team):
				body['parent_team_slug'] = parent
			github.gh(
				'api',
				'-X',
				'POST',
				f'orgs/{github.ORG}/teams',
				'--input',
				'-',
				stdin=json.dumps(body, ensure_ascii=False),
			)
		if (not exists or 'parent_team_slug' in drift) and parentSlug(
			teamDetails(team), team
		) != TEAM_PARENTS.get(team):
			raise RuntimeError(f'{team}: GitHub chưa áp dụng đúng team cha')
		for user in users:
			data = github.ghJson(
				'api',
				'-X',
				'PUT',
				f'orgs/{github.ORG}/teams/{team}/memberships/{user}',
				'-f',
				'role=maintainer',
			)
			role, membership = membershipState(data, f'{team}/{user}')
			if membership == 'pending':
				print(f'   ⚠ {user}: chờ chấp nhận lời mời vào team {team}')
			elif role == 'maintainer':
				print(f'   ✔ thêm {user} (maintainer)')
			else:
				raise RuntimeError(f'{team}/{user}: GitHub chưa cấp vai trò maintainer')
		for repo in missing:
			github.gh(
				'api',
				'-X',
				'PUT',
				f'orgs/{github.ORG}/teams/{team}/repos/{github.ORG}/{repo}',
				'-f',
				f'permission={permission}',
			)
			print(f'   ✔ {permission} {github.ORG}/{repo}')
	if apply:
		print(
			f'   CODEOWNERS dùng @{github.ORG}/{TEAM}; đổi thành viên thì cập nhật MAINTAINERS.md và MAINTAINERS trong scripts/orgsetup/teams.py.'
		)
