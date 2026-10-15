#!/usr/bin/env bash
# Sau khi tạo Dev Container / Codespaces: tin cậy thư mục làm việc rồi cài git hook (make hooks). Công cụ do
# update-content.sh cài trước đó.
# Không viết bằng Python vì: script chỉ nối hai lệnh git, make — shell gọn và tự nhiên hơn.
set -euo pipefail

# Thư mục làm việc gắn vào container có thể thuộc người dùng khác (root): git báo "dubious ownership" và từ chối
# chạy. Tin cậy đúng repository này như tiện ích Dev Containers của VS Code — công cụ khác không tự làm.
# Ghi đường dẫn thật (pwd -P) như git rev-parse --show-toplevel trả về; $PWD kế thừa có thể đi qua liên kết
# (ví dụ /var → /private/var trên macOS) nên khác đường dẫn repository mà git thấy.
workspace="$(pwd -P)"
git config --global --get-all safe.directory | grep -qxF "$workspace" || git config --global --add safe.directory "$workspace"
make hooks
