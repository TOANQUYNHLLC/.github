# Lệnh tiện ích — chạy giống hệt CI trên máy cục bộ. Gõ `make` để xem danh sách lệnh.
# Yêu cầu: python3, ruby, git; lint cần thêm yamllint, shellcheck, actionlint
# (macOS: brew install yamllint shellcheck actionlint).

.DEFAULT_GOAL := help
LINT_TOOLS := yamllint shellcheck actionlint

.PHONY: help check validate test lint tools links release-notes labels-preview labels-apply

help: ## Hiển thị danh sách lệnh
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  make %-15s %s\n", $$1, $$2}'

check: validate test lint ## Chạy toàn bộ kiểm tra giống CI

validate: ## Kiểm tra nội dung bằng scripts/validate.py
	python3 scripts/validate.py

test: ## Chạy test tự động của các script kiểm tra
	python3 -m unittest discover -s scripts -p 'test_*.py'

tools: ## Kiểm tra đã cài đủ công cụ lint
	@missing=""; for tool in $(LINT_TOOLS); do command -v $$tool >/dev/null || missing="$$missing $$tool"; done; \
	if [ -n "$$missing" ]; then echo "Thiếu công cụ:$$missing — macOS: brew install$$missing"; exit 1; fi; \
	echo "Đã có đủ công cụ: $(LINT_TOOLS)"

lint: tools ## Lint YAML, shell script và workflow
	yamllint -c .yamllint.yml --strict .
	shellcheck scripts/*.sh
	actionlint .github/workflows/*.yml workflow-templates/*.yml

links: ## Kiểm tra liên kết bên ngoài (website, Facebook…) còn hoạt động
	python3 scripts/check-external-links.py

release-notes: ## Xem trước nội dung Release của một tag: make release-notes TAG=v2026.09.Stable
	python3 scripts/release-notes.py $(TAG)

labels-preview: ## Xem trước việc đồng bộ nhãn lên các repository
	scripts/sync-labels.sh

labels-apply: ## Đồng bộ nhãn lên các repository (cần GitHub CLI và quyền quản trị)
	scripts/sync-labels.sh --apply
