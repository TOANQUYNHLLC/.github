# 00000004. RULESET PROTECT MAIN BẢO VỆ NHÁNH CHÍNH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Nhánh chính chứa nguồn dùng chung cho các dự án. Thay đổi cần được đánh giá, kiểm chứng và xác minh chữ ký trước khi sử dụng.

## ✅ QUYẾT ĐỊNH

`rulesets/protect-main.json` là mẫu Protect Main cho nhánh mặc định ở cấp repository. Quy tắc gồm:

- Pull Request có ít nhất một phê duyệt, phê duyệt của `CODEOWNERS`, giải quyết góp ý và phê duyệt sau lần đẩy cuối.
- Hủy phê duyệt khi có commit mới; quyền hủy phê duyệt giới hạn theo danh sách actor trong nguồn.
- Kiểm tra bắt buộc thành công trên branch cập nhật với nhánh chính và quy tắc code quality.
- Commit có chữ ký; hạn chế tạo, cập nhật, xóa nhánh và force push.
- Cho phép Merge, Squash và Rebase theo [ADR 00000007](00000007-signed-commits-merge-methods.md).

Danh sách bỏ qua dùng người quản trị trong `MAINTAINERS.md`, chế độ `always`, theo trách nhiệm tại `GOVERNANCE.md`. Tên check phải khớp job thực tế. Khi chọn mẫu cho dự án khác, bộ sinh chỉ giữ các check có trong workflow mẫu dùng chung.

Nguồn của quyết định: [rulesets/protect-main.json](../../rulesets/protect-main.json), [rulesets/organization-protect-main.json](../../rulesets/organization-protect-main.json), [scripts/rulesets.py](../../scripts/rulesets.py), [GOVERNANCE.md](../../GOVERNANCE.md).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Ruleset gom các điều kiện bảo vệ vào một chính sách có thể kiểm tra. Mẫu cấp repository phục vụ từng dự án; bản tổ chức do `orgRulesets()` sinh cung cấp chính sách chung khi phạm vi và gói dịch vụ hỗ trợ.

## ⚖️ HỆ QUẢ

Người quản trị import mẫu và xác nhận hiệu lực trực tiếp trên GitHub. Checks bắt buộc cần kết quả từ nguồn mà ruleset yêu cầu; chạy kiểm tra tại máy không tự tạo status checks. Khi Actions tắt, PR có thể chờ các job chưa có kết quả. Điều kiện gói dịch vụ và cách áp dụng được mô tả tại [hướng dẫn ruleset](../../rulesets/README.md).
