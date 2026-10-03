# 📝 NHẬT KÝ THAY ĐỔI

Mọi thay đổi đáng chú ý của repository `.github` thuộc **CÔNG TY TNHH TOÀN QUỲNH** được ghi tại đây.

Định dạng theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Phiên bản đặt theo năm và tháng phát hành, ví dụ `v2026.09.Stable`. Thay đổi mới ghi vào mục **CHƯA PHÁT HÀNH**, rồi chuyển sang một phiên bản khi gắn tag.

---

## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github/compare/v2026.09.Stable...HEAD)

### ✨ THÊM

**Tệp cộng đồng mặc định** — GitHub áp dụng cho mọi repository của tổ chức chưa có tệp riêng

- `CONTRIBUTING.md` — quy trình đóng góp; tên branch `<tiền tố>/<mô_tả>` bằng tiếng Anh, nối từ bằng dấu gạch dưới; quy ước commit `<loại>(<phạm vi>): <mô tả>` (`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`); ký commit bắt buộc dưới ruleset Protect Main; phong cách mã nguồn, kiểm thử, đánh giá, hợp nhất, sửa lỗi khẩn cấp, phụ thuộc.
- `SECURITY.md` — báo cáo lỗ hổng qua GitHub (**Security → Report a vulnerability**) hoặc email soạn sẵn mẫu; `.well-known/security.txt` (RFC 9116, đăng tại `https://toanquynh.com/.well-known/security.txt`).
- `CODE_OF_CONDUCT.md`, `SUPPORT.md` (Issues, Discussions, bảo mật, liên hệ).
- `.github/ISSUE_TEMPLATE/` (Báo lỗi, Đề xuất tính năng, Câu hỏi; tắt Issue trống) và `.github/DISCUSSION_TEMPLATE/` (Ý tưởng, Hỏi đáp, Thảo luận chung) — cùng tên trường, cùng cảnh báo dữ liệu nhạy cảm và kênh báo cáo bảo mật; GitHub chỉ nhận hai thư mục này bên trong `.github/`.

**Tài nguyên dùng chung**

