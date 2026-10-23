# 00000009. KIỂM TRA TRONG SCRIPTS/, TIỆN ÍCH TRONG SHELL/; ƯU TIÊN PYTHON, CHẠY ĐƯỢC TẠI MÁY

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-23

## 📌 BỐI CẢNH

Người đóng góp cần chạy cùng logic kiểm tra tại máy và trên GitHub Actions. Workflow mẫu cần gọi được các kiểm tra dùng chung mà không nhân bản mã xử lý.

## ✅ QUYẾT ĐỊNH

Logic kiểm tra đặt trong `scripts/`, ưu tiên Python. Script dùng ngôn ngữ khác ghi `Không viết bằng Python vì: <lý do>` trong 10 dòng đầu. Tiện ích Git dùng shell nằm trong `shell/`, có lệnh Makefile và tests phù hợp.

Workflow điều phối các lệnh: mỗi bước gọi một lệnh, điều kiện dùng `if:`. Không nhúng kiểm tra bằng `run: |`, `run: >`, `shell: python`, `python -c`, `node -e` hoặc `bash -c`. Dữ liệu sự kiện được truyền qua biến môi trường.

`scripts/check.py` khai báo các nhóm `content`, `format`, `lint`, `conventions`, `audit`; các workflow gọi nhóm hoặc script tương ứng. Nhóm `audit` chạy npm audit trên cây phụ thuộc tại máy. Dependency Review xét thay đổi phụ thuộc của PR và CodeQL phân tích mã nguồn trên GitHub Actions khi được bật. Workflow mẫu checkout `TOANQUYNHLLC/.github` vào `.org/` theo tag phát hành mới nhất trong `CHANGELOG.md` rồi gọi script tổ chức; tag được Protect Release Tags và Release bất biến bảo vệ.

Nguồn của quyết định: [scripts/check.py](../../scripts/check.py), [Makefile](../../Makefile), [.github/workflows/validate.yml](../../.github/workflows/validate.yml), [.github/workflows/dependency-review.yml](../../.github/workflows/dependency-review.yml).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Script độc lập có thể gọi, kiểm thử và chẩn đoán tại máy. YAML chỉ giữ phần điều phối. Shell phù hợp với các tiện ích Git đơn giản; yêu cầu nêu lý do giúp lựa chọn ngôn ngữ có căn cứ.

## ⚖️ HỆ QUẢ

Kiểm tra PR mới phải thuộc một nhóm trong bộ điều phối và được liệt kê tại README. ShellCheck kiểm tra shell script. Các workflow dùng script tổ chức chỉ chạy mã đã phát hành; mã chưa phát hành trên nhánh chính không tự chạy ở repository khác. `checkTemplateScriptRefs()` đối chiếu `ref` với phiên bản mới nhất.
