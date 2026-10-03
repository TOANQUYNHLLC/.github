"""Test tự động cho scripts/validate.py, scripts/release-notes.py và scripts/org-setup.py.

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


def load_release_notes():
	spec = importlib.util.spec_from_file_location(
		'release_notes', ROOT / 'scripts' / 'release-notes.py'
	)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def load_org_setup():
	spec = importlib.util.spec_from_file_location('org_setup', ROOT / 'scripts' / 'org-setup.py')
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

	def run_validate(self):
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

	def edit_re(self, name, pattern, new):
		"""Như edit() nhưng tìm bằng regex — dùng cho giá trị sẽ đổi theo thời gian (SHA, ngày, số)."""
		path = self.repo / name
		text, count = re.subn(
			pattern, new, path.read_text(encoding='utf-8'), count=1, flags=re.MULTILINE
		)
		self.assertEqual(count, 1, f'{name} không còn khớp mẫu {pattern!r}')
		path.write_text(text, encoding='utf-8')

	def assert_fails(self, message):
		code, output = self.run_validate()
		self.assertEqual(code, 1, output)
		self.assertIn(message, output)

	def test_khong_gan_cung_sha_action_trong_test(self):
		# SHA gắn cứng làm mọi Pull Request Dependabot nâng action bị chặn vì test mất đoạn neo.
		source = Path(__file__).read_text(encoding='utf-8')
		self.assertIsNone(
			re.search(r'@[0-9a-f]{40}', source), 'dùng edit_re() với mẫu [0-9a-f]{40}'
		)

	def test_repository_hien_tai_hop_le(self):
		code, output = self.run_validate()
		self.assertEqual(code, 0, output)

	def test_lien_ket_hong(self):
		self.edit('README.md', '(SECURITY.md)', '(KHONG_TON_TAI.md)')
		self.assert_fails('liên kết hỏng: KHONG_TON_TAI.md')

	def test_lien_ket_toi_muc_phai_ton_tai(self):
		self.edit('profile/README.md', '## 📞 THÔNG TIN LIÊN HỆ', '## 📞 LIÊN HỆ')
		self.assert_fails('liên kết hỏng: profile/README.md#-thông-tin-liên-hệ')

	def test_tieu_de_phai_viet_hoa(self):
		self.edit('README.md', '## 🎯 MỤC ĐÍCH', '## 🎯 Mục đích')
		self.assert_fails('tiêu đề phải viết hoa')

	def test_mau_email_bao_mat_phai_khop_lien_ket(self):
		self.edit('SECURITY.md', '- **Mô tả vấn đề:**', '- **Mô tả lỗi:**')
		self.assert_fails('nội dung liên kết email khác mẫu')

	def test_email_chung_khong_duoc_doi(self):
		# Ghép địa chỉ lúc chạy để chính file test không chứa email nào khác email chung.
		self.edit('SUPPORT.md', 'toanquynhvn@gmail.com', 'lienhe' + '@' + 'example.com')
		self.assert_fails('khác email chung của công ty')

	def test_security_txt_phai_co_email_cong_ty(self):
		self.edit('.well-known/security.txt', 'Contact: mailto:toanquynhvn@gmail.com\n', '')
		self.assert_fails('Contact phải có mailto:toanquynhvn@gmail.com')

	def test_security_txt_het_han(self):
		self.edit_re(
			'.well-known/security.txt', r'^Expires: .+$', 'Expires: 2020-01-01T00:00:00.000Z'
		)
		self.assert_fails('Expires đã hết hạn')

	def test_shell_phai_thut_le_bang_tab(self):
		self.edit('scripts/sync-labels.sh', '\tAPPLY=true', '    APPLY=true')
		self.assert_fails('thụt lề phải dùng tab')

	def test_prettier_phai_dung_tab_do_rong_4(self):
		self.edit('.prettierrc.json', '"tabWidth": 4', '"tabWidth": 2')
		self.assert_fails('bắt buộc "useTabs": true và "tabWidth": 4')

	def test_editorconfig_khong_duoc_dung_do_rong_2(self):
		self.edit('.editorconfig', 'indent_size = 4', 'indent_size = 2')
		self.assert_fails('không được dùng độ rộng 2')

	def test_markdown_khong_duoc_thut_le_bang_tab(self):
		self.edit('SUPPORT.md', '- Đọc `README.md`', '\t- Đọc `README.md`')
		self.assert_fails('phải thụt lề bằng 4 dấu cách')

	def test_yaml_khong_hop_le(self):
		self.edit('labels.yml', '  color: ', '\tcolor: ')
		self.assert_fails('YAML không hợp lệ')

	def test_khoang_trang_cuoi_dong(self):
		line = '# Bộ nhãn chuẩn cho mọi repository của CÔNG TY TNHH TOÀN QUỲNH.'
		self.edit('labels.yml', line, line + '  ')
		self.assert_fails('có khoảng trắng cuối dòng')

	def test_batch_phai_xuong_dong_crlf(self):
		(self.repo / 'scripts' / 'build.cmd').write_bytes(b'@echo off\ngoto :eof\n')
		self.assert_fails('phải xuống dòng bằng CRLF')

	def test_batch_crlf_hop_le(self):
		(self.repo / 'scripts' / 'build.cmd').write_bytes(b'@echo off\r\ngoto :eof\r\n')
		code, output = self.run_validate()
		self.assertEqual(code, 0, output)

	def test_registry_utf16_crlf_hop_le(self):
		content = 'Windows Registry Editor Version 5.00\r\n'
		(self.repo / 'scripts' / 'setup.reg').write_bytes(b'\xff\xfe' + content.encode('utf-16-le'))
		code, output = self.run_validate()
		self.assertEqual(code, 0, output)

	def test_registry_phai_la_utf16(self):
		(self.repo / 'scripts' / 'setup.reg').write_bytes(
			b'Windows Registry Editor Version 5.00\r\n'
		)
		self.assert_fails('phải mã hóa UTF-16 LE có BOM')

	def test_solution_phai_co_bom(self):
		(self.repo / 'scripts' / 'App.sln').write_bytes(
			b'Microsoft Visual Studio Solution File\r\n'
		)
		self.assert_fails('thiếu BOM UTF-8')

	def test_solution_co_bom_crlf_hop_le(self):
		(self.repo / 'scripts' / 'App.sln').write_bytes(
			b'\xef\xbb\xbfMicrosoft Visual Studio Solution File\r\n'
		)
		code, output = self.run_validate()
		self.assertEqual(code, 0, output)

	def test_fsharp_khong_duoc_thut_le_bang_tab(self):
		(self.repo / 'scripts' / 'App.fs').write_text('let f x =\n\tx + 1\n', encoding='utf-8')
		self.assert_fails('phải thụt lề bằng 4 dấu cách')

	def test_dart_khong_duoc_thut_le_bang_tab(self):
		(self.repo / 'scripts' / 'main.dart').write_text(
			'void main() {\n\tprint(1);\n}\n', encoding='utf-8'
		)
		self.assert_fails('phải thụt lề bằng 2 dấu cách')

	def test_editorconfig_do_rong_2_chi_cho_ngon_ngu_bat_buoc(self):
		self.edit(
			'.editorconfig',
			'nimble,zig,zon}]\nindent_style = space\n',
			'nimble,zig,zon}]\nindent_style = space\nindent_size = 2\n',
		)
		self.assert_fails('không được dùng độ rộng 2')

	def test_csv_giu_khoang_trang_cuoi_dong(self):
		(self.repo / 'scripts' / 'data.csv').write_bytes(b'ten,ghi chu\r\nA,co dau cach \r\n')
		code, output = self.run_validate()
		self.assertEqual(code, 0, output)

	def test_gitattributes_phai_khop_danh_sach_crlf(self):
		self.edit('.gitattributes', '*.dsw text eol=crlf\n', '')
		self.assert_fails('.gitattributes: thiếu .dsw text eol=crlf')

	def test_editorconfig_phai_khop_danh_sach_crlf(self):
		self.edit('.editorconfig', '[*.{bat,cmd,', '[*.{bat,')
		self.assert_fails('.editorconfig: thiếu .cmd trong mục "end_of_line = crlf"')

	def test_loai_commit_phai_khop_contributing(self):
		self.edit('.github/workflows/pr-title.yml', '|revert)', ')')
		self.assert_fails('.github/workflows/pr-title.yml: thiếu "revert" so với CONTRIBUTING.md')

	def test_tien_to_branch_phai_khop_contributing(self):
		self.edit('workflow-templates/branch-name.yml', '|release)', ')')
		self.assert_fails(
			'workflow-templates/branch-name.yml: thiếu "release" so với CONTRIBUTING.md'
		)

	def test_ruleset_phai_trung_ten_job(self):
		self.edit('rulesets/protect-main.json', '"Shell script và workflow"', '"Shell script"')
		self.assert_fails('kiểm tra bắt buộc "Shell script" không trùng tên job nào')

	def test_tieng_viet_phai_la_nfc(self):
		path = self.repo / 'SUPPORT.md'
		text = path.read_text(encoding='utf-8')
		path.write_text(unicodedata.normalize('NFD', text), encoding='utf-8')
		self.assert_fails('dạng tách dấu (NFD)')

	def test_phien_ban_cong_cu_chi_o_mise(self):
		self.edit(
			'.github/workflows/validate.yml',
			'run: ruff format --check scripts',
			'run: pip install ruff==0.1.0',
		)
		self.assert_fails('phiên bản công cụ phải lấy từ mise.toml')

	def test_xuong_dong_crlf(self):
		path = self.repo / 'SUPPORT.md'
		path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
		self.assert_fails('phải xuống dòng bằng LF')

	def test_nhan_trong_bieu_mau_phai_co_trong_labels(self):
		self.edit('.github/ISSUE_TEMPLATE/question.yml', '    - question', '    - hoi-dap')
		self.assert_fails('chưa có trong labels.yml')

	def test_bieu_mau_discussion_khong_ho_tro_name(self):
		self.edit(
			'.github/DISCUSSION_TEMPLATE/q-a.yml',
			"title: '[Hỏi đáp] '",
			"name: Hỏi đáp\ntitle: '[Hỏi đáp] '",
		)
		self.assert_fails('biểu mẫu Discussion không hỗ trợ khóa "name"')

	def test_bieu_mau_discussion_tieu_de_truong_viet_hoa(self):
		self.edit('.github/DISCUSSION_TEMPLATE/ideas.yml', 'label: 💡 Ý TƯỞNG', 'label: 💡 Ý tưởng')
		self.assert_fails('phải viết hoa')

	def test_bieu_mau_phai_nam_trong_thu_muc_github(self):
		(self.repo / '.github' / 'ISSUE_TEMPLATE').rename(self.repo / 'ISSUE_TEMPLATE')
		self.assert_fails('phải nằm trong thư mục .github/ để GitHub nhận diện')

	def test_bieu_mau_khong_dung_lien_ket_tuong_doi(self):
		self.edit(
			'.github/DISCUSSION_TEMPLATE/general.yml',
			'(https://github.com/TOANQUYNHLLC/.github/blob/main/CODE_OF_CONDUCT.md)',
			'(CODE_OF_CONDUCT.md)',
		)
		self.assert_fails('phải là URL tuyệt đối')

	def test_nhan_trong_cau_hinh_phai_co_trong_labels(self):
		self.edit('workflow-templates/stale.yml', 'stale-pr-label: stale', 'stale-pr-label: cu')
		self.assert_fails('nhãn "cu" chưa có trong labels.yml')

	def test_quyen_ghi_khong_cap_o_cap_workflow(self):
		# Khối permissions cấp workflow (không thụt lề) — không phụ thuộc thứ tự khối phía sau.
		self.edit_re(
			'.github/workflows/release.yml',
			r'^permissions:\n    contents: read$',
			'permissions:\n    contents: write',
		)
		self.assert_fails('quyền ghi chỉ cấp ở job cần dùng')

	def test_tep_khong_duoi_cung_duoc_kiem_tra(self):
		path = self.repo / 'NOTICE'
		path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
		self.assert_fails('NOTICE: phải xuống dòng bằng LF')

	def test_danh_sach_nhi_phan_khop_gitattributes(self):
		self.edit('.gitattributes', '*.zip binary\n', '')
		self.assert_fails('.gitattributes: thiếu .zip binary so với validate.py')

	def test_workflow_phai_khai_bao_permissions(self):
		self.edit('.github/workflows/links.yml', 'permissions:\n    contents: read\n\n', '')
		self.assert_fails('thiếu khai báo "permissions" ở cấp workflow')

	def test_job_phai_co_timeout(self):
		self.edit_re('.github/workflows/links.yml', r'^ +timeout-minutes: \d+\n', '')
		self.assert_fails('job "links" thiếu timeout-minutes')

	def test_ruff_phai_dung_tab(self):
		self.edit('ruff.toml', 'indent-style = "tab"', 'indent-style = "space"')
		self.assert_fails('ruff.toml: bắt buộc indent-width = 4 và indent-style = "tab"')

	def test_node_khong_khai_bao_trong_mise(self):
		self.edit('mise.toml', '[tools]\n', '[tools]\nnode = "24"\n')
		self.assert_fails('Node.js khai báo trong .nvmrc')

	def test_thieu_dong_trong_cuoi_file(self):
		path = self.repo / 'SUPPORT.md'
		path.write_bytes(path.read_bytes().rstrip(b'\n'))
		self.assert_fails('SUPPORT.md: thiếu dòng trống cuối file')

	def test_khong_duoc_co_bom_utf8(self):
		path = self.repo / 'SUPPORT.md'
		path.write_bytes(b'\xef\xbb\xbf' + path.read_bytes())
		self.assert_fails('SUPPORT.md: có BOM UTF-8')

	def test_shell_phai_co_shebang(self):
		self.edit('scripts/pre-commit.sh', '#!/usr/bin/env bash\n', '')
		self.assert_fails('shell script thiếu shebang')

	def test_security_txt_han_toi_da_mot_nam(self):
		self.edit_re(
			'.well-known/security.txt', r'^Expires: .+$', 'Expires: 2099-01-01T00:00:00.000Z'
		)
		self.assert_fails('Expires vượt quá 1 năm')

	def test_changelog_khong_lap_phien_ban(self):
		path = self.repo / 'CHANGELOG.md'
		path.write_text(
			path.read_text(encoding='utf-8') + '\n## [v2026.09.Stable]\n', encoding='utf-8'
		)
		self.assert_fails('có phiên bản bị lặp')

	def test_mau_nhan_phai_la_hex(self):
		self.edit_re('labels.yml', r"color: '[0-9a-fA-F]{6}'", "color: 'do'")
		self.assert_fails('color phải là mã hex 6 ký tự')

	def test_bieu_mau_khong_trung_id(self):
		self.edit('.github/ISSUE_TEMPLATE/bug_report.yml', 'id: expected', 'id: description')
		self.assert_fails('id "description" bị trùng')

	def test_contact_links_du_truong(self):
		self.edit_re('.github/ISSUE_TEMPLATE/config.yml', r'^ +about: .+\n', '')
		self.assert_fails('contact_links thiếu "about"')

	def test_ruleset_phai_ten_protect_main(self):
		self.edit('rulesets/protect-main.json', '"name": "Protect Main"', '"name": "Bảo vệ"')
		self.assert_fails('ruleset phải tên "Protect Main"')

	def test_muc_luc_adr_khop_trang_thai(self):
		self.edit(
			'docs/adr/0006-allow-all-merge-methods.md',
			'- **Trạng thái:** Chấp nhận',
			'- **Trạng thái:** Bị thay thế bởi [0008](0008-x.md)',
		)
		self.assert_fails('ADR 0006: trạng thái')

	def test_muc_luc_adr_nhan_so_khong_lien_ket(self):
		# Mẫu ADR ghi "Bị thay thế bởi NNNN" không kèm liên kết — phải hợp lệ.
		self.edit(
			'docs/adr/0005-merge-protect-main.md',
			'Bị thay thế một phần bởi [0006](0006-allow-all-merge-methods.md)',
			'Bị thay thế một phần bởi 0006',
		)
		code, output = self.run_validate()
		self.assertEqual(code, 0, output)

	def test_muc_luc_adr_du_moi_adr(self):
		# Số 9999 không trùng ADR thật nào — test không phải sửa mỗi khi thêm ADR.
		(self.repo / 'docs' / 'adr' / '9999-thu.md').write_text(
			'# 9999. THỬ\n\n- **Trạng thái:** Đề xuất\n- **Ngày:** 2026-09-27\n', encoding='utf-8'
		)
		self.assert_fails('bảng thiếu ADR 9999')

	def test_toml_phai_thut_le_bang_tab(self):
		self.edit('mise.toml', '[tools]\n', '[tools]\n    ')
		code, output = self.run_validate()
		self.assertEqual(code, 1, output)
		self.assertRegex(output, r'mise\.toml: dòng \d+: thụt lề phải dùng tab')

	def test_chu_thich_khoi_js_hop_le(self):
		path = self.repo / 'eslint.config.js'
		path.write_text(
			path.read_text(encoding='utf-8') + '\n/**\n * Chú thích khối.\n */\n', encoding='utf-8'
		)
		code, output = self.run_validate()
		self.assertEqual(code, 0, output)

	def test_prettier_khop_cau_hinh_chuan(self):
		self.edit('.prettierrc.json', '"printWidth": 100', '"printWidth": 120')
		self.assert_fails('.prettierrc.json: "printWidth" phải là 100')

	def test_ruff_khop_cau_hinh_chuan(self):
		self.edit('ruff.toml', 'line-ending = "lf"', 'line-ending = "cr-lf"')
		self.assert_fails('ruff.toml: format.line-ending phải là "lf"')

	def test_editorconfig_khop_cau_hinh_chuan(self):
		self.edit(
			'.editorconfig',
			'[*]\ncharset = utf-8\nend_of_line = lf\n',
			'[*]\ncharset = utf-8\nend_of_line = crlf\n',
		)
		self.assert_fails('.editorconfig: mục [*] thiếu "end_of_line = lf"')

	def test_prettierignore_khong_lap_gitignore(self):
		self.edit('.prettierignore', 'LICENSE\n', 'LICENSE\nnode_modules/\n')
		self.assert_fails('.prettierignore: "node_modules/" đã có trong .gitignore')

	def test_eslint_khong_bat_indent(self):
		self.edit(
			'eslint.config.js',
			"eqeqeq: ['error', 'always'],",
			"eqeqeq: ['error', 'always'],\n\t\t\tindent: ['error', 'tab'],",
		)
		self.assert_fails('eslint.config.js: không bật quy tắc indent')

	def test_bieu_mau_issue_chi_dung_khoa_duoc_chap_nhan(self):
		# GitHub từ chối cả biểu mẫu khi gặp khóa lạ, kể cả `type` dù tài liệu có nhắc tới.
		self.edit('.github/ISSUE_TEMPLATE/bug_report.yml', 'labels:\n    - bug\n', 'type: Bug\n')
		self.assert_fails('khóa "type" không được GitHub chấp nhận trong biểu mẫu Issue')

	def test_workflow_that_khong_dung_default_branch(self):
		self.edit(
			'.github/workflows/validate.yml',
			'            - main\n',
			'            - $default-branch\n',
		)
		self.assert_fails('$default-branch chỉ dùng trong workflow-templates/')

	def test_workflow_phai_co_concurrency(self):
		self.edit_re('.github/workflows/links.yml', r'^concurrency:\n(?:[ #].*\n)+', '')
		self.assert_fails('thiếu khai báo "concurrency" ở cấp workflow')

	def test_quyen_ghi_phai_co_chu_thich(self):
		self.edit_re('.github/workflows/release.yml', r'contents: write #.*$', 'contents: write')
		self.assert_fails('quyền ghi cần chú thích lý do')

	def test_workflow_mau_danh_muc_chung_dung_dau(self):
		self.edit(
			'workflow-templates/docs-check.properties.json',
			'["Continuous integration", "Markdown"]',
			'["Markdown", "Continuous integration"]',
		)
		self.assert_fails('danh mục đầu tiên phải là danh mục chung')

	def test_dependabot_phai_co_cooldown(self):
		self.edit_re(
			'.github/dependabot.yml', r'^      cooldown:\n          default-days: \d+\n', ''
		)
		self.assert_fails('github-actions: cần cooldown.default-days ≥ 7')

	def test_ruleset_tag_phai_bao_ve_tag_phat_hanh(self):
		self.edit('rulesets/protect-release-tags.json', '"refs/tags/v*"', '"refs/tags/release-*"')
		self.assert_fails('ruleset phải áp dụng cho refs/tags/v*')

	def test_ruleset_tag_phai_chan_xoa(self):
		# Thiếu deletion nhưng vẫn còn quy tắc khác — luật phải bắt được.
		self.edit('rulesets/protect-release-tags.json', '\t\t{ "type": "deletion" },\n', '')
		self.assert_fails('ruleset phải chặn creation, update, deletion')

	def test_nhan_trong_labeler_phai_co_trong_labels(self):
		self.edit('.github/labeler.yml', 'chore:\n', 'viec-vat:\n')
		self.assert_fails('nhãn "viec-vat" chưa có trong labels.yml')

	def test_labeler_du_tien_to_branch(self):
		self.edit('.github/labeler.yml', "release:\n    - head-branch: ['^release/']\n", '')
		self.assert_fails('thiếu luật head-branch cho tiền tố "release/"')

	def test_ruleset_to_chuc_nham_moi_repository(self):
		self.edit('rulesets/org-protect-main.json', '"~ALL"', '".github"')
		self.assert_fails('ruleset phải tên "Protect Main (Organization)" và nhắm mọi repository')

	def test_ruleset_tag_to_chuc_nham_moi_repository(self):
		self.edit('rulesets/org-protect-release-tags.json', '"~ALL"', '".github"')
		self.assert_fails('nhắm ~ALL repository và refs/tags/v*')

	def test_moi_ruleset_bat_buoc_commit_co_chu_ky(self):
		self.edit_re(
			'rulesets/protect-main.json', r'^\t\t\{ "type": "required_signatures" \},\n', ''
		)
		self.assert_fails('protect-main.json: ruleset phải có quy tắc required_signatures')

	def test_push_ruleset_to_chuc_nham_moi_repository(self):
		self.edit('rulesets/org-protect-pushes.json', '"target": "push"', '"target": "branch"')
		self.assert_fails('ruleset phải tên "Protect Pushes (Organization)", target "push"')

	def test_ruleset_to_chuc_khong_dung_actor_user(self):
		self.edit_re(
			'rulesets/org-protect-main.json',
			r'"actor_type": "OrganizationAdmin"',
			'"actor_type": "User"',
		)
		self.assert_fails('ruleset cấp tổ chức không dùng actor loại User')

	def test_action_phai_ghim_sha(self):
		# Không gắn cứng SHA: Dependabot nâng action hằng tháng, test phải chạy với mọi SHA.
		self.edit_re(
			'.github/workflows/validate.yml',
			r'actions/checkout@[0-9a-f]{40}',
			'actions/checkout@v4',
		)
		self.assert_fails('phải ghim theo commit SHA đầy đủ')

	def test_workflow_mau_thieu_properties(self):
		(self.repo / 'workflow-templates' / 'node-ci.properties.json').unlink()
		self.assert_fails('thiếu tệp node-ci.properties.json')

	def test_thieu_tep_bat_buoc(self):
		(self.repo / 'CODE_OF_CONDUCT.md').unlink()
		for name in ('README.md', 'CONTRIBUTING.md'):
			path = self.repo / name
			path.write_text(
				path.read_text(encoding='utf-8').replace('(CODE_OF_CONDUCT.md)', '(SUPPORT.md)'),
				encoding='utf-8',
			)
		self.assert_fails('thiếu tệp bắt buộc CODE_OF_CONDUCT.md')

	def test_changelog_phai_bat_dau_bang_chua_phat_hanh(self):
		self.edit('CHANGELOG.md', '## [CHƯA PHÁT HÀNH]', '## [v2099.01.Stable]')
		self.assert_fails('mục đầu tiên phải là')


class ReleaseNotesTest(unittest.TestCase):
	def setUp(self):
		self.module = load_release_notes()
		self.changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')

	def test_lay_dung_noi_dung_phien_ban(self):
		notes = self.module.release_notes(self.changelog, 'v2026.09.Stable')
		self.assertIn('### ✨ THÊM', notes)
		self.assertIn('PULL_REQUEST_TEMPLATE.md', notes)
		self.assertNotIn('<p align="center">', notes)
		self.assertNotIn('CHƯA PHÁT HÀNH', notes)

	def test_phien_ban_chua_co_trong_changelog(self):
		self.assertIsNone(self.module.release_notes(self.changelog, 'v1999.01.Stable'))


class OrgSetupTest(unittest.TestCase):
	def setUp(self):
		self.module = load_org_setup()
		self.template = (ROOT / 'repository-templates' / 'dependabot.yml').read_text(
			encoding='utf-8'
		)

	def ecosystems(self, text):
		return re.findall(r'package-ecosystem: (\S+)', text)

	def test_dependabot_chi_giu_ecosystem_repository_dung(self):
		text = self.module.filter_dependabot(self.template, {'package.json', 'README.md'})
		self.assertEqual(self.ecosystems(text), ['github-actions', 'npm'])

	def test_dependabot_nhan_dien_python_go_docker(self):
		text = self.module.filter_dependabot(
			self.template, {'pyproject.toml', 'go.mod', 'Dockerfile'}
		)
		self.assertEqual(self.ecosystems(text), ['github-actions', 'pip', 'gomod', 'docker'])

	def test_dependabot_sinh_ra_la_yaml_hop_le(self):
		text = self.module.filter_dependabot(self.template, {'package.json'})
		result = subprocess.run(
			['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.dump(YAML.load(STDIN.read))'],
			input=text,
			capture_output=True,
			text=True,
			check=True,
		)
		self.assertEqual(json.loads(result.stdout)['version'], 2)

	def test_tep_dung_chung_du_va_ruleset_dung_repository(self):
		files = self.module.planned_files(set())
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

	def test_tep_theo_ngon_ngu(self):
		files = self.module.planned_files(
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

	def test_so_sanh_ruleset_bo_qua_truong_github_them(self):
		wanted = json.loads((ROOT / 'rulesets' / 'protect-main.json').read_text(encoding='utf-8'))
		live = dict(
			wanted, id=1, node_id='RRS_x', source_type='Repository', source='o/r', _links={}
		)
		live['bypass_actors'] = list(reversed(wanted['bypass_actors']))
		live['rules'] = list(reversed(wanted['rules']))
		self.assertEqual(self.module.ruleset_summary(live), self.module.ruleset_summary(wanted))
		changed = dict(wanted, rules=wanted['rules'][1:])
		self.assertNotEqual(
			self.module.ruleset_summary(changed), self.module.ruleset_summary(wanted)
		)

	def test_repository_rieng_tu_bo_qua_bao_cao_lo_hong_rieng_tu(self):
		self.assertIn(
			'private-vulnerability-reporting', self.module.security_endpoints(False).values()
		)
		self.assertNotIn(
			'private-vulnerability-reporting', self.module.security_endpoints(True).values()
		)
		self.assertIn('automated-security-fixes', self.module.security_endpoints(True).values())
		self.assertIn('immutable-releases', self.module.security_endpoints(True).values())

	def test_tep_ruleset_to_chuc_khop_protect_main(self):
		# Tệp để import trên web phải đúng bằng org_ruleset() sinh từ Protect Main.
		for source, ruleset in self.module.org_rulesets():
			self.assertEqual(json.loads(source.read_text(encoding='utf-8')), ruleset, source.name)

	def test_so_ruleset_to_chuc_doc_qua_graphql(self):
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
		wanted = self.module.graphql_visible(self.module.org_tag_ruleset())
		live = self.module.graphql_ruleset(node)
		self.assertEqual(self.module.ruleset_summary(live), self.module.ruleset_summary(wanted))
		node['rules']['nodes'].pop()
		self.assertNotEqual(
			self.module.ruleset_summary(self.module.graphql_ruleset(node)),
			self.module.ruleset_summary(wanted),
		)
		# Push ruleset: không có refName, tham số của quy tắc push đổi sang dạng REST.
		pushes = self.module.org_push_ruleset()
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
			self.module.ruleset_summary(self.module.graphql_ruleset(node)),
			self.module.ruleset_summary(self.module.graphql_visible(pushes)),
		)
		main = self.module.graphql_visible(self.module.org_ruleset())
		for rule in main['rules']:
			self.assertNotIn(
				'require_extra_approval_for_unattributed_changes', rule.get('parameters', {})
			)

	def test_team_da_dung_thi_khong_ghi(self):
		calls = []
		self.module.gh_exists = lambda endpoint: True
		self.module.team_role = lambda user: 'maintainer'
		self.module.team_permission = lambda repo: 'admin' if repo == '.github' else 'maintain'
		self.module.gh = lambda *args, **kwargs: calls.append(args)
		output = io.StringIO()
		with contextlib.redirect_stdout(output):
			self.module.cmd_team(['.github', 'app'], apply=True)
		self.assertIn('✔ đủ người quản trị', output.getvalue())
		self.assertEqual(calls, [])
		# Chỉ ghi phần còn thiếu: một người chưa là maintainer, một repository chưa có quyền.
		self.module.team_role = lambda user: 'member' if user == 'trongtoandl81' else 'maintainer'
		self.module.team_permission = lambda repo: 'push' if repo == 'app' else 'maintain'
		with contextlib.redirect_stdout(io.StringIO()):
			self.module.cmd_team(['.github', 'app'], apply=True)
		self.assertEqual(
			[args[3] for args in calls],
			[
				'orgs/TOANQUYNHLLC/teams/maintainers/memberships/trongtoandl81',
				'orgs/TOANQUYNHLLC/teams/maintainers/repos/TOANQUYNHLLC/app',
			],
		)

	def test_ruleset_protect_main_cho_moi_repository(self):
		def checks(ruleset):
			return [
				check['context']
				for rule in ruleset['rules']
				if rule['type'] == 'required_status_checks'
				for check in rule['parameters']['required_status_checks']
			]

		self.assertEqual(
			[ruleset['name'] for _, ruleset in self.module.rulesets_for('app')],
			['Protect Main', 'Protect Release Tags'],
		)
		own = self.module.ruleset_for('.github')
		other = self.module.ruleset_for('app')
		self.assertEqual(own['name'], 'Protect Main')
		self.assertEqual(other['name'], 'Protect Main')
		self.assertEqual(len(checks(own)), 5)
		self.assertEqual(
			sorted(checks(other)), ['Kiểm tra tiêu đề Pull Request', 'Kiểm tra tên branch']
		)


if __name__ == '__main__':
	unittest.main()
