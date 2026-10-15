# 00000013. MỖI THAY ĐỔI SỬA LUÔN MỌI CHỖ LIÊN QUAN; TÀI LIỆU KHỚP VỚI CODE

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-08

## 📌 BỐI CẢNH

Mã nguồn, cấu hình, tests, biểu mẫu và tài liệu cùng mô tả bộ tài nguyên. Một thay đổi chỉ sử dụng được khi các nơi liên quan thống nhất tên, đường dẫn và hành vi.

## ✅ QUYẾT ĐỊNH

Mỗi thay đổi bao gồm các nơi gọi, tests, cấu hình, danh sách đối chiếu, ruleset, biểu mẫu, workflow mẫu, tài liệu, docstring và chú thích có liên quan. Tìm trong toàn repository bằng `git grep` theo tên và từ khóa của phạm vi sửa.

README cung cấp điểm bắt đầu và danh mục tài nguyên. Hướng dẫn chuyên đề mô tả cách vận hành, điều kiện và giới hạn. Mỗi ADR trình bày một quyết định hiện hành cùng lý do và hệ quả. Tài liệu phải dùng độc lập, không kể lại diễn biến phát triển hoặc lưu báo cáo kiểm tra.

`CHANGELOG.md` phục vụ chuẩn bị nội dung phiên bản theo [ADR 00000012](00000012-monthly-releases.md). Git lưu lịch sử mã nguồn; GitHub Releases lưu nội dung các bản đã công bố.

`checkDocsMatchCode()` đối chiếu lệnh Makefile, đường dẫn và hàm được nhắc trong Markdown; README liệt kê đủ lệnh, scripts, tiện ích shell và workflows.

`checkAdrIndex()` đối chiếu dãy mã liên tục, mã trong tiêu đề và mục lục ADR; mỗi hàng phải trỏ đúng tệp, không thiếu, thừa, trùng hoặc lệch thứ tự.

Nguồn của quyết định: [scripts/validation/docs.py](../../scripts/validation/docs.py), [specs/jobs-guideline.md](../../specs/jobs-guideline.md), [AGENTS.md](../../AGENTS.md).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Cập nhật cùng phạm vi tránh trạng thái code và tài liệu mô tả hai cách sử dụng khác nhau. Kiểm tra tự động bắt các tham chiếu có cấu trúc; việc đọc nội dung vẫn cần thiết để đánh giá ý nghĩa và tính đầy đủ.

## ⚖️ HỆ QUẢ

Chỉ hoàn tất khi nguồn, tests, ví dụ và hướng dẫn thống nhất. Bằng chứng kiểm thử, giới hạn xác minh và số đo được trình bày trong PR hoặc bàn giao, không thêm vào tài liệu sử dụng. Thông tin có một nơi mô tả chính và được liên kết từ các nơi khác.
