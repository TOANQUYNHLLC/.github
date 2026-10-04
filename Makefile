# Lệnh tiện ích — chạy giống hệt GitHub Actions trên máy cục bộ. Gõ `make` để xem danh sách lệnh.
# Yêu cầu: Node.js (theo .nvmrc), Python ≥ 3.11 (mise.toml), ruby, git, ruff, shellcheck, actionlint
# Cài đúng phiên bản trong mise.toml và .nvmrc: mise install; thư viện Node.js tự cài khi chạy kiểm tra.
# Các nhóm kiểm tra khai báo một nơi trong scripts/check.py — workflow validate.yml gọi cùng script.

.DEFAULT_GOAL := help

.PHONY: help check validate test format format-check lint conventions audit tools links versions forms release-notes release-prepare release-pr labels-preview labels-apply hooks org-preview

help: ## Hiển thị danh sách lệnh
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  make %-15s %s\n", $$1, $$2}'

check: ## Mọi kiểm tra GitHub Actions chạy trên Pull Request (trừ CodeQL) — chạy trước khi đẩy
	python3 scripts/check.py

validate: ## Kiểm tra nội dung bằng scripts/validate.py
	python3 scripts/validate.py

test: ## Chạy test tự động của các script (song song trên nhiều tiến trình)
	python3 scripts/run-tests.py

tools: ## Kiểm tra đã cài đủ công cụ, cài thư viện Node.js nếu thiếu
	python3 scripts/check.py tools

format: tools ## Định dạng lại toàn bộ bằng Prettier và ruff
	npx prettier --write .
	ruff format .

format-check: ## Prettier, ruff format, ruff check (job "Định dạng (Prettier, ruff)")
	python3 scripts/check.py format

lint: ## shellcheck, actionlint (job "Shell script và workflow")
	python3 scripts/check.py lint

conventions: ## Tên branch và tiêu đề commit theo quy ước (giống branch-name.yml, pr-title.yml)
	python3 scripts/check.py conventions

audit: ## Dependency có lỗ hổng mức high trở lên (giống dependency-review.yml)
	python3 scripts/check.py audit

hooks: ## Cài git hook (danh sách trong scripts/git-hooks.py), mẫu commit và để git blame bỏ qua commit chỉ đổi định dạng
	python3 scripts/git-hooks.py install
	git config blame.ignoreRevsFile .git-blame-ignore-revs
	git config commit.template .gitmessage

links: ## Kiểm tra liên kết bên ngoài (website, Facebook…) còn hoạt động
	python3 scripts/check-external-links.py

versions: ## Báo công cụ trong mise.toml có bản phát hành mới hơn (Dependabot chưa hỗ trợ mise.toml)
	python3 scripts/check-tool-versions.py

forms: ## Kiểm tra GitHub chấp nhận biểu mẫu Issue, Discussion: make forms REF=<branch> (mặc định main)
	python3 scripts/check-github-forms.py $(or $(REF),main)

release-notes: ## Xem trước nội dung Release của một tag: make release-notes TAG=Stable.v2026.11.010001
	python3 scripts/release.py notes $(TAG)

release-prepare: ## Chuyển CHƯA PHÁT HÀNH của CHANGELOG.md thành phiên bản của tháng nếu có thay đổi từ tag trước
	python3 scripts/release.py prepare

release-pr: ## Chuẩn bị rồi mở Pull Request phát hành tại máy (khi GitHub Actions tắt; cần gh, đứng ở main)
	python3 scripts/release.py prepare --open-pr

labels-preview: ## Xem trước việc đồng bộ nhãn lên các repository
	python3 scripts/org-setup.py labels

labels-apply: ## Đồng bộ nhãn lên các repository đã có (cần GitHub CLI, quyền quản trị; không gồm nhãn mặc định cấp tổ chức)
	python3 scripts/org-setup.py labels --apply

org-preview: ## Xem trước việc áp dụng tệp, cài đặt, ruleset, team, nhãn lên mọi repository và cài đặt tổ chức (cần gh)
	python3 scripts/org-setup.py preview
