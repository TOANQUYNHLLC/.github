# 📄 MẪU TỆP CHO TỪNG REPOSITORY

GitHub **không** kế thừa `CODEOWNERS` và `dependabot.yml` từ repository `.github` — mỗi repository cần tệp riêng. Chép mẫu dưới đây vào thư mục `.github/` của repository rồi sửa theo dự án.

| Mẫu                                | Chép vào                 | Nội dung                                                                    |
| ---------------------------------- | ------------------------ | --------------------------------------------------------------------------- |
| [`CODEOWNERS`](CODEOWNERS)         | `.github/CODEOWNERS`     | Người quản trị duyệt mọi thay đổi; ví dụ phân công theo thư mục cho team    |
| [`dependabot.yml`](dependabot.yml) | `.github/dependabot.yml` | Cập nhật GitHub Actions, npm, pip, Go, Docker; nhãn và tiền tố commit chuẩn |

Kết hợp với [ruleset bảo vệ nhánh chính](../rulesets/README.md) để bắt buộc người trong `CODEOWNERS` phê duyệt.
