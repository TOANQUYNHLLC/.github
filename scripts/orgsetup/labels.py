"""Lệnh labels: đồng bộ bộ nhãn chuẩn trong labels.yml."""

import json
import re
import subprocess
import urllib.parse

from orgsetup import github

LABELS_FILE = github.ROOT / 'labels.yml'


def inspectLabels(data):
	"""Tên không phân biệt hoa/thường và lỗi schema nhãn; dùng chung cho validator và lệnh đồng bộ."""
	names, problems = set(), []
	if not isinstance(data, list):
		return names, ['phải là danh sách nhãn']
	for index, label in enumerate(data, start=1):
		prefix = f'nhãn {index}'
		if not isinstance(label, dict):
			problems.append(f'{prefix}: phải là object')
			continue
		name = label.get('name')
		if not isinstance(name, str) or not name.strip():
			problems.append(f'{prefix}: name phải là chuỗi không trống')
		else:
			prefix = f'nhãn "{name}"'
			if name.lower() in names:
				problems.append(f'{prefix} bị trùng')
			names.add(name.lower())
		color = label.get('color')
		if not isinstance(color, str) or not re.fullmatch(r'[0-9a-fA-F]{6}', color):
			problems.append(f'{prefix}: color phải là mã hex 6 ký tự dạng chuỗi')
		description = label.get('description', '')
		if not isinstance(description, str):
			problems.append(f'{prefix}: description phải là chuỗi')
		elif len(description) > 100:
			problems.append(f'{prefix}: description vượt quá 100 ký tự')
	return names, problems


def loadLabels():
	"""Nhãn chuẩn trong labels.yml (đọc YAML bằng Ruby như validate.py — Python không có sẵn thư viện YAML)."""
	result = subprocess.run(
		[
			'ruby',
			'-ryaml',
			'-rjson',
			'-e',
			'puts JSON.dump(YAML.safe_load(File.read(ARGV[0]), aliases: true, filename: ARGV[0]))',
			str(LABELS_FILE),
		],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode != 0:
		detail = (
			result.stderr.strip().splitlines()[0]
			if result.stderr.strip()
			else 'Ruby không đọc được tệp'
		)
		raise ValueError(f'{LABELS_FILE.name}: YAML không hợp lệ ({detail})')
	data = json.loads(result.stdout)
	_, problems = inspectLabels(data)
	if problems:
		raise ValueError(f'{LABELS_FILE.name}: {"; ".join(problems)}')
	return data


def readLabels(repo):
	"""Đọc đủ nhãn và kiểm tra phản hồi trước khi tính thay đổi; description null của API là chuỗi rỗng."""
	data = github.ghList(f'repos/{github.ORG}/{repo}/labels')
	normalized = []
	for index, label in enumerate(data, start=1):
		if not isinstance(label, dict) or 'description' not in label:
			raise ValueError(f'{repo}: nhãn {index} thiếu trường trong phản hồi GitHub')
		normalized.append(
			{**label, 'description': '' if label['description'] is None else label['description']}
		)
	_, problems = inspectLabels(normalized)
	if problems:
		raise ValueError(f'{repo}: phản hồi nhãn không hợp lệ ({"; ".join(problems)})')
	return {label['name'].lower(): label for label in normalized}


def syncLabels(repos, apply):
	"""Tạo hoặc cập nhật nhãn chuẩn khác với labels.yml (kể cả tên chỉ khác chữ hoa/thường); không xóa nhãn riêng
	của repository."""
	wanted = loadLabels()
	for repo in repos:
		print(f'== {github.ORG}/{repo}')
		current = readLabels(repo)
		changes = []
		for label in wanted:
			# GitHub tra tên nhãn không phân biệt hoa/thường: "stable" đã có thì không tạo được "Stable" — so cả
			# cách viết để đổi tên cho đúng labels.yml.
			live = current.get(label['name'].lower())
			if (
				live is None
				or live['name'] != label['name']
				or live['color'].lower() != label['color'].lower()
				or (live.get('description') or '') != (label.get('description') or '')
			):
				changes.append((label, live['name'] if live else None))
		if not changes:
			print(f'   ✔ đủ {len(wanted)} nhãn chuẩn')
			continue
		for label, liveName in changes:
			if liveName is None:
				action = 'tạo'
			elif liveName != label['name']:
				action = f'đổi tên "{liveName}" →'
			else:
				action = 'cập nhật'
			if not apply:
				print(f'   (xem trước) {action} nhãn "{label["name"]}"')
				continue
			description = label.get('description') or ''
			if liveName is None:
				github.gh(
					'label',
					'create',
					label['name'],
					'--repo',
					f'{github.ORG}/{repo}',
					'--color',
					label['color'],
					'--description',
					description,
				)
			else:
				# PATCH theo tên đang có (mã hóa cả "/", ":" như ui/ux, area: api); new_name đổi được cả chữ hoa/thường.
				github.gh(
					'api',
					'-X',
					'PATCH',
					f'repos/{github.ORG}/{repo}/labels/{urllib.parse.quote(liveName, safe="")}',
					'-f',
					f'new_name={label["name"]}',
					'-f',
					f'color={label["color"]}',
					'-f',
					f'description={description}',
					'--silent',
				)
			print(f'   ✔ {action} nhãn "{label["name"]}"')
	# Nhãn mặc định cho repository tạo mới (Organization settings) không có API: lệnh này chỉ đồng bộ repository đã
	# có — nhắc để người quản trị không tưởng trang đó cũng đã đồng bộ.
	print(
		'– Nhãn mặc định cho repository mới (Organization settings → Repository labels) không đồng bộ được '
		'qua API: nhập trên web theo labels.yml (xem ROADMAP.md).'
	)
