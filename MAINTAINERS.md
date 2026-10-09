# 🧑‍💼 NGƯỜI QUẢN TRỊ

Người quản trị chịu trách nhiệm duy trì các repository của **CÔNG TY TNHH TOÀN QUỲNH**, đánh giá thay đổi, quản lý quyền truy cập và phát hành. Vai trò và quy trình quyết định theo [GOVERNANCE.md](GOVERNANCE.md).

## 👥 NGƯỜI QUẢN TRỊ HIỆN TẠI

| Họ và tên         | GitHub                                                     | Phạm vi                        |
| ----------------- | ---------------------------------------------------------- | ------------------------------ |
| Nguyễn Trọng Toàn | [@nguyentrongtoandl](https://github.com/nguyentrongtoandl) | Toàn bộ repository của tổ chức |
| Nguyễn Trọng Toàn | [@trongtoandl81](https://github.com/trongtoandl81)         | Toàn bộ repository của tổ chức |

Các tài khoản này thuộc [@TOANQUYNHLLC/maintainers](https://github.com/orgs/TOANQUYNHLLC/teams/maintainers), là chủ sở hữu mã trong `CODEOWNERS`. Danh sách phải khớp `MAINTAINERS` trong [teams.py](scripts/orgsetup/teams.py) và danh sách bỏ qua của ruleset cấp repository.

## 👪 CẤU TRÚC TEAM

| Team cha    | Team con                    | Phạm vi                                |
| ----------- | --------------------------- | -------------------------------------- |
| Engineering | Maintainers, Developers, QA | Phát triển và duy trì repository       |
| Creative    | Design, Marketing           | Thiết kế và truyền thông               |
| Admins      | Không có                    | Team độc lập, bí mật, quản trị tổ chức |

Engineering và Creative có chế độ `closed`, quyền `None` trong nguồn: script quản lý thông tin và cấu trúc, giữ nguyên thành viên và quyền repository. Các team có quyền cấu hình quản lý tài khoản quản trị với vai trò maintainer và quyền repository dưới đây.

| Team                                                                                  | Quyền trên repository | Phụ trách                                                                       |
| ------------------------------------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------- |
| [`@TOANQUYNHLLC/admins`](https://github.com/orgs/TOANQUYNHLLC/teams/admins) (bí mật)  | Admin                 | Quản trị Organization, repository, bảo mật và phân quyền                        |
| [`@TOANQUYNHLLC/maintainers`](https://github.com/orgs/TOANQUYNHLLC/teams/maintainers) | Maintain              | Duy trì repository, quản lý phát hành và kiểm duyệt Pull Request (`CODEOWNERS`) |
| [`@TOANQUYNHLLC/developers`](https://github.com/orgs/TOANQUYNHLLC/teams/developers)   | Write                 | Phát triển, review và duy trì mã nguồn                                          |
| [`@TOANQUYNHLLC/qa`](https://github.com/orgs/TOANQUYNHLLC/teams/qa)                   | Triage                | Quản lý issue, kiểm thử, xác nhận lỗi                                           |
| [`@TOANQUYNHLLC/design`](https://github.com/orgs/TOANQUYNHLLC/teams/design)           | Triage                | Thiết kế UI/UX, góp ý sản phẩm                                                  |
| [`@TOANQUYNHLLC/marketing`](https://github.com/orgs/TOANQUYNHLLC/teams/marketing)     | Read                  | Website, bài viết, hình ảnh truyền thông                                        |

## 🔄 ĐỒNG BỘ VÀ XÁC NHẬN

`TEAMS` và `TEAM_PARENTS` trong [teams.py](scripts/orgsetup/teams.py) là nguồn thông tin, quyền và quan hệ cha–con. Chạy `python3 scripts/org-setup.py team` để xem trước; thêm `--apply` để áp dụng, hoặc `--repo <tên>` để giới hạn repository.

Script kiểm tra cấu hình và trạng thái trước ghi, tạo team cha trước team con và xác nhận lại thông tin sau tạo/sửa. Cấu trúc không có chu trình; team cha và con phải `closed` theo [hợp đồng GitHub](https://docs.github.com/en/rest/teams/teams#update-a-team).

Membership phải đúng vai trò và `active`. Lời mời đã có đang `pending`, dữ liệu chưa rõ hoặc quyền tùy chỉnh chưa xếp hạng được chặn đồng bộ. Lời mời mới được báo riêng; lệnh xử lý các team còn lại rồi trả mã lỗi vì chưa hoàn tất. Quyền chuẩn cao hơn nguồn được giữ; sau cấp quyền phải đọc lại và xác nhận bằng hoặc cao hơn yêu cầu. Lỗi xác nhận dừng lệnh.

Script chỉ thêm người quản trị và cấp quyền; gỡ thành viên và thu hồi quyền theo quy trình trong [GOVERNANCE.md](GOVERNANCE.md).

## 📞 LIÊN HỆ

Dùng Issue **❓ Câu hỏi hoặc cần hỗ trợ** hoặc email [toanquynhvn@gmail.com](mailto:toanquynhvn@gmail.com). Báo cáo bảo mật riêng theo [SECURITY.md](SECURITY.md).

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
