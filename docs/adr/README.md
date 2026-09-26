# 🧭 BẢN GHI QUYẾT ĐỊNH KIẾN TRÚC

Mỗi quyết định quan trọng về quy ước, công cụ hoặc quy trình được ghi thành một tệp ADR (Architecture Decision Record) để người đến sau hiểu **vì sao** dự án làm như vậy.

| Số                                        | Quyết định                                                         | Trạng thái | Ngày       |
| ----------------------------------------- | ------------------------------------------------------------------ | ---------- | ---------- |
| [0001](0001-tab-indentation.md)           | Thụt lề bằng tab; chỉ ngôn ngữ bắt buộc mới dùng dấu cách          | Chấp nhận  | 2026-09-26 |
| [0002](0002-line-endings.md)              | Xuống dòng LF; chỉ loại tệp bắt buộc mới dùng CRLF                 | Chấp nhận  | 2026-09-26 |
| [0003](0003-branch-naming.md)             | Tên branch bằng tiếng Anh, nối từ bằng dấu gạch dưới               | Chấp nhận  | 2026-09-26 |
| [0004](0004-squash-merge-and-rulesets.md) | Squash and merge và ruleset bảo vệ nhánh chính                     | Chấp nhận  | 2026-09-26 |
| [0005](0005-merge-protect-main.md)        | Gộp hai ruleset thành Protect Main; danh sách bỏ qua của `.github` | Chấp nhận  | 2026-09-26 |

## ✍️ CÁCH THÊM ADR

1. Chép [`template.md`](template.md) thành `NNNN-ten-ngan.md` với số kế tiếp.
2. Điền bối cảnh, quyết định, hệ quả; trạng thái **Đề xuất**.
3. Tạo Pull Request; khi được hợp nhất, đổi trạng thái thành **Chấp nhận** và thêm vào bảng trên.
4. Không sửa nội dung ADR đã chấp nhận — khi đổi quyết định, tạo ADR mới và đánh dấu ADR cũ **Bị thay thế bởi NNNN**.
