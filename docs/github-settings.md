# ⚙️ CÀI ĐẶT GITHUB TỪ LOCAL

[`github-settings.json`](../github-settings.json) là nguồn cài đặt của tổ chức và từng repository. [`configuration.py`](../scripts/orgsetup/configuration.py) chỉ đọc, ghi các trường đã khai báo; không lưu phản hồi API thô, billing email, token, giá trị secrets hoặc khóa.

## 📥 NHẬP VÀ ÁP DỤNG

```sh
make org-import
git diff -- github-settings.json
make org-settings-preview
make org-settings-apply
```

- `make org-import`: đọc GitHub qua GitHub CLI đã đăng nhập, gồm repository đã archive; ghi nguyên tử tệp local sau khi đọc xong. Lỗi đọc cài đặt chính giữ nguyên tệp. Endpoint chưa đọc được được đánh dấu trong `unavailable`, không giữ giá trị cũ và không tự coi là tắt. Lệnh trả mã lỗi nếu còn mục chưa nhập.
- `make org-settings-preview`: chỉ đọc GitHub, liệt kê các trường sẽ thay đổi theo nguồn local. Không thay đổi GitHub hay tệp local.
- `make org-settings-apply`: đọc và xác minh mọi phạm vi trước khi ghi. `unavailable` còn dữ liệu, cấu hình sai hoặc lỗi đọc chặn việc ghi. Script gửi từng thay đổi qua API, đọc lại và trả mã lỗi khi trạng thái chưa khớp hoặc còn mục chỉ xử lý trên web. Cấu hình bảo mật đang gắn bất đồng bộ chưa được coi là đã hoàn tất.

Việc áp dụng nhiều endpoint không phải một transaction: thay đổi đã thành công không tự hoàn tác khi endpoint sau thất bại. Khi GitHub đang xử lý bất đồng bộ, chạy lại lệnh xem trước để xác nhận trạng thái. Quyền cần thiết do từng endpoint quy định; quyền quản trị repository không thay thế quyền quản trị tổ chức.

Validator kiểm tra hợp đồng nguồn JSON và các tính năng phụ thuộc trong `make check`: Actions cấp repository cần được tổ chức cho phép; Dependabot security updates cần alerts; push protection cần secret scanning; Release bất biến cấp repository phải tuân thủ chính sách tổ chức. Discussions được cập nhật qua mutation GraphQL `updateRepository`.

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
| `unavailable`                               | Các endpoint chưa đọc được; phải nhập lại thành công trước khi áp dụng                                                                     |

Mỗi repository đã nhập có phần riêng; `local-settings` áp dụng các phần này và phần tổ chức, không áp dụng `repository_defaults` cho repository mới chưa nhập. Sau khi tạo repository mới, nhập lại hoặc dùng các lệnh thiết lập repository truyền thống. Chỉ nhập những repository tài khoản hiện tại đọc được; danh sách API không chứng minh có quyền nhìn thấy toàn bộ repository riêng tư.

## 🔧 PHẠM VI API ĐƯỢC QUẢN LÝ

| Nhóm                | Nội dung                                                                                                                                                                  |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Actions             | Bật/tắt ở tổ chức và repository; ghim SHA khi API trả trường này; quyền mặc định `GITHUB_TOKEN`; duyệt workflow từ fork; chạy workflow của fork riêng tư ở phạm vi hỗ trợ |
| OIDC                | Template subject, dùng mặc định hoặc template tổ chức, claim tùy chỉnh và chế độ immutable subject; bỏ tiền tố subject do GitHub tự sinh                                  |
| Nhóm runner         | Tạo hoặc sửa nhóm do tổ chức quản lý, phạm vi repository, quyền chạy ở repository công khai và giới hạn workflow; không đăng ký runner hay xóa nhóm ngoài nguồn           |
| Lưu dữ liệu Actions | Số ngày giữ checks, trạng thái commit, log và artifact theo API; tuân thủ mức tối đa GitHub cho phép                                                                      |
| Bảo mật repository  | Dependabot alerts/security updates, secret scanning và tính năng có trường PATCH hợp lệ, push protection, báo cáo lỗ hổng riêng tư ở repository công khai                 |
| Cấu hình bảo mật    | Đổi phạm vi mặc định của cấu hình có sẵn; gắn hoặc tháo cấu hình theo tên. ID được đọc lại lúc lập kế hoạch                                                               |
| Code scanning       | Cấu hình default setup qua API; workflow CodeQL riêng vẫn được quản lý bằng tệp workflow, cần tránh bật hai cách thiết lập chồng nhau                                     |
| Release             | Chính sách Release bất biến cấp tổ chức và bật/tắt cấp repository trong phạm vi GitHub cho phép                                                                           |
| Tương tác           | Giới hạn tương tác lâu dài, bỏ giới hạn và giới hạn tạo Pull Request                                                                                                      |
| Topics              | Danh sách topics của từng repository đã nhập                                                                                                                              |

