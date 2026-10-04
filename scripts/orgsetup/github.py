"""Gọi GitHub CLI (gh) và liệt kê repository của tổ chức."""

import json
import subprocess
from pathlib import Path

ORG = 'TOANQUYNHLLC'

ROOT = Path(__file__).resolve().parents[2]


def gh(*args, stdin=None):
	result = subprocess.run(['gh', *args], input=stdin, capture_output=True, text=True, check=False)
	if result.returncode != 0:
		raise RuntimeError(result.stderr.strip() or f'gh {" ".join(args)} thất bại')
	return result.stdout


def ghJson(*args):
	output = gh(*args)
	return json.loads(output) if output.strip() else None


def ghExists(endpoint):
	try:
		gh('api', endpoint, '--silent')
		return True
	except RuntimeError:
		return False


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
