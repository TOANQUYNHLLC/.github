# 00000015. XÁC MINH KẾT QUẢ ĐỒNG BỘ GITHUB

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-10-08

## 📌 BỐI CẢNH

Phản hồi ghi thành công chưa chứng minh GitHub khớp nguồn. Đồng bộ cần xác minh danh tính, trạng thái sau ghi và thể hiện rõ tài nguyên chưa hoàn tất.

## ✅ QUYẾT ĐỊNH

Cài đặt xác minh danh tính tổ chức hoặc repository theo endpoint, không phân biệt hoa/thường. Thiếu danh tính hoặc chuyển hướng tới tài nguyên khác dừng lệnh.

Các trường cài đặt chính do `settings` và `org-settings` ghi được đọc lại, kiểm tra kiểu và đối chiếu trước khi báo thành công. Metadata đã xác nhận được dùng cho bước phụ thuộc; lỗi xác nhận dừng lệnh.

Team được kiểm tra cấu hình trước API và xác nhận thông tin, quan hệ cha–con sau ghi. Maintainer phải có membership phù hợp và `active`; quyền repository phải bằng hoặc cao hơn quyền chuẩn yêu cầu. Lời mời mới `pending` được tổng hợp và trả mã lỗi sau khi xử lý các team còn lại.

Ruleset được đọc và kiểm tra đầy đủ trước lần ghi đầu tiên trong từng phạm vi. Sau ghi, script xác minh ID phản hồi và đọc lại theo ID. Các trường tập hợp được đối chiếu theo nội dung; dữ liệu nguồn và payload giữ nguyên. Lỗi ghi hoặc xác nhận được tổng hợp sau khi thử các ruleset còn lại.

GraphQL dùng để đối chiếu, không thay thao tác áp dụng qua REST. Lỗi đọc hoặc giới hạn gói trả mã lỗi; ruleset cấp tổ chức cần gói hỗ trợ theo [ADR 00000004](00000004-protect-main.md).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Chỉ kiểm tra mã phản hồi không xác minh trạng thái thực tế. Coi việc đối chiếu GraphQL là đã áp dụng không đáp ứng yêu cầu ghi cấu hình. Coi lời mời đang chờ là thành viên hoạt động không phản ánh quyền thực tế.

## ⚖️ HỆ QUẢ

Xác nhận cần thêm request. Các lần ghi thành công không tự hoàn tác khi bước sau thất bại. Mã lỗi thể hiện còn thao tác chưa hoàn tất, kể cả khi một phần cấu hình đã được áp dụng.
