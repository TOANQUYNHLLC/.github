# 00000008. MỖI CÔNG CỤ CÓ MỘT NGUỒN PHIÊN BẢN

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-23

## 📌 BỐI CẢNH

Máy cục bộ, Dev Container và CI cần dùng công cụ nhất quán. Mỗi công cụ cần một nguồn phiên bản và cơ chế phát hiện các vị trí khai báo lệch nhau.

## ✅ QUYẾT ĐỊNH

Nguồn phiên bản được phân theo công cụ:

- `mise.toml`: Python cho máy cục bộ, Ruff, ShellCheck và actionlint.
- `.nvmrc`: Node.js; `devEngines` trong `package.json` phải khớp giá trị này.
- `package.json`: thư viện Node.js dùng cho công cụ phát triển.

CI chạy `python3` của runner cho các script cần Python ≥ 3.11; cài Ruff, ShellCheck, actionlint bằng mise và Node.js bằng `actions/setup-node`. Dev Container ghim Python trong image theo `mise.toml`, đặt `MISE_DISABLE_TOOLS=python` và cài các công cụ còn lại bằng mise.

Workflow và script đọc nguồn phiên bản, không tự khai báo bản riêng. Với workflow mẫu Python CI, dự án đích tạo `.python-version` theo phiên bản phù hợp; mẫu trong bộ tài nguyên dùng Python của `mise.toml` làm nguồn tham khảo. Git, GNU Make, Bash và Ruby là điều kiện môi trường được chuẩn bị riêng theo [hướng dẫn tại máy](../local-checks.md#-môi-trường).

Nguồn của quyết định: [mise.toml](../../mise.toml), [.nvmrc](../../.nvmrc), [package.json](../../package.json), [.devcontainer/devcontainer.json](../../.devcontainer/devcontainer.json), [scripts/check-tool-versions.py](../../scripts/check-tool-versions.py).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Khai báo tập trung giới hạn các nơi cần cập nhật khi nâng công cụ. Image Python được ghim cho container, còn CI sử dụng trình thông dịch có sẵn để chạy cùng bộ script tương thích phiên bản tối thiểu.

## ⚖️ HỆ QUẢ

Nâng Python cần đồng bộ image; nâng Node.js cần đồng bộ `devEngines`. Validator kiểm tra các nguồn và vị trí lặp bắt buộc. `make versions` theo dõi Ruff, ShellCheck, actionlint và mọi action trong `.github/workflows/`, `workflow-templates/`, chỉ đề xuất bản đã phát hành đủ `COOLDOWN_DAYS` ngày như cooldown của Dependabot; Python và Node.js nằm ngoài phạm vi lệnh này.
