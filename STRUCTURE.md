# CẤU TRÚC REPOSITORY `.github` CỦA TỔ CHỨC

Repository `TOANQUYNHLLC/.github` cung cấp một số tài liệu và mẫu mặc định cho các repository thuộc tổ chức. GitHub không sao chép các file này sang repository khác.

## 1. PHÂN BIỆT REPOSITORY VÀ THƯ MỤC `.github`

- `.github` bên ngoài là tên repository của tổ chức.
- `.github` bên trong là thư mục cấu hình GitHub, tính từ gốc repository.
- Vì vậy, đường dẫn local `.../.github/.github/ISSUE_TEMPLATE/` là hợp lệ khi thư mục ngoài cùng là gốc repository tên `.github`.
- Với dự án thông thường `website`, đường dẫn đúng là `website/.github/ISSUE_TEMPLATE/`, không phải `website/.github/.github/ISSUE_TEMPLATE/`.

## 2. CÂY THƯ MỤC

Phần cấu trúc liên quan đến tài liệu cộng đồng và cấu hình GitHub trong thư mục làm việc. Tệp chỉ có ở máy cần được hợp nhất vào nhánh mặc định trên GitHub trước khi có thể áp dụng cho repository khác.

```text
.github/                               ← Gốc repository TOANQUYNHLLC/.github
├── README.md                          ← Giới thiệu repository.
├── STRUCTURE.md                       ← Tài liệu cấu trúc.
├── CONTRIBUTING.md                    ← Hướng dẫn đóng góp mặc định
├── CODE_OF_CONDUCT.md                 ← Quy tắc ứng xử mặc định
├── SECURITY.md                        ← Chính sách bảo mật mặc định
├── SUPPORT.md                         ← Hướng dẫn hỗ trợ mặc định
├── ACCESSIBILITY.md                   ← Chính sách khả năng tiếp cận
├── specs/
│   └── JobsGuideLine.md                ← Quy trình rà soát dự án
├── profile/
│   └── README.md                      ← Giới thiệu trên trang tổ chức
├── .github/                           ← Thư mục cấu hình GitHub
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml             ← Form báo lỗi
│   │   ├── feature_request.yml        ← Form đề xuất tính năng
│   │   ├── question.yml               ← Form câu hỏi
│   │   └── config.yml                 ← Cấu hình bộ mẫu issue
│   ├── PULL_REQUEST_TEMPLATE.md       ← Mẫu PR mặc định
│   ├── PULL_REQUEST_TEMPLATE/
│   │   ├── feature.md                 ← Mẫu PR tính năng
│   │   ├── bugfix.md                  ← Mẫu PR sửa lỗi
│   │   └── release.md                 ← Mẫu PR chuẩn bị phát hành
│   ├── DISCUSSION_TEMPLATE/
│   │   ├── general.yml                ← Thảo luận chung
│   │   ├── ideas.yml                  ← Ý tưởng
│   │   └── q-a.yml                    ← Hỏi đáp
│   ├── VULNERABILITY_REPORT.yml       ← Form báo cáo lỗ hổng riêng tư
│   ├── CODEOWNERS                     ← Người phụ trách code của repo
│   ├── dependabot.yml                 ← Dependabot của repo
│   ├── release.yml                    ← Cấu hình nội dung Release tự sinh
│   ├── labeler.yml                    ← Cấu hình gắn nhãn PR
│   ├── copilot-instructions.md        ← Hướng dẫn Copilot
│   ├── instructions/                  ← Hướng dẫn theo đường dẫn
│   ├── agents/                        ← Agent Copilot
│   └── workflows/                     ← Workflow của repo
├── workflow-templates/                ← Workflow mẫu và metadata ở gốc repo
└── repository-templates/              ← Tệp để chép vào từng dự án
```

## 3. CÁC FILE ĐƯỢC DÙNG LÀM MẶC ĐỊNH

