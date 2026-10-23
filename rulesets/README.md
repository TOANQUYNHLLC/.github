# 🛡️ RULESET BẢO VỆ NHÁNH, TAG VÀ PUSH

[rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) thực thi chính sách bảo vệ khi loại repository, quyền và gói GitHub hỗ trợ. Tệp JSON là nguồn local; người quản trị cần đối chiếu và áp dụng, GitHub không tự cài ruleset từ repository này.

## 🗂️ NGUỒN CẤU HÌNH

| Tệp                                                                              | Phạm vi và nguồn                                                |
| -------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| [protect-main.json](protect-main.json)                                           | Protect Main cấp repository; nguồn bảo vệ nhánh mặc định        |
| [protect-release-tags.json](protect-release-tags.json)                           | Protect Release Tags cấp repository; nguồn bảo vệ tag phát hành |
| [protect-pushes.json](protect-pushes.json)                                       | Protect Pushes cấp repository; nguồn hạn chế tệp khi push       |
| [organization-protect-main.json](organization-protect-main.json)                 | Bản tổ chức sinh từ Protect Main                                |
| [organization-protect-release-tags.json](organization-protect-release-tags.json) | Bản tổ chức sinh từ Protect Release Tags                        |
| [organization-protect-pushes.json](organization-protect-pushes.json)             | Bản tổ chức sinh từ Protect Pushes                              |

`orgRulesets()` trong [rulesets.py](../scripts/orgsetup/rulesets.py) sinh các bản nhánh, tag và push cấp tổ chức. Sửa nguồn cấp repository rồi chạy `make org-ruleset-files` để ghi lại bản tổ chức; tests đối chiếu từng byte. Bản tổ chức giữ thứ tự khóa, quy tắc và bố cục dòng như bản cấp repository, nên so hai tệp cùng loại (ví dụ `git diff --no-index protect-main.json organization-protect-main.json`) chỉ thấy điểm khác của cấp tổ chức.

Ruleset đang cài trên GitHub được nhập riêng vào `collections.rulesets` của [github-settings.json](../github-settings.json), khôi phục bằng `make org-settings-apply`. Các tệp trong thư mục này là nguồn chính sách cho lệnh ruleset; thống nhất với bản khôi phục trước khi áp dụng. Ruleset chỉ đọc một phần qua GraphQL nằm trong `observed`, không dùng để ghi.

## ⚙️ PROTECT MAIN

- Áp dụng nhánh mặc định; thay đổi qua PR và ít nhất **1** phê duyệt của `CODEOWNERS`.
- Hủy phê duyệt cũ khi có commit mới, yêu cầu phê duyệt sau lần đẩy cuối; người quản trị kiểm soát việc hủy phê duyệt.
- Mọi góp ý được giải quyết; kiểm tra bắt buộc thành công trên branch cập nhật với nhánh chính; có code quality.
- Quy tắc deployment có danh sách môi trường rỗng nên không yêu cầu deployment.
- Cho phép Merge, Squash và Rebase; lựa chọn phương thức hợp nhất vẫn phải đáp ứng yêu cầu chữ ký.
- Commit có chữ ký; cấm force push, xóa và tạo/cập nhật nhánh ngoài phạm vi được phép.
- Danh sách bỏ qua dùng tài khoản trong [MAINTAINERS.md](../MAINTAINERS.md) với chế độ **always**, chỉ dùng khi thật cần theo [GOVERNANCE.md](../GOVERNANCE.md).

Quyết định theo [ADR 00000004](../docs/adr/00000004-protect-main.md) và [ADR 00000007](../docs/adr/00000007-signed-commits-merge-methods.md).

## 🏷️ PROTECT RELEASE TAGS

Áp dụng `refs/tags/Stable.v*`, `refs/tags/Beta.v*` và `refs/tags/v*`; chặn tạo, cập nhật, xóa tag và force push. Tag trỏ tới commit có chữ ký. Quy tắc status checks có danh sách rỗng nên không yêu cầu thêm check. Danh sách bỏ qua giống Protect Main, để người quản trị phát hành theo [ADR 00000006](../docs/adr/00000006-protect-release-tags.md).