- `workflow-templates/` — Node.js CI, Python CI, Go CI, CodeQL (quét cả workflow GitHub Actions; build mode theo tài liệu CodeQL hiện hành), rà soát dependency, Docker image, tạo GitHub Release, kiểm tra tiêu đề Pull Request và tên branch, gắn nhãn Pull Request (`actions/labeler`), đóng mục không hoạt động, kiểm tra tài liệu; phần kiểm tra chung (tên branch, tiêu đề, liên kết tài liệu, nội dung Release) gọi script Python của tổ chức — checkout `TOANQUYNHLLC/.github` vào `.org/` — nên quy ước sửa một nơi; mọi action ghim theo commit SHA, quyền ghi chỉ cấp ở job cần dùng, danh mục theo `actions/starter-workflows`.
- `rulesets/protect-release-tags.json` — ruleset **Protect Release Tags** (ADR 0008): chặn tạo, dời, xóa tag phát hành `v*` ngoài hai tài khoản quản trị; tag chỉ trỏ tới commit có chữ ký. Mọi ruleset bắt buộc **Require signed commits** (ADR 0009, `validate.py` kiểm tra). Ruleset đặt ở cấp repository vì gói GitHub Free không thực thi ruleset cấp tổ chức; push ruleset chỉ dành cho repository riêng tư.
- `rulesets/org-protect-main.json` — **Protect Main (Organization)**: bản cấp tổ chức sinh từ Protect Main, khớp ruleset đang cài trên web (mọi repository, 2 kiểm tra bắt buộc chung, `code_quality`; bỏ qua là chủ tổ chức — import không nhận actor loại `User`; không giới hạn người hủy phê duyệt); import trên web; chỉ thực thi với gói GitHub Team.
- `rulesets/org-protect-release-tags.json` — **Protect Release Tags (Organization)**: bản cấp tổ chức sinh từ Protect Release Tags (tag `v*` của mọi repository), khớp web — gồm quy tắc kiểm tra bắt buộc với danh sách rỗng (không chặn gì); áp dụng và giới hạn gói như Protect Main (Organization).
- `.github/workflows/monthly-release.yml` và `scripts/release.py` (`make release-prepare`) — lịch phát hành ngày 1 hằng tháng: chỉ khi có commit kể từ tag phát hành trước, chuyển mục **CHƯA PHÁT HÀNH** thành `vYYYY.MM.Stable` và mở Pull Request `release/vYYYY.MM` (commit tạo qua `createCommitOnBranch` nên được GitHub ký); người quản trị hợp nhất rồi gắn tag để `release.yml` tạo GitHub Release.
- Rà nhất quán giữa các tệp: `scripts/sync-labels.sh` (shell, luôn in đủ 47 nhãn) thành lệnh `org-setup.py labels` — Python, chỉ ghi nhãn khác `labels.yml`; `org-setup.py team` so cả tên, mô tả, chế độ hiển thị của team với web (mô tả `maintainers` thống nhất giữa script, `MAINTAINERS.md` và web); `validate.py` đối chiếu thêm loại commit trong `.gitmessage`, tiền tố branch trong `repository-templates/labeler.yml`, công cụ trong `mise.toml` với `check-tool-versions.py`; `GOVERNANCE.md` nêu ADR cho repository `.github`.
- Chỉ giữ tệp có chức năng cụ thể: bỏ ESLint (`eslint.config.js` và 4 thư viện — repository không có mã JavaScript nào ngoài chính tệp cấu hình), CodeQL cho JavaScript, `NOTICE` (repository không phân phối mã của bên thứ ba); job "Định dạng (Prettier, ruff)" đổi tên theo; `copilot-instructions.md` chỉ giữ phần riêng cho đánh giá Pull Request, quy ước chung đọc ở `AGENTS.md`.
- Mọi kiểm tra là tệp riêng, không viết trực tiếp trong `.yml`, `.yaml` (ADR 0013): `validate.py` báo lỗi khi bất kỳ workflow nào — kể cả workflow mẫu — có `run: |`, `shell: python` hoặc mã nhúng `python -c`; Go CI mẫu gọi `scripts/check-gofmt.py`, Python CI mẫu tách thành bước một lệnh với `if: hashFiles(...)`.
- Kiểm tra viết bằng Python trong `scripts/`, workflow chỉ gọi một lệnh (ADR 0012): `check.py` — nguồn duy nhất của các nhóm kiểm tra `content`, `format`, `lint`, `conventions`, `audit` mà `make check` và `validate.yml` cùng gọi, chạy tại máy mọi kiểm tra Actions chạy trên Pull Request (trừ CodeQL); `conventions.py` — tên branch, tiêu đề Pull Request/commit; `release.py` — xem trước nội dung, chuẩn bị phiên bản của tháng, mở Pull Request phát hành, tạo GitHub Release; `check-markdown-links.py` — liên kết nội bộ (dùng chung với `validate.py`). `validate.py` báo lỗi khi workflow của repository có `run: |`, khi tên hàm Python không phải camelCase tiếng Anh, và đối chiếu danh sách loại commit, tiền tố branch trong `conventions.py` với `CONTRIBUTING.md`.
- `rulesets/org-protect-pushes.json` — push ruleset **Protect Pushes (Organization)** (ADR 0010): chặn `.env`, khóa SSH riêng, tệp khóa và chứng chỉ (`*.pem`, `*.key`, `*.p12`, `*.pfx`…), kho mật khẩu, tệp cơ sở dữ liệu (`*.sqlite`, `*.db`), tệp trên 10 MB và đường dẫn trên 200 ký tự; bỏ qua là chủ tổ chức. GitHub chỉ áp dụng cho repository riêng tư, internal và chỉ thực thi với gói Team; không có `required_signatures` (push ruleset không nhận quy tắc này).
- `rulesets/protect-main.json` — ruleset **Protect Main** cho nhánh chính: cho phép Merge, Squash (không Rebase — ADR 0011, vì commit tạo lại mất chữ ký); kiểm tra tự động bắt buộc; phê duyệt của `CODEOWNERS`; commit có chữ ký; chặn tạo, cập nhật, xóa và force push.
- `repository-templates/` — `CODEOWNERS` (team `@TOANQUYNHLLC/maintainers`), `dependabot.yml`, `release.yml`, `rustfmt.toml`, `.clang-format`, `.python-version`, `.dockerignore`, `.env.example`, `PRIVACY.md`.
- `labels.yml` và `org-setup.py labels` (`make labels-preview`, `make labels-apply` — chỉ ghi nhãn khác `labels.yml`) — bộ 47 nhãn chuẩn, chọn theo tần suất ở 40 repository phổ biến và 30 repository ứng dụng (gồm y tế): 9 nhãn mặc định của GitHub, `regression` (nhóm 🐛 của Release), `ui/ux` (khớp lựa chọn "Giao diện hoặc trải nghiệm người dùng" của biểu mẫu), `i18n`, loại thay đổi khớp tiền tố branch và loại commit (`breaking change`, `performance`, `refactor`, `tests`, `build`, `ci`, `chore`, `hotfix`, `release`, `accessibility`) do `.github/labeler.yml` tự gắn cho Pull Request, phạm vi `area: …` khớp mục "Phạm vi ảnh hưởng" của biểu mẫu, mức độ ưu tiên, trạng thái xử lý (`needs triage` do biểu mẫu Issue tự gắn, `needs more info`, `confirmed`, `blocked`, `in progress`, `pinned`, `upstream` — `stale` bỏ qua bốn nhãn cuối), nhãn Dependabot theo ecosystem (`javascript`, `python`, `go`, `docker`, `github_actions`). GitHub Release nêu `breaking change` đầu tiên và tách `performance` thành nhóm riêng.
- `scripts/org-setup.py` và `make org-preview` — áp dụng lên các repository và tổ chức, khớp cài đặt đang có trên web (kiểm tra 2026-10-03, giữ giá trị local khi khác): Pull Request thêm tệp dùng chung (gồm cấu hình gắn nhãn `labeler.yml`; theo ngôn ngữ repository dùng); `settings` — Merge, Squash, auto-merge, **Update branch**, tiêu đề merge commit, sign-off khi commit trên web, tắt Wiki và Projects, Dependabot alerts và security updates, secret scanning, push protection, Release bất biến, quyền GitHub Actions (bắt buộc ghim SHA, `GITHUB_TOKEN` mặc định chỉ đọc, cho phép tạo Pull Request; không bật, tắt Actions và bỏ qua khi Actions tắt), description, homepage, Discussions, topics (từ `CITATION.cff`) của `.github`, so GitHub Pages; ruleset; `team` — 6 team (`admins`, `maintainers`, `developers`, `qa`, `design`, `marketing`); `org-settings` — cài đặt tổ chức và quyền Actions cấp tổ chức; mặc định chỉ xem trước; với repository riêng tư, bỏ qua báo cáo lỗ hổng riêng tư và cảnh báo (không dừng) khi GitHub từ chối tính năng hoặc ruleset; ruleset, team, cài đặt và tính năng bảo mật giống trên GitHub thì báo đã đúng, không ghi đè; `org-rulesets` so tệp với ruleset cấp tổ chức trên web qua GraphQL khi REST API trả HTTP 403 (gói Free, dù token có `admin:org`).
- `docs/adr/` — bản ghi quyết định: thụt lề bằng tab, LF/CRLF, tên branch, ruleset Protect Main, cách hợp nhất, nguồn phiên bản công cụ, ruleset tag phát hành, mọi ruleset bắt buộc commit có chữ ký, push ruleset, bỏ Rebase, kiểm tra bằng Python và tên hàm camelCase; mẫu ADR có trường **Điều chỉnh** cho quyết định thay thế một phần.

