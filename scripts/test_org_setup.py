"""Test tự động cho scripts/org-setup.py và gói scripts/orgsetup/: tệp dùng chung, ruleset, cài đặt, team, nhãn.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import base64
import contextlib
import copy
import importlib
import io
import json
import re
import subprocess
import sys
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


def teamFixture(team):
	name, _, privacy, description = teams.TEAMS[team]
	parent = teams.TEAM_PARENTS.get(team)
	return {
		'name': name,
		'privacy': privacy,
		'description': description,
		'parent': {'slug': parent} if parent else None,
	}


class OrgSetupTest(unittest.TestCase):
	def testRequiredReviewersAreValidatedBeforeAnyRulesetWrite(self):
		valid = {
			'file_patterns': ['src/**'],
			'minimum_approvals': 1,
			'reviewer': {'id': 7, 'type': 'Team'},
		}
		invalid = [42, {}, {'minimum_approvals': 1, 'reviewer': valid['reviewer']}]
		invalid.extend(dict(valid, file_patterns=value) for value in (None, 'src/**', [42]))
		invalid.append({'file_patterns': valid['file_patterns'], 'reviewer': valid['reviewer']})
		invalid.extend(dict(valid, minimum_approvals=value) for value in (None, '1', True, -1))
		invalid.extend(
			dict(valid, reviewer=value)
			for value in (
				None,
				[],
				{},
				{'id': 7},
				{'id': 7, 'type': 'User'},
				{'id': True, 'type': 'Team'},
				{'id': 0, 'type': 'Team'},
				{'id': '7', 'type': 'Team'},
			)
		)
		for organization in (False, True):
			for reviewer in invalid:
				wanted = rulesets.orgRulesets() if organization else rulesets.rulesetsFor('.github')
				wanted[-1][1]['rules'].append(
					{'type': 'pull_request', 'parameters': {'required_reviewers': [reviewer]}}
				)
				with (
					self.subTest(organization=organization, reviewer=reviewer),
					mock.patch.object(
						rulesets,
						'orgRulesets' if organization else 'rulesetsFor',
						return_value=wanted,
					),
					mock.patch.object(github, 'ghList', return_value=[]),
					mock.patch.object(github, 'ghJson') as read,
					mock.patch.object(github, 'gh') as write,
					contextlib.redirect_stdout(io.StringIO()),
					self.assertRaisesRegex((ValueError, TypeError), 'required_reviewers'),
				):
					if organization:
						rulesets.syncOrgRulesets(apply=True)
					else:
						rulesets.syncRulesets(['.github'], apply=True)
				read.assert_not_called()
				write.assert_not_called()

	def testRequiredReviewersAllowZeroApprovalsAndPreservePayload(self):
		wanted = rulesets.rulesetFor('.github')
		parameters = next(
			rule['parameters'] for rule in wanted['rules'] if rule['type'] == 'pull_request'
		)
		parameters['required_reviewers'] = [
			{
				'file_patterns': ['src/**', 'tests/**'],
				'minimum_approvals': count,
				'reviewer': {'id': count + 7, 'type': 'Team'},
			}
			for count in (0, 1)
		]
		original = copy.deepcopy(wanted)
		with (
			mock.patch.object(github, 'gh', return_value='{"id": 7}') as write,
			mock.patch.object(
				github, 'ghJson', return_value=self.reverseRulesetLists(dict(wanted, id=7))
			),
		):
			rulesets.applyRuleset('repos/TOANQUYNHLLC/.github/rulesets', wanted, 7)
		self.assertEqual(json.loads(write.call_args.kwargs['stdin']), original)
		self.assertEqual(wanted, original)

	def testGraphqlReviewerNodeIdsMatchRestTeamIds(self):
		reviewers = [
			{
				'filePatterns': ['src/**'],
				'minimumApprovals': count,
				'reviewerId': f'TEAM_NODE_{count + 7}',
			}
			for count in (0, 1, 0)
		]
		node = {
			'name': 'x',
			'target': 'BRANCH',
			'enforcement': 'ACTIVE',
			'conditions': {},
			'bypassActors': {'pageInfo': {'hasNextPage': False}, 'nodes': []},
			'rules': {
				'pageInfo': {'hasNextPage': False},
				'nodes': [{'type': 'PULL_REQUEST', 'parameters': {'requiredReviewers': reviewers}}],
			},
		}
		original = copy.deepcopy(node)
		with mock.patch.object(
			github,
			'ghJson',
			return_value={
				'data': {
					'nodes': [
						{'id': f'TEAM_NODE_{teamId}', '__typename': 'Team', 'databaseId': teamId}
						for teamId in (8, 7)
					]
				}
			},
		) as read:
			live = rulesets.graphqlRuleset(node)
		expected = dict(
			live,
			rules=[
				{
					'type': 'pull_request',
					'parameters': {
						'required_reviewers': [
							{
								'file_patterns': ['src/**'],
								'minimum_approvals': count,
								'reviewer': {'id': count + 7, 'type': 'Team'},
							}
							for count in (0, 1, 0)
						]
					},
				}
			],
		)
		self.assertEqual(rulesets.rulesetSummary(live), rulesets.rulesetSummary(expected))
		self.assertEqual(node, original)
		read.assert_called_once()
		self.assertIn('nodes(ids: ["TEAM_NODE_7", "TEAM_NODE_8"])', read.call_args.args[-1])

	def testGraphqlReviewersRequireVerifiedTeamIdentity(self):
		reviewers = [
			{'file_patterns': ['src/**'], 'minimum_approvals': 0, 'reviewer_id': 'TEAM_NODE_7'}
		]
		team = {'id': 'TEAM_NODE_7', '__typename': 'Team', 'databaseId': 7}
		for response in (
			None,
			{},
			{'data': {'nodes': None}},
			{'data': {'nodes': []}},
			{'data': {'nodes': [None]}},
			{'data': {'nodes': [team, team]}},
			{'data': {'nodes': [dict(team, id='OTHER_NODE')]}},
			{'data': {'nodes': [dict(team, __typename='User')]}},
			{'data': {'nodes': [dict(team, databaseId=True)]}},
			{'data': {'nodes': [dict(team, databaseId=0)]}},
			{'data': {'nodes': [team]}, 'errors': [{'message': 'Không có quyền'}]},
		):
			with (
				self.subTest(response=response),
				mock.patch.object(github, 'ghJson', return_value=response),
				self.assertRaisesRegex(ValueError, 'required_reviewers GraphQL'),
			):
				rulesets.graphqlRequiredReviewers(reviewers)
		for invalid in (None, {}, [42], [{}], [dict(reviewers[0], reviewer_id=7)]):
			with (
				self.subTest(invalid=invalid),
				mock.patch.object(github, 'ghJson') as read,
				self.assertRaisesRegex(ValueError, 'required_reviewers GraphQL'),
			):
				rulesets.graphqlRequiredReviewers(invalid)
			read.assert_not_called()
		with mock.patch.object(github, 'ghJson') as read:
			self.assertEqual(rulesets.graphqlRequiredReviewers([]), [])
		read.assert_not_called()

	def testOptionalNestedRulesetDefaultsRemainValid(self):
		for integration in ({}, {'integration_id': None}, {'integration_id': 15368}):
			wanted = rulesets.rulesetFor('.github')
			for rule in wanted['rules']:
				if rule['type'] == 'required_status_checks':
					rule['parameters'] = {
						'strict_required_status_checks_policy': True,
						'required_status_checks': [{'context': 'CI', **integration}],
					}
				elif rule['type'] == 'pull_request':
					rule['parameters']['dismissal_restriction'] = {'enabled': False}
			with (
				self.subTest(integration=integration),
				mock.patch.object(
					rulesets, 'rulesetsFor', return_value=[(rulesets.RULESET_FILE, wanted)]
				),
				mock.patch.object(
					github, 'ghList', return_value=[{'id': 1, 'name': wanted['name']}]
				),
				mock.patch.object(github, 'ghJson', return_value=dict(wanted, id=1)),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()) as output,
			):
				rulesets.syncRulesets(['.github'], apply=True)
			write.assert_not_called()
			self.assertIn('đã đúng', output.getvalue())

	def testInvalidNestedRulesetParametersStopBeforeAnyWrites(self):
		cases = (
			('pull_request', {'dismissal_restriction': {}}),
			('pull_request', {'dismissal_restriction': {'enabled': 'true', 'allowed_actors': []}}),
			('pull_request', {'dismissal_restriction': {'enabled': True, 'allowed_actors': None}}),
			('pull_request', {'dismissal_restriction': {'enabled': True, 'allowed_actors': [42]}}),
			(
				'pull_request',
				{
					'dismissal_restriction': {
						'enabled': True,
						'allowed_actors': [{'id': True, 'type': 'User'}],
					}
				},
			),
			(
				'pull_request',
				{
					'dismissal_restriction': {
						'enabled': True,
						'allowed_actors': [{'id': 0, 'type': 'User'}],
					}
				},
			),
			(
				'pull_request',
				{
					'dismissal_restriction': {
						'enabled': True,
						'allowed_actors': [{'id': 1, 'type': 'Unknown'}],
					}
				},
			),
			('required_status_checks', {}),
			(
				'required_status_checks',
				{'strict_required_status_checks_policy': 'true', 'required_status_checks': []},
			),
			(
				'required_status_checks',
				{
					'strict_required_status_checks_policy': True,
					'do_not_enforce_on_create': 1,
					'required_status_checks': [],
				},
			),
			(
				'required_status_checks',
				{'strict_required_status_checks_policy': True, 'required_status_checks': None},
			),
			(
				'required_status_checks',
				{'strict_required_status_checks_policy': True, 'required_status_checks': [42]},
			),
			(
				'required_status_checks',
				{'strict_required_status_checks_policy': True, 'required_status_checks': [{}]},
			),
			(
				'required_status_checks',
				{
					'strict_required_status_checks_policy': True,
					'required_status_checks': [{'context': ' '}],
				},
			),
			(
				'required_status_checks',
				{
					'strict_required_status_checks_policy': True,
					'required_status_checks': [{'context': 'CI', 'integration_id': True}],
				},
			),
			(
				'required_status_checks',
				{
					'strict_required_status_checks_policy': True,
					'required_status_checks': [{'context': 'CI', 'integration_id': '15368'}],
				},
			),
		)
		for organization in (False, True):
			for ruleType, parameters in cases:
				wanted = rulesets.orgRulesets() if organization else rulesets.rulesetsFor('.github')
				wanted[-1][1]['rules'].append({'type': ruleType, 'parameters': parameters})
				with (
					self.subTest(
						organization=organization, ruleType=ruleType, parameters=parameters
					),
					mock.patch.object(
						rulesets,
						'orgRulesets' if organization else 'rulesetsFor',
						return_value=wanted,
					),
					mock.patch.object(github, 'ghList', return_value=[]),
					mock.patch.object(github, 'ghJson') as read,
					mock.patch.object(github, 'gh') as write,
					contextlib.redirect_stdout(io.StringIO()),
					self.assertRaisesRegex((ValueError, TypeError), ruleType),
				):
					if organization:
						rulesets.syncOrgRulesets(apply=True)
					else:
						rulesets.syncRulesets(['.github'], apply=True)
				read.assert_not_called()
				write.assert_not_called()

	def reverseRulesetLists(self, value):
		"""Giả lập API trả danh sách theo thứ tự khác, giữ nguyên nội dung."""
		result = copy.deepcopy(value)
		for condition in result['conditions'].values():
			for key in ('include', 'exclude'):
				if isinstance(condition.get(key), list):
					condition[key].reverse()
		for rule in result['rules']:
			parameters = rule.get('parameters', {})
			for key in (
				'allowed_merge_methods',
				'required_status_checks',
				'code_scanning_tools',
				'restricted_file_paths',
				'restricted_file_extensions',
				'required_reviewers',
			):
				if isinstance(parameters.get(key), list):
					parameters[key].reverse()
			if 'dismissal_restriction' in parameters:
				parameters['dismissal_restriction']['allowed_actors'].reverse()
		return result

	def testReorderedRulesetListsDoNotCauseWrites(self):
		for organization in (False, True):
			wanted = rulesets.orgRulesets() if organization else rulesets.rulesetsFor('.github')
			listing = [
				{'name': item['name'], 'id': index + 1} for index, (_, item) in enumerate(wanted)
			]
			live = {
				index + 1: self.reverseRulesetLists(dict(item, id=index + 1))
				for index, (_, item) in enumerate(wanted)
			}
			with (
				self.subTest(organization=organization),
				mock.patch.object(github, 'ghList', return_value=listing),
				mock.patch.object(
					github,
					'ghJson',
					side_effect=lambda *args, live=live: live[int(args[-1].rsplit('/', 1)[-1])],
				),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				if organization:
					rulesets.syncOrgRulesets(apply=True)
				else:
					rulesets.syncRulesets(['.github'], apply=True)
			write.assert_not_called()

	def testRulesetReadbackAcceptsEquivalentListOrders(self):
		wanted = rulesets.rulesetFor('.github')
		with (
			mock.patch.object(github, 'gh', return_value='{"id": 7}'),
			mock.patch.object(
				github, 'ghJson', return_value=self.reverseRulesetLists(dict(wanted, id=7))
			),
		):
			rulesets.applyRuleset('repos/TOANQUYNHLLC/.github/rulesets', wanted, 7)

	def testRulesetSummaryKeepsInputsAndMeaningfulListDifferences(self):
		wanted = rulesets.orgTagRuleset()
		wanted['conditions']['ref_name']['exclude'] = ['refs/tags/dev-*', 'refs/tags/test-*']
		wanted['conditions']['repository_name']['include'] = ['app', 'website']
		wanted['conditions']['repository_name']['exclude'] = ['legacy', 'archive']
		original = copy.deepcopy(wanted)
		live = self.reverseRulesetLists(wanted)
		before = copy.deepcopy(live)
		self.assertEqual(rulesets.rulesetSummary(wanted), rulesets.rulesetSummary(live))
		self.assertEqual(wanted, original)
		self.assertEqual(live, before)
		live['conditions']['ref_name']['include'].pop()
		self.assertNotEqual(rulesets.rulesetSummary(wanted), rulesets.rulesetSummary(live))
		for value in ('merge', 'squash'):
			wanted = rulesets.rulesetFor('.github')
			live = copy.deepcopy(wanted)
			next(rule['parameters'] for rule in live['rules'] if rule['type'] == 'pull_request')[
				'allowed_merge_methods'
			] = [value]
			self.assertNotEqual(rulesets.rulesetSummary(wanted), rulesets.rulesetSummary(live))
		wanted['rules'].append({'type': 'custom_rule', 'parameters': {'sequence': ['a', 'b']}})
		live = copy.deepcopy(wanted)
		live['rules'][-1]['parameters']['sequence'].reverse()
		self.assertNotEqual(rulesets.rulesetSummary(wanted), rulesets.rulesetSummary(live))

	def testEquivalentCitationTopicsDoNotCauseWrites(self):
		with (
			mock.patch.object(
				settings, 'citationKeywords', return_value=['GitHub', 'PYTHON', 'python']
			),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			settings.syncTopics('.github', {'topics': ['python', 'github']}, apply=True)
		write.assert_not_called()

	def testRequiredReviewerPatternOrderIsVerifiedAfterWriting(self):
		wanted = rulesets.rulesetFor('.github')
		parameters = next(
			rule['parameters'] for rule in wanted['rules'] if rule['type'] == 'pull_request'
		)
		parameters['required_reviewers'] = [
			{
				'file_patterns': ['src/**', '!src/generated/**'],
				'minimum_approvals': 1,
				'reviewer': {'type': 'Team', 'id': 7},
			},
			{
				'file_patterns': ['docs/**'],
				'minimum_approvals': 0,
				'reviewer': {'type': 'Team', 'id': 8},
			},
		]
		original = copy.deepcopy(wanted)
		live = self.reverseRulesetLists(dict(wanted, id=9))
		self.assertEqual(rulesets.rulesetSummary(wanted), rulesets.rulesetSummary(live))
		liveParameters = next(
			rule['parameters'] for rule in live['rules'] if rule['type'] == 'pull_request'
		)
		liveParameters['required_reviewers'][1]['file_patterns'].reverse()
		self.assertNotEqual(rulesets.rulesetSummary(wanted), rulesets.rulesetSummary(live))
		with (
			mock.patch.object(github, 'gh', return_value='{"id": 9}') as write,
			mock.patch.object(github, 'ghJson', return_value=live),
			self.assertRaisesRegex(RuntimeError, 'Không xác minh được'),
		):
			rulesets.applyRuleset('repos/TOANQUYNHLLC/.github/rulesets', wanted, 9)
		self.assertEqual(json.loads(write.call_args.kwargs['stdin']), original)
		self.assertEqual(wanted, original)

	def testRulesetWriteResponseRequiresMatchingPositiveId(self):
		wanted = rulesets.rulesetFor('.github')
		for rulesetId in (None, 7):
			responses = [
				'',
				'invalid JSON',
				'null',
				'[]',
				'{}',
				'{"id": true}',
				'{"id": 0}',
				'{"id": "7"}',
			]
			if rulesetId is not None:
				responses.append('{"id": 8}')
			for response in responses:
				with (
					self.subTest(id=rulesetId, response=response),
					mock.patch.object(github, 'gh', return_value=response) as write,
					mock.patch.object(github, 'ghJson') as read,
					self.assertRaisesRegex(RuntimeError, 'Không xác minh được'),
				):
					rulesets.applyRuleset('repos/TOANQUYNHLLC/.github/rulesets', wanted, rulesetId)
				write.assert_called_once()
				read.assert_not_called()

	def testRulesetReadbackRejectsMissingIdentityOrConfiguration(self):
		wanted = rulesets.rulesetFor('.github')
		for response in (
			RuntimeError('HTTP 502'),
			{},
			wanted,
			dict(wanted, id=True),
			dict(wanted, id=8),
			dict(wanted, id=7, name='Sai tên'),
			dict(wanted, id=7, enforcement='disabled'),
			dict(wanted, id=7, rules=[]),
			dict(wanted, id=7, bypass_actors=[]),
			dict(wanted, id=7, conditions={}),
		):
			with (
				self.subTest(response=response),
				mock.patch.object(github, 'gh', return_value='{"id": 7}'),
				mock.patch.object(github, 'ghJson', side_effect=[response]) as read,
				self.assertRaisesRegex(RuntimeError, 'Không xác minh được'),
			):
				rulesets.applyRuleset('repos/TOANQUYNHLLC/.github/rulesets', wanted, 7)
			read.assert_called_once_with('api', 'repos/TOANQUYNHLLC/.github/rulesets/7')

	def testRulesetWriteReadsBackBothScopesByConfirmedId(self):
		for organization in (False, True):
			wanted = rulesets.orgRuleset() if organization else rulesets.rulesetFor('.github')
			endpoint = (
				'orgs/TOANQUYNHLLC/rulesets'
				if organization
				else 'repos/TOANQUYNHLLC/.github/rulesets'
			)
			for creating in (False, True):
				with (
					self.subTest(organization=organization, creating=creating),
					mock.patch.object(github, 'gh', return_value='{"id": 7}') as write,
					mock.patch.object(
						github, 'ghJson', return_value=dict(wanted, id=7, node_id='ignored')
					) as read,
				):
					rulesets.applyRuleset(endpoint, wanted, None if creating else 7)
				write.assert_called_once()
				self.assertEqual(write.call_args.args[2], 'POST' if creating else 'PUT')
				self.assertEqual(write.call_args.args[3], endpoint if creating else f'{endpoint}/7')
				self.assertEqual(json.loads(write.call_args.kwargs['stdin']), wanted)
				read.assert_called_once_with('api', f'{endpoint}/7')

	def testRulesetApplyRejectsUnconfirmedWrites(self):
		for organization in (False, True):
			for creating in (False, True):
				wanted = rulesets.orgRulesets() if organization else rulesets.rulesetsFor('.github')
				listing = (
					[]
					if creating
					else [
						{'name': item['name'], 'id': index + 1}
						for index, (_, item) in enumerate(wanted)
					]
				)
				writes = []

				def read(*args, wanted=wanted):
					index = int(args[-1].rsplit('/', 1)[-1]) - 1
					return dict(wanted[index][1], enforcement='disabled', id=index + 1)

				def write(*args, stdin=None, writes=writes):
					writes.append(args)
					return json.dumps({'id': len(writes)})

				with (
					self.subTest(organization=organization, creating=creating),
					mock.patch.object(github, 'ghList', return_value=listing),
					mock.patch.object(github, 'ghJson', side_effect=read),
					mock.patch.object(github, 'gh', side_effect=write),
					contextlib.redirect_stdout(io.StringIO()) as output,
					self.assertRaisesRegex(RuntimeError, 'Không áp dụng được'),
				):
					if organization:
						rulesets.syncOrgRulesets(apply=True)
					else:
						rulesets.syncRulesets(['.github'], apply=True)
				self.assertEqual(len(writes), len(wanted))
				self.assertNotIn('✔ đã', output.getvalue())

	def testOrganizationRulesetReadFailuresReturnFailureInCli(self):
		module = loadScript('org-setup')
		for command in ('org-rulesets', 'preview'):
			for response in (RuntimeError('HTTP 502'), [], [{'errors': [{'message': 'Lỗi đọc'}]}]):
				with (
					self.subTest(command=command, response=response),
					mock.patch.object(module, 'signedIn', return_value=True),
					mock.patch.object(module, 'COMMANDS', ('org-rulesets',)),
					mock.patch.object(github, 'listRepos', return_value=[]),
					mock.patch.object(github, 'ghList', side_effect=RuntimeError('HTTP 403')),
					mock.patch.object(
						github,
						'ghJson',
						side_effect=[response],
					),
					mock.patch.object(github, 'gh') as write,
					mock.patch.object(module.sys, 'argv', ['org-setup.py', command]),
					contextlib.redirect_stdout(io.StringIO()) as output,
					contextlib.redirect_stderr(io.StringIO()),
				):
					self.assertEqual(module.main(), 1)
				self.assertIn('không đọc được qua GraphQL', output.getvalue())
				self.assertNotIn('đã đúng', output.getvalue())
				write.assert_not_called()

	def testRepositoryRulesetWriteFailuresReturnFailureAfterOtherWrites(self):
		module = loadScript('org-setup')
		calls = []
		live = {}

		def write(*args, stdin=None):
			calls.append(args)
			if len(calls) == 1:
				raise RuntimeError('HTTP 500')
			live[f'{args[3]}/{len(calls)}'] = dict(json.loads(stdin), id=len(calls))
			return json.dumps({'id': len(calls)})

		with (
			mock.patch.object(module, 'signedIn', return_value=True),
			mock.patch.object(github, 'listRepos', return_value=['.github', 'app']),
			mock.patch.object(github, 'defaultBranch', return_value='main'),
			mock.patch.object(github, 'ghExists', return_value=True),
			mock.patch.object(github, 'ghList', return_value=[]),
			mock.patch.object(github, 'ghJson', side_effect=lambda *args: live[args[-1]]),
			mock.patch.object(github, 'gh', side_effect=write),
			mock.patch.object(module.sys, 'argv', ['org-setup.py', 'rulesets', '--apply']),
			contextlib.redirect_stdout(io.StringIO()) as output,
			contextlib.redirect_stderr(io.StringIO()) as error,
		):
			self.assertEqual(module.main(), 1)
		self.assertEqual(len(calls), 4)
		self.assertEqual(
			[args[3] for args in calls],
			['repos/TOANQUYNHLLC/.github/rulesets'] * 2 + ['repos/TOANQUYNHLLC/app/rulesets'] * 2,
		)
		self.assertEqual(output.getvalue().count('✔ đã tạo'), 3)
		self.assertIn('.github/Protect Main', error.getvalue())

	def testMissingRequiredWorkflowsBlockRulesetApplyInCli(self):
		module = loadScript('org-setup')
		live = {}

		def apply(*args, stdin=None):
			rulesetId = len(live) + 1
			live[f'{args[3]}/{rulesetId}'] = dict(json.loads(stdin), id=rulesetId)
			return json.dumps({'id': rulesetId})

		with (
			mock.patch.object(module, 'signedIn', return_value=True),
			mock.patch.object(github, 'listRepos', return_value=['app', '.github']),
			mock.patch.object(github, 'defaultBranch', return_value='main'),
			mock.patch.object(github, 'ghExists', return_value=False),
			mock.patch.object(github, 'ghList', return_value=[]),
			mock.patch.object(github, 'ghJson', side_effect=lambda *args: live[args[-1]]),
			mock.patch.object(github, 'gh', side_effect=apply) as write,
			mock.patch.object(module.sys, 'argv', ['org-setup.py', 'rulesets', '--apply']),
			contextlib.redirect_stdout(io.StringIO()) as output,
			contextlib.redirect_stderr(io.StringIO()) as error,
		):
			self.assertEqual(module.main(), 1)
		self.assertIn('hợp nhất Pull Request của lệnh files trước', output.getvalue())
		self.assertIn('app: thiếu workflow bắt buộc', error.getvalue())
		self.assertEqual(output.getvalue().count('✔ đã tạo'), 2)
		self.assertEqual(write.call_count, 2)
		self.assertTrue(
			all(
				call.args[3] == 'repos/TOANQUYNHLLC/.github/rulesets'
				for call in write.call_args_list
			)
		)

	def testInvalidPullRequestParametersStopBeforeWrites(self):
		for key, value in (
			('require d_review_thread_resolution', True),
			('required_review_thread_resolution', 'true'),
			('required_approving_review_count', True),
		):
			wanted = rulesets.rulesetFor('.github')
			parameters = next(
				rule['parameters'] for rule in wanted['rules'] if rule['type'] == 'pull_request'
			)
			parameters[key] = value
			with (
				self.subTest(key=key, value=value),
				mock.patch.object(
					rulesets, 'rulesetsFor', return_value=[(rulesets.RULESET_FILE, wanted)]
				),
				mock.patch.object(github, 'ghList', return_value=[]),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
				self.assertRaisesRegex(ValueError, 'pull_request'),
			):
				rulesets.syncRulesets(['.github'], apply=True)
			write.assert_not_called()

	def testOrganizationRulesetRenameUpdatesExistingId(self):
		wanted = rulesets.orgRulesets()
		oldNames = [
			'Protect Main (Organization)',
			'Protect Release Tags (Organization)',
			'Protect Pushes (Organization)',
		]
		listing = [{'name': name, 'id': index + 1} for index, name in enumerate(oldNames)]
		live = {
			index + 1: dict(item, name=name, id=index + 1)
			for index, ((_, item), name) in enumerate(zip(wanted, oldNames, strict=True))
		}

		def read(*args):
			return live[int(args[-1].rsplit('/', 1)[-1])]

		def apply(*args, stdin=None):
			rulesetId = int(args[3].rsplit('/', 1)[-1])
			live[rulesetId] = dict(json.loads(stdin), id=rulesetId)
			return json.dumps({'id': rulesetId})

		with (
			mock.patch.object(github, 'ghList', return_value=listing),
			mock.patch.object(github, 'ghJson', side_effect=read),
			mock.patch.object(github, 'gh', side_effect=apply) as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			rulesets.syncOrgRulesets(apply=True)
		self.assertEqual(len(write.call_args_list), 3)
		for index, call in enumerate(write.call_args_list):
			self.assertEqual(call.args[2], 'PUT')
			self.assertTrue(call.args[3].endswith(f'/{index + 1}'))
			self.assertEqual(json.loads(call.kwargs['stdin'])['name'], wanted[index][1]['name'])

	def testAmbiguousOrganizationRulesetRenameStopsBeforeWrites(self):
		with (
			mock.patch.object(
				github,
				'ghList',
				return_value=[
					{'name': 'Protect Main (Organization)', 'id': 1},
					{'name': 'Organization Protect Main', 'id': 2},
				],
			),
			mock.patch.object(github, 'ghJson') as read,
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaisesRegex(ValueError, 'ruleset'),
		):
			rulesets.syncOrgRulesets(apply=True)
		read.assert_not_called()
		write.assert_not_called()

	def testGraphqlReportsExistingOrganizationRulesetNames(self):
		wanted = rulesets.orgRulesets()
		oldNames = [
			'Protect Main (Organization)',
			'Protect Release Tags (Organization)',
			'Protect Pushes (Organization)',
		]
		nodes = [dict(item, name=name) for (_, item), name in zip(wanted, oldNames, strict=True)]
		data = [
			{
				'data': {
					'organization': {
						'rulesets': {'nodes': nodes, 'pageInfo': {'hasNextPage': False}}
					}
				}
			}
		]
		with (
			mock.patch.object(github, 'ghJson', return_value=data),
			mock.patch.object(rulesets, 'graphqlRuleset', side_effect=rulesets.graphqlVisible),
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			rulesets.compareOrgRulesets()
		self.assertNotIn('chưa có ruleset', output.getvalue())
		for name in oldNames:
			self.assertIn(name, output.getvalue())

	def testDefaultBranchSpecialCharactersAreEncoded(self):
		# Git nhận #, &, %, / trong tên nhánh; URL phải giữ nguyên ref thay vì hiểu thành fragment/query.
		with (
			mock.patch.object(github, 'defaultBranch', return_value='release/a&b#c%d'),
			mock.patch.object(github, 'ghExists', return_value=False) as exists,
			contextlib.redirect_stdout(io.StringIO()),
		):
			rulesets.syncRulesets(['app'], apply=False)
			for call in exists.call_args_list:
				self.assertTrue(call.args[0].endswith('?ref=release%2Fa%26b%23c%25d'))
		with (
			mock.patch.object(github, 'defaultBranch', return_value='release/a&b#c%d'),
			mock.patch.object(github, 'ghJson', side_effect=RuntimeError('HTTP 409')) as read,
			contextlib.redirect_stdout(io.StringIO()),
		):
			files.syncFiles(['app'], apply=False)
			read.assert_called_once_with(
				'api', 'repos/TOANQUYNHLLC/app/git/ref/heads/release%2Fa%26b%23c%25d'
			)

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
					self.assertRaisesRegex(RuntimeError, 'Không đối chiếu được'),
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
					self.assertRaisesRegex(RuntimeError, 'Không đối chiếu được'),
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
			self.assertRaisesRegex(RuntimeError, 'Không đối chiếu được'),
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
		live = {
			index + 1: dict(item, enforcement='disabled', id=index + 1)
			for index, (_, item) in enumerate(wanted)
		}
		written = set()

		def read(*args):
			rulesetId = int(args[-1].rsplit('/', 1)[-1])
			if rulesetId not in written:
				barrier.wait(timeout=2)
			return live[rulesetId]

		def apply(*args, stdin=None):
			rulesetId = int(args[3].rsplit('/', 1)[-1])
			live[rulesetId] = dict(json.loads(stdin), id=rulesetId)
			written.add(rulesetId)
			return json.dumps({'id': rulesetId})

		with (
			mock.patch.object(github, 'ghList', return_value=listing),
			mock.patch.object(github, 'ghJson', read),
			mock.patch.object(github, 'gh', side_effect=apply) as write,
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
		# Giá trị mong muốn ghi rõ: nguồn cài đặt thật đổi sau mỗi lần make org-import.
		wanted = {'allowed_actions': 'all', 'sha_pinning_required': False}
		with mock.patch.object(github, 'gh') as write, contextlib.redirect_stdout(io.StringIO()):
			settings.syncActions(
				'permissions',
				wanted,
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
		for data in (
			None,
			[],
			{},
			{'full_name': 'TOANQUYNHLLC/app', 'default_branch': None},
			{'full_name': 'TOANQUYNHLLC/app', 'default_branch': ''},
		):
			with (
				self.subTest(data=data),
				mock.patch.object(github, 'ghJson', return_value=data),
				self.assertRaises(ValueError),
			):
				github.defaultBranch('app')

	def testDefaultBranchIdentityStopsFileAndRulesetWrites(self):
		for identity in (None, 'TOANQUYNHLLC/renamed', 'another-owner/app'):
			for sync in (files.syncFiles, rulesets.syncRulesets):
				with (
					self.subTest(identity=identity, sync=sync.__name__),
					mock.patch.object(
						github,
						'ghJson',
						return_value={'full_name': identity, 'default_branch': 'main'},
					) as read,
					mock.patch.object(github, 'gh') as write,
					contextlib.redirect_stdout(io.StringIO()),
					self.assertRaisesRegex(ValueError, 'danh tính'),
				):
					sync(['app'], apply=True)
				read.assert_called_once_with('api', 'repos/TOANQUYNHLLC/app')
				write.assert_not_called()
		with mock.patch.object(
			github,
			'ghJson',
			return_value={'full_name': 'toanquynhllc/APP', 'default_branch': 'release/current'},
		):
			self.assertEqual(github.defaultBranch('app'), 'release/current')

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

	def testLegacySettingsRejectWrongResourceBeforeAnyWrite(self):
		for base, key in (
			('repos/TOANQUYNHLLC/app', 'full_name'),
			('orgs/TOANQUYNHLLC', 'login'),
		):
			for identity in (None, '', 7, 'OTHER/app', 'TOANQUYNHLLC/renamed'):
				for apply in (False, True):
					for changed in (False, True):
						current = {key: identity, 'description': 'Hiện tại'}
						if identity is None:
							current.pop(key)
						with (
							self.subTest(
								base=base, identity=identity, apply=apply, changed=changed
							),
							mock.patch.object(github, 'gh') as write,
							mock.patch.object(github, 'ghJson') as read,
							contextlib.redirect_stdout(io.StringIO()),
							self.assertRaisesRegex(ValueError, 'danh tính'),
						):
							settings.updateSettings(
								base,
								current,
								{'description': 'Mới' if changed else 'Hiện tại'},
								apply,
								'cài đặt',
							)
						write.assert_not_called()
						read.assert_not_called()

	def testLegacySettingsReadbackRejectsWrongResource(self):
		for base, key, expected in (
			('repos/TOANQUYNHLLC/app', 'full_name', 'TOANQUYNHLLC/app'),
			('orgs/TOANQUYNHLLC', 'login', 'TOANQUYNHLLC'),
		):
			for identity in (None, 'OTHER/app'):
				confirmed = {'description': 'Mới'}
				if identity is not None:
					confirmed[key] = identity
				with (
					self.subTest(base=base, identity=identity),
					mock.patch.object(github, 'ghJson', return_value=confirmed),
					mock.patch.object(github, 'gh') as write,
					contextlib.redirect_stdout(io.StringIO()) as output,
					self.assertRaisesRegex(ValueError, 'danh tính'),
				):
					settings.updateSettings(
						base,
						{key: expected, 'description': 'Cũ'},
						{'description': 'Mới'},
						True,
						'cài đặt',
					)
				write.assert_called_once()
				self.assertNotIn('✔ đã cập nhật', output.getvalue())

	def testResourceIdentityAcceptsCaseDifferences(self):
		for base, key, expected in (
			('repos/toanquynhllc/app', 'full_name', 'TOANQUYNHLLC/App'),
			('orgs/toanquynhllc', 'login', 'TOANQUYNHLLC'),
		):
			state = {key: expected, 'description': 'Mới'}
			with (
				self.subTest(base=base),
				mock.patch.object(github, 'ghJson', return_value=state),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
			):
				confirmed = settings.updateSettings(
					base,
					{key: expected, 'description': 'Cũ'},
					{'description': 'Mới'},
					True,
					'cài đặt',
				)
				self.assertIs(confirmed, state)
				write.assert_called_once()
		plan = []
		with mock.patch.object(
			github,
			'ghJson',
			return_value={'full_name': 'TOANQUYNHLLC/App', 'node_id': 'R_app'},
		):
			settings.repositorySettingChanges(
				plan,
				'repos/toanquynhllc/app',
				{'has_discussions': False},
				{'has_discussions': True},
			)
		self.assertEqual(plan[0][2]['variables']['input']['repositoryId'], 'R_app')

	def testUnconfirmedSettingsWritesReturnFailureInCli(self):
		module = loadScript('org-setup')
		for command, key, value in (
			('settings', 'has_issues', True),
			('org-settings', 'has_organization_projects', False),
		):
			identity = (
				{'full_name': 'TOANQUYNHLLC/app'}
				if command == 'settings'
				else {'login': 'TOANQUYNHLLC'}
			)
			for response in (
				{key: not value},
				{},
				[],
				None,
				{key: int(value)},
				RuntimeError('HTTP 403'),
			):
				confirmed = dict(response, **identity) if isinstance(response, dict) else response
				with self.subTest(command=command, confirmed=confirmed):
					with (
						mock.patch.object(module, 'signedIn', return_value=True),
						mock.patch.object(github, 'listRepos', return_value=['app']),
						mock.patch.object(
							settings, 'repositorySettings', return_value={key: value}
						),
						mock.patch.object(settings, 'ORG_SETTINGS', {key: value}),
						mock.patch.object(settings, 'ORG_WEB_ONLY_SETTINGS', {}),
						mock.patch.object(settings, 'readActions', return_value=[]),
						mock.patch.object(settings, 'syncTopics') as topics,
						mock.patch.object(settings, 'syncSecurity') as security,
						mock.patch.object(settings, 'syncActions') as actions,
						mock.patch.object(
							github, 'ghJson', side_effect=[{key: not value, **identity}, confirmed]
						),
						mock.patch.object(github, 'gh', return_value='{}') as write,
						mock.patch.object(module.sys, 'argv', ['org-setup.py', command, '--apply']),
						contextlib.redirect_stdout(io.StringIO()) as output,
						contextlib.redirect_stderr(io.StringIO()) as error,
					):
						self.assertEqual(module.main(), 1)
					write.assert_called_once()
					self.assertNotIn('✔ đã cập nhật', output.getvalue())
					self.assertIn('❌', error.getvalue())
					for remaining in (topics, security, actions):
						remaining.assert_not_called()

	def testSettingsConfirmationReturnsFreshStateAndAcceptsNullText(self):
		base = 'repos/TOANQUYNHLLC/app'
		current = {
			'full_name': 'TOANQUYNHLLC/app',
			'has_issues': False,
			'description': 'Cũ',
			'private': False,
		}
		original = dict(current)
		wanted = {'has_issues': True, 'description': ''}
		confirmed = dict(current, has_issues=True, description=None, private=True)
		with (
			mock.patch.object(github, 'ghJson', return_value=confirmed) as read,
			mock.patch.object(github, 'gh', return_value='{}') as write,
			contextlib.redirect_stdout(io.StringIO()) as output,
		):
			result = settings.updateSettings(base, current, wanted, True, 'cài đặt repository')
		self.assertIs(result, confirmed)
		self.assertEqual(current, original)
		read.assert_called_once_with('api', base)
		self.assertEqual(json.loads(write.call_args.kwargs['stdin']), wanted)
		self.assertIn('✔ đã cập nhật', output.getvalue())

	def testUnconfirmedDiscussionsWritesReturnFailureInCli(self):
		module = loadScript('org-setup')
		for enabled in (False, True):
			with self.subTest(enabled=enabled):
				current = {
					'has_discussions': not enabled,
					'node_id': 'R_app',
					'full_name': 'TOANQUYNHLLC/app',
				}
				with (
					mock.patch.object(module, 'signedIn', return_value=True),
					mock.patch.object(github, 'listRepos', return_value=['app']),
					mock.patch.object(
						settings, 'repositorySettings', return_value={'has_discussions': enabled}
					),
					mock.patch.object(settings, 'readActions', return_value=[]),
					mock.patch.object(settings, 'syncTopics') as topics,
					mock.patch.object(settings, 'syncSecurity') as security,
					mock.patch.object(settings, 'syncActions') as actions,
					mock.patch.object(github, 'ghJson', return_value=current),
					mock.patch.object(
						github, 'gh', return_value='{"errors": [{"message": "failed"}]}'
					) as write,
					mock.patch.object(module.sys, 'argv', ['org-setup.py', 'settings', '--apply']),
					contextlib.redirect_stdout(io.StringIO()) as output,
					contextlib.redirect_stderr(io.StringIO()),
				):
					self.assertEqual(module.main(), 1)
				write.assert_called_once()
				self.assertEqual(write.call_args.args[:4], ('api', '-X', 'POST', 'graphql'))
				self.assertNotIn('✔ đã cập nhật', output.getvalue())
				for remaining in (topics, security, actions):
					remaining.assert_not_called()

	def testSettingsUseConfirmedVisibilityForSecurity(self):
		for private in (False, True):
			with self.subTest(private=private):
				current = {
					'full_name': 'TOANQUYNHLLC/app',
					'visibility': 'public' if private else 'private',
					'private': not private,
				}
				confirmed = dict(
					current, visibility='private' if private else 'public', private=private
				)
				with (
					mock.patch.object(
						settings,
						'repositorySettings',
						return_value={'visibility': confirmed['visibility']},
					),
					mock.patch.object(settings, 'readActions', return_value=[]),
					mock.patch.object(settings, 'syncTopics') as topics,
					mock.patch.object(settings, 'syncSecurity') as security,
					mock.patch.object(settings, 'syncActions'),
					mock.patch.object(github, 'ghJson', side_effect=[current, confirmed]),
					mock.patch.object(github, 'gh', return_value='{}'),
					contextlib.redirect_stdout(io.StringIO()),
				):
					settings.syncSettings(['app'], apply=True, discussions=False)
				security.assert_called_once_with('app', confirmed, True)
				topics.assert_called_once_with('app', confirmed, True)

	def testUnconfirmedUnarchiveStopsRemainingWrites(self):
		current = {'full_name': 'TOANQUYNHLLC/app', 'archived': True, 'has_issues': False}
		with (
			mock.patch.object(
				settings, 'repositorySettings', return_value={'archived': False, 'has_issues': True}
			),
			mock.patch.object(settings, 'readActions', return_value=[]),
			mock.patch.object(settings, 'syncTopics') as topics,
			mock.patch.object(settings, 'syncSecurity') as security,
			mock.patch.object(settings, 'syncActions') as actions,
			mock.patch.object(github, 'ghJson', return_value=current),
			mock.patch.object(github, 'gh', return_value='{}') as write,
			contextlib.redirect_stdout(io.StringIO()) as output,
			self.assertRaisesRegex(RuntimeError, 'archived'),
		):
			settings.syncSettings(['app'], apply=True, discussions=False)
		write.assert_called_once()
		self.assertEqual(json.loads(write.call_args.kwargs['stdin']), {'archived': False})
		self.assertNotIn('✔ đã cập nhật', output.getvalue())
		for remaining in (topics, security, actions):
			remaining.assert_not_called()

	def testSettingsArchiveTransitionsSurroundOtherUpdates(self):
		base = 'repos/TOANQUYNHLLC/app'
		for before, after, apply in (
			(True, False, True),
			(False, True, True),
			(False, False, True),
			(True, False, False),
			(False, True, False),
			(False, False, False),
		):
			state = {
				'archived': before,
				'has_discussions': False,
				'description': 'Cũ',
				'node_id': 'R_app',
				'full_name': 'TOANQUYNHLLC/app',
			}
			events = []

			def read(*args, state=state):
				return dict(state)

			def write(*args, stdin=None, state=state, events=events):
				body = json.loads(stdin)
				if args[3] == base and set(body) == {'archived'}:
					state.update(body)
					events.append('archive' if body['archived'] else 'unarchive')
					return ''
				if state['archived']:
					raise RuntimeError('HTTP 403: repository đang archive')
				if args[3] == 'graphql':
					state['has_discussions'] = body['variables']['input']['hasDiscussionsEnabled']
					events.append('discussions')
				else:
					state.update(body)
					events.append('settings')
				return ''

			def remainingUpdate(*args, state=state, events=events, apply=apply):
				if apply and state['archived']:
					raise RuntimeError('HTTP 403: repository đang archive')
				events.append('remaining')

			with (
				self.subTest(before=before, after=after, apply=apply),
				mock.patch.object(
					settings,
					'repositorySettings',
					return_value={'archived': after, 'has_discussions': True, 'description': 'Mới'},
				),
				mock.patch.object(settings, 'readActions', return_value=[]),
				mock.patch.object(settings, 'syncTopics', side_effect=remainingUpdate),
				mock.patch.object(settings, 'syncSecurity', side_effect=remainingUpdate),
				mock.patch.object(settings, 'syncActions', side_effect=remainingUpdate),
				mock.patch.object(github, 'ghJson', side_effect=read),
				mock.patch.object(github, 'gh', side_effect=write) as request,
				contextlib.redirect_stdout(io.StringIO()),
			):
				settings.syncSettings(['app'], apply=apply, discussions=False)
				self.assertEqual(state['archived'], after if apply else before)
				self.assertEqual(state['has_discussions'], apply)
				self.assertEqual(state['description'], 'Mới' if apply else 'Cũ')
				if apply and before:
					self.assertEqual(events[0], 'unarchive')
				if apply and after:
					self.assertEqual(events[-1], 'archive')
				self.assertEqual(events.count('remaining'), 3)
				if not apply:
					request.assert_not_called()

	def testSettingsRejectInvalidFieldsBeforeUnarchiving(self):
		with (
			mock.patch.object(
				settings, 'repositorySettings', return_value={'archived': False, 'has_issues': True}
			),
			mock.patch.object(settings, 'readActions', return_value=[]),
			mock.patch.object(
				github, 'ghJson', return_value={'full_name': 'TOANQUYNHLLC/app', 'archived': True}
			),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaisesRegex(ValueError, 'has_issues'),
		):
			settings.syncSettings(['app'], apply=True, discussions=False)
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
				return teamFixture(team)

			with (
				self.subTest(value=value),
				mock.patch.object(github, 'ghJson', read),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
				self.assertRaisesRegex(RuntimeError, 'quyền'),
			):
				teams.syncTeams(['app'], apply=True)
			write.assert_not_called()

	def testUnconfirmedTeamRepositoryPermissionReturnsFailureInCli(self):
		module = loadScript('org-setup')
		for confirmed in (
			None,
			{'role_name': 'write'},
			{'role_name': 'custom_role'},
			{},
			RuntimeError('HTTP 403'),
			RuntimeError('HTTP 429'),
		):
			with self.subTest(confirmed=confirmed):
				permissionReads = []

				def read(*args, confirmed=confirmed, permissionReads=permissionReads):
					path = args[-1]
					if '/memberships/' in path:
						return {'role': 'maintainer', 'state': 'active'}
					if '/repos/' not in path:
						return {**teamFixture('maintainers'), 'parent': None}
					permissionReads.append(args)
					if len(permissionReads) == 1:
						return {'role_name': 'read'}
					if confirmed is None:
						raise RuntimeError('HTTP 404')
					if isinstance(confirmed, RuntimeError):
						raise confirmed
					return confirmed

				with (
					mock.patch.object(teams, 'TEAMS', {'maintainers': teams.TEAMS['maintainers']}),
					mock.patch.object(teams, 'TEAM_PARENTS', {}),
					mock.patch.object(module, 'signedIn', return_value=True),
					mock.patch.object(github, 'listRepos', return_value=['app']),
					mock.patch.object(github, 'ghJson', side_effect=read),
					mock.patch.object(github, 'gh', return_value='') as write,
					mock.patch.object(
						module.sys, 'argv', ['org-setup.py', 'team', '--repo', 'app', '--apply']
					),
					contextlib.redirect_stdout(io.StringIO()) as output,
					contextlib.redirect_stderr(io.StringIO()) as error,
				):
					self.assertEqual(module.main(), 1)
				write.assert_called_once_with(
					'api',
					'-X',
					'PUT',
					'orgs/TOANQUYNHLLC/teams/maintainers/repos/TOANQUYNHLLC/app',
					'-f',
					'permission=maintain',
				)
				self.assertEqual(len(permissionReads), 2)
				self.assertIn('application/vnd.github.v3.repository+json', permissionReads[-1][-2])
				self.assertNotIn('✔ maintain TOANQUYNHLLC/app', output.getvalue())
				self.assertIn('❌', error.getvalue())

	def testTeamPermissionConfirmationAcceptsEqualOrHigherStandardRoles(self):
		for permission, confirmed in (
			('pull', 'read'),
			('triage', 'triage'),
			('push', 'write'),
			('maintain', 'maintain'),
			('admin', 'admin'),
			('maintain', 'admin'),
		):
			with self.subTest(permission=permission, confirmed=confirmed):
				live, permissionReads = {}, []

				def read(*args, live=live, permissionReads=permissionReads):
					path = args[-1]
					if '/memberships/' in path:
						return {'role': 'maintainer', 'state': 'active'}
					if '/repos/' not in path:
						return {**teamFixture('qa'), 'parent': None}
					permissionReads.append(path)
					if path not in live:
						raise RuntimeError('HTTP 404')
					return {'role_name': live[path]}

				def write(*args, stdin=None, live=live, confirmed=confirmed):
					live[args[3]] = confirmed
					return ''

				profile = ('QA', permission, 'closed', teams.TEAMS['qa'][3])
				with (
					mock.patch.object(teams, 'TEAMS', {'qa': profile}),
					mock.patch.object(teams, 'TEAM_PARENTS', {}),
					mock.patch.object(github, 'ghJson', side_effect=read),
					mock.patch.object(github, 'gh', side_effect=write) as writer,
					contextlib.redirect_stdout(io.StringIO()) as output,
				):
					teams.syncTeams(['app', 'web'], apply=True)
				self.assertEqual(writer.call_count, 2)
				self.assertEqual(len(permissionReads), 4)
				for repo in ('app', 'web'):
					self.assertIn(f'✔ {permission} TOANQUYNHLLC/{repo}', output.getvalue())
					path = f'orgs/TOANQUYNHLLC/teams/qa/repos/TOANQUYNHLLC/{repo}'
					self.assertEqual(permissionReads.count(path), 2)
					self.assertEqual(live[path], confirmed)

	def testNewPendingTeamInvitationReturnsFailureAfterOtherMembershipWrites(self):
		module = loadScript('org-setup')
		profiles = {team: teams.TEAMS[team] for team in ('qa', 'developers')}

		def write(*args, stdin=None):
			state = (
				'pending'
				if args[3].endswith(f'/qa/memberships/{teams.MAINTAINERS[0]}')
				else 'active'
			)
			return json.dumps({'role': 'maintainer', 'state': state})

		with (
			mock.patch.object(teams, 'TEAMS', profiles),
			mock.patch.object(teams, 'TEAM_PARENTS', {}),
			mock.patch.object(
				teams,
				'teamDetails',
				side_effect=lambda team: {
					**teamFixture(team),
					'parent': None,
				},
			),
			mock.patch.object(teams, 'teamRole', return_value=None),
			mock.patch.object(teams, 'teamPermission', return_value='admin'),
			mock.patch.object(module, 'signedIn', return_value=True),
			mock.patch.object(github, 'listRepos', return_value=['app']),
			mock.patch.object(github, 'gh', side_effect=write) as writer,
			mock.patch.object(
				module.sys, 'argv', ['org-setup.py', 'team', '--repo', 'app', '--apply']
			),
			contextlib.redirect_stdout(io.StringIO()) as output,
			contextlib.redirect_stderr(io.StringIO()) as error,
		):
			self.assertEqual(module.main(), 1)
		self.assertEqual(writer.call_count, len(profiles) * len(teams.MAINTAINERS))
		self.assertIn(f'qa/{teams.MAINTAINERS[0]}', error.getvalue())
		self.assertIn(f'✔ thêm {teams.MAINTAINERS[1]} (maintainer)', output.getvalue())
		self.assertIn('== team TOANQUYNHLLC/developers: đã có', output.getvalue())
		self.assertIn('chờ chấp nhận lời mời', output.getvalue())

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
				return teamFixture(team)

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

	def testMalformedTeamParentStopsBeforeAnyWrite(self):
		for parent in ('missing', '', [], {}, {'slug': ''}, {'slug': False}):

			def read(*args, parent=parent):
				team = args[-1].rsplit('/', 1)[-1]
				details = teamFixture(team)
				if team == 'engineering':
					if parent == 'missing':
						del details['parent']
					else:
						details['parent'] = parent
				return details

			with (
				self.subTest(parent=parent),
				mock.patch.object(github, 'ghJson', read),
				mock.patch.object(github, 'gh') as write,
				mock.patch.object(teams, 'teamRole', return_value='maintainer'),
				mock.patch.object(teams, 'teamPermission', return_value='admin'),
				self.assertRaisesRegex(RuntimeError, 'team cha'),
			):
				teams.syncTeams(['app'], apply=True)
			write.assert_not_called()

	def testInvalidTeamHierarchyStopsBeforeReadingOrWriting(self):
		for parents in (
			{'unknown': 'engineering'},
			{'qa': 'unknown'},
			{'qa': []},
			{'qa': 'qa'},
			{'engineering': 'qa', 'qa': 'engineering'},
			{'qa': 'admins'},
		):
			with (
				self.subTest(parents=parents),
				mock.patch.object(teams, 'TEAM_PARENTS', parents),
				mock.patch.object(github, 'ghJson') as read,
				mock.patch.object(github, 'gh') as write,
				self.assertRaises(ValueError),
			):
				teams.syncTeams(['app'], apply=True)
			read.assert_not_called()
			write.assert_not_called()

	def testInvalidTeamProfilesStopBeforeReadingOrWriting(self):
		for profile in (
			('QA', 'owner', 'closed', 'Kiểm thử'),
			('QA', [], 'closed', 'Kiểm thử'),
			('QA', 'push', 'public', 'Kiểm thử'),
			('   ', 'push', 'closed', 'Kiểm thử'),
			('QA', 'push', 'closed', []),
			('QA', 'push'),
		):
			with (
				self.subTest(profile=profile),
				mock.patch.object(teams, 'TEAMS', {'qa': profile}),
				mock.patch.object(teams, 'TEAM_PARENTS', {}),
				mock.patch.object(github, 'ghJson') as read,
				mock.patch.object(github, 'gh') as write,
				self.assertRaises(ValueError),
			):
				teams.syncTeams(['app'], apply=True)
			read.assert_not_called()
			write.assert_not_called()

	def testUnconfirmedTeamMetadataStopsBeforeMembershipWrites(self):
		for creating in (False, True):
			for field, wrong in (
				('name', 'Sai tên'),
				('description', 'Sai mô tả'),
				('privacy', 'secret'),
			):
				calls = []
				live = {
					'details': None
					if creating
					else {**teamFixture('qa'), 'parent': None, 'description': 'mô tả cũ'}
				}

				def read(team, live=live):
					if live['details'] is None:
						raise RuntimeError('Not Found (HTTP 404)')
					return live['details']

				def write(*args, stdin=None, field=field, wrong=wrong, calls=calls, live=live):
					calls.append(args)
					if '/memberships/' in str(args):
						return json.dumps({'role': 'maintainer', 'state': 'active'})
					live['details'] = {**teamFixture('qa'), field: wrong}
					return '{}'

				with (
					self.subTest(creating=creating, field=field),
					mock.patch.object(teams, 'TEAMS', {'qa': teams.TEAMS['qa']}),
					mock.patch.object(teams, 'TEAM_PARENTS', {}),
					mock.patch.object(teams, 'teamDetails', side_effect=read),
					mock.patch.object(teams, 'teamRole', return_value=None),
					mock.patch.object(teams, 'teamPermission', return_value='admin'),
					mock.patch.object(github, 'gh', side_effect=write),
					contextlib.redirect_stdout(io.StringIO()),
					self.assertRaisesRegex(RuntimeError, 'thông tin team'),
				):
					teams.syncTeams(['app'], apply=True)
				self.assertEqual(len(calls), 1)
				self.assertIn(calls[0][2], ('POST', 'PATCH'))

	def testBlockedOrgRulesetApplyReturnsFailureInCli(self):
		module = loadScript('org-setup')
		with (
			mock.patch.object(module, 'signedIn', return_value=True),
			mock.patch.object(github, 'ghList', side_effect=RuntimeError('HTTP 403')),
			mock.patch.object(rulesets, 'compareOrgRulesets') as compare,
			mock.patch.object(github, 'gh') as write,
			mock.patch.object(module.sys, 'argv', ['org-setup.py', 'org-rulesets', '--apply']),
			contextlib.redirect_stdout(io.StringIO()),
			contextlib.redirect_stderr(io.StringIO()),
		):
			self.assertEqual(module.main(), 1)
		compare.assert_called_once_with()
		write.assert_not_called()

	def testFailedOrganizationRulesetWritesReturnFailureInCli(self):
		module = loadScript('org-setup')
		wanted = rulesets.orgRulesets()
		listing = [
			{'name': item['name'], 'id': index + 1} for index, (_, item) in enumerate(wanted)
		]

		def read(*args):
			index = int(args[-1].rsplit('/', 1)[-1]) - 1
			return dict(wanted[index][1], enforcement='disabled', id=index + 1)

		with (
			mock.patch.object(module, 'signedIn', return_value=True),
			mock.patch.object(github, 'ghList', return_value=listing),
			mock.patch.object(github, 'ghJson', side_effect=read),
			mock.patch.object(github, 'gh', side_effect=RuntimeError('HTTP 403')) as write,
			mock.patch.object(module.sys, 'argv', ['org-setup.py', 'org-rulesets', '--apply']),
			contextlib.redirect_stdout(io.StringIO()) as output,
			contextlib.redirect_stderr(io.StringIO()) as error,
		):
			self.assertEqual(module.main(), 1)
		self.assertEqual(write.call_count, len(wanted))
		self.assertNotIn('✔ đã', output.getvalue())
		self.assertIn('Không áp dụng được ruleset cấp tổ chức', error.getvalue())

	def testParentTeamsDoNotManageMembersOrRepositoryPermissions(self):
		for team in ('engineering', 'creative'):
			with (
				self.subTest(team=team),
				mock.patch.object(teams, 'teamDetails', side_effect=teamFixture),
				mock.patch.object(teams, 'teamRole') as role,
				mock.patch.object(teams, 'teamPermission') as permission,
			):
				self.assertEqual(teams.teamState(team, ['app'])[2:], ({}, [], []))
			role.assert_not_called()
			permission.assert_not_called()

	def testTeamParentDriftPreviewAndApplyOnlyChangeParent(self):
		for team, current in (
			('qa', None),
			('qa', {'slug': 'creative'}),
			('engineering', {'slug': 'creative'}),
		):
			live = {team: teamFixture(team) for team in teams.TEAMS}
			live[team]['parent'] = current
			calls = []

			def write(*args, stdin=None, calls=calls, live=live, team=team):
				body = json.loads(stdin)
				calls.append((args, body))
				parent = body['parent_team_slug']
				live[team]['parent'] = {'slug': parent} if parent else None

			with (
				self.subTest(team=team, current=current),
				mock.patch.object(
					teams, 'teamDetails', side_effect=lambda team, live=live: live[team]
				),
				mock.patch.object(teams, 'teamRole', return_value='maintainer'),
				mock.patch.object(teams, 'teamPermission', return_value='admin'),
				mock.patch.object(github, 'gh', side_effect=write),
				contextlib.redirect_stdout(io.StringIO()) as output,
			):
				teams.syncTeams(['app'], apply=False)
				self.assertEqual(calls, [])
				self.assertIn('parent_team_slug', output.getvalue())
				teams.syncTeams(['app'], apply=True)
			self.assertEqual(len(calls), 1)
			self.assertEqual(calls[0][0][2:4], ('PATCH', f'orgs/TOANQUYNHLLC/teams/{team}'))
			self.assertEqual(calls[0][1], {'parent_team_slug': teams.TEAM_PARENTS.get(team)})
			self.assertEqual(live[team]['parent'], teamFixture(team)['parent'])

	def testUnconfirmedTeamParentStopsBeforeMembershipWrites(self):
		live = {team: teamFixture(team) for team in teams.TEAMS}
		live['qa']['parent'] = None
		with (
			mock.patch.object(teams, 'teamDetails', side_effect=lambda team: live[team]),
			mock.patch.object(
				teams,
				'teamRole',
				side_effect=lambda team, user: None if team == 'qa' else 'maintainer',
			),
			mock.patch.object(teams, 'teamPermission', return_value='admin'),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaisesRegex(RuntimeError, 'chưa áp dụng đúng team cha'),
		):
			teams.syncTeams(['app'], apply=True)
		self.assertFalse(
			any('/teams/qa/memberships/' in str(call) for call in write.call_args_list)
		)

	def testCreateTeamHierarchyOrdersParentsBeforeChildren(self):
		profiles = {
			'qa': ('QA', None, 'closed', 'Kiểm thử'),
			'engineering': ('Engineering', None, 'closed', 'Phát triển'),
		}
		live, calls = {}, []

		def read(team):
			if team not in live:
				raise RuntimeError('Not Found (HTTP 404)')
			return live[team]

		def write(*args, stdin=None):
			body = json.loads(stdin)
			team = body['name'].lower()
			parent = body.get('parent_team_slug')
			if parent:
				self.assertIn(parent, live)
			calls.append((args, body))
			live[team] = {**body, 'parent': {'slug': parent} if parent else None}

		with (
			mock.patch.object(teams, 'TEAMS', profiles),
			mock.patch.object(teams, 'TEAM_PARENTS', {'qa': 'engineering'}),
			mock.patch.object(teams, 'teamDetails', side_effect=read),
			mock.patch.object(teams, 'teamRole') as role,
			mock.patch.object(teams, 'teamPermission') as permission,
			mock.patch.object(github, 'gh', side_effect=write),
			contextlib.redirect_stdout(io.StringIO()),
		):
			teams.syncTeams(['app'], apply=True)
		role.assert_not_called()
		permission.assert_not_called()
		self.assertEqual([body['name'] for _, body in calls], ['Engineering', 'QA'])
		self.assertTrue(all(args[2:4] == ('POST', 'orgs/TOANQUYNHLLC/teams') for args, _ in calls))
		self.assertEqual(calls[1][1]['parent_team_slug'], 'engineering')

	def testMembershipWriteDistinguishesInvitationFromActiveMember(self):
		teams.teamDetails = teamFixture
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
				if state == 'pending':
					with self.assertRaisesRegex(RuntimeError, 'chờ chấp nhận lời mời'):
						teams.syncTeams(['app'], apply=True)
				else:
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

	def testLabelComparisonIgnoresColorCaseAndNullableDescription(self):
		# Màu hex khác chữ hoa/thường, mô tả null của API so với mô tả trống: không ghi. Tên chỉ khác chữ hoa/thường
		# vẫn đổi theo labels.yml; nhãn riêng của repository giữ nguyên.
		wanted = [
			{'name': 'Bug', 'color': 'FFaa00'},
			{'name': 'Security', 'color': 'ABCDEF', 'description': 'Mô tả'},
			{'name': 'docs', 'color': 'ABCDEF'},
		]
		current = [
			{'name': 'bug', 'color': 'ffaa00', 'description': None},
			{'name': 'SECURITY', 'color': 'abcdef', 'description': 'Mô tả'},
			{'name': 'docs', 'color': 'abcdef', 'description': None},
			{'name': 'custom', 'color': 'ffffff', 'description': None},
		]
		with (
			mock.patch.object(labels, 'loadLabels', return_value=wanted),
			mock.patch.object(github, 'ghList', return_value=current),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(io.StringIO()),
		):
			labels.syncLabels(['app'], apply=True)
		self.assertEqual(
			[call.args[3] for call in write.call_args_list],
			['repos/TOANQUYNHLLC/app/labels/bug', 'repos/TOANQUYNHLLC/app/labels/SECURITY'],
		)

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

	def testPaginatedListsRequireAPageAndAcceptAnEmptyPage(self):
		with (
			mock.patch.object(github, 'ghJson', return_value=[]),
			self.assertRaisesRegex(ValueError, 'phản hồi phân trang'),
		):
			github.ghList('repos/o/r/labels')
		with mock.patch.object(github, 'ghJson', return_value=[[]]):
			self.assertEqual(github.ghList('repos/o/r/labels'), [])

	def testMissingRestPagesPreventLabelAndRulesetWrites(self):
		for action in (
			lambda: labels.syncLabels(['app'], apply=True),
			lambda: rulesets.syncRulesets(['.github'], apply=True),
			lambda: rulesets.syncOrgRulesets(apply=True),
		):
			with (
				self.subTest(action=action),
				mock.patch.object(github, 'ghJson', return_value=[]),
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(io.StringIO()),
				self.assertRaisesRegex(ValueError, 'phản hồi phân trang'),
			):
				action()
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
		# .python-version sinh từ mise.toml (nguồn phiên bản duy nhất, ADR 00000008).
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
		# Nguồn nhập có thể khác chính sách mặc định; dữ liệu giả lập giữ test độc lập với GitHub.
		overrides = {'.github': {'allow_rebase_merge': False, 'has_discussions': True}}
		with mock.patch.object(settings, 'REPOSITORY_OVERRIDES', overrides):
			own = settings.repositorySettings('.github')
			other = settings.repositorySettings('app')
			self.assertFalse(own['allow_rebase_merge'])
			self.assertEqual(own, dict(settings.REPOSITORY_SETTINGS, **overrides['.github']))
			overrides['.github']['allow_rebase_merge'] = True
			self.assertTrue(settings.repositorySettings('.github')['allow_rebase_merge'])
		self.assertIn('has_discussions', own)
		self.assertNotIn('has_discussions', other)
		self.assertNotIn('homepage', other)
		self.assertTrue(settings.repositorySettings('app', discussions=True)['has_discussions'])
		self.assertIn('rulesets', settings.citationKeywords())

	def testActionsPermissionsKeepEnabledState(self):
		calls = []
		# Kiểm tra chính sách bật ghim SHA độc lập với cài đặt vừa nhập từ GitHub (Actions đang tắt).
		wanted = {'allowed_actions': 'all', 'sha_pinning_required': True}
		live = {
			'repos/x/actions/permissions': {'enabled': True, 'allowed_actions': 'all'},
			'repos/x/actions/permissions/workflow': dict(settings.WORKFLOW_PERMISSIONS),
		}
		github.ghJson = lambda *args: live[args[1]]
		github.gh = lambda *args, **kwargs: calls.append((args, kwargs.get('stdin')))
		with contextlib.redirect_stdout(io.StringIO()):
			settings.syncActions('repos/x/actions/permissions', wanted, 'enabled', True)
		# Chỉ ghi phần khác (sha_pinning_required) và gửi lại enabled đang có — không bật, tắt Actions.
		self.assertEqual(len(calls), 1)
		self.assertEqual(json.loads(calls[0][1]), {'sha_pinning_required': True, 'enabled': True})
		# Actions đang tắt: GitHub không trả quyền — bỏ qua, không ghi.
		calls.clear()
		live['repos/x/actions/permissions'] = {'enabled': False, 'sha_pinning_required': False}
		output = io.StringIO()
		with contextlib.redirect_stdout(output):
			settings.syncActions('repos/x/actions/permissions', wanted, 'enabled', True)
		self.assertEqual(calls, [])
		# Chỉ báo đúng phần đã so được (quyền GITHUB_TOKEN), không báo quyền Actions "đã đúng".
		self.assertIn('✔ quyền GITHUB_TOKEN đã đúng', output.getvalue())
		self.assertNotIn('quyền GitHub Actions đã đúng', output.getvalue())
		# Không đọc được: không báo "đã đúng".
		github.ghJson = lambda *args: (_ for _ in ()).throw(RuntimeError('HTTP 403'))
		output = io.StringIO()
		with contextlib.redirect_stdout(output):
			settings.syncActions('repos/x/actions/permissions', wanted, 'enabled', True)
		self.assertNotIn('đã đúng', output.getvalue())

	def testOrgRulesetFilesMatchGenerated(self):
		# Tệp để import trên web phải đúng bằng orgRulesets() sinh từ bản cấp repository.
		for source, ruleset in rulesets.orgRulesets():
			self.assertEqual(json.loads(source.read_text(encoding='utf-8')), ruleset, source.name)

	def testOrgProtectMainAllowsRebaseOnlyAtOrganizationLevel(self):
		# ADR 00000007: bản cấp tổ chức cho phép thêm Rebase và áp dụng cả refs/heads/main; bản cấp repository vẫn chỉ
		# Merge, Squash trên nhánh mặc định.
		def mergeMethods(ruleset):
			return next(
				rule['parameters']['allowed_merge_methods']
				for rule in ruleset['rules']
				if rule['type'] == 'pull_request'
			)

		organization = rulesets.orgRuleset()
		self.assertEqual(mergeMethods(organization), ['merge', 'squash', 'rebase'])
		self.assertEqual(
			organization['conditions']['ref_name']['include'],
			['~DEFAULT_BRANCH', 'refs/heads/main'],
		)
		for repo in ('.github', 'app'):
			repository = rulesets.rulesetFor(repo)
			self.assertEqual(mergeMethods(repository), ['merge', 'squash'])
			self.assertEqual(repository['conditions']['ref_name']['include'], ['~DEFAULT_BRANCH'])

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
		# Dạng GraphQL trả về cho Organization Protect Release Tags trên web.
		node = {
			'name': 'Organization Protect Release Tags',
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
		details = {team: teamFixture(team) for team in teams.TEAMS}
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
		self.assertEqual(
			output.getvalue().count('✔ đủ người quản trị'),
			sum(permission is not None for _, permission, _, _ in teams.TEAMS.values()),
		)
		self.assertEqual(output.getvalue().count('✔ thông tin và cấu trúc team đã đúng'), 2)
		self.assertEqual(calls, [])
		# Chỉ ghi phần còn thiếu: một người chưa là maintainer, một repository chưa đủ quyền.
		teams.teamRole = lambda team, user: (
			'member' if (team, user) == ('maintainers', 'trongtoandl81') else 'maintainer'
		)
		permissions = {('maintainers', 'app'): 'write'}
		teams.teamPermission = lambda team, repo: permissions.get((team, repo), 'admin')

		def write(*args, stdin=None):
			calls.append(args)
			if '/repos/' in args[3]:
				permissions[('maintainers', 'app')] = 'maintain'
			return json.dumps({'role': 'maintainer', 'state': 'active'})

		github.gh = write
		with contextlib.redirect_stdout(io.StringIO()):
			teams.syncTeams(['.github', 'app'], apply=True)
		self.assertEqual(
			[args[3] for args in calls],
			[
				'orgs/TOANQUYNHLLC/teams/maintainers/memberships/trongtoandl81',
				'orgs/TOANQUYNHLLC/teams/maintainers/repos/TOANQUYNHLLC/app',
			],
		)
		self.assertEqual(permissions[('maintainers', 'app')], 'maintain')

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
					full_name='TOANQUYNHLLC/app',
					private=True,
					security_and_analysis={
						name: {'status': 'disabled'} for name in settings.SECURITY_FEATURES
					},
				)
			if path.endswith('/actions/permissions'):
				return dict(settings.ACTIONS_PERMISSIONS, enabled=True, allowed_actions='all')
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
				return teamFixture(team)

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

	def filesCommitFailure(self, deleteError=None):
		"""Chạy files --apply với commit GraphQL bị từ chối; trả (lỗi ném ra, các lệnh gh đã gọi)."""
		calls = []

		def read(*args):
			if '/git/ref/' in args[-1]:
				return {'object': {'sha': 'abc123'}}
			return {'truncated': False, 'tree': [{'path': 'package.json', 'type': 'blob'}]}

		def write(*args, **kwargs):
			calls.append(args)
			if args[:2] == ('api', 'graphql'):
				commit = json.loads(kwargs['stdin'])['variables']['input']
				actual = {
					entry['path']: base64.b64decode(entry['contents']).decode('utf-8')
					for entry in commit['fileChanges']['additions']
				}
				self.assertEqual(actual, files.plannedFiles({'package.json'}))
				self.assertEqual(commit['expectedHeadOid'], 'abc123')
				raise RuntimeError('branch đã đổi')
			if 'DELETE' in args and deleteError:
				raise RuntimeError(deleteError)

		with (
			mock.patch.object(github, 'defaultBranch', return_value='main'),
			mock.patch.object(github, 'ghJson', read),
			mock.patch.object(github, 'ghExists', return_value=False),
			mock.patch.object(github, 'gh', write),
			contextlib.redirect_stdout(io.StringIO()),
			self.assertRaises(RuntimeError) as raised,
		):
			files.syncFiles(['app'], apply=True)
		return str(raised.exception), calls

	def testFilesCommitFailureDeletesBranchWithoutPr(self):
		# Commit bị từ chối: xóa branch vừa tạo để lần chạy sau không bỏ qua repository vì "branch đã tồn tại".
		message, calls = self.filesCommitFailure()
		self.assertIn('branch đã đổi', message)
		self.assertIn(f'đã xóa branch {files.SYNC_BRANCH}', message)
		self.assertEqual(calls[0][:2], ('api', 'repos/TOANQUYNHLLC/app/git/refs'))
		self.assertEqual(
			calls[-1],
			(
				'api',
				'-X',
				'DELETE',
				f'repos/TOANQUYNHLLC/app/git/refs/heads/{files.SYNC_BRANCH}',
				'--silent',
			),
		)
		self.assertFalse([call for call in calls if call[:2] == ('pr', 'create')])

	def testFilesCommitFailureReportsBranchLeftBehind(self):
		message, calls = self.filesCommitFailure(deleteError='HTTP 403')
		self.assertIn('branch đã đổi', message)
		self.assertIn('chưa xóa được branch', message)
		self.assertIn('HTTP 403', message)
		self.assertFalse([call for call in calls if call[:2] == ('pr', 'create')])

	def testEmptyRepositoryIsSkippedOnlyForMissingDefaultRef(self):
		# 404: chưa có nhánh mặc định; 409: GitHub báo "Git Repository is empty" cho repository chưa có commit.
		for message in ('Not Found (HTTP 404)', 'Git Repository is empty. (HTTP 409)'):
			output = io.StringIO()
			with (
				mock.patch.object(github, 'defaultBranch', return_value='main'),
				mock.patch.object(github, 'ghJson', side_effect=RuntimeError(message)) as read,
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
		live = {team: teamFixture(team) for team in teams.TEAMS}
		live['qa']['description'] = 'mô tả cũ'
		teams.teamDetails = lambda team: live[team]

		def write(*args, stdin=None):
			calls.append((args, stdin))
			live['qa'].update(json.loads(stdin))

		github.gh = write
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
		self.assertEqual(len(calls), 2)
		self.assertEqual(calls[0][:3], ('label', 'create', wanted[0]['name']))
		self.assertEqual(calls[1][:3], ('api', '-X', 'PATCH'))
		self.assertIn(f'color={wanted[1]["color"]}', calls[1])

	def testLabelCaseDifferenceIsRenamed(self):
		# GitHub coi "stable" và "Stable" là một nhãn: chỉ khác chữ hoa/thường vẫn phải đổi tên theo labels.yml;
		# tên có "/", ":" được mã hóa trong đường dẫn API.
		calls = []
		wanted = labels.loadLabels()
		live = [dict(label) for label in wanted]
		renamed = {'Stable': 'stable', 'ui/ux': 'UI/UX'}
		for label in live:
			label['name'] = renamed.get(label['name'], label['name'])
		github.ghJson = lambda *args: [live]
		github.gh = lambda *args, **kwargs: calls.append(args)
		output = io.StringIO()
		with contextlib.redirect_stdout(output):
			labels.syncLabels(['app'], apply=False)
		self.assertIn('(xem trước) đổi tên "stable" → nhãn "Stable"', output.getvalue())
		self.assertEqual(calls, [])
		with contextlib.redirect_stdout(io.StringIO()):
			labels.syncLabels(['app'], apply=True)
		self.assertEqual(
			sorted(args[3] for args in calls),
			['repos/TOANQUYNHLLC/app/labels/UI%2FUX', 'repos/TOANQUYNHLLC/app/labels/stable'],
		)
		self.assertTrue(all(args[:3] == ('api', '-X', 'PATCH') for args in calls))
		self.assertEqual(
			{arg for args in calls for arg in args if arg.startswith('new_name=')},
			{'new_name=Stable', 'new_name=ui/ux'},
		)

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

	def syncRulesetsWith(self, apply, failingMethod=None):
		"""Chạy rulesets cho .github: Protect Main đã có (id 7, khác tệp), Protect Release Tags chưa có, thêm một
		ruleset lạ; trả (đầu ra, các lần ghi)."""
		wanted = dict(rulesets.rulesetsFor('.github'))
		protectMain = wanted[rulesets.RULESET_FILE]
		listing = [{'name': 'Protect Main', 'id': 7}, {'name': 'Cũ', 'id': 9}]
		writes = []
		live = {'7': dict(protectMain, enforcement='disabled', id=7)}

		def read(*args):
			if '--paginate' in args:
				return [listing]
			return live[args[-1].rsplit('/', 1)[-1]]

		def write(*args, stdin=None):
			writes.append((args, json.loads(stdin) if stdin else None))
			if failingMethod and failingMethod in args:
				raise RuntimeError('HTTP 403')
			rulesetId = 7 if args[2] == 'PUT' else 8
			live[str(rulesetId)] = dict(json.loads(stdin), id=rulesetId)
			return json.dumps({'id': rulesetId})

		output = io.StringIO()
		with (
			mock.patch.object(github, 'ghJson', read),
			mock.patch.object(github, 'gh', write),
			contextlib.redirect_stdout(output),
		):
			if failingMethod:
				with self.assertRaisesRegex(RuntimeError, 'Không áp dụng được'):
					rulesets.syncRulesets(['.github'], apply=apply)
			else:
				rulesets.syncRulesets(['.github'], apply=apply)
		return output.getvalue(), writes

	def testRulesetPreviewListsCreateAndUpdateWithoutWriting(self):
		output, writes = self.syncRulesetsWith(apply=False)
		self.assertEqual(writes, [])
		self.assertIn(
			'(xem trước) cập nhật ruleset "Protect Main" từ rulesets/protect-main.json', output
		)
		self.assertIn(
			'(xem trước) tạo ruleset "Protect Release Tags" từ rulesets/protect-release-tags.json',
			output,
		)
		self.assertIn('còn ruleset khác: Cũ', output)

	def testRulesetApplyUpdatesExistingCreatesMissing(self):
		# Ruleset đã có thì PUT theo id, chưa có thì POST; nội dung gửi đúng tệp nguồn.
		output, writes = self.syncRulesetsWith(apply=True)
		self.assertEqual(
			[args[:4] for args, _ in writes],
			[
				('api', '-X', 'PUT', 'repos/TOANQUYNHLLC/.github/rulesets/7'),
				('api', '-X', 'POST', 'repos/TOANQUYNHLLC/.github/rulesets'),
			],
		)
		wanted = dict(rulesets.rulesetsFor('.github'))
		self.assertEqual(writes[0][1], wanted[rulesets.RULESET_FILE])
		self.assertEqual(writes[1][1], wanted[rulesets.TAG_RULESET_FILE])
		self.assertIn('✔ đã cập nhật ruleset "Protect Main"', output)
		self.assertIn('✔ đã tạo ruleset "Protect Release Tags"', output)

	def testRulesetWriteFailureWarnsAndContinues(self):
		# Gói Free từ chối ghi (repository riêng tư): cảnh báo ruleset đó, vẫn ghi ruleset kế tiếp.
		output, writes = self.syncRulesetsWith(apply=True, failingMethod='PUT')
		self.assertEqual([args[2] for args, _ in writes], ['PUT', 'POST'])
		self.assertIn('⚠ không cập nhật được ruleset "Protect Main": HTTP 403', output)
		self.assertNotIn('✔ đã cập nhật ruleset "Protect Main"', output)
		self.assertIn('✔ đã tạo ruleset "Protect Release Tags"', output)

	def testOrgRulesetsFallBackToGraphqlWhenRestBlocked(self):
		# Gói Free: REST ruleset cấp tổ chức trả HTTP 403 — so qua GraphQL, không ghi.
		output = io.StringIO()
		for apply in (False, True):
			with (
				self.subTest(apply=apply),
				mock.patch.object(github, 'ghList', side_effect=RuntimeError('HTTP 403')),
				mock.patch.object(rulesets, 'compareOrgRulesets') as compare,
				mock.patch.object(github, 'gh') as write,
				contextlib.redirect_stdout(output),
			):
				if apply:
					with self.assertRaisesRegex(RuntimeError, 'Không áp dụng được'):
						rulesets.syncOrgRulesets(apply=True)
				else:
					rulesets.syncOrgRulesets(apply=False)
			compare.assert_called_once_with()
			write.assert_not_called()
		self.assertIn('REST API ruleset cấp tổ chức: HTTP 403', output.getvalue())

	def testOrgSettingsPatchOnlyApiSettingsAndReportWebOnly(self):
		# Cài đặt đổi được qua API thì PATCH phần khác; mục chỉ đổi trên web chỉ được báo, không ghi.
		current = dict(
			settings.ORG_SETTINGS, login='TOANQUYNHLLC', **settings.ORG_WEB_ONLY_SETTINGS
		)
		current['blog'] = 'https://cu.example'
		# Trên web khác nguồn cài đặt, dù nguồn (đổi sau mỗi lần make org-import) đang bật hay tắt 2FA.
		wanted = settings.ORG_WEB_ONLY_SETTINGS['two_factor_requirement_enabled']
		current['two_factor_requirement_enabled'] = not wanted
		readings = [
			{
				'enabled_repositories': 'all',
				'allowed_actions': 'all',
				**settings.ORG_ACTIONS_PERMISSIONS,
			},
			dict(settings.WORKFLOW_PERMISSIONS),
		]
		for apply in (False, True):
			writes, output = [], io.StringIO()
			live = dict(current)

			def write(*args, stdin=None, writes=writes, live=live):
				writes.append((args, stdin))
				live.update(json.loads(stdin))

			with (
				self.subTest(apply=apply),
				mock.patch.object(settings, 'readActions', return_value=readings),
				mock.patch.object(
					github, 'ghJson', side_effect=lambda *args, live=live: dict(live)
				),
				mock.patch.object(github, 'gh', side_effect=write),
				contextlib.redirect_stdout(output),
			):
				settings.syncOrgSettings(apply)
			text = output.getvalue()
			self.assertIn(f'two_factor_requirement_enabled: {not wanted} ≠ {wanted}', text)
			self.assertIn('quyền GitHub Actions đã đúng', text)
			if apply:
				self.assertEqual(live['blog'], settings.ORG_SETTINGS['blog'])
				self.assertEqual(
					writes,
					[
						(
							('api', '-X', 'PATCH', 'orgs/TOANQUYNHLLC', '--input', '-'),
							json.dumps({'blog': settings.ORG_SETTINGS['blog']}),
						)
					],
				)
			else:
				self.assertEqual(writes, [])
				self.assertIn('(xem trước) blog: https://cu.example', text)

	def testTopicsFollowCitationKeywords(self):
		keywords = settings.citationKeywords()
		writes = []

		def gh(*args, stdin=None):
			writes.append((args, stdin))

		with mock.patch.object(github, 'gh', gh), contextlib.redirect_stdout(io.StringIO()):
			# Repository khác .github không quản lý topics; topics khớp (khác thứ tự) thì không ghi.
			settings.syncTopics('app', {'topics': ['khac']}, apply=True)
			settings.syncTopics('.github', {'topics': list(reversed(keywords))}, apply=True)
			self.assertEqual(writes, [])
			settings.syncTopics('.github', {'topics': ['cu']}, apply=False)
			self.assertEqual(writes, [])
			settings.syncTopics('.github', {'topics': ['cu']}, apply=True)
		self.assertEqual(
			writes,
			[
				(
					('api', '-X', 'PUT', 'repos/TOANQUYNHLLC/.github/topics', '--input', '-'),
					json.dumps({'names': keywords}),
				)
			],
		)

	def testCommandsDispatchToTheirModules(self):
		# Mỗi lệnh của org-setup.py gọi đúng hàm đồng bộ với đúng danh sách repository và cờ --apply.
		module = loadScript('org-setup')
		targets = {
			'files': (module.files, 'syncFiles', (['app'], True)),
			'settings': (module.settings, 'syncSettings', (['app'], True, True)),
			'rulesets': (module.rulesets, 'syncRulesets', (['app'], True)),
			'team': (module.teams, 'syncTeams', (['app'], True)),
			'labels': (module.labels, 'syncLabels', (['app'], True)),
			'org-rulesets': (module.rulesets, 'syncOrgRulesets', (True,)),
			'org-settings': (module.settings, 'syncOrgSettings', (True,)),
		}
		self.assertEqual(set(targets), set(module.COMMANDS))
		for command, (owner, name, arguments) in targets.items():
			with self.subTest(command=command), mock.patch.object(owner, name) as target:
				module.runCommand(command, ['app'], True, discussions=True)
				target.assert_called_once_with(*arguments)

	def testCliRejectsUnsupportedOptionsBeforeGitHub(self):
		module = loadScript('org-setup')
		commands = (*module.COMMANDS, 'preview', 'import-settings', 'local-settings')
		cases = [(command, ['--discussions']) for command in commands if command != 'settings']
		for command in (
			'org-rulesets',
			'org-settings',
			'preview',
			'import-settings',
			'local-settings',
		):
			cases.extend((command, ['--repo', repo]) for repo in ('app', ''))
		cases.extend((command, ['--apply']) for command in ('preview', 'import-settings'))
		for command, options in cases:
			with (
				self.subTest(command=command, options=options),
				mock.patch.object(module.sys, 'argv', ['org-setup.py', command, *options]),
				mock.patch.object(module, 'signedIn') as login,
				mock.patch.object(github, 'listRepos') as listing,
				mock.patch.object(module, 'runCommand') as run,
				mock.patch.object(module.configuration, 'importSettings') as capture,
				mock.patch.object(module.configuration, 'syncConfiguredSettings') as sync,
				contextlib.redirect_stderr(io.StringIO()),
				contextlib.redirect_stdout(io.StringIO()),
				self.assertRaises(SystemExit) as stopped,
			):
				module.main()
			self.assertEqual(stopped.exception.code, 2)
			for operation in (login, listing, run, capture, sync):
				operation.assert_not_called()

	def testCliRejectsInvalidRepositoryNamesBeforeGitHub(self):
		module = loadScript('org-setup')
		for command in ('files', 'settings', 'rulesets', 'team', 'labels'):
			for repo in ('', ' ', '\t', '.', '..', ' app', 'app ', 'owner/app', 'app?x=1', 'app#x'):
				with (
					self.subTest(command=command, repo=repo),
					mock.patch.object(
						module.sys, 'argv', ['org-setup.py', command, '--repo', repo, '--apply']
					),
					mock.patch.object(module, 'signedIn') as login,
					mock.patch.object(github, 'listRepos') as listing,
					mock.patch.object(module, 'runCommand') as run,
					contextlib.redirect_stderr(io.StringIO()),
					contextlib.redirect_stdout(io.StringIO()),
					self.assertRaises(SystemExit) as stopped,
				):
					module.main()
				self.assertEqual(stopped.exception.code, 2)
				for operation in (login, listing, run):
					operation.assert_not_called()

	def testCliPreservesValidRepositoryScope(self):
		module = loadScript('org-setup')
		for command in ('files', 'settings', 'rulesets', 'team', 'labels'):
			for repo in ('.github', 'app_name-v1.2'):
				options = ['--discussions'] if command == 'settings' else []
				with (
					self.subTest(command=command, repo=repo),
					mock.patch.object(
						module.sys,
						'argv',
						['org-setup.py', command, '--repo', repo, '--apply', *options],
					),
					mock.patch.object(module, 'signedIn', return_value=True),
					mock.patch.object(github, 'listRepos', return_value=[repo]) as listing,
					mock.patch.object(module, 'runCommand') as run,
				):
					self.assertEqual(module.main(), 0)
				listing.assert_called_once_with(repo)
				run.assert_called_once_with(command, [repo], True, command == 'settings')

	def testNewTeamPreviewListsEveryStepWithoutWriting(self):
		output = io.StringIO()
		with (
			mock.patch.object(github, 'ghJson', side_effect=RuntimeError('Not Found (HTTP 404)')),
			mock.patch.object(github, 'gh') as write,
			contextlib.redirect_stdout(output),
		):
			teams.syncTeams(['app'], apply=False)
		write.assert_not_called()
		text = output.getvalue()
		for slug, (name, permission, privacy, _) in teams.TEAMS.items():
			self.assertIn(f'== team TOANQUYNHLLC/{slug}: chưa có', text)
			self.assertIn(f'(xem trước) tạo team {name} ({privacy})', text)
			if permission is not None:
				self.assertIn(f'(xem trước) cấp {permission} TOANQUYNHLLC/app', text)
		self.assertNotIn('cấp None', text)
		for user in teams.MAINTAINERS:
			self.assertIn(f'(xem trước) thêm {user} (maintainer)', text)

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
		# Chọn PYTHON rõ ràng để MAKEFLAGS của make cha không đổi trường hợp mặc định đang kiểm thử.
		# Kiểm tra cả trình thông dịch tùy chọn; tắt thông báo thư mục để chỉ so lệnh.
		for pythonCommand in ('python3', sys.executable):
			with self.subTest(pythonCommand=pythonCommand):
				self.assertEqual(
					subprocess.run(
						[
							'make',
							'--no-print-directory',
							'-n',
							'org-preview',
							f'PYTHON={pythonCommand}',
						],
						cwd=ROOT,
						capture_output=True,
						text=True,
						check=True,
					).stdout.strip(),
					f'{pythonCommand} scripts/org-setup.py preview',
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
