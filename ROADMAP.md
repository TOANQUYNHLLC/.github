# 🗺️ LỘ TRÌNH

Các việc dự kiến cho repository `.github` và quy trình làm việc chung của **CÔNG TY TNHH TOÀN QUỲNH** trên GitHub. Lộ trình có thể thay đổi; đề xuất mới xin tạo Issue **✨ Đề xuất tính năng**.

---

## 🚧 KHI TẠO REPOSITORY MỚI

Hiện tổ chức chỉ có repository `.github`.

- [ ] Tạo repository ứng dụng đầu tiên (ví dụ mã nguồn website `toanquynh.com` hoặc API `api.toanquynh.com`), rồi chạy các bước dưới. Khi chọn **Private**, lưu ý giới hạn của gói GitHub Free: ruleset (**Protect Main**, **Protect Release Tags**) không được thực thi, báo cáo lỗ hổng riêng tư chỉ có ở repository công khai, secret scanning và push protection cần **GitHub Secret Protection** trên gói Team trở lên — `org-setup.py` cảnh báo các mục này rồi chạy tiếp.

Với mỗi repository mới, người quản trị chạy [`scripts/org-setup.py`](scripts/org-setup.py) (GitHub CLI đã đăng nhập; xem trước bằng `make org-preview`) theo thứ tự:

- [ ] `python3 scripts/org-setup.py files --apply --repo <tên>` — Pull Request thêm `.editorconfig`, `.gitattributes`, workflow kiểm tra tiêu đề, tên branch và gắn nhãn (`labeler.yml` kèm cấu hình — sửa đường dẫn nhãn `area: …` cho khớp dự án), `CODEOWNERS`, `dependabot.yml`, `release.yml` và tệp định dạng, phiên bản theo ngôn ngữ; đánh giá rồi hợp nhất. Chép tay `.env.example`, `PRIVACY.md` khi cần ([`repository-templates/`](repository-templates/)).
- [ ] `python3 scripts/org-setup.py settings --apply --repo <tên>` — cho phép Merge, Squash, tắt Rebase; tự xóa branch; bật Dependabot alerts và security updates, secret scanning, push protection, báo cáo lỗ hổng riêng tư, Release bất biến; quyền GitHub Actions.
- [ ] `python3 scripts/org-setup.py rulesets --apply --repo <tên>` — ruleset **Protect Release Tags** từ [`protect-release-tags.json`](rulesets/protect-release-tags.json) và **Protect Main** từ [`protect-main.json`](rulesets/protect-main.json), Protect Main chỉ giữ kiểm tra bắt buộc mà repository có job tương ứng.
- [ ] `python3 scripts/org-setup.py labels --apply --repo <tên>` — bộ nhãn chuẩn.
- [ ] Thêm workflow CodeQL từ [`workflow-templates/codeql.yml`](workflow-templates/codeql.yml) (**Actions → New workflow**, sửa danh sách ngôn ngữ theo dự án): ruleset Protect Main (Organization) bắt buộc kết quả code scanning của CodeQL khi tổ chức dùng gói Team.
- [ ] `python3 scripts/org-setup.py team --apply --repo <tên>` — cấp quyền cho các team (**maintainers** quyền **Maintain** để `CODEOWNERS` có hiệu lực).

---

## 🏢 CÀI ĐẶT TỔ CHỨC TRÊN WEB

GitHub không có API cho các mục này — người quản trị làm trên web (`python3 scripts/org-setup.py org-settings` báo các mục web khác `ORG_WEB_ONLY_SETTINGS`).

- [ ] Nhãn mặc định cho repository tạo mới: **Organization settings → Repository → General → Repository labels** — nhập đủ các nhãn theo [`labels.yml`](labels.yml) (tên, màu, mô tả). Nhãn mặc định chỉ áp cho repository tạo sau đó; repository đã có đồng bộ bằng `python3 scripts/org-setup.py labels --apply --repo <tên>`.

---

## 💡 CÂN NHẮC

- [ ] Bật GitHub Discussions cho các repository khác khi cần (`python3 scripts/org-setup.py settings --apply --repo <tên> --discussions`); `.github` đã bật, biểu mẫu có sẵn trong [`.github/DISCUSSION_TEMPLATE/`](.github/DISCUSSION_TEMPLATE/).
- [ ] Khi nâng lên gói **Team**: ruleset cấp tổ chức được thực thi — cân nhắc ADR mới để bỏ ruleset cấp repository trùng lặp.
- [ ] Xóa quy tắc kiểm tra bắt buộc rỗng (không chặn gì) của **Protect Release Tags (Organization)** trên web, rồi bỏ khỏi `orgTagRuleset()` trong [`scripts/orgsetup/rulesets.py`](scripts/orgsetup/rulesets.py) và sinh lại tệp.
- [ ] Code security configuration **GitHub recommended** (**Organization settings → Advanced Security → Configurations**): đã có nhưng chưa gắn repository nào và chưa là mặc định cho repository mới — đây là cách GitHub khuyên dùng thay cho bật từng tính năng (`org-setup.py settings`). Lưu ý cấu hình này bật code scanning default setup: cần bật GitHub Actions và không dùng chung với workflow CodeQL (advanced setup) của repository.
- [ ] Quét bí mật theo mẫu tùy chỉnh (non-provider patterns) và kiểm tra bí mật còn hiệu lực (validity checks): cần gói **GitHub Secret Protection**.

---

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
