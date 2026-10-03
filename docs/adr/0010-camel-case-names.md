# 0010. TÊN HÀM, THAM SỐ, BIẾN CAMELCASE TIẾNG ANH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Script do nhiều người và công cụ AI cùng viết; tên hàm, biến lẫn nhiều kiểu (snake_case, tiếng Việt không dấu) khó đọc và khó tìm.

## ✅ QUYẾT ĐỊNH

- Tên hàm, tham số và biến viết **tiếng Anh, camelCase** (`checkLinks`, `syncSettings`, `changelogPath`; test `testBrokenLink`). Hằng số giữ `UPPER_CASE`, lớp giữ `PascalCase`.
- `validate.py` đọc cây cú pháp (`ast`) của mọi tệp Python: báo lỗi khi tên hàm, tham số không phải camelCase hoặc tên biến dùng snake_case.

## ⚖️ HỆ QUẢ

- Khác PEP 8 (snake_case); ruff với cấu hình chuẩn không kiểm tra tên nên không xung đột.
- Phương thức có tên do thư viện quy định (ví dụ `do_HEAD` của `http.server`, `http_open` của `urllib`) được gán qua thuộc tính hoặc `type()` thay vì định nghĩa trực tiếp.
