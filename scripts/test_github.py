"""Kiểm thử gọi GitHub CLI phục vụ phát hành, phân biệt lỗi đọc với tài nguyên thiếu."""

import unittest
from unittest import mock

try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript

github = loadScript('github')


class GitHubTest(unittest.TestCase):
	def testExistenceCheckDistinguishesMissingFromReadErrors(self):
		for message in ('HTTP 403', 'HTTP 429', 'HTTP 500', 'mất mạng', 'HTTP 4040'):
			with (
				self.subTest(message=message),
				mock.patch.object(github, 'gh', side_effect=RuntimeError(message)),
				self.assertRaisesRegex(RuntimeError, message),
			):
				github.ghExists('repos/o/r/contents/file')
		with mock.patch.object(github, 'gh', side_effect=RuntimeError('Not Found (HTTP 404)')):
			self.assertFalse(github.ghExists('repos/o/r/contents/file'))


if __name__ == '__main__':
	unittest.main()
