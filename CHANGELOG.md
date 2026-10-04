# 📝 NHẬT KÝ THAY ĐỔI

Mọi thay đổi đáng chú ý của repository `.github` thuộc **CÔNG TY TNHH TOÀN QUỲNH** được ghi tại đây.

Định dạng theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Phiên bản đặt theo năm và tháng phát hành, ví dụ `v2026.09.Stable`. Thay đổi mới ghi vào mục **CHƯA PHÁT HÀNH**, rồi chuyển sang một phiên bản khi gắn tag.

---

## [CHƯA PHÁT HÀNH](https://github.com/TOANQUYNHLLC/.github/compare/v2026.10.Stable...HEAD)

### 🐛 SỬA

- Validator báo trường và phần tử YAML/JSON lồng nhau sai kiểu tại tệp, tiếp tục các luật còn lại; kiểm tra nguồn phiên bản công cụ cũng nhận workflow `.yaml`.
- Kiểm tra liên kết bên ngoài báo tệp sai UTF-8 và URL sai dạng mà không dừng cả lượt; Canonical chỉ mở HTTP(S). Biểu mẫu GitHub có dữ liệu nhúng sai cấu trúc và phản hồi phiên bản công cụ sai dạng được báo theo từng mục; cấu hình phiên bản cục bộ sai chặn việc gọi mạng.
- Hook commit lấy cấu hình định dạng từ Git index, dừng khi không xuất được nội dung đã stage; kiểm tra Go báo lỗi khi thiếu `gofmt` hoặc công cụ thoát lỗi không có stderr.
- Phát hành đọc và kiểm tra UTF-8 của `CHANGELOG.md` trước khi tạo branch; CLI báo lỗi đọc/ghi tệp và lệnh ngoài thay vì traceback.
- Workflow gắn nhãn (repository và mẫu) dùng `pull_request_target` để xử lý PR từ fork, chỉ đọc cấu hình nhánh đích và metadata qua API; concurrency theo số PR tránh hủy lượt chạy của PR khác.
- Workflow đuôi `.yaml` được đưa vào actionlint, phép đối chiếu kiểm tra bắt buộc của ruleset và danh sách workflow trong tài liệu như `.yml`.
- Đồng bộ ruleset và nhãn đọc hết các trang REST; phép đối chiếu ruleset tổ chức đọc hết trang GraphQL, báo dữ liệu quy tắc hoặc danh sách bỏ qua bị cắt thay vì dùng dữ liệu thiếu. Lỗi đọc trang sau chặn việc ghi dựa trên danh sách chưa đầy đủ.
- Đồng bộ nhãn hỗ trợ YAML anchor/alias như validator; YAML sai hoặc cấu trúc nhãn không hợp lệ dừng trước khi gọi GitHub và được CLI báo lỗi thay vì traceback.
- Validator kiểm tra action, mã nhúng và biểu thức trong lệnh theo giá trị YAML: khóa có dấu nháy, dạng `{run: …}` và anchor/alias đều được kiểm tra; chú thích không bị coi là nội dung lệnh. Cấu trúc workflow, job, bước và kiểu gốc của cấu hình JSON sai được báo rõ thay vì gây traceback.
- YAML hỗ trợ anchor/alias, chỉ đọc dữ liệu thông thường và báo alias vòng lặp ở đúng tệp; lỗi một tệp không làm cả lô tệp hợp lệ bị báo lỗi.
- Khi chọn tệp test, chỉ nạp các tệp đó; lỗi import hoặc cú pháp chỉ chạy lại đúng phạm vi đã chọn để báo lỗi đầy đủ.
- Phép dò tài nguyên GitHub chỉ coi HTTP 404 là chưa có; lỗi quyền, giới hạn API hoặc mạng chặn việc đồng bộ team, tệp và ruleset dựa trên dữ liệu chưa đọc được. Tính năng bảo mật không đọc được trạng thái được cảnh báo và bỏ qua.
- Tệp dùng chung được thêm bằng một commit do GitHub ký qua `createCommitOnBranch`, kiểm tra HEAD trước khi ghi và không mở Pull Request khi commit thất bại.
- Phát hành kiểm tra Pull Request đang mở khi branch đã tồn tại, báo lỗi khi chưa có; chỉ báo đã xóa branch sau lỗi commit nếu GitHub xác nhận xóa thành công.
- Kiểm tra nội dung và liên kết Markdown báo tệp không đọc được hoặc sai UTF-8, tiếp tục các kiểm tra còn lại thay vì dừng bằng traceback.
- Công cụ kiểm tra báo lỗi rõ khi npm không cài được thư viện hoặc tên tệp test được chọn không tồn tại; không chạy một phần danh sách test rồi báo đạt.
- Anchor Markdown xử lý đúng tiêu đề trùng với hậu tố tự sinh của GitHub; kết quả phân tích tệp đích được dùng chung trong một lượt kiểm tra và làm mới ở lượt sau.
- Validator báo lỗi JSON của manifest, ruleset và ngày hết hạn thiếu múi giờ; quy tắc không viết mã nhúng hoặc lệnh nhiều dòng trong workflow cũng áp dụng cho bước bắt đầu bằng `- run:`.
- Liên kết huy hiệu workflow mở đúng tệp trên `main`; README nêu rõ kết quả huy hiệu khi Actions tắt, phạm vi kiểm tra tại máy và cách chọn tệp test.

