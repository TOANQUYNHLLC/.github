"""Test tự động cho scripts/validate.py: chép repository sang thư mục tạm, mỗi test cố ý làm hỏng một điểm rồi
khẳng định validate.py phát hiện đúng lỗi — để việc sửa script không vô tình làm mất một luật. Sau mỗi test bản
chép được trả về như lúc đầu.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import ROOT
except ModuleNotFoundError:
	from scripts.testsupport import ROOT


class ValidateTest(unittest.TestCase):
	def testCodeFencesDoNotCreateMarkdownErrors(self):
		for fence in ('~~~', '````'):
			with self.subTest(fence=fence):
				path = self.repo / 'example.md'
				path.write_text(
					f'# VÍ DỤ\n\n{fence}md\n```\n# Tiêu đề mẫu\n\tvar = 1\n[x](missing.md)\n```\n{fence}\n\n[x](actually_missing.md)\n',
					encoding='utf-8',
				)
				code, output = self.runValidate()
				self.assertEqual(code, 1)
				self.assertIn('actually_missing.md', output)
				self.assertNotIn('liên kết hỏng: missing.md', output)
				self.assertNotIn('tiêu đề phải viết hoa', output)
				self.assertNotIn('phải thụt lề', output)

	def testNestedYamlShapesAreReportedWithoutStoppingChecks(self):
		cases = (
			(
				'.github/ISSUE_TEMPLATE/bug_report.yml',
				'name: a\ndescription: a\nbody: [42]\n',
				'body',
			),
			('.github/ISSUE_TEMPLATE/config.yml', 'contact_links: [42]\n', 'contact_links'),
			('.github/dependabot.yml', 'updates: [42]\n', 'updates'),
			(
				'.github/dependabot.yml',
				'updates:\n    - cooldown: []\n      labels: [42]\n',
				'cooldown',
			),
			('repository-templates/release.yml', 'changelog: []\n', 'changelog'),
			(
				'repository-templates/release.yml',
				'changelog:\n    categories: [42]\n',
				'categories',
			),
		)
		for name, content, field in cases:
			with self.subTest(path=name, field=field):
				(self.repo / name).write_text(content, encoding='utf-8')
				(self.repo / 'SUPPORT.md').unlink()
				code, output = self.runValidate()
				self.assertEqual(code, 1)
				self.assertIn(name + ':', output)
				self.assertIn(field, output)
				self.assertIn('thiếu tệp bắt buộc SUPPORT.md', output)
				self.tearDown()

	def testNestedJsonShapesAreReportedWithoutStoppingChecks(self):
		cases = (
			('package.json', 'devEngines', []),
			('.prettierrc.json', 'overrides', [42]),
			('.devcontainer/devcontainer.json', 'customizations', []),
			('.vscode/extensions.json', 'recommendations', [{}]),
			('workflow-templates/go-ci.properties.json', 'categories', {}),
			('rulesets/protect-main.json', 'rules', [42]),
			('rulesets/protect-main.json', 'bypass_actors', [42]),
			('rulesets/protect-release-tags.json', 'conditions', []),
		)
		for name, field, value in cases:
			with self.subTest(path=name, field=field):
				path = self.repo / name
				data = json.loads(path.read_text(encoding='utf-8'))
				data[field] = value
				path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
				(self.repo / 'SUPPORT.md').unlink()
				code, output = self.runValidate()
				self.assertEqual(code, 1)
				self.assertIn(name + ':', output)
				self.assertIn(field, output)
				self.assertIn('thiếu tệp bắt buộc SUPPORT.md', output)
				self.tearDown()

	def testFormFieldTypesAreReported(self):
		path = self.repo / '.github/ISSUE_TEMPLATE/bug_report.yml'
		for content in (
			'body: [{type: input, attributes: []}]\n',
			'body: [{type: input, id: [], attributes: {label: 42}}]\n',
			'labels: [42]\nbody: []\n',
		):
			with self.subTest(content=content):
				path.write_text(content, encoding='utf-8')
				self.assertFails('phải là')

	def testYamlWorkflowCannotPinToolVersions(self):
		path = self.repo / '.github/workflows/extra.yaml'
		path.write_text('name: test\n# ruff==0.0.1\n', encoding='utf-8')
		self.assertFails('phiên bản công cụ phải lấy từ mise.toml')

	def testLabelItemsMustBeObjects(self):
		(self.repo / 'labels.yml').write_text('- 42\n', encoding='utf-8')
		self.assertFails('nhãn 1: phải là object')

	def testLabelFieldsKeepTheirDeclaredTypes(self):
		cases = (
			('name: bug', 'name: 42', 'name'),
			('name: bug', 'name: "  "', 'name'),
			("color: 'd73a4a'", 'color: 123456', 'color'),
			(
				'description: Một chức năng chạy sai, không chạy hoặc hiển thị không đúng',
				'description: false',
				'description',
			),
		)
		for old, new, field in cases:
			with self.subTest(field=field):
				self.edit('labels.yml', old, new)
				self.assertFails(field)
				self.tearDown()

	def testDuplicateLabelNamesIgnoreCase(self):
		self.edit('labels.yml', '- name: regression', '- name: BUG')
		self.assertFails('bị trùng')

	def testYamlWorkflowKeepsRequiredJobs(self):
		path = self.repo / '.github/workflows/validate.yml'
		path.rename(path.with_suffix('.yaml'))
		readme = self.repo / 'README.md'
		readme.write_text(
			readme.read_text(encoding='utf-8').replace(
				'.github/workflows/validate.yml', '.github/workflows/validate.yaml'
			),
			encoding='utf-8',
		)
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testYamlWorkflowMustBeDocumented(self):
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)
		path = self.repo / '.github/workflows/extra.yaml'
		path.write_bytes((self.repo / '.github/workflows/links.yml').read_bytes())
		self.assertFails('mục cấu trúc thiếu .github/workflows/extra.yaml')

	@classmethod
	def setUpClass(cls):
		# Chép repository một lần cho cả lớp và lưu bản chép làm mốc; tearDown trả về đúng mốc này.
		cls.tmp = tempfile.TemporaryDirectory()
		cls.repo = Path(cls.tmp.name)
		names = (
			subprocess.run(
				['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
				cwd=ROOT,
				capture_output=True,
				check=True,
			)
			.stdout.decode('utf-8')
			.split('\0')
		)
		# Mốc (nội dung, quyền) của từng tệp giữ trong bộ nhớ: tearDown so với mốc, không phải gọi git.
		cls.baseline = {}
		for name in filter(None, names):
			source = ROOT / name
			if source.is_file():
				target = cls.repo / name
				target.parent.mkdir(parents=True, exist_ok=True)
				shutil.copy2(source, target)
				cls.baseline[name] = (target.read_bytes(), target.stat().st_mode)
		cls.folders = {str(folder) for name in cls.baseline for folder in Path(name).parents}
		# validate.py liệt kê bằng git ls-files --others --exclude-standard: bản chép chỉ cần là repository git (để
		# áp .gitignore), không cần index — mọi tệp chép sang, kể cả tệp test thêm, đều được liệt kê.
		cls.git('init', '-q')

	@classmethod
	def tearDownClass(cls):
		cls.tmp.cleanup()

	@classmethod
	def git(cls, *args):
		return subprocess.run(
			['git', *args], cwd=cls.repo, capture_output=True, text=True, check=True
		).stdout.strip()

	def tearDown(self):
		# Trả bản chép về mốc: ghi lại tệp bị sửa, xóa (đổi tên là xóa cộng thêm); xóa tệp, thư mục test tạo
		# thêm (kể cả tệp bị .gitignore bỏ qua như __pycache__).
		found, visited = set(), []
		for folder, subfolders, files in os.walk(self.repo):
			base = Path(folder)
			relative = base.relative_to(self.repo)
			if base == self.repo:
				subfolders.remove('.git')
			visited.append((base, relative))
			for file in files:
				name = (relative / file).as_posix()
				path = base / file
				if name not in self.baseline:
					path.unlink()
					continue
				found.add(name)
				if path.read_bytes() != self.baseline[name][0]:
					path.write_bytes(self.baseline[name][0])
		# Thư mục test tạo thêm: xóa từ trong ra ngoài khi đã trống.
		for base, relative in reversed(visited):
			if str(relative) not in self.folders and not any(base.iterdir()):
				base.rmdir()
		for name in self.baseline.keys() - found:
			path = self.repo / name
			path.parent.mkdir(parents=True, exist_ok=True)
			path.write_bytes(self.baseline[name][0])
			path.chmod(self.baseline[name][1])

	def runValidate(self):
		# Chạy validate.py của bản chép trong tiến trình này — nhanh hơn nhiều so với chạy python3 riêng cho mỗi
		# test. Chỉ nạp lại khi script trong scripts/ hoặc gói scripts/validation/ của bản chép đổi (test có thể sửa
		# chính luật kiểm tra hoặc script được nạp như conventions.py).
		scripts = self.repo / 'scripts'
		package = sorted((scripts / 'validation').glob('*.py'))
		sources = b''.join(path.read_bytes() for path in [*sorted(scripts.glob('*.py')), *package])
		cls = type(self)
		if getattr(cls, 'validatorSources', None) != sources:
			previous = getattr(cls, 'modules', None)
			cls.validator, cls.modules = self.loadValidator(scripts)
			cls.validatorSources = sources
			# Kết quả đọc YAML (Ruby) và kiểm tra tên theo nội dung tệp chỉ phụ thuộc chính bộ luật (validate.py và
			# gói validation/): test sửa script khác thì giữ lại, không gọi lại Ruby và phân tích lại mọi tệp Python
			# sau mỗi lần nạp lại.
			rules = b''.join(path.read_bytes() for path in [scripts / 'validate.py', *package])
			if previous is not None and getattr(cls, 'rulesSource', None) == rules:
				cls.modules['common'].yamlResults.update(previous['common'].yamlResults)
				cls.modules['sources'].nameResults.update(previous['sources'].nameResults)
			cls.rulesSource = rules
		output = io.StringIO()
		with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
			code = cls.validator.main()
		return code, output.getvalue()

	@staticmethod
	def loadValidator(scripts):
		"""Nạp validate.py và gói validation/ của bản chép; trả (module validate, {tên module: module}). Gói của
		bản chép chỉ nằm trong sys.modules lúc nạp — test khác trong cùng tiến trình vẫn dùng gói của repository."""

		def packageModules():
			return {
				name: module
				for name, module in sys.modules.items()
				if name == 'validation' or name.startswith('validation.')
			}

		saved = packageModules()
		for name in saved:
			del sys.modules[name]
		sys.path.insert(0, str(scripts))
		try:
			spec = importlib.util.spec_from_file_location('validate_copy', scripts / 'validate.py')
			validator = importlib.util.module_from_spec(spec)
			with (
				contextlib.redirect_stdout(io.StringIO()),
				contextlib.redirect_stderr(io.StringIO()),
			):
				spec.loader.exec_module(validator)
			modules = {
				name.removeprefix('validation.'): module
				for name, module in packageModules().items()
			}
		finally:
			sys.path.remove(str(scripts))
			for name in packageModules():
				del sys.modules[name]
			sys.modules.update(saved)
		return validator, modules

	def testChangelogUnreleasedComparesFromReleaseTag(self):
		# So sánh từ tên branch (main...HEAD) luôn rỗng; phải từ tag phát hành gần nhất.
		self.editRegex('CHANGELOG.md', r'compare/[^)]+\.\.\.HEAD\)', 'compare/main...HEAD)')
		self.assertFails('liên kết CHƯA PHÁT HÀNH phải so sánh từ tag phát hành')
		for tag in ('Stable.v2026.11.010001', 'Beta.v2026.11.150002', 'v2026.10.Stable'):
			self.editRegex('CHANGELOG.md', r'compare/[^)]+\.\.\.HEAD\)', f'compare/{tag}...HEAD)')
			code, output = self.runValidate()
			self.assertEqual(code, 0, output)

	def testEditedValidatorRecomputesCachedResults(self):
		# runValidate chỉ giữ kết quả kiểm tra tên, đọc YAML qua lần nạp lại khi bộ luật (validate.py, gói validation/)
		# không đổi: sửa luật thì phải tính lại theo luật mới, không dùng kết quả của luật cũ.
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)
		self.edit(
			'scripts/validation/sources.py',
			"FUNCTION_NAME = re.compile(r'_?[a-z][a-zA-Z0-9]*')",
			"FUNCTION_NAME = re.compile(r'khongkhop')",
		)
		# Tệp không đổi (release.py) cũng phải được kiểm tra lại theo luật mới — chính sources.py đã đổi nội dung
		# nên luôn được kiểm tra lại, không chứng minh được gì.
		code, output = self.runValidate()
		self.assertNotEqual(code, 0, output)
		self.assertRegex(output, r'scripts/release\.py: dòng \d+: tên hàm .* phải viết camelCase')

	def edit(self, name, old, new):
		path = self.repo / name
		text = path.read_text(encoding='utf-8')
		self.assertIn(old, text, f'{name} không còn chứa đoạn cần sửa trong test')
		path.write_text(text.replace(old, new, 1), encoding='utf-8')

	def editRegex(self, name, pattern, new):
		"""Như edit() nhưng tìm bằng regex — dùng cho giá trị sẽ đổi theo thời gian (SHA, ngày, số)."""
		path = self.repo / name
		text, count = re.subn(
			pattern, new, path.read_text(encoding='utf-8'), count=1, flags=re.MULTILINE
		)
		self.assertEqual(count, 1, f'{name} không còn khớp mẫu {pattern!r}')
		path.write_text(text, encoding='utf-8')

	def assertFails(self, message):
		code, output = self.runValidate()
		self.assertEqual(code, 1, output)
		self.assertIn(message, output)

	def testNoHardcodedActionShaInTests(self):
		# SHA gắn cứng làm mọi Pull Request Dependabot nâng action bị chặn vì test mất đoạn neo.
		for path in sorted((ROOT / 'scripts').glob('test_*.py')):
			source = path.read_text(encoding='utf-8')
			self.assertIsNone(
				re.search(r'@[0-9a-f]{40}', source),
				f'{path.name}: dùng editRegex() với mẫu [0-9a-f]{{40}}',
			)

	def testCurrentRepositoryIsValid(self):
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testBrokenLink(self):
		self.edit('README.md', '(SECURITY.md)', '(KHONG_TON_TAI.md)')
		self.assertFails('liên kết hỏng: KHONG_TON_TAI.md')

	def testInvalidUtf8ReportsFileAndContinues(self):
		for name in ('README.md', 'package.json', 'scripts/check.py'):
			with self.subTest(path=name):
				path = self.repo / name
				original = path.read_bytes()
				path.write_bytes(original + b'\xff\n')
				try:
					# Không sửa script validator nạp trực tiếp: lỗi nằm trong nội dung được kiểm tra.
					self.assertFails(f'{name}: không phải UTF-8')
				finally:
					path.write_bytes(original)

	def testLinkAnchorMustExist(self):
		self.edit('profile/README.md', '## 📞 THÔNG TIN LIÊN HỆ', '## 📞 LIÊN HỆ')
		self.assertFails('liên kết hỏng: profile/README.md#-thông-tin-liên-hệ')

	def testHeadingsMustBeUppercase(self):
		self.edit('README.md', '## 🎯 MỤC ĐÍCH', '## 🎯 Mục đích')
		self.assertFails('tiêu đề phải viết hoa')

	def testSecurityEmailTemplateMatchesLink(self):
		self.edit('SECURITY.md', '- **Mô tả vấn đề:**', '- **Mô tả lỗi:**')
		self.assertFails('nội dung liên kết email khác mẫu')

	def testCompanyEmailCannotChange(self):
		# Ghép địa chỉ lúc chạy để chính file test không chứa email nào khác email chung.
		self.edit('SUPPORT.md', 'toanquynhvn@gmail.com', 'lienhe' + '@' + 'example.com')
		self.assertFails('khác email chung của công ty')

	def testEmailFoundOnLaterLine(self):
		# Email sai ở dòng cuối, sau các dòng có email đúng.
		path = self.repo / 'SUPPORT.md'
		path.write_text(
			path.read_text(encoding='utf-8') + '\nLiên hệ: ' + 'hotro' + '@' + 'example.com\n',
			encoding='utf-8',
		)
		self.assertFails('email "hotro' + '@' + 'example.com" khác email chung')

	def testEmailFoundAfterCompanyEmailOnSameLine(self):
		self.edit(
			'SUPPORT.md',
			'toanquynhvn@gmail.com',
			'toanquynhvn@gmail.com, ' + 'banhang' + '@' + 'example.com',
		)
		self.assertFails('email "banhang' + '@' + 'example.com" khác email chung')

	def testReadTextMatchesPathReadText(self):
		# readText() giải mã từ byte đã đọc; phải ra đúng như Path.read_text() (đổi mọi kiểu xuống dòng thành \n).
		self.runValidate()
		path = self.repo / 'newlines.txt'
		for data in (b'a\r\nb\rc\nd', b'\r\r\n\n', 'Toàn Quỳnh\r\n'.encode(), b''):
			path.write_bytes(data)
			self.modules['common'].bytesCache.clear()
			self.modules['common'].textCache.clear()
			self.assertEqual(
				self.modules['common'].readText(path), path.read_text(encoding='utf-8')
			)

	def testSecurityTxtNeedsCompanyEmail(self):
		self.edit('.well-known/security.txt', 'Contact: mailto:toanquynhvn@gmail.com\n', '')
		self.assertFails('Contact phải có mailto:toanquynhvn@gmail.com')

	def testSecurityTxtExpired(self):
		self.editRegex(
			'.well-known/security.txt', r'^Expires: .+$', 'Expires: 2020-01-01T00:00:00.000Z'
		)
		self.assertFails('Expires đã hết hạn')

	def testSecurityTxtExpiresNeedsTimezone(self):
		self.editRegex('.well-known/security.txt', r'^Expires: .+$', 'Expires: 2027-09-26T00:00:00')
		self.assertFails('Expires phải có múi giờ')

	def testInvalidPackageJsonIsReportedWithoutStopping(self):
		(self.repo / 'package.json').write_text('{\n', encoding='utf-8')
		self.assertFails('package.json: JSON không hợp lệ')

	def testInvalidRulesetJsonIsReportedWithoutStopping(self):
		(self.repo / 'rulesets/protect-main.json').write_text('{\n', encoding='utf-8')
		self.assertFails('rulesets/protect-main.json: JSON không hợp lệ')

	def testWorkflowInlineStepCannotEmbedCode(self):
		self.edit(
			'workflow-templates/docs-check.yml',
			'- name: Kiểm tra liên kết nội bộ\n              run: python3 .org/scripts/check-markdown-links.py',
			'- run: python3 -c "print(1)"',
		)
		self.assertFails('mã nhúng trong YAML')

	def testWorkflowInlineStepCannotUseMultilineRun(self):
		self.edit(
			'workflow-templates/docs-check.yml',
			'- name: Kiểm tra liên kết nội bộ\n              run: python3 .org/scripts/check-markdown-links.py',
			'- run: |\n                  python3 .org/scripts/check-markdown-links.py',
		)
		self.assertFails('lệnh nhiều dòng')

	def testWorkflowQuotedAndFlowRunCannotEmbedCode(self):
		path = self.repo / 'workflow-templates/docs-check.yml'
		original = path.read_text(encoding='utf-8')
		old = '- name: Kiểm tra liên kết nội bộ\n              run: python3 .org/scripts/check-markdown-links.py'
		for step in ('- "run": python3 -c "print(1)"', '- {run: \'python3 -c "print(1)"\'}'):
			with self.subTest(step=step):
				path.write_text(original.replace(old, step), encoding='utf-8')
				self.assertFails('mã nhúng trong YAML')

	def testWorkflowQuotedRunCannotUseExpressions(self):
		self.edit(
			'workflow-templates/docs-check.yml',
			'run: python3 .org/scripts/check-markdown-links.py',
			'"run": echo "${{ github.event.pull_request.title }}"',
		)
		self.assertFails('không viết ${{ … }} trong run:')

	def testQuotedPinnedActionIsValid(self):
		self.editRegex(
			'.github/workflows/validate.yml',
			r'uses: (actions/checkout@[0-9a-f]{40})',
			r'"uses": "\1"',
		)
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testQuotedUnpinnedActionIsRejected(self):
		self.editRegex(
			'.github/workflows/validate.yml',
			r'uses: actions/checkout@[0-9a-f]{40}',
			'"uses": actions/checkout@v4',
		)
		self.assertFails('phải ghim theo commit SHA đầy đủ')

	def testRunCommentDoesNotCountAsExpression(self):
		self.edit(
			'workflow-templates/docs-check.yml',
			'run: python3 .org/scripts/check-markdown-links.py',
			'run: python3 .org/scripts/check-markdown-links.py # ${{ nằm trong chú thích }}',
		)
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testWorkflowAnchorsAreResolvedAndChecked(self):
		path = self.repo / 'workflow-templates/docs-check.yml'
		original = path.read_text(encoding='utf-8')
		# GitHub hỗ trợ anchor/alias; run vẫn được kiểm tra theo giá trị ở nơi khai báo.
		for command, expected in (
			('python3 .org/scripts/check-markdown-links.py', 0),
			('python3 -c "print(1)"', 1),
		):
			with self.subTest(command=command):
				text = original.replace(
					'concurrency:', f"env:\n    COMMAND: &command '{command}'\n\nconcurrency:"
				)
				text = text.replace(
					'run: python3 .org/scripts/check-markdown-links.py', 'run: *command'
				)
				path.write_text(text, encoding='utf-8')
				code, output = self.runValidate()
				self.assertEqual(code, expected, output)
				if expected:
					self.assertIn('mã nhúng trong YAML', output)

	def testCyclicYamlReportsOnlyBrokenFile(self):
		(self.repo / '.github/labeler.yml').write_text(
			'cycle: &cycle\n    self: *cycle\n', encoding='utf-8'
		)
		code, output = self.runValidate()
		self.assertEqual(code, 1)
		self.assertIn('.github/labeler.yml: YAML không hợp lệ', output)
		self.assertNotIn('labels.yml: YAML không hợp lệ', output)

	def testJsonObjectCacheRefreshesNextRun(self):
		self.runValidate()
		common = self.modules['common']
		path = common.ROOT / 'package.json'
		first = common.readJsonObject(path)
		(self.repo / 'package.json').write_text('[]\n', encoding='utf-8')
		self.assertFails('package.json: cấu trúc JSON phải là object')
		self.assertIsNot(first, common.readJsonObject(path))

	def testInvalidWorkflowStructureReportsPath(self):
		path = self.repo / '.github/workflows/links.yml'
		for text in (
			'[]\n',
			'jobs: []\n',
			'jobs:\n    links: []\n',
			'jobs:\n    links:\n        steps: [42]\n',
			'jobs:\n    links:\n        steps: {}\n',
		):
			with self.subTest(text=text):
				path.write_text(text, encoding='utf-8')
				self.assertFails('links.yml: cấu trúc')

	def testJsonConfigMustBeObject(self):
		for name in (
			'package.json',
			'.prettierrc.json',
			'rulesets/protect-main.json',
			'.vscode/extensions.json',
			'workflow-templates/docs-check.properties.json',
		):
			with self.subTest(path=name):
				path = self.repo / name
				original = path.read_bytes()
				path.write_text('[]\n', encoding='utf-8')
				try:
					self.assertFails(f'{name}: cấu trúc JSON phải là object')
				finally:
					path.write_bytes(original)

	def testShellMustIndentWithTabs(self):
		path = self.repo / '.devcontainer' / 'post-create.sh'
		path.write_text(
			path.read_text(encoding='utf-8') + 'if true; then\n    echo x\nfi\n', encoding='utf-8'
		)
		self.assertFails('thụt lề phải dùng tab')

	def testPrettierMustUseTabWidth4(self):
		self.edit('.prettierrc.json', '"tabWidth": 4', '"tabWidth": 2')
		self.assertFails('bắt buộc "useTabs": true và "tabWidth": 4')

	def testEditorconfigMustNotUseWidth2(self):
		self.edit('.editorconfig', 'indent_size = 4', 'indent_size = 2')
		self.assertFails('không được dùng độ rộng 2')

	def testMarkdownMustNotIndentWithTabs(self):
		self.edit('SUPPORT.md', '- Đọc `README.md`', '\t- Đọc `README.md`')
		self.assertFails('phải thụt lề bằng 4 dấu cách')

	def testMarkdownTabInsideCodeFenceIsValid(self):
		path = self.repo / 'SUPPORT.md'
		path.write_text(
			path.read_text(encoding='utf-8') + '\n```makefile\nall:\n\techo x\n```\n',
			encoding='utf-8',
		)
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testInvalidYaml(self):
		self.edit('labels.yml', '  color: ', '\tcolor: ')
		self.assertFails('YAML không hợp lệ')

	def testTrailingWhitespace(self):
		line = '# Bộ nhãn chuẩn cho mọi repository của CÔNG TY TNHH TOÀN QUỲNH.'
		self.edit('labels.yml', line, line + '  ')
		self.assertFails('có khoảng trắng cuối dòng')

	def testBatchMustUseCrlf(self):
		(self.repo / 'build.cmd').write_bytes(b'@echo off\ngoto :eof\n')
		self.assertFails('phải xuống dòng bằng CRLF')

	def testBatchWithCrlfIsValid(self):
		(self.repo / 'build.cmd').write_bytes(b'@echo off\r\ngoto :eof\r\n')
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testRegistryUtf16CrlfIsValid(self):
		content = 'Windows Registry Editor Version 5.00\r\n'
		(self.repo / 'setup.reg').write_bytes(b'\xff\xfe' + content.encode('utf-16-le'))
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testRegistryMustBeUtf16(self):
		(self.repo / 'setup.reg').write_bytes(b'Windows Registry Editor Version 5.00\r\n')
		self.assertFails('phải mã hóa UTF-16 LE có BOM')

	def testSolutionMustHaveBom(self):
		(self.repo / 'App.sln').write_bytes(b'Microsoft Visual Studio Solution File\r\n')
		self.assertFails('thiếu BOM UTF-8')

	def testSolutionWithBomCrlfIsValid(self):
		(self.repo / 'App.sln').write_bytes(
			b'\xef\xbb\xbfMicrosoft Visual Studio Solution File\r\n'
		)
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testFsharpMustNotIndentWithTabs(self):
		(self.repo / 'App.fs').write_text('let f x =\n\tx + 1\n', encoding='utf-8')
		self.assertFails('phải thụt lề bằng 4 dấu cách')

	def testDartMustNotIndentWithTabs(self):
		(self.repo / 'main.dart').write_text('void main() {\n\tprint(1);\n}\n', encoding='utf-8')
		self.assertFails('phải thụt lề bằng 2 dấu cách')

	def testEditorconfigWidth2OnlyForRequiredLanguages(self):
		self.edit(
			'.editorconfig',
			'nimble,zig,zon}]\nindent_style = space\n',
			'nimble,zig,zon}]\nindent_style = space\nindent_size = 2\n',
		)
		self.assertFails('không được dùng độ rộng 2')

	def testCsvKeepsTrailingWhitespace(self):
		(self.repo / 'data.csv').write_bytes(b'ten,ghi chu\r\nA,co dau cach \r\n')
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testGitattributesMatchesCrlfList(self):
		self.edit('.gitattributes', '*.dsw text eol=crlf\n', '')
		self.assertFails('.gitattributes: thiếu .dsw text eol=crlf')

	def testEditorconfigMatchesCrlfList(self):
		self.edit('.editorconfig', '[*.{bat,cmd,', '[*.{bat,')
		self.assertFails('.editorconfig: thiếu .cmd trong mục "end_of_line = crlf"')

	def testCommitTypesMatchContributing(self):
		self.edit('scripts/conventions.py', "\t'revert',\n", '')
		self.assertFails(
			'scripts/conventions.py: COMMIT_TYPES thiếu "revert" so với CONTRIBUTING.md'
		)

	def testGitmessageTypesMatchContributing(self):
		self.edit('.gitmessage', 'chore, revert', 'chore')
		self.assertFails('.gitmessage: dòng "# Loại:" thiếu "revert"')

	def testTemplateLabelerCoversAllBranchPrefixes(self):
		self.edit(
			'repository-templates/labeler.yml', "release:\n    - head-branch: ['^release/']\n", ''
		)
		self.assertFails(
			'repository-templates/labeler.yml: thiếu luật head-branch cho tiền tố "release/"'
		)

	def testMiseToolsMatchVersionCheck(self):
		self.edit('mise.toml', 'actionlint = ', 'taplo = "0.10.0"\nactionlint = ')
		self.assertFails('scripts/check-tool-versions.py: REPOSITORIES thiếu taplo')

	def testNonPythonScriptNeedsReason(self):
		(self.repo / 'scripts' / 'check-x.sh').write_text(
			'#!/usr/bin/env bash\necho x\n', encoding='utf-8'
		)
		self.assertFails('scripts/check-x.sh: script không viết bằng Python — thêm dòng')
		(self.repo / 'tools.rb').write_text('puts 1\n', encoding='utf-8')
		self.assertFails('tools.rb: script không viết bằng Python')

	def testNonPythonScriptWithReasonIsValid(self):
		(self.repo / 'scripts' / 'check-x.sh').write_text(
			'#!/usr/bin/env bash\n# Không viết bằng Python vì: chỉ nối các lệnh cài đặt.\necho x\n',
			encoding='utf-8',
		)
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testFunctionNamesMustBeCamelCase(self):
		self.edit('scripts/release.py', 'def releaseNotes(', 'def release_notes(')
		self.assertFails('tên hàm "release_notes" phải viết camelCase tiếng Anh')

	def testParameterAndVariableNamesMustNotBeSnakeCase(self):
		self.edit(
			'scripts/release.py', 'def releaseNotes(changelog,', 'def releaseNotes(change_log,'
		)
		self.assertFails('tham số "change_log" phải viết camelCase tiếng Anh')
		self.edit(
			'scripts/release.py', 'def releaseNotes(change_log,', 'def releaseNotes(changelog,'
		)
		self.edit('scripts/release.py', 'changelogPath = ROOT', 'changelog_path = ROOT')
		self.assertFails('tên biến "changelog_path" phải viết camelCase tiếng Anh')

	def testLibraryDefinedNamesAreAllowed(self):
		# Tên do Python, thư viện quy định không phải tên tự đặt: __init__, __all__, phương thức ghi đè lớp cha
		# của thư viện (log_message) hoặc theo mẫu tên thư viện gọi (do_POST của http.server, ftp_open của
		# urllib) — kể cả tham số theo chữ ký của lớp cha.
		path = self.repo / 'scripts' / 'check-gofmt.py'
		path.write_text(
			path.read_text(encoding='utf-8')
			+ """