Immutable releases bổ sung bảo vệ tag và tệp đính kèm sau phát hành; tên tag đã phát hành không được dùng lại. Định dạng phiên bản theo [ADR 00000012](../docs/adr/00000012-monthly-releases.md).

## 🏢 RULESET CẤP TỔ CHỨC

Các bản tổ chức có trạng thái Active và phạm vi `~ALL`. Danh sách bỏ qua dùng `OrganizationAdmin`; không dùng actor `User` và không giới hạn người hủy phê duyệt như bản repository.

Organization Protect Main áp dụng nhánh mặc định cùng `refs/heads/main`, cho phép Merge, Squash và Rebase. Hạn chế cấp repository vẫn có hiệu lực. Bản tổ chức giữ các kiểm tra PR title, branch name và code quality; yêu cầu CodeQL không có cảnh báo `errors` hoặc bảo mật `high_or_higher`. Repository cần [workflow CodeQL](../workflow-templates/codeql.yml) để có kết quả. Bản tổ chức không có quy tắc deployment rỗng của bản cấp repository.

Organization Protect Release Tags dùng cùng phạm vi tag và các hạn chế của bản cấp repository, kể cả status checks rỗng. Cờ `do_not_enforce_on_create` có giá trị `true` ở cấp repository, `false` ở cấp tổ chức; danh sách check rỗng không yêu cầu thêm check khi tạo tag.

