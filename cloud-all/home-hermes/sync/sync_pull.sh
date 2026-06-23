#!/usr/bin/env bash
# sync_pull.sh - 从 GitHub hermes-sync 仓 拉到 ~/.hermes/
# 默认 dry-run (只看不写), --apply 才真覆盖
# 用法: ./sync_pull.sh [--apply]
set -e

HERMES="${HOME}/.hermes"
REPO_DIR="${HERMES}/github-mirror/atest"
REPO_URL="git@github.com:shishenshashen/atest.git"
BRANCH="main"
APPLY="false"
[ "${1}" = "--apply" ] && APPLY="true"

# 1. clone (if not exist)
if [ ! -d "${REPO_DIR}/.git" ]; then
    mkdir -p "${REPO_DIR}"
    echo "[init] cloning ${REPO_URL}..."
    git clone "${REPO_URL}" "${REPO_DIR}" 2>&1
fi

cd "${REPO_DIR}"

# 2. fetch + reset
echo "[fetch] origin/${BRANCH}..."
git fetch --depth 50 origin "${BRANCH}" 2>&1
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/${BRANCH}")
echo "[local]  ${LOCAL}"
echo "[remote] ${REMOTE}"

if [ "${LOCAL}" = "${REMOTE}" ]; then
    echo "[in-sync] no new commits"
    exit 0
fi

# 3. 看改动
echo "[diff] commits ahead/behind:"
git log --oneline "${LOCAL}..${REMOTE}" 2>&1 | head -20

# 4. dry-run 检冲突
echo ""
echo "[dry-run] what would change in ~/.hermes/:"
# 用 rsync --dry-run 模拟
if [ "${APPLY}" = "true" ]; then
    rsync -a --delete --dry-run \
        --exclude='.git/' \
        --exclude='.ssh/' \
        --exclude='__pycache__/' \
        --exclude='.mavis*' \
        "${REPO_DIR}/hermes/" "${HERMES}/" 2>&1 | head -30
    echo ""
    read -p "[apply? type YES to write to ~/.hermes] " CONFIRM
    if [ "${CONFIRM}" != "YES" ]; then
        echo "[abort] not applied"
        exit 0
    fi
    rsync -a --delete \
        --exclude='.git/' \
        --exclude='.ssh/' \
        --exclude='__pycache__/' \
        --exclude='.mavis*' \
        "${REPO_DIR}/hermes/" "${HERMES}/" 2>&1
    git reset --hard "origin/${BRANCH}" 2>&1
    echo "[done] applied ${REMOTE}"
else
    echo "(pass --apply to actually write)"
fi
