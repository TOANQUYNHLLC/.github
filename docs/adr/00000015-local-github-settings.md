# 00000015. NGUỒN CÀI ĐẶT GITHUB Ở LOCAL

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-23

## 📌 BỐI CẢNH

Cài đặt GitHub gồm hồ sơ, chính sách và tài nguyên có API riêng. Nguồn local cần cho phép đọc diff và áp dụng có kiểm chứng, đồng thời thể hiện dữ liệu chưa đọc được và mục chỉ đối chiếu.

## ✅ QUYẾT ĐỊNH

`github-settings.json` là nguồn khôi phục cài đặt tổ chức và repository. `configuration.py`, `resources.py`, `catalog.py`, `enterprise.py`, `branches.py`, `patterns.py`, `registries.py`, `policies.py`, `hosted.py` trong `scripts/orgsetup/` khai báo hợp đồng API và kiểm tra dữ liệu.

Nhập cài đặt chỉ ghi local, lọc theo trường cho phép, giữ giá trị `false` và giữ chính sách `repository_defaults`. Phần chưa đọc được ghi vào `unavailable`, không thay bằng giá trị đã lưu hoặc suy đoán.

Áp dụng xác minh mọi phạm vi trước khi ghi, chỉ ghi hợp đồng được hỗ trợ và đọc lại kết quả. Mục chỉ đọc được lưu để đối chiếu.

Cờ bảo mật mặc định có hợp đồng PATCH tổ chức nằm trong `settings`; cờ đặt trong `web_settings` được chuẩn hóa sang `settings` mà không đổi giá trị. Hai mục tiêu mâu thuẫn bị từ chối. API legacy đang được GitHub loại bỏ dần; cấu hình bảo mật hiện đại là nguồn ưu tiên khi gói/quyền cho phép. Trường API không còn trả được đánh dấu chưa biết, không suy đoán `false`.

`private_settings` tổ chức chứa tham chiếu cho trường hồ sơ riêng có API, hiện là `billing_email`. API trả trường thì nhập vào tệp riêng; không lưu giá trị trong Git hoặc kế hoạch. Mục được quản lý phải có giá trị riêng và API đối chiếu được trước ghi, đọc lại sau PATCH. Hợp đồng này không tự xử lý gói hoặc phương thức thanh toán.

`security_options` của repository giữ reviewers delegated bypass bằng ID tham chiếu team/role hiện có và mode; metadata cấu hình bị lọc khi nhập. Cờ bật feature và options được gửi cùng PATCH, đọc lại để xác nhận; options của feature tắt không được báo đã áp dụng. Không tạo lại principal hoặc đoán ID. Reviewer options trong định nghĩa bảo mật cũng được chuẩn hóa theo mode mặc định và nội dung tập hợp để không phụ thuộc ID cấu hình cũ.

Nguồn đã nhập và kiểm tra có thể dùng trực tiếp để khôi phục sau nâng cấp gói, trong phạm vi quyền và tính năng API cho phép. Nhập lại cập nhật nguồn theo trạng thái web; `--complete` bổ sung dữ liệu chưa có, gồm khóa lồng trong endpoint/tài nguyên đã quản lý; giữ giá trị local, `null` và danh sách rỗng, không thêm tài nguyên vào danh sách đã quản lý. Nâng cấp không tự đổi các giá trị tắt hoặc danh sách chọn rỗng trong nguồn. Lệnh audit đọc lại mọi nhóm được quản lý, kiểm tra phạm vi và dữ liệu chưa nhập; không coi `unavailable` rỗng là bằng chứng đã sao lưu toàn bộ trang Settings.

