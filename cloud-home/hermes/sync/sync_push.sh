#!/usr/bin/env bash
# sync_push.sh - 推 ~/.hermes/ 到 GitHub hermes-sync 仓
# 不传凭证, 不传 ~/.ssh/, 不传 ~/.mavis/ (P3 铁律)
# 跨平台: Git Bash / Linux bash / macOS zsh
# 用法: ./sync_push.sh [message]
set -e

HERMES="${HOME}/.hermes"
REPO_DIR="${HERMES}/github-mirror/atest"
REPO_URL="git@github.com:shishenshashen/atest.git"
BRANCH="main"

# 1. 准备本地仓
if [ ! -d "${REPO_DIR}/.git" ]; then
    mkdir -p "${REPO_DIR}"
    echo "[init] cloning ${REPO_URL}..."
    git clone "${REPO_URL}" "${REPO_DIR}" 2>&1
else
    echo "[fetch] updating from origin/${BRANCH}..."
    cd "${REPO_DIR}"
    git fetch --depth 50 origin "${BRANCH}" 2>&1 || true
    git reset --hard "origin/${BRANCH}" 2>&1 || true
fi

cd "${REPO_DIR}"

# 2. 设 identity (per-repo, 不污染全局)
git config user.name "OrientWan"
git config user.email "shishenshashen@users.noreply.github.com"

# 3. 同步 ~/.hermes/ 关键目录 到 仓内
# 不传: .ssh/ 凭证, .git/ 已 clone 的镜像仓, __pycache__/, *.pyc, *~
# Windows Git Bash 无 rsync, 用 Python 替代
echo "[rsync] copying ~/.hermes/ to repo..."
python "${HERMES}/sync/_hermes_rsync.py" \
    --src "${HERMES}/" \
    --dst "${REPO_DIR}/hermes/"

# 4. 加 gitignore (保险: 万一 rsync 漏过)
cat > "${REPO_DIR}/.gitignore" <<'EOF'
# 凭证 & 隐私
*.key
*.pem
.ssh/
.mavis*
.minimax*
.mm-x-agent*
@mmx-agentelectron-updater*

# 临时
__pycache__/
*.pyc
*.pyo
*~
*.tmp
*.log.gz
.DS_Store
Thumbs.db

# 大仓库内部 .git
github-mirror/*/.git/
hermes-agent/.git/

# 虚拟环境
.venv/
venv/
node_modules/
EOF

# 5. 检 status
echo "[status] git status:"
git status --short 2>&1 | head -20

# 6. commit + push
MSG="${1:-sync: $(date +%Y-%m-%dT%H:%M:%S)}"
git add -A
if git diff --cached --quiet; then
    echo "[no-changes] nothing to commit"
    exit 0
fi
git commit -m "${MSG}" 2>&1
echo "[push] origin ${BRANCH}..."
git push origin "${BRANCH}" 2>&1

# 7. 验
COMMIT=$(git rev-parse HEAD)
echo "[done] ${COMMIT}"
echo "[verify] https://github.com/shishenshashen/hermes-sync/commit/${COMMIT}"
