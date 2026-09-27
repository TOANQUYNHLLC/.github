"""Báo công cụ trong mise.toml có bản phát hành mới hơn (Dependabot chưa cập nhật mise.toml, ADR 0007).

Chạy: python3 scripts/check-tool-versions.py
Đọc bản phát hành mới nhất trên GitHub; đặt GH_TOKEN (workflow links.yml đặt sẵn) để tránh giới hạn truy cập.
Thoát mã 1 khi có công cụ cũ hơn bản mới nhất, để workflow hằng tuần báo cho người quản trị.
"""

import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Công cụ trong mise.toml → repository phát hành trên GitHub.
REPOSITORIES = {
	'ruff': 'astral-sh/ruff',
	'shellcheck': 'koalaman/shellcheck',
	'actionlint': 'rhysd/actionlint',
}


def latest_release(repository):
	request = urllib.request.Request(
		f'https://api.github.com/repos/{repository}/releases/latest',
		headers={'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'},
	)
	token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
	if token:
		request.add_header('Authorization', f'Bearer {token}')
	with urllib.request.urlopen(request, timeout=30) as response:
		return json.load(response)['tag_name'].removeprefix('v')


def version_key(version):
	return tuple(int(part) for part in re.findall(r'\d+', version))


def main():
	tools = tomllib.loads((ROOT / 'mise.toml').read_text(encoding='utf-8')).get('tools', {})
	outdated = 0
	for tool, repository in REPOSITORIES.items():
		current = str(tools.get(tool, ''))
		try:
			latest = latest_release(repository)
		except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
			outdated += 1
			print(f'❌ {tool}: không đọc được bản phát hành mới nhất ({exc})')
			continue
		if version_key(current) < version_key(latest):
			outdated += 1
			print(f'⬆️  {tool} {current} → {latest}: sửa mise.toml rồi chạy mise install')
		else:
			print(f'✅ {tool} {current}')
	print(f'{"✅ Công cụ đều mới nhất" if not outdated else f"❌ {outdated} công cụ cần xem lại"}.')
	return 1 if outdated else 0


if __name__ == '__main__':
	sys.exit(main())
