"""Test tự động cho shell/sync.sh (chuyển branch, git pull) và shell/prune-branches.sh (xóa branch đã hợp nhất mà
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
PRUNE = ROOT / 'shell' / 'prune-branches.sh'


class SyncTest(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		folder = Path(self.tmp.name)
		# Không phụ thuộc cấu hình git của máy (danh tính, ký commit, hook toàn cục).
		# git < 2.32 bỏ qua GIT_CONFIG_GLOBAL và đọc $HOME/.gitconfig: đặt cả hai cùng trỏ cấu hình sạch.
		home = folder / 'home'
		home.mkdir()
		config = home / '.gitconfig'
		config.write_text(
			'[user]\n\tname = test\n\temail = \n'
			'[commit]\n\tgpgsign = false\n[init]\n\tdefaultBranch = main\n',
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
		"""Như make syncmain, make sync BRANCH=…: sync.sh rồi prune-branches.sh; trả đầu ra của cả hai."""
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

	def testMakeTargetsRunSyncThenPrune(self):
		# Mỗi script một việc, Makefile ghép lại: chuyển branch, kéo code rồi mới dọn branch; thiếu BRANCH thì dừng.
		def recipe(*arguments):
			return subprocess.run(
				['make', '--no-print-directory', '-n', *arguments],
				cwd=ROOT,
				capture_output=True,
				text=True,
				check=False,
			)

		self.assertEqual(
			recipe('syncmain').stdout.splitlines(),
			['shell/sync.sh main', 'shell/prune-branches.sh'],
		)
		self.assertEqual(
			recipe('sync', 'BRANCH=feat/x').stdout.splitlines(),
			['shell/sync.sh "$BRANCH"', 'shell/prune-branches.sh'],
		)
		missing = recipe('sync')
		self.assertNotEqual(missing.returncode, 0)
		self.assertIn('Thiếu BRANCH', missing.stderr)

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
		# Máy chưa đặt user.name, user.email (máy mới, CI): commit-tree của bước nhận diện Squash vẫn chạy được.
		# main có thêm commit sau khi hợp nhất để nội dung khác branch — buộc đi qua bước so bằng git cherry.
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


if __name__ == '__main__':
	unittest.main()
