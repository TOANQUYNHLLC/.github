"""Áp dụng cấu hình chung của tổ chức lên các repository bằng GitHub CLI (gh).

Chạy: python3 scripts/org-setup.py <lệnh> [--apply] [--repo TÊN] [--discussions]
Mặc định chỉ xem trước, không thay đổi gì; thêm --apply để áp dụng trên GitHub.
Yêu cầu: gh đã đăng nhập bằng tài khoản có quyền quản trị tổ chức.
--repo chỉ nhận tên repository của tổ chức (không kèm owner), dùng với files, settings,
rulesets, team, labels; --discussions chỉ dùng với settings. Tùy chọn sai dừng trước khi gọi API.

Lệnh (nên chạy theo thứ tự):
	import-settings: đọc cài đặt GitHub của tổ chức và mọi repository đọc được (cả archive),
		ghi github-settings.json tại máy; gồm danh mục ruleset, team, nhãn, properties, environments và
		định nghĩa bảo mật, bảo vệ nhánh kiểu cũ, mạng, IP allow list và vai trò team; --complete chỉ bổ sung phần chưa có, giữ cài đặt local đã lưu.
		Không ghi GitHub, không nhận --apply, --repo, --discussions.
	settings-audit: đọc lại mọi nhóm được quản lý, kiểm tra phạm vi repository, dữ liệu chưa nhập và
		khác biệt của bản local; không ghi local hoặc GitHub, chưa đầy đủ thì trả mã lỗi.
	settings-inventory: xem khai báo cài đặt chưa biết và bản thủ công ở local; không cần đăng nhập.
	local-settings: đối chiếu github-settings.json; --apply để áp dụng các mục API được hỗ trợ,
		bao gồm trạng thái Actions, bảo mật, thời gian lưu dữ liệu, fork, tương tác và cấu hình bảo mật.
		Kiểm tra tổ chức trước, đọc repository song song có giới hạn; kế hoạch và ghi theo thứ tự nguồn.
		Đọc mọi phạm vi trước khi ghi, đọc lại sau khi áp dụng; lỗi hoặc mục chưa hoàn tất trả mã lỗi.
		Không nhận --repo, --discussions; --only chọn rõ nhóm cần xử lý, nguồn JSON xác định tài nguyên.
	files: mở Pull Request thêm các tệp dùng chung còn thiếu — .editorconfig, .gitattributes,
		workflow kiểm tra tiêu đề Pull Request, tên branch và gắn nhãn (labeler), CODEOWNERS, dependabot.yml, release.yml
		và tệp định dạng, phiên bản (.nvmrc, .python-version) theo ngôn ngữ repository dùng. Không ghi đè tệp đã có.
		Dữ liệu nhánh hoặc cây Git sai dừng trước khi ghi; thư mục trùng tên manifest không chọn ngôn ngữ;
		repository chưa có commit được bỏ qua; commit lỗi thì xóa branch vừa tạo.
	settings: cài đặt repository (REPOSITORY_SETTINGS: Merge và Squash, tắt Rebase — ADR 00000007, auto-merge,
		Update branch, sign-off khi commit trên web, tắt Wiki và Projects; phần riêng trong
		REPOSITORY_OVERRIDES, topics của .github lấy từ CITATION.cff); Discussions qua GraphQL sau khi
		xác minh ID repository; bật Dependabot alerts, secret
		scanning, push protection, Dependabot security updates, báo cáo lỗ hổng riêng tư, Release bất
		biến (immutable releases); quyền GitHub Actions (giữ nguyên trạng thái bật/tắt);
		--discussions bật thêm GitHub Discussions.
		Cài đặt thiếu trường/sai kiểu không được PATCH; quyền Actions và trạng thái bảo mật chưa đọc
		được được cảnh báo và bỏ qua. Topics lấy từ keywords YAML hợp lệ của CITATION.cff.
		Bỏ archive trước các cập nhật khác khi nguồn yêu cầu; archive sau topics, bảo mật và quyền Actions.
		Đọc lại các trường cài đặt chính sau khi ghi; lỗi đọc, sai kiểu hoặc giá trị chưa khớp dừng lệnh.
		Các bước topics và bảo mật dùng metadata đã xác nhận, gồm chế độ công khai/riêng tư mới.
	rulesets: tạo hoặc cập nhật ruleset Protect Main (rulesets/protect-main.json) và Protect Release
		Tags (rulesets/protect-release-tags.json, ADR 00000006); Protect Main của repository khác chỉ giữ
		kiểm tra bắt buộc có job tương ứng. Bỏ qua repository
		chưa có workflow kiểm tra bắt buộc — hợp nhất Pull Request của lệnh files trước.
		Sau khi ghi, xác minh ID và đọc lại cấu hình trước khi báo thành công.
		Đối chiếu danh sách tập hợp không phụ thuộc thứ tự, giữ nguyên nội dung gửi GitHub.
		Kiểm tra cờ và từng phần tử của quyền hủy phê duyệt, status checks trước lần ghi đầu tiên.
		--apply trả mã lỗi khi thiếu workflow hoặc có thao tác ghi, xác nhận thất bại,
		sau khi thử các ruleset còn lại.
	team: quản lý thông tin trong TEAMS và cấu trúc team cha và team con trong TEAM_PARENTS,
		tạo team cha trước team con,
		kiểm tra cấu hình trước khi gọi API; đọc lại thông tin và quan hệ sau khi tạo hoặc sửa.
		Team có quyền None giữ nguyên thành viên và quyền repository;
		các team có quyền cấu hình được thêm người quản trị và cấp quyền trên mọi repository
		(không hạ quyền đã cao hơn); đã đủ thì báo đã đúng.
		Lời mời đang chờ, dữ liệu sai hoặc quyền tùy chỉnh chưa xếp hạng được dừng trước khi ghi;
		lời mời mới được báo chờ chấp nhận cho đến khi GitHub xác nhận maintainer active.
		Sau mỗi lần cấp quyền repository, đọc lại và yêu cầu quyền bằng hoặc cao hơn nguồn;
		lỗi xác nhận dừng lệnh. Lời mời mới pending trả mã lỗi sau khi xử lý các team còn lại.
	labels: tạo hoặc cập nhật màu, mô tả theo labels.yml (chỉ nhãn khác), đổi tên nhãn chỉ khác chữ hoa/thường;
		không xóa nhãn riêng của repository.
	org-settings: cài đặt tổ chức (ORG_SETTINGS) và quyền GitHub Actions cấp tổ chức; mục chỉ đổi được
		trên web (ORG_WEB_ONLY_SETTINGS) thì chỉ so và báo.
		Đọc lại các trường ORG_SETTINGS sau khi ghi và dừng khi chưa xác nhận đúng nguồn.
	org-rulesets: tạo hoặc cập nhật ruleset cấp tổ chức Organization Protect Main, Organization Protect
		Release Tags và Organization Protect Pushes (ADR 00000005) (rulesets/organization-*.json) cho mọi
		repository; cần token có quyền admin:org
		(gh auth refresh -h github.com -s admin:org) và gói GitHub Team trở lên. Gói Free: REST API
		trả HTTP 403 nên chỉ so tệp với ruleset trên web (đọc qua GraphQL).
		Lỗi đọc GraphQL làm lệnh đối chiếu và preview trả mã lỗi.
		Sau khi ghi, xác minh ID và đọc lại cấu hình trước khi báo thành công.
		--apply trả mã lỗi khi REST bị chặn hoặc có thao tác ghi, xác nhận thất bại;
		tạo, sửa trên web cũng cần gói hỗ trợ.
	preview: xem trước mọi lệnh trên cùng lúc, in kết quả theo thứ tự trên (make org-preview).
"""

