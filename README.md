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
| [`.github/workflows/release.yml`](.github/workflows/release.yml)                                                                              | Gắn tag `v*` thì tạo GitHub Release từ `CHANGELOG.md`                                                                               |
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

| Đường dẫn                                                                                                                  | Chức năng                                                  |
| -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [`docs/adr/`](docs/adr/)                                                                                                   | Bản ghi các quyết định kiến trúc đang có hiệu lực và lý do |
| [`AGENTS.md`](AGENTS.md) · [`CLAUDE.md`](CLAUDE.md) · [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | Hướng dẫn cho AI coding agent và GitHub Copilot            |
| [`CHANGELOG.md`](CHANGELOG.md)                                                                                             | Nhật ký thay đổi theo phiên bản                            |
| [`LICENSE`](LICENSE)                                                                                                       | Giấy phép MIT cho nội dung của repository này              |

---

## 🛠️ PHÁT TRIỂN CỤC BỘ

Cài công cụ đúng phiên bản trong [`mise.toml`](mise.toml) và [`.nvmrc`](.nvmrc) — ruff, ShellCheck, actionlint, Node.js cùng phiên bản với CI (CI dùng Python có sẵn của runner, script cần ≥ 3.11) — rồi cài git hook:

```bash
mise install
make hooks
```

Không dùng mise thì cài Node.js đúng bản trong `.nvmrc` (ví dụ `brew install node@24` rồi đưa `$(brew --prefix node@24)/bin` lên đầu `PATH`): `devEngines` của `package.json` làm npm báo `EBADDEVENGINES` và dừng khi Node.js khác bản này. Thư viện Node.js (Prettier) tự cài khi chạy kiểm tra lần đầu. Git hook ([`scripts/git-hooks.py`](scripts/git-hooks.py)) chạy tự động:

- `git commit`: Prettier, `ruff format`, `ruff check` trên đúng phần đã stage; lỗi thì không commit.
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

Nếu npm không cài được thư viện, lượt kiểm tra dừng và giữ thông báo lỗi npm để xử lý phiên bản Node.js hoặc kết nối mạng. `make audit` cần truy cập registry npm; mất kết nối thì chỉ cảnh báo, cần chạy lại khi có mạng để xác minh dependency.

Chạy riêng các tệp test bằng tên có hoặc không có `.py`:

```sh
python3 scripts/run-tests.py test_check test_check_markdown_links.py
```

Chỉ các tệp test được chọn được nạp; tên sai hoặc tệp không có test làm lệnh thất bại trước khi chạy. Lỗi import hoặc cú pháp trong tệp được chọn sẽ chạy lại đúng danh sách đó bằng unittest để báo lỗi đầy đủ. Không truyền tên thì chạy toàn bộ test.

Bộ kiểm tra liên kết Markdown dùng anchor giống GitHub, kể cả tiêu đề trùng với hậu tố tự sinh; mỗi tệp đích được phân tích một lần trong một lượt kiểm tra và được đọc lại ở lượt sau. Tệp không đọc được hoặc sai UTF-8 làm kiểm tra thất bại và báo tên tệp; `validate.py` tiếp tục đối chiếu các nội dung còn đọc được để báo lỗi cùng lượt.

Validator kiểm tra cấu trúc workflow, action và lệnh theo giá trị YAML đã phân tích, gồm khóa có dấu nháy, dạng `{run: …}` và [anchor/alias](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations#yaml-anchors-and-aliases). Biểu thức trong chú thích không phải nội dung lệnh. YAML chỉ đọc dữ liệu thông thường; alias tạo vòng lặp được báo ở tệp gây lỗi. Cấu hình JSON phải là object; kết quả đọc cấu hình chỉ dùng lại trong cùng lượt kiểm tra và được làm mới ở lượt sau.

Workflow đuôi `.yml` và `.yaml` đều được actionlint kiểm tra, đối chiếu job với ruleset và yêu cầu liệt kê trong README.

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

`scripts/org-setup.py files` tìm tệp dùng chung còn thiếu bằng [Git Trees API](https://docs.github.com/en/rest/git/trees#get-a-tree) tại một commit cố định và tạo branch từ cùng commit đó. Mỗi lần chạy đọc lại trạng thái GitHub; nếu API cắt danh sách cây, script dò từng đường dẫn tại cùng commit. Khi áp dụng, toàn bộ tệp thiếu được gửi trong một commit qua [`createCommitOnBranch`](https://github.blog/changelog/2021-09-13-a-simpler-api-for-authoring-commits/) để GitHub ký; `expectedHeadOid` chặn ghi nếu branch đã đổi. Commit thất bại thì không mở Pull Request; branch đã tạo được giữ lại để người quản trị kiểm tra.

Các phép dò sự tồn tại chỉ coi HTTP 404 là chưa có; lỗi quyền, giới hạn API và lỗi mạng được báo để tránh ghi dựa trên dữ liệu chưa đọc được. Lệnh `team` dừng trước khi ghi nếu không đọc được trạng thái; `settings` cảnh báo và bỏ qua tính năng bảo mật không đọc được trạng thái.

Danh sách ruleset và nhãn được đọc đầy đủ bằng [phân trang của GitHub CLI](https://cli.github.com/manual/gh_api), mỗi trang REST tối đa 100 phần tử; lần chạy sau đọc lại GitHub. Lỗi trang sau không trả danh sách dở dang để ghi. Phép đối chiếu ruleset tổ chức qua GraphQL cũng đọc hết các trang; dữ liệu quy tắc hoặc danh sách bỏ qua bị cắt được báo chưa đọc đầy đủ.

Lệnh đồng bộ nhãn đọc `labels.yml` bằng chế độ YAML an toàn như validator, hỗ trợ anchor/alias không tạo vòng lặp. YAML lỗi hoặc cấu trúc không phải danh sách object nhãn chặn lệnh trước khi đọc hay ghi GitHub.

---

## 📝 QUẢN LÝ VÀ CẬP NHẬT

Các nội dung trong repository này được quản lý bởi những thành viên có thẩm quyền của CÔNG TY TNHH TOÀN QUỲNH. Mọi thay đổi đi qua Pull Request theo [`CONTRIBUTING.md`](CONTRIBUTING.md) và cần người quản trị duyệt.

Khi cập nhật nội dung, cần bảo đảm:

- Thông tin chính xác và phù hợp với định hướng của công ty.
- Không công khai dữ liệu cá nhân, thông tin y tế hoặc thông tin nội bộ.
- Không lưu trữ mật khẩu, mã truy cập, khóa API hoặc dữ liệu bảo mật.
- Tài liệu khớp với code sau mỗi thay đổi ([ADR 0013](docs/adr/0013-docs-match-code.md)).
- `make check` chạy thành công trước khi đưa lên nhánh chính.
- Thay đổi đáng chú ý được ghi vào [`CHANGELOG.md`](CHANGELOG.md).
- Tuân thủ quy định pháp luật và các chính sách của GitHub.

---

## 🚀 PHÁT HÀNH

Phát hành vào **ngày 1 hằng tháng**, chỉ khi có commit mới kể từ tag phát hành trước; phiên bản đặt theo tháng (`vYYYY.MM.Stable`).

1. Workflow [`monthly-release.yml`](.github/workflows/monthly-release.yml) chạy lúc 07:00 ngày 1 (giờ Việt Nam): chuyển mục **CHƯA PHÁT HÀNH** của [`CHANGELOG.md`](CHANGELOG.md) thành phiên bản của tháng (ví dụ `## [v2026.11.Stable] — 2026-11-01`) và mở Pull Request `release/v2026.11`. Có commit mà mục **CHƯA PHÁT HÀNH** trống thì báo lỗi — ghi `CHANGELOG.md` rồi chạy lại (**Actions → Chuẩn bị phát hành hằng tháng → Run workflow**).
2. Xem trước nội dung: `make release-notes TAG=v2026.11.Stable`; hợp nhất Pull Request bằng **Squash** hoặc **Merge**.
3. Người quản trị gắn và đẩy tag trên `main` (ruleset **Protect Release Tags** chỉ cho người quản trị tạo tag `v*`): `git tag v2026.11.Stable && git push origin v2026.11.Stable` — workflow [`release.yml`](.github/workflows/release.yml) tạo GitHub Release. Tổ chức bật **Immutable releases**: Release đã phát hành không dời được tag, không dùng lại được tên tag.

Chạy lại khi branch phát hành đã có: script xác minh và in URL của Pull Request đang mở. Nếu branch chưa có Pull Request đang mở, script báo lỗi kèm liên kết để kiểm tra và mở tay. Lỗi đọc trạng thái không tạo branch mới; lỗi commit sẽ thử xóa branch vừa tạo và báo rõ nếu chưa xóa được. Lỗi tạo Pull Request giữ branch để mở tay.

**Khi GitHub Actions tắt** (ví dụ để tiết kiệm chi phí), mọi việc định kỳ vẫn có người làm:

- Kiểm tra: hook `pre-push` chạy `make check` trước mỗi lần đẩy.
- Hợp nhất: kiểm tra bắt buộc của ruleset **Protect Main** không có lượt chạy để báo kết quả, nên chỉ người quản trị (danh sách bỏ qua của ruleset) hợp nhất được Pull Request — sau khi `make check` đã đạt tại máy.
- Liên kết, phiên bản công cụ, cài đặt trên GitHub: hook sau `git pull` chạy `make links`, `make versions`, `make org-preview`.
- Routine Claude Code (claude.ai/code/routines, người quản trị bật khi tắt Actions): **Nhắc phát hành hằng tháng** (08:00 ngày 1) báo có cần phát hành không; **Kiểm tra biểu mẫu hằng tháng** (09:00 ngày 1) chạy `check-github-forms.py`. Môi trường đám mây chặn mạng ra ngoài github.com và không có GitHub CLI đã đăng nhập, nên phần còn lại chạy tại máy.
- Phát hành: `git switch main && git pull --ff-only && make release-pr` thay cho bước 1; sau bước 3 tạo Release bằng `python3 scripts/release.py create v2026.11.Stable`.

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
