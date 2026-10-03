# 0014. QUY TẮC ĐẶT TÊN CAMELCASE CHỈ ÁP DỤNG CHO TÊN TỰ ĐẶT

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03
- **Điều chỉnh:** [0010](0010-camel-case-names.md) — phạm vi của quy tắc: tên do Python, thư viện quy định không áp dụng; bỏ cách gán qua thuộc tính hoặc `type()`

## 📌 BỐI CẢNH

ADR 0010 áp camelCase cho mọi tên hàm, tham số, biến. Tên mà Python hoặc thư viện quy định — `__init__`, `do_GET` của `http.server`, `http_open` của `urllib`, `log_message` — không đổi được, nên mã phải viết vòng để né quy tắc: gán phương thức qua `type()`, `SimpleNamespace`, gán hàm cho thuộc tính đối tượng. Cách viết vòng khó đọc hơn cách viết thông thường của thư viện mà không làm tên tự đặt nhất quán hơn.

## ✅ QUYẾT ĐỊNH

- Quy tắc camelCase tiếng Anh của ADR 0010 chỉ áp dụng cho **biến, hàm, tham số do người viết tự đặt**.
- Không áp dụng cho tên do Python, thư viện quy định:
    - Tên dạng `__tên__` (phương thức đặc biệt như `__init__`, biến như `__all__`); tham số của chúng vẫn là tên tự đặt.
    - Phương thức ghi đè phương thức có sẵn ở lớp cha của thư viện (`log_message`), hoặc đặt theo mẫu tên mà thư viện gọi (`LIBRARY_NAME_PATTERNS` trong `validate.py`: `do_<PHƯƠNG THỨC>` của `http.server`, `<giao thức>_open` của `urllib`) — kể cả tham số theo chữ ký của lớp cha.
- `validate.py` tra lớp cha thật (nạp module của thư viện) để phân biệt; tên tự đặt trong lớp con của thư viện vẫn bị kiểm tra.
- Viết mã theo cách thông thường của thư viện (kế thừa lớp, định nghĩa phương thức), không viết vòng để né quy tắc.

## ⚖️ HỆ QUẢ

- Dùng thư viện gọi phương thức theo mẫu tên chưa có trong `LIBRARY_NAME_PATTERNS` thì thêm mẫu vào danh sách, kèm test.
- Lớp cha không nạp được (thư viện chưa cài) thì tên vẫn bị kiểm tra như tên tự đặt.
