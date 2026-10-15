# 00000003. TÊN BRANCH TIẾNG ANH; COMMIT VÀ TIÊU ĐỀ PULL REQUEST THEO CONVENTIONAL COMMITS

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Tên branch và tiêu đề thay đổi cần cho biết mục đích công việc, dễ tìm kiếm và có thể kiểm tra bằng cùng quy tắc tại máy và trên GitHub.

## ✅ QUYẾT ĐỊNH

Branch dùng `<tiền tố>/<mô_tả>` bằng tiếng Anh, chữ thường; các từ trong mô tả nối bằng `_`, ví dụ `docs/update_readme`. Tiền tố nằm trong bảng của `CONTRIBUTING.md`. Nhánh chính và branch do Dependabot tạo được miễn kiểm tra tên.

Commit và tiêu đề Pull Request theo [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/): `<loại>(<phạm vi>): <mô tả>`, phạm vi tùy chọn. Tiêu đề một dòng, tối đa 72 ký tự, không kết thúc bằng dấu chấm.

`scripts/conventions.py` là nguồn kiểm tra, được gọi từ `make check`, workflow của repository và workflow mẫu. Danh sách loại commit, tiền tố branch và mẫu `.gitmessage` phải khớp hướng dẫn đóng góp.

Nguồn của quyết định: [CONTRIBUTING.md](../../CONTRIBUTING.md), [scripts/conventions.py](../../scripts/conventions.py), [.github/labeler.yml](../../.github/labeler.yml), [.gitmessage](../../.gitmessage).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Tiền tố biểu thị loại công việc, còn mô tả nêu nội dung cụ thể. Conventional Commits tạo cấu trúc tiêu đề thống nhất. Kiểm tra tự động giúp người đóng góp phát hiện sai lệch trước khi gửi PR.

## ⚖️ HỆ QUẢ

Tiền tố branch cần có luật trong `.github/labeler.yml`. Merge commit do GitHub tạo khi cập nhật branch không chịu quy tắc tiêu đề commit thông thường. Đổi quy ước phải đồng bộ tài liệu, script và mẫu trong cùng thay đổi.
