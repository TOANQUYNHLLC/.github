#!/usr/bin/env bash
# Cài công cụ cho Dev Container / Codespaces từ mise.toml và .nvmrc — cùng phiên bản với CI.
set -euo pipefail

curl -fsSL https://mise.run | sh
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"
# shellcheck disable=SC2016 # Biểu thức được chạy khi mở shell, không phải lúc này.
echo 'eval "$(~/.local/bin/mise activate bash)"' >>"$HOME/.bashrc"

mise trust --yes
mise install

npm install --no-audit --no-fund
make hooks
