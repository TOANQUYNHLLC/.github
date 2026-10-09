"""Kiểm tra khôi phục mẫu secret scanning và phiên bản chính sách khi ghi."""

import contextlib
import copy
import io
import json
import os
import tempfile
import unittest
from unittest import mock

try:
	from testsupport import ROOT
except ModuleNotFoundError:
	from scripts.testsupport import ROOT

from orgsetup import catalog, configuration, github, localdata, patterns

BASE = 'orgs/TOANQUYNHLLC'


def apiPattern(**changes):
	return dict(
		{
			'id': 17,
			'name': 'Internal Key',
			'slug': 'internal-key',
			'pattern': 'PRIVATE_REGEX',
			'state': 'unpublished',
			'push_protection_enabled': False,
			'custom_pattern_version': 'fresh-version',
			'created_at': 'METADATA',
		},
		**changes,
	)


def policyData(**changes):
	return dict(
		{
			'pattern_config_version': 'fresh-policy',
			'provider_pattern_overrides': [
				{
					'token_type': 'GITHUB_TOKEN',
					'slug': 'github-token',
					'setting': 'not-set',
					'enterprise_setting': None,
					'alert_total': 100,
				}
			],
			'custom_pattern_overrides': [
				{
					'token_type': 'cp_19',
					'custom_pattern_version': 'new-custom-version',
					'slug': 'internal-key',
					'setting': 'disabled',
					'alert_total': 10,
				}
			],
		},
		**changes,
	)