| File hoặc đường dẫn                             | Vị trí trong repository `.github` | Tác dụng                                                      |
| ----------------------------------------------- | --------------------------------- | ------------------------------------------------------------- |
| `CONTRIBUTING.md`                               | Gốc, `.github/` hoặc `docs/`      | Hướng dẫn đóng góp                                            |
| `CODE_OF_CONDUCT.md`                            | Gốc, `.github/` hoặc `docs/`      | Quy tắc ứng xử                                                |
| `SECURITY.md`                                   | Gốc, `.github/` hoặc `docs/`      | Hướng dẫn báo cáo bảo mật                                     |
| `SUPPORT.md`                                    | Gốc, `.github/` hoặc `docs/`      | Kênh hỗ trợ                                                   |
| `ACCESSIBILITY.md`                              | Gốc, `.github/` hoặc `docs/`      | Mục tiêu, hạn chế và cách báo cáo vấn đề về khả năng tiếp cận |
| `PULL_REQUEST_TEMPLATE.md`                      | Gốc, `.github/` hoặc `docs/`      | Một mẫu Pull Request                                          |
| `PULL_REQUEST_TEMPLATE/`                        | Gốc, `.github/` hoặc `docs/`      | Nhiều mẫu Pull Request                                        |
| `.github/ISSUE_TEMPLATE/*.md`                   | Đúng đường dẫn.                   | Mẫu issue Markdown                                            |
| `.github/ISSUE_TEMPLATE/*.yml`                  | Đúng đường dẫn.                   | Form issue có trường nhập                                     |
| `.github/ISSUE_TEMPLATE/config.yml`             | Đúng đường dẫn.                   | Cấu hình bộ mẫu issue và liên kết hỗ trợ                      |
| `.github/DISCUSSION_TEMPLATE/*.yml`             | Đúng đường dẫn.                   | Form danh mục Discussions                                     |
| `.github/FUNDING.yml`                           | Đúng đường dẫn.                   | Nút tài trợ                                                   |
| `.github/VULNERABILITY_REPORT.yml` hoặc `.yaml` | Đúng đường dẫn.                   | Form báo cáo lỗ hổng riêng tư                                 |

Không cần đặt cùng một tài liệu ở nhiều vị trí. Các tính năng Discussions, tài trợ và báo cáo lỗ hổng còn phụ thuộc vào việc bật tính năng và điều kiện hỗ trợ của GitHub.

### NHIỀU MẪU PULL REQUEST

Repository giữ mẫu chung và các mẫu riêng theo loại công việc. Các mẫu riêng giữ đầy đủ bố cục và checklist của mẫu chung, bổ sung nội dung phù hợp với từng loại:

```text
.github/
├── PULL_REQUEST_TEMPLATE.md           ← Mẫu chung khi không chọn mẫu riêng
└── PULL_REQUEST_TEMPLATE/
    ├── feature.md
    ├── bugfix.md
    └── release.md
```

