"""Phần dùng chung cho các tệp test trong scripts/ (không phải test — unittest chỉ nạp tệp test_*.py)."""

import contextlib
import importlib.util
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Gói scripts/orgsetup/ được nạp như khi chạy scripts/org-setup.py (thư mục scripts/ nằm trong sys.path).
if str(ROOT / 'scripts') not in sys.path:
	sys.path.insert(0, str(ROOT / 'scripts'))


def loadScript(name):
	"""Nạp một script trong scripts/ (tên có dấu gạch ngang nên không import thường được)."""
	spec = importlib.util.spec_from_file_location(
		name.replace('-', '_'), ROOT / 'scripts' / f'{name}.py'
	)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


@contextlib.contextmanager
def silenced():
	"""Ẩn mọi đầu ra, kể cả của tiến trình con (Prettier, ruff… ghi thẳng vào stdout, stderr của tiến trình) —
	test cố ý gây lỗi không làm nhiễu kết quả make check."""
	sys.stdout.flush()
	sys.stderr.flush()
	saved = [os.dup(1), os.dup(2)]
	with open(os.devnull, 'w') as devnull:
		os.dup2(devnull.fileno(), 1)
		os.dup2(devnull.fileno(), 2)
		try:
			with (
				contextlib.redirect_stdout(io.StringIO()),
				contextlib.redirect_stderr(io.StringIO()),
			):
				yield
		finally:
			os.dup2(saved[0], 1)
			os.dup2(saved[1], 2)
			for descriptor in saved:
				os.close(descriptor)
