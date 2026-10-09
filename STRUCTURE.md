# 📁 CẤU TRÚC VÀ PHẠM VI ÁP DỤNG

Repository `TOANQUYNHLLC/.github` cung cấp hồ sơ tổ chức, tệp cộng đồng và tài nguyên dùng chung. [README.md](README.md) là điểm bắt đầu; tài liệu này giải thích vị trí tệp và cách dùng trong repository đích.

## 🗂️ CÁC NHÓM TÀI NGUYÊN

| Vị trí                         | Nội dung                                                                         |
| ------------------------------ | -------------------------------------------------------------------------------- |
| Gốc repository                 | README, chính sách cộng đồng, quản trị, cấu hình công cụ và nguồn cài đặt GitHub |
| `profile/`                     | Hồ sơ hiển thị trên trang tổ chức                                                |
| `.github/`                     | Biểu mẫu, workflows và cấu hình phục vụ GitHub                                   |
| `workflow-templates/`          | Workflow mẫu, metadata và icon dùng trong bộ chọn Actions                        |
| `repository-templates/`        | Tệp nguồn để chọn và chép vào dự án                                              |
| `scripts/`                     | Kiểm tra, công cụ quản trị và tests                                              |
| `shell/`                       | Tiện ích Git tại máy                                                             |
| `rulesets/`                    | Nguồn bảo vệ nhánh, tag và push                                                  |
| `docs/`, `docs/adr/`, `specs/` | Hướng dẫn vận hành, quyết định kiến trúc và quy trình rà soát                    |

`.github` là tên repository và cũng là tên thư mục cấu hình bên trong. Vì vậy, đường dẫn local `.github/.github/ISSUE_TEMPLATE/` hợp lệ khi thư mục đầu là gốc repository. Dự án khác chỉ cần `<dự án>/.github/ISSUE_TEMPLATE/`.

## 📋 TỆP CỘNG ĐỒNG MẶC ĐỊNH

GitHub dùng nội dung từ repository `.github` công khai khi repository đích cùng tổ chức chưa có bản riêng tương ứng. Mặc định có thể áp dụng cho repository công khai hoặc riêng tư; tệp không được sao chép vào cây Git, bản clone hoặc gói tải xuống.

| File hoặc đường dẫn                             | Vị trí trong repository `.github` | Tác dụng                                                      |
| ----------------------------------------------- | --------------------------------- | ------------------------------------------------------------- |
| `CONTRIBUTING.md`                               | Gốc, `.github/` hoặc `docs/`      | Hướng dẫn đóng góp                                            |
| `CODE_OF_CONDUCT.md`                            | Gốc, `.github/` hoặc `docs/`      | Quy tắc ứng xử                                                |
| `SECURITY.md`                                   | Gốc, `.github/` hoặc `docs/`      | Hướng dẫn báo cáo bảo mật                                     |
| `SUPPORT.md`                                    | Gốc, `.github/` hoặc `docs/`      | Kênh hỗ trợ                                                   |
| `ACCESSIBILITY.md`                              | Gốc, `.github/` hoặc `docs/`      | Mục tiêu, hạn chế và cách báo cáo vấn đề về khả năng tiếp cận |
| `PULL_REQUEST_TEMPLATE.md`                      | Gốc, `.github/` hoặc `docs/`      | Một mẫu Pull Request                                          |
| `PULL_REQUEST_TEMPLATE/`                        | Gốc, `.github/` hoặc `docs/`      | Nhiều mẫu Pull Request                                        |
| `.github/ISSUE_TEMPLATE/*.md`                   | Đúng đường dẫn.                   | Mẫu issue Markdown                                            |
| `.github/ISSUE_TEMPLATE/*.yml`                  | Đúng đường dẫn.                   | Form issue có trường nhập                                     |
| `.github/ISSUE_TEMPLATE/config.yml`             | Đúng đường dẫn.                   | Cấu hình bộ mẫu issue và liên kết hỗ trợ                      |
| `.github/DISCUSSION_TEMPLATE/*.yml`             | Đúng đường dẫn.                   | Form danh mục Discussions                                     |
| `.github/FUNDING.yml`                           | Đúng đường dẫn.                   | Nút tài trợ                                                   |
| `.github/VULNERABILITY_REPORT.yml` hoặc `.yaml` | Đúng đường dẫn.                   | Form báo cáo lỗ hổng riêng tư                                 |

