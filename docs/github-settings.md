# ⚙️ CÀI ĐẶT GITHUB TỪ LOCAL

[github-settings.json](../github-settings.json) là nguồn cài đặt tổ chức và repository. [configuration.py](../scripts/orgsetup/configuration.py) và [resources.py](../scripts/orgsetup/resources.py) khai báo hợp đồng API, kiểm tra nguồn và lập kế hoạch áp dụng. Tệp local chỉ lưu trường được hỗ trợ, không lưu phản hồi API thô, billing email, token, secrets hoặc khóa.

## 📥 NHẬP, XEM TRƯỚC VÀ ÁP DỤNG

GitHub CLI cần đăng nhập bằng tài khoản có quyền theo từng endpoint. Quyền quản trị repository không thay thế quyền quản trị tổ chức.

```sh
make org-import
git diff -- github-settings.json
make org-settings-preview
make org-settings-apply
```

| Lệnh                        | Hành vi                                                                                                        |
| --------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `make org-import`           | Đọc cài đặt, kể cả repository archive, rồi ghi nguyên tử nguồn local theo định dạng Prettier; không sửa GitHub |
| `make org-settings-preview` | Đọc GitHub và lập danh sách khác biệt theo nguồn local                                                         |
| `make org-settings-apply`   | Xác minh mọi phạm vi trước khi ghi, áp dụng tuần tự và đọc lại để xác nhận                                     |

Lỗi đọc metadata chính giữ nguyên tệp khi nhập. Endpoint chưa đọc được ghi vào `unavailable`, không giữ giá trị cũ hoặc suy đoán trạng thái tắt. Lệnh nhập trả mã lỗi nếu còn mục chưa đọc được; nguồn có `unavailable` chặn áp dụng.

Với repository riêng tư, `security_and_analysis` thiếu hoặc `null` được đánh dấu chưa đọc được; các phần khác vẫn có thể nhập. Repository công khai thiếu trường này hoặc phản hồi sai kiểu là lỗi metadata chính. Tính năng bảo mật bị ẩn không được ghi thành trạng thái tắt.

Ghi nhiều endpoint không phải transaction: thao tác thành công không tự hoàn tác khi bước sau thất bại. Trạng thái đang xử lý bất đồng bộ, gồm liên kết cấu hình bảo mật, chưa được coi là hoàn tất. Sau khi GitHub xử lý xong, chạy lại xem trước để xác nhận.

## 🗂️ CẤU TRÚC NGUỒN

| Phần                                        | Vai trò                                                                                                                                    |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `organization_name`                         | Xác minh tổ chức trùng với tổ chức mà script quản lý                                                                                       |
| `repository_defaults`                       | Chính sách chung cho lệnh `settings` truyền thống khi repository chưa có phần riêng; không ghi đè bằng giá trị của một repository lúc nhập |
| `organization.settings`                     | Hồ sơ công khai, quyền mặc định của thành viên, tạo repository/Pages, fork riêng tư, Projects, sign-off và chính sách deploy key           |
| `repositories.<tên>.settings`               | Mô tả, trang chủ, tính năng, phương thức hợp nhất, nhánh mặc định, template repository, fork, visibility và archive                        |
| `endpoints`                                 | Cài đặt có API riêng; chỉ chấp nhận các endpoint và trường đã được script hỗ trợ                                                           |
| `repositories.<tên>.security`               | Trạng thái tính năng bảo mật có thể PATCH qua `security_and_analysis`                                                                      |
| `organization.security_configurations`      | Tên, loại và phạm vi mặc định cho repository mới của cấu hình bảo mật có sẵn                                                               |
| `organization.runner_groups`                | Quyền nhóm runner, workflow và repository được chọn; dùng tên repository, giải ID khi áp dụng                                              |
| `repositories.<tên>.security_configuration` | Tên cấu hình bảo mật cần gắn; `null` là không gắn                                                                                          |
| `web_settings`                              | Giá trị chỉ đối chiếu, không ghi qua lệnh này; gồm mục không có API ghi được hỗ trợ và cờ bảo mật REST cũ                                  |
| `unavailable`                               | Endpoint hoặc trường metadata chưa đọc được; phải nhập lại thành công trước khi áp dụng                                                    |

Tên repository không được trùng khi bỏ qua hoa/thường. `local-settings` quản lý tổ chức và các repository đã khai báo, không dùng `repository_defaults` cho repository mới chưa nhập. Sau khi tạo repository, nhập lại hoặc dùng các lệnh thiết lập riêng. Danh sách nhập chỉ gồm repository tài khoản hiện tại đọc được, không chứng minh tài khoản thấy toàn bộ repository riêng tư.

