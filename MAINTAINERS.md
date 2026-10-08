# 🧑‍💼 NGƯỜI QUẢN TRỊ

Danh sách người quản trị các repository của **CÔNG TY TNHH TOÀN QUỲNH** trên GitHub. Người quản trị thuộc team [`@TOANQUYNHLLC/maintainers`](https://github.com/orgs/TOANQUYNHLLC/teams/maintainers) — team được ghi trong `CODEOWNERS` nên mọi thành viên đều duyệt được Pull Request. Vai trò và quy trình thay đổi: xem [`GOVERNANCE.md`](GOVERNANCE.md).

---

## 👥 NGƯỜI QUẢN TRỊ HIỆN TẠI

| Họ và tên         | GitHub                                                     | Phạm vi                        |
| ----------------- | ---------------------------------------------------------- | ------------------------------ |
| Nguyễn Trọng Toàn | [@nguyentrongtoandl](https://github.com/nguyentrongtoandl) | Toàn bộ repository của tổ chức |
| Nguyễn Trọng Toàn | [@trongtoandl81](https://github.com/trongtoandl81)         | Toàn bộ repository của tổ chức |

## 👪 TEAM CỦA TỔ CHỨC

Người quản trị ở bảng trên được quản lý với vai trò maintainer trong các team có quyền repository ở bảng dưới. `python3 scripts/org-setup.py team` quản lý thông tin team, cấu trúc cha–con và cấp quyền trên mọi repository, giữ quyền đã cao hơn. Nguồn là `TEAMS` và `TEAM_PARENTS` trong [`scripts/orgsetup/teams.py`](scripts/orgsetup/teams.py).

Engineering và Creative là hai team cha ở cấp cao nhất, cùng chế độ hiển thị `closed`; Admins là team độc lập, bí mật. Engineering chứa Maintainers, Developers và QA; Creative chứa Design và Marketing. Hai team cha có quyền `None` trong nguồn local: lệnh chỉ quản lý tên, mô tả, chế độ hiển thị và vị trí trong cấu trúc, giữ nguyên thành viên và quyền repository của chúng.

Lệnh kiểm tra cấu trúc local, đọc đầy đủ trạng thái trước khi ghi và tạo team cha trước team con. Cấu trúc không được có chu trình; team cha và team con phải có chế độ hiển thị `closed`. Quan hệ dùng slug, được đọc lại sau khi tạo hoặc đổi team cha. Thành viên chỉ được tính khi đã `active`; lời mời `pending`, dữ liệu không đọc được hoặc quyền tùy chỉnh chưa xếp hạng được chặn đồng bộ. Lời mời mới được báo chờ chấp nhận cho đến khi GitHub xác nhận vai trò maintainer hoạt động. Cơ chế team lồng nhau xem [tài liệu GitHub](https://docs.github.com/en/rest/teams/teams#update-a-team).

| Team                                                                                  | Quyền trên repository | Phụ trách                                                                       |
| ------------------------------------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------- |
| [`@TOANQUYNHLLC/admins`](https://github.com/orgs/TOANQUYNHLLC/teams/admins) (bí mật)  | Admin                 | Quản trị Organization, repository, bảo mật và phân quyền                        |
| [`@TOANQUYNHLLC/maintainers`](https://github.com/orgs/TOANQUYNHLLC/teams/maintainers) | Maintain              | Duy trì repository, quản lý phát hành và kiểm duyệt Pull Request (`CODEOWNERS`) |
| [`@TOANQUYNHLLC/developers`](https://github.com/orgs/TOANQUYNHLLC/teams/developers)   | Write                 | Phát triển, review và duy trì mã nguồn                                          |
| [`@TOANQUYNHLLC/qa`](https://github.com/orgs/TOANQUYNHLLC/teams/qa)                   | Triage                | Quản lý issue, kiểm thử, xác nhận lỗi                                           |
| [`@TOANQUYNHLLC/design`](https://github.com/orgs/TOANQUYNHLLC/teams/design)           | Triage                | Thiết kế UI/UX, góp ý sản phẩm                                                  |
| [`@TOANQUYNHLLC/marketing`](https://github.com/orgs/TOANQUYNHLLC/teams/marketing)     | Read                  | Website, bài viết, hình ảnh truyền thông                                        |

---

## 📞 LIÊN HỆ

Liên hệ người quản trị qua Issue với biểu mẫu **❓ Câu hỏi hoặc cần hỗ trợ** hoặc email [toanquynhvn@gmail.com](mailto:toanquynhvn@gmail.com). Vấn đề bảo mật: làm theo [`SECURITY.md`](SECURITY.md).

---

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
