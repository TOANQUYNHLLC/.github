"""Gọi GitHub CLI cho quy trình phát hành của repository."""

import json
import re
import subprocess

CLI_TIMEOUT = 120


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


def isNotFound(exc):
	"""GitHub CLI ghi mã HTTP trong stderr; lỗi quyền, giới hạn API hoặc mạng không phải tệp thiếu."""
	return re.search(r'\bHTTP 404\b', str(exc)) is not None


def ghExists(endpoint):
	"""True nếu đọc được tài nguyên, False chỉ khi HTTP 404; các lỗi khác để người gọi xử lý."""
	try:
		gh('api', endpoint, '--silent')
		return True
	except RuntimeError as exc:
		if isNotFound(exc):
			return False
		raise
