# 0004. SQUASH AND MERGE VÀ RULESET BẢO VỆ NHÁNH CHÍNH

- **Trạng thái:** Bị thay thế một phần bởi [0005](0005-merge-protect-main.md) (danh sách bỏ qua) và [0006](0006-allow-all-merge-methods.md) (cách hợp nhất)
- **Ngày:** 2026-09-26

## 📌 BỐI CẢNH

Quy ước commit chỉ có ý nghĩa khi lịch sử nhánh chính gọn và mỗi thay đổi đi qua đánh giá. Tổ chức hiện chỉ có một người quản trị.

## ✅ QUYẾT ĐỊNH

- Nhánh chính chỉ nhận thay đổi qua Pull Request, hợp nhất bằng **Squash and merge**; tiêu đề Pull Request (đã kiểm tra theo quy ước commit) trở thành commit trên nhánh chính.
- Ruleset trong `rulesets/`: bắt buộc phê duyệt của `CODEOWNERS`, giải quyết mọi góp ý, kiểm tra tự động thành công, commit có chữ ký, cấm force push và xóa nhánh.
- Vai trò Admin được bỏ qua yêu cầu phê duyệt **chỉ khi hợp nhất Pull Request**, vì người quản trị duy nhất không thể tự phê duyệt.

## ⚖️ HỆ QUẢ

- Ruleset phải được người quản trị import thủ công; tên kiểm tra bắt buộc phải trùng tên job (được `scripts/validate.py` kiểm tra).
- Khi có thêm người quản trị, nên bỏ quyền bỏ qua của Admin.
