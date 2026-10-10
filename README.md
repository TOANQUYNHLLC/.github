# 🏢 CÔNG TY TNHH TOÀN QUỲNH

[![Checks](https://img.shields.io/github/actions/workflow/status/TOANQUYNHLLC/.github/validate.yml?branch=main&label=Checks&logo=githubactions&logoColor=white)](https://github.com/TOANQUYNHLLC/.github/blob/main/.github/workflows/validate.yml)
[![CodeQL](https://img.shields.io/github/actions/workflow/status/TOANQUYNHLLC/.github/codeql.yml?branch=main&label=CodeQL&logo=github&logoColor=white)](https://github.com/TOANQUYNHLLC/.github/blob/main/.github/workflows/codeql.yml)
[![Release](https://img.shields.io/github/v/release/TOANQUYNHLLC/.github?label=Release&display_name=release&logo=github)](https://github.com/TOANQUYNHLLC/.github/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/TOANQUYNHLLC/.github/main?label=Last%20Commit&logo=git&logoColor=white)](https://github.com/TOANQUYNHLLC/.github/commits/main)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-fe5196?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org/en/v1.0.0/)
[![Code Style: Prettier](https://img.shields.io/badge/Code%20Style-Prettier-ff69b4?logo=prettier&logoColor=white)](https://prettier.io)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Repository `.github` của **CÔNG TY TNHH TOÀN QUỲNH** quản lý hồ sơ tổ chức, tài liệu cộng đồng, mẫu cấu hình và công cụ vận hành GitHub. Thông tin công ty nằm trong [hồ sơ tổ chức](profile/README.md).

## 🎯 MỤC ĐÍCH

Repository cung cấp quy trình cộng tác và tài nguyên dùng chung cho các dự án. Người đóng góp bắt đầu từ [CONTRIBUTING.md](CONTRIBUTING.md); người quản trị dùng [MAINTAINERS.md](MAINTAINERS.md), [GOVERNANCE.md](GOVERNANCE.md) và [hướng dẫn cài đặt GitHub](docs/github-settings.md).

## ⚙️ PHẠM VI ÁP DỤNG

| Tài nguyên                     | Cách sử dụng                                                          |
| ------------------------------ | --------------------------------------------------------------------- |
| `profile/README.md`            | Hiển thị trên trang tổ chức                                           |
| Tệp cộng đồng và biểu mẫu      | GitHub dùng mặc định khi repository đích không có bản riêng tương ứng |
| `workflow-templates/`          | Chọn trong Actions hoặc chép, chỉnh và commit vào repository đích     |
| `repository-templates/`        | Chọn tệp nguồn rồi đặt đúng đường dẫn trong dự án                     |
| Ruleset, nhãn, team và cài đặt | Đối chiếu và áp dụng bằng công cụ quản trị                            |

Workflows, `CODEOWNERS`, dependencies và cấu hình công cụ cần được thiết lập trong từng dự án. Bộ mẫu Issue riêng hợp lệ ở repository đích thay thế cả bộ mặc định; labels phải tồn tại ở repository dùng biểu mẫu. [STRUCTURE.md](STRUCTURE.md) mô tả đường dẫn, phạm vi kế thừa và cách dùng template repository.

## 🛠️ PHÁT TRIỂN CỤC BỘ

Dùng phiên bản trong `mise.toml` và `.nvmrc`; kích hoạt mise trong shell rồi thiết lập:

```bash
mise trust
mise install
make hooks
make check
```

`make check` chạy validator, tests, formatter, lint, quy ước Git và kiểm tra dependency. Các nhóm độc lập chạy song song; CodeQL chạy trên GitHub Actions. Scripts cần Python ≥ 3.11 và Node.js đúng `.nvmrc`. Dev Container tự thiết lập công cụ và hook.

Quy tắc định dạng: UTF-8, LF, tab độ rộng 4; Markdown và YAML dùng 4 dấu cách. Ngoại lệ theo `.editorconfig`. Chi tiết môi trường, hook, cache và kiểm tra trực tuyến nằm trong [hướng dẫn kiểm tra tại máy](docs/local-checks.md).

## 🏢 QUẢN TRỊ GITHUB

GitHub CLI cần đăng nhập bằng tài khoản có quyền phù hợp. Các lệnh quản trị mặc định xem trước; `--apply` thực hiện ghi.

`make org-settings-inventory` xem danh mục local mà không cần đăng nhập. `pending_settings` khai báo trường/nhóm API chưa đọc được với giá trị `null` hoặc mục tiêu quản trị đã điền; `manual_settings` giữ trạng thái và tham chiếu cấu hình riêng cho billing, xác thực, Apps, Codespaces, Copilot, secrets và các nhóm cần thao tác thủ công. Khai báo chưa biết không đồng nghĩa đã sao lưu giá trị web. Hướng dẫn điền và khôi phục nằm trong [cài đặt chưa đọc được và cấu hình thủ công](docs/github-settings.md#-khai-báo-chưa-đọc-được-và-cấu-hình-thủ-công).

```bash
make org-preview
make org-import
make org-settings-audit
```

`make org-import` chỉ ghi cài đặt đọc được vào `github-settings.json`. Kiểm tra diff trước khi dùng `make org-settings-apply`. Dữ liệu chưa đọc được không được suy đoán; áp dụng cần xác minh nguồn, phạm vi và trạng thái sau ghi. Các thay đổi thành công không tự hoàn tác khi bước sau thất bại.

Để khôi phục sau nâng cấp gói GitHub, giữ bản local đã kiểm tra, dùng `make org-import-missing` bổ sung phần API từng bị chặn rồi xem trước và áp dụng. Bản tổng quát gồm cài đặt, ruleset đang cài, team và quyền repository, nhãn, custom properties, environments, Pages, variables, webhooks, bảo vệ nhánh kiểu cũ, IP allow list, cấu hình mạng, vai trò cho team, Actions policies, hosted runners, quyền truy cập Dependabot, mẫu secret scanning, chính sách push protection theo mẫu, private registries và định nghĩa bảo mật tùy chỉnh. Giới hạn lưu trữ/thời gian giữ cache Actions nằm trong nguồn theo repository. Giá trị variables, URL webhook, địa chỉ/tên IP allow list, regex tùy chỉnh và định nghĩa registry lưu riêng ngoài Git; phải sao lưu tệp riêng để khôi phục trên máy khác. Nhập lại bằng `make org-import` thay nguồn bằng trạng thái web; `make org-settings-audit` kiểm tra phạm vi đã nhập và trả mã lỗi khi còn phần thiếu. Lệnh `local-settings --only <nhóm>` cho phép khôi phục nhóm được chọn rõ khi nhóm khác chưa đủ quyền/gói; audit vẫn kiểm tra bản đầy đủ. Cách khôi phục và giới hạn nằm trong [hướng dẫn cài đặt GitHub](docs/github-settings.md#-khôi-phục-sau-nâng-cấp-gói).

Cờ bảo mật mặc định có hợp đồng PATCH tổ chức được quản lý trong `settings`; nguồn cũ được chuyển từ `web_settings` khi đọc. GitHub đang loại bỏ dần API legacy này; ưu tiên cấu hình bảo mật hiện đại khi gói/quyền hỗ trợ. `private_settings` giữ tham chiếu ngoài Git cho trường `billing_email` có API đọc/ghi. `security_options` lưu reviewers delegated bypass; trạng thái và options được áp dụng cùng PATCH, rồi đọc lại để xác nhận. Giới hạn principal và cách chọn nhóm nằm trong [cấu hình bảo mật có API](docs/github-settings.md#-cấu-hình-bảo-mật-có-api).

| Nguồn                                          | Phạm vi                                                                                                                                          |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `github-settings.json`                         | Bản khôi phục cài đặt và tài nguyên đang có trên GitHub; hợp đồng trong `configuration.py`, `resources.py`, `catalog.py` của `scripts/orgsetup/` |
| `repository-templates/`, `workflow-templates/` | Tệp thiếu được đề xuất qua Pull Request bằng lệnh `files`                                                                                        |
| `rulesets/`                                    | Bảo vệ nhánh, tag và push theo [hướng dẫn ruleset](rulesets/README.md)                                                                           |
| `scripts/orgsetup/teams.py`                    | Thông tin team, quan hệ cha–con và quyền repository                                                                                              |
| `labels.yml`                                   | Nhãn chuẩn; nhãn riêng được giữ khi đồng bộ                                                                                                      |

[hướng dẫn cài đặt GitHub](docs/github-settings.md) mô tả cách nhập, xem trước, áp dụng và giới hạn quyền/gói dịch vụ. Thiết lập dự án đích theo [ROADMAP.md](ROADMAP.md).

## 🚀 PHÁT HÀNH

Phiên bản có dạng `Stable.vYYYY.MM.DDXXXX` hoặc `Beta.vYYYY.MM.DDXXXX`: ngày chuẩn bị theo giờ Việt Nam, số thứ tự gồm 4 chữ số dùng chung hai kênh và bắt đầu lại mỗi tháng. [ADR 00000012](docs/adr/00000012-monthly-releases.md) quy định cách chọn phiên bản.

`CHANGELOG.md` chứa nội dung dành cho người sử dụng của phiên bản đang chuẩn bị. Các phiên bản đã công bố nằm ở [GitHub Releases](https://github.com/TOANQUYNHLLC/.github/releases).

1. Điền mục **CHƯA PHÁT HÀNH** rồi dùng `make release-pr`, hoặc workflow `monthly-release.yml` chạy lúc 07:00 ngày 1 hằng tháng khi có commit mới.
2. Xem nội dung bằng `make release-notes TAG=Stable.v2026.11.010001`, hoàn thành kiểm tra và hợp nhất PR bằng Merge hoặc Squash.
3. Người quản trị gắn tag trên `main`; workflow `release.yml` tạo Release. Khi Actions tắt, dùng `python3 scripts/release.py create Stable.v2026.11.010001` sau khi đẩy tag.

Chuẩn bị Beta bằng `python3 scripts/release.py prepare --channel Beta --open-pr`. Nội dung trống, lỗi đọc tag hoặc phiên bản không hợp lệ chặn chuẩn bị. Lần phát hành đầu tiên có thể chuẩn bị mục phiên bản và tag bằng tay theo cùng quy tắc. Release bất biến không cho dời hoặc dùng lại tag đã phát hành.

PR phát hành dùng [mẫu phát hành](.github/PULL_REQUEST_TEMPLATE/release.md); người quản trị xác nhận checklist trước khi hợp nhất. Nội dung GitHub tự sinh dùng nhãn trong `.github/release.yml`. PR do `GITHUB_TOKEN` mở có thể cần người có quyền ghi phê duyệt lượt chạy workflow theo yêu cầu của GitHub.

## 🧰 DANH SÁCH LỆNH

| Lệnh                          | Tác dụng                                                                                                                                                                                                                                |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make`                        | Xem danh sách lệnh                                                                                                                                                                                                                      |
| `make quick`                  | Kiểm tra nhanh: chỉ thu hẹp tests khi mọi tệp thay đổi là test; trường hợp khác chạy đầy đủ                                                                                                                                             |
| `make check`                  | Mọi nhóm kiểm tra, chạy song song                                                                                                                                                                                                       |
| `make validate`               | Kiểm tra nội dung bằng `scripts/validate.py`                                                                                                                                                                                            |
| `make test`                   | Test tự động của các script, song song theo CPU khả dụng                                                                                                                                                                                |
| `make format`                 | Định dạng lại toàn bộ bằng Prettier và ruff                                                                                                                                                                                             |
| `make format-check`           | Prettier, ruff format, ruff check — job "Định dạng (Prettier, ruff)"                                                                                                                                                                    |
| `make lint`                   | shellcheck, actionlint — job "Shell script và workflow"                                                                                                                                                                                 |
| `make conventions`            | Tên branch và tiêu đề commit theo quy ước                                                                                                                                                                                               |
| `make audit`                  | Dependency có lỗ hổng mức high trở lên                                                                                                                                                                                                  |
| `make tools`                  | Kiểm tra đã cài đủ công cụ; cài thư viện Node.js nếu thiếu hoặc sai phiên bản                                                                                                                                                           |
| `make hooks`                  | Cài git hook, mẫu commit `.gitmessage`, cấu hình `git blame` bỏ qua commit chỉ đổi định dạng                                                                                                                                            |
| `make sync [BRANCH=…]`        | Chuyển branch (mặc định `main`), kéo bằng fast-forward và dọn branch local đã hợp nhất; yêu cầu cây làm việc sạch                                                                                                                       |
| `make cleanup`                | `git clean -fdx`: **xóa vĩnh viễn** mọi tệp git không quản lý — tệp mới chưa `git add`, tệp bị `.gitignore` bỏ qua (`node_modules/`, `.cache/`, `.env`…); xem trước bằng `git clean -ndx`. Lần kiểm tra sau tự cài lại thư viện Node.js |
| `make links`                  | Liên kết bên ngoài còn hoạt động; bản `security.txt` trên website khớp repository                                                                                                                                                       |
| `make versions`               | Công cụ trong `mise.toml`, action chỉ có trong `workflow-templates/` có bản phát hành mới hơn                                                                                                                                           |
| `make forms REF=…`            | Kiểm tra Issue theo ref; Discussion chỉ xác minh trên nhánh mặc định, ref khác báo chưa xác minh và trả mã lỗi (mặc định `main`)                                                                                                        |
| `make org-import`             | Lấy cài đặt GitHub của tổ chức và các repository về `github-settings.json`; chỉ ghi local                                                                                                                                               |
| `make org-import-missing`     | Bổ sung dữ liệu chưa có sau nâng cấp gói hoặc quyền; giữ cài đặt local đã lưu                                                                                                                                                           |
| `make org-settings-audit`     | Kiểm tra toàn bộ phạm vi nhập, phần thiếu và khác biệt với GitHub; chỉ đọc                                                                                                                                                              |
| `make org-settings-inventory` | Xem khai báo chưa biết và trạng thái khôi phục thủ công ở local; không cần đăng nhập                                                                                                                                                    |
| `make org-settings-preview`   | Xem trước cài đặt API trong `github-settings.json`, gồm trạng thái Actions và các endpoint bổ sung                                                                                                                                      |
| `make org-settings-apply`     | Áp dụng cài đặt API trong `github-settings.json`, đọc lại để xác nhận; báo riêng mục cần thao tác trên web                                                                                                                              |
| `make org-preview`            | Xem trước việc áp dụng cấu hình chung lên mọi repository và cài đặt tổ chức (cần GitHub CLI)                                                                                                                                            |
| `make labels-preview`         | Xem trước việc đồng bộ nhãn lên các repository                                                                                                                                                                                          |
| `make labels-apply`           | Đồng bộ nhãn lên repository đã có (cần GitHub CLI); nhãn mặc định cấp tổ chức nhập trên web                                                                                                                                             |
| `make release-notes TAG=…`    | Xem trước nội dung GitHub Release của một tag                                                                                                                                                                                           |
| `make release-prepare`        | Chuyển mục CHƯA PHÁT HÀNH thành phiên bản của tháng nếu có thay đổi kể từ tag trước                                                                                                                                                     |
| `make release-pr`             | Chuẩn bị rồi mở Pull Request phát hành tại máy (cần GitHub CLI, đứng ở `main` sạch)                                                                                                                                                     |

## 📁 TÀI NGUYÊN VÀ CÔNG CỤ

**Hồ sơ và quản trị tổ chức**

| Đường dẫn                                              | Chức năng                                                                                         |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| [`profile/README.md`](profile/README.md)               | Trang giới thiệu công khai của CÔNG TY TNHH TOÀN QUỲNH trên GitHub                                |
| [`GOVERNANCE.md`](GOVERNANCE.md)                       | Vai trò, cách ra quyết định, đánh giá và hợp nhất, thay đổi người quản trị                        |
| [`MAINTAINERS.md`](MAINTAINERS.md)                     | Người quản trị và các team của tổ chức                                                            |
| [`ROADMAP.md`](ROADMAP.md)                             | Việc dự kiến: thiết lập repository mới, cài đặt tổ chức chỉ làm được trên web                     |
| [`.well-known/security.txt`](.well-known/security.txt) | Liên hệ bảo mật của tổ chức (RFC 9116), đăng tại `https://toanquynh.com/.well-known/security.txt` |

**Tệp cộng đồng mặc định** — dùng khi repository đích không có bản riêng tương ứng

| Đường dẫn                                                              | Chức năng                                                                                                                                                                                                                              |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`CONTRIBUTING.md`](CONTRIBUTING.md)                                   | Quy trình đóng góp, quy ước branch, commit và Pull Request                                                                                                                                                                             |
| [`SECURITY.md`](SECURITY.md)                                           | Chính sách bảo mật và cách báo cáo lỗ hổng                                                                                                                                                                                             |
| [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)                             | Quy tắc ứng xử trong không gian cộng tác                                                                                                                                                                                               |
| [`SUPPORT.md`](SUPPORT.md)                                             | Kênh hỗ trợ: đặt câu hỏi, báo lỗi, đề xuất, bảo mật và liên hệ                                                                                                                                                                         |
| [`ACCESSIBILITY.md`](ACCESSIBILITY.md)                                 | Mục tiêu trợ năng, cách báo cáo vấn đề và hướng dẫn đóng góp                                                                                                                                                                           |
| [`.github/VULNERABILITY_REPORT.yml`](.github/VULNERABILITY_REPORT.yml) | Biểu mẫu báo cáo lỗ hổng riêng tư theo chính sách bảo mật                                                                                                                                                                              |
| [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/)                   | Biểu mẫu Issue: báo lỗi chức năng, lỗi tài liệu, lỗi CI hoặc kiểm thử, đề xuất tính năng, câu hỏi; cấu hình `config.yml`                                                                                                               |
| [`.github/DISCUSSION_TEMPLATE/`](.github/DISCUSSION_TEMPLATE/)         | Biểu mẫu Discussions: Thông báo, Ý tưởng, Hỏi đáp, Thảo luận chung, chia sẻ demo và tình huống sử dụng                                                                                                                                 |
| [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) | Biểu mẫu Pull Request: tóm tắt thay đổi, kiểm thử, rủi ro và checklist                                                                                                                                                                 |
| [`.github/PULL_REQUEST_TEMPLATE/`](.github/PULL_REQUEST_TEMPLATE/)     | Mẫu PR riêng cho tính năng, sửa lỗi, hotfix, tái cấu trúc, dependency, kiểm thử, migration, hiệu năng, phát hành, cấu hình và tài liệu; chọn bằng tham số `template` theo [hướng dẫn đóng góp](CONTRIBUTING.md#-chọn-mẫu-pull-request) |

**Tài nguyên dùng chung cho các repository**

| Đường dẫn                                        | Chức năng                                                                                                                                                                               |
| ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`workflow-templates/`](workflow-templates/)     | Workflow mẫu theo công nghệ và chức năng; gọi scripts của tổ chức trong `.org/`                                                                                                         |
| [`repository-templates/`](repository-templates/) | Tệp riêng cho từng repository: `CODEOWNERS`, `dependabot.yml`, `release.yml`, `labeler.yml`, cấu hình định dạng, phiên bản theo ngôn ngữ, `.dockerignore`, `.env.example`, `PRIVACY.md` |
| [`rulesets/`](rulesets/)                         | Ruleset **Protect Main**, **Protect Release Tags** (cấp repository) và bản cấp tổ chức, push ruleset **Protect Pushes** — xem [`rulesets/README.md`](rulesets/README.md)                |
| [`labels.yml`](labels.yml)                       | Bộ nhãn chuẩn: nhãn mặc định của GitHub, loại thay đổi (khớp tiền tố branch), phạm vi `area: …`, mức độ ưu tiên, trạng thái xử lý, nhãn Dependabot                                      |

**Workflow của repository này**

| Đường dẫn                                                                                                                                     | Chức năng                                                                                                                               |
| --------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| [`.github/workflows/validate.yml`](.github/workflows/validate.yml)                                                                            | Mỗi job gọi một nhóm của `scripts/check.py`: `content` (validate, test), `format` (Prettier, ruff), `lint` (shellcheck, actionlint)     |
| [`.github/workflows/branch-name.yml`](.github/workflows/branch-name.yml) · [`.github/workflows/pr-title.yml`](.github/workflows/pr-title.yml) | Tên branch và tiêu đề Pull Request theo quy ước — gọi `scripts/conventions.py`                                                          |
| [`.github/workflows/labeler.yml`](.github/workflows/labeler.yml)                                                                              | Gắn nhãn Pull Request theo tiền tố branch và tệp thay đổi ([`.github/labeler.yml`](.github/labeler.yml))                                |
| [`.github/workflows/dependency-review.yml`](.github/workflows/dependency-review.yml)                                                          | Chặn Pull Request thêm dependency có lỗ hổng mức cao trở lên                                                                            |
| [`.github/workflows/codeql.yml`](.github/workflows/codeql.yml)                                                                                | Quét bảo mật CodeQL cho workflow và Python khi push, mở Pull Request và hằng tuần                                                       |
| [`.github/workflows/monthly-release.yml`](.github/workflows/monthly-release.yml)                                                              | Ngày 1 hằng tháng: mở Pull Request phát hành nếu có commit mới (mục [PHÁT HÀNH](#-phát-hành))                                           |
| [`.github/workflows/release.yml`](.github/workflows/release.yml)                                                                              | Gắn tag `Stable.v*`, `Beta.v*` hoặc `v*` thì tạo GitHub Release từ `CHANGELOG.md`                                                       |
| [`.github/workflows/links.yml`](.github/workflows/links.yml)                                                                                  | Hằng tuần: liên kết bên ngoài, GitHub chấp nhận biểu mẫu, công cụ trong `mise.toml` có bản mới                                          |
| [`.github/workflows/stale.yml`](.github/workflows/stale.yml)                                                                                  | Hằng tuần đánh dấu và đóng Issue, Pull Request không hoạt động                                                                          |
| [`.github/dependabot.yml`](.github/dependabot.yml)                                                                                            | Đề xuất cập nhật GitHub Action (ghim theo commit SHA), Prettier và feature của Dev Container, chờ 7 ngày sau khi phát hành (`cooldown`) |
| [`.github/CODEOWNERS`](.github/CODEOWNERS)                                                                                                    | Team người quản trị duyệt mọi thay đổi                                                                                                  |

Workflow mẫu cần được chọn theo công nghệ và chỉnh cho dự án đích. Cách áp dụng xem [cấu trúc repository](STRUCTURE.md) và [mẫu tệp](repository-templates/README.md).

**Script** — các kiểm tra và công cụ dùng chung

| Đường dẫn                                                                                   | Chức năng                                                                                                                                             |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`scripts/check.py`](scripts/check.py)                                                      | Điều phối nhóm kiểm tra dùng chung tại máy và trên GitHub Actions                                                                                     |
| [`scripts/validate.py`](scripts/validate.py) · [`scripts/validation/`](scripts/validation/) | Kiểm tra nội dung, quy ước, cấu hình và sự thống nhất của tài liệu                                                                                    |
| [`scripts/install-python-dependencies.py`](scripts/install-python-dependencies.py)          | Cài công cụ Python theo phiên bản Ruff của tổ chức, requirements và package cho workflow mẫu Python CI                                                |
| [`scripts/run-tests.py`](scripts/run-tests.py)                                              | Chạy tests song song theo CPU khả dụng và cân bằng nhóm theo thời gian chạy                                                                           |
| [`scripts/conventions.py`](scripts/conventions.py)                                          | Tên branch, tiêu đề commit và Pull Request (workflow của repository này và workflow mẫu)                                                              |
| [`scripts/git-hooks.py`](scripts/git-hooks.py)                                              | Cài và chạy hook trước commit, trước push và sau khi kéo code                                                                                         |
| [`scripts/check-branch-merged.py`](scripts/check-branch-merged.py)                          | Đối chiếu các nhóm thay đổi của branch với lịch sử nhánh chính, giữ khoảng trắng và dữ liệu nhị phân để dọn branch local                              |
| [`scripts/release.py`](scripts/release.py)                                                  | Phát hành từ `CHANGELOG.md`: xem trước nội dung, chuẩn bị phiên bản của tháng, mở Pull Request phát hành, tạo GitHub Release                          |
| [`scripts/org-setup.py`](scripts/org-setup.py) · [`scripts/orgsetup/`](scripts/orgsetup/)   | Nhập, đối chiếu và áp dụng cài đặt; quản lý tệp, ruleset, team và nhãn                                                                                |
| [`scripts/check-markdown-links.py`](scripts/check-markdown-links.py)                        | Liên kết nội bộ trong Markdown (dùng chung với `validate.py` và workflow mẫu `docs-check.yml`)                                                        |
| [`scripts/markdown.py`](scripts/markdown.py)                                                | Bỏ nội dung mã trong Markdown, dùng chung cho kiểm tra liên kết nội bộ, liên kết bên ngoài, tiêu đề, thụt lề và nhận diện cấu trúc nội dung phát hành |
| [`scripts/check-gofmt.py`](scripts/check-gofmt.py)                                          | Định dạng Go cho workflow mẫu `go-ci.yml`                                                                                                             |
| [`scripts/check-external-links.py`](scripts/check-external-links.py)                        | Liên kết bên ngoài còn hoạt động; bản `security.txt` trên website khớp repository                                                                     |
| [`scripts/check-github-forms.py`](scripts/check-github-forms.py)                            | GitHub chấp nhận biểu mẫu Issue, Discussion (lỗi khóa chỉ hiện trên trang xem tệp)                                                                    |
| [`scripts/check-tool-versions.py`](scripts/check-tool-versions.py)                          | Công cụ trong `mise.toml` và action chỉ có trong `workflow-templates/` (Dependabot không theo dõi) có bản phát hành mới hơn                           |
| [`scripts/test_*.py`](scripts/) · [`scripts/testsupport.py`](scripts/testsupport.py)        | Tests và công cụ hỗ trợ dựng môi trường kiểm thử                                                                                                      |

**Cấu hình và công cụ phát triển**

| Đường dẫn                                                                                                  | Chức năng                                                                                                                                                     |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`Makefile`](Makefile)                                                                                     | Lệnh thiết lập, kiểm tra, đồng bộ Git, phát hành và quản trị tổ chức                                                                                          |
| [`mise.toml`](mise.toml) · [`.nvmrc`](.nvmrc) · [`package.json`](package.json)                             | Nguồn phiên bản duy nhất: Python, ruff, ShellCheck, actionlint; Node.js; Prettier (`devEngines` chặn phiên bản sai)                                           |
| [`.editorconfig`](.editorconfig) · [`.prettierrc.json`](.prettierrc.json) · [`ruff.toml`](ruff.toml)       | Quy tắc định dạng (mục [PHÁT TRIỂN CỤC BỘ](#️-phát-triển-cục-bộ))                                                                                              |
| [`.gitattributes`](.gitattributes) · [`.gitignore`](.gitignore)                                            | Xuống dòng theo loại tệp, tệp nhị phân; bỏ qua tệp tạm, `node_modules/`, bí mật                                                                               |
| [`.devcontainer/`](.devcontainer/) · [`.vscode/extensions.json`](.vscode/extensions.json)                  | Môi trường Dev Container, Codespaces và cấu hình editor                                                                                                       |
| [`shell/sync.sh`](shell/sync.sh) · [`shell/prune-branches.sh`](shell/prune-branches.sh)                    | Chuyển, kéo branch bằng fast-forward và dọn branch local đã hợp nhất có branch theo dõi bị xóa                                                                |
| [`.gitmessage`](.gitmessage) · [`.git-blame-ignore-revs`](.git-blame-ignore-revs) · [`.mailmap`](.mailmap) | Mẫu commit theo quy ước; `git blame` bỏ qua commit chỉ đổi định dạng; gộp các cách viết tên tác giả                                                           |
| [`pyproject.toml`](pyproject.toml)                                                                         | Python tối thiểu của script (`requires-python`) để ruff trong VS Code và `ruff check` gõ tay kiểm tra giống `make check`; không đóng gói, không có dependency |
| [`.npmrc`](.npmrc) · [`.shellcheckrc`](.shellcheckrc)                                                      | npm ghi phiên bản chính xác, không tạo `package-lock.json`; cấu hình ShellCheck                                                                               |
| [`CITATION.cff`](CITATION.cff)                                                                             | Cách trích dẫn repository; từ khóa là nguồn của topics trên GitHub                                                                                            |
| [`.github.code-workspace`](.github.code-workspace)                                                         | Workspace VS Code: mở thư mục gốc của repository                                                                                                              |

**Tài liệu cho người phát triển**

| Đường dẫn                                                                                                                  | Chức năng                                                                                                           |
| -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| [`docs/adr/`](docs/adr/)                                                                                                   | Bản ghi các quyết định kiến trúc đang có hiệu lực và lý do                                                          |
| [`specs/`](specs/)                                                                                                         | Thư mục đặc tả và quy trình rà soát dự án                                                                           |
| [`AGENTS.md`](AGENTS.md) · [`CLAUDE.md`](CLAUDE.md) · [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | Hướng dẫn cho AI coding agent và GitHub Copilot                                                                     |
| [`.github/instructions/`](.github/instructions/)                                                                           | Hướng dẫn Copilot theo đường dẫn: mã Python, cấu hình GitHub và tài liệu                                            |
| [`.github/agents/repository-reviewer.agent.md`](.github/agents/repository-reviewer.agent.md)                               | Agent Copilot rà soát ảnh hưởng toàn tổ chức và sự thống nhất giữa tài liệu với code, dùng công cụ đọc và tìm kiếm  |
| [`specs/jobs-guideline.md`](specs/jobs-guideline.md)                                                                       | Yêu cầu chuẩn cho một đợt rà soát toàn dự án: phạm vi, cách kiểm chứng, điều kiện hoàn tất và nội dung Pull Request |
| [`docs/local-checks.md`](docs/local-checks.md)                                                                             | Thiết lập công cụ, hook và kiểm tra                                                                                 |
| [`docs/github-settings.md`](docs/github-settings.md)                                                                       | Nguồn cài đặt và hợp đồng API GitHub                                                                                |
| [`CHANGELOG.md`](CHANGELOG.md)                                                                                             | Khung nội dung chuẩn bị phát hành                                                                                   |

---

## 📝 QUY TẮC ĐÓNG GÓP

Mọi thay đổi đi qua Pull Request theo [CONTRIBUTING.md](CONTRIBUTING.md), được đánh giá và kiểm tra trước khi hợp nhất. Mỗi thay đổi phải sửa các nơi liên quan trong code, tests, cấu hình và tài liệu theo [ADR 00000013](docs/adr/00000013-related-changes.md).

Tài liệu mô tả trạng thái hiện tại theo từng chủ đề. Nội dung phát hành được chuẩn bị riêng; log phát triển và báo cáo kiểm tra không thuộc tài liệu dự án.

## 🔐 BẢO MẬT

Báo cáo lỗ hổng riêng theo [SECURITY.md](SECURITY.md). Không gửi mật khẩu, token, khóa API, dữ liệu cá nhân hoặc hồ sơ y tế qua kênh công khai.

## 📞 LIÊN HỆ

- Email: [toanquynhvn@gmail.com](mailto:toanquynhvn@gmail.com).
- Website: [toanquynh.com](https://toanquynh.com).
- Thông tin công ty: [hồ sơ tổ chức](profile/README.md#-thông-tin-liên-hệ).

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Repository quản lý hồ sơ và cấu hình GitHub của tổ chức.
</p>
