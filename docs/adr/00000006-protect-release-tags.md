# 00000006. RULESET PROTECT RELEASE TAGS CHO TAG PHÁT HÀNH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Tag là mốc xác định mã nguồn của một phiên bản. Quy trình phát hành cần kiểm soát việc tạo tag và giữ nguyên mốc đã công bố.

## ✅ QUYẾT ĐỊNH

`rulesets/protect-release-tags.json` bảo vệ `refs/tags/Stable.v*`, `refs/tags/Beta.v*` và `refs/tags/v*`. Mẫu hạn chế tạo, cập nhật, xóa tag và force push; commit được tag trỏ tới cần có chữ ký.

Người quản trị phát hành bằng quyền bỏ qua theo danh sách của Protect Main. Status checks có danh sách rỗng. `do_not_enforce_on_create` là `true` ở cấp repository và `false` ở bản tổ chức do `orgTagRuleset()` sinh; danh sách rỗng không bổ sung check khi tạo tag.

Quy trình dùng Immutable releases để bảo vệ tag và tệp đính kèm sau công bố. Bản có tài nguyên đính kèm được tạo nháp, tải đủ tệp rồi phát hành. Phiên bản theo [ADR 00000012](00000012-monthly-releases.md).

Nguồn của quyết định: [rulesets/protect-release-tags.json](../../rulesets/protect-release-tags.json), [rulesets/organization-protect-release-tags.json](../../rulesets/organization-protect-release-tags.json), [scripts/release.py](../../scripts/release.py).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Bảo vệ tag kiểm soát mốc phát hành, còn bảo vệ nhánh kiểm soát nội dung được hợp nhất. Hai chính sách có phạm vi riêng và cần cùng được thiết lập cho quy trình phát hành có kiểm soát.

## ⚖️ HỆ QUẢ

Người quản trị xác minh commit, nội dung phiên bản và tag trước khi công bố. Tag của bản bất biến được giữ nguyên và không dùng lại tên. Điều kiện áp dụng từng cấp ruleset nằm trong [hướng dẫn ruleset](../../rulesets/README.md).
