# 0003. TÊN BRANCH BẰNG TIẾNG ANH, NỐI TỪ BẰNG DẤU GẠCH DƯỚI

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-09-26

## 📌 BỐI CẢNH

Tên branch tiếng Việt không dấu (ví dụ `chore/thong-nhat-quy-tac-dinh-dang`) khó đọc và dễ nhầm nghĩa; công cụ và tài liệu kỹ thuật chủ yếu dùng tiếng Anh.

## ✅ QUYẾT ĐỊNH

- Tên branch dạng `<tiền tố>/<mô_tả>`: tiền tố trong bảng của `CONTRIBUTING.md`; mô tả bằng **tiếng Anh**, chữ thường, các từ nối bằng **dấu gạch dưới**.
- Workflow `branch-name.yml` kiểm tra tự động, bỏ qua branch của Dependabot.

## ⚖️ HỆ QUẢ

- Tiền tố branch trong `CONTRIBUTING.md` và workflow phải khớp nhau; `scripts/validate.py` kiểm tra điều này.
- Branch tạo trước quy ước này không đổi tên lại.
