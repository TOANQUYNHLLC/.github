"""Biểu mẫu Issue, Discussion và cấu hình chọn biểu mẫu."""

from validation.common import configField, configItems, error, loadYaml, readText
from validation.docs import checkAbsoluteLinks

FORM_TYPES = {'markdown', 'textarea', 'input', 'dropdown', 'checkboxes'}
# Khóa cấp cao nhất GitHub chấp nhận trong biểu mẫu Issue. `type` (Issue Type) có trong tài liệu nhưng GitHub
# từ chối: "type is not a permitted key" và không hiện biểu mẫu (xem scripts/check-github-forms.py).
ISSUE_FORM_KEYS = {'name', 'description', 'title', 'labels', 'assignees', 'projects', 'body'}
# Biểu mẫu Discussion chỉ nhận các khóa này ở cấp cao nhất (không có name, description như Issue).
DISCUSSION_FORM_KEYS = {'title', 'labels', 'body'}


FORM_LABELS = []


def checkForm(path, required=('name', 'description', 'body')):
	form = loadYaml(path, dict)
	if form is None:
		return
	for key in required:
		if not form.get(key):
			error(path, f'thiếu khóa bắt buộc "{key}"')
	checkAbsoluteLinks(path, readText(path))
	if path.parent.name == 'DISCUSSION_TEMPLATE':
		for key in sorted(set(form) - DISCUSSION_FORM_KEYS):
			error(path, f'biểu mẫu Discussion không hỗ trợ khóa "{key}"')
	if path.parent.name == 'ISSUE_TEMPLATE':
		for key in sorted(set(form) - ISSUE_FORM_KEYS):
			error(path, f'khóa "{key}" không được GitHub chấp nhận trong biểu mẫu Issue')
	FORM_LABELS.extend((path, label) for label in configItems(path, form, 'labels', str))
	ids = set()
	for index, item in enumerate(configItems(path, form, 'body'), start=1):
		kind = item.get('type')
		attributes = configField(path, item, 'attributes', dict)
		if not isinstance(kind, str) or kind not in FORM_TYPES:
			error(path, f'phần tử {index}: type "{kind}" không hợp lệ')
			continue
		if kind == 'markdown':
			if not attributes.get('value'):
				error(path, f'phần tử {index}: markdown thiếu value')
			continue
		label = configField(path, attributes, 'label', str)
		if not label:
			error(path, f'phần tử {index}: thiếu label')
		elif label != label.upper():
			error(path, f'phần tử {index}: tiêu đề trường "{attributes["label"]}" phải viết hoa')
		# id không bắt buộc: chỉ so trùng giữa các trường có id.
		itemId = configField(path, item, 'id', str)
		if itemId and itemId in ids:
			error(path, f'phần tử {index}: id "{itemId}" bị trùng')
		ids.add(itemId)
		if kind in ('dropdown', 'checkboxes') and not attributes.get('options'):
			error(path, f'phần tử {index}: {kind} thiếu options')


def checkIssueConfig(path):
	config = loadYaml(path, dict)
	if config is None:
		return
	for link in configItems(path, config, 'contact_links'):
		for key in ('name', 'url', 'about'):
			if not link.get(key):
				error(path, f'contact_links thiếu "{key}"')
