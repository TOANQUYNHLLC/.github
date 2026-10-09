# 00000009. KIỂM TRA TRONG SCRIPTS/, TIỆN ÍCH TRONG SHELL/; ƯU TIÊN PYTHON, CHẠY ĐƯỢC TẠI MÁY

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Kiểm tra cần chạy tại máy và trên GitHub Actions bằng cùng logic. Workflow mẫu cần dùng quy ước của tổ chức; tiện ích Git tại máy cần được kiểm thử độc lập.

## ✅ QUYẾT ĐỊNH

Mọi kiểm tra đặt trong `scripts/`, ưu tiên Python. Script dùng ngôn ngữ khác phải có dòng `Không viết bằng Python vì: <lý do>` trong 10 dòng đầu theo phạm vi validator kiểm tra.

Tiện ích phát triển đặt trong `shell/`, có lệnh Makefile và test tương ứng; ShellCheck kiểm tra shell script.

Workflow chỉ điều phối: mỗi bước gọi một lệnh, điều kiện dùng `if:`. Không nhúng kiểm tra bằng `run: |`, `run: >`, `shell: python`, `python -c`, `node -e` hoặc `bash -c`.

`scripts/check.py` khai báo các nhóm `content`, `format`, `lint`, `conventions`, `audit`. `make check` và workflow của repository gọi cùng nguồn.

Workflow mẫu checkout `TOANQUYNHLLC/.github` vào `.org/` và gọi script dùng chung của tổ chức.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Kiểm tra nhúng trong YAML khó chạy và kiểm thử tại máy. Chép logic vào từng workflow mẫu tạo nhiều bản phải đồng bộ. Cấm mọi ngôn ngữ ngoài Python không phù hợp với tiện ích mà shell xử lý tốt hơn.

## ⚖️ HỆ QUẢ

Kiểm tra tại máy và CI dùng cùng logic, trừ CodeQL chạy trên GitHub. Workflow mẫu phụ thuộc nhánh chính được bảo vệ của repository tổ chức. Script mới cần được gọi, kiểm thử và liệt kê trong README; tệp cấu hình như `eslint.config.js` không phải script kiểm tra.
