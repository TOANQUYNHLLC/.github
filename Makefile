# ==============================================================================
# Makefile — repository .github của CÔNG TY TNHH TOÀN QUỲNH
# ==============================================================================
# Lệnh tiện ích chạy tại máy giống hệt GitHub Actions. Gõ `make` để xem danh sách lệnh theo nhóm.
# Yêu cầu: Node.js (theo .nvmrc), Python ≥ 3.11 (mise.toml), ruby, git, ruff, shellcheck, actionlint
# Cài đúng phiên bản trong mise.toml và .nvmrc: mise install; thư viện Node.js tự cài khi chạy kiểm tra.
# Các nhóm kiểm tra khai báo một nơi trong scripts/check.py — workflow validate.yml gọi cùng script; logic nhiều
# bước nằm trong scripts/, shell/ (có test), Makefile chỉ gọi lệnh (ADR 00000009).
# Tương thích GNU Make ≥ 3.81 (bản mặc định của macOS): không dùng .ONESHELL, .SHELLFLAGS, !=.

# ------------------------------------------------------------------------------
# Cấu hình
# ------------------------------------------------------------------------------
SHELL := /bin/sh
.DEFAULT_GOAL := help
# Lệnh lỗi giữa chừng thì xóa tệp đích dở dang; không dùng luật dựng sẵn của make (repository không biên dịch).
.DELETE_ON_ERROR:
.SUFFIXES:
MAKEFLAGS += --no-builtin-rules

# Trình thông dịch Python chạy script (cần ≥ 3.11); ghi đè khi cần: make check PYTHON=python3.14
PYTHON := python3

# Tham số của lệnh: make sync BRANCH=…, make release-notes TAG=…, make forms REF=…. Công thức đọc giá trị từ biến
# môi trường ("$$BRANCH") thay vì chèn $(BRANCH) vào lệnh — ký tự đặc biệt không bị shell thông dịch.
export BRANCH TAG REF

##@ Trợ giúp

.PHONY: help
help: ## Hiển thị danh sách lệnh theo nhóm
	@awk 'BEGIN { FS = ":.*## " } /^##@ / { printf "\n%s\n", substr($$0, 5); next } /^[a-z][a-z-]*:.*## / { printf "  make %-16s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

##@ Thiết lập

.PHONY: tools
tools: ## Kiểm tra đã cài đủ công cụ, cài thư viện Node.js nếu thiếu hoặc sai phiên bản
	$(PYTHON) scripts/check.py tools

.PHONY: hooks
hooks: ## Cài git hook (danh sách trong scripts/git-hooks.py), mẫu commit và để git blame bỏ qua commit chỉ đổi định dạng
	$(PYTHON) scripts/git-hooks.py install
	git config blame.ignoreRevsFile .git-blame-ignore-revs
	git config commit.template .gitmessage

.PHONY: format
format: tools ## Định dạng lại toàn bộ bằng Prettier và ruff
	npx --no -- prettier --write .
	ruff format .

##@ Kiểm tra trước khi đẩy

.PHONY: check
check: ## Mọi kiểm tra GitHub Actions chạy trên Pull Request (trừ CodeQL) — chạy trước khi đẩy
	$(PYTHON) scripts/check.py

.PHONY: quick
quick: ## Kiểm tra nhanh khi đang sửa; phạm vi không chắc thì chạy đầy đủ
	$(PYTHON) scripts/check.py quick

.PHONY: validate
validate: ## Kiểm tra nội dung bằng scripts/validate.py
	$(PYTHON) scripts/validate.py

.PHONY: test
test: ## Chạy test tự động của các script (song song trên nhiều tiến trình)
	$(PYTHON) scripts/run-tests.py

.PHONY: format-check
format-check: ## Prettier, ruff format, ruff check (job "Định dạng (Prettier, ruff)")
	$(PYTHON) scripts/check.py format

.PHONY: lint
lint: ## shellcheck, actionlint (job "Shell script và workflow")
	$(PYTHON) scripts/check.py lint

.PHONY: conventions
conventions: ## Tên branch và tiêu đề commit theo quy ước (giống branch-name.yml, pr-title.yml)
	$(PYTHON) scripts/check.py conventions

