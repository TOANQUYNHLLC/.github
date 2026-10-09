# 00000008. MISE.TOML LÀ NGUỒN PHIÊN BẢN CÔNG CỤ DUY NHẤT

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Công cụ cần phiên bản nhất quán giữa máy cục bộ, CI và Dev Container. Mỗi loại công cụ có một nguồn phiên bản; những vị trí buộc phải nhắc lại phiên bản được kiểm tra tự động.

## ✅ QUYẾT ĐỊNH

`mise.toml` khai báo Python, ruff, ShellCheck và actionlint. `.nvmrc` khai báo Node.js; `devEngines` trong `package.json` giữ đúng giá trị đó. Thư viện Node.js khai báo trong `package.json`.

CI cài công cụ bằng mise, Node.js bằng `actions/setup-node` và chạy Python có sẵn của runner. Script cần Python **≥ 3.11**; ruff kiểm tra với `--target-version py311`.

Image Dev Container ghim bản Python theo `mise.toml` và đặt `MISE_DISABLE_TOOLS=python`. Các công cụ còn lại được cài bằng `mise install`. Validator kiểm tra nguồn phiên bản, `devEngines`, image và các vị trí không được tự ghi phiên bản.

Tệp `.python-version` cho repository đích được sinh từ `mise.toml`; `.nvmrc` được chép từ nguồn Node.js.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Khai báo phiên bản trong từng workflow và script dễ tạo sai lệch. Node.js trong cả `.nvmrc` và `mise.toml` tạo hai nguồn. Image Python không ghim có thể đổi runtime khi dựng lại; cài Python bằng mise trong container làm tăng thời gian thiết lập.

## ⚖️ HỆ QUẢ

Nâng Python phải cập nhật cả nguồn và image; nâng Node.js phải cập nhật `.nvmrc` cùng `devEngines`. `make versions` kiểm tra bản phát hành của ruff, ShellCheck và actionlint; Python và Node.js không thuộc phạm vi lệnh này.
