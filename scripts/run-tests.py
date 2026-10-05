"""Chạy test của scripts/ song song trên nhiều tiến trình (make test, nhóm content của make check).

Chạy: python3 scripts/run-tests.py [tên tệp test …]   (ví dụ: python3 scripts/run-tests.py test_release)
Chỉ nạp các tệp được chọn; tên sai thì báo lỗi trước khi chạy, không bỏ qua một phần yêu cầu.
Test được chia theo thời gian chạy đã đo, hoặc vòng tròn khi chưa có lịch sử. Lịch sử chỉ quyết định phân
nhóm, không bỏ test. Số tiến trình theo CPU khả dụng, affinity và quota cgroup v2. Lỗi nạp tệp test thì chạy
lại tuần tự để unittest báo lỗi đầy đủ.
"""

import contextlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
# Dùng mọi lõi CPU; mỗi tiến trình tốn thời gian khởi động và chép repository cho test_validate.py nên máy rất
# nhiều lõi cũng không cần quá mức này.
MAX_WORKERS = 16
TIMINGS_FILE = SCRIPTS.parent / '.cache' / 'local-checks' / 'test-times.json'


def availableCpus():
	"""Giới hạn CPU thực sự của tiến trình; nền tảng không hỗ trợ dùng os.cpu_count()."""
	count = getattr(os, 'process_cpu_count', os.cpu_count)() or 1
	if hasattr(os, 'sched_getaffinity'):
		with contextlib.suppress(OSError):
			count = min(count, len(os.sched_getaffinity(0)))
	try:
		quota, period = Path('/sys/fs/cgroup/cpu.max').read_text().split()
		if quota != 'max':
			count = min(count, max(1, math.ceil(int(quota) / int(period))))
	except (OSError, ValueError, ZeroDivisionError):
		pass
	return max(1, count)


def readTimings():
	"""Lịch sử hỏng/thiếu không ảnh hưởng việc chạy đầy đủ tests."""
	try:
		data = json.loads(TIMINGS_FILE.read_text(encoding='utf-8'))
		if not isinstance(data, dict):
			return {}
		return {
			name: value
			for name, value in data.items()
			if isinstance(value, (float, int))
			and not isinstance(value, bool)
			and 0 < value <= 3600
			and math.isfinite(value)
		}
	except (OSError, ValueError):
		return {}


def splitTests(ids, workers, timings):
	"""Mọi test xuất hiện đúng một lần; ưu tiên test chậm để cân bằng tổng thời gian của các nhóm."""
	if not timings:
		return [ids[index::workers] for index in range(workers)]
	shards, totals = [[] for _ in range(workers)], [0.0] * workers
	default = sum(timings.values()) / len(timings)
	for test in sorted(ids, key=lambda test: -timings.get(test, default)):
		index = min(range(workers), key=lambda index: totals[index])
		shards[index].append(test)
		totals[index] += timings.get(test, default)
	# unittest gọi lại fixture lớp khi thứ tự xen kẽ; giữ các test cùng lớp liền nhau.
	return [sorted(shard) for shard in shards if shard]


def writeTimings(ids, timings):
	"""Ghi cache nguyên tử; lỗi ghi giữ bản cũ và dọn tệp tạm, không ảnh hưởng kết quả tests."""
	temporary = None
	try:
		TIMINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
		with tempfile.NamedTemporaryFile(
			mode='w', encoding='utf-8', dir=TIMINGS_FILE.parent, delete=False
		) as file:
			temporary = Path(file.name)
			json.dump({test: timings[test] for test in ids if test in timings}, file)
		os.replace(temporary, TIMINGS_FILE)
	except OSError:
		pass
	finally:
		if temporary is not None:
			with contextlib.suppress(OSError):
				temporary.unlink(missing_ok=True)


def runWorker(ids, timingPath):
	"""Đo từng test bằng unittest; thất bại vẫn trả mã lỗi, thời gian không quyết định kết quả."""

	class TimedResult(unittest.TextTestResult):
		def startTest(self, test):
			super().startTest(test)
			self.started = time.monotonic()

		def stopTest(self, test):
			timings[test.id()] = max(time.monotonic() - self.started, 0.000001)
			super().stopTest(test)

	timings = {}
	suite = unittest.defaultTestLoader.loadTestsFromNames(ids)
	result = unittest.TextTestRunner(resultclass=TimedResult).run(suite)
	with contextlib.suppress(OSError):
		Path(timingPath).write_text(json.dumps(timings), encoding='utf-8')
	return 0 if result.wasSuccessful() else 1


