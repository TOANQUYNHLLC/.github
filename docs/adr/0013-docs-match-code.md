# 0013. TÀI LIỆU LUÔN KHỚP VỚI CODE

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Repository này vừa là code (script kiểm tra, workflow) vừa là tài liệu cho cả tổ chức. Tài liệu mô tả sai code — lệnh không còn, đường dẫn đã đổi, con số đã khác — làm người đọc làm sai và mất niềm tin vào mọi tài liệu khác. Sai lệch thường xuất hiện khi sửa code mà quên tài liệu nhắc tới nó.

## ✅ QUYẾT ĐỊNH

- Mỗi lần sửa code, người sửa (kể cả AI agent) kiểm tra mọi tài liệu liên quan — `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/adr/`, `rulesets/README.md`, docstring, chú thích — còn đúng với code hiện tại; sai thì sửa trong cùng Pull Request.
- Không ghi con số dễ lệch (số nhãn, số team, số quyết định…) vào câu chữ khi không cần.
- `validate.py` (`checkDocsMatchCode()`) kiểm tra phần đối chiếu được bằng máy:
    - Lệnh `make …`, đường dẫn trong `scripts/`, `docs/`, `rulesets/`, `workflow-templates/`, `repository-templates/`, `.github/workflows/` và hàm `tênHàm()` được nhắc trong tài liệu Markdown phải có thật.
    - `README.md` liệt kê đủ lệnh trong `Makefile`, script trong `scripts/` và workflow trong `.github/workflows/`.
- Người đánh giá Pull Request (kể cả GitHub Copilot) đối chiếu tài liệu với code thay đổi.

## ⚖️ HỆ QUẢ

- Pull Request đổi tên lệnh, script, hàm hay workflow mà quên tài liệu sẽ không qua `make check`.
- Phần mô tả hành vi (câu chữ) vẫn cần người kiểm tra — kiểm tra tự động chỉ bắt được tên và đường dẫn.
