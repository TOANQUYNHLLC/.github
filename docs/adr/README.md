# 🧭 BẢN GHI QUYẾT ĐỊNH KIẾN TRÚC

Mỗi quyết định quan trọng về quy ước, công cụ hoặc quy trình được ghi thành một tệp ADR (Architecture Decision Record) để người đến sau hiểu **vì sao** dự án làm như vậy. Mỗi chủ đề có đúng một ADR, mô tả quyết định đang áp dụng; lịch sử thay đổi nằm trong git.

`make check` đối chiếu ngày và trạng thái trong bảng với từng ADR; trạng thái là **Đề xuất** hoặc **Chấp nhận**.

| Số                                            | Quyết định                                                                            | Trạng thái | Ngày       |
| --------------------------------------------- | ------------------------------------------------------------------------------------- | ---------- | ---------- |
| [0001](0001-tab-indentation.md)               | Thụt lề bằng tab; chỉ ngôn ngữ bắt buộc mới dùng dấu cách                             | Chấp nhận  | 2026-10-03 |
| [0002](0002-line-endings.md)                  | Xuống dòng LF; chỉ loại tệp bắt buộc mới dùng CRLF                                    | Chấp nhận  | 2026-10-03 |
| [0003](0003-branch-and-commit-conventions.md) | Tên branch tiếng Anh; commit, tiêu đề Pull Request theo Conventional Commits          | Chấp nhận  | 2026-10-03 |
| [0004](0004-protect-main-ruleset.md)          | Ruleset Protect Main bảo vệ nhánh chính                                               | Chấp nhận  | 2026-10-03 |
| [0005](0005-org-push-ruleset.md)              | Push ruleset Protect Pushes cấp tổ chức                                               | Chấp nhận  | 2026-10-03 |
| [0006](0006-protect-release-tags.md)          | Ruleset Protect Release Tags cho tag phát hành                                        | Chấp nhận  | 2026-10-03 |
| [0007](0007-signed-commits-merge-methods.md)  | Commit có chữ ký trên nhánh chính và tag; phương thức hợp nhất                        | Chấp nhận  | 2026-10-03 |
| [0008](0008-mise-single-version-source.md)    | `mise.toml` là nguồn phiên bản công cụ duy nhất                                       | Chấp nhận  | 2026-10-03 |
| [0009](0009-checks-as-scripts.md)             | Kiểm tra trong `scripts/`, tiện ích trong `shell/`; ưu tiên Python, chạy được tại máy | Chấp nhận  | 2026-10-03 |
| [0010](0010-camel-case-names.md)              | Tên tự đặt viết camelCase tiếng Anh; cú pháp của ngôn ngữ giữ nguyên                  | Chấp nhận  | 2026-10-03 |
| [0011](0011-git-hooks.md)                     | Git hook kiểm tra đúng nội dung được commit, được đẩy; đối chiếu sau khi kéo          | Chấp nhận  | 2026-10-03 |
| [0012](0012-monthly-releases.md)              | Phát hành hằng tháng từ `CHANGELOG.md`; phiên bản theo ngày và số thứ tự              | Chấp nhận  | 2026-10-03 |
| [0013](0013-docs-match-code.md)               | Tài liệu luôn khớp với code                                                           | Chấp nhận  | 2026-10-03 |
| [0014](0014-local-github-settings.md)         | Nguồn cài đặt GitHub ở local                                                          | Chấp nhận  | 2026-10-07 |

## ✍️ CÁCH THÊM, CẬP NHẬT ADR

1. Chủ đề mới: chép [`template.md`](template.md) thành `NNNN-short-title.md` (tiếng Anh, nối bằng dấu gạch ngang) với số kế tiếp, thêm dòng vào bảng trên.
2. Đổi quyết định của chủ đề đã có: cập nhật chính ADR đó — bối cảnh, quyết định, phương án đã cân nhắc, hệ quả — để ADR chỉ mô tả quyết định hiện hành; cập nhật tên trong bảng nếu cần.
3. Chỉ ghi điều kiểm chứng được. ADR trong Pull Request ghi **Đề xuất**; khi người quản trị duyệt, đổi thành **Chấp nhận** trước khi hợp nhất.
