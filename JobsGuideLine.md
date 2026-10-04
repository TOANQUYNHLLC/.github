Tiếp tục công việc từ trạng thái hiện tại của repository. Hãy rà soát, sửa chữa, tối ưu và đồng bộ toàn bộ dự án, sau đó tạo Pull Request khi đã hoàn tất các bước kiểm chứng.

Mục tiêu là bàn giao một dự án hoạt động đúng, có cấu trúc rõ ràng, hiệu năng tốt và tài liệu phản ánh chính xác mã nguồn hiện tại. Chủ động xử lý các vấn đề tìm thấy trong phạm vi công việc, không dừng ở việc liệt kê lỗi hoặc đề xuất sửa.

**1. Xác định đầy đủ trạng thái dự án**

- Đọc các quy tắc của repository, bao gồm `AGENTS.md`, hướng dẫn đóng góp và cấu hình định dạng mã.
- Kiểm tra branch, trạng thái Git và các thay đổi đang có; giữ nguyên những thay đổi hợp lệ của người dùng.
- Kiểm kê các file do dự án quản lý: mã nguồn, cấu hình, scripts, workflows, tests, tài liệu và tài nguyên.
- Xác định những chức năng thực sự đang được triển khai, các điểm khởi chạy và mối liên hệ giữa các thành phần.
- Theo dõi phạm vi đã kiểm tra để tránh bỏ sót file. Với file sinh tự động, kiểm tra nguồn và quy trình tạo file thay vì chỉnh sửa trực tiếp.

**2. Kiểm tra và khôi phục badge GitHub Actions**

- Tìm hiểu vì sao badge trạng thái GitHub Actions đã bị loại bỏ trong các thay đổi trước.
- Khôi phục các badge vẫn phù hợp với workflows hiện tại.
- Kiểm tra chính xác repository, tên file workflow, branch, URL ảnh badge và liên kết khi nhấp vào.
- Nếu workflow đã đổi tên hoặc thay đổi cấu trúc, cập nhật badge tương ứng.
- Cân nhắc bổ sung badge hữu ích như CI, test, coverage, phiên bản hoặc giấy phép, nhưng chỉ khi dự án có nguồn dữ liệu thực tế và đáng tin cậy.
- Trình bày badge gọn gàng trong README, tránh trùng lặp và tránh hiển thị trạng thái không phản ánh đúng dự án.

**3. Rà soát và sửa từng file**

Kiểm tra nội dung của từng file cùng cách file đó tương tác với phần còn lại của hệ thống. Đặc biệt chú ý:

- Imports, exports, kiểu dữ liệu, đường dẫn, tên biến, cấu hình và dependencies.
- Logic xử lý, validation, giá trị mặc định, trường hợp biên và xử lý lỗi.
- Luồng bất đồng bộ, quản lý tài nguyên, trạng thái dùng chung và nguy cơ xung đột.
- Các chức năng, cấu hình hoặc cách triển khai trùng lặp, mâu thuẫn hay đã lỗi thời.
- Mã chết, dependencies không còn sử dụng và abstractions không còn cần thiết.
- Các vấn đề bảo mật trực tiếp liên quan đến phần mã đang kiểm tra, nếu có.

Chỉ xoá thành phần sau khi đã kiểm tra các nơi sử dụng và ảnh hưởng liên quan. Mỗi thay đổi phải có mục đích rõ ràng, giữ được hành vi hợp lệ và tuân thủ chuẩn của dự án.

Nếu phát hiện cách hoạt động chưa hợp lý, hãy cải thiện và bổ sung kiểm chứng tương ứng. Tránh thay đổi kiến trúc hoặc thêm dependencies khi chưa có lợi ích cụ thể.

**4. Tối ưu hiệu năng có kiểm chứng**

- Xác định các điểm nghẽn thực tế trước khi tối ưu.
- Kiểm tra những vấn đề phù hợp với dự án: xử lý lặp, truy vấn dư thừa, request không cần thiết, render thừa, tải tài nguyên, bundle và thời gian khởi động.
- Ghi nhận số liệu trước và sau đối với các thay đổi hiệu năng quan trọng, trong phạm vi môi trường cho phép.
- Nếu sử dụng caching, kiểm tra điều kiện cập nhật và vô hiệu hoá cache để tránh trả dữ liệu cũ.
- Xác minh rằng tối ưu không làm sai kết quả, thay đổi quyền truy cập, mất dữ liệu hoặc ảnh hưởng các luồng đang hoạt động.

Ưu tiên hiệu năng đi cùng tính đúng đắn và khả năng bảo trì.

**5. Kiểm tra chức năng và quy trình vận hành**

- Chạy các kiểm tra phù hợp đang có trong dự án: format, lint, typecheck, tests và build.
- Kiểm tra các scripts được sử dụng trong quá trình cài đặt, phát triển, kiểm thử và triển khai.
- Kiểm tra sự thống nhất giữa manifest, lockfile, phiên bản runtime, biến môi trường và cấu hình CI.
- Xác minh các luồng chức năng chính, luồng lỗi và trường hợp biên bằng cách phù hợp với loại dự án.
- Bổ sung hoặc cập nhật tests cho lỗi đã sửa và các hành vi quan trọng chưa được bảo vệ. Tests phải kiểm tra hành vi thực tế.
- Với giao diện, kiểm tra các thao tác chính và trạng thái loading, empty, error nếu có. Với API hoặc dịch vụ, kiểm tra đầu vào, đầu ra, mã lỗi và quyền truy cập nếu có.

Không tắt kiểm tra, bỏ qua tests, nới lỏng quy tắc hoặc che giấu lỗi chỉ để các checks báo thành công.

