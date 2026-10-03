"""Kiểm tra các liên kết http(s) trong tài liệu Markdown, YAML, CITATION.cff và security.txt còn hoạt động, và bản
security.txt đăng trên website (URL Canonical) khớp bản trong repository.

Chạy: python3 scripts/check-external-links.py
Workflow links.yml chạy hằng tuần; hook post-merge chạy sau mỗi lần git pull (make links).
Trang chặn truy cập tự động (403, 429, 999) chỉ được cảnh báo, không tính là lỗi.
"""

import http.client
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = {401, 403, 429, 999}
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; TOANQUYNH-link-check/1.0)'}
# Huy hiệu và trang workflow trả về trang động — không kiểm tra. Liên kết tag, so sánh phiên bản được kiểm tra:
# phát hành theo README (sửa CHANGELOG rồi gắn tag ngay) để liên kết không hỏng.
SKIP = ('img.shields.io', '/actions/workflows/')
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


def quickConnection(connectionClass):
	"""Tạo kết nối http.client dùng connectQuickly — gán cho từng kết nối vì __init__ (Python 3.14) đặt lại
	_create_connection, ghi đè ở lớp không có tác dụng."""

	def create(*args, **kwargs):
		connection = connectionClass(*args, **kwargs)
		connection._create_connection = connectQuickly
		return connection

	return create


def quickOpener():
	"""Opener của urllib mở kết nối bằng connectQuickly. Gán http_open, https_open (tên urllib quy định) cho
	từng handler thay vì kế thừa lớp — tên hàm trong script viết camelCase (ADR 0010)."""
	plain, secure = urllib.request.HTTPHandler(), urllib.request.HTTPSHandler()
	plain.http_open = lambda request: plain.do_open(
		quickConnection(http.client.HTTPConnection), request
	)
	secure.https_open = lambda request: secure.do_open(
		quickConnection(http.client.HTTPSConnection), request, context=secure._context
	)
	return urllib.request.build_opener(plain, secure)


OPENER = quickOpener()


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


def collectLinks():
	links = {}
	for path in textFiles():
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


def requestStatus(url, method):
	"""Mã HTTP của một lần gửi, hoặc thông báo khi không kết nối được."""
	request = urllib.request.Request(url, method=method, headers=HEADERS)
	try:
		with OPENER.open(request, timeout=15) as response:
			return response.status
	except urllib.error.HTTPError as exc:
		exc.close()  # lỗi HTTP giữ phản hồi đang mở — chỉ cần mã
		return exc.code
	except (urllib.error.URLError, TimeoutError) as exc:
		return f'không kết nối được ({getattr(exc, "reason", exc)})'


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


def canonicalUrl(path):
	"""URL Canonical khai báo trong tệp (trường của security.txt), None nếu không có."""
	match = CANONICAL.search(path.read_text(encoding='utf-8'))
	return match.group(1) if match else None


def publishedCopyDiffers(path):
	"""Thông báo khi bản đăng tại URL Canonical của tệp (ví dụ security.txt trên website) khác bản trong
	repository; None khi giống nhau."""
	url = canonicalUrl(path)
	request = urllib.request.Request(url, headers=HEADERS)
	try:
		with OPENER.open(request, timeout=15) as response:
			published = response.read().decode('utf-8')
	except urllib.error.HTTPError as exc:
		exc.close()  # lỗi HTTP giữ phản hồi đang mở — chỉ cần mã
		return f'không đọc được {url} (HTTP {exc.code})'
	except (urllib.error.URLError, TimeoutError, UnicodeDecodeError) as exc:
		return f'không đọc được {url} ({getattr(exc, "reason", exc)})'
	if published.replace('\r\n', '\n') != path.read_text(encoding='utf-8'):
		return f'{url} khác {path.relative_to(ROOT)} — đăng lại tệp lên website'
	return None


def main():
	broken = 0
	links = sorted(collectLinks().items())
	# Kiểm tra song song: tuần tự thì cả lượt mất vài chục giây.
	with ThreadPoolExecutor(max_workers=16) as pool:
		codes = list(pool.map(linkStatus, [url for url, _ in links]))
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
	for path in sorted(path for path in ROOT.glob('.well-known/*.txt') if canonicalUrl(path)):
		problem = publishedCopyDiffers(path)
		if problem:
			broken += 1
			print(f'❌ {problem}')
		else:
			print(f'✅ Bản đăng trên web khớp {path.relative_to(ROOT)}')
	print(f'{"✅ Không có liên kết hỏng" if not broken else f"❌ {broken} lỗi"}.')
	return 1 if broken else 0


if __name__ == '__main__':
	sys.exit(main())
