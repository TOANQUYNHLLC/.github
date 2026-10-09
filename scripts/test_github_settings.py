"""Kiểm tra nhập/áp dụng cài đặt: giữ false, lọc bí mật, chặn ghi khi đọc thiếu và xác nhận sau áp dụng."""

import contextlib
import copy
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

try:
	from testsupport import ROOT, loadScript
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript

from orgsetup import catalog, configuration, github, resources


def baselineConfig():
	"""Nguồn cài đặt cố định cho test: cấu trúc trường lấy từ github-settings.json thật (theo kịp hợp đồng API),
	giá trị mà các test giả định được ghim tại đây. Tệp thật đổi sau mỗi lần make org-import — bật Actions, thêm
	repository… — nên test không được dựa vào giá trị của nó."""
	config = configuration.readConfig(ROOT)
	organization, repository = config['organization'], config['repositories']['.github']
	for scope in (organization, repository):
		scope.pop('collections', None)
		scope.pop('observed', None)
	config['repositories'], config['unavailable'] = {'.github': repository}, {}
	organization['settings']['blog'] = 'https://toanquynh.com'
	organization['web_settings']['two_factor_requirement_enabled'] = True
	organization['runner_groups'] = [
		{
			'settings': {
				'name': 'Default',
				'visibility': 'all',
				'allows_public_repositories': False,
				'restricted_to_workflows': False,
				'selected_workflows': [],
			},
			'default': True,
			'inherited': False,
			'workflow_restrictions_read_only': False,
			'selected_repositories': [],
		}
	]
	repository['settings']['archived'] = False
	repository['settings']['allow_rebase_merge'] = False
	repository['endpoints']['actions/cache/retention-limit'] = {'max_cache_retention_days': 7}
	repository['endpoints']['actions/cache/storage-limit'] = {'max_cache_size_gb': 10}
	for scope in (organization, repository):
		for suffix in configuration.SELECTED_ENDPOINTS:
			scope['endpoints'].pop(suffix, None)
		scope['endpoints']['actions/permissions/workflow'] = {
			'default_workflow_permissions': 'read',
			'can_approve_pull_request_reviews': True,
		}
	organization['endpoints'].update(
		{
			'actions/permissions/self-hosted-runners': {'enabled_repositories': 'all'},
			'copilot/coding-agent/permissions': {'enabled_repositories': 'all'},
			'actions/permissions': {'enabled_repositories': 'none', 'sha_pinning_required': False},
			'actions/oidc/customization/sub': {},
			'settings/immutable-releases': {'enforced_repositories': 'all'},
		}
	)
	repository['endpoints'].update(
		{
			'actions/permissions': {'enabled': False, 'sha_pinning_required': False},
			'actions/oidc/customization/sub': {'use_default': True, 'use_immutable_subject': True},
			'vulnerability-alerts': {'enabled': True},
			'automated-security-fixes': {'enabled': True},
			'immutable-releases': {'enabled': True},
		}
	)
	repository['security'] = {
		'secret_scanning': 'enabled',
		'secret_scanning_push_protection': 'enabled',
		'secret_scanning_non_provider_patterns': 'disabled',
	}
	configuration.validateDependencies(config)
	return config


