"""Áp dụng cấu hình chung của tổ chức lên các repository bằng GitHub CLI (gh).

Chạy: python3 scripts/org-setup.py <lệnh> [--apply] [--repo TÊN] [--discussions]
Mặc định chỉ xem trước, không thay đổi gì; thêm --apply để áp dụng trên GitHub.
Yêu cầu: gh đã đăng nhập bằng tài khoản có quyền quản trị tổ chức.

Lệnh (nên chạy theo thứ tự):
	files: mở Pull Request thêm các tệp dùng chung còn thiếu — .editorconfig, .gitattributes,
		workflow kiểm tra tiêu đề Pull Request, tên branch và gắn nhãn (labeler), CODEOWNERS, dependabot.yml, release.yml
		và tệp định dạng theo ngôn ngữ repository dùng. Không ghi đè tệp đã có.
	settings: cài đặt repository (REPOSITORY_SETTINGS: Merge và Squash, tắt Rebase — ADR 0006, auto-merge,
		Update branch, sign-off khi commit trên web, tắt Wiki và Projects; phần riêng trong
		REPOSITORY_OVERRIDES, topics của .github lấy từ CITATION.cff); bật Dependabot alerts, secret
		scanning, push protection, Dependabot security updates, báo cáo lỗ hổng riêng tư, Release bất
		biến (immutable releases); quyền GitHub Actions (giữ nguyên trạng thái bật/tắt);
		--discussions bật thêm GitHub Discussions.
	rulesets: tạo hoặc cập nhật ruleset Protect Main (rulesets/protect-main.json) và Protect Release
		Tags (rulesets/protect-release-tags.json, ADR 0005); Protect Main của repository khác chỉ giữ
		kiểm tra bắt buộc có job tương ứng. Bỏ qua repository
		chưa có workflow kiểm tra bắt buộc — hợp nhất Pull Request của lệnh files trước.
	team: tạo các team trong TEAMS (sửa tên, mô tả, chế độ hiển thị khác web), thêm người quản trị và cấp
		quyền của từng team trên mọi repository (không hạ quyền đã cao hơn); đã đủ thì báo đã đúng.
	labels: tạo hoặc cập nhật màu, mô tả theo labels.yml (chỉ nhãn khác); không xóa nhãn riêng của repository.
	org-settings: cài đặt tổ chức (ORG_SETTINGS) và quyền GitHub Actions cấp tổ chức; mục chỉ đổi được
		trên web (ORG_WEB_ONLY_SETTINGS) thì chỉ so và báo.
	org-rulesets: tạo hoặc cập nhật ruleset cấp tổ chức Protect Main (Organization), Protect Release
		Tags (Organization) và Protect Pushes (Organization, ADR 0007) (rulesets/org-*.json) cho mọi
		repository; cần token có quyền admin:org
		(gh auth refresh -h github.com -s admin:org) và gói GitHub Team trở lên. Gói Free: REST API
		trả HTTP 403 nên chỉ so tệp với ruleset trên web (đọc qua GraphQL) — tạo, sửa bằng import trên web.
	preview: xem trước mọi lệnh trên cùng lúc, in kết quả theo thứ tự trên (make org-preview).
"""

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from orgsetup import files, github, labels, rulesets, settings, teams

COMMANDS = ('files', 'settings', 'rulesets', 'team', 'labels', 'org-rulesets', 'org-settings')


def previewAll():
	"""Xem trước mọi lệnh song song — mỗi lệnh chờ GitHub vài giây, tuần tự thì gần 40 giây; mỗi lệnh chạy
	một tiến trình riêng để kết quả in liền khối, đúng thứ tự COMMANDS."""

	def preview(command):
		return subprocess.run(
			[sys.executable, __file__, command], capture_output=True, text=True, check=False
		)

	with ThreadPoolExecutor(max_workers=len(COMMANDS)) as pool:
		results = list(pool.map(preview, COMMANDS))
	failed = [
		command for command, result in zip(COMMANDS, results, strict=True) if result.returncode
	]
	for command, result in zip(COMMANDS, results, strict=True):
		print(f'##### {command}', flush=True)
		print(result.stdout, end='', flush=True)
		print(result.stderr, end='', file=sys.stderr, flush=True)
	if failed:
		print(f'❌ Lệnh lỗi: {", ".join(failed)}', file=sys.stderr)
	return 1 if failed else 0


def main():
	parser = argparse.ArgumentParser(
		description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
	)
	parser.add_argument(
		'command',
		choices=(*COMMANDS, 'preview'),
	)
	parser.add_argument('--apply', action='store_true', help='áp dụng thay đổi trên GitHub')
	parser.add_argument('--repo', help='chỉ xử lý một repository')
	parser.add_argument(
		'--discussions', action='store_true', help='settings: bật GitHub Discussions'
	)
	args = parser.parse_args()
	if args.command == 'preview':
		if args.apply or args.repo or args.discussions:
			parser.error(
				'preview chỉ xem trước mọi lệnh, không nhận --apply, --repo, --discussions'
			)
		return previewAll()
	try:
		github.gh('auth', 'status')
	except (RuntimeError, FileNotFoundError):
		sys.exit('Cần GitHub CLI đã đăng nhập: https://cli.github.com rồi chạy gh auth login')
	# Lệnh org-* áp dụng cho cả tổ chức, không cần danh sách repository.
	repos = [] if args.command.startswith('org-') else github.listRepos(args.repo)
	if args.command == 'files':
		files.syncFiles(repos, args.apply)
	elif args.command == 'settings':
		settings.syncSettings(repos, args.apply, args.discussions)
	elif args.command == 'rulesets':
		rulesets.syncRulesets(repos, args.apply)
	elif args.command == 'org-rulesets':
		rulesets.syncOrgRulesets(args.apply)
	elif args.command == 'labels':
		labels.syncLabels(repos, args.apply)
	elif args.command == 'org-settings':
		settings.syncOrgSettings(args.apply)
	else:
		teams.syncTeams(repos, args.apply)
	if not args.apply:
		print('Chế độ xem trước — chạy lại với --apply để áp dụng.')
	return 0


if __name__ == '__main__':
	sys.exit(main())
