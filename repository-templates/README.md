# 📄 MẪU TỆP CHO TỪNG REPOSITORY

Thư mục này chứa tệp nguồn để chép vào từng dự án, không phải một GitHub template repository. GitHub **không** kế thừa các cấu hình dưới đây qua cơ chế tệp cộng đồng mặc định. Khi dùng tính năng **Template repository**, đặt tệp tại đường dẫn đích trong bảng trước khi tạo dự án mới; GitHub sao chép cấu trúc đó, không tự chuyển tệp ra khỏi thư mục `repository-templates/`. Cách chọn nội dung xem [`STRUCTURE.md`](../STRUCTURE.md#8-nội-dung-nên-đặt-trong-template-repository).

`python3 scripts/org-setup.py files --repo <tên>` chỉ xem trước. Thêm `--apply` thì script mở Pull Request thêm các tệp còn thiếu trong danh sách bên dưới, không ghi đè tệp đã có. Script bỏ qua repository nguồn `.github` và repository chưa có commit; cũng có thể chép tay theo đường dẫn đích.

**Các tệp lệnh `files` đề xuất cho repository đích**

| Tệp nguồn                                                                                                                                                              | Chép vào                 | Nội dung                                                                                                                           |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| [`.editorconfig`](../.editorconfig)                                                                                                                                    | `.editorconfig`          | Tab độ rộng 4, LF, UTF-8; dấu cách và CRLF chỉ cho loại tệp bắt buộc                                                               |
| [`.gitattributes`](../.gitattributes)                                                                                                                                  | `.gitattributes`         | LF mặc định, CRLF cho tệp bắt buộc, tệp nhị phân                                                                                   |
| [`CODEOWNERS`](CODEOWNERS)                                                                                                                                             | `.github/CODEOWNERS`     | Khai báo team `@TOANQUYNHLLC/maintainers` làm chủ sở hữu mã; cần quyền ghi và quy tắc riêng để bắt buộc phê duyệt                  |
| [`dependabot.yml`](dependabot.yml)                                                                                                                                     | `.github/dependabot.yml` | Script giữ GitHub Actions và ecosystem có manifest tương ứng ở gốc; dự án có manifest ở thư mục con cần chỉnh cấu hình             |
| [`release.yml`](release.yml)                                                                                                                                           | `.github/release.yml`    | Nhóm nội dung GitHub Release tự tạo theo nhãn chuẩn                                                                                |
| [`labeler.yml`](labeler.yml)                                                                                                                                           | `.github/labeler.yml`    | Gắn nhãn loại theo tiền tố branch, nhãn `area: …` theo thư mục — sửa đường dẫn cho khớp dự án (đi cùng workflow mẫu `labeler.yml`) |
| [`pr-title.yml`](../workflow-templates/pr-title.yml) · [`branch-name.yml`](../workflow-templates/branch-name.yml) · [`labeler.yml`](../workflow-templates/labeler.yml) | `.github/workflows/`     | Kiểm tra tiêu đề Pull Request, tên branch (hai kiểm tra bắt buộc của Protect Main) và tự gắn nhãn                                  |

**Theo ngôn ngữ** (lệnh `files` đề xuất khi thấy tệp khai báo ở thư mục gốc)

| Tệp nguồn                                  | Khi có                                                        | Nội dung                                                               |
| ------------------------------------------ | ------------------------------------------------------------- | ---------------------------------------------------------------------- |
| [`.prettierrc.json`](../.prettierrc.json)  | `package.json`                                                | Prettier: tab độ rộng 4; Markdown, YAML dùng dấu cách                  |
| [`.nvmrc`](../.nvmrc)                      | như trên                                                      | Phiên bản Node.js cho workflow mẫu Node.js CI                          |
| [`ruff.toml`](../ruff.toml)                | `pyproject.toml`, `requirements.txt`, `setup.py`, `setup.cfg` | ruff format: tab độ rộng 4, LF; bộ luật lint chung                     |
| `python` trong [`mise.toml`](../mise.toml) | như trên                                                      | Ghi vào `.python-version`: phiên bản Python cho workflow mẫu Python CI |
| [`rustfmt.toml`](rustfmt.toml)             | `Cargo.toml`                                                  | rustfmt: `hard_tabs = true`, độ rộng 4                                 |
| [`.clang-format`](.clang-format)           | `CMakeLists.txt`, `meson.build`                               | clang-format: `UseTab: Always`, độ rộng 4, LF                          |
| [`.dockerignore`](.dockerignore)           | `Dockerfile`, `compose.yaml`                                  | Không đưa `.git`, bí mật, tệp phát triển vào image                     |

**Chép tay khi cần** (nội dung phụ thuộc từng dự án)

| Tệp                            | Nội dung                                                                                           |
| ------------------------------ | -------------------------------------------------------------------------------------------------- |
| [`.env.example`](.env.example) | Mẫu biến môi trường có chú thích; tệp `.env` thật không bao giờ commit                             |
| [`PRIVACY.md`](PRIVACY.md)     | Khung chính sách quyền riêng tư cho ứng dụng xử lý dữ liệu cá nhân, sức khỏe — cần pháp lý rà soát |

Kết hợp với [ruleset Protect Main](../rulesets/README.md) để bắt buộc người trong `CODEOWNERS` phê duyệt. Dự án có `Dockerfile`, `compose.yaml` hoặc lockfile riêng theo công nghệ — không có mẫu chung.

Khi chép workflow mẫu vào template dự án, đặt tại `.github/workflows/` và thay `$default-branch` bằng nhánh dự án dùng. Metadata `.properties.json` và icon phục vụ bộ chọn workflow của tổ chức, không cần chép theo workflow vào dự án. Chuẩn bị các tệp phiên bản, manifests, lockfiles và lệnh mà workflow gọi.

Labels, secrets, variables, quyền team, rulesets và cài đặt tính năng GitHub được quản lý riêng; lệnh `files` chỉ thêm tệp. Bản sao tạo từ template repository không tự cập nhật khi nguồn thay đổi. Các hướng dẫn và README dành riêng cho repository `.github` cần viết lại trước khi dùng trong một dự án khác.

Workflow gắn nhãn dùng `pull_request_target` để có quyền gắn nhãn cho Pull Request từ fork. Workflow chỉ đọc cấu hình của nhánh đích và metadata qua API, không checkout hay chạy mã Pull Request; concurrency tách riêng theo số PR.
