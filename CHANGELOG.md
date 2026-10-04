# 📝 NHẬT KÝ THAY ĐỔI

Mọi thay đổi đáng chú ý của repository `.github` thuộc **CÔNG TY TNHH TOÀN QUỲNH** được ghi tại đây.

Định dạng theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Phiên bản đặt theo năm và tháng phát hành, ví dụ `v2026.09.Stable`. Thay đổi mới ghi vào mục **CHƯA PHÁT HÀNH**, rồi chuyển sang một phiên bản khi gắn tag.

---

## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github/compare/v2026.10.Stable...HEAD)

### ✨ THÊM

- Bản ghi quyết định kiến trúc trong `docs/adr/` (mỗi ADR gồm bối cảnh, quyết định, phương án đã cân nhắc, hệ quả): định dạng, quy ước branch và commit, ruleset, commit có chữ ký, nguồn phiên bản công cụ, kiểm tra là script, quy tắc đặt tên, git hook, phát hành hằng tháng, tài liệu khớp code.
- Kiểm tra tại máy giống GitHub Actions: `make check` chạy song song các nhóm `content`, `format`, `lint`, `conventions`, `audit` (khai báo trong `scripts/check.py`); test chia cho mọi lõi CPU (`scripts/run-tests.py`).
- Git hook (`make hooks`): `pre-commit` kiểm tra Prettier, `ruff format`, `ruff check` trên phần đã stage; `pre-push` chạy `make check` trên đúng nội dung được đẩy; `post-merge`, `post-rewrite` chạy song song `make org-preview`, `make links`, `make versions` sau khi kéo code.
- `validate.py` kiểm tra: định dạng, mã hóa, xuống dòng từng loại tệp; liên kết nội bộ (cả mục `#…`, liên kết mã hóa phần trăm); tiêu đề viết hoa; chữ trên huy hiệu tiếng Anh, hoa đầu mỗi từ; biểu mẫu Issue, Discussion; nhãn (đủ nhãn mặc định của GitHub); workflow (ghim SHA, quyền tối thiểu, không viết `${{ … }}` trong `run:`, `concurrency`, `timeout-minutes`, không viết kiểm tra trong YAML); ruleset; bảng ADR và đủ mục của từng ADR; tên tự đặt camelCase (cú pháp của ngôn ngữ giữ nguyên); tài liệu khớp code (lệnh `make`, đường dẫn, hàm được nhắc tới; `README.md` liệt kê đủ lệnh, script, workflow); người quản trị khớp `scripts/orgsetup/teams.py`; `security.txt` (báo trước 30 ngày khi sắp hết hạn); liên kết trong `CHANGELOG.md` là URL tuyệt đối.
- `make links`: liên kết bên ngoài còn hoạt động (thử IPv4 trước, thử lại khi máy chủ lỗi tạm thời; máy chủ ngắt kết nối hay trả phản hồi sai dạng thì báo liên kết đó, không dừng cả lượt) và bản `security.txt` trên website khớp repository. `make forms`: GitHub chấp nhận biểu mẫu trên một branch. `make versions`: công cụ trong `mise.toml` có bản mới.
- `make org-preview` (`org-setup.py preview`): xem trước cùng lúc việc áp dụng tệp dùng chung, cài đặt, ruleset, team, nhãn lên mọi repository và cài đặt tổ chức; các lệnh trong `scripts/orgsetup/` đọc GitHub song song, ghi tuần tự. Lệnh `files` thêm tệp phiên bản cho workflow mẫu: `.nvmrc` (Node.js CI), `.python-version` (Python CI).
- `make release-pr`: chuẩn bị và mở Pull Request phát hành tại máy khi GitHub Actions tắt; GitHub từ chối commit thì xóa branch phát hành vừa tạo để lần sau làm lại.
- Huy hiệu đầu `README.md`: kết quả `validate.yml` và CodeQL trên `main`, phiên bản phát hành, commit gần nhất, Conventional Commits, code style (Prettier, Ruff), giấy phép.
- Workflow mẫu `docs-check.yml`, `go-ci.yml` gọi `check-markdown-links.py`, `check-gofmt.py` của tổ chức (tệp Go sai cú pháp thì báo đúng tệp, dòng, cột; đọc đúng tên tệp tiếng Việt; anchor tiêu đề tính đúng như GitHub, kể cả tiêu đề có emoji hoặc liên kết; bỏ qua `vendor/`).

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