class PatternSettingsTest(unittest.TestCase):
	def setUp(self):
		self.temporary = tempfile.TemporaryDirectory()
		self.addCleanup(self.temporary.cleanup)
		patcher = mock.patch.dict(os.environ, ORGSETUP_PRIVATE_DIR=self.temporary.name)
		patcher.start()
		self.addCleanup(patcher.stop)
		localdata.resetCapture()
		self.addCleanup(localdata.resetCapture)

	def saveDefinition(self, entry, value=None):
		path = localdata.dataPath()
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(
			json.dumps(
				{
					entry['definition_source']: json.dumps(
						value or patterns.definition({'pattern': 'PRIVATE_REGEX'})
					)
				}
			),
			encoding='utf-8',
		)
		path.chmod(0o600)

	def testCapturePrivateRegexWithoutApiMetadataAndSaveOutsideRepository(self):
		with mock.patch.object(github, 'ghList', return_value=[apiPattern()]):
			items, ids = patterns.readDetails(BASE, 'custom_patterns')
		self.assertEqual(ids['Internal Key'], (17, 'fresh-version'))
		self.assertNotIn('PRIVATE_REGEX', json.dumps(items))
		self.assertNotIn('created_at', json.dumps(items))
		self.assertNotIn('custom_pattern_version', json.dumps(items))
		config = {'organization': {'collections': {'custom_patterns': items}}, 'repositories': {}}
		localdata.saveCapturedValues(config)
		self.assertFalse(localdata.dataPath().is_relative_to(ROOT))
		self.assertEqual(localdata.dataPath().stat().st_mode & 0o777, 0o600)
		self.assertEqual(
			patterns.privateDefinition(items[0]['definition_source'])['pattern'], 'PRIVATE_REGEX'
		)

	def testCreateUnpublishedAndUpdateWithFreshVersionNeverExposeRegexInPlan(self):
		with mock.patch.object(github, 'ghList', return_value=[apiPattern()]):
			items, _ = patterns.readDetails(BASE, 'custom_patterns')
		self.saveDefinition(items[0], patterns.definition({'pattern': 'NEW_PRIVATE_REGEX'}))
		plan = []
		with mock.patch.object(github, 'ghList', return_value=[]):
			patterns.collectionChanges(plan, BASE, 'custom_patterns', [], items)
		self.assertEqual(plan[0][1], 'POST')
		self.assertNotIn('NEW_PRIVATE_REGEX', json.dumps(plan))
		body = patterns.resolvePlanBody(plan[0][0], plan[0][2])
		self.assertEqual(body['patterns'][0]['pattern'], 'NEW_PRIVATE_REGEX')
		self.assertEqual(body['patterns'][0]['name'], 'Internal Key')
		localdata.resetCapture()
		with mock.patch.object(
			github, 'ghList', return_value=[apiPattern(id=91, custom_pattern_version='NEW_ROW')]
		):
			current, _ = patterns.readDetails(BASE, 'custom_patterns')
			plan = []
			patterns.collectionChanges(plan, BASE, 'custom_patterns', current, items)
		self.assertTrue(plan[0][0].endswith('/91'))
		self.assertEqual(
			patterns.resolvePlanBody(plan[0][0], plan[0][2])['custom_pattern_version'], 'NEW_ROW'
		)
		self.assertTrue(localdata.hasReferences(plan[0][2]))

	def testPublishedMissingPatternBlocksBeforeAnyWrite(self):
		with mock.patch.object(github, 'ghList', return_value=[apiPattern(state='published')]):
			items, _ = patterns.readDetails(BASE, 'custom_patterns')
		self.saveDefinition(items[0])
		with (
			mock.patch.object(github, 'ghList', return_value=[]),
			self.assertRaisesRegex(ValueError, 'xuất bản'),
		):
			patterns.collectionChanges([], BASE, 'custom_patterns', [], items)

	def testReadPolicyFiltersMetricsAndEphemeralIdsThenResolveFreshVersions(self):
		with mock.patch.object(github, 'ghJson', return_value=policyData()):
			current, _ = patterns.readDetails(BASE, 'pattern_settings')
			wanted = copy.deepcopy(current)
			for item in wanted:
				item['setting'] = 'enabled'
			plan = []
			patterns.collectionChanges(plan, BASE, 'pattern_settings', current, wanted)
		self.assertNotIn('alert_total', json.dumps(current))
		self.assertNotIn('cp_19', json.dumps(current))
		self.assertNotIn('fresh-policy', json.dumps(plan))
		fresh = policyData(pattern_config_version='LATEST_POLICY')
		fresh['custom_pattern_overrides'][0].update(
			token_type='cp_88', custom_pattern_version='LATEST_CUSTOM'
		)
		with mock.patch.object(github, 'ghJson', return_value=fresh):
			body = patterns.resolvePlanBody(plan[0][0], plan[0][2])
		self.assertEqual(body['pattern_config_version'], 'LATEST_POLICY')
		self.assertEqual(body['custom_pattern_settings'][0]['token_type'], 'cp_88')
		self.assertEqual(
			body['custom_pattern_settings'][0]['custom_pattern_version'], 'LATEST_CUSTOM'
		)

	def testConcurrentPolicyAndInheritedEnterpriseChangeCannotOverwrite(self):
		with mock.patch.object(github, 'ghJson', return_value=policyData()):
			current, _ = patterns.readDetails(BASE, 'pattern_settings')
			wanted = copy.deepcopy(current)
			wanted[0]['setting'] = 'enabled'
			plan = []
			patterns.collectionChanges(plan, BASE, 'pattern_settings', current, wanted)
			wanted[0]['enterprise_setting'] = 'disabled'
			with self.assertRaisesRegex(ValueError, 'enterprise'):
				patterns.collectionChanges([], BASE, 'pattern_settings', current, wanted)
		changed = policyData()
		changed['provider_pattern_overrides'][0]['setting'] = 'disabled'
		with (
			mock.patch.object(github, 'ghJson', return_value=changed),
			self.assertRaisesRegex(ValueError, 'thay đổi'),
		):
			patterns.resolvePlanBody(plan[0][0], plan[0][2])

	def testUnsupportedCustomNotSetAndIncompleteResponseBlock(self):
		with mock.patch.object(github, 'ghJson', return_value=policyData()):
			current, _ = patterns.readDetails(BASE, 'pattern_settings')
			wanted = copy.deepcopy(current)
			wanted[1]['setting'] = 'not-set'
			with self.assertRaisesRegex(ValueError, 'not-set'):
				patterns.collectionChanges([], BASE, 'pattern_settings', current, wanted)
		for response in (
			'{}',
			'{"created_patterns": []}',
			'{"created_patterns": [{"name":"Other","id":17}]}',
		):
			with self.subTest(response=response), self.assertRaises(ValueError):
				patterns.validateResponse(
					'unused', 'POST', response, {'custom_pattern': 'Internal Key'}
				)
		patterns.validateResponse(
			'unused',
			'POST',
			json.dumps({'created_patterns': [apiPattern()]}),
			{'custom_pattern': 'Internal Key'},
		)

	def testApiUnavailableCannotBecomeEmptyAndOtherScopeReferencesRejected(self):
		with (
			mock.patch.object(github, 'ghList', side_effect=RuntimeError('HTTP 404 PRIVATE')),
			mock.patch.object(github, 'ghJson', side_effect=RuntimeError('HTTP 404 PRIVATE')),
		):
			groups, observed, unavailable = catalog.readCollections(
				BASE, ['custom_patterns', 'pattern_settings']
			)
		self.assertEqual(groups, {})
		self.assertEqual(observed, {})
		self.assertEqual(len(unavailable), 2)
		self.assertNotIn('PRIVATE', json.dumps(unavailable))
		with mock.patch.object(github, 'ghList', return_value=[apiPattern()]):
			items, _ = patterns.readDetails(BASE, 'custom_patterns')
		with self.assertRaises(ValueError):
			catalog.validateReferenceScope('repos/TOANQUYNHLLC/.github', 'custom_patterns', items)
		config = copy.deepcopy(configuration.readConfig(ROOT))
		config['organization']['collections']['custom_patterns'] = items
		configuration.validateConfig(config)
		config['organization']['collections']['custom_patterns'][0]['definition_source'] = {
			'$captured_body': 'bad'
		}
		with self.assertRaises(ValueError):
			configuration.validateConfig(config)

	def testDuplicateNamesIdsAndMalformedDefinitionsCannotCapturePartialGroup(self):
		for items in ([apiPattern(), apiPattern()], [apiPattern(), apiPattern(name='Other')]):
			with (
				mock.patch.object(github, 'ghList', return_value=items),
				self.assertRaises(ValueError),
			):
				patterns.readDetails(BASE, 'custom_patterns')
		with self.assertRaises(ValueError):
			patterns.definition({'pattern': 'valid', 'secret': 'PRIVATE'})

	def testIncompleteWriteStopsFollowingResourcesWithoutLeakingRegex(self):
		with mock.patch.object(github, 'ghList', return_value=[apiPattern()]):
			items, _ = patterns.readDetails(BASE, 'custom_patterns')
		self.saveDefinition(items[0])
		wanted = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'collections': {
				'custom_patterns': items,
				'labels': [{'name': 'after', 'color': '000000'}],
			},
		}
		current = dict(wanted, collections={'custom_patterns': [], 'labels': []})
		config = copy.deepcopy(configuration.readConfig(ROOT))
		config['unavailable'] = {}
		output = io.StringIO()
		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(
				configuration, 'configuredScopes', return_value=[('.github', wanted, (current, {}))]
			),
			mock.patch.object(github, 'ghList', return_value=[]),
			mock.patch.object(catalog, 'readDetails', return_value=([], {})),
			mock.patch.object(github, 'gh', return_value='{}') as write,
			contextlib.redirect_stdout(output),
			self.assertRaises(RuntimeError) as caught,
		):
			configuration.syncConfiguredSettings(True)
		write.assert_called_once()
		self.assertNotIn('PRIVATE_REGEX', output.getvalue() + str(caught.exception))

	def testCustomPatternRoundtripAndSecondApplyDoesNotWrite(self):
		with mock.patch.object(github, 'ghList', return_value=[apiPattern()]):
			items, _ = patterns.readDetails(BASE, 'custom_patterns')
		self.saveDefinition(items[0])
		wanted = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'collections': {'custom_patterns': items},
		}
		live = []
		config = copy.deepcopy(configuration.readConfig(ROOT))
		config['unavailable'] = {}

		def readScopes(source):
			for item in live:
				localdata.captureValue(
					BASE + '/secret-scanning/custom-patterns/definition',
					localdata.privateValue(item['definition_source']),
				)
			return [
				(
					None,
					wanted,
					(dict(wanted, collections={'custom_patterns': copy.deepcopy(live)}), {}),
				)
			]

		def write(*args, stdin):
			body = json.loads(stdin)
			self.assertEqual(body['patterns'][0]['pattern'], 'PRIVATE_REGEX')
			live.extend(copy.deepcopy(items))
			return json.dumps({'created_patterns': [apiPattern()]})

		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(configuration, 'configuredScopes', side_effect=readScopes),
			mock.patch.object(
				patterns,
				'readDetails',
				side_effect=lambda base, key: (
					copy.deepcopy(live),
					{'Internal Key': (91, 'NEW_ROW')},
				),
			),
			mock.patch.object(github, 'gh', side_effect=write) as mutation,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
		mutation.assert_called_once()


if __name__ == '__main__':
	unittest.main()
