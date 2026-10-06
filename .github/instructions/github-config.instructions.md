---
applyTo: '.github/**/*.yml,.github/**/*.yaml,workflow-templates/**,repository-templates/**,rulesets/**,labels.yml'
---

# ⚙️ HƯỚNG DẪN CHO CẤU HÌNH GITHUB

Áp dụng cùng [`AGENTS.md`](../../AGENTS.md). Xác định cấu hình chỉ dùng trong repository này hay được phân phối cho các repository khác trước khi sửa.

- Workflow gọi script riêng cho mỗi bước; kiểm tra dùng chung với máy cục bộ qua `scripts/check.py`.
- Ghim action bằng SHA đầy đủ, xác minh bằng `git ls-remote` và ghi chú phiên bản. Đọc phiên bản công cụ từ các nguồn đã quy định.
- Khai báo quyền tối thiểu, concurrency và timeout cho mỗi job; quyền ghi chỉ đặt ở job cần dùng và có chú thích lý do.
- Truyền dữ liệu sự kiện qua `env:`; không chèn biểu thức GitHub Actions vào `run:`. Không chạy mã Pull Request không đáng tin trong workflow có quyền ghi.
- Nhãn trong biểu mẫu, Dependabot, cấu hình Release, labeler và stale phải có trong `labels.yml`; đối chiếu cả cấu hình của repository và bản mẫu.
- Sửa ruleset cấp repository thì sinh lại bản cấp tổ chức bằng `orgRulesets()` trong `scripts/orgsetup/rulesets.py`; giữ yêu cầu chữ ký cho nhánh và tag.
- Biểu mẫu dùng liên kết tuyệt đối vì có thể hiển thị ở repository khác. Khi sửa biểu mẫu, làm theo bước xác minh GitHub trong `AGENTS.md`.
- Chạy `make check` và cập nhật README, hướng dẫn hoặc ADR liên quan theo quy tắc của dự án.
