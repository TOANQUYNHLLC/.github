"""Test tự động cho Dev Container: .devcontainer/update-content.sh (cài công cụ), post-create.sh (tin cậy thư mục,
cài hook) và gh-login-hint.py (nhắc đăng nhập GitHub CLI).

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import ROOT
except ModuleNotFoundError:
	from scripts.testsupport import ROOT


class DevcontainerTest(unittest.TestCase):
	def setUp(self):
		# curl, mise, npm, make, sudo thay bằng lệnh giả ghi lại tham số: test không tải mạng, không cài gì.
		self.tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self.tmp.cleanup)
		folder = Path(self.tmp.name)
		self.tools, self.home, self.calls = folder / 'bin', folder / 'home', folder / 'calls'
		self.tools.mkdir()
		self.home.mkdir()
		for name in ('curl', 'mise', 'npm', 'make', 'sudo'):
			fake = self.tools / name
			fake.write_text(f'#!/bin/sh\necho "{name} $*" >> "{self.calls}"\n', encoding='utf-8')
			fake.chmod(0o755)
		# Chạy qua một liên kết tới repository: $PWD đi qua liên kết, khác đường dẫn thật mà git thấy.
		self.link = folder / 'link'
		self.link.symlink_to(ROOT.resolve())
		self.environment = dict(
			os.environ, HOME=str(self.home), PATH=f'{self.tools}:/usr/bin:/bin', PWD=str(self.link)
		)
		# git thật, cấu hình toàn cục nằm trong HOME tạm.
		self.environment.pop('GIT_CONFIG_GLOBAL', None)

	def runScript(self, name):
		subprocess.run(
			['bash', str(self.link / '.devcontainer' / name)],
			cwd=self.link,
			env=self.environment,
			capture_output=True,
			check=True,
		)

	def recordedCalls(self):
		return self.calls.read_text(encoding='utf-8').splitlines() if self.calls.exists() else []

	def testUpdateContentRerunDoesNotDuplicateSetup(self):
		# Chạy lại (dựng lại container, Codespaces cập nhật nội dung) không thêm trùng dòng kích hoạt mise vào
		# .bashrc, .zshrc; vẫn cài lại công cụ và thư viện Node.js.
		for _ in range(2):
			self.runScript('update-content.sh')
		for shell in ('bash', 'zsh'):
			lines = (self.home / f'.{shell}rc').read_text(encoding='utf-8').splitlines()
			self.assertEqual(lines, [f'eval "$(~/.local/bin/mise activate {shell})"'], shell)
		calls = self.recordedCalls()
		self.assertEqual(calls.count('mise install'), 2)
		self.assertEqual(calls.count('npm install --include=dev --no-audit --no-fund'), 2)
		self.assertFalse([call for call in calls if call.startswith('sudo')])

	def testUpdateContentSkipsDownloadWhenMiseInstalled(self):
		(self.home / '.local' / 'bin').mkdir(parents=True)
		installed = self.home / '.local' / 'bin' / 'mise'
		installed.write_text('#!/bin/sh\n', encoding='utf-8')
		installed.chmod(0o755)
		self.runScript('update-content.sh')
		self.assertFalse([call for call in self.recordedCalls() if call.startswith('curl')])

	@unittest.skipIf(
		os.getuid() == 0, 'root ghi được mọi thư mục — không tái hiện được volume chưa có quyền ghi'
	)
	def testUpdateContentTakesOwnershipOfNewVolumes(self):
		# Volume mới của Docker và thư mục cha Docker tự tạo (~/.local) thuộc root: chỉ thư mục chưa ghi được mới cần
		# sudo chown — thiếu bước này thì bộ cài mise không tạo được ~/.local/bin.
		local, mise = self.home / '.local', self.home / '.local' / 'share' / 'mise'
		mise.mkdir(parents=True)
		(self.home / '.npm').mkdir()
		for locked in (mise, local):
			locked.chmod(0o555)
			self.addCleanup(locked.chmod, 0o755)
		self.runScript('update-content.sh')
		owner = f'{os.getuid()}:{os.getgid()}'
		self.assertEqual(
			[call for call in self.recordedCalls() if call.startswith('sudo')],
			[f'sudo chown {owner} {local}', f'sudo chown {owner} {mise}'],
		)

	def testPostCreateTrustsWorkspaceOnceAndInstallsHooks(self):
		# Thư mục làm việc được tin cậy (safe.directory) để make hooks chạy được khi thư mục gắn vào container
		# thuộc người dùng khác — chạy lại cũng chỉ thêm một lần.
		for _ in range(2):
			self.runScript('post-create.sh')
		trusted = subprocess.run(
			['git', 'config', '--global', '--get-all', 'safe.directory'],
			env=self.environment,
			capture_output=True,
			text=True,
			check=True,
		).stdout.splitlines()
		self.assertEqual(trusted, [str(ROOT.resolve())])
		self.assertEqual(self.recordedCalls(), ['make hooks', 'make hooks'])


class GhLoginHintTest(unittest.TestCase):
	def setUp(self):
		# Script nằm trong .devcontainer/ (không phải scripts/), tên có dấu gạch ngang: nạp theo đường dẫn tệp.
		spec = importlib.util.spec_from_file_location(
			'gh_login_hint', ROOT / '.devcontainer' / 'gh-login-hint.py'
		)
		self.module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(self.module)

	def runHint(self, which, returncode=0):
		calls = []

		def run(command, **kwargs):
			calls.append((command, kwargs['env']))
			return subprocess.CompletedProcess(command, returncode)

		output = io.StringIO()
		with (
			mock.patch.object(self.module.shutil, 'which', return_value=which),
			mock.patch.object(self.module.subprocess, 'run', run),
			mock.patch.dict(os.environ, {'GH_TOKEN': 'x', 'GITHUB_TOKEN': 'y'}),
			contextlib.redirect_stdout(output),
		):
			self.assertEqual(self.module.main(), 0)
		return output.getvalue(), calls

	def testSignedInPrintsNothing(self):
		output, calls = self.runHint('/usr/bin/gh')
		self.assertEqual(output, '')
		# Token của môi trường (GITHUB_TOKEN của Codespaces) không thay cho đăng nhập bằng tài khoản quản trị.
		command, environment = calls[0]
		self.assertEqual(command, ['gh', 'auth', 'status'])
		self.assertNotIn('GH_TOKEN', environment)
		self.assertNotIn('GITHUB_TOKEN', environment)

	def testNotSignedInOrMissingCliPrintsHint(self):
		for which, returncode in (('/usr/bin/gh', 1), (None, 0)):
			with self.subTest(which=which):
				output, _ = self.runHint(which, returncode)
				self.assertIn('gh auth login', output)


if __name__ == '__main__':
	unittest.main()
