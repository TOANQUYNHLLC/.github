# 📝 NHẬT KÝ THAY ĐỔI

Mọi thay đổi đáng chú ý của repository `.github` thuộc **CÔNG TY TNHH TOÀN QUỲNH** được ghi tại đây.

Định dạng theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Phiên bản đặt theo năm và tháng phát hành, ví dụ `v2026.09.Stable`. Thay đổi mới ghi vào mục **CHƯA PHÁT HÀNH**, rồi chuyển sang một phiên bản khi gắn tag.

---

## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github/compare/v2026.10.Stable...HEAD)

### ✨ THÊM

- Bộ bản ghi quyết định kiến trúc trong `docs/adr/`: các quyết định đang có hiệu lực về định dạng, quy ước, ruleset, công cụ, kiểm tra, git hook và phát hành.
- Git hook (`make hooks`): `pre-commit` kiểm tra Prettier, `ruff format`, `ruff check` trên phần đã stage; `pre-push` chạy `make check` trên đúng nội dung được đẩy; `post-merge`, `post-rewrite` chạy song song `make org-preview`, `make links`, `make versions` sau khi kéo code.
- Quy tắc tài liệu khớp code (ADR 0013): mỗi lần sửa code phải kiểm tra tài liệu liên quan; `validate.py` báo lỗi khi tài liệu nhắc lệnh `make`, đường dẫn, hàm không có thật, hoặc `README.md` thiếu lệnh, script, workflow.
- `make release-pr`: chuẩn bị và mở Pull Request phát hành tại máy khi GitHub Actions tắt.
- `make org-preview` (`org-setup.py preview`): xem trước mọi lệnh áp dụng cấu hình chung cùng lúc.

### ♻️ THAY ĐỔI

- Mọi kiểm tra là script trong `scripts/`, ưu tiên Python, không viết trong YAML; `scripts/check.py` khai báo các nhóm kiểm tra dùng chung cho `make check` và GitHub Actions.
- ruff (`make check`, `make format`, hook `pre-commit`) kiểm tra cùng một phạm vi: mọi tệp Python của repository.
- `scripts/org-setup.py` chia thành các module trong `scripts/orgsetup/`; mỗi script có tệp test riêng.
- Mọi kiểm tra đọc đúng tệp có tên tiếng Việt, có khoảng trắng (`git ls-files -z`) và bỏ qua tệp đã xóa trên đĩa.
- Kiểm tra liên kết, biểu mẫu chạy song song và thử lại khi máy chủ lỗi tạm thời; `make forms` báo rõ khi branch chưa đẩy lên GitHub; `make org-preview` kiểm tra đăng nhập GitHub CLI một lần; `check-markdown-links.py` hiểu liên kết mã hóa phần trăm; `check-gofmt.py` bỏ qua `vendor/`.
- `validate.py` kiểm tra thêm: tên hàm, tham số, biến camelCase (đọc cây cú pháp); người quản trị trong `MAINTAINERS.md` khớp `org-setup.py team`; bộ nhãn chuẩn có đủ nhãn mặc định của GitHub; liên kết trong `CHANGELOG.md` là URL tuyệt đối; `security.txt` sắp hết hạn (trước 30 ngày). `make links` báo khi bản `security.txt` trên website khác bản trong repository.

### 🗑️ BỎ

- GitHub Pages của repository `.github`.

---

## [v2026.10.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2026.10.Stable) — 2026-10-03

Nội dung phát hành xem tại [GitHub Release v2026.10.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2026.10.Stable).

---

## [v2026.09.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2026.09.Stable) — 2026-09-26

Nội dung phát hành xem tại [GitHub Release v2026.09.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2026.09.Stable).

---

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
