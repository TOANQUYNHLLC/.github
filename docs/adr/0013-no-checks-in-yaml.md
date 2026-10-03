# 0013. MỌI KIỂM TRA LÀ TỆP RIÊNG, KHÔNG VIẾT TRỰC TIẾP TRONG YAML

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03
- **Điều chỉnh:** [0012](0012-python-checks-camel-case.md) — bỏ ngoại lệ cho lệnh riêng của từng ngôn ngữ trong workflow mẫu

## 📌 BỐI CẢNH

ADR 0012 cho phép workflow mẫu viết thẳng lệnh riêng của từng ngôn ngữ, nên `go-ci.yml` vẫn chứa đoạn shell kiểm tra `gofmt` và `python-ci.yml` chứa các nhánh `if` nhiều dòng. Kiểm tra viết trong YAML không chạy được tại máy, không có test và dễ lệch giữa các bản chép.

## ✅ QUYẾT ĐỊNH

- Mọi kiểm tra luôn viết thành tệp riêng trong `scripts/` (ưu tiên Python), **không** viết trực tiếp trong tệp `.yml`, `.yaml` — áp dụng cho cả `.github/workflows/` và `workflow-templates/`.
- Mỗi bước workflow gọi đúng một lệnh: cấm `run: |`, `run: >`, `shell: python` (hoặc ngôn ngữ khác) và mã nhúng kiểu `python -c`, `node -e`, `bash -c`. Điều kiện chạy dùng `if:` của GitHub Actions (ví dụ `hashFiles('tests/**') != ''`) thay cho `if` trong shell.
- Workflow mẫu gọi script của tổ chức (checkout `TOANQUYNHLLC/.github` vào `.org/`), ví dụ `scripts/check-gofmt.py`.
- `scripts/validate.py` kiểm tra mọi tệp workflow, kể cả workflow mẫu.

## ⚖️ HỆ QUẢ

- Kiểm tra nào cũng chạy được tại máy và có thể viết test; workflow chỉ còn cài công cụ và gọi lệnh.
- Workflow mẫu `go-ci.yml` cần quyền đọc repository `TOANQUYNHLLC/.github` (công khai) như các workflow mẫu kiểm tra khác.
