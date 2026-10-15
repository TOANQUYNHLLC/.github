"""Biểu mẫu Issue, Discussion, báo cáo lỗ hổng riêng tư: cấu trúc, kiểu dữ liệu và cấu hình chọn biểu mẫu."""

import re

from validation.common import configField, configItems, error, loadYaml, readText
from validation.docs import checkAbsoluteLinks

FORM_TYPES = {'markdown', 'textarea', 'input', 'dropdown', 'checkboxes'}
# Khóa cấp cao nhất GitHub chấp nhận trong biểu mẫu Issue. `type` (Issue Type) có trong tài liệu nhưng GitHub
# từ chối: "type is not a permitted key" và không hiện biểu mẫu (xem scripts/check-github-forms.py).
ISSUE_FORM_KEYS = {'name', 'description', 'title', 'labels', 'assignees', 'projects', 'body'}
# Biểu mẫu Discussion chỉ nhận các khóa này ở cấp cao nhất (không có name, description như Issue).
DISCUSSION_FORM_KEYS = {'title', 'labels', 'body'}


FORM_LABELS = []
# Tên biểu mẫu Issue → tệp đầu tiên dùng tên đó; GitHub từ chối biểu mẫu trùng tên ("Name must be unique").
ISSUE_FORM_NAMES = {}


def checkForm(path, required=('name', 'description', 'body')):
	form = loadYaml(path, dict)
	if form is None:
		return
	for key in required:
		value = form.get(key) if key == 'body' else configField(path, form, key, str)
		if not value or (isinstance(value, str) and not value.strip()):
			error(path, f'thiếu khóa bắt buộc "{key}"')
	checkAbsoluteLinks(path, readText(path))
	if path.parent.name == 'DISCUSSION_TEMPLATE':
		for key in sorted(set(form) - DISCUSSION_FORM_KEYS, key=str):
			error(path, f'biểu mẫu Discussion không hỗ trợ khóa "{key}"')
	if path.parent.name == 'ISSUE_TEMPLATE':
		for key in sorted(set(form) - ISSUE_FORM_KEYS, key=str):
			error(path, f'khóa "{key}" không được GitHub chấp nhận trong biểu mẫu Issue')
		name = form.get('name')
		if isinstance(name, str) and name.strip():
			first = ISSUE_FORM_NAMES.setdefault(name, path)
			if first != path:
				error(
					path,
					f'name "{name}" trùng với {first.name} — GitHub yêu cầu tên biểu mẫu Issue khác nhau',
				)
	FORM_LABELS.extend((path, label) for label in configItems(path, form, 'labels', str))
	ids = set()
	for index, item in enumerate(configItems(path, form, 'body'), start=1):
		kind = item.get('type')
		attributes = configField(path, item, 'attributes', dict)
		if not isinstance(kind, str) or kind not in FORM_TYPES:
			error(path, f'phần tử {index}: type "{kind}" không hợp lệ')
			continue
		if kind == 'markdown':
			if not configField(path, attributes, 'value', str).strip():
				error(path, f'phần tử {index}: markdown thiếu value')
			continue
		label = configField(path, attributes, 'label', str)
		if not label.strip():
			error(path, f'phần tử {index}: thiếu label')
		elif label != label.upper():
			error(path, f'phần tử {index}: tiêu đề trường "{attributes["label"]}" phải viết hoa')
		# id không bắt buộc: chỉ so trùng giữa các trường có id.
		itemId = configField(path, item, 'id', str)
		if itemId and not re.fullmatch(r'[A-Za-z0-9_-]+', itemId):
			error(path, f'phần tử {index}: id "{itemId}" không hợp lệ')
		if itemId and itemId in ids:
			error(path, f'phần tử {index}: id "{itemId}" bị trùng')
		ids.add(itemId)
		checkValidations(
			path, configField(path, item, 'validations', dict), kind, f'phần tử {index}'
		)
		if kind in ('dropdown', 'checkboxes'):
			optionType = str if kind == 'dropdown' else dict
			options = configItems(path, attributes, 'options', optionType)
			if not options:
				error(path, f'phần tử {index}: {kind} thiếu options')
			labels = []
			for optionIndex, option in enumerate(options, start=1):
				label = option if kind == 'dropdown' else configField(path, option, 'label', str)
				if not label.strip():
					error(path, f'phần tử {index}: options[{optionIndex}] thiếu label không trống')
				if kind == 'checkboxes':
					checkValidations(path, option, kind, f'phần tử {index}, options[{optionIndex}]')
				labels.append(label)
			if len(labels) != len(set(labels)):
				error(path, f'phần tử {index}: options bị trùng')


def checkValidations(path, validations, kind, location):
	"""Giữ boolean của YAML và số nguyên min_length đúng kiểu mà GitHub yêu cầu."""
	if 'required' in validations and type(validations['required']) is not bool:
		error(path, f'{location}: required: phải là boolean')
	if 'min_length' in validations and (
		kind not in ('input', 'textarea')
		or type(validations['min_length']) is not int
		or validations['min_length'] < 0
	):
		error(path, f'{location}: min_length phải là số nguyên không âm cho input hoặc textarea')


def checkIssueConfig(path):
	config = loadYaml(path, dict)
	if config is None:
		return
	if 'blank_issues_enabled' in config and type(config['blank_issues_enabled']) is not bool:
		error(path, 'blank_issues_enabled: phải là boolean')
	for link in configItems(path, config, 'contact_links'):
		for key in ('name', 'url', 'about'):
			if not configField(path, link, key, str).strip():
				error(path, f'contact_links thiếu "{key}"')
