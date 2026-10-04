# 0012. PHÁT HÀNH HẰNG THÁNG TỪ CHANGELOG.MD

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Quy ước của tổ chức thay đổi liên tục; các repository khác cần một mốc ổn định để biết đã có gì mới. Phát hành theo từng thay đổi quá dày, còn phát hành tùy hứng thì dễ quên.

## ✅ QUYẾT ĐỊNH

- Phát hành vào **ngày 1 hằng tháng**, chỉ khi có commit mới kể từ tag trước; phiên bản `vYYYY.MM.Stable` theo tháng phát hành.
- Nội dung lấy từ `CHANGELOG.md` (định dạng Keep a Changelog): thay đổi ghi vào mục **CHƯA PHÁT HÀNH**; khi phát hành, mục này chuyển thành phiên bản của tháng.
- `scripts/release.py` làm mọi bước: `prepare` chuyển mục, `open-pr` mở Pull Request phát hành có commit do GitHub ký (workflow `monthly-release.yml`; khi GitHub Actions tắt, `make release-pr` làm cả hai tại máy); người quản trị hợp nhất rồi gắn tag; `create` tạo GitHub Release từ mục của tag (workflow `release.yml`, hoặc chạy tại máy).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Phát hành theo từng thay đổi**: quá dày, mỗi Pull Request một phiên bản, repository khác khó theo dõi.
- **Phát hành khi người quản trị nhớ ra**: dễ quên, khoảng cách giữa các phiên bản không đều.

## ⚖️ HỆ QUẢ

- Có commit mà mục **CHƯA PHÁT HÀNH** trống thì không phát hành được — thay đổi đáng chú ý phải được ghi ngay khi hợp nhất.
- Workflow mẫu `release.yml` cho repository khác dùng cùng script; `CHANGELOG.md` chưa có mục của tag thì GitHub tự tạo nội dung từ các Pull Request.
