# 00000013. MỖI THAY ĐỔI SỬA LUÔN MỌI CHỖ LIÊN QUAN; TÀI LIỆU KHỚP VỚI CODE

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-08

## 📌 BỐI CẢNH

Repository này vừa là code (script kiểm tra, workflow) vừa là tài liệu cho cả tổ chức. Một tên, đường dẫn hay quy ước thường xuất hiện ở nhiều nơi cùng lúc: script, test, cấu hình, ruleset, biểu mẫu, workflow mẫu, tài liệu, ADR. Sửa một nơi mà quên các nơi còn lại thì repository tự mâu thuẫn — lệnh không còn, đường dẫn đã đổi, con số đã khác, danh sách lệch nhau — làm người đọc làm sai và mất niềm tin vào mọi tài liệu khác.

## ✅ QUYẾT ĐỊNH

- Khi sửa bất cứ gì trong repository — mã nguồn, cấu hình, dependencies, scripts, workflows, ruleset, biểu mẫu, tên tệp, quy ước, nội dung tài liệu hoặc hành vi của hệ thống — người sửa (kể cả AI agent) luôn rà soát toàn bộ repository để tìm và sửa mọi chỗ liên quan trong cùng thay đổi: code gọi tới, test, cấu hình, danh sách phải khớp nhau, biểu mẫu, workflow mẫu, tài liệu (`README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `STRUCTURE.md`, `docs/`, `docs/adr/`, `rulesets/README.md`), docstring, chú thích. Tìm bằng `git grep` theo tên cũ, tên mới và từ khóa của thay đổi; không chỉ dựa vào `make check`.
- Công việc chỉ hoàn tất khi mã nguồn, tests, ví dụ cấu hình và tài liệu liên quan đã thống nhất; biểu mẫu Pull Request có mục kiểm tra tương ứng.
- Không ghi con số dễ lệch (số nhãn, số team, số quyết định…) vào câu chữ khi không cần.
- Tài liệu chỉ mô tả hiện trạng: thứ code không còn (tệp, lệnh, tính năng, cài đặt đã bỏ) xoá khỏi tài liệu, kể cả mục **CHƯA PHÁT HÀNH** của `CHANGELOG.md`; lịch sử thay đổi nằm trong git và GitHub Release.
- `validate.py` (`checkDocsMatchCode()`) kiểm tra phần đối chiếu được bằng máy:
    - Lệnh `make …`, đường dẫn trong `scripts/`, `shell/`, `docs/`, `rulesets/`, `workflow-templates/`, `repository-templates/`, `.devcontainer/`, `.github/workflows/` và hàm `tênHàm()` được nhắc trong tài liệu Markdown phải có thật.
    - `README.md` liệt kê đủ lệnh trong `Makefile`, script trong `scripts/`, `shell/` và workflow trong `.github/workflows/`.
- Người đánh giá Pull Request (kể cả GitHub Copilot) đối chiếu phần còn lại của repository với thay đổi.

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

- **Chỉ sửa đúng chỗ được yêu cầu, để chỗ liên quan cho Pull Request sau**: repository mâu thuẫn giữa hai Pull Request, và chỗ bị bỏ sót thường không ai quay lại sửa.
- **Chỉ dựa vào người đánh giá đọc lại**: sai lệch vẫn lọt — con số trong tài liệu, vị trí hằng số sau khi tách module, lệnh đã đổi tên.
- **Kiểm tra tự động toàn bộ câu chữ**: không khả thi với mô tả hành vi bằng ngôn ngữ tự nhiên; chọn kiểm tra tự động phần đối chiếu được (tên, đường dẫn, danh sách) kết hợp người sửa tự rà soát và người đánh giá.
- **Giữ nội dung về thứ đã bỏ trong tài liệu để tham khảo**: làm tài liệu mâu thuẫn với hiện trạng; lịch sử đã có trong git và GitHub Release.
- **Chỉ đối chiếu `scripts/`**: đổi tên, xóa script tiện ích trong `shell/` hay script Dev Container thì tài liệu vẫn nhắc tới tệp không còn.

## ⚖️ HỆ QUẢ

- Pull Request lớn hơn vì gồm cả các chỗ liên quan, nhưng mỗi Pull Request để lại repository nhất quán.
- Pull Request đổi tên lệnh, script, hàm, tệp hay workflow mà quên tài liệu sẽ không qua `make check`.
- Phần mô tả hành vi (câu chữ) và liên kết từ repository khác vẫn cần người kiểm tra — kiểm tra tự động chỉ bắt được tên và đường dẫn trong repository này.
