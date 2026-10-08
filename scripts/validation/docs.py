"""Tài liệu: liên kết, tiêu đề, huy hiệu, email, security.txt, CHANGELOG.md, bảng ADR; tài liệu khớp code
(ADR 0013)."""

import builtins
import re
import urllib.parse
from datetime import UTC, datetime

from markdown import withoutCodeBlocks

from validation.common import (
	ROOT,
	anchorsCache,
	conventions,
	error,
	errors,
	markdownLinks,
	readText,
	trackedFiles,
)
from validation.workflows import repositoryWorkflows

# Email liên hệ chung của công ty — mọi tài liệu phải dùng đúng địa chỉ này.
COMPANY_EMAIL = 'toanquynhvn@gmail.com'
# Tag phát hành: Stable.vYYYY.MM.DDXXXX, Beta.vYYYY.MM.DDXXXX (ADR 0012) và tag vYYYY.MM.Stable đã phát hành.
RELEASE_TAG = re.compile(
	r'(Stable|Beta)\.v[0-9]{4}\.(0[1-9]|1[0-2])\.[0-9]{6}|v[0-9]{4}\.(0[1-9]|1[0-2])\.Stable'
)
EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}')


# Mục bắt buộc của mỗi ADR, theo thứ tự (docs/adr/template.md).
ADR_SECTIONS = ('BỐI CẢNH', 'QUYẾT ĐỊNH', 'PHƯƠNG ÁN ĐÃ CÂN NHẮC', 'HỆ QUẢ')
# Trạng thái của ADR: ADR chỉ mô tả quyết định hiện hành, đổi quyết định thì cập nhật chính ADR đó.
ADR_STATUSES = ('Đề xuất', 'Chấp nhận')
# Đường dẫn trong tài liệu bắt đầu bằng các thư mục này phải có thật trong repository.
DOC_PATH = re.compile(
	r'`((?:scripts|shell|docs|rulesets|workflow-templates|repository-templates|\.devcontainer|\.github/workflows)/'
	r'[^`\s*<>…]*)`'
)
# security.txt: báo trước khi Expires hết hạn để kịp gia hạn và đăng lại lên website.
EXPIRY_NOTICE_DAYS = 30


def checkLinks(path, text):
	for message in markdownLinks.findBrokenLinks(path, text, anchorsCache, ROOT):
		error(path, message)


def checkAbsoluteLinks(path, text, reason='biểu mẫu dùng ở mọi repository'):
	"""Nội dung hiển thị ngoài repository (biểu mẫu ở repository khác, nội dung GitHub Release): liên kết tương
	đối sẽ trỏ sai chỗ."""
	for match in re.finditer(r'\]\(([^)\s]+)\)', text):
		if not re.match(r'(https?|mailto):', match.group(1)):
			error(path, f'liên kết "{match.group(1)}" phải là URL tuyệt đối ({reason})')


def checkSecurityMailto(path, text):
	link = re.search(r'mailto:[^?)\s]+\?([^)\s]+)', text)
	details = re.search(r'<details>.*?<br>\s*\n(.*?)\n\s*</details>', text, re.DOTALL)
	if not link or not details:
		error(path, 'thiếu liên kết soạn email hoặc mẫu nội dung email')
		return
	query = urllib.parse.parse_qs(link.group(1))
	lines = [line.rstrip() for line in details.group(1).strip().split('\n')]
	subject = re.match(r'\*\*Tiêu đề:\*\*\s*(.+)', lines[0])
	template = '\n'.join(re.sub(r'\*\*', '', line) for line in lines[1:]).strip()
	if not subject or query.get('subject', [''])[0] != subject.group(1):
		error(path, 'tiêu đề trong liên kết email khác mẫu')
	if query.get('body', [''])[0].replace('\r\n', '\n').strip() != template:
		error(path, 'nội dung liên kết email khác mẫu "Xem Mẫu Nội Dung Email"')


