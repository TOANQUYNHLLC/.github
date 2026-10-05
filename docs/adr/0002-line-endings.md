# 0002. XUỐNG DÒNG LF; CHỈ LOẠI TỆP BẮT BUỘC MỚI DÙNG CRLF

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Người đóng góp dùng cả Windows và macOS; CI chạy trên Linux. Shell script xuống dòng CRLF không chạy được trên Linux, trong khi một số định dạng lại bắt buộc CRLF.

## ✅ QUYẾT ĐỊNH

- Mặc định **LF**, mã hóa **UTF-8** cho mọi tệp văn bản (`* text=auto eol=lf` trong `.gitattributes`, `end_of_line = lf` trong `.editorconfig`).
- **CRLF** chỉ cho tệp bắt buộc: batch script (`.bat`, `.cmd`), Visual C++ 6 (`.dsp`, `.dsw`), chuẩn MIME/iCalendar/vCard/CSV, dự án Visual Studio (kèm BOM UTF-8), registry/INF (UTF-16 LE có BOM).
- CSV và email giữ khoảng trắng cuối dòng vì đó là dữ liệu.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Để git tự chuyển theo hệ điều hành** (`core.autocrlf`): kết quả phụ thuộc cấu hình từng máy, cùng một tệp có thể vào repository với hai kiểu xuống dòng.
- **CRLF cho mọi tệp**: shell script không chạy được trên Linux (CI, Dev Container).
- **LF cho mọi tệp, kể cả batch script, dự án Visual Studio**: các định dạng đó bắt buộc CRLF; không chọn.

## ⚖️ HỆ QUẢ

- Danh sách đuôi tệp nằm ở `.editorconfig`, `.gitattributes` và `scripts/validation/formatting.py`; `validate.py` kiểm tra ba nơi khớp nhau.
- `.reg`, `.inf` lưu UTF-8 trong repository (diff đọc được) và checkout ra UTF-16 LE nhờ `working-tree-encoding`.
