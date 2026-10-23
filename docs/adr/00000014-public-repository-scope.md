# 00000014. PHẠM VI REPOSITORY CÔNG KHAI

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-23

## 📌 BỐI CẢNH

Tài nguyên cộng đồng, công cụ kiểm tra và bộ quản trị cài đặt GitHub dùng chung quy ước, validator và tests. Một nguồn duy nhất giúp mỗi thay đổi chỉ cần thực hiện và kiểm chứng một lần.

## ✅ QUYẾT ĐỊNH

Repository `.github` công khai là nguồn duy nhất cho hồ sơ tổ chức, tài liệu cộng đồng, biểu mẫu, workflow mẫu, nhãn, ruleset, công cụ kiểm tra, sinh mẫu, phát hành và bộ quản trị cài đặt GitHub trong `scripts/orgsetup/`.

`github-settings.json` là nguồn cài đặt tổ chức và repository theo [ADR 00000015](00000015-local-github-settings.md), được công khai cùng repository: cấu trúc team, quyền repository, chính sách và trạng thái tính năng đọc được qua API. Giá trị riêng — `billing_email`, giá trị variables, URL webhook, IP allow list, regex tùy chỉnh, định nghĩa registry, secrets và bản khôi phục thủ công — không vào Git; nguồn chỉ giữ tham chiếu, giá trị nằm ở thư mục riêng của `scripts/orgsetup/localdata.py` và gói sao lưu ngoài repository.

Người duy trì và actor trong ruleset là thông tin công khai để đối chiếu quy trình đóng góp.

Nguồn của quyết định: [scripts/orgsetup/configuration.py](../../scripts/orgsetup/configuration.py), [scripts/orgsetup/localdata.py](../../scripts/orgsetup/localdata.py), [scripts/validation/repository.py](../../scripts/validation/repository.py), [AGENTS.md](../../AGENTS.md).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Tách bộ quản trị và nguồn cài đặt sang repository riêng tư giữ kín cấu trúc team và trạng thái bảo mật, nhưng phải duy trì hai bản của cùng tài liệu, validator và tests; repository riêng tư trên gói Free không dùng được ruleset. Công khai bộ công cụ nhưng giữ `github-settings.json` ngoài Git cần thêm luồng nạp và sao lưu nguồn cho mọi lệnh, validator và tests.

## ⚖️ HỆ QUẢ

Mọi thay đổi đi qua một repository, một bộ kiểm tra và ruleset của nhánh chính. Ai xem repository cũng đọc được cấu trúc team, quyền repository và cài đặt bảo mật của tổ chức; trước khi nhập hoặc commit nguồn cài đặt, người quản trị kiểm tra không có giá trị riêng nào ngoài tham chiếu. Sự tồn tại của tệp JSON hoặc YAML không chứng minh chính sách đã có hiệu lực trên GitHub; người quản trị xác minh sau khi áp dụng.
