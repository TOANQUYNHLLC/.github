"""Test tự động cho scripts/release.py: nội dung phát hành, chuyển mục CHƯA PHÁT HÀNH thành phiên bản.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import io
import json
import re
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

RELEASE_FIXTURE = """# NHẬT KÝ THAY ĐỔI

## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github/compare/v2099.01.Stable...HEAD)

### ✨ THÊM

- Mục mới.

---

## [v2099.01.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2099.01.Stable) — 2099-01-01

### ✨ THÊM

- Mục cũ.

---

<p align="center">© 2099</p>
"""


class ReleaseTest(unittest.TestCase):
	def testValidLeapDatePreparesRealRepositoryRelease(self):
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			with (
				mock.patch.object(
					self.module.sys,
					'argv',
					[
						'release.py',
						'prepare',
						'--version',
						'v2104.02.Stable',
						'--date',
						'2104-02-29',
					],
				),
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(self.module.main(), 0)
			changelog = (clone / 'CHANGELOG.md').read_text(encoding='utf-8')
			self.assertIn('— 2104-02-29', changelog)
			self.assertEqual(self.module.unreleasedNotes(changelog), '')
			self.assertEqual(
				self.module.releaseNotes(changelog, 'v2104.02.Stable'), '### ✨ THÊM\n\n- Mục mới.'
			)

	def testInvalidDateLeavesRealRepositoryChangelogUntouched(self):
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			with (
				mock.patch.object(
					self.module.sys,
					'argv',
					[
						'release.py',
						'prepare',
						'--version',
						'v2099.02.Stable',
						'--date',
						'2099-02-29',
					],
				),
				contextlib.redirect_stdout(io.StringIO()) as output,
			):
				self.assertEqual(self.module.main(), 1)
			self.assertIn('Ngày phát hành không có thật', output.getvalue())
			self.assertEqual((clone / 'CHANGELOG.md').read_text(encoding='utf-8'), RELEASE_FIXTURE)
			self.assertEqual(
				subprocess.check_output(['git', 'status', '--porcelain'], cwd=clone), b''
			)

	def testInvalidPreparationInputsDoNotTouchFilesOrRunCommands(self):
		module = loadScript('release')
		cases = (
			('v2099.13.Stable', '2099-01-01'),
			('v2099.00.Stable', '2099-01-01'),
			('v0000.01.Stable', '2099-01-01'),
			('v2099.1.Stable', '2099-01-01'),
			('v2099.01.Stable\n## BROKEN', '2099-01-01'),
			('v2099.01.Stable', '2099-02-29'),
			('v2099.01.Stable', '2099-1-01'),
			('v2099.01.Stable', '2099-01-01\n## BROKEN'),
		)
		with tempfile.TemporaryDirectory() as folder:
			module.ROOT = Path(folder)
			path = module.ROOT / 'CHANGELOG.md'
			path.write_text(RELEASE_FIXTURE, encoding='utf-8')
			for version, date in cases:
				with self.subTest(version=version, date=date):
					with (
						mock.patch.object(
							module.sys,
							'argv',
							[
								'release.py',
								'prepare',
								'--version',
								version,
								'--date',
								date,
								'--open-pr',
							],
						),
						mock.patch.object(module, 'runCommand') as run,
						mock.patch.object(module, 'onCleanMain') as clean,
						contextlib.redirect_stdout(io.StringIO()) as output,
					):
						self.assertEqual(module.main(), 1)
					self.assertIn('❌', output.getvalue())
					self.assertEqual(path.read_text(encoding='utf-8'), RELEASE_FIXTURE)
					run.assert_not_called()
					clean.assert_not_called()

	def testInvalidOpenPrVersionDoesNotCallGitOrGithub(self):
		module = loadScript('release')
		with (
			mock.patch.object(
				module.sys,
				'argv',
				['release.py', 'open-pr', 'v2099.13.Stable', 'v2099.01.Stable', '1'],
			),
			mock.patch.object(module, 'runCommand') as run,
			mock.patch.object(module.github, 'ghExists') as read,
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			self.assertEqual(module.main(), 1)
		self.assertIn('Phiên bản', output.getvalue())
		run.assert_not_called()
		read.assert_not_called()

	def testMalformedExistingReleasePrIsNotReportedAsPending(self):
		module = loadScript('release')
		for data in (None, {}, {'message': 'lỗi'}, [42], [{}], [{'url': None}], [{'url': ''}]):
			with self.subTest(data=data):
				with (
					mock.patch.object(module, 'runCommand', return_value='abc123') as run,
					mock.patch.object(module.github, 'ghExists', return_value=True),
					mock.patch.object(module.github, 'ghJson', return_value=data),
					contextlib.redirect_stdout(io.StringIO()) as output,
				):
					self.assertEqual(
						module.openReleasePullRequest('v2099.02.Stable', 'v2099.01.Stable', 1), 1
					)
				self.assertIn('Không đọc được trạng thái', output.getvalue())
				self.assertNotIn('đang chờ:', output.getvalue())
				self.assertFalse(any(call.args[0] == 'gh' for call in run.call_args_list))

	def testActionMessagesEscapeNewlinesAndPercentSigns(self):
		module = loadScript('release')
		message = 'gh lỗi 50%\r\n::notice::dòng tiếp theo'
		for onActions in (False, True):
			with self.subTest(onActions=onActions):
				output = io.StringIO()
				with (
					mock.patch.dict(
						module.os.environ,
						{'GITHUB_ACTIONS': 'true'} if onActions else {},
						clear=True,
					),
					contextlib.redirect_stdout(output),
				):
					module.reportMessage('error', message)
				self.assertEqual(
					output.getvalue(),
					'::error::gh lỗi 50%25%0D%0A::notice::dòng tiếp theo\n'
					if onActions
					else message + '\n',
				)

	def testUnreadableChangelogDoesNotCreateReleaseBranch(self):
		module = loadScript('release')
		with tempfile.TemporaryDirectory() as folder:
			module.ROOT = Path(folder)
			for content in (None, b'\xff'):
				with self.subTest(content=content):
					if content is not None:
						(module.ROOT / 'CHANGELOG.md').write_bytes(content)
					output = io.StringIO()
					with (
						mock.patch.object(module.github, 'ghExists', return_value=False),
						mock.patch.object(module, 'runCommand', return_value='abc123') as run,
						contextlib.redirect_stdout(output),
					):
						self.assertEqual(
							module.openReleasePullRequest('v2099.02.Stable', 'v2099.01.Stable', 3),
							1,
						)
					self.assertIn('CHANGELOG.md', output.getvalue())
					self.assertFalse(any(call.args[0] == 'gh' for call in run.call_args_list))

	def testNotesReportsUnreadableChangelog(self):
		module = loadScript('release')
		with tempfile.TemporaryDirectory() as folder:
			path = Path(folder) / 'CHANGELOG.md'
			for content in (None, b'\xff'):
				with self.subTest(content=content):
					if content is not None:
						path.write_bytes(content)
					output = io.StringIO()
					with (
						mock.patch.object(
							module.sys,
							'argv',
							['release.py', 'notes', 'v2099.02.Stable', '--changelog', str(path)],
						),
						contextlib.redirect_stdout(output),
					):
						self.assertEqual(module.main(), 1)
					self.assertIn('❌', output.getvalue())

	def setUp(self):
		self.module = loadScript('release')

	def testExtractsVersionNotes(self):
		# Dữ liệu mẫu cố định: nội dung CHANGELOG.md thật thay đổi theo từng lần phát hành.
		notes = self.module.releaseNotes(RELEASE_FIXTURE, 'v2099.01.Stable')
		self.assertEqual(notes, '### ✨ THÊM\n\n- Mục cũ.')
		self.assertNotIn('<p align="center">', notes)
		self.assertNotIn('CHƯA PHÁT HÀNH', notes)
		# CHANGELOG.md thật đọc được mục của mọi phiên bản đã phát hành.
		changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
		for version in re.findall(r'^## \[(v[^\]]+)\]', changelog, re.MULTILINE):
			self.assertTrue(self.module.releaseNotes(changelog, version), version)

	def testMissingVersionReturnsNone(self):
		self.assertIsNone(self.module.releaseNotes(RELEASE_FIXTURE, 'v1999.01.Stable'))

	def testCutsUnreleasedIntoVersion(self):
		# CHANGELOG mẫu cố định: mục CHƯA PHÁT HÀNH của tệp thật trống ngay sau mỗi lần phát hành.
		changelog = self.module.cutRelease(RELEASE_FIXTURE, 'v2099.02.Stable', '2099-02-01')
		self.assertIn(
			'## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github/compare/v2099.02.Stable...HEAD)',
			changelog,
		)
		self.assertIn(
			'## [v2099.02.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2099.02.Stable)'
			' — 2099-02-01',
			changelog,
		)
		# Mục mới trống; nội dung cũ thành nội dung Release của phiên bản mới; phiên bản cũ giữ nguyên.
		self.assertEqual(self.module.unreleasedNotes(changelog), '')
		self.assertEqual(
			self.module.releaseNotes(changelog, 'v2099.02.Stable'), '### ✨ THÊM\n\n- Mục mới.'
		)
		self.assertEqual(
			self.module.releaseNotes(changelog, 'v2099.01.Stable'), '### ✨ THÊM\n\n- Mục cũ.'
		)
		self.assertLess(
			changelog.index('## [v2099.02.Stable]'), changelog.index('## [v2099.01.Stable]')
		)

	def testPrepareWithoutTagReportsClearly(self):
		# Repository chưa có tag v*: báo rõ cần gắn tag đầu tiên, không văng lỗi git.
		with tempfile.TemporaryDirectory() as folder:
			subprocess.run(['git', 'init', '-q'], cwd=folder, check=True)
			subprocess.run(
				[
					'git',
					'-c',
					'user.name=test',
					'-c',
					'user.email=',
					'-c',
					'commit.gpgsign=false',
					'commit',
					'-q',
					'--allow-empty',
					'-m',
					'x',
				],
				cwd=folder,
				check=True,
			)
			self.module.ROOT = Path(folder)
			output = io.StringIO()
			with contextlib.redirect_stdout(output):
				code = self.module.prepareRelease('v2099.01.Stable', '2099-01-01')
		self.assertEqual(code, 1)
		self.assertIn('Chưa có tag v* nào', output.getvalue())

	def releaseClone(self, folder):
		"""Repository có origin, tag v2099.01.Stable và một commit sau tag, đang ở main trùng origin/main."""
		origin, clone = Path(folder) / 'origin.git', Path(folder) / 'clone'
		subprocess.run(['git', 'init', '-q', '--bare', str(origin)], check=True)
		subprocess.run(
			['git', 'clone', '-q', str(origin), str(clone)], capture_output=True, check=True
		)
		(clone / 'CHANGELOG.md').write_text(RELEASE_FIXTURE, encoding='utf-8')
		# Không phụ thuộc cấu hình git của máy (runner chưa đặt danh tính, máy bật ký commit, tag).
		git = ['git', '-c', 'user.name=test', '-c', 'user.email=', '-c', 'commit.gpgsign=false']
		for command in (
			['add', 'CHANGELOG.md'],
			['commit', '-q', '-m', 'đầu'],
			['-c', 'tag.gpgsign=false', 'tag', 'v2099.01.Stable'],
			['commit', '-q', '--allow-empty', '-m', 'sau tag'],
			['branch', '-M', 'main'],
			['push', '-q', 'origin', 'main'],
		):
			subprocess.run([*git, *command], cwd=clone, check=True)
		self.module.ROOT = clone
		return clone

	def testOpenPrRequiresCleanMain(self):
		# make release-pr lấy HEAD làm gốc branch phát hành: đứng ở branch khác main thì dừng trước khi sửa
		# CHANGELOG.md hay gọi GitHub.
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			subprocess.run(['git', 'switch', '-q', '-c', 'feature'], cwd=clone, check=True)
			output = io.StringIO()
			with contextlib.redirect_stdout(output):
				code = self.module.prepareRelease('v2099.02.Stable', '2099-02-01', True)
			self.assertEqual(code, 1)
			self.assertIn('Cần đứng ở main sạch', output.getvalue())
			self.assertEqual((clone / 'CHANGELOG.md').read_text(encoding='utf-8'), RELEASE_FIXTURE)

	def testOpenPrReportsFetchFailure(self):
		# Không tải được origin (mất mạng, sai remote): báo rõ thay vì văng traceback.
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			subprocess.run(
				['git', 'remote', 'set-url', 'origin', str(Path(folder) / 'khong-co.git')],
				cwd=clone,
				check=True,
			)
			output = io.StringIO()
			with contextlib.redirect_stdout(output):
				code = self.module.prepareRelease('v2099.02.Stable', '2099-02-01', True)
			self.assertEqual(code, 1)
			self.assertIn('Không tải được origin/main', output.getvalue())

	def testOpenPrCommitsPreparedChangelogThenRestores(self):
		# make release-pr: mở Pull Request với CHANGELOG.md đã chuyển phiên bản, rồi trả tệp tại máy về như cũ.
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			opened = []

			def openPullRequest(version, previous, commits):
				changelog = (clone / 'CHANGELOG.md').read_text(encoding='utf-8')
				opened.append((version, previous, commits, '## [v2099.02.Stable]' in changelog))
				return 0

			with (
				mock.patch.object(self.module, 'openReleasePullRequest', openPullRequest),
				contextlib.redirect_stdout(io.StringIO()),
			):
				code = self.module.prepareRelease('v2099.02.Stable', '2099-02-01', True)
			self.assertEqual(code, 0)
			self.assertEqual(opened, [('v2099.02.Stable', 'v2099.01.Stable', 1, True)])
			self.assertEqual((clone / 'CHANGELOG.md').read_text(encoding='utf-8'), RELEASE_FIXTURE)

	def testOpenPrDeletesBranchWhenCommitFails(self):
		# GitHub từ chối commit (mất quyền, lỗi mạng): xóa branch vừa tạo để lần chạy sau không bỏ qua vì
		# "branch đã có", không mở Pull Request.
		calls = []

		def fakeRun(args, **kwargs):
			calls.append(args)
			if args[:3] == ['git', 'rev-parse', 'HEAD']:
				return subprocess.CompletedProcess(args, 0, 'abc123\n', '')
			if args[:2] == ['gh', 'api'] and args[2].endswith('/branches/release/v2099.02'):
				return subprocess.CompletedProcess(args, 1, '', 'Not Found (HTTP 404)')
			if args[:3] == ['gh', 'api', 'graphql']:
				raise subprocess.CalledProcessError(1, args, '', 'Resource not accessible\n')
			return subprocess.CompletedProcess(args, 0, '', '')

		output = io.StringIO()
		with (
			mock.patch.object(self.module.subprocess, 'run', fakeRun),
			# Biến rỗng (đặt mà không có giá trị) vẫn dùng repository mặc định.
			mock.patch.dict(self.module.os.environ, {'GITHUB_REPOSITORY': ''}),
			contextlib.redirect_stdout(output),
		):
			code = self.module.openReleasePullRequest('v2099.02.Stable', 'v2099.01.Stable', 3)
		self.assertEqual(code, 1)
		self.assertIn('Không commit được CHANGELOG.md lên release/v2099.02', output.getvalue())
		self.assertIn(
			[
				'gh',
				'api',
				'-X',
				'DELETE',
				'repos/TOANQUYNHLLC/.github/git/refs/heads/release/v2099.02',
				'--silent',
			],
			calls,
		)
		self.assertFalse([call for call in calls if call[:3] == ['gh', 'pr', 'create']])

	def testOpenPrReadFailureDoesNotCreateBranch(self):
		def run(args, **kwargs):
			if args[0] == 'git':
				return subprocess.CompletedProcess(args, 0, 'abc123', '')
			self.assertTrue('/branches/' in args[2], args)
			return subprocess.CompletedProcess(args, 1, '', 'Forbidden (HTTP 403)')

		output = io.StringIO()
		with (
			mock.patch.object(self.module.subprocess, 'run', run),
			contextlib.redirect_stdout(output),
		):
			code = self.module.openReleasePullRequest('v2099.02.Stable', 'v2099.01.Stable', 3)
		self.assertEqual(code, 1)
		self.assertIn('HTTP 403', output.getvalue())

	def testExistingReleaseBranchWithoutPrReportsFailure(self):
		def run(args, **kwargs):
			if args[0] == 'git':
				return subprocess.CompletedProcess(args, 0, 'abc123', '')
			if args[:3] == ['gh', 'pr', 'list']:
				return subprocess.CompletedProcess(args, 0, '[]', '')
			self.assertTrue('/branches/' in args[2], args)
			return subprocess.CompletedProcess(args, 0, '', '')

		output = io.StringIO()
		with (
			mock.patch.object(self.module.subprocess, 'run', run),
			contextlib.redirect_stdout(output),
		):
			code = self.module.openReleasePullRequest('v2099.02.Stable', 'v2099.01.Stable', 3)
		self.assertEqual(code, 1)
		self.assertIn('chưa có Pull Request đang mở', output.getvalue())
		self.assertIn('compare/main...release/v2099.02', output.getvalue())

	def testExistingReleasePrIsReportedWithUrl(self):
		url = 'https://github.com/TOANQUYNHLLC/.github/pull/123'

		def run(args, **kwargs):
			if args[0] == 'git':
				return subprocess.CompletedProcess(args, 0, 'abc123', '')
			if args[:3] == ['gh', 'pr', 'list']:
				return subprocess.CompletedProcess(args, 0, json.dumps([{'url': url}]), '')
			self.assertTrue('/branches/' in args[2], args)
			return subprocess.CompletedProcess(args, 0, '', '')

		output = io.StringIO()
		with (
			mock.patch.object(self.module.subprocess, 'run', run),
			contextlib.redirect_stdout(output),
		):
			code = self.module.openReleasePullRequest('v2099.02.Stable', 'v2099.01.Stable', 3)
		self.assertEqual(code, 0)
		self.assertIn(url, output.getvalue())

	def testCommitAndCleanupFailureDoesNotClaimBranchDeleted(self):
		def run(args, **kwargs):
			if args[0] == 'git':
				return subprocess.CompletedProcess(args, 0, 'abc123', '')
			if '/branches/' in args[2]:
				return subprocess.CompletedProcess(args, 1, '', 'Not Found (HTTP 404)')
			if args[:3] == ['gh', 'api', 'graphql']:
				raise subprocess.CalledProcessError(1, args, '', 'lỗi commit')
			if 'DELETE' in args:
				return subprocess.CompletedProcess(args, 1, '', 'lỗi xóa (HTTP 403)')
			return subprocess.CompletedProcess(args, 0, '', '')

		output = io.StringIO()
		with (
			mock.patch.object(self.module.subprocess, 'run', run),
			contextlib.redirect_stdout(output),
		):
			code = self.module.openReleasePullRequest('v2099.02.Stable', 'v2099.01.Stable', 3)
		self.assertEqual(code, 1)
		self.assertNotIn('đã xóa branch', output.getvalue())
		self.assertIn('chưa xóa được branch', output.getvalue())
		self.assertIn('HTTP 403', output.getvalue())

	def testEmptyUnreleasedSection(self):
		changelog = self.module.cutRelease(RELEASE_FIXTURE, 'v2099.02.Stable', '2099-02-01')
		self.assertEqual(self.module.unreleasedNotes(changelog), '')
		self.assertIsNone(self.module.releaseNotes(changelog, 'CHƯA PHÁT HÀNH'))
		self.assertIsNone(self.module.unreleasedNotes('# NHẬT KÝ\n'))


if __name__ == '__main__':
	unittest.main()
