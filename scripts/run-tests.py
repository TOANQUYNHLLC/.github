"""Chạy test của scripts/ song song trên nhiều tiến trình (make test, nhóm content của make check).

Chạy: python3 scripts/run-tests.py [tên tệp test …]   (ví dụ: python3 scripts/run-tests.py test_release)
Tên tệp được chọn phải có test; tên sai thì báo lỗi trước khi chạy, không bỏ qua một phần yêu cầu.
Test được chia đều theo vòng tròn cho các tiến trình — mỗi tiến trình nhận một phần của test_validate.py (nhóm
chậm nhất), nên cả bộ xong nhanh gần bằng số lõi CPU. Mỗi test tự dùng thư mục tạm riêng nên chạy song song an
toàn. Lỗi nạp tệp test (cú pháp, import) thì chạy lại tuần tự để unittest báo lỗi đầy đủ.
"""

import os
import re
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
# Dùng mọi lõi CPU; mỗi tiến trình tốn thời gian khởi động và chép repository cho test_validate.py nên máy rất
# nhiều lõi cũng không cần quá mức này.
MAX_WORKERS = 16


def testIds(suite):
	"""Mã của mọi test trong suite (đệ quy qua các suite con)."""
	for item in suite:
		if isinstance(item, unittest.TestSuite):
			yield from testIds(item)
		else:
			yield item.id()


def discoverTests(names):
	"""Mã test của các tệp test được chọn (mặc định mọi tệp test_*.py); lỗi nạp tệp thì trả None."""
	loader = unittest.TestLoader()
	suite = loader.discover(str(SCRIPTS), pattern='test_*.py', top_level_dir=str(SCRIPTS))
	ids = list(testIds(suite))
	if loader.errors or any(test.startswith('unittest.loader.') for test in ids):
		return None
	if names:
		ids = [test for test in ids if test.split('.')[0] in names]
	return ids


def runShard(ids):
	"""Chạy một nhóm test trong tiến trình riêng; trả (mã thoát, số test, đầu ra)."""
	result = subprocess.run(
		[sys.executable, '-m', 'unittest', *ids],
		cwd=SCRIPTS,
		capture_output=True,
		text=True,
		check=False,
	)
	output = result.stdout + result.stderr
	ran = re.search(r'^Ran (\d+) tests?', output, re.MULTILINE)
	return result.returncode, int(ran.group(1)) if ran else 0, output


def main():
	names = [name.removesuffix('.py') for name in sys.argv[1:]]
	ids = discoverTests(names)
	if ids is None:
		# Báo lỗi nạp tệp test đúng như unittest.
		command = [
			sys.executable,
			'-m',
			'unittest',
			'discover',
			'-s',
			str(SCRIPTS),
			'-p',
			'test_*.py',
		]
		return subprocess.run(command, check=False).returncode
	if not ids:
		print(f'Không có test nào khớp: {", ".join(names)}')
		return 1
	unknown = sorted(set(names) - {test.split('.')[0] for test in ids})
	if unknown:
		print(f'Không có test nào khớp: {", ".join(unknown)}')
		return 1
	workers = max(1, min(MAX_WORKERS, os.cpu_count() or 1, len(ids)))
	shards = [ids[index::workers] for index in range(workers)]
	started = time.monotonic()
	with ThreadPoolExecutor(max_workers=workers) as pool:
		results = list(pool.map(runShard, shards))
	elapsed = time.monotonic() - started
	failed = [output for code, _, output in results if code != 0]
	for output in failed:
		print(output, end='' if output.endswith('\n') else '\n')
	total = sum(ran for _, ran, _ in results)
	print(f'Ran {total} tests in {elapsed:.1f}s ({workers} tiến trình)')
	print('FAILED' if failed else 'OK')
	return 1 if failed else 0


if __name__ == '__main__':
	sys.exit(main())