### ⚡ TỐI ƯU

- Kiểm tra liên kết đọc mỗi tệp một lần trong lượt chạy; GET so bản `security.txt` trên website cũng kiểm tra URL Canonical, tránh request HEAD trùng và chạy song song với các liên kết khác.
- Đối chiếu job và tài liệu dùng lại danh sách workflow từ các tệp đã kiểm kê trong lượt kiểm tra, tránh quét lại thư mục ở từng phép đối chiếu.
- Tìm test được chọn không nạp các module test còn lại; cấu hình JSON được đọc một lần trong lượt đối chiếu, lượt mới đọc lại tệp.
- Lệnh đồng bộ tệp dùng chung đọc một cây Git tại commit cố định thay vì dò riêng từng tệp; phản hồi bị cắt thì dò từng đường dẫn, lần chạy sau đọc lại GitHub.

### ✨ THÊM

- Bản ghi quyết định kiến trúc trong `docs/adr/` (mỗi ADR gồm bối cảnh, quyết định, phương án đã cân nhắc, hệ quả): định dạng, quy ước branch và commit, ruleset, commit có chữ ký, nguồn phiên bản công cụ, kiểm tra là script, quy tắc đặt tên, git hook, phát hành hằng tháng, tài liệu khớp code.
- Kiểm tra tại máy giống GitHub Actions: `make check` chạy song song các nhóm `content`, `format`, `lint`, `conventions`, `audit` (khai báo trong `scripts/check.py`); test chia cho mọi lõi CPU (`scripts/run-tests.py`).
- Git hook (`make hooks`): `pre-commit` kiểm tra Prettier, `ruff format`, `ruff check` trên phần đã stage; `pre-push` chạy `make check` trên đúng nội dung được đẩy; `post-merge`, `post-rewrite` chạy song song `make org-preview`, `make links`, `make versions` sau khi kéo code.
- `validate.py` kiểm tra: định dạng, mã hóa, xuống dòng từng loại tệp; liên kết nội bộ (cả mục `#…`, liên kết mã hóa phần trăm); tiêu đề viết hoa; chữ trên huy hiệu tiếng Anh, hoa đầu mỗi từ; biểu mẫu Issue, Discussion; nhãn (đủ nhãn mặc định của GitHub); workflow (ghim SHA, quyền tối thiểu, không viết `${{ … }}` trong `run:`, `concurrency`, `timeout-minutes`, không viết kiểm tra trong YAML); ruleset; bảng ADR và đủ mục của từng ADR; tên tự đặt camelCase (cú pháp của ngôn ngữ giữ nguyên); tài liệu khớp code (lệnh `make`, đường dẫn, hàm được nhắc tới; `README.md` liệt kê đủ lệnh, script, workflow); người quản trị khớp `scripts/orgsetup/teams.py` và danh sách bỏ qua của ruleset; `devEngines` của `package.json` khớp `.nvmrc`; `security.txt` (báo trước 30 ngày khi sắp hết hạn); liên kết trong `CHANGELOG.md` là URL tuyệt đối.
- `make links`: liên kết bên ngoài còn hoạt động (thử IPv4 trước, thử lại khi máy chủ lỗi tạm thời; máy chủ ngắt kết nối hay trả phản hồi sai dạng thì báo liên kết đó, không dừng cả lượt) và bản `security.txt` trên website khớp repository. `make forms`: GitHub chấp nhận biểu mẫu trên một branch. `make versions`: công cụ trong `mise.toml` có bản mới.
- `make org-preview` (`org-setup.py preview`): xem trước cùng lúc việc áp dụng tệp dùng chung, cài đặt, ruleset, team, nhãn lên mọi repository và cài đặt tổ chức; các lệnh trong `scripts/orgsetup/` đọc GitHub song song, ghi tuần tự. Lệnh `files` thêm tệp phiên bản cho workflow mẫu: `.nvmrc` (Node.js CI), `.python-version` (Python CI).
- `make release-pr`: chuẩn bị và mở Pull Request phát hành tại máy khi GitHub Actions tắt; GitHub từ chối commit thì thử xóa branch phát hành vừa tạo và báo kết quả để lần sau làm lại.
- Huy hiệu đầu `README.md`: kết quả `validate.yml` và CodeQL trên `main`, phiên bản phát hành, commit gần nhất, Conventional Commits, code style (Prettier, Ruff), giấy phép.
- Workflow mẫu `docs-check.yml`, `go-ci.yml` gọi `check-markdown-links.py`, `check-gofmt.py` của tổ chức (tệp Go sai cú pháp thì báo đúng tệp, dòng, cột; đọc đúng tên tệp tiếng Việt; anchor tiêu đề tính đúng như GitHub, kể cả tiêu đề có emoji hoặc liên kết; bỏ qua `vendor/`).

---

## [v2026.10.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2026.10.Stable) — 2026-10-03

Nội dung phát hành xem tại [GitHub Release v2026.10.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2026.10.Stable).

---

## [v2026.09.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2026.09.Stable) — 2026-09-26

Nội dung phát hành xem tại [GitHub Release v2026.09.Stable](https://github.com/TOANQUYNHLLC/.github/releases/tag/v2026.09.Stable).

---

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
