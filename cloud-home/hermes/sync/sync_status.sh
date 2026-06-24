#!/usr/bin/env bash
# sync_status.sh - 看本地 vs GitHub hermes-sync 仓 差几条 commit
# 用法: ./sync_status.sh
set -e

HERMES="${HOME}/.hermes"
REPO_DIR="${HERMES}/github-mirror/atest"
REPO_URL="git@github.com:shishenshashen/atest.git"
BRANCH="main"

if [ ! -d "${REPO_DIR}/.git" ]; then
    echo "[no-repo] ${REPO_DIR} doesn't exist. Run sync_push.sh first to init."
    exit 1
fi

cd "${REPO_DIR}"
echo "[fetch] origin/${BRANCH}..."
git fetch --depth 50 origin "${BRANCH}" 2>&1
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/${BRANCH}")
echo "[local]  ${LOCAL:0:12}  $(git log -1 --pretty=format:'%ai %s' HEAD)"
echo "[remote] ${REMOTE:0:12}  $(git log -1 --pretty=format:'%ai %s' origin/${BRANCH})"
echo ""

AHEAD=$(git rev-list --count "${REMOTE}..${LOCAL}" 2>/dev/null || echo 0)
BEHIND=$(git rev-list --count "${LOCAL}..${REMOTE}" 2>/dev/null || echo 0)
echo "ahead (local 有 remote 没): ${AHEAD}"
echo "behind (remote 有 local 没): ${BEHIND}"

if [ "${AHEAD}" -gt 0 ]; then
    echo ""
    echo "[local-only commits] (need push):"
    git log --oneline "${REMOTE}..${LOCAL}" | head -10
fi
if [ "${BEHIND}" -gt 0 ]; then
    echo ""
    echo "[remote-only commits] (need pull):"
    git log --oneline "${LOCAL}..${REMOTE}" | head -10
fi
