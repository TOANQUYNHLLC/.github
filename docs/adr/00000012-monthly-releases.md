# 00000012. PHÁT HÀNH HẰNG THÁNG TỪ CHANGELOG.MD; PHIÊN BẢN THEO NGÀY VÀ SỐ THỨ TỰ

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Phiên bản cần có mốc nhận diện rõ ràng, nội dung dành cho người sử dụng và quy trình phát hành có thể chạy trên GitHub hoặc tại máy. Stable và Beta dùng cùng hệ thống số thứ tự.

## ✅ QUYẾT ĐỊNH

Workflow chuẩn bị bản Stable ngày **1 hằng tháng** khi có commit mới kể từ tag trước. `--channel Beta` chọn kênh thử nghiệm khi không truyền phiên bản cụ thể.

Phiên bản có dạng `Stable.vYYYY.MM.DDXXXX` hoặc `Beta.vYYYY.MM.DDXXXX`. Ngày hợp lệ theo ngày chuẩn bị ở Việt Nam; `XXXX` gồm 4 chữ số, từ `0001` đến `9999`, dùng chung hai kênh và bắt đầu lại mỗi tháng. Script chọn số tiếp theo từ các tag của tháng.

Branch dùng `release/stable.vYYYY.MM.DDXXXX` hoặc `release/beta.vYYYY.MM.DDXXXX`. PR mang nhãn `release`, `Pre-Release` và kênh tương ứng; Release Beta được đánh dấu thử nghiệm. Workflow và ruleset hỗ trợ nhóm tag `Stable.v*`, `Beta.v*`, `v*`.

`CHANGELOG.md` là khung nội dung đang chuẩn bị: mục **CHƯA PHÁT HÀNH** chứa tóm tắt cho người sử dụng và được chuyển thành mục phiên bản để tạo Release. Tệp không tích lũy nhật ký phát triển; nội dung các bản đã phát hành nằm ở GitHub Releases.

`scripts/release.py` chuẩn bị nội dung, mở PR có commit do GitHub ký và tạo Release. Người quản trị hợp nhất PR rồi gắn tag.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Phát hành theo mỗi thay đổi tạo quá nhiều phiên bản; lịch tùy ý khó duy trì. SHA hoặc giờ không thể hiện số lần phát hành trong tháng. Số thứ tự theo tháng phân biệt được nhiều bản Stable và Beta trong cùng kỳ.

## ⚖️ HỆ QUẢ

Mục CHƯA PHÁT HÀNH trống chặn chuẩn bị phát hành. Script cần đọc đủ tag trước khi chọn số thứ tự. Khi Actions tắt, dùng `make release-pr` và lệnh tạo Release tại máy. Workflow mẫu có thể dùng nội dung do GitHub sinh khi CHANGELOG chưa có mục của tag.
