# 🛡️ RULESET BẢO VỆ NHÁNH CHÍNH VÀ TAG PHÁT HÀNH

Mỗi repository của tổ chức có hai [ruleset](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets): **Protect Main** cho nhánh chính ([`protect-main.json`](protect-main.json)) và **Protect Release Tags** cho tag phát hành `v*` ([`protect-release-tags.json`](protect-release-tags.json), [ADR 0008](../docs/adr/0008-protect-release-tags.md)), để các quy tắc trong [`CONTRIBUTING.md`](../CONTRIBUTING.md) được GitHub thực thi. Ruleset **không** tự áp dụng từ repository này — người quản trị import trên web hoặc chạy `python3 scripts/org-setup.py rulesets --apply`.

Ruleset đặt ở **cấp repository**: tổ chức dùng gói GitHub Free nên ruleset cấp tổ chức (**Organization settings → Repository → Rulesets**) không được thực thi; **push ruleset** (chặn tệp theo đường dẫn, đuôi, kích thước) chỉ dùng được cho repository riêng tư hoặc internal.

## ⚙️ QUY TẮC CỦA PROTECT MAIN

- Mọi thay đổi phải qua Pull Request, có ít nhất **1** phê duyệt của người trong `CODEOWNERS`; phê duyệt cũ bị hủy khi có commit mới; cần phê duyệt lại sau lần đẩy cuối; chỉ người quản trị được hủy phê duyệt.
- Mọi góp ý phải được giải quyết; cho phép **Merge**, **Squash** và **Rebase** ([ADR 0006](../docs/adr/0006-allow-all-merge-methods.md)).
- Kiểm tra tự động bắt buộc thành công trên branch đã cập nhật với nhánh chính; code quality.
- Commit phải có chữ ký (GPG hoặc SSH).
- Cấm force push, cấm xóa; chặn tạo và cập nhật nhánh chính ngoài danh sách bỏ qua.
- Danh sách bỏ qua: hai tài khoản quản trị, chế độ **always** ([ADR 0005](../docs/adr/0005-merge-protect-main.md)).

## 🏷️ PROTECT RELEASE TAGS

- Áp dụng cho `refs/tags/v*`: chặn tạo, cập nhật (dời sang commit khác), xóa tag và force push.
- Danh sách bỏ qua giống Protect Main — chỉ hai tài khoản quản trị tạo được tag phát hành, nên GitHub Release luôn trỏ đúng mã đã phát hành.

## ✅ KIỂM TRA BẮT BUỘC

| Kiểm tra                                                    | Repository `.github` | Repository khác |
| ----------------------------------------------------------- | -------------------- | --------------- |
| `Liên kết, biểu mẫu, nhãn, cấu hình định dạng và mẫu email` | ✔                    |                 |
| `Định dạng (Prettier, ruff) và ESLint`                      | ✔                    |                 |
| `Shell script và workflow`                                  | ✔                    |                 |
| `Kiểm tra tiêu đề Pull Request`                             | ✔                    | ✔               |
| `Kiểm tra tên branch`                                       | ✔                    | ✔               |

Tên kiểm tra phải trùng **tên job**, nếu không Pull Request sẽ chờ mãi một kiểm tra không tồn tại. `scripts/org-setup.py` tự bỏ kiểm tra mà repository không có job tương ứng; `scripts/validate.py` báo lỗi khi tên không trùng job của repository này.

## 📥 CÁCH ÁP DỤNG

- **Bằng script** (khuyên dùng cho repository khác): `python3 scripts/org-setup.py rulesets --apply --repo <tên>` — tạo mới hoặc cập nhật hai ruleset **Protect Main**, **Protect Release Tags** và cảnh báo nếu repository còn ruleset khác.
- **Trên web** (repository `.github`): **Settings → Rules → Rulesets → New ruleset → Import a ruleset** → chọn `protect-main.json` → **Create**; lặp lại với `protect-release-tags.json`. Import `protect-main.json` trên web giữ nguyên cả 5 kiểm tra — chỉ dùng cho repository `.github`.
