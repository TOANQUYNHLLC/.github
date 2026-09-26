# 🗺️ LỘ TRÌNH

Các việc dự kiến cho repository `.github` và quy trình làm việc chung của **CÔNG TY TNHH TOÀN QUỲNH** trên GitHub. Lộ trình có thể thay đổi; đề xuất mới xin tạo Issue **✨ Đề xuất tính năng**. Việc đã hoàn thành được ghi trong [`CHANGELOG.md`](CHANGELOG.md).

---

## 🚧 ĐANG THỰC HIỆN

Công cụ đã sẵn sàng trong [`scripts/org-setup.py`](scripts/org-setup.py) — cần người quản trị chạy với GitHub CLI đã đăng nhập. Xem trước toàn bộ: `make org-preview`. Thứ tự áp dụng:

- [ ] Chép tệp dùng chung (workflow kiểm tra tiêu đề Pull Request và tên branch, `CODEOWNERS`, `dependabot.yml`, `release.yml`) vào mọi repository qua Pull Request: `python3 scripts/org-setup.py files --apply`, rồi đánh giá và hợp nhất từng Pull Request. Hiện tổ chức chỉ có repository `.github` (đã có sẵn các tệp này) — chạy lệnh khi tạo repository mới.
- [x] Chỉ cho phép **Squash and merge**, tự xóa branch sau khi hợp nhất: `python3 scripts/org-setup.py settings --apply` — đã áp dụng cho `.github` (2026-09-26).
- [ ] Cập nhật ruleset **Protect Main** đang có của `.github` theo [`dot-github.json`](rulesets/dot-github.json) (người quản trị tự làm — xem mục **KIỂM TRA TRÊN WEB**); repository khác: `python3 scripts/org-setup.py rulesets --apply`.
- [x] Đồng bộ bộ nhãn chuẩn: `make labels-apply` — đã áp dụng cho `.github` (2026-09-26).

---

## 🌐 KIỂM TRA TRÊN WEB

Các việc cấp quyền hoặc thay đổi bảo vệ nhánh do người quản trị tự làm trên GitHub:

- [ ] **Settings → Rules → Rulesets → Protect Main**: chỉ cho phép Squash and merge; thêm 5 kiểm tra bắt buộc trong [`dot-github.json`](rulesets/dot-github.json) (tên phải trùng tên job); giữ `nguyentrongtoandl` và `trongtoandl81` trong **Bypass list**.
- [x] **Settings → SSH and GPG keys**: cả `nguyentrongtoandl` và `trongtoandl81` đã đăng ký khóa ký commit ED25519 (2026-09-26).
- [ ] Tạo team **maintainers** (tổ chức đang có các team `developer`, `marketing`, `seo`, `ui-ux`): `gh auth refresh -s admin:org` rồi `python3 scripts/org-setup.py team --apply`, hoặc **Organization → Teams → New team**.
- [x] **Settings → General → Features**: Discussions đã bật cho `.github` (2026-09-26).

---

## 💡 CÂN NHẮC

- [ ] Tạo team **maintainers** (`python3 scripts/org-setup.py team --apply`), rồi chuyển `CODEOWNERS`, [`MAINTAINERS.md`](MAINTAINERS.md) sang `@TOANQUYNHLLC/maintainers`.
- [ ] Bật GitHub Discussions cho các repository khác khi cần (`python3 scripts/org-setup.py settings --apply --repo <tên> --discussions`); `.github` đã bật, biểu mẫu có sẵn trong [`DISCUSSION_TEMPLATE/`](DISCUSSION_TEMPLATE/).
