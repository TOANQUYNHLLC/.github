# 🏢 CÔNG TY TNHH TOÀN QUỲNH

[![Kiểm tra repository](https://github.com/TOANQUYNHLLC/.github/actions/workflows/validate.yml/badge.svg)](https://github.com/TOANQUYNHLLC/.github/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Repository `.github` chính thức của **CÔNG TY TNHH TOÀN QUỲNH**: hồ sơ tổ chức, tệp cộng đồng mặc định và cấu hình GitHub dùng chung cho mọi repository. Giới thiệu về công ty xem tại [`profile/README.md`](profile/README.md).

---

## 🎯 MỤC ĐÍCH

- 🏢 Quản lý nội dung giới thiệu công khai của tổ chức trên GitHub.
- 📋 Chuẩn hóa biểu mẫu Issue, Pull Request và quy trình cộng tác cho mọi repository.
- 🔐 Công bố chính sách bảo mật, quy tắc ứng xử và kênh hỗ trợ dùng chung.
- ⚙️ Cung cấp workflow mẫu, bộ nhãn chuẩn và công cụ kiểm tra để các dự án nhất quán ngay từ đầu.

---

## ⚙️ CÁCH HOẠT ĐỘNG

GitHub tự động áp dụng nội dung của repository này cho toàn tổ chức:

| Nội dung                           | Hiển thị ở đâu                                                                             |
| ---------------------------------- | ------------------------------------------------------------------------------------------ |
| `profile/README.md`                | Trang giới thiệu của tổ chức trên GitHub                                                   |
| Tệp cộng đồng mặc định và biểu mẫu | Mọi repository **chưa có tệp cùng tên riêng** — tệp riêng của repository luôn được ưu tiên |
| `workflow-templates/`              | Mục _Actions → New workflow_ của mọi repository trong tổ chức                              |

`LICENSE`, `CODEOWNERS`, `dependabot.yml` và `GOVERNANCE.md` **không** được kế thừa — GitHub chỉ áp dụng làm mặc định `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `FUNDING.yml`, biểu mẫu Issue, Pull Request và Discussion; repository cần các tệp khác thì phải có tệp riêng.

---

## 📁 CẤU TRÚC REPOSITORY

**Hồ sơ tổ chức**

| Đường dẫn                                | Chức năng                                                                              |
| ---------------------------------------- | -------------------------------------------------------------------------------------- |
| [`profile/README.md`](profile/README.md) | Trang giới thiệu công khai của CÔNG TY TNHH TOÀN QUỲNH trên GitHub                     |
| [`GOVERNANCE.md`](GOVERNANCE.md)         | Vai trò, cách ra quyết định, đánh giá và hợp nhất, thay đổi người quản trị của tổ chức |

**Tệp cộng đồng mặc định** — áp dụng cho mọi repository của tổ chức

| Đường dẫn                                                      | Chức năng                                                                               |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| [`SECURITY.md`](SECURITY.md)                                   | Chính sách bảo mật và cách báo cáo lỗ hổng                                              |
| [`CONTRIBUTING.md`](CONTRIBUTING.md)                           | Hướng dẫn đóng góp: quy trình, quy ước branch, commit và Pull Request                   |
| [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)                     | Quy tắc ứng xử trong không gian cộng tác                                                |
| [`.github/FUNDING.yml`](.github/FUNDING.yml)                   | Nút **Sponsor** — hiện chưa bật, điền tài khoản tài trợ khi có                          |
| [`.github/DISCUSSION_TEMPLATE/`](.github/DISCUSSION_TEMPLATE/) | Biểu mẫu GitHub Discussions cho mục Ý tưởng, Hỏi đáp, Thảo luận chung                   |
| [`SUPPORT.md`](SUPPORT.md)                                     | Kênh hỗ trợ: đặt câu hỏi, báo lỗi, đề xuất, bảo mật và liên hệ                          |
| [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/)           | Biểu mẫu Issue dạng form (báo lỗi, đề xuất tính năng, câu hỏi) và cấu hình `config.yml` |
| [`PULL_REQUEST_TEMPLATE.md`](PULL_REQUEST_TEMPLATE.md)         | Biểu mẫu Pull Request: tóm tắt thay đổi, kiểm thử, rủi ro và checklist                  |

**Tài nguyên dùng chung**

| Đường dẫn                                          | Chức năng                                                                                                                                                                                                                                                      |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`workflow-templates/`](workflow-templates/)       | Workflow mẫu: Node.js CI, Python CI, Go CI, CodeQL, rà soát dependency, Docker image, tạo GitHub Release, kiểm tra tiêu đề PR và tên branch, gắn nhãn Pull Request, đóng mục không hoạt động, kiểm tra tài liệu                                                |
| [`rulesets/`](rulesets/)                           | Ruleset **Protect Main** (`protect-main.json`) cho nhánh chính — Pull Request bắt buộc, phê duyệt, kiểm tra tự động, commit có chữ ký — và **Protect Release Tags** (`protect-release-tags.json`) chặn tạo, dời, xóa tag `v*`; đặt ở cấp repository (gói Free) |
| [`repository-templates/`](repository-templates/)   | Mẫu cho từng repository: `CODEOWNERS`, `dependabot.yml`, `release.yml`, tệp định dạng theo ngôn ngữ (Rust, C/C++, Python), `.dockerignore`, `.env.example`, `PRIVACY.md`                                                                                       |
| [`labels.yml`](labels.yml)                         | Bộ 41 nhãn chuẩn: 9 nhãn mặc định của GitHub, loại thay đổi (khớp tiền tố branch), phạm vi (`area: …`), mức độ ưu tiên, trạng thái xử lý (`needs triage`, `pinned`…), nhãn Dependabot theo ecosystem                                                           |
| [`scripts/sync-labels.sh`](scripts/sync-labels.sh) | Đồng bộ `labels.yml` lên các repository bằng GitHub CLI (mặc định chỉ xem trước)                                                                                                                                                                               |

**Cấu hình của repository này**

| Đường dẫn                                                                                                                                                                                                                                                             | Chức năng                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`.github/workflows/validate.yml`](.github/workflows/validate.yml)                                                                                                                                                                                                    | CI: kiểm tra nội dung, chạy test, `prettier --check`, ESLint, `ruff format --check`, `ruff check`, shellcheck, actionlint                                                                                                                                                                                                                                                                                                                                      |
| [`.github/workflows/branch-name.yml`](.github/workflows/branch-name.yml)                                                                                                                                                                                              | Bắt buộc tên branch của Pull Request theo quy ước `<tiền tố>/<mô_tả>`                                                                                                                                                                                                                                                                                                                                                                                          |
| [`.github/workflows/pr-title.yml`](.github/workflows/pr-title.yml)                                                                                                                                                                                                    | Bắt buộc tiêu đề Pull Request theo quy ước commit (`feat:`, `fix:`…)                                                                                                                                                                                                                                                                                                                                                                                           |
| [`.github/workflows/release.yml`](.github/workflows/release.yml)                                                                                                                                                                                                      | Gắn tag `v*` là tự tạo GitHub Release với nội dung lấy từ `CHANGELOG.md`                                                                                                                                                                                                                                                                                                                                                                                       |
| [`.github/workflows/links.yml`](.github/workflows/links.yml)                                                                                                                                                                                                          | Hằng tuần: kiểm tra liên kết bên ngoài (website, Facebook…), GitHub chấp nhận biểu mẫu, công cụ trong `mise.toml` có bản mới                                                                                                                                                                                                                                                                                                                                   |
| [`.github/workflows/codeql.yml`](.github/workflows/codeql.yml)                                                                                                                                                                                                        | Quét bảo mật CodeQL cho workflow, JavaScript và Python khi push, mở Pull Request và hằng tuần                                                                                                                                                                                                                                                                                                                                                                  |
| [`.github/workflows/dependency-review.yml`](.github/workflows/dependency-review.yml)                                                                                                                                                                                  | Chặn Pull Request thêm dependency có lỗ hổng mức cao trở lên                                                                                                                                                                                                                                                                                                                                                                                                   |
| [`.github/workflows/stale.yml`](.github/workflows/stale.yml)                                                                                                                                                                                                          | Hằng tuần đánh dấu và đóng Issue, Pull Request không hoạt động                                                                                                                                                                                                                                                                                                                                                                                                 |
| [`.github/workflows/labeler.yml`](.github/workflows/labeler.yml) · [`.github/labeler.yml`](.github/labeler.yml)                                                                                                                                                       | Tự gắn nhãn loại cho Pull Request theo tiền tố branch (và `ci`, `tests` theo tệp thay đổi)                                                                                                                                                                                                                                                                                                                                                                     |
| [`.github/copilot-instructions.md`](.github/copilot-instructions.md)                                                                                                                                                                                                  | Hướng dẫn cho GitHub Copilot khi đánh giá Pull Request                                                                                                                                                                                                                                                                                                                                                                                                         |
| [`.github/release.yml`](.github/release.yml)                                                                                                                                                                                                                          | Nhóm nội dung GitHub Release tự tạo theo nhãn                                                                                                                                                                                                                                                                                                                                                                                                                  |
| [`.github/dependabot.yml`](.github/dependabot.yml)                                                                                                                                                                                                                    | Tự động đề xuất cập nhật các GitHub Action đang ghim theo commit SHA và công cụ Node.js (chờ 7 ngày sau khi phát hành — `cooldown`)                                                                                                                                                                                                                                                                                                                            |
| [`.github/CODEOWNERS`](.github/CODEOWNERS)                                                                                                                                                                                                                            | Người quản trị bắt buộc duyệt mọi thay đổi                                                                                                                                                                                                                                                                                                                                                                                                                     |
| [`scripts/validate.py`](scripts/validate.py)                                                                                                                                                                                                                          | Kiểm tra liên kết, tiêu đề viết hoa, nhãn (cả trong `dependabot.yml`, `release.yml`, `stale.yml`, `labeler.yml`), biểu mẫu Issue và Discussion (vị trí trong `.github/`, khóa GitHub chấp nhận, liên kết tuyệt đối), workflow (SHA, quyền, `$default-branch`), ruleset, bảng ADR, cấu hình Prettier/ruff/EditorConfig chuẩn, quy ước commit và branch khớp `CONTRIBUTING.md`, định dạng file, email chung, `security.txt`, `CHANGELOG.md` và mẫu email bảo mật |
| [`scripts/test_validate.py`](scripts/test_validate.py)                                                                                                                                                                                                                | Test tự động: mỗi test cố ý làm hỏng một điểm để chứng minh luật tương ứng còn hoạt động; luật mới cần kèm test                                                                                                                                                                                                                                                                                                                                                |
| [`scripts/org-setup.py`](scripts/org-setup.py)                                                                                                                                                                                                                        | Áp dụng cấu hình chung lên mọi repository bằng GitHub CLI: Pull Request thêm tệp dùng chung, cách hợp nhất, ruleset, team maintainers (mặc định chỉ xem trước)                                                                                                                                                                                                                                                                                                 |
| [`scripts/pre-commit.sh`](scripts/pre-commit.sh)                                                                                                                                                                                                                      | Pre-commit hook kiểm tra định dạng file được stage bằng Prettier và ruff (cài bằng `make hooks`)                                                                                                                                                                                                                                                                                                                                                               |
| [`scripts/release-notes.py`](scripts/release-notes.py) · [`scripts/check-external-links.py`](scripts/check-external-links.py) · [`scripts/check-github-forms.py`](scripts/check-github-forms.py) · [`scripts/check-tool-versions.py`](scripts/check-tool-versions.py) | Tách nội dung phát hành từ `CHANGELOG.md`; kiểm tra liên kết bên ngoài; kiểm tra GitHub chấp nhận biểu mẫu (lỗi khóa chỉ hiện trên trang xem tệp); báo công cụ trong `mise.toml` có bản mới                                                                                                                                                                                                                                                                    |
| [`.well-known/security.txt`](.well-known/security.txt)                                                                                                                                                                                                                | Tệp `security.txt` (RFC 9116), đăng tại `https://toanquynh.com/.well-known/security.txt` — cập nhật tệp trên website mỗi khi sửa                                                                                                                                                                                                                                                                                                                               |
| [`Makefile`](Makefile)                                                                                                                                                                                                                                                | Lệnh chạy kiểm tra cục bộ giống CI — gõ `make` để xem danh sách                                                                                                                                                                                                                                                                                                                                                                                                |
| [`.editorconfig`](.editorconfig) · [`.prettierrc.json`](.prettierrc.json) · [`.prettierignore`](.prettierignore) · [`ruff.toml`](ruff.toml)                                                                                                                           | Quy tắc định dạng: tab độ rộng 4; chỉ ngôn ngữ bắt buộc dấu cách mới dùng dấu cách (4, hoặc 2 nếu formatter chính thức bắt buộc); UTF-8, LF (trừ file bắt buộc CRLF)                                                                                                                                                                                                                                                                                           |
| [`eslint.config.js`](eslint.config.js) · [`package.json`](package.json) · [`.nvmrc`](.nvmrc)                                                                                                                                                                          | ESLint (`defineConfig`, bỏ qua theo `.gitignore`, tắt quy tắc định dạng bằng `eslint-config-prettier`), công cụ Node.js; `devEngines` chặn Node.js, npm sai phiên bản                                                                                                                                                                                                                                                                                          |
| [`.gitattributes`](.gitattributes) · [`.gitignore`](.gitignore)                                                                                                                                                                                                       | Chuẩn hoá xuống dòng LF, bỏ qua file tạm và `node_modules/`                                                                                                                                                                                                                                                                                                                                                                                                    |
| [`MAINTAINERS.md`](MAINTAINERS.md) · [`ROADMAP.md`](ROADMAP.md)                                                                                                                                                                                                       | Người quản trị hiện tại; các việc dự kiến                                                                                                                                                                                                                                                                                                                                                                                                                      |
| [`AGENTS.md`](AGENTS.md)                                                                                                                                                                                                                                              | Hướng dẫn cho AI coding agent: lệnh kiểm tra, quy ước bắt buộc, những điều không được làm                                                                                                                                                                                                                                                                                                                                                                      |
| [`.vscode/extensions.json`](.vscode/extensions.json)                                                                                                                                                                                                                  | Gợi ý extension VS Code: EditorConfig, Prettier, ESLint, ruff, ShellCheck, GitHub Actions, YAML                                                                                                                                                                                                                                                                                                                                                                |
| [`CITATION.cff`](CITATION.cff) · [`NOTICE`](NOTICE)                                                                                                                                                                                                                   | Cách trích dẫn repository; ghi chú bản quyền và giấy phép công cụ bên thứ ba                                                                                                                                                                                                                                                                                                                                                                                   |
| [`docs/adr/`](docs/adr/)                                                                                                                                                                                                                                              | Bản ghi quyết định kiến trúc: thụt lề bằng tab, LF/CRLF, tên branch, ruleset Protect Main, cách hợp nhất, nguồn phiên bản công cụ, ruleset tag phát hành                                                                                                                                                                                                                                                                                                       |
| [`.devcontainer/`](.devcontainer/) · [`mise.toml`](mise.toml)                                                                                                                                                                                                         | Nguồn phiên bản duy nhất của ruff, ShellCheck, actionlint (Node.js lấy từ `.nvmrc`) cho máy cục bộ, Dev Container và CI                                                                                                                                                                                                                                                                                                                                        |
| [`.git-blame-ignore-revs`](.git-blame-ignore-revs) · [`.mailmap`](.mailmap)                                                                                                                                                                                           | `git blame` bỏ qua commit chỉ đổi định dạng; gộp các cách viết tên tác giả                                                                                                                                                                                                                                                                                                                                                                                     |
| [`.shellcheckrc`](.shellcheckrc) · [`CLAUDE.md`](CLAUDE.md)                                                                                                                                                                                                           | Cấu hình ShellCheck; Claude Code dùng chung hướng dẫn trong `AGENTS.md`                                                                                                                                                                                                                                                                                                                                                                                        |
| [`.gitmessage`](.gitmessage) · [`.npmrc`](.npmrc)                                                                                                                                                                                                                     | Mẫu commit theo quy ước (bật bằng `make hooks`); npm ghi phiên bản thư viện chính xác, không tạo `package-lock.json`                                                                                                                                                                                                                                                                                                                                           |
| [`CHANGELOG.md`](CHANGELOG.md)                                                                                                                                                                                                                                        | Nhật ký thay đổi của repository này, theo phiên bản                                                                                                                                                                                                                                                                                                                                                                                                            |
| [`LICENSE`](LICENSE)                                                                                                                                                                                                                                                  | Giấy phép MIT cho nội dung của repository này                                                                                                                                                                                                                                                                                                                                                                                                                  |

---

## 🛠️ PHÁT TRIỂN CỤC BỘ

Cài công cụ đúng phiên bản trong [`mise.toml`](mise.toml) và [`.nvmrc`](.nvmrc) — cùng phiên bản với CI:

```bash
mise install
npm install
make hooks
```

**Quy tắc định dạng** (khai báo trong [`.editorconfig`](.editorconfig) và [`.prettierrc.json`](.prettierrc.json), kiểm tra tự động bằng `make check`):

- Thụt lề bằng **tab thật**, độ rộng tab **4**; không dùng độ rộng 2.
- Chỉ ngôn ngữ **bắt buộc dấu cách** mới dùng dấu cách: **4 dấu cách** cho YAML (cả `.cff`), Markdown (Prettier luôn thụt lề danh sách bằng dấu cách), F#, Elm, Nim, Zig; **2 dấu cách** cho ngôn ngữ có formatter chính thức cố định độ rộng 2 — Dart, Elixir, Terraform, Crystal, Gleam, Nix. Mọi ngôn ngữ khác, kể cả Python và `Makefile`, dùng tab.
- Xuống dòng **LF**; chỉ file bắt buộc **CRLF** mới dùng CRLF: batch script (`.bat`, `.cmd`), Visual Studio/Visual C++ (`.sln`, `*proj`, `.dsp`, `.dsw`), registry/INF (`.reg`, `.inf`, UTF-16 LE), chuẩn MIME/iCalendar/vCard/CSV (`.eml`, `.mht`, `.ics`, `.vcs`, `.vcf`, `.csv`).
- Formatter: **Prettier** cho JavaScript, JSON, YAML, Markdown; **ruff** cho Python. ESLint chỉ kiểm tra chất lượng mã — mọi quy tắc định dạng của ESLint được tắt bằng `eslint-config-prettier`.
- UTF-8, xuống dòng LF, có dòng trống cuối file.
- Định dạng lại toàn bộ: `make format`.

Chạy toàn bộ kiểm tra giống CI trước khi tạo Pull Request:

```bash
make check
```

| Lệnh                       | Tác dụng                                                                                            |
| -------------------------- | --------------------------------------------------------------------------------------------------- |
| `make`                     | Xem danh sách lệnh                                                                                  |
| `make validate`            | Kiểm tra nội dung bằng `scripts/validate.py`                                                        |
| `make test`                | Chạy test tự động của các script kiểm tra                                                           |
| `make format`              | Định dạng lại toàn bộ bằng Prettier và ruff                                                         |
| `make format-check`        | Kiểm tra định dạng giống CI                                                                         |
| `make lint`                | ESLint, ruff check, shellcheck và actionlint                                                        |
| `make links`               | Kiểm tra liên kết bên ngoài còn hoạt động                                                           |
| `make versions`            | Báo công cụ trong `mise.toml` có bản phát hành mới hơn                                              |
| `make forms REF=…`         | Kiểm tra GitHub chấp nhận biểu mẫu Issue, Discussion trên một branch (mặc định `main`)              |
| `make release-notes TAG=…` | Xem trước nội dung GitHub Release của một tag                                                       |
| `make labels-preview`      | Xem trước việc đồng bộ nhãn lên các repository                                                      |
| `make labels-apply`        | Đồng bộ nhãn (cần GitHub CLI và quyền quản trị)                                                     |
| `make hooks`               | Cài pre-commit hook, mẫu commit `.gitmessage`, cấu hình `git blame` bỏ qua commit chỉ đổi định dạng |
| `make org-preview`         | Xem trước việc áp dụng cấu hình chung lên mọi repository (cần GitHub CLI)                           |

---

## 📝 QUẢN LÝ VÀ CẬP NHẬT

Các nội dung trong repository này được quản lý bởi những thành viên có thẩm quyền của CÔNG TY TNHH TOÀN QUỲNH. Mọi thay đổi đi qua Pull Request theo [`CONTRIBUTING.md`](CONTRIBUTING.md) và cần người quản trị duyệt.

Khi cập nhật nội dung, cần bảo đảm:

- Thông tin chính xác và phù hợp với định hướng của công ty.
- Không công khai dữ liệu cá nhân, thông tin y tế hoặc thông tin nội bộ.
- Không lưu trữ mật khẩu, mã truy cập, khóa API hoặc dữ liệu bảo mật.
- `make check` chạy thành công trước khi đưa lên nhánh chính.
- Các thay đổi quan trọng phải có mô tả rõ ràng trong commit hoặc Pull Request, và được ghi vào [`CHANGELOG.md`](CHANGELOG.md).
- Tuân thủ quy định pháp luật và các chính sách của GitHub.

---

## 🚀 PHÁT HÀNH

1. Chuyển nội dung mục **CHƯA PHÁT HÀNH** trong [`CHANGELOG.md`](CHANGELOG.md) thành phiên bản mới, ví dụ `## [v2026.10.Stable] — 2026-10-01`, rồi tạo lại mục **CHƯA PHÁT HÀNH** trống.
2. Kiểm tra trước nội dung: `make release-notes TAG=v2026.10.Stable`.
3. Người quản trị gắn và đẩy tag (ruleset **Protect Release Tags** chỉ cho người quản trị tạo tag `v*`): `git tag v2026.10.Stable && git push origin v2026.10.Stable` — workflow tự tạo GitHub Release; khi GitHub Actions tắt, tạo bằng `gh release create v2026.10.Stable --notes-file <(python3 scripts/release-notes.py v2026.10.Stable) --verify-tag`.

---

## 🔐 BẢO MẬT

Nếu phát hiện lỗ hổng hoặc vấn đề liên quan đến bảo mật, vui lòng **không đăng tải công khai** trong Issues, Discussions hoặc Pull Requests. Cách báo cáo riêng, thông tin cần cung cấp và cam kết xử lý được quy định tại [`SECURITY.md`](SECURITY.md).

> ⚠️ Không gửi mật khẩu, khóa API, token truy cập, dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế nhạy cảm qua bất kỳ kênh công khai nào.

---

## 📞 LIÊN HỆ

- 📧 **Email:** [toanquynhvn@gmail.com](mailto:toanquynhvn@gmail.com)
- 🌐 **Website:** [https://toanquynh.com](https://toanquynh.com)
- 🏢 **Thông tin đầy đủ:** [`profile/README.md`](profile/README.md#-thông-tin-liên-hệ)

---

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Repository quản lý hồ sơ và cấu hình GitHub của tổ chức.
</p>
