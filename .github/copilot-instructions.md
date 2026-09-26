# 🤖 HƯỚNG DẪN CHO GITHUB COPILOT

Làm theo [`AGENTS.md`](../AGENTS.md) — lệnh kiểm tra, quy ước bắt buộc và những điều không được làm trong repository này.

## 👀 KHI ĐÁNH GIÁ PULL REQUEST

- Nhận xét bằng tiếng Việt.
- Kiểm tra định dạng theo `.editorconfig`: tab độ rộng 4, chỉ YAML và Markdown dùng 4 dấu cách; LF.
- Action trong workflow phải ghim theo commit SHA đầy đủ, có `permissions` tối thiểu và `timeout-minutes`.
- Loại commit và tiền tố branch trong `CONTRIBUTING.md` phải khớp `pr-title.yml` và `branch-name.yml`; đuôi tệp phải khớp giữa `scripts/validate.py`, `.editorconfig` và `.gitattributes`.
- Biểu mẫu Issue, Discussion và `FUNDING.yml` phải nằm trong `.github/`; liên kết trong biểu mẫu là URL tuyệt đối; nhãn dùng ở biểu mẫu và cấu hình phải có trong `labels.yml`.
- Cảnh báo khi Pull Request chứa mật khẩu, token, dữ liệu cá nhân hoặc thông tin y tế.
