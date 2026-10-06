---
applyTo: '**/*.md'
---

# 📝 HƯỚNG DẪN CHO TÀI LIỆU

Áp dụng cùng [`AGENTS.md`](../../AGENTS.md).

- Viết tiếng Việt dạng NFC, tiêu đề Markdown viết hoa; chữ trên badge dùng tiếng Anh, hoa đầu mỗi từ.
- Tài liệu mô tả trạng thái hiện tại và đủ để dùng độc lập; không ghi nhật ký phát triển, báo cáo rà soát, log kiểm tra hoặc số đo thử nghiệm.
- Đối chiếu lệnh, đường dẫn, hàm, ví dụ và cấu hình với mã nguồn; cập nhật tài liệu trong cùng thay đổi khi hành vi thay đổi.
- README liệt kê đủ lệnh Makefile, scripts và workflows. Giữ thông tin công ty, người liên hệ và bản quyền theo nguồn hiện có.
- Tệp cộng đồng dùng chung và biểu mẫu cần liên kết phù hợp với nơi hiển thị; biểu mẫu và nội dung Release dùng URL tuyệt đối.
- ADR đã chấp nhận được giữ nguyên; khi đổi quyết định, thêm ADR mới và cập nhật trạng thái, mục lục theo [`docs/adr/README.md`](../../docs/adr/README.md).
- `CHANGELOG.md` chỉ chuẩn bị nội dung dành cho người sử dụng khi phát hành; giữ cấu trúc mà `scripts/release.py` đọc.
- Kiểm tra cấu trúc tiêu đề, nội dung liên kết và văn bản thay thế của hình ảnh; áp dụng hướng dẫn trợ năng của dự án nếu có. Chạy `make check` trước khi bàn giao.
