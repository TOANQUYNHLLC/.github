# 0008. RULESET PROTECT RELEASE TAGS CHO TAG PHÁT HÀNH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-09-27
- **Điều chỉnh:** [0005](0005-merge-protect-main.md) — mỗi repository có thêm một ruleset cho tag, bên cạnh Protect Main

## 📌 BỐI CẢNH

Workflow `release.yml` tạo GitHub Release khi gắn tag `v*`; Release, nhật ký thay đổi và liên kết so sánh phiên bản đều dựa vào tag đó. Ruleset Protect Main chỉ bảo vệ nhánh chính: bất kỳ ai có quyền ghi vẫn có thể tạo tag `v*`, dời tag sang commit khác hoặc xóa tag — Release đã công bố có thể trỏ tới mã khác với lúc phát hành.

Các lựa chọn đã cân nhắc (tổ chức dùng gói GitHub Free, repository công khai):

- Ruleset cấp tổ chức: không được thực thi khi chưa nâng gói.
- Push ruleset (chặn tệp theo đường dẫn, đuôi, kích thước): chỉ dùng được cho repository riêng tư hoặc internal.
- Ruleset tag cấp repository: dùng được với repository công khai trên gói Free.

## ✅ QUYẾT ĐỊNH

- Mỗi repository có thêm ruleset **Protect Release Tags**, định nghĩa trong `rulesets/protect-release-tags.json`: áp dụng cho `refs/tags/v*`, chặn tạo, cập nhật (dời), xóa tag và force push.
- Danh sách bỏ qua giống Protect Main: hai tài khoản quản trị, chế độ **always** — chỉ người quản trị tạo được tag phát hành.
- `scripts/org-setup.py rulesets` áp dụng cả hai ruleset; `scripts/validate.py` kiểm tra tệp ruleset tag.

## ⚖️ HỆ QUẢ

- Mỗi repository có hai ruleset: **Protect Main** (nhánh chính) và **Protect Release Tags** (tag `v*`), thay cho "một ruleset duy nhất" của ADR 0005.
- Người đóng góp không phải quản trị viên không tạo được tag `v*`; quy trình phát hành trong `README.md` do người quản trị thực hiện.
- Khi tổ chức nâng lên gói có ruleset cấp tổ chức, có thể chuyển hai ruleset lên cấp tổ chức bằng một ADR mới.
