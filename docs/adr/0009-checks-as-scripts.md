# 0009. KIỂM TRA TRONG SCRIPTS/, TIỆN ÍCH TRONG SHELL/; ƯU TIÊN PYTHON, CHẠY ĐƯỢC TẠI MÁY

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Kiểm tra viết thẳng trong workflow (`run: |`, Python nhúng) không chạy được tại máy, không có test, dễ lệch giữa các bản chép — và mất hẳn khi GitHub Actions tắt để tiết kiệm chi phí. Workflow mẫu chép quy ước vào từng repository thì đổi quy ước phải sửa mọi bản chép. Ngoài kiểm tra, người phát triển cần lệnh tiện ích chạy tại máy, không thuộc nhóm kiểm tra nào — ví dụ chuyển branch, kéo code rồi xóa branch đã hợp nhất (Squash tạo commit mới nên `git branch -d` báo "not fully merged").

## ✅ QUYẾT ĐỊNH

- Mọi kiểm tra viết thành script trong `scripts/`, mặc định bằng **Python**. Được dùng ngôn ngữ khác khi ngôn ngữ đó xử lý việc đó tốt hơn, với dòng `Không viết bằng Python vì: <lý do>` trong 10 dòng đầu tệp; `validate.py` báo lỗi khi thiếu (mọi tệp không phải Python trong `scripts/`, mọi tệp `.sh`, `.bash`, `.zsh`, `.rb`, `.pl`, `.ps1` ở bất kỳ đâu).
- Script tiện ích cho người phát triển — không phải kiểm tra — đặt trong `shell/`, mỗi script có lệnh `make` gọi nó (`make sync` → `shell/sync.sh`, `shell/prune-branches.sh`); theo cùng quy tắc ngôn ngữ, được ShellCheck kiểm tra và có test trong `scripts/test_*.py`.
- **Không** viết kiểm tra trong `.yml`, `.yaml` (cả `.github/workflows/` và `workflow-templates/`): mỗi bước gọi đúng một lệnh — cấm `run: |`, `run: >`, `shell: python` và mã nhúng `python -c`, `node -e`, `bash -c`; điều kiện dùng `if:` của GitHub Actions.
- `scripts/check.py` là nơi duy nhất khai báo các nhóm kiểm tra (`content`, `format`, `lint`, `conventions`, `audit`): `make check` và từng job của `validate.yml` gọi cùng script.
- Workflow mẫu checkout `TOANQUYNHLLC/.github` vào `.org/` rồi gọi script của tổ chức (`conventions.py`, `release.py`, `check-markdown-links.py`, `check-gofmt.py`, `install-python-dependencies.py`).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Viết kiểm tra trong workflow** (`run: |` bằng shell, Python nhúng): không chạy được tại máy khi GitHub Actions tắt, không có test, lặp lại ở `Makefile`, dễ lệch giữa các bản chép trong workflow mẫu.
- **Chỉ cho phép Python, cấm mọi ngôn ngữ khác**: cứng nhắc với việc mà ngôn ngữ khác làm tốt hơn (script cài đặt Dev Container nối các lệnh cài đặt); chọn ưu tiên Python kèm dòng lý do bắt buộc.
- **Mỗi workflow mẫu chép sẵn quy ước**: đổi quy ước phải sửa mọi repository; chọn gọi script của tổ chức từ `.org/`.
- **Đặt script tiện ích trong `scripts/`**: lẫn với các kiểm tra, khó biết script nào thuộc `make check`.
- **Chỉ ghi lệnh tiện ích trong `Makefile`**: lệnh nhiều bước, nhiều nhánh điều kiện trong `Makefile` không có test và không được ShellCheck kiểm tra.

## ⚖️ HỆ QUẢ

- Kiểm tra chạy y hệt tại máy và trên GitHub Actions (trừ CodeQL); mỗi script có test trong `scripts/test_*.py`.
- Repository dùng workflow mẫu phụ thuộc nhánh chính của `TOANQUYNHLLC/.github` (được Protect Main bảo vệ): đổi quy ước một nơi áp dụng ngay cho mọi repository; ghim theo tag sẽ làm các repository kẹt ở quy tắc cũ.
- Thêm script vào `shell/` thì thêm lệnh `make`, dòng trong bảng lệnh và mục cấu trúc của `README.md`, cùng test; `make check` báo khi thiếu. Repository khác không nhận script trong `shell/` — workflow mẫu chỉ gọi script trong `scripts/`.
- Tệp cấu hình viết bằng ngôn ngữ khác (ví dụ `eslint.config.js`) không phải script nên không cần dòng lý do.
