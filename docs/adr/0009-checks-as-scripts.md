# 0009. MỌI KIỂM TRA LÀ SCRIPT TRONG SCRIPTS/, ƯU TIÊN PYTHON, CHẠY ĐƯỢC TẠI MÁY

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Kiểm tra viết thẳng trong workflow (`run: |`, Python nhúng) không chạy được tại máy, không có test, dễ lệch giữa các bản chép — và mất hẳn khi GitHub Actions tắt để tiết kiệm chi phí. Workflow mẫu chép quy ước vào từng repository thì đổi quy ước phải sửa mọi bản chép.

## ✅ QUYẾT ĐỊNH

- Mọi kiểm tra viết thành script trong `scripts/`, mặc định bằng **Python**. Được dùng ngôn ngữ khác khi ngôn ngữ đó xử lý việc đó tốt hơn, với dòng `Không viết bằng Python vì: <lý do>` trong 10 dòng đầu tệp; `validate.py` báo lỗi khi thiếu (mọi tệp không phải Python trong `scripts/`, mọi tệp `.sh`, `.bash`, `.zsh`, `.rb`, `.pl`, `.ps1` ở bất kỳ đâu).
- **Không** viết kiểm tra trong `.yml`, `.yaml` (cả `.github/workflows/` và `workflow-templates/`): mỗi bước gọi đúng một lệnh — cấm `run: |`, `run: >`, `shell: python` và mã nhúng `python -c`, `node -e`, `bash -c`; điều kiện dùng `if:` của GitHub Actions.
- `scripts/check.py` là nơi duy nhất khai báo các nhóm kiểm tra (`content`, `format`, `lint`, `conventions`, `audit`): `make check` và từng job của `validate.yml` gọi cùng script.
- Workflow mẫu checkout `TOANQUYNHLLC/.github` vào `.org/` rồi gọi script của tổ chức (`conventions.py`, `release.py`, `check-markdown-links.py`, `check-gofmt.py`).

## ⚖️ HỆ QUẢ

- Kiểm tra chạy y hệt tại máy và trên GitHub Actions (trừ CodeQL); mỗi script có test trong `scripts/test_*.py`.
- Repository dùng workflow mẫu phụ thuộc nhánh chính của `TOANQUYNHLLC/.github` (được Protect Main bảo vệ): đổi quy ước một nơi áp dụng ngay cho mọi repository; ghim theo tag sẽ làm các repository kẹt ở quy tắc cũ.
- Tệp cấu hình viết bằng ngôn ngữ khác (ví dụ `eslint.config.js`) không phải script nên không cần dòng lý do.
