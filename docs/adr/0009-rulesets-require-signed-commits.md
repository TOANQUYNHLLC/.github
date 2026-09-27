# 0009. MỌI RULESET BẮT BUỘC COMMIT CÓ CHỮ KÝ

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-09-27
- **Điều chỉnh:** [0008](0008-protect-release-tags.md) — ruleset Protect Release Tags thêm quy tắc `required_signatures`

## 📌 BỐI CẢNH

Protect Main đã bắt buộc commit có chữ ký trên nhánh chính, nhưng Protect Release Tags (ADR 0008) chỉ chặn tạo, dời, xóa tag: tag phát hành `v*` vẫn có thể trỏ tới commit không có chữ ký. Bản cấp tổ chức của hai ruleset thừa hưởng đúng khoảng trống đó.

## ✅ QUYẾT ĐỊNH

- Mọi ruleset trong `rulesets/` — nhánh và tag, cấp repository và cấp tổ chức — có quy tắc `required_signatures` (**Require signed commits**): commit được đẩy tới ref khớp điều kiện phải có chữ ký đã xác minh.
- Protect Release Tags và bản cấp tổ chức của nó thêm quy tắc này; `scripts/validate.py` báo lỗi khi một ruleset thiếu quy tắc.

## ⚖️ HỆ QUẢ

- Tag phát hành chỉ trỏ được tới commit có chữ ký (người trong danh sách bỏ qua vẫn không bị chặn).
- Ruleset mới thêm vào `rulesets/` phải có `required_signatures`, nếu không kiểm tra tự động thất bại.
