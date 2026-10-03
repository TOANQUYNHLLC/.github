"""Test tự động cho các script trong scripts/: validate.py, conventions.py, release.py, check.py, org-setup.py.

Chạy: python3 -m unittest discover -s scripts -p 'test_*.py'   (hoặc: make test)
Mỗi test chép repository sang thư mục tạm, cố ý làm hỏng một điểm rồi khẳng định
validate.py phát hiện đúng lỗi — để việc sửa script không vô tình làm mất một luật.
"""

import contextlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def loadScript(name):
	"""Nạp một script trong scripts/ (tên có dấu gạch ngang nên không import thường được)."""
	spec = importlib.util.spec_from_file_location(
		name.replace('-', '_'), ROOT / 'scripts' / f'{name}.py'
	)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


class ValidateTest(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.repo = Path(self.tmp.name)
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
		for name in filter(None, names):
			source = ROOT / name
			if source.is_file():
				target = self.repo / name
				target.parent.mkdir(parents=True, exist_ok=True)
				shutil.copy2(source, target)
		subprocess.run(['git', 'init', '-q'], cwd=self.repo, check=True)

	def tearDown(self):
		self.tmp.cleanup()

	def runValidate(self):
		result = subprocess.run(
			[sys.executable, 'scripts/validate.py'],
			cwd=self.repo,
			capture_output=True,
			text=True,
			check=False,
		)
		return result.returncode, result.stdout

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
		source = Path(__file__).read_text(encoding='utf-8')
		self.assertIsNone(
			re.search(r'@[0-9a-f]{40}', source), 'dùng edit_re() với mẫu [0-9a-f]{40}'
		)

	def testCurrentRepositoryIsValid(self):
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

	def testBrokenLink(self):
		self.edit('README.md', '(SECURITY.md)', '(KHONG_TON_TAI.md)')
		self.assertFails('liên kết hỏng: KHONG_TON_TAI.md')

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

	def testSecurityTxtNeedsCompanyEmail(self):
		self.edit('.well-known/security.txt', 'Contact: mailto:toanquynhvn@gmail.com\n', '')
		self.assertFails('Contact phải có mailto:toanquynhvn@gmail.com')

	def testSecurityTxtExpired(self):
		self.editRegex(
			'.well-known/security.txt', r'^Expires: .+$', 'Expires: 2020-01-01T00:00:00.000Z'
		)
		self.assertFails('Expires đã hết hạn')

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
			'run: npm install --no-audit --no-fund',
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

	def testWorkflowMustDeclarePermissions(self):
		self.edit('.github/workflows/links.yml', 'permissions:\n    contents: read\n\n', '')
		self.assertFails('thiếu khai báo "permissions" ở cấp workflow')

	def testJobMustHaveTimeout(self):
		self.editRegex('.github/workflows/links.yml', r'^ +timeout-minutes: \d+\n', '')
		self.assertFails('job "links" thiếu timeout-minutes')

	def testRuffMustUseTabs(self):
		self.edit('ruff.toml', 'indent-style = "tab"', 'indent-style = "space"')
		self.assertFails('ruff.toml: bắt buộc indent-width = 4 và indent-style = "tab"')

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

	def testSecurityTxtExpiresWithinOneYear(self):
		self.editRegex(
			'.well-known/security.txt', r'^Expires: .+$', 'Expires: 2099-01-01T00:00:00.000Z'
		)
		self.assertFails('Expires vượt quá 1 năm')

	def testChangelogVersionsNotDuplicated(self):
		path = self.repo / 'CHANGELOG.md'
		path.write_text(
			path.read_text(encoding='utf-8') + '\n## [v2026.09.Stable]\n', encoding='utf-8'
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
			'docs/adr/0007-mise-single-version-source.md',
			'- **Trạng thái:** Chấp nhận',
			'- **Trạng thái:** Bị thay thế bởi [0008](0008-x.md)',
		)
		self.assertFails('ADR 0007: trạng thái')

	def testAdrIndexAcceptsUnlinkedNumber(self):
		# Mẫu ADR ghi "Bị thay thế bởi NNNN" không kèm liên kết — phải hợp lệ.
		self.edit(
			'docs/adr/0005-merge-protect-main.md',
			'Bị thay thế một phần bởi [0006](0006-allow-all-merge-methods.md)',
			'Bị thay thế một phần bởi 0006',
		)
		code, output = self.runValidate()
		self.assertEqual(code, 0, output)

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


RELEASE_FIXTURE = """# NHẬT KÝ THAY ĐỔI

## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github/compare/v2099.01.Stable...HEAD)

### ✨ THÊM

- Mục mới.

---

## [v2099.01.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2099.01.Stable) — 2099-01-01

### ✨ THÊM

- Mục cũ.

---

<p align="center">© 2099</p>
"""


class ReleaseTest(unittest.TestCase):
	def setUp(self):
		self.module = loadScript('release')
		self.changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')

	def testExtractsVersionNotes(self):
		notes = self.module.releaseNotes(self.changelog, 'v2026.09.Stable')
		self.assertIn('### ✨ THÊM', notes)
		self.assertIn('PULL_REQUEST_TEMPLATE.md', notes)
		self.assertNotIn('<p align="center">', notes)
		self.assertNotIn('CHƯA PHÁT HÀNH', notes)

	def testMissingVersionReturnsNone(self):
		self.assertIsNone(self.module.releaseNotes(self.changelog, 'v1999.01.Stable'))

	def testCutsUnreleasedIntoVersion(self):
		# CHANGELOG mẫu cố định: mục CHƯA PHÁT HÀNH của tệp thật trống ngay sau mỗi lần phát hành.
		changelog = self.module.cutRelease(RELEASE_FIXTURE, 'v2099.02.Stable', '2099-02-01')
		self.assertIn(
			'## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github/compare/v2099.02.Stable...HEAD)',
			changelog,
		)
		self.assertIn(
			'## [v2099.02.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2099.02.Stable)'
			' — 2099-02-01',
			changelog,
		)
		# Mục mới trống; nội dung cũ thành nội dung Release của phiên bản mới; phiên bản cũ giữ nguyên.
		self.assertEqual(self.module.unreleasedNotes(changelog), '')
		self.assertEqual(
			self.module.releaseNotes(changelog, 'v2099.02.Stable'), '### ✨ THÊM\n\n- Mục mới.'
		)
		self.assertEqual(
			self.module.releaseNotes(changelog, 'v2099.01.Stable'), '### ✨ THÊM\n\n- Mục cũ.'
		)
		self.assertLess(
			changelog.index('## [v2099.02.Stable]'), changelog.index('## [v2099.01.Stable]')
		)

	def testEmptyUnreleasedSection(self):
		changelog = self.module.cutRelease(RELEASE_FIXTURE, 'v2099.02.Stable', '2099-02-01')
		self.assertEqual(self.module.unreleasedNotes(changelog), '')
		self.assertIsNone(self.module.releaseNotes(changelog, 'CHƯA PHÁT HÀNH'))
		self.assertIsNone(self.module.unreleasedNotes('# NHẬT KÝ\n'))


class ConventionsTest(unittest.TestCase):
	def setUp(self):
		self.module = loadScript('conventions')

	def check(self, function, value):
		with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
			return function(value)

	def testBranchNames(self):
		for name in ('feature/appointment_booking', 'fix/123_login_error', 'release/v2026.10'):
			self.assertTrue(self.check(self.module.checkBranch, name), name)
		for name in ('feat/x', 'feature/Booking', 'feature/appointment-booking', 'chore'):
			self.assertFalse(self.check(self.module.checkBranch, name), name)
		# Branch của Dependabot và nhánh chính được bỏ qua.
		self.assertTrue(self.check(self.module.checkBranch, 'dependabot/npm_and_yarn/x-1.0'))
		self.assertTrue(self.check(self.module.checkBranch, 'main'))

	def testTitles(self):
		for title in ('feat: thêm', 'fix(booking)!: sửa', 'revert: feat: thêm'):
			self.assertTrue(self.check(self.module.checkTitle, title), title)
		for title in ('Sửa lỗi', 'feature: thêm', 'fix(Booking): sửa', 'fix:thiếu dấu cách'):
			self.assertFalse(self.check(self.module.checkTitle, title), title)


class CheckTest(unittest.TestCase):
	def testValidateWorkflowRunsCheckGroups(self):
		# Mỗi job của validate.yml gọi đúng một nhóm của check.py — tại máy và trên GitHub chạy cùng lệnh.
		groups = loadScript('check').checkGroups()
		workflow = (ROOT / '.github' / 'workflows' / 'validate.yml').read_text(encoding='utf-8')
		called = re.findall(r'run: python3 scripts/check\.py (\w+)$', workflow, re.MULTILINE)
		self.assertEqual(called, ['content', 'format', 'lint'])
		self.assertTrue(set(called) <= set(groups))
		self.assertEqual(list(groups), ['content', 'format', 'lint', 'conventions', 'audit'])


class OrgSetupTest(unittest.TestCase):
	def setUp(self):
		self.module = loadScript('org-setup')
		self.template = (ROOT / 'repository-templates' / 'dependabot.yml').read_text(
			encoding='utf-8'
		)

	def ecosystems(self, text):
		return re.findall(r'package-ecosystem: (\S+)', text)

	def testDependabotKeepsOnlyUsedEcosystems(self):
		text = self.module.filterDependabot(self.template, {'package.json', 'README.md'})
		self.assertEqual(self.ecosystems(text), ['github-actions', 'npm'])

	def testDependabotDetectsPythonGoDocker(self):
		text = self.module.filterDependabot(
			self.template, {'pyproject.toml', 'go.mod', 'Dockerfile'}
		)
		self.assertEqual(self.ecosystems(text), ['github-actions', 'pip', 'gomod', 'docker'])

	def testGeneratedDependabotIsValidYaml(self):
		text = self.module.filterDependabot(self.template, {'package.json'})
		result = subprocess.run(
			['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.dump(YAML.load(STDIN.read))'],
			input=text,
			capture_output=True,
			text=True,
			check=True,
		)
		self.assertEqual(json.loads(result.stdout)['version'], 2)

	def testSharedFilesAndRulesetPerRepository(self):
		files = self.module.plannedFiles(set())
		self.assertEqual(
			sorted(files),
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
		files = self.module.plannedFiles(
			{'package.json', 'pyproject.toml', 'Cargo.toml', 'Dockerfile'}
		)
		for path in (
			'.prettierrc.json',
			'ruff.toml',
			'.python-version',
			'rustfmt.toml',
			'.dockerignore',
		):
			self.assertIn(path, files)
		self.assertNotIn('.clang-format', files)
		self.assertIn('indent-style = "tab"', files['ruff.toml'])
		self.assertIn('hard_tabs = true', files['rustfmt.toml'])

	def testRulesetSummaryIgnoresGithubFields(self):
		wanted = json.loads((ROOT / 'rulesets' / 'protect-main.json').read_text(encoding='utf-8'))
		live = dict(
			wanted, id=1, node_id='RRS_x', source_type='Repository', source='o/r', _links={}
		)
		live['bypass_actors'] = list(reversed(wanted['bypass_actors']))
		live['rules'] = list(reversed(wanted['rules']))
		self.assertEqual(self.module.rulesetSummary(live), self.module.rulesetSummary(wanted))
		changed = dict(wanted, rules=wanted['rules'][1:])
		self.assertNotEqual(self.module.rulesetSummary(changed), self.module.rulesetSummary(wanted))

	def testPrivateRepositorySkipsPrivateVulnerabilityReporting(self):
		self.assertIn(
			'private-vulnerability-reporting', self.module.securityEndpoints(False).values()
		)
		self.assertNotIn(
			'private-vulnerability-reporting', self.module.securityEndpoints(True).values()
		)
		self.assertIn('automated-security-fixes', self.module.securityEndpoints(True).values())
		self.assertIn('immutable-releases', self.module.securityEndpoints(True).values())
		# Dependabot security updates cần Dependabot alerts bật trước.
		endpoints = list(self.module.securityEndpoints(False).values())
		self.assertLess(
			endpoints.index('vulnerability-alerts'), endpoints.index('automated-security-fixes')
		)

	def testRepositorySettingsMergeOverrides(self):
		own = self.module.repositorySettings('.github')
		other = self.module.repositorySettings('app')
		self.assertFalse(own['allow_rebase_merge'])
		self.assertTrue(own['has_discussions'])
		self.assertNotIn('has_discussions', other)
		self.assertNotIn('homepage', other)
		self.assertTrue(self.module.repositorySettings('app', discussions=True)['has_discussions'])
		self.assertIn('rulesets', self.module.citationKeywords())

	def testActionsPermissionsKeepEnabledState(self):
		calls = []
		live = {
			'repos/x/actions/permissions': {'enabled': True, 'allowed_actions': 'all'},
			'repos/x/actions/permissions/workflow': dict(self.module.WORKFLOW_PERMISSIONS),
		}
		self.module.ghJson = lambda *args: live[args[1]]
		self.module.gh = lambda *args, **kwargs: calls.append((args, kwargs.get('stdin')))
		with contextlib.redirect_stdout(io.StringIO()):
			self.module.syncActions(
				'repos/x/actions/permissions', self.module.ACTIONS_PERMISSIONS, 'enabled', True
			)
		# Chỉ ghi phần khác (sha_pinning_required) và gửi lại enabled đang có — không bật, tắt Actions.
		self.assertEqual(len(calls), 1)
		self.assertEqual(json.loads(calls[0][1]), {'sha_pinning_required': True, 'enabled': True})
		# Actions đang tắt: GitHub không trả quyền — bỏ qua, không ghi.
		calls.clear()
		live['repos/x/actions/permissions'] = {'enabled': False, 'sha_pinning_required': False}
		with contextlib.redirect_stdout(io.StringIO()):
			self.module.syncActions(
				'repos/x/actions/permissions', self.module.ACTIONS_PERMISSIONS, 'enabled', True
			)
		self.assertEqual(calls, [])

	def testOrgRulesetFilesMatchGenerated(self):
		# Tệp để import trên web phải đúng bằng orgRulesets() sinh từ bản cấp repository.
		for source, ruleset in self.module.orgRulesets():
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
		self.assertEqual(
			self.module.graphqlRuleset(live)['rules'], [self.module.ORG_CODE_SCANNING_RULE]
		)
		# Chỉ bản cấp tổ chức có code scanning, như trên web.
		self.assertIn(self.module.ORG_CODE_SCANNING_RULE, self.module.orgRuleset()['rules'])
		self.assertNotIn(
			'code_scanning', [r['type'] for r in self.module.rulesetFor('app')['rules']]
		)

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
		wanted = self.module.graphqlVisible(self.module.orgTagRuleset())
		live = self.module.graphqlRuleset(node)
		self.assertEqual(self.module.rulesetSummary(live), self.module.rulesetSummary(wanted))
		node['rules']['nodes'].pop()
		self.assertNotEqual(
			self.module.rulesetSummary(self.module.graphqlRuleset(node)),
			self.module.rulesetSummary(wanted),
		)
		# Push ruleset: không có refName, tham số của quy tắc push đổi sang dạng REST.
		pushes = self.module.orgPushRuleset()
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
			self.module.rulesetSummary(self.module.graphqlRuleset(node)),
			self.module.rulesetSummary(self.module.graphqlVisible(pushes)),
		)
		main = self.module.graphqlVisible(self.module.orgRuleset())
		for rule in main['rules']:
			self.assertNotIn(
				'require_extra_approval_for_unattributed_changes', rule.get('parameters', {})
			)

	def testTeamsAlreadyCorrectAreNotWritten(self):
		calls = []
		self.module.ghExists = lambda endpoint: True
		details = {
			team: {'name': name, 'description': description, 'privacy': privacy}
			for team, (name, _, privacy, description) in self.module.TEAMS.items()
		}
		self.module.teamDetails = lambda team: details[team]
		self.module.teamRole = lambda team, user: 'maintainer'
		# Quyền cao hơn (admin) đã đủ cho mọi team — không hạ quyền.
		self.module.teamPermission = lambda team, repo: 'admin'
		self.module.gh = lambda *args, **kwargs: calls.append(args)
		output = io.StringIO()
		with contextlib.redirect_stdout(output):
			self.module.syncTeams(['.github', 'app'], apply=True)
		self.assertEqual(output.getvalue().count('✔ đủ người quản trị'), len(self.module.TEAMS))
		self.assertEqual(calls, [])
		# Chỉ ghi phần còn thiếu: một người chưa là maintainer, một repository chưa đủ quyền.
		self.module.teamRole = lambda team, user: (
			'member' if (team, user) == ('maintainers', 'trongtoandl81') else 'maintainer'
		)
		self.module.teamPermission = lambda team, repo: (
			'write' if (team, repo) == ('maintainers', 'app') else 'admin'
		)
		with contextlib.redirect_stdout(io.StringIO()):
			self.module.syncTeams(['.github', 'app'], apply=True)
		self.assertEqual(
			[args[3] for args in calls],
			[
				'orgs/TOANQUYNHLLC/teams/maintainers/memberships/trongtoandl81',
				'orgs/TOANQUYNHLLC/teams/maintainers/repos/TOANQUYNHLLC/app',
			],
		)

	def testTeamDescriptionDriftIsPatched(self):
		calls = []
		self.module.ghExists = lambda endpoint: True
		self.module.teamRole = lambda team, user: 'maintainer'
		self.module.teamPermission = lambda team, repo: 'admin'
		self.module.teamDetails = lambda team: {
			'name': self.module.TEAMS[team][0],
			'description': 'mô tả cũ' if team == 'qa' else self.module.TEAMS[team][3],
			'privacy': self.module.TEAMS[team][2],
		}
		self.module.gh = lambda *args, **kwargs: calls.append((args, kwargs.get('stdin')))
		with contextlib.redirect_stdout(io.StringIO()):
			self.module.syncTeams(['.github'], apply=True)
		self.assertEqual([args[3] for args, _ in calls], ['orgs/TOANQUYNHLLC/teams/qa'])
		self.assertEqual(json.loads(calls[0][1]), {'description': self.module.TEAMS['qa'][3]})

	def testLabelsOnlyWriteDifferences(self):
		calls = []
		wanted = self.module.loadLabels()
		live = [dict(label) for label in wanted[1:]]
		live[0]['color'] = '000000'
		self.module.ghJson = lambda *args: live
		self.module.gh = lambda *args, **kwargs: calls.append(args)
		with contextlib.redirect_stdout(io.StringIO()):
			self.module.syncLabels(['app'], apply=True)
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
			[ruleset['name'] for _, ruleset in self.module.rulesetsFor('app')],
			['Protect Main', 'Protect Release Tags'],
		)
		own = self.module.rulesetFor('.github')
		other = self.module.rulesetFor('app')
		self.assertEqual(own['name'], 'Protect Main')
		self.assertEqual(other['name'], 'Protect Main')
		self.assertEqual(len(checks(own)), 5)
		self.assertEqual(
			sorted(checks(other)), ['Kiểm tra tiêu đề Pull Request', 'Kiểm tra tên branch']
		)


if __name__ == '__main__':
	unittest.main()
