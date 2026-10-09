# 00000002. XUỐNG DÒNG LF; CHỈ LOẠI TỆP BẮT BUỘC MỚI DÙNG CRLF

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Người đóng góp dùng nhiều hệ điều hành, còn CI và Dev Container chạy trên Linux. Quy tắc xuống dòng cần phù hợp với công cụ xử lý từng loại tệp và cho kết quả giống nhau trên các máy.

## ✅ QUYẾT ĐỊNH

Tệp văn bản mặc định dùng **UTF-8 và LF**. `.gitattributes` khai báo `* text=auto eol=lf`; `.editorconfig` khai báo `end_of_line = lf`.

Các định dạng bắt buộc dùng CRLF gồm batch script, Visual C++ 6, MIME, iCalendar, vCard, CSV và dự án Visual Studio. Dự án Visual Studio dùng BOM UTF-8; registry và INF dùng UTF-16 LE có BOM khi checkout. CSV và email giữ khoảng trắng cuối dòng vì đó là dữ liệu.

Danh sách ngoại lệ phải khớp giữa `.editorconfig`, `.gitattributes` và `scripts/validation/formatting.py`.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Tự chuyển xuống dòng theo hệ điều hành khiến kết quả phụ thuộc cấu hình máy. CRLF cho mọi tệp không phù hợp với shell trên Linux; LF cho mọi tệp không đáp ứng định dạng bắt buộc CRLF.

## ⚖️ HỆ QUẢ

Validator kiểm tra xuống dòng, mã hóa và danh sách ngoại lệ. Tệp `.reg`, `.inf` được lưu UTF-8 trong Git để đọc diff và chuyển sang UTF-16 LE khi checkout bằng `working-tree-encoding`.
