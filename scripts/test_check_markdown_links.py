"""Test tự động cho scripts/check-markdown-links.py.

Chạy: python3 -m unittest discover -s scripts -p 'test_*.py'   (hoặc: make test)
"""

import contextlib
import subprocess
import tempfile
import unittest
from pathlib import Path

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript


class MarkdownLinksTest(unittest.TestCase):
	def testPercentEncodedLinks(self):
		# Tên tệp có khoảng trắng (%20) và mục có chữ có dấu (%C3%AA…) vẫn tìm đúng tệp, đúng tiêu đề.
		module = loadScript('check-markdown-links')
		with tempfile.TemporaryDirectory() as folder:
			target = Path(folder) / 'ghi chú.md'
			target.write_text('# GHI CHÚ\n\n## Tiêu đề\n', encoding='utf-8')
			source = Path(folder) / 'README.md'
			good = '[a](ghi%20ch%C3%BA.md#ti%C3%AAu-%C4%91%E1%BB%81) [b](ghi%20chú.md)'
			self.assertEqual(module.findBrokenLinks(source, good), [])
			bad = '[a](ghi%20ch%C3%BA.md#kh%C3%B4ng-c%C3%B3) [b](kh%C3%B4ng%20c%C3%B3.md)'
			self.assertEqual(
				module.findBrokenLinks(source, bad),
				[
					'liên kết hỏng: ghi chú.md#không-có — không có tiêu đề tương ứng',
					'liên kết hỏng: không có.md',
				],
			)

	def testFindsFilesWithVietnameseNames(self):
		# Tên tệp tiếng Việt, có khoảng trắng được liệt kê nguyên văn; tệp đã xóa trên đĩa bị bỏ qua.
		module = loadScript('check-markdown-links')
		with tempfile.TemporaryDirectory() as folder:
			root = Path(folder)
			(root / 'ghi chú.md').write_text('# GHI CHÚ\n', encoding='utf-8')
			(root / 'xoá.md').write_text('# XOÁ\n', encoding='utf-8')
			subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
			subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
			(root / 'xoá.md').unlink()
			with contextlib.chdir(root):
				self.assertEqual(module.markdownFiles(), [Path('ghi chú.md')])


if __name__ == '__main__':
	unittest.main()
