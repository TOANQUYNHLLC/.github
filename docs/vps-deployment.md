# 🚀 TRIỂN KHAI LÊN VPS

Hướng dẫn dành cho người duy trì dự án đưa ứng dụng từ repository GitHub của tổ chức lên VPS Linux và tự động triển khai mỗi khi Pull Request được hợp nhất vào `main`. Các tệp mẫu dưới đây đặt trong **repository đích** và trên VPS; repository `.github` không chứa cấu hình triển khai của dự án nào. Địa chỉ máy chủ, khóa SSH và tệp `.env` chỉ nằm trong GitHub Secrets và trên VPS, không commit vào repository theo [ADR 00000014](adr/00000014-public-repository-scope.md).

Ví dụ dùng ứng dụng `myapp` của `TOANQUYNHLLC/myapp`, chạy Node.js ở cổng `3000`, tên miền `myapp.example.com`, VPS `203.0.113.10`. Thay các giá trị này theo dự án.

## 🧭 CƠ CHẾ HOẠT ĐỘNG

```text
Pull Request ──hợp nhất──▶ main ──push──▶ GitHub Actions (workflow Deploy, environment production)
                                                │  SSH bằng khóa chỉ được chạy lệnh triển khai
                                                ▼
                                   VPS: deploy-myapp <commit SHA>
                                   lấy commit → build vào releases/<phiên bản>
                                   → đổi symlink current → khởi động lại dịch vụ
                                   → kiểm tra /health, lỗi thì quay lại phiên bản trước
```

Ruleset [Protect Main](../rulesets/README.md) chỉ cho cập nhật `main` qua Pull Request đã được duyệt và đạt status checks, nên mỗi lần `main` nhận commit mới là một Pull Request vừa hợp nhất. Workflow vì vậy chạy theo sự kiện `push` vào `main` thay cho `pull_request` với `types: [closed]`:

- `push` triển khai đúng commit nằm trên `main` sau khi hợp nhất, với mọi cách hợp nhất (Merge, Squash, Rebase).
- Job dùng environment `production` giới hạn cho nhánh `main`; sự kiện `pull_request` bị đối chiếu theo branch của Pull Request nên không qua được giới hạn này, và Pull Request từ fork không được đọc secrets.
- Người trong danh sách bỏ qua của ruleset đẩy thẳng lên `main` cũng kích hoạt triển khai.

Trên VPS, mỗi phiên bản nằm trong một thư mục riêng; dịch vụ chạy từ symlink `current`. Đổi symlink là thao tác nguyên tử, phiên bản cũ còn nguyên để quay lại ngay khi phiên bản mới lỗi.

```text
/srv/myapp/
├── repo.git/            bản sao bare của repository, chỉ đọc qua deploy key
├── releases/<phiên bản>/ mã nguồn đã build của từng lần triển khai
├── shared/.env          cấu hình và bí mật dùng chung cho mọi phiên bản
└── current -> releases/<phiên bản đang chạy>
```

## 📋 YÊU CẦU

