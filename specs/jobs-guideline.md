# 📋 QUY TRÌNH RÀ SOÁT DỰ ÁN

Quy trình đọc, kiểm tra và đồng bộ dự án trong phạm vi được giao. Áp dụng cùng [AGENTS.md](../AGENTS.md) và [CONTRIBUTING.md](../CONTRIBUTING.md). Kết quả cần đạt là nguồn hoạt động đúng và tài liệu đủ để thiết lập, sử dụng, kiểm thử, vận hành độc lập.

## 🔎 KIỂM KÊ VÀ ĐỌC NGUỒN

- Đọc hướng dẫn dự án và kiểm tra branch, trạng thái Git, thay đổi đang có; bảo toàn công việc hợp lệ của người dùng.
- Liệt kê toàn bộ tài liệu, kể cả tệp trong thư mục ẩn, biểu mẫu và hướng dẫn AI. Đọc nội dung đầy đủ; khi đầu ra bị cắt, chia phần để đọc tiếp.
- Đối chiếu tài liệu với điểm khởi chạy, lệnh, cấu hình, scripts, workflows và tests liên quan. Với tệp sinh, xác định nguồn và lệnh sinh.
- Đối chiếu danh mục với các tệp thực tế để tìm mục thiếu, thừa, trùng hoặc sai thứ tự theo quy ước của từng loại. Với ADR, kiểm tra dãy mã liên tục cùng tên tệp, tiêu đề, mục lục và mọi tham chiếu.
- Chạy kiểm tra hiện có để xác nhận môi trường và trạng thái trước khi sửa. Phân biệt kết quả đã chạy với nhận định từ việc đọc mã.

## 🛠️ MÃ NGUỒN VÀ CẤU HÌNH

- Kiểm tra imports, exports, tên, kiểu dữ liệu, đường dẫn, giá trị mặc định, xử lý lỗi và quyền truy cập.
- Kiểm tra các luồng bất đồng bộ, tài nguyên, trạng thái dùng chung và khả năng xung đột khi thuộc phạm vi.
- Đối chiếu dependencies, manifest, lockfile, runtime, biến môi trường và cách CI gọi công cụ.
- Tìm mọi nơi tham chiếu trước khi xóa hoặc đổi tên; sửa code gọi tới, tests, ví dụ và tài liệu trong cùng thay đổi.
- Giữ thay đổi tập trung vào mục tiêu; thêm dependency hoặc đổi kiến trúc khi có căn cứ. Tests kiểm tra kết quả thực tế và các lỗi quan trọng.

## ⚡ HIỆU NĂNG VÀ TÀI NGUYÊN

Khi phạm vi gồm tối ưu hiệu năng, xác định điểm nghẽn bằng chỉ số phù hợp: độ trễ, truy vấn, CPU, bộ nhớ hoặc thời gian khởi động. Kiểm tra điều kiện cập nhật và vô hiệu hóa cache. Xác minh tối ưu giữ đúng dữ liệu, phân quyền và hành vi.

Đưa cách đo, kết quả và giới hạn vào PR hoặc artifact phục vụ đánh giá. Tài liệu sử dụng mô tả điều kiện và cách vận hành, không chứa nhật ký đo thử.

## 📝 BIÊN SOẠN TÀI LIỆU

- Viết theo hiện trạng như hướng dẫn của một dự án có thể dùng độc lập: mục đích, điều kiện, cách bắt đầu, thao tác, giới hạn và trách nhiệm.
- README là điểm bắt đầu và danh mục nguồn; tài liệu chuyên đề mô tả vận hành; ADR trình bày quyết định hiện hành cùng lý do. Một thông tin có một nơi mô tả chính.
- Đối chiếu lệnh, đường dẫn, hàm, ví dụ, liên kết, badge và tên biến môi trường với nguồn thực tế. Giữ thông tin công ty, liên hệ và bản quyền có căn cứ.
- Viết lại trọn chủ đề khi nội dung thay đổi. Không nối thêm lịch sử phát triển, mốc cập nhật, danh sách sửa lỗi, báo cáo rà soát hoặc log kiểm tra vào tài liệu dự án.
- `CHANGELOG.md` chỉ chuẩn bị tóm tắt cho người sử dụng khi phát hành theo [quy ước dự án](../AGENTS.md). Không dựng phiên bản hoặc ngày phát hành chưa được công bố.
- Cập nhật ADR, mục lục và các nơi tham chiếu theo [hướng dẫn ADR](../docs/adr/README.md); giữ nội dung quyết định thống nhất với code và cấu hình.
- Giữ nguyên lịch sử Git và thông tin bản quyền trong phạm vi rà soát tài liệu.

## 🧹 KIỂM TRA NỘI DUNG PHÁT TRIỂN

Dọn tệp tạm, bản sao không dùng, ghi chú thử nghiệm và mã debug sau khi xác minh chúng không cần cho vận hành. Giữ lỗi, cảnh báo và thông báo phục vụ người dùng. Không ghi secrets hoặc dữ liệu nhạy cảm vào nội dung hay đầu ra.

TODO/FIXME còn giá trị phải nêu rõ việc cần làm; xử lý mục thuộc phạm vi thay đổi. Kiểm tra cả hướng dẫn trong biểu mẫu và chú thích liên quan, không chỉ các tệp trong `docs/`.

## ✅ KIỂM CHỨNG VÀ BÀN GIAO

- Rà soát diff và tìm tham chiếu theo tên, thuật ngữ, đường dẫn của thay đổi trên toàn repository.
- Chạy formatter, lint, tests và kiểm chứng phù hợp. Kiểm tra lệnh thiết lập, scripts và workflow trong phạm vi; giao diện cần kiểm tra luồng chính, lỗi, rỗng và tải khi liên quan.
- Không bỏ qua, xóa hoặc nới lỏng tests để đạt kết quả thành công. Chạy `make check` sau thay đổi cuối cùng.
- Nêu rõ bước đã chạy, kết quả, bước chưa xác minh và lý do trong bàn giao; không ghi báo cáo này thành tài liệu dự án.
- Chỉ hoàn tất khi nguồn, tests, cấu hình, ví dụ và hướng dẫn thống nhất. Nếu được giao tạo PR, commit có chữ ký trên branch phù hợp, đẩy branch, tạo PR với mô tả và bằng chứng rồi gửi liên kết để review.
