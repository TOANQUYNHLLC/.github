"""Bản khôi phục web giữ chính sách bị API ẩn và không lưu phiên hoặc credentials."""

import contextlib
import copy
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orgsetup import backup, configuration, github, inventory, localdata, websettings


class WebSettingsTest(unittest.TestCase):
	def setUp(self):
		self.directory = tempfile.TemporaryDirectory()
		self.addCleanup(self.directory.cleanup)
		self.root = Path(self.directory.name) / 'repo'
		self.root.mkdir()
		self.config = {
			'organization_name': github.ORG,
			'repository_defaults': {},
			'organization': {'settings': {}, 'web_settings': {}, 'endpoints': {}},
			'repositories': {},
			'unavailable': {},
		}
		self.configPath = self.root / configuration.CONFIG_NAME
		self.configPath.write_text(configuration.jsonText(self.config))
		stack = contextlib.ExitStack()
		self.addCleanup(stack.close)
		stack.enter_context(mock.patch.object(github, 'ROOT', self.root))
		stack.enter_context(
			mock.patch.dict(
				os.environ, ORGSETUP_PRIVATE_DIR=str(Path(self.directory.name) / 'private')
			)
		)
		localdata.resetCapture()
		self.addCleanup(localdata.resetCapture)
		self.url = f'https://github.com/organizations/{github.ORG}/settings/security'

	def page(self, content, name='page.html'):
		path = Path(self.directory.name) / name
		path.write_text(content, encoding='utf-8')
		return path

	def testParserKeepsControlsAndRejectsSessionAndSecretFields(self):
		path = self.page("""<title>Settings</title><main><nav>PROFILE_ONLY</nav><div class="Layout-main">
			<script>SESSION_ONLY</script><form action="/organizations/TOANQUYNHLLC/settings/security">
			<input name="authenticity_token" value="SESSION_ONLY" type="hidden">
			<input name="password" value="SECRET_ONLY" type="password">
			<input name="organization[personal_access_tokens_policy]" value="restricted" type="radio" checked>
			<input name="require_2fa" type="checkbox" value="1" checked>
			<input name="other" type="checkbox" value="1">
			<select name="expiry"><option value="30">30 days</option><option value="90" selected>90 days</option></select>
			<textarea name="policy">fixture policy</textarea></form></div></main>""")
		_, page, _ = websettings.readSettingsPage(self.url, path, [])
		serialized = json.dumps(page)
		for value in ('SESSION_ONLY', 'SECRET_ONLY', 'PROFILE_ONLY'):
			self.assertNotIn(value, serialized)
		fields = {item['name']: item for item in page['fields']}
		self.assertTrue(fields['require_2fa']['checked'])
		self.assertFalse(fields['other']['checked'])
		self.assertEqual(fields['policy']['value'], 'fixture policy')
		self.assertTrue(fields['expiry']['options'][1]['selected'])
		self.assertIn('organization[personal_access_tokens_policy]', fields)

	def testRepeatedFormsKeepTheirContainersAndDoNotTruncateThePanel(self):
		rows = ''.join(
			f'<form action="/labels/{index}"><div><div><input name="label[name]" value="label-{index}"></form></div></div>'
			for index in range(30)
		)
		path = self.page(
			'<title>Settings</title><main><form><div class="Layout-main">'
			'<input name="first" value="inside"></form>'
			+ rows
			+ '<input name="last" value="inside"></div>'
			'<input name="profile" value="PROFILE_ONLY"></main>'
		)
		_, page, _ = websettings.readSettingsPage(self.url, path, [])
		fields = page['fields']
		self.assertEqual(
			[field['name'] for field in fields], ['first', *['label[name]'] * 30, 'last']
		)
		self.assertEqual(
			[field['value'] for field in fields[1:-1]], [f'label-{index}' for index in range(30)]
		)
		self.assertEqual(
			[field['form'] for field in fields[1:-1]], [f'/labels/{index}' for index in range(30)]
		)
		self.assertNotIn('PROFILE_ONLY', json.dumps(page))

	def testImportKeepsPrivateValuesOutOfPublicSourceAndPreservesOtherPages(self):
		first = self.page(
			'<title>Settings</title><div class="Layout-main"><input name="fixture" value="PRIVATE_VALUE"></div>'
		)
		second = self.page(
			'<title>Settings</title><div class="Layout-main"><input name="mode" value="off"></div>',
			'second.html',
		)
		with contextlib.redirect_stdout(io.StringIO()):
			websettings.importSettingsPages([{'url': self.url, 'path': first}])
			websettings.importSettingsPages([{'url': self.url + '?page=2', 'path': second}])
		config = configuration.readConfig()
		self.assertNotIn('PRIVATE_VALUE', self.configPath.read_text())
		manual = config['organization']['manual_settings']['authentication']
		self.assertEqual(manual['status'], 'pending')
		private = json.loads(localdata.privateValue(manual['configuration_source']))
		self.assertEqual(len(private['pages']), 2)
		self.assertIn('secrets', private['excluded_groups'])
		refreshed = inventory.refreshScope(
			config['organization'], self.config['organization'], f'orgs/{github.ORG}', {}, {}
		)
		self.assertEqual(refreshed['manual_settings']['authentication'], manual)

	def testEmptyFragmentAliasDoesNotReplaceCanonicalSettings(self):
		path = self.page(
			'<title>Settings</title><main><input name="policy" value="CURRENT_VALUE"></main>'
		)
		with contextlib.redirect_stdout(io.StringIO()):
			websettings.importSettingsPages([{'url': self.url + '#', 'path': path}])
		config = configuration.readConfig()
		item = config['organization']['manual_settings']['settings_pages']
		stored = json.loads(localdata.privateValue(item['configuration_source']))
		self.assertEqual(stored['pages'][0]['url'], self.url)
		alias = copy.deepcopy(stored['pages'][0])
		alias['url'] += '#'
		alias['fields'][0]['value'] = 'STALE_VALUE'
		stored['pages'].append(alias)
		item['configuration_source'] = localdata.captureValue(
			'manual/settings-pages', json.dumps(stored)
		)
		with contextlib.redirect_stdout(io.StringIO()):
			websettings.saveConfig(config)
			websettings.importSettingsPages([{'url': self.url + '?page=2', 'path': path}])
		config = configuration.readConfig()
		item = config['organization']['manual_settings']['settings_pages']
		stored = json.loads(localdata.privateValue(item['configuration_source']))
		pages = {page['url']: page for page in stored['pages']}
		self.assertEqual(set(pages), {self.url, self.url + '?page=2'})
		self.assertEqual(pages[self.url]['fields'][0]['value'], 'CURRENT_VALUE')
		self.assertNotIn('STALE_VALUE', json.dumps(stored))
		self.assertEqual(alias['url'], self.url + '#')
		self.assertEqual(alias['fields'][0]['value'], 'STALE_VALUE')

	def testInvalidBatchDoesNotWritePartialSourceOrPrivateData(self):
		path = self.page('<title>Settings</title><main>Settings</main>')
		before = self.configPath.read_bytes()
		with self.assertRaises(ValueError):
			websettings.importSettingsPages(
				[
					{'url': self.url, 'path': path},
					{
						'url': 'https://github.com/organizations/other/settings/security',
						'path': path,
					},
				]
			)
		self.assertEqual(self.configPath.read_bytes(), before)
		self.assertFalse(localdata.dataPath().exists())

	def testCredentialPagesAndHtmlInRepositoryAreRejected(self):
		path = self.page('<title>Settings</title><main>Settings</main>')
		for suffix in ('/secrets', '/secrets/actions', '/deploy_keys', '/hooks'):
			with self.subTest(suffix=suffix), self.assertRaises(ValueError):
				websettings.readSettingsPage(self.url.replace('/security', suffix), path, [])
		inside = self.root / 'raw.html'
		inside.write_text(path.read_text())
		with self.assertRaises(ValueError):
			websettings.readSettingsPage(self.url, inside, [])

	def testUnnamedAndAriaControlsPreserveTheirState(self):
		path = self.page(
			'<title>Settings</title><main><input id="feature" type="checkbox" checked><button id="review" role="switch" aria-checked="true">Review</button><button id="mixed" aria-pressed="mixed">Mixed</button></main>'
		)
		_, page, _ = websettings.readSettingsPage(self.url, path, [])
		fields = {item['name']: item for item in page['fields']}
		self.assertTrue(fields['feature']['checked'])
		self.assertEqual(fields['feature']['locator']['id'], 'feature')
		self.assertEqual(fields['review']['aria-checked'], 'true')
		self.assertEqual(fields['mixed']['aria-pressed'], 'mixed')

	def testBackupContainsPrivatePagesAndChecksWithoutOriginalMachine(self):
		path = self.page(
			'<title>Settings</title><main><input name="policy" value="PRIVATE_VALUE"></main>'
		)
		archive = Path(self.directory.name) / 'backup.tar.gz'
		with contextlib.redirect_stdout(io.StringIO()):
			websettings.importSettingsPages([{'url': self.url, 'path': path}])
			self.assertEqual(backup.writeBackup(archive), 1)
		with (
			mock.patch.object(
				localdata, 'readValues', side_effect=AssertionError('Không đọc tệp riêng tại máy')
			),
			mock.patch.object(github, 'gh', side_effect=AssertionError('Không gọi GitHub')),
		):
			config, values, problems = backup.readBackup(archive)
		ref = config['organization']['manual_settings']['authentication']['configuration_source']
		self.assertIn('PRIVATE_VALUE', values[ref])
		self.assertTrue(problems)
		self.assertNotIn('PRIVATE_VALUE', json.dumps(config))

	def testMembershipImportKeepsOnlyRestoreFieldsOutsideGitAndFailsAtomically(self):
		def read(path):
			if '/members?role=admin' in path:
				return [{'login': 'fixture-owner', 'avatar_url': 'PROFILE_ONLY'}]
			if path.endswith('/invitations'):
				return [
					{
						'login': 'fixture-invitee',
						'role': 'direct_member',
						'email': None,
						'inviter': {'login': 'PROFILE_ONLY'},
					}
				]
			return []

		with (
			mock.patch.object(github, 'ghList', side_effect=read),
			contextlib.redirect_stdout(io.StringIO()),
		):
			websettings.importMemberships()
		config = configuration.readConfig()
		self.assertNotIn('fixture-owner', json.dumps(config))
		manual = config['organization']['manual_settings']['members_and_collaborators']
		private = json.loads(localdata.privateValue(manual['configuration_source']))
		self.assertEqual(
			private['membership']['accounts'], [{'login': 'fixture-owner', 'role': 'admin'}]
		)
		self.assertNotIn('PROFILE_ONLY', json.dumps(private))
		before = self.configPath.read_bytes()
		with (
			mock.patch.object(github, 'ghList', side_effect=RuntimeError('API lỗi')),
			self.assertRaises(RuntimeError),
		):
			websettings.importMemberships()
		self.assertEqual(self.configPath.read_bytes(), before)

	def testWebOnlyActorCannotBeSentThroughApiCollections(self):
		item = {
			'ruleset_id': 7,
			'name': 'Fixture',
			'target': 'tag',
			'enforcement': 'active',
			'conditions': {'ref_name': {'include': ['~ALL'], 'exclude': []}},
			'bypass_actors': [
				{
					'name': 'Repository migrations',
					'actor_id': None,
					'actor_type': 'RepositoryMigration',
					'bypass_mode': 'always',
				},
			],
			'rules': [{'type': 'required_signatures'}],
		}
		config = copy.deepcopy(self.config)
		config['organization']['observed'] = {'web_rulesets': [item]}
		self.assertEqual(configuration.validateConfig(config), config)
		apiItem = {key: value for key, value in item.items() if key != 'ruleset_id'}
		config['organization']['collections'] = {'rulesets': [apiItem]}
		with self.assertRaises(ValueError):
			configuration.validateConfig(config)
		refreshed = inventory.refreshScope(
			{'observed': {'web_rulesets': [item]}},
			self.config['organization'],
			f'orgs/{github.ORG}',
			{},
			{},
		)
		self.assertEqual(refreshed['observed']['web_rulesets'], [item])

	def testUnparsedPageIsExplicitlyIncompleteAndForeignLinksAreExcluded(self):
		path = self.page(
			f'<title>Settings</title><a href="{self.url}">Settings</a><a href="https://github.com/organizations/other/settings">Other</a>'
		)
		_, page, links = websettings.readSettingsPage(self.url, path, [])
		self.assertEqual(links, [self.url])
		self.assertEqual(len(page['limitations']), 3)

	def testReadWebRulesetPreservesWebParametersAndRejectsIncompleteIdentity(self):
		policy = {
			'id': 7,
			'name': 'Fixture',
			'target': 'branch',
			'enforcement': 'enabled',
			'source': {'type': 'Organization', 'name': github.ORG},
			'missingConditionTargets': [],
			'conditions': [
				{'target': 'ref_name', 'parameters': {'include': ['~ALL'], 'exclude': []}}
			],
			'bypassActors': [
				{
					'name': 'Migrations',
					'actorId': None,
					'actorType': 'RepositoryMigration',
					'bypassMode': 0,
				}
			],
			'rules': [
				{
					'ruleType': 'pull_request',
					'parameters': {
						'authorized_dismissal_actors_only': True,
						'ignore_approvals_from_contributors': False,
						'allowed_merge_methods': ['merge', 'squash', 'rebase'],
					},
				}
			],
		}

		def makePage():
			return self.page(
				'<script data-target="react-app.embeddedData">'
				+ json.dumps({'payload': {'ruleset': policy, 'session': 'SESSION_ONLY'}})
				+ '</script>'
			)

		item = websettings.readWebRuleset(makePage())
		self.assertEqual(item['rules'][0]['parameters'], policy['rules'][0]['parameters'])
		self.assertNotIn('SESSION_ONLY', json.dumps(item))
		for mode in (True, 99):
			policy['bypassActors'][0]['bypassMode'] = mode
			with self.assertRaises(ValueError):
				websettings.readWebRuleset(makePage())
		policy['bypassActors'][0]['bypassMode'] = 0
		policy['source'] = {'type': 'Repository', 'name': f'{github.ORG}/fixture-repo'}
		policy['bypassActors'] = [
			{'name': 'PERSONAL_PROFILE', 'actorId': 123, 'actorType': 'User', 'bypassMode': 0}
		]
		item = websettings.readWebRuleset(makePage(), 'fixture-repo')
		self.assertEqual(item['bypass_actors'][0]['name'], 'User 123')
		self.assertNotIn('PERSONAL_PROFILE', json.dumps(item))
		policy['rules'][0]['parameters']['dismissal_restriction'] = {
			'enabled': True,
			'allowed_actors': ['PRIVATE_ACTOR_STRING'],
		}
		item = websettings.readWebRuleset(makePage(), 'fixture-repo')
		parameters = item['rules'][0]['parameters']
		self.assertNotIn('PRIVATE_ACTOR_STRING', json.dumps(item))
		self.assertNotIn('dismissal_restriction', parameters)
		self.assertIn(
			'PRIVATE_ACTOR_STRING',
			localdata.capturedValue(parameters['dismissal_restriction_source']),
		)
		config = copy.deepcopy(self.config)
		config['organization']['observed'] = {'web_rulesets': [item]}
		self.assertIn(parameters['dismissal_restriction_source'], localdata.valueReferences(config))
		policy['source'] = {
			'type': 'Repository',
			'name': 'fixture-repo',
			'url': f'http://github.com/{github.ORG}/fixture-repo/settings/rules',
		}
		self.assertEqual(websettings.readWebRuleset(makePage(), 'fixture-repo'), item)
		policy['source']['url'] = 'https://github.com/other/fixture-repo/settings/rules'
		with self.assertRaises(ValueError):
			websettings.readWebRuleset(makePage(), 'fixture-repo')
		with self.assertRaises(ValueError):
			websettings.readWebRuleset(makePage(), 'other-repo')
		policy['source'] = {'type': 'Organization', 'name': github.ORG}
		policy['conditions'] *= 2
		with self.assertRaises(ValueError):
			websettings.readWebRuleset(makePage())


if __name__ == '__main__':
	unittest.main()
