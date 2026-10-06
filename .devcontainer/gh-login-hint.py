"""Nhắc đăng nhập GitHub CLI mỗi khi mở Dev Container (postAttachCommand trong devcontainer.json).

make org-preview (hook sau git pull chạy tự động) đọc cài đặt tổ chức, cần GitHub CLI đăng nhập bằng tài khoản quản
trị TOANQUYNHLLC. GITHUB_TOKEN mà Codespaces cấp sẵn chỉ có quyền trên repository nên không được tính. Kiểm tra
bằng gh auth status như hook sau git pull (gh auth token đọc cả keychain dù chưa đăng nhập); chỉ in nhắc, không
chặn.
"""

import os
import shutil
import subprocess
import sys

HINT = (
	'💡 GitHub CLI chưa đăng nhập (hoặc không kiểm tra được) — make org-preview cần tài khoản quản trị '
	'TOANQUYNHLLC: gh auth login'
)


def storedLogin():
	"""Đã có tài khoản lưu bằng gh auth login; bỏ qua token lấy từ biến môi trường (GH_TOKEN, GITHUB_TOKEN)."""
	if not shutil.which('gh'):
		return False
	environment = {
		key: value for key, value in os.environ.items() if key not in ('GH_TOKEN', 'GITHUB_TOKEN')
	}
	result = subprocess.run(
		['gh', 'auth', 'status'], env=environment, capture_output=True, check=False
	)
	return result.returncode == 0


def main():
	if not storedLogin():
		print(HINT)
	return 0


if __name__ == '__main__':
	sys.exit(main())
