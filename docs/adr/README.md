# 🧭 BẢN GHI QUYẾT ĐỊNH KIẾN TRÚC

Mỗi quyết định quan trọng về quy ước, công cụ hoặc quy trình được ghi thành một tệp ADR (Architecture Decision Record) để người đến sau hiểu **vì sao** dự án làm như vậy.

| Số                                            | Quyết định                                                                   | Trạng thái | Ngày       |
| --------------------------------------------- | ---------------------------------------------------------------------------- | ---------- | ---------- |
| [0001](0001-tab-indentation.md)               | Thụt lề bằng tab; chỉ ngôn ngữ bắt buộc mới dùng dấu cách                    | Chấp nhận  | 2026-10-03 |
| [0002](0002-line-endings.md)                  | Xuống dòng LF; chỉ loại tệp bắt buộc mới dùng CRLF                           | Chấp nhận  | 2026-10-03 |
| [0003](0003-branch-and-commit-conventions.md) | Tên branch tiếng Anh; commit, tiêu đề Pull Request theo Conventional Commits | Chấp nhận  | 2026-10-03 |
| [0004](0004-protect-main-ruleset.md)          | Ruleset Protect Main bảo vệ nhánh chính                                      | Chấp nhận  | 2026-10-03 |
| [0005](0005-protect-release-tags.md)          | Ruleset Protect Release Tags cho tag phát hành `v*`                          | Chấp nhận  | 2026-10-03 |
| [0006](0006-signed-commits-no-rebase.md)      | Commit có chữ ký trên nhánh chính và tag; không hợp nhất bằng Rebase         | Chấp nhận  | 2026-10-03 |
| [0007](0007-org-push-ruleset.md)              | Push ruleset Protect Pushes cấp tổ chức                                      | Chấp nhận  | 2026-10-03 |
| [0008](0008-mise-single-version-source.md)    | `mise.toml` là nguồn phiên bản công cụ duy nhất                              | Chấp nhận  | 2026-10-03 |
| [0009](0009-checks-as-scripts.md)             | Mọi kiểm tra là script trong `scripts/`, ưu tiên Python, chạy được tại máy   | Chấp nhận  | 2026-10-03 |
| [0010](0010-camel-case-names.md)              | Tên tự đặt viết camelCase tiếng Anh; cú pháp của ngôn ngữ giữ nguyên         | Chấp nhận  | 2026-10-03 |
| [0011](0011-git-hooks.md)                     | Git hook kiểm tra đúng nội dung được commit, được đẩy; đối chiếu sau khi kéo | Chấp nhận  | 2026-10-03 |
| [0012](0012-monthly-releases.md)              | Phát hành hằng tháng từ `CHANGELOG.md`                                       | Chấp nhận  | 2026-10-03 |
| [0013](0013-docs-match-code.md)               | Tài liệu luôn khớp với code                                                  | Chấp nhận  | 2026-10-03 |

## ✍️ CÁCH THÊM ADR

1. Chép [`template.md`](template.md) thành `NNNN-short-title.md` (tiếng Anh, nối bằng dấu gạch ngang) với số kế tiếp.
2. Điền bối cảnh, quyết định, hệ quả; trạng thái **Đề xuất**.
3. Tạo Pull Request; khi được hợp nhất, đổi trạng thái thành **Chấp nhận** và thêm vào bảng trên.
4. Không sửa nội dung ADR đã chấp nhận — khi đổi quyết định, tạo ADR mới (ghi **Điều chỉnh:** ADR cũ) và chỉ đổi dòng trạng thái của ADR cũ thành **Bị thay thế bởi NNNN**, hoặc **Bị thay thế một phần bởi NNNN** kèm phần bị thay thế; cập nhật cột trạng thái trong bảng trên.
