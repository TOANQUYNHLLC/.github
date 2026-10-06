# 🔀 YÊU CẦU HỢP NHẤT MÃ NGUỒN

<!--
Cảm ơn bạn đã đóng góp cho dự án.
Mẫu dành cho Pull Request thêm, cập nhật hoặc thay thế dependency, công cụ hay GitHub Action.
Vui lòng điền đầy đủ các nội dung phù hợp và xóa những phần không áp dụng.
Không đưa mật khẩu, khóa API, token truy cập, dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế nhạy cảm vào Pull Request.
Vấn đề bảo mật: KHÔNG mô tả chi tiết lỗ hổng trong Pull Request công khai — báo cáo riêng qua tab Security → Report a vulnerability hoặc email toanquynhvn@gmail.com theo chính sách tại https://github.com/TOANQUYNHLLC/.github/blob/main/SECURITY.md
-->

## 📋 TÓM TẮT THAY ĐỔI

<!-- Mô tả ngắn gọn những nội dung đã thay đổi và kết quả mong muốn. -->

- Dependency, công cụ hoặc action bị ảnh hưởng:
- Phiên bản hoặc SHA hiện tại:
- Phiên bản hoặc SHA đề xuất:
- Tệp khai báo và lockfile liên quan:

## 🎯 MỤC ĐÍCH

<!-- Giải thích lý do cần thực hiện thay đổi này và vấn đề mà Pull Request giải quyết. -->

- Lý do thêm, cập nhật hoặc thay thế:
- Liên kết release notes, changelog hoặc thông báo chính thức của dependency:

## 🔗 VẤN ĐỀ LIÊN QUAN

<!-- Ví dụ: Closes #123, Fixes #123 hoặc Related to #123. -->

- Issue/Ticket:

## 🏷️ LOẠI THAY ĐỔI

<!-- Đánh dấu [x] vào các lựa chọn phù hợp. -->

- [ ] 🐛 Sửa lỗi
- [ ] ✨ Thêm tính năng mới
- [ ] ♻️ Tái cấu trúc hoặc cải thiện mã nguồn
- [ ] ⚡ Cải thiện hiệu năng
- [ ] 🎨 Thay đổi giao diện hoặc trải nghiệm người dùng
- [ ] 🔐 Cập nhật bảo mật
- [ ] 🗄️ Thay đổi cơ sở dữ liệu
- [ ] ⚙️ Thay đổi cấu hình, hạ tầng hoặc triển khai
- [ ] 📝 Cập nhật tài liệu
- [ ] 🧪 Bổ sung hoặc cập nhật kiểm thử
- [x] 🔧 Công việc bảo trì khác

## 📦 PHẠM VI ẢNH HƯỞNG

<!-- Đánh dấu các thành phần bị ảnh hưởng. -->

- [ ] Frontend
- [ ] Backend
- [ ] API
- [ ] Cơ sở dữ liệu
- [ ] Hệ thống xác thực hoặc phân quyền
- [ ] Hạ tầng hoặc quy trình triển khai
- [ ] Tài liệu
- [ ] Không ảnh hưởng đến chức năng hiện có

## 🛠️ NỘI DUNG ĐÃ THỰC HIỆN

<!-- Liệt kê những thay đổi chính để người đánh giá dễ kiểm tra. -->

- Thay đổi phá vỡ tương thích và cách xử lý:
- Yêu cầu runtime, cấu hình hoặc quyền mới:
- Điều kiện sử dụng dependency cần kiểm tra:
- Nguồn khai báo phiên bản và các nơi cần đồng bộ:

-
-
-

## 🧪 KIỂM THỬ

### CÁCH KIỂM THỬ

<!-- Mô tả các bước để kiểm tra thay đổi này. -->

1.
2.
3.

### KẾT QUẢ

- Kết quả cài đặt từ manifest và lockfile:
- Kết quả lint, kiểm thử và build với dependency mới:
- Kết quả kiểm tra lỗ hổng và tương thích liên quan:
- Phần chưa kiểm chứng và lý do:

- [ ] Đã kiểm thử trên môi trường phát triển
- [ ] Các kiểm thử tự động đã chạy thành công
- [ ] Đã kiểm tra các trường hợp biên liên quan
- [ ] Chưa thể kiểm thử đầy đủ và đã nêu rõ phần chưa kiểm chứng và lý do

## 📷 HÌNH ẢNH HOẶC VIDEO MINH HỌA

<!-- Bổ sung ảnh chụp màn hình hoặc video nếu thay đổi liên quan đến giao diện. -->

Không áp dụng.

## ⚠️ RỦI RO VÀ KHẢ NĂNG TƯƠNG THÍCH

<!-- Mô tả ảnh hưởng có thể xảy ra, thay đổi phá vỡ tương thích hoặc yêu cầu cập nhật dữ liệu. -->

- Mức độ rủi ro: Thấp / Trung bình / Cao
- Có thay đổi phá vỡ tương thích: Có / Không
- Có yêu cầu migration dữ liệu: Có / Không
- Có yêu cầu cập nhật biến môi trường: Có / Không

## ↩️ PHƯƠNG ÁN KHÔI PHỤC

<!-- Nêu cách hoàn tác hoặc khôi phục nếu thay đổi gây lỗi sau khi triển khai. -->

- Phiên bản hoặc SHA cần khôi phục:
- Manifest, lockfile và cấu hình phải hoàn tác cùng nhau:

## ✅ CHECKLIST TRƯỚC KHI GỬI

- [ ] Tôi đã tự kiểm tra lại mã nguồn và nội dung thay đổi.
- [ ] Thay đổi chỉ bao gồm những nội dung cần thiết cho Pull Request này.
- [ ] Mã nguồn tuân thủ quy ước và tiêu chuẩn của dự án.
- [ ] Tôi đã chạy formatter và lint của dự án, không còn lỗi.
- [ ] Tên branch, commit và tiêu đề Pull Request theo quy ước trong `CONTRIBUTING.md`.
- [ ] Tôi đã bổ sung hoặc cập nhật kiểm thử khi cần thiết.
- [ ] Tôi đã cập nhật tài liệu liên quan; nội dung phát hành trong `CHANGELOG.md` được cập nhật khi chuẩn bị phiên bản (nếu dự án có).
- [ ] Mã nguồn, tests, ví dụ cấu hình và tài liệu liên quan đã thống nhất; nội dung lỗi thời đã được cập nhật hoặc xoá trong cùng thay đổi.
- [ ] Tôi đã kiểm tra khả năng tương thích với chức năng hiện có.
- [ ] Tôi không đưa mật khẩu, khóa API, token truy cập hoặc thông tin bảo mật vào mã nguồn.
- [ ] Tôi không đưa dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế nhạy cảm vào repository.
- [ ] Tôi đã kiểm tra các tệp cấu hình và biến môi trường liên quan.
- [ ] Manifest, lockfile và các nguồn khai báo phiên bản liên quan đã thống nhất.
- [ ] Tôi đã đọc thông tin chính thức về thay đổi tương thích và yêu cầu mới.
- [ ] Tôi đã kiểm tra tác động bảo mật và quyền truy cập liên quan; GitHub Action được ghim SHA theo quy ước của dự án nếu áp dụng.
- [ ] Pull Request đã sẵn sàng để được đánh giá.

## 💬 GHI CHÚ CHO NGƯỜI ĐÁNH GIÁ

<!-- Nêu những phần cần được chú ý hoặc cần người đánh giá hỗ trợ kiểm tra kỹ hơn. -->

---

**CÔNG TY TNHH TOÀN QUỲNH**\
_Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm_
