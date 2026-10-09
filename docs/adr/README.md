# 🧭 BẢN GHI QUYẾT ĐỊNH KIẾN TRÚC

ADR (Architecture Decision Record) mô tả các quyết định về quy ước, công cụ và vận hành của repository. Mỗi chủ đề có một tài liệu hoàn chỉnh gồm bối cảnh, quyết định, lựa chọn và hệ quả. Mã ADR là định danh dùng để tham chiếu giữa code và tài liệu.

`make check` đối chiếu ngày và trạng thái trong bảng với từng ADR; trạng thái là **Đề xuất** hoặc **Chấp nhận**.

| Số                                                    | Quyết định                                                                                            | Trạng thái | Ngày       |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ---------- | ---------- |
| [00000001](00000001-tab-indentation.md)               | Thụt lề bằng tab; chỉ ngôn ngữ bắt buộc mới dùng dấu cách                                             | Chấp nhận  | 2026-10-03 |
| [00000002](00000002-line-endings.md)                  | Xuống dòng LF; chỉ loại tệp bắt buộc mới dùng CRLF                                                    | Chấp nhận  | 2026-10-03 |
| [00000003](00000003-branch-and-commit-conventions.md) | Tên branch tiếng Anh; commit, tiêu đề Pull Request theo Conventional Commits                          | Chấp nhận  | 2026-10-03 |
| [00000004](00000004-protect-main.md)                  | Ruleset Protect Main bảo vệ nhánh chính                                                               | Chấp nhận  | 2026-10-03 |
| [00000005](00000005-organization-protect-pushes.md)   | Push ruleset Protect Pushes cấp tổ chức                                                               | Chấp nhận  | 2026-10-03 |
| [00000006](00000006-protect-release-tags.md)          | Ruleset Protect Release Tags cho tag phát hành                                                        | Chấp nhận  | 2026-10-03 |
| [00000007](00000007-signed-commits-merge-methods.md)  | Commit có chữ ký trên nhánh chính và tag; phương thức hợp nhất                                        | Chấp nhận  | 2026-10-03 |
| [00000008](00000008-mise-single-version-source.md)    | `mise.toml` là nguồn phiên bản công cụ duy nhất                                                       | Chấp nhận  | 2026-10-03 |
| [00000009](00000009-checks-as-scripts.md)             | Kiểm tra trong `scripts/`, tiện ích trong `shell/`; ưu tiên Python, chạy được tại máy                 | Chấp nhận  | 2026-10-03 |
| [00000010](00000010-naming.md)                        | Tên tự đặt viết tiếng Anh: camelCase trong mã, kebab-case cho tệp; tên do công cụ quy định giữ nguyên | Chấp nhận  | 2026-10-08 |
| [00000011](00000011-git-hooks.md)                     | Git hook kiểm tra đúng nội dung được commit, được đẩy; đối chiếu sau khi kéo                          | Chấp nhận  | 2026-10-03 |
| [00000012](00000012-monthly-releases.md)              | Phát hành hằng tháng từ `CHANGELOG.md`; phiên bản theo ngày và số thứ tự                              | Chấp nhận  | 2026-10-03 |
| [00000013](00000013-related-changes.md)               | Mỗi thay đổi sửa luôn mọi chỗ liên quan; tài liệu khớp với code                                       | Chấp nhận  | 2026-10-08 |
| [00000014](00000014-local-github-settings.md)         | Nguồn cài đặt GitHub ở local                                                                          | Chấp nhận  | 2026-10-07 |
| [00000015](00000015-github-sync-verification.md)      | Xác minh cài đặt, team, ruleset và mã lỗi khi đồng bộ thất bại                                        | Đề xuất    | 2026-10-08 |

## ✍️ QUY TẮC BIÊN SOẠN

Dùng [mẫu ADR](template.md) cho chủ đề mới; tên tệp có dạng `NNNNNNNN-short-title.md`, số định danh kế tiếp gồm 8 chữ số và mô tả tiếng Anh dùng kebab-case. Mục lục phải khớp ngày, trạng thái và chủ đề trong tệp.

Khi quyết định thay đổi, viết lại ADR của chủ đề đó thành một mô tả thống nhất. ADR trình bày quyết định và lý do, không nối tiếp các mục thêm/sửa hoặc ghi diễn biến phát triển. Chỉ mô tả điều kiểm chứng được.

Trạng thái **Đề xuất** dùng cho quyết định đang chờ duyệt. Người quản trị xác nhận **Chấp nhận** trước khi hợp nhất. Ngày và trạng thái là thông tin của quyết định, không phải nhật ký sửa tài liệu.
