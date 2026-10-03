# 🤝 HƯỚNG DẪN ĐÓNG GÓP

Hướng dẫn này áp dụng cho **mọi repository** của **CÔNG TY TNHH TOÀN QUỲNH** trên GitHub, trừ khi repository đó có tệp `CONTRIBUTING.md` riêng.

Cảm ơn bạn đã dành thời gian đóng góp cho dự án. Khi tham gia, bạn đồng ý tuân thủ [Quy tắc ứng xử](CODE_OF_CONDUCT.md). Cần hỗ trợ? Xem [`SUPPORT.md`](SUPPORT.md).

---

## 📋 TRƯỚC KHI BẮT ĐẦU

- Đọc `README.md` của repository để nắm mục đích, cách cài đặt và quy ước riêng của dự án.
- Cài môi trường theo `README.md` và chạy các kiểm tra tự động một lần **trước khi sửa**, để biết lỗi nào có sẵn từ trước.
- Tìm trong Issues và Discussions xem vấn đề hoặc ý tưởng đã được nêu chưa, tránh tạo trùng lặp.
- Với thay đổi lớn, tạo Issue (hoặc Discussion mục Ý tưởng nếu repository đã bật) để trao đổi hướng xử lý trước khi viết mã.
- Vấn đề bảo mật **không** tạo Issue công khai — làm theo [`SECURITY.md`](SECURITY.md).

---

## 🐛 BÁO LỖI VÀ ĐỀ XUẤT

Tạo Issue mới và chọn biểu mẫu phù hợp:

| Biểu mẫu                   | Khi nào dùng                                                         |
| -------------------------- | -------------------------------------------------------------------- |
| 🐛 Báo lỗi                 | Một chức năng chạy sai, không chạy hoặc hiển thị không đúng          |
| ✨ Đề xuất tính năng       | Ý tưởng mới hoặc cải thiện chức năng, giao diện, hiệu năng, tài liệu |
| ❓ Câu hỏi hoặc cần hỗ trợ | Cần hỏi về cách sử dụng, cấu hình hoặc hoạt động của dự án           |

Pull Request được tự gắn nhãn loại theo tiền tố branch (`feature/` → `enhancement`, `fix/` → `bug`…). Issue mới được gắn nhãn `needs triage`; người quản trị phân loại (mức độ ưu tiên, `help wanted`, `good first issue`…), gắn `confirmed` khi đã xác nhận, rồi bỏ nhãn này. Khi cần người báo bổ sung, Issue được gắn `needs more info`; lỗi ở chức năng trước đây chạy đúng gắn `regression`; lỗi do thư viện bên ngoài gắn `upstream`.

Một báo lỗi tốt gồm:

- **Các bước tái hiện** cụ thể, đánh số theo thứ tự.
- **Kết quả mong đợi** và **kết quả thực tế**.
- **Môi trường** (phát triển, kiểm thử, production), **thiết bị, hệ điều hành và trình duyệt**, **phiên bản hoặc commit**.
- Ảnh chụp màn hình hoặc log liên quan — **che** mọi thông tin cá nhân, dữ liệu bệnh nhân, mật khẩu và token trước khi đính kèm.

---

## 🔀 QUY TRÌNH ĐÓNG GÓP MÃ NGUỒN

1. Cập nhật nhánh chính (`main`) và tạo branch mới, đặt tên theo quy ước bên dưới.
2. Thực hiện thay đổi, giữ phạm vi nhỏ và tập trung vào một mục đích.
3. Chạy formatter, lint và kiểm thử của dự án; bổ sung kiểm thử cho thay đổi.
4. Cập nhật tài liệu liên quan khi hành vi, cấu hình hoặc giao diện thay đổi; ghi thay đổi vào `CHANGELOG.md` nếu dự án có tệp này.
5. Đẩy branch lên GitHub, tạo Pull Request và điền đầy đủ biểu mẫu có sẵn.
6. Phản hồi góp ý của người đánh giá; Pull Request chỉ được hợp nhất khi đã được phê duyệt và mọi kiểm tra tự động thành công.
7. Xóa branch sau khi hợp nhất.

```sh
git switch main
git pull --ff-only
git switch -c feature/appointment_booking
# … sửa mã, chạy kiểm tra …
git add -A
git commit -m "feat: thêm chức năng đặt lịch khám"
git push -u origin feature/appointment_booking
```

---

## 🌿 QUY ƯỚC ĐẶT TÊN BRANCH

| Tiền tố     | Mục đích                                    | Ví dụ                           |
| ----------- | ------------------------------------------- | ------------------------------- |
| `feature/`  | Tính năng mới                               | `feature/appointment_booking`   |
| `fix/`      | Sửa lỗi                                     | `fix/login_error`               |
| `hotfix/`   | Sửa lỗi khẩn cấp trên bản đang chạy thật    | `hotfix/payment_timeout`        |
| `docs/`     | Tài liệu                                    | `docs/update_readme`            |
| `refactor/` | Tái cấu trúc, không đổi hành vi             | `refactor/split_payment_module` |
| `perf/`     | Cải thiện hiệu năng                         | `perf/cache_patient_list`       |
| `test/`     | Bổ sung hoặc sửa kiểm thử                   | `test/booking_edge_cases`       |
| `ci/`       | Workflow CI/CD, build, triển khai           | `ci/add_docker_build`           |
| `chore/`    | Cấu hình, phụ thuộc, bảo trì                | `chore/upgrade_dependencies`    |
| `release/`  | Chuẩn bị phát hành: CHANGELOG, số phiên bản | `release/v2026.10`              |

