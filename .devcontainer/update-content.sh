#!/usr/bin/env bash
# Cài công cụ cho Dev Container / Codespaces từ mise.toml và .nvmrc — ruff, ShellCheck, actionlint, Node.js cùng
# phiên bản với CI — và thư viện Node.js (updateContentCommand: Codespaces prebuild giữ sẵn kết quả).
# Python lấy từ image (devcontainer.json đặt MISE_DISABLE_TOOLS=python), mise không cài lại.
# Không viết bằng Python vì: script chỉ nối các lệnh cài đặt (curl | sh, mise, npm) và chạy trước khi có công cụ
# — shell xử lý chuỗi lệnh cài đặt gọn và tự nhiên hơn.
set -euo pipefail

# Volume giữ công cụ của mise và cache npm qua mỗi lần dựng lại (mounts trong devcontainer.json): Docker tạo volume
# mới — và thư mục cha chưa có như ~/.local, ~/.local/share — thuộc root, người dùng của container chưa ghi được.
for folder in "$HOME/.local" "$HOME/.local/share" "$HOME/.local/share/mise" "$HOME/.npm"; do
	if [[ -d "$folder" && ! -w "$folder" ]]; then
		sudo chown "$(id -u):$(id -g)" "$folder"
	fi
done

[[ -x "$HOME/.local/bin/mise" ]] || curl -fsSL https://mise.run | sh
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"
# Kích hoạt mise khi mở bash, zsh (image có sẵn zsh); chạy lại script không thêm trùng dòng.
for shell in bash zsh; do
	line="eval \"\$(~/.local/bin/mise activate $shell)\""
	grep -qxF "$line" "$HOME/.${shell}rc" 2>/dev/null || echo "$line" >>"$HOME/.${shell}rc"
done

mise trust --yes
mise install

npm install --include=dev --no-audit --no-fund
