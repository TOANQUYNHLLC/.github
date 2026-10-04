"""Test tự động cho scripts/org-setup.py và gói scripts/orgsetup/: tệp dùng chung, ruleset, cài đặt, team, nhãn.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import importlib
import io
import json
import re
import subprocess
import time
import unittest
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import ROOT, loadScript
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript

# Nạp sau testsupport: testsupport thêm scripts/ vào sys.path để import được gói orgsetup.
from orgsetup import files, github, labels, rulesets, settings, teams


class OrgSetupTest(unittest.TestCase):
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
			'ruff.toml',
			'.python-version',
			'rustfmt.toml',
			'.dockerignore',
		):
			self.assertIn(path, planned)
		self.assertNotIn('.clang-format', planned)
		self.assertIn('indent-style = "tab"', planned['ruff.toml'])
		self.assertIn('hard_tabs = true', planned['rustfmt.toml'])

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
			'bypassActors': {'nodes': []},
			'rules': {'nodes': [node]},
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
				'refName': {'include': ['refs/tags/v*'], 'exclude': []},
				'repositoryName': {'include': ['~ALL'], 'exclude': [], 'protected': False},
			},
			'bypassActors': {
				'nodes': [
					{
						'bypassMode': 'ALWAYS',
						'organizationAdmin': True,
						'repositoryRoleDatabaseId': None,
						'actor': None,
					}
				]
			},
			'rules': {
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
				]
			},
		}
		wanted = rulesets.graphqlVisible(rulesets.orgTagRuleset())
		live = rulesets.graphqlRuleset(node)
		self.assertEqual(rulesets.rulesetSummary(live), rulesets.rulesetSummary(wanted))
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
				]
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
		github.gh = lambda *args, **kwargs: calls.append(args)
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
				return dict(settings.repositorySettings('app'), private=True)
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
		github.ghJson = lambda *args: live
		github.gh = lambda *args, **kwargs: calls.append(args)
		with contextlib.redirect_stdout(io.StringIO()):
			labels.syncLabels(['app'], apply=True)
		# Một nhãn thiếu (tạo) và một nhãn sai màu (cập nhật); nhãn đúng không ghi lại.
		self.assertEqual([args[2] for args in calls], [wanted[0]['name'], wanted[1]['name']])

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


if __name__ == '__main__':
	unittest.main()
