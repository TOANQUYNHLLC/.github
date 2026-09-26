# 📝 NHẬT KÝ THAY ĐỔI

Mọi thay đổi đáng chú ý của repository `.github` thuộc **CÔNG TY TNHH TOÀN QUỲNH** được ghi tại đây.

Định dạng theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Phiên bản đặt theo năm và tháng phát hành, ví dụ `v2026.09.Stable`. Thay đổi mới ghi vào mục **CHƯA PHÁT HÀNH**, rồi chuyển sang một phiên bản khi gắn tag.

---

## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github/compare/v2026.09.Stable...HEAD)

### ✨ THÊM

- Workflow `codeql.yml` (actions, JavaScript, Python), `dependency-review.yml`, `stale.yml` cho chính repository `.github`.
- `.gitmessage` (mẫu commit, bật bằng `make hooks`), `.npmrc` (`engine-strict`, `save-exact`), `.github/copilot-instructions.md`.
- `trongtoandl81` được thêm vào `MAINTAINERS.md`, `CODEOWNERS` và mẫu `CODEOWNERS`, khớp quyền admin thực tế trên GitHub.
- `scripts/org-setup.py` và `make org-preview` — áp dụng cấu hình chung lên mọi repository của tổ chức bằng GitHub CLI: mở Pull Request thêm tệp dùng chung còn thiếu (`dependabot.yml` chỉ gồm ecosystem repository dùng), chỉ cho phép Squash and merge, tạo hoặc cập nhật ruleset, tạo team maintainers, bật Discussions; mặc định chỉ xem trước.
- `docs/adr/` — bản ghi quyết định kiến trúc: thụt lề bằng tab, LF/CRLF, tên branch, Squash and merge và ruleset.
- `.devcontainer/` và `mise.toml` — môi trường phát triển có sẵn công cụ kiểm tra, phiên bản khớp CI.
- `.git-blame-ignore-revs` (bỏ qua commit chuyển Python sang tab), `.mailmap` (gộp tên tác giả viết hoa và dạng Unicode tách dấu), `.shellcheckrc`, `CLAUDE.md` (dùng chung `AGENTS.md`).
- `GOVERNANCE.md` — vai trò, cách ra quyết định, đánh giá và hợp nhất, thay đổi người quản trị; `MAINTAINERS.md` — danh sách người quản trị.
- `DISCUSSION_TEMPLATE/` — biểu mẫu GitHub Discussions cho Ý tưởng, Hỏi đáp và Thảo luận chung.
- `FUNDING.yml` (chưa bật kênh tài trợ), `ROADMAP.md`, `CITATION.cff`, `NOTICE`.
- `.github/release.yml` và mẫu `repository-templates/release.yml` — nhóm nội dung GitHub Release tự tạo theo nhãn.
- `AGENTS.md` — hướng dẫn cho AI coding agent; `.vscode/extensions.json` — extension VS Code khuyến nghị.
- Workflow `branch-name.yml` (kèm bản mẫu) bắt buộc tên branch theo quy ước trong `CONTRIBUTING.md`; bỏ qua branch của Dependabot.
- Workflow mẫu `release.yml` tạo GitHub Release từ mục tương ứng trong `CHANGELOG.md` khi gắn tag.
- `rulesets/` — ruleset mẫu bảo vệ nhánh chính để import: Pull Request bắt buộc, phê duyệt của `CODEOWNERS`, chỉ Squash and merge, commit có chữ ký, cấm force push.
- `repository-templates/` — mẫu `CODEOWNERS` và `dependabot.yml` cho từng repository.
- `scripts/pre-commit.sh` và `make hooks` — pre-commit hook kiểm tra định dạng file được stage.
- Nhãn `stale` cho workflow đóng Issue và Pull Request không hoạt động.
- Dependabot cập nhật công cụ Node.js (npm) hằng tháng, gộp vào một Pull Request.
- Biểu mẫu Pull Request thêm mục kiểm tra formatter/lint và quy ước tên branch, commit, tiêu đề.
- `scripts/validate.py` kiểm tra loại commit và tiền tố branch trong `CONTRIBUTING.md` khớp các workflow, và kiểm tra bắt buộc trong ruleset trùng tên job có thật.
- Prettier (`.prettierrc.json`, `.prettierignore`) là formatter chính: tab độ rộng 4; Markdown và YAML dùng 4 dấu cách. CI chạy `prettier --check .`.
- ESLint (`eslint.config.js`) với `@eslint/js` và `eslint-config-prettier`, quy tắc chất lượng mã riêng của dự án (`eqeqeq`, `curly`, `no-var`, `prefer-const`…); không có quy tắc định dạng.
- ruff (`ruff.toml`) định dạng Python bằng tab độ rộng 4, xuống dòng LF; CI chạy `ruff format --check`.
- `package.json`, `package-lock.json`, `.nvmrc` — công cụ Node.js cố định phiên bản.
- `scripts/validate.py` chặn mọi thay đổi `.prettierrc.json`, `.editorconfig`, `ruff.toml` trái quy tắc (vd. độ rộng 2 ngoài nhóm ngôn ngữ bắt buộc), kiểm tra thụt lề, kiểu xuống dòng, mã hoá và BOM theo từng loại file, và đối chiếu danh sách đuôi file với `.editorconfig`, `.gitattributes`.
- `SECURITY.md` — chính sách bảo mật áp dụng cho mọi repository của tổ chức: thông tin cần cung cấp, cách gửi báo cáo kèm liên kết soạn email sẵn mẫu, cam kết xử lý và phiên bản được hỗ trợ.
- `CONTRIBUTING.md` — hướng dẫn đóng góp: quy trình, quy ước đặt tên branch, quy ước commit và yêu cầu đối với Pull Request.
- `CODE_OF_CONDUCT.md` — quy tắc ứng xử trong không gian cộng tác của tổ chức.
- `SUPPORT.md` — bảng chọn kênh hỗ trợ theo nhu cầu.
- `CHANGELOG.md` — nhật ký thay đổi của repository.
- `ISSUE_TEMPLATE/` — ba biểu mẫu Issue dạng form có trường bắt buộc (🐛 Báo lỗi, ✨ Đề xuất tính năng, ❓ Câu hỏi hoặc cần hỗ trợ) và `config.yml` tắt Issue trống, thêm liên kết báo cáo bảo mật và liên hệ công ty.
- `workflow-templates/` — workflow mẫu dùng chung: Node.js CI, Python CI (ruff, pytest), Go CI (gofmt, vet, test -race), CodeQL, rà soát dependency, build và đẩy Docker image lên GHCR, kiểm tra tiêu đề Pull Request, đóng Issue/Pull Request không hoạt động và kiểm tra liên kết tài liệu; mọi action ghim theo commit SHA.
- `labels.yml` và `scripts/sync-labels.sh` — bộ 16 nhãn chuẩn và công cụ đồng bộ lên các repository (mặc định chỉ xem trước).
- CI `.github/workflows/validate.yml` — kiểm tra nội dung bằng `scripts/validate.py`, định dạng, ESLint, shellcheck và actionlint.
- `.github/dependabot.yml` — tự động đề xuất cập nhật các GitHub Action ghim theo commit SHA.
- `.github/CODEOWNERS` — bắt buộc người quản trị duyệt mọi thay đổi.
- `Makefile` — `make check` chạy toàn bộ kiểm tra giống CI trên máy cục bộ.
- `.editorconfig`, `.gitattributes`, `.gitignore` — quy ước định dạng: UTF-8, xuống dòng LF, tab độ rộng 4 (kể cả Python); chỉ ngôn ngữ bắt buộc dấu cách mới dùng dấu cách (4, hoặc 2 nếu formatter chính thức cố định); chỉ file bắt buộc CRLF (batch script, Visual Studio, registry/INF, MIME/iCalendar/vCard/CSV) mới dùng CRLF.
- `profile/README.md` — badge liên hệ và phần giới thiệu tiếng Anh (**ABOUT US**).
- Quy trình phát hành: workflow `release.yml` tự tạo GitHub Release khi gắn tag, nội dung lấy từ `CHANGELOG.md` qua `scripts/release-notes.py`.
- Workflow `pr-title.yml` bắt buộc tiêu đề Pull Request theo quy ước commit.
- Workflow `links.yml` và `scripts/check-external-links.py` kiểm tra liên kết bên ngoài hằng tuần.
- `scripts/test_validate.py` — 40 test tự động cho các script kiểm tra.
- `.well-known/security.txt` (RFC 9116) với email chung của công ty.
- `scripts/validate.py` khoá email chung `toanquynhvn@gmail.com`, kiểm tra hạn `security.txt` và cấu trúc `CHANGELOG.md`.
- `make help` (mặc định khi gõ `make`), `make test`, `make links`, `make release-notes`; `make lint` báo rõ công cụ còn thiếu.

