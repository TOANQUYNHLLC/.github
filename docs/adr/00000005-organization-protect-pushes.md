# 00000005. PUSH RULESET PROTECT PUSHES CẤP REPOSITORY VÀ TỔ CHỨC

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Quy trình kiểm tra cần hạn chế tệp chứa khóa, cơ sở dữ liệu, kho mật khẩu hoặc tài nguyên quá lớn ngay tại thời điểm đẩy khi GitHub hỗ trợ push ruleset.

## ✅ QUYẾT ĐỊNH

`rulesets/protect-pushes.json` khai báo target `push`, không có điều kiện nhánh hoặc repository ở cấp repository. Mẫu có các hạn chế:

- Chặn `**/.env` và khóa SSH riêng `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`.
- Chặn đuôi `.pem`, `.key`, `.p12`, `.pfx`, `.jks`, `.keystore`, `.ppk`, `.kdbx`, `.sqlite`, `.sqlite3`, `.db`.
- Tệp tối đa 10 MB, không tính Git LFS; đường dẫn tối đa 200 ký tự.

Mẫu không chặn toàn bộ `.env.*` để cho phép tệp giá trị mẫu. Danh sách bỏ qua dùng người quản trị với chế độ `always`. `orgPushRuleset()` sinh bản tổ chức với phạm vi `~ALL` và actor `OrganizationAdmin`; `make org-ruleset-files` ghi tệp đó tại máy.

Push ruleset dùng các quy tắc hạn chế tệp; chữ ký thuộc ruleset nhánh và tag.

Nguồn của quyết định: [rulesets/protect-pushes.json](../../rulesets/protect-pushes.json), [rulesets/organization-protect-pushes.json](../../rulesets/organization-protect-pushes.json), [scripts/orgsetup/rulesets.py](../../scripts/orgsetup/rulesets.py).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

`.gitignore` hỗ trợ lựa chọn tệp tại máy nhưng có thể bị bỏ qua bằng `git add -f`. Push ruleset bổ sung ràng buộc trên GitHub. Sinh bản tổ chức từ nguồn repository tránh duy trì hai bộ hạn chế độc lập.

## ⚖️ HỆ QUẢ

Người quản trị chọn mẫu khi loại repository và gói GitHub hỗ trợ; xem [hướng dẫn ruleset](../../rulesets/README.md). Tệp dữ liệu mẫu hoặc chứng chỉ công khai thuộc danh sách chặn cần được đánh giá trước khi dùng quyền bỏ qua hay điều chỉnh chính sách.
