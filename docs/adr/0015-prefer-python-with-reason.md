# 0015. ƯU TIÊN PYTHON; NGÔN NGỮ KHÁC KHI XỬ LÝ TỐT HƠN, GHI LÝ DO

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-03
- **Điều chỉnh:** [0014](0014-python-only-scripts-git-hooks.md) — thay lệnh cấm "script chỉ viết bằng Python" bằng ưu tiên Python có ghi lý do

## 📌 BỐI CẢNH

ADR 0014 cấm mọi script không phải Python trong `scripts/` và mọi tệp `.sh` ngoài `.devcontainer/`. Quy tắc người dùng đặt là **ưu tiên** Python — nếu ngôn ngữ khác xử lý việc đó tốt hơn thì viết bằng ngôn ngữ đó. Lệnh cấm cứng mâu thuẫn với quy tắc này, còn "ưu tiên" thuần túy thì không kiểm tra tự động được (lỗi đã gặp: hook viết bằng shell dù Python làm tốt hơn).

## ✅ QUYẾT ĐỊNH

- Script (kiểm tra, công cụ, git hook) mặc định viết bằng **Python**.
- Được viết bằng ngôn ngữ khác khi ngôn ngữ đó xử lý việc đó tốt hơn, với điều kiện ghi dòng `Không viết bằng Python vì: <lý do>` trong 10 dòng đầu tệp.
- `validate.py` báo lỗi khi thiếu dòng lý do ở: mọi tệp không phải Python trong `scripts/`; mọi tệp script (`.sh`, `.bash`, `.zsh`, `.rb`, `.pl`, `.ps1`) ở bất kỳ đâu.
- Giữ phần còn lại của ADR 0014: một `scripts/git-hooks.py` cho mọi hook; `pre-push` chạy `make check`, `post-merge` chạy `make org-preview`.

## ⚖️ HỆ QUẢ

- Chọn ngôn ngữ khác phải tự trả lời "vì sao tốt hơn Python" ngay trong tệp — người đánh giá thấy lý do khi xem Pull Request.
- `.devcontainer/post-create.sh` giữ shell, kèm lý do: chỉ nối các lệnh cài đặt, chạy trước khi có công cụ.
- Tệp cấu hình viết bằng ngôn ngữ khác (ví dụ `eslint.config.js`) không phải script nên không cần dòng lý do.