Tạo, sửa và thực thi ruleset cấp tổ chức cần [GitHub Team hoặc Enterprise](https://docs.github.com/en/organizations/managing-organization-settings/creating-rulesets-for-repositories-in-your-organization), kể cả import trên web. Gói Free không thực thi ruleset cấp tổ chức hoặc ruleset repository riêng tư. Việc lưu mẫu JSON không đồng nghĩa ruleset đã được áp dụng.

## 📤 PROTECT PUSHES

Push ruleset chặn ngay khi đẩy trên các branch, gồm branch chưa hợp nhất, của repository riêng tư/internal và fork network khi gói hỗ trợ:

- Đường dẫn `**/.env` và khóa SSH riêng `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`.
- Đuôi `.pem`, `.key`, `.p12`, `.pfx`, `.jks`, `.keystore`, `.ppk`, `.kdbx`, `.sqlite`, `.sqlite3`, `.db`.
- Tệp tối đa **10 MB**, không tính Git LFS; đường dẫn tối đa **200** ký tự.

`.env.*` được giữ để cho phép `.env.example`. Push ruleset không áp dụng repository công khai và không có `required_signatures`. Bản cấp repository dùng danh sách bỏ qua của người quản trị như Protect Main và không khai báo điều kiện nhánh hoặc repository. `orgPushRuleset()` sinh bản tổ chức từ nguồn này, thêm phạm vi `~ALL` và đổi danh sách bỏ qua thành `OrganizationAdmin`. Chính sách theo [ADR 00000005](../docs/adr/00000005-organization-protect-pushes.md).

Import `protect-pushes.json` riêng tại **Repository settings → Rules → Rulesets → New ruleset → Import a ruleset** khi gói và loại repository hỗ trợ. Lệnh `rulesets` chỉ quản lý nhánh và tag; push ruleset được import trên web rồi xác nhận trên GitHub.

## ✅ KIỂM TRA BẮT BUỘC

| Kiểm tra                                                    | Repository `.github` | Repository khác |
| ----------------------------------------------------------- | -------------------- | --------------- |
| `Liên kết, biểu mẫu, nhãn, cấu hình định dạng và mẫu email` | ✔                    |                 |
| `Định dạng (Prettier, ruff)`                                | ✔                    |                 |
| `Shell script và workflow`                                  | ✔                    |                 |
| `Kiểm tra tiêu đề Pull Request`                             | ✔                    | ✔               |
| `Kiểm tra tên branch`                                       | ✔                    | ✔               |

Tên check phải đúng **tên job**. Với repository khác, lệnh `rulesets` chỉ giữ hai kiểm tra tên branch và tiêu đề Pull Request, đồng thời yêu cầu repository đích đã có các workflow tương ứng; thiếu workflow được báo khi xem trước và làm lượt áp dụng chưa hoàn tất. Validator đối chiếu mẫu nguồn với workflow của repository này.

Status checks do GitHub ghi nhận từ nguồn kiểm tra mà ruleset yêu cầu. `make check` tại máy không tự tạo các trạng thái đó. Khi Actions tắt hoặc job chưa có kết quả, PR có thể chờ checks bắt buộc; người quản trị cần bảo đảm nguồn kiểm tra được cấu hình và chạy phù hợp trước khi áp dụng chính sách.

Với job dùng runner chuẩn, tổ chức cần cho phép **Standard hosted runners**. Kiểm tra ô **Disable for all repositories** theo [hướng dẫn workflow chờ runner](../docs/local-checks.md#-workflow-chờ-runner) trước khi đánh giá kết quả checks bắt buộc.

## 📥 ĐỐI CHIẾU VÀ ÁP DỤNG

```sh
python3 scripts/org-setup.py rulesets --repo <tên>
python3 scripts/org-setup.py rulesets --apply --repo <tên>
python3 scripts/org-setup.py org-rulesets
```

Lệnh mặc định chỉ xem trước; nguồn khớp thì không ghi. Lệnh cấp tổ chức dùng `--apply` khi quyền và gói hỗ trợ. Import trên web tại **Settings → Rules → Rulesets → New ruleset → Import a ruleset**; cấp tổ chức ở **Organization settings → Repository → Rulesets**. Bản Protect Main đầy đủ chỉ dành cho `.github`; repository khác dùng script để chọn đúng check.

Script đọc hết các trang danh sách, xác minh tên/ID không trùng và chi tiết khớp danh sách. Chi tiết được đọc song song; cấu trúc toàn bộ ruleset cần so trong từng phạm vi được kiểm tra trước lần ghi đầu tiên. Thiếu trang, lỗi đọc hoặc dữ liệu sai chặn ghi trong phạm vi đó. Một trang REST chứa danh sách rỗng vẫn hợp lệ.

Các tên `Protect Main (Organization)`, `Protect Release Tags (Organization)`, `Protect Pushes (Organization)` được nhận diện để cập nhật cùng ID sang tên nguồn. Nếu cả tên này và tên nguồn cùng tồn tại, script chặn ghi do trùng tài nguyên.

Ghi tuần tự theo nguồn; sau ghi phải xác minh ID phản hồi và đọc lại theo ID, so tên, target, enforcement, conditions, bypass và rules. Lỗi ghi hoặc xác nhận được tổng hợp sau khi thử các ruleset còn lại; trả mã lỗi và không tự hoàn tác thay đổi thành công. Mỗi lượt dùng dữ liệu mới theo [ADR 00000016](../docs/adr/00000016-github-sync-verification.md).

## 🔎 QUY TẮC SO SÁNH VÀ KIỂM TRA DỮ LIỆU

Các danh sách tập hợp được so theo nội dung: include/exclude, phương thức merge, reviewer, người hủy phê duyệt, status checks, công cụ scanning, đường dẫn và đuôi bị chặn. Thứ tự `file_patterns` của từng reviewer được giữ vì [GitHub xét mẫu và phủ định theo thứ tự](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#required-reviewers). Nguồn và payload không được sắp xếp lại; trường ngoài danh sách chuẩn hóa giữ nguyên.

Validator và lệnh đồng bộ dùng chung hợp đồng kiểm tra [cấu trúc REST](https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset): cờ đúng boolean, số phê duyệt đúng số nguyên, phương thức merge hợp lệ và không trùng, actor đúng loại và ID, context không trống. `integration_id` có thể vắng hoặc `null`; giá trị khai báo phải là số nguyên, không nhận boolean. Cờ status checks bắt buộc và cờ tùy chọn được kiểm tra theo hợp đồng.

Reviewer bắt buộc cần `file_patterns` là danh sách chuỗi, `minimum_approvals` là số nguyên không âm, reviewer loại Team với ID nguyên dương. Phê duyệt `0` chỉ thêm team vào PR; danh sách rỗng không yêu cầu team. Kiểm tra cấu trúc không chứng minh team có quyền phù hợp.
