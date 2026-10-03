# 0011. BỎ REBASE ĐỂ COMMIT TRÊN NHÁNH CHÍNH LUÔN CÓ CHỮ KÝ

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03
- **Điều chỉnh:** [0006](0006-allow-all-merge-methods.md) — bỏ **Rebase** khỏi các cách hợp nhất được phép

## 📌 BỐI CẢNH

ADR 0006 cho phép Merge, Squash và Rebase; ADR 0009 bắt buộc commit có chữ ký trên nhánh chính. Hai quyết định mâu thuẫn: khi hợp nhất bằng **Rebase and merge**, GitHub tạo lại từng commit từ commit gốc nhưng không có khóa của người viết nên không ký được — commit trên nhánh chính mất chữ ký dù commit trên Pull Request đã ký.

Kiểm tra ngày 2026-10-03: 36/59 commit trên `main` của `.github` không có chữ ký, gồm mọi Pull Request hợp nhất bằng Rebase (#42–#45); chúng chỉ vào được `main` nhờ quyền bỏ qua của người quản trị. Không ký lại được nếu không viết lại lịch sử (cấm force push lên `main`).

**Squash and merge** và **Merge** tạo commit mới do GitHub ký, nên luôn có chữ ký.

## ✅ QUYẾT ĐỊNH

- Ruleset **Protect Main** (cấp repository và cấp tổ chức) chỉ cho phép `merge` và `squash` (`allowed_merge_methods`); cài đặt repository tắt **Allow rebase merging** (`allow_rebase_merge: false` trong `MERGE_SETTINGS` của `scripts/org-setup.py`).
- Vẫn ưu tiên **Squash and merge**; dùng **Merge** khi cần giữ các commit riêng của Pull Request.
- Rebase branch của mình lên nhánh chính tại máy (`git rebase origin/main`) vẫn được — commit được ký lại bằng khóa của người viết.

## ⚖️ HỆ QUẢ

- Mọi commit mới trên nhánh chính có chữ ký đã xác minh; 36 commit không ký trước đây giữ nguyên.
- Không còn lịch sử tuyến tính giữ nguyên từng commit mà không có merge commit; muốn giữ từng commit thì dùng Merge.
- Sau khi hợp nhất: chạy `python3 scripts/org-setup.py settings --apply` và `rulesets --apply` cho các repository; sửa **Protect Main (Organization)** trên web (bỏ Rebase) hoặc xóa rồi import lại `rulesets/org-protect-main.json`.
