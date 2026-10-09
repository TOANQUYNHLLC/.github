"""Gọi GitHub CLI (gh) và liệt kê repository của tổ chức."""

import json
import re
import subprocess
from pathlib import Path

ORG = 'TOANQUYNHLLC'
CLI_TIMEOUT = 120

ROOT = Path(__file__).resolve().parents[2]
COMMIT_MUTATION = (
	'mutation($input: CreateCommitOnBranchInput!) { createCommitOnBranch(input: $input) '
	'{ commit { oid } } }'
)


def gh(*args, stdin=None):
	try:
		result = subprocess.run(
			['gh', *args],
			input=stdin,
			capture_output=True,
			text=True,
			check=False,
			timeout=CLI_TIMEOUT,
		)
	except subprocess.TimeoutExpired as exc:
		# Kết quả mutation có thể chưa biết; không tự gửi lại hoặc in stdin chứa payload.
		raise RuntimeError(
			'GitHub CLI vượt thời gian chờ; chưa xác nhận kết quả, hãy xem trước lại'
		) from exc
	if result.returncode != 0:
		raise RuntimeError(result.stderr.strip() or f'gh {" ".join(args)} thất bại')
	return result.stdout


def ghJson(*args):
	output = gh(*args)
	return json.loads(output) if output.strip() else None


def ghList(endpoint):
	"""Gộp danh sách REST từ ít nhất một trang (trang rỗng hợp lệ); lỗi trang sau không trả danh sách thiếu."""
	separator = '&' if '?' in endpoint else '?'
	pages = ghJson('api', '--paginate', '--slurp', f'{endpoint}{separator}per_page=100')
	if (
		not isinstance(pages, list)
		or not pages
		or any(not isinstance(page, list) for page in pages)
	):
		raise ValueError(f'{endpoint}: phản hồi phân trang phải là danh sách các trang')
	return [item for page in pages for item in page]


def validateIdentity(endpoint, data):
	"""Xác minh tài nguyên sau chuyển hướng API; tên GitHub không phân biệt hoa/thường."""
	parts = endpoint.split('/')
	if len(parts) == 3 and parts[0] == 'repos':
		key, expected = 'full_name', '/'.join(parts[1:])
	elif len(parts) == 2 and parts[0] == 'orgs':
		key, expected = 'login', parts[1]
	else:
		raise ValueError(f'{endpoint}: endpoint không có danh tính repository hoặc tổ chức')
	if (
		not isinstance(data, dict)
		or not isinstance(data.get(key), str)
		or data[key].casefold() != expected.casefold()
	):
		raise ValueError(f'{endpoint}: không xác minh được danh tính tài nguyên')


def isNotFound(exc):
	"""GitHub CLI ghi mã HTTP trong stderr; lỗi quyền, giới hạn API hoặc mạng không phải tệp thiếu."""
	return re.search(r'\bHTTP 404\b', str(exc)) is not None


def isEmptyRepository(exc):
	"""API Git database (ref, cây) trả HTTP 409 "Git Repository is empty" cho repository chưa có commit nào."""
	return re.search(r'\bHTTP 409\b', str(exc)) is not None


def ghExists(endpoint):
	"""True nếu đọc được tài nguyên, False chỉ khi HTTP 404; các lỗi khác để người gọi xử lý."""
	try:
		gh('api', endpoint, '--silent')
		return True
	except RuntimeError as exc:
		if isNotFound(exc):
			return False
		raise


def listRepos(only, includeArchived=False):
	if only:
		return [only]
	# REST nhanh hơn gh repo list (GraphQL) gần một nửa; --paginate đọc đủ khi có hơn 100 repository.
	output = gh(
		'api',
		'--paginate',
		f'orgs/{ORG}/repos?per_page=100&type=all',
		'--jq',
		'.[] | .name' if includeArchived else '.[] | select(.archived | not) | .name',
	)
	return sorted(output.split())


def defaultBranch(repo):
	"""Xác minh repository trước khi dùng nhánh mặc định để đọc hoặc ghi tệp, ruleset."""
	endpoint = f'repos/{ORG}/{repo}'
	data = ghJson('api', endpoint)
	validateIdentity(endpoint, data)
	if not isinstance(data.get('default_branch'), str) or not data['default_branch']:
		raise ValueError(f'{repo}: không đọc được nhánh mặc định')
	return data['default_branch']
