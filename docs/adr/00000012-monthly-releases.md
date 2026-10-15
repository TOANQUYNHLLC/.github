# 00000012. PHÁT HÀNH HẰNG THÁNG TỪ CHANGELOG.MD; PHIÊN BẢN THEO NGÀY VÀ SỐ THỨ TỰ

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Bản phát hành cần có định danh theo ngày, nội dung dành cho người sử dụng và quy trình có thể chạy tại máy hoặc trên GitHub. Stable và Beta cần dùng chung cách đánh số.

## ✅ QUYẾT ĐỊNH

Phiên bản có dạng `Stable.vYYYY.MM.DDXXXX` hoặc `Beta.vYYYY.MM.DDXXXX`. Ngày là ngày chuẩn bị tại Việt Nam; `XXXX` từ `0001` đến `9999`, tăng chung cho hai kênh và bắt đầu lại theo tháng. Script chọn số sau khi tải các tag cần thiết từ origin.

`CHANGELOG.md` chuẩn bị nội dung trong mục CHƯA PHÁT HÀNH. Nhóm theo THÊM, THAY ĐỔI, SỬA LỖI, BẢO MẬT, NGỪNG HỖ TRỢ, LOẠI BỎ; chỉ dùng nhóm có nội dung. Mục LƯU Ý ÁP DỤNG mô tả điều kiện thiết lập hoặc nâng cấp. Tiêu đề viết HOA, liên kết dùng URL tuyệt đối.

Bản đầu tiên được chuẩn bị trên branch phát hành, kiểm tra và hợp nhất trước khi gắn tag. Liên kết CHƯA PHÁT HÀNH ban đầu trỏ tới repository. Với các bản tiếp theo, PR tổng hợp nội dung CHƯA PHÁT HÀNH được hợp nhất vào `main` trước bước chuẩn bị phiên bản. Lệnh `make release-pr` yêu cầu `main` sạch, trùng `origin/main`; đọc nội dung đã hợp nhất, mở PR phiên bản rồi khôi phục tệp tại máy. `scripts/release.py` dùng tag trước làm mốc đếm commit mới.

Khi Actions bật, workflow đặt lịch lúc 07:00 giờ Việt Nam ngày 1 hằng tháng, mở PR Stable khi có tag trước đó, commit mới và nội dung CHƯA PHÁT HÀNH. Branch là `release/<phiên bản viết thường>`; PR có nhãn `release`, `Pre-Release` và kênh. `--channel Beta` chọn bản thử nghiệm khi không truyền phiên bản cụ thể; Release Beta có cờ prerelease.

Khi chuẩn bị, nội dung được chuyển thành mục phiên bản có ngày và mục CHƯA PHÁT HÀNH được để trống. Tệp giữ mục phiên bản vừa chuẩn bị đến lần chuẩn bị kế tiếp; nội dung bản đã công bố nằm tại GitHub Releases. Người quản trị hợp nhất PR rồi gắn tag để công bố.

Nguồn của quyết định: [scripts/release.py](../../scripts/release.py), [CHANGELOG.md](../../CHANGELOG.md), [.github/workflows/monthly-release.yml](../../.github/workflows/monthly-release.yml), [.github/workflows/release.yml](../../.github/workflows/release.yml).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Ngày và số thứ tự phân biệt được các bản trong cùng tháng, kể cả khi dùng hai kênh. Lịch hằng tháng tạo mốc chuẩn bị ổn định; lệnh tại máy phục vụ khi Actions tắt. Tóm tắt theo ảnh hưởng sử dụng giúp người nhận bản phát hành biết cần làm gì.

## ⚖️ HỆ QUẢ

Mục nội dung trống hoặc không hợp lệ chặn chuẩn bị. Commit phát hành qua API được GitHub ký. Tag và Release tuân theo [ADR 00000006](00000006-protect-release-tags.md). Các bước vận hành nằm trong [README](../../README.md#-phát-hành); CHANGELOG không chứa log phát triển hoặc kết quả rà soát.
