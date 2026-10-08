"""Kiểm tra nhập/áp dụng cài đặt: giữ false, lọc bí mật, chặn ghi khi đọc thiếu và xác nhận sau áp dụng."""

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

from orgsetup import configuration, github, resources


def baselineConfig():
	"""Nguồn cài đặt cố định cho test: cấu trúc trường lấy từ github-settings.json thật (theo kịp hợp đồng API),
	giá trị mà các test giả định được ghim tại đây. Tệp thật đổi sau mỗi lần make org-import — bật Actions, thêm
	repository… — nên test không được dựa vào giá trị của nó."""
	config = configuration.readConfig(ROOT)
	organization, repository = config['organization'], config['repositories']['.github']
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
	for scope in (organization, repository):
		for suffix in configuration.SELECTED_ENDPOINTS:
			scope['endpoints'].pop(suffix, None)
		scope['endpoints']['actions/permissions/workflow'] = {
			'default_workflow_permissions': 'read',
			'can_approve_pull_request_reviews': True,
		}
	organization['endpoints'].update(
		{
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
		folder = tempfile.TemporaryDirectory()
		self.addCleanup(folder.cleanup)
		self.saveConfig(Path(folder.name), self.config)
		patcher = mock.patch.object(github, 'ROOT', Path(folder.name))
		patcher.start()
		self.addCleanup(patcher.stop)

	def saveConfig(self, root, config):
		(root / configuration.CONFIG_NAME).write_text(json.dumps(config), encoding='utf-8')

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
			return_value={'GitHub recommended': {'id': 731}},
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
			with (
				self.subTest(enabled=enabled),
				mock.patch.object(
					github,
					'ghJson',
					return_value={'full_name': 'TOANQUYNHLLC/app', 'node_id': 'REPO_ID'},
				),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				settings.updateSettings(
					'repos/TOANQUYNHLLC/app',
					{'has_discussions': not enabled, 'has_issues': False},
					{'has_discussions': enabled, 'has_issues': True},
					True,
					'cài đặt repository',
				)
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
				{'has_discussions': False, 'has_issues': False},
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
				'orgs/TOANQUYNHLLC', {'company': None}, {'company': ''}, True, 'hồ sơ'
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
					github, 'ghJson', return_value=self.config['organization']['settings']
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
