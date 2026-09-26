# 0002. XUỐNG DÒNG LF; CHỈ LOẠI TỆP BẮT BUỘC MỚI DÙNG CRLF

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-09-26

## 📌 BỐI CẢNH

Người đóng góp dùng cả Windows và macOS; CI chạy trên Linux. Shell script xuống dòng CRLF không chạy được trên Linux, trong khi một số định dạng lại bắt buộc CRLF.

## ✅ QUYẾT ĐỊNH

- Mặc định **LF** cho mọi tệp văn bản (`* text=auto eol=lf` trong `.gitattributes`, `end_of_line = lf` trong `.editorconfig`).
- **CRLF** chỉ cho tệp bắt buộc: batch script (`.bat`, `.cmd`), Visual C++ 6 (`.dsp`, `.dsw`), chuẩn MIME/iCalendar/vCard/CSV, dự án Visual Studio (kèm BOM UTF-8), registry/INF (UTF-16 LE có BOM).
- CSV và email giữ khoảng trắng cuối dòng vì đó là dữ liệu.

## ⚖️ HỆ QUẢ

- Danh sách đuôi tệp nằm ở `.editorconfig`, `.gitattributes` và `scripts/validate.py`; script kiểm tra ba nơi phải khớp nhau.
- `.reg`, `.inf` lưu UTF-8 trong repository (diff đọc được) và checkout ra UTF-16 LE nhờ `working-tree-encoding`.
