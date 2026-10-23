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
		check=False,
	)
	if result.returncode != 0:
		return ['.']
	# -z: tên tệp nguyên văn; bỏ tệp đã xóa trên đĩa nhưng còn trong index.
	return [
		name
		for name in result.stdout.decode('utf-8').split('\0')
		if name and not name.startswith('vendor/') and os.path.isfile(name)
	]


def runGofmt():
	"""(tệp gofmt sẽ đổi định dạng, lỗi gofmt báo — ví dụ lỗi cú pháp kèm dòng, cột).
	Dấu -- kết thúc tùy chọn để tên tệp bắt đầu bằng gạch ngang được đọc như đường dẫn."""
	files = goFiles()
	if not files:
		return [], ''
	result = subprocess.run(
		['gofmt', '-l', '--', *files], capture_output=True, text=True, check=False
	)
	problem = result.stderr.strip()
	if result.returncode and not problem:
		problem = f'gofmt thoát mã {result.returncode}'
	return [name for name in result.stdout.split('\n') if name], problem


def reportError(message):
	"""Chú thích ::error:: trên GitHub Actions (mã hóa %, xuống dòng thành %25, %0D, %0A để hiện đủ), dòng ❌ khi
	chạy tại máy."""
	if os.environ.get('GITHUB_ACTIONS'):
		message = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
		print(f'::error::{message}')
	else:
		print(f'❌ {message}')


def main():
	try:
		files, problems = runGofmt()
	except OSError as exc:
		reportError(f'Không chạy được gofmt: {exc}')
		return 1
	if problems:
		# Tệp Go không hợp lệ: gofmt không định dạng được — báo đúng lỗi thay vì traceback.
		reportError(f'gofmt không đọc được tệp Go:\n{problems}')
	if files:
		reportError(f'Các tệp chưa chạy gofmt (sửa bằng: gofmt -w .): {", ".join(files)}')
	if problems or files:
		return 1
	print('✅ Mọi tệp Go đã chạy gofmt.')
	return 0


if __name__ == '__main__':
	sys.exit(main())
