"""Đối chiếu toàn bộ thay đổi của branch với lịch sử nhánh chính để shell/prune-branches.sh dọn branch local.

Chạy: python3 scripts/check-branch-merged.py <nhánh chính> <branch>
Mã thoát: 0 đã hợp nhất theo nội dung, 1 còn thay đổi chưa xác nhận, 2 lỗi đọc Git.
Không sửa ref, index hay cây làm việc của người dùng; không tạo commit tạm. So bản vá giữ nguyên khoảng trắng
và dữ liệu nhị phân, chỉ bỏ số dòng, tên mục của hunk và ID blob trong dòng index của diff.
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DIFF_OPTIONS = (
	'--no-ext-diff',
	'--no-textconv',
	'--no-renames',
	'--binary',
	'--full-index',
	'--ignore-submodules=none',
	'--submodule=short',
	'--unified=3',
	'--inter-hunk-context=0',
	'--diff-algorithm=myers',
	'--no-indent-heuristic',
	'--no-color',
	'--src-prefix=a/',
	'--dst-prefix=b/',
)
INDEX_LINE = re.compile(rb'^index [0-9a-f]+\.\.[0-9a-f]+(?: [0-7]+)?\n', re.MULTILINE)
HUNK_LINE = re.compile(rb'^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@[^\n]*\n', re.MULTILINE)


def git(*args, root=None, allowedCodes=(0,), data=None, indexFile=None):
	"""Git chạy ở gốc repository; bỏ biến có thể ghi đè tham số định dạng diff."""
	environment = os.environ.copy()
	environment.pop('GIT_DIFF_OPTS', None)
	environment['GIT_NO_REPLACE_OBJECTS'] = '1'
	environment['GIT_GRAFT_FILE'] = os.devnull
	if indexFile is not None:
		environment['GIT_INDEX_FILE'] = str(indexFile)
	result = subprocess.run(
		['git', '-c', 'core.quotePath=true', '-c', 'diff.relative=false', *args],
		cwd=root,
		env=environment,
		capture_output=True,
		check=False,
		input=data,
	)
	if result.returncode not in allowedCodes:
		raise subprocess.CalledProcessError(result.returncode, result.args)
	return result


def patchKey(patch):
	"""Dấu vân tay của bản vá, giữ nguyên nội dung từng dòng; không phụ thuộc số dòng hay thứ tự tệp."""
	files = []
	for item in re.split(rb'(?=^diff --git )', patch, flags=re.MULTILINE):
		filePatch = item.strip(b'\n')
		if filePatch:
			filePatch = INDEX_LINE.sub(b'', filePatch)
			filePatch = HUNK_LINE.sub(b'@@\n', filePatch)
			files.append(filePatch)
	digest = hashlib.sha256()
	for filePatch in sorted(files):
		digest.update(len(filePatch).to_bytes(8, 'big'))
		digest.update(filePatch)
	return digest.digest()


def fileChanges(start, tip, root):
	"""Đường dẫn, mode và blob của từng thay đổi; NUL giữ nguyên tên tệp có khoảng trắng hay xuống dòng."""
	fields = git(
		'diff',
		'--raw',
		'-z',
		'--no-abbrev',
		'--no-renames',
		'--ignore-submodules=none',
		'--no-ext-diff',
		'--no-textconv',
		'--no-color',
		start,
		tip,
		'--',
		root=root,
	).stdout.split(b'\0')
	return [
		(fields[index].split(), os.fsdecode(fields[index + 1]))
		for index in range(0, len(fields) - 1, 2)
	]


def treeEntry(commit, path, root):
	item = git('--literal-pathspecs', 'ls-tree', '-z', commit, '--', path, root=root).stdout
	return item.split(b'\t', 1)[0].split() if item else []


def mergeMatches(changes, parent, commit, root, folder):
	"""Khi main đã sửa nội dung nền, so kết quả hợp nhất ba phía; không áp nhầm hunk vào khối lặp còn lại."""
	for change, path in changes:
		before, after = change[2], change[3]
		parentEntry = treeEntry(parent, path, root)
		expectedEntry = treeEntry(commit, path, root)
		if (parentEntry and parentEntry[2] == before) or (
			not parentEntry and not before.strip(b'0')
		):
			continue
		if expectedEntry and expectedEntry[2] == after:
			continue
		if (
			not parentEntry
			or not expectedEntry
			or change[0] not in (b':100644', b':100755')
			or parentEntry[1] != b'blob'
			or expectedEntry[1] != b'blob'
		):
			return False
		payloads = [
			git('cat-file', 'blob', value.decode(), root=root).stdout
			for value in (parentEntry[2], before, after)
		]
		if any(b'\0' in payload for payload in payloads):
			return False
		paths = [Path(folder) / name for name in ('current', 'base', 'other')]
		for target, payload in zip(paths, payloads, strict=True):
			target.write_bytes(payload)
		merged = git(
			'merge-file', '-p', *map(str, paths), root=root, allowedCodes=tuple(range(128))
		)
		if merged.returncode != 0:
			return False
		actual = git('hash-object', '--stdin', root=root, data=merged.stdout).stdout.strip()
		if actual != expectedEntry[2]:
			return False
	return True


def appliesAsCommit(patch, changes, parent, commit, root):
	"""Bản vá phải tái tạo đúng cây của commit trên main: khác vị trí trong nội dung lặp lại không coi là khớp.
	Dùng index riêng trong thư mục tạm; không checkout hoặc chạy merge driver của người dùng."""
	with tempfile.TemporaryDirectory() as folder:
		indexFile = Path(folder) / 'index'
		git('read-tree', parent, root=root, indexFile=indexFile)
		result = git(
			'apply',
			'--cached',
			'--whitespace=nowarn',
			'-',
			root=root,
			indexFile=indexFile,
			data=patch,
			allowedCodes=(0, 1),
		)
		if result.returncode != 0:
			return False
		actual = git('write-tree', root=root, indexFile=indexFile).stdout.strip()
		expected = git('rev-parse', f'{commit}^{{tree}}', root=root).stdout.strip()
		return actual == expected and mergeMatches(changes, parent, commit, root, folder)


def isMerged(mainRef, branchRef):
	"""Nhận diện Merge, cây giống nhau và các nhóm squash bao phủ toàn bộ branch; lỗi Git không coi là khớp."""
	root = os.fsdecode(git('rev-parse', '--show-toplevel').stdout.rstrip(b'\n'))
	main = git('rev-parse', '--verify', f'{mainRef}^{{commit}}', root=root).stdout.strip().decode()
	branch = (
		git('rev-parse', '--verify', f'{branchRef}^{{commit}}', root=root).stdout.strip().decode()
	)
	if (
		git('merge-base', '--is-ancestor', branch, main, root=root, allowedCodes=(0, 1)).returncode
		== 0
	):
		return True
	trees = git(
		'rev-parse', f'{main}^{{tree}}', f'{branch}^{{tree}}', root=root
	).stdout.splitlines()
	if trees[0] == trees[1]:
		return True
	bases = git('merge-base', '--all', main, branch, root=root, allowedCodes=(0, 1)).stdout.split()
	# Lịch sử không liên quan hoặc có nhiều điểm tách: không đủ căn cứ chia các nhóm, giữ branch.
	if len(bases) != 1:
		return False
	base = bases[0].decode()
	patches = git(
		'log',
		'--format=%x00%H %P%x00',
		'--no-show-signature',
		'--no-notes',
		'--no-merges',
		'-p',
		*DIFF_OPTIONS,
		f'{base}..{main}',
		'--',
		root=root,
	).stdout
	# Chỉ tách header ở đầu dòng; tệp bị ép diff dạng văn bản có thể chứa NUL trong nội dung.
	parts = re.split(rb'^\x00([0-9a-f]+) ([0-9a-f]+)\x00\n', patches, flags=re.MULTILINE)
	mainPatches = {}
	for index in range(1, len(parts), 3):
		commit, parent = parts[index].decode(), parts[index + 1].decode()
		mainPatches.setdefault(patchKey(parts[index + 2]), []).append((parent, commit))

	def matches(start, tip):
		patch = git('diff', *DIFF_OPTIONS, start, tip, '--', root=root).stdout
		if not patch:
			return True
		candidates = mainPatches.get(patchKey(patch), [])
		if not candidates:
			return False
		changes = fileChanges(start, tip, root)
		return any(
			appliesAsCommit(patch, changes, parent, commit, root) for parent, commit in candidates
		)

	if matches(base, branch):
		return True
	history = git(
		'rev-list', '--first-parent', '--reverse', f'{base}..{branch}', root=root
	).stdout.split()
	checkpoints = [base]
	for item in history:
		tip = item.decode()
		if any(matches(checkpoint, tip) for checkpoint in reversed(checkpoints)):
			checkpoints.append(tip)
	return checkpoints[-1] == branch


def main():
	if sys.version_info < (3, 11):  # noqa: UP036 — cố ý: báo lỗi khi shell gọi Python cũ của macOS
		print(
			'❌ Đối chiếu branch cần Python ≥ 3.11; kích hoạt mise rồi chạy lại.', file=sys.stderr
		)
		return 2
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument('mainRef', help='Ref hoặc SHA của nhánh chính để đối chiếu')
	parser.add_argument('branchRef', help='Ref hoặc SHA của branch cần kiểm tra')
	args = parser.parse_args()
	try:
		return 0 if isMerged(args.mainRef, args.branchRef) else 1
	except (OSError, subprocess.CalledProcessError) as exc:
		code = getattr(exc, 'returncode', None)
		print(f'❌ Không đối chiếu được lịch sử branch bằng Git (mã lỗi: {code}).', file=sys.stderr)
		return 2


if __name__ == '__main__':
	sys.exit(main())
