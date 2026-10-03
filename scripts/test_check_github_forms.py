"""Test tự động cho scripts/check-github-forms.py.

Chạy: python3 -m unittest discover -s scripts -p 'test_*.py'   (hoặc: make test)
"""

import contextlib
import io
import unittest
import urllib.error
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript


class GithubFormsTest(unittest.TestCase):
	def testTransientErrorIsRetried(self):
		# GitHub trả 503 khi bị gọi dồn: thử lại rồi đọc được; lỗi 404 thì báo ngay, không thử lại.
		module = loadScript('check-github-forms')
		module.RETRY_DELAY = 0
		unavailable = urllib.error.HTTPError(
			'https://github.com', 503, 'Service Unavailable', {}, None
		)
		missing = urllib.error.HTTPError('https://github.com', 404, 'Not Found', {}, None)
		responses = [unavailable, io.BytesIO(b'trang')]

		def urlopen(request, timeout):
			response = responses.pop(0)
			if isinstance(response, Exception):
				raise response
			return response

		with mock.patch.object(module.urllib.request, 'urlopen', urlopen):
			self.assertEqual(module.fetchPage('https://github.com'), 'trang')
			responses[:] = [missing, io.BytesIO(b'')]
			with self.assertRaises(urllib.error.HTTPError) as raised:
				module.fetchPage('https://github.com')
			raised.exception.close()
			self.assertEqual(len(responses), 1)

	def testMissingRefIsReportedOnce(self):
		# Branch chưa đẩy lên GitHub: mọi trang 404 — báo một dòng, không báo từng biểu mẫu lỗi.
		module = loadScript('check-github-forms')

		def missing(url):
			raise urllib.error.HTTPError(url, 404, 'Not Found', {}, None)

		output = io.StringIO()
		with (
			mock.patch.object(module, 'fetchPage', missing),
			mock.patch.object(module.sys, 'argv', ['check-github-forms.py', 'feature/x']),
			contextlib.redirect_stdout(output),
		):
			self.assertEqual(module.main(), 1)
		self.assertEqual(
			output.getvalue().strip(),
			'❌ Không có "feature/x" trên GitHub — đẩy branch trước: git push -u origin feature/x',
		)


if __name__ == '__main__':
	unittest.main()