import argparse
import contextlib
import io
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

# Gói orgsetup cần Python ≥ 3.11 (tomllib) — chặn sớm, báo rõ khi chạy bằng python3 cũ của hệ thống.
try:
	import tomllib  # noqa: F401
except ModuleNotFoundError:
	sys.exit(
		f'Cần Python ≥ 3.11 (đang dùng {sys.version.split()[0]}) — chạy mise install, mở terminal có mise.'
	)

from orgsetup import configuration, files, github, labels, rulesets, settings, teams

REPOSITORY_COMMANDS = ('files', 'settings', 'rulesets', 'team', 'labels')
COMMANDS = (*REPOSITORY_COMMANDS, 'org-rulesets', 'org-settings')
PREVIEW_NOTE = 'Chế độ xem trước — chạy lại với --apply để áp dụng.'


def runCommand(command, repos, apply, discussions=False):
	"""Chạy một lệnh; lệnh org-* áp dụng cho cả tổ chức, không dùng danh sách repository."""
	if command == 'files':
		files.syncFiles(repos, apply)
	elif command == 'settings':
		settings.syncSettings(repos, apply, discussions)
	elif command == 'rulesets':
		rulesets.syncRulesets(repos, apply)
	elif command == 'team':
		teams.syncTeams(repos, apply)
	elif command == 'labels':
		labels.syncLabels(repos, apply)
	elif command == 'org-rulesets':
		rulesets.syncOrgRulesets(apply)
	else:
		settings.syncOrgSettings(apply)


class ThreadOutput:
	"""stdout, stderr riêng cho từng luồng: preview chạy mọi lệnh song song trong một tiến trình mà đầu ra của
	mỗi lệnh vẫn liền khối. Luồng chưa gán bộ đệm (local.buffer) thì ghi thẳng ra đích gốc."""

	def __init__(self, fallback):
		self.fallback = fallback
		self.local = threading.local()

	def target(self):
		return getattr(self.local, 'buffer', self.fallback)

	def write(self, text):
		return self.target().write(text)

	def flush(self):
		self.target().flush()


