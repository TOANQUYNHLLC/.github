# 0018. PROTECT MAIN CẤP TỔ CHỨC CHO PHÉP REBASE VÀ ÁP DỤNG CẢ NHÁNH MAIN

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-08
- **Điều chỉnh:** 0006 — phương thức hợp nhất của ruleset Protect Main (Organization)

## 📌 BỐI CẢNH

Ruleset **Protect Main (Organization)** trên web cho phép **Merge**, **Squash** và **Rebase**, áp dụng cho nhánh mặc định và `refs/heads/main` của mọi repository. Tệp `rulesets/org-protect-main.json` sinh từ bản cấp repository nên chỉ cho Merge, Squash và chỉ nhắm nhánh mặc định ([ADR 0006](0006-signed-commits-no-rebase.md)); `make org-preview` vì vậy luôn báo ruleset khác tệp. Người quản trị chọn giữ cấu hình đang có trên web làm nguồn.

## ✅ QUYẾT ĐỊNH

- `orgRuleset()` trong `scripts/orgsetup/rulesets.py` sinh Protect Main (Organization) từ bản cấp repository rồi thêm `rebase` vào `allowed_merge_methods` và thêm `refs/heads/main` vào `ref_name.include`; `rulesets/org-protect-main.json` được sinh lại theo hàm này.
- Ruleset cấp repository (`rulesets/protect-main.json`) và cài đặt repository (`allow_rebase_merge: false`) giữ nguyên quyết định không Rebase của ADR 0006.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Sửa ruleset trên web theo tệp** (không Rebase, chỉ nhánh mặc định): giữ nguyên ADR 0006 cho mọi cấp; người quản trị không chọn.
- **Cho phép Rebase ở cả ruleset và cài đặt cấp repository**: thay đổi phạm vi rộng hơn yêu cầu, bỏ quyết định không Rebase cho mọi repository.

## ⚖️ HỆ QUẢ

- `make org-preview` so Protect Main (Organization) trên web với tệp và báo đã đúng.
- Ruleset vẫn giữ `required_signatures`. Theo [ADR 0006](0006-signed-commits-no-rebase.md), Rebase and merge tạo lại commit mà GitHub không ký bằng khóa của người viết, nên quy tắc chữ ký vẫn quyết định commit nào vào được nhánh chính.
- Repository có ruleset Protect Main cấp repository hoặc cài đặt `allow_rebase_merge: false` vẫn không hợp nhất bằng Rebase được; ruleset cấp tổ chức chỉ được thực thi khi tổ chức nâng lên gói Team.
- Repository có nhánh mặc định khác `main` được bảo vệ cả nhánh mặc định lẫn nhánh `main`.