Sau thay đổi cuối cùng, chạy lại các kiểm tra chịu ảnh hưởng và thực hiện một lượt kiểm tra tổng thể trước khi bàn giao.

**6. Dọn sạch log phát triển và nội dung dư thừa**

- Xoá debug prints, log thử nghiệm và instrumentation chỉ phục vụ quá trình phát triển.
- Giữ các log vận hành, cảnh báo và lỗi cần thiết; bảo đảm chúng không làm lộ thông tin nhạy cảm.
- Dọn file tạm, bản sao không còn dùng, ghi chú thử nghiệm và nội dung còn sót từ các lần chỉnh sửa trước.
- Rà soát các TODO/FIXME: xử lý những mục thuộc phạm vi hiện tại; chỉ giữ những mục còn giá trị với mô tả rõ ràng.
- Giữ nguyên lịch sử Git, thông tin bản quyền và giấy phép.

**7. Viết lại toàn bộ tài liệu theo trạng thái hiện tại**

Rà soát và viết lại README, hướng dẫn cài đặt, phát triển, kiểm thử, triển khai, cấu hình, kiến trúc, ADR và những tài liệu liên quan đang có.

Yêu cầu:

- Tài liệu phải có thể sử dụng độc lập như bộ tài liệu hoàn chỉnh của một dự án mới.
- Nội dung phải phản ánh mã nguồn và cách vận hành hiện tại.
- Xoá mô tả về chức năng, modules, endpoints, dependencies, scripts hoặc cấu hình đã bị loại bỏ.
- Xoá nhật ký phát triển và nội dung kể lại các lần sửa chữa không còn cần thiết.
- Kiểm tra các lệnh, đường dẫn, ví dụ, liên kết và tên biến môi trường; sửa những nội dung không còn đúng.
- Đối chiếu các ví dụ cấu hình với cấu hình thực tế; không đưa secrets vào tài liệu.
- Bảo đảm các tài liệu thống nhất với nhau và không chứa hướng dẫn mâu thuẫn.

Với ADR, rà soát toàn bộ và viết lại những quyết định kiến trúc còn áp dụng. Mỗi ADR cần nêu rõ quyết định, lý do, phương án được cân nhắc và hệ quả dựa trên hiện trạng có thể xác minh. Loại bỏ ADR không còn phù hợp, cập nhật mục lục và các liên kết liên quan. Không tự tạo lịch sử quyết định hoặc lý do không có căn cứ.

**8. Bổ sung quy tắc bắt buộc về đồng bộ tài liệu**

Thêm quy tắc sau vào nơi quy định cách làm việc của repository, ưu tiên `AGENTS.md` nếu dự án sử dụng file này:

“Mỗi khi thay đổi mã nguồn, cấu hình, dependencies, scripts, workflows hoặc hành vi của hệ thống, phải kiểm tra những tài liệu liên quan có còn khớp với trạng thái hiện tại hay không. Nếu có sai lệch, phải cập nhật hoặc xoá nội dung lỗi thời trong cùng thay đổi. Chỉ coi công việc hoàn tất khi mã nguồn, tests, ví dụ cấu hình và tài liệu liên quan đã thống nhất.”

Bổ sung mục kiểm tra tương ứng vào PR template nếu dự án có sử dụng.

**9. Điều kiện hoàn tất và tạo Pull Request**

Chỉ báo hoàn thành khi:

- Đã rà soát đầy đủ các file thuộc phạm vi.
- Các lỗi phát hiện trong phạm vi đã được xử lý và kiểm chứng.
- Các checks phù hợp đã chạy thành công.
- Các chức năng chính đã được xác minh.
- Badge phản ánh đúng workflows hiện tại.
- Log phát triển và thành phần dư thừa đã được dọn.
- README, ADR và các tài liệu liên quan đã khớp với code.
- Diff cuối cùng đã được kiểm tra, không có thay đổi ngoài ý muốn hoặc thông tin nhạy cảm.
- Check lại hoạt động các chức năng đã thống nhất với nhau.
- Đã kiểm tra từng file trong dự án.
- Luôn luôn phải ưu tiên kiểm tra tốc độ thực hiện của tính năng càng nhanh, tối ưu và đúng logic.
- Xoá, sửa các log, lịch sử lại giống như 1 PROJECT mới, KHÔNG được có log thay đổi và phát triển. Viết chuẩn hoá lại lịch sử release

Tiếp tục sửa và kiểm tra cho đến khi đáp ứng các điều kiện trên. Không bàn giao ở trạng thái còn lỗi đã biết mà có thể tự xử lý, hoặc để người dùng phải yêu cầu thêm một vòng rà soát mới.

Nếu có bước kiểm tra bị chặn bởi môi trường, quyền truy cập hoặc dịch vụ bên ngoài, hãy ghi rõ bước bị chặn, nguyên nhân, phần đã xác minh và phần còn thiếu. Không tuyên bố một kiểm tra đã thành công khi chưa thực hiện được.

Sau khi hoàn tất, commit các thay đổi và tạo Pull Request vào branch đích phù hợp. Nội dung PR phải nêu rõ:

- Vấn đề và hành vi sau khi sửa.
- Những thay đổi chính về code, hiệu năng, badge và tài liệu.
- Các kiểm tra đã chạy cùng kết quả.
- Bằng chứng cải thiện hiệu năng nếu có.
- Những giới hạn xác minh hoặc yêu cầu cấu hình còn liên quan.

Gửi lại liên kết PR và kết quả kiểm tra. Để PR ở trạng thái chờ review.
