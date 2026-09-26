# 🗺️ LỘ TRÌNH

Các việc dự kiến cho repository `.github` và quy trình làm việc chung của **CÔNG TY TNHH TOÀN QUỲNH** trên GitHub. Lộ trình có thể thay đổi; đề xuất mới xin tạo Issue **✨ Đề xuất tính năng**. Việc đã hoàn thành được ghi trong [`CHANGELOG.md`](CHANGELOG.md).

---

## 🔥 ƯU TIÊN: GỘP HAI RULESET THÀNH PROTECT MAIN

[`rulesets/dot-github.json`](rulesets/dot-github.json) đã gộp toàn bộ cài đặt của **Protect Main** hiện tại và ruleset mới, tên **Protect Main** ([ADR 0005](docs/adr/0005-merge-protect-main.md)). Người quản trị làm trong **Settings → Rules → Rulesets** của repository `.github` (trang chỉ người quản trị mở được) theo thứ tự để nhánh chính luôn được bảo vệ:

1. Mở **Protect Main** hiện tại → đổi tên thành `Protect Main (cũ)` → **Save changes**.
2. **New ruleset → Import a ruleset** → chọn `rulesets/dot-github.json` → **Create**. Ruleset mới tên **Protect Main**.
3. Xóa ruleset `Protect Main (cũ)` và ruleset **Bảo vệ nhánh chính — repository .github**.
4. Kiểm tra chỉ còn một ruleset và đủ quy tắc:

    ```sh
    gh api repos/TOANQUYNHLLC/.github/rulesets --jq '.[].name'
    gh api repos/TOANQUYNHLLC/.github/rules/branches/main --jq '[.[].type] | unique'
    ```

    Kết quả: chỉ `Protect Main`; 9 quy tắc `code_quality`, `creation`, `deletion`, `non_fast_forward`, `pull_request`, `required_linear_history`, `required_signatures`, `required_status_checks`, `update`.

---

## ✅ ĐÃ HOÀN THÀNH GẦN ĐÂY

- [x] Ruleset **Bảo vệ nhánh chính — repository .github** (import từ [`dot-github.json`](rulesets/dot-github.json)) đang áp dụng cho `main` cùng ruleset **Protect Main**: chỉ Squash and merge, bắt buộc 5 kiểm tra tự động, phê duyệt của `CODEOWNERS`, commit có chữ ký, lịch sử tuyến tính (2026-09-26). Hai ruleset cùng áp dụng — quy tắc chặt hơn được dùng.
- [x] Team **maintainers** (`nguyentrongtoandl`, `trongtoandl81`, quyền **Maintain**) là chủ sở hữu mã trong `CODEOWNERS` (2026-09-26).
- [x] Chỉ cho phép **Squash and merge**, tự xóa branch sau khi hợp nhất; đồng bộ 16 nhãn chuẩn; Discussions đã bật; cả hai tài khoản đã đăng ký khóa ký commit (2026-09-26).

Kiểm tra lại các quy tắc đang áp dụng cho `main`:

```sh
gh api repos/TOANQUYNHLLC/.github/rules/branches/main --jq '[.[].type] | unique'
```

---

## 🚧 KHI TẠO REPOSITORY MỚI

Hiện tổ chức chỉ có repository `.github`. Với mỗi repository mới, người quản trị chạy [`scripts/org-setup.py`](scripts/org-setup.py) (GitHub CLI đã đăng nhập; xem trước bằng `make org-preview`) theo thứ tự:

- [ ] `python3 scripts/org-setup.py files --apply --repo <tên>` — Pull Request thêm workflow kiểm tra tiêu đề và tên branch, `CODEOWNERS`, `dependabot.yml`, `release.yml`; đánh giá rồi hợp nhất.
- [ ] `python3 scripts/org-setup.py settings --apply --repo <tên>` — chỉ Squash and merge, tự xóa branch.
- [ ] `python3 scripts/org-setup.py rulesets --apply --repo <tên>` — ruleset [`default-branch.json`](rulesets/default-branch.json); kiểm tra **Bypass list** hiển thị **Repository admin**.
- [ ] `scripts/sync-labels.sh --apply <tên>` — bộ nhãn chuẩn.
- [ ] Cấp quyền cho team **maintainers** trên repository mới (**Maintain** trở lên) để `CODEOWNERS` có hiệu lực.

---

## 💡 CÂN NHẮC

- [ ] Bật GitHub Discussions cho các repository khác khi cần (`python3 scripts/org-setup.py settings --apply --repo <tên> --discussions`); `.github` đã bật, biểu mẫu có sẵn trong [`DISCUSSION_TEMPLATE/`](DISCUSSION_TEMPLATE/).
