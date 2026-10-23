# 📦 NỘI DUNG PHÁT HÀNH

Tóm tắt dành cho người sử dụng của phiên bản đang chuẩn bị. Nội dung được chuyển từ mục **CHƯA PHÁT HÀNH** sang mục phiên bản khi chuẩn bị Release; lịch sử các bản đã công bố nằm ở [GitHub Releases](https://github.com/TOANQUYNHLLC/.github/releases). Quy trình và cách biên soạn trong [`README.md`](https://github.com/TOANQUYNHLLC/.github/blob/main/README.md#-phát-hành).

## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github)

### ✨ THÊM

- Bộ tài nguyên khởi đầu gồm hồ sơ tổ chức, hướng dẫn đóng góp, chính sách cộng đồng và biểu mẫu Issue, Discussion, Pull Request.
- Workflow mẫu theo công nghệ, cấu hình repository, nhãn và ruleset để thiết lập kiểm tra và quy trình cộng tác trong từng dự án.
- Môi trường đóng góp với Dev Container, Git hook và lệnh `make check` để kiểm tra nội dung, định dạng, scripts, workflows, quy ước Git và dependency trước khi gửi thay đổi.
- Quy trình chuẩn bị và công bố GitHub Release từ nội dung được duyệt; hai kênh Stable và Beta dùng chung số thứ tự theo tháng.
- [Hướng dẫn triển khai lên VPS](https://github.com/TOANQUYNHLLC/.github/blob/main/docs/vps-deployment.md): chuẩn bị máy chủ, khóa SSH giới hạn và workflow tự động triển khai mỗi khi Pull Request hợp nhất vào `main`, kèm kiểm tra sức khỏe và quay lại phiên bản trước.
- [Bộ công cụ quản trị cài đặt GitHub](https://github.com/TOANQUYNHLLC/.github/blob/main/docs/github-settings.md) (lệnh `make org-preview`, `make org-settings-apply` và nhóm lệnh quản trị tổ chức): nhập, đối chiếu, áp dụng và sao lưu cài đặt tổ chức, repository từ `github-settings.json`; đồng bộ team, nhãn, ruleset và tệp dùng chung cho các repository.

### 📌 LƯU Ý ÁP DỤNG

- Workflow mẫu lấy script của tổ chức theo tag phát hành ghi ở `ref` của bước checkout `TOANQUYNHLLC/.github`, không theo nhánh chính; repository đích nhận bản mới bằng cách đổi `ref` sang tag mới đã kiểm chứng. Workflow mẫu dùng được sau khi tag trong `ref` đã phát hành.
- Tổ chức bật GitHub Actions cho mọi repository, cho phép mọi action nhưng bắt buộc ghim theo commit SHA đầy đủ; action ghim theo tag hoặc nhánh bị GitHub chặn khi chạy.
- Repository mới tự bật secret scanning và push protection.
- Mẫu `dependabot.yml` chờ 30 ngày sau khi một phiên bản phát hành mới đề xuất cập nhật; validator yêu cầu `cooldown.default-days` tối thiểu 30 cho mọi hệ sinh thái. `make versions` theo dõi mọi action trong `.github/workflows/`, `workflow-templates/` và chỉ đề xuất bản phát hành đã ra đủ 30 ngày.
- Tệp cộng đồng và biểu mẫu làm mặc định khi repository đích thiếu bản riêng tương ứng. Workflow và cấu hình mẫu cần được chọn, chỉnh và commit trong từng dự án theo [hướng dẫn áp dụng](https://github.com/TOANQUYNHLLC/.github/blob/main/STRUCTURE.md).
- Người đóng góp thiết lập công cụ và Git hook theo [hướng dẫn tại máy](https://github.com/TOANQUYNHLLC/.github/blob/main/docs/local-checks.md), rồi chạy `make check` trước khi gửi thay đổi.

---

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
