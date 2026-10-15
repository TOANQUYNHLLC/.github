# 🤖 HƯỚNG DẪN CHO GITHUB COPILOT

Làm theo [`AGENTS.md`](../AGENTS.md) — lệnh kiểm tra, quy ước bắt buộc và những điều không được làm trong repository này. Dùng các quy tắc dưới đây khi đánh giá Pull Request; lệnh và hợp đồng chi tiết lấy từ hướng dẫn chính.

Hướng dẫn theo loại tệp nằm trong [`instructions/`](instructions/): mã Python, cấu hình GitHub và tài liệu. Agent [`repository-reviewer`](agents/repository-reviewer.agent.md) chuyên rà soát ảnh hưởng toàn tổ chức và đối chiếu tài liệu với code, dùng công cụ đọc và tìm kiếm.

## 👀 KHI ĐÁNH GIÁ PULL REQUEST

- Nhận xét bằng tiếng Việt, nêu vấn đề cụ thể và căn cứ trong nguồn đã đọc.
- Ưu tiên lỗi mà `make check` không bắt được: logic sai, thay đổi ảnh hưởng mọi repository của tổ chức.
- Tìm trong toàn repository những chỗ liên quan mà Pull Request chưa sửa (nơi gọi tới, test, danh sách phải khớp nhau, workflow mẫu, tên tệp cũ còn được nhắc).
- Đối chiếu tài liệu với code của Pull Request (README, `AGENTS.md`, ADR, docstring, chú thích): chỉ ra mọi chỗ mô tả không còn đúng.
- Cảnh báo khi Pull Request chứa mật khẩu, token, dữ liệu cá nhân hoặc thông tin y tế.
