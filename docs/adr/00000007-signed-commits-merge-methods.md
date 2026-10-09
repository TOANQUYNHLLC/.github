# 00000007. COMMIT CÓ CHỮ KÝ TRÊN NHÁNH CHÍNH VÀ TAG; PHƯƠNG THỨC HỢP NHẤT

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Chữ ký xác minh người tạo commit cần được giữ trên các đường vào nhánh chính và tag. GitHub ký commit do Merge và Squash tạo; Rebase and merge tạo lại commit mà không có khóa của tác giả.

## ✅ QUYẾT ĐỊNH

Mọi ruleset nhánh và tag trong `rulesets/` có `required_signatures`. Push ruleset không nhận quy tắc này theo [ADR 00000005](00000005-organization-protect-pushes.md).

Ruleset và cài đặt cấp repository cho phép **Merge và Squash**, với `allow_rebase_merge: false`.

**Organization Protect Main** cho phép Merge, Squash và Rebase; phạm vi gồm nhánh mặc định và `refs/heads/main`. `orgRuleset()` trong `scripts/orgsetup/rulesets.py` sinh cấu hình này từ bản cấp repository.

Người đóng góp ký commit bằng GPG hoặc SSH. Rebase tại máy được phép khi commit được ký lại. Script tạo commit thay người dùng dùng GraphQL `createCommitOnBranch` để GitHub ký.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Rebase and merge ở cấp repository không đáp ứng yêu cầu giữ chữ ký. Chỉ dùng Squash không giữ được các commit riêng khi cần; bỏ yêu cầu chữ ký không xác minh được tác giả.

## ⚖️ HỆ QUẢ

Validator bắt buộc chữ ký trong ruleset nhánh và tag. Người được bỏ qua ruleset vẫn phải ký commit theo quy định. Cấp tổ chức cần gói hỗ trợ; quyền Rebase ở cấp tổ chức không vượt qua hạn chế của ruleset và cài đặt cấp repository.
