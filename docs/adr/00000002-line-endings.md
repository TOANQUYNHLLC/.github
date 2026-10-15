# 00000002. XUỐNG DÒNG LF; CHỈ LOẠI TỆP BẮT BUỘC MỚI DÙNG CRLF

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Tệp phải được đọc và xử lý nhất quán trên các hệ điều hành. Shell trên Linux và một số định dạng Windows có yêu cầu khác nhau về xuống dòng và mã hóa.

## ✅ QUYẾT ĐỊNH

Tệp văn bản mặc định dùng UTF-8, LF và ký tự xuống dòng cuối tệp. Git khai báo `* text=auto eol=lf`; editor dùng `end_of_line = lf`.

Batch script, Visual C++ 6, MIME, iCalendar, vCard, CSV và dự án Visual Studio dùng CRLF theo danh sách trong `.editorconfig` và `.gitattributes`. Dự án Visual Studio dùng BOM UTF-8. Tệp registry và INF được lưu UTF-8 trong Git, checkout thành UTF-16 LE có BOM qua `working-tree-encoding`.

CSV và email giữ khoảng trắng cuối dòng khi khoảng trắng là dữ liệu. Danh sách ngoại lệ phải khớp với `scripts/validation/formatting.py`.

Nguồn của quyết định: [.editorconfig](../../.editorconfig), [.gitattributes](../../.gitattributes), [scripts/validation/formatting.py](../../scripts/validation/formatting.py).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

LF làm mặc định giữ kết quả độc lập với hệ điều hành của người đóng góp. Khai báo ngoại lệ theo loại tệp đáp ứng yêu cầu công cụ và cho phép Git hiển thị diff văn bản có ích.

## ⚖️ HỆ QUẢ

Validator kiểm tra mã hóa, xuống dòng và tính thống nhất của các ngoại lệ. Khi bổ sung định dạng, cập nhật các nguồn liên quan trong cùng thay đổi; không áp dụng chuyển đổi xuống dòng hàng loạt ngoài phạm vi cần thiết.
