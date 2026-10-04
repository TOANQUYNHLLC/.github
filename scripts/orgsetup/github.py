"""Gọi GitHub CLI (gh) và liệt kê repository của tổ chức."""

import json
import re
import subprocess
from pathlib import Path

ORG = 'TOANQUYNHLLC'

ROOT = Path(__file__).resolve().parents[2]
COMMIT_MUTATION = (
	'mutation($input: CreateCommitOnBranchInput!) { createCommitOnBranch(input: $input) '
	'{ commit { oid } } }'
)


def gh(*args, stdin=None):
	result = subprocess.run(['gh', *args], input=stdin, capture_output=True, text=True, check=False)
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


def listRepos(only):
	if only:
		return [only]
	# REST nhanh hơn gh repo list (GraphQL) gần một nửa; --paginate đọc đủ khi có hơn 100 repository.
	output = gh(
		'api',
		'--paginate',
		f'orgs/{ORG}/repos?per_page=100&type=all',
		'--jq',
		'.[] | select(.archived | not) | .name',
	)
	return sorted(output.split())


def defaultBranch(repo):
	return ghJson('api', f'repos/{ORG}/{repo}')['default_branch']
