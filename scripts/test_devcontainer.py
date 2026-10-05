"""Test tự động cho .devcontainer/post-create.sh (cài công cụ cho Dev Container, Codespaces).

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import ROOT
except ModuleNotFoundError:
	from scripts.testsupport import ROOT


class PostCreateTest(unittest.TestCase):
	def testRerunDoesNotDuplicateSetup(self):
		# Chạy lại script (dựng lại container, chạy tay) không thêm trùng dòng kích hoạt mise vào .bashrc, .zshrc.
		# curl, mise, npm, make thay bằng lệnh giả: test không tải mạng, không cài gì.
		with tempfile.TemporaryDirectory() as folder:
			tools, home = Path(folder) / 'bin', Path(folder) / 'home'
			tools.mkdir()
			home.mkdir()
			for name in ('curl', 'mise', 'npm', 'make'):
				fake = tools / name
				fake.write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
				fake.chmod(0o755)
			# Chạy qua một liên kết tới repository: $PWD đi qua liên kết, khác đường dẫn thật mà git thấy.
			link = Path(folder) / 'link'
			link.symlink_to(ROOT.resolve())
			environment = dict(
				os.environ, HOME=str(home), PATH=f'{tools}:/usr/bin:/bin', PWD=str(link)
			)
			# git thật, cấu hình toàn cục nằm trong HOME tạm.
			environment.pop('GIT_CONFIG_GLOBAL', None)
			for _ in range(2):
				subprocess.run(
					['bash', str(link / '.devcontainer' / 'post-create.sh')],
					cwd=link,
					env=environment,
					capture_output=True,
					check=True,
				)
			for shell in ('bash', 'zsh'):
				lines = (home / f'.{shell}rc').read_text(encoding='utf-8').splitlines()
				self.assertEqual(lines, [f'eval "$(~/.local/bin/mise activate {shell})"'], shell)
			# Thư mục làm việc được tin cậy (safe.directory) để make hooks chạy được khi thư mục gắn vào container
			# thuộc người dùng khác — cũng chỉ thêm một lần.
			trusted = subprocess.run(
				['git', 'config', '--global', '--get-all', 'safe.directory'],
				env=environment,
				capture_output=True,
				text=True,
				check=True,
			).stdout.splitlines()
			self.assertEqual(trusted, [str(ROOT.resolve())])


if __name__ == '__main__':
	unittest.main()
