# 🏢 CÔNG TY TNHH TOÀN QUỲNH

[![Checks](https://img.shields.io/github/actions/workflow/status/TOANQUYNHLLC/.github/validate.yml?branch=main&label=Checks&logo=githubactions&logoColor=white)](https://github.com/TOANQUYNHLLC/.github/blob/main/.github/workflows/validate.yml)
[![CodeQL](https://img.shields.io/github/actions/workflow/status/TOANQUYNHLLC/.github/codeql.yml?branch=main&label=CodeQL&logo=github&logoColor=white)](https://github.com/TOANQUYNHLLC/.github/blob/main/.github/workflows/codeql.yml)
[![Release](https://img.shields.io/github/v/release/TOANQUYNHLLC/.github?label=Release&logo=github)](https://github.com/TOANQUYNHLLC/.github/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/TOANQUYNHLLC/.github/main?label=Last%20Commit&logo=git&logoColor=white)](https://github.com/TOANQUYNHLLC/.github/commits/main)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-fe5196?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org/en/v1.0.0/)
[![Code Style: Prettier](https://img.shields.io/badge/Code%20Style-Prettier-ff69b4?logo=prettier&logoColor=white)](https://prettier.io)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?logo=opensourceinitiative&logoColor=white)](LICENSE)

Repository `.github` chính thức của **CÔNG TY TNHH TOÀN QUỲNH**: hồ sơ tổ chức, tệp cộng đồng mặc định và cấu hình GitHub dùng chung cho mọi repository. Giới thiệu về công ty xem tại [`profile/README.md`](profile/README.md).

---

## 🎯 MỤC ĐÍCH

- 🏢 Quản lý nội dung giới thiệu công khai của tổ chức trên GitHub.
- 📋 Chuẩn hóa biểu mẫu Issue, Pull Request và quy trình cộng tác cho mọi repository.
- 🔐 Công bố chính sách bảo mật, quy tắc ứng xử và kênh hỗ trợ dùng chung.
- ⚙️ Cung cấp workflow mẫu, bộ nhãn chuẩn, ruleset và công cụ kiểm tra để các dự án nhất quán ngay từ đầu.

---

## ⚙️ CÁCH HOẠT ĐỘNG

GitHub tự động áp dụng nội dung của repository này cho toàn tổ chức:

| Nội dung                           | Hiển thị ở đâu                                                                             |
| ---------------------------------- | ------------------------------------------------------------------------------------------ |
| `profile/README.md`                | Trang giới thiệu của tổ chức trên GitHub                                                   |
| Tệp cộng đồng mặc định và biểu mẫu | Mọi repository **chưa có tệp cùng tên riêng** — tệp riêng của repository luôn được ưu tiên |
| `workflow-templates/`              | Mục _Actions → New workflow_ của mọi repository trong tổ chức                              |

GitHub chỉ kế thừa `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `ACCESSIBILITY.md`, `FUNDING.yml`, `VULNERABILITY_REPORT.yml` và các biểu mẫu Issue, Pull Request, Discussion (repository này dùng bốn tệp đầu và các biểu mẫu). `LICENSE`, `CODEOWNERS`, `dependabot.yml`, `GOVERNANCE.md` **không** được kế thừa — mỗi repository cần tệp riêng, lấy từ [`repository-templates/`](repository-templates/).

---

## 📁 CẤU TRÚC REPOSITORY

**Hồ sơ và quản trị tổ chức**

| Đường dẫn                                              | Chức năng                                                                                         |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| [`profile/README.md`](profile/README.md)               | Trang giới thiệu công khai của CÔNG TY TNHH TOÀN QUỲNH trên GitHub                                |
| [`GOVERNANCE.md`](GOVERNANCE.md)                       | Vai trò, cách ra quyết định, đánh giá và hợp nhất, thay đổi người quản trị                        |
| [`MAINTAINERS.md`](MAINTAINERS.md)                     | Người quản trị và các team của tổ chức                                                            |
| [`ROADMAP.md`](ROADMAP.md)                             | Việc dự kiến: thiết lập repository mới, cài đặt tổ chức chỉ làm được trên web                     |
| [`.well-known/security.txt`](.well-known/security.txt) | Liên hệ bảo mật của tổ chức (RFC 9116), đăng tại `https://toanquynh.com/.well-known/security.txt` |

**Tệp cộng đồng mặc định** — áp dụng cho mọi repository của tổ chức

| Đường dẫn                                                              | Chức năng                                                                  |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| [`CONTRIBUTING.md`](CONTRIBUTING.md)                                   | Quy trình đóng góp, quy ước branch, commit và Pull Request                 |
| [`SECURITY.md`](SECURITY.md)                                           | Chính sách bảo mật và cách báo cáo lỗ hổng                                 |
| [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)                             | Quy tắc ứng xử trong không gian cộng tác                                   |
| [`SUPPORT.md`](SUPPORT.md)                                             | Kênh hỗ trợ: đặt câu hỏi, báo lỗi, đề xuất, bảo mật và liên hệ             |
| [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/)                   | Biểu mẫu Issue: báo lỗi, đề xuất tính năng, câu hỏi; cấu hình `config.yml` |
| [`.github/DISCUSSION_TEMPLATE/`](.github/DISCUSSION_TEMPLATE/)         | Biểu mẫu Discussions: Ý tưởng, Hỏi đáp, Thảo luận chung                    |
| [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) | Biểu mẫu Pull Request: tóm tắt thay đổi, kiểm thử, rủi ro và checklist     |

**Tài nguyên dùng chung cho các repository**

| Đường dẫn                                        | Chức năng                                                                                                                                                                                                                                                                                   |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`workflow-templates/`](workflow-templates/)     | Workflow mẫu: Node.js CI, Python CI, Go CI, CodeQL, rà soát dependency, Docker image, tạo GitHub Release, kiểm tra tiêu đề Pull Request và tên branch, gắn nhãn, đóng mục không hoạt động, kiểm tra tài liệu. Kiểm tra gọi script của tổ chức (checkout `TOANQUYNHLLC/.github` vào `.org/`) |
| [`repository-templates/`](repository-templates/) | Tệp riêng cho từng repository: `CODEOWNERS`, `dependabot.yml`, `release.yml`, `labeler.yml`, cấu hình định dạng, phiên bản theo ngôn ngữ, `.dockerignore`, `.env.example`, `PRIVACY.md`                                                                                                     |
| [`rulesets/`](rulesets/)                         | Ruleset **Protect Main**, **Protect Release Tags** (cấp repository) và bản cấp tổ chức, push ruleset **Protect Pushes** — xem [`rulesets/README.md`](rulesets/README.md)                                                                                                                    |
| [`labels.yml`](labels.yml)                       | Bộ nhãn chuẩn: nhãn mặc định của GitHub, loại thay đổi (khớp tiền tố branch), phạm vi `area: …`, mức độ ưu tiên, trạng thái xử lý, nhãn Dependabot                                                                                                                                          |

**Workflow của repository này** — huy hiệu **Checks**, **CodeQL** ở đầu trang hiển thị kết quả lượt chạy gần nhất của `validate.yml`, `codeql.yml` trên `main`; bấm vào mở tệp workflow trên cùng nhánh. Khi GitHub Actions tắt, huy hiệu giữ kết quả lượt cuối và không xác nhận các commit mới. `make check` chạy các nhóm kiểm tra tại máy qua hook `pre-push`; CodeQL cần GitHub Actions. Quy trình khi Actions tắt xem mục **PHÁT HÀNH**.

Workflow gắn nhãn dùng `pull_request_target` theo [hướng dẫn của actions/labeler](https://github.com/actions/labeler#recommended-permissions) để xử lý cả Pull Request từ fork: chỉ đọc metadata và cấu hình của nhánh đích qua API. Quyền ghi nằm ở job gắn nhãn; workflow không checkout hay chạy mã của Pull Request. Nhóm concurrency dùng số Pull Request để các PR không hủy lượt chạy của nhau. Workflow mẫu gắn nhãn dùng cùng cách này.

| Đường dẫn                                                                                                                                     | Chức năng                                                                                                                           |
| --------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| [`.github/workflows/validate.yml`](.github/workflows/validate.yml)                                                                            | Mỗi job gọi một nhóm của `scripts/check.py`: `content` (validate, test), `format` (Prettier, ruff), `lint` (shellcheck, actionlint) |
| [`.github/workflows/branch-name.yml`](.github/workflows/branch-name.yml) · [`.github/workflows/pr-title.yml`](.github/workflows/pr-title.yml) | Tên branch và tiêu đề Pull Request theo quy ước — gọi `scripts/conventions.py`                                                      |
| [`.github/workflows/labeler.yml`](.github/workflows/labeler.yml)                                                                              | Gắn nhãn Pull Request theo tiền tố branch và tệp thay đổi ([`.github/labeler.yml`](.github/labeler.yml))                            |
| [`.github/workflows/dependency-review.yml`](.github/workflows/dependency-review.yml)                                                          | Chặn Pull Request thêm dependency có lỗ hổng mức cao trở lên                                                                        |
| [`.github/workflows/codeql.yml`](.github/workflows/codeql.yml)                                                                                | Quét bảo mật CodeQL cho workflow và Python khi push, mở Pull Request và hằng tuần                                                   |
| [`.github/workflows/monthly-release.yml`](.github/workflows/monthly-release.yml)                                                              | Ngày 1 hằng tháng: mở Pull Request phát hành nếu có commit mới (mục [PHÁT HÀNH](#-phát-hành))                                       |
| [`.github/workflows/release.yml`](.github/workflows/release.yml)                                                                              | Gắn tag `Stable.v*`, `Beta.v*` hoặc `v*` thì tạo GitHub Release từ `CHANGELOG.md`                                                   |
| [`.github/workflows/links.yml`](.github/workflows/links.yml)                                                                                  | Hằng tuần: liên kết bên ngoài, GitHub chấp nhận biểu mẫu, công cụ trong `mise.toml` có bản mới                                      |
| [`.github/workflows/stale.yml`](.github/workflows/stale.yml)                                                                                  | Hằng tuần đánh dấu và đóng Issue, Pull Request không hoạt động                                                                      |
| [`.github/dependabot.yml`](.github/dependabot.yml)                                                                                            | Đề xuất cập nhật GitHub Action (ghim theo commit SHA) và Prettier, chờ 7 ngày sau khi phát hành (`cooldown`)                        |
| [`.github/CODEOWNERS`](.github/CODEOWNERS)                                                                                                    | Team người quản trị duyệt mọi thay đổi                                                                                              |

**Script** — mọi kiểm tra chạy tại máy giống GitHub Actions

| Đường dẫn                                                                                 | Chức năng                                                                                                                                                                                                                                                                                                       |
| ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`scripts/check.py`](scripts/check.py)                                                    | Nguồn duy nhất của các nhóm kiểm tra (`content`, `format`, `lint`, `conventions`, `audit`); `make check` và `validate.yml` cùng gọi, các nhóm chạy song song                                                                                                                                                    |
| [`scripts/validate.py`](scripts/validate.py)                                              | Định dạng, mã hóa, xuống dòng từng loại tệp; liên kết nội bộ; tiêu đề viết hoa; chữ huy hiệu tiếng Anh, hoa đầu mỗi từ; biểu mẫu; nhãn; workflow; ruleset; bảng ADR và đủ mục của từng ADR; tên tự đặt camelCase; tài liệu khớp code; các danh sách phải khớp nhau; email chung; `security.txt`; `CHANGELOG.md` |
| [`scripts/run-tests.py`](scripts/run-tests.py)                                            | Chạy test song song trên mọi lõi CPU (`make test`, `make check`)                                                                                                                                                                                                                                                |
| [`scripts/conventions.py`](scripts/conventions.py)                                        | Tên branch, tiêu đề commit và Pull Request (workflow của repository này và workflow mẫu)                                                                                                                                                                                                                        |
| [`scripts/git-hooks.py`](scripts/git-hooks.py)                                            | Git hook: `pre-commit`, `pre-push`, `post-merge`, `post-rewrite` (mục [PHÁT TRIỂN CỤC BỘ](#️-phát-triển-cục-bộ))                                                                                                                                                                                                 |
| [`scripts/release.py`](scripts/release.py)                                                | Phát hành từ `CHANGELOG.md`: xem trước nội dung, chuẩn bị phiên bản của tháng, mở Pull Request phát hành, tạo GitHub Release                                                                                                                                                                                    |
| [`scripts/org-setup.py`](scripts/org-setup.py) · [`scripts/orgsetup/`](scripts/orgsetup/) | Áp dụng cấu hình chung lên mọi repository bằng GitHub CLI: tệp dùng chung, cài đặt, ruleset, team, nhãn, cài đặt tổ chức; mặc định chỉ xem trước — mỗi nhóm lệnh một module trong `orgsetup/`                                                                                                                   |
| [`scripts/check-markdown-links.py`](scripts/check-markdown-links.py)                      | Liên kết nội bộ trong Markdown (dùng chung với `validate.py` và workflow mẫu `docs-check.yml`)                                                                                                                                                                                                                  |
| [`scripts/markdown.py`](scripts/markdown.py)                                              | Bỏ nội dung mã trong Markdown, dùng chung cho kiểm tra liên kết nội bộ, liên kết bên ngoài, tiêu đề và thụt lề                                                                                                                                                                                                  |
| [`scripts/check-gofmt.py`](scripts/check-gofmt.py)                                        | Định dạng Go cho workflow mẫu `go-ci.yml`                                                                                                                                                                                                                                                                       |
| [`scripts/check-external-links.py`](scripts/check-external-links.py)                      | Liên kết bên ngoài còn hoạt động; bản `security.txt` trên website khớp repository                                                                                                                                                                                                                               |
| [`scripts/check-github-forms.py`](scripts/check-github-forms.py)                          | GitHub chấp nhận biểu mẫu Issue, Discussion (lỗi khóa chỉ hiện trên trang xem tệp)                                                                                                                                                                                                                              |
| [`scripts/check-tool-versions.py`](scripts/check-tool-versions.py)                        | Công cụ trong `mise.toml` có bản phát hành mới hơn                                                                                                                                                                                                                                                              |
| [`scripts/test_*.py`](scripts/) · [`scripts/testsupport.py`](scripts/testsupport.py)      | Test tự động, mỗi script một tệp; mỗi luật của `validate.py` có test cố ý làm hỏng một điểm để chứng minh luật còn hoạt động                                                                                                                                                                                    |

**Cấu hình và công cụ phát triển**

| Đường dẫn                                                                                                                                   | Chức năng                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| [`Makefile`](Makefile)                                                                                                                      | Lệnh chạy kiểm tra cục bộ — gõ `make` để xem danh sách                                                              |
| [`mise.toml`](mise.toml) · [`.nvmrc`](.nvmrc) · [`package.json`](package.json)                                                              | Nguồn phiên bản duy nhất: Python, ruff, ShellCheck, actionlint; Node.js; Prettier (`devEngines` chặn phiên bản sai) |
| [`.editorconfig`](.editorconfig) · [`.prettierrc.json`](.prettierrc.json) · [`.prettierignore`](.prettierignore) · [`ruff.toml`](ruff.toml) | Quy tắc định dạng (mục [PHÁT TRIỂN CỤC BỘ](#️-phát-triển-cục-bộ))                                                    |
| [`.gitattributes`](.gitattributes) · [`.gitignore`](.gitignore)                                                                             | Xuống dòng theo loại tệp, tệp nhị phân; bỏ qua tệp tạm, `node_modules/`, bí mật                                     |
| [`.devcontainer/`](.devcontainer/) · [`.vscode/extensions.json`](.vscode/extensions.json)                                                   | Dev Container cài công cụ từ `mise.toml`; extension VS Code giống nhau ở cả hai nơi                                 |
| [`.gitmessage`](.gitmessage) · [`.git-blame-ignore-revs`](.git-blame-ignore-revs) · [`.mailmap`](.mailmap)                                  | Mẫu commit theo quy ước; `git blame` bỏ qua commit chỉ đổi định dạng; gộp các cách viết tên tác giả                 |
| [`.npmrc`](.npmrc) · [`.shellcheckrc`](.shellcheckrc)                                                                                       | npm ghi phiên bản chính xác, không tạo `package-lock.json`; cấu hình ShellCheck                                     |
| [`CITATION.cff`](CITATION.cff)                                                                                                              | Cách trích dẫn repository; từ khóa là nguồn của topics trên GitHub                                                  |

**Tài liệu cho người phát triển**

| Đường dẫn                                                                                                                  | Chức năng                                                                                                           |
| -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| [`docs/adr/`](docs/adr/)                                                                                                   | Bản ghi các quyết định kiến trúc đang có hiệu lực và lý do                                                          |
| [`AGENTS.md`](AGENTS.md) · [`CLAUDE.md`](CLAUDE.md) · [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | Hướng dẫn cho AI coding agent và GitHub Copilot                                                                     |
| [`JobsGuideLine.md`](JobsGuideLine.md)                                                                                     | Yêu cầu chuẩn cho một đợt rà soát toàn dự án: phạm vi, cách kiểm chứng, điều kiện hoàn tất và nội dung Pull Request |
| [`CHANGELOG.md`](CHANGELOG.md)                                                                                             | Khung nội dung chuẩn bị phát hành                                                                                   |
| [`LICENSE`](LICENSE)                                                                                                       | Giấy phép MIT cho nội dung của repository này                                                                       |

---

## 🛠️ PHÁT TRIỂN CỤC BỘ

Cài công cụ đúng phiên bản trong [`mise.toml`](mise.toml) và [`.nvmrc`](.nvmrc) — ruff, ShellCheck, actionlint, Node.js cùng phiên bản với CI (CI dùng Python có sẵn của runner, script cần ≥ 3.11) — rồi cài git hook:

```bash
mise install
make hooks
```

Không dùng mise thì cài Node.js đúng bản trong `.nvmrc` (ví dụ `brew install node@24` rồi đưa `$(brew --prefix node@24)/bin` lên đầu `PATH`): `devEngines` của `package.json` làm npm báo `EBADDEVENGINES` và dừng khi Node.js khác bản này. Thư viện Node.js (Prettier) tự cài khi chạy kiểm tra lần đầu. Git hook ([`scripts/git-hooks.py`](scripts/git-hooks.py)) chạy tự động:

- `git commit`: Prettier, `ruff format`, `ruff check` trên đúng phần đã stage, dùng cấu hình trong Git index kể cả khi bản trên đĩa đã bị xóa; không xuất được nội dung đã stage hoặc kiểm tra lỗi thì không commit.
- `git push` một branch: `make check` trên đúng nội dung được đẩy — commit hết hoặc `git stash -u` trước; lỗi thì không đẩy; chỉ đẩy tag thì bỏ qua.
- `git pull` (cả `--rebase`): chạy song song `make org-preview` (so cài đặt trên GitHub với code), `make links`, `make versions` — chỉ báo, không chặn.

**Quy tắc định dạng** (khai báo trong [`.editorconfig`](.editorconfig), [`.prettierrc.json`](.prettierrc.json), [`ruff.toml`](ruff.toml); `make check` kiểm tra):

- Thụt lề bằng **tab**, độ rộng **4**, kể cả Python và `Makefile`.
- Chỉ ngôn ngữ **bắt buộc dấu cách** mới dùng dấu cách: **4** cho YAML (cả `.cff`), Markdown, F#, Elm, Nim, Zig; **2** cho Dart, Elixir, Terraform, Crystal, Gleam, Nix (formatter chính thức cố định độ rộng 2).
- UTF-8, xuống dòng **LF**, có dòng trống cuối tệp; **CRLF** chỉ cho tệp bắt buộc: batch script, dự án Visual Studio/Visual C++, registry/INF (UTF-16 LE), MIME/iCalendar/vCard/CSV.
- Formatter: **Prettier** cho JSON, YAML, Markdown; **ruff** cho Python. Định dạng lại toàn bộ: `make format`.

Chạy toàn bộ kiểm tra giống GitHub Actions trên Pull Request (trừ CodeQL) trước khi đẩy:

```bash
make check
```

`make check` chạy validator, tests, Prettier, Ruff, ShellCheck, actionlint, quy ước branch/commit và kiểm tra dependency. Các nhóm dùng chung cấu hình với GitHub Actions; CodeQL chạy trên GitHub. Validator đối chiếu định dạng, biểu mẫu, nhãn, ruleset, ADR, tên trong mã nguồn và tài liệu. Workflow `.yml` và `.yaml` đều được kiểm tra.

Chạy riêng các tệp test bằng tên có hoặc không có `.py`:

```sh
python3 scripts/run-tests.py test_check test_check_markdown_links.py
```

Không truyền tên thì chạy toàn bộ test. Tên sai, tệp không có test, lỗi import hoặc cú pháp đều làm lệnh thất bại. Bộ kiểm tra liên kết Markdown hỗ trợ anchor của GitHub, tiêu đề trùng, khối mã và mã nội tuyến; tệp đích được đọc một lần trong lượt kiểm tra, lượt sau đọc lại.

`make links` kiểm tra liên kết HTTP(S) và nội dung `security.txt` trên website. Các URL chỉ khác fragment dùng chung một lần kiểm tra HTTP trong lượt chạy; đường dẫn và query khác vẫn được kiểm tra riêng. Máy chủ `img.shields.io` được bỏ qua; URL sai được báo lỗi. Phép kiểm tra HTTP không xác minh anchor bên trong trang ngoài. Kết quả được đọc mới ở lượt sau. `make forms` xác minh biểu mẫu trên GitHub; `make versions` đối chiếu công cụ với phiên bản phát hành mới nhất. Kiểm tra phiên bản ưu tiên `GH_TOKEN`, rồi `GITHUB_TOKEN`, sau đó token GitHub CLI; thông tin đăng nhập được đọc mới mỗi lượt. `make audit` cần kết nối registry npm; khi mất mạng, chạy lại để xác minh dependency. Lỗi cài thư viện npm làm kiểm tra dừng.

| Lệnh                       | Tác dụng                                                                                     |
| -------------------------- | -------------------------------------------------------------------------------------------- |
| `make`                     | Xem danh sách lệnh                                                                           |
| `make check`               | Mọi nhóm kiểm tra, chạy song song                                                            |
| `make validate`            | Kiểm tra nội dung bằng `scripts/validate.py`                                                 |
| `make test`                | Test tự động của các script, song song trên mọi lõi CPU                                      |
| `make format`              | Định dạng lại toàn bộ bằng Prettier và ruff                                                  |
| `make format-check`        | Prettier, ruff format, ruff check — job "Định dạng (Prettier, ruff)"                         |
| `make lint`                | shellcheck, actionlint — job "Shell script và workflow"                                      |
| `make conventions`         | Tên branch và tiêu đề commit theo quy ước                                                    |
| `make audit`               | Dependency có lỗ hổng mức high trở lên                                                       |
| `make tools`               | Kiểm tra đã cài đủ công cụ; cài thư viện Node.js nếu thiếu                                   |
| `make hooks`               | Cài git hook, mẫu commit `.gitmessage`, cấu hình `git blame` bỏ qua commit chỉ đổi định dạng |
| `make links`               | Liên kết bên ngoài còn hoạt động; bản `security.txt` trên website khớp repository            |
| `make versions`            | Công cụ trong `mise.toml` có bản phát hành mới hơn                                           |
| `make forms REF=…`         | GitHub chấp nhận biểu mẫu Issue, Discussion trên một branch đã đẩy (mặc định `main`)         |
| `make org-preview`         | Xem trước việc áp dụng cấu hình chung lên mọi repository và cài đặt tổ chức (cần GitHub CLI) |
| `make labels-preview`      | Xem trước việc đồng bộ nhãn lên các repository                                               |
| `make labels-apply`        | Đồng bộ nhãn (cần GitHub CLI và quyền quản trị)                                              |
| `make release-notes TAG=…` | Xem trước nội dung GitHub Release của một tag                                                |
| `make release-prepare`     | Chuyển mục CHƯA PHÁT HÀNH thành phiên bản của tháng nếu có thay đổi kể từ tag trước          |
| `make release-pr`          | Chuẩn bị rồi mở Pull Request phát hành tại máy (cần GitHub CLI, đứng ở `main` sạch)          |

---

## ⚙️ ĐỒNG BỘ CẤU HÌNH

[`scripts/org-setup.py`](scripts/org-setup.py) dùng GitHub CLI để quản lý tệp chung, cài đặt, ruleset, team và nhãn. Đăng nhập bằng `gh auth login`; chạy `make org-preview` để xem trước. Các lệnh mặc định chỉ đọc, thêm `--apply` để áp dụng; `--repo <tên>` giới hạn repository. Quy trình thiết lập repository xem [`ROADMAP.md`](ROADMAP.md).

- **Tệp chung:** lệnh `files` lập kế hoạch từ cây Git tại một commit cố định, thêm tệp thiếu bằng commit do GitHub ký và mở Pull Request. Branch đổi trong lúc ghi hoặc commit thất bại thì không mở Pull Request.
- **Cài đặt:** lệnh `settings` quản lý phương thức hợp nhất, bảo mật và quyền Actions; topics lấy từ `CITATION.cff`. Tính năng bảo mật chỉ được bật khi đọc được trạng thái và các tính năng phụ thuộc đã sẵn sàng.
- **Ruleset:** đọc hết danh sách, xác minh tên, ID và cấu trúc chi tiết trước khi ghi trong từng repository hoặc cấp tổ chức. Đọc song song, ghi tuần tự; gói Free dùng GraphQL để đối chiếu cấp tổ chức. Cấu hình và cách áp dụng xem [`rulesets/README.md`](rulesets/README.md).
- **Team:** chỉ thành viên `active` được coi là đã tham gia; lời mời `pending`, quyền tùy chỉnh chưa xếp hạng được hoặc dữ liệu chưa rõ chặn đồng bộ team. Quyền chuẩn đã cao hơn được giữ nguyên.
- **Nhãn:** nguồn là `labels.yml`; tên không trống, không trùng khi bỏ qua hoa/thường, màu hex 6 ký tự và mô tả tối đa 100 ký tự. Phản hồi sai chặn ghi lên repository đó; nhãn riêng được giữ nguyên.

Lỗi quyền, giới hạn API hoặc lỗi mạng được báo để tránh ghi dựa trên dữ liệu chưa đọc được; chỉ HTTP 404 được coi là chưa có tài nguyên. Dữ liệu được đọc mới mỗi lượt. Các lần ghi đã thành công không được tự hoàn tác nếu một lần ghi sau thất bại.

---

## 📝 QUẢN LÝ VÀ CẬP NHẬT

Các nội dung trong repository này được quản lý bởi những thành viên có thẩm quyền của CÔNG TY TNHH TOÀN QUỲNH. Mọi thay đổi đi qua Pull Request theo [`CONTRIBUTING.md`](CONTRIBUTING.md) và cần người quản trị duyệt.

Khi cập nhật nội dung, cần bảo đảm:

- Thông tin chính xác và phù hợp với định hướng của công ty.
- Không công khai dữ liệu cá nhân, thông tin y tế hoặc thông tin nội bộ.
- Không lưu trữ mật khẩu, mã truy cập, khóa API hoặc dữ liệu bảo mật.
- Tài liệu khớp với code sau mỗi thay đổi ([ADR 0013](docs/adr/0013-docs-match-code.md)).
- `make check` chạy thành công trước khi đưa lên nhánh chính.
- Nội dung dành cho người sử dụng được chuẩn bị trong [`CHANGELOG.md`](CHANGELOG.md) khi phát hành phiên bản.
- Tuân thủ quy định pháp luật và các chính sách của GitHub.

---

## 🚀 PHÁT HÀNH

Phiên bản có dạng `Stable.vYYYY.MM.DDXXXX` / `Beta.vYYYY.MM.DDXXXX`. `YYYY.MM.DD` là ngày chuẩn bị phát hành theo giờ Việt Nam; `XXXX` là số thứ tự gồm 4 chữ số, từ `0001` đến `9999`, dùng chung cho Stable và Beta, bắt đầu lại từ `0001` mỗi tháng. Script chọn số lớn nhất trong các tag đúng định dạng của tháng rồi tăng một, kể cả khi đổi ngày hoặc đổi kênh. Workflow hằng tháng chuẩn bị bản Stable ngày 1 khi có commit mới kể từ tag trước. [`CHANGELOG.md`](CHANGELOG.md) là khung chuẩn bị nội dung phiên bản; điền tóm tắt dành cho người sử dụng vào mục **CHƯA PHÁT HÀNH** trước khi chuẩn bị phát hành. Mục này trống thì script báo lỗi. Lần chuẩn bị sau bỏ mục của phiên bản trước — lịch sử phát hành xem tại [GitHub Releases](https://github.com/TOANQUYNHLLC/.github/releases). Tệp dùng để chuẩn bị nội dung dành cho người sử dụng; tài liệu dự án không ghi nhật ký phát triển hay báo cáo kiểm tra.

1. Workflow [`monthly-release.yml`](.github/workflows/monthly-release.yml) chạy lúc 07:00 ngày 1 (giờ Việt Nam): chuyển nội dung đã chuẩn bị thành phiên bản của tháng và mở Pull Request `release/stable.vYYYY.MM.DDXXXX`. Có thể chạy tay tại **Actions → Chuẩn bị phát hành hằng tháng → Run workflow**.
2. Xem trước bằng `make release-notes TAG=Stable.v2026.11.010001`; đánh giá và hợp nhất Pull Request bằng **Squash** hoặc **Merge**.
3. Người quản trị gắn tag trên `main`: `git tag Stable.v2026.11.010001 && git push origin Stable.v2026.11.010001`. Workflow [`release.yml`](.github/workflows/release.yml) tạo GitHub Release. Với lần phát hành đầu tiên chưa có tag, thêm mục tiêu đề phiên bản tương ứng vào `CHANGELOG.md`, tạo commit có chữ ký và gắn tag bằng tay.

Chuẩn bị bản Beta bằng `python3 scripts/release.py prepare --channel Beta`; thêm `--open-pr` để mở Pull Request phát hành tại máy. Có thể truyền `--date YYYY-MM-DD`; ngày trong `--version` phải trùng ngày chuẩn bị. Branch của Beta có dạng `release/beta.vYYYY.MM.DDXXXX`. GitHub Release của tag `Beta.v*` được đánh dấu là bản thử nghiệm.

Nhãn phát hành trong [`labels.yml`](labels.yml): `Stable` — Phiên bản Ổn Định; `Beta` — Phiên bản Thử Nghiệm; `Pre-Release` — Phiên bản Chuẩn Bị Release. Pull Request phát hành tự nhận nhãn `release`, `Pre-Release` và nhãn kênh tương ứng. Cấu hình gắn nhãn trong repository và bản mẫu áp dụng cùng quy tắc.

[`scripts/release.py`](scripts/release.py) kiểm tra phiên bản, ngày, nội dung UTF-8 và trạng thái branch/PR trước khi tạo branch phát hành. Branch đã tồn tại phải có Pull Request đang mở. Lỗi commit được xử lý bằng cách thử xóa branch vừa tạo; lỗi mở Pull Request giữ branch để mở tay. Tổ chức dùng **Immutable releases**: bản đã phát hành không dời tag hoặc dùng lại tên tag.

**Khi GitHub Actions tắt:**

- Hook `pre-push` chạy `make check`; người quản trị hợp nhất sau khi kiểm tra tại máy đạt, vì các kiểm tra bắt buộc chưa có lượt chạy trên GitHub.
- Hook sau `git pull` chạy `make links`, `make versions`, `make org-preview`; kiểm tra biểu mẫu bằng `make forms`.
- Chuẩn bị phát hành tại máy: `git switch main && git pull --ff-only && make release-pr`.
- Sau khi hợp nhất và đẩy tag, tạo Release: `python3 scripts/release.py create Stable.v2026.11.010001`.

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
