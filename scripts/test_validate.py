"""Test tự động cho scripts/validate.py và scripts/release-notes.py.

Chạy: python3 -m unittest discover -s scripts -p 'test_*.py'   (hoặc: make test)
Mỗi test chép repository sang thư mục tạm, cố ý làm hỏng một điểm rồi khẳng định
validate.py phát hiện đúng lỗi — để việc sửa script không vô tình làm mất một luật.
"""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_release_notes():
	spec = importlib.util.spec_from_file_location('release_notes', ROOT / 'scripts' / 'release-notes.py')
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


class ValidateTest(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.repo = Path(self.tmp.name)
		names = subprocess.run(
			['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
			cwd=ROOT, capture_output=True, check=True,
		).stdout.decode('utf-8').split('\0')
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
			[sys.executable, 'scripts/validate.py'], cwd=self.repo, capture_output=True, text=True, check=False,
		)
		return result.returncode, result.stdout

	def edit(self, name, old, new):
		path = self.repo / name
		text = path.read_text(encoding='utf-8')
		self.assertIn(old, text, f'{name} không còn chứa đoạn cần sửa trong test')
		path.write_text(text.replace(old, new, 1), encoding='utf-8')

	def assert_fails(self, message):
		code, output = self.run_validate()
		self.assertEqual(code, 1, output)
		self.assertIn(message, output)

	def test_repository_hien_tai_hop_le(self):
		code, output = self.run_validate()
		self.assertEqual(code, 0, output)

	def test_lien_ket_hong(self):
		self.edit('README.md', '(SECURITY.md)', '(KHONG_TON_TAI.md)')
		self.assert_fails('liên kết hỏng: KHONG_TON_TAI.md')

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

	def test_security_txt_het_han(self):
		self.edit('.well-known/security.txt', 'Expires: 2027', 'Expires: 2020')
		self.assert_fails('Expires đã hết hạn')

	def test_thut_le_python_phai_dung_tab(self):
		path = self.repo / 'scripts' / 'validate.py'
		path.write_text(path.read_text(encoding='utf-8') + '\nif True:\n    pass\n', encoding='utf-8')
		self.assert_fails('thụt lề phải dùng tab')

	def test_yaml_khong_duoc_thut_le_bang_tab(self):
		self.edit('labels.yml', '  color: "d73a4a"', '\tcolor: "d73a4a"')
		self.assert_fails('YAML không được thụt lề bằng tab')

	def test_khoang_trang_cuoi_dong(self):
		self.edit('CONTRIBUTING.md', '# 🤝 HƯỚNG DẪN ĐÓNG GÓP', '# 🤝 HƯỚNG DẪN ĐÓNG GÓP ')
		self.assert_fails('có khoảng trắng cuối dòng')

	def test_xuong_dong_crlf(self):
		path = self.repo / 'SUPPORT.md'
		path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
		self.assert_fails('phải xuống dòng bằng LF')

	def test_nhan_trong_bieu_mau_phai_co_trong_labels(self):
		self.edit('ISSUE_TEMPLATE/question.yml', '    - question', '    - hoi-dap')
		self.assert_fails('chưa có trong labels.yml')

	def test_action_phai_ghim_sha(self):
		self.edit('.github/workflows/validate.yml', 'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1', 'actions/checkout@v4')
		self.assert_fails('phải ghim theo commit SHA đầy đủ')

	def test_workflow_mau_thieu_properties(self):
		(self.repo / 'workflow-templates' / 'node-ci.properties.json').unlink()
		self.assert_fails('thiếu tệp node-ci.properties.json')

	def test_thieu_tep_bat_buoc(self):
		(self.repo / 'CODE_OF_CONDUCT.md').unlink()
		for name in ('README.md', 'CONTRIBUTING.md'):
			path = self.repo / name
			path.write_text(path.read_text(encoding='utf-8').replace('(CODE_OF_CONDUCT.md)', '(SUPPORT.md)'), encoding='utf-8')
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


if __name__ == '__main__':
	unittest.main()
