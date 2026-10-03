# 🧭 BẢN GHI QUYẾT ĐỊNH KIẾN TRÚC

Mỗi quyết định quan trọng về quy ước, công cụ hoặc quy trình được ghi thành một tệp ADR (Architecture Decision Record) để người đến sau hiểu **vì sao** dự án làm như vậy.

| Số                                              | Quyết định                                                         | Trạng thái                       | Ngày       |
| ----------------------------------------------- | ------------------------------------------------------------------ | -------------------------------- | ---------- |
| [0001](0001-tab-indentation.md)                 | Thụt lề bằng tab; chỉ ngôn ngữ bắt buộc mới dùng dấu cách          | Chấp nhận                        | 2026-09-26 |
| [0002](0002-line-endings.md)                    | Xuống dòng LF; chỉ loại tệp bắt buộc mới dùng CRLF                 | Chấp nhận                        | 2026-09-26 |
| [0003](0003-branch-naming.md)                   | Tên branch bằng tiếng Anh, nối từ bằng dấu gạch dưới               | Chấp nhận                        | 2026-09-26 |
| [0004](0004-squash-merge-and-rulesets.md)       | Squash and merge và ruleset bảo vệ nhánh chính                     | Thay thế một phần bởi 0005, 0006 | 2026-09-26 |
| [0005](0005-merge-protect-main.md)              | Gộp hai ruleset thành Protect Main; danh sách bỏ qua của `.github` | Thay thế một phần bởi 0006, 0008 | 2026-09-26 |
| [0006](0006-allow-all-merge-methods.md)         | Cho phép cả ba cách hợp nhất; bỏ lịch sử tuyến tính                | Chấp nhận                        | 2026-09-26 |
| [0007](0007-mise-single-version-source.md)      | `mise.toml` là nguồn phiên bản công cụ duy nhất                    | Chấp nhận                        | 2026-09-26 |
| [0008](0008-protect-release-tags.md)            | Ruleset Protect Release Tags cho tag phát hành `v*`                | Thay thế một phần bởi 0009       | 2026-09-27 |
| [0009](0009-rulesets-require-signed-commits.md) | Mọi ruleset bắt buộc commit có chữ ký                              | Thay thế một phần bởi 0010       | 2026-09-27 |
| [0010](0010-org-push-ruleset.md)                | Push ruleset Protect Pushes cấp tổ chức                            | Chấp nhận                        | 2026-09-30 |

## ✍️ CÁCH THÊM ADR

1. Chép [`template.md`](template.md) thành `NNNN-ten-ngan.md` với số kế tiếp.
2. Điền bối cảnh, quyết định, hệ quả; trạng thái **Đề xuất**.
3. Tạo Pull Request; khi được hợp nhất, đổi trạng thái thành **Chấp nhận** và thêm vào bảng trên.
4. Không sửa nội dung ADR đã chấp nhận — khi đổi quyết định, tạo ADR mới (ghi **Điều chỉnh:** ADR cũ) và chỉ đổi dòng trạng thái của ADR cũ thành **Bị thay thế bởi NNNN**, hoặc **Bị thay thế một phần bởi NNNN** kèm phần bị thay thế; cập nhật cột trạng thái trong bảng trên.
