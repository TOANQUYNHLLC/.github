"""Kiểm tra bản khôi phục tổng quát, nguồn thiếu trên gói Free và bổ sung sau nâng cấp."""

import contextlib
import copy
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
	from testsupport import ROOT, loadScript
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript

from orgsetup import catalog, configuration, github, localdata, rulesets, settings


def sourceConfig():
	config = copy.deepcopy(configuration.readConfig(ROOT))
	config['unavailable'] = {}
	for scope in [config['organization'], *config['repositories'].values()]:
		scope.pop('collections', None)
		scope.pop('observed', None)
		scope.pop('pending_settings', None)
		scope.pop('private_settings', None)
		# Fixture danh mục API không quản lý cấu hình thủ công; test_inventory kiểm tra phần đó.
		for item in scope.get('manual_settings', {}).values():
			item.update(status='not_applicable', configuration_source=None)
	return config


class CatalogTest(unittest.TestCase):
	def testCaseInsensitiveRepositoryKeepsOverridesAndRequiredChecks(self):
		with mock.patch.object(
			settings, 'REPOSITORY_OVERRIDES', {'.github': {'homepage': 'https://example.test'}}
		):
			self.assertEqual(
				settings.repositorySettings('.GITHUB'), settings.repositorySettings('.github')
			)
		self.assertEqual(rulesets.rulesetFor('.GITHUB'), rulesets.rulesetFor('.github'))

	def testGitHubCliTimeoutCannotRetryMutationOrExposeInput(self):
		with (
			mock.patch.object(
				github.subprocess,
				'run',
				side_effect=subprocess.TimeoutExpired('gh', github.CLI_TIMEOUT),
			) as run,
			self.assertRaises(RuntimeError) as caught,
		):
			github.gh('api', '-X', 'PATCH', 'orgs/TOANQUYNHLLC', stdin='PRIVATE_INPUT')
		run.assert_called_once()
		self.assertEqual(run.call_args.kwargs['timeout'], github.CLI_TIMEOUT)
		self.assertNotIn('PRIVATE_INPUT', str(caught.exception))

	def testCreateSecurityDefinitionThenDefaultsAndBindingAndFreshVerification(self):
		wanted = sourceConfig()
		wanted['organization']['collections'] = {
			'security_definitions': [{'name': 'Baseline / Team', 'code_security': 'enabled'}]
		}
		wanted['organization']['security_configurations'].append(
			{
				'name': 'Baseline / Team',
				'target_type': 'organization',
				'default_for_new_repos': 'all',
			}
		)
		wanted['repositories']['.github']['security_configuration'] = 'Baseline / Team'
		current = copy.deepcopy(wanted)
		current['organization']['collections']['security_definitions'] = []
		current['organization']['security_configurations'].pop()
		current['repositories']['.github']['security_configuration'] = None
		identities = [{'id': 1, 'name': 'GitHub recommended', 'target_type': 'global'}]

		def readCore(repo=None):
			scope = copy.deepcopy(
				current['organization'] if repo is None else current['repositories'][repo]
			)
			scope.pop('collections', None)
			return scope, {}

		def readGroups(base, keys=None):
			return copy.deepcopy(current['organization'].get('collections', {})), {}, {}

		def write(*args, stdin):
			path, body = args[3], json.loads(stdin)
			if path == 'orgs/TOANQUYNHLLC/code-security/configurations':
				definition = dict(body, enforcement='enforced')
				current['organization']['collections']['security_definitions'] = [definition]
				identities.append(dict(definition, id=77, target_type='organization'))
			elif path == 'orgs/TOANQUYNHLLC/code-security/configurations/77/defaults':
				current['organization']['security_configurations'].append(
					{
						'name': 'Baseline / Team',
						'target_type': 'organization',
						'default_for_new_repos': body['default_for_new_repos'],
					}
				)
			elif path == 'orgs/TOANQUYNHLLC/code-security/configurations/77/attach':
				self.assertEqual(body, {'selected_repository_ids': [946], 'scope': 'selected'})
				current['repositories']['.github']['security_configuration'] = 'Baseline / Team'
			else:
				self.fail(f'Thao tác ngoài kế hoạch: {path}')
			return '{}'

		with (
			mock.patch.object(configuration, 'readConfig', return_value=wanted),
			mock.patch.object(configuration, 'readScope', side_effect=readCore),
			mock.patch.object(catalog, 'readCollections', side_effect=readGroups),
			mock.patch.object(github, 'ghList', side_effect=lambda path: copy.deepcopy(identities)),
			mock.patch.object(
				github, 'ghJson', return_value={'full_name': 'TOANQUYNHLLC/.github', 'id': 946}
			),
			mock.patch.object(github, 'gh', side_effect=write) as mutation,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			self.assertEqual(mutation.call_count, 3)
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			self.assertEqual(mutation.call_count, 3)
		self.assertEqual(current['repositories'], wanted['repositories'])

	def testLabelsFilterMetadataAndCredentials(self):
		with mock.patch.object(
			github,
			'ghList',
			return_value=[
				{
					'id': 2,
					'name': 'Bug',
					'color': 'abcdef',
					'description': None,
					'node_id': 'opaque',
					'token': 'SECRET_VALUE',
				}
			],
		):
			items, ids = catalog.readDetails('repos/TOANQUYNHLLC/.github', 'labels')
		self.assertEqual(items, [{'name': 'Bug', 'color': 'abcdef', 'description': None}])
		self.assertEqual(ids, {})
		self.assertNotIn('SECRET_VALUE', json.dumps(items))

	def testRulesetsExportOnlyWritableFieldsAndExcludeParents(self):
		wanted = rulesets.rulesetsFor('.github')[0][1]
		with (
			mock.patch.object(
				rulesets, 'readRulesetIds', return_value={wanted['name']: 99}
			) as listing,
			mock.patch.object(
				github,
				'ghJson',
				return_value=dict(
					wanted,
					id=99,
					source='Repository',
					created_at='metadata',
					_links={'self': 'metadata'},
				),
			),
		):
			items, ids = catalog.readDetails('repos/TOANQUYNHLLC/.github', 'rulesets')
		self.assertEqual(items, [wanted])
		self.assertEqual(ids, {wanted['name']: 99})
		listing.assert_called_once_with(
			'repos/TOANQUYNHLLC/.github/rulesets?includes_parents=false'
		)

	def testRulesetsRejectIdentityChangeBeforeImport(self):
		wanted = rulesets.rulesetsFor('.github')[0][1]
		with (
			mock.patch.object(rulesets, 'readRulesetIds', return_value={wanted['name']: 99}),
			mock.patch.object(github, 'ghJson', return_value=dict(wanted, id=100)),
			self.assertRaises(ValueError),
		):
			catalog.readDetails('repos/TOANQUYNHLLC/.github', 'rulesets')

	def testFreePlanGraphqlSnapshotIsObservedAndCannotBecomeApplySource(self):
		wanted = rulesets.orgRulesets()[0][1]
		with (
			mock.patch.object(catalog, 'readDetails', side_effect=RuntimeError('HTTP 403')),
			mock.patch.object(
				rulesets, 'readOrgRulesetsGraphql', return_value={wanted['name']: wanted}
			),
		):
			collections, observed, unavailable = catalog.readCollections(
				'orgs/TOANQUYNHLLC', ['rulesets']
			)
		self.assertEqual(collections, {})
		self.assertEqual(observed, {'rulesets': [wanted]})
		self.assertIn('GraphQL chỉ đọc một phần', unavailable['orgs/TOANQUYNHLLC/rulesets'])

	def testFailedCollectionDoesNotBecomeEmptyOrHideOtherGroups(self):
		def read(base, key):
			if key == 'labels':
				raise ValueError('Truncated pages')
			return [], {}

		with mock.patch.object(catalog, 'readDetails', side_effect=read):
			collections, observed, unavailable = catalog.readCollections(
				'repos/TOANQUYNHLLC/app', ['labels', 'autolinks']
			)
		self.assertEqual(collections, {'autolinks': []})
		self.assertEqual(observed, {})
		self.assertIn('repos/TOANQUYNHLLC/app/labels', unavailable)

	def testDuplicateAndInvalidResourceDefinitionsFail(self):
		invalid = (
			('labels', [{'name': 'Bug', 'color': 'abcdef'}, {'name': 'bug', 'color': 'abcdef'}]),
			('labels', [{'name': 'Bug', 'color': 'nothex'}]),
			(
				'autolinks',
				[
					{
						'key_prefix': 'TASK-',
						'url_template': 'https://example.com',
						'is_alphanumeric': True,
					}
				],
			),
			('security_definitions', [{'name': 'Baseline', 'token': 'unsafe'}]),
			('security_definitions', [{'name': 'Baseline', 'code_security': True}]),
			(
				'security_definitions',
				[
					{
						'name': 'Baseline',
						'secret_scanning_delegated_bypass_options': {
							'reviewers': [{'reviewer_id': True, 'reviewer_type': 'TEAM'}]
						},
					}
				],
			),
			('property_schema', [{'property_name': 'env', 'value_type': 'unexpected'}]),
		)
		for key, items in invalid:
			with self.subTest(key=key, items=items), self.assertRaises((ValueError, TypeError)):
				catalog.validateGroup(key, items)

	def testSecurityDefinitionsSkipGlobalAndFilterMetadata(self):
		with mock.patch.object(
			github,
			'ghList',
			return_value=[
				{'id': 1, 'name': 'GitHub recommended', 'target_type': 'global'},
				{
					'id': 2,
					'name': 'Baseline',
					'target_type': 'organization',
					'code_security': 'enabled',
					'enforcement': 'enforced',
					'created_at': 'metadata',
				},
			],
		):
			items, ids = catalog.readDetails('orgs/TOANQUYNHLLC', 'security_definitions')
		self.assertEqual(
			items, [{'name': 'Baseline', 'code_security': 'enabled', 'enforcement': 'enforced'}]
		)
		self.assertEqual(ids, {'Baseline': 2})

	def testNewSecurityDefinitionAcceptsApiDefaultsDuringReadBack(self):
		self.assertTrue(
			catalog.itemMatches(
				'security_definitions',
				{'name': 'Baseline', 'code_security': 'enabled', 'enforcement': 'enforced'},
				{'name': 'Baseline', 'code_security': 'enabled'},
			)
		)

	def testPropertyAndLabelUpsertNeverDeleteUnmanagedEntries(self):
		label = {'name': 'Bug', 'color': 'abcdef', 'description': None}
		propertyValue = {'property_name': 'environment', 'value': 'production'}
		current = {'collections': {'labels': [], 'custom_properties': []}}
		wanted = {'collections': {'labels': [label], 'custom_properties': [propertyValue]}}
		plan = []
		with mock.patch.object(catalog, 'readDetails', return_value=([], {})):
			catalog.collectionChanges(plan, 'repos/TOANQUYNHLLC/app', current, wanted, {})
		self.assertEqual(
			[(path, method, body) for path, method, body, _ in plan],
			[
				('repos/TOANQUYNHLLC/app/labels', 'POST', label),
				(
					'repos/TOANQUYNHLLC/app/properties/values',
					'PATCH',
					{'properties': [propertyValue]},
				),
			],
		)

	def testChangedAutolinkReplacesOnlyVerifiedPrefix(self):
		current = {
			'collections': {
				'autolinks': [
					{
						'key_prefix': 'TASK-',
						'url_template': 'https://old.example/<num>',
						'is_alphanumeric': False,
					}
				]
			}
		}
		target = {
			'key_prefix': 'TASK-',
			'url_template': 'https://new.example/<num>',
			'is_alphanumeric': True,
		}
		plan = []
		with mock.patch.object(
			catalog, 'readDetails', return_value=(current['collections']['autolinks'], {'TASK-': 7})
		):
			catalog.collectionChanges(
				plan,
				'repos/TOANQUYNHLLC/app',
				current,
				{'collections': {'autolinks': [target]}},
				{},
			)
		self.assertEqual(
			[(path, method) for path, method, _, _ in plan],
			[
				('repos/TOANQUYNHLLC/app/autolinks/7', 'DELETE'),
				('repos/TOANQUYNHLLC/app/autolinks', 'POST'),
			],
		)

	def testChangedResourceDuringPlanBlocksMutation(self):
		label = {'name': 'Bug', 'color': 'abcdef'}
		plan = []
		with (
			mock.patch.object(
				catalog, 'readDetails', return_value=([dict(label, color='000000')], {})
			),
			self.assertRaises(ValueError),
		):
			catalog.collectionChanges(
				plan,
				'repos/TOANQUYNHLLC/app',
				{'collections': {'labels': [label]}},
				{'collections': {'labels': [dict(label, color='ffffff')]}},
				{},
			)
		self.assertEqual(plan, [])

	def testTeamParentsAndRepositoryRolesUseNamesAndOrderedCreation(self):
		parent = {
			'name': 'Engineering',
			'slug': 'engineering',
			'description': '',
			'privacy': 'closed',
			'notification_setting': 'notifications_enabled',
			'parent_team_slug': None,
			'repositories': {},
		}
		child = dict(
			parent,
			name='Developers',
			slug='developers',
			parent_team_slug='engineering',
			repositories={'TOANQUYNHLLC/app': 'maintain'},
		)
		plan = []
		catalog.teamChanges(plan, 'orgs/TOANQUYNHLLC', {}, [child, parent])
		self.assertEqual(plan[0][2]['name'], 'Engineering')
		self.assertNotIn('parent_team_slug', plan[0][2])
		self.assertEqual(plan[1][2]['parent_team_slug'], 'engineering')
		self.assertEqual(plan[2][0], 'orgs/TOANQUYNHLLC/teams/developers/repos/TOANQUYNHLLC/app')
		self.assertEqual(plan[2][2], {'permission': 'maintain'})
		parent['parent_team_slug'] = 'developers'
		with self.assertRaises(ValueError):
			catalog.validateGroup('teams', [parent, child])

	def testEnvironmentsCapturePoliciesAndExcludeUserProfiles(self):
		data = [
			{
				'name': 'Production / EU',
				'deployment_branch_policy': {
					'protected_branches': False,
					'custom_branch_policies': True,
				},
				'protection_rules': [
					{'type': 'wait_timer', 'wait_timer': 15},
					{
						'type': 'required_reviewers',
						'prevent_self_review': True,
						'reviewers': [
							{'type': 'Team', 'reviewer': {'id': 17, 'name': 'Ignored metadata'}}
						],
					},
				],
			}
		]
		with mock.patch.object(
			catalog.resources,
			'readCollection',
			side_effect=[data, [], [{'id': 1, 'name': 'main', 'type': 'branch'}]],
		) as read:
			items = catalog.readEnvironments('repos/TOANQUYNHLLC/app')
		self.assertEqual(items[0]['reviewers'], [{'type': 'Team', 'id': 17}])
		self.assertEqual(items[0]['wait_timer'], 15)
		self.assertEqual(items[0]['branch_policies'], [{'name': 'main', 'type': 'branch'}])
		self.assertNotIn('Ignored metadata', json.dumps(items))
		self.assertIn('Production%20%2F%20EU', read.call_args.args[0])

	def testPaidCompletionKeepsSavedSettingsAndFillsFullRulesets(self):
		old = sourceConfig()
		old['organization']['observed'] = {
			'rulesets': [rulesets.graphqlVisible(rulesets.orgRulesets()[0][1])]
		}
		old['unavailable'] = {'orgs/TOANQUYNHLLC/rulesets': 'HTTP 403'}
		live = copy.deepcopy(old)
		live['organization']['settings']['description'] = 'Giá trị web sau nâng cấp'
		live['repositories']['.github']['settings']['allow_rebase_merge'] = not old['repositories'][
			'.github'
		]['settings']['allow_rebase_merge']
		live['organization']['collections'] = {
			'rulesets': [item for _, item in rulesets.orgRulesets()]
		}
		live['organization'].pop('observed')
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			path = root / configuration.CONFIG_NAME
			path.write_text(configuration.jsonText(old))
			with (
				mock.patch.object(github, 'ROOT', root),
				mock.patch.object(
					configuration,
					'captureScope',
					side_effect=lambda repo: (
						live['organization'] if repo is None else live['repositories'][repo],
						{},
					),
				),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(configuration.importSettings(complete=True), 0)
				captured = configuration.readConfig()
			write.assert_not_called()
			self.assertEqual(captured['unavailable'], {})
			self.assertNotIn('observed', captured['organization'])
			self.assertEqual(
				captured['organization']['collections']['rulesets'],
				live['organization']['collections']['rulesets'],
			)
			self.assertEqual(captured['organization']['settings'], old['organization']['settings'])
			self.assertEqual(captured['repositories'], old['repositories'])

	def testIncompleteSelectedCaptureRemainsReadableAndBlocksApply(self):
		config = sourceConfig()
		config['organization']['endpoints']['actions/permissions/self-hosted-runners'] = {
			'enabled_repositories': 'selected'
		}
		config['unavailable'] = {
			'orgs/TOANQUYNHLLC/actions/permissions/self-hosted-runners/repositories': 'HTTP 403'
		}
		configuration.validateConfig(config)
		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(github, 'gh') as write,
			self.assertRaises(ValueError),
		):
			configuration.syncConfiguredSettings(True)
		write.assert_not_called()

	def testMissingDefinitionResolvesNewIdOnlyAfterCreate(self):
		current = {'collections': {'security_definitions': []}, 'security_configurations': []}
		wanted = {
			'collections': {
				'security_definitions': [{'name': 'Baseline / Team', 'code_security': 'enabled'}]
			},
			'security_configurations': [
				{
					'name': 'Baseline / Team',
					'target_type': 'organization',
					'default_for_new_repos': 'all',
				}
			],
		}
		plan, cache = [], {}
		with mock.patch.object(catalog, 'readDetails', return_value=([], {})):
			catalog.collectionChanges(plan, 'orgs/TOANQUYNHLLC', current, wanted, cache)
			configuration.securityBindingChanges(
				plan, 'orgs/TOANQUYNHLLC', None, current, wanted, cache
			)
		self.assertEqual(plan[0][1], 'POST')
		self.assertEqual(
			plan[1][0],
			'orgs/TOANQUYNHLLC/code-security/configurations/@Baseline%20%2F%20Team/defaults',
		)
		with mock.patch.object(
			catalog,
			'readDetails',
			return_value=(wanted['collections']['security_definitions'], {'Baseline / Team': 77}),
		):
			self.assertEqual(
				catalog.resolvePlanPath(plan[1][0]),
				'orgs/TOANQUYNHLLC/code-security/configurations/77/defaults',
			)

	def testAuditReportsUncapturedRepositoryAndCollections(self):
		config = sourceConfig()
		current = copy.deepcopy(config['organization'])
		current['collections'] = {'teams': []}
		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(github, 'listRepos', return_value=['.github', 'new-repo']),
			mock.patch.object(
				configuration,
				'captureScope',
				side_effect=lambda repo: (
					current if repo is None else config['repositories']['.github'],
					{},
				),
			),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			self.assertEqual(configuration.auditSettings(), 1)
		write.assert_not_called()
		self.assertIn('Danh sách repository', output.getvalue())
		self.assertIn('collections/teams', output.getvalue())

	def testCliCompleteIsImportOnlyAndAuditCannotApply(self):
		module = loadScript('org-setup')
		for arguments in (['settings-audit', '--apply'], ['local-settings', '--complete']):
			with (
				self.subTest(arguments=arguments),
				mock.patch('sys.argv', ['org-setup.py', *arguments]),
				mock.patch.object(module, 'signedIn') as login,
				contextlib.redirect_stderr(io.StringIO()),
				self.assertRaises(SystemExit),
			):
				module.main()
			login.assert_not_called()
		with (
			mock.patch('sys.argv', ['org-setup.py', 'import-settings', '--complete']),
			mock.patch.object(module, 'signedIn', return_value=True),
			mock.patch.object(configuration, 'importSettings', return_value=0) as capture,
		):
			self.assertEqual(module.main(), 0)
		capture.assert_called_once_with(complete=True)


class PrivateSettingsTest(unittest.TestCase):
	def setUp(self):
		self.directory = tempfile.TemporaryDirectory()
		self.addCleanup(self.directory.cleanup)
		patch = mock.patch.dict(os.environ, {'ORGSETUP_PRIVATE_DIR': self.directory.name})
		patch.start()
		self.addCleanup(patch.stop)
		localdata.resetCapture()
		self.addCleanup(localdata.resetCapture)

	def saveItems(self, key, items):
		config = {'organization': {'collections': {key: items}}, 'repositories': {}}
		with contextlib.redirect_stdout(io.StringIO()):
			localdata.saveCapturedValues(config)
		return config

	def testPrivateValuesStayOutsideGitAndPreservePreviousReferences(self):
		path = 'repos/TOANQUYNHLLC/app/actions/variables/REGION'
		old = localdata.captureValue(path, 'PRIVATE_OLD')
		config = self.saveItems('variables', [{'name': 'REGION', 'value_source': old}])
		self.assertNotIn('PRIVATE_OLD', json.dumps(config))
		self.assertFalse(localdata.dataPath().is_relative_to(ROOT))
		self.assertEqual(localdata.dataPath().stat().st_mode & 0o777, 0o600)
		localdata.resetCapture()
		self.assertEqual(localdata.captureValue(path, 'PRIVATE_OLD'), old)
		new = localdata.captureValue(path, 'PRIVATE_NEW')
		self.assertNotEqual(new, old)
		self.saveItems('variables', [{'name': 'REGION', 'value_source': new}])
		self.assertEqual(localdata.privateValue(old), 'PRIVATE_OLD')
		self.assertEqual(localdata.privateValue(new), 'PRIVATE_NEW')

	def testPrivateDirectoryCannotBeRepositoryOrLinkedIntoIt(self):
		with (
			mock.patch.dict(os.environ, {'ORGSETUP_PRIVATE_DIR': str(ROOT)}),
			self.assertRaises(ValueError),
		):
			localdata.dataPath()
		(Path(self.directory.name) / github.ORG).symlink_to(ROOT, target_is_directory=True)
		with self.assertRaises(ValueError):
			localdata.readValues()

	def testFailedPublicSnapshotReplacementCannotCorruptOldPrivateValues(self):
		previous = sourceConfig()
		reference = 'repos/TOANQUYNHLLC/.github/actions/variables/REGION'
		alias = localdata.captureValue(reference, 'PRIVATE_OLD')
		previous['repositories']['.github']['collections'] = {
			'variables': [{'name': 'REGION', 'value_source': alias}]
		}
		with contextlib.redirect_stdout(io.StringIO()):
			localdata.saveCapturedValues(previous)

		def capture(repo):
			scope = copy.deepcopy(
				previous['organization'] if repo is None else previous['repositories'][repo]
			)
			if repo is not None:
				scope['collections']['variables'][0]['value_source'] = localdata.captureValue(
					reference, 'PRIVATE_NEW'
				)
			return scope, {}

		originalReplace = Path.replace

		def replace(path, target):
			if Path(target).name == configuration.CONFIG_NAME:
				raise OSError('Không thay được nguồn công khai')
			return originalReplace(path, target)

		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			publicPath = root / configuration.CONFIG_NAME
			publicPath.write_text(configuration.jsonText(previous), encoding='utf-8')
			before = publicPath.read_bytes()
			with (
				mock.patch.object(configuration, 'readConfig', return_value=previous),
				mock.patch.object(configuration, 'captureScope', side_effect=capture),
				mock.patch.object(github, 'listRepos', return_value=['.github']),
				mock.patch.object(github, 'ROOT', root),
				mock.patch.object(Path, 'replace', replace),
				contextlib.redirect_stdout(io.StringIO()),
				self.assertRaises(OSError),
			):
				configuration.importSettings()
			self.assertEqual(publicPath.read_bytes(), before)
			self.assertEqual(list(root.iterdir()), [publicPath])
		self.assertEqual(localdata.privateValue(alias), 'PRIVATE_OLD')

	def testPrivateFileRejectsSymlinksAndReadableByOthers(self):
		path = localdata.dataPath()
		path.parent.mkdir()
		path.write_text('{}', encoding='utf-8')
		path.chmod(0o644)
		with self.assertRaises(ValueError):
			localdata.readValues()
		path.unlink()
		path.symlink_to(ROOT / 'github-settings.json')
		with self.assertRaises(ValueError):
			localdata.readValues()

	def testVariableRoundTripUsesNamedSelectionAndDoesNotExposeValue(self):
		base = 'orgs/TOANQUYNHLLC'
		with mock.patch.object(
			catalog.resources,
			'readCollection',
			side_effect=[
				[{'name': 'REGION', 'value': 'PRIVATE_REGION', 'visibility': 'selected'}],
				[{'full_name': 'TOANQUYNHLLC/app', 'id': 19}],
			],
		):
			items, ids = catalog.readDetails(base, 'variables')
		self.assertEqual(ids, {})
		self.assertEqual(items[0]['selected_repositories'], ['TOANQUYNHLLC/app'])
		self.saveItems('variables', items)
		plan = []
		with mock.patch.object(catalog.resources, 'repositoryIds', return_value=[39]) as resolve:
			catalog.collectionChanges(
				plan,
				base,
				{'collections': {'variables': []}},
				{'collections': {'variables': items}},
				{},
			)
		resolve.assert_called_once_with(['TOANQUYNHLLC/app'], {})
		self.assertEqual(plan[0][1], 'POST')
		self.assertNotIn('PRIVATE_REGION', json.dumps(plan))
		body = localdata.resolveBody(plan[0][2])
		self.assertEqual(body['value'], 'PRIVATE_REGION')
		self.assertEqual(body['selected_repository_ids'], [39])
		self.assertTrue(catalog.itemMatches('variables', items[0], items[0]))
		changed = dict(
			items[0],
			value_source=localdata.captureValue(
				f'{base}/actions/variables/REGION', 'CHANGED_REGION'
			),
		)
		self.assertFalse(catalog.itemMatches('variables', changed, items[0]))

	def testEnvironmentVariablesUseEnvironmentApi(self):
		base = 'repos/TOANQUYNHLLC/app/environments/Production%20EU'
		with mock.patch.object(
			catalog.resources,
			'readCollection',
			return_value=[{'name': 'REGION', 'value': 'PRIVATE'}],
		) as read:
			items, _ = catalog.readDetails(base, 'variables')
		read.assert_called_once_with(f'{base}/variables', 'variables')
		self.saveItems('variables', items)
		plan = []
		catalog.collectionChanges(
			plan,
			base,
			{'collections': {'variables': []}},
			{'collections': {'variables': items}},
			{},
		)
		self.assertEqual(plan[0][0], f'{base}/variables')

	def testWebhookCaptureExcludesCredentialsAndCreateRequiresExplicitSecret(self):
		base = 'repos/TOANQUYNHLLC/app'
		data = [
			{
				'id': 11,
				'name': 'web',
				'active': True,
				'events': ['push'],
				'config': {
					'url': 'https://example.test/PRIVATE_URL',
					'content_type': 'json',
					'insecure_ssl': '0',
					'secret': 'MASKED_NOT_A_BACKUP',
				},
			}
		]
		with mock.patch.object(github, 'ghList', return_value=data):
			items, ids = catalog.readDetails(base, 'webhooks')
		self.assertEqual(ids[items[0]['url_source']], 11)
		config = self.saveItems('webhooks', items)
		self.assertNotIn('PRIVATE_URL', json.dumps(config))
		self.assertNotIn('MASKED_NOT_A_BACKUP', localdata.dataPath().read_text())
		with (
			mock.patch.object(catalog, 'readDetails', return_value=([], {})),
			self.assertRaises(ValueError),
		):
			catalog.collectionChanges(
				[],
				base,
				{'collections': {'webhooks': []}},
				{'collections': {'webhooks': items}},
				{},
			)
		values = localdata.readValues()
		values[items[0]['secret_source']] = 'PRIVATE_SHARED_SECRET'
		localdata.dataPath().write_text(json.dumps(values), encoding='utf-8')
		plan = []
		with mock.patch.object(catalog, 'readDetails', return_value=([], {})):
			catalog.collectionChanges(
				plan,
				base,
				{'collections': {'webhooks': []}},
				{'collections': {'webhooks': items}},
				{},
			)
		self.assertNotIn('PRIVATE_SHARED_SECRET', json.dumps(plan))
		body = localdata.resolveBody(plan[0][2])
		self.assertEqual(body['config']['secret'], 'PRIVATE_SHARED_SECRET')
		self.assertEqual(body['config']['url'], data[0]['config']['url'])

	def testExistingWebhookPreservesSecretAndEventsOrderIsIrrelevant(self):
		base = 'repos/TOANQUYNHLLC/app'
		alias = localdata.captureValue(f'{base}/hooks/url', 'https://example.test/PRIVATE')
		before = {
			'name': 'web',
			'active': True,
			'events': ['push', 'issues'],
			'url_source': alias,
			'secret_source': alias + '/secret',
			'content_type': 'json',
			'insecure_ssl': '0',
		}
		self.saveItems('webhooks', [before])
		self.assertTrue(
			catalog.itemMatches('webhooks', before, dict(before, events=['issues', 'push']))
		)
		plan = []
		with mock.patch.object(catalog, 'readDetails', return_value=([before], {alias: 13})):
			catalog.collectionChanges(
				plan,
				base,
				{'collections': {'webhooks': [before]}},
				{'collections': {'webhooks': [dict(before, content_type='form')]}},
				{},
			)
		self.assertEqual(plan[0][:2], (f'{base}/hooks/13/config', 'PATCH'))
		self.assertNotIn('secret', localdata.resolveBody(plan[0][2]))
		with (
			mock.patch.object(catalog, 'readDetails', return_value=([before], {alias: 13})),
			self.assertRaises(ValueError),
		):
			catalog.collectionChanges(
				[],
				base,
				{'collections': {'webhooks': [before]}},
				{'collections': {'webhooks': [dict(before, active=False)]}},
				{},
			)

	def testPrivateWriteErrorsCannotExposePayloadOrRetry(self):
		config = sourceConfig()
		alias = localdata.captureValue(
			'repos/TOANQUYNHLLC/.github/actions/variables/REGION', 'PRIVATE_PAYLOAD'
		)
		items = [{'name': 'REGION', 'value_source': alias}]
		self.saveItems('variables', items)
		wanted = config['repositories']['.github']
		wanted['collections'] = {'variables': items}
		current = copy.deepcopy(wanted)
		current['collections']['variables'] = []
		output = io.StringIO()
		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(
				configuration, 'configuredScopes', return_value=[('.github', wanted, (current, {}))]
			),
			mock.patch.object(
				github, 'gh', side_effect=RuntimeError('API rejected PRIVATE_PAYLOAD')
			) as write,
			contextlib.redirect_stdout(output),
			self.assertRaises(RuntimeError) as caught,
		):
			configuration.syncConfiguredSettings(True)
		write.assert_called_once()
		self.assertNotIn('PRIVATE_PAYLOAD', output.getvalue())
		self.assertNotIn('PRIVATE_PAYLOAD', str(caught.exception))
		self.assertTrue(caught.exception.__suppress_context__)

	def testMissingPrivateValueBlocksAllMutationsAndReservedPayloadIsRejected(self):
		config = sourceConfig()
		config['repositories']['.github']['collections'] = {
			'variables': [
				{
					'name': 'REGION',
					'value_source': 'repos/TOANQUYNHLLC/.github/actions/variables/REGION#'
					+ 'a' * 32,
				}
			]
		}
		current = copy.deepcopy(config['repositories']['.github'])
		current['collections']['variables'] = []
		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(
				configuration,
				'configuredScopes',
				return_value=[('.github', config['repositories']['.github'], (current, {}))],
			),
			mock.patch.object(github, 'gh') as write,
			self.assertRaises(ValueError),
		):
			configuration.syncConfiguredSettings(True)
		write.assert_not_called()
		config['repositories']['.github']['settings']['description'] = {'$local_value': 'arbitrary'}
		with self.assertRaises(ValueError):
			configuration.validateConfig(config)

	def testPrivateReferencesCannotCrossScopes(self):
		item = {
			'name': 'REGION',
			'value_source': 'repos/TOANQUYNHLLC/other/actions/variables/REGION#' + 'a' * 32,
		}
		with self.assertRaises(ValueError):
			catalog.validateReferenceScope('repos/TOANQUYNHLLC/app', 'variables', [item])

	def testPagesNotFoundRequiresVerifiedPublicAdmin(self):
		base = 'repos/TOANQUYNHLLC/app'
		for private in (True, False):
			with (
				self.subTest(private=private),
				mock.patch.object(
					github,
					'ghJson',
					side_effect=[
						RuntimeError('HTTP 404'),
						{
							'full_name': 'TOANQUYNHLLC/app',
							'private': private,
							'permissions': {'admin': True},
						},
					],
				),
			):
				if private:
					with self.assertRaises(ValueError):
						catalog.readDetails(base, 'pages')
				else:
					self.assertEqual(catalog.readDetails(base, 'pages'), ([], {}))

	def testInheritedOidcCannotBeRestoredAsOrganizationDefinition(self):
		with (
			mock.patch.object(
				github,
				'ghList',
				return_value=[{'custom_property_name': 'region', 'inclusion_source': 'enterprise'}],
			),
			self.assertRaises(ValueError),
		):
			catalog.readDetails('orgs/TOANQUYNHLLC', 'oidc_properties')
		catalog.validateGroup(
			'property_schema',
			[{'property_name': 'region', 'value_type': 'string', 'values_editable_by': None}],
		)


if __name__ == '__main__':
	unittest.main()
