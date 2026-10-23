"""Kiểm tra bản khôi phục bảo vệ nhánh kiểu cũ và phạm vi áp dụng được chọn rõ."""

import contextlib
import copy
import io
import json
import unittest
from unittest import mock

try:
	from testsupport import ROOT, loadScript
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript

from orgsetup import branches, catalog, configuration, github

BASE = 'repos/TOANQUYNHLLC/.github'


def connection(nodes, count=None, cursor=None):
	return {
		'totalCount': len(nodes) if count is None else count,
		'nodes': nodes,
		'pageInfo': {'hasNextPage': cursor is not None, 'endCursor': cursor},
	}


def apiRule(pattern='main'):
	item = dict.fromkeys(branches.BOOLEAN_FIELDS, False)
	item.update(
		id='B_old',
		pattern=pattern,
		requiredApprovingReviewCount=0,
		requiredDeploymentEnvironments=[],
		requiredStatusChecks=[{'context': 'CI', 'app': {'id': 'APP_ci'}}],
	)
	for field in branches.ACTOR_FIELDS.values():
		item[field] = connection([])
	return item


def apiPage(rules, total=None, cursor=None):
	return {
		'data': {
			'repository': {
				'id': 'R_fresh',
				'nameWithOwner': 'TOANQUYNHLLC/.github',
				'branchProtectionRules': connection(rules, total, cursor),
			}
		}
	}


