# 0010. TÊN TỰ ĐẶT VIẾT CAMELCASE TIẾNG ANH; CÚ PHÁP CỦA NGÔN NGỮ GIỮ NGUYÊN

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Script do nhiều người và công cụ AI cùng viết; tên hàm, biến lẫn nhiều kiểu (snake_case, tiếng Việt không dấu) khó đọc và khó tìm. Mặt khác, nhiều tên không do người viết chọn mà do ngôn ngữ, thư viện quy định — đổi chúng thì mã sai hoặc phải viết vòng (gán phương thức qua `type()`, gán hàm cho thuộc tính đối tượng), khó đọc hơn cách viết thông thường.

## ✅ QUYẾT ĐỊNH

- **Biến, hàm, tham số do người viết tự đặt:** tiếng Anh, camelCase (`checkLinks`, `syncSettings`, `changelogPath`; test `testBrokenLink`). Hằng số `UPPER_CASE`, lớp `PascalCase`.
- **Tên thuộc cú pháp, thư viện của ngôn ngữ giữ nguyên** — không đổi, không viết vòng để né quy tắc:
    - Từ khóa và tên dựng sẵn (`self`, `cls`, `print`, `type`…).
    - Phương thức, biến đặc biệt dạng `__tên__` (`__init__`, `__enter__`, `__all__`); tham số tự đặt của chúng vẫn viết camelCase.
    - Phương thức và tham số mà thư viện quy định: ghi đè phương thức có sẵn ở lớp cha (`setUp`, `log_message(self, format, *args)`) hoặc đặt theo mẫu tên mà thư viện gọi (`do_GET` của `http.server`, `http_open` của `urllib`).
    - Tên thuộc về thư viện hay dữ liệu bên ngoài: tham số từ khóa khi gọi hàm (`capture_output=True`), thuộc tính của đối tượng thư viện (`node.lineno`, `args.open_pr` do argparse sinh từ `--open-pr`), khóa của định dạng bên ngoài (`actor_id` của API GitHub, `timeout-minutes` của workflow), biến môi trường (`GH_TOKEN`).
- `validate.py` đọc cây cú pháp (`ast`) của mọi tệp Python và chỉ xét tên tự đặt: định nghĩa hàm, tham số, biến được gán. Phương thức mang tên thư viện quy định được nhận ra bằng cách tra lớp cha thật (nạp module của thư viện) và mẫu tên thư viện gọi (`LIBRARY_NAME_PATTERNS`); tên tự đặt trong lớp con của thư viện vẫn bị kiểm tra.

## ⚖️ HỆ QUẢ

- Khác PEP 8 (snake_case cho tên tự đặt); ruff với cấu hình chuẩn không kiểm tra tên nên không xung đột.
- Mã dùng thư viện viết theo cách thông thường (kế thừa lớp, định nghĩa phương thức đúng tên thư viện quy định).
- Dùng thư viện gọi phương thức theo mẫu tên chưa có trong `LIBRARY_NAME_PATTERNS` thì thêm mẫu vào danh sách, kèm test. Lớp cha không nạp được (thư viện chưa cài) thì tên vẫn bị kiểm tra như tên tự đặt.
