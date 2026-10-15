# 🛠️ THIẾT LẬP VÀ KIỂM TRA TẠI MÁY

Hướng dẫn dành cho người đóng góp thiết lập môi trường, sửa tài nguyên và kiểm chứng thay đổi trong repository `.github`. Clone dự án theo [README.md](../README.md), sau đó thực hiện các bước dưới đây. Quy ước branch, commit và Pull Request nằm trong [CONTRIBUTING.md](../CONTRIBUTING.md).

## 📦 MÔI TRƯỜNG

Phiên bản công cụ lấy từ [mise.toml](../mise.toml), [.nvmrc](../.nvmrc) và [package.json](../package.json). Kích hoạt mise trong shell theo [hướng dẫn mise](https://mise.jdx.dev/getting-started.html), rồi chạy:

```bash
mise trust
mise install
make hooks
```

Chuẩn bị Git ≥ 2.30, GNU Make ≥ 3.81, Bash ≥ 3.2 và Ruby trước khi chạy các lệnh của dự án. Ruby cùng thư viện chuẩn Psych dùng để đọc YAML cho validator. Các công cụ này cần có sẵn trong môi trường; `mise install` cài các công cụ được khai báo trong `mise.toml` và Node.js từ `.nvmrc`.

Scripts tương thích Python ≥ 3.11; phiên bản dùng để phát triển lấy từ `mise.toml`. Node.js phải đúng `.nvmrc`; `devEngines` làm npm dừng với `EBADDEVENGINES` khi phiên bản khác. `make tools` báo công cụ còn thiếu và cài thư viện Node.js khi thiếu hoặc sai phiên bản. Có thể chọn Python bằng `make check PYTHON=python3.14`; bộ điều phối dùng cùng trình thông dịch cho các scripts Python.

Dev Container và Codespaces trong [.devcontainer/](../.devcontainer/) ghim image Python theo mise, cài công cụ và hooks tự động. Codespaces cần tối thiểu 4 lõi CPU. Cache công cụ nằm trên volume để dùng lại khi dựng container. VS Code định dạng khi lưu bằng Prettier và Ruff; tests chạy được từ khung Testing.

Chạy `make check` sau khi thiết lập để xác nhận môi trường. Trước khi sửa, tạo branch theo quy ước, ví dụ `git switch -c docs/update_readme`. Dùng `make quick` trong lúc làm việc và chạy `make check` trước khi gửi thay đổi.

Đăng nhập GitHub CLI với quyền phù hợp khi mở Pull Request phát hành hoặc tạo GitHub Release. Validator, tests, formatter và bộ sinh ruleset chạy tại máy; các kiểm tra trực tuyến cần mạng theo phạm vi mô tả bên dưới.

## 📐 ĐỊNH DẠNG

Tệp văn bản dùng UTF-8, LF, tab độ rộng 4 và ký tự xuống dòng cuối tệp. Markdown, YAML và các ngoại lệ dùng dấu cách theo [.editorconfig](../.editorconfig). Các định dạng bắt buộc CRLF và mã hóa riêng được khai báo trong [.gitattributes](../.gitattributes).

Prettier định dạng JSON, YAML và Markdown; Ruff định dạng và lint Python. Cấu hình nằm trong [.prettierrc.json](../.prettierrc.json), [ruff.toml](../ruff.toml) và [pyproject.toml](../pyproject.toml). Dùng `make format` để định dạng toàn bộ; `make format-check` chỉ kiểm tra.

## 🪝 GIT HOOK

`make hooks` cài hook và mẫu commit. Hook dùng chung Git common directory cho các worktree; script cảnh báo nếu `core.hooksPath` làm Git bỏ qua hook. Trên Windows không tạo được symlink, script cài tệp gọi thay thế.

| Hook                                    | Nội dung                                                                                                                        |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `pre-commit`                            | Xuất phần đã stage và cấu hình trong index ra thư mục tạm; chạy Prettier, Ruff format và Ruff lint                              |
| `pre-push`                              | Chạy `make check` trên nội dung branch được đẩy; yêu cầu commit hết hoặc `git stash -u`; chỉ đẩy tag hoặc xóa branch thì bỏ qua |
| `post-merge`, `post-rewrite` cho rebase | Cài lại hook, chạy song song kiểm tra links và versions, không cần tài khoản quản trị tổ chức; chỉ thông báo                    |

Hook trước commit ghim phiên bản công cụ đọc từ nguồn để shim mise dùng đúng bản trong thư mục tạm. Tệp Python trong index được xuất thêm để Ruff nhận đúng gói khi sắp xếp imports; chỉ tệp đã stage được kiểm tra. Đường dẫn được đọc bằng NUL và truyền sau `--` để giữ nguyên ký tự đặc biệt.

Khi chạy lệnh kiểm tra, hook bỏ biến môi trường cục bộ do Git công bố để tests tìm đúng repository tạm theo thư mục làm việc. Các biến môi trường khác được giữ nguyên.

## ✅ KIỂM TRA TẠI MÁY

Chạy `make check` trước khi đẩy và trước khi bàn giao. [scripts/check.py](../scripts/check.py) điều phối các nhóm tại máy dưới đây; GitHub Actions gọi nhóm hoặc script dùng chung theo phạm vi của từng workflow:

| Nhóm          | Phạm vi                                    |
| ------------- | ------------------------------------------ |
| `content`     | Validator và tests                         |
| `format`      | Prettier, Ruff format, Ruff lint           |
| `lint`        | ShellCheck và actionlint                   |
| `conventions` | Tên branch, tiêu đề commit                 |
| `audit`       | Dependency npm có lỗ hổng mức high trở lên |

Công cụ được kiểm tra và thư viện Node.js được chuẩn bị trước khi chạy các nhóm. Các nhóm và lệnh độc lập chạy đồng thời; đầu ra và danh sách lỗi giữ thứ tự khai báo. CodeQL chạy riêng trên GitHub Actions khi được bật. Nhóm `audit` dùng npm audit cho cây phụ thuộc tại máy; workflow Dependency Review xét các phụ thuộc được PR thêm hoặc thay đổi, nên hai kết quả có phạm vi khác nhau.

Chạy thành công tại máy không tự gửi status check lên GitHub. Nếu ruleset yêu cầu job của Actions, PR vẫn cần kết quả từ các job đó; tham khảo [hướng dẫn áp dụng ruleset](../rulesets/README.md#-kiểm-tra-bắt-buộc).

`make quick` chỉ thu hẹp tests khi toàn bộ thay đổi so với `origin/main`, index, cây làm việc và tệp mới đều là các tệp test còn tồn tại. Sửa nguồn, cấu hình, tài liệu, xóa tệp hoặc lỗi đọc Git khiến lệnh chạy đầy đủ. Validator và các nhóm khác luôn chạy đầy đủ; trước push vẫn dùng `make check`.

Chạy riêng tệp test bằng tên có hoặc không có `.py`:

```sh
python3 scripts/run-tests.py test_check test_check_markdown_links.py
```

Không truyền tên thì chạy toàn bộ. Tên sai, tệp không có test, lỗi import hoặc cú pháp làm lệnh thất bại. Tham số Makefile như `BRANCH`, `TAG`, `REF` được truyền bằng biến môi trường để giữ nguyên ký tự đặc biệt.

## ⚡ CACHE VÀ THỰC THI

Prettier dùng cache nội dung trong `node_modules/.cache/prettier/`; cần xóa cache khi thêm hoặc nâng plugin. Bộ chạy tests lưu thời gian trong `.cache/local-checks/test-times.json` để cân bằng nhóm, không lưu kết quả đạt/thất bại và không bỏ tests. Lượt chạy một phần giữ thời gian của tệp khác; lượt đầy đủ bỏ mục của test không còn.

Cache thiếu, hỏng hoặc không ghi được vẫn chạy tests. Số tiến trình căn cứ CPU khả dụng, affinity và quota cgroup, theo giới hạn của script. Validator chỉ giữ các nút cú pháp cần xét tên và thư viện; quy tắc vẫn áp dụng cho hàm/lớp lồng nhau, tham số, bí danh, biến bắt lỗi, `:=` và `match/case`.

## 🌐 KIỂM TRA TRỰC TUYẾN

| Lệnh               | Phạm vi và giới hạn                                                                                                     |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `make links`       | Kiểm tra HTTP(S), đối chiếu `security.txt` trên website; bỏ qua `img.shields.io`, không xác minh anchor của trang ngoài |
| `make forms REF=…` | Xác minh Issue theo ref; Discussion chỉ xác minh trên nhánh mặc định, ref khác trả mã lỗi                               |
| `make versions`    | Kiểm tra bản phát hành mới của công cụ trong mise và action chỉ có ở workflow mẫu; không theo dõi Python, Node.js       |
| `make audit`       | Cần registry npm; lỗi kết nối được nhận diện có thể được cảnh báo và bỏ qua, phải chạy lại để xác minh dependency       |

`make links` dùng chung request cho URL chỉ khác fragment; đường dẫn và query khác được kiểm tra riêng. Kết quả không được dùng lại giữa các lượt. Kiểm tra phiên bản ưu tiên `GH_TOKEN`, `GITHUB_TOKEN`, rồi token GitHub CLI; đọc thông tin đăng nhập mới mỗi lượt.

Validator kiểm tra cấu trúc biểu mẫu tại máy. GitHub có thể từ chối biểu mẫu đã qua validator; chạy `make forms` để xác minh. Đổi tên tệp Issue mà giữ `name` có thể báo `Name must be unique` trên ref khác do GitHub đối chiếu với nhánh mặc định; xác minh lại sau hợp nhất. Discussion cần xác minh sau hợp nhất; biểu mẫu lỗ hổng riêng tư cần mở trang báo cáo bằng tài khoản phù hợp. Không gửi báo cáo thử.

Lỗi dữ liệu trang GitHub, lỗi HTTP registry và báo cáo lỗ hổng có mã lỗi làm kiểm tra thất bại. Lỗi cài dependency làm kiểm tra dừng.

## 🏃 WORKFLOW CHỜ RUNNER

Khi job ở trạng thái `queued`, chưa có tên runner và chưa chạy bước Checkout, người quản trị kiểm tra **Organization Settings → Actions → General → Standard hosted runners**. Với workflow dùng runner chuẩn như `ubuntu-latest`, bỏ tích **Disable for all repositories** rồi nhấn **Save**. Tích ô này tắt runner chuẩn cho mọi repository của tổ chức, kể cả khi Actions permissions vẫn được bật; xem [chính sách runner của GitHub](https://docs.github.com/en/organizations/managing-organization-settings/disabling-or-limiting-github-actions-for-your-organization#disabling-standard-hosted-runners).

Sau khi lưu, đối chiếu job được cấp runner và bắt đầu chạy các bước. Nếu job vẫn chờ, kiểm tra số job đang chạy, giới hạn concurrency, thông báo tài khoản trên giao diện và [GitHub Status](https://www.githubstatus.com/). Trạng thái `queued` chưa cung cấp kết quả kiểm tra mã nguồn.

## 🔗 PHẠM VI KIỂM TRA MARKDOWN

Kiểm tra nội bộ hỗ trợ liên kết nội tuyến, đường dẫn bắt đầu bằng `/` từ gốc repository và anchor tiêu đề ATX, kể cả tiêu đề trùng. Nội dung mã có hàng rào và mã nội tuyến được bỏ qua; tệp đích đọc một lần trong lượt rồi đọc lại ở lượt sau.

Script xử lý hàng rào thụt 0–3 dấu cách theo GFM; không phân tích đầy đủ khối mã thụt lề, khối lồng trong danh sách/blockquote, tiêu đề Setext/HTML hoặc liên kết tham chiếu. Các giới hạn này cần được xét khi đánh giá liên kết thủ công. Scripts lấy đường dẫn từ Git bằng danh sách NUL để không làm biến đổi tên tệp.

## 🔄 TIỆN ÍCH GIT

`make sync BRANCH=…` gọi [shell/sync.sh](../shell/sync.sh) rồi [shell/prune-branches.sh](../shell/prune-branches.sh). Bước đầu lỗi thì không dọn branch. Lệnh yêu cầu cây làm việc sạch, không đang dở thao tác Git; kéo bằng fast-forward và dừng khi branch lệch với origin.

Bước dọn dùng [scripts/check-branch-merged.py](../scripts/check-branch-merged.py) so nội dung đã hợp nhất vào `origin/main`, hỗ trợ Merge và Squash, kể cả branch được squash thành nhiều nhóm qua các PR khác nhau. Với Squash, script đối chiếu các nhóm commit liên tiếp từ điểm tách với lịch sử nhánh chính; bản vá giữ nguyên khoảng trắng, dữ liệu nhị phân, quyền tệp và thay đổi submodule. Bản vá phải tái tạo đúng cây của commit trên nhánh chính trong index tạm riêng. Nếu nhánh chính đã sửa nội dung nền, script còn đối chiếu kết quả hợp nhất ba phía để tránh áp nhầm vào đoạn lặp còn lại. Index và tệp đang sửa của người dùng không bị thay đổi; không tạo commit tạm. Nhóm không đổi nội dung cũng được chấp nhận. Không xác nhận được toàn bộ thay đổi hoặc có nhiều điểm tách thì giữ branch.

Script dùng ref đầy đủ để không nhầm tag trùng tên, đọc lại SHA trước khi xóa và giữ branch đã thay đổi trong lúc đối chiếu. Chỉ xóa branch local có branch theo dõi trên origin đã bị xóa; lỗi đọc Git được báo riêng và làm bước dọn trả mã lỗi. Giữ `main`, branch hiện tại, branch còn thay đổi và branch đang mở ở worktree khác. Thiếu `origin/main` làm lệnh dừng.

`make cleanup` dùng `git clean -fdx`, xóa vĩnh viễn mọi tệp Git không quản lý, kể cả `.env`, cache và tệp mới chưa add. Xem trước bằng `git clean -ndx`.
