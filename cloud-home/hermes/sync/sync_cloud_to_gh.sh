#!/usr/bin/env bash
# Hermes 云→GitHub 智能同步 (优化版)
# 推: 核心知识 (Obsidian 提炼) + 配置 + 记忆 + sessions
# 不传: 临时数据 / 缓存 / 凭证 / 临时 daily / 队列
# 用法: sync_cloud_to_gh.sh [--dry-run]
set -e

DRY_RUN="false"
[ "${1}" = "--dry-run" ] && DRY_RUN="true"

USER_HERMES="/c/Users/Administrator/.hermes"
REPO_DIR="${USER_HERMES}/github-mirror/atest"
REPO_URL="git@github.com:shishenshashen/atest.git"
BRANCH="main"
HERMES_HOME="/c/Users/Administrator/AppData/Roaming/cn.org.hermesagent.desktop/runtime/hermes-home"

cd "${REPO_DIR}"
git config user.name "OrientWan"
git config user.email "shishenshashen@users.noreply.github.com"

# 1. ~/.hermes (业务脚本/数据)
echo "[1/5] ~/.hermes/ (业务)"
if [ "${DRY_RUN}" = "false" ]; then
    python "${USER_HERMES}/sync/_hermes_rsync.py" \
        --src "${USER_HERMES}/" \
        --dst "${REPO_DIR}/cloud-home/hermes/" 2>&1 | tail -1
fi

# 2. hermes-home (config + memories, 过滤大缓存)
echo "[2/5] hermes-home (config + memories)"
if [ "${DRY_RUN}" = "false" ]; then
    python "${USER_HERMES}/sync/_cloud_rsync.py" \
        --src "${HERMES_HOME}" \
        --dst "${REPO_DIR}/cloud-home/hermes-home/" 2>&1 | tail -1
fi

# 3. state.db 单独 gzip
echo "[3/5] state.db -> state.db.gz"
if [ "${DRY_RUN}" = "false" ]; then
    python "${USER_HERMES}/sync/_state_db_pack.py" \
        "${HERMES_HOME}/state.db" \
        "${REPO_DIR}/cloud-home/hermes-home/state.db.gz" 2>&1 | tail -1
    rm -f "${REPO_DIR}/cloud-home/hermes-home/state.db" \
          "${REPO_DIR}/cloud-home/hermes-home/state.db-shm" \
          "${REPO_DIR}/cloud-home/hermes-home/state.db-wal"
fi

# 4. Obsidian vault 智能过滤 (核心知识)
echo "[4/5] Obsidian vault (核心: EA开发 + 提炼 + 索引)"
if [ "${DRY_RUN}" = "false" ]; then
    python "${USER_HERMES}/sync/_vault_filter.py" \
        "/c/ai/obsidian-文件" \
        "${REPO_DIR}/cloud-vault/" 2>&1 | tail -1
fi

# 5. .claude / .config / cu-mcp / .bashrc.d (小)
echo "[5/5] ~/.claude ~/.config ~/cu-mcp ~/.bashrc.d"
if [ "${DRY_RUN}" = "false" ]; then
    for src in .claude .config .bashrc.d; do
        if [ -d "${USER_HERMES}/../${src}" ]; then
            python "${USER_HERMES}/sync/_hermes_rsync.py" \
                --src "/c/Users/Administrator/${src}/" \
                --dst "${REPO_DIR}/cloud-home/${src}/" 2>&1 | tail -1
        fi
    done
    if [ -d "/c/Users/Administrator/cu-mcp" ]; then
        python "${USER_HERMES}/sync/_hermes_rsync.py" \
            --src "/c/Users/Administrator/cu-mcp/" \
            --dst "${REPO_DIR}/cloud-home/cu-mcp/" 2>&1 | tail -1
    fi
fi

# commit + push
echo "[push] git add + commit + push"
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
