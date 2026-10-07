"""Cài đặt tài nguyên Actions: nhóm runner và danh sách Apps để đối chiếu khi khôi phục."""

import re

from orgsetup import github

RUNNER_SETTINGS = {
	'name': str,
	'visibility': ('all', 'private', 'selected'),
	'allows_public_repositories': bool,
	'restricted_to_workflows': bool,
	'selected_workflows': list,
}
RUNNER_METADATA = ('default', 'inherited', 'workflow_restrictions_read_only')


def readCollection(endpoint, key):
	"""Đọc mọi trang object chứa total_count; trang thiếu/sai hoặc tổng thay đổi không trả dữ liệu thiếu."""
	separator = '&' if '?' in endpoint else '?'
	pages = github.ghJson('api', '--paginate', '--slurp', f'{endpoint}{separator}per_page=100')
	if not isinstance(pages, list) or not pages:
		raise ValueError(f'{endpoint}: không đọc được các trang dữ liệu')
	items, total = [], None
	for page in pages:
		if (
			not isinstance(page, dict)
			or type(page.get('total_count')) is not int
			or page['total_count'] < 0
			or not isinstance(page.get(key), list)
		):
			raise ValueError(f'{endpoint}: dữ liệu phân trang không hợp lệ')
		if total is not None and total != page['total_count']:
			raise ValueError(f'{endpoint}: tổng tài nguyên thay đổi trong lúc đọc')
		total = page['total_count']
		items.extend(page[key])
	if len(items) != total:
		raise ValueError(f'{endpoint}: chưa đọc đủ tài nguyên')
	return items


def installedApps():
	"""Chỉ lưu app_slug công khai; không ghi ID, tài khoản cài đặt hay credentials của Apps."""
	items = readCollection(f'orgs/{github.ORG}/installations', 'installations')
	if any(
		not isinstance(item, dict)
		or not isinstance(item.get('app_slug'), str)
		or not item['app_slug']
		for item in items
	):
		raise ValueError('Không đọc được tên GitHub Apps đã cài')
	return sorted({item['app_slug'] for item in items})


def validateRunnerGroups(groups):
	"""Hợp đồng tệp local: settings có thể ghi, metadata chỉ so; tên repository thay cho ID không khả chuyển."""
	if not isinstance(groups, list):
		raise TypeError('runner_groups phải là danh sách')
	names = set()
	for group in groups:
		if not isinstance(group, dict) or set(group) != {
			'settings',
			'selected_repositories',
			*RUNNER_METADATA,
		}:
			raise ValueError('Cấu trúc nhóm runner không hợp lệ')
		settings = group['settings']
		if not isinstance(settings, dict) or set(settings) != set(RUNNER_SETTINGS):
			raise ValueError('Nhóm runner thiếu trường hoặc có trường không được hỗ trợ')
		for key, expected in RUNNER_SETTINGS.items():
			value = settings[key]
			if isinstance(expected, tuple):
				valid = isinstance(value, str) and value in expected
			else:
				valid = type(value) is expected
			if not valid:
				raise ValueError(f'Nhóm runner: giá trị {key} không hợp lệ')
		if not settings['name'] or settings['name'] in names:
			raise ValueError('Nhóm runner trùng tên hoặc thiếu tên')
		names.add(settings['name'])
		if any(type(group[key]) is not bool for key in RUNNER_METADATA):
			raise ValueError('Metadata nhóm runner phải là boolean')
		for key, values in (
			('selected_repositories', group['selected_repositories']),
			('selected_workflows', settings['selected_workflows']),
		):
			if (
				not isinstance(values, list)
				or any(not isinstance(value, str) or not value for value in values)
				or len(values) != len(set(values))
			):
				raise ValueError(f'Nhóm runner: danh sách {key} không hợp lệ')
		if any(
			not re.fullmatch(rf'{re.escape(github.ORG)}/[A-Za-z0-9_.-]+', value)
			or value.split('/')[-1] in ('.', '..')
			for value in group['selected_repositories']
		):
			raise ValueError('Nhóm runner có repository ngoài tổ chức')
		if settings['visibility'] != 'selected' and group['selected_repositories']:
			raise ValueError('Nhóm runner chỉ khai báo repository riêng khi visibility=selected')
	return groups


