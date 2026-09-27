# 📝 NHẬT KÝ THAY ĐỔI

Mọi thay đổi đáng chú ý của repository `.github` thuộc **CÔNG TY TNHH TOÀN QUỲNH** được ghi tại đây.

Định dạng theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Phiên bản đặt theo năm và tháng phát hành, ví dụ `v2026.09.Stable`. Thay đổi mới ghi vào mục **CHƯA PHÁT HÀNH**, rồi chuyển sang một phiên bản khi gắn tag.

---

## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github/compare/v2026.09.Stable...HEAD)

### ✨ THÊM

**Tệp cộng đồng mặc định** — GitHub áp dụng cho mọi repository của tổ chức chưa có tệp riêng

- `CONTRIBUTING.md` — quy trình đóng góp; tên branch `<tiền tố>/<mô_tả>` bằng tiếng Anh, nối từ bằng dấu gạch dưới; quy ước commit `<loại>(<phạm vi>): <mô tả>` (`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`); ký commit bắt buộc dưới ruleset Protect Main; phong cách mã nguồn, kiểm thử, đánh giá, hợp nhất, sửa lỗi khẩn cấp, phụ thuộc.
- `SECURITY.md` — báo cáo lỗ hổng qua GitHub (**Security → Report a vulnerability**) hoặc email soạn sẵn mẫu; `.well-known/security.txt` (RFC 9116, chưa đăng lên website — xem `ROADMAP.md`).
- `CODE_OF_CONDUCT.md`, `SUPPORT.md` (Issues, Discussions, bảo mật, liên hệ), `.github/FUNDING.yml` (chưa bật kênh tài trợ).
- `.github/ISSUE_TEMPLATE/` (Báo lỗi, Đề xuất tính năng, Câu hỏi; tắt Issue trống) và `.github/DISCUSSION_TEMPLATE/` (Ý tưởng, Hỏi đáp, Thảo luận chung) — cùng tên trường, cùng cảnh báo dữ liệu nhạy cảm và kênh báo cáo bảo mật; GitHub chỉ nhận hai thư mục này và `FUNDING.yml` bên trong `.github/`.

**Tài nguyên dùng chung**

- `workflow-templates/` — Node.js CI, Python CI, Go CI, CodeQL, rà soát dependency, Docker image, tạo GitHub Release, kiểm tra tiêu đề Pull Request và tên branch, đóng mục không hoạt động, kiểm tra tài liệu; mọi action ghim theo commit SHA, quyền ghi chỉ cấp ở job cần dùng.
- `rulesets/protect-main.json` — ruleset **Protect Main** duy nhất cho nhánh chính: cho phép Merge, Squash, Rebase; kiểm tra tự động bắt buộc; phê duyệt của `CODEOWNERS`; commit có chữ ký; chặn tạo, cập nhật, xóa và force push.
- `repository-templates/` — `CODEOWNERS` (team `@TOANQUYNHLLC/maintainers`), `dependabot.yml`, `release.yml`, `rustfmt.toml`, `.clang-format`, `.python-version`, `.dockerignore`, `.env.example`, `PRIVACY.md`.
- `labels.yml` và `scripts/sync-labels.sh` — bộ 16 nhãn chuẩn.
- `scripts/org-setup.py` và `make org-preview` — áp dụng lên các repository: Pull Request thêm tệp dùng chung (theo ngôn ngữ repository dùng), cài đặt hợp nhất và tính năng bảo mật, ruleset, team maintainers; mặc định chỉ xem trước.
- `docs/adr/` — bản ghi quyết định: thụt lề bằng tab, LF/CRLF, tên branch, ruleset Protect Main, cách hợp nhất, nguồn phiên bản công cụ; mẫu ADR có trường **Điều chỉnh** cho quyết định thay thế một phần.

**Cấu hình và kiểm tra của repository này**

