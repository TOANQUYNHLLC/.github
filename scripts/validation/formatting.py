"""Định dạng từng loại tệp: mã hóa, xuống dòng, thụt lề; danh sách đuôi tệp khớp .editorconfig, .gitattributes
(ADR 0001, 0002)."""

import re
import unicodedata

from markdown import withoutCodeBlocks

from validation.common import ROOT, error, errors, lineNumber, readBytes, readText

# Bắt buộc thụt lề bằng 4 dấu cách: YAML, Markdown (Prettier), F#, Elm, Nim, Zig.
SPACE_SUFFIXES = (
	'.yml',
	'.yaml',
	'.cff',
	'.md',
	'.fs',
	'.fsi',
	'.fsx',
	'.elm',
	'.nim',
	'.nims',
	'.nimble',
	'.zig',
	'.zon',
)
# Formatter chính thức cố định 2 dấu cách: Dart, Elixir, Terraform, Crystal, Gleam, Nix.
TWO_SPACE_SUFFIXES = ('.dart', '.ex', '.exs', '.tf', '.tfvars', '.cr', '.gleam', '.nix')
TWO_SPACE_SECTION = '[*.{dart,ex,exs,tf,tfvars,cr,gleam,nix}]'
# Bắt buộc CRLF theo .editorconfig và .gitattributes.
CRLF_SUFFIXES = (
	'.bat',
	'.cmd',
	'.dsp',
	'.dsw',
	'.ics',
	'.vcs',
	'.vcf',
	'.eml',
	'.mht',
	'.mhtml',
	'.csv',
	'.sln',
	'.csproj',
	'.vbproj',
	'.vcxproj',
	'.vcxproj.filters',
	'.vcproj',
	'.fsproj',
	'.sqlproj',
	'.wixproj',
	'.reg',
	'.inf',
)
# Visual Studio ghi solution và project kèm BOM UTF-8.
UTF8_BOM_SUFFIXES = (
	'.sln',
	'.csproj',
	'.vbproj',
	'.vcxproj',
	'.vcxproj.filters',
	'.vcproj',
	'.fsproj',
	'.sqlproj',
	'.wixproj',
)
# regedit và Windows Setup đọc UTF-16 LE có BOM.
UTF16_SUFFIXES = ('.reg', '.inf')
# Khoảng trắng cuối dòng là dữ liệu: ô CSV, email format=flowed (RFC 3676).
KEEP_TRAILING_SPACE_SUFFIXES = ('.csv', '.eml', '.mht', '.mhtml')


# Tệp nhị phân (khai báo binary trong .gitattributes): không kiểm tra như văn bản.
BINARY_SUFFIXES = (
	'.png',
	'.jpg',
	'.jpeg',
	'.gif',
	'.ico',
	'.pdf',
	'.webp',
	'.woff',
	'.woff2',
	'.zip',
)


# Dòng có nội dung mà thụt lề chứa dấu cách; bỏ dòng tiếp nối chú thích khối (/** … */) do Prettier sinh ra:
# tab rồi " *".
MIXED_INDENT = re.compile(r'^(?!\t* \*)\t* [ \t]*\S', re.MULTILINE)
# Khoảng trắng cuối dòng (trước \r của CRLF nếu có).
TRAILING_SPACE = re.compile(r'[ \t]\r*$', re.MULTILINE)


def checkText(path):
	data = readBytes(path)
	name = path.name
	if name.endswith(UTF16_SUFFIXES):
		if not data.startswith(b'\xff\xfe'):
			error(path, 'phải mã hóa UTF-16 LE có BOM')
			return None
		encoding, label = 'utf-16', 'UTF-16 LE'
	elif name.endswith(UTF8_BOM_SUFFIXES):
		if not data.startswith(b'\xef\xbb\xbf'):
			error(path, 'thiếu BOM UTF-8')
		encoding, label = 'utf-8-sig', 'UTF-8'
	else:
		if data.startswith(b'\xef\xbb\xbf'):
			error(path, 'có BOM UTF-8')
		encoding, label = 'utf-8', 'UTF-8'
	try:
		text = data.decode(encoding)
	except UnicodeDecodeError:
		error(path, f'không phải {label}')
		return None
	if text and not text.endswith('\n'):
		error(path, 'thiếu dòng trống cuối file')
	# Tiếng Việt gõ trên macOS có thể ở dạng tách dấu (NFD): trông giống nhưng khác byte, làm hỏng tìm kiếm.
	# .mailmap cố ý chứa tên dạng NFD để ánh xạ về tên chuẩn.
	if name != '.mailmap' and not unicodedata.is_normalized('NFC', text):
		error(path, 'có chữ Unicode dạng tách dấu (NFD) — chuyển sang dạng dựng sẵn (NFC)')
	if name.endswith(CRLF_SUFFIXES):
		bare = text.replace('\r\n', '')
		if '\n' in bare or '\r' in bare:
			error(path, 'phải xuống dòng bằng CRLF (theo .editorconfig và .gitattributes)')
	elif '\r' in text:
		error(path, 'phải xuống dòng bằng LF (theo .editorconfig và .gitattributes)')
	if name.endswith(KEEP_TRAILING_SPACE_SUFFIXES):
		return text
	match = TRAILING_SPACE.search(text)
	if match:
		error(path, f'dòng {lineNumber(text, match.start())}: có khoảng trắng cuối dòng')
	return text


