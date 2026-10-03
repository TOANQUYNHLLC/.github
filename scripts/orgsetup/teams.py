"""Lệnh team: team của tổ chức, thành viên và quyền trên repository."""

import json
from concurrent.futures import ThreadPoolExecutor

from orgsetup import github

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
	"""Vai trò của người dùng trong team (maintainer, member), None nếu chưa là thành viên."""
	try:
		return (
			github.ghJson('api', f'orgs/{github.ORG}/teams/{team}/memberships/{user}') or {}
		).get('role')
	except RuntimeError:
		return None


def teamPermission(team, repo):
	"""Quyền của team trên repository (read, triage, write, maintain, admin), None nếu chưa được cấp."""
	try:
		return (
			github.ghJson(
				'api',
				'-H',
				'Accept: application/vnd.github.v3.repository+json',
				f'orgs/{github.ORG}/teams/{team}/repos/{github.ORG}/{repo}',
			)
			or {}
		).get('role_name')
	except RuntimeError:
		return None


def teamDetails(team):
	"""Tên, mô tả, chế độ hiển thị của team trên GitHub."""
	return github.ghJson('api', f'orgs/{github.ORG}/teams/{team}') or {}


def teamState(team, repos):
	"""Trạng thái team trên GitHub: (đã có, mục khác web, người chưa là maintainer, repository thiếu quyền)."""
	name, permission, privacy, description = TEAMS[team]
	exists = github.ghExists(f'orgs/{github.ORG}/teams/{team}')
	details = teamDetails(team) if exists else {}
	wanted = {'name': name, 'description': description, 'privacy': privacy}
	drift = {key: value for key, value in wanted.items() if exists and details.get(key) != value}
	users = [user for user in MAINTAINERS if not exists or teamRole(team, user) != 'maintainer']
	# Không hạ quyền: admin đã bao gồm maintain, maintain bao gồm push…
	missing = [
		repo
		for repo in repos
		if not exists
		or PERMISSION_RANK.get(teamPermission(team, repo), -1) < PERMISSION_RANK[permission]
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
			github.gh(
				'api',
				'-X',
				'PUT',
				f'orgs/{github.ORG}/teams/{team}/memberships/{user}',
				'-f',
				'role=maintainer',
			)
			print(f'   ✔ thêm {user} (maintainer)')
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
