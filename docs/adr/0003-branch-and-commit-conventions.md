# 0003. TÊN BRANCH TIẾNG ANH; COMMIT VÀ TIÊU ĐỀ PULL REQUEST THEO CONVENTIONAL COMMITS

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Tên branch và tiêu đề commit là nơi đầu tiên người đọc lịch sử nhìn vào. Tên branch tiếng Việt không dấu khó đọc và dễ nhầm nghĩa; tiêu đề commit tự do không gom nhóm được khi viết nhật ký thay đổi. Quy ước chỉ có tác dụng khi được kiểm tra tự động ở mọi repository.

## ✅ QUYẾT ĐỊNH

- Tên branch dạng `<tiền tố>/<mô_tả>`: tiền tố trong bảng của `CONTRIBUTING.md`; mô tả bằng **tiếng Anh**, chữ thường, các từ nối bằng **dấu gạch dưới** (ví dụ `docs/update_readme`). Branch của Dependabot được bỏ qua.
- Tiêu đề commit và Pull Request dạng `<loại>(<phạm vi>): <mô tả>` theo [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/), với loại trong bảng của `CONTRIBUTING.md`; phạm vi tùy chọn.
- `scripts/conventions.py` là nơi duy nhất khai báo danh sách loại commit và tiền tố branch; workflow `branch-name.yml`, `pr-title.yml` (của repository này và workflow mẫu) và `make check` cùng gọi script này.

## ⚖️ HỆ QUẢ

- `validate.py` kiểm tra danh sách trong `CONTRIBUTING.md`, `scripts/conventions.py` và mẫu commit `.gitmessage` khớp nhau; tiền tố branch mới cần thêm luật gắn nhãn trong `.github/labeler.yml`.
- Merge commit do nút **Update branch** của GitHub tạo không bị kiểm tra.
