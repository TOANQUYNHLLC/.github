# 0005. GỘP HAI RULESET THÀNH PROTECT MAIN

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-09-26
- **Điều chỉnh:** [0004](0004-squash-merge-and-rulesets.md) — danh sách bỏ qua của repository `.github`

## 📌 BỐI CẢNH

Repository `.github` có hai ruleset cùng áp dụng cho nhánh chính: **Protect Main** (tạo trên web) và **Bảo vệ nhánh chính — repository .github** (import từ `rulesets/dot-github.json`). Hai ruleset chồng nhau khó quản lý và khó biết quy tắc nào đang có hiệu lực.

## ✅ QUYẾT ĐỊNH

- Gộp thành một ruleset tên **Protect Main**, định nghĩa trong `rulesets/dot-github.json`, gồm toàn bộ quy tắc của cả hai: chỉ Squash and merge, 5 kiểm tra bắt buộc, phê duyệt của `CODEOWNERS` và phê duyệt lại sau lần đẩy cuối, chỉ người quản trị được hủy phê duyệt, commit có chữ ký, lịch sử tuyến tính, code quality, cấm force push, cấm xóa, chặn tạo và cập nhật nhánh chính ngoài danh sách bỏ qua.
- Giữ danh sách bỏ qua của Protect Main cũ: hai tài khoản `nguyentrongtoandl` và `trongtoandl81`, chế độ **always**.

## ⚖️ HỆ QUẢ

- Khác với ADR 0004 (vai trò Admin, chỉ khi hợp nhất Pull Request): hai tài khoản quản trị có thể đẩy thẳng lên nhánh chính. Theo `GOVERNANCE.md`, quyền này chỉ dùng khi thật cần; thay đổi thông thường vẫn qua Pull Request.
- Ruleset mẫu `default-branch.json` cho repository khác vẫn theo ADR 0004.