def previewAll(repos):
	"""Xem trước mọi lệnh song song — mỗi lệnh chờ GitHub vài lần, tuần tự thì vài chục giây; in kết quả liền
	khối theo thứ tự COMMANDS. Đăng nhập và danh sách repository đã kiểm tra một lần cho mọi lệnh."""
	out, err = ThreadOutput(sys.stdout), ThreadOutput(sys.stderr)

	def preview(command):
		buffer = io.StringIO()
		out.local.buffer = err.local.buffer = buffer
		try:
			runCommand(command, [] if command.startswith('org-') else repos, apply=False)
			return True, buffer.getvalue()
		except (RuntimeError, OSError, KeyError, ValueError, TypeError) as exc:
			print(f'❌ {exc}')
			return False, buffer.getvalue()
		finally:
			del out.local.buffer, err.local.buffer

	with (
		contextlib.redirect_stdout(out),
		contextlib.redirect_stderr(err),
		ThreadPoolExecutor(max_workers=len(COMMANDS)) as pool,
	):
		results = list(pool.map(preview, COMMANDS))
	failed = [command for command, (passed, _) in zip(COMMANDS, results, strict=True) if not passed]
	for command, (_, output) in zip(COMMANDS, results, strict=True):
		print(f'##### {command}')
		print(output, end='')
	print(PREVIEW_NOTE)
	if failed:
		print(f'❌ Lệnh lỗi: {", ".join(failed)}', file=sys.stderr)
	return 1 if failed else 0


def signedIn():
	try:
		github.gh('auth', 'status')
		return True
	except (RuntimeError, FileNotFoundError):
		return False


def main():
	parser = argparse.ArgumentParser(
		description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
	)
	parser.add_argument(
		'command',
		choices=(
			*COMMANDS,
			'preview',
			'import-settings',
			'local-settings',
			'settings-audit',
			'settings-inventory',
		),
	)
	parser.add_argument('--apply', action='store_true', help='áp dụng thay đổi trên GitHub')
	parser.add_argument(
		'--only',
		action='append',
		choices=sorted(configuration.SETTING_GROUPS),
		help='local-settings: chỉ xử lý nhóm được chọn; lặp tùy chọn để chọn nhiều nhóm',
	)
	parser.add_argument(
		'--complete',
		action='store_true',
		help='import-settings: bổ sung mục chưa có, giữ giá trị local đã lưu',
	)
	parser.add_argument('--repo', help='chỉ xử lý một repository')
	parser.add_argument(
		'--discussions', action='store_true', help='settings: bật GitHub Discussions'
	)
	args = parser.parse_args()
	if args.only is not None and args.command != 'local-settings':
		parser.error('--only chỉ dùng với local-settings')
	if args.repo is not None:
		if args.command not in REPOSITORY_COMMANDS:
			parser.error('--repo chỉ dùng với files, settings, rulesets, team, labels')
		if not re.fullmatch(r'[A-Za-z0-9_.-]+', args.repo) or args.repo in ('.', '..'):
			parser.error('--repo cần tên repository hợp lệ, không trống và không kèm owner')
	if args.discussions and args.command != 'settings':
		parser.error('--discussions chỉ dùng với settings')
	if args.complete and args.command != 'import-settings':
		parser.error('--complete chỉ dùng với import-settings')
	if args.apply and args.command in (
		'preview',
		'import-settings',
		'settings-audit',
		'settings-inventory',
	):
		parser.error(f'{args.command} không nhận --apply')
	if args.command == 'settings-inventory':
		try:
			return configuration.inventory.showInventory(configuration.readConfig())
		except (OSError, ValueError, TypeError) as exc:
			print(f'❌ {exc}', file=sys.stderr)
			return 1

	def repositories():
		# Giữ lỗi đọc để main báo sau khi xác minh đăng nhập; không gọi lại một request đã thất bại.
		if args.command.startswith('org-') or args.command in (
			'import-settings',
			'local-settings',
			'settings-audit',
		):
			return []
		try:
			return github.listRepos(args.repo)
		except (RuntimeError, OSError) as exc:
			return exc

	# Kiểm tra đăng nhập và lấy danh sách repository cùng lúc — mỗi việc chờ GitHub gần một giây.
	with ThreadPoolExecutor(max_workers=2) as pool:
		login, listing = pool.submit(signedIn), pool.submit(repositories)
		if not login.result():
			sys.exit('Cần GitHub CLI đã đăng nhập: https://cli.github.com rồi chạy gh auth login')
		repos = listing.result()
	if isinstance(repos, Exception):
		print(f'❌ {repos}', file=sys.stderr)
		return 1
	try:
		if args.command == 'import-settings':
			return (
				configuration.importSettings(complete=True)
				if args.complete
				else configuration.importSettings()
			)
		if args.command == 'settings-audit':
			return configuration.auditSettings()
		if args.command == 'local-settings':
			return (
				configuration.syncConfiguredSettings(args.apply, only=args.only)
				if args.only is not None
				else configuration.syncConfiguredSettings(args.apply)
			)
		if args.command == 'preview':
			return previewAll(repos)
		runCommand(args.command, repos, args.apply, args.discussions)
	except (RuntimeError, OSError, KeyError, ValueError, TypeError) as exc:
		print(f'❌ {exc}', file=sys.stderr)
		return 1
	if not args.apply:
		print(PREVIEW_NOTE)
	return 0


if __name__ == '__main__':
	sys.exit(main())
