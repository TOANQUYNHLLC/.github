# 0014. SỐ THỨ TỰ PHÁT HÀNH TRONG THÁNG

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-10-04
- **Điều chỉnh:** [0012](0012-monthly-releases.md) — định dạng phiên bản và tên branch phát hành; [0005](0005-protect-release-tags.md) — phạm vi tag được bảo vệ.

## 📌 BỐI CẢNH

Mỗi lần phát hành Stable hoặc Beta cần một tag riêng, có ngày chuẩn bị và số thứ tự trong tháng để nhận diện phiên bản.

## ✅ QUYẾT ĐỊNH

- Phiên bản có dạng `Stable.vYYYY.MM.DDXXXX` / `Beta.vYYYY.MM.DDXXXX`: năm, tháng và ngày theo ngày chuẩn bị phát hành ở Việt Nam; số thứ tự `XXXX` gồm 4 chữ số, từ `0001` đến `9999`. Ngày trong phiên bản phải có thật và trùng ngày chuẩn bị.
- Số thứ tự dùng chung cho Stable và Beta, bắt đầu lại từ `0001` mỗi tháng. Khi tự chọn phiên bản, script lấy số lớn nhất trong các tag đúng định dạng của tháng rồi tăng một, kể cả khi đổi ngày hoặc đổi kênh; báo lỗi nếu đã đạt `9999`.
- Pull Request phát hành mang nhãn `Pre-Release` và nhãn kênh `Stable` hoặc `Beta`; bộ nhãn chuẩn và cấu hình gắn nhãn dùng tên thống nhất.
- Mặc định chuẩn bị bản Stable; `--channel Beta` chọn bản Beta khi không truyền `--version`. GitHub Release của Beta được đánh dấu là bản thử nghiệm.
- Branch phát hành có dạng `release/stable.vYYYY.MM.DDXXXX` / `release/beta.vYYYY.MM.DDXXXX`, tương ứng với phiên bản được chuẩn bị và tuân thủ quy ước chữ thường của tên branch.
- Workflow phát hành và workflow mẫu nhận tag `Stable.v*`, `Beta.v*` và `v*` cũ. Ruleset cấp repository và cấp tổ chức bảo vệ cả ba nhóm tag, giữ các quy tắc chặn tạo, cập nhật, xóa, force push và yêu cầu chữ ký.
- Giữ lịch phát hành ngày 1 hằng tháng và quy trình lấy nội dung từ `CHANGELOG.md` của ADR 0012.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Số thứ tự tăng liên tục qua các tháng hoặc bắt đầu lại mỗi ngày:** chọn cách bắt đầu lại mỗi tháng để số thứ tự thể hiện lần phát hành trong tháng đó.
- **SHA commit hoặc giờ phát hành:** chọn số thứ tự để phiên bản thể hiện thứ tự phát hành.

## ⚖️ HỆ QUẢ

- Có thể chuẩn bị nhiều bản Stable và Beta trong cùng tháng với tag và branch riêng.
- Phải tải đầy đủ tag trước khi chọn số thứ tự. Workflow hằng tháng checkout toàn bộ lịch sử; lệnh mở Pull Request tại máy tải tag trước khi tự chọn phiên bản.
- `--version` nhận phiên bản đúng định dạng, với ngày chuẩn bị hợp lệ. Nội dung dành cho người sử dụng được chuẩn bị trong mục **CHƯA PHÁT HÀNH** của `CHANGELOG.md`; tài liệu dự án không chứa nhật ký phát triển hoặc báo cáo kiểm tra.
