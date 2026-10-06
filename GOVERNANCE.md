# 🏛️ QUẢN TRỊ DỰ ÁN

Tài liệu này mô tả ai ra quyết định và cách thay đổi được chấp nhận trong **mọi repository** của **CÔNG TY TNHH TOÀN QUỲNH** trên GitHub, trừ khi repository đó có tệp `GOVERNANCE.md` riêng.

---

## 👥 VAI TRÒ

| Vai trò            | Quyền hạn và trách nhiệm                                                                                                                           |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Người quản trị** | Quyết định định hướng, duyệt và hợp nhất Pull Request, quản lý quyền truy cập, ruleset và phát hành. Danh sách: [`MAINTAINERS.md`](MAINTAINERS.md) |
| **Người đóng góp** | Báo lỗi, đề xuất, gửi Pull Request theo [`CONTRIBUTING.md`](CONTRIBUTING.md)                                                                       |
| **Chủ sở hữu mã**  | Người hoặc team trong `CODEOWNERS` của từng repository, bắt buộc phê duyệt thay đổi thuộc phần mình phụ trách                                      |

---

## 🗳️ CÁCH RA QUYẾT ĐỊNH

- Thay đổi thông thường: quyết định qua Pull Request — cần phê duyệt của chủ sở hữu mã và mọi kiểm tra tự động thành công.
- Thay đổi lớn (kiến trúc, quy ước chung, công cụ, quy trình): tạo Issue để trao đổi trước; người quản trị ra quyết định cuối cùng và ghi lại lý do trong Issue (repository `.github` ghi thêm bản ghi quyết định trong `docs/adr/`).
- Thay đổi quy ước dùng chung cho cả tổ chức (repository `.github`): chỉ người quản trị được hợp nhất; khi chuẩn bị phiên bản, thay đổi được tóm tắt cho người sử dụng trong mục **CHƯA PHÁT HÀNH** của `CHANGELOG.md`.

---

## 🔀 ĐÁNH GIÁ VÀ HỢP NHẤT

- Nhánh chính được bảo vệ bằng ruleset trong [`rulesets/`](rulesets/): bắt buộc Pull Request, phê duyệt, kiểm tra tự động, cho phép Merge và Squash (ưu tiên Squash; không Rebase — ADR 0006), commit có chữ ký.
- Người quản trị được bỏ qua yêu cầu phê duyệt khi không có người quản trị khác để duyệt. Với repository `.github`, tài khoản của người quản trị ([`MAINTAINERS.md`](MAINTAINERS.md)) nằm trong danh sách bỏ qua của ruleset (xem [ADR 0004](docs/adr/0004-protect-main-ruleset.md)) nhưng chỉ dùng khi thật cần: thay đổi thông thường vẫn qua Pull Request và kiểm tra tự động, không đẩy thẳng lên nhánh chính.
- Sửa lỗi khẩn cấp theo quy trình **Sửa lỗi khẩn cấp** trong [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## ➕ THAY ĐỔI NGƯỜI QUẢN TRỊ

- Thêm người quản trị: người quản trị hiện tại đề xuất qua Pull Request kèm lý do, sửa cùng lúc [`MAINTAINERS.md`](MAINTAINERS.md), `MAINTAINERS` trong [`scripts/orgsetup/teams.py`](scripts/orgsetup/teams.py) và `actor_id` trong danh sách bỏ qua của [`rulesets/protect-*.json`](rulesets/) (`validate.py` báo lỗi khi lệch). Sau khi hợp nhất, chạy `python3 scripts/org-setup.py team --apply` và `rulesets --apply`. `CODEOWNERS` dùng team `@TOANQUYNHLLC/maintainers` nên không cần sửa.
- Người quản trị nghỉ hoặc không còn tham gia: bỏ khỏi danh sách hiện tại trong `MAINTAINERS.md`, `teams.py` và danh sách bỏ qua của ruleset như trên rồi chạy `rulesets --apply`; gỡ khỏi các team và thu hồi quyền truy cập ngay trên web (`org-setup.py team` chỉ thêm người, không gỡ).
- Quyền truy cập GitHub cấp theo nguyên tắc tối thiểu: chỉ cấp quyền cần cho công việc.

---

## 📜 THAY ĐỔI TÀI LIỆU NÀY

Mọi thay đổi `GOVERNANCE.md` đi qua Pull Request, do người quản trị phê duyệt; khi chuẩn bị phiên bản, thay đổi được nêu trong mục **CHƯA PHÁT HÀNH** của `CHANGELOG.md`.

---

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
