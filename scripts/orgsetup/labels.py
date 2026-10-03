"""Lệnh labels: đồng bộ bộ nhãn chuẩn trong labels.yml."""

import json
import subprocess

from orgsetup import github

LABELS_FILE = github.ROOT / 'labels.yml'


def loadLabels():
	"""Nhãn chuẩn trong labels.yml (đọc YAML bằng Ruby như validate.py — Python không có sẵn thư viện YAML)."""
	output = subprocess.run(
		[
			'ruby',
			'-ryaml',
			'-rjson',
			'-e',
			'puts JSON.dump(YAML.load_file(ARGV[0]))',
			str(LABELS_FILE),
		],
		capture_output=True,
		text=True,
		check=True,
	).stdout
	return json.loads(output)


def syncLabels(repos, apply):
	"""Tạo hoặc cập nhật nhãn chuẩn khác với labels.yml; không xóa nhãn riêng của repository."""
	wanted = loadLabels()
	for repo in repos:
		print(f'== {github.ORG}/{repo}')
		current = {
			label['name'].lower(): label
			for label in github.ghJson(
				'label',
				'list',
				'--repo',
				f'{github.ORG}/{repo}',
				'--limit',
				'500',
				'--json',
				'name,color,description',
			)
			or []
		}
		changes = []
		for label in wanted:
			live = current.get(str(label['name']).lower())
			if (
				live is None
				or live['color'].lower() != str(label['color']).lower()
				or (live.get('description') or '') != (label.get('description') or '')
			):
				changes.append((label, 'cập nhật' if live else 'tạo'))
		if not changes:
			print(f'   ✔ đủ {len(wanted)} nhãn chuẩn')
			continue
		for label, action in changes:
			if not apply:
				print(f'   (xem trước) {action} nhãn "{label["name"]}"')
				continue
			github.gh(
				'label',
				'create',
				str(label['name']),
				'--repo',
				f'{github.ORG}/{repo}',
				'--color',
				str(label['color']),
				'--description',
				label.get('description') or '',
				'--force',
			)
			print(f'   ✔ {action} nhãn "{label["name"]}"')