.PHONY: audit
audit: ## Dependency có lỗ hổng mức high trở lên (giống dependency-review.yml)
	$(PYTHON) scripts/check.py audit

##@ Kiểm tra trực tuyến (cần mạng)

.PHONY: links
links: ## Kiểm tra liên kết bên ngoài (website, Facebook…) còn hoạt động
	$(PYTHON) scripts/check-external-links.py

.PHONY: versions
versions: ## Báo công cụ trong mise.toml, action chỉ có trong workflow-templates/ có bản mới (Dependabot không theo dõi)
	$(PYTHON) scripts/check-tool-versions.py

.PHONY: forms
forms: ## Kiểm tra Issue theo ref; Discussion chỉ xác minh trên nhánh mặc định, ref khác trả mã lỗi: make forms REF=<branch>
	$(PYTHON) scripts/check-github-forms.py "$${REF:-main}"

##@ Đồng bộ git tại máy

.PHONY: sync
sync: ## Chuyển branch (mặc định main), git pull, xóa branch cục bộ đã hợp nhất: make sync [BRANCH=<branch>]
	shell/sync.sh "$${BRANCH:-main}"
	shell/prune-branches.sh

.PHONY: cleanup
cleanup: ## XÓA VĨNH VIỄN mọi tệp git không quản lý, kể cả tệp mới chưa add và node_modules/, .env (git clean -fdx)
	git clean -fdx

##@ Phát hành

.PHONY: release-notes
release-notes: ## Xem trước nội dung Release của một tag: make release-notes TAG=Stable.v2026.11.010001
	$(if $(TAG),,$(error Thiếu TAG: make release-notes TAG=<tag>, ví dụ TAG=Stable.v2026.11.010001))
	$(PYTHON) scripts/release.py notes "$$TAG"

.PHONY: release-prepare
release-prepare: ## Chuyển CHƯA PHÁT HÀNH của CHANGELOG.md thành phiên bản của tháng nếu có thay đổi từ tag trước
	$(PYTHON) scripts/release.py prepare

.PHONY: release-pr
release-pr: ## Chuẩn bị rồi mở Pull Request phát hành tại máy (khi GitHub Actions tắt; cần gh, đứng ở main)
	$(PYTHON) scripts/release.py prepare --open-pr

##@ Quản trị tổ chức (cần GitHub CLI đã đăng nhập)

.PHONY: org-import
org-import: ## Lấy cài đặt hiện tại từ GitHub về github-settings.json; chỉ ghi local
	$(PYTHON) scripts/org-setup.py import-settings

.PHONY: org-import-missing
org-import-missing: ## Bổ sung phần chưa có sau nâng cấp gói hoặc quyền; giữ cài đặt local đã lưu
	$(PYTHON) scripts/org-setup.py import-settings --complete

.PHONY: org-settings-audit
org-settings-audit: ## Kiểm tra toàn bộ phạm vi bản nhập và khác biệt với GitHub; chỉ đọc
	$(PYTHON) scripts/org-setup.py settings-audit

.PHONY: org-settings-preview
org-settings-preview: ## So cài đặt GitHub với github-settings.json, gồm trạng thái Actions và các endpoint bổ sung
	$(PYTHON) scripts/org-setup.py local-settings

.PHONY: org-settings-apply
org-settings-apply: ## Áp dụng cài đặt API từ github-settings.json rồi đọc lại; mục chỉ sửa trên web được báo riêng
	$(PYTHON) scripts/org-setup.py local-settings --apply

.PHONY: org-preview
org-preview: ## Xem trước việc áp dụng tệp, cài đặt, ruleset, team, nhãn lên mọi repository và cài đặt tổ chức
	$(PYTHON) scripts/org-setup.py preview

.PHONY: labels-preview
labels-preview: ## Xem trước việc đồng bộ nhãn lên các repository
	$(PYTHON) scripts/org-setup.py labels

.PHONY: labels-apply
labels-apply: ## Đồng bộ nhãn lên repository đã có (cần quyền quản trị); nhãn mặc định cấp tổ chức nhập trên web
	$(PYTHON) scripts/org-setup.py labels --apply
