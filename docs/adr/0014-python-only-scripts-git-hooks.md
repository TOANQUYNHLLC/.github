# 0014. SCRIPT CHỈ VIẾT BẰNG PYTHON, KỂ CẢ GIT HOOK; HOOK CHẠY KIỂM TRA TRƯỚC KHI ĐẨY VÀ SAU KHI KÉO

- **Trạng thái:** Bị thay thế một phần bởi [0015](0015-prefer-python-with-reason.md) (ưu tiên Python có ghi lý do thay cho cấm ngôn ngữ khác) và [0016](0016-git-hooks-check-what-is-pushed.md) (hook kiểm tra đúng nội dung được commit, được đẩy; thêm `post-rewrite`)
- **Ngày:** 2026-10-03
- **Điều chỉnh:** [0012](0012-python-checks-camel-case.md) — bỏ ngoại lệ "hook git bằng shell"

## 📌 BỐI CẢNH

ADR 0012 ưu tiên Python nhưng cho phép hook git viết bằng shell. Ngoại lệ đó không có lý do kỹ thuật: git chạy được hook viết bằng bất kỳ ngôn ngữ nào có shebang, và các hook chỉ gọi lệnh, lọc danh sách tệp, in thông báo — việc Python làm tốt. Ngoại lệ khiến `scripts/` có cả shell lẫn Python, và `validate.py` không chặn việc thêm script shell mới.

Người dùng yêu cầu hai quy tắc: luôn chạy `make check` trước khi đẩy; luôn chạy `make org-preview` sau khi kéo code mới.

## ✅ QUYẾT ĐỊNH

- Mọi tệp trong `scripts/` viết bằng **Python**, kể cả git hook. Shell chỉ dùng cho `.devcontainer/post-create.sh` — script cài đặt chạy trước khi có công cụ, không phải kiểm tra. `validate.py` báo lỗi khi `scripts/` có tệp không phải Python hoặc có tệp `.sh` ngoài `.devcontainer/`.
- Một script `scripts/git-hooks.py` cho mọi hook; `make hooks` liên kết `.git/hooks/pre-commit`, `pre-push`, `post-merge` tới script này:
    - `pre-commit`: Prettier, `ruff format` cho tệp đang được stage.
    - `pre-push`: `make check`; lỗi thì không đẩy.
    - `post-merge`: `make org-preview` sau `git pull` — so cài đặt trên GitHub với code vừa kéo về; chỉ báo, không chặn (cần GitHub CLI đã đăng nhập).

## ⚖️ HỆ QUẢ

- Mỗi lần `git push` chạy toàn bộ kiểm tra (khoảng 6 phút, phần lớn là test); bỏ qua hook là vi phạm quy ước (`--no-verify` bị cấm trong `AGENTS.md`).
- Sau mỗi lần `git pull`, người quản trị thấy ngay cài đặt trên web lệch với code (ví dụ ai đó sửa ruleset trên web).
- Hook chỉ có hiệu lực sau khi chạy `make hooks` (Dev Container tự chạy).
