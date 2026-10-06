"""Test tự động cho scripts/run-tests.py.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import io
import json
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
	def testTimingWriteFailurePreservesCacheAndCleansTemporaryFile(self):
		module = loadScript('run-tests')
		with tempfile.TemporaryDirectory() as folder:
			module.TIMINGS_FILE = Path(folder) / 'times.json'
			module.TIMINGS_FILE.write_text('{"old": 2}', encoding='utf-8')
			with mock.patch.object(module.os, 'replace', side_effect=OSError):
				module.writeTimings(['new'], {'new': 1})
			self.assertEqual(module.readTimings(), {'old': 2})
			self.assertEqual(list(Path(folder).iterdir()), [module.TIMINGS_FILE])
			module.writeTimings(['new'], {'new': 1, 'removed': 3})
			self.assertEqual(json.loads(module.TIMINGS_FILE.read_text()), {'new': 1})
			self.assertEqual(list(Path(folder).iterdir()), [module.TIMINGS_FILE])

	def testBalancedShardsNeverDropNewTests(self):
		module = loadScript('run-tests')
		ids = ['slow', 'fast', 'new', 'other']
		shards = module.splitTests(ids, 2, {'slow': 10, 'fast': 1, 'other': 1})
		self.assertCountEqual([test for shard in shards for test in shard], ids)
		self.assertEqual(shards[0], ['slow'])
		self.assertEqual(module.splitTests(ids, 2, {}), [ids[::2], ids[1::2]])

	def testTimedShardsKeepClassFixturesTogether(self):
		module = loadScript('run-tests')
		ids = ['a.First.testA', 'a.First.testB', 'b.Second.testA']
		shards = module.splitTests(ids, 1, dict(zip(ids, [10, 1, 5], strict=True)))
		self.assertEqual(shards, [ids])

	def testInvalidTimingHistoryFallsBack(self):
		module = loadScript('run-tests')
		with tempfile.TemporaryDirectory() as folder:
			module.TIMINGS_FILE = Path(folder) / 'times.json'
			for content in (
				'bad',
				'[]',
				'{"a": -1, "b": true, "c": "x", "d": 2}',
				'{"huge": ' + '9' * 400 + '}',
			):
				module.TIMINGS_FILE.write_text(content)
				self.assertEqual(module.readTimings(), {'d': 2} if '"d"' in content else {})

	def testCpuQuotaAndAffinityLimitWorkers(self):
		module = loadScript('run-tests')
		with (
			mock.patch.object(module.os, 'process_cpu_count', return_value=16, create=True),
			mock.patch.object(
				module.os, 'sched_getaffinity', return_value={0, 1, 2, 3}, create=True
			),
			mock.patch.object(Path, 'read_text', return_value='150000 100000'),
		):
			self.assertEqual(module.availableCpus(), 2)
		with (
			mock.patch.object(module.os, 'process_cpu_count', return_value=2, create=True),
			mock.patch.object(module.os, 'sched_getaffinity', side_effect=OSError, create=True),
			mock.patch.object(Path, 'read_text', side_effect=OSError),
		):
			self.assertEqual(module.availableCpus(), 2)

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

	def testPartialRunKeepsOtherTimings(self):
		# Chạy một tệp test (make quick, run-tests.py test_a) không xóa thời gian đã đo của test khác; lượt chạy đầy
		# đủ mới bỏ thời gian của test không còn.
		module = loadScript('run-tests')
		measured = (0, 1, '', {'test_a.A.testOne': 1})
		with tempfile.TemporaryDirectory() as folder:
			module.TIMINGS_FILE = Path(folder) / 'times.json'
			module.TIMINGS_FILE.write_text(
				'{"test_a.A.testOne": 2, "test_b.B.testTwo": 3}', encoding='utf-8'
			)
			for argv, expected in (
				(['run-tests.py', 'test_a'], {'test_a.A.testOne': 1, 'test_b.B.testTwo': 3}),
				(['run-tests.py'], {'test_a.A.testOne': 1}),
			):
				with (
					mock.patch.object(
						module, 'discoverTests', return_value=(['test_a.A.testOne'], [])
					),
					mock.patch.object(module, 'timedShard', return_value=measured),
					mock.patch.object(module.sys, 'argv', argv),
					contextlib.redirect_stdout(io.StringIO()),
				):
					self.assertEqual(module.main(), 0)
				self.assertEqual(
					json.loads(module.TIMINGS_FILE.read_text(encoding='utf-8')), expected, argv
				)

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
					module.discoverTests(['test_selected']),
					(['test_selected.Selected.testValid'], []),
				)

	def testFallbackKeepsSelectedScope(self):
		module = loadScript('run-tests')
		with (
			mock.patch.object(module.sys, 'argv', ['run-tests.py', 'test_conventions']),
			mock.patch.object(module, 'discoverTests', return_value=(None, [])),
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
			mock.patch.object(module, 'timedShard', return_value=(0, 1, '', {})) as run,
			contextlib.redirect_stdout(output),
		):
			self.assertEqual(module.main(), 1)
		self.assertIn('Không có test nào khớp: test_missing\n', output.getvalue())
		self.assertNotIn('test_conventions', output.getvalue())
		run.assert_not_called()

	def testSelectsTestFilesByName(self):
		module = loadScript('run-tests')
		ids, missing = module.discoverTests(['test_conventions'])
		self.assertEqual(missing, [])
		self.assertTrue(ids)
		self.assertTrue(all(test.startswith('test_conventions.') for test in ids))

	def testShardReportsCountAndFailure(self):
		# Nhóm đạt: mã thoát 0 và đếm đúng số test; test không tồn tại: mã thoát khác 0 để cả lượt báo lỗi.
		module = loadScript('run-tests')
		ids, _ = module.discoverTests(['test_conventions'])
		code, ran, _, timings = module.timedShard(ids)
		self.assertEqual((code, ran), (0, len(ids)))
		self.assertEqual(sorted(timings), sorted(ids))
		code, _, output, _ = module.timedShard(['test_conventions.KhongCo.testKhongCo'])
		self.assertNotEqual(code, 0, output)


if __name__ == '__main__':
	unittest.main()