### ♻️ THAY ĐỔI

- Ruleset **Protect Main** và cài đặt repository cho phép Merge, Squash và Rebase; bỏ **Require linear history** vì chặn merge commit (ADR 0006).
- `ROADMAP.md`: repository `.github` chưa có ruleset — ưu tiên tạo **Protect Main** từ `rulesets/protect-main.json`.
- Sửa liên kết trang Settings trong `ROADMAP.md` (trả về 404 với người chưa đăng nhập, làm hỏng kiểm tra liên kết hằng tuần); `rulesets/README.md` ghi đủ quy tắc của ruleset; `org-setup.py` nhắc đúng danh sách bỏ qua theo repository.
- `rulesets/protect-main.json` thay cho hai tệp `dot-github.json` và `default-branch.json`: một ruleset **Protect Main** duy nhất cho mọi repository (`org-setup.py` chỉ giữ kiểm tra bắt buộc mà repository có job); gộp toàn bộ cài đặt của ruleset Protect Main trên web (chặn tạo/cập nhật nhánh chính, phê duyệt lại sau lần đẩy cuối, code quality, danh sách bỏ qua) với ruleset mẫu, đặt tên **Protect Main**; thêm ADR 0005, cập nhật `GOVERNANCE.md`, `rulesets/README.md`, `ROADMAP.md`.
- `ROADMAP.md` cập nhật sau khi import ruleset mẫu: các việc cấu hình `.github` đã hoàn thành, còn lại quy trình cho repository mới và việc gộp hai ruleset.
- `ROADMAP.md` đưa việc cập nhật ruleset **Protect Main** lên ưu tiên, kèm hướng dẫn từng bước trên web và lệnh kiểm tra.
- `CODEOWNERS`, mẫu `CODEOWNERS` và `MAINTAINERS.md` chuyển sang team `@TOANQUYNHLLC/maintainers`; `scripts/org-setup.py team` cấp quyền maintain thay cho admin.
- Quy ước đặt tên branch: tên viết bằng tiếng Anh, các từ nối bằng dấu gạch dưới (`feature/appointment_booking`).
- `CONTRIBUTING.md` bổ sung hướng dẫn viết báo lỗi, phong cách mã nguồn, kiểm thử, giữ branch cập nhật, đánh giá mã nguồn, hợp nhất, sửa lỗi khẩn cấp và quản lý phụ thuộc; thêm tiền tố branch `hotfix/`, `perf/`, `test/`, `ci/`, `release/`.
- Quy ước commit và kiểm tra tiêu đề Pull Request thêm các loại `style`, `build`, `ci`, `revert`; phạm vi cho phép dấu gạch dưới.
- `README.md` tập trung vào chính repository: cách GitHub áp dụng nội dung cho toàn tổ chức, cấu trúc theo nhóm, hướng dẫn phát triển cục bộ; giới thiệu công ty và thông tin liên hệ đầy đủ chuyển về `profile/README.md`.
- Mục bảo mật trong `README.md` rút gọn, nội dung chi tiết chuyển sang `SECURITY.md`.
- Mẫu nội dung email báo cáo bảo mật bổ sung trường **Thông tin liên hệ của người báo cáo**; liên kết soạn email khớp hoàn toàn với mẫu.
- Tiêu đề trong mọi tài liệu và biểu mẫu viết hoa thống nhất.
- Cảnh báo dữ liệu nhạy cảm thống nhất một cách diễn đạt trên mọi tài liệu, bổ sung **token truy cập**.
- Biểu mẫu Pull Request trỏ tới chính sách bảo mật bằng liên kết tuyệt đối, dùng được từ mọi repository.
- `profile/README.md` thống nhất tên **Phòng khám chuyên khoa Nhi DR. MOON**.

### 🗑️ LOẠI BỎ

- `.yamllint.yml` và bước yamllint trong CI — Prettier đã định dạng YAML.
- Luật thụt lề tự viết trong `scripts/validate.py` — thay bằng Prettier, ruff và kiểm tra cấu hình.
- `ISSUE_TEMPLATE.md` dạng một tệp — thay bằng thư mục biểu mẫu `ISSUE_TEMPLATE/`.

---

## [v2026.09.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2026.09.Stable) — 2026-09-26

### ✨ THÊM

- `profile/README.md` — trang giới thiệu CÔNG TY TNHH TOÀN QUỲNH trên GitHub: giới thiệu chung, câu chuyện thương hiệu, lĩnh vực hoạt động, tầm nhìn, sứ mệnh, giá trị cốt lõi, dự án Phòng khám chuyên khoa Nhi DR. MOON và thông tin liên hệ.
- `README.md` — mục đích, cấu trúc và nguyên tắc quản lý repository `.github`.
- `PULL_REQUEST_TEMPLATE.md` — biểu mẫu Pull Request mặc định cho toàn tổ chức.
- `LICENSE` — giấy phép MIT.

---

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
