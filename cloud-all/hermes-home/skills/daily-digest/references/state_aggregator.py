# -*- coding: utf-8 -*-
"""daily-digest skill · state aggregator
扫 state.db / vault / mem0，返回指定时间范围的活动数据。
"""
import sqlite3
import os
import json
import re
from datetime import datetime, timedelta
from collections import Counter

APPDATA = os.environ.get("APPDATA") or r"C:\Users\Administrator\AppData\Roaming"
HERMES_HOME = os.path.join(APPDATA, "cn.org.hermesagent.desktop", "runtime", "hermes-home")
STATE_DB = os.path.join(HERMES_HOME, "state.db")
SESSIONS_JSON = os.path.join(HERMES_HOME, "sessions", "sessions.json")

VAULT_PATH = os.environ.get("OBSIDIAN_VAULT_PATH") or r"C:\ai\obsidian-文件\ai-managed"
REFLECTIONS_DIR = os.path.join(VAULT_PATH, "20-经验沉淀")

# 主题关键词 -> 主题分类
TOPIC_RULES = [
    (["mt5", "mql5", "mql", "ea", "metatrader", "expert advisor", "forex", "外汇", "xauusd", "黄金"], "MT5/EA"),
    (["股票", "stock", "equity", "期货", "futures", "回测", "策略", "signal"], "量化交易"),
    (["python", "rust", "golang", "javascript", "typescript", "代码", "programming", "函数", "class", "import"], "编程技巧"),
    (["obsidian", "notion", "logseq", "笔记", "vault", "moc", "wikilink"], "知识管理"),
    (["ai", "llm", "gpt", "claude", "模型", "agent", "mcp", "gpt-5", "mem0", "hermes"], "AI工具"),
    (["hermes", "hermes-agent", "minimax", "mavis", "minimaxcode"], "Hermes生态"),
    (["obsidian"], "知识管理"),
    (["windows", "msys", "bash", "powershell", "python", "pip", "uv", "cmd", "终端"], "本机环境"),
    (["微信", "weixin", "feishu", "飞书", "telegram", "slack", "whatsapp"], "消息平台"),
    (["盘", "disk", "c盘", "c drive", "storage", "清理", "释放"], "磁盘管理"),
    (["github", "git", "ssh", "ssh-key", "commit", "push", "merge"], "Git"),
    (["docker", "compose", "容器", "container", "kubernetes", "k8s"], "容器"),
    (["openai", "anthropic", "minimax", "minimaxi", "api key", "token", "model"], "LLM API"),
]

# 关键决定信号（粗略）
QUOTE_SIGNALS = ["以后", "记住", "记得", "要", "要改", "改成", "改成", "别", "不要",
                 "再", "继续", "坚持", "必须", "应该", "我要", "你先", "帮我",
                 "你看", "我觉得", "我觉得", "配置", "改成", "改到"]


def aggregate_range(start_dt, end_dt, label=""):
    """Aggregate activity in a time range."""
    if not os.path.exists(STATE_DB):
        return None
    db = sqlite3.connect(STATE_DB)
    c = db.cursor()

    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp()

    # Sessions in range
    c.execute("""
        SELECT DISTINCT session_id FROM messages
        WHERE timestamp >= ? AND timestamp < ?
    """, (start_ts, end_ts))
    sids = [r[0] for r in c.fetchall()]

    # Session platforms
    session_meta = {}
    if os.path.exists(SESSIONS_JSON):
        with open(SESSIONS_JSON, "r", encoding="utf-8") as f:
            sessions = json.load(f)
        for k, v in sessions.items():
            sid = v.get("session_id")
            if sid in sids:
                session_meta[sid] = v.get("origin", {}).get("platform", "unknown")
    # Fallback: any session_id not in sessions.json is "desktop"
    for sid in sids:
        if sid not in session_meta:
            session_meta[sid] = "desktop"

    # Counts by role
    c.execute("""
        SELECT role, COUNT(*) FROM messages
        WHERE timestamp >= ? AND timestamp < ?
        GROUP BY role
    """, (start_ts, end_ts))
    role_counts = {r[0]: r[1] for r in c.fetchall()}

    # User messages for analysis
    c.execute("""
        SELECT content FROM messages
        WHERE timestamp >= ? AND timestamp < ?
          AND role = 'user' AND content IS NOT NULL AND content != ''
    """, (start_ts, end_ts))
    user_msgs = [r[0] for r in c.fetchall()]

    # Topic classification
    topic_ctr = Counter()
    for m in user_msgs:
        m_low = m.lower()
        for kws, topic in TOPIC_RULES:
            if any(kw in m_low for kw in kws):
                topic_ctr[topic] += 1

    # Quote detection (high-signal user messages)
    quotes = []
    for m in user_msgs:
        m_clean = m.strip()
        if len(m_clean) < 8 or len(m_clean) > 120:
            continue
        if any(sig in m_clean for sig in QUOTE_SIGNALS):
            quotes.append(m_clean)

    # URLs found
    urls = []
    url_pat = re.compile(r"https?://[^\s]+")
    for m in user_msgs:
        urls.extend(url_pat.findall(m))

    db.close()

    return {
        "label": label,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "sessions": [{"id": sid, "platform": session_meta.get(sid, "?")} for sid in sids],
        "role_counts": role_counts,
        "topics": topic_ctr.most_common(15),
        "quotes": quotes[:8],  # top 8
        "urls": list(set(urls))[:10],
    }


def aggregate_today():
    now = datetime.now()
    start = datetime(now.year, now.month, now.day)
    end = start + timedelta(days=1)
    return aggregate_range(start, end, label=f"Daily {start.date()}")


def aggregate_week(week_start_dt):
    end = week_start_dt + timedelta(days=7)
    return aggregate_range(week_start_dt, end, label=f"Week of {week_start_dt.date()}")


def aggregate_month(year, month):
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return aggregate_range(start, end, label=f"Month {year}-{month:02d}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "today":
        data = aggregate_today()
    elif len(sys.argv) > 2 and sys.argv[1] == "month":
        data = aggregate_month(int(sys.argv[2]), int(sys.argv[3]))
    else:
        data = aggregate_today()
    print(json.dumps(data, indent=2, ensure_ascii=False))