def checkDocsMatchCode():
	"""Tài liệu khớp code: lệnh make, đường dẫn, hàm được nhắc tới phải có thật; README.md liệt kê đủ lệnh make,
	script và workflow của repository."""
	makefile = ROOT / 'Makefile'
	targets = (
		set(re.findall(r'^([a-z-]+):.*## ', readText(makefile), re.MULTILINE))
		if makefile.exists()
		else set()
	)
	scripts = sorted(
		path
		for path in (ROOT / 'scripts').rglob('*.py')
		if not path.name.startswith('test_') and '__pycache__' not in path.parts
	)
	functions = {
		name
		for path in scripts
		for name in re.findall(r'^\s*def (\w+)\(', readText(path), re.MULTILINE)
	}
	for path in (file for file in trackedFiles() if file.suffix == '.md'):
		text = readText(path)
		for target in sorted(set(re.findall(r'`make ([a-z][a-z-]*)', text))):
			if targets and target not in targets:
				error(path, f'nhắc "make {target}" nhưng Makefile không có lệnh này')
		for reference in sorted(set(DOC_PATH.findall(text))):
			# Tên branch ví dụ (docs/update_readme) trông như đường dẫn.
			if '_' in reference and conventions.BRANCH_PATTERN.match(reference):
				continue
			if not (ROOT / reference.rstrip('/')).exists():
				error(path, f'nhắc "{reference}" nhưng tệp, thư mục này không có')
		for name in sorted(set(re.findall(r'`([a-z][A-Za-z0-9]*)\(\)`', text))):
			if name not in functions and not hasattr(builtins, name):
				error(path, f'nhắc hàm "{name}()" nhưng không script nào trong scripts/ định nghĩa')
	readmePath = ROOT / 'README.md'
	if not readmePath.exists():
		return
	readme = readText(readmePath)
	# make help là lệnh mặc định — README ghi dạng `make`.
	for target in sorted(targets - {'help'}):
		if f'`make {target}' not in readme:
			error(readmePath, f'bảng lệnh thiếu "make {target}" (có trong Makefile)')
	# Script shell trong shell/ (make sync…) cũng phải có trong mục cấu trúc.
	for path in [*scripts, *(file for file in trackedFiles() if file.parent == ROOT / 'shell')]:
		relative = path.relative_to(ROOT).as_posix()
		folder = path.parent.relative_to(ROOT).as_posix() + '/'
		if f'`{relative}`' not in readme and (folder == 'scripts/' or f'`{folder}`' not in readme):
			error(readmePath, f'mục cấu trúc thiếu {relative}')
	for workflow in repositoryWorkflows():
		if f'`.github/workflows/{workflow.name}`' not in readme:
			error(readmePath, f'mục cấu trúc thiếu .github/workflows/{workflow.name}')


def checkAdrIndex():
	"""Bảng trong docs/adr/README.md phải liệt kê mọi ADR, cùng ngày và cùng trạng thái với từng tệp. Mỗi chủ đề
	một ADR mô tả quyết định hiện hành nên trạng thái chỉ là Đề xuất hoặc Chấp nhận."""
	folder = ROOT / 'docs' / 'adr'
	indexPath = folder / 'README.md'
	if not indexPath.exists():
		return
	rows = {
		number: (status.strip(), date.strip())
		for number, status, date in re.findall(
			r'^\| \[(\d{4})\]\([^)]+\) +\|[^|]+\|([^|]+)\|([^|]+)\|$',
			readText(indexPath),
			re.MULTILINE,
		)
	}
	for path in sorted(folder.glob('[0-9][0-9][0-9][0-9]-*.md')):
		number = path.name[:4]
		text = readText(path)
		status = re.search(r'^- \*\*Trạng thái:\*\* (.+)$', text, re.MULTILINE)
		date = re.search(r'^- \*\*Ngày:\*\* (.+)$', text, re.MULTILINE)
		if not status or not date:
			error(path, 'thiếu dòng "Trạng thái" hoặc "Ngày"')
			continue
		headings = re.findall(r'^## \S+ (.+)$', text, re.MULTILINE)
		if [heading for heading in headings if heading in ADR_SECTIONS] != list(ADR_SECTIONS):
			error(path, f'ADR phải có đủ các mục theo thứ tự: {", ".join(ADR_SECTIONS)}')
		if number not in rows:
			error(indexPath, f'bảng thiếu ADR {number}')
			continue
		if status.group(1).strip() not in ADR_STATUSES:
			error(path, f'trạng thái phải là {" hoặc ".join(ADR_STATUSES)}')
		rowStatus, rowDate = rows[number]
		if rowDate != date.group(1).strip():
			error(indexPath, f'ADR {number}: ngày "{rowDate}" khác tệp ADR ({date.group(1)})')
		if rowStatus != status.group(1).strip():
			error(
				indexPath,
				f'ADR {number}: trạng thái "{rowStatus}" khác tệp ADR ({status.group(1)})',
			)


