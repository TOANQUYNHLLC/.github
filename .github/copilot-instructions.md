# 🤖 HƯỚNG DẪN CHO GITHUB COPILOT

Làm theo [`AGENTS.md`](../AGENTS.md) — lệnh kiểm tra, quy ước bắt buộc và những điều không được làm trong repository này.

## 👀 KHI ĐÁNH GIÁ PULL REQUEST

- Nhận xét bằng tiếng Việt.
- Kiểm tra định dạng theo `.editorconfig`: tab độ rộng 4, chỉ YAML và Markdown dùng 4 dấu cách; LF.
- Action trong workflow phải ghim theo commit SHA đầy đủ, có `permissions` tối thiểu (quyền ghi chỉ ở job, có chú thích lý do), `concurrency` và `timeout-minutes`.
- Mọi kiểm tra là tệp riêng trong `scripts/` (ưu tiên Python), không viết trực tiếp trong `.yml`, `.yaml` — kể cả workflow mẫu: không `run: |`, không mã nhúng `python -c`; kiểm tra mới phải là một nhóm của `scripts/check.py` để chạy được tại máy. Tên hàm tiếng Anh, camelCase.
- Loại commit và tiền tố branch trong `CONTRIBUTING.md` phải khớp `scripts/conventions.py`; đuôi tệp phải khớp giữa `scripts/validate.py`, `.editorconfig` và `.gitattributes`.
- Biểu mẫu Issue, Discussion phải nằm trong `.github/`; biểu mẫu Issue chỉ dùng khóa GitHub chấp nhận (không có `type`); liên kết trong biểu mẫu là URL tuyệt đối; nhãn dùng ở biểu mẫu và cấu hình phải có trong `labels.yml`.
- Cảnh báo khi Pull Request chứa mật khẩu, token, dữ liệu cá nhân hoặc thông tin y tế.
