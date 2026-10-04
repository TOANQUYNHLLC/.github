"""Báo công cụ trong mise.toml có bản phát hành mới hơn (Dependabot chưa cập nhật mise.toml, ADR 0008).

Chạy: python3 scripts/check-tool-versions.py
Đọc bản phát hành mới nhất trên GitHub; dùng GH_TOKEN (workflow links.yml đặt sẵn) hoặc token của GitHub CLI đã
đăng nhập để tránh giới hạn truy cập.
Thoát mã 1 khi có công cụ cũ hơn bản mới nhất, để workflow hằng tuần báo cho người quản trị.
"""

import functools
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Công cụ trong mise.toml → repository phát hành trên GitHub.
REPOSITORIES = {
	'ruff': 'astral-sh/ruff',
	'shellcheck': 'koalaman/shellcheck',
	'actionlint': 'rhysd/actionlint',
}


@functools.cache
def cliToken():
	"""Token của GitHub CLI đã đăng nhập (đọc một lần); rỗng khi không có gh hoặc chưa đăng nhập."""
	if not shutil.which('gh'):
		return ''
	result = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, check=False)
	return result.stdout.strip() if result.returncode == 0 else ''


def latestRelease(repository):
	request = urllib.request.Request(
		f'https://api.github.com/repos/{repository}/releases/latest',
		headers={'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'},
	)
	token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN') or cliToken()
	if token:
		request.add_header('Authorization', f'Bearer {token}')
	with urllib.request.urlopen(request, timeout=30) as response:
		return json.load(response)['tag_name'].removeprefix('v')


def versionKey(version):
	return tuple(int(part) for part in re.findall(r'\d+', version))


def main():
	tools = tomllib.loads((ROOT / 'mise.toml').read_text(encoding='utf-8')).get('tools', {})

	def latest(repository):
		try:
			return latestRelease(repository)
		# OSError gồm lỗi lúc gửi (URLError) lẫn lúc đọc phản hồi (máy chủ ngắt kết nối); HTTPException: phản hồi
		# HTTP sai dạng, bị cắt ngang.
		except (OSError, http.client.HTTPException, KeyError, ValueError) as exc:
			if isinstance(exc, urllib.error.HTTPError):
				exc.close()  # lỗi HTTP giữ phản hồi đang mở
			return exc

	cliToken()  # đọc token một lần trước khi các luồng cùng cần
	# Hỏi GitHub song song — mỗi lần chờ mạng gần một giây.
	with ThreadPoolExecutor(max_workers=len(REPOSITORIES)) as pool:
		releases = list(pool.map(latest, REPOSITORIES.values()))
	outdated = 0
	for tool, release in zip(REPOSITORIES, releases, strict=True):
		current = str(tools.get(tool, ''))
		if isinstance(release, Exception):
			outdated += 1
			print(f'❌ {tool}: không đọc được bản phát hành mới nhất ({release})')
		elif versionKey(current) < versionKey(release):
			outdated += 1
			print(f'⬆️  {tool} {current} → {release}: sửa mise.toml rồi chạy mise install')
		else:
			print(f'✅ {tool} {current}')
	print(f'{"✅ Công cụ đều mới nhất" if not outdated else f"❌ {outdated} công cụ cần xem lại"}.')
	return 1 if outdated else 0


if __name__ == '__main__':
	sys.exit(main())
