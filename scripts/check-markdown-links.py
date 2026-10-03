"""Kiểm tra liên kết nội bộ trong tài liệu Markdown: tệp đích phải tồn tại, mục #… phải có tiêu đề tương ứng.

Chạy: python3 scripts/check-markdown-links.py   (kiểm tra mọi tệp .md của thư mục hiện tại)
Workflow mẫu docs-check.yml của repository khác gọi script này; validate.py dùng chung hàm findBrokenLinks().
"""

import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

# Repository chứa script; workflow mẫu checkout nó vào .org/ bên trong repository đang được kiểm tra.
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
CODE_FENCE = re.compile(r'```.*?```', re.DOTALL)
LINK = re.compile(r'\]\(([^)\s#]*)(?:#([^)\s]*))?\)')


def headingAnchors(path):
	"""Anchor GitHub tạo cho các tiêu đề Markdown: chữ thường, bỏ ký tự không phải chữ, số, khoảng trắng,
	gạch ngang; khoảng trắng thành "-"; tiêu đề trùng thêm hậu tố -1, -2…."""
	text = CODE_FENCE.sub('', path.read_text(encoding='utf-8'))
	seen, anchors = {}, set()
	for match in re.finditer(r'^#{1,6} (.+)$', text, re.MULTILINE):
		slug = re.sub(r'[^\w\- ]', '', re.sub(r'`([^`]*)`', r'\1', match.group(1)).strip().lower())
		slug = slug.replace(' ', '-')
		count = seen.get(slug, 0)
		seen[slug] = count + 1
		anchors.add(slug if count == 0 else f'{slug}-{count}')
	return anchors


def findBrokenLinks(path, text):
	"""Thông báo cho từng liên kết nội bộ hỏng trong nội dung Markdown của path."""
	messages = []
	for match in LINK.finditer(CODE_FENCE.sub('', text)):
		target, fragment = match.group(1), match.group(2)
		if re.match(r'[a-z]+:', target) or (not target and fragment is None):
			continue
		# Liên kết có thể mã hóa phần trăm (khoảng trắng %20, chữ có dấu trong tên tệp hay mục #…).
		target = urllib.parse.unquote(target)
		fragment = urllib.parse.unquote(fragment) if fragment else fragment
		destination = path.parent / target if target else path
		if not destination.exists():
			messages.append(f'liên kết hỏng: {target}')
		elif (
			fragment and destination.suffix == '.md' and fragment not in headingAnchors(destination)
		):
			messages.append(f'liên kết hỏng: {target}#{fragment} — không có tiêu đề tương ứng')
	return messages


def markdownFiles():
	"""Tệp .md git quản lý (bỏ qua .gitignore); ngoài git thì quét cả thư mục, trừ node_modules.
	Bỏ qua tài liệu của repository chứa script khi kiểm tra repository khác."""
	result = subprocess.run(
		['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '*.md'],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode == 0:
		# -z: tên tệp nguyên văn (tên tiếng Việt không bị đặt trong dấu nháy); bỏ tệp đã xóa trên đĩa.
		paths = [Path(name) for name in result.stdout.split('\0') if name and Path(name).is_file()]
	else:
		paths = [path for path in Path('.').rglob('*.md') if 'node_modules' not in path.parts]
	if Path.cwd().resolve() == SCRIPT_ROOT:
		return paths
	return [path for path in paths if not path.resolve().is_relative_to(SCRIPT_ROOT)]


def main():
	broken = 0
	for path in sorted(markdownFiles()):
		for message in findBrokenLinks(path, path.read_text(encoding='utf-8')):
			broken += 1
			print(f'❌ {path}: {message}')
	print(f'{"✅ Không có liên kết hỏng" if not broken else f"❌ {broken} liên kết hỏng"}.')
	return 1 if broken else 0


if __name__ == '__main__':
	sys.exit(main())