import http.server
import urllib.request
from http.server import BaseHTTPRequestHandler as Base

__all__ = ['Handler']


class Handler(http.server.BaseHTTPRequestHandler):
	def do_POST(self):
		pass

	def log_message(self, format, *args):
		pass


class Short(Base):
	def do_PATCH(self):
		pass


class Opener(urllib.request.HTTPHandler):
	def ftp_open(self, req):
		pass


class Holder:
	def __init__(self, value):
		self.value = value
""",
			encoding='utf-8',
		)
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testUserDefinedNamesInLibrarySubclassesAreChecked(self):
		# Tên tự đặt vẫn phải camelCase, kể cả trong lớp con của thư viện và tham số của __init__.
		path = self.repo / 'scripts' / 'check-gofmt.py'
		path.write_text(
			path.read_text(encoding='utf-8')
			+ """
import http.server


class Handler(http.server.BaseHTTPRequestHandler):
	def send_page(self):
		pass


class Holder:
	def __init__(self, start_value):
		self.value = start_value
""",
			encoding='utf-8',
		)
		code, output = self.runValidate()
		self.assertEqual(code, 1, output)
		self.assertIn('tên hàm "send_page" phải viết camelCase', output)
		self.assertIn('tham số "start_value" phải viết camelCase', output)

	def testInvalidPythonIsReported(self):
		self.edit('scripts/check-gofmt.py', 'def goFiles():', 'def goFiles(:')
		self.assertFails('scripts/check-gofmt.py: Python không hợp lệ')

	def testWorkflowHasNoMultilineShell(self):
		self.edit(
			'.github/workflows/validate.yml',
			'run: python3 scripts/check.py content',
			'run: |\n                  python3 scripts/check.py content',
		)
		self.assertFails('validate.yml: dòng 30: lệnh nhiều dòng')

	def testWorkflowTemplateHasNoMultilineShell(self):
		# Workflow mẫu cũng không được viết kiểm tra trực tiếp trong YAML.
		self.edit(
			'workflow-templates/go-ci.yml',
			'run: python3 .org/scripts/check-gofmt.py',
			'run: |\n                  test -z "$(gofmt -l .)"',
		)
		self.assertFails('workflow-templates/go-ci.yml: dòng')

	def testWorkflowHasNoEmbeddedCode(self):
		self.edit(
			'workflow-templates/docs-check.yml',
			'run: python3 .org/scripts/check-markdown-links.py',
			'run: python3 -c "print(1)"',
		)
		self.assertFails('mã nhúng trong YAML')

	def testBranchPrefixesMatchContributing(self):
		self.edit('scripts/conventions.py', "\t'release',\n", '')
		self.assertFails(
			'scripts/conventions.py: BRANCH_PREFIXES thiếu "release" so với CONTRIBUTING.md'
		)

	def testRulesetChecksMatchJobNames(self):
		self.edit('rulesets/protect-main.json', '"Shell script và workflow"', '"Shell script"')
		self.assertFails('kiểm tra bắt buộc "Shell script" không trùng tên job nào')

	def testVietnameseMustBeNfc(self):
		path = self.repo / 'SUPPORT.md'
		text = path.read_text(encoding='utf-8')
		path.write_text(unicodedata.normalize('NFD', text), encoding='utf-8')
		self.assertFails('dạng tách dấu (NFD)')

	def testToolVersionsOnlyInMise(self):
		self.edit(
			'.github/workflows/validate.yml',
			'run: npm install --include=dev --no-audit --no-fund',
			'run: pip install ruff==0.1.0',
		)
		self.assertFails('validate.yml: dòng 49: phiên bản công cụ phải lấy từ mise.toml')

	def testToolVersionsNotPinnedInCheckScript(self):
		self.edit(
			'scripts/check.py',
			"['ruff', 'format',",
			"['pipx', 'install', 'ruff==0.1.0'], ['ruff', 'format',",
		)
		self.assertFails('scripts/check.py: dòng')

	def testCrlfLineEndingsRejected(self):
		path = self.repo / 'SUPPORT.md'
		path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
		self.assertFails('phải xuống dòng bằng LF')

	def testFormLabelsMustExistInLabels(self):
		self.edit('.github/ISSUE_TEMPLATE/question.yml', '    - question', '    - hoi-dap')
		self.assertFails('chưa có trong labels.yml')

	def testDiscussionFormRejectsName(self):
		self.edit(
			'.github/DISCUSSION_TEMPLATE/q-a.yml',
			"title: '[Hỏi đáp] '",
			"name: Hỏi đáp\ntitle: '[Hỏi đáp] '",
		)
		self.assertFails('biểu mẫu Discussion không hỗ trợ khóa "name"')

	def testDiscussionFieldLabelsUppercase(self):
		self.edit('.github/DISCUSSION_TEMPLATE/ideas.yml', 'label: 💡 Ý TƯỞNG', 'label: 💡 Ý tưởng')
		self.assertFails('phải viết hoa')

	def testFormsMustLiveInGithubFolder(self):
		(self.repo / '.github' / 'ISSUE_TEMPLATE').rename(self.repo / 'ISSUE_TEMPLATE')
		self.assertFails('phải nằm trong thư mục .github/ để GitHub nhận diện')

	def testFormsMustNotUseRelativeLinks(self):
		self.edit(
			'.github/DISCUSSION_TEMPLATE/general.yml',
			'(https://github.com/TOANQUYNHLLC/.github/blob/main/CODE_OF_CONDUCT.md)',
			'(CODE_OF_CONDUCT.md)',
		)
		self.assertFails('phải là URL tuyệt đối')

	def testConfigLabelsMustExistInLabels(self):
		self.edit('workflow-templates/stale.yml', 'stale-pr-label: stale', 'stale-pr-label: cu')
		self.assertFails('nhãn "cu" chưa có trong labels.yml')

	def testWritePermissionNotAtWorkflowLevel(self):
		# Khối permissions cấp workflow (không thụt lề) — không phụ thuộc thứ tự khối phía sau.
		self.editRegex(
			'.github/workflows/release.yml',
			r'^permissions:\n    contents: read$',
			'permissions:\n    contents: write',
		)
		self.assertFails('quyền ghi chỉ cấp ở job cần dùng')

	def testFilesWithoutExtensionAreChecked(self):
		path = self.repo / 'LICENSE'
		path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
		self.assertFails('LICENSE: phải xuống dòng bằng LF')

	def testBinaryListMatchesGitattributes(self):
		self.edit('.gitattributes', '*.zip binary\n', '')
		self.assertFails('.gitattributes: thiếu .zip binary so với validate.py')

	def testWorkflowRunMustNotUseExpressions(self):
		# Tiêu đề Pull Request viết thẳng vào lệnh có thể chèn lệnh shell; phải đi qua env.
		self.edit(
			'workflow-templates/pr-title.yml',
			'run: python3 .org/scripts/conventions.py title "$PR_TITLE"',
			'run: python3 .org/scripts/conventions.py title "${{ github.event.pull_request.title }}"',
		)
		self.assertFails('không viết ${{ … }} trong run:')

	def testWorkflowMustDeclarePermissions(self):
		self.edit('.github/workflows/links.yml', 'permissions:\n    contents: read\n\n', '')
		self.assertFails('thiếu khai báo "permissions" ở cấp workflow')

	def testJobMustHaveTimeout(self):
		self.editRegex('.github/workflows/links.yml', r'^ +timeout-minutes: \d+\n', '')
		self.assertFails('job "links" thiếu timeout-minutes')

	def testRuffMustUseTabs(self):
		self.edit('ruff.toml', 'indent-style = "tab"', 'indent-style = "space"')
		self.assertFails('ruff.toml: bắt buộc indent-width = 4 và indent-style = "tab"')

	def testDevEnginesFollowsNvmrc(self):
		# Nâng Node.js trong .nvmrc mà quên devEngines của package.json: báo lỗi.
		(self.repo / '.nvmrc').write_text('26\n', encoding='utf-8')
		self.assertFails(
			'package.json: devEngines.runtime.version là "24", phải là "26" theo .nvmrc'
		)

	def testNodeNotDeclaredInMise(self):
		self.edit('mise.toml', '[tools]\n', '[tools]\nnode = "24"\n')
		self.assertFails('Node.js khai báo trong .nvmrc')

	def testMissingFinalNewline(self):
		path = self.repo / 'SUPPORT.md'
		path.write_bytes(path.read_bytes().rstrip(b'\n'))
		self.assertFails('SUPPORT.md: thiếu dòng trống cuối file')

	def testUtf8BomRejected(self):
		path = self.repo / 'SUPPORT.md'
		path.write_bytes(b'\xef\xbb\xbf' + path.read_bytes())
		self.assertFails('SUPPORT.md: có BOM UTF-8')

	def testShellMustHaveShebang(self):
		self.edit('.devcontainer/post-create.sh', '#!/usr/bin/env bash\n', '')
		self.assertFails('shell script thiếu shebang')

	def testSecurityTxtExpiringSoonIsReported(self):
		# Báo trước khi hết hạn để kịp gia hạn, đăng lại lên website.
		soon = (datetime.now(UTC) + timedelta(days=10)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
		self.editRegex('.well-known/security.txt', r'^Expires: .+$', f'Expires: {soon}')
		self.assertFails('ngày — gia hạn')

	def testSecurityTxtExpiresWithinOneYear(self):
		self.editRegex(
			'.well-known/security.txt', r'^Expires: .+$', 'Expires: 2099-01-01T00:00:00.000Z'
		)
		self.assertFails('Expires vượt quá 1 năm')

	def testChangelogVersionsNotDuplicated(self):
		path = self.repo / 'CHANGELOG.md'
		path.write_text(
			path.read_text(encoding='utf-8') + '\n## [v2099.01.Stable]\n\n## [v2099.01.Stable]\n',
			encoding='utf-8',
		)
		self.assertFails('có phiên bản bị lặp')

	def testLabelColorMustBeHex(self):
		self.editRegex('labels.yml', r"color: '[0-9a-fA-F]{6}'", "color: 'do'")
		self.assertFails('color phải là mã hex 6 ký tự')

	def testFormIdsMustBeUnique(self):
		self.edit('.github/ISSUE_TEMPLATE/bug_report.yml', 'id: expected', 'id: description')
		self.assertFails('id "description" bị trùng')

	def testContactLinksHaveAllFields(self):
		self.editRegex('.github/ISSUE_TEMPLATE/config.yml', r'^ +about: .+\n', '')
		self.assertFails('contact_links thiếu "about"')

	def testRulesetMustBeNamedProtectMain(self):
		self.edit('rulesets/protect-main.json', '"name": "Protect Main"', '"name": "Bảo vệ"')
		self.assertFails('ruleset phải tên "Protect Main"')

	def testAdrIndexMatchesStatus(self):
		self.edit(
			'docs/adr/0001-tab-indentation.md',
			'- **Trạng thái:** Chấp nhận',
			'- **Trạng thái:** Bị thay thế bởi [0002](0002-line-endings.md)',
		)
		self.assertFails('ADR 0001: trạng thái')

	def testAdrIndexAcceptsUnlinkedNumber(self):
		# Mẫu ADR ghi "Bị thay thế bởi NNNN" không kèm liên kết; bảng có liên kết — vẫn khớp vì cùng số.
		self.edit(
			'docs/adr/0001-tab-indentation.md',
			'- **Trạng thái:** Chấp nhận',
			'- **Trạng thái:** Bị thay thế bởi 0002',
		)
		self.editRegex(
			'docs/adr/README.md',
			r'^(\| \[0001\][^|]+\|[^|]+\|) Chấp nhận +\|',
			r'\1 Bị thay thế bởi [0002](0002-line-endings.md) |',
		)
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testChangelogLinksMustBeAbsolute(self):
		self.edit(
			'CHANGELOG.md',
			'# 📦 NỘI DUNG PHÁT HÀNH\n',
			'# 📦 NỘI DUNG PHÁT HÀNH\n\nXem [ADR](docs/adr/README.md).\n',
		)
		self.assertFails('phải là URL tuyệt đối (mỗi mục thành nội dung GitHub Release)')

	def testRulesetBypassMatchesMaintainers(self):
		# Thêm người quản trị mà quên thêm vào danh sách bỏ qua của ruleset: báo lỗi.
		self.edit('scripts/orgsetup/teams.py', "'trongtoandl81')", "'trongtoandl81', 'nguoimoi')")
		self.editRegex(
			'MAINTAINERS.md',
			r'^(\| .+\[@trongtoandl81\].+\n)',
			r'\1| Mới | [@nguoimoi](https://github.com/nguoimoi) | x |\n',
		)
		self.assertFails(
			'rulesets/protect-main.json: danh sách bỏ qua có 2 tài khoản, MAINTAINERS có 3 người'
		)

	def testMaintainersMatchTeamsScript(self):
		self.editRegex('MAINTAINERS.md', r'^\| .+\[@trongtoandl81\].+\n', '')
		self.assertFails('người quản trị "trongtoandl81" chỉ có ở một trong MAINTAINERS.md')

	def testDocsMustMatchCode(self):
		# Lệnh make, đường dẫn, hàm nhắc trong tài liệu phải có thật.
		self.edit(
			'ROADMAP.md',
			'# 🗺️ LỘ TRÌNH\n',
			'# 🗺️ LỘ TRÌNH\n\nChạy `make deploy`, xem `scripts/deploy.py`, hàm `deployAll()`.\n',
		)
		code, output = self.runValidate()
		self.assertEqual(code, 1, output)
		self.assertIn('nhắc "make deploy" nhưng Makefile không có lệnh này', output)
		self.assertIn('nhắc "scripts/deploy.py" nhưng tệp, thư mục này không có', output)
		self.assertIn('nhắc hàm "deployAll()" nhưng không script nào', output)

	def testReadmeListsEveryTargetScriptWorkflow(self):
		self.edit('Makefile', 'help: ##', 'deploy: ## Triển khai\n\techo deploy\n\nhelp: ##')
		(self.repo / 'scripts' / 'deploy.py').write_text('"""Triển khai."""\n', encoding='utf-8')
		(self.repo / '.github' / 'workflows' / 'deploy.yml').write_text(
			(self.repo / '.github' / 'workflows' / 'stale.yml').read_text(encoding='utf-8'),
			encoding='utf-8',
		)
		code, output = self.runValidate()
		self.assertEqual(code, 1, output)
		self.assertIn('bảng lệnh thiếu "make deploy"', output)
		self.assertIn('mục cấu trúc thiếu scripts/deploy.py', output)
		self.assertIn('mục cấu trúc thiếu .github/workflows/deploy.yml', output)

	def testLabelsKeepGithubDefaults(self):
		self.editRegex('labels.yml', r'^- name: wontfix\n(  .+\n)+', '')
		self.assertFails('thiếu nhãn mặc định của GitHub "wontfix"')

	def testBadgesUseEnglishTitleCase(self):
		# Chữ trên huy hiệu: tiếng Anh, hoa đầu mỗi từ — chữ thay thế, nhãn tự đặt hoặc nhãn mặc định của shields
		# (chữ thường), và huy hiệu GitHub Actions lấy chữ theo tên workflow tiếng Việt.
		self.edit(
			'README.md',
			'[![Last Commit](',
			'[![Commit gần nhất](https://img.shields.io/github/v/release/x/y?label=release)]'
			'(https://x.y)\n[![Stars](https://img.shields.io/github/stars/x/y)](https://x.y)\n'
			'[![Build](https://github.com/x/y/actions/workflows/a.yml/badge.svg)](https://x.y)\n'
			'[![Last Commit](',
		)
		code, output = self.runValidate()
		self.assertEqual(code, 1, output)
		self.assertIn('huy hiệu "Commit gần nhất": chữ thay thế phải tiếng Anh', output)
		self.assertIn('nhãn "release" phải tiếng Anh, hoa đầu mỗi từ', output)
		self.assertIn('huy hiệu "Stars": đặt label=', output)
		self.assertIn('huy hiệu "Build": huy hiệu của GitHub lấy chữ theo tên workflow', output)

	def testAdrNeedsEverySection(self):
		self.editRegex(
			'docs/adr/0001-tab-indentation.md', r'^## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC\n\n(?:.+\n)+\n', ''
		)
		self.assertFails('0001-tab-indentation.md: ADR phải có đủ các mục theo thứ tự')

	def testAdrIndexListsEveryAdr(self):
		# Số 9999 không trùng ADR thật nào — test không phải sửa mỗi khi thêm ADR.
		(self.repo / 'docs' / 'adr' / '9999-thu.md').write_text(
			'# 9999. THỬ\n\n- **Trạng thái:** Đề xuất\n- **Ngày:** 2026-09-27\n', encoding='utf-8'
		)
		self.assertFails('bảng thiếu ADR 9999')

	def testTomlMustIndentWithTabs(self):
		self.edit('mise.toml', '[tools]\n', '[tools]\n    ')
		code, output = self.runValidate()
		self.assertEqual(code, 1, output)
		self.assertRegex(output, r'mise\.toml: dòng \d+: thụt lề phải dùng tab')

	def testJsBlockCommentIsValid(self):
		path = self.repo / 'tool.js'
		path.write_text(
			"/**\n * Chú thích khối.\n */\nexport const name = 'x';\n", encoding='utf-8'
		)
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testPrettierMatchesStandard(self):
		self.edit('.prettierrc.json', '"printWidth": 100', '"printWidth": 120')
		self.assertFails('.prettierrc.json: "printWidth" phải là 100')

	def testRuffMatchesStandard(self):
		self.edit('ruff.toml', 'line-ending = "lf"', 'line-ending = "cr-lf"')
		self.assertFails('ruff.toml: format.line-ending phải là "lf"')

	def testEditorconfigMatchesStandard(self):
		self.edit(
			'.editorconfig',
			'[*]\ncharset = utf-8\nend_of_line = lf\n',
			'[*]\ncharset = utf-8\nend_of_line = crlf\n',
		)
		self.assertFails('.editorconfig: mục [*] thiếu "end_of_line = lf"')

	def testPrettierignoreDoesNotRepeatGitignore(self):
		self.edit('.prettierignore', 'LICENSE\n', 'LICENSE\nnode_modules/\n')
		self.assertFails('.prettierignore: "node_modules/" đã có trong .gitignore')

	def testEditorExtensionsMustMatch(self):
		self.edit('.vscode/extensions.json', '\t\t"charliermarsh.ruff",\n', '')
		self.assertFails('.vscode/extensions.json: thiếu extension "charliermarsh.ruff"')

	def testDevcontainerMustPinVersions(self):
		# Image, feature dùng latest hoặc không có tag thì mỗi lần dựng lại container có thể khác nhau.
		self.editRegex(
			'.devcontainer/devcontainer.json',
			r'devcontainers/python:[^"]+',
			'devcontainers/python:latest',
		)
		self.editRegex('.devcontainer/devcontainer.json', r'features/ruby:[^"]+', 'features/ruby')
		code, output = self.runValidate()
		self.assertEqual(code, 1, output)
		for reference in (
			'mcr.microsoft.com/devcontainers/python:latest',
			'ghcr.io/devcontainers/features/ruby',
		):
			self.assertIn(f'"{reference}" phải ghim phiên bản chính', output)

	def testEslintMustNotEnableIndent(self):
		# Repository dùng ESLint: phải có eslint-config-prettier và không bật indent.
		(self.repo / 'eslint.config.js').write_text(
			"import prettier from 'eslint-config-prettier';\n\n"
			"export default [{ rules: { indent: ['error', 'tab'] } }, prettier];\n",
			encoding='utf-8',
		)
		self.assertFails('eslint.config.js: không bật quy tắc indent')

	def testEslintMustUsePrettierConfig(self):
		(self.repo / 'eslint.config.js').write_text('export default [];\n', encoding='utf-8')
		self.assertFails('eslint.config.js: phải dùng eslint-config-prettier')

	def testIssueFormUsesOnlyAcceptedKeys(self):
		# GitHub từ chối cả biểu mẫu khi gặp khóa lạ, kể cả `type` dù tài liệu có nhắc tới.
		self.edit('.github/ISSUE_TEMPLATE/bug_report.yml', 'labels:\n    - bug\n', 'type: Bug\n')
		self.assertFails('khóa "type" không được GitHub chấp nhận trong biểu mẫu Issue')

	def testRealWorkflowMustNotUseDefaultBranch(self):
		self.edit(
			'.github/workflows/validate.yml',
			'            - main\n',
			'            - $default-branch\n',
		)
		self.assertFails('$default-branch chỉ dùng trong workflow-templates/')

	def testWorkflowMustHaveConcurrency(self):
		self.editRegex('.github/workflows/links.yml', r'^concurrency:\n(?:[ #].*\n)+', '')
		self.assertFails('thiếu khai báo "concurrency" ở cấp workflow')

	def testWritePermissionNeedsComment(self):
		self.editRegex('.github/workflows/release.yml', r'contents: write #.*$', 'contents: write')
		self.assertFails('quyền ghi cần chú thích lý do')

	def testWorkflowTemplateGeneralCategoryFirst(self):
		self.edit(
			'workflow-templates/docs-check.properties.json',
			'["Continuous integration", "Markdown"]',
			'["Markdown", "Continuous integration"]',
		)
		self.assertFails('danh mục đầu tiên phải là danh mục chung')

	def testDependabotMustHaveCooldown(self):
		self.editRegex(
			'.github/dependabot.yml', r'^      cooldown:\n          default-days: \d+\n', ''
		)
		self.assertFails('github-actions: cần cooldown.default-days ≥ 7')

	def testTagRulesetMustProtectReleaseTags(self):
		self.edit('rulesets/protect-release-tags.json', '"refs/tags/v*"', '"refs/tags/release-*"')
		self.assertFails('ruleset phải áp dụng cho refs/tags/v*')

	def testTagRulesetsMustProtectStableAndBeta(self):
		for name in ('protect-release-tags.json', 'org-protect-release-tags.json'):
			for channel in ('Stable', 'Beta'):
				with self.subTest(name=name, channel=channel):
					path = self.repo / 'rulesets' / name
					original = path.read_text(encoding='utf-8')
					self.edit(
						f'rulesets/{name}', f'refs/tags/{channel}.v*', 'refs/tags/unrelated-*'
					)
					self.assertFails(f'refs/tags/{channel}.v*')
					path.write_text(original, encoding='utf-8')

	def testTagRulesetMustBlockDeletion(self):
		# Thiếu deletion nhưng vẫn còn quy tắc khác — luật phải bắt được.
		self.edit('rulesets/protect-release-tags.json', '\t\t{ "type": "deletion" },\n', '')
		self.assertFails('ruleset phải chặn creation, update, deletion')

	def testLabelerLabelsMustExistInLabels(self):
		self.edit('.github/labeler.yml', 'chore:\n', 'viec-vat:\n')
		self.assertFails('nhãn "viec-vat" chưa có trong labels.yml')

	def testLabelerCoversAllBranchPrefixes(self):
		self.edit('.github/labeler.yml', "release:\n    - head-branch: ['^release/']\n", '')
		self.assertFails('thiếu luật head-branch cho tiền tố "release/"')

	def testOrgRulesetTargetsAllRepositories(self):
		self.edit('rulesets/org-protect-main.json', '"~ALL"', '".github"')
		self.assertFails('ruleset phải tên "Protect Main (Organization)" và nhắm mọi repository')

	def testOrgTagRulesetTargetsAllRepositories(self):
		self.edit('rulesets/org-protect-release-tags.json', '"~ALL"', '".github"')
		self.assertFails('nhắm ~ALL repository và refs/tags/v*')

	def testEveryRulesetRequiresSignedCommits(self):
		self.editRegex(
			'rulesets/protect-main.json', r'^\t\t\{ "type": "required_signatures" \},\n', ''
		)
		self.assertFails('protect-main.json: ruleset phải có quy tắc required_signatures')

	def testOrgPushRulesetTargetsAllRepositories(self):
		self.edit('rulesets/org-protect-pushes.json', '"target": "push"', '"target": "branch"')
		self.assertFails('ruleset phải tên "Protect Pushes (Organization)", target "push"')

	def testOrgRulesetMustNotUseUserActor(self):
		self.editRegex(
			'rulesets/org-protect-main.json',
			r'"actor_type": "OrganizationAdmin"',
			'"actor_type": "User"',
		)
		self.assertFails('ruleset cấp tổ chức không dùng actor loại User')

	def testActionMustBePinnedBySha(self):
		# Không gắn cứng SHA: Dependabot nâng action hằng tháng, test phải chạy với mọi SHA.
		self.editRegex(
			'.github/workflows/validate.yml',
			r'actions/checkout@[0-9a-f]{40}',
			'actions/checkout@v4',
		)
		self.assertFails('phải ghim theo commit SHA đầy đủ')

	def testWorkflowTemplateMissingProperties(self):
		(self.repo / 'workflow-templates' / 'node-ci.properties.json').unlink()
		self.assertFails('thiếu tệp node-ci.properties.json')

	def testMissingRequiredFile(self):
		(self.repo / 'CODE_OF_CONDUCT.md').unlink()
		for name in ('README.md', 'CONTRIBUTING.md'):
			path = self.repo / name
			path.write_text(
				path.read_text(encoding='utf-8').replace('(CODE_OF_CONDUCT.md)', '(SUPPORT.md)'),
				encoding='utf-8',
			)
		self.assertFails('thiếu tệp bắt buộc CODE_OF_CONDUCT.md')

	def testChangelogMustStartWithUnreleased(self):
		self.edit('CHANGELOG.md', '## [CHƯA PHÁT HÀNH]', '## [v2099.01.Stable]')
		self.assertFails('mục đầu tiên phải là')


if __name__ == '__main__':
	unittest.main()
