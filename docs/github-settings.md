# ⚙️ CÀI ĐẶT GITHUB TỪ LOCAL

[github-settings.json](../github-settings.json) là nguồn cài đặt tổ chức và repository. [configuration.py](../scripts/orgsetup/configuration.py), [resources.py](../scripts/orgsetup/resources.py), [catalog.py](../scripts/orgsetup/catalog.py), [enterprise.py](../scripts/orgsetup/enterprise.py), [branches.py](../scripts/orgsetup/branches.py), [patterns.py](../scripts/orgsetup/patterns.py), [registries.py](../scripts/orgsetup/registries.py), [policies.py](../scripts/orgsetup/policies.py) và [hosted.py](../scripts/orgsetup/hosted.py) khai báo hợp đồng API, kiểm tra nguồn và lập kế hoạch áp dụng. Tệp local chỉ lưu trường được hỗ trợ, không lưu phản hồi API thô, billing email, token, secrets hoặc khóa.

## 📥 NHẬP, XEM TRƯỚC VÀ ÁP DỤNG

GitHub CLI cần đăng nhập bằng tài khoản có quyền theo từng endpoint. Quyền quản trị repository không thay thế quyền quản trị tổ chức.

```sh
make org-import
git diff -- github-settings.json
make org-settings-audit
make org-settings-preview
make org-settings-apply
```

| Lệnh                        | Hành vi                                                                                                        |
| --------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `make org-import`           | Đọc cài đặt, kể cả repository archive, rồi ghi nguyên tử nguồn local theo định dạng Prettier; không sửa GitHub |
| `make org-import-missing`   | Bổ sung dữ liệu chưa có sau nâng cấp gói/quyền, giữ giá trị local đã lưu                                       |
| `make org-settings-audit`   | Đọc lại mọi nhóm được quản lý; kiểm tra phạm vi và bản local, chưa đầy đủ thì trả mã lỗi                       |
| `make org-settings-preview` | Đọc GitHub và lập danh sách khác biệt theo nguồn local                                                         |
| `make org-settings-apply`   | Xác minh mọi phạm vi trước khi ghi, áp dụng tuần tự và đọc lại để xác nhận                                     |

Lỗi đọc metadata chính giữ nguyên tệp khi nhập. Endpoint chưa đọc được ghi vào `unavailable`, không giữ giá trị cũ hoặc suy đoán trạng thái tắt. Lệnh nhập trả mã lỗi nếu còn mục chưa đọc được; nguồn có `unavailable` chặn áp dụng.

`local-settings --only <nhóm>` giới hạn xem trước và áp dụng vào nhóm được chọn rõ; có thể lặp `--only` để chọn nhiều nhóm. Nhóm gồm `settings`, `endpoints`, `security`, `runner_groups`, `security_configuration`, `security_configurations` và các tên trong bảng `collections` dưới đây. Chỉ các mục chưa đọc được thuộc phạm vi được chọn chặn kế hoạch; source, `unavailable` và audit đầy đủ được giữ nguyên. Danh tính sai, dữ liệu nguồn sai hoặc API thuộc nhóm được chọn chưa xác minh được vẫn chặn ghi. Đọc lại sau ghi dùng đúng phạm vi đã chọn, không tự mở rộng sang nhóm khác.

Ví dụ khôi phục ruleset và nhãn sau khi API tương ứng đã đọc được:

```sh
python3 scripts/org-setup.py local-settings --only rulesets --only labels
python3 scripts/org-setup.py local-settings --only rulesets --only labels --apply
```

Với repository riêng tư, `security_and_analysis` thiếu hoặc `null` được đánh dấu chưa đọc được; các phần khác vẫn có thể nhập. Repository công khai thiếu trường này hoặc phản hồi sai kiểu là lỗi metadata chính. Tính năng bảo mật bị ẩn không được ghi thành trạng thái tắt.

Ghi nhiều endpoint không phải transaction: thao tác thành công không tự hoàn tác khi bước sau thất bại. Trạng thái đang xử lý bất đồng bộ, gồm liên kết cấu hình bảo mật, chưa được coi là hoàn tất. Sau khi GitHub xử lý xong, chạy lại xem trước để xác nhận.

## 📤 KHÔI PHỤC SAU NÂNG CẤP GÓI

Giữ `github-settings.json` đã kiểm tra trong Git cùng các nguồn `rulesets/`, team, nhãn và workflow. `make org-import` thay toàn bộ phần cài đặt đã nhập bằng trạng thái hiện tại trên GitHub; chỉ nhập lại khi muốn cập nhật nguồn theo web. Khi muốn khôi phục bản đã lưu, dùng trực tiếp bản đó để xem trước và áp dụng.

Sau khi gói mới đã có hiệu lực, dùng tài khoản có quyền quản trị tương ứng và chạy:

```sh
make org-import-missing
git diff -- github-settings.json
make check
make org-settings-preview
make org-settings-apply
make org-settings-preview
```

