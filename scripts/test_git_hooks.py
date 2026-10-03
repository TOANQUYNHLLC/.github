"""Test tự động cho scripts/git-hooks.py: cài hook, danh sách ref của pre-push, pre-commit kiểm tra phần đã stage.

Chạy: python3 -m unittest discover -s scripts -p 'test_*.py'   (hoặc: make test)
"""

import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import ROOT, loadScript
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript


class GitHooksTest(unittest.TestCase):
	def setUp(self):
		self.module = loadScript('git-hooks')
		self.tmp = tempfile.TemporaryDirectory()
		self.repo = Path(self.tmp.name)
		self.git('init', '-q')
		for name in self.module.FORMAT_CONFIGS:
			shutil.copy2(ROOT / name, self.repo / name)
		self.git('add', '-A')
		self.git('-c', 'commit.gpgsign=false', 'commit', '-qm', 'init')

	def tearDown(self):
		self.tmp.cleanup()

	def git(self, *args):
		return subprocess.run(
			['git', *args], cwd=self.repo, capture_output=True, text=True, check=True
		).stdout.strip()

	def testPushedBranchesSkipsTagsAndDeletions(self):
		zero = self.module.ZERO_SHA
		lines = [
			f'refs/heads/main {"a" * 40} refs/heads/main {"b" * 40}',
			f'refs/tags/v1 {"c" * 40} refs/tags/v1 {zero}',
			f'(delete) {zero} refs/heads/old {"d" * 40}',
		]
		self.assertEqual(self.module.pushedBranches(lines), [('refs/heads/main', 'a' * 40)])
		self.assertEqual(self.module.pushedBranches(lines[1:]), [])

	def testInstallLinksEveryHookAndWarnsHooksPath(self):
		self.git('config', 'core.hooksPath', '.husky')
		output = io.StringIO()
		with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(output):
			self.module.installHooks(self.repo)
		self.assertIn('core.hooksPath = .husky', output.getvalue())
		for name in self.module.HOOKS:
			link = self.repo / '.git' / 'hooks' / name
			self.assertEqual(link.resolve(), self.module.SCRIPT, name)

	@unittest.skipUnless(
		(ROOT / 'node_modules' / '.bin' / 'prettier').exists(), 'cần Prettier (make tools)'
	)
	def testPreCommitChecksStagedContent(self):
		# Stage nội dung sai định dạng, sửa tệp trên đĩa cho đúng: hook vẫn phải chặn — và ngược lại.
		path = self.repo / 'a.md'
		path.write_text('#  Tiêu đề\n\n*  mục\n', encoding='utf-8')
		self.git('add', 'a.md')
		path.write_text('# Tiêu đề\n\n- mục\n', encoding='utf-8')
		with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
			self.assertEqual(self.module.preCommit(self.repo, []), 1)
			self.git('add', 'a.md')
			path.write_text('#  sai\n', encoding='utf-8')
			self.assertEqual(self.module.preCommit(self.repo, []), 0)

	def testAfterPullReportsWithoutBlocking(self):
		# Sau khi kéo code: org-preview chỉ chạy khi gh đã đăng nhập; links, versions luôn chạy; lệnh lỗi chỉ báo.
		for signedIn, expected in (
			(True, ['org-preview', 'links', 'versions']),
			(False, ['links', 'versions']),
		):
			called = []

			def run(command, *args, signedIn=signedIn, called=called, **kwargs):
				if command[0] == 'make':
					called.append(command[1])
				return subprocess.CompletedProcess(command, 0 if signedIn else 1)

			# subprocess, shutil của script là module dùng chung — vá tạm bằng mock.patch để tự hoàn lại.
			with (
				mock.patch.object(self.module, 'installHooks', return_value=0),
				mock.patch.object(self.module.shutil, 'which', return_value='/usr/bin/gh'),
				mock.patch.object(self.module.subprocess, 'run', run),
				contextlib.redirect_stdout(io.StringIO()),
				contextlib.redirect_stderr(io.StringIO()),
			):
				self.assertEqual(self.module.afterPull(self.repo), 0)
			self.assertEqual(called, expected)


if __name__ == '__main__':
	unittest.main()
