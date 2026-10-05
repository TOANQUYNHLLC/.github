"""Test tự động cho scripts/git-hooks.py: cài hook, danh sách ref của pre-push, pre-commit kiểm tra phần đã stage.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import io
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import ROOT, loadScript, silenced
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript, silenced


class GitHooksTest(unittest.TestCase):
	@unittest.skipUnless(
		(ROOT / 'node_modules/.bin/prettier').exists(), 'cần Prettier (make tools)'
	)
	def testPreCommitUsesIndexedConfigWhenWorkingCopyIsDeleted(self):
		(self.repo / 'a.json').write_text('{\n\t"a": 1\n}\n', encoding='utf-8')
		self.git('add', 'a.json')
		for name in ('.prettierrc.json', '.editorconfig'):
			(self.repo / name).unlink()
		with silenced():
			self.assertEqual(self.module.preCommit(self.repo, []), 0)

	def testPreCommitStopsWhenIndexCannotBeExported(self):
		(self.repo / 'a.md').write_text('# A\n', encoding='utf-8')
		self.git('add', 'a.md')
		originalRun = subprocess.run
		formatterCalls = []

		def run(command, **kwargs):
			if command[:2] == ['git', 'checkout-index']:
				return subprocess.CompletedProcess(command, 1, b'', b'index error')
			if command[0] != 'git':
				formatterCalls.append(command)
				return subprocess.CompletedProcess(command, 0)
			return originalRun(command, **kwargs)

		with mock.patch.object(self.module.subprocess, 'run', run), silenced():
			self.assertEqual(self.module.preCommit(self.repo, []), 1)
		self.assertEqual(formatterCalls, [])

	def setUp(self):
		self.module = loadScript('git-hooks')
		self.tmp = tempfile.TemporaryDirectory()
		self.repo = Path(self.tmp.name)
		self.git('init', '-q')
		for name in self.module.FORMAT_CONFIGS:
			shutil.copy2(ROOT / name, self.repo / name)
		self.git('add', '-A')
		# Không phụ thuộc cấu hình git của máy (runner chưa đặt danh tính, máy bật ký commit).
		self.git(
			'-c',
			'user.name=test',
			'-c',
			'user.email=',
			'-c',
			'commit.gpgsign=false',
			'commit',
			'-qm',
			'init',
		)

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

	def testOutsideRepositoryReportsGitError(self):
		# Không phải repository git (hoặc git từ chối vì dubious ownership): in đúng lời git, thoát mã 1, không
		# traceback.
		output = io.StringIO()
		with (
			tempfile.TemporaryDirectory() as folder,
			contextlib.chdir(folder),
			mock.patch.object(self.module.sys, 'argv', ['git-hooks.py', 'install']),
			mock.patch.dict('os.environ', {'GIT_CEILING_DIRECTORIES': str(Path(folder).parent)}),
			contextlib.redirect_stderr(output),
		):
			self.assertEqual(self.module.main(), 1)
		self.assertRegex(output.getvalue(), r'^❌ fatal: not a git repository')

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
		with silenced():
			self.assertEqual(self.module.preCommit(self.repo, []), 1)
			self.git('add', 'a.md')
			path.write_text('#  sai\n', encoding='utf-8')
			self.assertEqual(self.module.preCommit(self.repo, []), 0)

	@unittest.skipUnless(
		(ROOT / 'node_modules' / '.bin' / 'prettier').exists() and shutil.which('ruff'),
		'cần Prettier (make tools) và ruff (mise install)',
	)
	def testPreCommitRunsRuffCheck(self):
		# Tệp Python đúng định dạng nhưng còn lỗi lint (import thừa): hook chặn như nhóm format của make check.
		path = self.repo / 'tool.py'
		path.write_text('import os\n', encoding='utf-8')
		self.git('add', 'tool.py')
		with silenced():
			self.assertEqual(self.module.preCommit(self.repo, []), 1)
			path.write_text("print('ok')\n", encoding='utf-8')
			self.git('add', 'tool.py')
			self.assertEqual(self.module.preCommit(self.repo, []), 0)

	@unittest.skipUnless(
		(ROOT / 'node_modules' / '.bin' / 'prettier').exists() and shutil.which('ruff'),
		'cần Prettier (make tools) và ruff (mise install)',
	)
	def testPreCommitSortsImportsWithUnstagedPackageFiles(self):
		# Chỉ stage một tệp trong gói (như scripts/validation/docs.py): ruff vẫn phải thấy __init__.py và module
		# cùng gói đã commit để nhận gói là của repository — nếu không, thứ tự import đúng bị báo I001.
		package = self.repo / 'tools' / 'checks'
		package.mkdir(parents=True)
		(package / '__init__.py').write_text('', encoding='utf-8')
		(package / 'common.py').write_text('VALUE = 1\n', encoding='utf-8')
		self.git('add', 'tools')
		self.git(
			'-c',
			'user.name=test',
			'-c',
			'user.email=',
			'-c',
			'commit.gpgsign=false',
			'commit',
			'-qm',
			'gói',
		)
		(package / 'docs.py').write_text(
			'import re\n\nfrom markdown import render\n\nfrom checks.common import VALUE\n\n'
			'print(re, render, VALUE)\n',
			encoding='utf-8',
		)
		self.git('add', 'tools/checks/docs.py')
		result = subprocess.run(
			['ruff', 'check', '--select', 'I001', 'tools/checks/docs.py'],
			cwd=self.repo,
			capture_output=True,
			check=False,
		)
		self.assertEqual(result.returncode, 0, 'thứ tự import trong test phải đúng tại repository')
		with silenced():
			self.assertEqual(self.module.preCommit(self.repo, []), 0)

	@unittest.skipUnless(
		(ROOT / 'node_modules' / '.bin' / 'prettier').exists(), 'cần Prettier (make tools)'
	)
	def testPreCommitWithoutRuffBlocksClearly(self):
		path = self.repo / 'tool.py'
		path.write_text("print('ok')\n", encoding='utf-8')
		self.git('add', 'tool.py')
		which = shutil.which
		with (
			mock.patch.object(
				self.module.shutil, 'which', lambda name: None if name == 'ruff' else which(name)
			),
			silenced(),
		):
			self.assertEqual(self.module.preCommit(self.repo, []), 1)

	def testAfterPullReportsWithoutBlocking(self):
		# Sau khi kéo code: org-preview chỉ chạy khi gh đã đăng nhập; links, versions luôn chạy; chạy song song
		# nhưng in theo thứ tự; lệnh lỗi chỉ báo, không chặn.
		for signedIn, expected in (
			(True, ['org-preview', 'links', 'versions']),
			(False, ['links', 'versions']),
		):

			def run(command, *args, signedIn=signedIn, **kwargs):
				code = 0 if signedIn else 1
				return subprocess.CompletedProcess(command, code, f'kết quả {command[-1]}\n', '')

			output = io.StringIO()
			# subprocess, shutil của script là module dùng chung — vá tạm bằng mock.patch để tự hoàn lại.
			with (
				mock.patch.object(self.module, 'installHooks', return_value=0),
				mock.patch.object(self.module.shutil, 'which', return_value='/usr/bin/gh'),
				mock.patch.object(self.module.subprocess, 'run', run),
				contextlib.redirect_stdout(output),
				contextlib.redirect_stderr(io.StringIO()),
			):
				self.assertEqual(self.module.afterPull(self.repo), 0)
			self.assertEqual(
				re.findall(r'^kết quả (\S+)$', output.getvalue(), re.MULTILINE), expected
			)


if __name__ == '__main__':
	unittest.main()