Nhiều mẫu PR không tự tạo bộ chọn giống mẫu issue. Trên URL so sánh nhánh của repository đích, thêm `?quick_pull=1&template=feature.md`; đổi tên thành `bugfix.md` hoặc `release.md` để chọn mẫu tương ứng. Nếu URL đã có tham số, thêm `&template=feature.md`. Các mẫu cần được hợp nhất vào nhánh mặc định trước khi GitHub sử dụng. Xem [hướng dẫn chọn mẫu](CONTRIBUTING.md#-chọn-mẫu-pull-request).

## 4. CÁC FILE KHÔNG TỰ KẾ THỪA

| File/thư mục                               | Vai trò và phạm vi                                           |
| ------------------------------------------ | ------------------------------------------------------------ |
| `README.md`                                | Giới thiệu repo `.github`; không thành README của repo khác  |
| `STRUCTURE.md`                             | Tài liệu của repo; không tự xuất hiện ở repo khác            |
| `specs/JobsGuideLine.md`                   | Quy trình rà soát của repo; không tự sao chép sang repo khác |
| `profile/README.md`                        | Giới thiệu tổ chức; không thành README dự án                 |
| `LICENSE`                                  | Không tự cấp phép cho các repo khác                          |
| `.github/CODEOWNERS`                       | Phân công người phụ trách trong repo.                        |
| `.github/dependabot.yml`                   | Cấu hình cập nhật dependency trong repo.                     |
| `.github/workflows/`                       | Workflow trong repo; không tự chạy trong repo khác           |
| `workflow-templates/`                      | Cung cấp mẫu để tạo workflow; không tự cài vào repo mới      |
| `.gitignore`, `.gitattributes`             | Cấu hình Git của repo.                                       |
| `.editorconfig`, cấu hình formatter/linter | Cấu hình công cụ của repo.                                   |
| `AGENTS.md`                                | Hướng dẫn agent trong repo.                                  |
| `package.json` và cấu hình dự án khác      | Không tự sao chép sang dự án mới                             |

Các cấu hình bảo vệ nhánh, rulesets, quyền truy cập, secrets và labels cũng không được sao chép nhờ các file mặc định. Một số có cơ chế quản lý ở cấp tổ chức riêng.

## 5. QUY TẮC ÁP DỤNG

1. Repository `.github` cung cấp community health files mặc định phải public.
2. Mặc định áp dụng cho cả repository mới và đã tồn tại, public hoặc private thuộc cùng tài khoản/tổ chức.
3. Khi repository đích có file tương ứng riêng, GitHub dùng file riêng.
4. Với file hỗ trợ nhiều vị trí, thứ tự ưu tiên là `.github/`, gốc repository, rồi `docs/`. GitHub cũng áp dụng thứ tự này khi tìm file trong repository mặc định.
5. Nếu repository đích có mẫu issue hoặc cấu hình issue riêng hợp lệ, toàn bộ bộ mẫu `.github/ISSUE_TEMPLATE/` mặc định sẽ không được dùng; GitHub không trộn hai bộ.
6. Labels dùng trong mẫu issue phải được tạo trong repo `.github` và từng repository sử dụng mẫu; labels không tự kế thừa.
7. File mặc định không xuất hiện trong cây thư mục, lịch sử Git, bản clone, gói hoặc bản tải xuống của repository đích.
8. Thay đổi tài liệu mặc định được quản lý tập trung trong repo `.github`; các repo có tài liệu riêng tiếp tục dùng tài liệu riêng của mình.

## 6. KIỂM CHỨNG VIỆC ÁP DỤNG

Kiểm tra tại máy xác nhận cú pháp và cấu trúc tệp. Kiểm chứng việc GitHub áp dụng mặc định cần đọc trạng thái trên GitHub và dùng một repository đích thuộc cùng tổ chức. Thực hiện khi có repository đích và các tệp nguồn đã được hợp nhất vào nhánh mặc định.

| Nội dung                      | Cách kiểm chứng                                                                                                                         | Điều kiện cần                                                                                                                   |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Tài liệu cộng đồng mặc định   | Đối chiếu cây tệp của nhánh mặc định ở repo nguồn và repo đích; mở các liên kết cộng đồng trên repo đích để xác nhận tài liệu được dùng | Repo nguồn `.github` public; repo đích không có tài liệu riêng cùng loại                                                        |
| Mẫu Issue và `config.yml`     | Mở trang tạo Issue của repo đích, kiểm tra bộ chọn biểu mẫu, trường nhập và liên kết liên hệ                                            | Issues bật; repo đích không có mẫu hoặc cấu hình Issue riêng hợp lệ                                                             |
| Labels của mẫu Issue          | Đọc danh sách labels của từng repo qua GitHub CLI/API hoặc trang Issues → Labels; đối chiếu với trường `labels` trong các mẫu           | `bug`, `enhancement`, `question`, `needs triage` phải có ở repo nguồn và từng repo dùng mẫu; `labels.yml` chỉ là nguồn cấu hình |
| Mẫu Discussion                | Đối chiếu tên tệp với slug danh mục và mở trang tạo Discussion theo từng danh mục ở repo đích                                           | Discussions bật; danh mục phù hợp tồn tại                                                                                       |
| Form báo cáo lỗ hổng riêng tư | Đọc cài đặt Private vulnerability reporting; mở trang báo cáo bằng tài khoản GitHub và xác nhận các trường tùy chỉnh xuất hiện          | Form trên nhánh mặc định; repo đích bật báo cáo riêng tư; có tài khoản truy cập giao diện                                       |
| Workflow mẫu                  | Đối chiếu từng `.yml` với `.properties.json`, icon và bộ lọc `filePatterns`; mở Actions → New workflow ở repo đích rồi xem nội dung mẫu | Repo đích cho phép Actions; dự án phù hợp bộ lọc của mẫu; tài khoản có quyền tạo workflow                                       |

Không coi một trang chuyển hướng đến đăng nhập là bằng chứng form tùy chỉnh đã hoạt động. Nếu GitHub không phân tích được form báo cáo lỗ hổng, giao diện có thể dùng form mặc định; cần đối chiếu các trường thực tế với tệp cấu hình. Chỉ mở trang xem, không gửi báo cáo thử để kiểm tra giao diện.

Repository này cung cấp workflow mẫu và script dùng chung; các workflow hiện có không khai báo `workflow_call`. Nếu triển khai reusable workflow, tệp cần khai báo `on.workflow_call` trong `.github/workflows/` và repo đích cần gọi bằng `jobs.<job_id>.uses`. Việc checkout `TOANQUYNHLLC/.github` để chạy script là cách dùng chung script, không phải lời gọi reusable workflow.

Kiểm chứng trên repo đích không đòi hỏi tự tạo repo, bật tính năng hoặc đẩy tệp chỉ để lấy kết quả kiểm tra. Những thao tác triển khai đó cần thuộc phạm vi công việc được giao.

## 7. GIẤY PHÉP

`LICENSE` trong repository tổ chức `.github` không tự áp dụng cho mã nguồn của các repository khác. Mỗi dự án phải xác định giấy phép riêng và đưa thông báo cần thiết vào dự án nếu cấp phép.

Nếu không muốn cấp phép MIT cho repo `.github`, không thêm MIT chỉ để hoàn thiện cây thư mục. Tuy nhiên, việc bỏ giấy phép không thu hồi quyền đã cấp đối với các bản trước đây được phát hành theo MIT. Giữ các thông báo bản quyền và giấy phép bắt buộc của nội dung bên thứ ba.

## 8. NỘI DUNG NÊN ĐẶT TRONG TEMPLATE REPOSITORY

Dùng một repository được bật **Template repository** trên GitHub khi muốn dự án mới nhận bản sao của các tệp và cấu trúc thư mục. GitHub giữ đường dẫn trong template; thư mục `repository-templates/` của repository này chỉ chứa nguồn để chọn và chép sang vị trí phù hợp. Xem [hướng dẫn tạo template repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository).

### CHỌN TỆP VÀ ĐẶT ĐÚNG VỊ TRÍ

| Nguồn hiện có                                                                                                                                                                    | Đường dẫn trong template dự án                                      | Điều kiện và nội dung cần chỉnh                                                                                                                            |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`.gitignore`](.gitignore), [`.gitattributes`](.gitattributes), [`.editorconfig`](.editorconfig)                                                                                 | Giữ tên ở gốc dự án                                                 | Điều chỉnh loại tệp sinh ra, quy tắc Git và định dạng theo công nghệ; giữ các lockfile dự án cần để cài dependency tái lập được                            |
| [`.prettierrc.json`](.prettierrc.json), [`ruff.toml`](ruff.toml), [`rustfmt.toml`](repository-templates/rustfmt.toml), [`.clang-format`](repository-templates/.clang-format)     | Giữ tên ở gốc dự án                                                 | Chỉ chọn formatter/linter được dự án sử dụng và khai báo công cụ cần thiết trong cấu hình của dự án                                                        |
| [`.nvmrc`](.nvmrc), phiên bản Python trong [`mise.toml`](mise.toml)                                                                                                              | `.nvmrc` cho Node.js; `.python-version` cho workflow Python hiện có | Dùng phiên bản phù hợp dự án; `.python-version` được sinh từ nguồn phiên bản Python, không phải tệp nguồn có sẵn để chép                                   |
| [`repository-templates/CODEOWNERS`](repository-templates/CODEOWNERS)                                                                                                             | `.github/CODEOWNERS`                                                | Chỉnh phạm vi đường dẫn và team/người phụ trách; chủ sở hữu mã phải có quyền ghi tại repo đích; yêu cầu phê duyệt cần ruleset hoặc branch protection riêng |
| [`repository-templates/dependabot.yml`](repository-templates/dependabot.yml)                                                                                                     | `.github/dependabot.yml`                                            | Giữ các ecosystem thực tế được dùng; chỉnh thư mục manifest, lịch cập nhật và labels theo dự án                                                            |
| [`repository-templates/labeler.yml`](repository-templates/labeler.yml) và [`workflow-templates/labeler.yml`](workflow-templates/labeler.yml)                                     | `.github/labeler.yml` và `.github/workflows/labeler.yml`            | Dùng cả cấu hình và workflow khi cần tự gắn nhãn PR; chỉnh glob theo cây mã nguồn và tạo labels ở repo đích                                                |
| [`repository-templates/release.yml`](repository-templates/release.yml)                                                                                                           | `.github/release.yml`                                               | Dùng khi tạo Release với nội dung GitHub tự sinh; cấu hình không tự tạo Release; các labels cần tồn tại ở repo đích                                        |
| Các workflow được chọn từ [`workflow-templates/`](workflow-templates/)                                                                                                           | `.github/workflows/`                                                | Chọn theo công nghệ và nhu cầu kiểm tra; chỉnh nhánh, lệnh, quyền và cấu hình phụ thuộc trước khi dùng                                                     |
| [`AGENTS.md`](AGENTS.md), [hướng dẫn Copilot](.github/copilot-instructions.md), [instructions](.github/instructions/), [agents](.github/agents/)                                 | `AGENTS.md` và các đường dẫn tương ứng trong `.github/`             | Viết lại hướng dẫn theo dự án đích; chỉnh `applyTo`, liên kết, lệnh và phạm vi agent vốn đang dành cho repository tổ chức                                  |
| [`repository-templates/.dockerignore`](repository-templates/.dockerignore), [`.env.example`](repository-templates/.env.example), [`PRIVACY.md`](repository-templates/PRIVACY.md) | `.dockerignore`, `.env.example`, `PRIVACY.md` ở gốc dự án           | Chỉ thêm khi dự án cần; `.env.example` dùng giá trị mẫu; điền nội dung sản phẩm và rà soát chính sách quyền riêng tư trước khi công bố                     |

