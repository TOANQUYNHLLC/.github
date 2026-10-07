"""Kiểm tra liên kết nội bộ trong tài liệu Markdown: tệp đích phải tồn tại, mục #… phải có tiêu đề tương ứng.

Chạy: python3 scripts/check-markdown-links.py   (kiểm tra mọi tệp .md của thư mục hiện tại)
Workflow mẫu docs-check.yml của repository khác gọi script này; validate.py (scripts/validation/docs.py) dùng chung hàm findBrokenLinks().
"""

import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

from markdown import withoutCode, withoutCodeBlocks

# Repository chứa script; workflow mẫu checkout nó vào .org/ bên trong repository đang được kiểm tra.
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'\]\(([^)\s#]*)(?:#([^)\s]*))?\)')


def headingSlug(title):
	"""Anchor GitHub tạo cho một tiêu đề: bỏ định dạng code, liên kết chỉ giữ chữ hiển thị; chữ thường; bỏ ký tự
	không phải chữ, số, khoảng trắng, gạch ngang — nhưng giữ U+200D (nối emoji, như 🧑‍💼) và U+FE0F (biến thể
	emoji, như 🛠️) như GitHub; khoảng trắng thành "-"."""
	title = re.sub(r'`([^`]*)`', r'\1', title)
	title = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', title)
	return re.sub(r'[^\w\- \u200d\ufe0f]', '', title.strip().lower()).replace(' ', '-')


def headingAnchors(path):
	"""Anchor của mọi tiêu đề Markdown trong tệp; tiêu đề trùng thêm hậu tố -1, -2…."""
	text = withoutCodeBlocks(path.read_text(encoding='utf-8'))
	seen, anchors = {}, set()
	for match in re.finditer(r'^#{1,6} (.+)$', text, re.MULTILINE):
		original = slug = headingSlug(match.group(1))
		# Hậu tố sinh cho tiêu đề trước cũng giữ chỗ: A, A, A-1 → a, a-1, a-1-1.
		while slug in seen:
			seen[original] += 1
			slug = f'{original}-{seen[original]}'
		seen[slug] = 0
		anchors.add(slug)
	return anchors


def findBrokenLinks(path, text, anchorsCache=None):
	"""Thông báo cho từng liên kết nội bộ hỏng trong nội dung Markdown của path. anchorsCache chỉ dùng trong
	một lượt kiểm tra; lượt mới tạo bộ đệm mới để nhận thay đổi trên đĩa."""
	if anchorsCache is None:
		anchorsCache = {}
	messages = []
	for match in LINK.finditer(withoutCode(text)):
		target, fragment = match.group(1), match.group(2)
		if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:|^//', target) or (not target and fragment is None):
			continue
		# Liên kết có thể mã hóa phần trăm (khoảng trắng %20, chữ có dấu trong tên tệp hay mục #…).
		target = urllib.parse.unquote(target)
		fragment = urllib.parse.unquote(fragment) if fragment else fragment
		destination = path.parent / target if target else path
		if not destination.exists():
			messages.append(f'liên kết hỏng: {target}')
		elif fragment and destination.suffix == '.md':
			key = destination.resolve()
			if key not in anchorsCache:
				try:
					anchorsCache[key] = headingAnchors(destination)
				except (OSError, UnicodeError) as exc:
					anchorsCache[key] = exc
			if isinstance(anchorsCache[key], Exception):
				messages.append(f'không đọc được Markdown {destination}: {anchorsCache[key]}')
				continue
			if fragment not in anchorsCache[key]:
				messages.append(f'liên kết hỏng: {target}#{fragment} — không có tiêu đề tương ứng')
	return messages


def markdownFiles():
	"""Tệp .md git quản lý (bỏ qua .gitignore); ngoài git thì quét cả thư mục, trừ node_modules.
	Bỏ qua tài liệu của repository chứa script khi kiểm tra repository khác."""
	result = subprocess.run(
		['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '*.md'],
		capture_output=True,
		check=False,
	)
	if result.returncode == 0:
		# -z: tên tệp nguyên văn (tên tiếng Việt không bị đặt trong dấu nháy); bỏ tệp đã xóa trên đĩa.
		paths = [
			Path(name)
			for name in result.stdout.decode('utf-8').split('\0')
			if name and Path(name).is_file()
		]
	else:
		paths = [path for path in Path('.').rglob('*.md') if 'node_modules' not in path.parts]
	if Path.cwd().resolve() == SCRIPT_ROOT:
		return paths
	return [path for path in paths if not path.resolve().is_relative_to(SCRIPT_ROOT)]


def main():
	broken = 0
	anchorsCache = {}
	for path in sorted(markdownFiles()):
		try:
			messages = findBrokenLinks(path, path.read_text(encoding='utf-8'), anchorsCache)
		except (OSError, UnicodeError) as exc:
			messages = [f'không đọc được Markdown: {exc}']
		for message in messages:
			broken += 1
			print(f'❌ {path}: {message}')
	print(f'{"✅ Không có liên kết hỏng" if not broken else f"❌ {broken} lỗi"}.')
	return 1 if broken else 0


if __name__ == '__main__':
	sys.exit(main())