## 🔧 PHẠM VI API ĐƯỢC QUẢN LÝ

| Nhóm                | Nội dung                                                                                                                                                                                  |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Actions             | Bật/tắt ở tổ chức và repository; danh sách repository được chọn; actions và reusable workflows được phép; ghim SHA khi API trả trường này; quyền mặc định `GITHUB_TOKEN`; chính sách fork |
| OIDC                | Template subject, dùng mặc định hoặc template tổ chức, claim tùy chỉnh và chế độ immutable subject; bỏ tiền tố subject do GitHub tự sinh                                                  |
| Nhóm runner         | Tạo hoặc sửa nhóm do tổ chức quản lý, phạm vi repository, quyền chạy ở repository công khai và giới hạn workflow; không đăng ký runner hay xóa nhóm ngoài nguồn                           |
| Lưu dữ liệu Actions | Số ngày giữ checks, trạng thái commit, log và artifact theo API; tuân thủ mức tối đa GitHub cho phép                                                                                      |
| Bảo mật repository  | Dependabot alerts/security updates, secret scanning và tính năng có trường PATCH hợp lệ, push protection, báo cáo lỗ hổng riêng tư ở repository công khai                                 |
| Cấu hình bảo mật    | Đổi phạm vi mặc định của cấu hình có sẵn; gắn hoặc tháo cấu hình theo tên. ID được đọc lại lúc lập kế hoạch                                                                               |
| Code scanning       | Cấu hình default setup qua API; workflow CodeQL riêng vẫn được quản lý bằng tệp workflow, cần tránh bật hai cách thiết lập chồng nhau                                                     |
| Release             | Chính sách Release bất biến cấp tổ chức, gồm danh sách repository được chọn, và bật/tắt cấp repository trong phạm vi GitHub cho phép                                                      |
| Tương tác           | Giới hạn tương tác lâu dài, bỏ giới hạn và giới hạn tạo Pull Request                                                                                                                      |
| Topics              | Danh sách topics của từng repository đã nhập                                                                                                                                              |

## ✅ XÁC MINH VÀ THỨ TỰ ÁP DỤNG

Luồng đọc xác minh `login` của tổ chức hoặc `full_name` của repository theo endpoint, không phân biệt hoa/thường. Thiếu danh tính hoặc chuyển hướng tới tài nguyên khác dừng lệnh; nguồn không tự đổi owner hoặc tên. Quy tắc cũng áp dụng khi giải ID cho Discussions, cấu hình bảo mật và nhánh mặc định dùng bởi `files`, `rulesets`.

Metadata được xác minh trước khi đọc song song các endpoint độc lập. Với `local-settings`, tổ chức được đọc và kiểm tra trước; kế hoạch tổ chức sai thì dừng trước khi đọc repository. Các repository được đọc song song có giới hạn rồi lập kế hoạch theo thứ tự nguồn. Mọi lần đọc và xác minh hoàn tất trước thao tác ghi đầu tiên.

Khi bỏ archive, script thực hiện trước các cập nhật khác của repository; khi archive, thực hiện sau cùng. Dependabot alerts được bật trước security updates và tắt sau security updates, không phụ thuộc thứ tự endpoint trong JSON. Discussions dùng GraphQL `updateRepository`; các trường repository khác dùng REST.

Khi đổi `merge_commit_message` hoặc `squash_merge_commit_message`, request gửi kèm tiêu đề tương ứng lấy từ nguồn hoặc trạng thái đã xác minh. Thiếu tiêu đề hợp lệ chặn ghi; phần xem trước chỉ liệt kê giá trị thực sự đổi.

`local-settings` đọc lại trạng thái sau áp dụng bằng dữ liệu mới. Các trường chính do `settings`, `org-settings` ghi cũng được đọc lại, kiểm tra kiểu và đối chiếu trước khi báo thành công; gồm Discussions và archive. Chuỗi rỗng và `null` của trường văn bản rỗng được coi là tương đương. `settings` dùng metadata đã xác nhận cho các bước topics và bảo mật phụ thuộc.

`settings` dùng `repository_defaults` và phần riêng từng repository nhưng giữ hành vi thiết lập: chỉ bật bảo mật, giữ trạng thái Actions và lấy topics `.github` từ `CITATION.cff`. Dùng `local-settings` để áp dụng đúng trạng thái nhập, gồm giá trị tắt và topics từ JSON.

