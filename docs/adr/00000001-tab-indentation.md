# 00000001. THỤT LỀ BẰNG TAB; CHỈ NGÔN NGỮ BẮT BUỘC MỚI DÙNG DẤU CÁCH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Các repository cần một quy ước thụt lề thống nhất. Tab cho phép mỗi người chọn độ rộng hiển thị và tệp nhỏ hơn; một số ngôn ngữ và formatter chính thức lại không chấp nhận tab.

## ✅ QUYẾT ĐỊNH

- Mặc định thụt lề bằng **tab**, độ rộng **4**, cho mọi ngôn ngữ — kể cả Python (`ruff format` với `indent-style = "tab"`), JSON, shell, `Makefile`.
- Chỉ ngôn ngữ bắt buộc dấu cách mới dùng dấu cách:
    - **4** cho YAML (đặc tả cấm tab), Markdown (Prettier luôn thụt lề danh sách bằng dấu cách), F#, Elm, Nim, Zig.
    - **2** cho Dart, Elixir, Terraform, Crystal, Gleam, Nix — formatter chính thức cố định độ rộng 2.
- Quy tắc khai báo trong `.editorconfig`, `.prettierrc.json`, `ruff.toml` và được `scripts/validate.py` kiểm tra.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Dấu cách cho mọi tệp** (mặc định của nhiều formatter, khuyến nghị của PEP 8): không cho người đọc chọn độ rộng hiển thị và làm tệp lớn hơn; không chọn.
- **Tab cho mọi tệp, kể cả YAML, Markdown**: đặc tả YAML cấm tab và Prettier luôn thụt lề danh sách Markdown bằng dấu cách — không làm được; vì vậy chỉ ngôn ngữ bắt buộc dấu cách mới dùng dấu cách.

## ⚖️ HỆ QUẢ

- Python dùng tab, khác khuyến nghị PEP 8; không bật lint `W191` của ruff.
- Formatter mặc định dấu cách (rustfmt, clang-format…) được cấu hình dùng tab trong từng repository — `org-setup.py files` thêm tệp cấu hình mẫu.
- Commit chỉ đổi định dạng được liệt kê trong `.git-blame-ignore-revs`.
