# 0016. IMAGE DEV CONTAINER GHIM ĐÚNG BẢN PYTHON CỦA MISE.TOML

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-06
- **Điều chỉnh:** 0008 — nơi khai báo phiên bản Python của Dev Container

## 📌 BỐI CẢNH

Dev Container lấy Python từ image (`MISE_DISABLE_TOOLS=python`), không cài bằng mise ([ADR 0008](0008-mise-single-version-source.md)). Tag `mcr.microsoft.com/devcontainers/python:3-3-trixie` luôn trỏ tới Python 3 mới nhất: khi Python bản mới phát hành, container dựng lại tự lên bản đó trong khi máy cục bộ vẫn dùng bản trong `mise.toml`, nên script có thể chạy khác nhau giữa hai nơi.

## ✅ QUYẾT ĐỊNH

- Image Dev Container ghim đúng bản Python của `mise.toml` (`python:3-3.14-trixie` khi `mise.toml` ghi `python = "3.14"`).
- `mise.toml` vẫn là nguồn: tag image nhắc lại bản đó, như `devEngines` của `package.json` nhắc lại `.nvmrc`. `checkDevcontainerPins()` trong `scripts/validation/tooling.py` báo lỗi khi tag image không ghim bản Python hoặc khác `mise.toml`.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Giữ tag `3-3-trixie`**: không phải sửa khi nâng Python, nhưng Dev Container lặng lẽ khác máy cục bộ sau mỗi lần Python phát hành bản mới.
- **Cài Python bằng mise trong Dev Container** (bỏ `MISE_DISABLE_TOOLS=python`): mise dựng Python từ mã nguồn hoặc tải bản dựng sẵn mỗi lần tạo container, chậm hơn nhiều so với Python có sẵn trong image.

## ⚖️ HỆ QUẢ

- Nâng Python: sửa `mise.toml` cùng tag image trong `.devcontainer/devcontainer.json`; `make check` báo khi quên một nơi.
- CI vẫn dùng `python3` có sẵn của runner theo [ADR 0008](0008-mise-single-version-source.md).
