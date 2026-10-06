# 📋 QUY TRÌNH RÀ SOÁT DỰ ÁN

Hướng dẫn dành cho các đợt rà soát, sửa chữa và đồng bộ toàn dự án. Áp dụng cùng [`AGENTS.md`](../AGENTS.md) và [`CONTRIBUTING.md`](../CONTRIBUTING.md), trong phạm vi công việc được giao.

Mục tiêu là mã nguồn hoạt động đúng, cấu trúc rõ ràng và tài liệu đủ để cài đặt, sử dụng, kiểm thử và vận hành dự án độc lập.

---

## 🔎 XÁC ĐỊNH PHẠM VI VÀ TRẠNG THÁI

- Đọc quy tắc của repository, hướng dẫn đóng góp và cấu hình định dạng.
- Kiểm tra branch, trạng thái Git và các thay đổi đang có; giữ nguyên thay đổi hợp lệ của người dùng.
- Kiểm kê mã nguồn, cấu hình, scripts, workflows, tests, tài liệu và tài nguyên thuộc phạm vi.
- Xác định chức năng đang được triển khai, điểm khởi chạy và quan hệ giữa các thành phần.
- Với tệp sinh tự động, kiểm tra nguồn và quy trình tạo thay vì sửa trực tiếp.
- Chạy các kiểm tra hiện có trước khi sửa để xác định trạng thái ban đầu.

---

## 🛠️ KIỂM TRA MÃ NGUỒN VÀ CẤU HÌNH

- Kiểm tra imports, exports, kiểu dữ liệu, đường dẫn, tên biến, cấu hình và dependencies.
- Kiểm tra logic, giá trị mặc định, trường hợp biên, xử lý lỗi và quyền truy cập.
- Kiểm tra luồng bất đồng bộ, quản lý tài nguyên, trạng thái dùng chung và nguy cơ xung đột.
- Đối chiếu manifest, lockfile, phiên bản runtime, biến môi trường và cấu hình CI.
- Xử lý mã chết, thành phần trùng lặp và cấu hình lỗi thời sau khi kiểm tra các nơi sử dụng.
- Giữ thay đổi tập trung vào vấn đề cụ thể; chỉ đổi kiến trúc hoặc thêm dependency khi có lý do rõ ràng.
- Bổ sung hoặc cập nhật tests cho lỗi và hành vi quan trọng; tests phải kiểm tra kết quả thực tế.

---

## ⚡ KIỂM TRA HIỆU NĂNG

- Xác định điểm nghẽn bằng số liệu phù hợp với chức năng: thời gian xử lý, truy vấn, request, render, tải tài nguyên hoặc khởi động.
- Kiểm tra điều kiện cập nhật và vô hiệu hóa cache khi có caching.
- Xác minh tối ưu không làm sai kết quả, quyền truy cập hoặc các luồng sử dụng.
- Đưa bằng chứng và giới hạn đo lường vào Pull Request; tài liệu dự án chỉ mô tả cách vận hành hiện tại.

---

## 🧹 DỌN NỘI DUNG PHÁT TRIỂN

- Xóa debug prints, log thử nghiệm và instrumentation chỉ phục vụ phát triển sau khi xác minh chúng không cần cho vận hành.
- Giữ thông báo vận hành, cảnh báo và lỗi cần thiết; kiểm tra để không lộ dữ liệu nhạy cảm.
- Dọn tệp tạm, bản sao không còn dùng, ghi chú thử nghiệm và báo cáo rà soát không thuộc tài liệu sản phẩm.
- Xử lý TODO/FIXME thuộc phạm vi; mục còn giá trị phải mô tả rõ việc cần làm.
- Tài liệu mô tả hiện trạng, không chứa nhật ký sửa lỗi, diễn biến phát triển, log kiểm tra hoặc số đo thử nghiệm.
- `CHANGELOG.md` dùng để chuẩn bị nội dung dành cho người sử dụng khi phát hành, theo quy ước trong [`AGENTS.md`](../AGENTS.md).
- Giữ nguyên lịch sử Git và thông tin bản quyền.

---

## 📝 ĐỒNG BỘ TÀI LIỆU

- Kiểm tra README, hướng dẫn cài đặt, phát triển, kiểm thử, triển khai, cấu hình, kiến trúc, docstring và chú thích liên quan.
- Cập nhật hoặc xóa nội dung không còn khớp với mã nguồn, bao gồm tệp, lệnh, chức năng và cấu hình.
- Kiểm tra lệnh, đường dẫn, ví dụ, liên kết và tên biến môi trường; không đưa secrets vào tài liệu.
- Mỗi khi thay đổi mã nguồn, cấu hình, dependencies, scripts, workflows hoặc hành vi của hệ thống, cập nhật tài liệu liên quan trong cùng thay đổi. Chỉ hoàn tất khi mã nguồn, tests, ví dụ cấu hình và tài liệu thống nhất.
- Với ADR, đối chiếu quyết định đang áp dụng; khi thay đổi quyết định, thêm ADR mới và cập nhật trạng thái, mục lục theo [`docs/adr/README.md`](../docs/adr/README.md).
- Kiểm tra badge theo repository, tên workflow, branch, URL ảnh và đích liên kết; chỉ dùng badge có nguồn dữ liệu phù hợp với dự án.
- Đối chiếu checklist trong biểu mẫu Pull Request với quy tắc đóng góp và yêu cầu đồng bộ tài liệu.

---

## ✅ KIỂM CHỨNG

- Chạy formatter, lint, tests và các kiểm tra chức năng phù hợp với thay đổi.
- Kiểm tra scripts cài đặt, phát triển, kiểm thử và triển khai trong phạm vi.
- Xác minh luồng chính, luồng lỗi và trường hợp biên; với giao diện, kiểm tra trạng thái tải, rỗng và lỗi.
- Không bỏ qua kiểm tra, nới lỏng quy tắc hoặc xóa tests để đạt kết quả thành công.
- Sau thay đổi cuối cùng, chạy `make check` và kiểm tra diff để phát hiện thay đổi ngoài ý muốn hoặc thông tin nhạy cảm.
- Nếu bị chặn bởi môi trường, quyền truy cập hoặc dịch vụ bên ngoài, nêu rõ bước chưa chạy, nguyên nhân và giới hạn xác minh trong phần bàn giao.

---

## 🔀 BÀN GIAO VÀ PULL REQUEST

Hoàn tất khi các tệp thuộc phạm vi đã được kiểm tra, vấn đề đã được xử lý, tài liệu khớp với code và các kiểm tra cần thiết đã đạt.

Khi phạm vi công việc bao gồm tạo Pull Request:

1. Commit có chữ ký trên branch phù hợp với quy ước.
2. Đẩy branch và tạo Pull Request vào branch đích.
3. Mô tả vấn đề, hành vi sau thay đổi, nội dung chính và kết quả kiểm chứng; nêu giới hạn xác minh nếu có.
4. Gửi liên kết Pull Request và để ở trạng thái chờ review.