class GitHubSettingsTest(unittest.TestCase):
	def testSecurityAndDiscussionsShareIdentityOnlyWithinOnePlan(self):
		wanted = copy.deepcopy(self.config)
		repository = wanted['repositories'].pop('.github')
		wanted['repositories']['app'] = repository
		repository['settings']['has_discussions'] = True
		repository['security_configuration'] = 'Baseline'
		original = copy.deepcopy(wanted)
		for repositoryId, nodeId in ((99, 'R_first'), (109, 'R_second')):
			current = copy.deepcopy(repository)
			current['settings']['has_discussions'] = False
			current['security_configuration'] = None
			bodies = []

			def recordWrite(*args, stdin, current=current, bodies=bodies):
				body = json.loads(stdin)
				bodies.append(body)
				if args[3] == 'graphql':
					current['settings']['has_discussions'] = body['variables']['input'][
						'hasDiscussionsEnabled'
					]
				else:
					current['security_configuration'] = 'Baseline'

			with (
				self.subTest(repositoryId=repositoryId, nodeId=nodeId),
				mock.patch.object(configuration, 'readConfig', return_value=wanted),
				mock.patch.object(
					configuration,
					'readScope',
					side_effect=lambda repo, current=current: (
						current if repo is not None else wanted['organization'],
						{},
					),
				),
				mock.patch.object(
					github,
					'ghJson',
					return_value={
						'full_name': 'TOANQUYNHLLC/app',
						'id': repositoryId,
						'node_id': nodeId,
					},
				) as identity,
				mock.patch.object(
					github,
					'ghList',
					return_value=[{'name': 'Baseline', 'id': 7, 'target_type': 'organization'}],
				),
				mock.patch.object(github, 'gh', side_effect=recordWrite) as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(configuration.syncConfiguredSettings(apply=True), 0)
			identity.assert_called_once_with('api', 'repos/TOANQUYNHLLC/app')
			self.assertEqual(write.call_count, 2)
			self.assertEqual(
				bodies[0], {'selected_repository_ids': [repositoryId], 'scope': 'selected'}
			)
			self.assertEqual(bodies[1]['variables']['input']['repositoryId'], nodeId)
			self.assertEqual(wanted, original)

	def testIncompleteRepositoryIdentityIsReadAgainWhenNeeded(self):
		base = 'repos/TOANQUYNHLLC/app'
		complete = {'full_name': 'TOANQUYNHLLC/app', 'id': 99, 'node_id': 'R_app'}
		for nodeId in (None, '', True):
			resourceCache, plan = {}, []
			with (
				self.subTest(nodeId=nodeId),
				mock.patch.object(
					github, 'ghJson', side_effect=[dict(complete, node_id=nodeId), complete]
				) as read,
			):
				configuration.securityBindingChanges(
					plan,
					base,
					'app',
					{'security_configuration': 'Baseline'},
					{'security_configuration': None},
					resourceCache,
				)
				configuration.repositorySettingChanges(
					plan,
					base,
					{'has_discussions': False},
					{'has_discussions': True},
					resourceCache,
				)
				configuration.repositorySettingChanges(
					plan,
					base,
					{'has_discussions': False},
					{'has_discussions': True},
					resourceCache,
				)
			self.assertEqual(read.call_count, 2)
			self.assertEqual(plan[0][2], {'selected_repository_ids': [99]})
			self.assertEqual(plan[1][2]['variables']['input']['repositoryId'], 'R_app')
			self.assertEqual(plan[2][2]['variables']['input']['repositoryId'], 'R_app')

	def testEquivalentTopicAndLanguageListsDoNotCauseWrites(self):
		wanted = copy.deepcopy(self.config)
		repository = wanted['repositories']['.github']
		repository['endpoints']['topics'] = {'names': ['PYTHON', 'github', 'python']}
		repository['endpoints']['code-scanning/default-setup'] = {
			'state': 'configured',
			'languages': ['python', 'actions'],
			'query_suite': 'default',
		}
		current = copy.deepcopy(repository)
		current['endpoints']['topics']['names'] = ['github', 'python']
		current['endpoints']['code-scanning/default-setup']['languages'].reverse()
		original = copy.deepcopy(wanted)
		before = copy.deepcopy(current)
		with (
			mock.patch.object(configuration, 'readConfig', return_value=wanted),
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=lambda repo: (
					current if repo is not None else wanted['organization'],
					{},
				),
			),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(apply=True), 0)
		write.assert_not_called()
		self.assertEqual(wanted, original)
		self.assertEqual(current, before)

	def testChangedTopicAndLanguageListsKeepPayloadAndVerifyEquivalentReadback(self):
		for suffix, key, target, previous in (
			('topics', 'names', ['PYTHON', 'github'], ['legacy']),
			('topics', 'names', [], ['python']),
			('code-scanning/default-setup', 'languages', ['python', 'actions'], ['ruby']),
		):
			wanted = copy.deepcopy(self.config)
			repository = wanted['repositories']['.github']
			repository['endpoints'][suffix] = (
				{key: target}
				if suffix == 'topics'
				else {'state': 'configured', key: target, 'query_suite': 'default'}
			)
			current = copy.deepcopy(repository)
			current['endpoints'][suffix][key] = previous
			original = copy.deepcopy(wanted)

			def recordWrite(*args, stdin, current=current, suffix=suffix, key=key, target=target):
				current['endpoints'][suffix].update(json.loads(stdin))
				current['endpoints'][suffix][key] = (
					[item.lower() for item in reversed(target)]
					if suffix == 'topics'
					else list(reversed(target))
				)

			with (
				self.subTest(suffix=suffix, target=target),
				mock.patch.object(configuration, 'readConfig', return_value=wanted),
				mock.patch.object(
					configuration,
					'readScope',
					side_effect=lambda repo, current=current, wanted=wanted: (
						current if repo is not None else wanted['organization'],
						{},
					),
				),
				mock.patch.object(github, 'gh', side_effect=recordWrite) as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(configuration.syncConfiguredSettings(apply=True), 0)
			write.assert_called_once()
			self.assertEqual(json.loads(write.call_args.kwargs['stdin'])[key], target)
			self.assertEqual(wanted, original)

	def testOidcClaimOrderStillCausesUpdate(self):
		wanted = {'use_default': False, 'include_claim_keys': ['repo', 'context']}
		current = dict(wanted, include_claim_keys=['context', 'repo'])
		plan = []
		configuration.addChanges(
			plan,
			'repos/TOANQUYNHLLC/app/actions/oidc/customization/sub',
			current,
			wanted,
			'PUT',
			'actions/oidc/customization/sub',
		)
		self.assertEqual(len(plan), 1)
		self.assertEqual(plan[0][2], wanted)
		self.assertEqual(plan[0][3], {'include_claim_keys': ['repo', 'context']})

	def testLanguageOrderDoesNotMaskCodeScanningPolicyChange(self):
		wanted = {
			'state': 'configured',
			'languages': ['python', 'actions'],
			'query_suite': 'extended',
		}
		current = dict(wanted, languages=['actions', 'python'], query_suite='default')
		plan = []
		configuration.addChanges(
			plan,
			'repos/TOANQUYNHLLC/app/code-scanning/default-setup',
			current,
			wanted,
			'PATCH',
			'code-scanning/default-setup',
		)
		self.assertEqual(len(plan), 1)
		self.assertEqual(plan[0][2], {'query_suite': 'extended'})
		self.assertEqual(plan[0][3], {'query_suite': 'extended'})

	def testConfiguredRepositoryReadsOverlapAndKeepWriteOrder(self):
		names = [f'app{index}' for index in range(8)]
		wanted = copy.deepcopy(self.config)
		wanted['repositories'] = {
			repo: copy.deepcopy(self.config['repositories']['.github']) for repo in names
		}
		current = {
			None: copy.deepcopy(wanted['organization']),
			**copy.deepcopy(wanted['repositories']),
		}
		for repo, scope in current.items():
			scope['settings']['description'] = f'Giá trị cũ của {repo}'
		self.saveConfig(github.ROOT, wanted)
		barrier, secondFinished = threading.Barrier(4, timeout=3), threading.Event()
		lock = threading.Lock()
		completed, writes = [], []
		active, peak = 0, 0

		def read(repo):
			nonlocal active, peak
			if repo is not None and not writes:
				with lock:
					active += 1
					peak = max(peak, active)
				barrier.wait()
				if repo == names[0]:
					self.assertTrue(secondFinished.wait(3))
				with lock:
					active -= 1
					completed.append(repo)
				if repo == names[1]:
					secondFinished.set()
			return copy.deepcopy(current[repo]), {}

		def write(*args, **kwargs):
			self.assertCountEqual(completed, names)
			path = args[3]
			repo = None if path.startswith('orgs/') else path.split('/')[2]
			current[repo]['settings'].update(json.loads(kwargs['stdin']))
			writes.append(path)

		with (
			mock.patch.object(configuration, 'readScope', side_effect=read) as reader,
			mock.patch.object(github, 'gh', side_effect=write),
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
		self.assertEqual(peak, 4)
		self.assertGreater(completed.index(names[0]), completed.index(names[1]))
		self.assertEqual(
			writes, ['orgs/TOANQUYNHLLC', *(f'repos/TOANQUYNHLLC/{repo}' for repo in names)]
		)
		self.assertCountEqual([call.args[0] for call in reader.call_args_list], [None, *names] * 2)

	def testConfiguredRepositoryReadFailureBlocksAllWrites(self):
		names = ['app', 'last']
		wanted = copy.deepcopy(self.config)
		wanted['repositories'] = {
			repo: copy.deepcopy(self.config['repositories']['.github']) for repo in names
		}
		self.saveConfig(github.ROOT, wanted)
		for failure in ('exception', 'unavailable'):

			def read(repo, failure=failure):
				scope = copy.deepcopy(
					wanted['organization'] if repo is None else wanted['repositories'][repo]
				)
				scope['settings']['description'] = 'Giá trị cũ'
				if repo == 'last':
					if failure == 'exception':
						raise RuntimeError('last: HTTP 403')
					return scope, {'repos/TOANQUYNHLLC/last/topics': 'HTTP 403'}
				return scope, {}

			with (
				self.subTest(failure=failure),
				mock.patch.object(configuration, 'readScope', side_effect=read),
				mock.patch.object(github, 'gh') as write,
				self.assertRaisesRegex((RuntimeError, ValueError), 'last'),
			):
				configuration.syncConfiguredSettings(True)
			write.assert_not_called()

	def testScopeReadsIndependentResourcesWithEndpoints(self):
		organization = self.config['organization']
		data = dict(organization['settings'], **organization['web_settings'], login=github.ORG)
		data.pop('installed_apps', None)
		for fail in (None, 'runner_groups', 'installed_apps', 'security_configurations'):
			barrier = threading.Barrier(4, timeout=3)

			def read(value, failure=False, barrier=barrier):
				barrier.wait()
				if failure:
					raise RuntimeError('HTTP 403')
				return value

			with (
				self.subTest(fail=fail),
				mock.patch.object(github, 'ghJson', return_value=data),
				mock.patch.object(
					configuration, 'endpointDefinitions', return_value={'example': ('GET', {})}
				),
				mock.patch.object(
					configuration, 'readEndpoint', side_effect=lambda *args: read({'enabled': True})
				),
				mock.patch.object(
					resources,
					'readRunnerGroups',
					side_effect=lambda fail=fail: read(
						organization['runner_groups'], fail == 'runner_groups'
					),
				),
				mock.patch.object(
					resources,
					'installedApps',
					side_effect=lambda fail=fail: read(
						organization['web_settings']['installed_apps'], fail == 'installed_apps'
					),
				),
				mock.patch.object(
					configuration,
					'readSecurityDefaults',
					side_effect=lambda fail=fail: read(
						organization['security_configurations'], fail == 'security_configurations'
					),
				),
			):
				captured, unavailable = configuration.readScope()
			self.assertEqual(captured['endpoints'], {'example': {'enabled': True}})
			expectedUnavailable = {}
			for key, suffix in (
				('runner_groups', 'actions/runner-groups'),
				('installed_apps', 'installations'),
				('security_configurations', 'code-security'),
			):
				observed = captured['web_settings'] if key == 'installed_apps' else captured
				wanted = organization['web_settings'] if key == 'installed_apps' else organization
				if fail == key:
					self.assertNotIn(key, observed)
					expectedUnavailable[f'orgs/TOANQUYNHLLC/{suffix}'] = (
						'Không đọc được cấu hình bảo mật và phạm vi áp dụng'
						if key == 'security_configurations'
						else 'Không đọc đủ hoặc không xác minh được tài nguyên'
					)
				else:
					self.assertEqual(observed[key], wanted[key])
			self.assertEqual(unavailable, expectedUnavailable)

	def testSelectedListsAreReadOnlyWhenActiveAndFailuresRemainUnavailable(self):
		for active, fail in ((False, False), (True, False), (True, True)):
			organization = copy.deepcopy(self.config['organization'])
			if active:
				organization['endpoints']['actions/permissions'].update(
					enabled_repositories='selected', allowed_actions='selected'
				)
				organization['endpoints']['actions/permissions/repositories'] = {
					'selected_repositories': []
				}
				organization['endpoints']['actions/permissions/selected-actions'] = {
					'github_owned_allowed': False,
					'verified_allowed': False,
					'patterns_allowed': [],
				}
			data = dict(organization['settings'], **organization['web_settings'], login=github.ORG)

			def read(path, suffix, fields, fail=fail, organization=organization):
				if fail and suffix == 'actions/permissions/selected-actions':
					raise RuntimeError('HTTP 403')
				return organization['endpoints'][suffix]

			with (
				self.subTest(active=active, fail=fail),
				mock.patch.object(github, 'ghJson', return_value=data),
				mock.patch.object(configuration, 'readEndpoint', side_effect=read) as reader,
				mock.patch.object(
					resources, 'readRunnerGroups', return_value=organization['runner_groups']
				),
				mock.patch.object(
					resources,
					'installedApps',
					return_value=organization['web_settings']['installed_apps'],
				),
				mock.patch.object(
					configuration,
					'readSecurityDefaults',
					return_value=organization['security_configurations'],
				),
			):
				captured, unavailable = configuration.readScope()
			calls = {call.args[1] for call in reader.call_args_list}
			self.assertEqual('actions/permissions/repositories' in calls, active)
			self.assertEqual('actions/permissions/selected-actions' in calls, active)
			if fail:
				self.assertEqual(
					unavailable,
					{'orgs/TOANQUYNHLLC/actions/permissions/selected-actions': 'HTTP 403'},
				)
				self.assertNotIn('actions/permissions/selected-actions', captured['endpoints'])
			else:
				self.assertEqual(unavailable, {})
				self.assertEqual(captured['endpoints'], organization['endpoints'])

	def testSelectedRepositoryIdsMustResolveBeforeAnyMutation(self):
		config = copy.deepcopy(self.config)
		config['organization']['endpoints']['settings/immutable-releases'] = {
			'enforced_repositories': 'selected'
		}
		config['organization']['endpoints']['settings/immutable-releases/repositories'] = {
			'selected_repositories': ['TOANQUYNHLLC/missing']
		}
		self.saveConfig(github.ROOT, config)
		with (
			mock.patch.object(
				configuration, 'readScope', return_value=(self.config['organization'], {})
			),
			mock.patch.object(
				resources, 'repositoryIds', side_effect=ValueError('Không đọc được repository')
			),
			mock.patch.object(github, 'gh') as write,
			self.assertRaises(ValueError),
		):
			configuration.syncConfiguredSettings(True)
		write.assert_not_called()

	def testSelectedListOrderingDoesNotCreateDrift(self):
		plan = []
		with mock.patch.object(resources, 'repositoryIds') as resolve:
			configuration.selectedEndpointChanges(
				plan,
				'orgs/TOANQUYNHLLC',
				'actions/permissions/repositories',
				{'selected_repositories': ['TOANQUYNHLLC/app', 'TOANQUYNHLLC/.github']},
				{'selected_repositories': ['TOANQUYNHLLC/.github', 'TOANQUYNHLLC/app']},
			)
		resolve.assert_not_called()
		self.assertEqual(plan, [])

	def testSelectedImmutableReleasesPreventConflictingRepositorySettings(self):
		config = copy.deepcopy(self.config)
		config['organization']['endpoints']['settings/immutable-releases'] = {
			'enforced_repositories': 'selected'
		}
		config['organization']['endpoints']['settings/immutable-releases/repositories'] = {
			'selected_repositories': ['TOANQUYNHLLC/.github']
		}
		config['repositories']['.github']['endpoints']['immutable-releases'] = {'enabled': False}
		self.saveConfig(github.ROOT, config)
		with self.assertRaisesRegex(ValueError, 'Release bất biến'):
			configuration.readConfig()
		config['organization']['endpoints']['settings/immutable-releases/repositories'][
			'selected_repositories'
		] = []
		self.saveConfig(github.ROOT, config)
		self.assertEqual(configuration.readConfig(), config)

	def testSelectedActionsAreImportedWithCompletePolicy(self):
		policy = {
			'github_owned_allowed': True,
			'verified_allowed': False,
			'patterns_allowed': ['actions/*', 'TOANQUYNHLLC/*'],
		}
		fields = {'github_owned_allowed': bool, 'verified_allowed': bool, 'patterns_allowed': list}
		with mock.patch.object(github, 'ghJson', return_value=policy):
			self.assertEqual(
				configuration.readEndpoint(
					'repos/TOANQUYNHLLC/.github/actions/permissions/selected-actions',
					'actions/permissions/selected-actions',
					fields,
				),
				policy,
			)
		for invalid in (
			{'github_owned_allowed': True},
			dict(policy, patterns_allowed=['actions/*', 'actions/*']),
		):
			with (
				mock.patch.object(github, 'ghJson', return_value=invalid),
				self.assertRaises(ValueError),
			):
				configuration.readEndpoint(
					'repos/TOANQUYNHLLC/.github/actions/permissions/selected-actions',
					'actions/permissions/selected-actions',
					fields,
				)

	def testSelectedRepositoriesImportNamesAndRejectIncompleteIdentity(self):
		fields = {'selected_repositories': list}
		path = 'orgs/TOANQUYNHLLC/actions/permissions/repositories'
		items = [
			{'id': 99, 'full_name': 'TOANQUYNHLLC/app'},
			{'id': 100, 'full_name': 'TOANQUYNHLLC/.github'},
		]
		with mock.patch.object(resources, 'readCollection', return_value=items):
			self.assertEqual(
				configuration.readEndpoint(path, 'actions/permissions/repositories', fields),
				{'selected_repositories': ['TOANQUYNHLLC/.github', 'TOANQUYNHLLC/app']},
			)
		for invalid in (
			[{'id': True, 'full_name': 'TOANQUYNHLLC/app'}],
			[items[0], items[0]],
			[{'id': 99, 'full_name': 'other/app'}],
		):
			with (
				mock.patch.object(resources, 'readCollection', return_value=invalid),
				self.assertRaises(ValueError),
			):
				configuration.readEndpoint(path, 'actions/permissions/repositories', fields)

	def testSelectedPolicyValidatesCompanionListsBeforeWriting(self):
		config = copy.deepcopy(self.config)
		config['organization']['endpoints']['actions/permissions'].update(
			enabled_repositories='selected', allowed_actions='selected'
		)
		config['organization']['endpoints'].update(
			{
				'actions/permissions/repositories': {
					'selected_repositories': ['TOANQUYNHLLC/.github']
				},
				'actions/permissions/selected-actions': {
					'github_owned_allowed': True,
					'verified_allowed': False,
					'patterns_allowed': [],
				},
			}
		)
		self.saveConfig(github.ROOT, config)
		self.assertEqual(configuration.readConfig(), config)
		for suffix in ('actions/permissions/repositories', 'actions/permissions/selected-actions'):
			invalid = copy.deepcopy(config)
			del invalid['organization']['endpoints'][suffix]
			self.saveConfig(github.ROOT, invalid)
			with (
				self.subTest(suffix=suffix),
				mock.patch.object(github, 'gh') as write,
				self.assertRaises(ValueError),
			):
				configuration.syncConfiguredSettings(True)
			write.assert_not_called()

	def testApplySelectedPolicyResolvesIdsAndConfirmsReadBack(self):
		wanted = copy.deepcopy(self.config)
		endpoints = wanted['organization']['endpoints']
		endpoints['actions/permissions'].update(
			enabled_repositories='selected', allowed_actions='selected'
		)
		endpoints['settings/immutable-releases']['enforced_repositories'] = 'selected'
		for suffix in (
			'actions/permissions/repositories',
			'settings/immutable-releases/repositories',
		):
			endpoints[suffix] = {'selected_repositories': ['TOANQUYNHLLC/.github']}
		endpoints['actions/permissions/selected-actions'] = {
			'github_owned_allowed': True,
			'verified_allowed': False,
			'patterns_allowed': ['actions/*'],
		}
		self.saveConfig(github.ROOT, wanted)
		with (
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=[
					(self.config['organization'], {}),
					(self.config['repositories']['.github'], {}),
					(wanted['organization'], {}),
					(wanted['repositories']['.github'], {}),
				],
			),
			mock.patch.object(resources, 'repositoryIds', return_value=[99]),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
		calls = {call.args[3]: json.loads(call.kwargs['stdin']) for call in write.call_args_list}
		self.assertEqual(
			calls['orgs/TOANQUYNHLLC/actions/permissions/repositories'],
			{'selected_repository_ids': [99]},
		)
		self.assertEqual(
			calls['orgs/TOANQUYNHLLC/settings/immutable-releases/repositories'],
			{'selected_repository_ids': [99]},
		)
		self.assertEqual(
			calls['orgs/TOANQUYNHLLC/actions/permissions/selected-actions'],
			endpoints['actions/permissions/selected-actions'],
		)
		paths = [call.args[3] for call in write.call_args_list]
		self.assertLess(
			paths.index('orgs/TOANQUYNHLLC/actions/permissions'),
			paths.index('orgs/TOANQUYNHLLC/actions/permissions/repositories'),
		)
		self.assertLess(
			paths.index('orgs/TOANQUYNHLLC/settings/immutable-releases'),
			paths.index('orgs/TOANQUYNHLLC/settings/immutable-releases/repositories'),
		)

	def testRepositoryOutsideSelectedOrganizationCannotEnableActions(self):
		config = copy.deepcopy(self.config)
		endpoints = config['organization']['endpoints']
		endpoints['actions/permissions'].update(
			enabled_repositories='selected', allowed_actions='all'
		)
		endpoints['actions/permissions/repositories'] = {'selected_repositories': []}
		config['repositories']['.github']['endpoints']['actions/permissions'].update(
			enabled=True, allowed_actions='all'
		)
		self.saveConfig(github.ROOT, config)
		with (
			mock.patch.object(github, 'gh') as write,
			self.assertRaisesRegex(ValueError, 'Actions'),
		):
			configuration.syncConfiguredSettings(True)
		write.assert_not_called()

	def setUp(self):
		# Mọi lần đọc nguồn cài đặt trong test (readConfig() không truyền root) dùng bản cố định.
		self.config = baselineConfig()
		# Các test hợp đồng chính dùng catalog giả lập; test_catalog kiểm tra danh mục thật riêng.
		catalogReader = mock.patch.object(catalog, 'readCollections', return_value=({}, {}, {}))
		catalogReader.start()
		self.addCleanup(catalogReader.stop)
		folder = tempfile.TemporaryDirectory()
		self.addCleanup(folder.cleanup)
		self.saveConfig(Path(folder.name), self.config)
		patcher = mock.patch.object(github, 'ROOT', Path(folder.name))
		patcher.start()
		self.addCleanup(patcher.stop)

	def saveConfig(self, root, config):
		(root / configuration.CONFIG_NAME).write_text(json.dumps(config), encoding='utf-8')

	def testRepositoryAliasesCannotCreateConflictingPlans(self):
		wanted = copy.deepcopy(self.config)
		wanted['repositories']['.GitHub'] = copy.deepcopy(wanted['repositories']['.github'])
		wanted['repositories']['.GitHub']['settings']['has_discussions'] = not wanted[
			'repositories'
		]['.github']['settings']['has_discussions']
		self.saveConfig(github.ROOT, wanted)
		with (
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=lambda repo: (
					wanted['repositories']['.github']
					if repo is not None
					else wanted['organization'],
					{},
				),
			) as read,
			mock.patch.object(
				github,
				'ghJson',
				return_value={'full_name': 'TOANQUYNHLLC/.github', 'id': 99, 'node_id': 'R_github'},
			) as identity,
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaisesRegex(ValueError, 'repository.*trùng'),
		):
			configuration.syncConfiguredSettings(apply=True)
		read.assert_not_called()
		identity.assert_not_called()
		write.assert_not_called()

	def testPrivateSecurityMetadataUnavailableIsImportedAndBlocksAllWrites(self):
		repository = copy.deepcopy(self.config['repositories']['.github'])
		repository['settings']['visibility'] = 'private'
		data = dict(
			repository['settings'],
			**repository['web_settings'],
			full_name='TOANQUYNHLLC/app',
			private=True,
			security_and_analysis=None,
		)
		readScope = configuration.readScope

		def read(repo=None):
			return (
				(copy.deepcopy(self.config['organization']), {})
				if repo is None
				else readScope(repo)
			)

		with (
			mock.patch.object(github, 'listRepos', return_value=['app']),
			mock.patch.object(configuration, 'readScope', side_effect=read),
			mock.patch.object(configuration, 'endpointDefinitions', return_value={}),
			mock.patch.object(configuration, 'readSecurityConfiguration', return_value=None),
			mock.patch.object(github, 'ghJson', return_value=data),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.importSettings(), 1)
			imported = configuration.readConfig()
			self.assertEqual(imported['repositories']['app']['settings'], repository['settings'])
			self.assertEqual(imported['repositories']['app']['security'], {})
			self.assertEqual(
				list(imported['unavailable']), ['repos/TOANQUYNHLLC/app (security_and_analysis)']
			)
			with self.assertRaisesRegex(ValueError, 'có mục chưa nhập'):
				configuration.syncConfiguredSettings(apply=True)
			imported['unavailable'] = {}
			imported['organization']['settings']['description'] = 'Giá trị mới cần áp dụng'
			self.saveConfig(github.ROOT, imported)
			with self.assertRaisesRegex(ValueError, 'security_and_analysis.*dừng trước khi ghi'):
				configuration.syncConfiguredSettings(apply=True)
		write.assert_not_called()

	def testPrivateSecurityMetadataOnlyAcceptsOmittedOrNullAsUnavailable(self):
		repository = self.config['repositories']['.github']
		for private, analysis in (
			(True, None),
			(True, 'omitted'),
			(True, []),
			(True, False),
			(False, None),
		):
			data = dict(
				repository['settings'],
				**repository['web_settings'],
				full_name='TOANQUYNHLLC/app',
				private=private,
				security_and_analysis=analysis,
			)
			if analysis == 'omitted':
				data.pop('security_and_analysis')
			with (
				self.subTest(private=private, analysis=analysis),
				mock.patch.object(github, 'ghJson', return_value=data),
				mock.patch.object(configuration, 'endpointDefinitions', return_value={}),
				mock.patch.object(configuration, 'readSecurityConfiguration', return_value=None),
			):
				if private and (analysis is None or analysis == 'omitted'):
					scope, unavailable = configuration.readScope('app')
					self.assertEqual(scope['security'], {})
					self.assertIn('repos/TOANQUYNHLLC/app (security_and_analysis)', unavailable)
				else:
					with self.assertRaisesRegex(ValueError, 'security_and_analysis'):
						configuration.readScope('app')

	def testImportOnlyKeepsAllowlistedSettings(self):
		source = copy.deepcopy(self.config['repositories']['.github'])
		current = dict(
			source['settings'],
			**source['web_settings'],
			full_name='TOANQUYNHLLC/.github',
			private=False,
			temp_clone_token='SECRET_VALUE',
		)
		current['security_and_analysis'] = {
			key: {'status': value} for key, value in source['security'].items()
		}
		with (
			mock.patch.object(github, 'ghJson', return_value=current),
			mock.patch.object(
				configuration,
				'readSecurityConfiguration',
				return_value=source.get('security_configuration'),
			),
			mock.patch.object(
				configuration,
				'readEndpoint',
				side_effect=lambda path, suffix, fields: source['endpoints'][suffix],
			),
		):
			scope, unavailable = configuration.readScope('.github')
		self.assertFalse(scope['endpoints']['actions/permissions']['enabled'])
		self.assertFalse(scope['settings']['allow_rebase_merge'])
		self.assertEqual(scope['security']['secret_scanning_non_provider_patterns'], 'disabled')
		self.assertNotIn('SECRET_VALUE', json.dumps(scope))
		self.assertEqual(unavailable, {})

	def testImportCannotOverwriteFileAfterFatalRead(self):
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			self.saveConfig(root, self.config)
			original = (root / configuration.CONFIG_NAME).read_bytes()
			with (
				mock.patch.object(github, 'ROOT', root),
				mock.patch.object(github, 'listRepos', return_value=['.github']),
				mock.patch.object(configuration, 'readScope', side_effect=RuntimeError('HTTP 403')),
				mock.patch.object(github, 'gh') as write,
				self.assertRaises(RuntimeError),
			):
				configuration.importSettings()
			write.assert_not_called()
			self.assertEqual((root / configuration.CONFIG_NAME).read_bytes(), original)
			self.assertFalse((root / 'github-settings.json.tmp').exists())

	def testImportWritesOnlyLocalAndReportsIncompleteCapture(self):
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			self.saveConfig(root, self.config)
			unavailable = {'orgs/TOANQUYNHLLC/actions/permissions': 'HTTP 403'}
			organization = copy.deepcopy(self.config['organization'])
			del organization['endpoints']['actions/permissions']
			with (
				mock.patch.object(github, 'ROOT', root),
				mock.patch.object(github, 'listRepos', return_value=['.github']),
				mock.patch.object(
					configuration,
					'readScope',
					side_effect=lambda repo: (
						(organization, unavailable)
						if repo is None
						else (self.config['repositories'][repo], {})
					),
				),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(configuration.importSettings(), 1)
			write.assert_not_called()
			captured = json.loads((root / configuration.CONFIG_NAME).read_text())
			self.assertEqual(captured['unavailable'], unavailable)
			self.assertNotIn('actions/permissions', captured['organization']['endpoints'])

	def testImportedSnapshotRestoresSettingsWithoutReimportAndIsIdempotent(self):
		captured = copy.deepcopy(self.config)
		organization, repository = captured['organization'], captured['repositories']['.github']
		organization['endpoints']['actions/permissions'] = {
			'enabled_repositories': 'selected',
			'allowed_actions': 'all',
			'sha_pinning_required': True,
		}
		organization['endpoints']['actions/permissions/repositories'] = {
			'selected_repositories': []
		}
		repository['settings'].update(
			{
				'has_wiki': True,
				'has_projects': True,
				'is_template': False,
				'allow_rebase_merge': True,
			}
		)
		for scope in (organization, repository):
			scope['endpoints']['interaction-limits/pulls/creation-cap']['include_drafts'] = False
		current = copy.deepcopy(captured)

		def readScope(repo=None):
			scope = current['organization'] if repo is None else current['repositories'][repo]
			return copy.deepcopy(scope), {}

		def restore(*args, stdin):
			path, payload = args[3], json.loads(stdin)
			base = 'orgs/TOANQUYNHLLC' if path.startswith('orgs/') else 'repos/TOANQUYNHLLC/.github'
			scope = (
				current['organization']
				if path.startswith('orgs/')
				else current['repositories']['.github']
			)
			if path == base:
				analysis = payload.pop('security_and_analysis', {})
				scope.get('security', {}).update(
					{key: value['status'] for key, value in analysis.items()}
				)
				scope['settings'].update(payload)
			else:
				suffix = path[len(base) + 1 :]
				if suffix == 'actions/permissions/repositories':
					self.assertEqual(payload, {'selected_repository_ids': []})
					payload = {'selected_repositories': []}
				scope['endpoints'][suffix] = payload

		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			self.saveConfig(root, self.config)
			with (
				mock.patch.object(github, 'ROOT', root),
				mock.patch.object(github, 'listRepos', return_value=['.github']),
				mock.patch.object(configuration, 'readScope', side_effect=readScope),
				mock.patch.object(github, 'gh', side_effect=restore) as write,
				mock.patch.object(
					github, 'ghJson', return_value={'maximum_allowed_days': 90}
				) as readLimits,
				mock.patch.object(github, 'ghList') as readCatalog,
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(configuration.importSettings(), 0)
				write.assert_not_called()
				snapshot = (root / configuration.CONFIG_NAME).read_bytes()
				self.assertEqual(configuration.readConfig(root), captured)
				# Mô phỏng GitHub đổi trạng thái sau khi đã lưu nguồn: khôi phục trực tiếp bản local.
				organization = current['organization']
				organization['endpoints']['actions/permissions'] = {
					'enabled_repositories': 'all',
					'allowed_actions': 'all',
					'sha_pinning_required': False,
				}
				organization['endpoints'].pop('actions/permissions/repositories')
				organization['endpoints']['actions/permissions/artifact-and-log-retention'][
					'days'
				] = 30
				repository = current['repositories']['.github']
				repository['settings'].update(
					{
						'has_wiki': False,
						'has_projects': False,
						'is_template': True,
						'allow_rebase_merge': False,
					}
				)
				repository['security']['secret_scanning_push_protection'] = 'disabled'
				repository['endpoints']['topics'] = {'names': []}
				self.assertEqual(configuration.syncConfiguredSettings(False), 0)
				write.assert_not_called()
				self.assertEqual(configuration.syncConfiguredSettings(True), 0)
				self.assertEqual(current, captured)
				self.assertEqual(write.call_count, 6)
				self.assertEqual(configuration.syncConfiguredSettings(True), 0)
				self.assertEqual(write.call_count, 6)
				self.assertEqual((root / configuration.CONFIG_NAME).read_bytes(), snapshot)
				self.assertEqual(readLimits.call_count, 2)
				readLimits.assert_called_with(
					'api', 'orgs/TOANQUYNHLLC/actions/permissions/artifact-and-log-retention'
				)
				readCatalog.assert_not_called()

	def testImportWritesPrettierFormattedJson(self):
		# make check chạy Prettier trên github-settings.json: tệp vừa nhập phải đúng định dạng đó ngay, không cần
		# make format. Tệp trong repository đã qua Prettier nên là mẫu chuẩn.
		path = ROOT / configuration.CONFIG_NAME
		self.assertEqual(configuration.jsonText(json.loads(path.read_text())), path.read_text())
		self.assertEqual(
			configuration.jsonText({'short': ['a', 'b'], 'empty': [], 'object': {}}),
			'{\n\t"short": ["a", "b"],\n\t"empty": [],\n\t"object": {}\n}\n',
		)
		# Vượt printWidth (tab rộng 4) hoặc mảng gồm các mảng nhiều phần tử: mỗi phần tử một dòng.
		self.assertEqual(
			configuration.jsonText({'long': ['x' * 45, 'y' * 45]}),
			f'{{\n\t"long": [\n\t\t"{"x" * 45}",\n\t\t"{"y" * 45}"\n\t]\n}}\n',
		)
		self.assertEqual(
			configuration.jsonText(
				{'pairs': [['a', 'b'], ['c', 'd']], 'mixed': [['a', 'b'], ['c']]}
			),
			'{\n\t"pairs": [\n\t\t["a", "b"],\n\t\t["c", "d"]\n\t],\n\t"mixed": [["a", "b"], ["c"]]\n}\n',
		)
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			self.saveConfig(root, self.config)
			with (
				mock.patch.object(github, 'ROOT', root),
				mock.patch.object(github, 'listRepos', return_value=['.github']),
				mock.patch.object(
					configuration,
					'readScope',
					side_effect=lambda repo: (
						(self.config['organization'], {})
						if repo is None
						else (self.config['repositories'][repo], {})
					),
				),
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(configuration.importSettings(), 0)
			written = (root / configuration.CONFIG_NAME).read_text(encoding='utf-8')
			self.assertEqual(written, configuration.jsonText(json.loads(written)))
			self.assertIn('\t"organization_name": "TOANQUYNHLLC",\n', written)

	def testUnknownKeysAndSelectedListsAreRejectedBeforeWriting(self):
		for mutate in (
			lambda config: config['organization']['settings'].update(
				billing_email='toanquynhvn@gmail.com'
			),
			lambda config: config['repositories']['.github']['endpoints'].update(
				{'hooks': {'url': 'https://example.test'}}
			),
			lambda config: config['organization']['endpoints']['actions/permissions'].update(
				enabled_repositories='selected'
			),
			lambda config: config['repositories'].update(
				{'../other': config['repositories']['.github']}
			),
			lambda config: config['organization']['endpoints'][
				'actions/permissions/artifact-and-log-retention'
			].update(days=True),
		):
			with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
				root, config = Path(directory), copy.deepcopy(self.config)
				mutate(config)
				self.saveConfig(root, config)
				with (
					mock.patch.object(github, 'ROOT', root),
					mock.patch.object(github, 'gh') as write,
					self.assertRaises(ValueError),
				):
					configuration.syncConfiguredSettings(True)
				write.assert_not_called()

	def testPreviewAndApplyValidateAllScopesBeforeWriting(self):
		organization = copy.deepcopy(self.config['organization'])
		organization['settings']['blog'] = 'https://old.example.test'
		for apply in (False, True):
			with (
				self.subTest(apply=apply),
				mock.patch.object(
					configuration,
					'readScope',
					side_effect=[
						(organization, {}),
						(
							self.config['repositories']['.github'],
							{'repos/TOANQUYNHLLC/.github/topics': 'HTTP 403'},
						),
					],
				),
				mock.patch.object(github, 'gh') as write,
				self.assertRaises(ValueError),
			):
				configuration.syncConfiguredSettings(apply)
			write.assert_not_called()

	def testPreviewCannotWriteAndIncludesActionsState(self):
		organization = copy.deepcopy(self.config['organization'])
		organization['endpoints']['actions/permissions']['enabled_repositories'] = 'all'
		organization['endpoints']['actions/permissions']['allowed_actions'] = 'all'
		with (
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=[(organization, {}), (self.config['repositories']['.github'], {})],
			),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			self.assertEqual(configuration.syncConfiguredSettings(False), 0)
		write.assert_not_called()
		self.assertIn('"enabled_repositories": "none"', output.getvalue())

	def testPutIncludesRequiredStateAndConfirmsReadBack(self):
		organization = copy.deepcopy(self.config['organization'])
		organization['endpoints']['actions/permissions']['sha_pinning_required'] = True
		with (
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=[
					(organization, {}),
					(self.config['repositories']['.github'], {}),
					(self.config['organization'], {}),
					(self.config['repositories']['.github'], {}),
				],
			),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
		self.assertEqual(write.call_count, 1)
		self.assertEqual(
			write.call_args.args,
			('api', '-X', 'PUT', 'orgs/TOANQUYNHLLC/actions/permissions', '--input', '-'),
		)
		self.assertEqual(
			json.loads(write.call_args.kwargs['stdin']),
			{'enabled_repositories': 'none', 'sha_pinning_required': False},
		)

	def testUnchangedReadBackDoesNotClaimSuccessfulApply(self):
		organization = copy.deepcopy(self.config['organization'])
		organization['settings']['blog'] = 'https://old.example.test'
		with (
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=[(organization, {}), (self.config['repositories']['.github'], {})] * 2,
			),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 1)
		self.assertEqual(write.call_count, 1)
		self.assertIn('chưa xác nhận hoàn tất', output.getvalue())

	def testWebOnlyDifferencesCannotBePatched(self):
		organization = copy.deepcopy(self.config['organization'])
		organization['web_settings']['two_factor_requirement_enabled'] = False
		with (
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=[(organization, {}), (self.config['repositories']['.github'], {})],
			),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 1)
		write.assert_not_called()
		self.assertIn('two_factor_requirement_enabled', output.getvalue())

	def testImportCliRejectsApplyAndDispatchesReadOnly(self):
		module = loadScript('org-setup')
		with (
			mock.patch('sys.argv', ['org-setup.py', 'import-settings', '--apply']),
			contextlib.redirect_stderr(io.StringIO()),
			self.assertRaises(SystemExit),
		):
			module.main()
		with (
			mock.patch('sys.argv', ['org-setup.py', 'import-settings']),
			mock.patch.object(module, 'signedIn', return_value=True),
			mock.patch.object(github, 'listRepos') as listing,
			mock.patch.object(configuration, 'importSettings', return_value=0) as capture,
		):
			self.assertEqual(module.main(), 0)
		listing.assert_not_called()
		capture.assert_called_once_with()

	def testSecurityDefaultsResolveCurrentIdsByName(self):
		current = {
			'security_configurations': [
				{
					'name': 'GitHub recommended',
					'target_type': 'global',
					'default_for_new_repos': 'none',
				}
			]
		}
		wanted = copy.deepcopy(current)
		wanted['security_configurations'][0]['default_for_new_repos'] = 'all'
		plan = []
		with mock.patch.object(
			configuration,
			'securityConfigurationIds',
			return_value={'GitHub recommended': {'id': 731, 'target_type': 'global'}},
		):
			configuration.securityBindingChanges(plan, 'orgs/TOANQUYNHLLC', None, current, wanted)
		self.assertEqual(
			plan,
			[
				(
					'orgs/TOANQUYNHLLC/code-security/configurations/731/defaults',
					'PUT',
					{'default_for_new_repos': 'all'},
					{'default_for_new_repos': 'all'},
				)
			],
		)

	def testSecurityConfigurationAttachmentUsesVerifiedRepositoryId(self):
		plan = []
		with (
			mock.patch.object(
				configuration,
				'securityConfigurationIds',
				return_value={'GitHub recommended': {'id': 731}},
			),
			mock.patch.object(
				github, 'ghJson', return_value={'full_name': 'TOANQUYNHLLC/app', 'id': 946}
			),
		):
			configuration.securityBindingChanges(
				plan,
				'repos/TOANQUYNHLLC/app',
				'app',
				{'security_configuration': None},
				{'security_configuration': 'GitHub recommended'},
			)
		self.assertEqual(
			plan[0][:3],
			(
				'orgs/TOANQUYNHLLC/code-security/configurations/731/attach',
				'POST',
				{'selected_repository_ids': [946], 'scope': 'selected'},
			),
		)

	def testDisabledSecurityUpdatesAreAppliedBeforeAlerts(self):
		config = copy.deepcopy(self.config)
		target = config['repositories']['.github']
		target['endpoints']['vulnerability-alerts']['enabled'] = False
		target['endpoints']['automated-security-fixes']['enabled'] = False
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			self.saveConfig(root, config)
			with (
				mock.patch.object(github, 'ROOT', root),
				mock.patch.object(
					configuration,
					'readScope',
					side_effect=[
						(self.config['organization'], {}),
						(self.config['repositories']['.github'], {}),
						(config['organization'], {}),
						(target, {}),
					],
				),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(configuration.syncConfiguredSettings(True), 0)
		self.assertEqual(
			[call.args for call in write.call_args_list],
			[
				('api', '-X', 'DELETE', 'repos/TOANQUYNHLLC/.github/automated-security-fixes'),
				('api', '-X', 'DELETE', 'repos/TOANQUYNHLLC/.github/vulnerability-alerts'),
			],
		)

	def testEnabledAlertsAreAppliedBeforeSecurityUpdatesRegardlessOfJsonOrder(self):
		for updatesFirst in (False, True):
			with self.subTest(updatesFirst=updatesFirst):
				config = copy.deepcopy(self.config)
				target = config['repositories']['.github']
				endpoints = target['endpoints']
				securityEndpoints = ['vulnerability-alerts', 'automated-security-fixes']
				if updatesFirst:
					securityEndpoints.reverse()
				target['endpoints'] = {
					**{key: {'enabled': True} for key in securityEndpoints},
					**{
						key: value
						for key, value in endpoints.items()
						if key not in securityEndpoints
					},
				}
				current = copy.deepcopy(target)
				for key in securityEndpoints:
					current['endpoints'][key]['enabled'] = False
				writes = []

				def write(*args, current=current, writes=writes):
					suffix = args[-1].rsplit('/', 1)[-1]
					if (
						suffix == 'automated-security-fixes'
						and not current['endpoints']['vulnerability-alerts']['enabled']
					):
						raise RuntimeError('Dependabot alerts chưa bật')
					writes.append(suffix)
					current['endpoints'][suffix]['enabled'] = True

				with tempfile.TemporaryDirectory() as directory:
					root = Path(directory)
					self.saveConfig(root, config)
					with (
						mock.patch.object(github, 'ROOT', root),
						mock.patch.object(
							configuration,
							'readScope',
							side_effect=lambda repo, config=config, current=current: (
								copy.deepcopy(config['organization'] if repo is None else current),
								{},
							),
						),
						mock.patch.object(github, 'gh', side_effect=write),
						contextlib.redirect_stdout(io.StringIO()),
					):
						self.assertEqual(configuration.syncConfiguredSettings(True), 0)
				self.assertEqual(writes, ['vulnerability-alerts', 'automated-security-fixes'])
				self.assertEqual(current, target)

	def testRetentionAboveApiLimitStopsBeforeAnyMutation(self):
		config = copy.deepcopy(self.config)
		config['repositories']['.github']['endpoints'][
			'actions/permissions/artifact-and-log-retention'
		]['days'] = 100
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			self.saveConfig(root, config)
			with (
				mock.patch.object(github, 'ROOT', root),
				mock.patch.object(
					configuration,
					'readScope',
					side_effect=[
						(self.config['organization'], {}),
						(self.config['repositories']['.github'], {}),
					],
				),
				mock.patch.object(github, 'ghJson', return_value={'maximum_allowed_days': 90}),
				mock.patch.object(github, 'gh') as write,
				self.assertRaises(ValueError),
			):
				configuration.syncConfiguredSettings(True)
			write.assert_not_called()

	def testDependencyConflictsCannotBeApplied(self):
		for mutate in (
			lambda data: data['repositories']['.github']['security'].update(
				secret_scanning='disabled'
			),
			lambda data: data['repositories']['.github']['endpoints'][
				'vulnerability-alerts'
			].update(enabled=False),
			lambda data: data['repositories']['.github']['endpoints']['immutable-releases'].update(
				enabled=False
			),
		):
			config = copy.deepcopy(self.config)
			mutate(config)
			with self.subTest(mutate=mutate), self.assertRaises(ValueError):
				configuration.validateDependencies(config)

	def testMergeMessagePatchIncludesRequiredTitleWithoutChangingDiff(self):
		for prefix in ('merge', 'squash_merge'):
			messageKey, titleKey = f'{prefix}_commit_message', f'{prefix}_commit_title'
			for includeTitle in (False, True):
				current = {messageKey: 'BLANK', titleKey: 'PR_TITLE'}
				wanted = {messageKey: 'PR_BODY'}
				if includeTitle:
					wanted[titleKey] = 'PR_TITLE'
				original = copy.deepcopy((current, wanted))
				plan = []
				with self.subTest(prefix=prefix, includeTitle=includeTitle):
					configuration.repositorySettingChanges(
						plan, 'repos/TOANQUYNHLLC/app', current, wanted
					)
					self.assertEqual(
						plan,
						[
							(
								'repos/TOANQUYNHLLC/app',
								'PATCH',
								{messageKey: 'PR_BODY', titleKey: 'PR_TITLE'},
								{messageKey: 'PR_BODY'},
							)
						],
					)
					self.assertEqual((current, wanted), original)

	def testMergeMessagePatchUsesChangedTitleAndKeepsTitleOnlyUpdates(self):
		for prefix, title in (('merge', 'MERGE_MESSAGE'), ('squash_merge', 'COMMIT_OR_PR_TITLE')):
			messageKey, titleKey = f'{prefix}_commit_message', f'{prefix}_commit_title'
			current = {messageKey: 'BLANK', titleKey: 'PR_TITLE'}
			for wanted in (
				{messageKey: 'PR_BODY', titleKey: title},
				{titleKey: title},
				current,
			):
				plan = []
				with self.subTest(prefix=prefix, wanted=wanted):
					configuration.repositorySettingChanges(
						plan, 'repos/TOANQUYNHLLC/app', current, wanted
					)
					if wanted == current:
						self.assertEqual(plan, [])
					else:
						self.assertEqual(plan[0][2], wanted)
						self.assertEqual(plan[0][3], wanted)

	def testMergeMessageCannotPlanWritesWithoutValidTitle(self):
		for prefix in ('merge', 'squash_merge'):
			messageKey, titleKey = f'{prefix}_commit_message', f'{prefix}_commit_title'
			for title in (None, '', 'INVALID', True, []):
				current = {messageKey: 'BLANK', 'has_discussions': False}
				if title is not None:
					current[titleKey] = title
				plan = []
				with (
					self.subTest(prefix=prefix, title=title),
					mock.patch.object(github, 'ghJson') as read,
					self.assertRaisesRegex(ValueError, titleKey),
				):
					configuration.repositorySettingChanges(
						plan,
						'repos/TOANQUYNHLLC/app',
						current,
						{messageKey: 'PR_BODY', 'has_discussions': True},
					)
				self.assertEqual(plan, [])
				read.assert_not_called()

	def testLegacyMergeMessageUpdatesSendRequiredTitleAndConfirmState(self):
		from orgsetup import settings

		for prefix in ('merge', 'squash_merge'):
			messageKey, titleKey = f'{prefix}_commit_message', f'{prefix}_commit_title'
			state = {'full_name': 'TOANQUYNHLLC/app', messageKey: 'BLANK', titleKey: 'PR_TITLE'}
			current = dict(state)

			def writeSettings(*args, stdin=None, state=state, titleKey=titleKey):
				body = json.loads(stdin)
				self.assertIn(titleKey, body)
				state.update(body)

			with (
				self.subTest(prefix=prefix),
				mock.patch.object(github, 'ghJson', return_value=state) as read,
				mock.patch.object(github, 'gh', side_effect=writeSettings) as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				confirmed = settings.updateSettings(
					'repos/TOANQUYNHLLC/app',
					current,
					{messageKey: 'PR_BODY', titleKey: 'PR_TITLE'},
					True,
					'cài đặt repository',
				)
				self.assertEqual(confirmed[messageKey], 'PR_BODY')
				read.assert_called_once_with('api', 'repos/TOANQUYNHLLC/app')
				self.assertEqual(
					json.loads(write.call_args.kwargs['stdin']),
					{messageKey: 'PR_BODY', titleKey: 'PR_TITLE'},
				)

	def testConfiguredMergeMessageUpdatesSendRequiredTitleAndConfirmState(self):
		for prefix in ('merge', 'squash_merge'):
			messageKey, titleKey = f'{prefix}_commit_message', f'{prefix}_commit_title'
			config = copy.deepcopy(self.config)
			target = config['repositories']['.github']
			target['settings'].update({messageKey: 'PR_BODY', titleKey: 'PR_TITLE'})
			current = copy.deepcopy(target)
			current['settings'][messageKey] = 'BLANK'
			self.saveConfig(github.ROOT, config)

			def writeSettings(*args, stdin=None, current=current, titleKey=titleKey):
				body = json.loads(stdin)
				self.assertIn(titleKey, body)
				current['settings'].update(body)

			with (
				self.subTest(prefix=prefix),
				mock.patch.object(
					configuration,
					'readScope',
					side_effect=[
						(config['organization'], {}),
						(current, {}),
						(config['organization'], {}),
						(current, {}),
					],
				),
				mock.patch.object(github, 'gh', side_effect=writeSettings) as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(configuration.syncConfiguredSettings(True), 0)
				write.assert_called_once()
				self.assertEqual(current['settings'][messageKey], 'PR_BODY')
				self.assertEqual(
					json.loads(write.call_args.kwargs['stdin']),
					{messageKey: 'PR_BODY', titleKey: 'PR_TITLE'},
				)

	def testDiscussionsUseDocumentedGraphqlMutation(self):
		plan = []
		with mock.patch.object(
			github, 'ghJson', return_value={'full_name': 'TOANQUYNHLLC/app', 'node_id': 'REPO_ID'}
		):
			configuration.repositorySettingChanges(
				plan,
				'repos/TOANQUYNHLLC/app',
				{'has_discussions': False, 'has_issues': False},
				{'has_discussions': True, 'has_issues': True},
			)
		self.assertEqual(plan[0][:2], ('graphql', 'POST'))
		self.assertEqual(
			plan[0][2]['variables']['input'],
			{'repositoryId': 'REPO_ID', 'hasDiscussionsEnabled': True},
		)
		self.assertEqual(plan[1][:3], ('repos/TOANQUYNHLLC/app', 'PATCH', {'has_issues': True}))

	def testLegacySettingsToggleDiscussionsWithGraphql(self):
		from orgsetup import settings

		for enabled in (True, False):
			state = {
				'full_name': 'TOANQUYNHLLC/app',
				'node_id': 'REPO_ID',
				'has_discussions': not enabled,
				'has_issues': False,
			}

			def writeSettings(*args, stdin=None, state=state):
				body = json.loads(stdin)
				if args[3] == 'graphql':
					state['has_discussions'] = body['variables']['input']['hasDiscussionsEnabled']
				else:
					state.update(body)

			with (
				self.subTest(enabled=enabled),
				mock.patch.object(github, 'ghJson', return_value=state) as read,
				mock.patch.object(github, 'gh', side_effect=writeSettings) as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				confirmed = settings.updateSettings(
					'repos/TOANQUYNHLLC/app',
					{
						'full_name': 'TOANQUYNHLLC/app',
						'has_discussions': not enabled,
						'has_issues': False,
					},
					{'has_discussions': enabled, 'has_issues': True},
					True,
					'cài đặt repository',
				)
			self.assertEqual(confirmed['has_discussions'], enabled)
			self.assertTrue(confirmed['has_issues'])
			self.assertEqual(read.call_count, 2)
			self.assertEqual(write.call_count, 2)
			self.assertEqual(
				write.call_args_list[0].args, ('api', '-X', 'POST', 'graphql', '--input', '-')
			)
			self.assertEqual(
				json.loads(write.call_args_list[0].kwargs['stdin'])['variables']['input'],
				{'repositoryId': 'REPO_ID', 'hasDiscussionsEnabled': enabled},
			)
			self.assertEqual(
				write.call_args_list[1].args,
				('api', '-X', 'PATCH', 'repos/TOANQUYNHLLC/app', '--input', '-'),
			)
			self.assertEqual(
				json.loads(write.call_args_list[1].kwargs['stdin']), {'has_issues': True}
			)

	def testLegacyDiscussionsCannotWriteBeforeRepositoryIdentityIsVerified(self):
		from orgsetup import settings

		with (
			mock.patch.object(
				github,
				'ghJson',
				return_value={'full_name': 'TOANQUYNHLLC/other', 'node_id': 'OTHER_ID'},
			),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaises(ValueError),
		):
			settings.updateSettings(
				'repos/TOANQUYNHLLC/app',
				{'full_name': 'TOANQUYNHLLC/app', 'has_discussions': False, 'has_issues': False},
				{'has_discussions': True, 'has_issues': True},
				True,
				'cài đặt repository',
			)
		write.assert_not_called()

	def testArchiveTransitionKeepsRepositoryWritableDuringOtherUpdates(self):
		for archive in (True, False):
			with self.subTest(archive=archive), tempfile.TemporaryDirectory() as directory:
				root, config = Path(directory), copy.deepcopy(self.config)
				target = config['repositories']['.github']
				target['settings']['archived'] = archive
				permissionPath = 'actions/permissions/workflow'
				target['endpoints'][permissionPath]['can_approve_pull_request_reviews'] = False
				current = copy.deepcopy(self.config['repositories']['.github'])
				current['settings']['archived'] = not archive
				self.saveConfig(root, config)
				archived = not archive
				permissionStates = []

				def writeSettings(
					*args,
					stdin=None,
					permissionPath=permissionPath,
					permissionStates=permissionStates,
				):
					nonlocal archived
					body = json.loads(stdin)
					if args[3] == 'repos/TOANQUYNHLLC/.github' and 'archived' in body:
						archived = body['archived']
					elif args[3] == f'repos/TOANQUYNHLLC/.github/{permissionPath}':
						permissionStates.append(archived)

				with (
					mock.patch.object(github, 'ROOT', root),
					mock.patch.object(
						configuration,
						'readScope',
						side_effect=[
							(config['organization'], {}),
							(current, {}),
							(config['organization'], {}),
							(target, {}),
						],
					),
					mock.patch.object(github, 'gh', side_effect=writeSettings),
					contextlib.redirect_stdout(io.StringIO()),
				):
					self.assertEqual(configuration.syncConfiguredSettings(True), 0)
				self.assertEqual(permissionStates, [False])
				self.assertEqual(archived, archive)

	def testNullableProfileDoesNotCauseLegacyPatch(self):
		from orgsetup import settings

		with mock.patch.object(github, 'gh') as write, contextlib.redirect_stdout(io.StringIO()):
			settings.updateSettings(
				'orgs/TOANQUYNHLLC',
				{'login': 'TOANQUYNHLLC', 'company': None},
				{'company': ''},
				True,
				'hồ sơ',
			)
		write.assert_not_called()

	def testSecurityAssociationDistinguishesDetachedAndPending(self):
		for status in ('detached', 'removed', 'removed_by_enterprise'):
			with (
				self.subTest(status=status),
				mock.patch.object(
					github,
					'ghJson',
					return_value={
						'status': status,
						'configuration': {'name': 'GitHub recommended'},
					},
				),
			):
				self.assertIsNone(configuration.readSecurityConfiguration('repos/TOANQUYNHLLC/app'))
		for status in ('attaching', 'updating', 'failed'):
			with (
				self.subTest(status=status),
				mock.patch.object(
					github,
					'ghJson',
					return_value={
						'status': status,
						'configuration': {'name': 'GitHub recommended'},
					},
				),
				self.assertRaises(ValueError),
			):
				configuration.readSecurityConfiguration('repos/TOANQUYNHLLC/app')

	def testOidcFiltersDerivedSubjectAndSupportsOrganizationInheritance(self):
		suffix = 'actions/oidc/customization/sub'
		with mock.patch.object(github, 'ghJson', return_value=None):
			self.assertEqual(
				configuration.readEndpoint(
					'orgs/TOANQUYNHLLC/' + suffix, suffix, configuration.ORG_ENDPOINTS[suffix][1]
				),
				{},
			)
			with self.assertRaises(TypeError):
				configuration.readEndpoint(
					'repos/TOANQUYNHLLC/app/' + suffix,
					suffix,
					configuration.REPO_ENDPOINTS[suffix][1],
				)
		with mock.patch.object(
			github,
			'ghJson',
			return_value={
				'use_default': True,
				'use_immutable_subject': True,
				'sub_claim_prefix': 'DERIVED_VALUE',
			},
		):
			captured = configuration.readEndpoint(
				'repos/TOANQUYNHLLC/app/' + suffix, suffix, configuration.REPO_ENDPOINTS[suffix][1]
			)
		self.assertEqual(captured, {'use_default': True, 'use_immutable_subject': True})
		self.assertEqual(
			configuration.validateOidc({'use_default': False}, False), {'use_default': False}
		)

	def testOidcRejectsInvalidClaimKeysBeforeWriting(self):
		for claims in (['repo', 'repo'], ['repo/context'], [''], [123]):
			with self.subTest(claims=claims), self.assertRaises(ValueError):
				configuration.validateOidc({'include_claim_keys': claims}, True)
		with self.assertRaises(ValueError):
			configuration.validateOidc({'sub_claim_prefix': 'DERIVED_VALUE'}, True)

	def testOidcCanCreateTemplateWhenOptionalClaimsWereAbsent(self):
		plan = []
		suffix = 'actions/oidc/customization/sub'
		target = {'include_claim_keys': ['repo', 'context'], 'use_immutable_subject': True}
		configuration.addChanges(plan, 'orgs/TOANQUYNHLLC/' + suffix, {}, target, 'PUT', suffix)
		self.assertEqual(plan, [('orgs/TOANQUYNHLLC/' + suffix, 'PUT', target, target)])

	def testOidcUnsetOrganizationTemplateCannotSilentlyClaimRestoration(self):
		organization = copy.deepcopy(self.config['organization'])
		organization['endpoints']['actions/oidc/customization/sub'] = {
			'include_claim_keys': ['repo', 'context']
		}
		with (
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=[(organization, {}), (self.config['repositories']['.github'], {})],
			),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 1)
		write.assert_not_called()
		self.assertIn('OIDC', output.getvalue())

	def runnerGroup(self):
		return {
			'settings': {
				'name': 'Build',
				'visibility': 'all',
				'allows_public_repositories': False,
				'restricted_to_workflows': False,
				'selected_workflows': [],
			},
			'default': False,
			'inherited': False,
			'workflow_restrictions_read_only': False,
			'selected_repositories': [],
		}

	def testResourcePaginationRejectsIncompleteOrChangingTotals(self):
		for pages in (
			[],
			[{'total_count': 2, 'items': [1]}],
			[{'total_count': True, 'items': []}],
			[{'total_count': 2, 'items': [1]}, {'total_count': 3, 'items': [2]}],
		):
			with (
				self.subTest(pages=pages),
				mock.patch.object(github, 'ghJson', return_value=pages),
				self.assertRaises(ValueError),
			):
				resources.readCollection('orgs/TOANQUYNHLLC/example', 'items')
		with mock.patch.object(
			github,
			'ghJson',
			return_value=[{'total_count': 2, 'items': [1]}, {'total_count': 2, 'items': [2]}],
		) as read:
			self.assertEqual(resources.readCollection('orgs/TOANQUYNHLLC/example', 'items'), [1, 2])
		self.assertIn('--paginate', read.call_args.args)

	def testInstalledAppsExcludeInstallationMetadataAndCredentials(self):
		with mock.patch.object(
			resources,
			'readCollection',
			return_value=[
				{
					'app_slug': 'example',
					'access_tokens_url': 'SECRET_VALUE',
					'account': {'private_data': 'SECRET_VALUE'},
					'id': 12,
				}
			],
		):
			self.assertEqual(resources.installedApps(), ['example'])

	def testLegacyOrgSettingsReadsAppsSeparatelyInsteadOfAssumingRootField(self):
		from orgsetup import settings

		for observed, expected in (
			(['example'], None),
			([], 'installed_apps: []'),
			(RuntimeError('HTTP 403'), 'không đọc được danh sách GitHub Apps'),
		):
			with (
				self.subTest(observed=observed),
				mock.patch.object(
					settings, 'ORG_WEB_ONLY_SETTINGS', {'installed_apps': ['example']}
				),
				# settings đọc nguồn cài đặt thật lúc import: ghim về bản cố định của test.
				mock.patch.object(
					settings, 'ORG_SETTINGS', self.config['organization']['settings']
				),
				mock.patch.object(settings, 'readActions', return_value=[]),
				mock.patch.object(settings, 'syncActions'),
				mock.patch.object(
					github,
					'ghJson',
					return_value=dict(
						self.config['organization']['settings'], login='TOANQUYNHLLC'
					),
				),
				mock.patch.object(
					resources,
					'installedApps',
					**(
						{'side_effect': observed}
						if isinstance(observed, Exception)
						else {'return_value': observed}
					),
				),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()) as output,
			):
				settings.syncOrgSettings(True)
			write.assert_not_called()
			if expected:
				self.assertIn(expected, output.getvalue())
			else:
				self.assertNotIn('installed_apps:', output.getvalue())

	def testRunnerGroupRepositoryReadsOverlapAndFailWithoutPartialResults(self):
		details, expected = {}, []
		for index in reversed(range(8)):
			group = self.runnerGroup()
			group['settings'].update(name=f'Build{index}', visibility='selected')
			details[group['settings']['name']] = {
				**group['settings'],
				**{key: group[key] for key in resources.RUNNER_METADATA},
				'id': index + 1,
			}
			group['selected_repositories'] = ['TOANQUYNHLLC/app', 'TOANQUYNHLLC/web']
			expected.append(group)
		default = self.runnerGroup()
		default['settings']['name'] = 'Default'
		default['default'] = True
		details['Default'] = {
			**default['settings'],
			**{key: default[key] for key in resources.RUNNER_METADATA},
			'id': 9,
		}
		expected.append(default)
		original = copy.deepcopy(details)
		for failure in (False, True):
			barrier = threading.Barrier(4, timeout=3)
			secondFinished = threading.Event()
			lock = threading.Lock()
			active, peak, completed = 0, 0, []

			def readRepositories(
				endpoint,
				key,
				failure=failure,
				barrier=barrier,
				secondFinished=secondFinished,
				lock=lock,
				completed=completed,
			):
				nonlocal active, peak
				groupId = int(endpoint.split('/')[-2])
				self.assertEqual(key, 'repositories')
				self.assertLess(groupId, 9)
				with lock:
					active += 1
					peak = max(peak, active)
				try:
					barrier.wait()
					if groupId == 8:
						self.assertTrue(secondFinished.wait(timeout=3))
					if groupId == 7 and failure:
						raise RuntimeError('HTTP 403')
					return [
						{'id': 109, 'full_name': 'TOANQUYNHLLC/web'},
						{'id': 99, 'full_name': 'TOANQUYNHLLC/app'},
					]
				finally:
					with lock:
						active -= 1
						completed.append(groupId)
					if groupId == 7:
						secondFinished.set()

			with (
				self.subTest(failure=failure),
				mock.patch.object(resources, 'runnerGroupDetails', return_value=details),
				mock.patch.object(
					resources, 'readCollection', side_effect=readRepositories
				) as read,
			):
				if failure:
					with self.assertRaisesRegex(RuntimeError, 'HTTP 403'):
						resources.readRunnerGroups()
				else:
					self.assertEqual(
						resources.readRunnerGroups(),
						sorted(expected, key=lambda group: group['settings']['name']),
					)
			self.assertEqual(read.call_count, 8)
			self.assertEqual(peak, 4)
			self.assertEqual(active, 0)
			self.assertCountEqual(completed, range(1, 9))
			self.assertGreater(completed.index(8), completed.index(7))
			self.assertEqual(details, original)

	def testRunnerGroupImportUsesRepositoryNamesAndExcludesRuntimeIds(self):
		target = self.runnerGroup()
		target['settings']['visibility'] = 'selected'
		item = {
			**target['settings'],
			**{key: target[key] for key in resources.RUNNER_METADATA},
			'id': 12,
			'runners_url': 'UNMANAGED_VALUE',
		}
		with (
			mock.patch.object(resources, 'runnerGroupDetails', return_value={'Build': item}),
			mock.patch.object(
				resources,
				'readCollection',
				return_value=[{'id': 99, 'full_name': 'TOANQUYNHLLC/app'}],
			),
		):
			groups = resources.readRunnerGroups()
		target['selected_repositories'] = ['TOANQUYNHLLC/app']
		self.assertEqual(groups, [target])
		self.assertNotIn('UNMANAGED_VALUE', json.dumps(groups))

	def testRunnerGroupPaginationRejectsDuplicateIdsWhenTotalsMatch(self):
		pages = [
			{'total_count': 2, 'runner_groups': [{'id': 12, 'name': 'Build'}]},
			{'total_count': 2, 'runner_groups': [{'id': 12, 'name': 'Renamed'}]},
		]
		with (
			mock.patch.object(github, 'ghJson', return_value=pages),
			self.assertRaises(ValueError),
		):
			resources.runnerGroupDetails()
		pages[1]['runner_groups'][0]['id'] = 13
		with mock.patch.object(github, 'ghJson', return_value=pages):
			self.assertEqual(
				resources.runnerGroupDetails(),
				{'Build': {'id': 12, 'name': 'Build'}, 'Renamed': {'id': 13, 'name': 'Renamed'}},
			)

	def testRepositoryResolverRejectsDuplicateIds(self):
		items = [
			{'full_name': 'TOANQUYNHLLC/app', 'id': 99},
			{'full_name': 'TOANQUYNHLLC/web', 'id': 99},
		]
		names = ['TOANQUYNHLLC/web', 'TOANQUYNHLLC/app']
		with mock.patch.object(github, 'ghList', return_value=items), self.assertRaises(ValueError):
			resources.repositoryIds(names)
		items[1]['id'] = 100
		original = copy.deepcopy(items)
		with mock.patch.object(github, 'ghList', return_value=items):
			self.assertEqual(resources.repositoryIds(names), [100, 99])
		self.assertEqual(items, original)

	def testEmptyRepositorySelectionDoesNotReadCatalog(self):
		with mock.patch.object(github, 'ghList') as read:
			self.assertEqual(resources.repositoryIds([]), [])
		read.assert_not_called()

	def testRunnerGroupPlanSharesCatalogAndRefreshesNextPlan(self):
		current = self.runnerGroup()
		target = copy.deepcopy(current)
		target['settings']['visibility'] = 'selected'
		target['selected_repositories'] = ['TOANQUYNHLLC/web', 'TOANQUYNHLLC/app']
		created = copy.deepcopy(target)
		created['settings']['name'] = 'Deploy'
		created['selected_repositories'] = ['TOANQUYNHLLC/app']
		original = copy.deepcopy([current, target, created])
		with (
			mock.patch.object(resources, 'runnerGroupDetails', return_value={'Build': {'id': 12}}),
			mock.patch.object(
				github,
				'ghList',
				side_effect=[
					[
						{'full_name': 'TOANQUYNHLLC/app', 'id': 99},
						{'full_name': 'TOANQUYNHLLC/web', 'id': 100},
					],
					[
						{'full_name': 'TOANQUYNHLLC/app', 'id': 199},
						{'full_name': 'TOANQUYNHLLC/web', 'id': 200},
					],
				],
			) as read,
		):
			for index, expected in enumerate(([100, 99], [200, 199]), start=1):
				plan = []
				resources.runnerGroupChanges(plan, [current], [target, created])
				self.assertEqual(read.call_count, index)
				self.assertEqual(plan[1][2], {'selected_repository_ids': expected})
				self.assertEqual(plan[2][2]['selected_repository_ids'], [expected[1]])
		self.assertEqual([current, target, created], original)

	def testSecurityDefaultPlanReadsConfigurationCatalogOnce(self):
		current = {
			'security_configurations': [
				{'name': name, 'target_type': 'organization', 'default_for_new_repos': 'none'}
				for name in ('Baseline', 'Strict')
			]
		}
		wanted = copy.deepcopy(current)
		for item in wanted['security_configurations']:
			item['default_for_new_repos'] = 'all'
		with mock.patch.object(
			github,
			'ghList',
			return_value=[
				{'name': 'Baseline', 'target_type': 'organization', 'id': 11},
				{'name': 'Strict', 'target_type': 'organization', 'id': 12},
			],
		) as read:
			plan = []
			configuration.securityBindingChanges(plan, 'orgs/TOANQUYNHLLC', None, current, wanted)
		read.assert_called_once()
		self.assertEqual(
			[path for path, _, _, _ in plan],
			[
				'orgs/TOANQUYNHLLC/code-security/configurations/11/defaults',
				'orgs/TOANQUYNHLLC/code-security/configurations/12/defaults',
			],
		)

	def testChangedSecurityCatalogBlocksAllConfiguredWrites(self):
		current = copy.deepcopy(self.config['organization'])
		current['security_configurations'] = [
			{'name': name, 'target_type': 'organization', 'default_for_new_repos': 'none'}
			for name in ('Baseline', 'Strict')
		]
		wanted = copy.deepcopy(self.config)
		wanted['organization'] = copy.deepcopy(current)
		for item in wanted['organization']['security_configurations']:
			item['default_for_new_repos'] = 'all'
		self.saveConfig(github.ROOT, wanted)
		for changed in (None, {'name': 'Strict', 'target_type': 'global', 'id': 12}):
			catalog = [{'name': 'Baseline', 'target_type': 'organization', 'id': 11}]
			if changed is not None:
				catalog.append(changed)
			with (
				self.subTest(changed=changed),
				mock.patch.object(configuration, 'readScope', return_value=(current, {})) as scope,
				mock.patch.object(github, 'ghList', return_value=catalog) as read,
				mock.patch.object(github, 'gh') as write,
				self.assertRaisesRegex(ValueError, 'cấu hình bảo mật Strict'),
			):
				configuration.syncConfiguredSettings(True)
			scope.assert_called_once_with(None)
			read.assert_called_once()
			write.assert_not_called()

	def testConfiguredPlanSharesRepositoryCatalogAcrossPoliciesAndRunnerGroups(self):
		wanted = copy.deepcopy(self.config)
		endpoints = wanted['organization']['endpoints']
		endpoints['actions/permissions'].update(
			enabled_repositories='selected', allowed_actions='all'
		)
		endpoints['settings/immutable-releases']['enforced_repositories'] = 'selected'
		for suffix in (
			'actions/permissions/repositories',
			'settings/immutable-releases/repositories',
		):
			endpoints[suffix] = {'selected_repositories': ['TOANQUYNHLLC/.github']}
		wanted['repositories']['.github']['endpoints']['immutable-releases']['enabled'] = True
		group = self.runnerGroup()
		group['settings']['visibility'] = 'selected'
		group['selected_repositories'] = ['TOANQUYNHLLC/.github']
		wanted['organization']['runner_groups'] = [group]
		self.saveConfig(github.ROOT, wanted)
		with (
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=[
					(self.config['organization'], {}),
					(self.config['repositories']['.github'], {}),
					(wanted['organization'], {}),
					(wanted['repositories']['.github'], {}),
				],
			),
			mock.patch.object(
				github, 'ghList', return_value=[{'full_name': 'TOANQUYNHLLC/.github', 'id': 99}]
			) as catalog,
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
		catalog.assert_called_once_with('orgs/TOANQUYNHLLC/repos?type=all')
		bodies = {
			call.args[3]: json.loads(call.kwargs['stdin'])
			for call in write.call_args_list
			if 'stdin' in call.kwargs
		}
		for path in (
			'orgs/TOANQUYNHLLC/actions/runner-groups',
			'orgs/TOANQUYNHLLC/actions/permissions/repositories',
			'orgs/TOANQUYNHLLC/settings/immutable-releases/repositories',
		):
			self.assertEqual(bodies[path]['selected_repository_ids'], [99])

	def testRepositoryCacheRejectsInvalidCatalogAndUnknownNames(self):
		cache = {}
		with mock.patch.object(
			github,
			'ghList',
			side_effect=[
				[
					{'full_name': 'TOANQUYNHLLC/app', 'id': 99},
					{'full_name': 'TOANQUYNHLLC/web', 'id': 99},
				],
				[{'full_name': 'TOANQUYNHLLC/app', 'id': 100}],
			],
		) as read:
			with self.assertRaises(ValueError):
				resources.repositoryIds(['TOANQUYNHLLC/app'], cache)
			self.assertEqual(cache, {})
			self.assertEqual(resources.repositoryIds(['TOANQUYNHLLC/app'], cache), [100])
			with self.assertRaises(ValueError):
				resources.repositoryIds(['TOANQUYNHLLC/missing'], cache)
			self.assertEqual(read.call_count, 2)

	def testConfiguredVerificationReadsFreshRepositoryCatalog(self):
		wanted = copy.deepcopy(self.config)
		endpoints = wanted['organization']['endpoints']
		endpoints['actions/permissions'].update(
			enabled_repositories='selected', allowed_actions='all'
		)
		endpoints['actions/permissions/repositories'] = {
			'selected_repositories': ['TOANQUYNHLLC/.github']
		}
		self.saveConfig(github.ROOT, wanted)
		with (
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=[
					(self.config['organization'], {}),
					(self.config['repositories']['.github'], {}),
					(self.config['organization'], {}),
					(self.config['repositories']['.github'], {}),
				],
			),
			mock.patch.object(
				github,
				'ghList',
				side_effect=[
					[{'full_name': 'TOANQUYNHLLC/.github', 'id': 99}],
					[{'full_name': 'TOANQUYNHLLC/.github', 'id': 199}],
				],
			) as catalog,
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 1)
		self.assertEqual(catalog.call_count, 2)
		self.assertEqual(write.call_count, 2)
		body = json.loads(write.call_args_list[-1].kwargs['stdin'])
		self.assertEqual(body, {'selected_repository_ids': [99]})
		self.assertIn('chưa xác nhận hoàn tất', output.getvalue())

	def testSecurityDefaultsRequireMatchingCatalogIdentity(self):
		configurationData = {'name': 'Baseline', 'id': 12, 'target_type': 'organization'}
		for defaultIdentity in (
			{'name': 'Baseline'},
			dict(configurationData, id=13),
			dict(configurationData, id=True),
			dict(configurationData, target_type='global'),
			dict(configurationData, name='Other'),
		):
			with (
				self.subTest(defaultIdentity=defaultIdentity),
				mock.patch.object(
					github,
					'ghList',
					side_effect=[
						[configurationData],
						[{'configuration': defaultIdentity, 'default_for_new_repos': 'all'}],
					],
				),
				self.assertRaisesRegex(ValueError, 'cấu hình bảo mật mặc định'),
			):
				configuration.readSecurityDefaults()

	def testSecurityDefaultsKeepUnselectedConfigurationsWithoutIds(self):
		configurations = [
			{'name': 'Baseline', 'id': 12, 'target_type': 'organization'},
			{'name': 'GitHub recommended', 'id': 17, 'target_type': 'global'},
		]
		for defaults in (
			[],
			[{'configuration': configurations[1], 'default_for_new_repos': 'public'}],
		):
			with (
				self.subTest(defaults=defaults),
				mock.patch.object(github, 'ghList', side_effect=[configurations, defaults]),
			):
				self.assertEqual(
					configuration.readSecurityDefaults(),
					[
						{
							'name': 'Baseline',
							'target_type': 'organization',
							'default_for_new_repos': 'none',
						},
						{
							'name': 'GitHub recommended',
							'target_type': 'global',
							'default_for_new_repos': 'public' if defaults else 'none',
						},
					],
				)

	def testMismatchedSecurityDefaultsBlockAllConfiguredWrites(self):
		wanted = copy.deepcopy(self.config)
		wanted['repositories'] = {}
		organization = wanted['organization']
		configurationData = {'name': 'Baseline', 'id': 12, 'target_type': 'organization'}
		organization['security_configurations'] = [
			{'name': 'Baseline', 'target_type': 'organization', 'default_for_new_repos': 'none'}
		]
		data = dict(organization['settings'], **organization['web_settings'], login=github.ORG)
		data['description'] = 'Mô tả cần cập nhật'

		def readCatalog(endpoint):
			if endpoint.endswith('/defaults'):
				return [
					{
						'configuration': dict(configurationData, id=13),
						'default_for_new_repos': 'all',
					}
				]
			return [configurationData]

		with (
			mock.patch.object(configuration, 'readConfig', return_value=wanted),
			mock.patch.object(github, 'ghJson', return_value=data),
			mock.patch.object(github, 'ghList', side_effect=readCatalog),
			mock.patch.object(
				configuration,
				'readEndpoint',
				side_effect=lambda path, suffix, fields: organization['endpoints'][suffix],
			),
			mock.patch.object(
				resources, 'readRunnerGroups', return_value=organization['runner_groups']
			),
			mock.patch.object(
				resources,
				'installedApps',
				return_value=organization['web_settings']['installed_apps'],
			),
			mock.patch.object(github, 'gh') as write,
			self.assertRaisesRegex(ValueError, 'code-security.*dừng trước khi ghi'),
		):
			configuration.syncConfiguredSettings(apply=True)
		write.assert_not_called()

	def testSecurityConfigurationResolverRequiresUniqueIdsAndNonemptyNames(self):
		first = {'id': 12, 'name': 'Baseline', 'target_type': 'organization'}
		for second in (
			dict(first, name='Other'),
			dict(first, id=13),
			dict(first, id=13, name=''),
		):
			with (
				self.subTest(second=second),
				mock.patch.object(github, 'ghList', return_value=[first, second]),
				self.assertRaises(ValueError),
			):
				configuration.securityConfigurationIds()
		second = dict(first, id=13, name='Other')
		with mock.patch.object(github, 'ghList', return_value=[first, second]):
			self.assertEqual(
				configuration.securityConfigurationIds(), {'Baseline': first, 'Other': second}
			)

	def testRunnerGroupRepositoryImportRequiresCompleteUniqueIdentity(self):
		target = self.runnerGroup()
		target['settings']['visibility'] = 'selected'
		item = {
			**target['settings'],
			**{key: target[key] for key in resources.RUNNER_METADATA},
			'id': 12,
		}
		for repositories in (
			[{'full_name': 'TOANQUYNHLLC/app'}],
			[{'full_name': 'TOANQUYNHLLC/app', 'id': True}],
			[{'full_name': 'TOANQUYNHLLC/app', 'id': 0}],
			[
				{'full_name': 'TOANQUYNHLLC/app', 'id': 99},
				{'full_name': 'TOANQUYNHLLC/web', 'id': 99},
			],
		):
			with (
				self.subTest(repositories=repositories),
				mock.patch.object(resources, 'runnerGroupDetails', return_value={'Build': item}),
				mock.patch.object(resources, 'readCollection', return_value=repositories),
				self.assertRaises(ValueError),
			):
				resources.readRunnerGroups()

	def testAmbiguousResourceIdsStopAllConfiguredWrites(self):
		for resource in ('runner', 'repository', 'security'):
			config = copy.deepcopy(self.config)
			before = copy.deepcopy(config['organization'])
			before['settings']['blog'] = 'https://cu.example'
			group = self.runnerGroup()
			if resource == 'runner':
				before['runner_groups'] = [copy.deepcopy(group)]
				group['settings']['allows_public_repositories'] = True
				config['organization']['runner_groups'] = [group]
				items = [{'id': 12, 'name': 'Build'}, {'id': 12, 'name': 'Renamed'}]
			elif resource == 'repository':
				group['settings']['visibility'] = 'selected'
				group['selected_repositories'] = ['TOANQUYNHLLC/app', 'TOANQUYNHLLC/web']
				config['organization']['runner_groups'] = [group]
				items = [{'id': 99, 'full_name': name} for name in group['selected_repositories']]
			else:
				default = {
					'name': 'Baseline',
					'target_type': 'organization',
					'default_for_new_repos': 'all',
				}
				config['organization']['security_configurations'] = [default]
				before['security_configurations'] = [dict(default, default_for_new_repos='none')]
				items = [
					{'id': 12, 'name': name, 'target_type': 'organization'}
					for name in ('Baseline', 'Other')
				]
			self.saveConfig(github.ROOT, config)
			with (
				self.subTest(resource=resource),
				mock.patch.object(
					configuration,
					'readScope',
					side_effect=[(before, {}), (config['repositories']['.github'], {})],
				),
				mock.patch.object(resources, 'readCollection', return_value=items),
				mock.patch.object(github, 'ghList', return_value=items),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
				self.assertRaises(ValueError),
			):
				configuration.syncConfiguredSettings(True)
			write.assert_not_called()

	def testRunnerGroupOrderDoesNotCreateChanges(self):
		for inherited in (False, True):
			for readOnly in (False, True):
				with self.subTest(inherited=inherited, readOnly=readOnly):
					current = self.runnerGroup()
					current['inherited'] = inherited
					current['workflow_restrictions_read_only'] = readOnly
					current['settings'].update(
						visibility='selected',
						restricted_to_workflows=True,
						selected_workflows=[
							'TOANQUYNHLLC/app/.github/workflows/build.yml@refs/heads/main',
							'TOANQUYNHLLC/app/.github/workflows/deploy.yml@refs/heads/main',
						],
					)
					current['selected_repositories'] = ['TOANQUYNHLLC/app', 'TOANQUYNHLLC/web']
					target = copy.deepcopy(current)
					target['settings']['selected_workflows'].reverse()
					target['selected_repositories'].reverse()
					original = copy.deepcopy([current, target])
					plan = []
					with (
						mock.patch.object(resources, 'runnerGroupDetails') as lookup,
						mock.patch.object(resources, 'repositoryIds') as resolve,
					):
						resources.runnerGroupChanges(plan, [current], [target])
					self.assertEqual(plan, [])
					self.assertEqual([current, target], original)
					lookup.assert_not_called()
					resolve.assert_not_called()

	def testRunnerGroupReadOnlyWorkflowChangesRemainBlocked(self):
		current = self.runnerGroup()
		current['workflow_restrictions_read_only'] = True
		current['settings']['restricted_to_workflows'] = True
		workflow = 'TOANQUYNHLLC/app/.github/workflows/build.yml@refs/heads/main'
		other = 'TOANQUYNHLLC/app/.github/workflows/deploy.yml@refs/heads/main'
		current['settings']['selected_workflows'] = [workflow]
		for workflows in ([], [other], [workflow, other]):
			with self.subTest(workflows=workflows):
				target = copy.deepcopy(current)
				target['settings']['selected_workflows'] = workflows
				plan = []
				with (
					mock.patch.object(resources, 'runnerGroupDetails') as lookup,
					self.assertRaisesRegex(ValueError, 'không có quyền sửa'),
				):
					resources.runnerGroupChanges(plan, [current], [target])
				self.assertEqual(plan, [])
				lookup.assert_not_called()

	def testRunnerGroupReadOnlyWorkflowOrderAllowsOtherSettings(self):
		current = self.runnerGroup()
		current['workflow_restrictions_read_only'] = True
		current['settings'].update(
			restricted_to_workflows=True,
			selected_workflows=[
				'TOANQUYNHLLC/app/.github/workflows/build.yml@refs/heads/main',
				'TOANQUYNHLLC/app/.github/workflows/deploy.yml@refs/heads/main',
			],
		)
		target = copy.deepcopy(current)
		target['settings']['selected_workflows'].reverse()
		target['settings']['allows_public_repositories'] = True
		plan = []
		with mock.patch.object(resources, 'runnerGroupDetails', return_value={'Build': {'id': 12}}):
			resources.runnerGroupChanges(plan, [current], [target])
		self.assertEqual(
			plan,
			[
				(
					'orgs/TOANQUYNHLLC/actions/runner-groups/12',
					'PATCH',
					{'name': 'Build', 'allows_public_repositories': True},
					{'allows_public_repositories': True},
				)
			],
		)

	def testRunnerGroupApplyAcceptsReorderedReadback(self):
		wanted = copy.deepcopy(self.config)
		group = self.runnerGroup()
		group['settings'].update(
			restricted_to_workflows=True,
			selected_workflows=[
				'TOANQUYNHLLC/app/.github/workflows/deploy.yml@refs/heads/main',
				'TOANQUYNHLLC/app/.github/workflows/build.yml@refs/heads/main',
			],
		)
		wanted['organization']['runner_groups'] = [group]
		self.saveConfig(github.ROOT, wanted)
		before = copy.deepcopy(wanted['organization'])
		before['runner_groups'][0]['settings'].update(
			restricted_to_workflows=False, selected_workflows=[]
		)
		after = copy.deepcopy(wanted['organization'])
		after['runner_groups'][0]['settings']['selected_workflows'].reverse()
		with (
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=[
					(before, {}),
					(wanted['repositories']['.github'], {}),
					(after, {}),
					(wanted['repositories']['.github'], {}),
				],
			) as reader,
			mock.patch.object(resources, 'runnerGroupDetails', return_value={'Build': {'id': 12}}),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
		reader.assert_has_calls([mock.call(None), mock.call('.github')] * 2)
		write.assert_called_once()
		self.assertEqual(
			write.call_args.args[:4],
			('api', '-X', 'PATCH', 'orgs/TOANQUYNHLLC/actions/runner-groups/12'),
		)
		body = json.loads(write.call_args.kwargs['stdin'])
		self.assertEqual(
			body,
			{
				'name': 'Build',
				'restricted_to_workflows': True,
				'selected_workflows': group['settings']['selected_workflows'],
			},
		)
		self.assertIn('khớp', output.getvalue())
		self.assertNotIn('chưa xác nhận hoàn tất', output.getvalue())

	def testRunnerGroupWorkflowOnlyUpdateIncludesRestrictionAndConfirmsState(self):
		wanted = copy.deepcopy(self.config)
		group = self.runnerGroup()
		group['settings'].update(
			restricted_to_workflows=True,
			selected_workflows=['TOANQUYNHLLC/app/.github/workflows/deploy.yml@refs/heads/main'],
		)
		wanted['organization']['runner_groups'] = [group]
		self.saveConfig(github.ROOT, wanted)
		current = copy.deepcopy(wanted['organization'])
		current['runner_groups'][0]['settings']['selected_workflows'] = [
			'TOANQUYNHLLC/app/.github/workflows/build.yml@refs/heads/main'
		]
		original = copy.deepcopy(group)

		def writeSettings(*args, stdin=None):
			body = json.loads(stdin)
			state = current['runner_groups'][0]['settings']
			state.update({key: value for key, value in body.items() if key != 'selected_workflows'})
			# Hợp đồng REST: danh sách workflow chỉ áp dụng khi cờ trong request được bật.
			if body.get('restricted_to_workflows') is True:
				state['selected_workflows'] = body['selected_workflows']

		with (
			mock.patch.object(
				configuration,
				'readScope',
				side_effect=[
					(current, {}),
					(wanted['repositories']['.github'], {}),
					(current, {}),
					(wanted['repositories']['.github'], {}),
				],
			),
			mock.patch.object(resources, 'runnerGroupDetails', return_value={'Build': {'id': 12}}),
			mock.patch.object(github, 'gh', side_effect=writeSettings) as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			write.assert_called_once()
			self.assertEqual(
				json.loads(write.call_args.kwargs['stdin']),
				{
					'name': 'Build',
					'restricted_to_workflows': True,
					'selected_workflows': original['settings']['selected_workflows'],
				},
			)
		self.assertEqual(current['runner_groups'], [original])
		self.assertEqual(group, original)

	def testRunnerGroupEnablingRestrictionIncludesRetainedWorkflows(self):
		current = self.runnerGroup()
		current['settings']['selected_workflows'] = [
			'TOANQUYNHLLC/app/.github/workflows/build.yml@refs/heads/main'
		]
		target = copy.deepcopy(current)
		target['settings']['restricted_to_workflows'] = True
		plan = []
		with mock.patch.object(resources, 'runnerGroupDetails', return_value={'Build': {'id': 12}}):
			resources.runnerGroupChanges(plan, [current], [target])
		self.assertEqual(
			plan[0][2],
			{
				'name': 'Build',
				'restricted_to_workflows': True,
				'selected_workflows': target['settings']['selected_workflows'],
			},
		)
		self.assertEqual(plan[0][3], {'restricted_to_workflows': True})

	def testRunnerGroupCannotChangeIgnoredWorkflowListBeforeAnyWrite(self):
		for wasRestricted in (False, True):
			for workflows in (
				[],
				['TOANQUYNHLLC/app/.github/workflows/deploy.yml@refs/heads/main'],
			):
				current = self.runnerGroup()
				current['settings'].update(
					restricted_to_workflows=wasRestricted,
					selected_workflows=[
						'TOANQUYNHLLC/app/.github/workflows/build.yml@refs/heads/main'
					],
				)
				target = copy.deepcopy(current)
				previous = copy.deepcopy(self.config)
				target['settings'].update(
					restricted_to_workflows=False, selected_workflows=workflows
				)
				previous['organization']['runner_groups'] = [target]
				self.saveConfig(github.ROOT, previous)
				before = copy.deepcopy(previous['organization'])
				before['settings']['blog'] = 'https://cu.example'
				before['runner_groups'] = [current]
				with (
					self.subTest(wasRestricted=wasRestricted, workflows=workflows),
					mock.patch.object(configuration, 'readScope', return_value=(before, {})),
					mock.patch.object(resources, 'runnerGroupDetails') as lookup,
					mock.patch.object(github, 'gh') as write,
					contextlib.redirect_stdout(io.StringIO()),
					self.assertRaisesRegex(ValueError, 'restricted_to_workflows'),
				):
					configuration.syncConfiguredSettings(True)
				lookup.assert_not_called()
				write.assert_not_called()

	def testRunnerGroupDisablingRestrictionKeepsStoredWorkflows(self):
		for wasRestricted in (False, True):
			current = self.runnerGroup()
			current['settings'].update(
				restricted_to_workflows=wasRestricted,
				selected_workflows=['TOANQUYNHLLC/app/.github/workflows/build.yml@refs/heads/main'],
			)
			target = copy.deepcopy(current)
			if wasRestricted:
				target['settings']['restricted_to_workflows'] = False
				changes = {'restricted_to_workflows': False}
			else:
				target['settings']['allows_public_repositories'] = True
				changes = {'allows_public_repositories': True}
			plan = []
			with (
				self.subTest(wasRestricted=wasRestricted),
				mock.patch.object(
					resources, 'runnerGroupDetails', return_value={'Build': {'id': 12}}
				),
			):
				resources.runnerGroupChanges(plan, [current], [target])
				self.assertEqual(plan[0][2], dict(changes, name='Build'))
				self.assertEqual(plan[0][3], changes)

	def testRunnerGroupCreationCannotSendIgnoredWorkflowList(self):
		target = self.runnerGroup()
		target['settings']['selected_workflows'] = [
			'TOANQUYNHLLC/app/.github/workflows/build.yml@refs/heads/main'
		]
		plan = []
		with (
			mock.patch.object(resources, 'runnerGroupDetails') as lookup,
			mock.patch.object(resources, 'repositoryIds') as resolve,
			self.assertRaisesRegex(ValueError, 'restricted_to_workflows'),
		):
			resources.runnerGroupChanges(plan, [], [target])
		self.assertEqual(plan, [])
		lookup.assert_not_called()
		resolve.assert_not_called()

	def testRunnerGroupChangingToSelectedExplicitlyClearsRetainedRepositories(self):
		current = self.runnerGroup()
		target = copy.deepcopy(current)
		target['settings']['visibility'] = 'selected'
		plan = []
		with (
			mock.patch.object(resources, 'runnerGroupDetails', return_value={'Build': {'id': 12}}),
			mock.patch.object(github, 'ghList', return_value=[]),
		):
			resources.runnerGroupChanges(plan, [current], [target])
		self.assertEqual(
			plan[0][:3],
			(
				'orgs/TOANQUYNHLLC/actions/runner-groups/12',
				'PATCH',
				{'name': 'Build', 'visibility': 'selected'},
			),
		)
		self.assertEqual(
			plan[1][:3],
			(
				'orgs/TOANQUYNHLLC/actions/runner-groups/12/repositories',
				'PUT',
				{'selected_repository_ids': []},
			),
		)

	def testRunnerGroupCreationResolvesRepositoryIdsAndKeepsOtherGroups(self):
		target = self.runnerGroup()
		target['settings']['visibility'] = 'selected'
		target['selected_repositories'] = ['TOANQUYNHLLC/app']
		plan = []
		with mock.patch.object(
			github, 'ghList', return_value=[{'full_name': 'TOANQUYNHLLC/app', 'id': 99}]
		):
			resources.runnerGroupChanges(
				plan, [self.config['organization']['runner_groups'][0]], [target]
			)
		self.assertEqual(len(plan), 1)
		self.assertEqual(plan[0][1], 'POST')
		self.assertEqual(plan[0][2]['selected_repository_ids'], [99])
		self.assertNotIn('default', plan[0][2])

	def testRunnerGroupRejectsInheritedChangesAndUnresolvedRepositories(self):
		current = self.runnerGroup()
		current['inherited'] = True
		target = copy.deepcopy(current)
		target['settings']['allows_public_repositories'] = True
		with self.assertRaises(ValueError):
			resources.runnerGroupChanges([], [current], [target])
		for name in ('OTHER/app', 'TOANQUYNHLLC/..', 'TOANQUYNHLLC/'):
			group = self.runnerGroup()
			group['settings']['visibility'] = 'selected'
			group['selected_repositories'] = [name]
			with self.subTest(name=name), self.assertRaises(ValueError):
				resources.validateRunnerGroups([group])
		with mock.patch.object(github, 'ghList', return_value=[]), self.assertRaises(ValueError):
			resources.repositoryIds(['TOANQUYNHLLC/app'])


if __name__ == '__main__':
	unittest.main()
