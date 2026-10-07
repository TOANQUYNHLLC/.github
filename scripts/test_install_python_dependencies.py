"""Test cài phụ thuộc của workflow mẫu Python; không tải mạng hoặc cài package khi chạy tests."""

import contextlib
import io
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

try:
	from testsupport import ROOT, loadScript
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript


class PythonDependenciesTest(unittest.TestCase):
	def setUp(self):
		self.module = loadScript('install-python-dependencies')
		self.tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self.tmp.cleanup)
		self.project = Path(self.tmp.name)

	def testRequirementsAndPackageInstallBeforePinnedTools(self):
		for name in ('requirements.txt', 'requirements-dev.txt'):
			(self.project / name).write_text('pytest\n', encoding='utf-8')
		(self.project / 'pyproject.toml').write_text(
			'[project]\nname = "example"\nversion = "0"\ndependencies = ["requests"]\n',
			encoding='utf-8',
		)
		commands = self.module.dependencyCommands(self.project)
		version = tomllib.loads((ROOT / 'mise.toml').read_text(encoding='utf-8'))['tools']['ruff']
		prefix = [self.module.sys.executable, '-m', 'pip', 'install']
		self.assertEqual(
			commands,
			[
				[*prefix, '-r', 'requirements.txt'],
				[*prefix, '-r', 'requirements-dev.txt'],
				[*prefix, '-e', '.'],
				[*prefix, f'ruff=={version}', 'pytest'],
			],
		)

	def testPackageDetectionSupportsBuildBackendsAndLegacySetup(self):
		for filename, contents in (
			('setup.py', ''),
			('setup.cfg', '[metadata]\nname = example\n'),
			('pyproject.toml', '[build-system]\nrequires = ["setuptools"]\n'),
			('pyproject.toml', '[tool.poetry]\nname = "example"\n'),
			('pyproject.toml', '[project]\ndynamic = ["dependencies"]\n'),
		):
			with self.subTest(filename=filename, contents=contents):
				path = self.project / filename
				path.write_text(contents, encoding='utf-8')
				try:
					self.assertEqual(
						self.module.dependencyCommands(self.project)[0][-2:], ['-e', '.']
					)
				finally:
					path.unlink()

	def testToolOnlyOrMetadataOnlyProjectDoesNotInstallPackage(self):
		for contents in (
			'[tool.ruff]\nline-length = 100\n',
			'[project]\nname = "example"\nversion = "0"\nrequires-python = ">=3.11"\n',
		):
			with self.subTest(contents=contents):
				(self.project / 'pyproject.toml').write_text(contents, encoding='utf-8')
				self.assertEqual(len(self.module.dependencyCommands(self.project)), 1)

	def testSetupConfigOnlyForToolsDoesNotInstallPackage(self):
		(self.project / 'setup.cfg').write_text(
			'[flake8]\nmax-line-length = 100\n', encoding='utf-8'
		)
		self.assertEqual(len(self.module.dependencyCommands(self.project)), 1)

	def testMalformedManifestStopsBeforeAnyInstallation(self):
		(self.project / 'pyproject.toml').write_text('[project\n', encoding='utf-8')
		with (
			mock.patch.object(self.module.Path, 'cwd', return_value=self.project),
			mock.patch.object(self.module.subprocess, 'run') as run,
			contextlib.redirect_stderr(io.StringIO()),
		):
			self.assertEqual(self.module.main(), 1)
		run.assert_not_called()

	def testInstallationFailureStopsRemainingCommands(self):
		(self.project / 'requirements.txt').write_text('example\n', encoding='utf-8')
		with (
			mock.patch.object(self.module.Path, 'cwd', return_value=self.project),
			mock.patch.object(
				self.module.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, ['pip'])
			) as run,
			contextlib.redirect_stderr(io.StringIO()),
		):
			self.assertEqual(self.module.main(), 1)
		run.assert_called_once()


if __name__ == '__main__':
	unittest.main()
