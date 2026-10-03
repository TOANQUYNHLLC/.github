# 🤖 HƯỚNG DẪN CHO GITHUB COPILOT

Làm theo [`AGENTS.md`](../AGENTS.md) — lệnh kiểm tra, quy ước bắt buộc và những điều không được làm trong repository này. Tệp này chỉ ghi phần riêng cho việc đánh giá Pull Request.

## 👀 KHI ĐÁNH GIÁ PULL REQUEST

- Nhận xét bằng tiếng Việt.
- Ưu tiên lỗi mà `make check` không bắt được: logic sai, thay đổi ảnh hưởng mọi repository của tổ chức.
- Đối chiếu tài liệu với code của Pull Request (README, `AGENTS.md`, ADR, docstring, chú thích): chỉ ra mọi chỗ mô tả không còn đúng.
- Cảnh báo khi Pull Request chứa mật khẩu, token, dữ liệu cá nhân hoặc thông tin y tế.
