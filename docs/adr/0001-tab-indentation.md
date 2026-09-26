# 0001. THỤT LỀ BẰNG TAB; CHỈ NGÔN NGỮ BẮT BUỘC MỚI DÙNG DẤU CÁCH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-09-26

## 📌 BỐI CẢNH

Các repository cần một quy ước thụt lề thống nhất. Tab cho phép mỗi người chọn độ rộng hiển thị và tệp nhỏ hơn; một số ngôn ngữ và formatter chính thức lại không chấp nhận tab.

## ✅ QUYẾT ĐỊNH

- Mặc định thụt lề bằng **tab**, độ rộng **4**, cho mọi ngôn ngữ — kể cả Python (`ruff format` với `indent-style = "tab"`).
- Chỉ ngôn ngữ bắt buộc dấu cách mới dùng dấu cách: **4** cho YAML (đặc tả cấm tab), Markdown (Prettier luôn thụt lề danh sách bằng dấu cách), F#, Elm, Nim, Zig; **2** cho Dart, Elixir, Terraform, Crystal, Gleam, Nix — formatter chính thức cố định độ rộng 2.
- Quy tắc khai báo trong `.editorconfig`, `.prettierrc.json`, `ruff.toml` và được `scripts/validate.py` kiểm tra.

## ⚖️ HỆ QUẢ

- Python dùng tab trái với khuyến nghị PEP 8; nếu bật lint `W191` của ruff phải bỏ qua quy tắc này.
- Formatter mặc định dấu cách (rustfmt, clang-format, swift-format…) phải cấu hình dùng tab trong từng dự án.
- Commit chuyển đổi định dạng được liệt kê trong `.git-blame-ignore-revs`.
