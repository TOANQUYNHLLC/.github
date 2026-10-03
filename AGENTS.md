# 🤖 HƯỚNG DẪN CHO AI AGENT

Hướng dẫn cho AI coding agent (Claude Code, GitHub Copilot, Codex, Cursor…) khi làm việc trong repository `.github` của **CÔNG TY TNHH TOÀN QUỲNH**. Người đóng góp xem [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## 📌 REPOSITORY NÀY LÀ GÌ

Repository `.github` đặc biệt của tổ chức: tệp cộng đồng (`CONTRIBUTING.md`, `SECURITY.md`…), biểu mẫu Issue/Pull Request và `workflow-templates/` được GitHub **áp dụng cho mọi repository** của tổ chức. Mọi thay đổi ảnh hưởng toàn tổ chức — giữ phạm vi nhỏ và chính xác.

---

## 🛠️ LỆNH

| Lệnh               | Khi nào chạy                                                                                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `make check`       | **Luôn chạy trước khi đẩy** (hook `pre-push` tự chạy) và trước khi báo hoàn thành — `scripts/check.py` chạy toàn bộ kiểm tra như GitHub Actions (trừ CodeQL) |
| `make org-preview` | **Luôn chạy sau khi kéo code mới** (hook `post-merge` tự chạy sau `git pull`) — so cài đặt trên GitHub với code; chỉ xem trước                               |
| `make hooks`       | Một lần sau khi clone: cài hook `pre-commit`, `pre-push`, `post-merge`                                                                                       |
| `make format`      | Định dạng lại bằng Prettier và ruff                                                                                                                          |
| `make test`        | Chỉ chạy test của `scripts/`                                                                                                                                 |

---

## 📐 QUY ƯỚC BẮT BUỘC

- **Định dạng:** theo `.editorconfig` — UTF-8, LF, thụt lề bằng **tab** độ rộng 4 (kể cả Python, JSON, shell, `Makefile`); YAML và Markdown dùng 4 dấu cách. Không tự đổi sang dấu cách hay độ rộng 2.
- **Ngôn ngữ:** nội dung tài liệu và thông báo viết bằng tiếng Việt, chữ dạng dựng sẵn (NFC); tiêu đề Markdown viết HOA (cả hai được `scripts/validate.py` kiểm tra).
- **Branch:** `<tiền tố>/<mô_tả>` bằng tiếng Anh, nối từ bằng `_` (ví dụ `docs/update_readme`). Không commit thẳng lên `main`.
- **Commit và tiêu đề Pull Request:** `<loại>(<phạm vi>): <mô tả>` với loại trong bảng của `CONTRIBUTING.md`.
- **Ruleset:** mọi ruleset nhánh và tag trong `rulesets/` có quy tắc `required_signatures` (ADR 0009) — push ruleset không nhận quy tắc này (ADR 0010); bản cấp tổ chức sinh lại từ bản cấp repository bằng `orgRulesets()` trong `scripts/org-setup.py` (riêng `org-protect-pushes.json` là nguồn, không có bản cấp repository).
- **Kiểm tra luôn là tệp riêng:** mọi kiểm tra viết thành script trong `scripts/`, **ưu tiên Python** (kể cả git hook — `scripts/git-hooks.py`); nếu ngôn ngữ khác xử lý việc đó tốt hơn thì viết bằng ngôn ngữ đó và ghi dòng `Không viết bằng Python vì: <lý do>` ở đầu tệp (ví dụ `.devcontainer/post-create.sh`) — `validate.py` báo lỗi khi thiếu (ADR 0015). **Không** viết kiểm tra trực tiếp trong tệp `.yml`, `.yaml`, kể cả workflow mẫu. Mỗi bước workflow gọi một lệnh: không `run: |`, không `shell: python`, không mã nhúng `python -c`/`node -e`/`bash -c`; điều kiện dùng `if:` của GitHub Actions (`validate.py` kiểm tra). Workflow mẫu gọi script của tổ chức (checkout `TOANQUYNHLLC/.github` vào `.org/`). Kiểm tra mà Actions chạy trên Pull Request phải là một nhóm trong `scripts/check.py` để `make check` chạy được tại máy (ADR 0012, 0013, 0014, 0015).
- **Tên hàm:** tiếng Anh, camelCase (`checkLinks`, `syncSettings`; test `testBrokenLink`) — `validate.py` kiểm tra mọi tệp Python (ADR 0012).
- **Workflow:** Mọi action ghim theo commit SHA đầy đủ kèm chú thích phiên bản; khai báo `permissions` tối thiểu, quyền ghi chỉ ở job và có chú thích lý do; khai báo `concurrency`; job nào cũng có `timeout-minutes`. Workflow mẫu: danh mục đầu tiên là danh mục chung của `actions/starter-workflows`. Không đoán SHA — lấy bằng `git ls-remote`.
- **Danh sách phải khớp nhau:** loại commit và tiền tố branch giữa `CONTRIBUTING.md` và `scripts/conventions.py`; đuôi file giữa `scripts/validate.py`, `.editorconfig`, `.gitattributes`; nhãn trong biểu mẫu, `dependabot.yml`, `repository-templates/release.yml`, `stale.yml`, `labeler.yml` phải có trong `labels.yml`; tiền tố branch mới thì thêm luật vào `.github/labeler.yml`. Sửa một nơi thì sửa cả các nơi còn lại.
- **Phiên bản công cụ:** chỉ khai báo trong `mise.toml` (ruff, ShellCheck, actionlint), `.nvmrc` (Node.js) và `package.json` (thư viện Node.js); không ghi phiên bản trong workflow hay script.
- **Biểu mẫu:** biểu mẫu Issue, Discussion (và `FUNDING.yml` nếu bật tài trợ) phải nằm trong `.github/` (GitHub không nhận ở thư mục gốc); biểu mẫu Pull Request cũng đặt ở `.github/` để mọi biểu mẫu một chỗ; liên kết trong biểu mẫu và `.github/PULL_REQUEST_TEMPLATE.md` là URL tuyệt đối vì nội dung hiển thị ở repository khác. Sửa biểu mẫu thì đẩy branch rồi chạy `make forms REF=<branch>` trước khi hợp nhất — GitHub có thể từ chối khóa mà tài liệu vẫn nhắc (ví dụ `type`).
- **CHANGELOG:** thay đổi đáng chú ý ghi vào mục **CHƯA PHÁT HÀNH** của `CHANGELOG.md`.
- **Quyết định lớn:** đọc `docs/adr/` trước khi đổi quy ước; đổi quyết định thì thêm ADR mới, không sửa ADR đã chấp nhận.
- **Commit chỉ đổi định dạng:** thêm SHA vào `.git-blame-ignore-revs`.

---

## 🚫 KHÔNG ĐƯỢC LÀM

- Không đưa mật khẩu, token, khóa API, dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế vào repository.
- Không bỏ qua kiểm tra (`--no-verify`), không bỏ ký commit (`--no-gpg-sign`), không force push lên `main`.
- Không sửa `LICENSE` và không bịa thông tin công ty, người liên hệ, liên kết — chỉ dùng thông tin đã có trong repository.
- Không xóa hoặc nới lỏng test trong `scripts/test_scripts.py` để kiểm tra thành công.
- Không thêm tệp không có chức năng cụ thể (cấu hình toàn chú thích, bản sao của tệp khác, script không ai gọi).