Tệp có nhiều vị trí được tìm theo thứ tự `.github/`, gốc, `docs/`; repository này đặt tài liệu cộng đồng ở gốc và biểu mẫu trong `.github/`. Bộ Issue riêng hợp lệ, kể cả `config.yml`, thay thế toàn bộ bộ mặc định. Labels phải được tạo tại repository dùng mẫu.

Discussion cần bật tính năng và có category slug phù hợp với tên tệp. Báo cáo lỗ hổng cần bật Private vulnerability reporting. Biểu mẫu nằm trên nhánh mặc định; tệp mẫu không tự bật tính năng hoặc tạo category.

Pull Request có mẫu chung và mẫu theo loại công việc. Dùng `?quick_pull=1&template=feature.md` trên URL so sánh nhánh, hoặc `&template=feature.md` khi URL đã có query. Tên tệp theo `.github/PULL_REQUEST_TEMPLATE/`; xem [cách chọn mẫu](CONTRIBUTING.md#-chọn-mẫu-pull-request). Liên kết trong biểu mẫu dùng URL tuyệt đối vì biểu mẫu hiển thị ở repository khác.

## ⚙️ TÀI NGUYÊN CẦN THIẾT LẬP RIÊNG

Workflows, `CODEOWNERS`, Dependabot, labels, ruleset, secrets, variables, quyền team và cài đặt tính năng không tự được thiết lập qua tệp cộng đồng. Cấu hình công cụ, manifests, README, hướng dẫn AI và chính sách quản trị cần phù hợp với dự án đích.

Workflow mẫu được chọn trong **Actions → New workflow** hoặc chép vào `.github/workflows/`. Kiểm tra dùng scripts tổ chức bằng cách checkout vào `.org/`; đó là dùng chung script. Workflow hiện có không khai báo `workflow_call`, nên không gọi như reusable workflow bằng `jobs.<job_id>.uses`.

## 📦 TEMPLATE REPOSITORY

Một repository được bật **Template repository** sao chép cây tệp tại thời điểm tạo dự án. Thư mục `repository-templates/` chỉ chứa nguồn; phải chọn và đặt tệp ở đường dẫn đích trước khi dùng tính năng template.

| Nguồn hiện có                                                                                                                                                                    | Đường dẫn trong template dự án                                      | Điều kiện và nội dung cần chỉnh                                                                                                                            |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`.gitignore`](.gitignore), [`.gitattributes`](.gitattributes), [`.editorconfig`](.editorconfig)                                                                                 | Giữ tên ở gốc dự án                                                 | Điều chỉnh loại tệp sinh ra, quy tắc Git và định dạng theo công nghệ; giữ các lockfile dự án cần để cài dependency tái lập được                            |
| [`.prettierrc.json`](.prettierrc.json), [`ruff.toml`](ruff.toml), [`rustfmt.toml`](repository-templates/rustfmt.toml), [`.clang-format`](repository-templates/.clang-format)     | Giữ tên ở gốc dự án                                                 | Chỉ chọn formatter/linter được dự án sử dụng và khai báo công cụ cần thiết trong cấu hình của dự án                                                        |
| [`.nvmrc`](.nvmrc), phiên bản Python trong [`mise.toml`](mise.toml)                                                                                                              | `.nvmrc` cho Node.js; `.python-version` cho workflow Python hiện có | Dùng phiên bản phù hợp dự án; `.python-version` được sinh từ nguồn phiên bản Python, không phải tệp nguồn có sẵn để chép                                   |
| [`repository-templates/CODEOWNERS`](repository-templates/CODEOWNERS)                                                                                                             | `.github/CODEOWNERS`                                                | Chỉnh phạm vi đường dẫn và team/người phụ trách; chủ sở hữu mã phải có quyền ghi tại repo đích; yêu cầu phê duyệt cần ruleset hoặc branch protection riêng |
| [`repository-templates/dependabot.yml`](repository-templates/dependabot.yml)                                                                                                     | `.github/dependabot.yml`                                            | Giữ các ecosystem thực tế được dùng; chỉnh thư mục manifest, lịch cập nhật và labels theo dự án                                                            |
| [`repository-templates/labeler.yml`](repository-templates/labeler.yml) và [`workflow-templates/labeler.yml`](workflow-templates/labeler.yml)                                     | `.github/labeler.yml` và `.github/workflows/labeler.yml`            | Dùng cả cấu hình và workflow khi cần tự gắn nhãn PR; chỉnh glob theo cây mã nguồn và tạo labels ở repo đích                                                |
| [`repository-templates/release.yml`](repository-templates/release.yml)                                                                                                           | `.github/release.yml`                                               | Dùng khi tạo Release với nội dung GitHub tự sinh; cấu hình không tự tạo Release; các labels cần tồn tại ở repo đích                                        |
| Các workflow được chọn từ [`workflow-templates/`](workflow-templates/)                                                                                                           | `.github/workflows/`                                                | Chọn theo công nghệ và nhu cầu kiểm tra; chỉnh nhánh, lệnh, quyền và cấu hình phụ thuộc trước khi dùng                                                     |
| [`AGENTS.md`](AGENTS.md), [hướng dẫn Copilot](.github/copilot-instructions.md), [instructions](.github/instructions/), [agents](.github/agents/)                                 | `AGENTS.md` và các đường dẫn tương ứng trong `.github/`             | Viết lại hướng dẫn theo dự án đích; chỉnh `applyTo`, liên kết, lệnh và phạm vi agent vốn đang dành cho repository tổ chức                                  |
| [`repository-templates/.dockerignore`](repository-templates/.dockerignore), [`.env.example`](repository-templates/.env.example), [`PRIVACY.md`](repository-templates/PRIVACY.md) | `.dockerignore`, `.env.example`, `PRIVACY.md` ở gốc dự án           | Chỉ thêm khi dự án cần; `.env.example` dùng giá trị mẫu; điền nội dung sản phẩm và rà soát chính sách quyền riêng tư trước khi công bố                     |

