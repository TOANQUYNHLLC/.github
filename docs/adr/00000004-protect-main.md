# 00000004. RULESET PROTECT MAIN BẢO VỆ NHÁNH CHÍNH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Nhánh chính cần bảo đảm thay đổi được đánh giá, kiểm tra và xác minh chữ ký. Gói GitHub Free cho phép thực thi ruleset cấp repository công khai; ruleset cấp tổ chức cần gói Team hoặc Enterprise.

## ✅ QUYẾT ĐỊNH

`rulesets/protect-main.json` là nguồn cho **Protect Main** trên nhánh mặc định của từng repository:

- Thay đổi qua Pull Request, có ít nhất **1** phê duyệt của `CODEOWNERS`, hủy phê duyệt cũ khi có commit mới và yêu cầu phê duyệt sau lần đẩy cuối.
- Mọi góp ý được giải quyết; các kiểm tra bắt buộc thành công trên branch cập nhật với nhánh chính; có quy tắc code quality.
- Cho phép Merge và Squash, ưu tiên Squash; commit có chữ ký; cấm force push và xóa nhánh.

Danh sách bỏ qua dùng các tài khoản trong `MAINTAINERS.md` với chế độ **always**. Người quản trị chỉ dùng quyền này khi thật cần theo `GOVERNANCE.md`.

Với repository đích, script chỉ chọn kiểm tra bắt buộc có job tương ứng. Bản cấp tổ chức được sinh bằng `orgRulesets()` trong `scripts/orgsetup/rulesets.py`, dùng `OrganizationAdmin` làm danh sách bỏ qua và có các điều kiện riêng theo [ADR 00000007](00000007-signed-commits-merge-methods.md).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Chỉ dùng ruleset cấp tổ chức không bảo vệ được repository trên gói Free. Chỉ cho phép Squash không đáp ứng Pull Request cần giữ các commit riêng. Danh sách bỏ qua giới hạn khi hợp nhất PR không đáp ứng phạm vi xử lý khẩn cấp của người quản trị.

## ⚖️ HỆ QUẢ

Tên kiểm tra bắt buộc phải trùng job; validator đối chiếu với workflow của repository này. Tạo, sửa và thực thi ruleset cấp tổ chức, kể cả import trên web, chịu [giới hạn gói GitHub](https://docs.github.com/en/organizations/managing-organization-settings/creating-rulesets-for-repositories-in-your-organization).

Khi REST bị chặn, `org-rulesets` đối chiếu qua GraphQL; `--apply` trả mã lỗi vì chưa áp dụng. Việc xác nhận sau ghi theo [ADR 00000015](00000015-github-sync-verification.md).
