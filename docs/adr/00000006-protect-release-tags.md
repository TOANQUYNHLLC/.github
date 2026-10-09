# 00000006. RULESET PROTECT RELEASE TAGS CHO TAG PHÁT HÀNH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Tag xác định mã nguồn của phiên bản phát hành. Bảo vệ nhánh chính không ngăn người có quyền ghi tạo, dời hoặc xóa tag; tag và Release cần chính sách bảo vệ riêng.

## ✅ QUYẾT ĐỊNH

`rulesets/protect-release-tags.json` là nguồn cho **Protect Release Tags**, áp dụng cho `refs/tags/Stable.v*`, `refs/tags/Beta.v*` và `refs/tags/v*`.

Ruleset chặn tạo, cập nhật, xóa tag và force push; tag phải trỏ tới commit có chữ ký. Danh sách bỏ qua giống Protect Main, để người quản trị thực hiện phát hành.

Tổ chức dùng **Immutable releases**: tag và tệp đính kèm của Release đã phát hành không được thay đổi; tên tag không được dùng lại. Định dạng phiên bản theo [ADR 00000012](00000012-monthly-releases.md).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Ruleset cấp repository bảo vệ repository công khai trên gói Free. Ruleset cấp tổ chức cần gói hỗ trợ; push ruleset không bảo vệ tag của repository công khai.

## ⚖️ HỆ QUẢ

Người quản trị tạo tag phát hành. Release có tệp đính kèm được tạo dưới dạng bản nháp, tải đủ tệp rồi phát hành. Bản cấp tổ chức được sinh từ nguồn cấp repository để quản lý khi có gói hỗ trợ.
