# 00000004. RULESET PROTECT MAIN BẢO VỆ NHÁNH CHÍNH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Quy ước chỉ có ý nghĩa khi nhánh chính chỉ nhận thay đổi đã được đánh giá và kiểm tra. Tổ chức có hai người quản trị và dùng gói GitHub Free: ruleset cấp tổ chức chưa được thực thi, ruleset cấp repository thì có (với repository công khai).

## ✅ QUYẾT ĐỊNH

- Mỗi repository có ruleset **Protect Main** cho nhánh mặc định, định nghĩa trong `rulesets/protect-main.json`:
    - Mọi thay đổi qua Pull Request, ít nhất **1** phê duyệt của `CODEOWNERS`; phê duyệt cũ bị hủy khi có commit mới, cần phê duyệt lại sau lần đẩy cuối; mọi góp ý phải được giải quyết.
    - Cho phép **Merge** và **Squash** (ưu tiên Squash); không có Rebase ([ADR 00000007](00000007-signed-commits-merge-methods.md)).
    - Kiểm tra tự động bắt buộc thành công trên branch đã cập nhật với nhánh chính; code quality; commit có chữ ký; cấm force push, cấm xóa.
- Danh sách bỏ qua: hai tài khoản quản trị, chế độ **always** — tổ chức chỉ có hai người quản trị nên một người không thể tự phê duyệt Pull Request của mình. Quyền này chỉ dùng khi thật cần (`GOVERNANCE.md`).
- Repository khác chỉ bắt buộc kiểm tra có job tương ứng (tiêu đề Pull Request, tên branch); `scripts/org-setup.py rulesets` áp dụng và so với ruleset trên GitHub.
- Bản cấp tổ chức (`rulesets/org-*.json`) sinh từ bản cấp repository bằng `orgRulesets()` trong `scripts/orgsetup/rulesets.py`, dùng chủ tổ chức (`OrganizationAdmin`) làm danh sách bỏ qua, thêm code scanning và phương thức hợp nhất của cấp tổ chức ([ADR 00000007](00000007-signed-commits-merge-methods.md)); chỉ được thực thi khi tổ chức nâng lên gói Team.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Chỉ ruleset cấp tổ chức**: gói GitHub Free không thực thi ruleset cấp tổ chức; giữ bản cấp tổ chức sẵn sàng cho khi nâng lên gói Team.
- **Chỉ Squash and merge**: gộp mọi commit của Pull Request lớn thành một, mất các bước trung gian có ý nghĩa; cho phép thêm Merge.
- **Bỏ qua chỉ cho vai trò Admin khi hợp nhất Pull Request**: hẹp hơn danh sách bỏ qua **always** hiện tại; chọn danh sách hai tài khoản quản trị để người quản trị xử lý được việc khẩn cấp, kèm quy định chỉ dùng khi thật cần (`GOVERNANCE.md`).

## ⚖️ HỆ QUẢ

- Tên kiểm tra bắt buộc phải trùng tên job — `validate.py` kiểm tra với job của repository này.
- Ở gói Free, ghi ruleset cấp tổ chức qua API bị chặn: `org-setup.py org-rulesets` chỉ so tệp với ruleset trên web; tạo, sửa bằng **Import a ruleset** trên web.
- Khi tổ chức nâng lên gói Team, có thể bỏ ruleset cấp repository trùng lặp; cập nhật ADR này khi đổi quyết định.
