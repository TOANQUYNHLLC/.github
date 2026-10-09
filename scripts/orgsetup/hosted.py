"""Khôi phục hosted runner pools bằng tên nhóm runner và image đã xác minh."""

import copy
import json
import re
from urllib.parse import quote

from orgsetup import github, resources

GROUP_PATH = 'actions/hosted-runners'
FIELDS = {
	'name',
	'runner_group',
	'image',
	'size',
	'maximum_runners',
	'enable_static_ip',
	'image_gen',
}


def validateGroup(items):
	if not isinstance(items, list):
		raise TypeError('Hosted runners phải là danh sách')
	names = set()
	for item in items:
		if (
			not isinstance(item, dict)
			or set(item) != FIELDS
			or not isinstance(item['name'], str)
			or not re.fullmatch(r'[A-Za-z0-9._-]{1,64}', item['name'])
		):
			raise ValueError('Hosted runner thiếu trường hoặc tên không hợp lệ')
		if (
			any(
				not isinstance(item[field], str) or not item[field]
				for field in ('runner_group', 'size')
			)
			or type(item['maximum_runners']) is not int
			or item['maximum_runners'] < 1
			or any(type(item[field]) is not bool for field in ('enable_static_ip', 'image_gen'))
		):
			raise ValueError('Hosted runner có cấu hình sai kiểu hoặc giới hạn không hợp lệ')
		image = item['image']
		if not isinstance(image, dict) or image.get('source') not in (
			'github',
			'partner',
			'custom',
		):
			raise ValueError('Hosted runner thiếu image source')
		identityField = 'name' if image['source'] == 'custom' else 'id'
		if (
			set(image)
			!= {'source', identityField, *(['version'] if image['source'] == 'custom' else [])}
			or not isinstance(image[identityField], str)
			or not image[identityField]
		):
			raise ValueError('Hosted runner thiếu định danh image; custom image dùng tên')
		if image['source'] == 'custom' and not isinstance(image['version'], (str, type(None))):
			raise ValueError('Hosted runner có image version sai kiểu')
		if item['name'] in names:
			raise ValueError('Hosted runner trùng tên')
		names.add(item['name'])
	return items


def customImages(base):
	images = resources.readCollection(f'{base}/{GROUP_PATH}/images/custom', 'images')
	result = {}
	for item in images:
		if (
			not isinstance(item, dict)
			or not isinstance(item.get('name'), str)
			or not item['name']
			or type(item.get('id')) is not int
			or item['id'] <= 0
			or item['name'] in result
			or str(item['id']) in result.values()
		):
			raise ValueError('Danh mục custom image thiếu danh tính hoặc trùng')
		result[item['name']] = str(item['id'])
	return result


def readDetails(base):
	if base != f'orgs/{github.ORG}':
		raise ValueError('Hosted runners chỉ hỗ trợ tổ chức đã khai báo')
	items = resources.readCollection(f'{base}/{GROUP_PATH}', 'runners')
	if not items:
		return [], {}
	groups = resources.runnerGroupDetails()
	groupNames = {item['id']: name for name, item in groups.items()}
	result, ids, images = [], {}, None
	for item in items:
		if (
			not isinstance(item, dict)
			or type(item.get('id')) is not int
			or item['id'] < 1
			or item['id'] in ids.values()
		):
			raise ValueError('Hosted runner thiếu ID hoặc trùng ID')
		image, size = item.get('image_details'), item.get('machine_size_details')
		if (
			not isinstance(image, dict)
			or not isinstance(size, dict)
			or item.get('runner_group_id') not in groupNames
			or not isinstance(image.get('id'), str)
			or not image['id']
		):
			raise ValueError('Hosted runner thiếu image, size hoặc nhóm runner')
		if item.get('status') not in ('Ready', 'Shutdown'):
			raise ValueError(
				'Hosted runner chưa sẵn sàng, đang lỗi/xóa hoặc trạng thái chưa xác minh'
			)
		value = {field: item[field] for field in ('name', 'maximum_runners', 'image_gen')}
		value.update(
			runner_group=groupNames[item['runner_group_id']],
			size=size['id'],
			enable_static_ip=item['public_ip_enabled'],
			image={'id': image['id'], 'source': image['source']},
		)
		if image['source'] == 'custom':
			if images is None:
				images = customImages(base)
			names = [name for name, resourceId in images.items() if resourceId == image['id']]
			if len(names) != 1 or 'version' not in image:
				raise ValueError('Hosted runner chưa xác minh được tên/phiên bản custom image')
			value['image'] = {'name': names[0], 'source': 'custom', 'version': image['version']}
		ids[value['name']] = item['id']
		result.append(value)
	return validateGroup(result), ids


