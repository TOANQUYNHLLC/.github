# 🗺️ LỘ TRÌNH

Các việc dự kiến cho repository `.github` và quy trình làm việc chung của **CÔNG TY TNHH TOÀN QUỲNH** trên GitHub. Lộ trình có thể thay đổi; đề xuất mới xin tạo Issue **✨ Đề xuất tính năng**. Việc đã hoàn thành được ghi trong [`CHANGELOG.md`](CHANGELOG.md).

---

## 🔥 ƯU TIÊN: CẬP NHẬT RULESET PROTECT MAIN

Ruleset **Protect Main** của `.github` hiện vẫn cho phép cả 3 cách hợp nhất và **chưa bắt buộc kiểm tra tự động nào** — Pull Request có thể được hợp nhất dù CI thất bại. Việc thay đổi bảo vệ nhánh do người quản trị làm trên web:

1. Mở [Settings → Rules → Rulesets](https://github.com/TOANQUYNHLLC/.github/settings/rules) → **Protect Main**.
2. Mục **Require a pull request before merging** → **Allowed merge methods**: chỉ giữ **Squash**.
3. Mục **Require status checks to pass** → **Add checks**, thêm đủ 5 kiểm tra (gõ đúng tên job; chọn nguồn **GitHub Actions**):
    - `Liên kết, biểu mẫu, nhãn, cấu hình định dạng và mẫu email`
    - `Định dạng (Prettier, ruff) và ESLint`
    - `Shell script và workflow`
    - `Kiểm tra tiêu đề Pull Request`
    - `Kiểm tra tên branch`
4. Giữ **Require branches to be up to date before merging**; giữ `nguyentrongtoandl` và `trongtoandl81` trong **Bypass list**.
5. Chọn **Save changes**.
6. Kiểm tra lại (kết quả phải liệt kê `squash` và 5 kiểm tra trên):

    ```sh
    id=$(gh api repos/TOANQUYNHLLC/.github/rulesets --jq '.[] | select(.name=="Protect Main") | .id')
    gh api repos/TOANQUYNHLLC/.github/rulesets/$id --jq '[.rules[] | select(.type=="pull_request" or .type=="required_status_checks") | .parameters | .allowed_merge_methods // [.required_status_checks[].context]]'
    ```

---

## 🚧 ĐANG THỰC HIỆN

Công cụ đã sẵn sàng trong [`scripts/org-setup.py`](scripts/org-setup.py) — cần người quản trị chạy với GitHub CLI đã đăng nhập. Xem trước toàn bộ: `make org-preview`. Thứ tự áp dụng:

- [ ] Chép tệp dùng chung (workflow kiểm tra tiêu đề Pull Request và tên branch, `CODEOWNERS`, `dependabot.yml`, `release.yml`) vào mọi repository qua Pull Request: `python3 scripts/org-setup.py files --apply`, rồi đánh giá và hợp nhất từng Pull Request. Hiện tổ chức chỉ có repository `.github` (đã có sẵn các tệp này) — chạy lệnh khi tạo repository mới.
- [x] Chỉ cho phép **Squash and merge**, tự xóa branch sau khi hợp nhất: `python3 scripts/org-setup.py settings --apply` — đã áp dụng cho `.github` (2026-09-26).
- [ ] Ruleset cho repository khác: `python3 scripts/org-setup.py rulesets --apply` (sau khi đã hợp nhất Pull Request của lệnh `files`).
- [x] Đồng bộ bộ nhãn chuẩn: `make labels-apply` — đã áp dụng cho `.github` (2026-09-26).

---

## 🌐 KIỂM TRA TRÊN WEB

Các việc cấp quyền hoặc thay đổi bảo vệ nhánh do người quản trị tự làm trên GitHub:

- [x] **Settings → SSH and GPG keys**: cả `nguyentrongtoandl` và `trongtoandl81` đã đăng ký khóa ký commit ED25519 (2026-09-26).
- [x] Team **maintainers** gồm `nguyentrongtoandl`, `trongtoandl81`, quyền **Maintain** trên `.github` (2026-09-26).
- [x] **Settings → General → Features**: Discussions đã bật cho `.github` (2026-09-26).

---

## 💡 CÂN NHẮC

- [x] Chuyển `CODEOWNERS` và [`MAINTAINERS.md`](MAINTAINERS.md) sang team `@TOANQUYNHLLC/maintainers` (2026-09-26).
- [ ] Bật GitHub Discussions cho các repository khác khi cần (`python3 scripts/org-setup.py settings --apply --repo <tên> --discussions`); `.github` đã bật, biểu mẫu có sẵn trong [`DISCUSSION_TEMPLATE/`](DISCUSSION_TEMPLATE/).
