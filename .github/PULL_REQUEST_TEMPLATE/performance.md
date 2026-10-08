# 🔀 YÊU CẦU HỢP NHẤT MÃ NGUỒN

<!--
Cảm ơn bạn đã đóng góp cho dự án.
Mẫu dành cho tối ưu hiệu năng có số liệu trước/sau và cách đo có thể tái hiện.
Vui lòng điền đầy đủ các nội dung phù hợp và xóa những phần không áp dụng.
Không đưa mật khẩu, khóa API, token truy cập, dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế nhạy cảm vào Pull Request.
Vấn đề bảo mật: KHÔNG mô tả chi tiết lỗ hổng trong Pull Request công khai — báo cáo riêng qua tab Security → Report a vulnerability hoặc email toanquynhvn@gmail.com theo chính sách tại https://github.com/TOANQUYNHLLC/.github/blob/main/SECURITY.md
-->

## 📋 TÓM TẮT THAY ĐỔI

<!-- Mô tả ngắn gọn những nội dung đã thay đổi và kết quả mong muốn. -->

- Luồng xử lý và điểm nghẽn cần tối ưu:
- Chỉ số mục tiêu, giá trị hiện tại và ngưỡng chấp nhận:
- Hành vi chức năng và yêu cầu bảo mật cần giữ nguyên:

## 🎯 MỤC ĐÍCH

<!-- Giải thích lý do cần thực hiện thay đổi này và vấn đề mà Pull Request giải quyết. -->

- Bằng chứng xác định điểm nghẽn:
- Tình huống sử dụng hoặc mức tải được hưởng lợi:

## 🔗 VẤN ĐỀ LIÊN QUAN

<!-- Ví dụ: Closes #123, Fixes #123 hoặc Related to #123. -->

- Issue/Ticket:

## 🏷️ LOẠI THAY ĐỔI

<!-- Đánh dấu [x] vào các lựa chọn phù hợp. -->

- [ ] 🐛 Sửa lỗi
- [ ] ✨ Thêm tính năng mới
- [ ] ♻️ Tái cấu trúc hoặc cải thiện mã nguồn
- [x] ⚡ Cải thiện hiệu năng
- [ ] 🎨 Thay đổi giao diện hoặc trải nghiệm người dùng
- [ ] 🔐 Cập nhật bảo mật
- [ ] 🗄️ Thay đổi cơ sở dữ liệu
- [ ] ⚙️ Thay đổi cấu hình, hạ tầng hoặc triển khai
- [ ] 📝 Cập nhật tài liệu
- [ ] 🧪 Bổ sung hoặc cập nhật kiểm thử
- [ ] 🔧 Công việc bảo trì khác

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

- Thay đổi thuật toán, truy vấn, tài nguyên hoặc cache:
- Chi phí hoặc đánh đổi về bộ nhớ, CPU, độ trễ và khả năng bảo trì:
- Điều kiện cập nhật/vô hiệu hóa cache và ảnh hưởng đến tính nhất quán (nếu có):

-
-
-

## 🧪 KIỂM THỬ

### CÁCH KIỂM THỬ

<!-- Mô tả các bước để kiểm tra thay đổi này. -->

<!-- Chọn chỉ số phù hợp: độ trễ, thông lượng, CPU, bộ nhớ, truy vấn hoặc thời gian khởi động. Dùng dữ liệu giả lập; không đính kèm dữ liệu sản xuất hoặc thông tin nhạy cảm. -->

- Commit trước/sau và lệnh chạy benchmark:
- Môi trường: phần cứng, hệ điều hành, runtime/dependency và cấu hình:
- Dữ liệu, khối lượng công việc, mức đồng thời và thời lượng đo:
- Số lần lặp, giai đoạn làm nóng và trạng thái cache:
- Cách giữ điều kiện đo trước/sau tương đương và xử lý nhiễu:
- Cách kiểm tra tính đúng đắn, quyền truy cập và các tình huống có thể bị chậm hơn:

1.
2.
3.

### KẾT QUẢ