def runnerGroupDetails():
	"""Đọc ID để gửi API; loại thông tin này ra khỏi tệp nguồn local."""
	items = readCollection(f'orgs/{github.ORG}/actions/runner-groups', 'runner_groups')
	result = {}
	for item in items:
		if (
			not isinstance(item, dict)
			or type(item.get('id')) is not int
			or item['id'] < 1
			or not isinstance(item.get('name'), str)
			or not item['name']
			or item['name'] in result
		):
			raise ValueError('Danh sách nhóm runner thiếu ID hoặc trùng tên')
		result[item['name']] = item
	return result


def readRunnerGroups():
	groups = []
	for item in runnerGroupDetails().values():
		group = {
			'settings': {key: item[key] for key in RUNNER_SETTINGS if key in item},
			**{key: item[key] for key in RUNNER_METADATA if key in item},
			'selected_repositories': [],
		}
		if item.get('visibility') == 'selected':
			repositories = readCollection(
				f'orgs/{github.ORG}/actions/runner-groups/{item["id"]}/repositories', 'repositories'
			)
			if any(
				not isinstance(repo, dict) or not isinstance(repo.get('full_name'), str)
				for repo in repositories
			):
				raise ValueError('Nhóm runner: danh sách repository không hợp lệ')
			group['selected_repositories'] = sorted(repo['full_name'] for repo in repositories)
		groups.append(group)
	validateRunnerGroups(groups)
	return sorted(groups, key=lambda group: group['settings']['name'])


def repositoryIds(names):
	"""Giải full_name thành ID hiện tại; API đọc metadata không nhận URL do tệp local tùy ý cung cấp."""
	items = github.ghList(f'orgs/{github.ORG}/repos?type=all')
	lookup = {}
	for item in items:
		if (
			not isinstance(item, dict)
			or not isinstance(item.get('full_name'), str)
			or type(item.get('id')) is not int
			or item['id'] < 1
			or item['full_name'] in lookup
		):
			raise ValueError('Không đọc được ID các repository của tổ chức')
		lookup[item['full_name']] = item['id']
	if any(name not in lookup for name in names):
		raise ValueError('Nhóm runner chọn repository chưa có hoặc tài khoản chưa đọc được')
	return [lookup[name] for name in names]


def runnerGroupChanges(plan, current, wanted):
	"""Tạo/cập nhật nhóm trong nguồn; xác minh mọi trường và metadata trước khi lập lệnh ghi."""
	validateRunnerGroups(current)
	validateRunnerGroups(wanted)
	present = {group['settings']['name']: group for group in current}
	details = None
	for target in wanted:
		name, settings = target['settings']['name'], target['settings']
		group = present.get(name)
		if group == target:
			continue
		if group is None:
			if any(target[key] for key in RUNNER_METADATA):
				raise ValueError(
					f'Nhóm runner {name}: nhóm mặc định/kế thừa phải tồn tại trước khi áp dụng'
				)
			body = dict(settings)
			if settings['visibility'] == 'selected':
				body['selected_repository_ids'] = repositoryIds(target['selected_repositories'])
			plan.append(
				(f'orgs/{github.ORG}/actions/runner-groups', 'POST', body, {'runner_group': name})
			)
			continue
		if any(group[key] != target[key] for key in RUNNER_METADATA) or group['inherited']:
			raise ValueError(f'Nhóm runner {name}: metadata khác hoặc nhóm do enterprise quản lý')
		if group['workflow_restrictions_read_only'] and any(
			group['settings'][key] != settings[key]
			for key in ('restricted_to_workflows', 'selected_workflows')
		):
			raise ValueError(f'Nhóm runner {name}: không có quyền sửa giới hạn workflow')
		if details is None:
			details = runnerGroupDetails()
		if name not in details:
			raise ValueError(f'Nhóm runner {name}: tài nguyên đổi trong lúc đọc')
		endpoint = f'orgs/{github.ORG}/actions/runner-groups/{details[name]["id"]}'
		changes = {key: value for key, value in settings.items() if group['settings'][key] != value}
		if changes:
			plan.append((endpoint, 'PATCH', dict(changes, name=name), changes))
		if settings['visibility'] == 'selected' and (
			group['settings']['visibility'] != 'selected'
			or sorted(group['selected_repositories']) != sorted(target['selected_repositories'])
		):
			body = {'selected_repository_ids': repositoryIds(target['selected_repositories'])}
			plan.append(
				(
					f'{endpoint}/repositories',
					'PUT',
					body,
					{'selected_repositories': target['selected_repositories']},
				)
			)
