# 🛡️ RULESET BẢO VỆ NHÁNH CHÍNH VÀ TAG PHÁT HÀNH

Mỗi repository của tổ chức có hai [ruleset](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets): **Protect Main** cho nhánh chính ([`protect-main.json`](protect-main.json)) và **Protect Release Tags** cho tag phát hành `v*` ([`protect-release-tags.json`](protect-release-tags.json), [ADR 0008](../docs/adr/0008-protect-release-tags.md)), để các quy tắc trong [`CONTRIBUTING.md`](../CONTRIBUTING.md) được GitHub thực thi. Ruleset **không** tự áp dụng từ repository này — người quản trị import trên web hoặc chạy `python3 scripts/org-setup.py rulesets --apply`.

Ruleset đặt ở **cấp repository**: tổ chức dùng gói GitHub Free nên ruleset cấp tổ chức (**Organization settings → Repository → Rulesets**) không được thực thi; **push ruleset** (chặn tệp theo đường dẫn, đuôi, kích thước) chỉ dùng được cho repository riêng tư hoặc internal. Gói Free cũng không thực thi ruleset trên repository **riêng tư** — `org-setup.py` cảnh báo và bỏ qua thay vì dừng.

## ⚙️ QUY TẮC CỦA PROTECT MAIN

- Mọi thay đổi phải qua Pull Request, có ít nhất **1** phê duyệt của người trong `CODEOWNERS`; phê duyệt cũ bị hủy khi có commit mới; cần phê duyệt lại sau lần đẩy cuối; chỉ người quản trị được hủy phê duyệt.
- Mọi góp ý phải được giải quyết; cho phép **Merge** và **Squash** ([ADR 0006](../docs/adr/0006-allow-all-merge-methods.md)); không cho phép **Rebase** vì commit tạo lại mất chữ ký ([ADR 0011](../docs/adr/0011-disallow-rebase-merge.md)).
- Kiểm tra tự động bắt buộc thành công trên branch đã cập nhật với nhánh chính; code quality.
- Commit phải có chữ ký (GPG hoặc SSH).
- Cấm force push, cấm xóa; chặn tạo và cập nhật nhánh chính ngoài danh sách bỏ qua.
- Danh sách bỏ qua: hai tài khoản quản trị, chế độ **always** ([ADR 0005](../docs/adr/0005-merge-protect-main.md)).

Mọi ruleset nhánh và tag — cấp repository và cấp tổ chức — có quy tắc **Require signed commits** (`required_signatures`, [ADR 0009](../docs/adr/0009-rulesets-require-signed-commits.md)); `scripts/validate.py` báo lỗi khi thiếu. Push ruleset không nhận quy tắc này ([ADR 0010](../docs/adr/0010-org-push-ruleset.md)).

## 🏷️ PROTECT RELEASE TAGS

- Áp dụng cho `refs/tags/v*`: chặn tạo, cập nhật (dời sang commit khác), xóa tag và force push; tag chỉ trỏ tới commit có chữ ký.
- Danh sách bỏ qua giống Protect Main — chỉ hai tài khoản quản trị tạo được tag phát hành, nên GitHub Release luôn trỏ đúng mã đã phát hành.
- Bổ sung cho ruleset: tổ chức bắt buộc **Immutable releases** cho mọi repository — khi Release đã phát hành, không ai (kể cả người trong danh sách bỏ qua) dời được tag, sửa được tệp đính kèm, hay xóa được tag khi Release còn đó; xóa Release rồi cũng không dùng lại được tên tag.

## 🏢 RULESET CẤP TỔ CHỨC

Ba ruleset cho mọi repository (`~ALL`); hai ruleset đầu đã import trên web (**Active**) nhưng chỉ được thực thi khi tổ chức nâng lên gói **GitHub Team** (gói Free không thực thi ruleset cấp tổ chức):

