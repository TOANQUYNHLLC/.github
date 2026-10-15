"""Test tự động cho scripts/check-tool-versions.py.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import http.client
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

MISE = '[tools]\nruff = "0.16.10"\nshellcheck = "0.11.0"\nactionlint = "1.7.12"\n'


class ToolVersionsTest(unittest.TestCase):
	def testMissingCliExecutableReturnsAnonymousToken(self):
		module = loadScript('check-tool-versions')
		with (
			mock.patch.object(module.shutil, 'which', return_value='gh'),
			mock.patch.object(module.subprocess, 'run', side_effect=FileNotFoundError('gh')),
		):
			self.assertEqual(module.cliToken(), '')

	def testEnvironmentTokenAvoidsCliLookup(self):
		module = loadScript('check-tool-versions')
		releases = {
			'astral-sh/ruff': '0.16.10',
			'koalaman/shellcheck': '0.11.0',
			'rhysd/actionlint': '1.7.12',
		}
		for key in ('GH_TOKEN', 'GITHUB_TOKEN'):
			with (
				self.subTest(key=key),
				mock.patch.dict(module.os.environ, {key: 'provided_token'}, clear=True),
				mock.patch.object(module, 'cliToken') as cli,
				mock.patch.object(module, 'templateOnlyActions', dict),
				mock.patch.object(
					module, 'latestRelease', side_effect=lambda repo, *args: releases[repo]
				) as latest,
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(module.main(), 0)
			cli.assert_not_called()
			self.assertEqual(
				[call.args[1] for call in latest.call_args_list], ['provided_token'] * 3
			)

	def testCliTokenIsRefreshedForEachRun(self):
		module = loadScript('check-tool-versions')
		releases = {
			'astral-sh/ruff': '0.16.10',
			'koalaman/shellcheck': '0.11.0',
			'rhysd/actionlint': '1.7.12',
		}
		responses = [
			subprocess.CompletedProcess([], 0, 'first_token\n', ''),
			subprocess.CompletedProcess([], 0, 'second_token\n', ''),
		]
		with (
			mock.patch.dict(module.os.environ, {}, clear=True),
			mock.patch.object(module.shutil, 'which', return_value='gh'),
			mock.patch.object(module.subprocess, 'run', side_effect=responses) as read,
			mock.patch.object(module, 'templateOnlyActions', dict),
			mock.patch.object(
				module, 'latestRelease', side_effect=lambda repo, *args: releases[repo]
			) as latest,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(module.main(), 0)
			self.assertEqual(module.main(), 0)
		self.assertEqual(read.call_count, 2)
		self.assertEqual(
			[call.args[1] for call in latest.call_args_list],
			['first_token'] * 3 + ['second_token'] * 3,
		)

	def testExplicitAnonymousTokenDoesNotReadCli(self):
		module = loadScript('check-tool-versions')
		with (
			mock.patch.object(module, 'cliToken') as cli,
			mock.patch.object(
				module.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"tag_name":"v1.2.3"}')
			) as read,
		):
			self.assertEqual(module.latestRelease('example/tool', token=''), '1.2.3')
		cli.assert_not_called()
		self.assertNotIn('Authorization', read.call_args.args[0].headers)

	def testMalformedReleasesAreRejected(self):
		module = loadScript('check-tool-versions')
		for data in (
			[],
			{},
			{'tag_name': None},
			{'tag_name': 42},
			{'tag_name': ''},
			{'tag_name': 'garbage'},
		):
			with (
				self.subTest(data=data),
				mock.patch.object(module, 'cliToken', str),
				mock.patch.object(
					module.urllib.request,
					'urlopen',
					return_value=io.BytesIO(json.dumps(data).encode()),
				),
				self.assertRaises((ValueError, TypeError)),
			):
				module.latestRelease('example/tool')

	def testInvalidLocalVersionsFailBeforeNetwork(self):
		module = loadScript('check-tool-versions')
		for content in (
			'[tools\n',
			'[tools]\nruff = "latest"\n',
			'[tools]\nruff = "0.16.10"\n',
			'tools = []\n',
		):
			with self.subTest(content=content), tempfile.TemporaryDirectory() as folder:
				module.ROOT = Path(folder)
				(module.ROOT / 'mise.toml').write_text(content, encoding='utf-8')
				with (
					mock.patch.object(module, 'latestRelease') as network,
					contextlib.redirect_stdout(io.StringIO()),
				):
					self.assertEqual(module.main(), 1)
					network.assert_not_called()

	def runCheck(self, latestRelease):
		"""Chạy main() với mise.toml mẫu và bản phát hành giả; trả (mã thoát, đầu ra)."""
		module = loadScript('check-tool-versions')
		output = io.StringIO()
		with tempfile.TemporaryDirectory() as folder:
			(Path(folder) / 'mise.toml').write_text(MISE, encoding='utf-8')
			module.ROOT = Path(folder)
			with (
				mock.patch.object(
					module, 'latestRelease', lambda repository, token: latestRelease(repository)
				),
				mock.patch.object(module, 'cliToken', str),
				contextlib.redirect_stdout(output),
			):
				code = module.main()
		return code, output.getvalue()

	def testCurrentToolsPass(self):
		releases = {'astral-sh/ruff': '0.16.10', 'koalaman/shellcheck': '0.11.0'}
		code, output = self.runCheck(lambda repository: releases.get(repository, '1.7.12'))
		self.assertEqual(code, 0, output)
		self.assertIn('✅ Công cụ đều mới nhất.', output)

	def testNewerReleaseIsReported(self):
		# So theo số (0.16.10 < 0.17.0), không theo chữ.
		releases = {'astral-sh/ruff': '0.17.0', 'koalaman/shellcheck': '0.11.0'}
		code, output = self.runCheck(lambda repository: releases.get(repository, '1.7.12'))
		self.assertEqual(code, 1)
		self.assertIn('⬆️  ruff 0.16.10 → 0.17.0', output)
		self.assertIn('✅ shellcheck 0.11.0', output)

	def testUnreadableReleaseIsReported(self):
		# Máy chủ ngắt kết nối khi đang đọc phản hồi (lỗi urllib không gói thành URLError): báo công cụ đó, không
		# làm dừng cả lượt kiểm tra.
		def latestRelease(repository):
			if repository == 'astral-sh/ruff':
				raise http.client.RemoteDisconnected('đóng kết nối')
			return {'koalaman/shellcheck': '0.11.0'}.get(repository, '1.7.12')

		code, output = self.runCheck(latestRelease)
		self.assertEqual(code, 1)
		self.assertIn('❌ ruff: không đọc được bản phát hành mới nhất (đóng kết nối)', output)
		self.assertIn('✅ actionlint 1.7.12', output)

	def testTemplateOnlyActionsAreChecked(self):
		# Dependabot chỉ quét .github/workflows/: action chỉ có trong workflow-templates/ được so với bản phát hành
		# mới nhất; action có trong .github/workflows/ không hỏi lại. Nhiều mẫu dùng khác nhau thì lấy bản thấp nhất.
		sha = '0' * 40
		workflows = {
			'.github/workflows/ci.yml': f'steps:\n    - uses: actions/checkout@{sha} # v7.0.1\n',
			'workflow-templates/docker.yml': (
				f'steps:\n    - uses: actions/checkout@{sha} # v6.0.0\n'
				f'    - uses: docker/login-action@{sha} # v4.6.0\n'
				f'    - name: Go\n      uses: actions/setup-go@{sha} # v7.0.0\n'
			),
			'workflow-templates/old.yaml': f'jobs:\n  - uses: docker/login-action@{sha} # v4.5.0\n',
		}
		module = loadScript('check-tool-versions')
		with tempfile.TemporaryDirectory() as folder:
			module.ROOT = Path(folder)
			for name, text in workflows.items():
				(module.ROOT / name).parent.mkdir(parents=True, exist_ok=True)
				(module.ROOT / name).write_text(text, encoding='utf-8')
			self.assertEqual(
				module.templateOnlyActions(),
				{'docker/login-action': '4.5.0', 'actions/setup-go': '7.0.0'},
			)

		releases = {
			'docker/login-action': '4.6.0',
			'actions/setup-go': '7.0.0',
			'koalaman/shellcheck': '0.11.0',
		}
		module = loadScript('check-tool-versions')
		output = io.StringIO()
		with tempfile.TemporaryDirectory() as folder:
			module.ROOT = Path(folder)
			(module.ROOT / 'mise.toml').write_text(MISE, encoding='utf-8')
			with (
				mock.patch.object(
					module,
					'templateOnlyActions',
					return_value={'docker/login-action': '4.5.0', 'actions/setup-go': '7.0.0'},
				),
				mock.patch.object(
					module,
					'latestRelease',
					lambda repository, token: releases.get(
						repository, '0.16.10' if 'ruff' in repository else '1.7.12'
					),
				),
				mock.patch.object(module, 'cliToken', str),
				contextlib.redirect_stdout(output),
			):
				self.assertEqual(module.main(), 1)
		text = output.getvalue()
		self.assertIn(
			'⬆️  docker/login-action 4.5.0 → 4.6.0: sửa SHA và chú thích trong workflow-templates/',
			text,
		)
		self.assertIn('✅ actions/setup-go 7.0.0', text)


if __name__ == '__main__':
	unittest.main()
