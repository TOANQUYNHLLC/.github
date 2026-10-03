"""Test tự động cho scripts/check-gofmt.py.

Chạy: python3 -m unittest discover -s scripts -p 'test_*.py'   (hoặc: make test)
"""

import contextlib
import subprocess
import tempfile
import unittest
from pathlib import Path

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript


class GofmtTest(unittest.TestCase):
	def testVendorIsSkipped(self):
		# Mã của bên thứ ba trong vendor/ không thuộc trách nhiệm định dạng của repository.
		module = loadScript('check-gofmt')
		with tempfile.TemporaryDirectory() as folder:
			for name in ('main.go', 'cmd/app/app.go', 'vendor/lib/lib.go', 'README.md'):
				path = Path(folder) / name
				path.parent.mkdir(parents=True, exist_ok=True)
				path.write_text('package x\n', encoding='utf-8')
			subprocess.run(['git', 'init', '-q'], cwd=folder, check=True)
			with contextlib.chdir(folder):
				self.assertEqual(sorted(module.goFiles()), ['cmd/app/app.go', 'main.go'])


if __name__ == '__main__':
	unittest.main()
