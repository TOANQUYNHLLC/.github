# 00000003. TÊN BRANCH TIẾNG ANH; COMMIT VÀ TIÊU ĐỀ PULL REQUEST THEO CONVENTIONAL COMMITS

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Branch, commit và Pull Request cần có tên dễ tìm, dễ đánh giá và phục vụ việc phân nhóm nội dung phát hành. Quy ước dùng chung cần được kiểm tra tại máy và trong workflow.

## ✅ QUYẾT ĐỊNH

Branch có dạng `<tiền tố>/<mô_tả>`: tiền tố theo `CONTRIBUTING.md`, mô tả bằng tiếng Anh, chữ thường và nối từ bằng dấu gạch dưới, ví dụ `docs/update_readme`. Branch của Dependabot được miễn kiểm tra.

Commit và tiêu đề Pull Request có dạng `<loại>(<phạm vi>): <mô tả>` theo [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/); phạm vi là tùy chọn.

`scripts/conventions.py` khai báo các loại commit và tiền tố branch. `make check`, workflow của repository và workflow mẫu dùng cùng script.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Tên branch tiếng Việt không dấu dễ nhầm nghĩa. Tiêu đề tự do khó phân nhóm nội dung phát hành. Chỉ ghi quy ước trong tài liệu không bảo đảm việc áp dụng nhất quán.

## ⚖️ HỆ QUẢ

Danh sách trong `CONTRIBUTING.md`, `scripts/conventions.py` và `.gitmessage` phải khớp. Tiền tố branch phải có luật gắn nhãn trong `.github/labeler.yml`. Merge commit do nút **Update branch** của GitHub tạo được miễn kiểm tra.
