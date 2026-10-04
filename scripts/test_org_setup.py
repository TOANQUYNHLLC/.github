"""Test tự động cho scripts/org-setup.py và gói scripts/orgsetup/: tệp dùng chung, ruleset, cài đặt, team, nhãn.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import base64
import contextlib
import importlib
import io
import json
import re
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import ROOT, loadScript
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript

# Nạp sau testsupport: testsupport thêm scripts/ vào sys.path để import được gói orgsetup.
from orgsetup import files, github, labels, rulesets, settings, teams


class OrgSetupTest(unittest.TestCase):
	def testGraphqlDeployKeysKeepNullableIds(self):
		node = {
			'name': 'x',
			'target': 'BRANCH',
			'enforcement': 'ACTIVE',
			'conditions': {},
			'bypassActors': {
				'pageInfo': {'hasNextPage': False},
				'nodes': [
					{
						'bypassMode': 'ALWAYS',
						'organizationAdmin': False,
						'deployKey': True,
						'repositoryRoleDatabaseId': None,
						'actor': None,
					}
				],
			},
			'rules': {'pageInfo': {'hasNextPage': False}, 'nodes': []},
		}
		self.assertEqual(
			rulesets.graphqlRuleset(node)['bypass_actors'],
			[
				{'actor_id': None, 'actor_type': 'DeployKey', 'bypass_mode': 'always'},
			],
		)

	def testMalformedGraphqlRulesetsAreReportedWithoutSuccessOrTraceback(self):
		valid = {
			'name': 'x',
			'target': 'BRANCH',
			'enforcement': 'ACTIVE',
			'conditions': {},
			'bypassActors': {'nodes': [], 'pageInfo': {'hasNextPage': False}},
			'rules': {'nodes': [], 'pageInfo': {'hasNextPage': False}},
		}
		cases = (
			('target', 42),
			('conditions', []),
			('bypassActors', []),
			('rules', {'nodes': [], 'pageInfo': {}}),
			('rules', {'nodes': [], 'pageInfo': {'hasNextPage': 'false'}}),
			('rules', {'nodes': [42], 'pageInfo': {'hasNextPage': False}}),
			(
				'rules',
				{
					'nodes': [{'type': 'CODE_QUALITY', 'parameters': {'severity': 42}}],
					'pageInfo': {'hasNextPage': False},
				},
			),
			(
				'bypassActors',
				{
					'nodes': [
						{
							'organizationAdmin': 'false',
							'deployKey': False,
							'bypassMode': 'ALWAYS',
							'repositoryRoleDatabaseId': None,
							'actor': None,
						}
					],
					'pageInfo': {'hasNextPage': False},
				},
			),
		)
		for field, value in cases:
			with self.subTest(field=field, value=value):
				node = dict(valid, **{field: value})
				data = [
					{
						'data': {
							'organization': {
								'rulesets': {'nodes': [node], 'pageInfo': {'hasNextPage': False}}
							}
						}
					}
				]
				with (
					mock.patch.object(github, 'ghJson', return_value=data),
					contextlib.redirect_stdout(io.StringIO()) as output,
				):
					rulesets.compareOrgRulesets()
				self.assertIn('không đọc được qua GraphQL', output.getvalue())
				self.assertNotIn('đã đúng', output.getvalue())
				self.assertNotIn('chưa có ruleset', output.getvalue())

	def testGraphqlPageErrorsOrMissingLastPageDoNotLookLikeMissingRulesets(self):
		connection = {'nodes': [], 'pageInfo': {'hasNextPage': False}}
		valid = {'data': {'organization': {'rulesets': connection}}}
		for data in (
			[],
			[None],
			[valid, valid],
			[{'errors': [{'message': 'Không được đọc'}], **valid}],
			[
				{
					'data': {
						'organization': {
							'rulesets': {'nodes': [], 'pageInfo': {'hasNextPage': True}}
						}
					}
				}
			],
			[{'data': {'organization': {'rulesets': {'nodes': []}}}}],
		):
			with self.subTest(data=data):
				with (
					mock.patch.object(github, 'ghJson', return_value=data),
					contextlib.redirect_stdout(io.StringIO()) as output,
				):
					rulesets.compareOrgRulesets()
				self.assertIn('không đọc được qua GraphQL', output.getvalue())
				self.assertNotIn('chưa có ruleset', output.getvalue())

	def testDuplicateGraphqlRulesetsAreNotCollapsed(self):
		wanted = rulesets.orgRulesets()[0][1]
		data = [
			{
				'data': {
					'organization': {
						'rulesets': {'nodes': [wanted, wanted], 'pageInfo': {'hasNextPage': False}}
					}
				}
			}
		]
		with (
			mock.patch.object(github, 'ghJson', return_value=data),
			mock.patch.object(rulesets, 'graphqlRuleset', rulesets.graphqlVisible),
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			rulesets.compareOrgRulesets()
		self.assertIn('không đọc được qua GraphQL', output.getvalue())
		self.assertNotIn('đã đúng', output.getvalue())

	def testRulesetSummarySupportsNullableActorIds(self):
		wanted = rulesets.rulesetFor('.github')
		actors = [
			{'actor_id': None, 'actor_type': 'DeployKey', 'bypass_mode': 'always'},
			{'actor_id': 7, 'actor_type': 'Integration', 'bypass_mode': 'exempt'},
			{'actor_id': None, 'actor_type': 'OrganizationAdmin', 'bypass_mode': 'always'},
		]
		live = dict(wanted, bypass_actors=actors)
		other = dict(wanted, bypass_actors=[dict(actor) for actor in reversed(actors)])
		other['bypass_actors'][0]['actor_id'] = 1
		self.assertEqual(rulesets.rulesetSummary(live), rulesets.rulesetSummary(other))

	def testMalformedRulesetListsStopBeforeDetailReadsAndWrites(self):
		invalid = (42, {}, {'name': 'x', 'id': True}, {'name': 'x', 'id': 0}, {'name': [], 'id': 1})
		for organization in (False, True):
			for item in invalid:
				with self.subTest(organization=organization, item=item):
					with (
						mock.patch.object(github, 'ghList', return_value=[item]),
						mock.patch.object(github, 'ghJson') as read,
						mock.patch.object(github, 'gh') as write,
						contextlib.redirect_stdout(io.StringIO()),
						self.assertRaisesRegex(ValueError, 'ruleset'),
					):
						if organization:
							rulesets.syncOrgRulesets(apply=True)
						else:
							rulesets.syncRulesets(['.github'], apply=True)
					read.assert_not_called()
					write.assert_not_called()

	def testDuplicateRulesetIdentitiesDoNotChooseAnArbitraryId(self):
		for listing in (
			[{'name': 'Protect Main', 'id': 1}, {'name': 'Protect Main', 'id': 2}],
			[{'name': 'Protect Main', 'id': 1}, {'name': 'Other', 'id': 1}],
		):
			with self.subTest(listing=listing):
				with (
					mock.patch.object(github, 'ghList', return_value=listing),
					mock.patch.object(github, 'ghJson') as read,
					mock.patch.object(github, 'gh') as write,
					contextlib.redirect_stdout(io.StringIO()),
					self.assertRaisesRegex(ValueError, 'trùng'),
				):
					rulesets.syncRulesets(['.github'], apply=True)
				read.assert_not_called()
				write.assert_not_called()

	def testRulesetSummaryRejectsMissingAndMalformedFields(self):
		wanted = rulesets.rulesetFor('.github')
		for field, value in (
			('name', None),
			('target', 42),
			('enforcement', 'unknown'),
			('conditions', []),
			('conditions', {'ref_name': {'include': [42], 'exclude': []}}),
			('bypass_actors', None),
			('bypass_actors', [42]),
			('bypass_actors', [{'actor_type': 'User', 'actor_id': None, 'bypass_mode': 'always'}]),
			('rules', None),
			('rules', [42]),
			('rules', [{'type': 'pull_request', 'parameters': []}]),
		):
			with (
				self.subTest(field=field, value=value),
				self.assertRaisesRegex((TypeError, ValueError), 'ruleset'),
			):
				rulesets.rulesetSummary(dict(wanted, **{field: value}))
		for field in ('name', 'target', 'enforcement', 'conditions', 'bypass_actors', 'rules'):
			with self.subTest(missing=field):
				current = {key: value for key, value in wanted.items() if key != field}
				with self.assertRaisesRegex(TypeError, field):
					rulesets.rulesetSummary(current)

	def testEveryRulesetIsValidatedBeforeTheFirstWrite(self):
		for organization in (False, True):
			wanted = rulesets.orgRulesets() if organization else rulesets.rulesetsFor('.github')
			listing = [
				{'name': item['name'], 'id': index + 1} for index, (_, item) in enumerate(wanted)
			]
			for failure in ({}, RuntimeError('HTTP 429 ở ruleset sau')):
				with self.subTest(organization=organization, failure=failure):

					def read(*args, failure=failure, wanted=wanted):
						index = int(args[-1].rsplit('/', 1)[-1]) - 1
						if index == 1:
							if isinstance(failure, Exception):
								raise failure
							return failure
						return dict(wanted[index][1], enforcement='disabled', id=index + 1)

					with (
						mock.patch.object(github, 'ghList', return_value=listing),
						mock.patch.object(github, 'ghJson', read),
						mock.patch.object(github, 'gh') as write,
						contextlib.redirect_stdout(io.StringIO()),
						self.assertRaises((TypeError, ValueError, RuntimeError)),
					):
						if organization:
							rulesets.syncOrgRulesets(apply=True)
						else:
							rulesets.syncRulesets(['.github'], apply=True)
					write.assert_not_called()

	def testRulesetDetailMustMatchTheListedIdentity(self):
		wanted = rulesets.rulesetsFor('.github')
		with (
			mock.patch.object(
				github, 'ghList', return_value=[{'name': wanted[0][1]['name'], 'id': 1}]
			),
			mock.patch.object(github, 'ghJson', return_value=dict(wanted[1][1], id=1)),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaisesRegex(ValueError, 'name'),
		):
			rulesets.syncRulesets(['.github'], apply=True)
		write.assert_not_called()

	def testRulesetDetailIdMustMatchTheListedId(self):
		wanted = rulesets.rulesetFor('.github')
		for badId in (None, '1', True, 2):
			with (
				self.subTest(id=badId),
				mock.patch.object(
					github, 'ghList', return_value=[{'name': wanted['name'], 'id': 1}]
				),
				mock.patch.object(github, 'ghJson', return_value=dict(wanted, id=badId)),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
				self.assertRaisesRegex(ValueError, 'id'),
			):
				rulesets.syncRulesets(['.github'], apply=True)
			write.assert_not_called()

	def testOrgRulesetReadsOverlapAndWritesFollowSourceOrder(self):
		wanted = rulesets.orgRulesets()
		listing = [
			{'name': item['name'], 'id': index + 1} for index, (_, item) in enumerate(wanted)
		]
		barrier = threading.Barrier(len(wanted))

		def read(*args):
			barrier.wait(timeout=2)
			index = int(args[-1].rsplit('/', 1)[-1]) - 1
			return dict(wanted[index][1], enforcement='disabled', id=index + 1)

		with (
			mock.patch.object(github, 'ghList', return_value=listing),
			mock.patch.object(github, 'ghJson', read),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			rulesets.syncOrgRulesets(apply=True)
		self.assertEqual(
			[call.args[3].rsplit('/', 1)[-1] for call in write.call_args_list], ['1', '2', '3']
		)

	def testSettingsSchemaErrorsAreReportedByCli(self):
		module = loadScript('org-setup')
		output = io.StringIO()
		with (
			mock.patch.object(module.sys, 'argv', ['org-setup.py', 'settings', '--repo', 'app']),
			mock.patch.object(module, 'signedIn', return_value=True),
			mock.patch.object(
				module, 'runCommand', side_effect=TypeError('không đọc được object cài đặt')
			),
			contextlib.redirect_stderr(output),
		):
			self.assertEqual(module.main(), 1)
		self.assertIn('không đọc được object cài đặt', output.getvalue())
		self.assertNotIn('Traceback', output.getvalue())

	def testDisabledSecurityFeaturesAreEnabledInOrder(self):
		current = {
			'private': True,
			'security_and_analysis': {
				name: {'status': 'disabled'} for name in settings.SECURITY_FEATURES
			},
		}
		with (
			mock.patch.object(github, 'ghExists', return_value=False),
			mock.patch.object(github, 'ghJson', return_value={'enabled': False}),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			settings.syncSecurity('app', current, apply=True)
		self.assertEqual(
			json.loads(write.call_args_list[0].kwargs['stdin']),
			{
				'security_and_analysis': {
					name: {'status': 'enabled'} for name in settings.SECURITY_FEATURES
				}
			},
		)
		self.assertEqual(
			[call.args[-1].rsplit('/', 1)[-1] for call in write.call_args_list[1:]],
			['vulnerability-alerts', 'automated-security-fixes', 'immutable-releases'],
		)

	def testOrgActionsKeepSelectedRepositoryPolicy(self):
		current = {
			'enabled_repositories': 'selected',
			'allowed_actions': 'all',
			'sha_pinning_required': True,
		}
		with mock.patch.object(github, 'gh') as write, contextlib.redirect_stdout(io.StringIO()):
			settings.syncActions(
				'permissions',
				settings.ORG_ACTIONS_PERMISSIONS,
				'enabled_repositories',
				True,
				[current, dict(settings.WORKFLOW_PERMISSIONS)],
			)
		write.assert_called_once()
		self.assertEqual(
			json.loads(write.call_args.kwargs['stdin']),
			{'sha_pinning_required': False, 'enabled_repositories': 'selected'},
		)

	def testDefaultBranchMustBeReadable(self):
		for data in (None, [], {}, {'default_branch': None}, {'default_branch': ''}):
			with (
				self.subTest(data=data),
				mock.patch.object(github, 'ghJson', return_value=data),
				self.assertRaises(ValueError),
			):
				github.defaultBranch('app')

	def testMalformedFileInventoryStopsBeforeWrites(self):
		validRef = {'object': {'sha': 'abc123'}}
		validTree = {'truncated': False, 'tree': []}
		cases = [
			(reference, validTree, [])
			for reference in (None, [], {}, {'object': []}, {'object': {'sha': None}})
		]
		cases += [
			(validRef, tree, [])
			for tree in (
				[],
				{},
				{'truncated': 'false', 'tree': []},
				{'truncated': False, 'tree': None},
				{'truncated': False, 'tree': [{'path': None, 'type': 'blob'}]},
				{'truncated': False, 'tree': [{'path': '.nvmrc', 'type': 'unknown'}]},
			)
		]
		cases += [
			(validRef, {'truncated': True, 'tree': []}, contents)
			for contents in (
				{},
				None,
				[{'name': None}],
				[{'name': 'package.json', 'type': 'unknown'}],
			)
		]
		for reference, tree, contents in cases:

			def read(*args, reference=reference, tree=tree, contents=contents):
				path = args[-1]
				return (
					reference
					if '/git/ref/' in path
					else tree
					if '/git/trees/' in path
					else contents
				)

			with (
				self.subTest(reference=reference, tree=tree, contents=contents),
				mock.patch.object(github, 'defaultBranch', return_value='main'),
				mock.patch.object(github, 'ghJson', read),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
				self.assertRaises(ValueError),
			):
				files.syncFiles(['app'], apply=True)
			write.assert_not_called()

	def testManifestDirectoriesAreNotDependencies(self):
		for truncated in (False, True):

			def read(*args, truncated=truncated):
				path = args[-1]
				if '/git/ref/' in path:
					return {'object': {'sha': 'abc123'}}
				if '/git/trees/' in path:
					return {
						'truncated': truncated,
						'tree': [{'path': 'package.json', 'type': 'tree'}],
					}
				return [{'name': 'package.json', 'type': 'dir'}]

			with (
				self.subTest(truncated=truncated),
				mock.patch.object(github, 'defaultBranch', return_value='main'),
				mock.patch.object(github, 'ghJson', read),
				mock.patch.object(github, 'ghExists', return_value=True),
				mock.patch.object(files, 'plannedFiles', wraps=files.plannedFiles) as plan,
				contextlib.redirect_stdout(io.StringIO()),
			):
				files.syncFiles(['app'], apply=False)
			plan.assert_called_once_with(set())

	def testSecurityUpdatesWaitForReadableAlerts(self):
		current = {
			'private': True,
			'security_and_analysis': {
				name: {'status': 'enabled'} for name in settings.SECURITY_FEATURES
			},
		}
		with (
			mock.patch.object(github, 'ghExists', side_effect=RuntimeError('HTTP 403')),
			mock.patch.object(github, 'ghJson', return_value={'enabled': False}),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			settings.syncSecurity('app', current, apply=True)
		paths = [call.args[-1] for call in write.call_args_list]
		self.assertFalse(any(path.endswith('/automated-security-fixes') for path in paths))
		self.assertTrue(any(path.endswith('/immutable-releases') for path in paths))

	def testSecurityUpdatesWaitForSuccessfulAlertsWrite(self):
		current = {
			'private': True,
			'security_and_analysis': {
				name: {'status': 'enabled'} for name in settings.SECURITY_FEATURES
			},
		}

		def write(*args, **kwargs):
			if args[-1].endswith('/vulnerability-alerts'):
				raise RuntimeError('HTTP 403')

		with (
			mock.patch.object(github, 'ghExists', return_value=False),
			mock.patch.object(github, 'ghJson', return_value={'enabled': False}),
			mock.patch.object(github, 'gh', side_effect=write) as call,
			contextlib.redirect_stdout(io.StringIO()),
		):
			settings.syncSecurity('app', current, apply=True)
		self.assertFalse(
			any(args[-1].endswith('/automated-security-fixes') for args, _ in call.call_args_list)
		)

	def testUnknownActionsStateCannotBeWritten(self):
		for enabledKey, wanted, states in (
			(
				'enabled',
				settings.ACTIONS_PERMISSIONS,
				({}, {'enabled': None}, {'enabled': 'false'}, {'enabled': 0}, []),
			),
			(
				'enabled_repositories',
				settings.ORG_ACTIONS_PERMISSIONS,
				(
					{},
					{'enabled_repositories': None},
					{'enabled_repositories': 'other'},
					{'enabled_repositories': []},
				),
			),
		):
			for current in states:
				output = io.StringIO()
				with (
					self.subTest(current=current),
					mock.patch.object(github, 'gh') as write,
					contextlib.redirect_stdout(output),
				):
					settings.syncActions(
						'permissions',
						wanted,
						enabledKey,
						True,
						[current, dict(settings.WORKFLOW_PERMISSIONS)],
					)
				write.assert_not_called()
				self.assertIn('không đọc được', output.getvalue())
				self.assertNotIn('đã đúng', output.getvalue())

	def testMalformedWorkflowPermissionsAreSkipped(self):
		for current in (
			{},
			[],
			{'default_workflow_permissions': 'read'},
			{'default_workflow_permissions': 'unknown', 'can_approve_pull_request_reviews': True},
			{'default_workflow_permissions': 'read', 'can_approve_pull_request_reviews': 'false'},
		):
			output = io.StringIO()
			with (
				self.subTest(current=current),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(output),
			):
				settings.syncActions(
					'permissions',
					settings.ACTIONS_PERMISSIONS,
					'enabled',
					True,
					[{'enabled': False}, current],
				)
			write.assert_not_called()
			self.assertIn('không đọc được', output.getvalue())
			self.assertNotIn('đã đúng', output.getvalue())

	def testActionsJsonErrorIsReportedPerEndpoint(self):
		output = io.StringIO()
		with (
			mock.patch.object(github, 'ghJson', side_effect=ValueError('JSON không hợp lệ')),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(output),
		):
			settings.syncActions('permissions', settings.ACTIONS_PERMISSIONS, 'enabled', True)
		write.assert_not_called()
		self.assertIn('JSON không hợp lệ', output.getvalue())

	def testMalformedSecurityStatusIsNotChanged(self):
		current = {
			'private': False,
			'security_and_analysis': {
				name: {'status': 'enabled'} for name in settings.SECURITY_FEATURES
			},
		}
		for data in ({}, {'enabled': 'false'}, {'enabled': None}, [], {'enabled': 0}):
			output = io.StringIO()
			with (
				self.subTest(data=data),
				mock.patch.object(github, 'ghJson', return_value=data),
				mock.patch.object(github, 'ghExists', return_value=True),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(output),
			):
				settings.syncSecurity('app', current, apply=True)
			write.assert_not_called()
			self.assertIn('không đọc được trạng thái', output.getvalue())
			self.assertNotIn('tính năng bảo mật đã bật', output.getvalue())

	def testMissingSecurityAnalysisIsNotPatched(self):
		for analysis in (
			None,
			{},
			[],
			{'secret_scanning': {'status': 'unknown'}},
			{'secret_scanning': []},
			{
				'secret_scanning': {'status': 'unknown'},
				'secret_scanning_push_protection': {'status': 'disabled'},
			},
		):
			output = io.StringIO()
			with (
				self.subTest(analysis=analysis),
				mock.patch.object(github, 'ghJson', return_value={'enabled': True}),
				mock.patch.object(github, 'ghExists', return_value=True),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(output),
			):
				settings.syncSecurity(
					'app', {'private': True, 'security_and_analysis': analysis}, apply=True
				)
			write.assert_not_called()
			self.assertIn('không đọc được trạng thái', output.getvalue())
			self.assertNotIn('tính năng bảo mật đã bật', output.getvalue())

	def testInvalidSettingsObjectStopsBeforePatch(self):
		for current in ([], {}, {'has_issues': 'false'}, {'has_issues': 1}):
			with (
				self.subTest(current=current),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
				self.assertRaises((ValueError, TypeError)),
			):
				settings.updateSettings(
					'repos/o/r', current, {'has_issues': True}, True, 'cài đặt repository'
				)
			write.assert_not_called()

	def testCitationKeywordsUseYamlValues(self):
		with (
			tempfile.TemporaryDirectory() as folder,
			mock.patch.object(github, 'ROOT', Path(folder)),
		):
			for text in (
				'keywords: [github, rulesets]\n',
				'keywords:\n    - "github"\n    - rulesets # ghi chú\n',
				'values: &topics [github, rulesets]\nkeywords: *topics\n',
			):
				with self.subTest(text=text):
					(Path(folder) / 'CITATION.cff').write_text(text, encoding='utf-8')
					self.assertEqual(settings.citationKeywords(), ['github', 'rulesets'])

	def testInvalidTopicsNeverClearExistingTopics(self):
		with (
			tempfile.TemporaryDirectory() as folder,
			mock.patch.object(github, 'ROOT', Path(folder)),
		):
			for text in (
				'keywords: [\n',
				'title: example\n',
				'keywords: false\n',
				'keywords: [42]\n',
			):
				(Path(folder) / 'CITATION.cff').write_text(text, encoding='utf-8')
				with (
					self.subTest(text=text),
					mock.patch.object(github, 'gh') as write,
					contextlib.redirect_stdout(io.StringIO()),
					self.assertRaises(ValueError),
				):
					settings.syncTopics('.github', {'topics': ['github']}, apply=True)
				write.assert_not_called()

	def testUnknownTeamPermissionsStopBeforeAnyWrite(self):
		for value in (
			{'role_name': 'release_manager', 'permissions': {'push': True}},
			{},
			{'role_name': []},
			[],
		):

			def read(*args, value=value):
				path = args[-1]
				if '/memberships/' in path:
					return {'role': 'maintainer', 'state': 'active'}
				if '/repos/' in path:
					return value
				team = path.rsplit('/', 1)[-1]
				name, _, privacy, description = teams.TEAMS[team]
				return {'name': name, 'privacy': privacy, 'description': description}

			with (
				self.subTest(value=value),
				mock.patch.object(github, 'ghJson', read),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
				self.assertRaisesRegex(RuntimeError, 'quyền'),
			):
				teams.syncTeams(['app'], apply=True)
			write.assert_not_called()

	def testPendingOrMalformedMembershipStopsBeforeAnyWrite(self):
		for membership in (
			{'role': 'maintainer', 'state': 'pending'},
			{'role': 'maintainer'},
			{'role': 'owner', 'state': 'active'},
			[],
		):

			def read(*args, membership=membership):
				path = args[-1]
				if '/memberships/' in path:
					return membership
				if '/repos/' in path:
					return {'role_name': 'admin'}
				team = path.rsplit('/', 1)[-1]
				name, _, privacy, description = teams.TEAMS[team]
				return {'name': name, 'privacy': privacy, 'description': description}

			with (
				self.subTest(membership=membership),
				mock.patch.object(github, 'ghJson', read),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
				self.assertRaises(RuntimeError),
			):
				teams.syncTeams(['app'], apply=True)
			write.assert_not_called()

	def testMalformedTeamDetailsStopBeforeAnyWrite(self):
		for details in ({}, {'name': 'QA', 'privacy': []}, {'name': 'QA', 'privacy': 'closed'}, []):
			with (
				self.subTest(details=details),
				mock.patch.object(github, 'ghJson', return_value=details),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				with self.assertRaises(RuntimeError):
					teams.teamDetails('qa')
				with self.assertRaises(RuntimeError):
					teams.syncTeams(['app'], apply=True)
			write.assert_not_called()

	def testMembershipWriteDistinguishesInvitationFromActiveMember(self):
		teams.teamDetails = lambda team: {
			'name': teams.TEAMS[team][0],
			'description': teams.TEAMS[team][3],
			'privacy': teams.TEAMS[team][2],
		}
		teams.teamRole = lambda team, user: None
		teams.teamPermission = lambda team, repo: 'admin'
		for state in ('pending', 'active'):
			output = io.StringIO()
			with (
				self.subTest(state=state),
				mock.patch.object(
					github, 'gh', return_value=json.dumps({'role': 'maintainer', 'state': state})
				),
				contextlib.redirect_stdout(output),
			):
				teams.syncTeams(['app'], apply=True)
			if state == 'pending':
				self.assertIn('chờ chấp nhận lời mời', output.getvalue())
				self.assertNotIn('✔ thêm nguyentrongtoandl (maintainer)', output.getvalue())
			else:
				self.assertIn('✔ thêm nguyentrongtoandl (maintainer)', output.getvalue())

	def testLabelsSupportYamlAliases(self):
		with tempfile.TemporaryDirectory() as folder:
			path = Path(folder) / 'labels.yml'
			path.write_text(
				'- name: first\n  color: &color "ffffff"\n- name: second\n  color: *color\n',
				encoding='utf-8',
			)
			with mock.patch.object(labels, 'LABELS_FILE', path):
				self.assertEqual(
					labels.loadLabels(),
					[{'name': 'first', 'color': 'ffffff'}, {'name': 'second', 'color': 'ffffff'}],
				)

	def testLabelFieldsStopBeforeAnyGithubCall(self):
		valid = {'name': 'valid', 'color': 'ffffff', 'description': 'Đúng'}
		invalid = (
			{'color': 'ffffff'},
			{'name': 42, 'color': 'ffffff'},
			{'name': '  ', 'color': 'ffffff'},
			{'name': 'invalid', 'color': 123456},
			{'name': 'invalid', 'color': 'gggggg'},
			{'name': 'invalid', 'color': 'ffffff', 'description': False},
			{'name': 'invalid', 'color': 'ffffff', 'description': None},
			{'name': 'invalid', 'color': 'ffffff', 'description': 'a' * 101},
			{'name': 'VALID', 'color': 'ffffff'},
		)
		with tempfile.TemporaryDirectory() as folder:
			path = Path(folder) / 'labels.yml'
			for label in invalid:
				with self.subTest(label=label):
					path.write_text(json.dumps([valid, label]), encoding='utf-8')
					with (
						mock.patch.object(labels, 'LABELS_FILE', path),
						mock.patch.object(github, 'ghList') as read,
						mock.patch.object(github, 'gh') as write,
						contextlib.redirect_stdout(io.StringIO()),
						self.assertRaisesRegex(ValueError, 'labels.yml'),
					):
						labels.syncLabels(['app'], apply=True)
					read.assert_not_called()
					write.assert_not_called()

	def testMalformedLiveLabelsPreventWritesAndSuccessMessage(self):
		valid = {'name': 'custom', 'color': 'ffffff', 'description': None}
		invalid = (
			42,
			{},
			{'name': 'bug', 'color': 'd73a4a'},
			{'name': 42, 'color': 'ffffff', 'description': None},
			{'name': 'bug', 'color': 123456, 'description': None},
			{'name': 'bug', 'color': 'ffffff', 'description': False},
			{'name': 'CUSTOM', 'color': 'ffffff', 'description': None},
		)
		for label in invalid:
			with self.subTest(label=label):
				output = io.StringIO()
				with (
					mock.patch.object(github, 'ghList', return_value=[valid, label]),
					mock.patch.object(github, 'gh') as write,
					contextlib.redirect_stdout(output),
					self.assertRaisesRegex(ValueError, 'app.*nhãn'),
				):
					labels.syncLabels(['app'], apply=True)
				write.assert_not_called()
				self.assertNotIn('✔', output.getvalue())

	def testLabelComparisonPreservesCaseAndNullableDescription(self):
		wanted = [
			{'name': 'Bug', 'color': 'FFaa00'},
			{'name': 'Security', 'color': 'ABCDEF', 'description': 'Mô tả'},
		]
		current = [
			{'name': 'bug', 'color': 'ffaa00', 'description': None},
			{'name': 'SECURITY', 'color': 'abcdef', 'description': 'Mô tả'},
			{'name': 'custom', 'color': 'ffffff', 'description': None},
		]
		with (
			mock.patch.object(labels, 'loadLabels', return_value=wanted),
			mock.patch.object(github, 'ghList', return_value=current),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			labels.syncLabels(['app'], apply=True)
		write.assert_not_called()

	def testInvalidLabelsStopBeforeGithubRead(self):
		with tempfile.TemporaryDirectory() as folder:
			path = Path(folder) / 'labels.yml'
			for content in ('- name: [\n', 'cycle: &cycle\n  self: *cycle\n', '{}\n', '- 42\n'):
				path.write_text(content, encoding='utf-8')
				with (
					self.subTest(content=content),
					mock.patch.object(labels, 'LABELS_FILE', path),
					mock.patch.object(github, 'gh') as call,
					contextlib.redirect_stdout(io.StringIO()),
					self.assertRaisesRegex(ValueError, 'labels.yml'),
				):
					labels.syncLabels(['app'], apply=True)
				call.assert_not_called()

	def testPaginatedListsRefreshNextCall(self):
		with mock.patch.object(
			github, 'ghJson', side_effect=[[[{'name': 'cũ'}]], [[{'name': 'mới'}]]]
		) as read:
			self.assertEqual(github.ghList('repos/o/r/labels'), [{'name': 'cũ'}])
			self.assertEqual(github.ghList('repos/o/r/labels'), [{'name': 'mới'}])
		self.assertEqual(read.call_count, 2)
		self.assertEqual(read.call_args.args[-1], 'repos/o/r/labels?per_page=100')

	def testMalformedPaginatedLabelsPreventWrites(self):
		with (
			mock.patch.object(github, 'ghJson', return_value={'unexpected': []}),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaisesRegex(ValueError, 'phản hồi phân trang'),
		):
			labels.syncLabels(['app'], apply=True)
		write.assert_not_called()

	def testTruncatedGraphqlCollectionsAreNotCompared(self):
		for collection in ('rules', 'bypassActors'):
			node = {
				'name': 'x',
				'rules': {'nodes': [], 'pageInfo': {'hasNextPage': False}},
				'bypassActors': {'nodes': [], 'pageInfo': {'hasNextPage': False}},
			}
			node[collection]['pageInfo'] = {'hasNextPage': True}
			with (
				self.subTest(collection=collection),
				self.assertRaisesRegex(ValueError, 'chưa được đọc đầy đủ'),
			):
				rulesets.graphqlRuleset(node)

	def testRulesetsOnLaterRestPageAreNotCreatedAgain(self):
		for organization in (False, True):
			wanted = rulesets.orgRulesets() if organization else rulesets.rulesetsFor('.github')
			listing = [
				{'name': item['name'], 'id': index + 1} for index, (_, item) in enumerate(wanted)
			]
			current = {
				str(item['id']): dict(value, id=item['id'])
				for item, (_, value) in zip(listing, wanted, strict=True)
			}
			reads = []

			def read(*args, reads=reads, current=current, listing=listing):
				reads.append(args)
				path = next(arg for arg in args if arg.startswith(('orgs/', 'repos/')))
				if '/rulesets/' in path:
					return current[path.rsplit('/', 1)[-1]]
				return [[], listing] if '--paginate' in args and '--slurp' in args else []

			with (
				self.subTest(organization=organization),
				mock.patch.object(github, 'ghJson', read),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				if organization:
					rulesets.syncOrgRulesets(apply=True)
				else:
					rulesets.syncRulesets(['.github'], apply=True)
				write.assert_not_called()
			self.assertEqual(len(reads), len(wanted) + 1)

	def testPaginatedReadErrorPreventsRulesetWrites(self):
		with (
			mock.patch.object(github, 'ghJson', side_effect=RuntimeError('HTTP 429 ở trang sau')),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaisesRegex(RuntimeError, 'HTTP 429'),
		):
			rulesets.syncRulesets(['.github'], apply=True)
		write.assert_not_called()

	def testLabelsOnLaterPageAreNotWrittenAgain(self):
		wanted = labels.loadLabels()

		def read(*args):
			return [[], wanted] if '--paginate' in args and '--slurp' in args else []

		with (
			mock.patch.object(github, 'ghJson', read),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			labels.syncLabels(['app'], apply=True)
		write.assert_not_called()

	def testGraphqlRulesetsOnLaterPageAreCompared(self):
		wanted = [item for _, item in rulesets.orgRulesets()]
		pages = [
			{
				'data': {
					'organization': {
						'rulesets': {'nodes': wanted[:1], 'pageInfo': {'hasNextPage': True}}
					}
				}
			},
			{
				'data': {
					'organization': {
						'rulesets': {'nodes': wanted[1:], 'pageInfo': {'hasNextPage': False}}
					}
				}
			},
		]
		output = io.StringIO()
		with (
			mock.patch.object(github, 'ghJson', return_value=pages) as read,
			mock.patch.object(rulesets, 'graphqlRuleset', rulesets.graphqlVisible),
			contextlib.redirect_stdout(output),
		):
			rulesets.compareOrgRulesets()
		self.assertEqual(output.getvalue().count('đã đúng'), len(wanted))
		self.assertNotIn('chưa có', output.getvalue())
		self.assertIn('--paginate', read.call_args.args)
		self.assertIn('--slurp', read.call_args.args)
		self.assertIn('$endCursor', rulesets.ORG_RULESETS_QUERY)
		self.assertIn('pageInfo', rulesets.ORG_RULESETS_QUERY)

	def setUp(self):
		# Nạp lại từng module trước và sau mỗi test: test thay hàm gọi GitHub bằng hàm giả, không để lọt sang
		# test khác hay tệp test khác.
		self.reloadModules()
		self.addCleanup(self.reloadModules)
		self.template = (ROOT / 'repository-templates' / 'dependabot.yml').read_text(
			encoding='utf-8'
		)

	def reloadModules(self):
		for module in (github, files, rulesets, settings, teams, labels):
			importlib.reload(module)

	def ecosystems(self, text):
		return re.findall(r'package-ecosystem: (\S+)', text)

	def testDependabotKeepsOnlyUsedEcosystems(self):
		text = files.filterDependabot(self.template, {'package.json', 'README.md'})
		self.assertEqual(self.ecosystems(text), ['github-actions', 'npm'])

	def testDependabotDetectsPythonGoDocker(self):
		text = files.filterDependabot(self.template, {'pyproject.toml', 'go.mod', 'Dockerfile'})
		self.assertEqual(self.ecosystems(text), ['github-actions', 'pip', 'gomod', 'docker'])

	def testGeneratedDependabotIsValidYaml(self):
		text = files.filterDependabot(self.template, {'package.json'})
		result = subprocess.run(
			['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.dump(YAML.load(STDIN.read))'],
			input=text,
			capture_output=True,
			text=True,
			check=True,
		)
		self.assertEqual(json.loads(result.stdout)['version'], 2)

	def testSharedFilesAndRulesetPerRepository(self):
		planned = files.plannedFiles(set())
		self.assertEqual(
			sorted(planned),
			sorted(
				[
					'.editorconfig',
					'.gitattributes',
					'.github/workflows/pr-title.yml',
					'.github/workflows/branch-name.yml',
					'.github/workflows/labeler.yml',
					'.github/labeler.yml',
					'.github/CODEOWNERS',
					'.github/dependabot.yml',
					'.github/release.yml',
				]
			),
		)

	def testLanguageFiles(self):
		planned = files.plannedFiles({'package.json', 'pyproject.toml', 'Cargo.toml', 'Dockerfile'})
		for path in (
			'.prettierrc.json',
			'.nvmrc',
			'ruff.toml',
			'.python-version',
			'rustfmt.toml',
			'.dockerignore',
		):
			self.assertIn(path, planned)
		self.assertNotIn('.clang-format', planned)
		self.assertIn('indent-style = "tab"', planned['ruff.toml'])
		self.assertIn('hard_tabs = true', planned['rustfmt.toml'])
		# Workflow mẫu đọc phiên bản từ tệp này: Node.js CI (.nvmrc), Python CI (.python-version).
		self.assertEqual(planned['.nvmrc'], (ROOT / '.nvmrc').read_text(encoding='utf-8'))
		# .python-version sinh từ mise.toml (nguồn phiên bản duy nhất, ADR 0008).
		mise = (ROOT / 'mise.toml').read_text(encoding='utf-8')
		python = re.search(r'^python = "(.+)"$', mise, re.MULTILINE).group(1)
		self.assertEqual(planned['.python-version'], f'{python}\n')
		self.assertNotIn('.nvmrc', files.plannedFiles({'go.mod'}))

	def testRulesetSummaryIgnoresGithubFields(self):
		wanted = json.loads((ROOT / 'rulesets' / 'protect-main.json').read_text(encoding='utf-8'))
		live = dict(
			wanted, id=1, node_id='RRS_x', source_type='Repository', source='o/r', _links={}
		)
		live['bypass_actors'] = list(reversed(wanted['bypass_actors']))
		live['rules'] = list(reversed(wanted['rules']))
		self.assertEqual(rulesets.rulesetSummary(live), rulesets.rulesetSummary(wanted))
		changed = dict(wanted, rules=wanted['rules'][1:])
		self.assertNotEqual(rulesets.rulesetSummary(changed), rulesets.rulesetSummary(wanted))

	def testPrivateRepositorySkipsPrivateVulnerabilityReporting(self):
		self.assertIn('private-vulnerability-reporting', settings.securityEndpoints(False).values())
		self.assertNotIn(
			'private-vulnerability-reporting', settings.securityEndpoints(True).values()
		)
		self.assertIn('automated-security-fixes', settings.securityEndpoints(True).values())
		self.assertIn('immutable-releases', settings.securityEndpoints(True).values())
		# Dependabot security updates cần Dependabot alerts bật trước.
		endpoints = list(settings.securityEndpoints(False).values())
		self.assertLess(
			endpoints.index('vulnerability-alerts'), endpoints.index('automated-security-fixes')
		)

	def testRepositorySettingsMergeOverrides(self):
		own = settings.repositorySettings('.github')
		other = settings.repositorySettings('app')
		self.assertFalse(own['allow_rebase_merge'])
		self.assertTrue(own['has_discussions'])
		self.assertNotIn('has_discussions', other)
		self.assertNotIn('homepage', other)
		self.assertTrue(settings.repositorySettings('app', discussions=True)['has_discussions'])
		self.assertIn('rulesets', settings.citationKeywords())

	def testActionsPermissionsKeepEnabledState(self):
		calls = []
		live = {
			'repos/x/actions/permissions': {'enabled': True, 'allowed_actions': 'all'},
			'repos/x/actions/permissions/workflow': dict(settings.WORKFLOW_PERMISSIONS),
		}
		github.ghJson = lambda *args: live[args[1]]
		github.gh = lambda *args, **kwargs: calls.append((args, kwargs.get('stdin')))
		with contextlib.redirect_stdout(io.StringIO()):
			settings.syncActions(
				'repos/x/actions/permissions', settings.ACTIONS_PERMISSIONS, 'enabled', True
			)
		# Chỉ ghi phần khác (sha_pinning_required) và gửi lại enabled đang có — không bật, tắt Actions.
		self.assertEqual(len(calls), 1)
		self.assertEqual(json.loads(calls[0][1]), {'sha_pinning_required': True, 'enabled': True})
		# Actions đang tắt: GitHub không trả quyền — bỏ qua, không ghi.
		calls.clear()
		live['repos/x/actions/permissions'] = {'enabled': False, 'sha_pinning_required': False}
		output = io.StringIO()
		with contextlib.redirect_stdout(output):
			settings.syncActions(
				'repos/x/actions/permissions', settings.ACTIONS_PERMISSIONS, 'enabled', True
			)
		self.assertEqual(calls, [])
		# Chỉ báo đúng phần đã so được (quyền GITHUB_TOKEN), không báo quyền Actions "đã đúng".
		self.assertIn('✔ quyền GITHUB_TOKEN đã đúng', output.getvalue())
		self.assertNotIn('quyền GitHub Actions đã đúng', output.getvalue())
		# Không đọc được: không báo "đã đúng".
		github.ghJson = lambda *args: (_ for _ in ()).throw(RuntimeError('HTTP 403'))
		output = io.StringIO()
		with contextlib.redirect_stdout(output):
			settings.syncActions(
				'repos/x/actions/permissions', settings.ACTIONS_PERMISSIONS, 'enabled', True
			)
		self.assertNotIn('đã đúng', output.getvalue())

	def testOrgRulesetFilesMatchGenerated(self):
		# Tệp để import trên web phải đúng bằng orgRulesets() sinh từ bản cấp repository.
		for source, ruleset in rulesets.orgRulesets():
			self.assertEqual(json.loads(source.read_text(encoding='utf-8')), ruleset, source.name)

	def testOrgCodeScanningRuleMatchesGraphql(self):
		# Dạng GraphQL trả về cho quy tắc code scanning trên web phải khớp quy tắc trong tệp cấp tổ chức.
		node = {
			'type': 'CODE_SCANNING',
			'parameters': {
				'__typename': 'CodeScanningParameters',
				'codeScanningTools': [
					{
						'tool': 'CodeQL',
						'alertsThreshold': 'errors',
						'securityAlertsThreshold': 'high_or_higher',
					}
				],
			},
		}
		live = {
			'name': 'x',
			'target': 'BRANCH',
			'enforcement': 'ACTIVE',
			'conditions': {},
			'bypassActors': {'nodes': [], 'pageInfo': {'hasNextPage': False}},
			'rules': {'nodes': [node], 'pageInfo': {'hasNextPage': False}},
		}
		self.assertEqual(rulesets.graphqlRuleset(live)['rules'], [rulesets.ORG_CODE_SCANNING_RULE])
		# Chỉ bản cấp tổ chức có code scanning, như trên web.
		self.assertIn(rulesets.ORG_CODE_SCANNING_RULE, rulesets.orgRuleset()['rules'])
		self.assertNotIn('code_scanning', [r['type'] for r in rulesets.rulesetFor('app')['rules']])

	def testCompareOrgRulesetsViaGraphql(self):
		# Dạng GraphQL trả về cho Protect Release Tags (Organization) trên web.
		node = {
			'name': 'Protect Release Tags (Organization)',
			'target': 'TAG',
			'enforcement': 'ACTIVE',
			'conditions': {
				'refName': {
					'include': ['refs/tags/v*', 'refs/tags/Stable.v*', 'refs/tags/Beta.v*'],
					'exclude': [],
				},
				'repositoryName': {'include': ['~ALL'], 'exclude': [], 'protected': False},
			},
			'bypassActors': {
				'pageInfo': {'hasNextPage': False},
				'nodes': [
					{
						'bypassMode': 'ALWAYS',
						'organizationAdmin': True,
						'deployKey': False,
						'repositoryRoleDatabaseId': None,
						'actor': None,
					}
				],
			},
			'rules': {
				'pageInfo': {'hasNextPage': False},
				'nodes': [
					{'type': 'CREATION', 'parameters': None},
					{'type': 'UPDATE', 'parameters': {'__typename': 'UpdateParameters'}},
					{'type': 'DELETION', 'parameters': None},
					{'type': 'NON_FAST_FORWARD', 'parameters': None},
					{'type': 'REQUIRED_SIGNATURES', 'parameters': None},
					{
						'type': 'REQUIRED_STATUS_CHECKS',
						'parameters': {
							'__typename': 'RequiredStatusChecksParameters',
							'doNotEnforceOnCreate': False,
							'strictRequiredStatusChecksPolicy': True,
							'requiredStatusChecks': [],
						},
					},
				],
			},
		}
		wanted = rulesets.graphqlVisible(rulesets.orgTagRuleset())
		live = rulesets.graphqlRuleset(node)
		self.assertEqual(rulesets.rulesetSummary(live), rulesets.rulesetSummary(wanted))
		includes = node['conditions']['refName']['include']
		node['conditions']['refName']['include'] = ['refs/tags/v*']
		self.assertNotEqual(
			rulesets.rulesetSummary(rulesets.graphqlRuleset(node)),
			rulesets.rulesetSummary(wanted),
		)
		node['conditions']['refName']['include'] = includes
		node['rules']['nodes'].pop()
		self.assertNotEqual(
			rulesets.rulesetSummary(rulesets.graphqlRuleset(node)),
			rulesets.rulesetSummary(wanted),
		)
		# Push ruleset: không có refName, tham số của quy tắc push đổi sang dạng REST.
		pushes = rulesets.orgPushRuleset()
		parameters = {rule['type']: rule['parameters'] for rule in pushes['rules']}
		paths = parameters['file_path_restriction']['restricted_file_paths']
		extensions = parameters['file_extension_restriction']['restricted_file_extensions']
		node = {
			'name': pushes['name'],
			'target': 'PUSH',
			'enforcement': 'ACTIVE',
			'conditions': {
				'refName': None,
				'repositoryName': {'include': ['~ALL'], 'exclude': [], 'protected': False},
			},
			'bypassActors': node['bypassActors'],
			'rules': {
				'pageInfo': {'hasNextPage': False},
				'nodes': [
					{
						'type': 'FILE_PATH_RESTRICTION',
						'parameters': {
							'__typename': 'FilePathRestrictionParameters',
							'restrictedFilePaths': paths,
						},
					},
					{
						'type': 'FILE_EXTENSION_RESTRICTION',
						'parameters': {
							'__typename': 'FileExtensionRestrictionParameters',
							'restrictedFileExtensions': extensions,
						},
					},
					{
						'type': 'MAX_FILE_SIZE',
						'parameters': {'__typename': 'MaxFileSizeParameters', 'maxFileSize': 10},
					},
					{
						'type': 'MAX_FILE_PATH_LENGTH',
						'parameters': {
							'__typename': 'MaxFilePathLengthParameters',
							'maxFilePathLength': 200,
						},
					},
				],
			},
		}
		self.assertEqual(
			rulesets.rulesetSummary(rulesets.graphqlRuleset(node)),
			rulesets.rulesetSummary(rulesets.graphqlVisible(pushes)),
		)
		main = rulesets.graphqlVisible(rulesets.orgRuleset())
		for rule in main['rules']:
			self.assertNotIn(
				'require_extra_approval_for_unattributed_changes', rule.get('parameters', {})
			)

	def testTeamsAlreadyCorrectAreNotWritten(self):
		calls = []
		github.ghExists = lambda endpoint: True
		details = {
			team: {'name': name, 'description': description, 'privacy': privacy}
			for team, (name, _, privacy, description) in teams.TEAMS.items()
		}
		teams.teamDetails = lambda team: details[team]
		teams.teamRole = lambda team, user: 'maintainer'
		# Quyền cao hơn (admin) đã đủ cho mọi team — không hạ quyền.
		teams.teamPermission = lambda team, repo: 'admin'
		github.gh = lambda *args, **kwargs: (
			calls.append(args) or json.dumps({'role': 'maintainer', 'state': 'active'})
		)
		output = io.StringIO()
		with contextlib.redirect_stdout(output):
			teams.syncTeams(['.github', 'app'], apply=True)
		self.assertEqual(output.getvalue().count('✔ đủ người quản trị'), len(teams.TEAMS))
		self.assertEqual(calls, [])
		# Chỉ ghi phần còn thiếu: một người chưa là maintainer, một repository chưa đủ quyền.
		teams.teamRole = lambda team, user: (
			'member' if (team, user) == ('maintainers', 'trongtoandl81') else 'maintainer'
		)
		teams.teamPermission = lambda team, repo: (
			'write' if (team, repo) == ('maintainers', 'app') else 'admin'
		)
		with contextlib.redirect_stdout(io.StringIO()):
			teams.syncTeams(['.github', 'app'], apply=True)
		self.assertEqual(
			[args[3] for args in calls],
			[
				'orgs/TOANQUYNHLLC/teams/maintainers/memberships/trongtoandl81',
				'orgs/TOANQUYNHLLC/teams/maintainers/repos/TOANQUYNHLLC/app',
			],
		)

	def testSettingsReadActionsEarlyButPrintInOrder(self):
		# Quyền Actions đọc song song với cài đặt repository (bắt đầu trước khi đọc xong repository); đầu ra vẫn
		# theo thứ tự cài đặt → bảo mật → quyền Actions.
		started = []
		repository = 'repos/TOANQUYNHLLC/app'

		def ghJson(*args):
			path = args[-1]
			started.append(path)
			if path == repository:
				time.sleep(0.2)
				return dict(
					settings.repositorySettings('app'),
					private=True,
					security_and_analysis={
						name: {'status': 'disabled'} for name in settings.SECURITY_FEATURES
					},
				)
			if path.endswith('/actions/permissions'):
				return dict(settings.ACTIONS_PERMISSIONS, enabled=True)
			if path.endswith('/actions/permissions/workflow'):
				return dict(settings.WORKFLOW_PERMISSIONS)
			return {'enabled': True}

		github.ghJson = ghJson
		github.ghExists = lambda endpoint: True
		output = io.StringIO()
		with contextlib.redirect_stdout(output):
			settings.syncSettings(['app'], apply=False, discussions=False)
		lines = output.getvalue().splitlines()
		self.assertEqual(lines[0], '== TOANQUYNHLLC/app')
		order = [
			next(index for index, line in enumerate(lines) if text in line)
			for text in (
				'cài đặt repository đã đúng',
				'bật secret_scanning',
				'quyền GitHub Actions đã đúng',
			)
		]
		self.assertEqual(order, sorted(order))
		# Đọc quyền Actions bắt đầu trước khi đọc trạng thái bảo mật (việc chỉ làm sau khi có cài đặt repository).
		security = next(
			index
			for index, path in enumerate(started)
			if path != repository and '/actions/' not in path
		)
		self.assertLess(started.index(f'{repository}/actions/permissions'), security, started)

	def testMissingTeamNeedsEveryMaintainerAndRepository(self):
		# Chi tiết team, vai trò, quyền đọc cùng lúc: team chưa có (404) thì mọi người, mọi repository cần thêm.
		def notFound(*args):
			raise RuntimeError('HTTP 404')

		teams.teamDetails = notFound
		teams.teamRole = lambda team, user: None
		teams.teamPermission = lambda team, repo: None
		self.assertEqual(
			teams.teamState('qa', ['.github', 'app']),
			(False, {}, {}, list(teams.MAINTAINERS), ['.github', 'app']),
		)

	def testListReposReadsEveryPageWithoutArchived(self):
		calls = []

		def gh(*args, **kwargs):
			calls.append(args)
			return 'app\n.github\n'

		github.gh = gh
		self.assertEqual(github.listRepos(None), ['.github', 'app'])
		self.assertIn('--paginate', calls[0])
		self.assertIn('select(.archived | not)', calls[0][-1])
		self.assertEqual(github.listRepos('app'), ['app'])
		self.assertEqual(len(calls), 1)

	def testExistenceCheckDistinguishesMissingFromReadErrors(self):
		for message in ('HTTP 403', 'HTTP 429', 'HTTP 500', 'mất mạng', 'HTTP 4040'):
			with (
				self.subTest(message=message),
				mock.patch.object(github, 'gh', side_effect=RuntimeError(message)),
				self.assertRaisesRegex(RuntimeError, message),
			):
				github.ghExists('repos/o/r/contents/file')
		with mock.patch.object(github, 'gh', side_effect=RuntimeError('Not Found (HTTP 404)')):
			self.assertFalse(github.ghExists('repos/o/r/contents/file'))

	def testTeamReadErrorsPreventWrites(self):
		for failingPath in ('/teams/admins', '/memberships/', '/repos/'):

			def read(*args, failingPath=failingPath):
				path = args[-1]
				if path.endswith(failingPath) or failingPath in path:
					raise RuntimeError('Forbidden (HTTP 403)')
				if '/memberships/' in path:
					return {'role': 'maintainer', 'state': 'active'}
				if '/repos/' in path:
					return {'role_name': 'admin'}
				team = path.rsplit('/', 1)[-1]
				name, _, privacy, description = teams.TEAMS[team]
				return {'name': name, 'privacy': privacy, 'description': description}

			with (
				self.subTest(path=failingPath),
				mock.patch.object(github, 'ghJson', read),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
				self.assertRaisesRegex(RuntimeError, 'HTTP 403'),
			):
				teams.syncTeams(['app'], apply=True)
			write.assert_not_called()

	def testSecurityUnreadStatusIsNotEnabled(self):
		output = io.StringIO()
		with (
			mock.patch.object(github, 'ghJson', return_value={'enabled': True}),
			mock.patch.object(
				github, 'gh', side_effect=RuntimeError('Forbidden (HTTP 403)')
			) as call,
			contextlib.redirect_stdout(output),
		):
			settings.syncSecurity('app', {'private': True}, apply=True)
		self.assertIn('không đọc được trạng thái', output.getvalue())
		self.assertNotIn('đã bật Dependabot alerts', output.getvalue())
		self.assertFalse(
			[args for args, _ in call.call_args_list if '-X' in args and 'PUT' in args]
		)

	def testFilesReadFailurePreventsWrites(self):
		with (
			mock.patch.object(github, 'defaultBranch', return_value='main'),
			mock.patch.object(github, 'ghJson', side_effect=RuntimeError('HTTP 403')),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaisesRegex(RuntimeError, 'HTTP 403'),
		):
			files.syncFiles(['app'], apply=True)
		write.assert_not_called()

	def testFilesUseOneTreeAtFixedCommitAndRefreshNextRun(self):
		calls, writes, bodies = [], [], []
		planned = files.plannedFiles({'package.json'})
		paths = set(planned) - {'.nvmrc'}

		def read(*args):
			path = args[-1]
			calls.append(path)
			if path.endswith('/git/ref/heads/main'):
				return {'object': {'sha': 'abc123'}}
			if path.endswith('/git/trees/abc123?recursive=1'):
				return {
					'truncated': False,
					'tree': [{'path': name, 'type': 'blob'} for name in paths | {'package.json'}],
				}
			self.fail(f'Request đọc không cần thiết: {path}')

		def write(*args, **kwargs):
			writes.append(args)
			if kwargs.get('stdin'):
				bodies.append(json.loads(kwargs['stdin']))
			return 'url'

		with (
			mock.patch.object(github, 'defaultBranch', return_value='main'),
			mock.patch.object(github, 'ghJson', read),
			mock.patch.object(github, 'ghExists', return_value=False),
			mock.patch.object(github, 'gh', write),
			contextlib.redirect_stdout(io.StringIO()),
		):
			files.syncFiles(['app'], apply=True)
			paths.add('.nvmrc')
			files.syncFiles(['app'], apply=True)
		self.assertEqual(len(calls), 4)
		self.assertEqual(len([call for call in writes if call[:2] == ('api', 'graphql')]), 1)
		self.assertIn('sha=abc123', writes[0])
		self.assertIn('createCommitOnBranch', bodies[0]['query'])
		commit = bodies[0]['variables']['input']
		self.assertEqual(commit['expectedHeadOid'], 'abc123')
		self.assertEqual(
			commit['branch'],
			{'repositoryNameWithOwner': 'TOANQUYNHLLC/app', 'branchName': files.SYNC_BRANCH},
		)
		self.assertEqual(
			[entry['path'] for entry in commit['fileChanges']['additions']], ['.nvmrc']
		)

	def testTruncatedTreeChecksPathsIndividually(self):
		def read(*args):
			path = args[-1]
			if '/git/ref/' in path:
				return {'object': {'sha': 'abc123'}}
			if '/git/trees/' in path:
				return {'truncated': True, 'tree': []}
			self.assertTrue(path.endswith('/contents?ref=abc123'), path)
			return [{'name': 'package.json', 'type': 'file'}]

		with (
			mock.patch.object(github, 'defaultBranch', return_value='main'),
			mock.patch.object(github, 'ghJson', read),
			mock.patch.object(github, 'ghExists', return_value=True) as exists,
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			files.syncFiles(['app'], apply=True)
		self.assertEqual(exists.call_count, len(files.plannedFiles({'package.json'})))
		self.assertTrue(all(args[0].endswith('?ref=abc123') for args, _ in exists.call_args_list))
		write.assert_not_called()

	def testFilesCommitFailureDoesNotOpenPartialPr(self):
		def read(*args):
			if '/git/ref/' in args[-1]:
				return {'object': {'sha': 'abc123'}}
			return {'truncated': False, 'tree': [{'path': 'package.json', 'type': 'blob'}]}

		def write(*args, **kwargs):
			if args[:2] == ('api', 'graphql'):
				commit = json.loads(kwargs['stdin'])['variables']['input']
				actual = {
					entry['path']: base64.b64decode(entry['contents']).decode('utf-8')
					for entry in commit['fileChanges']['additions']
				}
				self.assertEqual(actual, files.plannedFiles({'package.json'}))
				self.assertEqual(commit['expectedHeadOid'], 'abc123')
				raise RuntimeError('branch đã đổi')
			self.assertEqual(args[:2], ('api', 'repos/TOANQUYNHLLC/app/git/refs'))

		with (
			mock.patch.object(github, 'defaultBranch', return_value='main'),
			mock.patch.object(github, 'ghJson', read),
			mock.patch.object(github, 'ghExists', return_value=False),
			mock.patch.object(github, 'gh', write),
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaisesRegex(RuntimeError, 'branch đã đổi'),
		):
			files.syncFiles(['app'], apply=True)

	def testEmptyRepositoryIsSkippedOnlyForMissingDefaultRef(self):
		output = io.StringIO()
		with (
			mock.patch.object(github, 'defaultBranch', return_value='main'),
			mock.patch.object(
				github, 'ghJson', side_effect=RuntimeError('Not Found (HTTP 404)')
			) as read,
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(output),
		):
			files.syncFiles(['app'], apply=True)
		self.assertIn('repository trống', output.getvalue())
		self.assertEqual(read.call_args.args[-1], 'repos/TOANQUYNHLLC/app/git/ref/heads/main')
		write.assert_not_called()

	def testTeamDescriptionDriftIsPatched(self):
		calls = []
		github.ghExists = lambda endpoint: True
		teams.teamRole = lambda team, user: 'maintainer'
		teams.teamPermission = lambda team, repo: 'admin'
		teams.teamDetails = lambda team: {
			'name': teams.TEAMS[team][0],
			'description': 'mô tả cũ' if team == 'qa' else teams.TEAMS[team][3],
			'privacy': teams.TEAMS[team][2],
		}
		github.gh = lambda *args, **kwargs: calls.append((args, kwargs.get('stdin')))
		with contextlib.redirect_stdout(io.StringIO()):
			teams.syncTeams(['.github'], apply=True)
		self.assertEqual([args[3] for args, _ in calls], ['orgs/TOANQUYNHLLC/teams/qa'])
		self.assertEqual(json.loads(calls[0][1]), {'description': teams.TEAMS['qa'][3]})

	def testLabelsOnlyWriteDifferences(self):
		calls = []
		wanted = labels.loadLabels()
		live = [dict(label) for label in wanted[1:]]
		live[0]['color'] = '000000'
		github.ghJson = lambda *args: [live]
		github.gh = lambda *args, **kwargs: calls.append(args)
		with contextlib.redirect_stdout(io.StringIO()):
			labels.syncLabels(['app'], apply=True)
		# Một nhãn thiếu (tạo) và một nhãn sai màu (cập nhật); nhãn đúng không ghi lại.
		self.assertEqual([args[2] for args in calls], [wanted[0]['name'], wanted[1]['name']])

	def testLabelsRemindOrganizationDefaultsOnce(self):
		# Lệnh chỉ đồng bộ repository đã có; nhắc một lần rằng nhãn mặc định cấp tổ chức (không có API) phải làm trên
		# web — dù đồng bộ nhiều repository và không có gì để ghi.
		live = [dict(label) for label in labels.loadLabels()]
		github.ghJson = lambda *args: [live]
		github.gh = lambda *args, **kwargs: self.fail(f'không được ghi: {args}')
		output = io.StringIO()
		with contextlib.redirect_stdout(output):
			labels.syncLabels(['app', 'web'], apply=True)
		self.assertEqual(output.getvalue().count('Nhãn mặc định cho repository mới'), 1)
		self.assertIn('nhập trên web theo labels.yml', output.getvalue())

	def testProtectMainPerRepository(self):
		def checks(ruleset):
			return [
				check['context']
				for rule in ruleset['rules']
				if rule['type'] == 'required_status_checks'
				for check in rule['parameters']['required_status_checks']
			]

		self.assertEqual(
			[ruleset['name'] for _, ruleset in rulesets.rulesetsFor('app')],
			['Protect Main', 'Protect Release Tags'],
		)
		own = rulesets.rulesetFor('.github')
		other = rulesets.rulesetFor('app')
		self.assertEqual(own['name'], 'Protect Main')
		self.assertEqual(other['name'], 'Protect Main')
		self.assertEqual(len(checks(own)), 5)
		self.assertEqual(
			sorted(checks(other)), ['Kiểm tra tiêu đề Pull Request', 'Kiểm tra tên branch']
		)

	def testPreviewRunsEveryCommandInOrder(self):
		# make org-preview: mọi lệnh chạy song song trong một tiến trình nhưng in đúng thứ tự COMMANDS, đầu ra
		# của từng lệnh không lẫn nhau; một lệnh lỗi thì mã thoát 1.
		module = loadScript('org-setup')

		def run(command, repos, apply, discussions=False):
			# Lệnh đầu chậm nhất: nếu đầu ra không tách theo luồng, dòng của nó sẽ in sau cùng.
			time.sleep(0.2 if command == module.COMMANDS[0] else 0)
			print(f'kết quả {command}')
			if command == 'team':
				raise RuntimeError('gh lỗi')

		output = io.StringIO()
		with (
			mock.patch.object(module, 'runCommand', run),
			contextlib.redirect_stdout(output),
			contextlib.redirect_stderr(io.StringIO()),
		):
			code = module.previewAll(['app'])
		self.assertEqual(code, 1)
		self.assertEqual(
			re.findall(r'^kết quả (\S+)$', output.getvalue(), re.MULTILINE), list(module.COMMANDS)
		)
		self.assertIn('❌ gh lỗi', output.getvalue())
		self.assertEqual(
			subprocess.run(
				['make', '-n', 'org-preview'], cwd=ROOT, capture_output=True, text=True, check=True
			).stdout.strip(),
			'python3 scripts/org-setup.py preview',
		)

	def testPreviewChecksLoginOnce(self):
		# Chưa đăng nhập GitHub CLI: dừng trước khi chạy lệnh nào, báo một lần.
		module = loadScript('org-setup')
		with (
			mock.patch.object(module.github, 'gh', side_effect=RuntimeError('chưa đăng nhập')),
			mock.patch.object(module, 'runCommand') as run,
			mock.patch.object(module.sys, 'argv', ['org-setup.py', 'preview']),
			self.assertRaises(SystemExit) as stopped,
		):
			module.main()
		self.assertIn('gh auth login', str(stopped.exception.code))
		run.assert_not_called()

	def testCommandReadErrorReturnsFailureWithoutTraceback(self):
		module = loadScript('org-setup')
		output = io.StringIO()
		with (
			mock.patch.object(module, 'signedIn', return_value=True),
			mock.patch.object(module.github, 'listRepos', return_value=['app']),
			mock.patch.object(module, 'runCommand', side_effect=RuntimeError('HTTP 403')),
			mock.patch.object(module.sys, 'argv', ['org-setup.py', 'team', '--apply']),
			contextlib.redirect_stderr(output),
		):
			self.assertEqual(module.main(), 1)
		self.assertIn('HTTP 403', output.getvalue())
		self.assertNotIn('Traceback', output.getvalue())

	def testFailedListingIsNotRequestedTwice(self):
		module = loadScript('org-setup')
		output = io.StringIO()
		with (
			mock.patch.object(module, 'signedIn', return_value=True),
			mock.patch.object(
				module.github, 'listRepos', side_effect=RuntimeError('HTTP 429')
			) as listing,
			mock.patch.object(module, 'runCommand') as run,
			mock.patch.object(module.sys, 'argv', ['org-setup.py', 'files']),
			contextlib.redirect_stderr(output),
		):
			self.assertEqual(module.main(), 1)
		listing.assert_called_once()
		run.assert_not_called()
		self.assertIn('HTTP 429', output.getvalue())


if __name__ == '__main__':
	unittest.main()
