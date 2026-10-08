---
applyTo: 'scripts/**/*.py,.devcontainer/**/*.py'
---

# 🐍 HƯỚNG DẪN CHO MÃ PYTHON

Áp dụng cùng [`AGENTS.md`](../../AGENTS.md).

- Kiểm tra các nơi gọi script hoặc hàm trước khi thay đổi tên, tham số, mã thoát hay thông báo; sửa mọi nơi liên quan trong cùng thay đổi.
- Tên hàm, tham số và biến tự đặt dùng camelCase tiếng Anh; hằng số dùng `UPPER_CASE`, lớp dùng `PascalCase`. Quy tắc áp dụng cả bí danh import tự đặt và biến được gán trong `match/case`. Giữ tên do ngôn ngữ và thư viện quy định. Tên tệp script viết kebab-case (`check-markdown-links.py`), module được `import` viết một từ, test đặt `test_*.py`. Dùng tab độ rộng 4 theo `.editorconfig`.
- Giữ khả năng chạy với Python tối thiểu trong `pyproject.toml`; phiên bản công cụ lấy từ `mise.toml`.
- Logic kiểm tra đặt trong `scripts/`; khai báo nhóm tương ứng trong `scripts/check.py` nếu GitHub Actions chạy kiểm tra đó trên Pull Request.
- Khi sửa `scripts/orgsetup/`, kiểm tra cả chế độ xem trước và áp dụng; lỗi đọc API phải được xử lý trước khi ghi vào phạm vi liên quan.
- Bổ sung tests cho hành vi thay đổi và trường hợp lỗi; dùng dữ liệu mô phỏng cho các thao tác ghi lên GitHub.
- Chạy `make check` trước khi bàn giao và cập nhật tài liệu liên quan trong cùng thay đổi.
