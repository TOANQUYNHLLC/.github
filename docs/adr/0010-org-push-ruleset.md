# 0010. PUSH RULESET PROTECT PUSHES CẤP TỔ CHỨC

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-09-30
- **Điều chỉnh:** [0009](0009-rulesets-require-signed-commits.md) — push ruleset không có quy tắc `required_signatures`

## 📌 BỐI CẢNH

Quy tắc chung cấm đưa mật khẩu, khóa, dữ liệu cá nhân và hồ sơ bệnh án vào repository. `.gitignore` bỏ qua `.env` và secret scanning (push protection) chặn chuỗi bí mật đã biết mẫu, nhưng không ngăn được tệp khóa riêng, kho khóa, tệp cơ sở dữ liệu hay tệp lớn bị thêm bằng `git add -f` hoặc ở repository chưa có `.gitignore` chung.

Push ruleset (chặn tệp theo đường dẫn, đuôi, kích thước, độ dài đường dẫn) làm được việc này, với các ràng buộc:

- GitHub chỉ áp dụng push ruleset cho repository **riêng tư** hoặc **internal** (kể cả toàn bộ fork network); không có hiệu lực với repository công khai như `.github`.
- Ở cấp tổ chức, ruleset chỉ được thực thi với gói **GitHub Team** trở lên — như hai ruleset cấp tổ chức đã có.
- Push ruleset chỉ nhận bốn quy tắc push (`file_path_restriction`, `file_extension_restriction`, `max_file_size`, `max_file_path_length`); không thêm được `required_signatures` như ADR 0009 yêu cầu.

## ✅ QUYẾT ĐỊNH

- Thêm ruleset cấp tổ chức **Protect Pushes (Organization)** trong `rulesets/org-protect-pushes.json`: target `push`, nhắm `~ALL` repository, danh sách bỏ qua là chủ tổ chức (`OrganizationAdmin`, **always**) như hai ruleset cấp tổ chức kia.
- Quy tắc:
    - Chặn đường dẫn `**/.env` và khóa SSH riêng (`id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`). Không chặn `.env.*` vì `.env.example` được phép commit.
    - Chặn đuôi khóa, chứng chỉ, kho mật khẩu (`*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`, `*.ppk`, `*.kdbx`) và tệp cơ sở dữ liệu (`*.sqlite`, `*.sqlite3`, `*.db`) — nơi dễ lọt dữ liệu cá nhân, y tế.
    - Tệp tối đa **10 MB** (Git LFS không tính); đường dẫn tối đa **200** ký tự để clone được trên Windows.
- Không có bản cấp repository: tệp JSON là nguồn; `org_push_ruleset()` trong `scripts/org-setup.py` chuẩn hóa danh sách bỏ qua và phạm vi, `org-rulesets` so và áp dụng như hai ruleset kia.
- Quy tắc `required_signatures` của ADR 0009 chỉ áp dụng cho ruleset nhánh và tag; `scripts/validate.py` bỏ qua push ruleset khi kiểm tra.

## ⚖️ HỆ QUẢ

- Khi tổ chức nâng lên gói Team, mọi repository riêng tư, internal bị chặn các tệp trên ngay khi đẩy, kể cả commit trên branch chưa hợp nhất; chủ tổ chức vẫn đẩy được khi thật sự cần.
- Repository cần tệp bị chặn (ví dụ chứng chỉ công khai `*.pem`, cơ sở dữ liệu mẫu) phải nhờ chủ tổ chức đẩy, hoặc đề xuất thay đổi danh sách bằng Pull Request.
- Ruleset mới trong `rulesets/` có target `push` không cần `required_signatures`; ruleset nhánh và tag vẫn bắt buộc.
