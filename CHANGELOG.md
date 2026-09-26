# 📝 NHẬT KÝ THAY ĐỔI

Mọi thay đổi đáng chú ý của repository `.github` thuộc **CÔNG TY TNHH TOÀN QUỲNH** được ghi tại đây.

Định dạng theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Phiên bản đặt theo năm và tháng phát hành, ví dụ `v2026.09.Stable`. Thay đổi mới ghi vào mục **CHƯA PHÁT HÀNH**, rồi chuyển sang một phiên bản khi gắn tag.

---

## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github/compare/v2026.09.Stable...HEAD)

### ✨ THÊM

- `SECURITY.md` — chính sách bảo mật áp dụng cho mọi repository của tổ chức: thông tin cần cung cấp, cách gửi báo cáo kèm liên kết soạn email sẵn mẫu, cam kết xử lý và phiên bản được hỗ trợ.
- `CONTRIBUTING.md` — hướng dẫn đóng góp: quy trình, quy ước đặt tên branch, quy ước commit và yêu cầu đối với Pull Request.
- `CODE_OF_CONDUCT.md` — quy tắc ứng xử trong không gian cộng tác của tổ chức.
- `SUPPORT.md` — bảng chọn kênh hỗ trợ theo nhu cầu.
- `CHANGELOG.md` — nhật ký thay đổi của repository.
- `ISSUE_TEMPLATE/` — ba biểu mẫu Issue dạng form có trường bắt buộc (🐛 Báo lỗi, ✨ Đề xuất tính năng, ❓ Câu hỏi hoặc cần hỗ trợ) và `config.yml` tắt Issue trống, thêm liên kết báo cáo bảo mật và liên hệ công ty.
- `workflow-templates/` — workflow mẫu dùng chung: Node.js CI và kiểm tra liên kết tài liệu.
- `labels.yml` và `scripts/sync-labels.sh` — bộ 15 nhãn chuẩn và công cụ đồng bộ lên các repository (mặc định chỉ xem trước).
- CI `.github/workflows/validate.yml` — kiểm tra nội dung bằng `scripts/validate.py` và lint bằng yamllint, shellcheck, actionlint.
- `.github/dependabot.yml` — tự động đề xuất cập nhật các GitHub Action ghim theo commit SHA.
- `.github/CODEOWNERS` — bắt buộc người quản trị duyệt mọi thay đổi.
- `Makefile` — `make check` chạy toàn bộ kiểm tra giống CI trên máy cục bộ.
- `.editorconfig`, `.gitattributes`, `.gitignore`, `.yamllint.yml` — quy ước định dạng: UTF-8, xuống dòng LF, thụt lề bằng tab độ rộng 4; YAML bắt buộc dùng dấu cách nên dùng dấu cách, mỗi cấp 4. `scripts/validate.py` kiểm tra quy tắc này trên mọi loại file.
- `profile/README.md` — badge liên hệ và phần giới thiệu tiếng Anh (**ABOUT US**).
- Quy trình phát hành: workflow `release.yml` tự tạo GitHub Release khi gắn tag, nội dung lấy từ `CHANGELOG.md` qua `scripts/release-notes.py`.
- Workflow `pr-title.yml` bắt buộc tiêu đề Pull Request theo quy ước commit.
- Workflow `links.yml` và `scripts/check-external-links.py` kiểm tra liên kết bên ngoài hằng tuần.
- `scripts/test_validate.py` — 17 test tự động cho các script kiểm tra.
- `.well-known/security.txt` (RFC 9116) với email chung của công ty.
- `scripts/validate.py` khoá email chung `toanquynhvn@gmail.com`, kiểm tra hạn `security.txt` và cấu trúc `CHANGELOG.md`.
- `make help` (mặc định khi gõ `make`), `make test`, `make links`, `make release-notes`; `make lint` báo rõ công cụ còn thiếu.

### ♻️ THAY ĐỔI

- `README.md` tập trung vào chính repository: cách GitHub áp dụng nội dung cho toàn tổ chức, cấu trúc theo nhóm, hướng dẫn phát triển cục bộ; giới thiệu công ty và thông tin liên hệ đầy đủ chuyển về `profile/README.md`.
- Mục bảo mật trong `README.md` rút gọn, nội dung chi tiết chuyển sang `SECURITY.md`.
- Mẫu nội dung email báo cáo bảo mật bổ sung trường **Thông tin liên hệ của người báo cáo**; liên kết soạn email khớp hoàn toàn với mẫu.
- Tiêu đề trong mọi tài liệu và biểu mẫu viết hoa thống nhất.
- Cảnh báo dữ liệu nhạy cảm thống nhất một cách diễn đạt trên mọi tài liệu, bổ sung **token truy cập**.
- Biểu mẫu Pull Request trỏ tới chính sách bảo mật bằng liên kết tuyệt đối, dùng được từ mọi repository.
- `profile/README.md` thống nhất tên **Phòng khám chuyên khoa Nhi DR. MOON**.

### 🗑️ LOẠI BỎ

- `ISSUE_TEMPLATE.md` dạng một tệp — thay bằng thư mục biểu mẫu `ISSUE_TEMPLATE/`.

---

## [v2026.09.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2026.09.Stable) — 2026-09-26

### ✨ THÊM

- `profile/README.md` — trang giới thiệu CÔNG TY TNHH TOÀN QUỲNH trên GitHub: giới thiệu chung, câu chuyện thương hiệu, lĩnh vực hoạt động, tầm nhìn, sứ mệnh, giá trị cốt lõi, dự án Phòng khám chuyên khoa Nhi DR. MOON và thông tin liên hệ.
- `README.md` — mục đích, cấu trúc và nguyên tắc quản lý repository `.github`.
- `PULL_REQUEST_TEMPLATE.md` — biểu mẫu Pull Request mặc định cho toàn tổ chức.
- `LICENSE` — giấy phép MIT.

---

<p align="center">
	<strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
	Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
