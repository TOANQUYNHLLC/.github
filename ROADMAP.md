# 🗺️ LỘ TRÌNH

Các việc dự kiến cho repository `.github` và quy trình làm việc chung của **CÔNG TY TNHH TOÀN QUỲNH** trên GitHub. Lộ trình có thể thay đổi; đề xuất mới xin tạo Issue **✨ Đề xuất tính năng**. Việc đã hoàn thành được ghi trong [`CHANGELOG.md`](CHANGELOG.md).

---

## ✅ ĐÃ HOÀN THÀNH GẦN ĐÂY

- [x] Ruleset cấp tổ chức **Protect Main (Organization)** và **Protect Release Tags (Organization)** đã import trên web (**Active**); [`rulesets/org-protect-main.json`](rulesets/org-protect-main.json), [`rulesets/org-protect-release-tags.json`](rulesets/org-protect-release-tags.json) khớp bản trên web. GitHub chỉ thực thi khi tổ chức nâng lên gói **Team** (2026-09-27).
- [x] Đối chiếu thêm 30 repository ứng dụng (gồm OpenEMR, Medplum, OpenMRS, HAPI FHIR): thêm `ui/ux`, `i18n` (47 nhãn), đồng bộ lên `.github` (2026-09-27).
- [x] Đối chiếu nhãn với 40 repository phổ biến: thêm `regression`, `build`, `confirmed`, `upstream` (45 nhãn), đồng bộ lên `.github` (2026-09-27).
- [x] Đồng bộ bộ 41 nhãn chuẩn (thêm `chore`, `hotfix`, `release`, `pinned`, sáu nhãn `area: …`) lên `.github`; `.github/labeler.yml` tự gắn nhãn loại cho Pull Request theo tiền tố branch (2026-09-27).
- [x] Đồng bộ bộ 31 nhãn chuẩn (thêm 15 nhãn phổ biến: `help wanted`, loại thay đổi, trạng thái xử lý, nhãn Dependabot theo ecosystem) lên `.github` bằng `scripts/sync-labels.sh --apply` (2026-09-27).
- [x] Đăng [`.well-known/security.txt`](.well-known/security.txt) tại `https://toanquynh.com/.well-known/security.txt` (hosting P.A Việt Nam, thư mục `public_html/.well-known/`); `links.yml` kiểm tra URL này hằng tuần (2026-09-27).
- [x] Ruleset **Protect Main** duy nhất cho `main` của `.github`, tạo từ [`rulesets/protect-main.json`](rulesets/protect-main.json) ([ADR 0005](docs/adr/0005-merge-protect-main.md)), đang áp dụng 8 quy tắc: `code_quality`, `creation`, `deletion`, `non_fast_forward`, `pull_request`, `required_signatures`, `required_status_checks`, `update` (2026-09-26).
- [x] Team **maintainers** (`nguyentrongtoandl`, `trongtoandl81`, quyền **Maintain**) là chủ sở hữu mã trong `CODEOWNERS` (2026-09-26).
- [x] Cho phép Merge, Squash và Rebase, tự xóa branch sau khi hợp nhất ([ADR 0006](docs/adr/0006-allow-all-merge-methods.md)); đồng bộ 16 nhãn chuẩn; Discussions đã bật; cả hai tài khoản đã đăng ký khóa ký commit (2026-09-26).
- [x] Bật secret scanning, push protection, Dependabot security updates và báo cáo lỗ hổng riêng tư (**Security → Report a vulnerability**) cho `.github`; `SECURITY.md` và `security.txt` thêm kênh báo cáo qua GitHub (2026-09-26).

Kiểm tra lại ruleset và các quy tắc đang áp dụng cho `main`:

```sh
gh api repos/TOANQUYNHLLC/.github/rulesets --jq '.[].name'
gh api repos/TOANQUYNHLLC/.github/rules/branches/main --jq '[.[].type] | unique'
python3 scripts/org-setup.py org-rulesets   # so ruleset cấp tổ chức trên web với rulesets/org-*.json
```

---

## 🚧 KHI TẠO REPOSITORY MỚI

