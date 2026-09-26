"""In nội dung phát hành của một phiên bản, lấy từ CHANGELOG.md.

Chạy: python3 scripts/release-notes.py v2026.09.Stable
Dùng trong workflow release.yml để tạo GitHub Release khi gắn tag.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def release_notes(changelog, version):
    """Trả về phần nội dung dưới tiêu đề ## [version] cho tới tiêu đề phiên bản kế tiếp."""
    pattern = re.compile(r'^## \[(?P<name>[^\]]+)\].*$', re.MULTILINE)
    headings = list(pattern.finditer(changelog))
    for index, heading in enumerate(headings):
        if heading.group('name') != version:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(changelog)
        body = changelog[heading.end() : end]
        body = re.split(r'^<p align="center">', body, flags=re.MULTILINE)[0]
        body = re.sub(r'\n---\s*$', '', body.strip())
        return body.strip()
    return None


def main():
    if len(sys.argv) != 2 or not sys.argv[1]:
        print('Cách dùng: python3 scripts/release-notes.py <tag>', file=sys.stderr)
        return 2
    version = sys.argv[1]
    notes = release_notes((ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'), version)
    if not notes:
        print(
            f'CHANGELOG.md chưa có mục ## [{version}] — hãy chuyển nội dung '
            'CHƯA PHÁT HÀNH thành phiên bản này trước khi gắn tag.',
            file=sys.stderr,
        )
        return 1
    print(notes)
    return 0


if __name__ == '__main__':
    sys.exit(main())