def collectionChanges(plan, base, current, targets, resourceCache):
	validateGroup(targets)
	present = {item['name']: item for item in current}
	changed = [item for item in targets if present.get(item['name']) != item]
	if not changed:
		return
	latest, ids = readDetails(base)
	if {item['name']: item for item in latest} != present:
		raise ValueError('Hosted runners thay đổi trong lúc đọc')
	groups = resources.runnerGroupDetails()
	planned = resourceCache.get('planned_runner_groups', set())
	sizes = resources.readCollection(f'{base}/{GROUP_PATH}/machine-sizes', 'machine_specs')
	for target in changed:
		if target['runner_group'] not in groups and target['runner_group'] not in planned:
			raise ValueError('Hosted runner cần nhóm runner có sẵn hoặc trong cùng kế hoạch')
		if target['size'] not in {item.get('id') for item in sizes if isinstance(item, dict)}:
			raise ValueError('Hosted runner dùng machine size không còn khả dụng')
		image = copy.deepcopy(target['image'])
		if image['source'] == 'custom':
			images = customImages(base)
			if image['name'] not in images:
				raise ValueError('Hosted runner cần custom image được tạo sẵn')
			imageId = images[image['name']]
			if image['version'] is not None:
				version = github.ghJson(
					'api',
					f'{base}/{GROUP_PATH}/images/custom/{imageId}/versions/{quote(image["version"], safe="")}',
				)
				if (
					not isinstance(version, dict)
					or version.get('version') != image['version']
					or version.get('state') != 'Ready'
				):
					raise ValueError('Hosted runner chưa có custom image version sẵn sàng')
		else:
			available = resources.readCollection(
				f'{base}/{GROUP_PATH}/images/{"github-owned" if image["source"] == "github" else "partner"}',
				'images',
			)
			if image['id'] not in {item.get('id') for item in available if isinstance(item, dict)}:
				raise ValueError('Hosted runner dùng image không còn khả dụng')
		body = copy.deepcopy(target)
		# Giữ tên cho bước ghi; nhóm/custom image có thể vừa được tạo, không dùng ID của snapshot.
		path = f'{base}/{GROUP_PATH}'
		method = 'POST'
		if target['name'] in ids:
			path += f'/{ids[target["name"]]}'
			method = 'PATCH'
		plan.append((path, method, body, {'hosted_runner': target['name']}))


def resolvePlanBody(base, body, method):
	result = copy.deepcopy(body)
	groups = resources.runnerGroupDetails()
	name = result.pop('runner_group')
	if name not in groups:
		raise ValueError('Không xác minh được ID nhóm trước khi ghi hosted runner')
	result['runner_group_id'] = groups[name]['id']
	image = result['image']
	if image['source'] == 'custom':
		images = customImages(base)
		name = image.pop('name')
		if name not in images:
			raise ValueError('Không xác minh được custom image trước khi ghi hosted runner')
		image['id'] = images[name]
	if method == 'PATCH':
		result.pop('image')
		result.update(image_source=image['source'], image_id=image['id'])
		if 'version' in image:
			result['image_version'] = image['version']
	return result


def validateResponse(response, name):
	data = json.loads(response)
	if (
		not isinstance(data, dict)
		or data.get('name') != name
		or type(data.get('id')) is not int
		or data['id'] <= 0
	):
		raise ValueError('API chưa xác nhận hosted runner vừa gửi')
	if data.get('status') != 'Ready':
		raise ValueError(
			'Hosted runner chưa sẵn sàng; xem trước lại sau khi GitHub triển khai xong'
		)
