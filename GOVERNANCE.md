# 🏛️ QUẢN TRỊ DỰ ÁN

Quy định vai trò, quyết định và quyền truy cập cho các repository của **CÔNG TY TNHH TOÀN QUỲNH**, trừ khi dự án có chính sách riêng. `GOVERNANCE.md` là chính sách tổ chức, không tự được GitHub sao chép vào repository đích.

## 👥 VAI TRÒ

| Vai trò        | Trách nhiệm                                                                                                                 |
| -------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Người quản trị | Định hướng, phê duyệt và hợp nhất PR, quản lý quyền, ruleset và phát hành; danh sách trong [MAINTAINERS.md](MAINTAINERS.md) |
| Chủ sở hữu mã  | Đánh giá phần phụ trách theo `CODEOWNERS` của repository                                                                    |
| Người đóng góp | Báo lỗi, đề xuất và gửi PR theo [CONTRIBUTING.md](CONTRIBUTING.md)                                                          |

## 🗳️ RA QUYẾT ĐỊNH

Thay đổi thông thường được xem xét qua Pull Request, cần phê duyệt của chủ sở hữu mã và các kiểm tra phù hợp. Thay đổi lớn về kiến trúc, quy ước, công cụ hoặc quy trình được trao đổi qua Issue trước; người quản trị quyết định cuối cùng.

Repository `.github` ghi quyết định chung trong [ADR](docs/adr/README.md), mỗi chủ đề một tài liệu hoàn chỉnh. Tài liệu vận hành mô tả hiện trạng; nội dung cho người sử dụng được chuẩn bị trong `CHANGELOG.md` khi phát hành.

## 🔀 ĐÁNH GIÁ VÀ HỢP NHẤT

Nhánh chính được bảo vệ theo [ruleset](rulesets/README.md) khi loại repository và gói GitHub hỗ trợ. Thay đổi qua PR, có phê duyệt, kiểm tra phù hợp và commit có chữ ký. Cấp repository cho phép Merge và Squash, ưu tiên Squash; không Rebase and merge theo [ADR 00000007](docs/adr/00000007-signed-commits-merge-methods.md).

Người quản trị chỉ dùng quyền bỏ qua ruleset khi thật cần, gồm trường hợp không có người quản trị khác để duyệt. Thay đổi thông thường vẫn qua PR và kiểm tra, không đẩy thẳng lên nhánh chính. Danh sách bỏ qua theo [ADR 00000004](docs/adr/00000004-protect-main.md).

Sửa lỗi khẩn cấp theo quy trình trong [CONTRIBUTING.md](CONTRIBUTING.md). Kiểm tra tại máy vẫn bắt buộc khi GitHub Actions tắt.

## 🔑 QUẢN LÝ QUYỀN TRUY CẬP

Quyền được cấp theo nhu cầu công việc. Mọi thay đổi người quản trị được đề xuất và duyệt qua PR; cập nhật cùng lúc:

- [MAINTAINERS.md](MAINTAINERS.md).
- `MAINTAINERS` trong [teams.py](scripts/orgsetup/teams.py).
- Danh sách bỏ qua của ruleset cấp repository trong [rulesets/](rulesets/).

Sau khi hợp nhất, áp dụng team bằng `python3 scripts/org-setup.py team --apply` và ruleset bằng `python3 scripts/org-setup.py rulesets --apply`. `CODEOWNERS` dùng team maintainers nên không cần liệt kê tài khoản riêng.

Khi người quản trị ngừng tham gia, cập nhật các nguồn trên và thu hồi membership, quyền truy cập trên GitHub. Lệnh team chỉ thêm người, không tự gỡ; việc sửa danh sách local chưa hoàn tất thu hồi quyền.

## 📝 DUY TRÌ CHÍNH SÁCH

Người quản trị phê duyệt thay đổi chính sách qua PR. Tài liệu, cấu hình và scripts liên quan phải thống nhất trong cùng thay đổi; nội dung phát hành chỉ được chuẩn bị khi phát hành phiên bản.

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
