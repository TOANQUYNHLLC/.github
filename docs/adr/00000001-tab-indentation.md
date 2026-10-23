# 00000001. THỤT LỀ BẰNG TAB; CHỈ NGÔN NGỮ BẮT BUỘC MỚI DÙNG DẤU CÁCH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Mã nguồn và cấu hình cần có cách thụt lề thống nhất giữa editor, formatter và CI. Một số định dạng yêu cầu dấu cách hoặc có formatter quy định sẵn độ rộng.

## ✅ QUYẾT ĐỊNH

Dùng tab độ rộng 4 cho Python, JSON, shell, Makefile và các định dạng hỗ trợ tab. Python dùng `ruff format` với `indent-style = "tab"`.

Ngoại lệ dùng dấu cách được khai báo trong `.editorconfig`:

- Độ rộng 4 cho YAML, Markdown, F#, Elm, Nim và Zig.
- Độ rộng 2 cho Dart, Elixir, Terraform, Crystal, Gleam và Nix.

`.prettierrc.json` và `ruff.toml` tuân theo các quy tắc này. Mẫu rustfmt và clang-format trong `repository-templates/` cung cấp cấu hình tab cho dự án tương ứng.

Nguồn của quyết định: [.editorconfig](../../.editorconfig), [.prettierrc.json](../../.prettierrc.json), [ruff.toml](../../ruff.toml), [scripts/validation/formatting.py](../../scripts/validation/formatting.py).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Tab cho phép người đọc chọn độ rộng hiển thị. Ngoại lệ theo định dạng giúp YAML và các formatter có quy tắc cố định tạo được nội dung hợp lệ. Dùng một kiểu cho mọi định dạng không đáp ứng đồng thời hai yêu cầu này.

## ⚖️ HỆ QUẢ

Người đóng góp dùng formatter của dự án trước khi commit. Validator đối chiếu các nguồn cấu hình; Ruff không bật luật `W191`. Khi có commit chỉ đổi định dạng, ghi SHA vào `.git-blame-ignore-revs` và cấu hình Git blame dùng tệp đó theo quy ước đóng góp.
