"""Kiểm tra các liên kết http(s) trong tài liệu Markdown, YAML, CITATION.cff và security.txt còn hoạt động, và bản
security.txt đăng trên website (URL Canonical) khớp bản trong repository.

Chạy: python3 scripts/check-external-links.py
Workflow links.yml chạy hằng tuần; hook post-merge chạy sau mỗi lần git pull (make links).
Trang chặn truy cập tự động (403, 429, 999) chỉ được cảnh báo, không tính là lỗi.
URL Canonical cần đọc được nội dung để so: GET thay cả kiểm tra liên kết, lỗi đọc tính là lỗi.
"""

import http.client
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from markdown import withoutCode

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = {401, 403, 429, 999}
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; TOANQUYNH-link-check/1.0)'}
# Huy hiệu shields.io sinh động và hay chặn truy cập tự động — không kiểm tra. Liên kết tag, so sánh phiên bản
# được kiểm tra: phát hành theo README (sửa CHANGELOG rồi gắn tag ngay) để liên kết không hỏng.
SKIP = ('img.shields.io',)
# Tệp ngoài Markdown: URL đứng trần (khóa YAML, trường của security.txt), không nằm trong (…).
PATTERNS = ('*.md', '*.yml', '*.yaml', '*.cff', '*.txt')
CANONICAL = re.compile(r'^Canonical:\s*(\S+)$', re.MULTILINE)
# Giây chờ trước khi thử lại liên kết trả lỗi máy chủ (5xx).
RETRY_DELAY = 2
# Giây chờ kết nối tới mỗi địa chỉ của máy chủ; chờ phản hồi vẫn 15 giây.
CONNECT_TIMEOUT = 3
# Địa chỉ đã không kết nối được — các lần kết nối sau (HEAD rồi GET, chuyển hướng) thử sau cùng.
UNREACHABLE = set()


def connectQuickly(address, timeout, sourceAddress=None):
	"""Như socket.create_connection nhưng thử IPv4 trước, mỗi địa chỉ chỉ chờ CONNECT_TIMEOUT giây và nhớ địa chỉ
	hỏng: urllib thử địa chỉ lần lượt (IPv6 trước), nên máy chủ có IPv6 hỏng (ví dụ conventionalcommits.org) làm
	mỗi liên kết chờ thêm vài giây — curl, trình duyệt thử song song nên không chậm."""
	host, port = address
	candidates = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
	# IPv4 trước (máy chủ có IPv6 hỏng không làm mỗi liên kết chờ thêm vài giây); địa chỉ đã hỏng thử sau cùng.
	candidates.sort(
		key=lambda candidate: (candidate[4][0] in UNREACHABLE, candidate[0] != socket.AF_INET)
	)
	error = OSError(f'không có địa chỉ cho {host}')
	for family, kind, protocol, _, socketAddress in candidates:
		connection = socket.socket(family, kind, protocol)
		try:
			connection.settimeout(CONNECT_TIMEOUT)
			if sourceAddress:
				connection.bind(sourceAddress)
			connection.connect(socketAddress)
		except OSError as exc:
			connection.close()
			UNREACHABLE.add(socketAddress[0])
			error = exc
			continue
		connection.settimeout(timeout)
		return connection
	raise error


class QuickHTTPConnection(http.client.HTTPConnection):
	"""Kết nối HTTP dùng connectQuickly — gán trong __init__ vì __init__ của http.client đặt lại
	_create_connection, ghi đè ở mức lớp không có tác dụng."""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._create_connection = connectQuickly


class QuickHTTPSConnection(http.client.HTTPSConnection):
	"""Như QuickHTTPConnection cho HTTPS."""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._create_connection = connectQuickly


class QuickHTTPHandler(urllib.request.HTTPHandler):
	def http_open(self, req):
		return self.do_open(QuickHTTPConnection, req)


class QuickHTTPSHandler(urllib.request.HTTPSHandler):
	def https_open(self, req):
		return self.do_open(QuickHTTPSConnection, req, context=self._context)


# Opener của urllib mở mọi kết nối bằng connectQuickly.
OPENER = urllib.request.build_opener(QuickHTTPHandler, QuickHTTPSHandler)


def textFiles():
	output = subprocess.run(
		['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z', *PATTERNS],
		cwd=ROOT,
		capture_output=True,
		text=True,
		check=True,
	).stdout
	# -z: tên tệp có khoảng trắng; bỏ tệp đã xóa trên đĩa nhưng còn trong index.
	return [ROOT / name for name in output.split('\0') if name and (ROOT / name).is_file()]


def readDocuments():
	"""Đọc mỗi tệp một lần trong lượt chạy; giữ lỗi từng tệp để vẫn kiểm tra các tệp còn lại."""
	documents, problems = {}, []
	for path in textFiles():
		try:
			documents[path] = path.read_text(encoding='utf-8')
		except (OSError, UnicodeError) as exc:
			problems.append(f'{path.relative_to(ROOT)}: không đọc được ({errorReason(exc)})')
	return documents, problems


def collectLinks(documents=None):
	if documents is None:
		documents, problems = readDocuments()
		if problems:
			raise ValueError('; '.join(problems))
	links = {}
	for path, text in documents.items():
		if path.suffix == '.md':
			urls = re.findall(r'\((https?://[^)\s]+)\)', withoutCode(text), flags=re.IGNORECASE)
		else:
			urls = [
				url.rstrip('.,;:')
				for url in re.findall(r'https?://[^\s)\]\'"<>`]+', text, flags=re.IGNORECASE)
				if '${' not in url
			]
		for url in urls:
			if not any(part in url for part in SKIP):
				links.setdefault(url, set()).add(str(path.relative_to(ROOT)))
	return links


