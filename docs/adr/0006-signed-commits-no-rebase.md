# 0006. COMMIT CÓ CHỮ KÝ TRÊN NHÁNH CHÍNH VÀ TAG; KHÔNG HỢP NHẤT BẰNG REBASE

- **Trạng thái:** Bị thay thế một phần bởi 0018 (phương thức hợp nhất của Protect Main cấp tổ chức)
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Commit có chữ ký đã xác minh cho biết ai thực sự tạo ra thay đổi. Chữ ký chỉ có giá trị khi mọi đường vào nhánh chính và tag phát hành đều giữ được nó: **Rebase and merge** của GitHub tạo lại từng commit nhưng không có khóa của người viết nên không ký được, còn **Squash and merge** và **Merge** tạo commit mới do GitHub ký.

## ✅ QUYẾT ĐỊNH

- Mọi ruleset nhánh và tag trong `rulesets/` — cấp repository và cấp tổ chức — có quy tắc `required_signatures`; `validate.py` báo lỗi khi thiếu. Push ruleset không nhận quy tắc này ([ADR 0007](0007-org-push-ruleset.md)).
- Ruleset và cài đặt repository chỉ cho phép **Merge** và **Squash** (`allowed_merge_methods`, `allow_rebase_merge: false`).
- Người đóng góp ký commit bằng GPG hoặc SSH; rebase branch của mình lên nhánh chính tại máy vẫn được vì commit được ký lại bằng khóa của người viết.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Cho phép cả Merge, Squash và Rebase**: Rebase and merge tạo lại commit trên nhánh chính mà không có chữ ký của người viết, không đáp ứng yêu cầu xác minh commit.
- **Chỉ Squash and merge**: luôn có chữ ký nhưng mất các commit riêng của Pull Request lớn; giữ thêm Merge.
- **Không bắt buộc chữ ký**: không xác minh được ai tạo thay đổi trên nhánh chính và tag phát hành.

## ⚖️ HỆ QUẢ

- Commit vào nhánh chính qua Pull Request và commit mà tag phát hành trỏ tới đều có chữ ký đã xác minh; người trong danh sách bỏ qua của ruleset không bị chặn nên vẫn phải tự ký commit.
- Muốn giữ từng commit của Pull Request thì dùng Merge (có merge commit), không có lịch sử tuyến tính giữ nguyên commit.
- Script tạo commit thay người dùng (ví dụ `release.py open-pr`) dùng GraphQL `createCommitOnBranch` để GitHub ký.