README, mã nguồn, manifests, lockfiles, lệnh kiểm thử và cấu hình build của template cần được viết cho dự án đích. `README.md` và `profile/README.md` của repository này mô tả repository cộng đồng và tổ chức; không dùng nguyên nội dung đó làm README ứng dụng.

### CHUẨN BỊ WORKFLOW VÀ CẤU HÌNH PHỤ THUỘC

- Khi chép workflow vào template, thay `$default-branch` bằng tên nhánh mà dự án dùng. GitHub chỉ tự thay placeholder này khi tạo workflow qua cơ chế workflow templates, không xử lý nó như biến khi sao chép tệp từ template repository.
- Workflow Node.js hiện có cần `.nvmrc` và lockfile phù hợp với `npm ci`; workflow Python cần `.python-version`. Chuẩn bị các tệp và lệnh mà workflow gọi trước khi đưa vào template.
- Metadata `.properties.json` và icon của `workflow-templates/` dùng cho bộ chọn workflow ở repository tổ chức; dự án chỉ cần các tệp workflow đã chọn trong `.github/workflows/`.
- Chọn mẫu Dependabot từ `repository-templates/dependabot.yml`. Cấu hình `.github/dependabot.yml` đang phục vụ chính repository này, với các dependency công cụ phát triển và Dev Container riêng.
- Tài liệu cộng đồng có thể tiếp tục dùng mặc định của tổ chức. Chỉ đặt bản riêng trong template khi dự án cần nội dung riêng hoặc muốn các tài liệu có trong bản clone; các bản sao sẽ ghi đè mặc định tương ứng và không tự cập nhật theo repo nguồn.

