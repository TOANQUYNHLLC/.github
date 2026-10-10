"""Test tự động cho shell/sync.sh (chuyển branch, git pull) và shell/prune-branches.sh (xóa branch đã hợp nhất mà
remote đã xóa).

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import ROOT, loadScript
except ModuleNotFoundError:
	from scripts.testsupport import ROOT, loadScript

SCRIPT = ROOT / 'shell' / 'sync.sh'
PRUNE = ROOT / 'shell' / 'prune-branches.sh'


class SyncTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		# Remote và hai bản clone mẫu dựng một lần mỗi tiến trình (khoảng mười lệnh git); mỗi test chép bản mẫu.
		cls.templates = tempfile.TemporaryDirectory()
		cls.addClassCleanup(cls.templates.cleanup)

	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		folder = Path(self.tmp.name)
		template = Path(type(self).templates.name)
		if not (template / 'other').exists():
			self.prepare(template)
			self.build(template)
		shutil.copytree(template, folder, symlinks=True, dirs_exist_ok=True)
		self.prepare(folder)
		# git clone ghi đường dẫn remote nguyên văn vào .git/config: đổi sang remote của bản chép.
		for repo in (self.clone, self.other):
			config = repo / '.git' / 'config'
			config.write_text(
				config.read_text(encoding='utf-8').replace(str(template), str(folder)),
				encoding='utf-8',
			)

	def prepare(self, folder):
		"""Cấu hình git sạch và đường dẫn remote, hai bản clone trong folder."""
		# Không phụ thuộc cấu hình git của máy (danh tính, ký commit, hook toàn cục).
		# git < 2.32 bỏ qua GIT_CONFIG_GLOBAL và đọc $HOME/.gitconfig: đặt cả hai cùng trỏ cấu hình sạch.
		# Tắt bảo trì tự động: commit, push chạy "git maintenance run --auto" ở tiến trình nền, ghi vào repository
		# đúng lúc test chép mẫu hoặc xóa thư mục tạm.
		home = folder / 'home'
		home.mkdir(exist_ok=True)
		config = home / '.gitconfig'
		config.write_text(
			'[user]\n\tname = test\n\temail = \n'
			'[commit]\n\tgpgsign = false\n[init]\n\tdefaultBranch = main\n'
			'[maintenance]\n\tauto = false\n[gc]\n\tauto = 0\n[receive]\n\tautogc = false\n',
			encoding='utf-8',
		)
		self.environment = dict(
			os.environ, GIT_CONFIG_GLOBAL=str(config), GIT_CONFIG_NOSYSTEM='1', HOME=str(home)
		)
		self.remote, self.clone, self.other = (
			folder / 'remote.git',
			folder / 'clone',
			folder / 'other',
		)

	def build(self, folder):
		"""Remote có main với một commit; clone (đã đẩy main, theo dõi origin/main) và other cùng trỏ remote."""
		self.git(folder, 'init', '-q', '--bare', str(self.remote))
		# init.defaultBranch chỉ có từ git 2.28: đặt main tường minh để test chạy được với git cũ.
		self.git(self.remote, 'symbolic-ref', 'HEAD', 'refs/heads/main')
		self.git(folder, 'clone', '-q', str(self.remote), str(self.clone))
		self.git(self.clone, 'symbolic-ref', 'HEAD', 'refs/heads/main')
		self.commit(self.clone, 'base.txt', 'base')
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'main')
		self.git(folder, 'clone', '-q', str(self.remote), str(self.other))

	def tearDown(self):
		self.tmp.cleanup()

	def git(self, cwd, *args):
		return subprocess.run(
			['git', *args],
			cwd=cwd,
			env=self.environment,
			capture_output=True,
			text=True,
			check=True,
		).stdout

	def commit(self, repo, name, content):
		(repo / name).write_text(f'{content}\n', encoding='utf-8')
		self.git(repo, 'add', name)
		self.git(repo, 'commit', '-qm', f'thêm {name}')

	def branch(self, name, *files):
		"""Tạo branch từ main trong clone, commit từng tệp, đẩy lên remote, quay lại main."""
		self.git(self.clone, 'switch', '-q', '-c', name, 'main')
		for file in files:
			self.commit(self.clone, file, name)
		self.git(self.clone, 'push', '-q', '-u', 'origin', name)
		self.git(self.clone, 'switch', '-q', 'main')

	def mergeOnRemote(self, name, squash):
		"""Hợp nhất như GitHub (Squash hoặc Merge) từ một bản clone khác rồi xóa branch trên remote."""
		self.git(self.other, 'fetch', '-q', 'origin')
		self.git(self.other, 'switch', '-q', 'main')
		self.git(self.other, 'pull', '-q')
		if squash:
			self.git(self.other, 'merge', '-q', '--squash', f'origin/{name}')
			self.git(self.other, 'commit', '-qm', f'{name} (#1)')
		else:
			self.git(self.other, 'merge', '-q', '--no-ff', '-m', f'Merge {name}', f'origin/{name}')
		self.git(self.other, 'push', '-q', 'origin', 'main', f':{name}')

	def runScript(self, script=SCRIPT, *arguments):
		return subprocess.run(
			['bash', str(script), *arguments],
			cwd=self.clone,
			env=self.environment,
			capture_output=True,
			text=True,
			check=True,
		)

	def sync(self, branch='main'):
		"""Như make sync [BRANCH=…]: sync.sh rồi prune-branches.sh; trả đầu ra của cả hai."""
		first = self.runScript(SCRIPT, branch)
		second = self.runScript(PRUNE)
		return subprocess.CompletedProcess(first.args, 0, first.stdout + second.stdout, '')

	def attempt(self, script, *arguments, environment=None):
		"""Chạy script, không ném lỗi khi thoát khác 0 — để khẳng định mã thoát, thông báo."""
		return subprocess.run(
			['bash', str(script), *arguments],
			cwd=self.clone,
			env=environment or self.environment,
			capture_output=True,
			text=True,
			check=False,
		)

	def localBranches(self):
		return self.git(
			self.clone, 'for-each-ref', '--format=%(refname:short)', 'refs/heads'
		).split()

	def gitFailureEnvironment(self, argument):
		"""Git giả chỉ làm lỗi lệnh có một tham số đã chọn; mọi lệnh khác gọi Git thật."""
		folder = Path(self.tmp.name) / 'bin'
		folder.mkdir(exist_ok=True)
		wrapper = folder / 'git'
		wrapper.write_text(
			'#!/usr/bin/env python3\nimport os\nimport sys\n'
			f'if {argument!r} in sys.argv[1:]:\n    sys.exit(128)\n'
			f'os.execv({shutil.which("git")!r}, ["git", *sys.argv[1:]])\n',
			encoding='utf-8',
		)
		wrapper.chmod(0o755)
		return dict(self.environment, PATH=f'{folder}{os.pathsep}{os.environ["PATH"]}')

	def testDeletesSquashedAndMergedBranches(self):
		# Squash đổi SHA nên git branch -d báo "not fully merged"; script nhận ra theo nội dung. Branch hợp nhất
		# bằng Merge là tổ tiên của main.
		self.branch('feat/squashed', 'a.txt', 'b.txt')
		self.branch('fix/merged', 'c.txt')
		self.mergeOnRemote('feat/squashed', squash=True)
		self.mergeOnRemote('fix/merged', squash=False)
		self.git(self.clone, 'switch', '-q', 'feat/squashed')
		self.sync()
		self.assertEqual(self.localBranches(), ['main'])
		self.assertEqual(self.git(self.clone, 'branch', '--show-current').strip(), 'main')
		self.assertTrue((self.clone / 'a.txt').exists())

	def testKeepsBranchWithUnmergedChanges(self):
		# Branch được squash rồi có thêm commit chưa vào main: remote đã xóa nhưng còn thay đổi — giữ lại.
		self.branch('feat/extra', 'a.txt')
		self.mergeOnRemote('feat/extra', squash=True)
		self.git(self.clone, 'switch', '-q', 'feat/extra')
		self.commit(self.clone, 'later.txt', 'chưa đẩy')
		result = self.sync()
		self.assertEqual(self.localBranches(), ['feat/extra', 'main'])
		self.assertIn('Giữ lại feat/extra: có thay đổi chưa vào main', result.stdout)

	def testDeletesBranchSquashedInSeveralGroups(self):
		# Một branch tiếp tục được dùng sau lần squash đầu: mỗi nhóm khớp một commit khác trên main.
		self.branch('fix/groups', 'a.txt', 'b.txt')
		self.mergeOnRemote('fix/groups', squash=True)
		self.git(self.clone, 'switch', '-q', 'fix/groups')
		self.commit(self.clone, 'c.txt', 'nhóm sau')
		self.commit(self.clone, 'd.txt', 'nhóm sau')
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/groups')
		self.mergeOnRemote('fix/groups', squash=True)
		# main đã sửa lại nội dung sau hợp nhất: không thể chỉ so cây cuối của branch với main hiện tại.
		self.commit(self.other, 'a.txt', 'đã sửa trên main')
		self.git(self.other, 'push', '-q', 'origin', 'main')
		self.sync()
		self.assertEqual(self.localBranches(), ['main'])
		self.assertEqual((self.clone / 'a.txt').read_text(), 'đã sửa trên main\n')

	def testDeletesBranchContainingSeparatelySquashedMerge(self):
		# Như fix/project_review: commit riêng, merge nhánh đã squash riêng, rồi một nhóm commit squash.
		self.branch('fix/review', 'a.txt')
		self.branch('docs/guide', 'b.txt')
		self.mergeOnRemote('fix/review', squash=True)
		self.mergeOnRemote('docs/guide', squash=True)
		self.git(self.clone, 'switch', '-q', 'fix/review')
		self.git(self.clone, 'merge', '-q', '--no-ff', '-m', 'nhập tài liệu', 'docs/guide')
		self.commit(self.clone, 'c.txt', 'sửa lỗi')
		self.commit(self.clone, 'd.txt', 'sửa lỗi')
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/review')
		self.mergeOnRemote('fix/review', squash=True)
		self.commit(self.other, 'later.txt', 'sau hợp nhất')
		self.git(self.other, 'push', '-q', 'origin', 'main')
		self.sync()
		self.assertEqual(self.localBranches(), ['main'])

	def testPruneTriesAllValidSquashBoundaries(self):
		# Commit đầu từng được cherry-pick rồi revert; bản squash sau chứa cả commit đầu và commit thứ hai.
		# Chọn ngay điểm chia đầu tiên sẽ bỏ lỡ nhóm lớn hơn và giữ nhầm branch đã hợp nhất.
		self.branch('fix/boundaries', 'a.txt', 'b.txt')
		first = self.git(self.clone, 'rev-parse', 'fix/boundaries~1').strip()
		self.git(self.other, 'fetch', '-q', 'origin')
		self.git(self.other, 'cherry-pick', first)
		self.git(self.other, 'revert', '--no-edit', 'HEAD')
		self.git(self.other, 'push', '-q', 'origin', 'main')
		self.mergeOnRemote('fix/boundaries', squash=True)
		self.git(self.clone, 'switch', '-q', 'fix/boundaries')
		self.commit(self.clone, 'c.txt', 'nhóm sau')
		self.commit(self.clone, 'd.txt', 'nhóm sau')
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/boundaries')
		self.mergeOnRemote('fix/boundaries', squash=True)
		self.commit(self.other, 'later.txt', 'sau hợp nhất')
		self.git(self.other, 'push', '-q', 'origin', 'main')
		self.sync()
		self.assertEqual(self.localBranches(), ['main'])

	def testKeepsUnmergedChangesBetweenSquashedGroups(self):
		# Các commit trước và sau đã vào main, nhưng commit ở giữa chưa vào: không được bỏ qua nhóm đó.
		self.branch('fix/incomplete', 'a.txt', 'b.txt')
		self.mergeOnRemote('fix/incomplete', squash=True)
		self.git(self.clone, 'switch', '-q', 'fix/incomplete')
		self.commit(self.clone, 'missing.txt', 'chưa hợp nhất')
		self.commit(self.clone, 'c.txt', 'đã hợp nhất')
		later = self.git(self.clone, 'rev-parse', 'HEAD').strip()
		self.git(self.other, 'fetch', '-q', str(self.clone), later)
		self.git(self.other, 'cherry-pick', later)
		self.git(self.other, 'push', '-q', 'origin', 'main')
		result = self.sync()
		self.assertEqual(self.localBranches(), ['fix/incomplete', 'main'])
		self.assertIn('Giữ lại fix/incomplete: có thay đổi chưa vào main', result.stdout)

	def testKeepsBranchOpenInWorktree(self):
		# Branch đang mở ở worktree khác: git branch -D từ chối — script báo và chạy tiếp các branch sau.
		self.branch('docs/worktree', 'a.txt')
		self.branch('feat/squashed', 'b.txt')
		self.mergeOnRemote('docs/worktree', squash=True)
		self.mergeOnRemote('feat/squashed', squash=True)
		worktree = Path(self.tmp.name) / 'worktree'
		self.git(self.clone, 'worktree', 'add', '-q', str(worktree), 'docs/worktree')
		result = self.sync()
		self.assertEqual(self.localBranches(), ['docs/worktree', 'main'])
		self.assertIn('Giữ lại docs/worktree: đang mở ở worktree', result.stdout)

	def testSyncsGivenBranchFromRemote(self):
		# make sync BRANCH=…: branch chỉ có trên remote thì git switch tạo branch theo dõi origin; kéo được commit
		# mới do người khác đẩy, rồi vẫn dọn branch đã hợp nhất.
		self.git(self.other, 'switch', '-q', '-c', 'feat/other')
		self.commit(self.other, 'other.txt', 'từ máy khác')
		self.git(self.other, 'push', '-q', '-u', 'origin', 'feat/other')
		self.branch('fix/squashed', 'b.txt')
		self.mergeOnRemote('fix/squashed', squash=True)
		self.sync('feat/other')
		self.assertEqual(self.git(self.clone, 'branch', '--show-current').strip(), 'feat/other')
		self.assertTrue((self.clone / 'other.txt').exists())
		self.assertEqual(
			self.git(self.clone, 'rev-parse', '--abbrev-ref', 'feat/other@{upstream}').strip(),
			'origin/feat/other',
		)
		self.assertEqual(self.localBranches(), ['feat/other', 'main'])

	def testLocalOnlyBranchSkipsPullButStillCleansUp(self):
		# Branch chưa đẩy lên không có upstream: bỏ qua git pull (không dừng), vẫn dọn branch đã hợp nhất.
		self.git(self.clone, 'branch', 'local/only')
		self.branch('fix/squashed', 'b.txt')
		self.mergeOnRemote('fix/squashed', squash=True)
		result = self.sync('local/only')
		self.assertIn(
			'Bỏ qua git pull: local/only chưa có branch theo dõi trên origin.', result.stdout
		)
		self.assertEqual(self.git(self.clone, 'branch', '--show-current').strip(), 'local/only')
		self.assertEqual(self.localBranches(), ['local/only', 'main'])

	def testTracksOriginWhenAnotherRemoteHasSameBranch(self):
		# Remote khác (upstream của fork…) cũng có branch cùng tên: vẫn theo dõi đúng origin, không để git switch báo
		# "matched multiple remote tracking branches".
		self.git(self.other, 'switch', '-q', '-c', 'feat/shared')
		self.commit(self.other, 'shared.txt', 'trên origin')
		self.git(self.other, 'push', '-q', '-u', 'origin', 'feat/shared')
		upstream = Path(self.tmp.name) / 'upstream.git'
		self.git(self.clone, 'init', '-q', '--bare', str(upstream))
		self.git(self.clone, 'remote', 'add', 'upstream', str(upstream))
		self.git(self.clone, 'push', '-q', 'upstream', 'main:feat/shared')
		self.git(self.clone, 'fetch', '-q', 'upstream')
		self.sync('feat/shared')
		self.assertEqual(
			self.git(self.clone, 'rev-parse', '--abbrev-ref', 'feat/shared@{upstream}').strip(),
			'origin/feat/shared',
		)
		self.assertTrue((self.clone / 'shared.txt').exists())

	def testRefNameWithPrefixGetsHint(self):
		# Nhập nhầm origin/main, refs/heads/main: dừng, gợi ý tên đúng; không đổi branch, không tạo branch lạ.
		self.git(self.clone, 'switch', '-q', '-c', 'feature/here')
		for name in ('origin/main', 'refs/heads/main'):
			with self.subTest(name=name):
				result = self.attempt(SCRIPT, name)
				self.assertEqual(result.returncode, 1, result.stderr)
				self.assertIn('truyền tên branch không kèm tiền tố (ví dụ main)', result.stderr)
				self.assertEqual(
					self.git(self.clone, 'branch', '--show-current').strip(), 'feature/here'
				)
		self.assertEqual(self.localBranches(), ['feature/here', 'main'])

	def testUnknownBranchStopsWithoutCleanup(self):
		# Branch không có ở máy lẫn remote: git switch báo lỗi, script dừng, không dọn branch nào.
		self.branch('fix/squashed', 'b.txt')
		self.mergeOnRemote('fix/squashed', squash=True)
		result = subprocess.run(
			['bash', str(SCRIPT), 'khong/co'],
			cwd=self.clone,
			env=self.environment,
			capture_output=True,
			text=True,
			check=False,
		)
		self.assertEqual(result.returncode, 1, result.stderr)
		self.assertIn('Không có branch khong/co ở máy lẫn trên origin', result.stderr)
		self.assertEqual(self.localBranches(), ['fix/squashed', 'main'])

	def testSyncNeedsBranch(self):
		# sync.sh chỉ chuyển branch, kéo code: thiếu tên branch thì báo cách dùng, không làm gì.
		result = subprocess.run(
			['bash', str(SCRIPT)],
			cwd=self.clone,
			env=self.environment,
			capture_output=True,
			text=True,
			check=False,
		)
		self.assertEqual(result.returncode, 2)
		self.assertIn('Cách dùng: shell/sync.sh <branch>', result.stderr)

	def testMakeSyncDefaultsToMainThenPrunes(self):
		# Mỗi script một việc, Makefile ghép lại: chuyển branch, kéo code rồi mới dọn branch. Không truyền BRANCH
		# (hoặc truyền rỗng) thì về main; tên có ký tự đặc biệt tới script nguyên văn. Chạy make thật với hai script
		# giả ghi lại tham số, trong thư mục tạm (không đụng repository).
		folder = Path(self.tmp.name) / 'make'
		(folder / 'shell').mkdir(parents=True)
		calls = folder / 'calls'
		for name in ('sync.sh', 'prune-branches.sh'):
			fake = folder / 'shell' / name
			fake.write_text(
				f'#!/bin/sh\nprintf "%s [%s]\\n" {name} "$*" >> "{calls}"\n', encoding='utf-8'
			)
			fake.chmod(0o755)
		for arguments, branch in (
			([], 'main'),
			(['BRANCH='], 'main'),
			(['BRANCH=feat/x'], 'feat/x'),
			(['BRANCH=a; echo chèn'], 'a; echo chèn'),
		):
			with self.subTest(arguments=arguments):
				calls.unlink(missing_ok=True)
				subprocess.run(
					[
						'make',
						'--no-print-directory',
						'-s',
						'-f',
						str(ROOT / 'Makefile'),
						'sync',
						*arguments,
					],
					cwd=folder,
					env=self.environment,
					capture_output=True,
					check=True,
				)
				self.assertEqual(
					calls.read_text(encoding='utf-8').splitlines(),
					[f'sync.sh [{branch}]', 'prune-branches.sh []'],
				)
		# Không có lệnh syncmain riêng: make sync không truyền BRANCH là về main.
		removed = subprocess.run(
			['make', '--no-print-directory', '-n', 'syncmain'],
			cwd=ROOT,
			capture_output=True,
			text=True,
			check=False,
		)
		self.assertNotEqual(removed.returncode, 0)

	def testMakeVariablesReachScriptsUnparsedByShell(self):
		# TAG, REF đi qua biến môi trường như BRANCH: ký tự đặc biệt của shell không thành lệnh; thiếu TAG thì báo
		# rõ thay vì lỗi tiếng Anh của argparse; REF mặc định main.
		# PYTHON truyền từ make cha qua MAKEFLAGS không được thay đổi trường hợp test mặc định.
		def recipe(*arguments, pythonCommand='python3'):
			return subprocess.run(
				['make', '--no-print-directory', '-n', f'PYTHON={pythonCommand}', *arguments],
				cwd=ROOT,
				capture_output=True,
				text=True,
				check=False,
			)

		for pythonCommand in ('python3', sys.executable):
			with self.subTest(pythonCommand=pythonCommand):
				self.assertEqual(
					recipe(
						'release-notes', 'TAG=x; echo chèn', pythonCommand=pythonCommand
					).stdout.splitlines(),
					[f'{pythonCommand} scripts/release.py notes "$TAG"'],
				)
				self.assertEqual(
					recipe('forms', pythonCommand=pythonCommand).stdout.splitlines(),
					[f'{pythonCommand} scripts/check-github-forms.py "${{REF:-main}}"'],
				)
		missing = recipe('release-notes')
		self.assertNotEqual(missing.returncode, 0)
		self.assertIn('Thiếu TAG', missing.stderr)

	def testDivergedBranchIsNotMergedAutomatically(self):
		# Branch ở máy và trên origin cùng có commit mới: chỉ tua nhanh — dừng, không tự tạo merge commit (git
		# pull mặc định tạo merge commit hoặc dừng với thông báo khó hiểu tùy cấu hình pull.rebase).
		self.commit(self.other, 'remote.txt', 'trên origin')
		self.git(self.other, 'push', '-q', 'origin', 'main')
		self.commit(self.clone, 'local.txt', 'chỉ ở máy')
		before = self.git(self.clone, 'rev-parse', 'HEAD')
		result = self.attempt(SCRIPT, 'main')
		self.assertEqual(result.returncode, 1, result.stderr)
		self.assertIn('Không tua nhanh được main', result.stderr)
		self.assertEqual(self.git(self.clone, 'rev-parse', 'HEAD'), before)

	def testRefusesOperationInProgress(self):
		# Đang dở merge (xung đột): không chuyển branch giữa chừng.
		self.git(self.clone, 'switch', '-q', '-c', 'feat/a')
		self.commit(self.clone, 'base.txt', 'nhánh a')
		self.git(self.clone, 'switch', '-q', 'main')
		self.commit(self.clone, 'base.txt', 'nhánh main')
		subprocess.run(
			['git', 'merge', '-q', 'feat/a'],
			cwd=self.clone,
			env=self.environment,
			capture_output=True,
			check=False,
		)
		self.git(self.clone, 'add', 'base.txt')
		result = self.attempt(SCRIPT, 'feat/a')
		self.assertEqual(result.returncode, 1, result.stderr)
		self.assertIn('Đang dở thao tác git (MERGE_HEAD)', result.stderr)
		self.assertEqual(self.git(self.clone, 'branch', '--show-current').strip(), 'main')

	def testRejectsInvalidBranchNames(self):
		# Tên bắt đầu bằng "-" là tùy chọn của git switch; tên sai quy tắc ref bị từ chối trước khi gọi git.
		for name in ('-c', '--detach', 'a..b', 'x y'):
			with self.subTest(name=name):
				result = self.attempt(SCRIPT, name)
				self.assertEqual(result.returncode, 1, result.stderr)
				self.assertIn(f'Tên branch không hợp lệ: {name}', result.stderr)
				self.assertEqual(self.git(self.clone, 'branch', '--show-current').strip(), 'main')

	def testReportsDeletedUpstream(self):
		# Branch theo dõi trên origin đã bị xóa: báo đúng lý do bỏ qua git pull, không nhầm với branch chưa đẩy.
		self.branch('feat/gone', 'a.txt')
		self.git(self.other, 'push', '-q', 'origin', ':feat/gone')
		result = self.attempt(SCRIPT, 'feat/gone')
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertIn('branch theo dõi của feat/gone trên origin đã bị xóa', result.stdout)

	def testPruneWorksWithoutGitIdentity(self):
		# Máy chưa đặt user.name, user.email (máy mới, CI): bước nhận diện Squash không tạo commit tạm.
		# main có thêm commit sau khi hợp nhất để nội dung khác branch — buộc đi qua bước so bản vá.
		self.branch('fix/squashed', 'b.txt')
		self.mergeOnRemote('fix/squashed', squash=True)
		self.commit(self.other, 'later.txt', 'sau khi hợp nhất')
		self.git(self.other, 'push', '-q', 'origin', 'main')
		config = Path(self.tmp.name) / 'no-identity'
		config.write_text('[commit]\n\tgpgsign = false\n', encoding='utf-8')
		environment = {
			key: value
			for key, value in self.environment.items()
			if not key.startswith(('GIT_AUTHOR_', 'GIT_COMMITTER_')) and key != 'EMAIL'
		}
		environment.update(
			GIT_CONFIG_GLOBAL=str(config), HOME=self.tmp.name, GIT_CONFIG_NOSYSTEM='1'
		)
		result = self.attempt(PRUNE, environment=environment)
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(self.localBranches(), ['main'])

	def testPruneStopsWithoutOriginMain(self):
		# Không có origin/main thì không so được gì: báo lỗi rõ, không coi mọi branch là "có thay đổi".
		self.branch('fix/squashed', 'b.txt')
		self.git(self.other, 'push', '-q', 'origin', 'main:trunk')
		# Remote không cho xóa branch đang là HEAD của nó: đổi HEAD sang trunk trước.
		self.git(self.remote, 'symbolic-ref', 'HEAD', 'refs/heads/trunk')
		self.git(self.other, 'push', '-q', 'origin', ':main')
		result = self.attempt(PRUNE)
		self.assertEqual(result.returncode, 1, result.stderr)
		self.assertIn('Không có origin/main', result.stderr)
		self.assertEqual(self.localBranches(), ['fix/squashed', 'main'])

	def testPruneNeverDeletesMain(self):
		# main theo dõi một branch đã bị xóa trên origin (ví dụ đổi upstream nhầm): vẫn giữ main.
		self.git(self.other, 'push', '-q', 'origin', 'main:old-main')
		self.git(self.clone, 'fetch', '-q')
		self.git(self.clone, 'branch', '-q', '--set-upstream-to=origin/old-main', 'main')
		self.git(self.other, 'push', '-q', 'origin', ':old-main')
		result = self.attempt(PRUNE)
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertIn('Giữ lại main: branch chính', result.stdout)
		self.assertEqual(self.localBranches(), ['main'])

	def testRefusesUncommittedChanges(self):
		# git switch mang thay đổi chưa commit sang main: script dừng trước khi đổi branch, không xóa gì.
		self.branch('feat/squashed', 'a.txt')
		self.mergeOnRemote('feat/squashed', squash=True)
		self.git(self.clone, 'switch', '-q', 'feat/squashed')
		(self.clone / 'draft.txt').write_text('đang sửa\n', encoding='utf-8')
		result = subprocess.run(
			['bash', str(SCRIPT), 'main'],
			cwd=self.clone,
			env=self.environment,
			capture_output=True,
			text=True,
			check=False,
		)
		self.assertEqual(result.returncode, 1, result.stderr)
		self.assertIn('Còn thay đổi chưa commit', result.stderr)
		self.assertEqual(self.git(self.clone, 'branch', '--show-current').strip(), 'feat/squashed')
		self.assertEqual(self.localBranches(), ['feat/squashed', 'main'])

	def testPruneStaysOnCurrentBranchAndUsesOriginMain(self):
		# prune-branches.sh không đổi branch, không kéo code: branch hiện tại được giữ (không xóa được), branch khác đã
		# squash vẫn bị xóa dù main cục bộ chưa có commit hợp nhất — so với origin/main vừa tải về.
		self.branch('feat/current', 'a.txt')
		self.branch('fix/squashed', 'b.txt')
		self.mergeOnRemote('feat/current', squash=True)
		self.mergeOnRemote('fix/squashed', squash=True)
		self.git(self.clone, 'switch', '-q', 'feat/current')
		localMain = self.git(self.clone, 'rev-parse', 'main')
		result = self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['feat/current', 'main'])
		self.assertIn('Giữ lại feat/current: đang là branch hiện tại', result.stdout)
		self.assertEqual(self.git(self.clone, 'branch', '--show-current').strip(), 'feat/current')
		self.assertEqual(self.git(self.clone, 'rev-parse', 'main'), localMain)

	def testPruneKeepsUncommittedWorkInPlace(self):
		# Khác sync.sh, prune-branches.sh chạy được khi còn thay đổi chưa commit: không đổi branch nên không mang
		# thay đổi đi đâu.
		self.branch('fix/squashed', 'b.txt')
		self.mergeOnRemote('fix/squashed', squash=True)
		self.git(self.clone, 'switch', '-q', '-c', 'feature/wip')
		(self.clone / 'draft.txt').write_text('đang sửa\n', encoding='utf-8')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['feature/wip', 'main'])
		self.assertTrue((self.clone / 'draft.txt').exists())

	def testRefusesNewFilesDespiteUserConfig(self):
		# status.showUntrackedFiles=no làm git status ẩn tệp mới: git switch sẽ mang tệp đó sang branch khác.
		self.git(self.clone, 'switch', '-q', '-c', 'feature/wip')
		(self.clone / 'draft.txt').write_text('chưa add\n', encoding='utf-8')
		result = self.attempt(
			SCRIPT,
			'main',
			environment=dict(
				self.environment,
				GIT_CONFIG_COUNT='1',
				GIT_CONFIG_KEY_0='status.showUntrackedFiles',
				GIT_CONFIG_VALUE_0='no',
			),
		)
		self.assertEqual(result.returncode, 1, result.stderr)
		self.assertIn('Còn thay đổi chưa commit', result.stderr)
		self.assertEqual(self.git(self.clone, 'branch', '--show-current').strip(), 'feature/wip')

	def testKeepsBranchWithoutRemoteOrStillOnRemote(self):
		# Chỉ xét branch mà remote đã xóa: branch chưa đẩy và branch còn trên remote giữ nguyên.
		self.branch('feat/open', 'a.txt')
		self.git(self.clone, 'branch', 'local/only')
		self.sync()
		self.assertEqual(self.localBranches(), ['feat/open', 'local/only', 'main'])

	def testPruneKeepsDistinctWhitespace(self):
		# git cherry bỏ khoảng trắng khi so bản vá; thụt lề khác vẫn có thể đổi hành vi Python.
		self.git(self.clone, 'switch', '-q', '-c', 'fix/whitespace')
		self.commit(self.clone, 'logic.py', "if True:\n\tprint('x')")
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/whitespace')
		self.git(self.clone, 'switch', '-q', 'main')
		self.commit(self.other, 'logic.py', "if True:\n    print('x')")
		self.git(self.other, 'push', '-q', 'origin', 'main', ':fix/whitespace')
		result = self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['fix/whitespace', 'main'])
		self.assertIn('Giữ lại fix/whitespace', result.stdout)

	def testPruneDoesNotResolveOriginMainAsTag(self):
		self.branch('fix/unmerged', 'a.txt')
		self.git(self.other, 'push', '-q', 'origin', ':fix/unmerged')
		self.git(self.clone, 'tag', 'origin/main', 'fix/unmerged')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['fix/unmerged', 'main'])

	def testPruneHandlesTagWithSameNameAsBranch(self):
		self.branch('fix/squashed', 'a.txt')
		self.mergeOnRemote('fix/squashed', squash=True)
		self.git(self.clone, 'tag', 'fix/squashed', 'main')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['main'])
		self.assertEqual(
			self.git(self.clone, 'tag', '--list', 'fix/squashed').strip(), 'fix/squashed'
		)

	def testPruneDoesNotIgnoreSubmoduleChanges(self):
		# gitlink được tạo trực tiếp trong index để không phụ thuộc mạng hay git submodule của máy.
		moduleCommit = self.git(self.clone, 'rev-parse', 'HEAD').strip()
		self.git(self.clone, 'switch', '-q', '-c', 'fix/submodule')
		self.git(
			self.clone, 'update-index', '--add', '--cacheinfo', f'160000,{moduleCommit},vendor'
		)
		self.git(self.clone, 'commit', '-qm', 'thêm submodule')
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/submodule')
		self.git(self.clone, 'switch', '-q', 'main')
		self.git(self.clone, 'config', 'diff.ignoreSubmodules', 'all')
		self.git(self.other, 'push', '-q', 'origin', ':fix/submodule')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['fix/submodule', 'main'])

	def testPruneKeepsDistinctStringWhitespace(self):
		self.git(self.clone, 'switch', '-q', '-c', 'fix/string_space')
		self.commit(self.clone, 'logic.py', "print('a b')")
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/string_space')
		self.git(self.clone, 'switch', '-q', 'main')
		self.commit(self.other, 'logic.py', "print('ab')")
		self.git(self.other, 'push', '-q', 'origin', 'main', ':fix/string_space')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['fix/string_space', 'main'])

	def testPruneReportsGitFailureAndContinuesOtherBranches(self):
		self.branch('fix/broken', 'a.txt')
		self.branch('fix/squashed', 'b.txt')
		self.mergeOnRemote('fix/broken', squash=True)
		self.mergeOnRemote('fix/squashed', squash=True)
		tip = self.git(self.clone, 'rev-parse', 'fix/broken').strip()
		result = self.attempt(PRUNE, environment=self.gitFailureEnvironment(f'{tip}^{{commit}}'))
		self.assertEqual(result.returncode, 1, result.stderr)
		self.assertIn('Giữ lại fix/broken: lỗi đối chiếu lịch sử', result.stderr)
		self.assertEqual(self.localBranches(), ['fix/broken', 'main'])

	def testPruneStopsWhenFetchFails(self):
		self.branch('fix/squashed', 'a.txt')
		self.mergeOnRemote('fix/squashed', squash=True)
		result = self.attempt(PRUNE, environment=self.gitFailureEnvironment('fetch'))
		self.assertEqual(result.returncode, 1, result.stderr)
		self.assertIn('Không tải được từ origin', result.stderr)
		self.assertEqual(self.localBranches(), ['fix/squashed', 'main'])

	def testPruneKeepsDifferentBinaryContent(self):
		self.git(self.clone, 'switch', '-q', '-c', 'fix/binary')
		(self.clone / 'data.bin').write_bytes(b'\0local\xff\n')
		self.git(self.clone, 'add', 'data.bin')
		self.git(self.clone, 'commit', '-qm', 'thêm dữ liệu nhị phân local')
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/binary')
		self.git(self.clone, 'switch', '-q', 'main')
		(self.other / 'data.bin').write_bytes(b'\0main\xff\n')
		self.git(self.other, 'add', 'data.bin')
		self.git(self.other, 'commit', '-qm', 'thêm dữ liệu nhị phân main')
		self.git(self.other, 'push', '-q', 'origin', 'main', ':fix/binary')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['fix/binary', 'main'])

	def testPruneRecognizesSquashedBinaryContent(self):
		self.git(self.clone, 'switch', '-q', '-c', 'fix/binary')
		(self.clone / 'data.bin').write_bytes(b'\0local\xff\n')
		self.git(self.clone, 'add', 'data.bin')
		self.git(self.clone, 'commit', '-qm', 'thêm dữ liệu nhị phân')
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/binary')
		self.git(self.clone, 'switch', '-q', 'main')
		self.mergeOnRemote('fix/binary', squash=True)
		self.commit(self.other, 'later.txt', 'sau hợp nhất')
		self.git(self.other, 'push', '-q', 'origin', 'main')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['main'])

	def testPruneKeepsUnmergedExecutableBit(self):
		self.git(self.clone, 'switch', '-q', '-c', 'fix/executable')
		path = self.clone / 'base.txt'
		path.chmod(path.stat().st_mode | 0o111)
		self.git(self.clone, 'update-index', '--chmod=+x', 'base.txt')
		self.git(self.clone, 'commit', '-qm', 'đổi quyền thực thi')
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/executable')
		self.git(self.clone, 'switch', '-q', 'main')
		self.git(self.other, 'push', '-q', 'origin', ':fix/executable')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['fix/executable', 'main'])

	def testPruneKeepsOriginalHistoryDespiteReplaceRefs(self):
		self.branch('fix/original', 'a.txt')
		self.git(self.other, 'push', '-q', 'origin', ':fix/original')
		self.git(self.clone, 'replace', 'fix/original', 'main')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['fix/original', 'main'])

	def testPruneFromSubdirectoryIncludesAllPaths(self):
		self.branch('fix/outside', 'a.txt')
		self.git(self.other, 'push', '-q', 'origin', ':fix/outside')
		folder = self.clone / 'nested'
		folder.mkdir()
		self.git(self.clone, 'config', 'diff.relative', 'true')
		subprocess.run(
			['bash', str(PRUNE)], cwd=folder, env=self.environment, capture_output=True, check=True
		)
		self.assertEqual(self.localBranches(), ['fix/outside', 'main'])

	def testPruneKeepsChangesAtDifferentRepeatedLines(self):
		self.commit(self.clone, 'repeated.txt', 'x\nx')
		self.git(self.clone, 'push', '-q', 'origin', 'main')
		self.git(self.other, 'pull', '-q')
		self.git(self.clone, 'switch', '-q', '-c', 'fix/first_line')
		self.commit(self.clone, 'repeated.txt', 'y\nx')
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/first_line')
		self.git(self.clone, 'switch', '-q', 'main')
		self.commit(self.other, 'repeated.txt', 'x\ny')
		self.git(self.other, 'push', '-q', 'origin', 'main', ':fix/first_line')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['fix/first_line', 'main'])

	def testPruneKeepsChangesAtDifferentRepeatedBlocks(self):
		block = '\n'.join(['a'] * 10)
		original = f'{block}\nseparator\n{block}'
		self.commit(self.clone, 'repeated.txt', original)
		self.git(self.clone, 'push', '-q', 'origin', 'main')
		self.git(self.other, 'pull', '-q')
		lines = original.splitlines()
		self.git(self.clone, 'switch', '-q', '-c', 'fix/first_block')
		lines[5] = 'changed'
		self.commit(self.clone, 'repeated.txt', '\n'.join(lines))
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/first_block')
		self.git(self.clone, 'switch', '-q', 'main')
		lines[5], lines[16] = 'a', 'changed'
		self.commit(self.other, 'repeated.txt', '\n'.join(lines))
		self.git(self.other, 'push', '-q', 'origin', 'main', ':fix/first_block')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['fix/first_block', 'main'])

	def testPruneKeepsBranchUpdatedDuringVerification(self):
		self.branch('fix/racing', 'a.txt')
		before = self.git(self.clone, 'rev-parse', 'fix/racing').strip()
		self.mergeOnRemote('fix/racing', squash=True)
		self.commit(self.other, 'post.txt', 'sau hợp nhất')
		self.git(self.other, 'push', '-q', 'origin', 'main')
		self.git(self.clone, 'switch', '-q', 'fix/racing')
		self.commit(self.clone, 'later.txt', 'chưa hợp nhất')
		after = self.git(self.clone, 'rev-parse', 'HEAD').strip()
		self.git(self.clone, 'switch', '-q', 'main')
		self.git(self.clone, 'update-ref', 'refs/heads/fix/racing', before)
		folder = Path(self.tmp.name) / 'bin'
		folder.mkdir()
		realGit = shutil.which('git')
		wrapper = folder / 'git'
		wrapper.write_text(
			'#!/usr/bin/env python3\nimport os\nimport subprocess\nimport sys\n'
			'if "write-tree" in sys.argv[1:]:\n'
			f'    subprocess.run([{realGit!r}, "update-ref", "refs/heads/fix/racing", '
			f'{after!r}, {before!r}], check=True)\n'
			f'os.execv({realGit!r}, ["git", *sys.argv[1:]])\n',
			encoding='utf-8',
		)
		wrapper.chmod(0o755)
		result = self.attempt(
			PRUNE,
			environment=dict(self.environment, PATH=f'{folder}{os.pathsep}{os.environ["PATH"]}'),
		)
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertEqual(self.localBranches(), ['fix/racing', 'main'])
		self.assertEqual(self.git(self.clone, 'rev-parse', 'fix/racing').strip(), after)
		self.assertIn('Giữ lại fix/racing: branch đã thay đổi trong lúc đối chiếu', result.stdout)

	def testPruneReportsUnreadableUpstream(self):
		self.branch('fix/squashed', 'a.txt')
		self.mergeOnRemote('fix/squashed', squash=True)
		result = self.attempt(
			PRUNE, environment=self.gitFailureEnvironment('refs/remotes/origin/fix/squashed')
		)
		self.assertEqual(result.returncode, 1, result.stderr)
		self.assertIn('Giữ lại fix/squashed: không đọc được branch theo dõi', result.stderr)
		self.assertEqual(self.localBranches(), ['fix/squashed', 'main'])

	def testPrunePreservesUserIndexAndWorktree(self):
		self.branch('fix/squashed', 'a.txt')
		self.mergeOnRemote('fix/squashed', squash=True)
		self.commit(self.other, 'later.txt', 'sau hợp nhất')
		self.git(self.other, 'push', '-q', 'origin', 'main')
		draft = self.clone / 'draft.txt'
		draft.write_text('đã stage\n', encoding='utf-8')
		self.git(self.clone, 'add', 'draft.txt')
		draft.write_text('đang sửa thêm\n', encoding='utf-8')
		index = self.clone / '.git' / 'index'
		before = index.read_bytes()
		head = self.git(self.clone, 'rev-parse', 'HEAD')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['main'])
		self.assertEqual(index.read_bytes(), before)
		self.assertEqual(draft.read_text(), 'đang sửa thêm\n')
		self.assertEqual(self.git(self.clone, 'rev-parse', 'HEAD'), head)

	def testPruneRecognizesTextDiffContainingNul(self):
		self.git(self.clone, 'switch', '-q', '-c', 'fix/nul_text')
		(self.clone / 'data.dat').write_bytes(b'a\0b\nlast line')
		self.git(self.clone, 'add', 'data.dat')
		self.git(self.clone, 'commit', '-qm', 'thêm nội dung có NUL')
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/nul_text')
		self.git(self.clone, 'switch', '-q', 'main')
		self.mergeOnRemote('fix/nul_text', squash=True)
		self.commit(self.other, 'later.txt', 'sau hợp nhất')
		self.git(self.other, 'push', '-q', 'origin', 'main')
		info = self.clone / '.git' / 'info'
		info.mkdir(exist_ok=True)
		(info / 'attributes').write_text('data.dat diff\n', encoding='utf-8')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['main'])

	def testPruneKeepsOriginalHistoryDespiteGrafts(self):
		self.branch('fix/original', 'a.txt')
		self.git(self.other, 'push', '-q', 'origin', ':fix/original')
		main = self.git(self.clone, 'rev-parse', 'main').strip()
		branch = self.git(self.clone, 'rev-parse', 'fix/original').strip()
		info = self.clone / '.git' / 'info'
		info.mkdir(exist_ok=True)
		(info / 'grafts').write_text(f'{main} {branch}\n{branch}\n', encoding='utf-8')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['fix/original', 'main'])

	def testPruneHandlesSha256Repository(self):
		folder = Path(self.tmp.name) / 'sha256'
		folder.mkdir()
		probe = subprocess.run(
			['git', 'init', '-q', '--bare', '--object-format=sha256', str(folder / 'probe.git')],
			env=self.environment,
			capture_output=True,
			check=False,
		)
		if probe.returncode != 0:
			self.skipTest('Git hiện tại chưa hỗ trợ repository SHA-256')
		self.prepare(folder)
		self.environment['GIT_DEFAULT_HASH'] = 'sha256'
		self.build(folder)
		self.branch('fix/sha256', 'a.txt', 'b.txt')
		self.mergeOnRemote('fix/sha256', squash=True)
		self.git(self.clone, 'switch', '-q', 'fix/sha256')
		self.commit(self.clone, 'c.txt', 'nhóm sau')
		self.commit(self.clone, 'd.txt', 'nhóm sau')
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/sha256')
		self.mergeOnRemote('fix/sha256', squash=True)
		self.commit(self.other, 'later.txt', 'sau hợp nhất')
		self.git(self.other, 'push', '-q', 'origin', 'main')
		self.sync()
		self.assertEqual(self.localBranches(), ['main'])
		self.assertEqual(len(self.git(self.clone, 'rev-parse', 'HEAD').strip()), 64)

	def testPruneKeepsChangeInSectionDeletedOnMain(self):
		block = '\n'.join(['a'] * 10)
		original = f'FIRST\n{block}\nSECOND\n{block}'
		self.commit(self.clone, 'sections.txt', original)
		self.git(self.clone, 'push', '-q', 'origin', 'main')
		self.git(self.other, 'pull', '-q')
		self.git(self.clone, 'switch', '-q', '-c', 'fix/first_section')
		lines = original.splitlines()
		lines[6] = 'changed'
		self.commit(self.clone, 'sections.txt', '\n'.join(lines))
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/first_section')
		self.git(self.clone, 'switch', '-q', 'main')
		remaining = f'SECOND\n{block}'.splitlines()
		self.commit(self.other, 'sections.txt', '\n'.join(remaining))
		remaining[6] = 'changed'
		self.commit(self.other, 'sections.txt', '\n'.join(remaining))
		self.git(self.other, 'push', '-q', 'origin', 'main', ':fix/first_section')
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['fix/first_section', 'main'])

	def testPruneRecognizesSquashAfterMainInsertsPrefix(self):
		original = '\n'.join(f'line {index}' for index in range(20))
		self.commit(self.clone, 'lines.txt', original)
		self.git(self.clone, 'push', '-q', 'origin', 'main')
		self.git(self.other, 'pull', '-q')
		self.git(self.clone, 'switch', '-q', '-c', 'fix/line')
		changed = original.replace('line 12', 'changed')
		self.commit(self.clone, 'lines.txt', changed)
		self.git(self.clone, 'push', '-q', '-u', 'origin', 'fix/line')
		self.git(self.clone, 'switch', '-q', 'main')
		self.commit(self.other, 'lines.txt', f'prefix\n{original}')
		self.mergeOnRemote('fix/line', squash=True)
		self.runScript(PRUNE)
		self.assertEqual(self.localBranches(), ['main'])

	def testPruneUsesSelectedPythonInterpreter(self):
		self.branch('fix/squashed', 'a.txt')
		self.mergeOnRemote('fix/squashed', squash=True)
		folder = Path(self.tmp.name) / 'interpreter selection'
		folder.mkdir()
		marker = folder / 'called'
		interpreter = folder / 'python'
		interpreter.write_text(
			'#!/usr/bin/env python3\nimport os\nimport sys\nfrom pathlib import Path\n'
			f'Path({str(marker)!r}).write_text("đã chọn", encoding="utf-8")\n'
			f'os.execv({sys.executable!r}, [{sys.executable!r}, *sys.argv[1:]])\n',
			encoding='utf-8',
		)
		interpreter.chmod(0o755)
		result = self.attempt(PRUNE, environment=dict(self.environment, PYTHON=str(interpreter)))
		self.assertEqual(result.returncode, 0, result.stderr)
		self.assertTrue(marker.exists())
		self.assertEqual(self.localBranches(), ['main'])


class BranchMergeCliTest(unittest.TestCase):
	def testOldPythonStopsBeforeReadingGit(self):
		module = loadScript('check-branch-merged')
		output = io.StringIO()
		with (
			mock.patch.object(module.sys, 'version_info', (3, 9, 25)),
			mock.patch.object(module, 'git') as gitMock,
			contextlib.redirect_stderr(output),
		):
			self.assertEqual(module.main(), 2)
		gitMock.assert_not_called()
		self.assertIn('Python ≥ 3.11', output.getvalue())


if __name__ == '__main__':
	unittest.main()