- [`org-protect-main.json`](org-protect-main.json) — **Protect Main (Organization)**: cùng quy tắc với Protect Main trên nhánh mặc định.
- [`org-protect-release-tags.json`](org-protect-release-tags.json) — **Protect Release Tags (Organization)**: cùng quy tắc với Protect Release Tags trên tag `v*`.
- [`org-protect-pushes.json`](org-protect-pushes.json) — **Protect Pushes (Organization)**: push ruleset, xem [mục dưới](#-protect-pushes-cấp-tổ-chức).

Khác với bản cấp repository:

- Chỉ giữ 2 kiểm tra bắt buộc có ở mọi repository (tiêu đề Pull Request, tên branch) — như Protect Main của repository khác; vẫn có `code_quality`.
- Không dùng actor loại `User` (import báo "contains an invalid actor"): danh sách bỏ qua là **chủ tổ chức** (`OrganizationAdmin`) — cùng hai người quản trị như bản cấp repository; không giới hạn người hủy phê duyệt.
- Protect Release Tags (Organization) có thêm quy tắc kiểm tra bắt buộc với danh sách rỗng như trên web — quy tắc này không chặn gì, có thể xóa trên web rồi bỏ trong `orgTagRuleset()`.
- Hai tệp sinh từ `protect-main.json`, `protect-release-tags.json` bằng `orgRulesets()` trong `scripts/org-setup.py` và khớp ruleset đang cài trên web; test bảo đảm tệp khớp `orgRulesets()` — sửa bản cấp repository rồi sinh lại tệp cấp tổ chức.
- Áp dụng: **Organization settings → Repository → Rulesets → New ruleset → Import a ruleset** → chọn `org-protect-main.json` → **Create**, lặp lại với `org-protect-release-tags.json` và `org-protect-pushes.json`. Ở gói Free, ghi ruleset cấp tổ chức qua REST (HTTP 403, dù token có quyền `admin:org`) lẫn GraphQL (`updateRepositoryRuleset`, `createRepositoryRuleset`) đều bị chặn, nên `python3 scripts/org-setup.py org-rulesets` chỉ so tệp với ruleset trên web (đọc qua GraphQL); `--apply` chỉ tạo, cập nhật được khi tổ chức dùng gói Team.

## 📤 PROTECT PUSHES (CẤP TỔ CHỨC)

Push ruleset ([ADR 0010](../docs/adr/0010-org-push-ruleset.md)) chặn ngay khi đẩy — trên mọi branch, kể cả branch chưa hợp nhất — những tệp không được có trong repository:

- Đường dẫn: `**/.env` và khóa SSH riêng (`id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`). `.env.*` không bị chặn vì `.env.example` được phép commit.
- Đuôi: khóa, chứng chỉ, kho mật khẩu (`*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`, `*.ppk`, `*.kdbx`) và tệp cơ sở dữ liệu (`*.sqlite`, `*.sqlite3`, `*.db`).
- Tệp tối đa **10 MB** (Git LFS không tính); đường dẫn tối đa **200** ký tự.

Khác hai ruleset cấp tổ chức kia:

- GitHub chỉ áp dụng push ruleset cho repository **riêng tư** hoặc **internal** (cả fork network) — repository công khai như `.github` không bị ảnh hưởng; vẫn chỉ thực thi với gói Team.
- Không có `required_signatures` (push ruleset chỉ nhận bốn quy tắc push) và không có bản cấp repository: tệp là nguồn, `orgPushRuleset()` chỉ chuẩn hóa danh sách bỏ qua và phạm vi.
- Import và so với web như hai tệp kia (`python3 scripts/org-setup.py org-rulesets`).

## ✅ KIỂM TRA BẮT BUỘC

| Kiểm tra                                                    | Repository `.github` | Repository khác |
| ----------------------------------------------------------- | -------------------- | --------------- |
| `Liên kết, biểu mẫu, nhãn, cấu hình định dạng và mẫu email` | ✔                    |                 |
| `Định dạng (Prettier, ruff)`                                | ✔                    |                 |
| `Shell script và workflow`                                  | ✔                    |                 |
| `Kiểm tra tiêu đề Pull Request`                             | ✔                    | ✔               |
| `Kiểm tra tên branch`                                       | ✔                    | ✔               |

Tên kiểm tra phải trùng **tên job**, nếu không Pull Request sẽ chờ mãi một kiểm tra không tồn tại. `scripts/org-setup.py` tự bỏ kiểm tra mà repository không có job tương ứng; `scripts/validate.py` báo lỗi khi tên không trùng job của repository này.

## 📥 CÁCH ÁP DỤNG

- **Bằng script** (khuyên dùng cho repository khác): `python3 scripts/org-setup.py rulesets --apply --repo <tên>` — tạo mới hoặc cập nhật hai ruleset **Protect Main**, **Protect Release Tags** (so với ruleset trên GitHub trước: giống tệp thì báo đã đúng, không ghi) và cảnh báo nếu repository còn ruleset khác.
- **Trên web** (repository `.github`): **Settings → Rules → Rulesets → New ruleset → Import a ruleset** → chọn `protect-main.json` → **Create**; lặp lại với `protect-release-tags.json`. Import `protect-main.json` trên web giữ nguyên cả 5 kiểm tra — chỉ dùng cho repository `.github`.