Hiện tổ chức chỉ có repository `.github`.

- [ ] Tạo repository ứng dụng đầu tiên (ví dụ mã nguồn website `toanquynh.com` hoặc API `api.toanquynh.com`), rồi chạy các bước dưới. Khi chọn **Private**, lưu ý giới hạn của gói GitHub Free: ruleset (**Protect Main**, **Protect Release Tags**) không được thực thi, báo cáo lỗ hổng riêng tư chỉ có ở repository công khai, secret scanning và push protection cần **GitHub Secret Protection** trên gói Team trở lên — `org-setup.py` cảnh báo các mục này rồi chạy tiếp.

Với mỗi repository mới, người quản trị chạy [`scripts/org-setup.py`](scripts/org-setup.py) (GitHub CLI đã đăng nhập; xem trước bằng `make org-preview`) theo thứ tự:

- [ ] `python3 scripts/org-setup.py files --apply --repo <tên>` — Pull Request thêm `.editorconfig`, `.gitattributes`, workflow kiểm tra tiêu đề, tên branch và gắn nhãn (`labeler.yml` kèm cấu hình — sửa đường dẫn nhãn `area: …` cho khớp dự án), `CODEOWNERS`, `dependabot.yml`, `release.yml` và tệp định dạng theo ngôn ngữ; đánh giá rồi hợp nhất. Chép tay `.env.example`, `PRIVACY.md` khi cần ([`repository-templates/`](repository-templates/)).
- [ ] `python3 scripts/org-setup.py settings --apply --repo <tên>` — cho phép Merge, Squash, Rebase; tự xóa branch; bật secret scanning, push protection, Dependabot security updates, báo cáo lỗ hổng riêng tư.
- [ ] `python3 scripts/org-setup.py rulesets --apply --repo <tên>` — ruleset **Protect Release Tags** từ [`protect-release-tags.json`](rulesets/protect-release-tags.json) và **Protect Main** từ [`protect-main.json`](rulesets/protect-main.json), Protect Main chỉ giữ 2 kiểm tra bắt buộc mà repository có.
- [ ] `scripts/sync-labels.sh --apply <tên>` — bộ nhãn chuẩn.
- [ ] `python3 scripts/org-setup.py team --apply --repo <tên>` — cấp quyền **Maintain** cho team **maintainers** để `CODEOWNERS` có hiệu lực.

---

## 🏢 CÀI ĐẶT TỔ CHỨC TRÊN WEB

GitHub không có API cho các mục này — người quản trị làm trên web.

- [ ] Nhãn mặc định cho repository tạo mới: **Organization settings → Repository → General → Repository labels** — nhập đủ 47 nhãn theo [`labels.yml`](labels.yml) (tên, màu, mô tả; `ui/ux` `d4a5ff`, `i18n` `5319e7` là hai nhãn thêm sau cùng). Nhãn mặc định chỉ áp cho repository tạo sau đó; repository đã có đồng bộ bằng `scripts/sync-labels.sh --apply <tên>`.

---

## 💡 CÂN NHẮC

- [ ] Bật GitHub Discussions cho các repository khác khi cần (`python3 scripts/org-setup.py settings --apply --repo <tên> --discussions`); `.github` đã bật, biểu mẫu có sẵn trong [`.github/DISCUSSION_TEMPLATE/`](.github/DISCUSSION_TEMPLATE/).
- [ ] Khi nâng lên gói **Team**: ruleset cấp tổ chức được thực thi — cân nhắc ADR mới để bỏ ruleset cấp repository trùng lặp.
- [ ] Xóa quy tắc kiểm tra bắt buộc rỗng (không chặn gì) của **Protect Release Tags (Organization)** trên web, rồi bỏ khỏi `org_tag_ruleset()` trong [`scripts/org-setup.py`](scripts/org-setup.py) và sinh lại tệp.
- [ ] Quét bí mật theo mẫu tùy chỉnh (non-provider patterns) và kiểm tra bí mật còn hiệu lực (validity checks): cần gói **GitHub Secret Protection**.

---

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
