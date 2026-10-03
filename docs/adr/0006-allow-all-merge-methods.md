# 0006. CHO PHÉP CẢ BA CÁCH HỢP NHẤT

- **Trạng thái:** Bị thay thế một phần bởi [0011](0011-disallow-rebase-merge.md) (bỏ Rebase)
- **Ngày:** 2026-09-26
- **Điều chỉnh:** [0004](0004-squash-merge-and-rulesets.md), [0005](0005-merge-protect-main.md) — cách hợp nhất và lịch sử tuyến tính

## 📌 BỐI CẢNH

Chỉ cho phép Squash and merge gộp mọi commit của Pull Request lớn thành một, làm mất các bước trung gian có ý nghĩa. Người quản trị cần chọn cách hợp nhất phù hợp từng Pull Request.

## ✅ QUYẾT ĐỊNH

- Ruleset **Protect Main** và cài đặt repository cho phép **Merge**, **Squash** và **Rebase**.
- Bỏ quy tắc **Require linear history**, vì quy tắc này chặn merge commit.
- Mặc định vẫn ưu tiên **Squash and merge** cho Pull Request nhỏ, một mục đích; dùng Merge hoặc Rebase khi các commit riêng cần được giữ lại.

## ⚖️ HỆ QUẢ

- Lịch sử nhánh chính có thể có merge commit.
- Mọi commit trên Pull Request phải theo quy ước commit khi hợp nhất bằng Merge hoặc Rebase, vì chúng đi thẳng vào nhánh chính.
- Ruleset còn 8 quy tắc: `code_quality`, `creation`, `deletion`, `non_fast_forward`, `pull_request`, `required_signatures`, `required_status_checks`, `update`.
