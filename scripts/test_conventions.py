"""Test tự động cho scripts/conventions.py: tên branch, tiêu đề Pull Request/commit.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import io
import subprocess
import unittest
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript


class ConventionsTest(unittest.TestCase):
	def testTitlesEnforceDocumentedLimits(self):
		for title in (
			'fix: ',
			'fix:   ',
			'fix: mô tả\ndòng khác',
			'fix: mô tả\rdòng khác',
			'fix: mô tả\r',
			'fix: mô tả\u2028',
			'fix: kết thúc.',
			'fix: kết thúc. ',
			'fix: ' + 'a' * 68,
		):
			with self.subTest(title=title):
				self.assertFalse(self.check(self.module.checkTitle, title))
		self.assertTrue(self.check(self.module.checkTitle, 'fix: ' + 'a' * 67))

	def testActionsErrorIsOneEncodedAnnotation(self):
		output = io.StringIO()
		with (
			mock.patch.dict(self.module.os.environ, {'GITHUB_ACTIONS': 'true'}),
			contextlib.redirect_stdout(output),
		):
			self.module.reportError('mô tả 100%\r\ndòng khác')
		self.assertEqual(output.getvalue(), '::error::mô tả 100%25%0D%0Adòng khác\n')

	def testGitLogFailureWithExistingBaseIsNotSkipped(self):
		responses = [
			subprocess.CompletedProcess([], 128, '', 'fatal: broken repository'),
			subprocess.CompletedProcess([], 0, 'abc123\n', ''),
		]
		with (
			mock.patch.object(self.module.sys, 'argv', ['conventions.py', 'title']),
			mock.patch.object(self.module.subprocess, 'run', side_effect=responses),
			contextlib.redirect_stdout(io.StringIO()),
			contextlib.redirect_stderr(io.StringIO()),
		):
			self.assertEqual(self.module.main(), 1)

	def testExplicitEmptyTitleDoesNotCheckLocalHistory(self):
		with (
			mock.patch.object(self.module.sys, 'argv', ['conventions.py', 'title', '']),
			mock.patch.object(self.module, 'gitOutput') as git,
			contextlib.redirect_stderr(io.StringIO()),
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(self.module.main(), 1)
		git.assert_not_called()

	def testGitErrorsCannotReportSuccess(self):
		for kind in ('branch', 'title'):
			with (
				self.subTest(kind=kind),
				mock.patch.object(self.module.sys, 'argv', ['conventions.py', kind]),
				mock.patch.object(
					self.module.subprocess,
					'run',
					return_value=subprocess.CompletedProcess(
						[], 128, '', 'fatal: not a git repository'
					),
				),
				contextlib.redirect_stderr(io.StringIO()),
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(self.module.main(), 1)

	def testNoCommitsNeedsOnlyOneGitCommand(self):
		with (
			mock.patch.object(self.module.sys, 'argv', ['conventions.py', 'title']),
			mock.patch.object(
				self.module.subprocess,
				'run',
				return_value=subprocess.CompletedProcess([], 0, '', ''),
			) as run,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(self.module.main(), 0)
		self.assertEqual(run.call_count, 1)

	def testMissingOriginMainIsReportedExplicitly(self):
		output = io.StringIO()
		responses = [
			subprocess.CompletedProcess([], 128, '', 'unknown revision origin/main..HEAD'),
			subprocess.CompletedProcess([], 1, '', ''),
		]
		with (
			mock.patch.object(self.module.sys, 'argv', ['conventions.py', 'title']),
			mock.patch.object(self.module.subprocess, 'run', side_effect=responses),
			contextlib.redirect_stdout(output),
		):
			self.assertEqual(self.module.main(), 0)
		self.assertIn('chưa có origin/main', output.getvalue())

	def setUp(self):
		self.module = loadScript('conventions')

	def check(self, function, value):
		with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
			return function(value)

	def testBranchNames(self):
		for name in ('feature/appointment_booking', 'fix/123_login_error', 'release/v2026.10'):
			self.assertTrue(self.check(self.module.checkBranch, name), name)
		for name in (
			'feat/x',
			'feature/Booking',
			'feature/appointment-booking',
			'chore',
			'fix/example\n',
		):
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
