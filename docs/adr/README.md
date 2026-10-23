# 🧭 QUYẾT ĐỊNH KIẾN TRÚC

ADR (Architecture Decision Record) mô tả các lựa chọn đang áp dụng cho bộ tài nguyên `.github`: định dạng, đóng góp, bảo vệ nguồn, công cụ, kiểm tra và phát hành. Mỗi mã nhận diện một chủ đề để code và hướng dẫn cùng tham chiếu.

## 📚 DANH MỤC

| Số                                                    | Quyết định                                                                                            | Trạng thái | Ngày       |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ---------- | ---------- |
| [00000001](00000001-tab-indentation.md)               | Thụt lề bằng tab; chỉ ngôn ngữ bắt buộc mới dùng dấu cách                                             | Chấp nhận  | 2026-10-03 |
| [00000002](00000002-line-endings.md)                  | Xuống dòng LF; chỉ loại tệp bắt buộc mới dùng CRLF                                                    | Chấp nhận  | 2026-10-03 |
| [00000003](00000003-branch-and-commit-conventions.md) | Tên branch tiếng Anh; commit, tiêu đề Pull Request theo Conventional Commits                          | Chấp nhận  | 2026-10-03 |
| [00000004](00000004-protect-main.md)                  | Ruleset Protect Main bảo vệ nhánh chính                                                               | Chấp nhận  | 2026-10-03 |
| [00000005](00000005-organization-protect-pushes.md)   | Push ruleset Protect Pushes cấp repository và tổ chức                                                 | Chấp nhận  | 2026-10-03 |
| [00000006](00000006-protect-release-tags.md)          | Ruleset Protect Release Tags cho tag phát hành                                                        | Chấp nhận  | 2026-10-03 |
| [00000007](00000007-signed-commits-merge-methods.md)  | Commit có chữ ký trên nhánh chính và tag; phương thức hợp nhất                                        | Chấp nhận  | 2026-10-03 |
| [00000008](00000008-mise-single-version-source.md)    | Mỗi công cụ có một nguồn phiên bản theo vai trò                                                       | Chấp nhận  | 2026-10-23 |
| [00000009](00000009-checks-as-scripts.md)             | Kiểm tra trong `scripts/`, tiện ích trong `shell/`; ưu tiên Python, chạy được tại máy                 | Chấp nhận  | 2026-10-23 |
| [00000010](00000010-naming.md)                        | Tên tự đặt viết tiếng Anh: camelCase trong mã, kebab-case cho tệp; tên do công cụ quy định giữ nguyên | Chấp nhận  | 2026-10-08 |
| [00000011](00000011-git-hooks.md)                     | Git hook kiểm tra đúng nội dung được commit, được đẩy; đối chiếu sau khi kéo                          | Chấp nhận  | 2026-10-03 |
| [00000012](00000012-monthly-releases.md)              | Phát hành hằng tháng từ `CHANGELOG.md`; phiên bản theo ngày và số thứ tự                              | Chấp nhận  | 2026-10-23 |
| [00000013](00000013-related-changes.md)               | Mỗi thay đổi sửa luôn mọi chỗ liên quan; tài liệu khớp với code                                       | Chấp nhận  | 2026-10-08 |
| [00000014](00000014-public-repository-scope.md)       | Repository công khai là nguồn duy nhất cho tài nguyên, công cụ và nguồn cài đặt GitHub                | Chấp nhận  | 2026-10-23 |
| [00000015](00000015-local-github-settings.md)         | Nguồn cài đặt GitHub ở local                                                                          | Chấp nhận  | 2026-10-23 |
| [00000016](00000016-github-sync-verification.md)      | Xác minh cài đặt, team, ruleset và mã lỗi khi đồng bộ thất bại                                        | Đề xuất    | 2026-10-23 |

## ✍️ CẤU TRÚC VÀ CÁCH DÙNG

Mỗi ADR có bối cảnh, quyết định, nguồn quy tắc hoặc cấu hình, các lựa chọn và lý do, cùng hệ quả vận hành. Đọc quyết định của chủ đề và các nguồn liên kết trước khi thay đổi quy ước; hướng dẫn thao tác cụ thể nằm trong README hoặc tài liệu chuyên đề.

Dùng [mẫu ADR](template.md) cho chủ đề mới. Tên tệp là `NNNNNNNN-short-title.md`, với mã gồm 8 chữ số và phần mô tả kebab-case tiếng Anh. Dãy mã bắt đầu từ `00000001`, liên tục và không trùng; thêm chủ đề bằng mã kế tiếp. Khi chuẩn hóa lại mã, đồng bộ tên tệp, tiêu đề, mục lục và mọi tham chiếu trong cùng thay đổi.

Trạng thái **Đề xuất** dành cho quyết định chờ duyệt; **Chấp nhận** dành cho quyết định được người quản trị phê duyệt. Ngày thể hiện thông tin của quyết định. Bảng liệt kê đúng từng ADR một lần theo mã tăng dần; liên kết trỏ đúng tên tệp. `make check` đối chiếu dãy mã, mã trong tiêu đề, liên kết mục lục, ngày, trạng thái và cấu trúc mục.

Khi sửa quyết định, biên soạn lại ADR tương ứng thành mô tả hiện hành và đồng bộ code, tests, cấu hình, hướng dẫn liên quan. Không thêm mốc cập nhật, diễn biến thử nghiệm, danh sách sửa lỗi hay log phát triển. Bằng chứng đánh giá và kiểm thử đặt trong PR.