`collections` chứa ruleset đang cài, cấu trúc team và quyền repository, security managers, nhãn, autolinks, custom properties, environments, Pages, OIDC custom properties, variables, webhooks, bảo vệ nhánh kiểu cũ, cấu hình mạng, IP allow list, vai trò cho team, Actions policies, hosted runners, quyền truy cập Dependabot, mẫu secret scanning, chính sách push protection theo mẫu, private registries và định nghĩa bảo mật do tổ chức quản lý. Tài nguyên được tạo hoặc cập nhật theo nguồn, không xóa mục ngoài nguồn. API không có cập nhật autolink nên việc đổi cấu hình thay đúng prefix đã xác minh. Nhóm runner và liên kết bảo mật dùng tên; ID cấu hình mới được giải sau khi tạo, trước bước defaults/attach. Không sao chép định nghĩa bảo mật toàn cục do GitHub quản lý.

Giá trị variables, URL webhook, địa chỉ/tên IP allow list, regex tùy chỉnh và định nghĩa registry lưu bằng `localdata.py` ở tệp riêng ngoài repository, quyền `0600`; JSON trong Git chỉ chứa tham chiếu theo phạm vi. Tham chiếu mới không thay giá trị cũ để các bản nguồn trước vẫn khôi phục được. Xem trước chỉ đọc; áp dụng giải tham chiếu sau khi đã xác minh đủ dữ liệu cho mọi phạm vi. Shared secret webhook không xuất được qua API: tạo lại hoặc đổi events/trạng thái cần người quản trị cung cấp riêng; cập nhật qua endpoint cấu hình riêng giữ secret đang có. Không lưu secrets hoặc hồ sơ người dùng trong Git. Sao lưu tệp riêng cùng nguồn tương ứng là điều kiện khôi phục dữ liệu có tham chiếu.

Bảo vệ nhánh kiểu cũ giữ pattern và App ràng buộc của check, giải ID rule/repository mới khi áp dụng. Cấu hình mạng giải ID cấu hình mới, xác minh tài nguyên cloud ngoài GitHub trước ghi. Vai trò dùng tên và quyền để xác minh định nghĩa có sẵn; chỉ gán trực tiếp cho team. Không tự sao chép cấu hình kế thừa enterprise sang tổ chức. Bật thực thi IP được thực hiện sau các cập nhật khác; mutation GraphQL phải trả kết quả hợp lệ trước bước tiếp theo.

Mẫu secret scanning giữ định nghĩa ở tệp riêng, giải lại ID và phiên bản trước cập nhật; xuất bản và dry run cần giao diện web. Chính sách theo mẫu chỉ ghi override cấp tổ chức, không sửa giá trị kế thừa enterprise. Private registries giữ cấu hình xác thực ở tệp riêng và tên repository trong nguồn; OIDC không cần secret. Tạo lại registry dùng token/password cần sealed box LibSodium và khóa GitHub hiện tại do quản trị chuẩn bị; không thể nhập lại secret bị API ẩn. Tên do GitHub cấp được giải theo loại và URL sau tạo. Phản hồi API phải xác nhận tài nguyên trước bước ghi tiếp theo.

Actions policies nhập đầy đủ chi tiết do phạm vi sở hữu; không sao chép policy kế thừa. Điều kiện chọn repository và quyền Dependabot lưu tên, giải ID mới trước ghi. Dependabot khôi phục danh sách cấp quyền và default level đã lưu; `null` chỉ đối chiếu vì API không có reset tương ứng. Cache Actions lưu giới hạn dung lượng và thời gian giữ riêng với artifact/log retention. Nhóm runner lưu liên kết mạng bằng tên; thứ tự tạo mạng, nhóm và hosted runner bảo đảm ID được giải sau tạo. Hosted runner dùng danh mục image/size hiện tại, custom image cần được tạo sẵn. Pool chưa triển khai xong không được báo hoàn tất.

`--only` giới hạn thao tác vào nhóm người quản trị chọn rõ, gồm đọc lại xác nhận. Mục chưa đọc được thuộc nhóm được chọn vẫn chặn toàn bộ kế hoạch; các nhóm ngoài phạm vi không được ghi. Nguồn và audit đầy đủ giữ dấu chưa nhập, không báo bản sao lưu đầy đủ chỉ vì một nhóm áp dụng thành công.

