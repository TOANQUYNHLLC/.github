# 0008. MISE.TOML LÀ NGUỒN PHIÊN BẢN CÔNG CỤ DUY NHẤT

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Phiên bản công cụ ghi ở nhiều nơi (CI, Dev Container, máy cục bộ) dễ lệch nhau, làm máy cục bộ và CI định dạng, kiểm tra khác nhau.

## ✅ QUYẾT ĐỊNH

- `mise.toml` là nơi duy nhất khai báo phiên bản Python, ruff, ShellCheck, actionlint.
- Node.js chỉ khai báo trong `.nvmrc` (`actions/setup-node` và mise cùng đọc); `devEngines` của `package.json` nhắc lại đúng bản đó (cùng giá trị với `.nvmrc`): npm chặn Node.js khác bản này, và mise cũng đọc `devEngines` để chọn Node.js — ghi khoảng như `>=24` thì mise cài bản mới nhất, khác CI. Thư viện Node.js chỉ trong `package.json`.
- CI cài ruff, ShellCheck, actionlint bằng `jdx/mise-action` và Node.js bằng `actions/setup-node`; Dev Container cài mise rồi chạy `mise install` (Python lấy từ image).
- `validate.py` báo lỗi khi workflow hoặc script tự ghi phiên bản ruff, ShellCheck, actionlint; khi công cụ trong `mise.toml` không có trong danh sách kiểm tra bản mới; khi Node.js khai báo trong `mise.toml`; khi `devEngines` lệch `.nvmrc`.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Ghi phiên bản ở từng nơi dùng** (CI `pip install ruff==…`, `go install actionlint@…`, script Dev Container): nâng ở một nơi dễ quên nơi khác, máy cục bộ và CI định dạng khác nhau.
- **Node.js trong cả `mise.toml` và `.nvmrc`**: hai nguồn cho một phiên bản; chọn `.nvmrc` vì `actions/setup-node` và mise cùng đọc được.

## ⚖️ HỆ QUẢ

- Nâng phiên bản: sửa một dòng trong `mise.toml`; Node.js thì sửa `.nvmrc` cùng `devEngines` (`validate.py` báo khi quên).
- Phiên bản Python trong `mise.toml` áp dụng tại máy. Job CI chạy `python3` có sẵn của runner, có thể khác bản tại máy; script chỉ cần Python ≥ 3.11 (`scripts/check.py` chặn bản cũ hơn, `ruff check --target-version py311` bắt cú pháp mới hơn).
- Tệp phiên bản mà `org-setup.py files` cấp cho repository khác lấy từ cùng nguồn: `.python-version` sinh từ `python` trong `mise.toml`, `.nvmrc` chép từ `.nvmrc`.
- Dependabot chưa cập nhật `mise.toml`: `scripts/check-tool-versions.py` (`make versions`) báo khi ruff, ShellCheck, actionlint có bản mới (không theo dõi Python, Node.js) — workflow `links.yml` chạy hằng tuần, hook sau `git pull` chạy tại máy.
