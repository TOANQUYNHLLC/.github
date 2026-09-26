# 🗺️ LỘ TRÌNH

Các việc dự kiến cho repository `.github` và quy trình làm việc chung của **CÔNG TY TNHH TOÀN QUỲNH** trên GitHub. Lộ trình có thể thay đổi; đề xuất mới xin tạo Issue **✨ Đề xuất tính năng**. Việc đã hoàn thành được ghi trong [`CHANGELOG.md`](CHANGELOG.md).

---

## 🔥 ƯU TIÊN: TẠO RULESET PROTECT MAIN

Repository `.github` hiện **không có ruleset nào** — nhánh chính chưa được bảo vệ. Người quản trị tạo ruleset **Protect Main** duy nhất từ [`rulesets/protect-main.json`](rulesets/protect-main.json) ([ADR 0005](docs/adr/0005-merge-protect-main.md)) bằng một trong hai cách:

- **Lệnh:** `python3 scripts/org-setup.py rulesets --apply --repo .github`
- **Trên web:** **Settings → Rules → Rulesets → New ruleset → Import a ruleset** → chọn `rulesets/protect-main.json` → **Create**.

Kiểm tra chỉ có một ruleset và đủ quy tắc:

```sh
gh api repos/TOANQUYNHLLC/.github/rulesets --jq '.[].name'
gh api repos/TOANQUYNHLLC/.github/rules/branches/main --jq '[.[].type] | unique'
```

Kết quả: chỉ `Protect Main`; 9 quy tắc `code_quality`, `creation`, `deletion`, `non_fast_forward`, `pull_request`, `required_signatures`, `required_status_checks`, `update`.

---

## ✅ ĐÃ HOÀN THÀNH GẦN ĐÂY

- [x] Team **maintainers** (`nguyentrongtoandl`, `trongtoandl81`, quyền **Maintain**) là chủ sở hữu mã trong `CODEOWNERS` (2026-09-26).
- [x] Cho phép Merge, Squash và Rebase, tự xóa branch sau khi hợp nhất ([ADR 0006](docs/adr/0006-allow-all-merge-methods.md)); đồng bộ 16 nhãn chuẩn; Discussions đã bật; cả hai tài khoản đã đăng ký khóa ký commit (2026-09-26).

Kiểm tra lại các quy tắc đang áp dụng cho `main`:

```sh
gh api repos/TOANQUYNHLLC/.github/rules/branches/main --jq '[.[].type] | unique'
```

---

## 🚧 KHI TẠO REPOSITORY MỚI

Hiện tổ chức chỉ có repository `.github`. Với mỗi repository mới, người quản trị chạy [`scripts/org-setup.py`](scripts/org-setup.py) (GitHub CLI đã đăng nhập; xem trước bằng `make org-preview`) theo thứ tự:

- [ ] `python3 scripts/org-setup.py files --apply --repo <tên>` — Pull Request thêm workflow kiểm tra tiêu đề và tên branch, `CODEOWNERS`, `dependabot.yml`, `release.yml`; đánh giá rồi hợp nhất.
- [ ] `python3 scripts/org-setup.py settings --apply --repo <tên>` — cho phép Merge, Squash, Rebase; tự xóa branch.
- [ ] `python3 scripts/org-setup.py rulesets --apply --repo <tên>` — ruleset **Protect Main** từ [`protect-main.json`](rulesets/protect-main.json), chỉ giữ 2 kiểm tra bắt buộc mà repository có.
- [ ] `scripts/sync-labels.sh --apply <tên>` — bộ nhãn chuẩn.
- [ ] Cấp quyền cho team **maintainers** trên repository mới (**Maintain** trở lên) để `CODEOWNERS` có hiệu lực.

---

## 💡 CÂN NHẮC

- [ ] Bật GitHub Discussions cho các repository khác khi cần (`python3 scripts/org-setup.py settings --apply --repo <tên> --discussions`); `.github` đã bật, biểu mẫu có sẵn trong [`DISCUSSION_TEMPLATE/`](DISCUSSION_TEMPLATE/).
