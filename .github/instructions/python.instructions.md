---
applyTo: 'scripts/**/*.py,.devcontainer/**/*.py'
---

# 🐍 HƯỚNG DẪN CHO MÃ PYTHON

Quy tắc cho scripts và tests Python của bộ tài nguyên. Đọc cùng [`AGENTS.md`](../../AGENTS.md), cấu hình công cụ và các nơi gọi mã trong phạm vi sửa.

- Kiểm tra các nơi gọi script hoặc hàm trước khi thay đổi tên, tham số, mã thoát hay thông báo; sửa mọi nơi liên quan trong cùng thay đổi.
- Tên hàm, tham số và biến tự đặt dùng camelCase tiếng Anh; hằng số dùng `UPPER_CASE`, lớp dùng `PascalCase`. Quy tắc áp dụng cả bí danh import tự đặt và biến được gán trong `match/case`. Giữ tên do ngôn ngữ và thư viện quy định. Tên tệp script viết kebab-case (`check-markdown-links.py`), module được `import` viết một từ, test đặt `test_*.py`. Dùng tab độ rộng 4 theo `.editorconfig`.
- Giữ khả năng chạy với Python tối thiểu trong `pyproject.toml`; phiên bản công cụ lấy từ `mise.toml`.
- Logic kiểm tra đặt trong `scripts/`; khai báo nhóm tương ứng trong `scripts/check.py` nếu GitHub Actions chạy kiểm tra đó trên Pull Request.
- Giữ kiểm tra và sinh mẫu chạy được tại máy; thao tác phát hành gọi GitHub phải được kiểm thử bằng dữ liệu mô phỏng.
- Bổ sung tests cho hành vi thay đổi và trường hợp lỗi; dùng dữ liệu mô phỏng cho các thao tác ghi lên GitHub.
- Chạy `make check` trước khi bàn giao và cập nhật tài liệu liên quan trong cùng thay đổi.
