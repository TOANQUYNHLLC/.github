# 0012. PHÁT HÀNH HẰNG THÁNG TỪ CHANGELOG.MD; PHIÊN BẢN THEO NGÀY VÀ SỐ THỨ TỰ

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Quy ước của tổ chức thay đổi liên tục; các repository khác cần một mốc ổn định để biết đã có gì mới. Phát hành theo từng thay đổi quá dày, còn phát hành tùy hứng thì dễ quên. Mỗi lần phát hành Stable hoặc Beta cần một tag riêng, có ngày chuẩn bị và số thứ tự trong tháng để nhận diện phiên bản.

## ✅ QUYẾT ĐỊNH

- Phát hành vào **ngày 1 hằng tháng**, chỉ khi có commit mới kể từ tag trước; mặc định chuẩn bị bản Stable, `--channel Beta` chọn bản Beta khi không truyền `--version`.
- Phiên bản có dạng `Stable.vYYYY.MM.DDXXXX` / `Beta.vYYYY.MM.DDXXXX`: năm, tháng và ngày theo ngày chuẩn bị phát hành ở Việt Nam; số thứ tự `XXXX` gồm 4 chữ số, từ `0001` đến `9999`. Ngày trong phiên bản phải có thật và trùng ngày chuẩn bị.
- Số thứ tự dùng chung cho Stable và Beta, bắt đầu lại từ `0001` mỗi tháng. Khi tự chọn phiên bản, script lấy số lớn nhất trong các tag đúng định dạng của tháng rồi tăng một, kể cả khi đổi ngày hoặc đổi kênh; báo lỗi nếu đã đạt `9999`.
- Branch phát hành có dạng `release/stable.vYYYY.MM.DDXXXX` / `release/beta.vYYYY.MM.DDXXXX`; Pull Request phát hành mang nhãn `release`, `Pre-Release` và nhãn kênh `Stable` hoặc `Beta`. GitHub Release của Beta được đánh dấu là bản thử nghiệm.
- Workflow phát hành và workflow mẫu nhận tag `Stable.v*`, `Beta.v*` và `v*`; ruleset tag bảo vệ cả ba nhóm ([ADR 0005](0005-protect-release-tags.md)).
- Nội dung lấy từ `CHANGELOG.md` theo cấu trúc tiêu đề phiên bản của Keep a Changelog: khi chuẩn bị phát hành, điền tóm tắt dành cho người sử dụng vào mục **CHƯA PHÁT HÀNH**; mục này chuyển thành mục của phiên bản được chuẩn bị để `release.yml` đọc khi gắn tag. Lần chuẩn bị sau bỏ mục đó: `CHANGELOG.md` không tích luỹ nhật ký thay đổi, lịch sử phát hành nằm ở GitHub Release. Parser cũng nhận tệp chỉ có mục **CHƯA PHÁT HÀNH**.
- `scripts/release.py` làm mọi bước: `prepare` chuyển mục, `open-pr` mở Pull Request phát hành có commit do GitHub ký (workflow `monthly-release.yml`; khi GitHub Actions tắt, `make release-pr` làm cả hai tại máy); người quản trị hợp nhất rồi gắn tag; `create` tạo GitHub Release từ mục của tag (workflow `release.yml`, hoặc chạy tại máy).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Phát hành theo từng thay đổi**: quá dày, mỗi Pull Request một phiên bản, repository khác khó theo dõi.
- **Phát hành khi người quản trị nhớ ra**: dễ quên, khoảng cách giữa các phiên bản không đều.
- **Số thứ tự tăng liên tục qua các tháng hoặc bắt đầu lại mỗi ngày**: chọn bắt đầu lại mỗi tháng để số thứ tự thể hiện lần phát hành trong tháng đó.
- **SHA commit hoặc giờ phát hành làm phiên bản**: chọn số thứ tự để phiên bản thể hiện thứ tự phát hành.

## ⚖️ HỆ QUẢ

- Có commit mà mục **CHƯA PHÁT HÀNH** trống thì không phát hành được; người quản trị chuẩn bị nội dung phiên bản trước khi chạy lệnh phát hành.
- Có thể chuẩn bị nhiều bản Stable và Beta trong cùng tháng với tag và branch riêng.
- Phải tải đầy đủ tag trước khi chọn số thứ tự: workflow hằng tháng checkout toàn bộ lịch sử; lệnh chạy tại máy tải tag trước khi tự chọn phiên bản.
- Workflow mẫu `release.yml` cho repository khác dùng cùng script; `CHANGELOG.md` chưa có mục của tag thì GitHub tự tạo nội dung từ các Pull Request.
