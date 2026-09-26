# Lệnh tiện ích — chạy giống hệt CI trên máy cục bộ. Gõ `make` để xem danh sách lệnh.
# Yêu cầu: Node.js (theo .nvmrc), python3, ruby, git, ruff, shellcheck, actionlint
# (macOS: brew install ruff shellcheck actionlint; sau đó chạy `npm ci`).

.DEFAULT_GOAL := help
TOOLS := git python3 ruby npx ruff shellcheck actionlint

.PHONY: help check validate test format format-check lint tools links release-notes labels-preview labels-apply hooks org-preview

help: ## Hiển thị danh sách lệnh
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  make %-15s %s\n", $$1, $$2}'

check: validate test format-check lint ## Chạy toàn bộ kiểm tra giống CI

validate: ## Kiểm tra nội dung bằng scripts/validate.py
	python3 scripts/validate.py

test: ## Chạy test tự động của các script kiểm tra
	python3 -m unittest discover -s scripts -p 'test_*.py'

tools: ## Kiểm tra đã cài đủ công cụ
	@missing=""; for tool in $(TOOLS); do command -v $$tool >/dev/null || missing="$$missing $$tool"; done; \
	if [ -n "$$missing" ]; then echo "Thiếu công cụ:$$missing — macOS: brew install ruff shellcheck actionlint; Node.js cho npx"; exit 1; fi; \
	[ -d node_modules ] || npm ci --no-audit --no-fund

format: tools ## Định dạng lại toàn bộ bằng Prettier và ruff
	npx prettier --write .
	ruff format scripts

format-check: tools ## Kiểm tra định dạng (Prettier, ruff) giống CI
	npx prettier --check .
	ruff format --check scripts

lint: tools ## ESLint, shellcheck và actionlint
	npx eslint .
	shellcheck scripts/*.sh .devcontainer/*.sh
	actionlint .github/workflows/*.yml workflow-templates/*.yml

hooks: ## Cài pre-commit hook, mẫu commit và để git blame bỏ qua commit chỉ đổi định dạng
	ln -sf ../../scripts/pre-commit.sh .git/hooks/pre-commit
	git config blame.ignoreRevsFile .git-blame-ignore-revs
	git config commit.template .gitmessage
	@echo "Đã cài .git/hooks/pre-commit, blame.ignoreRevsFile và commit.template"

links: ## Kiểm tra liên kết bên ngoài (website, Facebook…) còn hoạt động
	python3 scripts/check-external-links.py

release-notes: ## Xem trước nội dung Release của một tag: make release-notes TAG=v2026.09.Stable
	python3 scripts/release-notes.py $(TAG)

labels-preview: ## Xem trước việc đồng bộ nhãn lên các repository
	scripts/sync-labels.sh

labels-apply: ## Đồng bộ nhãn lên các repository (cần GitHub CLI và quyền quản trị)
	scripts/sync-labels.sh --apply

org-preview: ## Xem trước việc áp dụng tệp, cài đặt, ruleset, team lên mọi repository (cần gh)
	for command in files settings rulesets team; do python3 scripts/org-setup.py $$command; done
