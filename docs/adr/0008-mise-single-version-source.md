# 0008. MISE.TOML LÀ NGUỒN PHIÊN BẢN CÔNG CỤ DUY NHẤT

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Phiên bản công cụ ghi ở nhiều nơi (CI, Dev Container, máy cục bộ) dễ lệch nhau, làm máy cục bộ và CI định dạng, kiểm tra khác nhau.

## ✅ QUYẾT ĐỊNH

- `mise.toml` là nơi duy nhất khai báo phiên bản Python, ruff, ShellCheck, actionlint.
- Node.js chỉ khai báo trong `.nvmrc` (`actions/setup-node` và mise cùng đọc); thư viện Node.js chỉ trong `package.json`.
- CI cài công cụ bằng `jdx/mise-action`; Dev Container cài mise rồi chạy `mise install` (Python lấy từ image).
- `validate.py` báo lỗi khi workflow hoặc script tự ghi phiên bản ruff, ShellCheck, actionlint, hoặc khi công cụ trong `mise.toml` không có trong danh sách kiểm tra bản mới.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Ghi phiên bản ở từng nơi dùng** (CI `pip install ruff==…`, `go install actionlint@…`, script Dev Container): nâng ở một nơi dễ quên nơi khác, máy cục bộ và CI định dạng khác nhau.
- **Node.js trong cả `mise.toml` và `.nvmrc`**: hai nguồn cho một phiên bản; chọn `.nvmrc` vì `actions/setup-node` và mise cùng đọc được.

## ⚖️ HỆ QUẢ

- Nâng phiên bản: sửa một dòng trong `mise.toml` (hoặc `.nvmrc`).
- Tệp phiên bản mà `org-setup.py files` cấp cho repository khác lấy từ cùng nguồn: `.python-version` sinh từ `python` trong `mise.toml`, `.nvmrc` chép từ `.nvmrc`.
- Dependabot chưa cập nhật `mise.toml`: `scripts/check-tool-versions.py` (`make versions`) báo khi có bản mới — workflow `links.yml` chạy hằng tuần, hook sau `git pull` chạy tại máy.
