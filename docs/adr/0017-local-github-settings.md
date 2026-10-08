# 0017. NGUỒN CÀI ĐẶT GITHUB Ở LOCAL

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-07

## 📌 BỐI CẢNH

Giá trị cố định trong Python không phản ánh đầy đủ các cài đặt GitHub có endpoint riêng. Cần nhập trạng thái hiện tại về local và dùng cùng nguồn đó khi áp dụng lại, đồng thời phân biệt mục có API ghi với mục chỉ đối chiếu.

## ✅ QUYẾT ĐỊNH

- Dùng `github-settings.json` làm nguồn cài đặt tổ chức và từng repository. Các module Python khai báo hợp đồng API và kiểm tra dữ liệu, không duy trì một bản giá trị hồ sơ riêng.
- Nhập chỉ ghi local, lọc trường theo danh sách cho phép và giữ giá trị `false`. Phần chính sách chung `repository_defaults` được giữ riêng khỏi trạng thái từng repository.
- Endpoint chưa đọc được được đánh dấu, không dùng dữ liệu cũ thay thế. Xác minh mọi phạm vi trước khi ghi; đọc lại sau khi áp dụng.
- Chỉ áp dụng tài nguyên và trường có hợp đồng được hỗ trợ. Mục chỉ đọc được giữ để đối chiếu; quyền, giới hạn gói và tài nguyên cần cơ chế riêng được mô tả rõ.
- Nhóm runner và liên kết cấu hình bảo mật lưu tên thay cho ID; ID chỉ được giải từ API tại thời điểm áp dụng. Cấu hình OIDC chỉ lưu trường có thể ghi, bỏ subject prefix do GitHub sinh. Danh sách Apps chỉ phục vụ đối chiếu.
- Ruleset, team, nhãn và workflow tiếp tục dùng nguồn và cơ chế hiện có.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- Giữ giá trị trong Python: việc nhập khó tách dữ liệu khỏi hành vi và không bao quát endpoint riêng.
- Lưu toàn bộ phản hồi API: có metadata, dữ liệu nhạy cảm và trường không được chấp nhận khi ghi.
- Dùng phiên đăng nhập trình duyệt để tự sửa mọi trang Settings: phụ thuộc biểu mẫu nội bộ, không phải hợp đồng API ổn định.

## ⚖️ HỆ QUẢ

Người quản trị có thể kiểm tra diff cài đặt và áp dụng các phần được hỗ trợ từ local. Đây không phải bản sao lưu toàn bộ tài khoản GitHub; các thao tác API riêng lẻ không tạo transaction và vẫn chịu giới hạn quyền, gói dịch vụ.
