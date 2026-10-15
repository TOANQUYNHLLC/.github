---
applyTo: '**/*.md'
---

# 📝 HƯỚNG DẪN CHO TÀI LIỆU

Áp dụng cùng [`AGENTS.md`](../../AGENTS.md).

- Viết tiếng Việt dạng NFC, tiêu đề Markdown viết hoa; chữ trên badge dùng tiếng Anh, hoa đầu mỗi từ.
- Viết tài liệu như hướng dẫn sử dụng độc lập của dự án: chức năng, điều kiện thiết lập, cách vận hành và giới hạn hiện tại. Không kể lại quá trình dọn dẹp, di chuyển hoặc thay thế thành phần; không nối tiếp các mục thêm/sửa, nhật ký phát triển, báo cáo rà soát, log kiểm tra hoặc số đo thử nghiệm.
- README là điểm bắt đầu và danh mục tài nguyên; hướng dẫn chuyên đề mô tả vận hành; ADR trình bày quyết định cùng lý do. Thông tin chỉ có một nơi mô tả chính, các tài liệu khác liên kết tới nơi đó.
- Đối chiếu lệnh, đường dẫn, hàm, ví dụ và cấu hình với mã nguồn; cập nhật tài liệu trong cùng thay đổi khi hành vi thay đổi.
- Khi rà soát toàn bộ, đọc từng tệp trong danh mục, kể cả mẫu và hướng dẫn trong thư mục ẩn; kiểm tra cả nơi tham chiếu tới tệp đó. Phân biệt kết quả kiểm tra tại máy với trạng thái trên GitHub.
- Tên tệp tài liệu mới viết kebab-case tiếng Anh (`local-checks.md`), trừ tên GitHub quy định (`README.md`, `SECURITY.md`…).
- README liệt kê đủ lệnh Makefile, scripts và workflows. Giữ thông tin công ty, người liên hệ và bản quyền theo nguồn hiện có.
- Tệp cộng đồng dùng chung và biểu mẫu cần liên kết phù hợp với nơi hiển thị; biểu mẫu và nội dung Release dùng URL tuyệt đối.
- Mỗi chủ đề một ADR mô tả quyết định hiện hành; dãy mã liên tục từ `00000001`, không trùng, khớp tên tệp, tiêu đề và mục lục. Khi đổi quyết định hoặc chuẩn hóa mã, đồng bộ mọi nơi tham chiếu theo [`docs/adr/README.md`](../../docs/adr/README.md).
- `CHANGELOG.md` chỉ chuẩn bị nội dung dành cho người sử dụng khi phát hành; giữ cấu trúc mà `scripts/release.py` đọc.
- Kiểm tra cấu trúc tiêu đề, nội dung liên kết và văn bản thay thế của hình ảnh; áp dụng hướng dẫn trợ năng của dự án nếu có. Chạy `make check` trước khi bàn giao.
