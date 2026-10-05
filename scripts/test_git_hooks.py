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

	def testToolEnvironmentPinsRepositoryVersions(self):
		# Shim của mise ở thư mục tạm không thấy mise.toml, .nvmrc: hook ghim đúng phiên bản của repository; biến
		# người dùng đã đặt được giữ nguyên.
		ruff = re.search(
			r'^ruff = "([^"]+)"$', (ROOT / 'mise.toml').read_text(encoding='utf-8'), re.MULTILINE
		).group(1)
		node = (ROOT / '.nvmrc').read_text(encoding='utf-8').strip()
		with mock.patch.dict('os.environ', clear=False) as environ:
			environ.pop('MISE_RUFF_VERSION', None)
			environ['MISE_NODE_VERSION'] = '22'
			environment = self.module.toolEnvironment()
		self.assertEqual(environment['MISE_RUFF_VERSION'], ruff)
		self.assertEqual(environment['MISE_NODE_VERSION'], '22')
		with mock.patch.dict('os.environ', clear=False) as environ:
			environ.pop('MISE_NODE_VERSION', None)
			self.assertEqual(self.module.toolEnvironment()['MISE_NODE_VERSION'], node)

	def prePush(self, lines, makeCode=0):
		"""Chạy hook pre-push với các dòng git đưa vào stdin; make check thay bằng lệnh giả trả makeCode, git thật.
		Trả (mã thoát, đã gọi make check chưa)."""
		originalRun, made = subprocess.run, []

		def run(command, *args, **kwargs):
			if command[:2] == ['make', 'check']:
				made.append(command)
				return subprocess.CompletedProcess(command, makeCode)
			return originalRun(command, *args, **kwargs)

		with (
			mock.patch.object(self.module.subprocess, 'run', run),
			mock.patch.object(
				self.module.sys, 'stdin', io.StringIO(''.join(f'{line}\n' for line in lines))
			),
			silenced(),
		):
			code = self.module.prePush(self.repo, [])
		return code, bool(made)

	def testPrePushRunsMakeCheckOnPushedHead(self):
		# Đẩy đúng HEAD, thư mục làm việc sạch: chạy make check, lỗi thì chặn.
		head = self.git('rev-parse', 'HEAD')
		line = f'refs/heads/main {head} refs/heads/main {self.module.ZERO_SHA}'
		self.assertEqual(self.prePush([line]), (0, True))
		self.assertEqual(self.prePush([line], makeCode=2), (1, True))

	def testPrePushBlocksWhatMakeCheckCannotSee(self):
		# make check kiểm tra thư mục làm việc: còn thay đổi chưa commit, hoặc đẩy branch khác HEAD thì chặn mà
		# không chạy make check; chỉ đẩy tag hoặc xóa branch thì bỏ qua.
		head = self.git('rev-parse', 'HEAD')
		zero = self.module.ZERO_SHA
		self.assertEqual(
			self.prePush([f'refs/heads/other {"a" * 40} refs/heads/other {zero}']), (1, False)
		)
		self.assertEqual(self.prePush([f'refs/tags/v1 {head} refs/tags/v1 {zero}']), (0, False))
		(self.repo / 'draft.txt').write_text('chưa commit\n', encoding='utf-8')
		self.assertEqual(
			self.prePush([f'refs/heads/main {head} refs/heads/main {zero}']), (1, False)
		)

	def testPreCommitRunsToolsWithPinnedVersions(self):
		# Prettier, ruff chạy trong thư mục tạm phải nhận môi trường ghim phiên bản — không dựa vào mặc định toàn
		# máy của mise (máy chạy test có thể đã đặt, che mất lỗi).
		(self.repo / 'tool.py').write_text("print('ok')\n", encoding='utf-8')
		self.git('add', 'tool.py')
		originalRun, environments = subprocess.run, []

		def run(command, *args, **kwargs):
			if command[0] in (str(self.module.PRETTIER), 'ruff'):
				environments.append(kwargs.get('env') or {})
				return subprocess.CompletedProcess(command, 0)
			return originalRun(command, *args, **kwargs)

		with (
			# Tệp có thật thay cho Prettier: máy chưa chạy make tools vẫn kiểm tra được môi trường truyền vào.
			mock.patch.object(self.module, 'PRETTIER', Path(__file__)),
			mock.patch.object(self.module.shutil, 'which', return_value='/usr/bin/ruff'),
			mock.patch.object(self.module.subprocess, 'run', run),
			silenced(),
		):
			self.assertEqual(self.module.preCommit(self.repo, []), 0)
		self.assertEqual(len(environments), 3)
		for environment in environments:
			self.assertIn('MISE_RUFF_VERSION', environment)
			self.assertIn('MISE_NODE_VERSION', environment)

	def testPushedBranchesSkipsTagsAndDeletions(self):
		zero = self.module.ZERO_SHA
		lines = [
			f'refs/heads/main {"a" * 40} refs/heads/main {"b" * 40}',
			f'refs/tags/v1 {"c" * 40} refs/tags/v1 {zero}',
			f'(delete) {zero} refs/heads/old {"d" * 40}',
		]
		self.assertEqual(self.module.pushedBranches(lines), [('refs/heads/main', 'a' * 40)])
		self.assertEqual(self.module.pushedBranches(lines[1:]), [])

	def testOldPythonIsReportedBeforeRunningHooks(self):
		# Ứng dụng giao diện trên macOS gọi hook bằng Python 3.9 của hệ thống: báo rõ phiên bản cần, thoát mã 1,
		# không chạy hook nào (post-merge trên 3.9 từng dừng bằng traceback của zip strict).
		output = io.StringIO()
		with (
			mock.patch.object(self.module.sys, 'version_info', (3, 9, 25)),
			mock.patch.object(self.module.sys, 'version', '3.9.25 (main)'),
			mock.patch.object(self.module.sys, 'argv', ['post-merge', '0']),
			mock.patch.object(self.module, 'afterPull') as afterPull,
			contextlib.redirect_stderr(output),
		):
			self.assertEqual(self.module.main(), 1)
		afterPull.assert_not_called()
		self.assertIn('Git hook cần Python ≥ 3.11 (đang dùng 3.9.25)', output.getvalue())

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
			env=self.module.toolEnvironment(),
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
