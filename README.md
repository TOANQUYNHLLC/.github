# 🏢 CÔNG TY TNHH TOÀN QUỲNH

[![Kiểm tra repository](https://github.com/TOANQUYNHLLC/.github/actions/workflows/validate.yml/badge.svg)](https://github.com/TOANQUYNHLLC/.github/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Repository `.github` chính thức của **CÔNG TY TNHH TOÀN QUỲNH**: hồ sơ tổ chức, tệp cộng đồng mặc định và cấu hình GitHub dùng chung cho mọi repository. Giới thiệu về công ty xem tại [`profile/README.md`](profile/README.md).

---

## 🎯 MỤC ĐÍCH

- 🏢 Quản lý nội dung giới thiệu công khai của tổ chức trên GitHub.
- 📋 Chuẩn hóa biểu mẫu Issue, Pull Request và quy trình cộng tác cho mọi repository.
- 🔐 Công bố chính sách bảo mật, quy tắc ứng xử và kênh hỗ trợ dùng chung.
- ⚙️ Cung cấp workflow mẫu, bộ nhãn chuẩn và công cụ kiểm tra để các dự án nhất quán ngay từ đầu.

---

## ⚙️ CÁCH HOẠT ĐỘNG

GitHub tự động áp dụng nội dung của repository này cho toàn tổ chức:

| Nội dung | Hiển thị ở đâu |
|---|---|
| `profile/README.md` | Trang giới thiệu của tổ chức trên GitHub |
| Tệp cộng đồng mặc định và biểu mẫu | Mọi repository **chưa có tệp cùng tên riêng** — tệp riêng của repository luôn được ưu tiên |
| `workflow-templates/` | Mục *Actions → New workflow* của mọi repository trong tổ chức |

`LICENSE`, `CODEOWNERS` và `dependabot.yml` **không** được kế thừa — mỗi repository cần tệp riêng.

---

## 📁 CẤU TRÚC REPOSITORY

**Hồ sơ tổ chức**

| Đường dẫn | Chức năng |
|---|---|
| [`profile/README.md`](profile/README.md) | Trang giới thiệu công khai của CÔNG TY TNHH TOÀN QUỲNH trên GitHub |

**Tệp cộng đồng mặc định** — áp dụng cho mọi repository của tổ chức

| Đường dẫn | Chức năng |
|---|---|
| [`SECURITY.md`](SECURITY.md) | Chính sách bảo mật và cách báo cáo lỗ hổng |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Hướng dẫn đóng góp: quy trình, quy ước branch, commit và Pull Request |
| [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) | Quy tắc ứng xử trong không gian cộng tác |
| [`SUPPORT.md`](SUPPORT.md) | Kênh hỗ trợ: đặt câu hỏi, báo lỗi, đề xuất, bảo mật và liên hệ |
| [`ISSUE_TEMPLATE/`](ISSUE_TEMPLATE/) | Biểu mẫu Issue dạng form (báo lỗi, đề xuất tính năng, câu hỏi) và cấu hình `config.yml` |
| [`PULL_REQUEST_TEMPLATE.md`](PULL_REQUEST_TEMPLATE.md) | Biểu mẫu Pull Request: tóm tắt thay đổi, kiểm thử, rủi ro và checklist |

**Tài nguyên dùng chung**

| Đường dẫn | Chức năng |
|---|---|
| [`workflow-templates/`](workflow-templates/) | Workflow mẫu: Node.js CI, kiểm tra tài liệu |
| [`labels.yml`](labels.yml) | Bộ nhãn chuẩn: loại vấn đề, mức độ ưu tiên, trạng thái |
| [`scripts/sync-labels.sh`](scripts/sync-labels.sh) | Đồng bộ `labels.yml` lên các repository bằng GitHub CLI (mặc định chỉ xem trước) |

**Cấu hình của repository này**

| Đường dẫn | Chức năng |
|---|---|
| [`.github/workflows/validate.yml`](.github/workflows/validate.yml) | CI: kiểm tra nội dung, chạy test và lint YAML, shell script, workflow khi push và tạo Pull Request |
| [`.github/workflows/pr-title.yml`](.github/workflows/pr-title.yml) | Bắt buộc tiêu đề Pull Request theo quy ước commit (`feat:`, `fix:`…) |
| [`.github/workflows/release.yml`](.github/workflows/release.yml) | Gắn tag `v*` là tự tạo GitHub Release với nội dung lấy từ `CHANGELOG.md` |
| [`.github/workflows/links.yml`](.github/workflows/links.yml) | Kiểm tra liên kết bên ngoài (website, Facebook…) hằng tuần |
| [`.github/dependabot.yml`](.github/dependabot.yml) | Tự động đề xuất cập nhật các GitHub Action đang ghim theo commit SHA |
| [`.github/CODEOWNERS`](.github/CODEOWNERS) | Người quản trị bắt buộc duyệt mọi thay đổi |
| [`scripts/validate.py`](scripts/validate.py) | Kiểm tra liên kết, tiêu đề viết hoa, nhãn, biểu mẫu Issue, workflow, định dạng file, email chung, `security.txt`, `CHANGELOG.md` và mẫu email bảo mật |
| [`scripts/test_validate.py`](scripts/test_validate.py) | Test tự động: mỗi luật kiểm tra đều có một ca cố ý làm hỏng để chứng minh luật còn hoạt động |
| [`scripts/release-notes.py`](scripts/release-notes.py) · [`scripts/check-external-links.py`](scripts/check-external-links.py) | Tách nội dung phát hành từ `CHANGELOG.md`; kiểm tra liên kết bên ngoài |
| [`.well-known/security.txt`](.well-known/security.txt) | Tệp `security.txt` (RFC 9116) để đăng tại `https://toanquynh.com/.well-known/security.txt` |
| [`Makefile`](Makefile) | Lệnh chạy kiểm tra cục bộ giống CI — gõ `make` để xem danh sách |
| [`.editorconfig`](.editorconfig) · [`.gitattributes`](.gitattributes) · [`.gitignore`](.gitignore) · [`.yamllint.yml`](.yamllint.yml) | Quy ước định dạng: UTF-8, xuống dòng LF, thụt lề, bỏ qua file tạm |
| [`CHANGELOG.md`](CHANGELOG.md) | Nhật ký thay đổi của repository này, theo phiên bản |
| [`LICENSE`](LICENSE) | Giấy phép MIT cho nội dung của repository này |

---

## 🛠️ PHÁT TRIỂN CỤC BỘ

Cài công cụ (macOS):

```bash
brew install yamllint shellcheck actionlint
```

**Quy tắc định dạng** (khai báo trong [`.editorconfig`](.editorconfig), kiểm tra tự động bằng `make check`):

- Thụt lề bằng **tab**, độ rộng tab **4**.
- Ngôn ngữ bắt buộc dùng dấu cách (YAML) thì dùng **dấu cách**, mỗi cấp **4**.
- UTF-8, xuống dòng LF, có dòng trống cuối file, không khoảng trắng cuối dòng.

Chạy toàn bộ kiểm tra giống CI trước khi tạo Pull Request:

```bash
make check
```

| Lệnh | Tác dụng |
|---|---|
| `make` | Xem danh sách lệnh |
| `make validate` | Kiểm tra nội dung bằng `scripts/validate.py` |
| `make test` | Chạy test tự động của các script kiểm tra |
| `make lint` | Kiểm tra đã cài đủ công cụ rồi lint YAML, shell script và workflow |
| `make links` | Kiểm tra liên kết bên ngoài còn hoạt động |
| `make release-notes TAG=…` | Xem trước nội dung GitHub Release của một tag |
| `make labels-preview` | Xem trước việc đồng bộ nhãn lên các repository |
| `make labels-apply` | Đồng bộ nhãn (cần GitHub CLI và quyền quản trị) |

---

## 📝 QUẢN LÝ VÀ CẬP NHẬT

Các nội dung trong repository này được quản lý bởi những thành viên có thẩm quyền của CÔNG TY TNHH TOÀN QUỲNH. Mọi thay đổi đi qua Pull Request theo [`CONTRIBUTING.md`](CONTRIBUTING.md) và cần người quản trị duyệt.

Khi cập nhật nội dung, cần bảo đảm:

- Thông tin chính xác và phù hợp với định hướng của công ty.
- Không công khai dữ liệu cá nhân, thông tin y tế hoặc thông tin nội bộ.
- Không lưu trữ mật khẩu, mã truy cập, khóa API hoặc dữ liệu bảo mật.
- `make check` chạy thành công trước khi đưa lên nhánh chính.
- Các thay đổi quan trọng phải có mô tả rõ ràng trong commit hoặc Pull Request, và được ghi vào [`CHANGELOG.md`](CHANGELOG.md).
- Tuân thủ quy định pháp luật và các chính sách của GitHub.

---

## 🚀 PHÁT HÀNH

1. Chuyển nội dung mục **CHƯA PHÁT HÀNH** trong [`CHANGELOG.md`](CHANGELOG.md) thành phiên bản mới, ví dụ `## [v2026.10.Stable] — 2026-10-01`, rồi tạo lại mục **CHƯA PHÁT HÀNH** trống.
2. Kiểm tra trước nội dung: `make release-notes TAG=v2026.10.Stable`.
3. Gắn và đẩy tag: `git tag v2026.10.Stable && git push origin v2026.10.Stable` — workflow tự tạo GitHub Release.

---

## 🔐 BẢO MẬT

Nếu phát hiện lỗ hổng hoặc vấn đề liên quan đến bảo mật, vui lòng **không đăng tải công khai** trong Issues, Discussions hoặc Pull Requests. Cách báo cáo riêng, thông tin cần cung cấp và cam kết xử lý được quy định tại [`SECURITY.md`](SECURITY.md).

> ⚠️ Không gửi mật khẩu, khóa API, token truy cập, dữ liệu cá nhân, hồ sơ bệnh án hoặc thông tin y tế nhạy cảm qua bất kỳ kênh công khai nào.

---

## 📞 LIÊN HỆ

- 📧 **Email:** [toanquynhvn@gmail.com](mailto:toanquynhvn@gmail.com)
- 🌐 **Website:** [https://toanquynh.com](https://toanquynh.com)
- 🏢 **Thông tin đầy đủ:** [`profile/README.md`](profile/README.md#-thông-tin-liên-hệ)

---

<p align="center">
	<strong>© 2026 CÔNG TY TNHH TOÀN QUỲNH</strong><br>
	Repository quản lý hồ sơ và cấu hình GitHub của tổ chức.
</p>
