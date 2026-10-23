"""Kiểm tra nhập Repository policies từ trang web, giữ allow list và dữ liệu riêng của bản khôi phục."""

import contextlib
import io
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript

from orgsetup import backup, configuration, github, inventory, localdata, repopolicies


def policyFixture():
	actors = [
		{
			'name': name,
			'actorType': kind,
			'actorId': actorId,
			'bypassMode': 0,
			'owner': 'PAGE_ONLY_METADATA',
		}
		for name, kind, actorId in (
			('Organization admin', 'OrganizationAdmin', None),
			('Deploy keys', 'DeployKey', None),
			('Repository migrations', 'RepositoryMigration', None),
			('Repository admin', 'RepositoryRole', 5),
			('Dependabot', 'Integration', 101),
			('GitHub Merge Queue', 'Integration', 102),
			('Copilot code review', 'Integration', 103),
			('Copilot cloud agent', 'Integration', 104),
			('GitHub Code Quality Agent', 'Integration', 105),
		)
	]
	return {
		'id': 7,
		'name': 'RepoPolicies',
		'target': 'repository',
		'enforcement': 'enabled',
		'source': {'name': github.ORG, 'type': 'Organization'},
		'missingConditionTargets': [],
		'conditions': [
			{'target': 'repository_name', 'parameters': {'include': ['~ALL'], 'exclude': []}}
		],
		'bypassActors': actors,
		'rules': [
			{
				'ruleType': 'repository_visibility',
				'parameters': {'public': False, 'private': True, 'internal': False},
			},
			*(
				{'ruleType': kind, 'parameters': {}}
				for kind in ('repository_create', 'repository_delete', 'repository_transfer')
			),
			{
				'ruleType': 'repository_name',
				'parameters': {'negate': True, 'pattern': '^fixture-name$'},
			},
		],
	}


