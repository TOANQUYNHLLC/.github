# 0012. KIỂM TRA VIẾT BẰNG PYTHON TRONG SCRIPTS/; TÊN HÀM CAMELCASE TIẾNG ANH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

- Logic kiểm tra nằm rải trong workflow (`run: |` bằng shell, awk, Python nhúng) và lặp lại ở `Makefile`: cùng một kiểm tra viết hai nơi, dễ lệch nhau, và không chạy được tại máy khi GitHub Actions tắt để tiết kiệm chi phí.
- Workflow mẫu (`workflow-templates/`) chép quy ước (loại commit, tiền tố branch) vào từng repository; đổi quy ước phải sửa mọi bản chép.
- Script cùng chức năng bị tách nhỏ (bốn script phát hành, hai script quy ước) và tên hàm theo nhiều kiểu; tên test viết tiếng Việt không dấu khó đọc.

## ✅ QUYẾT ĐỊNH

- Logic kiểm tra và xử lý của workflow viết thành script trong `scripts/`, **ưu tiên Python**; chỉ dùng ngôn ngữ khác khi phù hợp hơn hẳn (hook git, script cài đặt Dev Container bằng shell). Workflow trong `.github/workflows/` chỉ gọi một lệnh — `validate.py` báo lỗi khi có `run: |`.
- `scripts/check.py` là nơi duy nhất khai báo các nhóm kiểm tra (`content`, `format`, `lint`, `conventions`, `audit`): `make check` và từng job của `validate.yml` gọi cùng script.
- Quy ước chung nằm trong một script: `scripts/conventions.py` (loại commit, tiền tố branch), `scripts/release.py` (phát hành từ `CHANGELOG.md`), `scripts/check-markdown-links.py` (liên kết nội bộ, dùng chung với `validate.py`). Workflow mẫu checkout `TOANQUYNHLLC/.github` vào `.org/` rồi gọi các script này; lệnh riêng của từng ngôn ngữ (gofmt, pip, npm) vẫn viết thẳng.
- Tên hàm viết **tiếng Anh, camelCase** (`checkLinks`, `syncSettings`, test `testBrokenLink`) — `validate.py` kiểm tra mọi tệp Python. Hằng số giữ `UPPER_CASE`, lớp giữ `PascalCase`.

## ⚖️ HỆ QUẢ

- Kiểm tra chạy y hệt tại máy và trên GitHub Actions; tắt Actions không làm mất kiểm tra (trừ CodeQL).
- Repository khác dùng workflow mẫu phụ thuộc nhánh chính của `TOANQUYNHLLC/.github` (được Protect Main bảo vệ); đổi quy ước một nơi áp dụng ngay cho mọi repository.
- Tên hàm Python khác PEP 8 (snake_case); ruff với cấu hình chuẩn không kiểm tra tên nên không xung đột.
- ADR cũ nhắc tên hàm cũ (ví dụ `org_push_ruleset()` trong ADR 0010) giữ nguyên làm bản ghi lịch sử; hàm hiện tại là `orgPushRuleset()`.