def editorconfigSuffixes(editorconfig, setting):
	"""Đuôi file của mọi mục .editorconfig dạng [*.x] hoặc [*.{x,y}] có chứa `setting`."""
	suffixes = set()
	for header, body in re.findall(
		r'^\[\*\.\{?([^\]}]+)\}?\]\n((?:[^\[].*\n?)*)', editorconfig, re.MULTILINE
	):
		if re.search(rf'^{re.escape(setting)}$', body, re.MULTILINE):
			suffixes.update(f'.{name}' for name in header.split(','))
	return suffixes


def checkSuffixLists():
	"""Danh sách đuôi file trong validate.py, .editorconfig và .gitattributes phải khớp nhau."""
	editorconfig = readText(ROOT / '.editorconfig')
	attributes = readText(ROOT / '.gitattributes')
	for setting, expected in (
		('end_of_line = crlf', CRLF_SUFFIXES),
		('charset = utf-8-bom', UTF8_BOM_SUFFIXES),
		('charset = utf-16le', UTF16_SUFFIXES),
		('trim_trailing_whitespace = false', KEEP_TRAILING_SPACE_SUFFIXES),
		('indent_size = 2', TWO_SPACE_SUFFIXES),
	):
		found = editorconfigSuffixes(editorconfig, setting)
		for suffix in sorted(set(expected) ^ found):
			where = 'thiếu' if suffix in expected else 'thừa'
			errors.append(
				f'.editorconfig: {where} {suffix} trong mục "{setting}" so với validate.py'
			)
	spaces = editorconfigSuffixes(editorconfig, 'indent_style = space') - set(TWO_SPACE_SUFFIXES)
	for suffix in sorted(set(SPACE_SUFFIXES) ^ spaces):
		where = 'thiếu' if suffix in SPACE_SUFFIXES else 'thừa'
		errors.append(f'.editorconfig: {where} {suffix} trong mục dấu cách so với validate.py')
	crlf = set(re.findall(r'^\*(\.\S+) .*\beol=crlf\b', attributes, re.MULTILINE))
	for suffix in sorted(set(CRLF_SUFFIXES) ^ crlf):
		where = 'thiếu' if suffix in CRLF_SUFFIXES else 'thừa'
		errors.append(f'.gitattributes: {where} {suffix} text eol=crlf so với validate.py')
	utf16 = set(
		re.findall(r'^\*(\.\S+) .*\bworking-tree-encoding=UTF-16LE-BOM\b', attributes, re.MULTILINE)
	)
	for suffix in sorted(set(UTF16_SUFFIXES) ^ utf16):
		where = 'thiếu' if suffix in UTF16_SUFFIXES else 'thừa'
		errors.append(
			f'.gitattributes: {where} working-tree-encoding cho {suffix} so với validate.py'
		)
	binary = set(re.findall(r'^\*(\.\S+) binary$', attributes, re.MULTILINE))
	for suffix in sorted(set(BINARY_SUFFIXES) ^ binary):
		where = 'thiếu' if suffix in BINARY_SUFFIXES else 'thừa'
		errors.append(f'.gitattributes: {where} {suffix} binary so với validate.py')


def checkSpaceOnly(path, text):
	"""Ngôn ngữ bắt buộc dấu cách (4 hoặc 2 mỗi cấp theo formatter chính thức): không dùng tab."""
	if '\t' not in text:
		return
	width = 2 if path.suffix in TWO_SPACE_SUFFIXES else 4
	if path.suffix == '.md':
		text = withoutCodeBlocks(text)
	for number, line in enumerate(text.split('\n'), start=1):
		if re.match(r'^ *\t', line):
			error(
				path,
				f'dòng {number}: {path.suffix} phải thụt lề bằng {width} dấu cách, không dùng tab',
			)
			return


def checkTabOnly(path, text):
	"""Mọi tệp mặc định dùng tab (theo .editorconfig): thụt lề chỉ bằng tab, không trộn dấu cách."""
	match = MIXED_INDENT.search(text)
	if match:
		error(
			path,
			f'dòng {lineNumber(text, match.start())}: thụt lề phải dùng tab theo .editorconfig',
		)