def titleCase(text):
	"""Chữ tiếng Anh (ASCII), mỗi từ bắt đầu bằng chữ hoa hoặc số: Last Commit, Code Style: Prettier."""
	return text.isascii() and all(
		word[0].isupper() or word[0].isdigit() for word in re.findall(r'[^\s:/()-]+', text)
	)


def badgeLabel(url):
	"""Nhãn của huy hiệu shields.io: tham số label=, hoặc phần đầu của /badge/<nhãn>-<nội dung>-<màu>
	("_" là dấu cách, "--" là dấu gạch ngang); None khi không đặt nhãn (shields tự đặt chữ thường)."""
	parsed = urllib.parse.urlparse(url)
	label = urllib.parse.parse_qs(parsed.query).get('label')
	if label:
		return label[0]
	match = re.match(r'/badge/((?:[^-]|--)+)-', parsed.path)
	if not match:
		return None
	return urllib.parse.unquote(match.group(1)).replace('--', '-').replace('_', ' ')


def checkBadges(path, text):
	"""Chữ trên huy hiệu viết tiếng Anh, hoa đầu mỗi từ (Last Commit, Code Style): chữ thay thế và nhãn."""
	for alt, url in re.findall(r'\[!\[([^\]]*)\]\(([^)\s]+)\)\]', text):
		if not titleCase(alt):
			error(path, f'huy hiệu "{alt}": chữ thay thế phải tiếng Anh, hoa đầu mỗi từ')
		parsed = urllib.parse.urlparse(url)
		if parsed.netloc == 'img.shields.io' and not parsed.path.startswith('/endpoint'):
			label = badgeLabel(url)
			if label is None:
				error(
					path,
					f'huy hiệu "{alt}": đặt label= tiếng Anh, hoa đầu mỗi từ (shields tự đặt chữ thường)',
				)
			elif not titleCase(label):
				error(path, f'huy hiệu "{alt}": nhãn "{label}" phải tiếng Anh, hoa đầu mỗi từ')
		elif parsed.path.endswith('/badge.svg'):
			error(
				path,
				f'huy hiệu "{alt}": huy hiệu của GitHub lấy chữ theo tên workflow — dùng huy hiệu shields.io có label=',
			)


def checkHeadings(path, text):
	"""Tiêu đề ATX, kể cả thụt lề từ 0 đến 3 dấu cách và phân cách bằng tab, phải viết hoa."""
	for number, line in enumerate(withoutCodeBlocks(text).split('\n'), start=1):
		heading = re.match(r' {0,3}#{1,6}(?:[ \t]+|$)(.*)', line)
		title = re.sub(r'`[^`]*`|\[[^\]]*\]\([^)]*\)', '', heading.group(1)) if heading else ''
		if heading and title != title.upper():
			error(path, f'dòng {number}: tiêu đề phải viết hoa — "{heading.group(1)}"')


