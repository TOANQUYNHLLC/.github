# 00000005. PUSH RULESET PROTECT PUSHES CẤP TỔ CHỨC

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Quy tắc chung cấm đưa mật khẩu, khóa, dữ liệu cá nhân và hồ sơ bệnh án vào repository. `.gitignore` và secret scanning (push protection) không ngăn được tệp khóa riêng, kho khóa, tệp cơ sở dữ liệu hay tệp lớn bị thêm bằng `git add -f`. Push ruleset chặn được các tệp này, nhưng GitHub chỉ áp dụng cho repository riêng tư hoặc internal, ở cấp tổ chức chỉ thực thi với gói Team, và chỉ nhận bốn quy tắc push.

## ✅ QUYẾT ĐỊNH

- Ruleset cấp tổ chức **Organization Protect Pushes** trong `rulesets/org-protect-pushes.json`: target `push`, nhắm `~ALL` repository, danh sách bỏ qua là chủ tổ chức (`OrganizationAdmin`, **always**).
- Quy tắc:
    - Chặn đường dẫn `**/.env` và khóa SSH riêng (`id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`); không chặn `.env.*` vì `.env.example` được phép commit.
    - Chặn đuôi khóa, chứng chỉ, kho mật khẩu (`*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`, `*.ppk`, `*.kdbx`) và tệp cơ sở dữ liệu (`*.sqlite`, `*.sqlite3`, `*.db`).
    - Tệp tối đa **10 MB** (Git LFS không tính); đường dẫn tối đa **200** ký tự để clone được trên Windows.
- Không có bản cấp repository: tệp JSON là nguồn; `orgPushRuleset()` trong `scripts/orgsetup/rulesets.py` chuẩn hóa danh sách bỏ qua và phạm vi.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Chỉ dựa vào `.gitignore` và secret scanning (push protection)**: không ngăn được tệp khóa riêng, kho khóa, tệp cơ sở dữ liệu hay tệp lớn bị thêm bằng `git add -f` hoặc ở repository chưa có `.gitignore` chung.
- **Push ruleset cấp repository**: [GitHub hỗ trợ trên gói Team cho repository riêng tư hoặc internal](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets#push-rulesets). Cấu hình hiện tại chỉ có bản cấp tổ chức nhắm `~ALL`; tệp JSON cấp tổ chức là nguồn duy nhất, không có các bản cấp repository.
- **Thêm `required_signatures` vào push ruleset** như các ruleset khác: push ruleset chỉ nhận bốn quy tắc push, GitHub không chấp nhận.

## ⚖️ HỆ QUẢ

- Khi tổ chức nâng lên gói Team, mọi repository riêng tư, internal bị chặn các tệp trên ngay khi đẩy, kể cả trên branch chưa hợp nhất; repository công khai như `.github` không bị ảnh hưởng.
- Repository cần tệp bị chặn (ví dụ chứng chỉ công khai, cơ sở dữ liệu mẫu) nhờ chủ tổ chức đẩy hoặc đề xuất đổi danh sách bằng Pull Request.
