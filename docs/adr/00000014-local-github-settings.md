# 00000014. NGUỒN CÀI ĐẶT GITHUB Ở LOCAL

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-07

## 📌 BỐI CẢNH

Cài đặt GitHub gồm hồ sơ, chính sách và tài nguyên có API riêng. Nguồn local cần cho phép đọc diff và áp dụng có kiểm chứng, đồng thời thể hiện dữ liệu chưa đọc được và mục chỉ đối chiếu.

## ✅ QUYẾT ĐỊNH

`github-settings.json` là nguồn cài đặt tổ chức và repository. `configuration.py` và `resources.py` trong `scripts/orgsetup/` khai báo hợp đồng API và kiểm tra dữ liệu.

Nhập cài đặt chỉ ghi local, lọc theo trường cho phép, giữ giá trị `false` và giữ chính sách `repository_defaults`. Dữ liệu chưa đọc được được đánh dấu trong `unavailable`, không thay bằng giá trị cũ hoặc suy đoán.

Áp dụng xác minh mọi phạm vi trước khi ghi, chỉ ghi hợp đồng được hỗ trợ và đọc lại kết quả. Mục chỉ đọc được lưu để đối chiếu.

Nhóm runner và liên kết cấu hình bảo mật lưu tên; script giải ID tại thời điểm lập kế hoạch. OIDC lưu trường có thể ghi; GitHub Apps chỉ lưu tên để đối chiếu. Ruleset, team, nhãn và workflow dùng nguồn riêng.

Phạm vi và giới hạn trong [hướng dẫn cài đặt GitHub](../github-settings.md).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Giá trị hồ sơ trong Python trộn dữ liệu với hành vi. Lưu phản hồi API thô đưa metadata và trường không thể ghi vào nguồn. Tự thao tác qua biểu mẫu trình duyệt phụ thuộc giao diện thay vì hợp đồng API.

## ⚖️ HỆ QUẢ

Người quản trị kiểm tra diff sau nhập và xem trước trước khi áp dụng. Nguồn không phải bản sao toàn bộ tài khoản; không chứa secrets và không vượt quyền hoặc giới hạn gói. Ghi nhiều endpoint không phải transaction.
