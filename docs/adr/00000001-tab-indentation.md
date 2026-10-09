# 00000001. THỤT LỀ BẰNG TAB; CHỈ NGÔN NGỮ BẮT BUỘC MỚI DÙNG DẤU CÁCH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Các repository dùng chung quy tắc thụt lề để mã nguồn được định dạng nhất quán. Tab cho phép người đọc chọn độ rộng hiển thị; định dạng không hỗ trợ tab cần ngoại lệ rõ ràng.

## ✅ QUYẾT ĐỊNH

Mặc định dùng **tab, độ rộng 4** cho Python, JSON, shell, Makefile và các ngôn ngữ hỗ trợ tab. Python dùng `ruff format` với `indent-style = "tab"`.

Các ngoại lệ dùng dấu cách theo yêu cầu của định dạng hoặc formatter:

- Độ rộng **4**: YAML, Markdown, F#, Elm, Nim, Zig.
- Độ rộng **2**: Dart, Elixir, Terraform, Crystal, Gleam, Nix.

Quy tắc nằm trong `.editorconfig`, `.prettierrc.json` và `ruff.toml`; `scripts/validate.py` đối chiếu các cấu hình.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Dấu cách cho mọi tệp không đáp ứng lựa chọn độ rộng hiển thị của người đọc. Tab cho mọi tệp không tương thích với YAML và formatter Markdown. Quy tắc mặc định kèm ngoại lệ đáp ứng cả hai yêu cầu.

## ⚖️ HỆ QUẢ

Python dùng tab và không bật luật `W191` của ruff. Formatter như rustfmt và clang-format được cấu hình dùng tab trong từng dự án; lệnh `files` cung cấp mẫu tương ứng. Commit chỉ đổi định dạng được ghi trong `.git-blame-ignore-revs`.
