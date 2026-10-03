# 🤖 HƯỚNG DẪN CHO AI AGENT

Hướng dẫn cho AI coding agent (Claude Code, GitHub Copilot, Codex, Cursor…) khi làm việc trong repository `.github` của **CÔNG TY TNHH TOÀN QUỲNH**. Người đóng góp xem [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## 📌 REPOSITORY NÀY LÀ GÌ

Repository `.github` đặc biệt của tổ chức: tệp cộng đồng (`CONTRIBUTING.md`, `SECURITY.md`…), biểu mẫu Issue/Pull Request và `workflow-templates/` được GitHub **áp dụng cho mọi repository** của tổ chức. Mọi thay đổi ảnh hưởng toàn tổ chức — giữ phạm vi nhỏ và chính xác.

---

## 🛠️ LỆNH

| Lệnh               | Khi nào chạy                                                                                                                                                                                                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `make check`       | **Luôn chạy trước khi đẩy** (hook `pre-push` tự chạy trên đúng nội dung được đẩy: commit hết hoặc `git stash -u` trước; chỉ đẩy tag thì bỏ qua) và trước khi báo hoàn thành — `scripts/check.py` chạy toàn bộ kiểm tra như GitHub Actions (trừ CodeQL) |
| `make org-preview` | **Luôn chạy sau khi kéo code mới** (hook `post-merge` sau `git pull`, `post-rewrite` sau `git pull --rebase` tự chạy) — so cài đặt trên GitHub với code; chỉ xem trước                                                                                 |
| `make hooks`       | Một lần sau khi clone: cài hook `pre-commit`, `pre-push`, `post-merge`, `post-rewrite` (danh sách trong `scripts/git-hooks.py`; cảnh báo khi `core.hooksPath` làm git bỏ qua hook)                                                                     |
| `make format`      | Định dạng lại bằng Prettier và ruff                                                                                                                                                                                                                    |
| `make test`        | Chỉ chạy test của `scripts/`                                                                                                                                                                                                                           |

---

## 📐 QUY ƯỚC BẮT BUỘC

- **Định dạng:** theo `.editorconfig` — UTF-8, LF, thụt lề bằng **tab** độ rộng 4 (kể cả Python, JSON, shell, `Makefile`); YAML và Markdown dùng 4 dấu cách. Không tự đổi sang dấu cách hay độ rộng 2.
- **Ngôn ngữ:** nội dung tài liệu và thông báo viết bằng tiếng Việt, chữ dạng dựng sẵn (NFC); tiêu đề Markdown viết HOA (cả hai được `scripts/validate.py` kiểm tra).
- **Branch:** `<tiền tố>/<mô_tả>` bằng tiếng Anh, nối từ bằng `_` (ví dụ `docs/update_readme`). Không commit thẳng lên `main`.
- **Commit và tiêu đề Pull Request:** `<loại>(<phạm vi>): <mô tả>` với loại trong bảng của `CONTRIBUTING.md`.
- **Ruleset:** mọi ruleset nhánh và tag trong `rulesets/` có quy tắc `required_signatures` (ADR 0006) — push ruleset không nhận quy tắc này (ADR 0007); bản cấp tổ chức sinh lại từ bản cấp repository bằng `orgRulesets()` trong `scripts/orgsetup/rulesets.py` (riêng `org-protect-pushes.json` là nguồn, không có bản cấp repository).
- **Kiểm tra luôn là tệp riêng:** mọi kiểm tra viết thành script trong `scripts/`, **ưu tiên Python** (kể cả git hook — `scripts/git-hooks.py`); nếu ngôn ngữ khác xử lý việc đó tốt hơn thì viết bằng ngôn ngữ đó và ghi dòng `Không viết bằng Python vì: <lý do>` ở đầu tệp (ví dụ `.devcontainer/post-create.sh`) — `validate.py` báo lỗi khi thiếu (ADR 0009). **Không** viết kiểm tra trực tiếp trong tệp `.yml`, `.yaml`, kể cả workflow mẫu. Mỗi bước workflow gọi một lệnh: không `run: |`, không `shell: python`, không mã nhúng `python -c`/`node -e`/`bash -c`; điều kiện dùng `if:` của GitHub Actions (`validate.py` kiểm tra). Workflow mẫu gọi script của tổ chức (checkout `TOANQUYNHLLC/.github` vào `.org/`). Kiểm tra mà Actions chạy trên Pull Request phải là một nhóm trong `scripts/check.py` để `make check` chạy được tại máy (ADR 0009).
- **Tên hàm, tham số, biến tự đặt:** tiếng Anh, camelCase (`checkLinks`, `syncSettings`, `changelogPath`; test `testBrokenLink`); hằng số `UPPER_CASE`, lớp `PascalCase`. Quy tắc chỉ áp dụng cho tên tự đặt; cú pháp của ngôn ngữ giữ nguyên — từ khóa, tên dựng sẵn, `__init__`, tên thư viện quy định (`setUp`, `do_GET` của `http.server`, `http_open` của `urllib`), tham số từ khóa khi gọi thư viện (`capture_output=True`), khóa JSON/YAML của định dạng bên ngoài, biến môi trường; viết theo cách thông thường của thư viện, không viết vòng để né quy tắc. `validate.py` kiểm tra mọi tệp Python (ADR 0010).
- **Workflow:** Mọi action ghim theo commit SHA đầy đủ kèm chú thích phiên bản; khai báo `permissions` tối thiểu, quyền ghi chỉ ở job và có chú thích lý do; khai báo `concurrency`; job nào cũng có `timeout-minutes`. Workflow mẫu: danh mục đầu tiên là danh mục chung của `actions/starter-workflows`. Không đoán SHA — lấy bằng `git ls-remote`.
- **Danh sách phải khớp nhau:** loại commit và tiền tố branch giữa `CONTRIBUTING.md` và `scripts/conventions.py`; đuôi file giữa `scripts/validate.py`, `.editorconfig`, `.gitattributes`; nhãn trong biểu mẫu, `dependabot.yml`, `repository-templates/release.yml`, `stale.yml`, `labeler.yml` phải có trong `labels.yml`; tiền tố branch mới thì thêm luật vào `.github/labeler.yml`; người quản trị giữa `MAINTAINERS.md` và `MAINTAINERS` của `scripts/orgsetup/teams.py`. Sửa một nơi thì sửa cả các nơi còn lại.
- **Phiên bản công cụ:** chỉ khai báo trong `mise.toml` (Python, ruff, ShellCheck, actionlint), `.nvmrc` (Node.js) và `package.json` (thư viện Node.js); không ghi phiên bản trong workflow hay script.
- **Biểu mẫu:** biểu mẫu Issue, Discussion (và `FUNDING.yml` nếu bật tài trợ) phải nằm trong `.github/` (GitHub không nhận ở thư mục gốc); biểu mẫu Pull Request cũng đặt ở `.github/` để mọi biểu mẫu một chỗ; liên kết trong biểu mẫu và `.github/PULL_REQUEST_TEMPLATE.md` là URL tuyệt đối vì nội dung hiển thị ở repository khác. Sửa biểu mẫu thì đẩy branch rồi chạy `make forms REF=<branch>` trước khi hợp nhất — GitHub có thể từ chối khóa mà tài liệu vẫn nhắc (ví dụ `type`).
- **Tài liệu khớp code:** mỗi lần sửa code, kiểm tra mọi tài liệu liên quan (`README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/adr/`, `rulesets/README.md`, docstring, chú thích) còn đúng với code hiện tại; sai thì sửa ngay trong cùng Pull Request. Không ghi con số dễ lệch (số nhãn, số team…) vào câu chữ. `validate.py` bắt phần đối chiếu được: lệnh `make`, đường dẫn, hàm được nhắc tới phải có thật; `README.md` liệt kê đủ lệnh make, script, workflow (ADR 0013).
- **CHANGELOG:** thay đổi đáng chú ý ghi vào mục **CHƯA PHÁT HÀNH** của `CHANGELOG.md`.
- **Quyết định lớn:** đọc `docs/adr/` trước khi đổi quy ước; đổi quyết định thì thêm ADR mới, không sửa ADR đã chấp nhận.
- **Commit chỉ đổi định dạng:** thêm SHA vào `.git-blame-ignore-revs`.

---

## 🚫 KHÔNG ĐƯỢC LÀM

- Không đưa mật khẩu, token, khóa API, dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế vào repository.
- Không bỏ qua kiểm tra (`--no-verify`), không bỏ ký commit (`--no-gpg-sign`), không force push lên `main`.
- Không sửa `LICENSE` và không bịa thông tin công ty, người liên hệ, liên kết — chỉ dùng thông tin đã có trong repository.
- Không xóa hoặc nới lỏng test trong `scripts/test_*.py` để kiểm tra thành công.
- Không thêm tệp không có chức năng cụ thể (cấu hình toàn chú thích, bản sao của tệp khác, script không ai gọi).
