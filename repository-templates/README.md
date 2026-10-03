# 📄 MẪU TỆP CHO TỪNG REPOSITORY

GitHub **không** kế thừa các tệp dưới đây từ repository `.github` — mỗi repository cần tệp riêng. `python3 scripts/org-setup.py files --apply --repo <tên>` mở Pull Request thêm các tệp còn thiếu (không ghi đè tệp đã có); cũng có thể chép tay.

**Mọi repository** (org-setup.py tự thêm)

| Tệp nguồn                                                                                                                                                              | Chép vào                 | Nội dung                                                                                                                           |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| [`.editorconfig`](../.editorconfig)                                                                                                                                    | `.editorconfig`          | Tab độ rộng 4, LF, UTF-8; dấu cách và CRLF chỉ cho loại tệp bắt buộc                                                               |
| [`.gitattributes`](../.gitattributes)                                                                                                                                  | `.gitattributes`         | LF mặc định, CRLF cho tệp bắt buộc, tệp nhị phân                                                                                   |
| [`CODEOWNERS`](CODEOWNERS)                                                                                                                                             | `.github/CODEOWNERS`     | Team `@TOANQUYNHLLC/maintainers` duyệt mọi thay đổi                                                                                |
| [`dependabot.yml`](dependabot.yml)                                                                                                                                     | `.github/dependabot.yml` | Chỉ giữ ecosystem repository dùng (GitHub Actions, npm, pip, Go, Docker)                                                           |
| [`release.yml`](release.yml)                                                                                                                                           | `.github/release.yml`    | Nhóm nội dung GitHub Release tự tạo theo nhãn chuẩn                                                                                |
| [`labeler.yml`](labeler.yml)                                                                                                                                           | `.github/labeler.yml`    | Gắn nhãn loại theo tiền tố branch, nhãn `area: …` theo thư mục — sửa đường dẫn cho khớp dự án (đi cùng workflow mẫu `labeler.yml`) |
| [`pr-title.yml`](../workflow-templates/pr-title.yml) · [`branch-name.yml`](../workflow-templates/branch-name.yml) · [`labeler.yml`](../workflow-templates/labeler.yml) | `.github/workflows/`     | Kiểm tra tiêu đề Pull Request, tên branch (hai kiểm tra bắt buộc của Protect Main) và tự gắn nhãn                                  |

**Theo ngôn ngữ** (org-setup.py thêm khi thấy tệp khai báo ở thư mục gốc)

| Tệp nguồn                                 | Khi có                                           | Nội dung                                              |
| ----------------------------------------- | ------------------------------------------------ | ----------------------------------------------------- |
| [`.prettierrc.json`](../.prettierrc.json) | `package.json`                                   | Prettier: tab độ rộng 4; Markdown, YAML dùng dấu cách |
| [`ruff.toml`](../ruff.toml)               | `pyproject.toml`, `requirements.txt`, `setup.py` | ruff format: tab độ rộng 4, LF                        |
| [`.python-version`](.python-version)      | như trên                                         | Phiên bản Python cho workflow mẫu Python CI           |
| [`rustfmt.toml`](rustfmt.toml)            | `Cargo.toml`                                     | rustfmt: `hard_tabs = true`, độ rộng 4                |
| [`.clang-format`](.clang-format)          | `CMakeLists.txt`, `meson.build`                  | clang-format: `UseTab: Always`, độ rộng 4, LF         |
| [`.dockerignore`](.dockerignore)          | `Dockerfile`, `compose.yaml`                     | Không đưa `.git`, bí mật, tệp phát triển vào image    |

**Chép tay khi cần** (nội dung phụ thuộc từng dự án)

| Tệp                            | Nội dung                                                                                           |
| ------------------------------ | -------------------------------------------------------------------------------------------------- |
| [`.env.example`](.env.example) | Mẫu biến môi trường có chú thích; tệp `.env` thật không bao giờ commit                             |
| [`PRIVACY.md`](PRIVACY.md)     | Khung chính sách quyền riêng tư cho ứng dụng xử lý dữ liệu cá nhân, sức khỏe — cần pháp lý rà soát |

Kết hợp với [ruleset Protect Main](../rulesets/README.md) để bắt buộc người trong `CODEOWNERS` phê duyệt. Dự án có `Dockerfile`, `compose.yaml` hoặc lockfile riêng theo công nghệ — không có mẫu chung.
