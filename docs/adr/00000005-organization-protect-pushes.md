# 00000005. PUSH RULESET PROTECT PUSHES CẤP TỔ CHỨC

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

`.gitignore` và secret scanning không chặn được mọi tệp khóa, kho mật khẩu, cơ sở dữ liệu hoặc tệp lớn. Push ruleset bổ sung kiểm soát theo đường dẫn, đuôi và kích thước khi gói GitHub và loại repository hỗ trợ.

## ✅ QUYẾT ĐỊNH

`rulesets/organization-protect-pushes.json` là nguồn cho **Organization Protect Pushes**: target `push`, phạm vi `~ALL`, danh sách bỏ qua `OrganizationAdmin` với chế độ **always**.

- Chặn `**/.env` và khóa SSH riêng `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`.
- Chặn đuôi khóa và kho mật khẩu: `.pem`, `.key`, `.p12`, `.pfx`, `.jks`, `.keystore`, `.ppk`, `.kdbx`; chặn cơ sở dữ liệu `.sqlite`, `.sqlite3`, `.db`.
- Giới hạn tệp **10 MB**, không tính Git LFS; đường dẫn tối đa **200** ký tự.

`.env.*` không bị chặn để `.env.example` được phép commit. `orgPushRuleset()` chuẩn hóa phạm vi và danh sách bỏ qua. Push ruleset chỉ có nguồn cấp tổ chức và không có `required_signatures`.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Chỉ dùng `.gitignore` không chặn `git add -f`; secret scanning không bao quát mọi tệp cần hạn chế. [Push ruleset cấp repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets#push-rulesets) cần cấu hình riêng từng nơi. Nguồn cấp tổ chức quản lý chung phạm vi. Quy tắc chữ ký thuộc ruleset nhánh và tag, không thuộc các quy tắc push GitHub hỗ trợ.

## ⚖️ HỆ QUẢ

Push ruleset cấp tổ chức cần gói hỗ trợ và chỉ áp dụng cho repository riêng tư hoặc internal. Repository cần chứng chỉ công khai hoặc cơ sở dữ liệu mẫu thuộc danh sách chặn phải được chủ tổ chức xử lý hoặc đề xuất chỉnh chính sách qua Pull Request.