def timedShard(ids):
	with tempfile.TemporaryDirectory() as folder:
		path = Path(folder) / 'times.json'
		result = subprocess.run(
			[sys.executable, str(SCRIPTS / 'run-tests.py'), '--worker', str(path), *ids],
			cwd=SCRIPTS,
			capture_output=True,
			text=True,
			check=False,
		)
		output = result.stdout + result.stderr
		ran = re.search(r'^Ran (\d+) tests?', output, re.MULTILINE)
		try:
			timings = json.loads(path.read_text(encoding='utf-8'))
		except (OSError, ValueError):
			timings = {}
		return result.returncode, int(ran.group(1)) if ran else 0, output, timings


def testIds(suite):
	"""Mã của mọi test trong suite (đệ quy qua các suite con)."""
	for item in suite:
		if isinstance(item, unittest.TestSuite):
			yield from testIds(item)
		else:
			yield item.id()


def discoverTests(names):
	"""(mã test, tên không có test nào) của các tệp test được chọn (mặc định mọi tệp test_*.py). Có tên sai thì
	trả ngay danh sách tên đó, không chạy phần còn lại; lỗi nạp tệp thì mã test là None."""
	loader = unittest.TestLoader()
	selected = list(dict.fromkeys(names)) if names else [None]
	ids, missing = [], []
	for name in selected:
		pattern = f'{name}.py' if name else 'test_*.py'
		suite = loader.discover(str(SCRIPTS), pattern=pattern, top_level_dir=str(SCRIPTS))
		found = list(testIds(suite))
		if name and not found:
			missing.append(name)
		ids.extend(found)
	if missing:
		return [], missing
	if loader.errors or any(test.startswith('unittest.loader.') for test in ids):
		return None, []
	if names:
		ids = [test for test in ids if test.split('.')[0] in names]
	return ids, sorted(set(names) - {test.split('.')[0] for test in ids})


def runShard(ids):
	"""Chạy một nhóm test trong tiến trình riêng; trả (mã thoát, số test, đầu ra)."""
	return timedShard(ids)[:3]


def main():
	if len(sys.argv) > 2 and sys.argv[1] == '--worker':
		return runWorker(sys.argv[3:], sys.argv[2])
	names = [name.removesuffix('.py') for name in sys.argv[1:]]
	ids, missing = discoverTests(names)
	# Chỉ nêu tên sai, không nêu tên đúng đi kèm.
	if missing:
		print(f'Không có test nào khớp: {", ".join(missing)}')
		return 1
	if ids is None:
		# Báo lỗi nạp đúng phạm vi đã chọn; chạy mọi tệp chỉ khi không truyền tên.
		command = [sys.executable, '-m', 'unittest']
		command += names if names else ['discover', '-s', str(SCRIPTS), '-p', 'test_*.py']
		return subprocess.run(command, cwd=SCRIPTS, check=False).returncode
	if not ids:
		print('Không có tệp test_*.py nào.')
		return 1
	workers = max(1, min(MAX_WORKERS, availableCpus(), len(ids)))
	timings = readTimings()
	shards = splitTests(ids, workers, timings)
	started = time.monotonic()
	with ThreadPoolExecutor(max_workers=workers) as pool:
		results = list(pool.map(timedShard, shards))
	elapsed = time.monotonic() - started
	failed = [output for code, _, output, _ in results if code != 0]
	for output in failed:
		print(output, end='' if output.endswith('\n') else '\n')
	total = sum(ran for _, ran, _, _ in results)
	for _, _, _, measured in results:
		timings.update(measured)
	writeTimings(ids, timings)
	print(f'Ran {total} tests in {elapsed:.1f}s ({workers} tiến trình)')
	print('FAILED' if failed else 'OK')
	return 1 if failed else 0


if __name__ == '__main__':
	sys.exit(main())
