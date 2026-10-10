"""Kiểm tra khai báo chưa biết, mục tiêu local và bản khôi phục thủ công ngoài Git."""

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
	from testsupport import ROOT, loadScript
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript

from orgsetup import catalog, configuration, github, inventory, localdata


def minimalConfig():
	return {
		'organization_name': github.ORG,
		'repository_defaults': {},
		'organization': {'settings': {}, 'web_settings': {}, 'endpoints': {}},
		'repositories': {},
		'unavailable': {},
	}


class SettingsInventoryTest(unittest.TestCase):
	def testEveryBlockedContractHasAnExplicitUnknownSlot(self):
		config = configuration.readConfig(ROOT)
		paths = set()
		for base, scope in inventory.scopes(config):
			for section, items in scope.get('pending_settings', {}).items():
				for key in items:
					suffix = (
						inventory.catalog.GROUP_PATHS[key]
						if section == 'collections'
						else f'settings/{key}'
						if section == 'settings'
						else key
					)
					paths.add(f'{base}/{suffix}')
		self.assertEqual(paths, set(config['unavailable']))

	def testConfiguredTargetsUseTheExistingValidatorAndKeepSourceUnchanged(self):
		config = minimalConfig()
		config['organization']['pending_settings'] = {'collections': {'network_configurations': []}}
		before = copy.deepcopy(config)
		self.assertEqual(configuration.validateConfig(config), before)
		selected = configuration.selectSettingGroups(config, ['network_configurations'])
		self.assertEqual(selected['organization']['collections'], {'network_configurations': []})
		self.assertEqual(config, before)
		config['organization']['pending_settings']['collections']['network_configurations'] = [
			{'name': 'Invalid', 'raw_api_response': True}
		]
		with self.assertRaises(ValueError):
			configuration.validateConfig(config)

	def testNullDoesNotBecomeAnEmptyCollectionOrZeroLimit(self):
		scope = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'pending_settings': {
				'collections': {'webhooks': None},
				'endpoints': {'actions/cache/storage-limit': None},
			},
		}
		activated = inventory.configuredScope(scope)
		self.assertNotIn('collections', activated)
		self.assertEqual(activated['endpoints'], {})
		self.assertEqual(len(inventory.scopeProblems(scope, 'repos/TOANQUYNHLLC/app')), 2)

	def testMalformedAndConflictingTargetsAreRejected(self):
		for pending in (
			{'settings': {'billing_email': None}},
			{'endpoints': {'unknown-api': None}},
			{'collections': {'unknown_resource': None}},
			{'collections': []},
		):
			with self.subTest(pending=pending):
				config = minimalConfig()
				config['organization']['pending_settings'] = pending
				with self.assertRaises(ValueError):
					configuration.validateConfig(config)
		config = minimalConfig()
		config['organization']['collections'] = {'webhooks': []}
		config['organization']['pending_settings'] = {'collections': {'webhooks': [{}]}}
		with self.assertRaisesRegex(ValueError, 'trùng mục tiêu'):
			configuration.validateConfig(config)

	def testCompleteImportKeepsExplicitTargetAndManualBackupAfterApiUnlock(self):
		config = minimalConfig()
		target = [
			{
				'name': 'Compute',
				'compute_service': 'actions',
				'network_settings_ids': ['CloudSetting'],
			}
		]
		config['organization']['pending_settings'] = {
			'collections': {'network_configurations': target}
		}
		config['organization']['manual_settings'] = {
			'billing': {'status': 'pending', 'configuration_source': 'manual/billing'}
		}
		config['unavailable'] = {'orgs/TOANQUYNHLLC/settings/network-configurations': 'HTTP 404'}
		captured = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'collections': {'network_configurations': []},
		}
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			(root / configuration.CONFIG_NAME).write_text(configuration.jsonText(config))
			with (
				mock.patch.object(github, 'ROOT', root),
				mock.patch.object(configuration, 'captureScope', return_value=(captured, {})),
				mock.patch.object(localdata, 'saveCapturedValues') as savePrivate,
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(configuration.importSettings(complete=True), 0)
				result = configuration.readConfig(root)
				write.assert_not_called()
				savePrivate.assert_called_once()
		self.assertEqual(result['organization']['collections']['network_configurations'], target)
		self.assertNotIn('pending_settings', result['organization'])
		self.assertEqual(
			result['organization']['manual_settings']['billing'],
			config['organization']['manual_settings']['billing'],
		)
		self.assertEqual(result['unavailable'], {})

	def testImportNeverCreatesKnownValuesForBlockedSettings(self):
		config = minimalConfig()
		base = 'orgs/TOANQUYNHLLC'
		problem = {base + '/hooks': 'HTTP 404'}
		result = inventory.refreshScope(
			config['organization'],
			config['organization'],
			base,
			problem,
			configuration.ORG_ENDPOINTS,
		)
		self.assertEqual(result['pending_settings'], {'collections': {'webhooks': None}})
		self.assertNotIn('collections', result)
		self.assertEqual(set(result['manual_settings']), set(inventory.MANUAL_GROUPS))
		self.assertTrue(
			all(item['status'] == 'unverified' for item in result['manual_settings'].values())
		)

	def testManualConfigCannotStoreRawValuesOrClaimVerificationWithoutBackup(self):
		for item in (
			{'status': 'verified', 'configuration_source': None},
			{'status': 'pending', 'configuration_source': 'manual/billing', 'token': 'private'},
			{'status': 'invalid', 'configuration_source': None},
			{'status': 'pending', 'configuration_source': '../private value'},
		):
			with self.subTest(item=item):
				config = minimalConfig()
				config['organization']['manual_settings'] = {'billing': item}
				with self.assertRaises(ValueError):
					configuration.validateConfig(config)

	def testMissingPrivateBackupAndUnverifiedManualStateRemainIncomplete(self):
		config = minimalConfig()
		config['organization']['manual_settings'] = {
			'billing': {'status': 'verified', 'configuration_source': 'manual/billing'},
			'authentication': {'status': 'unverified', 'configuration_source': None},
		}
		with mock.patch.object(localdata, 'privateValue', side_effect=ValueError('PRIVATE_VALUE')):
			problems = inventory.configProblems(config)
		self.assertEqual(len(problems), 2)
		self.assertNotIn('PRIVATE_VALUE', str(problems))
		self.assertEqual(localdata.valueReferences(config), {'manual/billing'})
		config['organization']['manual_settings']['authentication']['status'] = 'not_applicable'
		with mock.patch.object(localdata, 'privateValue', return_value='PRIVATE_CONFIGURATION'):
			output = io.StringIO()
			with contextlib.redirect_stdout(output):
				self.assertEqual(inventory.showInventory(config), 0)
			self.assertNotIn('PRIVATE_CONFIGURATION', output.getvalue())

	def testInventoryWorksOfflineAndRejectsApplyBeforeAuthentication(self):
		module = loadScript('org-setup')
		config = minimalConfig()
		with (
			mock.patch.object(module.sys, 'argv', ['org-setup.py', 'settings-inventory']),
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(module, 'signedIn') as login,
			mock.patch.object(github, 'gh') as request,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(module.main(), 0)
			login.assert_not_called()
			request.assert_not_called()
		with (
			mock.patch.object(
				module.sys, 'argv', ['org-setup.py', 'settings-inventory', '--apply']
			),
			mock.patch.object(module, 'signedIn') as login,
			contextlib.redirect_stderr(io.StringIO()),
			self.assertRaises(SystemExit),
		):
			module.main()
			login.assert_not_called()

	def testUnavailableSourceBlocksWritesEvenWithExplicitPendingTarget(self):
		config = minimalConfig()
		config['organization']['pending_settings'] = {'collections': {'webhooks': []}}
		config['unavailable'] = {'orgs/TOANQUYNHLLC/hooks': 'HTTP 404'}
		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(github, 'gh') as write,
			self.assertRaisesRegex(ValueError, 'chưa nhập'),
		):
			configuration.syncConfiguredSettings(True)
		write.assert_not_called()

	def testPendingCollectionIsReadBeforePlanningEvenWithoutActiveCollection(self):
		config = minimalConfig()
		config['organization']['pending_settings'] = {'collections': {'webhooks': []}}
		with (
			mock.patch.object(
				configuration, 'captureScope', return_value=({'collections': {'webhooks': []}}, {})
			) as read,
			mock.patch.object(configuration, 'readScope') as coreRead,
		):
			list(configuration.configuredScopes(config))
		read.assert_called_once_with(None, ['webhooks'])
		coreRead.assert_not_called()

	def testSelectedPendingEndpointAppliesAndSecondApplyIsNoop(self):
		config = minimalConfig()
		config['repositories']['app'] = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'pending_settings': {
				'endpoints': {'actions/cache/storage-limit': {'max_cache_size_gb': 20}}
			},
		}
		before = copy.deepcopy(config)
		live = {'max_cache_size_gb': 10}

		def readScope(repo=None):
			return {
				'settings': {},
				'web_settings': {},
				'endpoints': {'actions/cache/storage-limit': dict(live)} if repo else {},
			}, {}

		def write(*args, stdin):
			self.assertEqual(
				args[:4], ('api', '-X', 'PUT', 'repos/TOANQUYNHLLC/app/actions/cache/storage-limit')
			)
			live.update(json.loads(stdin))
			return '{}'

		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(configuration, 'readScope', side_effect=readScope),
			mock.patch.object(github, 'gh', side_effect=write) as request,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True, only=['endpoints']), 0)
			self.assertEqual(configuration.syncConfiguredSettings(True, only=['endpoints']), 0)
			request.assert_called_once()
		self.assertEqual(live, {'max_cache_size_gb': 20})
		self.assertEqual(config, before)

	def testUnverifiedManualStateDoesNotReportFullRestoreSuccess(self):
		config = minimalConfig()
		config['organization']['manual_settings'] = {
			'billing': {'status': 'unverified', 'configuration_source': None}
		}
		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(
				configuration, 'readScope', return_value=(config['organization'], {})
			),
			mock.patch.object(github, 'gh') as request,
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 1)
			request.assert_not_called()
		self.assertIn('manual_settings/billing', output.getvalue())

	def testMissingManualValuesDoNotCreateAnEmptyPrivateBackup(self):
		config = minimalConfig()
		config['organization']['manual_settings'] = {
			'billing': {'status': 'pending', 'configuration_source': 'manual/billing'}
		}
		with tempfile.TemporaryDirectory() as directory:
			path = Path(directory) / 'values.json'
			with (
				mock.patch.object(localdata, 'dataPath', return_value=path),
				mock.patch.object(localdata, 'readValues', return_value={}),
				mock.patch.object(localdata, 'CAPTURED_VALUES', {}),
			):
				localdata.saveCapturedValues(config)
			self.assertFalse(path.exists())

	def testOldDefaultSecurityFlagsRestoreFromLocalAndSecondApplyIsNoop(self):
		old = minimalConfig()
		old['organization']['web_settings'] = dict.fromkeys(
			configuration.LEGACY_SECURITY_DEFAULTS, True
		)
		before = copy.deepcopy(old)
		config = configuration.validateConfig(old)
		self.assertEqual(old, before)
		self.assertEqual(config['organization']['web_settings'], {})
		live = {
			'settings': dict.fromkeys(configuration.LEGACY_SECURITY_DEFAULTS, False),
			'web_settings': {},
			'endpoints': {},
		}

		def write(*args, stdin):
			self.assertEqual(args[:4], ('api', '-X', 'PATCH', 'orgs/TOANQUYNHLLC'))
			live['settings'].update(json.loads(stdin))
			return '{}'

		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(
				configuration, 'readScope', side_effect=lambda repo=None: (copy.deepcopy(live), {})
			),
			mock.patch.object(github, 'gh', side_effect=write) as request,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			request.assert_called_once()
		self.assertEqual(live['settings'], before['organization']['web_settings'])

	def testConflictingOldAndNewDefaultFlagsCannotChooseASilentWinner(self):
		config = minimalConfig()
		key = configuration.LEGACY_SECURITY_DEFAULTS[0]
		config['organization']['settings'][key] = False
		config['organization']['web_settings'][key] = True
		with self.assertRaisesRegex(ValueError, 'hai mục tiêu'):
			configuration.validateConfig(config)
		config['organization']['web_settings'][key] = False
		self.assertIs(configuration.validateConfig(config)['organization']['settings'][key], False)

	def testMissingDeprecatedFlagProducesGapAndNeverGuessesFalse(self):
		scope = configuration.readConfig(ROOT)['organization']
		data = dict(scope['settings'], **scope['web_settings'], login=github.ORG)
		key = configuration.LEGACY_SECURITY_DEFAULTS[0]
		data.pop(key)
		with (
			mock.patch.object(github, 'ghJson', return_value=data),
			mock.patch.object(configuration, 'endpointDefinitions', return_value={}),
			mock.patch.object(configuration.resources, 'readRunnerGroups', return_value=[]),
			mock.patch.object(configuration.resources, 'installedApps', return_value=[]),
			mock.patch.object(configuration, 'readSecurityDefaults', return_value=[]),
		):
			captured, gaps = configuration.readScope()
		self.assertNotIn(key, captured['settings'])
		path = f'orgs/{github.ORG}/settings/{key}'
		self.assertIn(path, gaps)
		result = inventory.refreshScope(
			{},
			captured,
			f'orgs/{github.ORG}',
			gaps,
			configuration.ORG_ENDPOINTS,
			configuration.ORG_FIELDS,
		)
		self.assertIsNone(result['pending_settings']['settings'][key])
		self.assertTrue(configuration.groupUnavailable(path, {'settings'}))

	def testCompleteImportDoesNotAttachLiveSelectedRepositoriesToLocalNone(self):
		previous = {
			'settings': {},
			'web_settings': {},
			'endpoints': {'actions/permissions': {'enabled_repositories': 'none'}},
		}
		captured = {
			'settings': {},
			'web_settings': {},
			'endpoints': {
				'actions/permissions': {
					'enabled_repositories': 'selected',
					'allowed_actions': 'all',
				},
				'actions/permissions/repositories': {'selected_repositories': ['TOANQUYNHLLC/app']},
			},
		}
		result = configuration.completeScope(previous, captured)
		self.assertEqual(result['endpoints']['actions/permissions']['enabled_repositories'], 'none')
		self.assertNotIn('actions/permissions/repositories', result['endpoints'])
		config = minimalConfig()
		config['organization'] = result
		configuration.validateConfig(config)

	def testLocalSelectedListRemainsUnknownWhenLivePolicyHidesIt(self):
		config = minimalConfig()
		config['organization']['endpoints']['actions/permissions'] = {
			'enabled_repositories': 'selected',
			'allowed_actions': 'all',
		}
		suffix = 'actions/permissions/repositories'
		path = f'orgs/{github.ORG}/{suffix}'
		config['unavailable'][path] = 'HTTP 403'
		live = {
			'settings': {},
			'web_settings': {},
			'endpoints': {
				'actions/permissions': {'enabled_repositories': 'all', 'allowed_actions': 'all'}
			},
		}
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			(root / configuration.CONFIG_NAME).write_text(configuration.jsonText(config))
			with (
				mock.patch.object(github, 'ROOT', root),
				mock.patch.object(configuration, 'captureScope', return_value=(live, {})),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(configuration.importSettings(complete=True), 1)
				result = configuration.readConfig(root)
				write.assert_not_called()
		self.assertIn(path, result['unavailable'])
		self.assertIsNone(result['organization']['pending_settings']['endpoints'][suffix])
		self.assertNotIn(suffix, result['organization']['endpoints'])

	def testPrivateSecurityGapAlsoBlocksSelectedSecurityOptions(self):
		path = 'repos/TOANQUYNHLLC/app (security_and_analysis)'
		self.assertTrue(configuration.groupUnavailable(path, {'security'}))
		self.assertTrue(configuration.groupUnavailable(path, {'security_options'}))
		self.assertFalse(configuration.groupUnavailable(path, {'labels'}))

	def testRepositoryReviewerOptionsRoundtripIsOnePatchAndThenNoop(self):
		config = minimalConfig()
		key = 'secret_scanning_delegated_bypass_options'
		feature = 'secret_scanning_delegated_bypass'
		config['repositories']['app'] = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'security': {feature: 'enabled'},
			'security_options': {
				key: {'reviewers': [{'reviewer_id': 7, 'reviewer_type': 'TEAM', 'mode': 'EXEMPT'}]}
			},
		}
		configuration.validateConfig(config)
		live = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'security': {feature: 'disabled'},
		}

		def read(repo=None):
			return (copy.deepcopy(live) if repo else config['organization']), {}

		def write(*args, stdin):
			body = json.loads(stdin)['security_and_analysis']
			self.assertEqual(set(body), {feature, key})
			live['security'][feature] = body[feature]['status']
			live['security_options'] = {key: body[key]}
			return '{}'

		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(configuration, 'readScope', side_effect=read),
			mock.patch.object(github, 'gh', side_effect=write) as request,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			request.assert_called_once()

	def testDisabledReviewerFeatureAndBadOptionsStopBeforeWrites(self):
		key = 'secret_scanning_delegated_bypass_options'
		current = {'security': {'secret_scanning_delegated_bypass': 'disabled'}}
		wanted = {'security_options': {key: {'reviewers': []}}}
		plan = []
		with self.assertRaisesRegex(ValueError, 'enabled'):
			configuration.securityChanges(plan, 'repos/TOANQUYNHLLC/app', current, wanted)
		self.assertEqual(plan, [])
		for reviewers in (
			[{'reviewer_id': True, 'reviewer_type': 'TEAM'}],
			[{'reviewer_id': 1, 'reviewer_type': 'USER'}],
			[{'reviewer_id': 1, 'reviewer_type': 'TEAM'}] * 2,
			[{'reviewer_id': 1, 'reviewer_type': 'ROLE', 'security_configuration_id': 99}],
		):
			with self.subTest(reviewers=reviewers), self.assertRaises(ValueError):
				catalog.securityOptions({'reviewers': reviewers})

	def testSecurityConfigurationReviewerMetadataIsFilteredAndModeIsStable(self):
		item = {
			'name': 'Default',
			'target_type': 'organization',
			'id': 90,
			'secret_scanning_delegated_bypass_options': {
				'reviewers': [
					{'reviewer_id': 7, 'reviewer_type': 'TEAM', 'security_configuration_id': 90}
				]
			},
		}
		with mock.patch.object(github, 'ghList', return_value=[item]):
			items, identities = catalog.readDetails('orgs/TOANQUYNHLLC', 'security_definitions')
		self.assertEqual(identities, {'Default': 90})
		self.assertNotIn('security_configuration_id', json.dumps(items))
		self.assertTrue(
			catalog.itemMatches(
				'security_definitions',
				items[0],
				{
					'name': 'Default',
					'secret_scanning_delegated_bypass_options': {
						'reviewers': [{'reviewer_id': 7, 'reviewer_type': 'TEAM'}]
					},
				},
			)
		)

	def testPrivateBillingEmailRestoresWithoutAppearingInSourceOrPlan(self):
		config = minimalConfig()
		alias = 'orgs/TOANQUYNHLLC/settings/billing_email#' + 'a' * 32
		config['organization']['private_settings'] = {'billing_email': {'value_source': alias}}
		configuration.validateConfig(config)
		live = ['OLD_PRIVATE_VALUE']
		private = {alias: 'TARGET_PRIVATE_VALUE'}

		def read(repo=None):
			captured = localdata.captureValue('orgs/TOANQUYNHLLC/settings/billing_email', live[0])
			return {
				'settings': {},
				'web_settings': {},
				'endpoints': {},
				'private_settings': {'billing_email': {'value_source': captured}},
			}, {}

		def write(*args, stdin):
			self.assertEqual(args[:4], ('api', '-X', 'PATCH', 'orgs/TOANQUYNHLLC'))
			live[0] = json.loads(stdin)['billing_email']
			return '{}'

		output = io.StringIO()
		with (
			mock.patch.object(localdata, 'readValues', return_value=private),
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(configuration, 'readScope', side_effect=read),
			mock.patch.object(github, 'gh', side_effect=write) as request,
			contextlib.redirect_stdout(output),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			request.assert_called_once()
		self.assertEqual(live[0], private[alias])
		self.assertNotIn('PRIVATE_VALUE', output.getvalue())
		self.assertNotIn('PRIVATE_VALUE', json.dumps(config))
		self.assertIn(alias, localdata.valueReferences(config))

	def testPrivateBillingFailureRedactsApiError(self):
		config = minimalConfig()
		alias = 'orgs/TOANQUYNHLLC/settings/billing_email#' + 'b' * 32
		config['organization']['private_settings'] = {'billing_email': {'value_source': alias}}

		def read(repo=None):
			captured = localdata.captureValue(
				'orgs/TOANQUYNHLLC/settings/billing_email', 'OLD_PRIVATE_VALUE'
			)
			return {
				'settings': {},
				'web_settings': {},
				'endpoints': {},
				'private_settings': {'billing_email': {'value_source': captured}},
			}, {}

		with (
			mock.patch.object(
				localdata, 'readValues', return_value={alias: 'TARGET_PRIVATE_VALUE'}
			),
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(configuration, 'readScope', side_effect=read),
			mock.patch.object(github, 'gh', side_effect=RuntimeError('TARGET_PRIVATE_VALUE')),
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaises(RuntimeError) as failure,
		):
			configuration.syncConfiguredSettings(True)
		self.assertNotIn('PRIVATE_VALUE', str(failure.exception))
		self.assertIsNone(failure.exception.__cause__)

	def testPrivateSourceCannotStoreRawEmailOrWriteAnUnreadValue(self):
		config = minimalConfig()
		config['organization']['private_settings'] = {
			'billing_email': {'value': 'TARGET_PRIVATE_VALUE'}
		}
		with self.assertRaises(ValueError):
			configuration.validateConfig(config)
		config['organization']['private_settings'] = {
			'billing_email': {
				'value_source': 'orgs/TOANQUYNHLLC/settings/billing_email#' + 'c' * 32
			}
		}
		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(
				configuration, 'readScope', return_value=(minimalConfig()['organization'], {})
			),
			mock.patch.object(github, 'gh') as request,
			mock.patch.object(localdata, 'readValues', return_value={}),
			self.assertRaisesRegex(ValueError, 'API chưa trả'),
		):
			configuration.syncConfiguredSettings(True)
		request.assert_not_called()

	def testReviewerPatchMustBeConfirmedByReadback(self):
		config = minimalConfig()
		config['repositories']['app'] = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'security': {'secret_scanning_delegated_bypass': 'enabled'},
			'security_options': {'secret_scanning_delegated_bypass_options': {'reviewers': []}},
		}
		current = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'security': {'secret_scanning_delegated_bypass': 'enabled'},
		}
		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=lambda repo=None: (current if repo else config['organization'], {}),
			),
			mock.patch.object(github, 'gh', return_value='{}') as request,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 1)
			request.assert_called_once()


if __name__ == '__main__':
	unittest.main()
