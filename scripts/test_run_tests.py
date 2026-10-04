"""Test tự động cho scripts/run-tests.py.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript


class RunTestsTest(unittest.TestCase):
	def testBrokenImportWithMissingSelectionDoesNotRun(self):
		module = loadScript('run-tests')
		output = io.StringIO()
		with tempfile.TemporaryDirectory() as folder:
			root = Path(folder)
			(root / 'test_broken_selection.py').write_text(
				'raise ImportError("lỗi nạp")\n', encoding='utf-8'
			)
			with (
				mock.patch.object(module, 'SCRIPTS', root),
				mock.patch.object(
					module.sys,
					'argv',
					['run-tests.py', 'test_broken_selection', 'test_missing_selection'],
				),
				mock.patch.object(
					module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)
				) as run,
				contextlib.redirect_stdout(output),
			):
				self.assertEqual(module.main(), 1)
				run.assert_not_called()
		self.assertIn('Không có test nào khớp', output.getvalue())

	def testSelectionDoesNotImportOtherFiles(self):
		module = loadScript('run-tests')
		with tempfile.TemporaryDirectory() as folder:
			root = Path(folder)
			(root / 'test_selected.py').write_text(
				'import unittest\nclass Selected(unittest.TestCase):\n\tdef testValid(self):\n\t\tself.assertTrue(True)\n',
				encoding='utf-8',
			)
			(root / 'test_unselected.py').write_text(
				'raise RuntimeError("không được nạp")\n', encoding='utf-8'
			)
			with mock.patch.object(module, 'SCRIPTS', root):
				self.assertEqual(
					module.discoverTests(['test_selected']), ['test_selected.Selected.testValid']
				)

	def testFallbackKeepsSelectedScope(self):
		module = loadScript('run-tests')
		with (
			mock.patch.object(module.sys, 'argv', ['run-tests.py', 'test_conventions']),
			mock.patch.object(module, 'discoverTests', return_value=None),
			mock.patch.object(
				module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)
			) as run,
		):
			self.assertEqual(module.main(), 1)
		self.assertEqual(run.call_args.args[0][-1], 'test_conventions')
		self.assertNotIn('discover', run.call_args.args[0])

	def testUnknownSelectionDoesNotRunPartialSuite(self):
		module = loadScript('run-tests')
		output = io.StringIO()
		with (
			mock.patch.object(
				module.sys, 'argv', ['run-tests.py', 'test_conventions.py', 'test_missing']
			),
			mock.patch.object(module, 'runShard', return_value=(0, 1, '')) as run,
			contextlib.redirect_stdout(output),
		):
			self.assertEqual(module.main(), 1)
		self.assertIn('test_missing', output.getvalue())
		run.assert_not_called()

	def testSelectsTestFilesByName(self):
		module = loadScript('run-tests')
		ids = module.discoverTests(['test_conventions'])
		self.assertTrue(ids)
		self.assertTrue(all(test.startswith('test_conventions.') for test in ids))

	def testShardReportsCountAndFailure(self):
		# Nhóm đạt: mã thoát 0 và đếm đúng số test; test không tồn tại: mã thoát khác 0 để cả lượt báo lỗi.
		module = loadScript('run-tests')
		ids = module.discoverTests(['test_conventions'])
		code, ran, _ = module.runShard(ids)
		self.assertEqual((code, ran), (0, len(ids)))
		code, _, output = module.runShard(['test_conventions.KhongCo.testKhongCo'])
		self.assertNotEqual(code, 0, output)


if __name__ == '__main__':
	unittest.main()