Validator kiểm tra hợp đồng và phụ thuộc: Actions repository cần được tổ chức cho phép; security updates cần alerts; push protection cần secret scanning; Release bất biến phải tuân thủ chính sách tổ chức.

## 🎯 CHÍNH SÁCH SELECTED

Danh sách con chỉ được nhập khi chính sách cha là `selected`. Nguồn đổi sang chế độ này phải khai báo endpoint đi kèm. Danh sách rỗng có nghĩa không chọn phần tử nào.

| Chính sách cha                                                    | Endpoint đi kèm trong `endpoints`          | Dữ liệu local                                                  |
| ----------------------------------------------------------------- | ------------------------------------------ | -------------------------------------------------------------- |
| `actions/permissions.enabled_repositories` của tổ chức            | `actions/permissions/repositories`         | `selected_repositories`: tên đầy đủ như `TOANQUYNHLLC/.github` |
| `actions/permissions.allowed_actions` của tổ chức hoặc repository | `actions/permissions/selected-actions`     | `github_owned_allowed`, `verified_allowed`, `patterns_allowed` |
| `settings/immutable-releases.enforced_repositories` của tổ chức   | `settings/immutable-releases/repositories` | `selected_repositories`: tên đầy đủ thuộc tổ chức              |

Script đọc đủ các trang, giải tên thành ID đã xác minh, ghi chính sách cha trước danh sách con rồi đọc lại cả hai. ID chỉ dùng trong request, không lưu vào nguồn. Tên và ID phải hợp lệ, không trùng; nhiều tên trỏ cùng ID bị coi là mơ hồ và chặn ghi.

