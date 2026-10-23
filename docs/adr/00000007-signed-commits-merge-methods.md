# 00000007. COMMIT CÓ CHỮ KÝ TRÊN NHÁNH CHÍNH VÀ TAG; PHƯƠNG THỨC HỢP NHẤT

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03

## 📌 BỐI CẢNH

Commit đi vào nhánh chính hoặc được dùng làm mốc phát hành cần xác minh được chữ ký. Các phương thức hợp nhất có cách tạo commit khác nhau.

## ✅ QUYẾT ĐỊNH

Mọi mẫu ruleset nhánh và tag trong `rulesets/` khai báo `required_signatures`. Push ruleset áp dụng hợp đồng riêng theo [ADR 00000005](00000005-organization-protect-pushes.md).

Mẫu Protect Main cho phép Merge, Squash và Rebase; ưu tiên Squash khi hợp nhất PR. Phương thức được chọn phải đáp ứng mọi bảo vệ và cài đặt đang có hiệu lực. Bản tổ chức do `orgRuleset()` sinh áp dụng nhánh mặc định cùng `refs/heads/main`.

Người đóng góp ký commit bằng GPG hoặc SSH. Rebase tại máy phải ký các commit được tạo lại. Script phát hành dùng GraphQL `createCommitOnBranch` để tạo commit được GitHub ký.

Nguồn của quyết định: [rulesets/protect-main.json](../../rulesets/protect-main.json), [rulesets/protect-release-tags.json](../../rulesets/protect-release-tags.json), [scripts/orgsetup/github.py](../../scripts/orgsetup/github.py).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Yêu cầu chữ ký xác minh commit trong khi lựa chọn phương thức hợp nhất đáp ứng nhu cầu giữ hoặc gộp thay đổi. [GitHub không ký lại commit do Rebase and merge tạo](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification#signature-verification-for-rebase-and-merge), nên việc cho phép phương thức này không bảo đảm PR đáp ứng ruleset.

## ⚖️ HỆ QUẢ

Validator đối chiếu yêu cầu chữ ký và các phương thức trong nguồn mẫu. Người quản trị kiểm tra chữ ký trước hợp nhất hoặc phát hành; quyền bỏ qua ruleset không miễn nghĩa vụ ký commit của dự án.
