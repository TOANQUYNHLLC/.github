# 🤖 HƯỚNG DẪN CHO AI AGENT

Quy tắc làm việc cho AI coding agent trong bộ tài nguyên `.github` của **CÔNG TY TNHH TOÀN QUỲNH**. Người đóng góp xem [`CONTRIBUTING.md`](CONTRIBUTING.md). Khi được giao rà soát, sửa và đồng bộ toàn dự án, làm theo [`specs/jobs-guideline.md`](specs/jobs-guideline.md).

---

## 📌 REPOSITORY NÀY LÀ GÌ

Repository `.github` đặc biệt của tổ chức: GitHub dùng tệp cộng đồng (`CONTRIBUTING.md`, `SECURITY.md`…) và biểu mẫu làm mặc định khi repository đích không có bản riêng tương ứng. `workflow-templates/` cung cấp mẫu để chọn và tạo workflow trong từng repository; cấu hình không tự sao chép hoặc tự chạy ở repository khác. Thay đổi tài nguyên dùng chung có thể ảnh hưởng toàn tổ chức — giữ phạm vi nhỏ và chính xác.

---

## 🛠️ LỆNH

| Lệnh                 | Khi nào chạy                                                                                                                                                                                                                                                                        |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make check`         | **Luôn chạy trước khi đẩy** (hook `pre-push` kiểm tra đúng nội dung được đẩy: commit hết hoặc `git stash -u` trước; chỉ đẩy tag thì bỏ qua) và trước khi báo hoàn thành. `scripts/check.py` chạy các nhóm tại máy; Dependency Review và CodeQL có phạm vi riêng trên GitHub Actions |
| `make ruleset-files` | Sinh mẫu ruleset cấp tổ chức tại máy; không ghi GitHub                                                                                                                                                                                                                              |
| `make hooks`         | Một lần sau khi clone: cài hook `pre-commit`, `pre-push`, `post-merge`, `post-rewrite` (danh sách trong `scripts/git-hooks.py`; cảnh báo khi `core.hooksPath` làm git bỏ qua hook)                                                                                                  |
| `make format`        | Định dạng lại bằng Prettier và ruff                                                                                                                                                                                                                                                 |
| `make test`          | Chỉ chạy test của `scripts/`                                                                                                                                                                                                                                                        |

---

## 🔒 PHẠM VI CÔNG KHAI

Repository cung cấp tài nguyên cộng đồng và công cụ kiểm tra, sinh mẫu, phát hành phục vụ các tài nguyên đó. Danh sách người duy trì và actor của mẫu ruleset là nguồn đối chiếu công khai cho quy trình đóng góp. Không đưa bản sao cài đặt thực tế, danh mục repository riêng tư, dữ liệu team và quyền nội bộ, công cụ sao lưu hoặc đồng bộ tổ chức vào dự án. Phạm vi theo [ADR 00000014](docs/adr/00000014-public-repository-scope.md).

## 📐 NỘI DUNG VÀ TÊN GỌI

- **Định dạng:** theo `.editorconfig` — UTF-8, LF, thụt lề bằng **tab** độ rộng 4 (kể cả Python, JSON, shell, `Makefile`); YAML và Markdown dùng 4 dấu cách. Không tự đổi sang dấu cách hay độ rộng 2.
- **Ngôn ngữ:** nội dung tài liệu và thông báo viết bằng tiếng Việt, chữ dạng dựng sẵn (NFC); tiêu đề Markdown viết HOA. Riêng chữ trên huy hiệu (badge) viết **tiếng Anh, hoa đầu mỗi từ** (`Last Commit`, `Code Style: Prettier`) — cả chữ thay thế lẫn nhãn; huy hiệu shields.io đặt `label=`, huy hiệu workflow dùng shields.io vì huy hiệu gốc của GitHub lấy chữ theo tên workflow. `scripts/validate.py` kiểm tra cả ba.
- **Tên hàm, tham số, biến tự đặt:** tiếng Anh, camelCase (`checkLinks`, `syncSettings`, `changelogPath`; test `testBrokenLink`); hằng số `UPPER_CASE`, lớp `PascalCase`. Quy tắc chỉ áp dụng cho tên tự đặt; cú pháp của ngôn ngữ giữ nguyên — từ khóa, tên dựng sẵn, `__init__`, tên thư viện quy định (`setUp`, `do_GET` của `http.server`, `http_open` của `urllib`), tham số từ khóa khi gọi thư viện (`capture_output=True`), khóa JSON/YAML của định dạng bên ngoài, biến môi trường; viết theo cách thông thường của thư viện, không viết vòng để né quy tắc. `validate.py` kiểm tra mọi tệp Python (ADR 00000010).
- **Tên tệp, thư mục tự đặt:** tiếng Anh, kebab-case theo nội dung (`check-markdown-links.py`, `docs/local-checks.md`, `organization-protect-main.json`, `bug-report.yml`); module Python được `import` viết một từ (`rulesets`); ADR `NNNNNNNN-short-title.md`. Tên do GitHub hoặc công cụ quy định giữ nguyên: tên VIẾT HOA (`README.md`, `CODEOWNERS`, `ISSUE_TEMPLATE/`), `Makefile`, `__init__.py`, `test_*.py`, tệp và thư mục bắt đầu bằng dấu chấm. `checkFileNames()` trong `validate.py` kiểm tra (ADR 00000010).

## 🔀 ĐÓNG GÓP VÀ KIỂM TRA

- **Branch:** `<tiền tố>/<mô_tả>` bằng tiếng Anh, nối từ bằng `_` (ví dụ `docs/update_readme`). Không commit thẳng lên `main`.
- **Commit và tiêu đề Pull Request:** `<loại>(<phạm vi>): <mô tả>` với loại trong bảng của `CONTRIBUTING.md`.
- **Kiểm tra luôn là tệp riêng:** mọi kiểm tra viết thành script trong `scripts/`, **ưu tiên Python** (kể cả git hook — `scripts/git-hooks.py`); nếu ngôn ngữ khác xử lý việc đó tốt hơn thì viết bằng ngôn ngữ đó và ghi dòng `Không viết bằng Python vì: <lý do>` ở đầu tệp (ví dụ `.devcontainer/post-create.sh`) — `validate.py` báo lỗi khi thiếu (ADR 00000009). **Không** viết kiểm tra trực tiếp trong tệp `.yml`, `.yaml`, kể cả workflow mẫu. Mỗi bước workflow gọi một lệnh: không `run: |`, không `shell: python`, không mã nhúng `python -c`/`node -e`/`bash -c`; điều kiện dùng `if:` của GitHub Actions (`validate.py` kiểm tra). Workflow mẫu gọi script của tổ chức (checkout `TOANQUYNHLLC/.github` vào `.org/`). Kiểm tra PR do dự án tự viết phải thuộc một nhóm trong `scripts/check.py` để chạy được tại máy; Dependency Review và CodeQL dùng action chuyên biệt trên GitHub (ADR 00000009).
- **Danh sách phải khớp nhau:** loại commit và tiền tố branch giữa `CONTRIBUTING.md` và `scripts/conventions.py`; đuôi file giữa `scripts/validation/formatting.py`, `.editorconfig`, `.gitattributes`; nhãn trong biểu mẫu, `dependabot.yml`, `.github/release.yml`, `repository-templates/release.yml`, `stale.yml`, `labeler.yml` phải có trong `labels.yml`; tiền tố branch mới thì thêm luật vào `.github/labeler.yml`; người quản trị giữa `MAINTAINERS.md` và `MAINTAINERS` của `scripts/maintainers.py`, và số tài khoản trong danh sách bỏ qua của `rulesets/protect-*.json`. Sửa một nơi thì sửa cả các nơi còn lại.
- **Commit chỉ đổi định dạng:** tạo hoặc cập nhật `.git-blame-ignore-revs` với SHA cần bỏ qua và cấu hình `git blame` dùng tệp đó.

## ⚙️ CẤU HÌNH VÀ TÀI NGUYÊN

- **Ruleset:** mọi ruleset nhánh và tag trong `rulesets/` có quy tắc `required_signatures` (ADR 00000007) — push ruleset không nhận quy tắc này (ADR 00000005); bản cấp tổ chức sinh lại từ bản cấp repository bằng `make ruleset-files` (`orgRulesets()` trong `scripts/rulesets.py`), cùng thứ tự và bố cục dòng để so hai tệp chỉ thấy điểm khác. `protect-pushes.json` là nguồn cho bản tổ chức và để import riêng ở cấp repository khi gói và loại repository hỗ trợ.
- **Workflow:** Mọi action ghim theo commit SHA đầy đủ kèm chú thích phiên bản; khai báo `permissions` tối thiểu, quyền ghi chỉ ở job và có chú thích lý do; khai báo `concurrency`; job nào cũng có `timeout-minutes`; không viết `${{ … }}` trong `run:` — truyền qua `env:` (chống chèn lệnh). Workflow mẫu: danh mục đầu tiên là danh mục chung của `actions/starter-workflows`. Không đoán SHA — lấy bằng `git ls-remote`.
- **Phiên bản công cụ:** chỉ khai báo trong `mise.toml` (Python, ruff, ShellCheck, actionlint), `.nvmrc` (Node.js; `devEngines` của `package.json` ghi đúng giá trị của `.nvmrc`) và `package.json` (thư viện Node.js); không ghi phiên bản trong workflow hay script. CI dùng `python3` có sẵn của runner (script cần ≥ 3.11) ; image Dev Container ghim đúng bản Python của `mise.toml` (ADR 00000008).
- **Biểu mẫu:** biểu mẫu Issue, Discussion, `VULNERABILITY_REPORT.yml` hoặc `.yaml` (và `FUNDING.yml` nếu bật tài trợ) phải nằm trong `.github/` (GitHub không nhận ở thư mục gốc); biểu mẫu Pull Request cũng đặt ở `.github/` để mọi biểu mẫu một chỗ; liên kết trong biểu mẫu, `.github/PULL_REQUEST_TEMPLATE.md` và các mẫu riêng trong `.github/PULL_REQUEST_TEMPLATE/` là URL tuyệt đối vì nội dung hiển thị ở repository khác. Sửa biểu mẫu thì chạy `make validate`; Issue cần đẩy branch rồi kiểm tra bằng `make forms REF=<branch>` trước khi hợp nhất — GitHub có thể từ chối khóa mà tài liệu vẫn nhắc (ví dụ `type`). Đổi tên tệp biểu mẫu Issue mà giữ `name` thì ref khác báo `Name must be unique` (GitHub so với biểu mẫu trên nhánh mặc định; `make validate` đã kiểm tra trùng tên trong branch) — xác minh bằng `make forms` sau khi hợp nhất. Discussion chỉ xác minh được trên nhánh mặc định: chạy `make forms` sau khi hợp nhất. `make forms` trên ref khác có Discussion báo chưa xác minh và trả mã lỗi; biểu mẫu lỗ hổng riêng tư được kiểm tra tại máy bằng validator và cần xác minh trên trang báo cáo riêng tư khi được áp dụng.

## 📝 TÀI LIỆU VÀ PHÁT HÀNH

- **Sửa mọi chỗ liên quan:** khi sửa bất cứ gì trong project — mã nguồn, cấu hình, ruleset, biểu mẫu, workflow, tên tệp, quy ước hay nội dung tài liệu — luôn rà soát toàn bộ repository và sửa lại mọi chỗ liên quan trong cùng thay đổi: code gọi tới, test, cấu hình, danh sách phải khớp nhau, workflow mẫu, tài liệu, ADR, docstring, chú thích. Tìm bằng `git grep` theo tên cũ, tên mới và từ khóa của thay đổi; không chỉ dựa vào `make check` (ADR 00000013).
- **Tài liệu khớp code:** Mỗi khi thay đổi mã nguồn, cấu hình, dependencies, scripts, workflows hoặc hành vi của hệ thống, phải kiểm tra những tài liệu liên quan có còn khớp với trạng thái hiện tại hay không. Nếu có sai lệch, phải cập nhật hoặc xoá nội dung lỗi thời trong cùng thay đổi. Chỉ coi công việc hoàn tất khi mã nguồn, tests, ví dụ cấu hình và tài liệu liên quan đã thống nhất. README là điểm bắt đầu; hướng dẫn chuyên đề mô tả cách vận hành; mỗi ADR trình bày một quyết định cùng lý do. Tài liệu liên quan gồm `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/`, `rulesets/README.md`, docstring, chú thích; nội dung phải thống nhất theo hiện trạng, không nối tiếp các mục thêm/sửa hoặc ghi lại thứ đã bỏ. Không ghi con số dễ lệch (số nhãn, số team…) vào câu chữ. `validate.py` bắt phần đối chiếu được: lệnh `make`, đường dẫn, hàm được nhắc tới phải có thật; `README.md` liệt kê đủ lệnh make, script (cả `shell/`), workflow (ADR 00000013).
- **Đọc và đối chiếu từng tệp:** khi được giao rà soát toàn bộ tài liệu, kiểm kê cả tệp ẩn và biểu mẫu; đọc đầy đủ từng tệp, chia phần nếu đầu ra bị cắt. Đối chiếu nội dung với tất cả nơi tham chiếu và các nguồn quy tắc liên quan; không suy ra toàn bộ tài liệu đúng chỉ từ việc tìm từ khóa hoặc chạy validator. Kết quả bàn giao nêu phạm vi đã đọc, nguồn đối chiếu và kiểm chứng thực tế; không ghi báo cáo rà soát vào tài liệu dự án.
- **Nội dung phát hành:** phiên bản có dạng `Stable.vYYYY.MM.DDXXXX` / `Beta.vYYYY.MM.DDXXXX`, số thứ tự gồm 4 chữ số, dùng chung cho hai kênh và bắt đầu lại từ `0001` mỗi tháng (ADR 00000012). Khi chuẩn bị phát hành, điền tóm tắt thay đổi và ảnh hưởng với người sử dụng vào mục **CHƯA PHÁT HÀNH** của `CHANGELOG.md`; nhóm theo hướng dẫn PHÁT HÀNH trong `README.md`, bỏ nhóm trống, dùng liên kết tuyệt đối. Khi chuyển phiên bản, giữ mục vừa chuẩn bị để tạo Release; lần chuẩn bị tiếp theo thay mục đó, lịch sử các bản đã công bố nằm ở GitHub Releases. Tài liệu dự án trình bày hiện trạng; không thêm mục lịch sử phát triển hay lịch sử thay đổi. Viết tài liệu độc lập theo hiện trạng của dự án; không ghi danh sách commit, lịch sử phát triển, nhật ký sửa lỗi, diễn biến dọn dẹp, báo cáo rà soát, log kiểm tra hoặc số đo thử nghiệm. Bằng chứng kiểm chứng thuộc PR hoặc bàn giao.
- **Quyết định lớn:** đọc `docs/adr/` trước khi đổi quy ước; mỗi chủ đề một ADR mô tả quyết định hiện hành — đổi quyết định thì cập nhật ADR của chủ đề đó, chủ đề mới thì thêm ADR (`docs/adr/README.md`).

---

## 🚫 KHÔNG ĐƯỢC LÀM

- Không đưa mật khẩu, token, khóa API, dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế vào repository.
- Không bỏ qua kiểm tra (`--no-verify`), không bỏ ký commit (`--no-gpg-sign`), không force push lên `main`.
- Không tự thêm giấy phép nguồn mở hoặc tuyên bố cho phép phân phối lại nội dung của dự án. Không bịa thông tin công ty, người liên hệ, liên kết — chỉ dùng thông tin đã có trong repository.
- Không xóa hoặc nới lỏng test trong `scripts/test_*.py` để kiểm tra thành công.
- Không thêm tệp không có chức năng cụ thể (cấu hình toàn chú thích, bản sao của tệp khác, script không ai gọi).
