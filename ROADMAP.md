# 🗺️ LỘ TRÌNH

Các việc dự kiến cho repository `.github` và quy trình làm việc chung của **CÔNG TY TNHH TOÀN QUỲNH** trên GitHub. Lộ trình có thể thay đổi; đề xuất mới xin tạo Issue **✨ Đề xuất tính năng**. Việc đã hoàn thành được ghi trong [`CHANGELOG.md`](CHANGELOG.md).

---

## ✅ ĐÃ HOÀN THÀNH GẦN ĐÂY

- [x] Ruleset **Protect Main** duy nhất trên `.github`, tạo từ [`rulesets/protect-main.json`](rulesets/protect-main.json): chỉ Squash and merge, 5 kiểm tra bắt buộc, phê duyệt của `CODEOWNERS` và phê duyệt lại sau lần đẩy cuối, commit có chữ ký, lịch sử tuyến tính, code quality, chặn tạo/cập nhật/xóa/force push; danh sách bỏ qua hai tài khoản quản trị (2026-09-26).
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
- [ ] `python3 scripts/org-setup.py rulesets --apply --repo <tên>` — ruleset **Protect Main** từ [`protect-main.json`](rulesets/protect-main.json), chỉ giữ 2 kiểm tra bắt buộc mà repository có.
- [ ] `scripts/sync-labels.sh --apply <tên>` — bộ nhãn chuẩn.
- [ ] Cấp quyền cho team **maintainers** trên repository mới (**Maintain** trở lên) để `CODEOWNERS` có hiệu lực.

---

## 💡 CÂN NHẮC

- [ ] Bật GitHub Discussions cho các repository khác khi cần (`python3 scripts/org-setup.py settings --apply --repo <tên> --discussions`); `.github` đã bật, biểu mẫu có sẵn trong [`DISCUSSION_TEMPLATE/`](DISCUSSION_TEMPLATE/).
