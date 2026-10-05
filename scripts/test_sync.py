"""Test tự động cho shell/sync.sh (chuyển branch, git pull) và shell/cleanup-main.sh (xóa branch đã hợp nhất mà
remote đã xóa).

Chạy: make test (song song)   hoặc: python3 -m unittest discover -s scripts -p 'test_*.py'
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

# discover (make test) đặt scripts/ vào sys.path; chạy từ thư mục gốc (python3 -m unittest scripts.test_…) thì không.
try:
	from testsupport import ROOT
except ModuleNotFoundError:
	from scripts.testsupport import ROOT

SCRIPT = ROOT / 'shell' / 'sync.sh'
CLEANUP = ROOT / 'shell' / 'cleanup-main.sh'


class SyncMainTest(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		folder = Path(self.tmp.name)
		# Không phụ thuộc cấu hình git của máy (danh tính, ký commit, hook toàn cục).
		config = folder / 'gitconfig'
		config.write_text(
			'[user]\n\tname = test\n\temail = \n'
			'[commit]\n\tgpgsign = false\n[init]\n\tdefaultBranch = main\n',
			encoding='utf-8',
		)
		self.environment = dict(os.environ, GIT_CONFIG_GLOBAL=str(config), GIT_CONFIG_NOSYSTEM='1')
		self.remote, self.clone, self.other = (
			folder / 'remote.git',
			folder / 'clone',
			folder / 'other',
		)
		self.git(folder, 'init', '-q', '--bare', str(self.remote))
		self.git(folder, 'clone', '-q', str(self.remote), str(self.clone))
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

	def localBranches(self):
		return self.git(
			self.clone, 'for-each-ref', '--format=%(refname:short)', 'refs/heads'
		).split()

	def testDeletesSquashedAndMergedBranches(self):
		# Squash đổi SHA nên git branch -d báo "not fully merged"; script nhận ra theo nội dung. Branch hợp nhất
		# bằng Merge là tổ tiên của main.
		self.branch('feat/squashed', 'a.txt', 'b.txt')
		self.branch('fix/merged', 'c.txt')
		self.mergeOnRemote('feat/squashed', squash=True)
		self.mergeOnRemote('fix/merged', squash=False)
		self.git(self.clone, 'switch', '-q', 'feat/squashed')
		self.runScript()
		self.assertEqual(self.localBranches(), ['main'])
		self.assertEqual(self.git(self.clone, 'branch', '--show-current').strip(), 'main')
		self.assertTrue((self.clone / 'a.txt').exists())

	def testKeepsBranchWithUnmergedChanges(self):
		# Branch được squash rồi có thêm commit chưa vào main: remote đã xóa nhưng còn thay đổi — giữ lại.
		self.branch('feat/extra', 'a.txt')
		self.mergeOnRemote('feat/extra', squash=True)
		self.git(self.clone, 'switch', '-q', 'feat/extra')
		self.commit(self.clone, 'later.txt', 'chưa đẩy')
		result = self.runScript()
		self.assertEqual(self.localBranches(), ['feat/extra', 'main'])
		self.assertIn('Giữ lại feat/extra: có thay đổi chưa vào main', result.stdout)

	def testKeepsBranchOpenInWorktree(self):
		# Branch đang mở ở worktree khác: git branch -D từ chối — script báo và chạy tiếp các branch sau.
		self.branch('docs/worktree', 'a.txt')
		self.branch('feat/squashed', 'b.txt')
		self.mergeOnRemote('docs/worktree', squash=True)
		self.mergeOnRemote('feat/squashed', squash=True)
		worktree = Path(self.tmp.name) / 'worktree'
		self.git(self.clone, 'worktree', 'add', '-q', str(worktree), 'docs/worktree')
		result = self.runScript()
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
		self.runScript(SCRIPT, 'feat/other')
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
		result = self.runScript(SCRIPT, 'local/only')
		self.assertIn(
			'Bỏ qua git pull: local/only chưa có branch theo dõi trên origin.', result.stdout
		)
		self.assertEqual(self.git(self.clone, 'branch', '--show-current').strip(), 'local/only')
		self.assertEqual(self.localBranches(), ['local/only', 'main'])

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
		self.assertNotEqual(result.returncode, 0)
		self.assertEqual(self.localBranches(), ['fix/squashed', 'main'])

	def testRefusesUncommittedChanges(self):
		# git switch mang thay đổi chưa commit sang main: script dừng trước khi đổi branch, không xóa gì.
		self.branch('feat/squashed', 'a.txt')
		self.mergeOnRemote('feat/squashed', squash=True)
		self.git(self.clone, 'switch', '-q', 'feat/squashed')
		(self.clone / 'draft.txt').write_text('đang sửa\n', encoding='utf-8')
		result = subprocess.run(
			['bash', str(SCRIPT)],
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

	def testCleanupStaysOnCurrentBranchAndUsesOriginMain(self):
		# cleanup-main.sh không đổi branch, không kéo code: branch hiện tại được giữ (không xóa được), branch khác đã
		# squash vẫn bị xóa dù main cục bộ chưa có commit hợp nhất — so với origin/main vừa tải về.
		self.branch('feat/current', 'a.txt')
		self.branch('fix/squashed', 'b.txt')
		self.mergeOnRemote('feat/current', squash=True)
		self.mergeOnRemote('fix/squashed', squash=True)
		self.git(self.clone, 'switch', '-q', 'feat/current')
		localMain = self.git(self.clone, 'rev-parse', 'main')
		result = self.runScript(CLEANUP)
		self.assertEqual(self.localBranches(), ['feat/current', 'main'])
		self.assertIn('Giữ lại feat/current: đang là branch hiện tại', result.stdout)
		self.assertEqual(self.git(self.clone, 'branch', '--show-current').strip(), 'feat/current')
		self.assertEqual(self.git(self.clone, 'rev-parse', 'main'), localMain)

	def testCleanupKeepsUncommittedWorkInPlace(self):
		# Khác sync.sh, cleanup-main.sh chạy được khi còn thay đổi chưa commit: không đổi branch nên không mang
		# thay đổi đi đâu.
		self.branch('fix/squashed', 'b.txt')
		self.mergeOnRemote('fix/squashed', squash=True)
		self.git(self.clone, 'switch', '-q', '-c', 'feature/wip')
		(self.clone / 'draft.txt').write_text('đang sửa\n', encoding='utf-8')
		self.runScript(CLEANUP)
		self.assertEqual(self.localBranches(), ['feature/wip', 'main'])
		self.assertTrue((self.clone / 'draft.txt').exists())

	def testKeepsBranchWithoutRemoteOrStillOnRemote(self):
		# Chỉ xét branch mà remote đã xóa: branch chưa đẩy và branch còn trên remote giữ nguyên.
		self.branch('feat/open', 'a.txt')
		self.git(self.clone, 'branch', 'local/only')
		self.runScript()
		self.assertEqual(self.localBranches(), ['feat/open', 'local/only', 'main'])


if __name__ == '__main__':
	unittest.main()