**Cấu hình và kiểm tra của repository này**

- Quản trị: `GOVERNANCE.md` (GitHub không áp dụng làm tệp mặc định), `MAINTAINERS.md`, `ROADMAP.md`, `CHANGELOG.md`, `CITATION.cff`.
- Định dạng: `.editorconfig`, `.gitattributes`, `.prettierrc.json`, `ruff.toml`, `.shellcheckrc` — UTF-8, LF, tab độ rộng 4 (kể cả Python); dấu cách chỉ cho ngôn ngữ bắt buộc; CRLF chỉ cho loại tệp bắt buộc.
- CI: workflow Pull Request chỉ hủy lượt chạy cũ của cùng Pull Request, lượt chạy trên nhánh chính luôn chạy hết (`concurrency`); `validate.yml` (các nhóm `content`, `format`, `lint` của `scripts/check.py`), `pr-title.yml`, `branch-name.yml`, `codeql.yml`, `dependency-review.yml`, `links.yml` (URL trong Markdown — gồm liên kết tag và so sánh phiên bản —, YAML, `CITATION.cff`, `security.txt`; GitHub chấp nhận biểu mẫu — `scripts/check-github-forms.py`; công cụ `mise.toml` có bản mới — `scripts/check-tool-versions.py`), `stale.yml`, `release.yml` (GitHub Release từ `CHANGELOG.md`).
- `scripts/validate.py` — kiểm tra mọi tệp văn bản (trừ tệp nhị phân khai báo trong `.gitattributes`): định dạng và mã hóa từng loại tệp (thụt lề chỉ bằng tab ở mọi tệp không bắt buộc dấu cách), chữ tiếng Việt dạng NFC, email chung, liên kết (cả mục `#…` theo cách GitHub tạo anchor), tiêu đề viết hoa; biểu mẫu Issue và Discussion (vị trí trong `.github/`, khóa hợp lệ, liên kết tuyệt đối); nhãn dùng trong biểu mẫu, `dependabot.yml`, `release.yml` mẫu, `labeler.yml`, `stale.yml` phải có trong `labels.yml`; Dependabot có `cooldown` ≥ 7 ngày; workflow (ghim SHA, quyền ghi chỉ ở job và có chú thích lý do, `concurrency`, `timeout-minutes`, `$default-branch` chỉ trong workflow mẫu, phiên bản công cụ chỉ từ `mise.toml`); `.prettierrc.json`, `ruff.toml`, `.editorconfig` khớp cấu hình chuẩn, `.prettierignore` không lặp `.gitignore`, ESLint (nếu repository dùng) có `eslint-config-prettier` và không bật `indent`, extension VS Code giống Dev Container; ruleset; bảng ADR khớp từng ADR; các danh sách trong `CONTRIBUTING.md`, workflow, `.editorconfig`, `.gitattributes` phải khớp nhau. Mỗi test trong `scripts/test_validate.py` cố ý làm hỏng một điểm để chứng minh luật còn hoạt động.
- `.github/`: `CODEOWNERS`, `dependabot.yml` (GitHub Actions, npm; `cooldown` 7 ngày, bản mẫu cũng vậy), `labeler.yml`, `copilot-instructions.md`.
- Công cụ: `package.json` (`devEngines`: Node.js, npm; chỉ khai báo thư viện, lệnh chạy qua `make`), `.nvmrc`, `.npmrc` (không tạo `package-lock.json`), `mise.toml` — nguồn phiên bản duy nhất cho máy cục bộ, Dev Container và CI (`jdx/mise-action`, ADR 0007), `Makefile`, `.devcontainer/` (image và feature theo `latest`, không commit `devcontainer-lock.json`), `.vscode/extensions.json`; `make hooks` cài pre-commit hook (chạy được trong git worktree), mẫu commit `.gitmessage` và `.git-blame-ignore-revs`; `.mailmap`.
- `AGENTS.md`, `CLAUDE.md` — hướng dẫn cho AI coding agent.

### ♻️ THAY ĐỔI

- Bỏ **Rebase and merge** (ADR 0011, điều chỉnh ADR 0006): GitHub tạo lại commit mà không ký được nên commit trên `main` mất chữ ký, trái quy tắc commit có chữ ký (ADR 0009). Protect Main (cả bản cấp tổ chức) chỉ cho phép Merge và Squash; `org-setup.py settings` tắt **Allow rebase merging**.
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