class RepositoryPoliciesTest(unittest.TestCase):
	def setUp(self):
		self.directory = tempfile.TemporaryDirectory()
		self.addCleanup(self.directory.cleanup)
		self.root = Path(self.directory.name) / 'repo'
		self.root.mkdir()
		self.configPath = self.root / configuration.CONFIG_NAME
		config = {
			'organization_name': github.ORG,
			'repository_defaults': {},
			'organization': {'settings': {}, 'web_settings': {}, 'endpoints': {}},
			'repositories': {},
			'unavailable': {},
		}
		self.configPath.write_text(configuration.jsonText(config), encoding='utf-8')
		self.stack = contextlib.ExitStack()
		self.addCleanup(self.stack.close)
		self.stack.enter_context(mock.patch.object(github, 'ROOT', self.root))
		self.stack.enter_context(
			mock.patch.dict(
				os.environ, ORGSETUP_PRIVATE_DIR=str(Path(self.directory.name) / 'private')
			)
		)
		localdata.resetCapture()
		self.addCleanup(localdata.resetCapture)

	def page(self, policy=None, name='page.html'):
		path = Path(self.directory.name) / name
		data = {
			'payload': {
				'ruleset': policy if policy is not None else policyFixture(),
				'session': 'PAGE_ONLY_METADATA',
			},
			'appPayload': {},
		}
		path.write_text(
			'<script type="application/json" id="client-env">{"login":"PAGE_ONLY_METADATA"}</script><script type="application/json" data-target="react-app.embeddedData">'
			+ json.dumps(data)
			+ '</script>',
			encoding='utf-8',
		)
		return path

	def importPage(self, path):
		with contextlib.redirect_stdout(io.StringIO()) as output:
			repopolicies.importPolicyPages([path])
		self.assertNotIn('^fixture-name$', output.getvalue())
		return configuration.readConfig()

	def testImportPreservesAllActorsRulesAndPrivateDefinition(self):
		config = self.importPage(self.page())
		item = config['organization']['observed']['repository_policies'][0]
		self.assertEqual(item['enforcement'], 'active')
		self.assertEqual(
			item['conditions'], {'repository_name': {'include': ['~ALL'], 'exclude': []}}
		)
		self.assertEqual(
			[
				(actor['name'], actor['actor_type'], actor['actor_id'], actor['bypass_mode'])
				for actor in item['bypass_actors']
			],
			[
				(actor['name'], actor['actorType'], actor['actorId'], 'always')
				for actor in policyFixture()['bypassActors']
			],
		)
		self.assertEqual(len(item['rules']), 5)
		self.assertEqual(
			item['rules'][0]['parameters'], {'public': False, 'private': True, 'internal': False}
		)
		parameters = item['rules'][-1]['parameters']
		self.assertTrue(parameters['negate'])
		self.assertEqual(localdata.privateValue(parameters['pattern_source']), '^fixture-name$')
		manual = config['organization']['manual_settings']['repository_policies']
		self.assertEqual(manual['status'], 'pending')
		self.assertEqual(
			json.loads(localdata.privateValue(manual['configuration_source']))[0]['rules'][-1][
				'parameters'
			]['pattern'],
			'^fixture-name$',
		)
		public = self.configPath.read_text()
		self.assertNotIn('PAGE_ONLY_METADATA', public)
		self.assertNotIn('^fixture-name$', public)
		self.assertNotIn('PAGE_ONLY_METADATA', localdata.dataPath().read_text())
		self.assertEqual(localdata.dataPath().stat().st_mode & 0o777, 0o600)

	def testInvalidPageStopsBeforeWritingSourceOrPrivateData(self):
		original = self.configPath.read_bytes()
		for field in ('source', 'actor', 'mode', 'target', 'condition', 'rule'):
			with self.subTest(field=field):
				policy = policyFixture()
				if field == 'source':
					policy['source']['name'] = 'another-organization'
				elif field == 'actor':
					policy['bypassActors'][-1]['actorId'] = None
				elif field == 'mode':
					policy['bypassActors'][-1]['bypassMode'] = 1
				elif field == 'target':
					policy['target'] = 'branch'
				elif field == 'condition':
					policy['missingConditionTargets'] = ['repository']
				else:
					policy['rules'][-1]['ruleType'] = 'unknown_rule'
				with self.assertRaises((ValueError, TypeError)):
					repopolicies.importPolicyPages([self.page(), self.page(policy, 'invalid.html')])
				self.assertEqual(self.configPath.read_bytes(), original)
				self.assertFalse(localdata.dataPath().exists())

	def testRefreshApiPreservesWebSnapshotAndManualReference(self):
		config = self.importPage(self.page())
		scope = config['organization']
		captured = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'observed': {'rulesets': []},
		}
		refreshed = inventory.refreshScope(scope, captured, f'orgs/{github.ORG}', {}, {})
		self.assertEqual(
			refreshed['observed']['repository_policies'], scope['observed']['repository_policies']
		)
		self.assertEqual(
			refreshed['manual_settings']['repository_policies'],
			scope['manual_settings']['repository_policies'],
		)
		self.assertEqual(refreshed['observed']['rulesets'], [])
		refreshed['observed']['repository_policies'][0]['name'] = 'Changed'
		self.assertEqual(scope['observed']['repository_policies'][0]['name'], 'RepoPolicies')

	def testImportReplacesSameIdAndKeepsOtherPoliciesAndEmptyRegex(self):
		first = policyFixture()
		first['rules'][-1]['parameters']['pattern'] = ''
		self.importPage(self.page(first))
		second = policyFixture()
		second.update(id=8, name='OtherPolicy')
		config = self.importPage(self.page(second))
		self.assertEqual(len(config['organization']['observed']['repository_policies']), 2)
		first['name'] = 'Renamed'
		config = self.importPage(self.page(first))
		self.assertEqual(
			{
				policy['name']
				for policy in config['organization']['observed']['repository_policies']
			},
			{'Renamed', 'OtherPolicy'},
		)

	def testWebPolicyNeverEntersApiCollectionsAndBackupIncludesPrivateData(self):
		config = self.importPage(self.page())
		self.assertNotIn('repository_policies', config['organization'].get('collections', {}))
		path = Path(self.directory.name) / 'backup.tar.gz'
		with contextlib.redirect_stdout(io.StringIO()):
			self.assertEqual(backup.writeBackup(path), 1)
		with tarfile.open(path, 'r:gz') as archive:
			values = json.load(archive.extractfile('values.json'))
			self.assertTrue(localdata.valueReferences(config) <= values.keys())
			self.assertIn('^fixture-name$', values.values())
		config['organization'].setdefault('collections', {})['repository_policies'] = config[
			'organization'
		]['observed']['repository_policies']
		with self.assertRaises(ValueError):
			configuration.validateConfig(config)

	def testCliRejectsNonPolicyHtmlWithoutLeakingPageContents(self):
		module = loadScript('import-repository-policies')
		path = Path(self.directory.name) / 'bad.html'
		path.write_text('PAGE_ONLY_METADATA', encoding='utf-8')
		with (
			mock.patch.object(module.sys, 'argv', ['import-repository-policies.py', str(path)]),
			contextlib.redirect_stderr(io.StringIO()) as output,
		):
			self.assertEqual(module.main(), 1)
		self.assertNotIn('PAGE_ONLY_METADATA', output.getvalue())
