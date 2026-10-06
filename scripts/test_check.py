"""Test tự động cho scripts/check.py: nhóm kiểm tra khớp workflow validate.yml.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import io
import re
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import unittest
from pathlib import Path
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import ROOT, loadScript
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript


class CheckTest(unittest.TestCase):
	def runMain(self, argv, changed=None):
		"""main() của check.py với công cụ coi như đủ; trả (mã thoát, đầu ra, nhóm và test được chọn)."""
		module = loadScript('check')
		output = io.StringIO()
		with (
			mock.patch.object(module.sys, 'argv', ['check.py', *argv]),
			mock.patch.object(module, 'ensureTools', return_value=True),
			mock.patch.object(module, 'changedFiles', return_value=changed),
			mock.patch.object(module, 'runGroups', return_value=True) as run,
			contextlib.redirect_stdout(output),
		):
			code = module.main()
		return code, output.getvalue(), run.call_args.args if run.called else None

	def testUnknownGroupIsRejectedBeforeRunning(self):
		code, output, ran = self.runMain(['khong_co'])
		self.assertEqual(code, 2)
		self.assertIn('Nhóm không có: khong_co', output)
		self.assertIsNone(ran)

	def testQuickNarrowsOnlyTestsWhenOnlyTestFilesChanged(self):
		# make quick: chỉ sửa tệp test thì chỉ chạy các tệp test đó, mọi nhóm khác vẫn chạy đủ; sửa tệp khác (hoặc
		# không đọc được Git) thì chạy đầy đủ.
		module = loadScript('check')
		groups = list(module.checkGroups())
		for changed, selected, message in (
			({'scripts/test_check.py'}, ['test_check'], 'chỉ thu hẹp tests'),
			({'scripts/test_check.py', 'README.md'}, None, 'chạy mọi kiểm tra'),
			(None, None, 'chạy mọi kiểm tra'),
		):
			with self.subTest(changed=changed):
				code, output, ran = self.runMain(['quick'], changed)
				self.assertEqual(code, 0)
				self.assertIn(message, output)
				self.assertEqual(ran, (groups, selected))

	def testToolsOnlyChecksToolsWithoutRunning(self):
		code, _, ran = self.runMain(['tools'])
		self.assertEqual(code, 0)
		self.assertIsNone(ran)

	def testCommandsRunTogetherAndKeepOrderedFailures(self):
		module = loadScript('check')
		commands = [['first'], ['second'], ['third']]
		barrier = threading.Barrier(len(commands), timeout=3)

		def runCommand(name, command):
			barrier.wait()
			return command == commands[1], f'{command[0]} hoàn tất\n'

		with (
			mock.patch.object(module, 'checkGroups', return_value={'content': commands}),
			mock.patch.object(module, 'runCommand', side_effect=runCommand),
		):
			output, failed = module.runGroup('content')
		self.assertEqual(
			output,
			''.join(f'$ {command[0]}\n{command[0]} hoàn tất\n' for command in commands),
		)
		self.assertEqual(failed, ['content: first', 'content: third'])

	def testQuickScopeFallsBackForSharedFilesAndDeletedTests(self):
		module = loadScript('check')
		self.assertEqual(module.quickTests({'scripts/test_check.py'}), ['test_check'])
		for paths in (
			None,
			set(),
			{'labels.yml'},
			{'scripts/test_missing.py'},
			{'scripts/test_check.py', 'scripts/check.py'},
		):
			self.assertIsNone(module.quickTests(paths))

	def testChangedFilesCombinesCommittedStagedAndNewFiles(self):
		# make quick xét commit so với origin/main, thay đổi chưa commit và tệp mới; một lệnh git lỗi (chưa có
		# origin/main…) thì không đoán phạm vi — trả None để chạy đầy đủ.
		module = loadScript('check')
		outputs = {
			'origin/main...HEAD': 'scripts/test_check.py\0',
			'HEAD': 'scripts/test_check.py\0README.md\0',
			'--others': 'scripts/test_new.py\0',
		}

		def run(command, *args, **kwargs):
			key = next(key for key in outputs if key in command)
			return subprocess.CompletedProcess(command, 0, outputs[key], '')

		with mock.patch.object(module.subprocess, 'run', run):
			self.assertEqual(
				module.changedFiles(),
				{'scripts/test_check.py', 'README.md', 'scripts/test_new.py'},
			)

		def failing(command, *args, **kwargs):
			code = 128 if 'origin/main...HEAD' in command else 0
			return subprocess.CompletedProcess(command, code, '', 'fatal: bad revision')

		with mock.patch.object(module.subprocess, 'run', failing):
			self.assertIsNone(module.changedFiles())

	def testQuickSelectionDoesNotMutateFullCommands(self):
		module = loadScript('check')
		commands = [list(command) for command in module.checkGroups()['content']]
		with mock.patch.object(module, 'runCommand', return_value=(True, '')) as run:
			module.runGroup('content', ['test_check'])
			run.assert_has_calls(
				[
					mock.call('content', commands[0]),
					mock.call('content', [*commands[-1], 'test_check']),
				],
				any_order=True,
			)
			run.reset_mock()
			module.runGroup('content')
			run.assert_has_calls(
				[mock.call('content', command) for command in commands], any_order=True
			)
			self.assertEqual(run.call_count, len(commands))
		self.assertEqual(module.checkGroups()['content'], commands)

	def testMinimumPythonDeclaredConsistently(self):
		# requires-python của pyproject.toml (ruff đọc khi chạy ngoài check.py) phải trùng --target-version mà
		# check.py, git hook truyền cho ruff và phiên bản check.py chặn — lệch thì VS Code và make check báo khác nhau.
		project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']
		major, minor = re.fullmatch(r'>=(\d+)\.(\d+)', project['requires-python']).groups()
		target = f'py{major}{minor}'
		lint = loadScript('check').checkGroups()['format']
		self.assertIn(['ruff', 'check', '--target-version', target, '.'], lint)
		hooks = (ROOT / 'scripts' / 'git-hooks.py').read_text(encoding='utf-8')
		self.assertIn(f"'--target-version', '{target}'", hooks)
		check = (ROOT / 'scripts' / 'check.py').read_text(encoding='utf-8')
		self.assertIn(f'sys.version_info < ({major}, {minor})', check)

	def testScriptsNeedingNewPythonReportOldVersionClearly(self):
		# python3 của macOS là 3.9; ứng dụng giao diện gọi hook, make gọi script bằng bản đó. Script dùng tomllib,
		# zip(strict=…) phải báo phiên bản cần thay vì traceback — giả lập Python 3.9: không có tomllib.
		simulate = (
			'import os, runpy, sys; sys.modules["tomllib"] = None; sys.version_info = (3, 9, 25); '
			'sys.version = "3.9.25 (giả lập)"; sys.argv = sys.argv[1:]; '
			'sys.path.insert(0, os.path.dirname(sys.argv[0])); '
			'runpy.run_path(sys.argv[0], run_name="__main__")'
		)
		for script, arguments in (
			('check.py', []),
			('validate.py', []),
			('git-hooks.py', ['post-merge', '0']),
			('org-setup.py', ['preview']),
			('check-tool-versions.py', []),
			('check-external-links.py', []),
			('check-github-forms.py', []),
		):
			with self.subTest(script=script):
				result = subprocess.run(
					[sys.executable, '-c', simulate, str(ROOT / 'scripts' / script), *arguments],
					cwd=ROOT,
					capture_output=True,
					text=True,
					timeout=30,
					check=False,
				)
				output = result.stdout + result.stderr
				self.assertEqual(result.returncode, 1, output)
				self.assertIn('Python ≥ 3.11 (đang dùng 3.9.25)', output)
				self.assertNotIn('Traceback', output)

	def testLabelerSupportsForksWithoutRunningPrCode(self):
		validator = loadScript('validate')
		for name in ('.github/workflows/labeler.yml', 'workflow-templates/labeler.yml'):
			with self.subTest(path=name):
				workflow = validator.loadYaml(ROOT / name, dict)
				# Psych đọc khóa YAML 1.1 "on" thành true; JSON chuyển khóa đó thành chuỗi "true".
				events = workflow.get('on', workflow.get('true', {}))
				self.assertIn('pull_request_target', events)
				self.assertNotIn('pull_request', events)
				self.assertIn('github.event.pull_request.number', workflow['concurrency']['group'])
				job = workflow['jobs']['label']
				self.assertEqual(job['permissions'], {'contents': 'read', 'pull-requests': 'write'})
				self.assertEqual(len(job['steps']), 1)
				self.assertTrue(job['steps'][0]['uses'].startswith('actions/labeler@'))
				self.assertNotIn('run', job['steps'][0])

	def testWorkflowLintIncludesBothYamlExtensions(self):
		module = loadScript('check')
		with tempfile.TemporaryDirectory() as folder:
			module.ROOT = Path(folder)
			for name in (
				'.github/workflows/check.yml',
				'.github/workflows/build.yaml',
				'workflow-templates/example.yaml',
			):
				path = module.ROOT / name
				path.parent.mkdir(parents=True, exist_ok=True)
				path.write_text('name: kiểm tra\n', encoding='utf-8')
			self.assertEqual(
				module.workflowFiles(),
				[
					'.github/workflows/build.yaml',
					'.github/workflows/check.yml',
					'workflow-templates/example.yaml',
				],
			)

	def testFailedDependencyInstallStopsChecksWithoutTraceback(self):
		module = loadScript('check')
		module.checkGroups()
		with tempfile.TemporaryDirectory() as folder:
			module.ROOT = Path(folder)
			output = io.StringIO()
			with (
				mock.patch.object(module.shutil, 'which', return_value='/bin/tool'),
				mock.patch.object(
					module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)
				),
				mock.patch.object(module.sys, 'argv', ['check.py', 'format']),
				mock.patch.object(module, 'runGroups') as run,
				contextlib.redirect_stdout(output),
			):
				self.assertEqual(module.main(), 1)
			self.assertIn('Không cài được thư viện Node.js', output.getvalue())
			run.assert_not_called()

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
		# Nhóm chậm (đầu) và nhóm nhanh chạy cùng lúc; đầu ra vẫn theo thứ tự nhóm, lệnh lỗi được liệt kê. Barrier
		# chỉ mở khi cả hai nhóm cùng đang chạy — chạy tuần tự thì hết hạn chờ; không đo thời gian nên không phụ
		# thuộc tốc độ máy.
		module = loadScript('check')
		barrier = threading.Barrier(2, timeout=10)

		def runGroup(name, selectedTests=None):
			barrier.wait()
			if name == 'slow':
				time.sleep(0.05)  # xong sau nhóm nhanh: đầu ra vẫn phải đứng trước
				return '$ slow\nchậm\n', []
			return '$ fast\nnhanh\n', ['fast: fast']

		output = io.StringIO()
		with (
			mock.patch.object(module, 'runGroup', runGroup),
			contextlib.redirect_stdout(output),
		):
			self.assertFalse(module.runGroups(['slow', 'fast']))
		text = output.getvalue()
		self.assertLess(text.index('chậm'), text.index('nhanh'))
		self.assertIn('❌ fast:', text)

	def testPrettierUsesInstalledVersion(self):
		# --no: không tự tải Prettier mới nhất; thiếu "--" thì npm coi --check là cấu hình của npm, in tệp rồi
		# thoát 0 mà Prettier không chạy.
		module = loadScript('check')
		with mock.patch.object(module, 'shellScripts', return_value=[]):
			command = module.checkGroups()['format'][0]
		self.assertEqual(command[:4], ['npx', '--no', '--', 'prettier'])
		makefile = (ROOT / 'Makefile').read_text(encoding='utf-8')
		self.assertIn('\tnpx --no -- prettier --write .\n', makefile)

	def testNodeModulesReinstalledWhenMissingOrOutdated(self):
		# Thiếu thư viện (NODE_ENV=production làm npm bỏ devDependencies) hoặc khác phiên bản package.json (sau khi
		# Dependabot nâng) thì cài lại, kèm devDependencies; đúng phiên bản thì không gọi npm.
		module = loadScript('check')
		with tempfile.TemporaryDirectory() as folder:
			root = Path(folder)
			(root / 'package.json').write_text(
				'{"devDependencies": {"prettier": "3.9.9"}}', encoding='utf-8'
			)
			installed = root / 'node_modules' / 'prettier' / 'package.json'
			module.ROOT = root
			for case, version, expected in (
				('missing', None, True),
				('outdated', '3.9.8', True),
				('current', '3.9.9', False),
			):
				if version:
					installed.parent.mkdir(parents=True, exist_ok=True)
					installed.write_text(f'{{"version": "{version}"}}', encoding='utf-8')
				passed = subprocess.CompletedProcess([], 0, '', '')
				with (
					mock.patch.object(module, 'checkGroups', return_value={'audit': [['npm']]}),
					mock.patch.object(module.shutil, 'which', return_value='/bin/x'),
					mock.patch.object(module.subprocess, 'run', return_value=passed) as run,
				):
					self.assertTrue(module.ensureTools(['audit']), case)
				calls = [call.args[0] for call in run.call_args_list]
				self.assertEqual(calls, [module.NPM_INSTALL] if expected else [], case)
				if expected:
					self.assertIn('--include=dev', module.NPM_INSTALL)


if __name__ == '__main__':
	unittest.main()
