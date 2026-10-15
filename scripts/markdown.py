"""Bỏ nội dung mã trong Markdown để các kiểm tra liên kết, tiêu đề, thụt lề và parser nội dung phát hành
dùng cùng cách đọc khối mã."""

import re

FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})([^\n]*)$')
CODE_DELIMITER = re.compile(r'`+|\n[ \t]*\n')


def withoutCodeBlocks(text):
	"""Giữ số dòng; hàng rào mở/đóng thụt tối đa 3 dấu cách, không nhận tab hoặc mã thụt lề.
	Khối mã chỉ đóng bằng cùng dấu và ít nhất bằng số dấu mở; phía sau chỉ nhận dấu cách ASCII hoặc tab.
	Khối chưa đóng kéo dài đến cuối tệp. Dấu backtick trong phần ngôn ngữ không mở khối backtick."""
	lines = text.split('\n')
	fence = ''
	for index, line in enumerate(lines):
		# CR trong CRLF là kết thúc dòng, không phải phần chữ theo sau hàng rào.
		match = FENCE.fullmatch(line.removesuffix('\r'))
		if fence:
			lines[index] = ''
			if (
				match
				and match[1][0] == fence[0]
				and len(match[1]) >= len(fence)
				and not match[2].strip(' \t')
			):
				fence = ''
		elif match and (match[1][0] == '~' or '`' not in match[2]):
			fence = match[1]
			lines[index] = ''
	return '\n'.join(lines)


def withoutCode(text):
	"""Bỏ mã nội tuyến và giữ số dòng; ghép dấu backtick bằng chỉ mục để không quét lại phần còn lại.
	Backslash chỉ escape dấu mở ngoài mã; dấu đóng trong mã không bị escape. Không ghép qua dòng trống."""
	text = withoutCodeBlocks(text)
	if '`' not in text:
		return text
	delimiters = list(CODE_DELIMITER.finditer(text))
	nextRuns = {}
	closingIndices = [None] * len(delimiters)
	openingOffsets = [0] * len(delimiters)
	for index in range(len(delimiters) - 1, -1, -1):
		delimiter = delimiters[index]
		if text[delimiter.start()] == '\n':
			nextRuns.clear()
			continue
		start = delimiter.start()
		while start > 0 and text[start - 1] == '\\':
			start -= 1
		offset = (delimiter.start() - start) % 2
		openingOffsets[index] = offset
		size = delimiter.end() - delimiter.start()
		closingIndices[index] = nextRuns.get(size - offset)
		nextRuns[size] = index
	parts, cursor, index = [], 0, 0
	while index < len(delimiters):
		closing = closingIndices[index]
		if closing is None:
			index += 1
			continue
		start = delimiters[index].start() + openingOffsets[index]
		end = delimiters[closing].end()
		parts.extend((text[cursor:start], '\n' * text.count('\n', start, end)))
		cursor, index = end, closing + 1
	parts.append(text[cursor:])
	return ''.join(parts)
