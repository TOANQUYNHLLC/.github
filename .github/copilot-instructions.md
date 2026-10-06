# 🤖 HƯỚNG DẪN CHO GITHUB COPILOT

Làm theo [`AGENTS.md`](../AGENTS.md) — lệnh kiểm tra, quy ước bắt buộc và những điều không được làm trong repository này. Tệp này chỉ ghi phần riêng cho việc đánh giá Pull Request.

Hướng dẫn theo loại tệp nằm trong [`instructions/`](instructions/): mã Python, cấu hình GitHub và tài liệu. Agent [`repository-reviewer`](agents/repository-reviewer.agent.md) chuyên rà soát ảnh hưởng toàn tổ chức và đối chiếu tài liệu với code, dùng công cụ đọc và tìm kiếm.

## 👀 KHI ĐÁNH GIÁ PULL REQUEST

- Nhận xét bằng tiếng Việt.
- Ưu tiên lỗi mà `make check` không bắt được: logic sai, thay đổi ảnh hưởng mọi repository của tổ chức.
- Đối chiếu tài liệu với code của Pull Request (README, `AGENTS.md`, ADR, docstring, chú thích): chỉ ra mọi chỗ mô tả không còn đúng.
- Cảnh báo khi Pull Request chứa mật khẩu, token, dữ liệu cá nhân hoặc thông tin y tế.
