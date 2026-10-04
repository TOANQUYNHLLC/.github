"""Test tự động cho scripts/check-markdown-links.py.

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import loadScript
except ModuleNotFoundError:
	from scripts.testsupport import loadScript


class MarkdownLinksTest(unittest.TestCase):
	def testMainSharesAnchorsAndRefreshesNextRun(self):
		module = loadScript('check-markdown-links')
		with tempfile.TemporaryDirectory() as folder:
			root = Path(folder)
			target = root / 'target.md'
			target.write_text('## A\n', encoding='utf-8')
			sources = [root / 'first.md', root / 'second.md']
			for path in sources:
				path.write_text('[x](target.md#a)\n', encoding='utf-8')
			with (
				mock.patch.object(module, 'markdownFiles', return_value=sources),
				mock.patch.object(module, 'headingAnchors', wraps=module.headingAnchors) as anchors,
				contextlib.redirect_stdout(io.StringIO()),
			):
				self.assertEqual(module.main(), 0)
				self.assertEqual(anchors.call_count, 1)
				target.write_text('## B\n', encoding='utf-8')
				self.assertEqual(module.main(), 1)
				self.assertEqual(anchors.call_count, 2)

	def testHeadingSuffixCollisionsMatchGithub(self):
		# Kết quả từ API markdown của GitHub: hậu tố sinh tự động cũng có thể trùng tiêu đề tiếp theo.
		module = loadScript('check-markdown-links')
		with tempfile.TemporaryDirectory() as folder:
			path = Path(folder) / 'README.md'
			path.write_text('## A\n## A\n## A-1\n## A\n## A-1-1\n', encoding='utf-8')
			self.assertEqual(module.headingAnchors(path), {'a', 'a-1', 'a-1-1', 'a-2', 'a-1-1-1'})
			self.assertEqual(module.findBrokenLinks(path, '[x](#a-1-1-1)'), [])

	def testAnchorsAreReusedOnlyWithinOneRun(self):
		module = loadScript('check-markdown-links')
		with tempfile.TemporaryDirectory() as folder:
			path = Path(folder) / 'README.md'
			path.write_text('## A\n', encoding='utf-8')
			with mock.patch.object(
				module, 'headingAnchors', wraps=module.headingAnchors
			) as anchors:
				self.assertEqual(module.findBrokenLinks(path, '[x](#a) [y](./README.md#a)'), [])
				self.assertEqual(anchors.call_count, 1)
				path.write_text('## B\n', encoding='utf-8')
				self.assertTrue(module.findBrokenLinks(path, '[x](#a)'))
				self.assertEqual(anchors.call_count, 2)

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

	def testHeadingSlugsMatchGithub(self):
		# Giá trị mong đợi lấy từ anchor GitHub tạo thật (gh api markdown, mode=markdown): GitHub giữ U+FE0F của
		# emoji như 🛠️ và U+200D của emoji ghép như 🧑‍💼; tiêu đề có liên kết chỉ lấy chữ hiển thị.
		module = loadScript('check-markdown-links')
		for title, expected in (
			('🚀 PHÁT HÀNH', '-phát-hành'),
			('🛠️ PHÁT TRIỂN CỤC BỘ', '\ufe0f-phát-triển-cục-bộ'),
			('🧑\u200d💼 NGƯỜI QUẢN TRỊ', '\u200d-người-quản-trị'),
			('[CHƯA PHÁT HÀNH](https://github.com/x/y/compare/v1...HEAD)', 'chưa-phát-hành'),
			(
				'[v2026.10.Stable](https://github.com/x/y/releases/tag/v2026.10.Stable) — 2026-10-03',
				'v202610stable--2026-10-03',
			),
			('0012. PHÁT HÀNH TỪ `CHANGELOG.MD`', '0012-phát-hành-từ-changelogmd'),
		):
			self.assertEqual(module.headingSlug(title), expected, title)
		with tempfile.TemporaryDirectory() as folder:
			path = Path(folder) / 'README.md'
			path.write_text('## 🛠️ PHÁT TRIỂN CỤC BỘ\n', encoding='utf-8')
			self.assertEqual(module.findBrokenLinks(path, '[x](#\ufe0f-phát-triển-cục-bộ)'), [])


if __name__ == '__main__':
	unittest.main()
