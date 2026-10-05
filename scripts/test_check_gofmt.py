"""Test tự động cho scripts/check-gofmt.py.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript


class GofmtTest(unittest.TestCase):
	def testFailedToolWithoutDiagnosticsIsNotAccepted(self):
		module = loadScript('check-gofmt')
		with (
			mock.patch.object(module, 'goFiles', return_value=['main.go']),
			mock.patch.object(
				module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 2, '', '')
			),
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(module.main(), 1)

	def testMissingToolIsReported(self):
		module = loadScript('check-gofmt')
		output = io.StringIO()
		with (
			mock.patch.object(module, 'goFiles', return_value=['main.go']),
			mock.patch.object(module.subprocess, 'run', side_effect=FileNotFoundError('gofmt')),
			contextlib.redirect_stdout(output),
		):
			self.assertEqual(module.main(), 1)
		self.assertIn('gofmt', output.getvalue())

	def testVendorIsSkipped(self):
		# Mã của bên thứ ba trong vendor/ không thuộc trách nhiệm định dạng của repository; tên tệp có dấu,
		# khoảng trắng được liệt kê nguyên văn.
		module = loadScript('check-gofmt')
		with tempfile.TemporaryDirectory() as folder:
			for name in ('main.go', 'cmd/app/ứng dụng.go', 'vendor/lib/lib.go', 'README.md'):
				path = Path(folder) / name
				path.parent.mkdir(parents=True, exist_ok=True)
				path.write_text('package x\n', encoding='utf-8')
			subprocess.run(['git', 'init', '-q'], cwd=folder, check=True)
			with contextlib.chdir(folder):
				self.assertEqual(sorted(module.goFiles()), ['cmd/app/ứng dụng.go', 'main.go'])

	def testSyntaxErrorIsReported(self):
		# Tệp Go sai cú pháp: gofmt thoát mã 2 — báo đúng lỗi (tệp:dòng:cột) thay vì traceback; tệp chưa định dạng
		# vẫn được liệt kê. Trên GitHub Actions thông báo nhiều dòng giữ trên một chú thích (%0A).
		module = loadScript('check-gofmt')
		gofmt = subprocess.CompletedProcess(
			[], 2, 'ugly.go\n', "bad.go:2:12: expected ')', found '{'\n"
		)
		for actions, expected in (
			('', "❌ gofmt không đọc được tệp Go:\nbad.go:2:12: expected ')', found '{'"),
			(
				'true',
				"::error::gofmt không đọc được tệp Go:%0Abad.go:2:12: expected ')', found '{'",
			),
		):
			output = io.StringIO()
			with (
				mock.patch.object(module, 'goFiles', return_value=['bad.go', 'ugly.go']),
				mock.patch.object(module.subprocess, 'run', return_value=gofmt),
				mock.patch.dict(module.os.environ, {'GITHUB_ACTIONS': actions}),
				contextlib.redirect_stdout(output),
			):
				self.assertEqual(module.main(), 1)
			self.assertIn(expected, output.getvalue())
			self.assertIn('ugly.go', output.getvalue())

	def testActionsAnnotationEscapesPercentSigns(self):
		# GitHub Actions giải mã %25, %0D, %0A trong chú thích: tên tệp có % phải mã hóa để hiện đúng.
		module = loadScript('check-gofmt')
		output = io.StringIO()
		with (
			mock.patch.dict(module.os.environ, {'GITHUB_ACTIONS': 'true'}),
			contextlib.redirect_stdout(output),
		):
			module.reportError('50%0A.go\r\nhết')
		self.assertEqual(output.getvalue(), '::error::50%250A.go%0D%0Ahết\n')


if __name__ == '__main__':
	unittest.main()
