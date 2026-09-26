# 🛡️ RULESET BẢO VỆ NHÁNH CHÍNH

Mẫu [ruleset](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) để các quy tắc trong [`CONTRIBUTING.md`](../CONTRIBUTING.md) được GitHub thực thi, không chỉ nằm trên giấy. Ruleset **không** tự áp dụng từ repository này — người quản trị cần import vào từng repository hoặc cho cả tổ chức.

| Tệp                                          | Dùng cho                                                                                                                                                                                                                                                 |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`default-branch.json`](default-branch.json) | Mọi repository đã thêm workflow mẫu **Kiểm tra tiêu đề Pull Request** và **Kiểm tra tên branch**                                                                                                                                                         |
| [`dot-github.json`](dot-github.json)         | Ruleset **Protect Main** của chính repository `.github`: gộp mọi quy tắc của mẫu chung và Protect Main cũ, bắt buộc thêm các job của `validate.yml`; danh sách bỏ qua là hai tài khoản quản trị (xem [ADR 0005](../docs/adr/0005-merge-protect-main.md)) |

## ⚙️ QUY TẮC ÁP DỤNG CHO NHÁNH MẶC ĐỊNH

- Mọi thay đổi phải qua Pull Request, có ít nhất **1** phê duyệt, trong đó có người trong `CODEOWNERS`; phê duyệt cũ bị hủy khi có commit mới.
- Mọi góp ý phải được giải quyết trước khi hợp nhất; chỉ cho phép **Squash and merge**, lịch sử tuyến tính.
- Các kiểm tra tự động bắt buộc phải thành công trên branch đã cập nhật với nhánh chính.
- Commit phải có chữ ký (GPG hoặc SSH).
- Cấm force push và cấm xóa nhánh chính.
- `default-branch.json`: vai trò **Admin** của repository được bỏ qua ruleset **chỉ khi hợp nhất Pull Request**, để người quản trị hợp nhất được Pull Request của chính mình khi không có người khác duyệt.
- `dot-github.json` thêm: chặn tạo và cập nhật nhánh chính ngoài danh sách bỏ qua, phê duyệt lại sau lần đẩy cuối, chỉ người quản trị được hủy phê duyệt, code quality; danh sách bỏ qua là hai tài khoản quản trị ở chế độ **always** ([ADR 0005](../docs/adr/0005-merge-protect-main.md)).

## 📥 CÁCH IMPORT

1. Mở **Settings → Rules → Rulesets** của repository (hoặc **Settings → Repository → Rulesets** của tổ chức).
2. Chọn **New ruleset → Import a ruleset** và chọn tệp JSON phù hợp.
3. Kiểm tra lại danh sách kiểm tra bắt buộc: tên phải trùng **tên job** trong workflow của repository, nếu không Pull Request sẽ chờ mãi một kiểm tra không tồn tại.
4. Chọn **Create**.
