"""Test tự động cho scripts/check.py: nhóm kiểm tra khớp workflow validate.yml.

Chạy: python3 -m unittest discover -s scripts -p 'test_*.py'   (hoặc: make test)
"""

import contextlib
import io
import re
import subprocess
import unittest
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
			'network': subprocess.CompletedProcess(
				[],
				1,
				'',
				'npm warn audit request to https://x failed, reason: connect ECONNREFUSED',
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
				self.assertEqual(module.runCommand('audit', ['npm', 'audit']), expected, case)


if __name__ == '__main__':
	unittest.main()