- VPS Ubuntu 24.04 LTS hoặc Debian 12, đăng nhập được bằng tài khoản quản trị có `sudo` và khóa SSH.
- Tên miền trỏ bản ghi A/AAAA về VPS nếu dùng HTTPS.
- Repository đích đã áp dụng ruleset Protect Main và status checks bắt buộc theo [hướng dẫn ruleset](../rulesets/README.md); kiểm tra chạy trong Pull Request, workflow triển khai không chạy lại tests.
- Tổ chức bật GitHub Actions và runner chuẩn theo [hướng dẫn workflow chờ runner](local-checks.md#-workflow-chờ-runner); chính sách Actions của tổ chức quản lý theo [hướng dẫn cài đặt GitHub](github-settings.md).
- Ứng dụng khởi động được bằng một lệnh và có endpoint kiểm tra sức khỏe (ví dụ `/health`) trả mã `200` khi sẵn sàng.
- Quyền quản trị repository để tạo environment, secrets và deploy key.

## 🖥️ CHUẨN BỊ VPS

Các lệnh trong mục này chạy trên VPS bằng tài khoản quản trị.

### 1️⃣ CẬP NHẬT VÀ BẢO VỆ MÁY CHỦ

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y git curl ufw fail2ban unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Tắt đăng nhập bằng mật khẩu và đăng nhập trực tiếp bằng `root` sau khi đã đăng nhập được bằng khóa SSH. Tạo tệp `/etc/ssh/sshd_config.d/99-hardening.conf`:

```text
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
```

Kiểm tra cấu hình rồi nạp lại; giữ phiên SSH hiện tại và mở phiên mới để xác nhận còn đăng nhập được trước khi thoát:

```bash
sudo sshd -t
sudo systemctl reload ssh
```

### 2️⃣ NGƯỜI DÙNG TRIỂN KHAI VÀ THƯ MỤC

Người dùng `deploy` sở hữu mã nguồn và chạy dịch vụ; không có mật khẩu, không thuộc nhóm `sudo`.

```bash
sudo adduser --system --group --home /srv/myapp --shell /bin/bash deploy
sudo install -d -o deploy -g deploy -m 750 /srv/myapp /srv/myapp/releases /srv/myapp/shared
sudo install -d -o deploy -g deploy -m 700 /srv/myapp/.ssh
```

Cài runtime của dự án ở phạm vi hệ thống, đúng phiên bản mà repository đích khai báo (`.nvmrc`, `mise.toml`, `.python-version`…), ví dụ gói Node.js của NodeSource hoặc Python của bản phân phối. Lệnh triển khai chạy qua SSH không nạp tệp cấu hình shell; runtime cài bằng mise cần thêm thư mục shims vào `PATH` trong lệnh triển khai ở bước 6.

### 3️⃣ DEPLOY KEY ĐỂ VPS ĐỌC REPOSITORY

Tạo khóa đọc repository cho người dùng `deploy`:

```bash
sudo -u deploy ssh-keygen -t ed25519 -N '' -C 'myapp-vps-read' -f /srv/myapp/.ssh/github_read
sudo -u deploy cat /srv/myapp/.ssh/github_read.pub
```

Thêm khóa công khai vừa in vào **Settings → Deploy keys → Add deploy key** của repository, **không** tích **Allow write access**. Deploy key chỉ có quyền trên một repository; mỗi dự án dùng khóa riêng.

Khai báo bí danh `github-myapp` để Git dùng đúng khóa. Mở tệp bằng `sudoedit -u deploy /srv/myapp/.ssh/config`, ghi nội dung dưới đây rồi đặt quyền bằng `sudo chmod 600 /srv/myapp/.ssh/config`:

```text
Host github-myapp
	HostName github.com
	User git
	IdentityFile ~/.ssh/github_read
	IdentitiesOnly yes
```

Kết nối lần đầu, đối chiếu dấu vân tay khóa máy chủ với [dấu vân tay GitHub công bố](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints) trước khi chấp nhận, rồi tạo bản sao bare:

```bash
sudo -u deploy ssh -T github-myapp
sudo -u deploy git clone --bare github-myapp:TOANQUYNHLLC/myapp.git /srv/myapp/repo.git
sudo -u deploy git --git-dir=/srv/myapp/repo.git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
sudo -u deploy git --git-dir=/srv/myapp/repo.git fetch --prune origin
```

Lệnh `ssh -T` thành công khi GitHub trả lời `You've successfully authenticated, but GitHub does not provide shell access`.

### 4️⃣ CẤU HÌNH DÙNG CHUNG

Tạo `/srv/myapp/shared/.env` từ `.env.example` của dự án (mẫu của tổ chức: [`repository-templates/.env.example`](../repository-templates/.env.example)) và điền giá trị thật trên VPS:

```bash
sudo -u deploy touch /srv/myapp/shared/.env
sudo chmod 600 /srv/myapp/shared/.env
sudoedit -u deploy /srv/myapp/shared/.env
```

Mỗi lần triển khai liên kết tệp này vào thư mục phiên bản, nên cấu hình giữ nguyên qua các lần triển khai. Tệp tải lên, dữ liệu do ứng dụng ghi cũng đặt trong `shared/`.

### 5️⃣ DỊCH VỤ SYSTEMD

Tạo `/etc/systemd/system/myapp.service`:

```ini
[Unit]
Description=myapp
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=/srv/myapp/current
EnvironmentFile=/srv/myapp/shared/.env
# Python: ExecStart=/srv/myapp/current/.venv/bin/gunicorn app:app --bind 127.0.0.1:3000
ExecStart=/usr/bin/node dist/server.js
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/srv/myapp/shared

[Install]
WantedBy=multi-user.target
```

Ứng dụng chỉ lắng nghe `127.0.0.1`; Nginx nhận kết nối từ bên ngoài. `ProtectSystem=strict` chỉ cho dịch vụ ghi vào `shared/`. Bật dịch vụ, chưa khởi động vì `current` chưa có:

```bash
sudo systemctl daemon-reload
sudo systemctl enable myapp.service
```

Cho người dùng `deploy` khởi động lại đúng dịch vụ này, không cấp quyền `sudo` khác. Tạo tệp bằng `sudo visudo -f /etc/sudoers.d/myapp-deploy`:

```text
deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart myapp.service
```

### 6️⃣ LỆNH TRIỂN KHAI

Lệnh `deploy-myapp` nhận commit SHA đầy đủ, chỉ chấp nhận commit thuộc `main`, build vào thư mục phiên bản mới, chuyển `current`, kiểm tra sức khỏe và tự quay lại phiên bản trước khi lỗi. Tạo tệp bằng `sudoedit /usr/local/bin/deploy-myapp`, sửa mục build theo dự án:

```bash
#!/usr/bin/env bash
# Triển khai một commit của nhánh main: deploy-myapp <commit SHA>.
set -euo pipefail

APP=myapp
BASE=/srv/$APP
REPO=$BASE/repo.git
HEALTH_URL=http://127.0.0.1:3000/health
KEEP_RELEASES=5
# Runtime cài bằng mise: export PATH="$BASE/.local/share/mise/shims:$PATH"

# Gọi qua SSH, forced command trong authorized_keys đưa lệnh của client vào SSH_ORIGINAL_COMMAND.
sha=${1:-${SSH_ORIGINAL_COMMAND:-}}
if [[ ! $sha =~ ^[0-9a-f]{40}$ ]]; then
	echo "Cần commit SHA đầy đủ 40 ký tự, nhận: '$sha'" >&2
	exit 2
fi

# Mỗi lần chỉ một lượt triển khai; lượt sau chờ tối đa 10 phút.
exec 9>"$BASE/deploy.lock"
flock -w 600 9

git --git-dir="$REPO" fetch --prune --quiet origin
if ! git --git-dir="$REPO" merge-base --is-ancestor "$sha" origin/main; then
	echo "Commit $sha không thuộc nhánh main" >&2
	exit 1
fi

previous=''
if [[ -L $BASE/current ]]; then
	previous=$(readlink -f "$BASE/current")
fi

activate() {
	ln -sfn "$1" "$BASE/current.next"
	mv -T "$BASE/current.next" "$BASE/current"
	sudo /usr/bin/systemctl restart "$APP.service"
}

isHealthy() {
	for _ in {1..30}; do
		if curl -fsS -o /dev/null "$HEALTH_URL"; then
			return 0
		fi
		sleep 2
	done
	return 1
}

# Mỗi lượt một thư mục mới, kể cả khi triển khai lại cùng commit.
release=$(mktemp -d "$BASE/releases/$(date -u +%Y%m%d%H%M%S)-${sha:0:12}-XXXXXX")
trap 'rm -rf -- "$release"' ERR
echo "Build $sha vào $release"
git --git-dir="$REPO" archive "$sha" | tar -x -C "$release"
ln -sfn "$BASE/shared/.env" "$release/.env"
echo "$sha" >"$release/REVISION"
cd "$release"
# Build — thay bằng lệnh của dự án.
# Python: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
npm ci
npm run build
npm prune --omit=dev
trap - ERR

if ! activate "$release" || ! isHealthy; then
	echo "Phiên bản $sha không đạt kiểm tra sức khỏe" >&2
	if [[ -n $previous ]]; then
		activate "$previous"
		echo "Đã quay lại $(cat "$previous/REVISION")" >&2
	fi
	exit 1
fi

# Giữ các phiên bản mới nhất để quay lại nhanh; không xóa phiên bản đang chạy.
# Tên thư mục bắt đầu bằng thời điểm build nên glob sắp xếp từ cũ đến mới.
current=$(readlink -f "$BASE/current")
releases=("$BASE"/releases/*)
for ((index = 0; index < ${#releases[@]} - KEEP_RELEASES; index++)); do
	if [[ ${releases[index]} != "$current" ]]; then
		rm -rf -- "${releases[index]}"
	fi
done
echo "Đã triển khai $sha"
```

Tệp thuộc `root` để khóa của GitHub Actions không sửa được lệnh mà nó được phép chạy:

```bash
sudo chown root:root /usr/local/bin/deploy-myapp
sudo chmod 755 /usr/local/bin/deploy-myapp
```

### 7️⃣ NGINX VÀ HTTPS

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Tạo `/etc/nginx/sites-available/myapp`:

```nginx
server {
	listen 80;
	listen [::]:80;
	server_name myapp.example.com;

	location / {
		proxy_pass http://127.0.0.1:3000;
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
	}
}
```

Bật site, kiểm tra cấu hình và xin chứng chỉ; Certbot tự sửa cấu hình sang HTTPS và gia hạn bằng timer của systemd:

```bash
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/myapp
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d myapp.example.com
```

### 8️⃣ TRIỂN KHAI LẦN ĐẦU TẠI VPS

Chạy lệnh triển khai với commit mới nhất của `main` để kiểm tra toàn bộ phần VPS trước khi nối GitHub Actions:

```bash
sudo -u deploy /usr/local/bin/deploy-myapp "$(sudo -u deploy git --git-dir=/srv/myapp/repo.git rev-parse origin/main)"
systemctl status myapp.service
curl -fsS https://myapp.example.com/health
```

## 🔑 KHÓA SSH CHO GITHUB ACTIONS

Tạo khóa trên máy của người quản trị, không tạo trên VPS, để khóa riêng chỉ nằm trong GitHub Secrets:

```bash
ssh-keygen -t ed25519 -N '' -C 'github-actions-myapp' -f ./myapp-actions
```

Trên VPS, mở `authorized_keys` của người dùng `deploy` và thêm nội dung `myapp-actions.pub` thành một dòng có tiền tố giới hạn:

```bash
sudoedit -u deploy /srv/myapp/.ssh/authorized_keys
sudo chmod 600 /srv/myapp/.ssh/authorized_keys
```

```text
command="/usr/local/bin/deploy-myapp",restrict ssh-ed25519 AAAA… github-actions-myapp
```

`command=` buộc mọi kết nối bằng khóa này chạy lệnh triển khai, chữ client gửi chỉ được dùng làm commit SHA; `restrict` tắt terminal, chuyển tiếp cổng và agent. Khóa lộ ra cũng chỉ triển khai được commit đã có trên `main`. Cú pháp đầy đủ trong mục AUTHORIZED_KEYS FILE FORMAT của [sshd(8)](https://man.openbsd.org/sshd.8).

Lấy khóa máy chủ của VPS cho `known_hosts` từ máy quản trị và đối chiếu dấu vân tay với VPS:

```bash
# Trên máy quản trị; cổng khác 22 thì thêm -p <cổng>.
ssh-keyscan -t ed25519 203.0.113.10 > myapp-known-hosts
ssh-keygen -lf myapp-known-hosts
# Trên VPS: dấu vân tay phải trùng với dòng trên.
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Kiểm tra khóa: kết nối không kèm SHA phải bị từ chối với thông báo `Cần commit SHA đầy đủ 40 ký tự`, không mở được shell:

```bash
ssh -i ./myapp-actions deploy@203.0.113.10
```

Sau khi lưu vào GitHub Secrets ở bước tiếp theo, xóa `myapp-actions` và `myapp-known-hosts` khỏi máy quản trị.

## ⚙️ CẤU HÌNH REPOSITORY TRÊN GITHUB

Trong **Settings → Environments → New environment** của repository đích, tạo environment `production` theo [hướng dẫn environment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments):

- **Deployment branches and tags:** chọn **Selected branches and tags**, thêm `main`.
- **Required reviewers** (tùy chọn): người được chỉ định bấm **Approve and deploy** trước khi job chạy; bỏ trống để triển khai ngay khi hợp nhất.
- **Environment secrets:**

| Secret            | Giá trị                                                          |
| ----------------- | ---------------------------------------------------------------- |
| `VPS_HOST`        | IP hoặc tên miền SSH của VPS, ví dụ `203.0.113.10`               |
| `VPS_PORT`        | Cổng SSH; bỏ trống thì dùng `22`                                 |
| `VPS_USER`        | `deploy`                                                         |
| `VPS_SSH_KEY`     | Toàn bộ nội dung khóa riêng `myapp-actions`, kể cả dòng đầu/cuối |
| `VPS_KNOWN_HOSTS` | Nội dung `myapp-known-hosts` đã đối chiếu dấu vân tay            |

Environment cùng chính sách branch có thể quản lý trong nguồn cài đặt theo [hướng dẫn cài đặt GitHub](github-settings.md); giá trị secrets luôn tạo trên GitHub, không lưu trong nguồn. Secrets của environment chỉ cấp cho job khai báo `environment: production` và chạy trên `main`; cách quản lý xem [hướng dẫn secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

## 🔁 WORKFLOW TỰ ĐỘNG TRIỂN KHAI

Thêm hai tệp vào repository đích qua một Pull Request (ví dụ branch `ci/add_vps_deploy`, commit `ci(deploy): triển khai lên VPS khi hợp nhất vào main`).

Tệp `deploy.yml` trong `.github/workflows/`:

```yaml
name: Deploy

on:
    push:
        branches:
            - main
    workflow_dispatch:
        inputs:
            sha:
                description: Commit SHA đầy đủ trên main cần triển khai lại; bỏ trống để dùng commit mới nhất
                required: false
                type: string

permissions:
    contents: read

concurrency:
    # Các lượt triển khai xếp hàng, không hủy lượt đang chạy giữa chừng.
    group: deploy-production
    cancel-in-progress: false

jobs:
    deploy:
        name: Triển khai lên VPS
        if: github.ref == 'refs/heads/main'
        runs-on: ubuntu-latest
        timeout-minutes: 20
        environment: production
        steps:
            - name: Checkout
              uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
              with:
                  persist-credentials: false

            - name: Triển khai
              env:
                  DEPLOY_SHA: ${{ inputs.sha || github.sha }}
                  VPS_HOST: ${{ secrets.VPS_HOST }}
                  VPS_PORT: ${{ secrets.VPS_PORT }}
                  VPS_USER: ${{ secrets.VPS_USER }}
                  VPS_SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
                  VPS_KNOWN_HOSTS: ${{ secrets.VPS_KNOWN_HOSTS }}
              run: python3 scripts/deploy.py
```

Workflow theo quy ước của tổ chức: action ghim commit SHA đầy đủ (SHA mới lấy bằng `git ls-remote`, Dependabot đề xuất cập nhật), quyền tối thiểu, mỗi bước một lệnh, giá trị `${{ … }}` truyền qua `env:`. Khi một lượt đang chạy, GitHub giữ tối đa một lượt chờ trong nhóm `concurrency`; lượt chờ cũ bị thay bằng lượt mới nhất.

Tệp `deploy.py` trong `scripts/` dùng `python3` có sẵn của runner, chỉ thư viện chuẩn:

```python
"""Triển khai commit lên VPS qua SSH; khóa chỉ được chạy lệnh triển khai trên VPS (forced command)."""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
	sha = os.environ['DEPLOY_SHA']
	if not re.fullmatch(r'[0-9a-f]{40}', sha):
		sys.exit(f'DEPLOY_SHA phải là commit SHA đầy đủ 40 ký tự: {sha!r}')
	host = os.environ['VPS_HOST']
	user = os.environ['VPS_USER']
	port = os.environ.get('VPS_PORT') or '22'
	with tempfile.TemporaryDirectory() as folder:
		keyPath = Path(folder) / 'id_ed25519'
		knownHostsPath = Path(folder) / 'known_hosts'
		# ssh từ chối khóa riêng mà người khác đọc được.
		keyPath.touch(mode=0o600)
		keyPath.write_text(os.environ['VPS_SSH_KEY'].strip() + '\n')
		knownHostsPath.write_text(os.environ['VPS_KNOWN_HOSTS'].strip() + '\n')
		options = {
			'BatchMode': 'yes',
			'IdentitiesOnly': 'yes',
			'StrictHostKeyChecking': 'yes',
			'UserKnownHostsFile': str(knownHostsPath),
			'ServerAliveInterval': '30',
		}
		command = ['ssh', '-i', str(keyPath), '-p', port]
		for name, value in options.items():
			command += ['-o', f'{name}={value}']
		command += [f'{user}@{host}', sha]
		sys.exit(subprocess.run(command, check=False).returncode)


if __name__ == '__main__':
	main()
```

`StrictHostKeyChecking=yes` cùng `known_hosts` đã đối chiếu chặn kết nối tới máy chủ giả mạo. Lệnh triển khai trên VPS in tiến trình vào log của job và trả mã lỗi khi build hoặc kiểm tra sức khỏe thất bại, nên job đỏ đồng nghĩa phiên bản mới không được giữ lại.

## ✅ KIỂM CHỨNG

1. Hợp nhất Pull Request chứa workflow; tab **Actions** hiện lượt chạy **Deploy** trên `main`.
2. Lượt chạy kết thúc thành công, trang **Deployments** của repository ghi nhận environment `production` với commit vừa hợp nhất.
3. Trên VPS, `cat /srv/myapp/current/REVISION` in đúng commit đó; `curl -fsS https://myapp.example.com/health` trả `200`.
4. Mở và hợp nhất một Pull Request nhỏ tiếp theo để xác nhận triển khai tự động lặp lại.

## ↩️ QUAY LẠI PHIÊN BẢN TRƯỚC

- **Revert qua Pull Request (khuyến nghị):** tạo Pull Request `revert` cho thay đổi lỗi và hợp nhất; workflow tự triển khai, `main` luôn trùng mã đang chạy.
- **Chạy lại commit cũ:** tab **Actions → Deploy → Run workflow**, chọn `main`, nhập commit SHA đầy đủ đã có trên `main`. Lượt tự động kế tiếp sẽ triển khai lại commit mới nhất của `main`.
- **Khẩn cấp trên VPS:** khi GitHub Actions không dùng được, chọn phiên bản trong `ls /srv/myapp/releases` rồi chuyển symlink:

```bash
sudo -u deploy ln -sfn /srv/myapp/releases/<phiên bản> /srv/myapp/current.next
sudo -u deploy mv -T /srv/myapp/current.next /srv/myapp/current
sudo systemctl restart myapp.service
```

## 🩺 XỬ LÝ SỰ CỐ

| Hiện tượng                                            | Nguyên nhân và cách xử lý                                                                                                         |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Hợp nhất xong nhưng workflow không chạy               | Actions bị tắt hoặc workflow chưa có trên `main`; xem [workflow chờ runner](local-checks.md#-workflow-chờ-runner) khi job chờ mãi |
| Job dừng ở **Waiting for review**                     | Environment bật **Required reviewers**; người được chỉ định phê duyệt trong lượt chạy                                             |
| `Host key verification failed`                        | `VPS_KNOWN_HOSTS` sai, thiếu hoặc lấy sai cổng; quét lại bằng `ssh-keyscan` và đối chiếu dấu vân tay                              |
| `Permission denied (publickey)`                       | Khóa không khớp `authorized_keys`, hoặc thư mục `.ssh` và tệp có quyền rộng hơn `700`/`600`; xem `sudo journalctl -u ssh`         |
| `Commit … không thuộc nhánh main`                     | SHA nhập tay lấy từ branch khác hoặc chưa được đẩy lên `main`                                                                     |
| `sudo: a password is required`                        | Lệnh trong `/etc/sudoers.d/myapp-deploy` khác lệnh trong `deploy-myapp`; kiểm tra bằng `sudo -l -U deploy`                        |
| `Phiên bản … không đạt kiểm tra sức khỏe`             | Ứng dụng không khởi động hoặc `/health` lỗi; phiên bản trước đã được khôi phục, xem `sudo journalctl -u myapp.service -n 200`     |
| `npm`, `node` hoặc `python3` không tìm thấy khi build | Runtime cài theo người dùng, không có trong `PATH` của lệnh triển khai; cài ở phạm vi hệ thống hoặc khai báo `PATH` ở đầu lệnh    |

## 🔐 BẢO MẬT

- Khóa của GitHub Actions chỉ chạy được `deploy-myapp` và chỉ triển khai commit thuộc `main`; deploy key của VPS chỉ đọc một repository.
- Mã chạy trên VPS là mã đã qua review và status checks của Protect Main. Giữ ruleset bật; người trong danh sách bỏ qua đẩy thẳng lên `main` cũng triển khai lên VPS.
- Secrets nằm trong environment `production` giới hạn nhánh `main`; Pull Request và branch khác không đọc được.
- Thay khóa khi người có quyền quản trị rời dự án hoặc nghi lộ: tạo khóa mới, cập nhật `VPS_SSH_KEY`, xóa dòng cũ trong `authorized_keys`; thay deploy key tương tự trong **Settings → Deploy keys**.
- Không commit `.env`, địa chỉ máy chủ, khóa hay log có dữ liệu người dùng; báo lỗ hổng theo [SECURITY.md](../SECURITY.md).

## 📚 TÀI LIỆU THAM KHẢO

- [Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
- [Using secrets in GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [Control the concurrency of workflows and jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [Managing deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)
- [systemd.service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [Certbot instructions](https://certbot.eff.org/instructions)
