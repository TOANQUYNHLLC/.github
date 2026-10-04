# 0011. GIT HOOK KIỂM TRA ĐÚNG NỘI DUNG ĐƯỢC COMMIT, ĐƯỢC ĐẨY VÀ ĐỐI CHIẾU SAU KHI KÉO

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Kiểm tra trên GitHub Actions chỉ chạy sau khi đẩy, và không chạy khi Actions tắt để tiết kiệm chi phí — nên kiểm tra phải chạy tại máy trước khi đẩy. Cài đặt trên web có thể bị sửa tay, lệch với code. Hook kiểm tra tệp trên đĩa thay vì nội dung thật sự được commit, được đẩy sẽ cho kết quả sai.

## ✅ QUYẾT ĐỊNH

- Một script `scripts/git-hooks.py` cho mọi hook; `make hooks` (`git-hooks.py install`) liên kết hook vào `<git common dir>/hooks` (dùng chung mọi worktree) và cảnh báo khi `core.hooksPath` làm git bỏ qua hook.
- `pre-commit`: xuất phần đã stage (`git checkout-index`) cùng cấu hình định dạng vào thư mục tạm rồi chạy Prettier, `ruff format`, `ruff check` ở đó.
- `pre-push`: chỉ đẩy tag hoặc xóa branch thì bỏ qua; còn thay đổi chưa commit hoặc đẩy branch khác HEAD thì chặn; còn lại chạy `make check`, lỗi thì chặn.
- `post-merge` (sau `git pull`) và `post-rewrite` với tham số `rebase` (sau `git pull --rebase`): cài lại hook, rồi chạy song song `make org-preview` (khi GitHub CLI đã đăng nhập), `make links`, `make versions`; chỉ báo, không chặn.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Chỉ dựa vào GitHub Actions**: Actions có thể tắt để tiết kiệm chi phí; khi đó không còn kiểm tra nào trước khi đẩy.
- **Hook viết bằng shell**: git chạy được hook ở mọi ngôn ngữ có shebang, các hook chỉ gọi lệnh và lọc danh sách tệp — việc Python làm tốt; chọn Python theo ADR 0009.
- **Hook kiểm tra tệp trên đĩa**: sai khi chỉ stage một phần tệp (`git add -p`) hoặc còn thay đổi chưa commit; chọn kiểm tra đúng nội dung được commit, được đẩy.
- **Chỉ chạy `make org-preview` sau `post-merge`**: bỏ sót `git pull --rebase`; thêm `post-rewrite`.

## ⚖️ HỆ QUẢ

- Kết quả hook khớp đúng nội dung được commit, được đẩy; phải commit hoặc `git stash -u` trước khi đẩy.
- Sau mỗi lần kéo code, người quản trị thấy ngay cài đặt trên web lệch với code, liên kết hỏng, công cụ có bản mới.
- Bỏ qua hook (`--no-verify`) bị cấm trong `AGENTS.md`; hook chỉ có hiệu lực sau `make hooks` (Dev Container tự chạy).
