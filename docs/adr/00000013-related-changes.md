# 00000013. MỖI THAY ĐỔI SỬA LUÔN MỌI CHỖ LIÊN QUAN; TÀI LIỆU KHỚP VỚI CODE

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-08

## 📌 BỐI CẢNH

Code, tests, cấu hình, workflows và tài liệu cùng mô tả một hệ thống. Tên, đường dẫn và quy tắc dùng chung xuất hiện ở nhiều nơi; chúng phải thống nhất trong mỗi thay đổi.

## ✅ QUYẾT ĐỊNH

Mỗi thay đổi phải rà soát toàn repository và sửa các nơi liên quan trong cùng phạm vi: nơi gọi, test, cấu hình, danh sách đối chiếu, ruleset, biểu mẫu, workflow mẫu, tài liệu, docstring và chú thích. Tìm bằng `git grep` theo tên và từ khóa; không chỉ dựa vào kết quả kiểm tra.

README là điểm bắt đầu sử dụng; hướng dẫn chuyên đề mô tả cách vận hành; mỗi ADR mô tả một quyết định và lý do. Tài liệu trình bày hiện trạng thống nhất, không ghi chuỗi thêm/sửa, log phát triển, báo cáo rà soát hoặc số đo thử nghiệm. Không ghi số lượng dễ lỗi thời khi không cần.

`CHANGELOG.md` chỉ chứa nội dung phiên bản đang chuẩn bị. Git và GitHub Releases lưu lịch sử tương ứng.

`checkDocsMatchCode()` kiểm tra lệnh Makefile, đường dẫn và hàm được nhắc trong Markdown; README phải liệt kê đủ lệnh, scripts, tiện ích shell và workflows.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Sửa nơi gọi và tài liệu ở PR khác để lại trạng thái mâu thuẫn. Chỉ dựa vào người đánh giá dễ bỏ sót tham chiếu; kiểm tra tự động toàn bộ câu chữ không khả thi. Kết hợp đối chiếu tự động với rà soát nội dung đáp ứng cả hai nhu cầu.

## ⚖️ HỆ QUẢ

Chỉ hoàn tất khi mã nguồn, tests, ví dụ cấu hình và tài liệu thống nhất. PR phải phản ánh đủ các nơi liên quan; người đánh giá kiểm tra hành vi và những liên kết ngoài phạm vi validator.