- Tên branch viết bằng **tiếng Anh**, chữ thường, không dấu; các từ nối bằng **dấu gạch dưới** (`_`), ví dụ `feature/appointment_booking`.
- Có thể thêm số Issue sau tiền tố: `fix/123_login_error`.
- Ngắn gọn, tối đa khoảng 50 ký tự; mỗi branch chỉ phục vụ một mục đích.
- Tên branch của Pull Request được kiểm tra tự động (trừ branch do Dependabot tạo).

---

## 📝 QUY ƯỚC COMMIT

Viết commit theo dạng [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) `<loại>(<phạm vi>): <mô tả ngắn>`, ví dụ `fix(booking): sửa lỗi không lưu được lịch hẹn`. Phạm vi là tùy chọn. Tiêu đề Pull Request dùng cùng quy ước và được kiểm tra tự động.

| Loại       | Ý nghĩa                                               |
| ---------- | ----------------------------------------------------- |
| `feat`     | Thêm tính năng                                        |
| `fix`      | Sửa lỗi                                               |
| `docs`     | Cập nhật tài liệu                                     |
| `style`    | Định dạng mã nguồn, không đổi hành vi                 |
| `refactor` | Tái cấu trúc mã nguồn                                 |
| `perf`     | Cải thiện hiệu năng                                   |
| `test`     | Bổ sung hoặc cập nhật kiểm thử                        |
| `build`    | Hệ thống build, phụ thuộc                             |
| `ci`       | Workflow CI/CD                                        |
| `chore`    | Cấu hình, công việc bảo trì khác                      |
| `revert`   | Hoàn tác một commit trước đó, ví dụ `revert: feat: …` |

- Dòng tiêu đề tối đa 72 ký tự, không kết thúc bằng dấu chấm, mô tả **làm gì**.
- Phần thân (cách tiêu đề một dòng trống) giải thích **vì sao** và ảnh hưởng của thay đổi.
- Phần cuối liên kết Issue (`Closes #123`) và ghi thay đổi phá vỡ tương thích bằng dấu `!` sau loại hoặc dòng `BREAKING CHANGE:`; Pull Request đó gắn nhãn `breaking change` để được nêu đầu tiên trong GitHub Release.
- Mỗi commit chỉ chứa một thay đổi có ý nghĩa; không commit file sinh tự động (trừ lockfile, xem mục Phụ thuộc), log, file bí mật (`.env`).
- Ký commit bằng GPG hoặc SSH để GitHub hiển thị **Verified** — **bắt buộc** trên repository áp dụng ruleset **Protect Main** (commit chưa ký không hợp nhất được vào `main`).
- Nếu repository có tệp `.gitmessage`, dùng làm mẫu commit: `git config commit.template .gitmessage`.

```text
feat(booking)!: cho phép đặt lịch theo khung 15 phút

Bệnh nhân cần chọn giờ chính xác hơn khung 30 phút hiện tại.
API /appointments trả về trường slot_minutes thay cho duration.

BREAKING CHANGE: ứng dụng di động phiên bản cũ cần cập nhật để đọc slot_minutes.
Closes #123
```

---

## 🎨 PHONG CÁCH MÃ NGUỒN

- Tuân thủ `.editorconfig` của repository: UTF-8, xuống dòng LF, thụt lề bằng tab độ rộng 4; chỉ ngôn ngữ bắt buộc dấu cách (YAML, Markdown…) mới dùng dấu cách.
- Chạy formatter và lint của dự án trước khi commit (ví dụ `npm run format`, `ruff format`, `gofmt`, `make check`); không định dạng thủ công trái với formatter.
- Nếu dự án có pre-commit hook (ví dụ `make hooks`), cài một lần để phát hiện lỗi định dạng ngay khi commit.
- Không tắt quy tắc lint nếu không có lý do; khi buộc phải tắt, ghi chú lý do ngay tại chỗ.
- Đặt tên biến, hàm, file bằng tiếng Anh, rõ nghĩa; chú thích giải thích **vì sao**, không lặp lại mã làm gì.
- Không để lại mã chết, mã đã comment, `console.log` hoặc `print` dùng để gỡ lỗi.

---

## 🧪 KIỂM THỬ

- Sửa lỗi: thêm kiểm thử tái hiện lỗi, thất bại trước khi sửa và thành công sau khi sửa.
- Tính năng mới: kiểm thử cho luồng chính và các trường hợp biên.
- Mọi kiểm thử phải chạy thành công trên máy cục bộ trước khi tạo Pull Request.
- Không xóa, bỏ qua hoặc nới lỏng kiểm thử chỉ để CI thành công.

