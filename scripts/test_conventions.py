"""Test tự động cho scripts/conventions.py: tên branch, tiêu đề Pull Request/commit.

Chạy: python3 -m unittest discover -s scripts -p 'test_*.py'   (hoặc: make test)
"""

import contextlib
import io
import unittest

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript


class ConventionsTest(unittest.TestCase):
	def setUp(self):
		self.module = loadScript('conventions')

	def check(self, function, value):
		with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
			return function(value)

	def testBranchNames(self):
		for name in ('feature/appointment_booking', 'fix/123_login_error', 'release/v2026.10'):
			self.assertTrue(self.check(self.module.checkBranch, name), name)
		for name in ('feat/x', 'feature/Booking', 'feature/appointment-booking', 'chore'):
			self.assertFalse(self.check(self.module.checkBranch, name), name)
		# Branch của Dependabot và nhánh chính được bỏ qua.
		self.assertTrue(self.check(self.module.checkBranch, 'dependabot/npm_and_yarn/x-1.0'))
		self.assertTrue(self.check(self.module.checkBranch, 'main'))
		# HEAD không ở branch nào (đang rebase): không có tên để kiểm tra, không báo lỗi.
		self.assertTrue(self.check(self.module.checkBranch, ''))

	def testTitles(self):
		for title in ('feat: thêm', 'fix(booking)!: sửa', 'revert: feat: thêm'):
			self.assertTrue(self.check(self.module.checkTitle, title), title)
		for title in ('Sửa lỗi', 'feature: thêm', 'fix(Booking): sửa', 'fix:thiếu dấu cách'):
			self.assertFalse(self.check(self.module.checkTitle, title), title)


if __name__ == '__main__':
	unittest.main()
