"""Kiểm tra khôi phục mạng, vai trò team và IP allow list mà không ghi GitHub thật."""

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

from orgsetup import catalog, configuration, enterprise, github, localdata

BASE = 'orgs/TOANQUYNHLLC'


def ipPage(entries, total=None, nextPage=False, cursor=None):
	return {
		'data': {
			'organization': {
				'id': 'O_org',
				'login': github.ORG,
				'ipAllowListEnabledSetting': 'DISABLED',
				'ipAllowListForInstalledAppsEnabledSetting': 'DISABLED',
				'ipAllowListEntries': {
					'totalCount': len(entries) if total is None else total,
					'nodes': entries,
					'pageInfo': {'hasNextPage': nextPage, 'endCursor': cursor},
				},
			}
		}
	}


def ipEntry(value='192.0.2.0/24', identity='I_entry'):
	return {
		'id': identity,
		'allowListValue': value,
		'name': 'Office',
		'isActive': True,
		'owner': {'__typename': 'Organization', 'id': 'O_org', 'login': github.ORG},
	}


class EnterpriseSettingsTest(unittest.TestCase):
	def setUp(self):
		self.directory = tempfile.TemporaryDirectory()
		self.addCleanup(self.directory.cleanup)
		patch = mock.patch.dict(os.environ, {'ORGSETUP_PRIVATE_DIR': self.directory.name})
		patch.start()
		self.addCleanup(patch.stop)
		localdata.resetCapture()
		self.addCleanup(localdata.resetCapture)

	def savePolicy(self, policy):
		with contextlib.redirect_stdout(io.StringIO()):
			localdata.saveCapturedValues(
				{'organization': {'collections': {'ip_allow_list': [policy]}}, 'repositories': {}}
			)

	def testNetworkSnapshotFiltersMetadataAndKeepsExternalCloudReference(self):
		data = [
			{
				'id': 'NC_old',
				'name': 'Office-Network',
				'compute_service': 'actions',
				'network_settings_ids': ['NS_cloud'],
				'created_on': 'DATE',
				'credentials': 'PRIVATE',
			}
		]
		with mock.patch.object(enterprise.resources, 'readCollection', return_value=data) as read:
			items, ids = enterprise.readDetails(BASE, 'network_configurations')
		read.assert_called_once_with(
			f'{BASE}/settings/network-configurations', 'network_configurations'
		)
		self.assertEqual(ids, {'Office-Network': 'NC_old'})
		self.assertEqual(items[0]['network_settings_ids'], ['NS_cloud'])
		self.assertNotIn('created_on', items[0])
		self.assertNotIn('PRIVATE', json.dumps(items))

	def testNetworkCreateUsesVerifiedCloudResourceAndUpdateUsesFreshStringId(self):
		before = {'name': 'Office', 'compute_service': 'none', 'network_settings_ids': ['NS_cloud']}
		target = dict(before, compute_service='actions')
		for current, method, endpoint in (
			([], 'POST', f'{BASE}/settings/network-configurations'),
			([before], 'PATCH', f'{BASE}/settings/network-configurations/NC_fresh'),
		):
			with (
				self.subTest(method=method),
				mock.patch.object(
					enterprise, 'readDetails', return_value=(current, {'Office': 'NC_fresh'})
				),
				mock.patch.object(github, 'ghJson', return_value={'id': 'NS_cloud'}) as read,
			):
				plan = []
				enterprise.collectionChanges(
					plan, BASE, 'network_configurations', current, [target], {}
				)
			read.assert_called_once_with('api', f'{BASE}/settings/network-settings/NS_cloud')
			self.assertEqual(plan[0][:3], (endpoint, method, target))

	def testNetworkMissingCloudWrongIdentityAndReadOnlyServiceBlockWrites(self):
		target = {
			'name': 'Office',
			'compute_service': 'actions',
			'network_settings_ids': ['NS_cloud'],
		}
		for changed, response in (
			(dict(target, network_settings_ids=[]), {}),
			(target, {'id': 'WRONG'}),
			(dict(target, compute_service='codespaces'), {}),
		):
			with (
				self.subTest(target=changed),
				mock.patch.object(enterprise, 'readDetails', return_value=([], {})),
				mock.patch.object(github, 'ghJson', return_value=response),
				self.assertRaises(ValueError),
			):
				enterprise.collectionChanges([], BASE, 'network_configurations', [], [changed], {})

	def testNetworkConcurrentModificationAndDuplicateIdsAreRejected(self):
		before = {'name': 'Office', 'compute_service': 'none', 'network_settings_ids': ['NS_cloud']}
		with (
			mock.patch.object(
				enterprise,
				'readDetails',
				return_value=([dict(before, compute_service='actions')], {'Office': 'NC'}),
			),
			self.assertRaises(ValueError),
		):
			enterprise.collectionChanges(
				[],
				BASE,
				'network_configurations',
				[before],
				[dict(before, network_settings_ids=['NS_new'])],
				{},
			)
		with (
			mock.patch.object(
				enterprise.resources,
				'readCollection',
				return_value=[dict(before, id='NC'), dict(before, name='Other', id='NC')],
			),
			self.assertRaises(ValueError),
		):
			enterprise.readDetails(BASE, 'network_configurations')

	def testRoleImportCapturesDirectAssignmentsWithoutUserProfiles(self):
		role = {
			'id': 19,
			'name': 'security_manager',
			'source': 'Predefined',
			'base_role': 'read',
			'permissions': ['view_alerts'],
			'organization': {'PRIVATE_PROFILE': 'PRIVATE'},
		}
		teams = [
			{
				'slug': 'direct',
				'assignment': 'direct',
				'type': 'organization',
				'members': ['PRIVATE_USER'],
			},
			{'slug': 'parent', 'assignment': 'indirect', 'type': 'organization'},
			{'slug': 'mixed', 'assignment': 'mixed', 'type': 'organization'},
		]
		with (
			mock.patch.object(enterprise.resources, 'readCollection', return_value=[role]),
			mock.patch.object(github, 'ghList', return_value=teams),
		):
			items, ids = enterprise.readDetails(BASE, 'organization_roles')
		self.assertEqual(items[0]['teams'], ['direct', 'mixed'])
		self.assertEqual(ids, {'security_manager': 19})
		self.assertNotIn('PRIVATE', json.dumps(items))

	def testRoleRestoreUsesFreshIdAndRejectsDifferentPermissionDefinition(self):
		before = {
			'name': 'security_manager',
			'source': 'Predefined',
			'base_role': 'read',
			'permissions': ['view_alerts'],
			'teams': [],
		}
		target = dict(before, teams=['admins'])
		plan = []
		with (
			mock.patch.object(
				enterprise, 'readDetails', return_value=([before], {'security_manager': 27})
			),
			mock.patch.object(github, 'ghJson', return_value={'slug': 'admins'}),
		):
			enterprise.collectionChanges(plan, BASE, 'organization_roles', [before], [target], {})
		self.assertEqual(plan[0][:3], (f'{BASE}/organization-roles/teams/admins/27', 'PUT', None))
		with (
			mock.patch.object(
				enterprise, 'readDetails', return_value=([before], {'security_manager': 27})
			),
			self.assertRaises(ValueError),
		):
			enterprise.collectionChanges(
				[],
				BASE,
				'organization_roles',
				[before],
				[dict(target, permissions=['write_everything'])],
				{},
			)

	def testNewTeamCreationPrecedesRoleAssignmentWithoutRequiringOldId(self):
		team = {
			'name': 'Admins',
			'slug': 'admins',
			'privacy': 'closed',
			'notification_setting': 'notifications_enabled',
			'parent_team_slug': None,
			'repositories': {},
		}
		role = {
			'name': 'security_manager',
			'source': 'Predefined',
			'base_role': 'read',
			'permissions': [],
			'teams': [],
		}
		current = {'collections': {'teams': [], 'organization_roles': [role]}}
		wanted = {
			'collections': {'organization_roles': [dict(role, teams=['admins'])], 'teams': [team]}
		}
		with (
			mock.patch.object(
				enterprise, 'readDetails', return_value=([role], {'security_manager': 27})
			),
			mock.patch.object(github, 'ghJson') as read,
		):
			plan = []
			catalog.collectionChanges(plan, BASE, current, wanted, {})
		read.assert_not_called()
		self.assertEqual(plan[0][:2], (f'{BASE}/teams', 'POST'))
		self.assertEqual(plan[1][:2], (f'{BASE}/organization-roles/teams/admins/27', 'PUT'))

	def testRoleUnknownAssignmentCannotBeAssumedDirect(self):
		role = {
			'id': 1,
			'name': 'Role',
			'source': 'Organization',
			'base_role': 'read',
			'permissions': [],
		}
		with (
			mock.patch.object(enterprise.resources, 'readCollection', return_value=[role]),
			mock.patch.object(
				github, 'ghList', return_value=[{'slug': 'admins', 'type': 'organization'}]
			),
			self.assertRaises(ValueError),
		):
			enterprise.readDetails(BASE, 'organization_roles')

	def testTeamResponseWithDifferentSlugStopsBeforeGrantingRole(self):
		config = copy.deepcopy(configuration.readConfig(ROOT))
		config['unavailable'] = {}
		team = {
			'name': 'Admins',
			'slug': 'admins',
			'privacy': 'closed',
			'notification_setting': 'notifications_enabled',
			'parent_team_slug': None,
			'repositories': {},
		}
		role = {
			'name': 'security_manager',
			'source': 'Predefined',
			'base_role': 'read',
			'permissions': [],
			'teams': [],
		}
		wanted = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'collections': {'teams': [team], 'organization_roles': [dict(role, teams=['admins'])]},
		}
		current = dict(wanted, collections={'teams': [], 'organization_roles': [role]})
		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(
				configuration, 'configuredScopes', return_value=[(None, wanted, (current, {}))]
			),
			mock.patch.object(
				enterprise, 'readDetails', return_value=([role], {'security_manager': 27})
			),
			mock.patch.object(
				github, 'gh', return_value='{"id":19,"name":"Admins","slug":"different"}'
			) as write,
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaises(ValueError),
		):
			configuration.syncConfiguredSettings(True)
		write.assert_called_once()

	def testIpSnapshotReadsAllPagesKeepsAddressAndNameOutsideGit(self):
		with mock.patch.object(
			github,
			'ghJson',
			side_effect=[
				ipPage([ipEntry()], total=2, nextPage=True, cursor='next'),
				ipPage([ipEntry('2001:db8::/32', 'I_v6')], total=2),
			],
		) as read:
			items, ids = enterprise.readIpAllowList(BASE)
		self.assertEqual(len(items[0]['entries']), 2)
		self.assertEqual(len(ids), 3)
		self.assertIn('after=next', read.call_args.args)
		self.savePolicy(items[0])
		self.assertNotIn('192.0.2', json.dumps(items))
		self.assertNotIn('Office', json.dumps(items))
		self.assertEqual(
			localdata.privateValue(items[0]['entries'][0]['value_source']), '192.0.2.0/24'
		)

	def testIpUnavailableAndPartialPagesNeverBecomeDisabledPolicy(self):
		for data in (
			{'errors': [{'message': 'Forbidden'}], 'data': {'organization': None}},
			ipPage([], total=1),
		):
			with (
				self.subTest(data=data),
				mock.patch.object(github, 'ghJson', return_value=data),
				self.assertRaises(ValueError),
			):
				enterprise.readIpAllowList(BASE)
		with mock.patch.object(
			github, 'ghJson', return_value={'errors': [{'message': 'Forbidden'}]}
		):
			collections, _, unavailable = catalog.readCollections(BASE, ['ip_allow_list'])
		self.assertEqual(collections, {})
		self.assertIn(f'{BASE}/ip-allow-list', unavailable)

	def testIpInheritedEntryOrChangingPolicyBlocksSnapshot(self):
		entry = ipEntry()
		entry['owner'] = {'__typename': 'Enterprise'}
		with (
			mock.patch.object(github, 'ghJson', return_value=ipPage([entry])),
			self.assertRaises(ValueError),
		):
			enterprise.readIpAllowList(BASE)
		second = ipPage([ipEntry('198.51.100.0/24', 'I_second')], total=2)
		second['data']['organization']['ipAllowListEnabledSetting'] = 'ENABLED'
		with (
			mock.patch.object(
				github,
				'ghJson',
				side_effect=[ipPage([ipEntry()], total=2, nextPage=True, cursor='next'), second],
			),
			self.assertRaises(ValueError),
		):
			enterprise.readIpAllowList(BASE)

	def testIpRestoreCreatesManagedEntryAndEnablesPolicyAfterRepositoryUpdates(self):
		with mock.patch.object(github, 'ghJson', return_value=ipPage([ipEntry()])):
			targets, _ = enterprise.readIpAllowList(BASE)
		target = dict(targets[0], enabled=True)
		self.savePolicy(target)
		before = {'enabled': False, 'apps_enabled': False, 'entries': []}
		with mock.patch.object(
			enterprise, 'readIpAllowList', return_value=([before], {'owner': 'O_fresh'})
		):
			plan = []
			enterprise.ipAllowListChanges(plan, BASE, [before], [target])
		self.assertNotIn('192.0.2', json.dumps(plan))
		body = localdata.resolveBody(plan[0][2])
		self.assertEqual(body['variables']['input']['allowListValue'], '192.0.2.0/24')
		self.assertEqual(body['variables']['input']['ownerId'], 'O_fresh')
		plan.append(('repos/TOANQUYNHLLC/app', 'PATCH', {'has_wiki': False}, {'has_wiki': False}))
		ordered = enterprise.finalizePlan(plan)
		self.assertEqual(ordered[-2][0], 'repos/TOANQUYNHLLC/app')
		self.assertIn('updateIpAllowListEnabledSetting', ordered[-1][2]['query'])

	def testIpUpdateUsesFreshEntryIdAndDisableRunsFirst(self):
		with mock.patch.object(github, 'ghJson', return_value=ipPage([ipEntry()])):
			policies, ids = enterprise.readIpAllowList(BASE)
		before = dict(policies[0], enabled=True)
		self.savePolicy(before)
		target = copy.deepcopy(before)
		target['enabled'] = False
		target['entries'][0]['is_active'] = False
		ids[next(key for key in ids if key != 'owner')] = 'I_fresh'
		with mock.patch.object(enterprise, 'readIpAllowList', return_value=([before], ids)):
			plan = []
			enterprise.ipAllowListChanges(plan, BASE, [before], [target])
		self.assertEqual(plan[0][2]['variables']['input']['settingValue'], 'DISABLED')
		self.assertEqual(plan[1][2]['variables']['input']['ipAllowListEntryId'], 'I_fresh')
		self.assertNotIn('deleteIpAllowListEntry', json.dumps(plan))

	def testInvalidPrivateIpAndCrossScopeReferencesDoNotLeak(self):
		with self.assertRaises(ValueError) as caught:
			enterprise.validateNetwork('PRIVATE_INVALID_ADDRESS')
		self.assertNotIn('PRIVATE_INVALID_ADDRESS', str(caught.exception))
		policy = {
			'enabled': False,
			'apps_enabled': False,
			'entries': [
				{
					'value_source': 'orgs/OTHER/ip-allow-list/value#' + 'a' * 32,
					'name_source': f'{BASE}/ip-allow-list/name#' + 'b' * 32,
					'is_active': True,
				}
			],
		}
		with self.assertRaises(ValueError):
			catalog.validateReferenceScope(BASE, 'ip_allow_list', [policy])

	def testGraphqlErrorsStopBeforeEnablingPolicyAndVerification(self):
		config = copy.deepcopy(configuration.readConfig(ROOT))
		config['unavailable'] = {}
		before = {'enabled': False, 'apps_enabled': False, 'entries': []}
		with mock.patch.object(github, 'ghJson', return_value=ipPage([ipEntry()])):
			policies, _ = enterprise.readIpAllowList(BASE)
		self.savePolicy(policies[0])
		config['organization']['collections'] = {'ip_allow_list': [dict(policies[0], enabled=True)]}
		config['organization'].pop('observed', None)
		current = copy.deepcopy(config['organization'])
		current['collections']['ip_allow_list'] = [before]
		output = io.StringIO()
		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(
				configuration,
				'configuredScopes',
				return_value=[(None, config['organization'], (current, {}))],
			),
			mock.patch.object(
				enterprise, 'readIpAllowList', return_value=([before], {'owner': 'O_fresh'})
			),
			mock.patch.object(
				github,
				'gh',
				return_value=json.dumps(
					{'errors': [{'message': 'PRIVATE_SERVER_ECHO'}], 'data': None}
				),
			) as write,
			contextlib.redirect_stdout(output),
			self.assertRaises(RuntimeError) as caught,
		):
			configuration.syncConfiguredSettings(True)
		write.assert_called_once()
		self.assertNotIn('PRIVATE_SERVER_ECHO', str(caught.exception))
		self.assertNotIn('192.0.2', output.getvalue())


if __name__ == '__main__':
	unittest.main()
