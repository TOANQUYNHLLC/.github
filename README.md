# 🏢 CÔNG TY TNHH TOÀN QUỲNH

[![Checks](https://img.shields.io/github/actions/workflow/status/TOANQUYNHLLC/.github/validate.yml?branch=main&label=Checks&logo=githubactions&logoColor=white)](https://github.com/TOANQUYNHLLC/.github/blob/main/.github/workflows/validate.yml)
[![CodeQL](https://img.shields.io/github/actions/workflow/status/TOANQUYNHLLC/.github/codeql.yml?branch=main&label=CodeQL&logo=github&logoColor=white)](https://github.com/TOANQUYNHLLC/.github/blob/main/.github/workflows/codeql.yml)
[![Release](https://img.shields.io/github/v/release/TOANQUYNHLLC/.github?label=Release&display_name=release&logo=github)](https://github.com/TOANQUYNHLLC/.github/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/TOANQUYNHLLC/.github/main?label=Last%20Commit&logo=git&logoColor=white)](https://github.com/TOANQUYNHLLC/.github/commits/main)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-fe5196?logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org/en/v1.0.0/)
[![Code Style: Prettier](https://img.shields.io/badge/Code%20Style-Prettier-ff69b4?logo=prettier&logoColor=white)](https://prettier.io)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

`.github` là bộ tài nguyên cộng đồng và công cụ kiểm tra dùng chung của **CÔNG TY TNHH TOÀN QUỲNH** trên GitHub. Repository cung cấp tài liệu đóng góp, biểu mẫu, workflow và mẫu cấu hình để thiết lập quy trình làm việc cho các dự án của tổ chức.

## 🎯 MỤC ĐÍCH

Người duy trì dự án chọn tài nguyên theo công nghệ và nhu cầu, sau đó kiểm chứng trong repository đích. Người đóng góp dùng cùng bộ quy ước và kiểm tra tại máy để chuẩn bị thay đổi có thể đánh giá qua Pull Request.

| Nhu cầu                          | Bắt đầu tại                                                                                 |
| -------------------------------- | ------------------------------------------------------------------------------------------- |
| Áp dụng tài nguyên cho một dự án | [Cấu trúc và phạm vi áp dụng](STRUCTURE.md), [mẫu tệp](repository-templates/README.md)      |
| Đóng góp cho bộ tài nguyên       | [Hướng dẫn đóng góp](CONTRIBUTING.md), [thiết lập tại máy](docs/local-checks.md)            |
| Duy trì và phát hành             | [Quản trị dự án](GOVERNANCE.md), [người quản trị](MAINTAINERS.md), [phát hành](#-phát-hành) |
| Tìm thông tin công ty            | [Hồ sơ tổ chức](profile/README.md)                                                          |

## ⚙️ PHẠM VI ÁP DỤNG

| Tài nguyên                | Cách sử dụng                                                          |
| ------------------------- | --------------------------------------------------------------------- |
| `profile/README.md`       | Hiển thị trên trang tổ chức                                           |
| Tệp cộng đồng và biểu mẫu | GitHub dùng mặc định khi repository đích không có bản riêng tương ứng |
| `workflow-templates/`     | Chọn trong Actions hoặc chép, chỉnh và commit vào repository đích     |
| `repository-templates/`   | Chọn tệp nguồn rồi đặt đúng đường dẫn trong dự án                     |
| Ruleset và nhãn           | Mẫu chính sách để người quản trị áp dụng trong từng repository        |

Workflows, `CODEOWNERS`, dependencies và cấu hình công cụ cần được thiết lập trong từng dự án. Bộ mẫu Issue riêng hợp lệ ở repository đích thay thế cả bộ mặc định; labels phải tồn tại ở repository dùng biểu mẫu. [STRUCTURE.md](STRUCTURE.md) mô tả đường dẫn, phạm vi kế thừa và cách dùng template repository.

## 🛠️ PHÁT TRIỂN CỤC BỘ

Clone repository và chuyển vào thư mục dự án:

```sh
git clone https://github.com/TOANQUYNHLLC/.github.git
cd .github
```

Cài sẵn Git, GNU Make, Bash và Ruby theo [yêu cầu môi trường](docs/local-checks.md#-môi-trường). Dùng phiên bản công cụ trong `mise.toml` và `.nvmrc`; kích hoạt mise trong shell rồi thiết lập:

```bash
mise trust
mise install
make hooks
make check
```

`make check` chạy validator, tests, formatter, lint, quy ước Git và npm audit. Các nhóm độc lập chạy song song. Dependency Review xét thay đổi phụ thuộc của PR, còn CodeQL phân tích mã nguồn trên GitHub Actions khi được bật. Scripts cần Python ≥ 3.11 và Node.js đúng `.nvmrc`. Dev Container tự thiết lập công cụ và hook.

Kết quả tại máy phục vụ kiểm chứng trước khi gửi thay đổi; GitHub chỉ ghi nhận status checks từ nguồn kiểm tra được ruleset yêu cầu. Khi Actions tắt, các job của repository không chạy và PR có thể chờ checks dù `make check` tại máy đã đạt. Cách áp dụng bảo vệ nằm trong [hướng dẫn ruleset](rulesets/README.md).

Workflow dùng `ubuntu-latest` cần tổ chức cho phép **Standard hosted runners**. Trong **Organization Settings → Actions → General**, ô **Disable for all repositories** phải bỏ tích để dùng runner chuẩn. Xem [cách kiểm tra workflow chờ runner](docs/local-checks.md#-workflow-chờ-runner).

Quy tắc định dạng: UTF-8, LF, tab độ rộng 4; Markdown và YAML dùng 4 dấu cách. Ngoại lệ theo `.editorconfig`. Chi tiết môi trường, hook, cache và kiểm tra trực tuyến nằm trong [hướng dẫn kiểm tra tại máy](docs/local-checks.md).

## 🔒 PHẠM VI CÔNG KHAI

Phạm vi của dự án gồm tài nguyên cộng đồng, công cụ kiểm tra, sinh mẫu và phát hành. Danh sách người duy trì cùng actor trong mẫu ruleset là thông tin công khai phục vụ quy trình đóng góp. Dữ liệu truy cập và cấu hình nội bộ không thuộc bộ tài nguyên này; quy tắc chi tiết trong [ADR 00000014](docs/adr/00000014-public-repository-scope.md).

`make ruleset-files` sinh các bản ruleset cấp tổ chức từ nguồn cấp repository tại máy; không đọc hoặc ghi GitHub. Cách chọn và áp dụng mẫu nằm trong [STRUCTURE.md](STRUCTURE.md) và [hướng dẫn ruleset](rulesets/README.md).

## 🚀 PHÁT HÀNH

Phiên bản có dạng `Stable.vYYYY.MM.DDXXXX` hoặc `Beta.vYYYY.MM.DDXXXX`: ngày chuẩn bị theo giờ Việt Nam, số thứ tự gồm 4 chữ số dùng chung hai kênh và bắt đầu lại mỗi tháng. [ADR 00000012](docs/adr/00000012-monthly-releases.md) quy định cách chọn phiên bản.

`CHANGELOG.md` chứa nội dung dành cho người sử dụng của phiên bản đang chuẩn bị. Mục **CHƯA PHÁT HÀNH** được chuyển thành mục phiên bản khi chuẩn bị Release, đồng thời tạo mục **CHƯA PHÁT HÀNH** trống cho lần tiếp theo. Tệp giữ mục phiên bản vừa chuẩn bị đến lần chuẩn bị kế tiếp; lịch sử các bản đã công bố nằm ở [GitHub Releases](https://github.com/TOANQUYNHLLC/.github/releases).

### ✍️ BIÊN SOẠN NỘI DUNG

Mỗi gạch đầu dòng nêu một thay đổi và ảnh hưởng cụ thể với người sử dụng. Nhóm nội dung theo **THÊM**, **THAY ĐỔI**, **SỬA LỖI**, **BẢO MẬT**, **NGỪNG HỖ TRỢ**, **LOẠI BỎ**; chỉ tạo nhóm có nội dung. Dùng mục **LƯU Ý ÁP DỤNG** khi cần hướng dẫn thiết lập, nâng cấp hoặc xử lý thay đổi phá vỡ tương thích. Tiêu đề viết HOA, liên kết dùng URL tuyệt đối vì nội dung được đưa vào GitHub Release.

Tổng hợp nội dung khi chuẩn bị phát hành, tập trung vào kết quả sử dụng; không chép danh sách commit, báo cáo rà soát hoặc log kiểm tra vào CHANGELOG. Phiên bản và ngày chỉ được điền khi chuẩn bị bản cụ thể.

### 🌱 PHIÊN BẢN ĐẦU TIÊN

Khi chưa có tag, liên kết **CHƯA PHÁT HÀNH** trỏ tới repository. Chuẩn bị bản đầu tiên trên branch phát hành theo các bước sau:

1. Chọn phiên bản theo ngày chuẩn bị ở Việt Nam, kênh Stable hoặc Beta và số thứ tự `0001` nếu tháng chưa có tag phát hành.
2. Chuyển nội dung **CHƯA PHÁT HÀNH** xuống mục `## [<phiên bản>](https://github.com/TOANQUYNHLLC/.github/releases/tag/<phiên bản>) — YYYY-MM-DD`, điền phiên bản và ngày thực tế. Giữ mục **CHƯA PHÁT HÀNH** trống ở trên cùng, đổi liên kết thành `https://github.com/TOANQUYNHLLC/.github/compare/<phiên bản>...HEAD`.
3. Xem trước bằng `make release-notes TAG=<phiên bản>`, chạy `make check`, commit có chữ ký rồi mở PR theo [mẫu phát hành](.github/PULL_REQUEST_TEMPLATE/release.md). Sau khi hợp nhất, gắn và đẩy tag trên commit `main` chứa nội dung phiên bản.
4. Khi Actions bật, workflow `release.yml` tạo GitHub Release từ mục phiên bản. Khi Actions tắt, chạy `python3 scripts/release.py create <phiên bản>` sau khi đẩy tag.

### 📦 CÁC PHIÊN BẢN TIẾP THEO

1. Tổng hợp nội dung dành cho người sử dụng vào mục **CHƯA PHÁT HÀNH** trên một branch đóng góp, kiểm tra và hợp nhất PR chứa nội dung đó vào `main`.
2. Chuyển về `main`, kéo bằng `git pull --ff-only` và bảo đảm cây làm việc sạch, trùng `origin/main`. Chạy `make release-pr` để tạo PR chuyển nội dung thành mục phiên bản; lệnh này đọc nội dung đã có trên `main` và trả tệp tại máy về trạng thái trước khi chạy.
3. Xem nội dung bằng `make release-notes TAG=<phiên bản>` trên branch của PR phát hành, xác nhận checklist, hoàn thành kiểm tra và hợp nhất bằng Merge hoặc Squash.
4. Gắn và đẩy tag trên `main`, sau đó công bố bằng workflow hoặc lệnh `create` như bản đầu tiên.

Khi Actions bật, workflow `monthly-release.yml` thực hiện bước chuẩn bị từ nội dung đã có trên nhánh mặc định, theo lịch 07:00 giờ Việt Nam ngày 1 hằng tháng hoặc khi chạy thủ công. Workflow yêu cầu có tag trước đó và commit mới; mục **CHƯA PHÁT HÀNH** trống chặn chuẩn bị.

Chuẩn bị Beta bằng `python3 scripts/release.py prepare --channel Beta --open-pr`. Lệnh chuẩn bị tự động dùng tag trước đó để xác định thay đổi; nội dung trống, lỗi đọc tag hoặc phiên bản không hợp lệ chặn chuẩn bị. Tag của Release bất biến phải được giữ nguyên sau công bố.

Workflow Release của repository này yêu cầu mục phiên bản trong CHANGELOG. Workflow mẫu cho dự án khác cho phép GitHub tự sinh nội dung khi thiếu mục của tag; nhãn phân nhóm nằm trong `.github/release.yml`. Với PR do `GITHUB_TOKEN` mở hoặc cập nhật, người có quyền ghi phê duyệt lượt chạy khi GitHub hiển thị **Approve workflows to run**, theo [cơ chế kích hoạt workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow#triggering-a-workflow-from-a-workflow).

## 🧰 DANH SÁCH LỆNH

| Lệnh                       | Tác dụng                                                                                                                                                                                                                                |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make`                     | Xem danh sách lệnh                                                                                                                                                                                                                      |
| `make quick`               | Kiểm tra nhanh: chỉ thu hẹp tests khi mọi tệp thay đổi là test; trường hợp khác chạy đầy đủ                                                                                                                                             |
| `make check`               | Mọi nhóm kiểm tra, chạy song song                                                                                                                                                                                                       |
| `make validate`            | Kiểm tra nội dung bằng `scripts/validate.py`                                                                                                                                                                                            |
| `make test`                | Test tự động của các script, song song theo CPU khả dụng                                                                                                                                                                                |
| `make format`              | Định dạng lại toàn bộ bằng Prettier và ruff                                                                                                                                                                                             |
| `make format-check`        | Prettier, ruff format, ruff check — job "Định dạng (Prettier, ruff)"                                                                                                                                                                    |
| `make lint`                | shellcheck, actionlint — job "Shell script và workflow"                                                                                                                                                                                 |
| `make conventions`         | Tên branch và tiêu đề commit theo quy ước                                                                                                                                                                                               |
| `make audit`               | Dependency có lỗ hổng mức high trở lên                                                                                                                                                                                                  |
| `make tools`               | Kiểm tra đã cài đủ công cụ; cài thư viện Node.js nếu thiếu hoặc sai phiên bản                                                                                                                                                           |
| `make hooks`               | Cài git hook và mẫu commit `.gitmessage`                                                                                                                                                                                                |
| `make sync [BRANCH=…]`     | Chuyển branch (mặc định `main`), kéo bằng fast-forward và dọn branch local đã hợp nhất; yêu cầu cây làm việc sạch                                                                                                                       |
| `make cleanup`             | `git clean -fdx`: **xóa vĩnh viễn** mọi tệp git không quản lý — tệp mới chưa `git add`, tệp bị `.gitignore` bỏ qua (`node_modules/`, `.cache/`, `.env`…); xem trước bằng `git clean -ndx`. Lần kiểm tra sau tự cài lại thư viện Node.js |
| `make links`               | Liên kết bên ngoài còn hoạt động; bản `security.txt` trên website khớp repository                                                                                                                                                       |
| `make versions`            | Công cụ trong `mise.toml`, action chỉ có trong `workflow-templates/` có bản phát hành mới hơn                                                                                                                                           |
| `make forms REF=…`         | Kiểm tra Issue theo ref; Discussion chỉ xác minh trên nhánh mặc định, ref khác báo chưa xác minh và trả mã lỗi (mặc định `main`)                                                                                                        |
| `make release-notes TAG=…` | Xem trước nội dung GitHub Release của một tag                                                                                                                                                                                           |
| `make release-prepare`     | Chuyển mục CHƯA PHÁT HÀNH thành phiên bản của tháng nếu có thay đổi kể từ tag trước                                                                                                                                                     |
| `make ruleset-files`       | Sinh mẫu ruleset cấp tổ chức tại máy, không cần đăng nhập GitHub                                                                                                                                                                        |
| `make release-pr`          | Chuẩn bị rồi mở Pull Request phát hành tại máy (cần GitHub CLI, đứng ở `main` sạch)                                                                                                                                                     |

## 📁 TÀI NGUYÊN VÀ CÔNG CỤ

**Hồ sơ và quy trình đóng góp**

| Đường dẫn                                              | Chức năng                                                                                         |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| [`profile/README.md`](profile/README.md)               | Trang giới thiệu công khai của CÔNG TY TNHH TOÀN QUỲNH trên GitHub                                |
| [`GOVERNANCE.md`](GOVERNANCE.md)                       | Vai trò, cách ra quyết định, đánh giá và hợp nhất, thay đổi người quản trị                        |
| [`MAINTAINERS.md`](MAINTAINERS.md)                     | Người duy trì công khai và chủ sở hữu mã                                                          |
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
| [`rulesets/`](rulesets/)                         | Ruleset **Protect Main**, **Protect Release Tags**, **Protect Pushes** cấp repository và bản cấp tổ chức — xem [`rulesets/README.md`](rulesets/README.md)                               |
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
| [`scripts/rulesets.py`](scripts/rulesets.py)                                                | Kiểm tra hợp đồng và sinh mẫu ruleset offline                                                                                                         |
| [`scripts/maintainers.py`](scripts/maintainers.py)                                          | Danh sách người duy trì công khai, đối chiếu với tài liệu và ruleset                                                                                  |
| [`scripts/github.py`](scripts/github.py)                                                    | Gọi GitHub CLI phục vụ quy trình phát hành                                                                                                            |
| [`scripts/check-markdown-links.py`](scripts/check-markdown-links.py)                        | Liên kết nội bộ trong Markdown (dùng chung với `validate.py` và workflow mẫu `docs-check.yml`)                                                        |
| [`scripts/markdown.py`](scripts/markdown.py)                                                | Bỏ nội dung mã trong Markdown, dùng chung cho kiểm tra liên kết nội bộ, liên kết bên ngoài, tiêu đề, thụt lề và nhận diện cấu trúc nội dung phát hành |
| [`scripts/check-gofmt.py`](scripts/check-gofmt.py)                                          | Định dạng Go cho workflow mẫu `go-ci.yml`                                                                                                             |
| [`scripts/check-external-links.py`](scripts/check-external-links.py)                        | Liên kết bên ngoài còn hoạt động; bản `security.txt` trên website khớp repository                                                                     |
| [`scripts/check-github-forms.py`](scripts/check-github-forms.py)                            | GitHub chấp nhận biểu mẫu Issue, Discussion (lỗi khóa chỉ hiện trên trang xem tệp)                                                                    |
| [`scripts/check-tool-versions.py`](scripts/check-tool-versions.py)                          | Công cụ trong `mise.toml` và action chỉ có trong `workflow-templates/` (Dependabot không theo dõi) có bản phát hành mới hơn                           |
| [`scripts/test_*.py`](scripts/) · [`scripts/testsupport.py`](scripts/testsupport.py)        | Tests và công cụ hỗ trợ dựng môi trường kiểm thử                                                                                                      |

**Cấu hình và công cụ phát triển**

| Đường dẫn                                                                                            | Chức năng                                                                                                                                                     |
| ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`Makefile`](Makefile)                                                                               | Lệnh thiết lập, kiểm tra, đồng bộ Git, sinh mẫu ruleset và phát hành                                                                                          |
| [`mise.toml`](mise.toml) · [`.nvmrc`](.nvmrc) · [`package.json`](package.json)                       | Nguồn phiên bản duy nhất: Python, ruff, ShellCheck, actionlint; Node.js; Prettier (`devEngines` chặn phiên bản sai)                                           |
| [`.editorconfig`](.editorconfig) · [`.prettierrc.json`](.prettierrc.json) · [`ruff.toml`](ruff.toml) | Quy tắc định dạng (mục [PHÁT TRIỂN CỤC BỘ](#️-phát-triển-cục-bộ))                                                                                              |
| [`.gitattributes`](.gitattributes) · [`.gitignore`](.gitignore)                                      | Xuống dòng theo loại tệp, tệp nhị phân; bỏ qua tệp tạm, `node_modules/`, bí mật                                                                               |
| [`.devcontainer/`](.devcontainer/) · [`.vscode/extensions.json`](.vscode/extensions.json)            | Môi trường Dev Container, Codespaces và cấu hình editor                                                                                                       |
| [`shell/sync.sh`](shell/sync.sh) · [`shell/prune-branches.sh`](shell/prune-branches.sh)              | Chuyển, kéo branch bằng fast-forward và dọn branch local đã hợp nhất có branch theo dõi bị xóa                                                                |
| [`.gitmessage`](.gitmessage)                                                                         | Mẫu commit theo quy ước                                                                                                                                       |
| [`pyproject.toml`](pyproject.toml)                                                                   | Python tối thiểu của script (`requires-python`) để ruff trong VS Code và `ruff check` gõ tay kiểm tra giống `make check`; không đóng gói, không có dependency |
| [`.npmrc`](.npmrc) · [`.shellcheckrc`](.shellcheckrc)                                                | npm ghi phiên bản chính xác, không tạo `package-lock.json`; cấu hình ShellCheck                                                                               |

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
    Tài nguyên cộng đồng và công cụ kiểm tra dùng chung của tổ chức.
</p>