---

## 🔄 GIỮ BRANCH CẬP NHẬT

Khi nhánh chính có thay đổi mới, rebase branch của bạn lên nhánh chính và xử lý xung đột ở phía branch:

```sh
git fetch origin
git rebase origin/main
# … xử lý xung đột, rồi: git add <file> && git rebase --continue
git push --force-with-lease --force-if-includes
```

Chỉ force push bằng `--force-with-lease --force-if-includes` (git ≥ 2.30: từ chối ghi đè commit trên GitHub mà bạn chưa kéo về) trên branch của chính mình, **không** force push lên `main` hoặc branch người khác đang làm.

---

## ✅ YÊU CẦU ĐỐI VỚI PULL REQUEST

- Điền đầy đủ [biểu mẫu Pull Request](.github/PULL_REQUEST_TEMPLATE.md), liên kết Issue liên quan.
- Giữ Pull Request nhỏ, dễ đánh giá; tách thay đổi lớn thành nhiều Pull Request nối tiếp.
- Công việc chưa xong mở dưới dạng **Draft Pull Request**, chuyển sang **Ready for review** khi hoàn tất.
- Tự đọc lại toàn bộ diff trước khi yêu cầu đánh giá.
- Thay đổi giao diện kèm ảnh chụp màn hình hoặc video trước và sau.
- Các kiểm tra tự động phải thành công.
- Không chứa mật khẩu, khóa API, token truy cập hoặc thông tin bảo mật.
- Không chứa dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế nhạy cảm.
- Nêu rõ rủi ro, thay đổi phá vỡ tương thích và phương án khôi phục nếu có.

---

## 👀 ĐÁNH GIÁ MÃ NGUỒN

**Người đánh giá**

- Kiểm tra tính đúng đắn, bảo mật, hiệu năng, khả năng bảo trì và kiểm thử đi kèm.
- Góp ý cụ thể, tập trung vào mã nguồn, không vào người viết; giải thích lý do và gợi ý cách sửa.
- Đánh dấu góp ý không bắt buộc bằng tiền tố `nit:`; chọn **Request changes** khi có vấn đề phải sửa trước khi hợp nhất.

**Người gửi Pull Request**

- Trả lời hoặc sửa theo mọi góp ý; đẩy commit mới thay vì force push trong lúc đang được đánh giá, để người đánh giá thấy phần đã sửa.
- Để người đánh giá đánh dấu **Resolve conversation** sau khi đồng ý với cách xử lý.

---

## 🔀 HỢP NHẤT

- Ưu tiên **Squash and merge**: toàn bộ Pull Request thành một commit trên `main`, tiêu đề commit là tiêu đề Pull Request.
- Dùng **Merge** khi cần giữ các commit riêng của Pull Request; khi đó mọi commit phải theo quy ước commit.
- Không có **Rebase and merge**: GitHub tạo lại commit mà không ký được nên commit trên `main` mất chữ ký (ADR 0011 của repository `.github`). Rebase branch của bạn lên nhánh chính tại máy vẫn được.
- Chỉ hợp nhất khi đã được phê duyệt, mọi kiểm tra tự động thành công và mọi góp ý đã được giải quyết.
- Xóa branch sau khi hợp nhất.

---

## 🚑 SỬA LỖI KHẨN CẤP

Dùng khi lỗi trên bản đang chạy thật cần sửa ngay:

1. Tạo branch `hotfix/<mô_tả>` từ `main`.
2. Chỉ sửa đúng lỗi, kèm kiểm thử tái hiện; không gộp thay đổi khác.
3. Tạo Pull Request với nhãn `priority: khẩn cấp` và báo người quản trị để đánh giá ngay.
4. Sau khi hợp nhất, phát hành bản vá và ghi vào `CHANGELOG.md`.

---

## 📦 PHỤ THUỘC

- Chỉ thêm thư viện khi thật sự cần; nêu lý do trong Pull Request và ưu tiên thư viện đang được duy trì, có giấy phép phù hợp.
- Commit kèm lockfile (`package-lock.json`, `poetry.lock`, `go.sum`…); cài bằng lệnh tái lập được như `npm ci`. Repository chỉ dùng công cụ phát triển có thể ghi phiên bản chính xác trong `package.json` thay cho lockfile — nêu rõ trong `README.md` (ví dụ repository `.github`).
- Action trong GitHub Actions ghim theo commit SHA đầy đủ, kèm chú thích phiên bản.
- Pull Request cập nhật phụ thuộc từ Dependabot được đánh giá như mọi Pull Request khác.

---

## 📞 LIÊN HỆ

Mọi thắc mắc về việc đóng góp, vui lòng tạo Issue với biểu mẫu **❓ Câu hỏi hoặc cần hỗ trợ** hoặc liên hệ [toanquynhvn@gmail.com](mailto:toanquynhvn@gmail.com).

---

<p align="center">
    <strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
    Kết nối công nghệ – Kiến tạo giá trị – Chăm sóc bằng sự tận tâm
</p>
