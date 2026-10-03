"""Phần dùng chung cho các tệp test trong scripts/ (không phải test — unittest chỉ nạp tệp test_*.py)."""

import importlib.util
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
