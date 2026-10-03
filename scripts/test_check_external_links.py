"""Test tự động cho scripts/check-external-links.py.

Chạy: python3 -m unittest discover -s scripts -p 'test_*.py'   (hoặc: make test)
"""

import http.server
import socket
import socketserver
import threading
import unittest
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript


def answerOk(handler):
	handler.send_response(200)
	handler.end_headers()


# do_HEAD, log_message là tên http.server quy định — gán qua type() để tên hàm vẫn camelCase (ADR 0012).
QuietHandler = type(
	'QuietHandler',
	(http.server.BaseHTTPRequestHandler,),
	{'do_HEAD': answerOk, 'log_message': lambda handler, *args: None},
)


class ExternalLinksTest(unittest.TestCase):
	def testUnreachableAddressIsSkippedAndRemembered(self):
		# Địa chỉ đầu không kết nối được (như IPv6 hỏng của conventionalcommits.org): linkStatus chuyển sang
		# địa chỉ sau và nhớ địa chỉ hỏng — chứng minh opener thật sự kết nối qua connectQuickly.
		module = loadScript('check-external-links')
		# TCPServer thay HTTPServer: HTTPServer tra tên máy (getfqdn), trên macOS mất vài giây.
		server = socketserver.TCPServer(('127.0.0.1', 0), QuietHandler)
		threading.Thread(target=server.serve_forever, daemon=True).start()
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
		self.assertEqual(module.UNREACHABLE, {'::1'})


if __name__ == '__main__':
	unittest.main()