<!-- Ghi đơn vị, cách tổng hợp (ví dụ trung vị hoặc p95 khi phù hợp) và độ biến động; không chỉ chọn lần chạy tốt nhất. Số liệu và log đã lọc thông tin nhạy cảm đặt trong PR hoặc artifact, không ghi thành nhật ký vào tài liệu dự án. -->

| Chỉ số và đơn vị | Trước thay đổi | Sau thay đổi | Chênh lệch | Ngưỡng chấp nhận |
| ---------------- | -------------- | ------------ | ---------- | ---------------- |
|                  |                |              |            |                  |

- Số lần đo và độ biến động của kết quả:
- Kết quả kiểm thử chức năng và kiểm thử hồi quy hiệu năng:
- Tình huống chậm hơn hoặc tiêu thụ nhiều tài nguyên hơn:
- Giới hạn của benchmark và phần chưa thể kiểm chứng:

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

- Nguy cơ tăng tài nguyên, sai dữ liệu, lỗi cache hoặc giảm hiệu năng ở mức tải khác:
- Chỉ số theo dõi sau triển khai và ngưỡng dừng/khôi phục:

## ↩️ PHƯƠNG ÁN KHÔI PHỤC

<!-- Nêu cách hoàn tác hoặc khôi phục nếu thay đổi gây lỗi sau khi triển khai. -->

- Cách tắt tối ưu hoặc khôi phục mã nguồn/cấu hình:
- Cách xử lý cache hoặc trạng thái phát sinh (nếu có):
- Cách kiểm tra chức năng và đo lại để xác nhận hệ thống phục hồi:

## ✅ CHECKLIST TRƯỚC KHI GỬI

- [ ] Tôi đã tự kiểm tra lại mã nguồn và nội dung thay đổi.
- [ ] Thay đổi chỉ bao gồm những nội dung cần thiết cho Pull Request này.
- [ ] Mã nguồn tuân thủ quy ước và tiêu chuẩn của dự án.
- [ ] Tôi đã chạy formatter và lint của dự án, không còn lỗi.
- [ ] Tên branch, commit và tiêu đề Pull Request theo quy ước trong `CONTRIBUTING.md`.
- [ ] Tôi đã bổ sung hoặc cập nhật kiểm thử khi cần thiết.
- [ ] Tôi đã cập nhật tài liệu liên quan; nội dung phát hành trong `CHANGELOG.md` được cập nhật khi chuẩn bị phiên bản (nếu dự án có).
- [ ] Tôi đã rà soát toàn bộ dự án và sửa mọi chỗ liên quan tới thay đổi; mã nguồn, tests, ví dụ cấu hình và tài liệu liên quan đã thống nhất, nội dung lỗi thời đã được cập nhật hoặc xoá trong cùng thay đổi.
- [ ] Tôi đã kiểm tra khả năng tương thích với chức năng hiện có.
- [ ] Tôi không đưa mật khẩu, khóa API, token truy cập hoặc thông tin bảo mật vào mã nguồn.
- [ ] Tôi không đưa dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế nhạy cảm vào repository.
- [ ] Tôi đã kiểm tra các tệp cấu hình và biến môi trường liên quan.
- [ ] Tôi đã cung cấp lệnh, môi trường và dữ liệu benchmark có thể tái hiện.
- [ ] Tôi đã đối chiếu trước/sau trong điều kiện tương đương, nêu số lần đo và độ biến động.
- [ ] Tôi đã kiểm tra tối ưu giữ đúng kết quả, quyền truy cập và hành vi hiện có.
- [ ] Tôi đã nêu đánh đổi tài nguyên, tình huống chậm hơn, giới hạn đo và phương án khôi phục.
- [ ] Pull Request đã sẵn sàng để được đánh giá.

## 💬 GHI CHÚ CHO NGƯỜI ĐÁNH GIÁ

<!-- Nêu những phần cần được chú ý hoặc cần người đánh giá hỗ trợ kiểm tra kỹ hơn. -->

---

**CÔNG TY TNHH TOÀN QUỲNH**\
_Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm_