- Quản trị: `GOVERNANCE.md` (GitHub không áp dụng làm tệp mặc định), `MAINTAINERS.md`, `ROADMAP.md`, `CHANGELOG.md`, `CITATION.cff`, `NOTICE`.
- Định dạng: `.editorconfig`, `.gitattributes`, `.prettierrc.json`, `ruff.toml`, `eslint.config.js`, `.shellcheckrc` — UTF-8, LF, tab độ rộng 4 (kể cả Python); dấu cách chỉ cho ngôn ngữ bắt buộc; CRLF chỉ cho loại tệp bắt buộc.
- CI: workflow Pull Request chỉ hủy lượt chạy cũ của cùng Pull Request, lượt chạy trên nhánh chính luôn chạy hết (`concurrency`); `validate.yml` (nội dung, test tự động, Prettier, `ruff format`, `ruff check`, ESLint, shellcheck, actionlint), `pr-title.yml`, `branch-name.yml`, `codeql.yml`, `dependency-review.yml`, `links.yml` (URL trong Markdown, YAML, `CITATION.cff`, `security.txt`; GitHub chấp nhận biểu mẫu — `scripts/check-github-forms.py`), `stale.yml`, `release.yml` (GitHub Release từ `CHANGELOG.md`).
- `scripts/validate.py` — kiểm tra mọi tệp văn bản (trừ tệp nhị phân khai báo trong `.gitattributes`): định dạng và mã hóa từng loại tệp (thụt lề chỉ bằng tab ở mọi tệp không bắt buộc dấu cách), chữ tiếng Việt dạng NFC, email chung, liên kết, tiêu đề viết hoa; biểu mẫu Issue và Discussion (vị trí trong `.github/`, khóa hợp lệ, liên kết tuyệt đối); nhãn dùng trong biểu mẫu, `dependabot.yml`, `release.yml`, `stale.yml` phải có trong `labels.yml`; workflow (ghim SHA, quyền ghi chỉ ở job, `timeout-minutes`, `$default-branch` chỉ trong workflow mẫu, phiên bản công cụ chỉ từ `mise.toml`); `.prettierrc.json`, `ruff.toml`, `.editorconfig` khớp cấu hình chuẩn, `.prettierignore` không lặp `.gitignore`, ESLint dùng `eslint-config-prettier` và không bật `indent`; ruleset; bảng ADR khớp từng ADR; các danh sách trong `CONTRIBUTING.md`, workflow, `.editorconfig`, `.gitattributes` phải khớp nhau. Mỗi test trong `scripts/test_validate.py` cố ý làm hỏng một điểm để chứng minh luật còn hoạt động.
- `.github/`: `CODEOWNERS`, `dependabot.yml` (GitHub Actions, npm), `release.yml`, `copilot-instructions.md`.
- Công cụ: `package.json` (`devEngines`: Node.js, npm), `.nvmrc`, `.npmrc` (không tạo `package-lock.json`), `mise.toml` — nguồn phiên bản duy nhất cho máy cục bộ, Dev Container và CI (`jdx/mise-action`, ADR 0007), `Makefile`, `.devcontainer/` (image và feature theo `latest`, không commit `devcontainer-lock.json`), `.vscode/extensions.json`; `make hooks` cài pre-commit hook (chạy được trong git worktree), mẫu commit `.gitmessage` và `.git-blame-ignore-revs`; `.mailmap`.
- `AGENTS.md`, `CLAUDE.md` — hướng dẫn cho AI coding agent.

### ♻️ THAY ĐỔI

- `README.md` tập trung vào chính repository: cách GitHub áp dụng nội dung cho toàn tổ chức (và những tệp không được kế thừa), cấu trúc theo nhóm, phát triển cục bộ; giới thiệu công ty chuyển về `profile/README.md`.
- `PULL_REQUEST_TEMPLATE.md` thêm mục kiểm tra formatter/lint và quy ước tên branch, commit, tiêu đề; nêu kênh báo cáo bảo mật (GitHub hoặc email) bằng liên kết tuyệt đối.
- `profile/README.md` thêm badge liên hệ, phần giới thiệu tiếng Anh (**ABOUT US**), thống nhất tên **Phòng khám chuyên khoa Nhi DR. MOON**.
- Tiêu đề mọi tài liệu và biểu mẫu viết hoa; tài liệu công khai thống nhất đường phân cách giữa các mục và chân trang; cảnh báo dữ liệu nhạy cảm thống nhất một cách diễn đạt.

---

## [v2026.09.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2026.09.Stable) — 2026-09-26

### ✨ THÊM

- `profile/README.md` — trang giới thiệu CÔNG TY TNHH TOÀN QUỲNH trên GitHub: giới thiệu chung, câu chuyện thương hiệu, lĩnh vực hoạt động, tầm nhìn, sứ mệnh, giá trị cốt lõi, dự án Phòng khám chuyên khoa Nhi DR. MOON và thông tin liên hệ.
- `README.md` — mục đích, cấu trúc và nguyên tắc quản lý repository `.github`.
- `PULL_REQUEST_TEMPLATE.md` — biểu mẫu Pull Request mặc định cho toàn tổ chức.
- `LICENSE` — giấy phép MIT.

---

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
