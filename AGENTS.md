# 🤖 HƯỚNG DẪN CHO AI AGENT

Hướng dẫn cho AI coding agent (Claude Code, GitHub Copilot, Codex, Cursor…) khi làm việc trong repository `.github` của **CÔNG TY TNHH TOÀN QUỲNH**. Người đóng góp xem [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## 📌 REPOSITORY NÀY LÀ GÌ

Repository `.github` đặc biệt của tổ chức: tệp cộng đồng (`CONTRIBUTING.md`, `SECURITY.md`…), biểu mẫu Issue/Pull Request và `workflow-templates/` được GitHub **áp dụng cho mọi repository** của tổ chức. Mọi thay đổi ảnh hưởng toàn tổ chức — giữ phạm vi nhỏ và chính xác.

---

## 🛠️ LỆNH

| Lệnh          | Khi nào chạy                                                         |
| ------------- | -------------------------------------------------------------------- |
| `make check`  | **Bắt buộc** trước khi báo hoàn thành — chạy toàn bộ kiểm tra như CI |
| `make format` | Định dạng lại bằng Prettier và ruff                                  |
| `make test`   | Chỉ chạy test của `scripts/`                                         |

---

## 📐 QUY ƯỚC BẮT BUỘC

- **Định dạng:** theo `.editorconfig` — UTF-8, LF, thụt lề bằng **tab** độ rộng 4 (kể cả Python, JSON, shell, `Makefile`); YAML và Markdown dùng 4 dấu cách. Không tự đổi sang dấu cách hay độ rộng 2.
- **Ngôn ngữ:** nội dung tài liệu và thông báo viết bằng tiếng Việt, chữ dạng dựng sẵn (NFC); tiêu đề Markdown viết HOA (cả hai được `scripts/validate.py` kiểm tra).
- **Branch:** `<tiền tố>/<mô_tả>` bằng tiếng Anh, nối từ bằng `_` (ví dụ `docs/update_readme`). Không commit thẳng lên `main`.
- **Commit và tiêu đề Pull Request:** `<loại>(<phạm vi>): <mô tả>` với loại trong bảng của `CONTRIBUTING.md`.
- **Workflow:** mọi action ghim theo commit SHA đầy đủ kèm chú thích phiên bản; khai báo `permissions` tối thiểu, quyền ghi chỉ ở job và có chú thích lý do; khai báo `concurrency`; job nào cũng có `timeout-minutes`. Workflow mẫu: danh mục đầu tiên là danh mục chung của `actions/starter-workflows`. Không đoán SHA — lấy bằng `git ls-remote`.
- **Danh sách phải khớp nhau:** loại commit và tiền tố branch giữa `CONTRIBUTING.md` và các workflow `pr-title.yml`, `branch-name.yml`; đuôi file giữa `scripts/validate.py`, `.editorconfig`, `.gitattributes`; nhãn trong biểu mẫu, `dependabot.yml`, `release.yml`, `stale.yml` phải có trong `labels.yml`. Sửa một nơi thì sửa cả các nơi còn lại.
- **Phiên bản công cụ:** chỉ khai báo trong `mise.toml` (ruff, ShellCheck, actionlint), `.nvmrc` (Node.js) và `package.json` (thư viện Node.js); không ghi phiên bản trong workflow hay script.
- **Biểu mẫu:** biểu mẫu Issue, Discussion và `FUNDING.yml` phải nằm trong `.github/` (GitHub không nhận ở thư mục gốc); liên kết trong biểu mẫu và `PULL_REQUEST_TEMPLATE.md` là URL tuyệt đối vì nội dung hiển thị ở repository khác. Sửa biểu mẫu thì đẩy branch rồi chạy `make forms REF=<branch>` trước khi hợp nhất — GitHub có thể từ chối khóa mà tài liệu vẫn nhắc (ví dụ `type`).
- **CHANGELOG:** thay đổi đáng chú ý ghi vào mục **CHƯA PHÁT HÀNH** của `CHANGELOG.md`.
- **Quyết định lớn:** đọc `docs/adr/` trước khi đổi quy ước; đổi quyết định thì thêm ADR mới, không sửa ADR đã chấp nhận.
- **Commit chỉ đổi định dạng:** thêm SHA vào `.git-blame-ignore-revs`.

---

## 🚫 KHÔNG ĐƯỢC LÀM

- Không đưa mật khẩu, token, khóa API, dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế vào repository.
- Không bỏ qua kiểm tra (`--no-verify`), không bỏ ký commit (`--no-gpg-sign`), không force push lên `main`.
- Không sửa `LICENSE` và không bịa thông tin công ty, người liên hệ, liên kết — chỉ dùng thông tin đã có trong repository.
- Không xóa hoặc nới lỏng test trong `scripts/test_validate.py` để kiểm tra thành công.
