"""Test tự động cho scripts/check.py: nhóm kiểm tra khớp workflow validate.yml.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import io
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import ROOT, loadScript
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript


class CheckTest(unittest.TestCase):
	def testValidateWorkflowRunsCheckGroups(self):
		# Mỗi job của validate.yml gọi đúng một nhóm của check.py — tại máy và trên GitHub chạy cùng lệnh.
		groups = loadScript('check').checkGroups()
		workflow = (ROOT / '.github' / 'workflows' / 'validate.yml').read_text(encoding='utf-8')
		called = re.findall(r'run: python3 scripts/check\.py (\w+)$', workflow, re.MULTILINE)
		self.assertEqual(called, ['content', 'format', 'lint'])
		self.assertTrue(set(called) <= set(groups))
		self.assertEqual(list(groups), ['content', 'format', 'lint', 'conventions', 'audit'])

	def testAuditNetworkErrorOnlyWarns(self):
		# Mất mạng: audit chỉ cảnh báo; lỗ hổng thật (mã thoát khác 0, không phải lỗi mạng) vẫn chặn.
		module = loadScript('check')
		results = {
			# Lỗi gộp vào đầu ra (stderr=STDOUT) như khi check.py chạy lệnh thật.
			'network': subprocess.CompletedProcess(
				[], 1, 'npm warn audit request to https://x failed, reason: connect ECONNREFUSED\n'
			),
			'vulnerable': subprocess.CompletedProcess([], 1, '1 high severity vulnerability\n', ''),
		}
		for case, expected in (('network', True), ('vulnerable', False)):
			# subprocess của script là module dùng chung — vá tạm bằng mock.patch để tự hoàn lại.
			with (
				mock.patch.object(module.subprocess, 'run', return_value=results[case]),
				contextlib.redirect_stdout(io.StringIO()),
				contextlib.redirect_stderr(io.StringIO()),
			):
				self.assertEqual(module.runCommand('audit', ['npm', 'audit'])[0], expected, case)

	def testShellScriptsKeepSpecialNames(self):
		# Script shell ở bất kỳ thư mục nào, tên có dấu vẫn được shellcheck kiểm tra.
		module = loadScript('check')
		with tempfile.TemporaryDirectory() as folder:
			root = Path(folder)
			(root / 'công cụ').mkdir()
			(root / 'công cụ' / 'cài đặt.sh').write_text('#!/usr/bin/env bash\n', encoding='utf-8')
			subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
			module.ROOT = root
			self.assertEqual(module.shellScripts(), ['công cụ/cài đặt.sh'])

	def testGroupsAreListedOnce(self):
		# main, ensureTools, runGroup cùng dùng danh sách nhóm: liệt kê script shell (gọi git) chỉ một lần mỗi lượt.
		module = loadScript('check')
		calls = []

		def shellScripts():
			calls.append(1)
			return ['a.sh']

		passed = subprocess.CompletedProcess([], 0, '', '')
		with (
			mock.patch.object(module, 'shellScripts', shellScripts),
			mock.patch.object(module.subprocess, 'run', return_value=passed),
			mock.patch.object(module.sys, 'argv', ['check.py']),
			mock.patch.object(module.shutil, 'which', return_value='/bin/x'),
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(module.main(), 0)
		self.assertEqual(len(calls), 1)

	def testGroupsRunInParallelButPrintInOrder(self):
		# Nhóm chậm (đầu) và nhóm nhanh chạy cùng lúc; đầu ra vẫn theo thứ tự nhóm, lệnh lỗi được liệt kê.
		module = loadScript('check')
		groups = {
			'slow': [[sys.executable, '-c', 'import time; time.sleep(0.5); print("chậm")']],
			'fast': [[sys.executable, '-c', 'print("nhanh"); raise SystemExit(1)']],
		}
		output = io.StringIO()
		with (
			mock.patch.object(module, 'checkGroups', return_value=groups),
			contextlib.redirect_stdout(output),
		):
			started = time.monotonic()
			self.assertFalse(module.runGroups(['slow', 'fast']))
			self.assertLess(time.monotonic() - started, 1.0)
		text = output.getvalue()
		self.assertLess(text.index('chậm'), text.index('nhanh'))
		self.assertIn('❌ fast:', text)


if __name__ == '__main__':
	unittest.main()