def errorReason(exc):
	"""Lý do lỗi kết nối gọn trên một dòng (dòng trạng thái sai có thể kèm xuống dòng, lỗi có thể rỗng)."""
	return ' '.join(str(getattr(exc, 'reason', exc)).split()) or type(exc).__name__


def requestStatus(url, method):
	"""Mã HTTP của một lần gửi, hoặc thông báo khi không kết nối được."""
	try:
		request = httpRequest(url, method)
		with OPENER.open(request, timeout=15) as response:
			return response.status
	except urllib.error.HTTPError as exc:
		exc.close()  # lỗi HTTP giữ phản hồi đang mở — chỉ cần mã
		return exc.code
	# urllib chỉ gói lỗi lúc gửi thành URLError; lỗi lúc đọc phản hồi (máy chủ ngắt kết nối, dòng trạng thái
	# sai) là OSError, HTTPException — bắt hết để một trang lỗi không làm dừng cả lượt kiểm tra.
	except (OSError, http.client.HTTPException, ValueError) as exc:
		return f'không kết nối được ({errorReason(exc)})'


def httpRequest(url, method='GET'):
	"""Chỉ nhận URL HTTP(S) có máy chủ và cổng hợp lệ; không mở tệp cục bộ từ trường Canonical."""
	parts = urllib.parse.urlsplit(url)
	if parts.scheme not in ('http', 'https') or not parts.hostname:
		raise ValueError('URL phải dùng HTTP(S) và có tên máy chủ')
	# urlsplit chỉ kiểm tra cổng khi đọc thuộc tính này.
	if parts.port == 0:
		raise ValueError('cổng HTTP phải nằm trong khoảng 1–65535')
	return urllib.request.Request(url, method=method, headers=HEADERS)


def linkStatus(url):
	"""HEAD trước cho nhẹ; HEAD lỗi thì GET (có máy chủ trả 403, 404, 405 cho HEAD dù trang vẫn còn); lỗi máy
	chủ (5xx) thường chỉ tạm thời nên chờ rồi thử lại một lần."""
	code = requestStatus(url, 'HEAD')
	if isinstance(code, int) and code < 400:
		return code
	code = requestStatus(url, 'GET')
	if isinstance(code, int) and code >= 500:
		time.sleep(RETRY_DELAY)
		code = requestStatus(url, 'GET')
	return code


def canonicalUrl(path, text=None):
	"""URL Canonical khai báo trong tệp (trường của security.txt), None nếu không có."""
	match = CANONICAL.search(path.read_text(encoding='utf-8') if text is None else text)
	return match.group(1) if match else None


def publishedCopyDiffers(path, text=None):
	"""Thông báo khi bản đăng tại URL Canonical của tệp (ví dụ security.txt trên website) khác bản trong
	repository; None khi giống nhau."""
	url = None
	try:
		if text is None:
			text = path.read_text(encoding='utf-8')
		url = canonicalUrl(path, text)
		request = httpRequest(url)
		with OPENER.open(request, timeout=15) as response:
			published = response.read().decode('utf-8')
	except urllib.error.HTTPError as exc:
		exc.close()  # lỗi HTTP giữ phản hồi đang mở — chỉ cần mã
		return f'không đọc được {url} (HTTP {exc.code})'
	except (OSError, http.client.HTTPException, ValueError) as exc:
		return f'không đọc được {url or path.relative_to(ROOT)} ({errorReason(exc)})'
	if published.replace('\r\n', '\n') != text:
		return f'{url} khác {path.relative_to(ROOT)} — đăng lại tệp lên website'
	return None


def main():
	try:
		documents, problems = readDocuments()
	except (OSError, subprocess.CalledProcessError) as exc:
		print(f'❌ Không liệt kê được tệp tài liệu ({errorReason(exc)}).')
		return 1
	broken = len(problems)
	for problem in problems:
		print(f'❌ {problem}')
	copies = sorted(
		(path, text)
		for path, text in documents.items()
		if path.parent == ROOT / '.well-known'
		and path.suffix == '.txt'
		and canonicalUrl(path, text)
	)
	canonicalUrls = {canonicalUrl(path, text) for path, text in copies}
	# GET so nội dung cũng xác nhận URL Canonical hoạt động — không gửi thêm HEAD tới cùng URL.
	links = sorted(
		(url, files) for url, files in collectLinks(documents).items() if url not in canonicalUrls
	)
	# Kiểm tra song song: tuần tự thì cả lượt mất vài chục giây.
	with ThreadPoolExecutor(max_workers=16) as pool:
		copyResults = [pool.submit(publishedCopyDiffers, path, text) for path, text in copies]
		codes = list(pool.map(linkStatus, [url for url, _ in links]))
		copyProblems = [result.result() for result in copyResults]
	for (url, files), code in zip(links, codes, strict=True):
		where = ', '.join(sorted(files))
		if isinstance(code, int) and code < 400:
			print(f'✅ {code} {url}')
		elif code in BLOCKED:
			print(f'⚠️  {code} {url} — trang chặn truy cập tự động, cần kiểm tra thủ công ({where})')
		else:
			broken += 1
			print(f'❌ {code} {url} ({where})')
	# Chỉ tệp có Canonical mới có bản đăng trên web để so.
	for (path, _), problem in zip(copies, copyProblems, strict=True):
		if problem:
			broken += 1
			print(f'❌ {problem}')
		else:
			print(f'✅ Bản đăng trên web khớp {path.relative_to(ROOT)}')
	print(f'{"✅ Không có liên kết hỏng" if not broken else f"❌ {broken} lỗi"}.')
	return 1 if broken else 0


if __name__ == '__main__':
	sys.exit(main())
