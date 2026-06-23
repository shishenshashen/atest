#!/usr/bin/env bash
# Hermes 云→GitHub 全量同步
# 推: ~/.hermes + hermes-home + C:/ai + obsidian + .claude + .config + cu-mcp + .bashrc.d
# 状态: state.db (gzip 压缩 51M->~23M)
# 不传: .ssh (凭证) / .env / 大缓存 (lsp/skills/node_modules)
# 用法: sync_cloud_to_gh.sh [--dry-run]
set -e

DRY_RUN="false"
[ "${1}" = "--dry-run" ] && DRY_RUN="true"

USER_HERMES="/c/Users/Administrator/.hermes"
REPO_DIR="${USER_HERMES}/github-mirror/atest"
REPO_URL="git@github.com:shishenshashen/atest.git"
BRANCH="main"

cd "${REPO_DIR}"
git config user.name "OrientWan"
git config user.email "shishenshashen@users.noreply.github.com"

# 1. 全量同步 (8 块)
echo "[1/3] all-sync (~/.hermes + hermes-home + C:/ai + obsidian + .claude + .config + cu-mcp + .bashrc.d)"
if [ "${DRY_RUN}" = "false" ]; then
    python "${USER_HERMES}/sync/_all_sync.py" --dst "${REPO_DIR}/cloud-all"
else
    echo "(dry-run, skip)"
fi

# 2. state.db 单独 gzip
echo "[2/3] state.db -> state.db.gz"
if [ "${DRY_RUN}" = "false" ]; then
    HERMES_HOME="/c/Users/Administrator/AppData/Roaming/cn.org.hermesagent.desktop/runtime/hermes-home"
    python "${USER_HERMES}/sync/_state_db_pack.py" \
        "${HERMES_HOME}/state.db" \
        "${REPO_DIR}/cloud-all/hermes-home/state.db.gz" 2>&1 | tail -3
    # 删仓内裸 state.db
    rm -f "${REPO_DIR}/cloud-all/hermes-home/state.db" \
          "${REPO_DIR}/cloud-all/hermes-home/state.db-shm" \
          "${REPO_DIR}/cloud-all/hermes-home/state.db-wal"
fi

# 3. git add + commit + push
echo "[3/3] git add + commit + push"
git add -A
if git diff --cached --quiet; then
    echo "[no-changes]"
    exit 0
fi
STAT=$(git diff --cached --stat | tail -1 | tr -s ' ')
MSG="cloud-sync: $(date +%Y-%m-%dT%H:%M:%S) ${STAT}"
git commit -m "${MSG}" 2>&1 | tail -3
git push origin "${BRANCH}" 2>&1 | tail -5
COMMIT=$(git rev-parse HEAD)
echo "[done] ${COMMIT}"
echo "[verify] https://github.com/shishenshashen/atest/commit/${COMMIT}"
