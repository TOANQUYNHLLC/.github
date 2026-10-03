"""Kiểm tra mọi tệp Go đã chạy gofmt.

Chạy: python3 scripts/check-gofmt.py   (trong thư mục gốc của repository Go)
Workflow mẫu go-ci.yml của repository khác gọi script này (checkout TOANQUYNHLLC/.github vào .org/).
"""

import os
import subprocess
import sys


def unformattedFiles():
	"""Tệp Go mà gofmt sẽ đổi định dạng."""
	output = subprocess.run(['gofmt', '-l', '.'], capture_output=True, text=True, check=True).stdout
	return [name for name in output.split('\n') if name]


def main():
	files = unformattedFiles()
	if not files:
		print('✅ Mọi tệp Go đã chạy gofmt.')
		return 0
	prefix = '::error::' if os.environ.get('GITHUB_ACTIONS') else '❌ '
	print(f'{prefix}Các tệp chưa chạy gofmt (sửa bằng: gofmt -w .): {", ".join(files)}')
	return 1


if __name__ == '__main__':
	sys.exit(main())
