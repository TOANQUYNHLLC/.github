"""Kiểm tra các liên kết http(s) trong tài liệu Markdown, YAML, CITATION.cff và security.txt còn hoạt động.

Chạy: python3 scripts/check-external-links.py
Workflow links.yml chạy định kỳ hằng tuần. Trang chặn truy cập tự động (403, 429, 999)
chỉ được cảnh báo, không tính là lỗi.
"""

import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = {401, 403, 429, 999}
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; TOANQUYNH-link-check/1.0)'}
# Liên kết cần gắn tag hoặc chỉ tồn tại sau khi phát hành — không kiểm tra.
SKIP = ('/compare/', '/releases/tag/', 'img.shields.io', '/actions/workflows/')
# Tệp ngoài Markdown: URL đứng trần (khóa YAML, trường của security.txt), không nằm trong (…).
PATTERNS = ('*.md', '*.yml', '*.yaml', '*.cff', '*.txt')


def text_files():
	output = subprocess.run(
		['git', 'ls-files', '--cached', '--others', '--exclude-standard', *PATTERNS],
		cwd=ROOT,
		capture_output=True,
		text=True,
		check=True,
	).stdout
	return [ROOT / name for name in output.split()]


def collect_links():
	links = {}
	for path in text_files():
		text = path.read_text(encoding='utf-8')
		if path.suffix == '.md':
			urls = re.findall(
				r'\((https?://[^)\s]+)\)', re.sub(r'```.*?```', '', text, flags=re.DOTALL)
			)
		else:
			urls = [
				url.rstrip('.,;:')
				for url in re.findall(r'https?://[^\s)\]\'"<>`]+', text)
				if '${' not in url
			]
		for url in urls:
			if not any(part in url for part in SKIP):
				links.setdefault(url, set()).add(str(path.relative_to(ROOT)))
	return links


def status(url):
	for method in ('HEAD', 'GET'):
		try:
			request = urllib.request.Request(url, method=method, headers=HEADERS)
			with urllib.request.urlopen(request, timeout=15) as response:
				return response.status
		except urllib.error.HTTPError as exc:
			if method == 'GET' or exc.code not in (405, 501):
				return exc.code
		except (urllib.error.URLError, TimeoutError) as exc:
			return f'không kết nối được ({getattr(exc, "reason", exc)})'
	return None


def main():
	broken = 0
	for url, files in sorted(collect_links().items()):
		code = status(url)
		where = ', '.join(sorted(files))
		if isinstance(code, int) and code < 400:
			print(f'✅ {code} {url}')
		elif code in BLOCKED:
			print(f'⚠️  {code} {url} — trang chặn truy cập tự động, cần kiểm tra thủ công ({where})')
		else:
			broken += 1
			print(f'❌ {code} {url} ({where})')
	print(f'{"✅ Không có liên kết hỏng" if not broken else f"❌ {broken} liên kết hỏng"}.')
	return 1 if broken else 0


if __name__ == '__main__':
	sys.exit(main())
