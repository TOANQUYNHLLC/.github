# 0005. RULESET PROTECT RELEASE TAGS CHO TAG PHÁT HÀNH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

GitHub Release, nội dung phát hành và liên kết so sánh phiên bản đều dựa vào tag phát hành: `Stable.v*`, `Beta.v*` ([ADR 0012](0012-monthly-releases.md)) và các tag `v*` đã phát hành. Protect Main chỉ bảo vệ nhánh: người có quyền ghi vẫn tạo, dời hoặc xóa được tag, khiến Release đã công bố trỏ tới mã khác lúc phát hành.

## ✅ QUYẾT ĐỊNH

- Mỗi repository có ruleset **Protect Release Tags** trong `rulesets/protect-release-tags.json`: áp dụng cho `refs/tags/Stable.v*`, `refs/tags/Beta.v*` và `refs/tags/v*`, chặn tạo, cập nhật (dời), xóa tag và force push; tag chỉ trỏ tới commit có chữ ký.
- Danh sách bỏ qua giống Protect Main: chỉ người quản trị tạo được tag phát hành.
- Tổ chức bật **Immutable releases**: Release đã phát hành không dời được tag, không sửa được tệp đính kèm, không dùng lại được tên tag.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Ruleset tag cấp tổ chức**: không được thực thi với gói Free; giữ bản cấp tổ chức sẵn sàng cho gói Team.
- **Push ruleset**: chỉ áp dụng cho repository riêng tư hoặc internal, không bảo vệ được repository công khai như `.github`.
- **Ruleset tag cấp repository** (chọn): dùng được với repository công khai trên gói Free.

## ⚖️ HỆ QUẢ

- Người đóng góp không phải người quản trị không tạo được tag phát hành; phát hành do người quản trị thực hiện ([ADR 0012](0012-monthly-releases.md)).
- Release đính kèm tệp phải tạo bản nháp, tải tệp lên rồi mới phát hành.