Workflow chép vào template cần thay `$default-branch` bằng nhánh thực tế. GitHub chỉ tự xử lý placeholder khi tạo từ bộ chọn workflow mẫu. Metadata `.properties.json` và icon phục vụ bộ chọn, không cần chép sang dự án.

Chuẩn bị manifests, lockfiles, tệp phiên bản và lệnh workflow gọi. Node.js CI dùng `.nvmrc` và `npm ci`, chỉ chạy script lint/test/build có trong package. Python CI dùng `.python-version`, cài requirements và package khi dự án có khai báo package; pyproject chỉ cấu hình công cụ không kích hoạt cài package. Poetry `package-mode = false` cần luồng cài dependency riêng hoặc requirements. Pytest chạy khi có tệp trong `tests/`.

`python3 scripts/org-setup.py files --repo <tên>` xem trước tệp thiếu; `--apply` mở PR cho các tệp thuộc danh sách được quản lý. Lệnh không ghi đè tệp đã có, không chép toàn bộ template và bỏ qua repository chưa có commit. Phạm vi theo [mẫu tệp](repository-templates/README.md).

Tệp tạo từ template không tự cập nhật theo nguồn. Sau tạo, đối chiếu cài đặt, nhãn, quyền và ruleset theo [ROADMAP.md](ROADMAP.md) và [cài đặt GitHub](docs/github-settings.md).

## ✅ KIỂM CHỨNG