`make org-import-missing` chỉ bổ sung trường, endpoint và nhóm tài nguyên chưa có, giữ các giá trị local đã nhập hoặc đã chỉnh. Lệnh điền cả khóa thiếu trong object và trong các tài nguyên đã có cùng tên; không thêm mục vào danh sách local đang quản lý, không thay danh sách rỗng hoặc giá trị `null`. Lệnh không mở rộng danh sách repository của bản đã lưu; nhập mới bằng `make org-import` khi muốn cập nhật toàn bộ phạm vi theo GitHub. Phần chỉ quan sát của ruleset được thay bằng hợp đồng REST đầy đủ khi API đã đọc được. Còn lỗi quyền, gói hoặc dữ liệu thì giữ `unavailable` và chặn áp dụng.

Kiểm tra kết quả xem trước trước từng lần áp dụng. Cài đặt dùng đúng giá trị local, kể cả trạng thái tắt và danh sách chọn rỗng. Nâng cấp không tự bật Actions hoặc các tính năng bảo mật trong nguồn: nếu muốn bật, sửa nguồn và các trường phụ thuộc rồi kiểm tra và xem trước. `repository_defaults` là chính sách cho lệnh `settings`; các giá trị riêng đã nhập cho repository được ưu tiên.

`make org-settings-audit` kiểm tra bản nhập có đủ và khớp các nhóm API đang đọc được hay không; trả mã lỗi khi thiếu phạm vi repository, thiếu nhóm, khác dữ liệu hoặc có `unavailable`. Nguồn local chủ động khác trạng thái web cũng được báo khác; đây là kết quả đối chiếu bản nhập, không phải yêu cầu đổi mục tiêu khôi phục theo web. Sau áp dụng, dùng xem trước để xác minh các mục nguồn đang quản lý.

