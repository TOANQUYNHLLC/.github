# 🛡️ RULESET BẢO VỆ NHÁNH CHÍNH

Mỗi repository của tổ chức có **một** [ruleset](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) duy nhất tên **Protect Main**, định nghĩa trong [`protect-main.json`](protect-main.json), để các quy tắc trong [`CONTRIBUTING.md`](../CONTRIBUTING.md) được GitHub thực thi. Ruleset **không** tự áp dụng từ repository này — người quản trị import trên web hoặc chạy `python3 scripts/org-setup.py rulesets --apply`.

## ⚙️ QUY TẮC

- Mọi thay đổi phải qua Pull Request, có ít nhất **1** phê duyệt của người trong `CODEOWNERS`; phê duyệt cũ bị hủy khi có commit mới; cần phê duyệt lại sau lần đẩy cuối; chỉ người quản trị được hủy phê duyệt.
- Mọi góp ý phải được giải quyết; cho phép **Merge**, **Squash** và **Rebase** ([ADR 0006](../docs/adr/0006-allow-all-merge-methods.md)).
- Kiểm tra tự động bắt buộc thành công trên branch đã cập nhật với nhánh chính; code quality.
- Commit phải có chữ ký (GPG hoặc SSH).
- Cấm force push, cấm xóa; chặn tạo và cập nhật nhánh chính ngoài danh sách bỏ qua.
- Danh sách bỏ qua: hai tài khoản quản trị, chế độ **always** ([ADR 0005](../docs/adr/0005-merge-protect-main.md)).

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

- **Bằng script** (khuyên dùng cho repository khác): `python3 scripts/org-setup.py rulesets --apply --repo <tên>` — tạo mới hoặc cập nhật ruleset **Protect Main** và cảnh báo nếu repository còn ruleset khác.
- **Trên web** (repository `.github`): **Settings → Rules → Rulesets → New ruleset → Import a ruleset** → chọn `protect-main.json` → **Create**. Import trên web giữ nguyên cả 5 kiểm tra — chỉ dùng cho repository `.github`.