`observed` chỉ chứa dữ liệu đối chiếu, gồm ruleset đọc qua GraphQL khi REST bị chặn và Repository policies nhập từ HTML trang Settings. Phần này không trở thành payload ghi: GraphQL không trả đủ tham số REST, bản chụp web không phải hợp đồng API. `unavailable` chặn áp dụng cho đến khi đã bổ sung và xác minh dữ liệu.

Repository policies được nhập riêng bằng `scripts/import-repository-policies.py`, hợp đồng trong `scripts/orgsetup/repopolicies.py`. Bản chụp ở `organization.observed.repository_policies` giữ danh tính policy, trạng thái, phạm vi, các actor và quy tắc đã đọc; bỏ metadata trang, hồ sơ và dữ liệu phiên. Regex và bản cấu hình khôi phục thủ công được lưu ngoài Git. `manual_settings.repository_policies` giữ trạng thái `pending` và tham chiếu; không tự xác nhận `verified` khi nhập. Nhập API giữ bản chụp web đến khi người quản trị nhập lại trang, không suy đoán trang đã được làm mới.

Trang Settings ngoài hợp đồng API được nhập bằng `scripts/import-web-settings.py`, bộ lọc và validator trong `scripts/orgsetup/websettings.py`. Chỉ nội dung panel và biểu mẫu được chuẩn hóa vào kho riêng, không giữ HTML hoặc dữ liệu phiên. Tham chiếu từng nhóm và bản kiểm kê trang ở `manual_settings`, chờ quản trị đối chiếu. Snapshot chỉ đọc của ruleset web trong `observed.web_rulesets` của từng phạm vi giữ cả `RepositoryMigration` không được REST nhận; không biến snapshot thành payload API, không bỏ actor và không tự chuyển nguồn chính sách `rulesets/`. Định danh chuỗi của dismissal restriction trên web lưu qua tham chiếu ngoài Git, không giả làm actor REST hoặc lưu hồ sơ trong nguồn. Nhập API giữ snapshot web và bản thủ công; trạng thái bị API ẩn vẫn chặn áp dụng API tương ứng. Các phần loại khỏi phạm vi, trang chưa đọc được và trạng thái động được ghi trong bản riêng, không thay bằng mặc định hoặc dấu hoàn tất. Danh tính, vai trò trực tiếp và lời mời được nhập riêng qua API vào bản thủ công ngoài Git; không lưu metadata hồ sơ và không gửi mutation membership khi nhập.

`pending_settings` khai báo trường cài đặt chính và nhóm API chưa đọc được bằng `null`; không suy đoán danh sách rỗng hoặc giá trị mặc định. Người quản trị có thể điền mục tiêu đúng hợp đồng khi cần. Nhập bổ sung giữ mục tiêu đã điền, nhập theo web cập nhật mục tiêu API khi đọc được; phần chưa biết được bỏ khi có dữ liệu thật. Chính sách cha local quyết định có giữ danh sách `selected`; không ghép danh sách web vào mục tiêu không chọn `selected`, không bỏ dấu thiếu khi API ẩn danh sách local đang cần. Mục tiêu pending không vượt kiểm tra quyền, danh tính, dữ liệu hoặc dấu `unavailable`.

`manual_settings` là danh mục nhóm cần quản trị xử lý riêng, chỉ giữ trạng thái và tham chiếu bản cấu hình ngoài Git. Không nhập secrets, hồ sơ người dùng hoặc thông tin thanh toán vào nguồn công khai. `pending`/`verified` cần bản cấu hình riêng; `verified` và `not_applicable` là xác nhận thủ công, không phải kết quả API. Import giữ phần này, không tự đánh dấu hoàn tất. Lệnh inventory đọc local không cần đăng nhập; audit và kết quả khôi phục đầy đủ báo các mục thủ công chưa đủ. Danh mục không bảo đảm bao phủ mọi trang web hoặc tính năng mới của GitHub.

