"""Kiểm tra GitHub có chấp nhận các biểu mẫu Issue và Discussion không.

Chạy: python3 scripts/check-github-forms.py [ref]   (ref mặc định: main; có thể là tên branch đã đẩy lên)
GitHub từ chối cả biểu mẫu khi gặp khóa lạ (ví dụ `type is not a permitted key`) mà không báo lúc commit
hay trong API; lỗi chỉ hiện trên trang xem tệp. Script đọc dữ liệu JSON nhúng của trang đó — không phải
API chính thức, nên khi GitHub đổi cấu trúc trang, script báo "không đọc được" thay vì báo đạt.
Workflow links.yml chạy hằng tuần; khi GitHub Actions tắt, routine Claude Code chạy hằng tháng. Sửa biểu mẫu
thì đẩy branch rồi chạy make forms REF=<branch> trước khi hợp nhất.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'TOANQUYNHLLC/.github'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; TOANQUYNH-form-check/1.0)'}
# Giây chờ trước lần thử lại thứ n (nhân với n).
RETRY_DELAY = 2
EMBEDDED = re.compile(
	r'<script type="application/json" data-target="react-app\.embeddedData">(.*?)</script>',
	re.DOTALL,
)


def formPaths():
	folder = ROOT / '.github'
	paths = [
		*(folder / 'ISSUE_TEMPLATE').glob('*.yml'),
		*(folder / 'DISCUSSION_TEMPLATE').glob('*.yml'),
	]
	# config.yml cấu hình trang chọn biểu mẫu, không phải biểu mẫu.
	return sorted(path for path in paths if path.name != 'config.yml')


def fetchPage(url, attempts=3):
	"""Nội dung trang; lỗi tạm thời của GitHub (429, 5xx — hay gặp khi gọi dồn) thì chờ rồi thử lại."""
	request = urllib.request.Request(url, headers=HEADERS)
	for attempt in range(1, attempts + 1):
		try:
			with urllib.request.urlopen(request, timeout=30) as response:
				return response.read().decode('utf-8')
		except urllib.error.HTTPError as exc:
			if attempt == attempts or (exc.code != 429 and exc.code < 500):
				raise
			time.sleep(RETRY_DELAY * attempt)
	return ''


def templateData(ref, relative):
	page = fetchPage(f'https://github.com/{REPOSITORY}/blob/{ref}/{relative}')
	match = EMBEDDED.search(page)
	if not match:
		return None
	route = json.loads(match.group(1)).get('payload', {}).get('codeViewBlobRoute') or {}
	return route.get('issueTemplate') or route.get('discussionTemplate')


def templateErrors(template):
	messages = [error.get('message', '') for error in template.get('errors') or []]
	for item in template.get('inputs') or []:
		for key, value in ((item.get('input') or {}).get('errors') or {}).items():
			messages.append(f'{key}: {value}')
	return [re.sub(r'<[^>]+>', '', str(message)) for message in messages]


def main():
	ref = sys.argv[1] if len(sys.argv) > 1 else 'main'
	failed = 0
	relatives = [path.relative_to(ROOT).as_posix() for path in formPaths()]

	def fetch(relative):
		try:
			return templateData(ref, relative)
		except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
			return exc

	# Đọc các trang song song — mỗi trang mất khoảng một giây.
	with ThreadPoolExecutor(max_workers=4) as pool:
		templates = list(pool.map(fetch, relatives))
	for relative, template in zip(relatives, templates, strict=True):
		if isinstance(template, Exception):
			failed += 1
			print(f'❌ {relative}: không đọc được trang ({template})')
			continue
		if template is None:
			failed += 1
			print(f'❌ {relative}: GitHub không nhận là biểu mẫu, hoặc cấu trúc trang đã đổi')
			continue
		errors = templateErrors(template)
		if errors:
			failed += 1
			print(f'❌ {relative}: ' + '; '.join(errors))
		else:
			print(f'✅ {relative}')
	print(
		f'{"✅ GitHub chấp nhận mọi biểu mẫu" if not failed else f"❌ {failed} biểu mẫu lỗi"} ({ref}).'
	)
	return 1 if failed else 0


if __name__ == '__main__':
	sys.exit(main())
