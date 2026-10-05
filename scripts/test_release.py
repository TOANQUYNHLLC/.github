"""Test tự động cho scripts/release.py: nội dung phát hành, chuyển mục CHƯA PHÁT HÀNH thành phiên bản.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import io
import json
import re
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
	def testDefaultPreparationStartsAtOneAfterLegacyTag(self):
		# Tag v* đã phát hành là tag trước để đếm commit; số thứ tự của tháng bắt đầu từ 0001. CHANGELOG.md chỉ giữ
		# mục của phiên bản đang chuẩn bị, bỏ mục phiên bản trước (lịch sử nằm ở GitHub Release).
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			outputs = Path(folder) / 'outputs'
			with (
				mock.patch.object(
					self.module.sys, 'argv', ['release.py', 'prepare', '--date', '2099-02-01']
				),
				mock.patch.dict(self.module.os.environ, {'GITHUB_OUTPUT': str(outputs)}),
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(self.module.main(), 0)
			changelog = (clone / 'CHANGELOG.md').read_text(encoding='utf-8')
			self.assertEqual(
				self.module.releaseNotes(changelog, 'Stable.v2099.02.010001'),
				'### ✨ THÊM\n\n- Mục mới.',
			)
			self.assertIsNone(self.module.releaseNotes(changelog, 'v2099.01.Stable'))
			self.assertTrue(changelog.endswith('---\n\n<p align="center">© 2099</p>\n'))
			self.assertEqual(
				outputs.read_text(encoding='utf-8'),
				'version=Stable.v2099.02.010001\nprevious=v2099.01.Stable\ncommits=1\n',
			)

	def testDefaultVersionIncrementsHighestSequenceWithinMonth(self):
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			for tag in (
				'Stable.v2099.01.019999',
				'Beta.v2099.02.010010',
				'Stable.v2099.02.030002',
				'Stable.v2099.03.010050',
				'Stable.v2099.02.010000',
				'Stable.v2099.02.019999extra',
				'Stable.v2099.02.01999',
				'Stable.v2099.02.0110000',
				'Beta.v2099.02.309999',
				'Gamma.v2099.02.019999',
				'Stable.v2099.05.019998',
			):
				subprocess.run(
					['git', '-c', 'tag.gpgsign=false', 'tag', tag], cwd=clone, check=True
				)
			self.assertEqual(self.module.nextReleaseVersion('2099-02-01'), 'Stable.v2099.02.010011')
			self.assertEqual(self.module.nextReleaseVersion('2099-02-04'), 'Stable.v2099.02.040011')
			self.assertEqual(
				self.module.nextReleaseVersion('2099-02-04', 'Beta'), 'Beta.v2099.02.040011'
			)
			self.assertEqual(self.module.nextReleaseVersion('2099-04-01'), 'Stable.v2099.04.010001')
			self.assertEqual(
				self.module.nextReleaseVersion('2099-04-01', 'Beta'), 'Beta.v2099.04.010001'
			)
			self.assertEqual(self.module.nextReleaseVersion('2099-05-01'), 'Stable.v2099.05.019999')

	def testMonthTagsTakeSequenceNumbers(self):
		# Release bất biến gắn tag vYYYY.MM.<kênh>: mỗi tag là một lần phát hành của tháng, bản kế tiếp không dùng
		# lại số đã phát hành. Tag sai dạng, tháng khác không tính.
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			for tag in ('v2099.06.Stable', 'v2099.07.Stable', 'v2099.07.Beta', 'v2099.08.Gamma'):
				subprocess.run(
					['git', '-c', 'tag.gpgsign=false', 'tag', tag], cwd=clone, check=True
				)
			self.assertEqual(self.module.nextReleaseVersion('2099-06-05'), 'Stable.v2099.06.050002')
			self.assertEqual(self.module.nextReleaseVersion('2099-07-01'), 'Stable.v2099.07.010003')
			self.assertEqual(self.module.nextReleaseVersion('2099-08-01'), 'Stable.v2099.08.010001')
			subprocess.run(
				['git', '-c', 'tag.gpgsign=false', 'tag', 'Beta.v2099.06.100002'],
				cwd=clone,
				check=True,
			)
			self.assertEqual(self.module.nextReleaseVersion('2099-06-12'), 'Stable.v2099.06.120003')

	def testInvalidDefaultDateDoesNotCallGitOrChangeChangelog(self):
		with tempfile.TemporaryDirectory() as folder:
			self.module.ROOT = Path(folder)
			path = self.module.ROOT / 'CHANGELOG.md'
			path.write_text(RELEASE_FIXTURE, encoding='utf-8')
			for date in ('2099-02-29', '2099-1-01', '20990101', '0000-01-01'):
				with self.subTest(date=date):
					with (
						mock.patch.object(
							self.module.sys,
							'argv',
							['release.py', 'prepare', '--date', date, '--open-pr'],
						),
						mock.patch.object(self.module, 'runCommand') as run,
						mock.patch.object(self.module, 'onCleanMain') as clean,
						contextlib.redirect_stdout(io.StringIO()) as output,
					):
						self.assertEqual(self.module.main(), 1)
					self.assertIn('Ngày phát hành', output.getvalue())
					run.assert_not_called()
					clean.assert_not_called()
					self.assertEqual(path.read_text(encoding='utf-8'), RELEASE_FIXTURE)

	def testDefaultSequenceOverflowDoesNotChangeChangelog(self):
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			subprocess.run(
				['git', '-c', 'tag.gpgsign=false', 'tag', 'Stable.v2099.02.019999'],
				cwd=clone,
				check=True,
			)
			with (
				mock.patch.object(
					self.module.sys, 'argv', ['release.py', 'prepare', '--date', '2099-02-01']
				),
				contextlib.redirect_stdout(io.StringIO()) as output,
			):
				self.assertEqual(self.module.main(), 1)
			self.assertIn('đã đạt 9999', output.getvalue())
			self.assertEqual((clone / 'CHANGELOG.md').read_text(encoding='utf-8'), RELEASE_FIXTURE)
			self.assertEqual(
				subprocess.check_output(['git', 'status', '--porcelain'], cwd=clone), b''
			)

	def testDefaultOpenPrSelectsSequenceAfterFetchingTags(self):
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			origin = Path(folder) / 'origin.git'
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
					'chuẩn bị',
				],
				cwd=clone,
				check=True,
			)
			subprocess.run(['git', 'push', '-q', 'origin', 'main'], cwd=clone, check=True)
			subprocess.run(
				['git', '-c', 'tag.gpgsign=false', 'tag', 'Beta.v2099.02.010003', 'main~1'],
				cwd=origin,
				check=True,
			)
			with (
				mock.patch.object(self.module, 'openReleasePullRequest', return_value=0) as openPr,
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(self.module.prepareRelease(None, '2099-02-01', True), 0)
			openPr.assert_called_once_with('Stable.v2099.02.010004', 'Beta.v2099.02.010003', 1)
			self.assertEqual((clone / 'CHANGELOG.md').read_text(encoding='utf-8'), RELEASE_FIXTURE)

	def testExistingNewFormatTagSkipsPreparation(self):
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			subprocess.run(
				['git', '-c', 'tag.gpgsign=false', 'tag', 'Stable.v2099.02.010001'],
				cwd=clone,
				check=True,
			)
			with contextlib.redirect_stdout(io.StringIO()) as output:
				self.assertEqual(
					self.module.prepareRelease('Stable.v2099.02.010001', '2099-02-01'), 0
				)
			self.assertIn('Đã có tag', output.getvalue())
			self.assertEqual((clone / 'CHANGELOG.md').read_text(encoding='utf-8'), RELEASE_FIXTURE)

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
						'Stable.v2104.02.290001',
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
				self.module.releaseNotes(changelog, 'Stable.v2104.02.290001'),
				'### ✨ THÊM\n\n- Mục mới.',
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
						'Stable.v2099.02.010001',
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
			('v2099.01.Stable', '2099-01-01'),
			('v2099.01.Stable.000001', '2099-01-01'),
			('Gamma.v2099.01.010001', '2099-01-01'),
			('stable.v2099.01.010001', '2099-01-01'),
			('Stable.v2099.02.290001', '2099-02-28'),
			('Beta.v2099.04.310001', '2099-04-30'),
			('Stable.v2099.01.000001', '2099-01-01'),
			('Stable.v2099.01.320001', '2099-01-01'),
			('Stable.v2099.01.020001', '2099-01-01'),
			('Stable.v2099.01.010000', '2099-01-01'),
			('Stable.v2099.01.01001', '2099-01-01'),
			('Stable.v2099.01.0110000', '2099-01-01'),
			('Stable.v2099.01.01abcd', '2099-01-01'),
			('Stable.v2099.01.01０００１', '2099-01-01'),
			('Stable.v2099.13.010001', '2099-01-01'),
			('Stable.v2099.00.010001', '2099-01-01'),
			('Stable.v0000.01.010001', '2099-01-01'),
			('Stable.v2099.1.010001', '2099-01-01'),
			('Stable.v2099.01.010001\n## BROKEN', '2099-01-01'),
			('Stable.v2099.01.010001', '2099-02-29'),
			('Stable.v2099.01.010001', '2099-1-01'),
			('Stable.v2099.01.010001', '2099-01-01\n## BROKEN'),
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
				['release.py', 'open-pr', 'Stable.v2099.13.010001', 'v2099.01.Stable', '1'],
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
						module.openReleasePullRequest(
							'Stable.v2099.02.010001', 'v2099.01.Stable', 1
						),
						1,
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
							module.openReleasePullRequest(
								'Stable.v2099.02.010001', 'v2099.01.Stable', 3
							),
							1,
						)
					self.assertIn('CHANGELOG.md', output.getvalue())
					self.assertFalse(any(call.args[0] == 'gh' for call in run.call_args_list))

	def testNotesOfPublishedTagPointToGithubRelease(self):
		# CHANGELOG.md không giữ mục của phiên bản đã phát hành: tag đã có thì chỉ tới GitHub Release (mã 0); tag
		# chưa có thì vẫn báo cần chuẩn bị nội dung (mã 1).
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			changelog = clone / 'CHANGELOG.md'
			changelog.write_text(
				RELEASE_FIXTURE[: RELEASE_FIXTURE.index('## [v2099.01.Stable]')], encoding='utf-8'
			)
			for tag, code, expected in (
				(
					'v2099.01.Stable',
					0,
					'https://github.com/TOANQUYNHLLC/.github/releases/tag/v2099.01.Stable',
				),
				('Stable.v2099.02.010001', 1, 'hãy chuyển nội dung CHƯA PHÁT HÀNH'),
			):
				with self.subTest(tag=tag):
					output = io.StringIO()
					with (
						mock.patch.dict(self.module.os.environ, {'GITHUB_REPOSITORY': ''}),
						contextlib.redirect_stdout(output),
						contextlib.redirect_stderr(output),
					):
						self.assertEqual(self.module.printNotes(tag, changelog), code)
					self.assertIn(expected, output.getvalue())

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
							[
								'release.py',
								'notes',
								'Stable.v2099.02.010001',
								'--changelog',
								str(path),
							],
						),
						contextlib.redirect_stdout(output),
					):
						self.assertEqual(module.main(), 1)
					self.assertIn('❌', output.getvalue())

	@classmethod
	def setUpClass(cls):
		# Repository mẫu cho releaseClone() dựng một lần mỗi tiến trình: dựng bằng git mất khoảng 0,2 giây, chép lại
		# chỉ vài chục mili giây.
		cls.templates = tempfile.TemporaryDirectory()
		cls.addClassCleanup(cls.templates.cleanup)

	def setUp(self):
		self.module = loadScript('release')

	def testBetaChannelPreparesCorrectDate(self):
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			with (
				mock.patch.object(
					self.module.sys,
					'argv',
					['release.py', 'prepare', '--date', '2099-02-04', '--channel', 'Beta'],
				),
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(self.module.main(), 0)
			changelog = (clone / 'CHANGELOG.md').read_text(encoding='utf-8')
			self.assertIn('## [Beta.v2099.02.040001]', changelog)
			self.assertIn('— 2099-02-04', changelog)
			self.assertEqual(
				self.module.releaseNotes(changelog, 'Beta.v2099.02.040001'),
				'### ✨ THÊM\n\n- Mục mới.',
			)

	def testCreateReleaseMarksOnlyBetaAsPrerelease(self):
		with tempfile.TemporaryDirectory() as folder:
			path = Path(folder) / 'CHANGELOG.md'
			for version in ('Stable.v2099.02.040001', 'Beta.v2099.02.040002', 'v2099.01.Stable'):
				for generated in (False, True):
					with self.subTest(version=version, generated=generated):
						path.write_text(
							'' if generated else f'## [{version}]\n\n- Nội dung phát hành.\n',
							encoding='utf-8',
						)
						with (
							mock.patch.object(self.module.subprocess, 'run') as run,
							contextlib.redirect_stdout(io.StringIO()),
						):
							self.assertEqual(self.module.createRelease(version, path, generated), 0)
						run.assert_called_once()
						command = run.call_args.args[0]
						self.assertEqual(command[:4], ['gh', 'release', 'create', version])
						self.assertEqual('--prerelease' in command, version.startswith('Beta.'))
						self.assertIn('--generate-notes' if generated else '--notes-file', command)

	def testReleasePullRequestHasPreparationAndChannelLabels(self):
		with tempfile.TemporaryDirectory() as folder:
			self.module.ROOT = Path(folder)
			(self.module.ROOT / 'CHANGELOG.md').write_text(RELEASE_FIXTURE, encoding='utf-8')
			for channel in ('Stable', 'Beta'):
				with self.subTest(channel=channel):
					with (
						mock.patch.object(self.module, 'runCommand', return_value='abc123'),
						mock.patch.object(self.module.github, 'ghExists', return_value=False),
						mock.patch.object(
							self.module.subprocess,
							'run',
							return_value=subprocess.CompletedProcess(
								[], 0, 'https://github.com/x/y/pull/1', ''
							),
						) as run,
						contextlib.redirect_stdout(io.StringIO()),
					):
						self.assertEqual(
							self.module.openReleasePullRequest(
								f'{channel}.v2099.02.040001', 'v2099.01.Stable', 1
							),
							0,
						)
					command = run.call_args.args[0]
					self.assertEqual(command[:3], ['gh', 'pr', 'create'])
					labels = [
						command[index + 1]
						for index, value in enumerate(command)
						if value == '--label'
					]
					self.assertEqual(labels, ['release', 'Pre-Release', channel])

	def testReleasePullRequestFromActionsExplainsHowToRunChecks(self):
		# Pull Request mở bằng GITHUB_TOKEN không khởi chạy workflow kiểm tra; mở tại máy (make release-pr) thì
		# kiểm tra chạy bình thường nên không cần hướng dẫn.
		with tempfile.TemporaryDirectory() as folder:
			self.module.ROOT = Path(folder)
			(self.module.ROOT / 'CHANGELOG.md').write_text(RELEASE_FIXTURE, encoding='utf-8')
			for onActions in (False, True):
				with self.subTest(onActions=onActions):
					with (
						mock.patch.object(self.module, 'runCommand', return_value='abc123'),
						mock.patch.object(self.module.github, 'ghExists', return_value=False),
						mock.patch.dict(
							self.module.os.environ,
							{'GITHUB_ACTIONS': 'true'} if onActions else {},
							clear=True,
						),
						mock.patch.object(
							self.module.subprocess,
							'run',
							return_value=subprocess.CompletedProcess(
								[], 0, 'https://github.com/x/y/pull/1', ''
							),
						) as run,
						contextlib.redirect_stdout(io.StringIO()),
					):
						self.module.openReleasePullRequest(
							'Stable.v2099.02.040001', 'v2099.01.Stable', 1
						)
					command = run.call_args.args[0]
					body = command[command.index('--body') + 1]
					self.assertEqual('Reopen pull request' in body, onActions)

	def testExtractsVersionNotes(self):
		# Dữ liệu mẫu cố định: nội dung CHANGELOG.md thật thay đổi theo từng lần phát hành.
		notes = self.module.releaseNotes(RELEASE_FIXTURE, 'v2099.01.Stable')
		self.assertEqual(notes, '### ✨ THÊM\n\n- Mục cũ.')
		self.assertNotIn('<p align="center">', notes)
		self.assertNotIn('CHƯA PHÁT HÀNH', notes)
		# CHANGELOG.md thật đọc được mục của mọi phiên bản đã phát hành.
		changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
		for version in re.findall(
			r'^## \[((?:v|Stable\.v|Beta\.v)[^\]]+)\]', changelog, re.MULTILINE
		):
			self.assertTrue(self.module.releaseNotes(changelog, version), version)

	def testMissingVersionReturnsNone(self):
		self.assertIsNone(self.module.releaseNotes(RELEASE_FIXTURE, 'v1999.01.Stable'))

	def testUnreleasedWorksWithoutPreviousVersionSections(self):
		header = (
			'# NỘI DUNG PHÁT HÀNH\n\n'
			'## [CHƯA PHÁT HÀNH]'
			'(https://github.com/TOANQUYNHLLC/.github/compare/v2099.01.Stable...HEAD)\n'
		)
		for footer in ('', '\n---\n\n<p align="center">© 2099</p>\n'):
			with self.subTest(footer=footer):
				self.assertEqual(self.module.unreleasedNotes(header + footer), '')
				changelog = header + '\n- Nội dung phiên bản.\n' + footer
				self.assertEqual(self.module.unreleasedNotes(changelog), '- Nội dung phiên bản.')
				prepared = self.module.cutRelease(changelog, 'Stable.v2099.02.010001', '2099-02-01')
				self.assertEqual(self.module.unreleasedNotes(prepared), '')
				self.assertEqual(
					self.module.releaseNotes(prepared, 'Stable.v2099.02.010001'),
					'- Nội dung phiên bản.',
				)
				if footer:
					self.assertTrue(prepared.endswith('<p align="center">© 2099</p>\n'))

	def testCutsUnreleasedIntoVersion(self):
		# CHANGELOG mẫu cố định: mục CHƯA PHÁT HÀNH của tệp thật trống ngay sau mỗi lần phát hành.
		changelog = self.module.cutRelease(RELEASE_FIXTURE, 'Stable.v2099.02.010001', '2099-02-01')
		self.assertIn(
			'## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github/compare/Stable.v2099.02.010001...HEAD)',
			changelog,
		)
		self.assertIn(
			'## [Stable.v2099.02.010001](https://github.com/TOANQUYNHLLC/.github/releases/tag/Stable.v2099.02.010001)'
			' — 2099-02-01',
			changelog,
		)
		# Mục mới trống; nội dung chuẩn bị thành nội dung Release của phiên bản mới. Mục của phiên bản trước bị
		# bỏ — CHANGELOG.md không tích luỹ lịch sử (lịch sử ở GitHub Release); chân trang giữ nguyên.
		self.assertEqual(self.module.unreleasedNotes(changelog), '')
		self.assertEqual(
			self.module.releaseNotes(changelog, 'Stable.v2099.02.010001'),
			'### ✨ THÊM\n\n- Mục mới.',
		)
		self.assertIsNone(self.module.releaseNotes(changelog, 'v2099.01.Stable'))
		self.assertNotIn('Mục cũ', changelog)
		self.assertEqual(len(self.module.VERSION_HEADING.findall(changelog)), 2)
		self.assertTrue(changelog.endswith('---\n\n<p align="center">© 2099</p>\n'))

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
				code = self.module.prepareRelease('Stable.v2099.01.010001', '2099-01-01')
		self.assertEqual(code, 1)
		self.assertIn('Chưa có tag phát hành nào', output.getvalue())

	def releaseClone(self, folder):
		"""Repository có origin, tag v2099.01.Stable và một commit sau tag, đang ở main trùng origin/main — chép từ
		repository mẫu của lớp; origin trỏ tới bản chép, mỗi test sửa thoải mái."""
		template = Path(type(self).templates.name)
		if not (template / 'clone').exists():
			self.buildReleaseClone(template)
		shutil.copytree(template, folder, symlinks=True, dirs_exist_ok=True)
		clone = Path(folder) / 'clone'
		# git clone ghi đường dẫn origin nguyên văn vào .git/config: đổi sang origin của bản chép.
		config = clone / '.git' / 'config'
		config.write_text(
			config.read_text(encoding='utf-8').replace(str(template), str(Path(folder))),
			encoding='utf-8',
		)
		self.module.ROOT = clone
		return clone

	@staticmethod
	def buildReleaseClone(folder):
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

	def testPrepareFetchesTagsBeforeChoosingSequence(self):
		# Tag mới chỉ có trên origin (người khác vừa phát hành) vẫn được tính: make release-prepare không chọn trùng
		# số thứ tự đã dùng. Không tải được origin thì dừng, giữ nguyên CHANGELOG.md.
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			origin = Path(folder) / 'origin.git'
			subprocess.run(
				['git', '-c', 'tag.gpgsign=false', 'tag', 'Beta.v2099.02.010005', 'main~1'],
				cwd=origin,
				check=True,
			)
			with contextlib.redirect_stdout(io.StringIO()):
				self.assertEqual(self.module.prepareRelease(None, '2099-02-01'), 0)
			changelog = (clone / 'CHANGELOG.md').read_text(encoding='utf-8')
			self.assertIn('## [Stable.v2099.02.010006]', changelog)

		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			subprocess.run(
				['git', 'remote', 'set-url', 'origin', str(Path(folder) / 'khong-co.git')],
				cwd=clone,
				check=True,
			)
			output = io.StringIO()
			with contextlib.redirect_stdout(output):
				self.assertEqual(self.module.prepareRelease(None, '2099-02-01'), 1)
			self.assertIn('Không tải được tag từ origin', output.getvalue())
			changelog = (clone / 'CHANGELOG.md').read_text(encoding='utf-8')
			self.assertEqual(changelog, RELEASE_FIXTURE)

	def testOpenPrRequiresCleanMain(self):
		# make release-pr lấy HEAD làm gốc branch phát hành: đứng ở branch khác main thì dừng trước khi sửa
		# CHANGELOG.md hay gọi GitHub.
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			subprocess.run(['git', 'switch', '-q', '-c', 'feature'], cwd=clone, check=True)
			output = io.StringIO()
			with contextlib.redirect_stdout(output):
				code = self.module.prepareRelease('Stable.v2099.02.010001', '2099-02-01', True)
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
				code = self.module.prepareRelease('Stable.v2099.02.010001', '2099-02-01', True)
			self.assertEqual(code, 1)
			self.assertIn('Không tải được origin/main', output.getvalue())

	def testOpenPrCommitsPreparedChangelogThenRestores(self):
		# make release-pr: mở Pull Request với CHANGELOG.md đã chuyển phiên bản, rồi trả tệp tại máy về như cũ.
		with tempfile.TemporaryDirectory() as folder:
			clone = self.releaseClone(folder)
			opened = []

			def openPullRequest(version, previous, commits):
				changelog = (clone / 'CHANGELOG.md').read_text(encoding='utf-8')
				opened.append(
					(version, previous, commits, '## [Stable.v2099.02.010001]' in changelog)
				)
				return 0

			with (
				mock.patch.object(self.module, 'openReleasePullRequest', openPullRequest),
				contextlib.redirect_stdout(io.StringIO()),
			):
				code = self.module.prepareRelease('Stable.v2099.02.010001', '2099-02-01', True)
			self.assertEqual(code, 0)
			self.assertEqual(opened, [('Stable.v2099.02.010001', 'v2099.01.Stable', 1, True)])
			self.assertEqual((clone / 'CHANGELOG.md').read_text(encoding='utf-8'), RELEASE_FIXTURE)

	def testOpenPrDeletesBranchWhenCommitFails(self):
		# GitHub từ chối commit (mất quyền, lỗi mạng): xóa branch vừa tạo để lần chạy sau không bỏ qua vì
		# "branch đã có", không mở Pull Request.
		calls = []

		def fakeRun(args, **kwargs):
			calls.append(args)
			if args[:3] == ['git', 'rev-parse', 'HEAD']:
				return subprocess.CompletedProcess(args, 0, 'abc123\n', '')
			if args[:2] == ['gh', 'api'] and args[2].endswith(
				'/branches/release/stable.v2099.02.010001'
			):
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
			code = self.module.openReleasePullRequest(
				'Stable.v2099.02.010001', 'v2099.01.Stable', 3
			)
		self.assertEqual(code, 1)
		self.assertIn(
			'Không commit được CHANGELOG.md lên release/stable.v2099.02.010001', output.getvalue()
		)
		self.assertIn(
			[
				'gh',
				'api',
				'-X',
				'DELETE',
				'repos/TOANQUYNHLLC/.github/git/refs/heads/release/stable.v2099.02.010001',
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
			code = self.module.openReleasePullRequest(
				'Stable.v2099.02.010001', 'v2099.01.Stable', 3
			)
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
			code = self.module.openReleasePullRequest(
				'Stable.v2099.02.010001', 'v2099.01.Stable', 3
			)
		self.assertEqual(code, 1)
		self.assertIn('chưa có Pull Request đang mở', output.getvalue())
		self.assertIn('compare/main...release/stable.v2099.02.010001', output.getvalue())

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
			code = self.module.openReleasePullRequest(
				'Stable.v2099.02.010001', 'v2099.01.Stable', 3
			)
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
			code = self.module.openReleasePullRequest(
				'Stable.v2099.02.010001', 'v2099.01.Stable', 3
			)
		self.assertEqual(code, 1)
		self.assertNotIn('đã xóa branch', output.getvalue())
		self.assertIn('chưa xóa được branch', output.getvalue())
		self.assertIn('HTTP 403', output.getvalue())

	def testEmptyUnreleasedSection(self):
		changelog = self.module.cutRelease(RELEASE_FIXTURE, 'Stable.v2099.02.010001', '2099-02-01')
		self.assertEqual(self.module.unreleasedNotes(changelog), '')
		self.assertIsNone(self.module.releaseNotes(changelog, 'CHƯA PHÁT HÀNH'))
		self.assertIsNone(self.module.unreleasedNotes('# NHẬT KÝ\n'))


if __name__ == '__main__':
	unittest.main()
