# 0013. TÀI LIỆU LUÔN KHỚP VỚI CODE

- **Trạng thái:** Bị thay thế một phần bởi 0015 (phạm vi thư mục mà `checkDocsMatchCode()` đối chiếu)
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Repository này vừa là code (script kiểm tra, workflow) vừa là tài liệu cho cả tổ chức. Tài liệu mô tả sai code — lệnh không còn, đường dẫn đã đổi, con số đã khác — làm người đọc làm sai và mất niềm tin vào mọi tài liệu khác. Sai lệch thường xuất hiện khi sửa code mà quên tài liệu nhắc tới nó.

## ✅ QUYẾT ĐỊNH

- Mỗi khi thay đổi mã nguồn, cấu hình, dependencies, scripts, workflows hoặc hành vi của hệ thống, người sửa (kể cả AI agent) kiểm tra mọi tài liệu liên quan — `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/adr/`, `rulesets/README.md`, docstring, chú thích — còn đúng với trạng thái hiện tại; sai thì cập nhật hoặc xoá nội dung lỗi thời trong cùng thay đổi. Công việc chỉ hoàn tất khi mã nguồn, tests, ví dụ cấu hình và tài liệu liên quan đã thống nhất; biểu mẫu Pull Request có mục kiểm tra tương ứng.
- Không ghi con số dễ lệch (số nhãn, số team, số quyết định…) vào câu chữ khi không cần.
- Tài liệu chỉ mô tả hiện trạng: thứ code không còn (tệp, lệnh, tính năng, cài đặt đã bỏ) xoá khỏi tài liệu, kể cả mục **CHƯA PHÁT HÀNH** của `CHANGELOG.md`; lịch sử thay đổi nằm trong git và GitHub Release.
- `validate.py` (`checkDocsMatchCode()`) kiểm tra phần đối chiếu được bằng máy:
    - Lệnh `make …`, đường dẫn trong `scripts/`, `docs/`, `rulesets/`, `workflow-templates/`, `repository-templates/`, `.github/workflows/` và hàm `tênHàm()` được nhắc trong tài liệu Markdown phải có thật.
    - `README.md` liệt kê đủ lệnh trong `Makefile`, script trong `scripts/` và workflow trong `.github/workflows/`.
- Người đánh giá Pull Request (kể cả GitHub Copilot) đối chiếu tài liệu với code thay đổi.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Chỉ dựa vào người đánh giá đọc lại**: sai lệch vẫn lọt — con số trong tài liệu, vị trí hằng số sau khi tách module, lệnh đã đổi tên.
- **Kiểm tra tự động toàn bộ câu chữ**: không khả thi với mô tả hành vi bằng ngôn ngữ tự nhiên; chọn kiểm tra tự động phần đối chiếu được (tên, đường dẫn, danh sách) kết hợp người đánh giá.
- **Giữ nội dung về thứ đã bỏ trong tài liệu để tham khảo**: làm tài liệu mâu thuẫn với hiện trạng; lịch sử đã có trong git và GitHub Release.

## ⚖️ HỆ QUẢ

- Pull Request đổi tên lệnh, script, hàm hay workflow mà quên tài liệu sẽ không qua `make check`.
- Phần mô tả hành vi (câu chữ) vẫn cần người kiểm tra — kiểm tra tự động chỉ bắt được tên và đường dẫn.
