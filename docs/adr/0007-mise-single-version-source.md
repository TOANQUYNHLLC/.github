# 0007. MISE.TOML LÀ NGUỒN PHIÊN BẢN CÔNG CỤ DUY NHẤT

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-09-26

## 📌 BỐI CẢNH

Phiên bản ruff và actionlint được ghi ở ba nơi: CI (`pip install ruff==…`, `go install actionlint@…`), `mise.toml` và script Dev Container. Node.js ghi ở cả `.nvmrc` và `mise.toml`. Nâng phiên bản ở một nơi dễ quên nơi khác, làm máy cục bộ và CI định dạng khác nhau.

## ✅ QUYẾT ĐỊNH

- `mise.toml` là nơi duy nhất khai báo phiên bản ruff, ShellCheck, actionlint.
- Node.js chỉ khai báo trong `.nvmrc`: `actions/setup-node` và mise (`idiomatic_version_file_enable_tools`) cùng đọc tệp này.
- CI cài công cụ bằng `jdx/mise-action`; Dev Container cài mise rồi chạy `mise install`.
- `scripts/validate.py` báo lỗi khi workflow hoặc script tự ghi phiên bản các công cụ này.

## ⚖️ HỆ QUẢ

- Nâng phiên bản: sửa một dòng trong `mise.toml` (hoặc `.nvmrc`), CI và Dev Container tự dùng bản mới.
- Dependabot chưa cập nhật `mise.toml`; người quản trị kiểm tra phiên bản mới khi rà soát định kỳ.
