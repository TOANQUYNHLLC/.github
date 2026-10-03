# 🤖 HƯỚNG DẪN CHO AI AGENT

Hướng dẫn cho AI coding agent (Claude Code, GitHub Copilot, Codex, Cursor…) khi làm việc trong repository `.github` của **CÔNG TY TNHH TOÀN QUỲNH**. Người đóng góp xem [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## 📌 REPOSITORY NÀY LÀ GÌ

Repository `.github` đặc biệt của tổ chức: tệp cộng đồng (`CONTRIBUTING.md`, `SECURITY.md`…), biểu mẫu Issue/Pull Request và `workflow-templates/` được GitHub **áp dụng cho mọi repository** của tổ chức. Mọi thay đổi ảnh hưởng toàn tổ chức — giữ phạm vi nhỏ và chính xác.

---

## 🛠️ LỆNH

| Lệnh          | Khi nào chạy                                                                                                            |
| ------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `make check`  | **Bắt buộc** trước khi đẩy và báo hoàn thành — `scripts/check.py` chạy toàn bộ kiểm tra như GitHub Actions (trừ CodeQL) |
| `make format` | Định dạng lại bằng Prettier và ruff                                                                                     |
| `make test`   | Chỉ chạy test của `scripts/`                                                                                            |

---

## 📐 QUY ƯỚC BẮT BUỘC

- **Định dạng:** theo `.editorconfig` — UTF-8, LF, thụt lề bằng **tab** độ rộng 4 (kể cả Python, JSON, shell, `Makefile`); YAML và Markdown dùng 4 dấu cách. Không tự đổi sang dấu cách hay độ rộng 2.
- **Ngôn ngữ:** nội dung tài liệu và thông báo viết bằng tiếng Việt, chữ dạng dựng sẵn (NFC); tiêu đề Markdown viết HOA (cả hai được `scripts/validate.py` kiểm tra).
- **Branch:** `<tiền tố>/<mô_tả>` bằng tiếng Anh, nối từ bằng `_` (ví dụ `docs/update_readme`). Không commit thẳng lên `main`.
- **Commit và tiêu đề Pull Request:** `<loại>(<phạm vi>): <mô tả>` với loại trong bảng của `CONTRIBUTING.md`.
- **Ruleset:** mọi ruleset nhánh và tag trong `rulesets/` có quy tắc `required_signatures` (ADR 0009) — push ruleset không nhận quy tắc này (ADR 0010); bản cấp tổ chức sinh lại từ bản cấp repository bằng `orgRulesets()` trong `scripts/org-setup.py` (riêng `org-protect-pushes.json` là nguồn, không có bản cấp repository).
- **Script và workflow:** logic kiểm tra và xử lý của workflow viết thành script trong `scripts/` — ưu tiên Python, chỉ dùng ngôn ngữ khác khi Python không phù hợp (ví dụ hook git bằng shell); workflow chỉ gọi một lệnh, không viết `run: |` trong `.github/workflows/` (`validate.py` kiểm tra). Workflow mẫu gọi script của tổ chức (checkout `TOANQUYNHLLC/.github` vào `.org/`); chỉ lệnh riêng của từng ngôn ngữ (gofmt, pip, npm) được viết thẳng. Kiểm tra mà Actions chạy trên Pull Request phải là một nhóm trong `scripts/check.py` để `make check` chạy được tại máy (ADR 0012).
- **Tên hàm:** tiếng Anh, camelCase (`checkLinks`, `syncSettings`; test `testBrokenLink`) — `validate.py` kiểm tra mọi tệp Python (ADR 0012).
- **Workflow:** Mọi action ghim theo commit SHA đầy đủ kèm chú thích phiên bản; khai báo `permissions` tối thiểu, quyền ghi chỉ ở job và có chú thích lý do; khai báo `concurrency`; job nào cũng có `timeout-minutes`. Workflow mẫu: danh mục đầu tiên là danh mục chung của `actions/starter-workflows`. Không đoán SHA — lấy bằng `git ls-remote`.
- **Danh sách phải khớp nhau:** loại commit và tiền tố branch giữa `CONTRIBUTING.md` và `scripts/conventions.py`; đuôi file giữa `scripts/validate.py`, `.editorconfig`, `.gitattributes`; nhãn trong biểu mẫu, `dependabot.yml`, `repository-templates/release.yml`, `stale.yml`, `labeler.yml` phải có trong `labels.yml`; tiền tố branch mới thì thêm luật vào `.github/labeler.yml`. Sửa một nơi thì sửa cả các nơi còn lại.
- **Phiên bản công cụ:** chỉ khai báo trong `mise.toml` (ruff, ShellCheck, actionlint), `.nvmrc` (Node.js) và `package.json` (thư viện Node.js); không ghi phiên bản trong workflow hay script.
- **Biểu mẫu:** biểu mẫu Issue, Discussion (và `FUNDING.yml` nếu bật tài trợ) phải nằm trong `.github/` (GitHub không nhận ở thư mục gốc); liên kết trong biểu mẫu và `PULL_REQUEST_TEMPLATE.md` là URL tuyệt đối vì nội dung hiển thị ở repository khác. Sửa biểu mẫu thì đẩy branch rồi chạy `make forms REF=<branch>` trước khi hợp nhất — GitHub có thể từ chối khóa mà tài liệu vẫn nhắc (ví dụ `type`).
- **CHANGELOG:** thay đổi đáng chú ý ghi vào mục **CHƯA PHÁT HÀNH** của `CHANGELOG.md`.
- **Quyết định lớn:** đọc `docs/adr/` trước khi đổi quy ước; đổi quyết định thì thêm ADR mới, không sửa ADR đã chấp nhận.
- **Commit chỉ đổi định dạng:** thêm SHA vào `.git-blame-ignore-revs`.

---

## 🚫 KHÔNG ĐƯỢC LÀM

- Không đưa mật khẩu, token, khóa API, dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế vào repository.
- Không bỏ qua kiểm tra (`--no-verify`), không bỏ ký commit (`--no-gpg-sign`), không force push lên `main`.
- Không sửa `LICENSE` và không bịa thông tin công ty, người liên hệ, liên kết — chỉ dùng thông tin đã có trong repository.
- Không xóa hoặc nới lỏng test trong `scripts/test_validate.py` để kiểm tra thành công.
- Không thêm tệp không có chức năng cụ thể (cấu hình toàn chú thích, bản sao của tệp khác, script không ai gọi).