Phản hồi REST phân trang cần ít nhất một trang; một trang chứa danh sách rỗng là hợp lệ. Thiếu trang hoặc sai kiểu không được coi là chưa có tài nguyên. [ghList()](../scripts/orgsetup/github.py) áp dụng cùng hợp đồng khi đọc nhãn và ruleset; cơ chế bao trang theo [GitHub CLI](https://cli.github.com/manual/gh_api).

Danh mục repository và cấu hình bảo mật dùng chung trong một lượt lập kế hoạch khi cần giải ID; danh sách chọn rỗng không cần đọc danh mục repository. Discussions và liên kết bảo mật có thể dùng chung danh tính mới nếu đủ `full_name`, ID REST và Node ID GraphQL. Dữ liệu thiếu ID không được cache; cache không giữ giữa lượt xem trước, áp dụng và xác nhận.

Topics, ngôn ngữ CodeQL và các danh sách chọn được so theo nội dung. Topics được chuẩn hóa chữ thường như [GitHub lưu](https://docs.github.com/en/rest/repos/repos#replace-all-repository-topics). Thay đổi thứ tự hoặc topics trùng không tạo thao tác ghi; nguồn và payload được giữ nguyên. Thứ tự claim OIDC vẫn có ý nghĩa khi đối chiếu.

## 🏃 NHÓM RUNNER

Nguồn quản lý thông tin nhóm, quyền repository và giới hạn workflow, không đăng ký runner hoặc xóa nhóm ngoài nguồn. Nhóm mặc định và nhóm enterprise phải tồn tại sẵn; script không tạo lại nhóm mặc định, sửa nhóm kế thừa hoặc vượt quyền sửa.

`selected_repositories` chỉ dùng khi `visibility: selected`, gồm tên repository thuộc tổ chức mà tài khoản đọc được. Danh sách repository của các nhóm selected được đọc song song có giới hạn, xác minh đầy đủ và sắp xếp kết quả theo tên. Nhóm all/private không đọc danh sách chọn; lỗi ở một nhóm làm tài nguyên nhóm runner chưa nhập được, không trả dữ liệu một phần để áp dụng.

Danh sách repository và workflow được so theo nội dung. Workflow chỉ được gửi khi `restricted_to_workflows` bật; request bật giới hạn hoặc đổi danh sách gửi đủ cờ và `selected_workflows`.

Khi tắt giới hạn, danh sách lưu sẵn được giữ. Yêu cầu đồng thời đổi danh sách bị chặn vì API bỏ qua trường khi cờ tắt. Tạo nhóm với cờ tắt chỉ nhận danh sách rỗng; nhóm đã có danh sách vẫn được nhập và chỉnh các cài đặt khác.

## 🛡️ CẤU HÌNH BẢO MẬT VÀ OIDC

Cấu hình bảo mật được giải theo tên; script quản lý phạm vi mặc định và liên kết, không tạo bản sao định nghĩa tùy chỉnh. Phạm vi mặc định phải khớp tên, ID và `target_type` trong danh mục đã xác minh. Dữ liệu thiếu hoặc mâu thuẫn được đánh dấu chưa đọc được; kế hoạch đổi phạm vi sai loại chặn mọi lần ghi.

Code scanning default setup và workflow CodeQL advanced setup cần được chọn phù hợp để tránh thiết lập chồng nhau. Quyền, loại repository và gói dịch vụ quyết định tính năng bảo mật có thể dùng.

OIDC chỉ lưu trường có thể ghi, bỏ subject prefix do GitHub sinh. Tổ chức trả `null` được lưu thành object rỗng, thể hiện chưa tùy chỉnh. API không có DELETE để trở về trạng thái này; nguồn yêu cầu rỗng trong khi GitHub có template được báo là mục cần xử lý. Repository có `use_default: false` có thể dùng template tổ chức mà không khai báo claim riêng. Subject phải khớp chính sách tin cậy của dịch vụ cloud.

## 🌐 GIỚI HẠN VÀ CƠ CHẾ RIÊNG

| Nhóm                                                       | Phạm vi xử lý                                                                                                                      |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `web_settings`                                             | Chỉ đối chiếu; gồm yêu cầu 2FA, tên nhánh mặc định tổ chức, quyền thành viên và cờ bảo mật REST không có hợp đồng ghi trong script |
| Actions bị tắt                                             | Chỉ lưu trường API trả; không suy đoán `allowed_actions` bị ẩn hoặc danh sách selected chưa đọc được                               |
| GitHub Apps                                                | Chỉ lưu tên đã cài trong `installed_apps`; cài/gỡ và quyền installation dùng luồng riêng                                           |
| Ruleset, team, nhãn                                        | Dùng nguồn và lệnh riêng; xem [ruleset](../rulesets/README.md), [team](../MAINTAINERS.md) và [labels.yml](../labels.yml)           |
| OAuth, billing, SSO, credentials, secrets, deploy key      | Cơ chế quản trị riêng; nguồn không lưu giá trị bí mật                                                                              |
| Webhook, environments, custom properties, Pages, variables | Chưa được bộ nhập này quản lý                                                                                                      |

`--repo <tên>` chỉ dùng với `files`, `settings`, `rulesets`, `team`, `labels`; tên không trống, không có khoảng trắng hoặc owner. Lệnh cấp tổ chức, `preview`, `import-settings`, `local-settings` từ chối tùy chọn này. `--discussions` chỉ dùng với `settings`; `preview` và `import-settings` không nhận `--apply`. Tùy chọn được kiểm tra trước đăng nhập và API để giữ đúng phạm vi.

Ruleset cấp tổ chức cần gói GitHub hỗ trợ, kể cả import trên web; GraphQL chỉ đối chiếu. Team xác nhận thông tin, membership và quyền sau ghi; lời mời đang chờ chưa hoàn tất. Chi tiết và mã lỗi theo [ADR 00000015](adr/00000015-github-sync-verification.md).

Một tài nguyên có API riêng không đồng nghĩa bộ nhập hỗ trợ tài nguyên đó. Khả năng áp dụng phụ thuộc hợp đồng script, quyền tài khoản và gói dịch vụ; nguồn hợp lệ hoặc PR đã tạo không chứng minh cài đặt GitHub được áp dụng.

## 📚 TÀI LIỆU GITHUB

- [Update an organization](https://docs.github.com/en/rest/orgs/orgs#update-an-organization)
- [Update a repository](https://docs.github.com/en/rest/repos/repos#update-a-repository)
- [GitHub Actions permissions](https://docs.github.com/en/rest/actions/permissions)
- [GitHub Actions OIDC](https://docs.github.com/en/rest/actions/oidc)
- [OIDC subject và template tổ chức](https://docs.github.com/en/actions/reference/security/oidc)
- [Self-hosted runner groups](https://docs.github.com/en/rest/actions/self-hosted-runner-groups)
- [Code security configurations](https://docs.github.com/en/rest/code-security/configurations)
- [Organization interaction limits](https://docs.github.com/en/rest/interactions/orgs)
- [Code scanning default setup](https://docs.github.com/en/rest/code-scanning/code-scanning#update-a-code-scanning-default-setup-configuration)
- [UpdateRepositoryInput của GraphQL](https://docs.github.com/en/graphql/reference/repos#input-object-updaterepositoryinput)
- [OpenAPI chính thức của GitHub](https://github.com/github/rest-api-description)
