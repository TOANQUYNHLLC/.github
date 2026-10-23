"""Kiểm tra Actions policies, quyền Dependabot và giới hạn cache trên gói có quyền."""

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

from orgsetup import catalog, configuration, github, policies, resources

ORG_BASE = 'orgs/TOANQUYNHLLC'
REPO_BASE = 'repos/TOANQUYNHLLC/.github'


def apiPolicy(**changes):
	return dict(
		{
			'id': 9,
			'name': 'Execution',
			'target': 'actions',
			'source_type': 'Repository',
			'source': 'TOANQUYNHLLC/.github',
			'enforcement': 'active',
			'conditions': {'workflow_path': {'include': ['~ALL'], 'exclude': []}},
			'rules': [
				{
					'type': 'restrict_action_events',
					'parameters': {'allowed_events': ['push', 'workflow_dispatch']},
				}
			],
			'created_at': 'METADATA',
		},
		**changes,
	)


class ActionsPoliciesTest(unittest.TestCase):
	def capture(self, item):
		base = ORG_BASE if item['source_type'] == 'Organization' else REPO_BASE
		with (
			mock.patch.object(
				resources, 'readCollection', return_value=[{'id': item['id'], 'name': item['name']}]
			),
			mock.patch.object(github, 'ghJson', return_value=item),
		):
			return policies.readDetails(base, 'actions_policies')

	def testCaptureFullDetailsExcludesInheritedMetadataAndConvertsRepositoryIds(self):
		item = apiPolicy(
			source_type='Organization',
			source='TOANQUYNHLLC',
			conditions={'repository_id': {'repository_ids': [17]}},
		)
		with (
			mock.patch.object(
				resources, 'readCollection', return_value=[{'id': 9, 'name': 'Execution'}]
			) as collection,
			mock.patch.object(
				github,
				'ghJson',
				side_effect=[
					item,
					{'id': 17, 'full_name': 'TOANQUYNHLLC/.github', 'owner': {'email': 'PRIVATE'}},
				],
			),
		):
			items, ids = policies.readDetails(ORG_BASE, 'actions_policies')
		self.assertIn('has_parents=false', collection.call_args.args[0])
		self.assertEqual(ids, {'Execution': 9})
		self.assertEqual(
			items[0]['conditions'], {'selected_repositories': ['TOANQUYNHLLC/.github']}
		)
		self.assertNotIn('PRIVATE', json.dumps(items))
		self.assertNotIn('repository_ids', json.dumps(items))
		self.assertNotIn('created_at', json.dumps(items))

	def testPolicyCreateUpdateUsesFreshIdsAndDefaultWorkflowReadbackIsNoop(self):
		items, _ = self.capture(apiPolicy())
		wanted = copy.deepcopy(items)
		wanted[0]['conditions'] = {}
		with mock.patch.object(policies, 'readDetails', return_value=([], {})):
			plan = []
			policies.collectionChanges(plan, REPO_BASE, 'actions_policies', [], wanted, {})
		self.assertEqual(plan[0][1], 'POST')
		self.assertNotIn('conditions', plan[0][2])
		plan = []
		policies.collectionChanges(plan, REPO_BASE, 'actions_policies', items, wanted, {})
		self.assertEqual(plan, [])
		wanted[0]['enforcement'] = 'evaluate'
		with mock.patch.object(policies, 'readDetails', return_value=(items, {'Execution': 92})):
			policies.collectionChanges(plan, REPO_BASE, 'actions_policies', items, wanted, {})
		self.assertTrue(plan[0][0].endswith('/92'))
		self.assertEqual(plan[0][1], 'PUT')

	def testExplicitRepositoryNamesAreResolvedAtApplyPlanAndConditionsCannotBeLost(self):
		item = apiPolicy(
			source_type='Organization',
			source='TOANQUYNHLLC',
			conditions={'repository_name': {'include': ['~ALL'], 'exclude': []}},
		)
		items, _ = self.capture(item)
		wanted = copy.deepcopy(items)
		wanted[0]['conditions'] = {'selected_repositories': ['TOANQUYNHLLC/.github']}
		with (
			mock.patch.object(policies, 'readDetails', return_value=(items, {'Execution': 10})),
			mock.patch.object(resources, 'repositoryIds', return_value=[41]),
		):
			plan = []
			policies.collectionChanges(plan, ORG_BASE, 'actions_policies', items, wanted, {})
		self.assertEqual(plan[0][2]['conditions'], {'repository_id': {'repository_ids': [41]}})
		wanted[0]['conditions'] = {}
		with (
			mock.patch.object(policies, 'readDetails', return_value=(items, {'Execution': 10})),
			self.assertRaises(ValueError),
		):
			policies.collectionChanges([], ORG_BASE, 'actions_policies', items, wanted, {})

	def testInvalidPolicyForeignScopeAndConcurrentEditCannotWrite(self):
		for changes in (
			{'source': 'OTHER/.github'},
			{'source_type': 'Enterprise'},
			{'target': 'branch'},
			{'id': 0},
		):
			with self.subTest(changes=changes), self.assertRaises(ValueError):
				self.capture(apiPolicy(**changes))
		items, _ = self.capture(apiPolicy())
		wanted = copy.deepcopy(items)
		wanted[0]['enforcement'] = 'disabled'
		changed = copy.deepcopy(items)
		changed[0]['enforcement'] = 'evaluate'
		with (
			mock.patch.object(policies, 'readDetails', return_value=(changed, {'Execution': 9})),
			self.assertRaisesRegex(ValueError, 'thay đổi'),
		):
			policies.collectionChanges([], REPO_BASE, 'actions_policies', items, wanted, {})
		wanted[0]['rules'][0]['parameters']['allowed_events'] = ['UNSUPPORTED']
		with self.assertRaises(ValueError):
			policies.validateGroup('actions_policies', wanted)
		with self.assertRaises(ValueError):
			policies.validateScope(
				REPO_BASE, 'actions_policies', [{'conditions': {'repository_name': {}}}]
			)

	def testDependabotPaginationCapturesNullDefaultAndNeverProfiles(self):
		pages = [
			{
				'default_level': None,
				'accessible_repositories': [
					{'id': 15, 'full_name': 'TOANQUYNHLLC/a', 'owner': {'email': 'PRIVATE'}}
				],
			},
			{
				'default_level': None,
				'accessible_repositories': [{'id': 19, 'full_name': 'TOANQUYNHLLC/b'}],
			},
		]
		with mock.patch.object(github, 'ghJson', return_value=pages):
			items, ids = policies.readDetails(ORG_BASE, 'dependabot_access')
		self.assertEqual(
			items, [{'default_level': None, 'repositories': ['TOANQUYNHLLC/a', 'TOANQUYNHLLC/b']}]
		)
		self.assertEqual(ids, {'TOANQUYNHLLC/a': 15, 'TOANQUYNHLLC/b': 19})
		pages[1]['default_level'] = 'public'
		with mock.patch.object(github, 'ghJson', return_value=pages), self.assertRaises(ValueError):
			policies.readDetails(ORG_BASE, 'dependabot_access')

	def testDependabotRestoresDefaultAndExactGrantListWithVerifiedIds(self):
		current = [{'default_level': None, 'repositories': ['TOANQUYNHLLC/old']}]
		wanted = [{'default_level': 'public', 'repositories': ['TOANQUYNHLLC/new']}]
		with (
			mock.patch.object(
				policies, 'readDetails', return_value=(current, {'TOANQUYNHLLC/old': 21})
			),
			mock.patch.object(resources, 'repositoryIds', return_value=[92]),
		):
			plan = []
			policies.collectionChanges(plan, ORG_BASE, 'dependabot_access', current, wanted, {})
		self.assertEqual([step[1] for step in plan], ['PUT', 'PATCH'])
		self.assertEqual(
			plan[1][2], {'repository_ids_to_add': [92], 'repository_ids_to_remove': [21]}
		)
		with (
			mock.patch.object(
				policies, 'readDetails', return_value=(wanted, {'TOANQUYNHLLC/new': 92})
			),
			self.assertRaisesRegex(ValueError, 'null'),
		):
			policies.collectionChanges([], ORG_BASE, 'dependabot_access', wanted, current, {})

	def testHiddenDependabotDefaultDoesNotLoseReadableRepositoryListOrBecomeNull(self):
		with mock.patch.object(github, 'ghJson', return_value=[{'accessible_repositories': []}]):
			groups, _, unavailable = catalog.readCollections(ORG_BASE, ['dependabot_access'])
		self.assertEqual(groups, {'dependabot_access': [{'repositories': []}]})
		self.assertIn('default_level', unavailable[ORG_BASE + '/dependabot/repository-access'])
		with self.assertRaisesRegex(ValueError, 'không suy đoán'):
			policies.collectionChanges(
				[],
				ORG_BASE,
				'dependabot_access',
				[{'repositories': []}],
				[{'default_level': 'public', 'repositories': []}],
				{},
			)

	def testImportMissingFillsNestedFieldsWithoutOverwritingTargetsOrAddingManagedItems(self):
		previous = {
			'settings': {},
			'web_settings': {},
			'endpoints': {'actions/permissions': {'enabled': False}},
			'collections': {'dependabot_access': [{'repositories': []}], 'actions_policies': []},
			'runner_groups': [
				{
					'settings': {'name': 'Compute', 'visibility': 'selected'},
					'selected_repositories': [],
				}
			],
		}
		captured = {
			'settings': {},
			'web_settings': {},
			'endpoints': {'actions/permissions': {'enabled': True, 'allowed_actions': 'all'}},
			'collections': {
				'dependabot_access': [
					{'default_level': 'public', 'repositories': ['TOANQUYNHLLC/new']}
				],
				'actions_policies': [{'name': 'Execution'}],
			},
			'runner_groups': [
				{
					'settings': {
						'name': 'Compute',
						'visibility': 'all',
						'network_configuration': 'Cloud',
					},
					'selected_repositories': ['TOANQUYNHLLC/new'],
				},
				{'settings': {'name': 'Outside'}},
			],
		}
		before = copy.deepcopy(previous)
		result = configuration.completeScope(previous, captured)
		self.assertEqual(
			result['endpoints']['actions/permissions'], {'enabled': False, 'allowed_actions': 'all'}
		)
		self.assertEqual(
			result['collections']['dependabot_access'],
			[{'repositories': [], 'default_level': 'public'}],
		)
		self.assertEqual(result['collections']['actions_policies'], [])
		self.assertEqual(len(result['runner_groups']), 1)
		self.assertEqual(result['runner_groups'][0]['selected_repositories'], [])
		self.assertEqual(
			result['runner_groups'][0]['settings'],
			{'name': 'Compute', 'visibility': 'selected', 'network_configuration': 'Cloud'},
		)
		self.assertEqual(previous, before)

	def testCacheLimitsCaptureAndWriteRejectInvalidTypesAndUnavailableIsKept(self):
		for suffix, field in (
			('actions/cache/storage-limit', 'max_cache_size_gb'),
			('actions/cache/retention-limit', 'max_cache_retention_days'),
		):
			method, fields = configuration.REPO_ENDPOINTS[suffix]
			with mock.patch.object(
				github, 'ghJson', return_value={field: 10, 'unused': 'METADATA'}
			):
				self.assertEqual(
					configuration.readEndpoint(REPO_BASE + '/' + suffix, suffix, fields),
					{field: 10},
				)
			plan = []
			configuration.addChanges(
				plan, REPO_BASE + '/' + suffix, {field: 10}, {field: 20}, method, suffix
			)
			self.assertEqual(plan[0][1:3], ('PUT', {field: 20}))
			for value in (0, -1, True, '10'):
				with self.subTest(value=value), self.assertRaises(ValueError):
					configuration.checkFields({field: value}, fields, suffix)
		with mock.patch.object(
			resources, 'readCollection', side_effect=RuntimeError('HTTP 403 PRIVATE')
		):
			groups, _, unavailable = catalog.readCollections(ORG_BASE, ['actions_policies'])
		self.assertEqual(groups, {})
		self.assertEqual(unavailable, {ORG_BASE + '/actions/policies': 'HTTP 403'})

	def testPolicyRoundtripChecksResponseAndSecondApplyIsNoop(self):
		items, _ = self.capture(apiPolicy())
		wanted = {
			'settings': {},
			'web_settings': {},
			'endpoints': {},
			'collections': {'actions_policies': items},
		}
		live = []
		config = copy.deepcopy(configuration.readConfig(ROOT))
		config['unavailable'] = {}

		def readScopes(source):
			return [
				(
					'.github',
					wanted,
					(dict(wanted, collections={'actions_policies': copy.deepcopy(live)}), {}),
				)
			]

		def write(*args, stdin):
			body = json.loads(stdin)
			self.assertEqual(body['name'], 'Execution')
			live.extend(copy.deepcopy(items))
			return json.dumps(apiPolicy(id=81))

		with (
			mock.patch.object(configuration, 'readConfig', return_value=config),
			mock.patch.object(configuration, 'configuredScopes', side_effect=readScopes),
			mock.patch.object(
				policies,
				'readDetails',
				side_effect=lambda base, key: (copy.deepcopy(live), {'Execution': 81}),
			),
			mock.patch.object(github, 'gh', side_effect=write) as mutation,
			contextlib.redirect_stdout(io.StringIO()),
		):
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
			self.assertEqual(configuration.syncConfiguredSettings(True), 0)
		mutation.assert_called_once()


if __name__ == '__main__':
	unittest.main()
