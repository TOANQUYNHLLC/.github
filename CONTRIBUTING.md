# 🤝 HƯỚNG DẪN ĐÓNG GÓP

Hướng dẫn này áp dụng cho **mọi repository** của **CÔNG TY TNHH TOÀN QUỲNH** trên GitHub, trừ khi repository đó có tệp `CONTRIBUTING.md` riêng.

Cảm ơn bạn đã dành thời gian đóng góp cho dự án. Khi tham gia, bạn đồng ý tuân thủ [Quy tắc ứng xử](CODE_OF_CONDUCT.md). Cần hỗ trợ? Xem [`SUPPORT.md`](SUPPORT.md).

---

## 📋 TRƯỚC KHI BẮT ĐẦU

- Đọc `README.md` của repository để nắm mục đích, cách cài đặt và quy ước riêng của dự án.
- Tìm trong Issues xem vấn đề hoặc ý tưởng đã được nêu chưa, tránh tạo trùng lặp.
- Với thay đổi lớn, tạo Issue để trao đổi hướng xử lý trước khi viết mã.
- Vấn đề bảo mật **không** tạo Issue công khai — làm theo [`SECURITY.md`](SECURITY.md).

---

## 🐛 BÁO LỖI VÀ ĐỀ XUẤT

Tạo Issue mới và chọn biểu mẫu phù hợp:

| Biểu mẫu | Khi nào dùng |
|---|---|
| 🐛 Báo lỗi | Một chức năng chạy sai, không chạy hoặc hiển thị không đúng |
| ✨ Đề xuất tính năng | Ý tưởng mới hoặc cải thiện chức năng, giao diện, hiệu năng, tài liệu |
| ❓ Câu hỏi hoặc cần hỗ trợ | Cần hỏi về cách sử dụng, cấu hình hoặc hoạt động của dự án |

---

## 🔀 QUY TRÌNH ĐÓNG GÓP MÃ NGUỒN

1. Tạo branch mới từ nhánh chính (`main`), đặt tên theo quy ước bên dưới.
2. Thực hiện thay đổi, giữ phạm vi nhỏ và tập trung vào một mục đích.
3. Tự kiểm thử và chạy các kiểm tra tự động của dự án.
4. Cập nhật tài liệu liên quan khi hành vi, cấu hình hoặc giao diện thay đổi; ghi thay đổi vào `CHANGELOG.md` nếu dự án có tệp này.
5. Tạo Pull Request và điền đầy đủ biểu mẫu có sẵn.
6. Phản hồi góp ý của người đánh giá; Pull Request chỉ được hợp nhất khi đã được phê duyệt.

---

## 🌿 QUY ƯỚC ĐẶT TÊN BRANCH

| Tiền tố | Mục đích | Ví dụ |
|---|---|---|
| `feature/` | Tính năng mới | `feature/dat-lich-kham` |
| `fix/` | Sửa lỗi | `fix/loi-dang-nhap` |
| `docs/` | Tài liệu | `docs/cap-nhat-readme` |
| `refactor/` | Tái cấu trúc, không đổi hành vi | `refactor/tach-module-thanh-toan` |
| `chore/` | Cấu hình, phụ thuộc, bảo trì | `chore/nang-cap-thu-vien` |

Tên branch dùng chữ thường, không dấu, các từ nối bằng dấu gạch ngang.

---

## 📝 QUY ƯỚC COMMIT

Viết commit theo dạng `<loại>: <mô tả ngắn>`, ví dụ `fix: sửa lỗi không lưu được lịch hẹn`. Tiêu đề Pull Request dùng cùng quy ước và được kiểm tra tự động; có thể thêm phạm vi `fix(api): …` hoặc dấu `!` cho thay đổi phá vỡ tương thích `feat!: …`.

| Loại | Ý nghĩa |
|---|---|
| `feat` | Thêm tính năng |
| `fix` | Sửa lỗi |
| `docs` | Cập nhật tài liệu |
| `refactor` | Tái cấu trúc mã nguồn |
| `perf` | Cải thiện hiệu năng |
| `test` | Bổ sung hoặc cập nhật kiểm thử |
| `chore` | Cấu hình, phụ thuộc, công việc bảo trì |

Mỗi commit chỉ chứa một thay đổi có ý nghĩa; mô tả rõ **làm gì** và **vì sao**.

---

## ✅ YÊU CẦU ĐỐI VỚI PULL REQUEST

- Điền đầy đủ [biểu mẫu Pull Request](PULL_REQUEST_TEMPLATE.md), liên kết Issue liên quan.
- Các kiểm tra tự động phải thành công.
- Không chứa mật khẩu, khóa API, token truy cập hoặc thông tin bảo mật.
- Không chứa dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế nhạy cảm.
- Nêu rõ rủi ro, thay đổi phá vỡ tương thích và phương án khôi phục nếu có.

---

## 📞 LIÊN HỆ

Mọi thắc mắc về việc đóng góp, vui lòng tạo Issue với biểu mẫu **❓ Câu hỏi hoặc cần hỗ trợ** hoặc liên hệ [toanquynhvn@gmail.com](mailto:toanquynhvn@gmail.com).

---

<p align="center">
	<strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
	Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
