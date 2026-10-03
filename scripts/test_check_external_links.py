"""Test tự động cho scripts/check-external-links.py.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import http.server
import socket
import socketserver
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript


def answerOk(handler):
	handler.send_response(200)
	handler.end_headers()


def answerWith(codes):
	"""Trả lần lượt các mã trong codes (mã cuối dùng cho mọi lần sau)."""

	def answer(handler):
		handler.send_response(codes.pop(0) if len(codes) > 1 else codes[0])
		handler.end_headers()

	return answer


def handlerClass(head, get=None):
	"""Lớp xử lý HTTP trả lời HEAD bằng head, GET bằng get (mặc định như HEAD), không in nhật ký."""

	class Handler(http.server.BaseHTTPRequestHandler):
		def do_HEAD(self):
			head(self)

		def do_GET(self):
			(get or head)(self)

		def log_message(self, format, *args):
			pass

	return Handler


QuietHandler = handlerClass(answerOk)


class ExternalLinksTest(unittest.TestCase):
	def testUnreachableAddressIsSkippedAndRemembered(self):
		# Địa chỉ đầu không kết nối được: linkStatus chuyển sang địa chỉ sau và nhớ địa chỉ hỏng — chứng minh
		# opener thật sự kết nối qua connectQuickly. Cổng đóng trên 127.0.0.1 thay cho địa chỉ hỏng.
		module = loadScript('check-external-links')
		# TCPServer thay HTTPServer: HTTPServer tra tên máy (getfqdn), trên macOS mất vài giây.
		server = socketserver.TCPServer(('127.0.0.1', 0), QuietHandler)
		threading.Thread(
			target=server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True
		).start()
		port = server.server_address[1]
		with socket.socket() as probe:
			probe.bind(('127.0.0.1', 0))
			closed = probe.getsockname()[1]
		candidates = [
			(socket.AF_INET, socket.SOCK_STREAM, 0, '', ('127.0.0.1', closed)),
			(socket.AF_INET, socket.SOCK_STREAM, 0, '', ('localhost', port)),
		]
		try:
			with mock.patch.object(module.socket, 'getaddrinfo', return_value=candidates):
				self.assertEqual(module.linkStatus(f'http://example.test:{port}/'), 200)
		finally:
			server.shutdown()
			server.server_close()
		self.assertEqual(module.UNREACHABLE, {'127.0.0.1'})

	def testIpv4IsTriedFirst(self):
		# Máy chủ có IPv6 hỏng (như conventionalcommits.org): thử IPv4 trước nên không phải chờ IPv6.
		module = loadScript('check-external-links')
		server = socketserver.TCPServer(('127.0.0.1', 0), QuietHandler)
		threading.Thread(
			target=server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True
		).start()
		port = server.server_address[1]
		candidates = [
			(socket.AF_INET6, socket.SOCK_STREAM, 0, '', ('::1', port, 0, 0)),
			(socket.AF_INET, socket.SOCK_STREAM, 0, '', ('127.0.0.1', port)),
		]
		try:
			with mock.patch.object(module.socket, 'getaddrinfo', return_value=candidates):
				self.assertEqual(module.linkStatus(f'http://example.test:{port}/'), 200)
		finally:
			server.shutdown()
			server.server_close()
		self.assertEqual(module.UNREACHABLE, set())

	def testFallsBackToGetAndRetriesServerErrors(self):
		# HEAD bị từ chối (404) nhưng GET đọc được: liên kết còn sống. GET lỗi 503 lần đầu: thử lại rồi đạt.
		module = loadScript('check-external-links')
		module.RETRY_DELAY = 0
		for head, get, expected in (
			([404], [200], 200),
			([404], [503, 200], 200),
			([404], [404], 404),
		):
			server = socketserver.TCPServer(
				('127.0.0.1', 0), handlerClass(answerWith(head), answerWith(get))
			)
			threading.Thread(
				target=server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True
			).start()
			try:
				url = f'http://127.0.0.1:{server.server_address[1]}/'
				self.assertEqual(module.linkStatus(url), expected, (head, get))
			finally:
				server.shutdown()
				server.server_close()

	def testPublishedCopyMustMatch(self):
		# security.txt đăng trên website (URL Canonical) phải giống bản trong repository.
		module = loadScript('check-external-links')
		served = []

		def answer(handler):
			body = served[0].encode()
			handler.send_response(200)
			handler.send_header('Content-Length', str(len(body)))
			handler.end_headers()
			handler.wfile.write(body)

		server = socketserver.TCPServer(('127.0.0.1', 0), handlerClass(answer))
		threading.Thread(
			target=server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True
		).start()
		url = f'http://127.0.0.1:{server.server_address[1]}/.well-known/security.txt'
		try:
			with tempfile.TemporaryDirectory() as folder:
				module.ROOT = Path(folder)
				path = Path(folder) / 'security.txt'
				path.write_text(f'Contact: mailto:a\nCanonical: {url}\n', encoding='utf-8')
				served.append(path.read_text(encoding='utf-8').replace('\n', '\r\n'))
				self.assertIsNone(module.publishedCopyDiffers(path))
				served[0] = 'Contact: mailto:b\n'
				self.assertIn('khác security.txt', module.publishedCopyDiffers(path))
		finally:
			server.shutdown()
			server.server_close()

	def testCollectsLinksFromFilesWithSpaces(self):
		# Tên tệp có khoảng trắng vẫn được đọc; tệp đã xóa trên đĩa (còn trong index) bị bỏ qua.
		module = loadScript('check-external-links')
		with tempfile.TemporaryDirectory() as folder:
			root = Path(folder)
			(root / 'ghi chú.md').write_text('[a](https://example.com/a)\n', encoding='utf-8')
			(root / 'xoa.md').write_text('[b](https://example.com/b)\n', encoding='utf-8')
			subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
			subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
			(root / 'xoa.md').unlink()
			module.ROOT = root
			self.assertEqual(module.collectLinks(), {'https://example.com/a': {'ghi chú.md'}})


if __name__ == '__main__':
	unittest.main()
