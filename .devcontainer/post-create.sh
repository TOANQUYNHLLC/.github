#!/usr/bin/env bash
# Cài công cụ kiểm tra cho Dev Container / Codespaces, cùng phiên bản với CI và mise.toml.
set -euo pipefail

sudo apt-get update
sudo apt-get install -y --no-install-recommends shellcheck

pipx install ruff==0.16.9

# actionlint: dùng script cài đặt chính thức, đặt vào thư mục bin của người dùng.
mkdir -p "$HOME/.local/bin"
bash <(curl -fsSL https://raw.githubusercontent.com/rhysd/actionlint/v1.7.12/scripts/download-actionlint.bash) 1.7.12 "$HOME/.local/bin"

npm ci --no-audit --no-fund
make hooks
