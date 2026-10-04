"""Bỏ nội dung mã trong Markdown để các kiểm tra liên kết, tiêu đề và thụt lề dùng cùng cách đọc."""

import re

FENCE = re.compile(r'^[ \t]*(`{3,}|~{3,})([^\n]*)$')
CODE_SPAN = re.compile(r'(?<!`)(`+)(?!`)(?:(?!\n[ \t]*\n).)*?(?<!`)\1(?!`)', re.DOTALL)


def withoutCodeBlocks(text):
	"""Giữ số dòng; khối mã chỉ đóng bằng cùng dấu và ít nhất bằng số dấu mở, không kèm chữ.
	Khối chưa đóng kéo dài đến cuối tệp. Dấu backtick trong phần ngôn ngữ không mở khối backtick."""
	lines = text.split('\n')
	fence = ''
	for index, line in enumerate(lines):
		match = FENCE.fullmatch(line)
		if fence:
			lines[index] = ''
			if (
				match
				and match[1][0] == fence[0]
				and len(match[1]) >= len(fence)
				and not match[2].strip()
			):
				fence = ''
		elif match and (match[1][0] == '~' or '`' not in match[2]):
			fence = match[1]
			lines[index] = ''
	return '\n'.join(lines)


def withoutCode(text):
	"""Bỏ thêm mã nội tuyến có dấu backtick đóng dài đúng bằng dấu mở; giữ số dòng."""
	return CODE_SPAN.sub(lambda match: '\n' * match[0].count('\n'), withoutCodeBlocks(text))
