"""Nhập Repository policies từ HTML trang Settings đã lưu, không ghi cài đặt GitHub."""

import argparse
import sys

from orgsetup import repopolicies


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		'policyFiles', nargs='+', help='HTML trang Repository policy đã lưu bằng trình duyệt'
	)
	args = parser.parse_args()
	try:
		repopolicies.importPolicyPages(args.policyFiles)
	except (OSError, ValueError, TypeError, KeyError):
		print(
			'❌ Không nhập được Repository policies: kiểm tra tệp HTML, nguồn tổ chức và dữ liệu policy.',
			file=sys.stderr,
		)
		return 1
	return 0


if __name__ == '__main__':
	sys.exit(main())
