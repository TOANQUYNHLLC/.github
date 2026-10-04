"""Test tự động cho scripts/run-tests.py.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import io
import unittest
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript


class RunTestsTest(unittest.TestCase):
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
