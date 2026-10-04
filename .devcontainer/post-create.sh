#!/usr/bin/env bash
# Cài công cụ cho Dev Container / Codespaces từ mise.toml và .nvmrc — ruff, ShellCheck, actionlint, Node.js cùng
# phiên bản với CI.
# Python lấy từ image (devcontainer.json đặt MISE_DISABLE_TOOLS=python), mise không cài lại.
# Không viết bằng Python vì: script chỉ nối các lệnh cài đặt (curl | sh, mise, npm, make) và chạy trước khi
# có công cụ — shell xử lý chuỗi lệnh cài đặt gọn và tự nhiên hơn.
set -euo pipefail

curl -fsSL https://mise.run | sh
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"
# Kích hoạt mise khi mở bash, zsh (image có sẵn zsh); chạy lại script không thêm trùng dòng.
for shell in bash zsh; do
	line="eval \"\$(~/.local/bin/mise activate $shell)\""
	grep -qxF "$line" "$HOME/.${shell}rc" 2>/dev/null || echo "$line" >>"$HOME/.${shell}rc"
done

mise trust --yes
mise install

npm install --no-audit --no-fund
# Thư mục làm việc gắn vào container có thể thuộc người dùng khác (root): git báo "dubious ownership" và từ chối
# chạy. Tin cậy đúng repository này như tiện ích Dev Containers của VS Code — công cụ khác không tự làm.
git config --global --get-all safe.directory | grep -qxF "$PWD" || git config --global --add safe.directory "$PWD"
make hooks
