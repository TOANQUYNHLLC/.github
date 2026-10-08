# 00000007. COMMIT CÓ CHỮ KÝ TRÊN NHÁNH CHÍNH VÀ TAG; PHƯƠNG THỨC HỢP NHẤT

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Commit có chữ ký đã xác minh cho biết ai thực sự tạo ra thay đổi. Chữ ký chỉ có giá trị khi mọi đường vào nhánh chính và tag phát hành đều giữ được nó: **Rebase and merge** của GitHub tạo lại từng commit nhưng không có khóa của người viết nên không ký được, còn **Squash and merge** và **Merge** tạo commit mới do GitHub ký. Ruleset **Organization Protect Main** do người quản trị cấu hình trên web cho mọi repository của tổ chức.

## ✅ QUYẾT ĐỊNH

- Mọi ruleset nhánh và tag trong `rulesets/` — cấp repository và cấp tổ chức — có quy tắc `required_signatures`; `validate.py` báo lỗi khi thiếu. Push ruleset không nhận quy tắc này ([ADR 00000005](00000005-org-push-ruleset.md)).
- Ruleset và cài đặt cấp repository chỉ cho phép **Merge** và **Squash** (`allowed_merge_methods`, `allow_rebase_merge: false`).
- Ruleset Organization Protect Main cho phép **Merge**, **Squash** và **Rebase**, áp dụng cho nhánh mặc định và `refs/heads/main` của mọi repository: `orgRuleset()` trong `scripts/orgsetup/rulesets.py` sinh bản này từ bản cấp repository rồi thêm `rebase` và `refs/heads/main`.
- Người đóng góp ký commit bằng GPG hoặc SSH; rebase branch của mình lên nhánh chính tại máy vẫn được vì commit được ký lại bằng khóa của người viết.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Cho phép Rebase ở cấp repository**: Rebase and merge tạo lại commit trên nhánh chính mà không có chữ ký của người viết, không đáp ứng yêu cầu xác minh commit.
- **Chỉ Squash and merge**: luôn có chữ ký nhưng mất các commit riêng của Pull Request lớn; giữ thêm Merge.
- **Không bắt buộc chữ ký**: không xác minh được ai tạo thay đổi trên nhánh chính và tag phát hành.

## ⚖️ HỆ QUẢ

- Commit vào nhánh chính qua Pull Request và commit mà tag phát hành trỏ tới đều có chữ ký đã xác minh; người trong danh sách bỏ qua của ruleset không bị chặn nên vẫn phải tự ký commit.
- Muốn giữ từng commit của Pull Request thì dùng Merge (có merge commit), không có lịch sử tuyến tính giữ nguyên commit.
- Ruleset cấp tổ chức vẫn có `required_signatures`; repository có Protect Main cấp repository hoặc `allow_rebase_merge: false` không hợp nhất bằng Rebase được. Ruleset cấp tổ chức chỉ được thực thi khi tổ chức dùng gói Team; repository có nhánh mặc định khác `main` được bảo vệ cả hai nhánh.
- Script tạo commit thay người dùng (ví dụ `release.py open-pr`) dùng GraphQL `createCommitOnBranch` để GitHub ký.
