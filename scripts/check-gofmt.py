"""Kiểm tra mọi tệp Go đã chạy gofmt.

Chạy: python3 scripts/check-gofmt.py   (trong thư mục gốc của repository Go)
Workflow mẫu go-ci.yml của repository khác gọi script này (checkout TOANQUYNHLLC/.github vào .org/).
"""

import os
import subprocess
import sys


def goFiles():
	"""Tệp Go git quản lý, trừ vendor/ (mã của bên thứ ba); ngoài git thì để gofmt tự quét thư mục."""
	result = subprocess.run(
		['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '*.go'],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode != 0:
		return ['.']
	# -z: tên tệp nguyên văn; bỏ tệp đã xóa trên đĩa nhưng còn trong index.
	return [
		name
		for name in result.stdout.split('\0')
		if name and not name.startswith('vendor/') and os.path.isfile(name)
	]


def unformattedFiles():
	"""Tệp Go mà gofmt sẽ đổi định dạng."""
	files = goFiles()
	if not files:
		return []
	output = subprocess.run(
		['gofmt', '-l', *files], capture_output=True, text=True, check=True
	).stdout
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