`manual_settings.settings_pages` giữ tham chiếu bản kiểm kê mọi trang Settings, gồm mục chỉ đối chiếu, cấu hình runner bên ngoài và tính năng ngoài hợp đồng API. Inventory/audit kiểm tra nhóm bắt buộc bị bỏ, dữ liệu riêng của mọi tài nguyên tham chiếu, shared secret webhook, cấu trúc định nghĩa regex/registry và sealed box credentials registry; phương thức OIDC không yêu cầu credentials registry. Tham chiếu thủ công không miễn kiểm tra giá trị API cùng tên. Kiểm tra offline không xác minh khóa GitHub hiện tại hoặc giải mã credentials; kiểm tra nội dung trang và khả năng truy cập kho riêng vẫn do quản trị xác nhận.

`backup.py` đóng gói nguồn và các giá trị riêng được tham chiếu vào archive ngoài repository, quyền `0600`; không ghi đè gói đã có. Manifest giữ checksum từng tệp và danh sách phần chưa đủ. Gói chưa đủ vẫn lưu dữ liệu đã có, nhưng tạo và kiểm tra đều trả mã lỗi. Kiểm tra offline dùng dữ liệu trong gói, không phụ thuộc tệp riêng tại máy và không ghi GitHub. Checksum phát hiện dữ liệu thay đổi; không chứng minh nguồn gốc archive hoặc cài đặt trên GitHub đã đúng. Khôi phục trên cùng tổ chức cần kiểm tra gói, đối chiếu nguồn, dữ liệu riêng và quyền/gói, xử lý phần thủ công rồi audit trên GitHub; archive không chứa cấu hình bên ngoài chỉ được nhắc bằng tham chiếu.

Bản đọc để khôi phục được xuất offline từ archive đã kiểm tra bằng `settings-backup-export`. Tham chiếu riêng được giải từ dữ liệu trong gói, biến và regex giữ chuỗi, cấu hình JSON được giải để đọc; giá trị thiếu, trạng thái thủ công và dấu chưa đọc API vẫn được giữ. Tệp chứa dữ liệu riêng chỉ được ghi ngoài Git, quyền `0600`, không ghi đè. Bản đọc không phải payload API hoặc nguồn thay thế, không tự xác nhận khôi phục và không tải kho ngoài.

OIDC lưu trường có thể ghi; GitHub Apps chỉ lưu tên để đối chiếu. `rulesets/`, `teams.py`, `labels.yml` và workflow là nguồn chính sách riêng cho các lệnh thiết lập; không tự ghi đè bằng bản nhập. Khôi phục bằng `local-settings` dùng hiện trạng đã lưu, còn các lệnh riêng áp dụng chính sách dự án. Người quản trị thống nhất hai nguồn trước khi phối hợp.

Phạm vi và giới hạn trong [hướng dẫn cài đặt GitHub](../github-settings.md).

Nguồn của quyết định: [github-settings.json](../../github-settings.json), [scripts/orgsetup/configuration.py](../../scripts/orgsetup/configuration.py), [scripts/orgsetup/resources.py](../../scripts/orgsetup/resources.py), [scripts/orgsetup/catalog.py](../../scripts/orgsetup/catalog.py), [scripts/orgsetup/localdata.py](../../scripts/orgsetup/localdata.py), [scripts/orgsetup/backup.py](../../scripts/orgsetup/backup.py).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Giá trị hồ sơ trong Python trộn dữ liệu với hành vi. Lưu phản hồi API thô đưa metadata và trường không thể ghi vào nguồn. Tự thao tác qua biểu mẫu trình duyệt phụ thuộc giao diện thay vì hợp đồng API.

## ⚖️ HỆ QUẢ

Người quản trị kiểm tra diff sau khi nhập, chạy xem trước rồi mới áp dụng. Nguồn không phải bản sao toàn bộ tài khoản; không chứa secrets và không vượt quyền hoặc giới hạn gói. Ghi nhiều endpoint không phải transaction.
