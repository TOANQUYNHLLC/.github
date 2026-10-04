"""Lệnh team: team của tổ chức, thành viên và quyền trên repository."""

import json
from concurrent.futures import ThreadPoolExecutor

from orgsetup import github

MAINTAINERS = ('nguyentrongtoandl', 'trongtoandl81')

# Team ghi trong CODEOWNERS.
TEAM = 'maintainers'

# Team của tổ chức: slug → (tên, quyền trên mọi repository, hiển thị, mô tả
# khi tạo). Mọi team gồm mọi người trong MAINTAINERS với vai trò maintainer.
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
		'Duy trì repository, quản lý phát hành và kiểm duyệt Pull Request.',
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
	"""Tên, mô tả, chế độ hiển thị của team trên GitHub."""
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
	return data


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
	# Đọc trạng thái các team song song — mỗi team vài lượt gọi gh, tuần tự thì hơn 20 giây; ghi vẫn tuần tự.
	with ThreadPoolExecutor(max_workers=len(TEAMS)) as pool:
		states = list(pool.map(lambda team: teamState(team, repos), TEAMS))
	for (team, (name, permission, privacy, description)), state in zip(
		TEAMS.items(), states, strict=True
	):
		exists, details, drift, users, missing = state
		print(f'== team {github.ORG}/{team}: {"đã có" if exists else "chưa có"}')
		if not users and not missing and not drift:
			print(f'   ✔ đủ người quản trị, team có quyền {permission} {len(repos)} repository')
			continue
		for key, value in drift.items():
			print(f'   {"" if apply else "(xem trước) "}{key}: {details.get(key)} → {value}')
		if drift and apply:
			body = json.dumps(drift, ensure_ascii=False)
			github.gh(
				'api', '-X', 'PATCH', f'orgs/{github.ORG}/teams/{team}', '--input', '-', stdin=body
			)
		if not apply:
			if not exists:
				print(f'   (xem trước) tạo team {name} ({privacy})')
			for user in users:
				print(f'   (xem trước) thêm {user} (maintainer)')
			for repo in missing:
				print(f'   (xem trước) cấp {permission} {github.ORG}/{repo}')
			continue
		if not exists:
			github.gh(
				'api',
				f'orgs/{github.ORG}/teams',
				'-f',
				f'name={name}',
				'-f',
				f'privacy={privacy}',
				'-f',
				f'description={description}',
			)
		for user in users:
			data = github.ghJson(
				'api',
				'-X',
				'PUT',
				f'orgs/{github.ORG}/teams/{team}/memberships/{user}',
				'-f',
				'role=maintainer',
			)
			role, state = membershipState(data, f'{team}/{user}')
			if state == 'pending':
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
