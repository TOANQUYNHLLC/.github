"""Kiểm thử hợp đồng và bộ sinh ruleset offline của repository công khai."""

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
	from testsupport import ROOT
except ModuleNotFoundError:
	from scripts.testsupport import ROOT

import rulesets


class RulesetsTest(unittest.TestCase):
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

	def testOrgRulesetFilesMatchGenerated(self):
		# Tệp để import trên web phải đúng từng byte với orgRulesets() sinh từ bản cấp repository, cùng bố cục
		# jsonText với bản cấp repository: so hai tệp cùng loại chỉ thấy điểm khác của cấp tổ chức.
		for source, ruleset in rulesets.orgRulesets():
			self.assertEqual(json.loads(source.read_text(encoding='utf-8')), ruleset, source.name)
			self.assertEqual(
				source.read_text(encoding='utf-8'),
				rulesets.jsonText(ruleset),
				f'{source.name}: chạy make ruleset-files',
			)
		for source in (
			rulesets.RULESET_FILE,
			rulesets.TAG_RULESET_FILE,
			rulesets.PUSH_RULESET_FILE,
		):
			text = source.read_text(encoding='utf-8')
			self.assertEqual(text, rulesets.jsonText(json.loads(text)), source.name)

	def testWriteOrgRulesetFilesRegeneratesLayoutWithoutLogin(self):
		module = rulesets
		with tempfile.TemporaryDirectory() as folder:
			root = Path(folder)
			(root / 'rulesets').mkdir()
			names = (
				'RULESET_FILE',
				'TAG_RULESET_FILE',
				'PUSH_RULESET_FILE',
				'ORG_RULESET_FILE',
				'ORG_TAG_RULESET_FILE',
				'ORG_PUSH_RULESET_FILE',
			)
			paths = {}
			for name in names:
				source = getattr(rulesets, name)
				paths[name] = root / 'rulesets' / source.name
				paths[name].write_bytes(source.read_bytes())
			# Bản tổ chức viết một dòng (bố cục khác) và thiếu quy tắc: lệnh ghi lại theo bản cấp repository.
			paths['ORG_RULESET_FILE'].write_text('{"name": "Cũ", "rules": []}\n', encoding='utf-8')
			paths['ORG_PUSH_RULESET_FILE'].write_text(
				json.dumps(json.loads(paths['ORG_PUSH_RULESET_FILE'].read_text(encoding='utf-8')))
				+ '\n',
				encoding='utf-8',
			)
			with contextlib.ExitStack() as stack:
				for name, path in paths.items():
					stack.enter_context(mock.patch.object(rulesets, name, path))
				externalCalls = stack.enter_context(
					mock.patch('subprocess.run', side_effect=AssertionError('Không gọi lệnh ngoài'))
				)
				for run in range(2):
					with (
						mock.patch('sys.argv', ['rulesets.py']),
						contextlib.redirect_stdout(io.StringIO()) as output,
					):
						self.assertEqual(module.main(), 0)
					if run == 0:
						self.assertIn(
							'✎ đã ghi lại rulesets/organization-protect-main.json',
							output.getvalue(),
						)
						self.assertIn(
							'✎ đã ghi lại rulesets/organization-protect-pushes.json',
							output.getvalue(),
						)
						self.assertIn(
							'✔ rulesets/organization-protect-release-tags.json', output.getvalue()
						)
					else:
						self.assertEqual(output.getvalue().count('đã khớp bản cấp repository'), 3)
				expected = {
					path.name: rulesets.jsonText(item) for path, item in rulesets.orgRulesets()
				}
				externalCalls.assert_not_called()
			for name in ('ORG_RULESET_FILE', 'ORG_TAG_RULESET_FILE', 'ORG_PUSH_RULESET_FILE'):
				path = paths[name]
				self.assertEqual(path.read_text(encoding='utf-8'), expected[path.name])
				self.assertEqual(path.read_bytes(), getattr(rulesets, name).read_bytes(), path.name)

	def testPushRulesetUsesRepositorySourceAndMaintainers(self):
		# Bản tổ chức phải nhận thay đổi chính sách từ nguồn repository, đổi đúng phạm vi và actor.
		repository = json.loads(rulesets.PUSH_RULESET_FILE.read_text(encoding='utf-8'))
		main = rulesets.rulesetFor('.github')
		self.assertEqual(repository['name'], 'Protect Pushes')
		self.assertEqual(repository['target'], 'push')
		self.assertEqual(repository['conditions'], {})
		self.assertEqual(repository['bypass_actors'], main['bypass_actors'])
		self.assertNotIn('required_signatures', [rule['type'] for rule in repository['rules']])
		with tempfile.TemporaryDirectory() as folder:
			path = Path(folder) / 'protect-pushes.json'
			for rule in repository['rules']:
				if rule['type'] == 'max_file_size':
					rule['parameters']['max_file_size'] = 7
			path.write_text(json.dumps(repository), encoding='utf-8')
			with mock.patch.object(rulesets, 'PUSH_RULESET_FILE', path):
				organization = rulesets.orgPushRuleset()
		self.assertEqual(organization['name'], 'Organization Protect Pushes')
		self.assertEqual(organization['rules'], repository['rules'])
		self.assertEqual(organization['conditions'], {'repository_name': rulesets.ORG_REPOSITORIES})
		self.assertEqual(organization['bypass_actors'], rulesets.ORG_BYPASS_ACTORS)

	def testProtectMainAllowsRebaseAtBothLevels(self):
		# ADR 00000007: cả hai cấp cho phép Merge, Squash, Rebase; chỉ bản tổ chức áp dụng thêm refs/heads/main.
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
			self.assertEqual(mergeMethods(repository), ['merge', 'squash', 'rebase'])
			self.assertEqual(repository['conditions']['ref_name']['include'], ['~DEFAULT_BRANCH'])

	def testOrgProtectMainPreservesSourceMergeMethods(self):
		# Nguồn đã có Rebase không được thêm lần nữa; bộ sinh giữ nguyên thứ tự và danh sách của nguồn.
		for methods in (['merge', 'squash'], ['rebase', 'squash', 'merge']):
			with self.subTest(methods=methods):
				repository = rulesets.rulesetFor('app')
				for rule in repository['rules']:
					if rule['type'] == 'pull_request':
						rule['parameters']['allowed_merge_methods'] = methods
				with mock.patch.object(rulesets, 'rulesetFor', return_value=repository):
					organization = rulesets.orgRuleset()
				rulesets.rulesetSummary(organization)
				self.assertEqual(
					next(rule for rule in organization['rules'] if rule['type'] == 'pull_request')[
						'parameters'
					]['allowed_merge_methods'],
					methods,
				)

	def testReleaseTagCreationChecksMatchEachLevel(self):
		# Cờ đọc từ web khác nhau theo cấp; danh sách check rỗng ở cả hai cấp không thêm check phát hành.
		repository = json.loads(rulesets.TAG_RULESET_FILE.read_text(encoding='utf-8'))
		for source, expected in ((repository, True), (rulesets.orgTagRuleset(), False)):
			checks = next(
				rule for rule in source['rules'] if rule['type'] == 'required_status_checks'
			)
			self.assertEqual(checks['parameters']['do_not_enforce_on_create'], expected)
			self.assertEqual(checks['parameters']['required_status_checks'], [])

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


if __name__ == '__main__':
	unittest.main()