`settings` và `org-settings` truyền thống đọc giá trị cài đặt từ nguồn JSON; lệnh `settings` vẫn giữ hành vi chỉ bật bảo mật, topics `.github` theo `CITATION.cff`, giữ trạng thái Actions. Dùng `local-settings` khi cần khôi phục đúng cấu hình đã nhập, gồm cả trạng thái tắt và topics theo JSON.

## 🌐 PHẦN CẦN CƠ CHẾ RIÊNG

- Các mục `web_settings` như yêu cầu 2FA, tên nhánh mặc định cấp tổ chức và một số quyền thành viên không có endpoint ghi được script hỗ trợ. Các cờ bảo mật “enabled for new repositories” trong REST cũ chỉ được đọc để đối chiếu; chính sách mới dùng code security configurations.
- Khi Actions tắt, GitHub có thể không trả `allowed_actions`. Tệp chỉ lưu trường thực sự đọc được; không thể khôi phục một giá trị bị ẩn. Chế độ `selected` của Actions hoặc Release bất biến cần thêm danh sách phạm vi, chưa được script nhập/áp dụng và sẽ báo chưa xác minh thay vì bỏ mất danh sách.
- Định nghĩa cấu hình bảo mật tùy chỉnh không được xuất thành tài nguyên tạo mới. Cấu hình do GitHub quản lý được giải theo tên; script quản lý phạm vi và liên kết, không sao chép định nghĩa của GitHub.
- OIDC tổ chức trả `null` được lưu thành object rỗng, nghĩa là chưa tùy chỉnh. API không có thao tác DELETE để trở về trạng thái này; nếu local yêu cầu rỗng nhưng web đã có template, script báo mục cần xử lý thay vì giả định đã xóa. Repository đặt `use_default: false` có thể dùng template tổ chức mà không cần khai báo claim riêng. Thay đổi subject phải khớp với chính sách tin cậy của dịch vụ cloud.
- Nhóm runner mặc định hoặc do enterprise quản lý phải tồn tại sẵn; script không tạo lại nhóm mặc định, sửa nhóm kế thừa hay vượt quyền sửa giới hạn workflow. Danh sách `selected_repositories` chỉ dùng khi `visibility` là `selected`, phải nằm trong tổ chức và được tài khoản hiện tại đọc thấy.
- Ruleset, labels, team và quyền team dùng các nguồn hiện có trong [`rulesets/`](../rulesets/), [`labels.yml`](../labels.yml), [`teams.py`](../scripts/orgsetup/teams.py). Nhập cài đặt không ghi đè các nguồn này; đối chiếu bằng `make org-preview`, áp dụng bằng các lệnh `rulesets`, `org-rulesets`, `labels`, `team` của [`org-setup.py`](../scripts/org-setup.py). Ruleset cấp tổ chức phụ thuộc quyền và gói GitHub; không có API vượt qua giới hạn gói.
- `organization.web_settings.installed_apps` chỉ lưu tên GitHub Apps đã cài để đối chiếu, không lưu quyền của từng installation, token hay tài khoản cài đặt. Việc cài hoặc gỡ Apps vẫn cần luồng quản trị riêng.
- OAuth Apps, billing, SSO, webhook có thông tin xác thực, credentials của runner, deploy key và secrets cần cơ chế quản trị riêng. API không cho đọc lại giá trị secrets hoặc khóa riêng. Webhook, environments, custom properties, Pages và variables chưa được bộ nhập này quản lý. Không coi tệp JSON là bản sao toàn bộ trang Settings hoặc bản khôi phục mọi tài nguyên của tài khoản.

## 📚 TÀI LIỆU GITHUB

- [Update an organization](https://docs.github.com/en/rest/orgs/orgs#update-an-organization)
- [Update a repository](https://docs.github.com/en/rest/repos/repos#update-a-repository)
- [GitHub Actions permissions](https://docs.github.com/en/rest/actions/permissions)
- [GitHub Actions OIDC](https://docs.github.com/en/rest/actions/oidc)
- [OIDC subject và template tổ chức](https://docs.github.com/en/actions/reference/security/oidc)
- [Self-hosted runner groups](https://docs.github.com/en/rest/actions/self-hosted-runner-groups)
- [Code security configurations](https://docs.github.com/en/rest/code-security/configurations)
- [Organization interaction limits](https://docs.github.com/en/rest/interactions/orgs)
- [Code scanning default setup](https://docs.github.com/en/rest/code-scanning/code-scanning#update-default-setup-configuration)
- [UpdateRepositoryInput của GraphQL](https://docs.github.com/en/graphql/reference/repos#updaterepositoryinput)
- [OpenAPI chính thức của GitHub](https://github.com/github/rest-api-description)