class BranchSettingsTest(unittest.TestCase):
	def testCaptureKeepsWildcardAppsAndOpaqueActorIdsWithoutProfiles(self):
		rule = apiRule('release/*')
		rule['creator'] = {'login': 'PRIVATE_PROFILE'}
		rule['pushAllowances'] = connection(
			[{'actor': {'__typename': 'Team', 'id': 'T_admins', 'login': 'PRIVATE_PROFILE'}}]
		)
		with mock.patch.object(github, 'ghJson', return_value=apiPage([rule])):
			items, ids = branches.readDetails(BASE)
		self.assertEqual(ids, {'release/*': 'B_old', None: 'R_fresh'})
		self.assertEqual(items[0]['requiredStatusChecks'], [{'context': 'CI', 'appId': 'APP_ci'}])
		self.assertEqual(items[0]['pushActorIds'], ['T_admins'])
		self.assertNotIn('PRIVATE_PROFILE', json.dumps(items))
		self.assertNotIn('B_old', json.dumps(items))

	def testActorConnectionReadsEveryPage(self):
		rule = apiRule()
		rule['pushAllowances'] = connection(
			[{'actor': {'__typename': 'User', 'id': 'U_one'}}], 2, 'next'
		)
		second = {
			'data': {
				'node': {
					'pushAllowances': connection(
						[{'actor': {'__typename': 'Team', 'id': 'T_two'}}], 2
					)
				}
			}
		}
		with mock.patch.object(github, 'ghJson', side_effect=[apiPage([rule]), second]) as read:
			items, _ = branches.readDetails(BASE)
		self.assertEqual(items[0]['pushActorIds'], ['T_two', 'U_one'])
		self.assertIn('after=next', read.call_args.args)

	def testMissingActorPageAndRepeatedCursorBlockImport(self):
		for nodes, total, cursor in (([], 1, None), ([{'actor': None}], 1, None)):
			with self.subTest(total=total), self.assertRaises(ValueError):
				branches.readActors(connection(nodes, total, cursor), 'B_old', 'pushAllowances')
		page = connection([], 1, 'again')
		with (
			mock.patch.object(
				github, 'ghJson', return_value={'data': {'node': {'pushAllowances': page}}}
			),
			self.assertRaises(ValueError),
		):
			branches.readActors(page, 'B_old', 'pushAllowances')

	def testRepositoryIdentityWrongTotalAndDuplicatePatternsAreRejected(self):
		wrong = apiPage([])
		wrong['data']['repository']['nameWithOwner'] = 'OTHER/.github'
		for data in (wrong, apiPage([], total=1), apiPage([apiRule(), apiRule()])):
			with (
				self.subTest(data=data),
				mock.patch.object(github, 'ghJson', return_value=data),
				self.assertRaises(ValueError),
			):
				branches.readDetails(BASE)

	def testPatternNamedRepositoryCannotOverwriteRepositoryIdentity(self):
		with mock.patch.object(github, 'ghJson', return_value=apiPage([apiRule('repository')])):
			items, ids = branches.readDetails(BASE)
		self.assertEqual(ids['repository'], 'B_old')
		self.assertEqual(ids[None], 'R_fresh')
		self.assertEqual(items[0]['pattern'], 'repository')

	def testCreateAndUpdateUseFreshIdentitiesAndPreserveFalseValues(self):
		with mock.patch.object(github, 'ghJson', return_value=apiPage([apiRule()])):
			items, _ = branches.readDetails(BASE)
		target = dict(items[0], requiresCommitSignatures=True)
		for live, ids, identityField, expected in (
			([], {None: 'R_new'}, 'repositoryId', 'R_new'),
			(items, {None: 'R_new', 'main': 'B_new'}, 'branchProtectionRuleId', 'B_new'),
		):
			with (
				self.subTest(identityField=identityField),
				mock.patch.object(branches, 'readDetails', return_value=(live, ids)),
			):
				plan = []
				branches.collectionChanges(plan, BASE, live, [target])
			values = plan[0][2]['variables']['input']
			self.assertEqual(values[identityField], expected)
			self.assertFalse(values['allowsForcePushes'])
			self.assertTrue(values['requiresCommitSignatures'])
			self.assertEqual(values['requiredStatusChecks'][0]['appId'], 'APP_ci')

	def testConcurrentBranchProtectionChangesBlockMutation(self):
		with mock.patch.object(github, 'ghJson', return_value=apiPage([apiRule()])):
			items, _ = branches.readDetails(BASE)
		with (
			mock.patch.object(
				branches,
				'readDetails',
				return_value=(
					[dict(items[0], allowsForcePushes=True)],
					{'main': 'B_new', None: 'R_new'},
				),
			),
			self.assertRaises(ValueError),
		):
			branches.collectionChanges(
				[], BASE, items, [dict(items[0], requiresCommitSignatures=True)]
			)

	def testRoundTripReadbackIsRequiredAndSecondApplyDoesNotWrite(self):
		with mock.patch.object(github, 'ghJson', return_value=apiPage([apiRule()])):
			items, _ = branches.readDetails(BASE)
		target = dict(items[0], requiresCommitSignatures=True)
		config = copy.deepcopy(configuration.readConfig(ROOT))
		config['unavailable'] = {}
		config['organization'] = {'settings': {}, 'web_settings': {}, 'endpoints': {}}
		wanted = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'collections': {'branch_protection': [target]},
		}
		config['repositories'] = {'.github': wanted}
		live = []
		before = json.dumps(config)

		def readScopes(source):
			return [
				(None, source['organization'], (source['organization'], {})),
				(
					'.github',
					source['repositories']['.github'],
					(dict(wanted, collections={'branch_protection': copy.deepcopy(live)}), {}),
				),
			]

		def write(*args, stdin):
			values = json.loads(stdin)['variables']['input']
			self.assertEqual(values.pop('repositoryId'), 'R_new')
			live.append(values)
			return json.dumps({'data': {'createBranchProtectionRule': {'clientMutationId': None}}})

		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(configuration, 'configuredScopes', side_effect=readScopes),
			mock.patch.object(
				branches,
				'readDetails',
				side_effect=lambda base: (copy.deepcopy(live), {None: 'R_new', 'main': 'B_new'}),
			),
			mock.patch.object(github, 'gh', side_effect=write) as mutation,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
		mutation.assert_called_once()
		self.assertEqual(json.dumps(config), before)

	def testSelectedGroupsKeepOriginalSnapshotAndDoNotHideSelectedFailures(self):
		config = copy.deepcopy(configuration.readConfig(ROOT))
		config['unavailable'] = {
			f'orgs/{github.ORG}/hooks': 'HTTP 404',
			f'orgs/{github.ORG}/settings/network-configurations': 'HTTP 404',
		}
		before = json.dumps(config)
		selected = configuration.selectSettingGroups(config, ['labels'])
		self.assertEqual(selected['unavailable'], {})
		self.assertEqual(set(selected['repositories']['.github']['collections']), {'labels'})
		self.assertEqual(
			selected['organization'], {'settings': {}, 'web_settings': {}, 'endpoints': {}}
		)
		self.assertEqual(json.dumps(config), before)
		selected = configuration.selectSettingGroups(config, ['network_configurations'])
		self.assertEqual(
			selected['unavailable'],
			{f'orgs/{github.ORG}/settings/network-configurations': 'HTTP 404'},
		)

	def testIncompleteGraphqlMutationPayloadStopsBeforeFollowingWrites(self):
		with mock.patch.object(github, 'ghJson', return_value=apiPage([apiRule()])):
			items, _ = branches.readDetails(BASE)
		wanted = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'collections': {
				'branch_protection': items,
				'labels': [{'name': 'example', 'color': '000000'}],
			},
		}
		current = dict(wanted, collections={'branch_protection': [], 'labels': []})
		config = copy.deepcopy(configuration.readConfig(ROOT))
		config['unavailable'] = {}
		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(
				configuration, 'configuredScopes', return_value=[('.github', wanted, (current, {}))]
			),
			mock.patch.object(branches, 'readDetails', return_value=([], {None: 'R_new'})),
			mock.patch.object(catalog, 'readDetails', return_value=([], {})),
			mock.patch.object(
				github, 'gh', return_value='{"data":{"createBranchProtectionRule":{}}}'
			) as write,
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaises(ValueError),
		):
			configuration.syncConfiguredSettings(True)
		write.assert_called_once()

	def testExplicitSelectionReadsBackSameScopeWithoutWritingOtherGroups(self):
		config = copy.deepcopy(configuration.readConfig(ROOT))
		config['unavailable'] = {f'orgs/{github.ORG}/hooks': 'HTTP 404'}
		config['repositories'] = {
			'.github': {
				'settings': {},
				'web_settings': {},
				'endpoints': {},
				'collections': {'labels': [{'name': 'example', 'color': '000000'}]},
			}
		}
		live = []

		def scopes(source):
			wanted = source['repositories']['.github']
			return [
				(
					None,
					source['organization'],
					(source['organization'], {f'orgs/{github.ORG}/hooks': 'HTTP 404'}),
				),
				(
					'.github',
					wanted,
					(dict(wanted, collections={'labels': copy.deepcopy(live)}), {}),
				),
			]

		def write(*args, stdin):
			self.assertEqual(args[3], f'{BASE}/labels')
			live.append(json.loads(stdin))
			return '{}'

		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(configuration, 'configuredScopes', side_effect=scopes),
			mock.patch.object(catalog, 'readDetails', return_value=([], {})),
			mock.patch.object(github, 'gh', side_effect=write) as mutation,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True, only=['labels']), 0)
		mutation.assert_called_once()
		self.assertIn(f'orgs/{github.ORG}/hooks', config['unavailable'])

	def testOnlyFlagRejectsWrongCommandAndInvalidGroupBeforeLogin(self):
		module = loadScript('org-setup')
		for arguments in (
			['import-settings', '--only', 'labels'],
			['local-settings', '--only', 'UNKNOWN'],
		):
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
			mock.patch(
				'sys.argv',
				['org-setup.py', 'local-settings', '--only', 'labels', '--only', 'rulesets'],
			),
			mock.patch.object(module, 'signedIn', return_value=True),
			mock.patch.object(configuration, 'syncConfiguredSettings', return_value=0) as sync,
		):
			self.assertEqual(module.main(), 0)
		sync.assert_called_once_with(False, only=['labels', 'rulesets'])


if __name__ == '__main__':
	unittest.main()