### CẤU HÌNH GITHUB SAU KHI TẠO REPOSITORY

Tệp trong template được sao chép tại thời điểm tạo, không tự đồng bộ khi template thay đổi. Labels, secrets, variables, quyền team, rulesets/branch protection, cài đặt Actions, Discussions và báo cáo lỗ hổng cần được đối chiếu và thiết lập bằng cơ chế riêng. Việc chép `labels.yml`, ruleset JSON hoặc `CODEOWNERS` không tự tạo các cài đặt và quyền đó.

Lệnh `python3 scripts/org-setup.py files --repo <tên>` xem trước các tệp thiếu trong repo đích đã có commit. Thêm `--apply` thì script mở PR thêm các tệp thuộc danh sách của nó; không ghi đè tệp đã có và không sao chép toàn bộ nội dung của template repository. Phạm vi cụ thể xem [`repository-templates/README.md`](repository-templates/README.md).

## 9. BỘ KHỞI ĐẦU ĐỀ XUẤT

- `README.md`: giải thích mục đích repository `.github`.
- `profile/README.md`: giới thiệu tổ chức Công ty TNHH TOÀN QUỲNH.
- `CONTRIBUTING.md`: quy trình đóng góp và quy ước dự án.
- `SECURITY.md`: kênh báo cáo lỗ hổng.
- `SUPPORT.md`: kênh hỗ trợ.
- `.github/PULL_REQUEST_TEMPLATE.md`: checklist PR.
- `.github/ISSUE_TEMPLATE/bug_report.yml`: form báo lỗi.
- `.github/ISSUE_TEMPLATE/feature_request.yml`: form yêu cầu tính năng.
- `.github/ISSUE_TEMPLATE/config.yml`: cấu hình bộ mẫu issue.

Thêm các file còn lại khi có nhu cầu thực tế. Quy ước được viết trong tài liệu không tự thực thi; kiểm tra tự động cần workflow hoặc công cụ tương ứng trong từng dự án.

## 10. TÀI LIỆU THAM KHẢO

- [Creating a default community health file](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [Configuring private vulnerability reporting for a repository](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository)
- [Creating a pull request template for your repository](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository)
- [Using query parameters to create a pull request](https://docs.github.com/en/pull-requests/reference/using-query-parameters-to-create-a-pull-request)
- [Reusing workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)
- [Creating workflow templates for your organization](https://docs.github.com/en/actions/how-tos/reuse-automations/create-workflow-templates)
- [Creating a template repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository)
- [Creating a repository from a template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template)

Đối chiếu tài liệu chính thức khi triển khai để xác nhận điều kiện hỗ trợ và cách áp dụng của GitHub.
