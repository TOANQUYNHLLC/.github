"""Nhập HTML trang Settings từ manifest ngoài Git; chỉ ghi nguồn local và dữ liệu riêng."""

import argparse
import json
import sys
from pathlib import Path

from orgsetup import github, websettings


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		'manifest', nargs='?', help='JSON ngoài Git chứa danh sách {url, path} của HTML đã lưu'
	)
	parser.add_argument(
		'--memberships',
		action='store_true',
		help='Đọc danh tính và vai trò qua API, chỉ lưu ngoài Git',
	)
	args = parser.parse_args()
	if not args.manifest and not args.memberships:
		parser.error('Cần manifest hoặc --memberships')
	try:
		if args.manifest:
			if Path(args.manifest).resolve().is_relative_to(github.ROOT.resolve()):
				raise ValueError('Manifest phải nằm ngoài repository')
			entries = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
			if (
				not isinstance(entries, list)
				or not entries
				or any(
					not isinstance(item, dict) or set(item) != {'url', 'path'} for item in entries
				)
			):
				raise ValueError('Manifest không hợp lệ')
			websettings.importSettingsPages(entries)
		if args.memberships:
			websettings.importMemberships()
	except (OSError, ValueError, TypeError, KeyError, RuntimeError):
		print(
			'❌ Không nhập được Settings; kiểm tra manifest, HTML, phạm vi và dữ liệu riêng.',
			file=sys.stderr,
		)
		return 1
	return 0


if __name__ == '__main__':
	sys.exit(main())
