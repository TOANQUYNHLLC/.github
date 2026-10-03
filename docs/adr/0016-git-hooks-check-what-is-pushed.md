# 0016. GIT HOOK KIỂM TRA ĐÚNG NỘI DUNG ĐƯỢC COMMIT, ĐƯỢC ĐẨY VÀ CHẠY SAU MỌI CÁCH KÉO CODE

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03
- **Điều chỉnh:** [0014](0014-python-only-scripts-git-hooks.md) — thêm hook `post-rewrite`, `pre-push` kiểm tra đúng nội dung được đẩy

## 📌 BỐI CẢNH

Hook của ADR 0014 có năm chỗ chưa hợp lý:

- `pre-push` chạy `make check` trên thư mục làm việc: còn thay đổi chưa commit thì kiểm tra khác nội dung được đẩy; đẩy branch khác HEAD thì kiểm tra nhầm branch.
- `post-merge` không chạy sau `git pull --rebase`, nên quy tắc "chạy `make org-preview` sau khi kéo" bị bỏ qua.
- `pre-commit` kiểm tra tệp trên đĩa, không phải phần đã stage (`git add -p`).
- `pre-push` chạy đủ `make check` (khoảng 6 phút) kể cả khi chỉ đẩy tag hoặc xóa branch.
- `make hooks` cài vào `--git-path hooks` — theo `core.hooksPath` nên có thể ghi vào thư mục của công cụ khác — và không cảnh báo git đang bỏ qua `.git/hooks`; danh sách hook viết cứng trong `Makefile`.

## ✅ QUYẾT ĐỊNH

- `pre-commit`: xuất phần đã stage (`git checkout-index`) cùng cấu hình định dạng vào thư mục tạm rồi chạy Prettier, `ruff format` ở đó.
- `pre-push`: đọc danh sách ref git đưa vào; chỉ đẩy tag hoặc xóa branch thì bỏ qua; còn thay đổi chưa commit hoặc đẩy branch khác HEAD thì chặn; còn lại chạy `make check`, lỗi thì chặn.
- `post-merge` (sau `git pull` gộp, tua nhanh) và `post-rewrite` với tham số `rebase` (sau `git pull --rebase`): cài lại hook rồi chạy `make org-preview`; chỉ báo, không chặn. `post-rewrite` sau `git commit --amend` bỏ qua.
- `python3 scripts/git-hooks.py install` (gọi từ `make hooks`) là nơi duy nhất cài hook: danh sách lấy từ `HOOKS` trong script, cài vào `<git common dir>/hooks` (dùng chung mọi worktree), cảnh báo khi `core.hooksPath` được đặt.

## ⚖️ HỆ QUẢ

- Kết quả hook khớp đúng nội dung được commit, được đẩy; đẩy tag phát hành không phải chờ `make check`.
- Kéo code bằng cách nào cũng được đối chiếu cài đặt trên GitHub, và hook mới thêm có hiệu lực ngay sau khi kéo.
- Phải commit hoặc `git stash -u` trước khi đẩy; đẩy branch khác HEAD phải checkout branch đó trước.
