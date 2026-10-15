# 📄 MẪU TỆP CHO TỪNG REPOSITORY

Chọn các tệp trong danh mục dưới đây để thiết lập dự án theo công nghệ và nhu cầu. Chép tệp vào đúng đường dẫn đích, điền cấu hình của dự án rồi kiểm chứng trước khi hợp nhất.

Các cấu hình này được thiết lập trong từng repository. Khi dùng GitHub **Template repository**, đặt tệp vào cấu trúc đích trước khi tạo dự án từ template. Phân biệt với tệp cộng đồng mặc định và cách dùng workflow tại [STRUCTURE.md](../STRUCTURE.md#-template-repository).

## 📄 TỆP DÙNG CHUNG

| Tệp nguồn                                                                                                                                                              | Chép vào                 | Nội dung                                                                                                                           |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| [`.editorconfig`](../.editorconfig)                                                                                                                                    | `.editorconfig`          | Tab độ rộng 4, LF, UTF-8; dấu cách và CRLF chỉ cho loại tệp bắt buộc                                                               |
| [`.gitattributes`](../.gitattributes)                                                                                                                                  | `.gitattributes`         | LF mặc định, CRLF cho tệp bắt buộc, tệp nhị phân                                                                                   |
| [`CODEOWNERS`](CODEOWNERS)                                                                                                                                             | `.github/CODEOWNERS`     | Khai báo team `@TOANQUYNHLLC/maintainers` làm chủ sở hữu mã; cần quyền ghi và quy tắc riêng để bắt buộc phê duyệt                  |
| [`dependabot.yml`](dependabot.yml)                                                                                                                                     | `.github/dependabot.yml` | Giữ GitHub Actions và ecosystem phù hợp với manifest của dự án; chỉnh directory nếu manifest ở thư mục con                         |
| [`release.yml`](release.yml)                                                                                                                                           | `.github/release.yml`    | Nhóm nội dung GitHub Release tự tạo theo nhãn chuẩn                                                                                |
| [`labeler.yml`](labeler.yml)                                                                                                                                           | `.github/labeler.yml`    | Gắn nhãn loại theo tiền tố branch, nhãn `area: …` theo thư mục — sửa đường dẫn cho khớp dự án (đi cùng workflow mẫu `labeler.yml`) |
| [`pr-title.yml`](../workflow-templates/pr-title.yml) · [`branch-name.yml`](../workflow-templates/branch-name.yml) · [`labeler.yml`](../workflow-templates/labeler.yml) | `.github/workflows/`     | Kiểm tra tiêu đề Pull Request, tên branch (hai kiểm tra bắt buộc của Protect Main) và tự gắn nhãn                                  |

## 💻 TỆP THEO CÔNG NGHỆ

Dùng manifest của dự án để chọn runtime và formatter. Khai báo công cụ cùng dependencies trong nguồn cấu hình của dự án đích.

| Tệp nguồn                                  | Khi có                                                        | Nội dung                                                               |
| ------------------------------------------ | ------------------------------------------------------------- | ---------------------------------------------------------------------- |
| [`.prettierrc.json`](../.prettierrc.json)  | `package.json`                                                | Prettier: tab độ rộng 4; Markdown, YAML dùng dấu cách                  |
| [`.nvmrc`](../.nvmrc)                      | `package.json`                                                | Phiên bản Node.js cho workflow mẫu Node.js CI                          |
| [`ruff.toml`](../ruff.toml)                | `pyproject.toml`, `requirements.txt`, `setup.py`, `setup.cfg` | ruff format: tab độ rộng 4, LF; bộ luật lint chung                     |
| `python` trong [`mise.toml`](../mise.toml) | `pyproject.toml`, `requirements.txt`, `setup.py`, `setup.cfg` | Ghi vào `.python-version`: phiên bản Python cho workflow mẫu Python CI |
| [`rustfmt.toml`](rustfmt.toml)             | `Cargo.toml`                                                  | rustfmt: `hard_tabs = true`, độ rộng 4                                 |
| [`.clang-format`](.clang-format)           | `CMakeLists.txt`, `meson.build`                               | clang-format: `UseTab: Always`, độ rộng 4, LF                          |
| [`.dockerignore`](.dockerignore)           | `Dockerfile`, `compose.yaml`                                  | Không đưa `.git`, bí mật, tệp phát triển vào image                     |

## ✍️ NỘI DUNG RIÊNG

Điền thông tin riêng của sản phẩm trước khi sử dụng các khung dưới đây; chỉ dùng giá trị mô phỏng trong tệp mẫu.

| Tệp                            | Nội dung                                                                                           |
| ------------------------------ | -------------------------------------------------------------------------------------------------- |
| [`.env.example`](.env.example) | Mẫu biến môi trường có chú thích; tệp `.env` thật không bao giờ commit                             |
| [`PRIVACY.md`](PRIVACY.md)     | Khung chính sách quyền riêng tư cho ứng dụng xử lý dữ liệu cá nhân, sức khỏe — cần pháp lý rà soát |

## ✅ ĐIỀU KIỆN ÁP DỤNG

Kết hợp với [ruleset Protect Main](../rulesets/README.md) để bắt buộc người trong `CODEOWNERS` phê duyệt. Dự án có `Dockerfile`, `compose.yaml` hoặc lockfile riêng theo công nghệ — không có mẫu chung.

Khi chép workflow mẫu vào template dự án, đặt tại `.github/workflows/` và thay `$default-branch` bằng nhánh dự án dùng. Metadata `.properties.json` và icon phục vụ bộ chọn workflow của tổ chức, không cần chép theo workflow vào dự án. Chuẩn bị các tệp phiên bản, manifests, lockfiles và lệnh mà workflow gọi.

Labels, secrets, variables, quyền team, rulesets và cài đặt tính năng GitHub được quản lý riêng. Bản sao tạo từ template repository không tự cập nhật khi nguồn thay đổi. Các hướng dẫn và README dành riêng cho repository `.github` cần viết lại trước khi dùng trong một dự án khác.

Workflow gắn nhãn dùng `pull_request_target` để có quyền gắn nhãn cho Pull Request từ fork. Workflow chỉ đọc cấu hình của nhánh đích và metadata qua API, không checkout hay chạy mã Pull Request; concurrency tách riêng theo số PR.
