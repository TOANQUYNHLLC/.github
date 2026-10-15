# 🏛️ QUẢN TRỊ DỰ ÁN

Chính sách về vai trò, quyền quyết định và trách nhiệm duy trì các repository của **CÔNG TY TNHH TOÀN QUỲNH**. Dự án có chính sách riêng áp dụng tài liệu của dự án đó; GitHub không tự sao chép `GOVERNANCE.md` vào repository đích.

## 👥 VAI TRÒ

| Vai trò        | Trách nhiệm                                                                                                               |
| -------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Người quản trị | Định hướng, phê duyệt và hợp nhất PR; quản lý quyền, ruleset và phát hành; danh sách tại [MAINTAINERS.md](MAINTAINERS.md) |
| Chủ sở hữu mã  | Đánh giá thành phần phụ trách theo `CODEOWNERS`                                                                           |
| Người đóng góp | Báo lỗi, đề xuất và gửi PR theo [CONTRIBUTING.md](CONTRIBUTING.md)                                                        |

## 🗳️ QUYẾT ĐỊNH VÀ PHÊ DUYỆT

Thay đổi thông thường được xem xét trong Pull Request. Thay đổi lớn về kiến trúc, quy ước, công cụ hoặc quy trình cần trao đổi qua Issue trước khi thực hiện; người quản trị quyết định cuối cùng.

Các quyết định của repository `.github` nằm trong [ADR](docs/adr/README.md). Mỗi chủ đề có một bản mô tả hiện hành với lý do và hệ quả, còn tài liệu vận hành hướng dẫn sử dụng bộ tài nguyên.

## 🔀 HỢP NHẤT VÀ PHÁT HÀNH

Thay đổi đi qua PR có phê duyệt, kiểm tra phù hợp và commit có chữ ký. Mẫu [ruleset](rulesets/README.md) được áp dụng khi loại repository và gói GitHub hỗ trợ. Merge, Squash và Rebase phải đáp ứng các bảo vệ đang có hiệu lực; ưu tiên Squash theo [ADR 00000007](docs/adr/00000007-signed-commits-merge-methods.md).

Quyền bỏ qua ruleset chỉ dùng khi thật cần, gồm trường hợp không có người quản trị khác để duyệt. Thay đổi thông thường vẫn phải qua PR, không đẩy trực tiếp lên nhánh chính. Kiểm tra tại máy bắt buộc cả khi Actions tắt. Sửa lỗi khẩn cấp theo [hướng dẫn đóng góp](CONTRIBUTING.md); phát hành theo [README](README.md#-phát-hành).

Người quản trị xác nhận nguồn chạy các checks bắt buộc trước khi áp dụng ruleset. Kết quả tại máy không thay thế status checks của GitHub; khi Actions tắt, PR có thể chờ các job được yêu cầu. Chính sách và điều kiện áp dụng nằm trong [hướng dẫn ruleset](rulesets/README.md#-kiểm-tra-bắt-buộc).

## 🔑 QUYỀN TRUY CẬP

Cấp quyền theo nhu cầu công việc. Khi thay đổi người quản trị, đề xuất qua PR và đồng bộ:

- Danh sách trong [MAINTAINERS.md](MAINTAINERS.md).
- `MAINTAINERS` trong [maintainers.py](scripts/maintainers.py).
- Danh sách bỏ qua của mẫu ruleset cấp repository trong [rulesets/](rulesets/).

Sau khi hợp nhất, người quản trị cấp hoặc thu hồi quyền trên GitHub, xác minh thành viên team và ruleset. `CODEOWNERS` dùng team maintainers làm chủ sở hữu mã. Khi một người ngừng tham gia, phải xác nhận thu hồi quyền thực tế bên cạnh cập nhật nguồn đối chiếu công khai.

## 📝 DUY TRÌ CHÍNH SÁCH

Thay đổi chính sách được phê duyệt qua PR cùng mã nguồn, cấu hình và hướng dẫn liên quan. Nội dung phiên bản được chuẩn bị trong `CHANGELOG.md` theo quy trình phát hành.

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