def checkEmails(path, text):
	# Email không vắt qua hai dòng: chỉ quét các dòng có "@" (nhanh gấp vài lần quét cả tệp, cùng kết quả).
	if '@' not in text:
		return
	lines = '\n'.join(line for line in text.split('\n') if '@' in line)
	for email in set(EMAIL.findall(lines)):
		if email.lower() != COMPANY_EMAIL:
			error(path, f'email "{email}" khác email chung của công ty ({COMPANY_EMAIL})')


def checkSecurityTxt(path, text):
	fields = dict(re.findall(r'^([A-Za-z-]+):\s*(.+)$', text, re.MULTILINE))
	for key in ('Contact', 'Expires'):
		if key not in fields:
			error(path, f'thiếu trường bắt buộc "{key}" (RFC 9116)')
	# RFC 9116 cho phép nhiều Contact; email chung của công ty phải là một trong số đó.
	contacts = re.findall(r'^Contact:\s*(.+)$', text, re.MULTILINE)
	if contacts and f'mailto:{COMPANY_EMAIL}' not in contacts:
		error(path, f'Contact phải có mailto:{COMPANY_EMAIL}')
	expires = fields.get('Expires', '')
	try:
		moment = datetime.fromisoformat(expires)
	except ValueError:
		error(path, f'Expires không đúng định dạng ISO 8601: {expires}')
		return
	if moment.tzinfo is None:
		error(path, 'Expires phải có múi giờ (Z hoặc độ lệch UTC)')
		return
	remaining = (moment - datetime.now(UTC)).days
	if remaining < 0:
		error(path, 'Expires đã hết hạn — gia hạn tối đa 1 năm')
	elif remaining < EXPIRY_NOTICE_DAYS:
		error(
			path,
			f'Expires còn {remaining} ngày — gia hạn (tối đa 1 năm) rồi đăng lại tệp lên website',
		)
	elif remaining > 366:
		error(path, 'Expires vượt quá 1 năm (RFC 9116 khuyến nghị tối đa 1 năm)')


def checkChangelog(path, text):
	# Tiêu đề và liên kết trong ví dụ mã là nội dung nguyên văn, không phải cấu trúc của CHANGELOG.
	text = withoutCodeBlocks(text)
	versions = re.findall(r'^## \[([^\]]+)\]', text, re.MULTILINE)
	if not versions or versions[0] != 'CHƯA PHÁT HÀNH':
		error(path, 'mục đầu tiên phải là "## [CHƯA PHÁT HÀNH]"')
	if len(versions) != len(set(versions)):
		error(path, 'có phiên bản bị lặp')
	# So sánh từ tag phát hành gần nhất tới HEAD; trước tag đầu tiên dùng SHA commit gốc. Không dùng tên branch
	# (main…HEAD) vì trang so sánh sẽ rỗng khi xem trên main.
	unreleased = re.search(
		r'^## \[CHƯA PHÁT HÀNH\]\([^)]*/compare/([^)]+)\.\.\.HEAD\)', text, re.MULTILINE
	)
	if unreleased and not (
		RELEASE_TAG.fullmatch(unreleased.group(1))
		or re.fullmatch(r'[0-9a-f]{40}', unreleased.group(1))
	):
		error(
			path,
			f'liên kết CHƯA PHÁT HÀNH phải so sánh từ tag phát hành (Stable.v…, Beta.v…, v…) '
			f'hoặc SHA commit gốc trước lần phát hành đầu tiên tới HEAD, '
			f'không phải "{unreleased.group(1)}"',
		)
	checkAbsoluteLinks(path, text, 'mỗi mục thành nội dung GitHub Release')


def checkRequiredFiles():
	errors.extend(
		f'thiếu tệp bắt buộc {required}'
		for required in (
			'README.md',
			'CHANGELOG.md',
			'SECURITY.md',
			'CONTRIBUTING.md',
			'CODE_OF_CONDUCT.md',
			'SUPPORT.md',
		)
		if not (ROOT / required).exists()
	)
