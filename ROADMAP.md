# 🗺️ LỘ TRÌNH

Các hạng mục thiết lập và định hướng vận hành GitHub cho **CÔNG TY TNHH TOÀN QUỲNH**. Tài liệu mô tả công việc theo điều kiện áp dụng, không lưu danh sách hoàn thành hoặc nhật ký phát triển. Đề xuất được trao đổi qua Issue **✨ Đề xuất tính năng**.

## 🚧 THIẾT LẬP REPOSITORY ĐÍCH

Với repository cần dùng tài nguyên chung, người quản trị xem trước bằng `make org-preview`, rồi thực hiện các bước phù hợp với dự án:

| Phạm vi       | Cách thiết lập                                                                                                  |
| ------------- | --------------------------------------------------------------------------------------------------------------- |
| Tệp chung     | `python3 scripts/org-setup.py files --repo <tên>`; dùng `--apply` để mở PR thêm tệp thiếu, đánh giá và hợp nhất |
| Cài đặt       | `python3 scripts/org-setup.py settings --repo <tên>`; áp dụng cài đặt và bảo mật có hỗ trợ                      |
| Nhãn          | `python3 scripts/org-setup.py labels --repo <tên>`; đồng bộ nhãn trước khi dùng biểu mẫu và labeler             |
| Team          | `python3 scripts/org-setup.py team --repo <tên>`; kiểm tra quyền để `CODEOWNERS` có hiệu lực                    |
| Ruleset       | `python3 scripts/org-setup.py rulesets --repo <tên>`; áp dụng sau khi có workflow bắt buộc                      |
| Cài đặt local | Nhập bằng `make org-import`, kiểm tra diff và dùng `make org-settings-preview`                                  |

Các lệnh trên mặc định xem trước; `--apply` mới ghi. Workflow CI và CodeQL được chọn theo công nghệ từ [workflow-templates/](workflow-templates/). Tệp có nội dung riêng như `.env.example`, `PRIVACY.md` được chọn và chỉnh theo [mẫu tệp](repository-templates/README.md).

Repository riêng tư trên gói Free chịu giới hạn ruleset và tính năng bảo mật. Không coi tệp nguồn đã có là cấu hình đã được GitHub áp dụng; xác minh kết quả theo [hướng dẫn cài đặt](docs/github-settings.md).

## 🏢 CHÍNH SÁCH CẤP TỔ CHỨC

Nhãn mặc định cho repository tạo mới được quản lý trên **Organization settings → Repository → General → Repository labels** theo [labels.yml](labels.yml). Nhãn mặc định chỉ áp dụng cho repository tạo sau đó; repository đã có dùng lệnh đồng bộ nhãn.

Các mục chỉ quản lý trên web và tài nguyên ngoài phạm vi bộ nhập được liệt kê trong [cài đặt GitHub](docs/github-settings.md). Người quản trị đối chiếu quyền và gói dịch vụ trước khi triển khai.

## 💡 ĐỊNH HƯỚNG ÁP DỤNG

| Điều kiện                          | Việc cần xem xét                                                                                                        |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Dự án cần thảo luận                | Bật Discussions, chuẩn bị danh mục phù hợp và xác minh biểu mẫu                                                         |
| Tổ chức dùng gói hỗ trợ ruleset    | Áp dụng ruleset cấp tổ chức, xem xét phạm vi chồng lặp với cấp repository và cập nhật ADR nếu đổi chính sách            |
| Quản lý bảo mật bằng configuration | Chọn phạm vi mặc định và repository được gắn; xác minh tương thích giữa CodeQL default setup và workflow advanced setup |
| Cần quét bí mật nâng cao           | Đối chiếu quyền, gói GitHub Secret Protection và cấu hình mẫu tùy chỉnh, validity checks                                |

Quyết định áp dụng qua [GOVERNANCE.md](GOVERNANCE.md); tài liệu chỉ mô tả chính sách đã xác định và công việc có mục đích rõ ràng.

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
