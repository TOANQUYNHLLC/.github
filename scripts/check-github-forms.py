"""Kiểm tra GitHub có chấp nhận các biểu mẫu Issue và Discussion không.

Chạy: python3 scripts/check-github-forms.py [ref]   (ref mặc định: main; có thể là tên branch đã đẩy lên)
GitHub từ chối cả biểu mẫu khi gặp khóa lạ (ví dụ `type is not a permitted key`) mà không báo lúc commit
hay trong API; lỗi chỉ hiện trên trang xem tệp. Script đọc dữ liệu JSON nhúng của trang đó — không phải
API chính thức, nên khi GitHub đổi cấu trúc trang, script báo "không đọc được" thay vì báo đạt.
Workflow links.yml chạy hằng tuần; khi GitHub Actions tắt, chạy make forms tại máy. Sửa biểu mẫu thì đẩy
branch rồi kiểm tra Issue bằng make forms REF=<branch>. Discussion chỉ xác minh được trên nhánh mặc định;
ref khác được báo chưa xác minh và trả mã lỗi, không dùng dữ liệu Discussion của nhánh mặc định để báo đạt.
"""

import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.parse
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


class UnverifiedDiscussion(Exception):
	"""GitHub chỉ cung cấp dữ liệu Discussion của nhánh mặc định, không phải ref được yêu cầu."""


def formPaths():
	folder = ROOT / '.github'
	paths = [
		path
		for kind in ('ISSUE_TEMPLATE', 'DISCUSSION_TEMPLATE')
		for pattern in ('*.yml', '*.yaml')
		for path in (folder / kind).glob(pattern)
	]
	# config.yml cấu hình trang chọn biểu mẫu, không phải biểu mẫu.
	return sorted(path for path in paths if path.stem != 'config')


def fetchPage(url, attempts=3):
	"""Nội dung trang; lỗi tạm thời của GitHub (429, 5xx — hay gặp khi gọi dồn) thì chờ rồi thử lại, lần cuối
	vẫn lỗi thì ném lỗi."""
	request = urllib.request.Request(url, headers=HEADERS)
	for attempt in range(1, attempts):
		try:
			with urllib.request.urlopen(request, timeout=30) as response:
				return response.read().decode('utf-8')
		except urllib.error.HTTPError as exc:
			if exc.code != 429 and exc.code < 500:
				raise
			exc.close()  # lỗi HTTP giữ phản hồi đang mở — đóng trước khi thử lại
			time.sleep(RETRY_DELAY * attempt)
	with urllib.request.urlopen(request, timeout=30) as response:
		return response.read().decode('utf-8')


def templateData(ref, relative):
	# Mã hoá phần đường dẫn: tên branch có thể chứa #, %… (git cho phép) — ghép thẳng thì URL bị cắt, đọc nhầm trang.
	path = urllib.parse.quote(f'{ref}/{relative}', safe='/')
	page = fetchPage(f'https://github.com/{REPOSITORY}/blob/{path}')
	match = EMBEDDED.search(page)
	if not match:
		return None
	pageData = json.loads(match.group(1))
	payload = pageData.get('payload') if isinstance(pageData, dict) else None
	data = payload.get('codeViewBlobRoute') if isinstance(payload, dict) else None
	if not isinstance(data, dict):
		raise TypeError('cấu trúc dữ liệu trang đã đổi')
	if 'DISCUSSION_TEMPLATE' in Path(relative).parts:
		# Nội dung blob theo ref, nhưng discussionTemplate theo nhánh mặc định. Chỉ tin khi trang đang xem đúng
		# nhánh mặc định; cả SHA của commit cũ lẫn tên branch khác đều không xác minh được.
		layout = payload.get('codeViewLayoutRoute')
		blobLayout = payload.get('codeViewBlobLayoutRoute')
		repo = layout.get('repo') if isinstance(layout, dict) else None
		refInfo = blobLayout.get('refInfo') if isinstance(blobLayout, dict) else None
		if (
			not isinstance(repo, dict)
			or not isinstance(repo.get('defaultBranch'), str)
			or not repo['defaultBranch']
			or not isinstance(refInfo, dict)
			or not isinstance(refInfo.get('name'), str)
			or not isinstance(refInfo.get('refType'), str)
		):
			raise TypeError('không đọc được nhánh mặc định và ref của trang Discussion')
		if refInfo['name'] != repo['defaultBranch'] or refInfo['refType'] != 'branch':
			raise UnverifiedDiscussion(
				f'chỉ xác minh Discussion trên nhánh mặc định {repo["defaultBranch"]}; '
				'kiểm tra tại máy bằng make validate, rồi chạy make forms sau khi hợp nhất'
			)
		return data.get('discussionTemplate')
	return data.get('issueTemplate')


