# 0015. SCRIPT TIỆN ÍCH CHO NGƯỜI PHÁT TRIỂN NẰM TRONG SHELL/

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-05
- **Điều chỉnh:** 0013 — phạm vi thư mục mà `checkDocsMatchCode()` đối chiếu

## 📌 BỐI CẢNH

`scripts/` chứa các kiểm tra mà `make check` và GitHub Actions chạy ([ADR 0009](0009-checks-as-scripts.md)). Ngoài kiểm tra, người phát triển cần lệnh tiện ích chạy tại máy, không thuộc nhóm kiểm tra nào: `make syncmain` về `main`, kéo code mới rồi xóa branch cục bộ đã hợp nhất. Pull Request hợp nhất bằng Squash tạo commit mới trên `main` nên `git branch -d` báo "not fully merged"; việc dọn branch chỉ nối các lệnh `git` và đọc kết quả từng dòng. [ADR 0013](0013-docs-match-code.md) chỉ đối chiếu tài liệu với `scripts/` và vài thư mục khác: script đặt ngoài các thư mục đó mà đổi tên hay bị xóa thì tài liệu nhắc tới nó không bị báo.

## ✅ QUYẾT ĐỊNH

- Script tiện ích cho người phát triển — không phải kiểm tra — đặt trong `shell/`, mỗi script có lệnh `make` gọi nó (`make syncmain` → `shell/sync-main.sh`). Kiểm tra vẫn đặt trong `scripts/` theo [ADR 0009](0009-checks-as-scripts.md).
- Script trong `shell/` theo [ADR 0009](0009-checks-as-scripts.md) như mọi script: ưu tiên Python; dùng shell thì ghi dòng `Không viết bằng Python vì: <lý do>`; ShellCheck kiểm tra; có test trong `scripts/test_*.py`.
- `checkDocsMatchCode()` mở rộng phạm vi của [ADR 0013](0013-docs-match-code.md):
    - Đường dẫn trong `shell/` và `.devcontainer/` được nhắc trong tài liệu Markdown phải có thật.
    - `README.md` liệt kê đủ script trong `shell/` như script trong `scripts/`.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Đặt script tiện ích trong `scripts/`**: lẫn với các kiểm tra mà ADR 0009 quy định, khó biết script nào thuộc `make check`.
- **Chỉ ghi lệnh trong `Makefile`**: lệnh nhiều bước, nhiều nhánh điều kiện trong `Makefile` không có test và không được ShellCheck kiểm tra.
- **Không đối chiếu `shell/` với tài liệu**: đổi tên, xóa script thì `README.md` vẫn nhắc tới script không còn.

## ⚖️ HỆ QUẢ

- Thêm script vào `shell/` thì thêm lệnh `make`, dòng trong bảng lệnh và mục cấu trúc của `README.md`, cùng test; `make check` báo khi thiếu.
- Repository khác không nhận script trong `shell/` — workflow mẫu chỉ gọi script trong `scripts/`.
