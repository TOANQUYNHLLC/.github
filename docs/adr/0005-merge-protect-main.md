# 0005. GỘP HAI RULESET THÀNH PROTECT MAIN

- **Trạng thái:** Bị thay thế một phần bởi [0006](0006-allow-all-merge-methods.md) (cách hợp nhất, lịch sử tuyến tính)
- **Ngày:** 2026-09-26
- **Điều chỉnh:** [0004](0004-squash-merge-and-rulesets.md) — danh sách bỏ qua của repository `.github`

## 📌 BỐI CẢNH

Repository `.github` có hai ruleset cùng áp dụng cho nhánh chính: **Protect Main** (tạo trên web) và **Bảo vệ nhánh chính — repository .github** (import từ tệp ruleset mẫu trước đây). Hai ruleset chồng nhau khó quản lý và khó biết quy tắc nào đang có hiệu lực.

## ✅ QUYẾT ĐỊNH

- Gộp thành một ruleset tên **Protect Main**, định nghĩa trong một tệp duy nhất `rulesets/protect-main.json` dùng cho mọi repository, gồm toàn bộ quy tắc của cả hai: chỉ Squash and merge, 5 kiểm tra bắt buộc, phê duyệt của `CODEOWNERS` và phê duyệt lại sau lần đẩy cuối, chỉ người quản trị được hủy phê duyệt, commit có chữ ký, lịch sử tuyến tính, code quality, cấm force push, cấm xóa, chặn tạo và cập nhật nhánh chính ngoài danh sách bỏ qua.
- Giữ danh sách bỏ qua của Protect Main cũ: hai tài khoản `nguyentrongtoandl` và `trongtoandl81`, chế độ **always**.

## ⚖️ HỆ QUẢ

- Khác với ADR 0004 (vai trò Admin, chỉ khi hợp nhất Pull Request): hai tài khoản quản trị có thể đẩy thẳng lên nhánh chính. Theo `GOVERNANCE.md`, quyền này chỉ dùng khi thật cần; thay đổi thông thường vẫn qua Pull Request.
- Bỏ hai tệp mẫu riêng (`dot-github.json`, `default-branch.json`): repository khác cũng dùng **Protect Main**; `scripts/org-setup.py` chỉ giữ kiểm tra bắt buộc mà repository có job tương ứng.
- Danh sách bỏ qua hai tài khoản chế độ **always** áp dụng cho mọi repository, thay cho vai trò Admin chỉ khi hợp nhất Pull Request của ADR 0004.