def templateErrors(template):
	if (
		not isinstance(template, dict)
		or not isinstance(template.get('errors'), list)
		or not isinstance(template.get('inputs'), list)
		or ('valid' in template and type(template['valid']) is not bool)
	):
		raise TypeError('cấu trúc dữ liệu biểu mẫu đã đổi')
	messages = []
	for error in template['errors']:
		if not isinstance(error, dict) or not isinstance(error.get('message'), str):
			raise TypeError('cấu trúc errors của biểu mẫu đã đổi')
		messages.append(error['message'])
	for item in template['inputs']:
		if not isinstance(item, dict):
			raise TypeError('cấu trúc inputs của biểu mẫu đã đổi')
		inputData = item.get('input')
		if inputData is None:
			continue
		if not isinstance(inputData, dict) or (
			'errors' in inputData
			and inputData['errors'] is not None
			and not isinstance(inputData['errors'], dict)
		):
			raise TypeError('cấu trúc input.errors của biểu mẫu đã đổi')
		for key, value in (inputData.get('errors') or {}).items():
			messages.append(f'{key}: {value}')
	if template.get('valid') is False and not messages:
		messages.append('GitHub đánh dấu biểu mẫu không hợp lệ')
	return [re.sub(r'<[^>]+>', '', str(message)) for message in messages]


def main():
	# zip(strict=…) cần Python ≥ 3.10, script cần ≥ 3.11 — báo rõ thay vì traceback giữa chừng.
	if sys.version_info < (3, 11):  # noqa: UP036 — cố ý: chặn khi bị chạy bằng Python cũ
		print(
			f'Cần Python ≥ 3.11 (đang dùng {sys.version.split()[0]}) — chạy mise install, mở terminal có mise.'
		)
		return 1
	ref = sys.argv[1] if len(sys.argv) > 1 else 'main'
	failed = unverified = 0
	relatives = [path.relative_to(ROOT).as_posix() for path in formPaths()]
	if not relatives:
		print('❌ Không tìm thấy biểu mẫu Issue hoặc Discussion để kiểm tra.')
		return 1

	def fetch(relative):
		try:
			return templateData(ref, relative)
		# OSError gồm lỗi lúc gửi (URLError) lẫn lúc đọc phản hồi (máy chủ ngắt kết nối); HTTPException: phản hồi
		# HTTP sai dạng, bị cắt ngang; ValueError: JSON nhúng sai, trang không phải UTF-8.
		except (
			OSError,
			http.client.HTTPException,
			ValueError,
			TypeError,
			UnverifiedDiscussion,
		) as exc:
			if isinstance(exc, urllib.error.HTTPError):
				exc.close()  # chỉ cần mã lỗi, không cần nội dung phản hồi
			return exc

	# Đọc các trang song song — mỗi trang mất khoảng một giây.
	with ThreadPoolExecutor(max_workers=max(1, len(relatives))) as pool:
		templates = list(pool.map(fetch, relatives))
	# Mọi trang đều 404: ref chưa có trên GitHub, không phải biểu mẫu lỗi.
	if templates and all(
		isinstance(template, urllib.error.HTTPError) and template.code == 404
		for template in templates
	):
		print(f'❌ Không có "{ref}" trên GitHub — đẩy branch trước: git push -u origin {ref}')
		return 1
	for relative, template in zip(relatives, templates, strict=True):
		if isinstance(template, UnverifiedDiscussion):
			unverified += 1
			print(f'⚠ {relative}: chưa xác minh ({template})')
			continue
		if isinstance(template, Exception):
			failed += 1
			print(f'❌ {relative}: không đọc được trang ({template})')
			continue
		if template is None:
			failed += 1
			print(f'❌ {relative}: GitHub không nhận là biểu mẫu, hoặc cấu trúc trang đã đổi')
			continue
		try:
			errors = templateErrors(template)
		except TypeError as exc:
			failed += 1
			print(f'❌ {relative}: không đọc được biểu mẫu ({exc})')
			continue
		if errors:
			failed += 1
			print(f'❌ {relative}: ' + '; '.join(errors))
		else:
			print(f'✅ {relative}')
	if unverified:
		print(f'⚠ {unverified} Discussion chưa xác minh; {failed} biểu mẫu lỗi ({ref}).')
	else:
		print(
			f'{"✅ GitHub chấp nhận mọi biểu mẫu" if not failed else f"❌ {failed} biểu mẫu lỗi"} ({ref}).'
		)
	return 1 if failed or unverified else 0


if __name__ == '__main__':
	sys.exit(main())