Ruleset trong `collections` là bản đang cài trên web. Các lệnh `org-rulesets`, `rulesets`, `team`, `labels` áp dụng chính sách dự án từ nguồn riêng; dùng khi muốn chuyển sang chính sách đó, sau khi thống nhất với bản khôi phục. Bản nhánh/tag cấp tổ chức trong `rulesets/` vẫn được sinh từ nguồn cấp repository theo [hướng dẫn ruleset](../rulesets/README.md). [GitHub Team hoặc Enterprise](https://docs.github.com/en/organizations/managing-organization-settings/creating-rulesets-for-repositories-in-your-organization) hỗ trợ ruleset tổ chức; tính năng bảo mật có thể cần quyền sử dụng riêng theo [gói GitHub](https://docs.github.com/en/get-started/learning-about-github/githubs-plans).

Mục `web_settings` phải được người quản trị khôi phục trên web khi có khác biệt. API ẩn giá trị, cài đặt Apps, secrets và các cơ chế ngoài phạm vi không được suy đoán hoặc tự khôi phục.

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
| `organization.runner_groups`                | Quyền nhóm runner, workflow, repository được chọn và liên kết mạng; dùng tên, giải ID khi áp dụng                                          |
| `repositories.<tên>.security_configuration` | Tên cấu hình bảo mật cần gắn; `null` là không gắn                                                                                          |
| `web_settings`                              | Giá trị chỉ đối chiếu, không ghi qua lệnh này; gồm mục không có API ghi được hỗ trợ và cờ bảo mật REST cũ                                  |
| `collections`                               | Cấu hình có thể ghi của tài nguyên; dùng tên và giải ID khi cần                                                                            |
| `observed`                                  | Chỉ đối chiếu; ruleset GraphQL thiếu trường REST không được dùng để ghi                                                                    |
| `unavailable`                               | Endpoint hoặc trường metadata chưa đọc được; phải bổ sung thành công trước khi áp dụng                                                     |

Tên repository không được trùng khi bỏ qua hoa/thường. `local-settings` quản lý tổ chức và các repository đã khai báo, không dùng `repository_defaults` cho repository mới chưa nhập. Sau khi tạo repository, nhập lại hoặc dùng các lệnh thiết lập riêng. Danh sách nhập chỉ gồm repository tài khoản hiện tại đọc được, không chứng minh tài khoản thấy toàn bộ repository riêng tư.

## 🔧 PHẠM VI API ĐƯỢC QUẢN LÝ

| Nhóm                | Nội dung                                                                                                                                                                                                                                                    |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Actions             | Bật/tắt ở tổ chức và repository; chính sách self-hosted runners và quyền chia sẻ workflow private; danh sách repository được chọn; actions và reusable workflows được phép; ghim SHA khi API trả trường này; quyền mặc định `GITHUB_TOKEN`; chính sách fork |
| OIDC                | Template subject, dùng mặc định hoặc template tổ chức, claim tùy chỉnh và chế độ immutable subject; bỏ tiền tố subject do GitHub tự sinh                                                                                                                    |
| Nhóm runner         | Tạo hoặc sửa nhóm do tổ chức quản lý, phạm vi repository, quyền chạy ở repository công khai và giới hạn workflow; không đăng ký runner hay xóa nhóm ngoài nguồn                                                                                             |
| Lưu dữ liệu Actions | Số ngày giữ checks, trạng thái commit, log và artifact theo API; tuân thủ mức tối đa GitHub cho phép                                                                                                                                                        |
| Bảo mật repository  | Dependabot alerts/security updates, secret scanning và tính năng có trường PATCH hợp lệ, push protection, báo cáo lỗ hổng riêng tư ở repository công khai                                                                                                   |
| Cấu hình bảo mật    | Tạo hoặc sửa định nghĩa của tổ chức; đổi phạm vi mặc định; gắn hoặc tháo cấu hình theo tên. ID được đọc lại lúc lập kế hoạch                                                                                                                                |
| Code scanning       | Cấu hình default setup qua API; workflow CodeQL riêng vẫn được quản lý bằng tệp workflow, cần tránh bật hai cách thiết lập chồng nhau                                                                                                                       |
| Release             | Chính sách Release bất biến cấp tổ chức, gồm danh sách repository được chọn, và bật/tắt cấp repository trong phạm vi GitHub cho phép                                                                                                                        |
| Tương tác           | Giới hạn tương tác lâu dài, bỏ giới hạn và giới hạn tạo Pull Request                                                                                                                                                                                        |
| Topics              | Danh sách topics của từng repository đã nhập                                                                                                                                                                                                                |

## 🧩 DANH MỤC TÀI NGUYÊN

| Nhóm `collections`       | Dữ liệu và thao tác                                                                                                                 |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| `rulesets`               | Ruleset trực tiếp của tổ chức hoặc repository, không lấy ruleset kế thừa thành bản repository; tạo/sửa theo tên đã lưu              |
| `teams`                  | Tên, mô tả, privacy, notification, team cha và quyền từng repository; tạo cha trước con; không nhập membership hoặc lời mời         |
| `security_managers`      | Team được cấp vai trò quản lý bảo mật; không lưu danh sách người dùng                                                               |
| `security_definitions`   | Định nghĩa bảo mật tùy chỉnh do tổ chức sở hữu; không sửa định nghĩa global của GitHub                                              |
| `labels`                 | Tên, màu, mô tả; cập nhật đúng tên, không xóa nhãn ngoài nguồn                                                                      |
| `autolinks`              | Prefix, URL template và chế độ alphanumeric; thay đúng prefix nếu cấu hình đổi                                                      |
| `property_schema`        | Định nghĩa custom properties của tổ chức; property kế thừa enterprise cần nguồn cấp enterprise                                      |
| `custom_properties`      | Giá trị custom properties của repository; chỉ dùng dữ liệu cấu hình không nhạy cảm                                                  |
| `environments`           | Thời gian chờ, chặn tự phê duyệt, reviewer ID, chính sách branch/tag và tham chiếu variables; không lưu hồ sơ reviewer hoặc secrets |
| `pages`                  | Build type, branch/path source, custom domain và HTTPS; không lưu nội dung site hoặc dữ liệu deploy                                 |
| `oidc_properties`        | Repository custom properties do tổ chức đưa vào OIDC token; không tạo lại cấu hình kế thừa enterprise                               |
| `variables`              | Tên biến ở cấp tổ chức/repository, visibility và repository được chọn; giá trị lưu riêng ngoài Git                                  |
| `webhooks`               | Events, trạng thái hoạt động, kiểu nội dung và SSL; URL lưu riêng, shared secret cần cung cấp khi tạo lại                           |
| `branch_protection`      | Bảo vệ nhánh kiểu cũ theo pattern, chữ ký, review, status checks ràng buộc Apps, deployments và actor IDs; độc lập với ruleset      |
| `network_configurations` | Cấu hình mạng hosted compute cấp tổ chức, cloud network settings và failover; kiểm tra ID cloud trước ghi                           |
| `organization_roles`     | Định nghĩa quyền để đối chiếu và danh sách team được gán trực tiếp; giải ID vai trò mới ở lượt áp dụng                              |
| `actions_policies`       | Chính sách chạy workflow cấp tổ chức/repository, enforcement, workflow/repository conditions và rule actor/event                    |
| `dependabot_access`      | Default level và danh sách repository được cấp quyền truy cập dependency; chỉ cấp tổ chức                                           |
| `hosted_runners`         | Hosted runner pools cấp tổ chức, image, size, giới hạn scale, static IP và nhóm runner theo tên                                     |
| `custom_patterns`        | Mẫu secret scanning cấp tổ chức/repository, định nghĩa regex lưu riêng; trạng thái xuất bản chỉ đối chiếu                           |
| `pattern_settings`       | Override push protection theo mẫu cấp tổ chức; dùng token type nhà cung cấp hoặc slug mẫu tùy chỉnh                                 |
| `private_registries`     | Cấu hình registry cấp tổ chức, visibility và repository được chọn; định nghĩa xác thực lưu riêng                                    |
| `ip_allow_list`          | Cờ thực thi, cờ cho GitHub Apps và các entry cấp tổ chức; địa chỉ và tên entry lưu riêng ngoài Git                                  |

Mọi nhóm dùng hợp đồng cho phép và kiểm tra dữ liệu trước khi lưu. Lỗi một nhóm giữ dấu chưa đọc được; không thay bằng danh sách rỗng. Pages trả 404 chỉ được coi là không có site khi đã xác minh repository công khai và quyền admin; repository riêng tư có thể bị ẩn bởi gói nên vẫn báo chưa đọc được.

Khôi phục tạo hoặc cập nhật các mục local quản lý, giữ tài nguyên ngoài nguồn. Danh sách local rỗng không có nghĩa xóa toàn bộ tài nguyên trên web. Environment có quy tắc Apps chưa được hỗ trợ hoặc cần bỏ branch policy được báo lỗi thay vì làm mất quy tắc. Nguồn trong Git không chứa secrets, giá trị variables, URL webhook, địa chỉ/tên IP allow list, regex tùy chỉnh, định nghĩa registry hoặc hồ sơ người dùng.

## 🔐 DỮ LIỆU LOCAL NGOÀI GIT

[localdata.py](../scripts/orgsetup/localdata.py) lưu giá trị variables, URL webhook, địa chỉ/tên entry của IP allow list, định nghĩa regex và registry tại `~/.local/share/toanquynh-orgsetup/TOANQUYNHLLC/values.json`, quyền `0600`. Có thể đặt `ORGSETUP_PRIVATE_DIR` thành thư mục khác ngoài repository; symlink dẫn vào repository và tệp cho tài khoản khác đọc bị từ chối. Tệp chỉ chứa ánh xạ tham chiếu sang chuỗi giá trị, không lưu phản hồi API thô. Các giá trị này không xuất hiện trong kế hoạch hoặc thông báo lỗi khi ghi.

`value_source` của variable và `url_source` của webhook trỏ tới khóa trong tệp riêng. Tham chiếu giữ đúng phạm vi tổ chức, repository hoặc environment. Mỗi giá trị mới có tham chiếu riêng; giá trị cũ được giữ để khôi phục các bản nguồn trước, kể cả khi thay tệp JSON công khai thất bại. Sao lưu an toàn tệp riêng cùng phiên bản `github-settings.json` tương ứng trước khi chuyển máy hoặc khôi phục; chỉ có nguồn trong Git thì chưa đủ khi nguồn chứa tham chiếu riêng tư. Xem trước không ghi tệp riêng.

GitHub không cho đọc lại shared secret của webhook. Khi tạo lại webhook, người quản trị bổ sung shared secret vào tệp riêng dưới khóa `secret_source` của mục đó; nếu webhook chủ ý không có secret thì cung cấp chuỗi rỗng. Thiếu giá trị chặn toàn bộ kế hoạch trước thao tác ghi đầu tiên. Cập nhật riêng cấu hình webhook qua endpoint `/config` giữ secret trên GitHub; đổi events hoặc trạng thái hoạt động dùng endpoint tổng và cũng cần cung cấp secret riêng để tránh bị API xóa. Webhook được nhận diện theo URL đã lưu; thay URL được coi là tạo mục mới, cần secret riêng. Secrets của Actions không được nhập hoặc khôi phục bằng lệnh này.

Webhook tổ chức cần quyền riêng: token classic phải có `admin:org_hook`; quyền `admin:org` không thay thế. API trả `404` không chứng minh tổ chức không có webhook. Nếu chưa đủ scope, người quản trị bổ sung bằng `gh auth refresh -h github.com -s admin:org_hook`, hoàn tất đăng nhập rồi chạy `make org-import-missing`. Với token fine-grained hoặc GitHub App, cấp quyền Webhooks tương ứng theo [hợp đồng webhook tổ chức](https://docs.github.com/en/rest/orgs/webhooks).

## ✅ XÁC MINH VÀ THỨ TỰ ÁP DỤNG

Luồng đọc xác minh `login` của tổ chức hoặc `full_name` của repository theo endpoint, không phân biệt hoa/thường. Thiếu danh tính hoặc chuyển hướng tới tài nguyên khác dừng lệnh; nguồn không tự đổi owner hoặc tên. Quy tắc cũng áp dụng khi giải ID cho Discussions, cấu hình bảo mật và nhánh mặc định dùng bởi `files`, `rulesets`.

Metadata được xác minh trước khi đọc song song các endpoint độc lập. Với `local-settings`, tổ chức được đọc và kiểm tra trước; kế hoạch tổ chức sai thì dừng trước khi đọc repository. Các repository được đọc song song có giới hạn rồi lập kế hoạch theo thứ tự nguồn. Mọi lần đọc và xác minh kế hoạch hoàn tất trước thao tác ghi đầu tiên. ID của định nghĩa bảo mật cần tạo được giải theo tên sau bước tạo; chưa xác minh được ID thì dừng trước defaults hoặc attach. Mỗi lệnh GitHub CLI có thời gian chờ hữu hạn; mutation hết thời gian chờ không tự gửi lại, phải xem trước để xác định kết quả.

Khi bỏ archive, script thực hiện trước các cập nhật khác của repository; khi archive, thực hiện sau cùng. Dependabot alerts được bật trước security updates và tắt sau security updates, không phụ thuộc thứ tự endpoint trong JSON. Discussions dùng GraphQL `updateRepository`; các trường repository khác dùng REST.

Khi đổi `merge_commit_message` hoặc `squash_merge_commit_message`, request gửi kèm tiêu đề tương ứng lấy từ nguồn hoặc trạng thái đã xác minh. Thiếu tiêu đề hợp lệ chặn ghi; phần xem trước chỉ liệt kê giá trị thực sự đổi.

`local-settings` đọc lại trạng thái sau áp dụng bằng dữ liệu mới. Các trường chính do `settings`, `org-settings` ghi cũng được đọc lại, kiểm tra kiểu và đối chiếu trước khi báo thành công; gồm Discussions và archive. Chuỗi rỗng và `null` của trường văn bản rỗng được coi là tương đương. `settings` dùng metadata đã xác nhận cho các bước topics và bảo mật phụ thuộc.

`settings` dùng `repository_defaults` và phần riêng từng repository nhưng giữ hành vi thiết lập: chỉ bật bảo mật, giữ trạng thái Actions và lấy topics `.github` từ `CITATION.cff`. Dùng `local-settings` để áp dụng đúng trạng thái nhập, gồm giá trị tắt và topics từ JSON.

Validator kiểm tra hợp đồng và phụ thuộc: Actions repository cần được tổ chức cho phép; security updates cần alerts; push protection cần secret scanning; Release bất biến phải tuân thủ chính sách tổ chức.

## 🎯 CHÍNH SÁCH SELECTED

Danh sách con chỉ được nhập khi chính sách cha là `selected`. Nguồn đổi sang chế độ này phải khai báo endpoint đi kèm. Danh sách rỗng có nghĩa không chọn phần tử nào.

| Chính sách cha                                                             | Endpoint đi kèm trong `endpoints`                      | Dữ liệu local                                                  |
| -------------------------------------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------- |
| `actions/permissions.enabled_repositories` của tổ chức                     | `actions/permissions/repositories`                     | `selected_repositories`: tên đầy đủ như `TOANQUYNHLLC/.github` |
| `actions/permissions/self-hosted-runners.enabled_repositories` của tổ chức | `actions/permissions/self-hosted-runners/repositories` | `selected_repositories`: tên đầy đủ thuộc tổ chức              |
| `copilot/coding-agent/permissions.enabled_repositories` của tổ chức        | `copilot/coding-agent/permissions/repositories`        | `selected_repositories`: tên đầy đủ thuộc tổ chức              |
| `actions/permissions.allowed_actions` của tổ chức hoặc repository          | `actions/permissions/selected-actions`                 | `github_owned_allowed`, `verified_allowed`, `patterns_allowed` |
| `settings/immutable-releases.enforced_repositories` của tổ chức            | `settings/immutable-releases/repositories`             | `selected_repositories`: tên đầy đủ thuộc tổ chức              |

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

Cấu hình bảo mật được giải theo tên; script tạo/sửa định nghĩa tùy chỉnh của tổ chức trong `collections.security_definitions`, quản lý phạm vi mặc định và liên kết. Các định nghĩa global chỉ được tham chiếu theo tên. Phạm vi mặc định phải khớp tên, ID và `target_type` trong danh mục đã xác minh. Dữ liệu thiếu hoặc mâu thuẫn được đánh dấu chưa đọc được; kế hoạch đổi phạm vi sai loại chặn mọi lần ghi.

Code scanning default setup và workflow CodeQL advanced setup cần được chọn phù hợp để tránh thiết lập chồng nhau. Quyền, loại repository và gói dịch vụ quyết định tính năng bảo mật có thể dùng.

OIDC chỉ lưu trường có thể ghi, bỏ subject prefix do GitHub sinh. Tổ chức trả `null` được lưu thành object rỗng, thể hiện chưa tùy chỉnh. API không có DELETE để trở về trạng thái này; nguồn yêu cầu rỗng trong khi GitHub có template được báo là mục cần xử lý. Repository có `use_default: false` có thể dùng template tổ chức mà không khai báo claim riêng. Subject phải khớp chính sách tin cậy của dịch vụ cloud.

## 🏢 MẠNG, VAI TRÒ VÀ BẢO VỆ NHÁNH

`network_configurations` lưu cấu hình do tổ chức quản lý, không triển khai tài nguyên Azure hoặc đăng ký runner. ID cấu hình GitHub được giải mới theo tên; `network_settings_ids` là ID tài nguyên cloud có sẵn, cần xác minh API trước tạo/sửa. Tạo cấu hình cần một network setting; failover cần setting dự phòng. API ghi hỗ trợ `none` và `actions`; cấu hình `codespaces` vẫn được nhập để đối chiếu nhưng thay đổi cần luồng riêng. Token classic cần `read:network_configurations` khi đọc, `write:network_configurations` khi ghi; gói GitHub không thay thế scope token. Cấu hình mạng đang có không bị tự xóa.

`organization_roles` lưu tên, nguồn, base role, quyền và team được gán trực tiếp. Gán gián tiếp được khôi phục qua quan hệ cha–con của team; không biến thành quyền trực tiếp. API hiện hành cho đọc định nghĩa và gán vai trò, không tạo định nghĩa: vai trò cần tồn tại và khớp quyền trước khi áp dụng. ID vai trò được đọc lại theo tên, không dùng ID cũ trong bản lưu. Team cần có sẵn hoặc nằm trong cùng kế hoạch tạo team. Sau khi tạo/sửa, phải xác nhận slug, tên và ID của team trước khi cấp quyền tiếp theo. Việc thu hồi quyền và gán cho từng người dùng dùng quy trình quản trị riêng; bản nhập không chứa danh sách người dùng.

`ip_allow_list` đọc đủ entry và các cờ qua GraphQL. Entry kế thừa enterprise không được biến thành entry cấp tổ chức. `value_source` và `name_source` trỏ tới địa chỉ/CIDR và tên trong tệp riêng ngoài Git; chỉ UUID tham chiếu và trạng thái hoạt động nằm trong nguồn công khai. Khi áp dụng, giải lại ID tổ chức và entry, tạo/cập nhật các địa chỉ được quản lý, giữ entry ngoài nguồn. Tắt thực thi IP được xử lý trước; bật thực thi và cho Apps được xử lý sau các cập nhật khác. Các request khôi phục và đọc lại cần xuất phát từ mạng được chính sách mới cho phép. Gói và quyền GitHub phải hỗ trợ tính năng thực thi này.

`branch_protection` nhập đầy đủ pattern bảo vệ nhánh kiểu cũ và các danh sách actor phân trang qua GraphQL. Nguồn không chứa ID rule hoặc hồ sơ người dùng; actor ID và App ID là định danh opaque theo hợp đồng GraphQL. Tạo/sửa giải ID repository/rule mới, giữ check ràng buộc đúng GitHub App, không thay rule wildcard bằng danh sách nhánh hiện có. Rule ngoài nguồn được giữ. Thiếu trang, danh tính sai hoặc GraphQL trả lỗi đều chặn ghi; kết quả mutation được kiểm tra trước request tiếp theo và toàn bộ trạng thái được đọc lại. Phần này độc lập với ruleset, không tự chuyển giữa hai cơ chế bảo vệ.

## ▶️ ACTIONS POLICIES, CACHE VÀ HOSTED RUNNER

`actions_policies` nhập danh sách với `has_parents=false` và đọc chi tiết từng policy. Tên, nguồn sở hữu, ID và target phải khớp; policy kế thừa không được sao chép xuống phạm vi con. Nguồn giữ enforcement, điều kiện repository/workflow và rule giới hạn actor hoặc event, loại metadata. Actor ID là tham chiếu quyền API, không lưu hồ sơ người dùng; actor cần tồn tại khi khôi phục. Điều kiện API `repository_id` được lưu bằng `selected_repositories` với tên đầy đủ và giải ID mới trước ghi. Điều kiện property giữ name/value/source theo hợp đồng. Workflow `~ALL` và điều kiện mặc định được so theo cùng ý nghĩa để lần áp dụng tiếp theo không ghi lại.

Thay đổi policy dùng ID vừa đọc, tạo bằng POST và cập nhật bằng PUT; tài nguyên ngoài nguồn được giữ. Cấu hình đổi đồng thời, rule/event lạ hoặc điều kiện không hợp lệ chặn kế hoạch. Bỏ `conditions` trong request không xóa điều kiện đang có; để chọn mọi workflow, dùng `workflow_path` với `include: ["~ALL"]`, `exclude: []`. Phản hồi phải xác nhận đúng tên và ID trước request tiếp theo, sau đó toàn bộ nguồn được đọc lại. API tổ chức có thể cần GitHub Team và quyền tương ứng; xem [Actions policies](https://docs.github.com/en/rest/actions/policies).

`dependabot_access` đọc mọi trang và giữ `default_level` cùng danh sách repository được cấp quyền. Nguồn chỉ lưu tên repository, không giữ metadata hoặc hồ sơ owner. Khi áp dụng, đặt default level rồi thêm/bỏ đúng các quyền khác biệt để danh sách khớp local; các repository không bị xóa. API không trả `default_level` thì vẫn giữ danh sách repository đã đọc và đánh dấu trường chưa nhập, không suy đoán `null`. Default level `null` được lưu đúng như API trả nhưng không thể gửi để reset; nhu cầu reset được báo trước ghi. Danh sách chỉ nhận repository thuộc tổ chức; lỗi/trùng ID hoặc chính sách đổi giữa các trang không trả dữ liệu thiếu. Xem [Dependabot repository access](https://docs.github.com/en/rest/dependabot/repository-access).

Giới hạn cache nằm ở `repositories.<tên>.endpoints.actions/cache/retention-limit.max_cache_retention_days` và `actions/cache/storage-limit.max_cache_size_gb`, dùng GET/PUT và đọc lại xác nhận. Đây là cài đặt cache, tách khỏi thời gian giữ artifact/log. API có thể trả HTTP 402 khi tài khoản chưa có phương thức thanh toán; nguồn giữ dấu chưa đọc được, không dùng giá trị mặc định để thay thế. Xem [hợp đồng cache Actions](https://docs.github.com/en/rest/actions/cache).

`hosted_runners` giữ tên pool, `runner_group` theo tên, image, machine size, giới hạn scale, cờ static IP và image generation. Không lưu ID pool/nhóm, địa chỉ IP được cấp hoặc dữ liệu hoạt động. Image GitHub/partner dùng mã trong danh mục công khai; custom image dùng tên và phiên bản, giải ID hiện tại khi ghi. Script xác minh image/size khả dụng trước lập kế hoạch, không tự tạo image, tài nguyên cloud hoặc bản sao filesystem của runner. Custom image và phiên bản cần được tạo sẵn.

Nhóm runner có thể dùng `settings.network_configuration` là tên cấu hình mạng hoặc `null` để bỏ liên kết đã đọc được. Tên được xác minh khi lập kế hoạch và giải ID ngay trước request; trường bị API ẩn không được suy đoán là `null`. Khi có tạo mới, thứ tự là cấu hình mạng, nhóm runner rồi hosted runner. Pool chỉ được tạo/sửa theo nguồn, không tự xóa pool ngoài nguồn. GitHub đang provisioning hoặc phản hồi không khớp tên/ID thì chưa báo hoàn tất; xem trước lại khi pool đã sẵn sàng. IP mới do GitHub cấp không được bảo đảm giống địa chỉ trước đây. Khả năng tạo/scale và chi phí phụ thuộc gói và tài khoản GitHub; xem [hosted runners](https://docs.github.com/en/rest/actions/hosted-runners).

## 🔎 MẪU SECRET SCANNING VÀ PRIVATE REGISTRIES

`custom_patterns` giữ tên, slug, trạng thái xuất bản, cờ push protection và `definition_source`. Định nghĩa riêng là chuỗi JSON gồm `pattern`, `start_delimiter`, `end_delimiter`, `must_match`, `must_not_match`; metadata, ID và row version không nằm trong bản lưu. Khi cập nhật, script đọc lại ID/phiên bản và kiểm tra cấu hình chưa bị đổi đồng thời. Tạo mẫu dùng API bulk create, xác nhận đúng tên và ID trước request tiếp theo. Regex có thể chứa ví dụ nhạy cảm nên không xuất hiện trong Git, kế hoạch hoặc lỗi ghi.

API không có dry run hoặc xuất bản mẫu. Nếu mẫu đã xuất bản bị mất, kế hoạch dừng trước mọi lần ghi: chuẩn bị nguồn cho bản nháp `state: unpublished`, `push_protection_enabled: false`, tạo bằng nhóm `custom_patterns`, chạy thử và xuất bản trên web rồi xác nhận lại nguồn. Không gửi trường trạng thái hoặc slug vào API cập nhật. Đổi push protection dùng `pattern_settings` cấp tổ chức. Phần này giữ tên token type nhà cung cấp hoặc slug mẫu tùy chỉnh, explicit setting và giá trị kế thừa enterprise để đối chiếu; không lưu số liệu cảnh báo hoặc ID `cp_*`. Phiên bản chính sách và mẫu được đọc lại ngay trước ghi; chính sách đổi đồng thời hoặc kế thừa không khớp thì dừng. API không hỗ trợ `not-set` cho mẫu tùy chỉnh. Xem [hợp đồng mẫu](https://docs.github.com/en/rest/secret-scanning/custom-patterns), [chính sách push protection](https://docs.github.com/en/rest/secret-scanning/push-protection) và [giới hạn xuất bản](https://github.blog/changelog/2026-07-13-create-and-manage-secret-scanning-custom-patterns-via-rest-api/).

`private_registries` giữ tên để đối chiếu, `definition_source`, `credential_source`, visibility và tên repository được chọn. Định nghĩa riêng là chuỗi JSON chứa loại registry, URL, username, `replaces_base`, `auth_type` và các tham số OIDC theo phương thức. Script đọc từng cấu hình, không đoán URL bị ẩn; metadata và encrypted secret không được nhập. Repository ID được đổi thành tên trong nguồn và giải ID mới khi áp dụng. Tạo bằng OIDC gửi cấu hình đã lưu, không gửi secret; thay đổi `auth_type` của registry đang có cần xử lý riêng vì API không cho đổi.

Khi tạo lại registry token/password hoặc đổi thông tin kết nối/xác thực, quản trị bổ sung chuỗi JSON gồm `encrypted_value` và `key_id` dưới khóa `credential_source` trong tệp riêng. Mã hóa secret bằng sealed box LibSodium với khóa lấy từ `GET /orgs/TOANQUYNHLLC/private-registries/public-key`, theo [hướng dẫn mã hóa của GitHub](https://docs.github.com/en/rest/guides/encrypting-secrets-for-the-rest-api). Script kiểm tra key ID khi lập kế hoạch và ngay trước ghi; khóa đã đổi thì cần mã hóa lại. Không lưu ciphertext/key ID trong Git; không tự nhập lại hoặc suy đoán mật khẩu/token bị API ẩn. Cập nhật riêng visibility/danh sách repository giữ secret hiện có. Đọc lại chỉ xác nhận cấu hình, không chứng minh credentials đăng nhập registry thành công.

API tạo registry không nhận tên: GitHub cấp tên và script tìm lại tài nguyên theo loại/URL, không tự tạo bản trùng. Phản hồi phải khớp cấu hình gửi trước bước tiếp theo. Các mục ngoài nguồn được giữ; không tự xóa registry. Cần quyền Organization private registries phù hợp; xem [hợp đồng registry](https://docs.github.com/en/rest/private-registries/organization-configurations).

## 🌐 GIỚI HẠN VÀ CƠ CHẾ RIÊNG

| Nhóm                                                  | Phạm vi xử lý                                                                                                                                               |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `web_settings`                                        | Chỉ đối chiếu; gồm yêu cầu 2FA, tên nhánh mặc định tổ chức, quyền thành viên và cờ bảo mật REST không có hợp đồng ghi trong script                          |
| Actions bị tắt                                        | Chỉ lưu trường API trả; không suy đoán `allowed_actions` bị ẩn hoặc danh sách selected chưa đọc được                                                        |
| GitHub Apps                                           | Chỉ lưu tên đã cài trong `installed_apps`; cài/gỡ và quyền installation dùng luồng riêng                                                                    |
| Ruleset, team, nhãn                                   | Bản đang cài nằm trong `collections`; nguồn chính sách riêng vẫn ở [ruleset](../rulesets/README.md), [team](../MAINTAINERS.md), [labels.yml](../labels.yml) |
| Codespaces access, dry run/xuất bản mẫu               | API Codespaces access chỉ có ghi chính sách, không có đọc tương ứng; dry run và xuất bản mẫu cần web, không báo đã sao lưu tự động                          |
| OAuth, billing, SSO, credentials, secrets, deploy key | Cơ chế quản trị riêng; nguồn không lưu giá trị bí mật                                                                                                       |

`--repo <tên>` chỉ dùng với `files`, `settings`, `rulesets`, `team`, `labels`; tên không trống, không có khoảng trắng hoặc owner. Lệnh cấp tổ chức, `preview`, `import-settings`, `local-settings`, `settings-audit` từ chối tùy chọn này. `--discussions` chỉ dùng với `settings`; `preview`, `import-settings` và `settings-audit` không nhận `--apply`. `--complete` chỉ dùng với `import-settings`; `--only` chỉ dùng với `local-settings`. Tùy chọn được kiểm tra trước đăng nhập và API để giữ đúng phạm vi.

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
- [Custom properties](https://docs.github.com/en/rest/orgs/custom-properties)
- [Environments](https://docs.github.com/en/rest/deployments/environments)
- [Actions variables](https://docs.github.com/en/rest/actions/variables)
- [Organization webhooks](https://docs.github.com/en/rest/orgs/webhooks)
- [Repository webhooks](https://docs.github.com/en/rest/repos/webhooks)
- [GitHub Pages](https://docs.github.com/en/rest/pages/pages)
- [Security managers](https://docs.github.com/en/rest/orgs/security-managers)
- [OpenAPI chính thức của GitHub](https://github.com/github/rest-api-description)
- [Network configurations](https://docs.github.com/en/rest/orgs/network-configurations)
- [Organization roles](https://docs.github.com/en/rest/orgs/organization-roles)
- [GitHub GraphQL](https://docs.github.com/en/graphql)