| Nội dung                      | Cách kiểm chứng                                                                                                                         | Điều kiện cần                                                                                                                                                   |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tài liệu cộng đồng mặc định   | Đối chiếu cây tệp của nhánh mặc định ở repo nguồn và repo đích; mở các liên kết cộng đồng trên repo đích để xác nhận tài liệu được dùng | Repo nguồn `.github` public; repo đích không có tài liệu riêng cùng loại                                                                                        |
| Mẫu Issue và `config.yml`     | Mở trang tạo Issue của repo đích, kiểm tra bộ chọn biểu mẫu, trường nhập và liên kết liên hệ                                            | Issues bật; repo đích không có mẫu hoặc cấu hình Issue riêng hợp lệ                                                                                             |
| Labels của mẫu Issue          | Đọc danh sách labels của từng repo qua GitHub CLI/API hoặc trang Issues → Labels; đối chiếu với trường `labels` trong các mẫu           | `bug`, `documentation`, `enhancement`, `question`, `tests`, `ci`, `needs triage` phải có ở repo nguồn và từng repo dùng mẫu; `labels.yml` chỉ là nguồn cấu hình |
| Mẫu Discussion                | Đối chiếu tên tệp với slug danh mục và mở trang tạo Discussion theo từng danh mục ở repo đích                                           | Discussions bật; danh mục phù hợp tồn tại                                                                                                                       |
| Form báo cáo lỗ hổng riêng tư | Đọc cài đặt Private vulnerability reporting; mở trang báo cáo bằng tài khoản GitHub và xác nhận các trường tùy chỉnh xuất hiện          | Form trên nhánh mặc định; repo đích bật báo cáo riêng tư; có tài khoản truy cập giao diện                                                                       |
| Workflow mẫu                  | Đối chiếu từng `.yml` với `.properties.json`, icon và bộ lọc `filePatterns`; mở Actions → New workflow ở repo đích rồi xem nội dung mẫu | Repo đích cho phép Actions; dự án phù hợp bộ lọc của mẫu; tài khoản có quyền tạo workflow                                                                       |

Validator kiểm tra cấu trúc tại máy; `make forms` xác minh Issue và Discussion theo phạm vi GitHub hỗ trợ. Biểu mẫu lỗ hổng riêng tư cần mở trang bằng tài khoản phù hợp để đối chiếu trường thực tế. Trang chuyển hướng đăng nhập không chứng minh biểu mẫu đã hoạt động; không gửi báo cáo thử để kiểm tra.

Xác minh trên repository đích nằm trong phạm vi được giao; việc kiểm tra không tự cho phép tạo dự án, bật tính năng hoặc đẩy cấu hình. Công cụ kiểm tra và giới hạn theo [hướng dẫn tại máy](docs/local-checks.md).

## 📜 BẢN QUYỀN VÀ GIẤY PHÉP

Không tự thêm giấy phép nguồn mở hoặc tuyên bố cho phép phân phối lại nội dung của tổ chức. Repository đích phải có chính sách giấy phép phù hợp riêng; giữ thông báo bản quyền và giấy phép bắt buộc của nội dung bên thứ ba. Tệp giấy phép trong repository `.github`, nếu có, không tự áp dụng cho mã nguồn dự án khác.

## 📚 TÀI LIỆU THAM KHẢO

- [Creating a default community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [Configuring private vulnerability reporting for a repository](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository)
- [Creating a pull request template for your repository](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository)
- [Using query parameters to create a pull request](https://docs.github.com/en/pull-requests/reference/using-query-parameters-to-create-a-pull-request)
- [Reusing workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)
- [Creating workflow templates for your organization](https://docs.github.com/en/actions/how-tos/reuse-automations/create-workflow-templates)
- [Creating a template repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository)
- [Creating a repository from a template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template)

Đối chiếu tài liệu chính thức khi triển khai để xác nhận điều kiện hỗ trợ và cách áp dụng của GitHub.
