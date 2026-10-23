"""Kiểm tra hosted runner và liên kết mạng khả chuyển của nhóm runner."""

import contextlib
import copy
import io
import json
import unittest
from unittest import mock

try:
	from testsupport import ROOT
except ModuleNotFoundError:
	from scripts.testsupport import ROOT

from orgsetup import catalog, configuration, enterprise, github, hosted, resources

BASE = 'orgs/TOANQUYNHLLC'


def runnerGroup(name='Compute'):
	return {
		'settings': {
			'name': name,
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


def targetRunner(**changes):
	return dict(
		{
			'name': 'build-linux',
			'runner_group': 'Compute',
			'image': {'source': 'github', 'id': 'ubuntu-latest'},
			'size': '4-core',
			'maximum_runners': 2,
			'enable_static_ip': False,
			'image_gen': False,
		},
		**changes,
	)


def apiRunner(**changes):
	return dict(
		{
			'name': 'build-linux',
			'id': 14,
			'runner_group_id': 7,
			'image_details': {
				'source': 'github',
				'id': 'ubuntu-latest',
				'size_gb': 80,
				'version': 'latest',
			},
			'machine_size_details': {'id': '4-core', 'cpu_cores': 4},
			'maximum_runners': 2,
			'public_ip_enabled': False,
			'image_gen': False,
			'status': 'Ready',
			'public_ips': [{'prefix': 'PRIVATE_IP'}],
			'last_active_on': 'METADATA',
		},
		**changes,
	)


class HostedSettingsTest(unittest.TestCase):
	def testCaptureExcludesPublicAddressesAndIdsAndStoresGroupName(self):
		with (
			mock.patch.object(resources, 'readCollection', return_value=[apiRunner()]),
			mock.patch.object(resources, 'runnerGroupDetails', return_value={'Compute': {'id': 7}}),
		):
			items, ids = hosted.readDetails(BASE)
		self.assertEqual(items, [targetRunner()])
		self.assertEqual(ids, {'build-linux': 14})
		self.assertNotIn('PRIVATE_IP', json.dumps(items))

	def testCustomImageUsesNameAndFreshIdIncludingVersion(self):
		item = apiRunner(image_details={'source': 'custom', 'id': '43', 'version': '1.2'})
		with (
			mock.patch.object(
				resources,
				'readCollection',
				side_effect=[[item], [{'name': 'Build Image', 'id': 43}]],
			),
			mock.patch.object(resources, 'runnerGroupDetails', return_value={'Compute': {'id': 7}}),
		):
			items, _ = hosted.readDetails(BASE)
		self.assertEqual(
			items[0]['image'], {'name': 'Build Image', 'source': 'custom', 'version': '1.2'}
		)
		with (
			mock.patch.object(
				resources, 'runnerGroupDetails', return_value={'Compute': {'id': 81}}
			),
			mock.patch.object(hosted, 'customImages', return_value={'Build Image': '96'}),
		):
			body = hosted.resolvePlanBody(BASE, items[0], 'PATCH')
		self.assertEqual(body['runner_group_id'], 81)
		self.assertEqual(body['image_id'], '96')
		self.assertEqual(body['image_version'], '1.2')
		self.assertNotIn('image', body)

	def testCreateAndUpdateResolveCurrentGroupIdAndDoNotDeleteOtherPools(self):
		current = [targetRunner()]
		wanted = [targetRunner(maximum_runners=3), targetRunner(name='second')]
		with (
			mock.patch.object(hosted, 'readDetails', return_value=(current, {'build-linux': 92})),
			mock.patch.object(
				resources, 'runnerGroupDetails', return_value={'Compute': {'id': 27}}
			),
			mock.patch.object(
				resources,
				'readCollection',
				side_effect=lambda path, key: (
					[{'id': '4-core'}] if key == 'machine_specs' else [{'id': 'ubuntu-latest'}]
				),
			),
		):
			plan = []
			hosted.collectionChanges(plan, BASE, current, wanted, {})
			body = hosted.resolvePlanBody(BASE, plan[0][2], plan[0][1])
		self.assertEqual([step[1] for step in plan], ['PATCH', 'POST'])
		self.assertTrue(plan[0][0].endswith('/92'))
		self.assertEqual(body['runner_group_id'], 27)
		self.assertEqual(body['image_id'], 'ubuntu-latest')
		self.assertEqual(body['maximum_runners'], 3)
		plan = []
		hosted.collectionChanges(plan, BASE, [*current, targetRunner(name='outside')], current, {})
		self.assertEqual(plan, [])

	def testUnknownGroupImageSizeAndPendingProvisioningBlock(self):
		for group, available in (
			({}, [{'id': '4-core'}, {'id': 'ubuntu-latest'}]),
			({'Compute': {'id': 1}}, []),
		):
			with (
				mock.patch.object(hosted, 'readDetails', return_value=([], {})),
				mock.patch.object(resources, 'runnerGroupDetails', return_value=group),
				mock.patch.object(resources, 'readCollection', return_value=available),
				self.assertRaises(ValueError),
			):
				hosted.collectionChanges([], BASE, [], [targetRunner()], {})
		with self.assertRaisesRegex(ValueError, 'sẵn sàng'):
			hosted.validateResponse(json.dumps(apiRunner(status='Provisioning')), 'build-linux')
		with self.assertRaises(ValueError):
			hosted.validateResponse(json.dumps(apiRunner(name='OTHER')), 'build-linux')

	def testRunnerNetworkCaptureAndRestoreUseNamesAndFreshIds(self):
		api = dict(
			runnerGroup()['settings'],
			id=7,
			default=False,
			inherited=False,
			workflow_restrictions_read_only=False,
			network_configuration_id='OLD_NETWORK',
		)
		with (
			mock.patch.object(resources, 'runnerGroupDetails', return_value={'Compute': api}),
			mock.patch.object(
				enterprise,
				'readDetails',
				return_value=([{'name': 'Cloud'}], {'Cloud': 'OLD_NETWORK'}),
			),
		):
			groups = resources.readRunnerGroups()
		self.assertEqual(groups[0]['settings']['network_configuration'], 'Cloud')
		self.assertNotIn('OLD_NETWORK', json.dumps(groups))
		with mock.patch.object(enterprise, 'readDetails', return_value=([], {})):
			body = resources.runnerGroupBody(
				groups[0]['settings'], {'planned_network_configurations': {'Cloud'}}
			)
		with mock.patch.object(
			enterprise, 'readDetails', return_value=([{'name': 'Cloud'}], {'Cloud': 'NEW_NETWORK'})
		):
			body = resources.resolveRunnerGroupBody(body)
		self.assertEqual(body['network_configuration_id'], 'NEW_NETWORK')
		self.assertNotIn('network_configuration', body)
		self.assertNotIn('network_configuration_name', body)
		self.assertEqual(
			resources.resolveRunnerGroupBody({'network_configuration_name': None}),
			{'network_configuration_id': None},
		)

	def testMissingRunnerNetworkFieldCannotBeTreatedAsNull(self):
		current = [runnerGroup()]
		wanted = copy.deepcopy(current)
		wanted[0]['settings']['network_configuration'] = None
		with self.assertRaisesRegex(ValueError, 'không suy đoán'):
			resources.runnerGroupChanges([], current, wanted)

	def testGroupCreatedBeforePoolAndRoundtripUsesNewGroupId(self):
		target = targetRunner()
		wanted = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'runner_groups': [runnerGroup()],
			'collections': {'hosted_runners': [target]},
		}
		live, groups = [], {}
		config = copy.deepcopy(configuration.readConfig(ROOT))
		config['unavailable'] = {}

		def readScopes(source):
			return [
				(
					None,
					wanted,
					(
						dict(
							wanted,
							runner_groups=[runnerGroup()] if groups else [],
							collections={'hosted_runners': copy.deepcopy(live)},
						),
						{},
					),
				)
			]

		def write(*args, stdin):
			path, body = args[3], json.loads(stdin)
			if path.endswith('/runner-groups'):
				groups['Compute'] = {'id': 81}
				return json.dumps(dict(body, id=81))
			self.assertTrue(path.endswith('/hosted-runners'))
			self.assertEqual(body['runner_group_id'], 81)
			live.append(copy.deepcopy(target))
			return json.dumps(apiRunner(id=92, runner_group_id=81))

		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(configuration, 'configuredScopes', side_effect=readScopes),
			mock.patch.object(
				hosted,
				'readDetails',
				side_effect=lambda base: (copy.deepcopy(live), {'build-linux': 92} if live else {}),
			),
			mock.patch.object(
				resources, 'runnerGroupDetails', side_effect=lambda: copy.deepcopy(groups)
			),
			mock.patch.object(
				resources,
				'readCollection',
				side_effect=lambda path, key: (
					[{'id': '4-core'}] if key == 'machine_specs' else [{'id': 'ubuntu-latest'}]
				),
			),
			mock.patch.object(github, 'gh', side_effect=write) as mutation,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
		self.assertEqual(mutation.call_count, 2)

	def testUnavailablePaidPoolsAreNotReplacedWithEmptyGroup(self):
		with mock.patch.object(
			resources, 'readCollection', side_effect=RuntimeError('HTTP 404 PRIVATE')
		):
			groups, _, unavailable = catalog.readCollections(BASE, ['hosted_runners'])
		self.assertEqual(groups, {})
		self.assertEqual(unavailable, {BASE + '/actions/hosted-runners': 'HTTP 404'})


if __name__ == '__main__':
	unittest.main()
