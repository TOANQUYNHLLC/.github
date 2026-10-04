"""Test tự động cho scripts/check-tool-versions.py.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import http.client
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript

MISE = '[tools]\nruff = "0.16.10"\nshellcheck = "0.11.0"\nactionlint = "1.7.12"\n'


class ToolVersionsTest(unittest.TestCase):
	def runCheck(self, latestRelease):
		"""Chạy main() với mise.toml mẫu và bản phát hành giả; trả (mã thoát, đầu ra)."""
		module = loadScript('check-tool-versions')
		output = io.StringIO()
		with tempfile.TemporaryDirectory() as folder:
			(Path(folder) / 'mise.toml').write_text(MISE, encoding='utf-8')
			module.ROOT = Path(folder)
			with (
				mock.patch.object(module, 'latestRelease', latestRelease),
				mock.patch.object(module, 'cliToken', str),
				contextlib.redirect_stdout(output),
			):
				code = module.main()
		return code, output.getvalue()

	def testCurrentToolsPass(self):
		releases = {'astral-sh/ruff': '0.16.10', 'koalaman/shellcheck': '0.11.0'}
		code, output = self.runCheck(lambda repository: releases.get(repository, '1.7.12'))
		self.assertEqual(code, 0, output)
		self.assertIn('✅ Công cụ đều mới nhất.', output)

	def testNewerReleaseIsReported(self):
		# So theo số (0.16.10 < 0.17.0), không theo chữ.
		releases = {'astral-sh/ruff': '0.17.0', 'koalaman/shellcheck': '0.11.0'}
		code, output = self.runCheck(lambda repository: releases.get(repository, '1.7.12'))
		self.assertEqual(code, 1)
		self.assertIn('⬆️  ruff 0.16.10 → 0.17.0', output)
		self.assertIn('✅ shellcheck 0.11.0', output)

	def testUnreadableReleaseIsReported(self):
		# Máy chủ ngắt kết nối khi đang đọc phản hồi (lỗi urllib không gói thành URLError): báo công cụ đó, không
		# làm dừng cả lượt kiểm tra.
		def latestRelease(repository):
			if repository == 'astral-sh/ruff':
				raise http.client.RemoteDisconnected('đóng kết nối')
			return {'koalaman/shellcheck': '0.11.0'}.get(repository, '1.7.12')

		code, output = self.runCheck(latestRelease)
		self.assertEqual(code, 1)
		self.assertIn('❌ ruff: không đọc được bản phát hành mới nhất (đóng kết nối)', output)
		self.assertIn('✅ actionlint 1.7.12', output)


if __name__ == '__main__':
	unittest.main()
