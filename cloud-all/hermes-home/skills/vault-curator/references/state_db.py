# -*- coding: utf-8 -*-
"""vault-curator skill · state_db 工具函数
用于自动监控微信/飞书 DM session 并归档到 ai-managed vault。
"""
import sqlite3
import os
import json
from datetime import datetime

# 路径配置
APPDATA = os.environ.get("APPDATA") or r"C:\Users\Administrator\AppData\Roaming"
HERMES_HOME = os.path.join(APPDATA, "cn.org.hermesagent.desktop", "runtime", "hermes-home")
STATE_DB = os.path.join(HERMES_HOME, "state.db")
SESSIONS_JSON = os.path.join(HERMES_HOME, "sessions", "sessions.json")

VAULT_PATH = os.environ.get("OBSIDIAN_VAULT_PATH") or r"C:\ai\obsidian-文件\ai-managed"
ARCHIVE_STATE = os.path.join(VAULT_PATH, "90-索引", "_archive_state.json")


def find_unarchived_sessions():
    """Find DM sessions (weixin/feishu/telegram) with URLs not yet archived."""
    if not os.path.exists(SESSIONS_JSON):
        return []
    if not os.path.exists(STATE_DB):
        return []

    with open(SESSIONS_JSON, "r", encoding="utf-8") as f:
        sessions = json.load(f)

    archive_state = {"archived_sessions": {}}
    if os.path.exists(ARCHIVE_STATE):
        try:
            with open(ARCHIVE_STATE, "r", encoding="utf-8") as f:
                archive_state = json.load(f)
        except Exception:
            pass

    candidates = []
    for key, s in sessions.items():
        platform = s.get("origin", {}).get("platform", "")
        if platform not in ("weixin", "feishu", "telegram", "whatsapp", "slack"):
            continue
        sid = s.get("session_id")
        if not sid:
            continue
        if sid in archive_state.get("archived_sessions", {}):
            continue
        # Has URL in user messages?
        try:
            db = sqlite3.connect(STATE_DB)
            c = db.cursor()
            c.execute(
                "SELECT content, timestamp FROM messages "
                "WHERE session_id = ? AND role = 'user' AND content LIKE '%https%' "
                "ORDER BY id LIMIT 5",
                (sid,),
            )
            urls = [{"content": r[0], "timestamp": r[1]} for r in c.fetchall()]
            db.close()
        except Exception:
            urls = []
        if urls:
            candidates.append({
                "session_id": sid,
                "platform": platform,
                "updated_at": s.get("updated_at"),
                "urls": urls,
            })
    return candidates


def get_session_full_transcript(session_id):
    """Get full transcript of a session for analysis."""
    if not os.path.exists(STATE_DB):
        return []
    db = sqlite3.connect(STATE_DB)
    c = db.cursor()
    c.execute(
        "SELECT id, role, content, timestamp FROM messages "
        "WHERE session_id = ? ORDER BY id",
        (session_id,),
    )
    rows = c.fetchall()
    db.close()
    return [
        {"id": r[0], "role": r[1], "content": r[2], "timestamp": r[3]}
        for r in rows
    ]


def mark_archived(session_id, platform, files):
    """Mark a session as archived."""
    archive_state = {"archived_sessions": {}}
    if os.path.exists(ARCHIVE_STATE):
        try:
            with open(ARCHIVE_STATE, "r", encoding="utf-8") as f:
                archive_state = json.load(f)
        except Exception:
            pass
    archive_state.setdefault("archived_sessions", {})[session_id] = {
        "platform": platform,
        "archived_at": datetime.now().isoformat(),
        "files_created": files,
    }
    os.makedirs(os.path.dirname(ARCHIVE_STATE), exist_ok=True)
    with open(ARCHIVE_STATE, "w", encoding="utf-8") as f:
        json.dump(archive_state, f, indent=2, ensure_ascii=False)


def decide_archive_target(url, content=""):
    """Decide which 10-提炼/ subfolder to archive to based on URL/content keywords."""
    text = (url + " " + content).lower()
    rules = [
        (["mt5", "mql5", "mql", "ea", "metatrader", "expert advisor", "forex", "外汇", "量化"], "EA开发"),
        (["股票", "stock", "equity", "期货", "futures"], "量化交易"),
        (["python", "rust", "golang", "javascript", "typescript", "代码", "programming"], "编程技巧"),
        (["obsidian", "notion", "logseq", "笔记"], "工具"),
        (["ai", "llm", "gpt", "claude", "模型", "agent", "mcp"], "AI与自动化"),
        (["claude code", "codex", "opencode", "hermes"], "AI与自动化"),
    ]
    for keywords, target in rules:
        if any(kw in text for kw in keywords):
            return target
    return "其他"


if __name__ == "__main__":
    # Quick test
    print("=== Test: find unarchived sessions ===")
    cands = find_unarchived_sessions()
    for c in cands:
        print(f"  [{c['platform']}] {c['session_id']} (updated {c['updated_at']})")
        for u in c["urls"]:
            print(f"    URL: {u['content'][:80]}")
