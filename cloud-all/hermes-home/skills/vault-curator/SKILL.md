---
name: vault-curator
description: >
  AI-maintained Obsidian vault workflow with auto-monitoring. Trigger when
  user wants to: process clipped materials in 00-Inbox/, write reflections,
  maintain MOC index, OR when a new weixin/feishu/Telegram session is detected
  with link-sharing content. Auto-archives DM-received articles/links to
  10-提炼/ + writes skill references + updates MOC.
license: MIT
metadata:
  author: 小神龙
  version: "2.0.0"
  category: productivity
  tags: "obsidian, vault, curation, knowledge-management, wechat, weixin, feishu, auto-monitor"
platforms: [linux, macos, windows]
---

# Vault Curator v2 · AI 维护 Obsidian vault（带自动监控）

> **AI 主动维护** 的 vault 叫 `ai-managed`，路径是 `$OBSIDIAN_VAULT_PATH`
> （老大环境里设的是 `C:\ai\obsidian-文件\ai-managed`）。
> 老大的主 vault `mt/` **永远只读**。

## 🆕 v2 升级（2026-06-10）

加了**自动监控**：新会话开始时，AI 主动检查**上一次有未归档的微信/飞书 session**。
如果发现用户消息含 URL 还没归档到 vault，**自动触发**归档工作流。

---

## Vault 目录结构

```
$OBSIDIAN_VAULT_PATH/
├── 00-Inbox/          # 老大剪藏的原材料
├── 10-提炼/           # AI 提炼后的成品（按主题分子目录）
│   ├── EA开发/
│   ├── 量化交易/
│   ├── 编程技巧/
│   ├── 工具/
│   ├── AI与自动化/
│   └── 其他/
├── 20-经验沉淀/       # 经验/教训（按月归档）
│   └── YYYY-MM/
├── 30-技能档案/       # 内部 skill / 外源 skill / 命令速查
├── 40-项目档案/       # 项目档案
├── 90-索引/           # MOC 主入口
├── 98-已处理/         # AI 处理完的原始剪藏
└── 99-临时/           # AI 临时草稿
```

---

## 🆕 工作流 0：自动监控（每次会话开始）

**触发**：新会话开始（Hermes Desktop 启动 / 用户开新 chat）

**步骤**：

1. **检查上次未归档的 session**
   - 查 `~/.hermes/sessions/sessions.json`，找 `platform: weixin / feishu / telegram` 的 session
   - 比对上次更新时间和上次**已知**归档状态
   - **新发现的** → 进入工作流 1

2. **识别"含链接"的用户消息**
   - 在 `state.db` 的 `messages` 表查
   - `role=user` 且 `content` 匹配 `https?://`
   - 把候选 URL 列表展示给老大

3. **询问老大**（避免误触发）：
   > "检测到您上次微信/飞书 DM 有 N 条链接未归档到 vault：
   > 1. https://xxx (whichllm)
   > 2. https://yyy
   > 是否自动归档到 10-提炼/？"

4. **老大确认** → 走工作流 1

---

## 工作流 1：处理 00-Inbox/ 的新材料

1. 列 `00-Inbox/` 下 `.md`
2. 每个文件：
   a. `read_file` 读
   b. 理解主题
   c. 决定归档目标
   d. `write_file` 写新文件到目标目录
      - 文件名：`YYYY-MM-DD_<主题>.md`
      - frontmatter 必填
   e. 内容含：来源、原文要点、AI 提炼、wikilink
   f. `terminal` 移原文件到 `98-已处理/`
3. 更新 `90-索引/MOC.md`

## 工作流 2：写经验沉淀

写到 `20-经验沉淀/<本月>/YYYY-MM-DD_<主题>.md`

结构：
```markdown
---
title, tags, type=reflection, date
---
# 主题
## 📌 背景
## 🛠️ 做了什么
## 💡 学到什么
## ⚠️ 坑点
## 🔗 相关
```

## 工作流 3：写技能档案

写到 `30-技能档案/<子目录>/<技能名>.md`
含：用途、用法、示例、坑点、相关链向

## 工作流 4：维护 MOC

`90-索引/MOC.md` AI 自动维护的主入口。

---

## 🆕 工作流 5：自动归档 DM 收到的链接（核心升级）

**触发**：工作流 0 检测到未归档的微信/飞书链接

**数据源**：`~/.hermes/state.db` 的 `messages` 表

**步骤**：

1. 拉 session 元数据（`sessions.json`）：
   ```python
   session = {
     "session_id": "20260610_123639_78e91f4c",
     "platform": "weixin",
     "updated_at": "2026-06-10T12:38:09",
     "origin": {"user_id": "...", "user_name": "..."}
   }
   ```

2. 拉用户消息（含 URL 的）：
   ```sql
   SELECT id, role, content, timestamp
   FROM messages
   WHERE session_id = ?
     AND role = 'user'
     AND content LIKE '%https?://%'
   ORDER BY id
   ```

3. 对每个 URL：
   - 找 assistant 回复（含标题/摘要）
   - 找 tool 调用（含 `wx.html` 之类）
   - 合成"原文 + AI 提炼"

4. 决定归档位置（启发式）：
   - 关键词匹配（`MT5/MQL/EA/Quant` → `10-提炼/EA开发/`）
   - 关键词匹配（`AI/模型/LLM/agent` → `10-提炼/AI与自动化/`）
   - 兜底：`10-提炼/其他/`

5. 写新文件 + 更新 MOC

6. **标记 session 为已归档**：
   - 写入 `90-索引/_archive_state.json`：
     ```json
     {
       "archived_sessions": {
         "20260610_123639_78e91f4c": {
           "platform": "weixin",
           "archived_at": "2026-06-10T13:45:00",
           "files_created": [
             "10-提炼/AI与自动化/2026-06-10_WhichLLM 挑本地LLM的开源工具.md"
           ]
         }
       }
     }
     ```

---

## 工具速查

- `read_file` - 读
- `write_file` - 写
- `search_files` (target=files) - 列目录
- `search_files` (target=content) - 搜内容
- `patch` - 局部改
- `terminal` - 移动文件（`move` / `mv`）
- `python` (via `terminal`) - 查 SQLite 状态库

## Python 工具函数（写在 skill 的 references/）

`~/.hermes/skills/vault-curator/references/state_db.py`:
```python
import sqlite3, os, json
from datetime import datetime

STATE_DB = os.path.expandvars(
    r"%APPDATA%\cn.org.hermesagent.desktop\runtime\hermes-home\state.db"
)
SESSIONS = os.path.expandvars(
    r"%APPDATA%\cn.org.hermesagent.desktop\runtime\hermes-home\sessions\sessions.json"
)
ARCHIVE_STATE = os.path.expandvars(
    r"$OBSIDIAN_VAULT_PATH/90-索引/_archive_state.json"
)

def find_unarchived_sessions():
    """Find DM sessions with URLs not yet archived."""
    with open(SESSIONS, "r", encoding="utf-8") as f:
        sessions = json.load(f)
    archive_state = {}
    if os.path.exists(ARCHIVE_STATE):
        with open(ARCHIVE_STATE, "r", encoding="utf-8") as f:
            archive_state = json.load(f)
    
    candidates = []
    for key, s in sessions.items():
        platform = s.get("origin", {}).get("platform", "")
        if platform not in ("weixin", "feishu", "telegram"):
            continue
        sid = s.get("session_id")
        if sid in archive_state.get("archived_sessions", {}):
            continue
        # Has URL in user messages?
        db = sqlite3.connect(STATE_DB)
        c = db.cursor()
        c.execute(
            "SELECT content FROM messages WHERE session_id = ? AND role = 'user' AND content LIKE '%https%' LIMIT 5",
            (sid,),
        )
        urls = [r[0] for r in c.fetchall()]
        db.close()
        if urls:
            candidates.append({
                "session_id": sid,
                "platform": platform,
                "updated_at": s.get("updated_at"),
                "urls": urls,
            })
    return candidates

def mark_archived(session_id, platform, files):
    """Mark a session as archived."""
    archive_state = {"archived_sessions": {}}
    if os.path.exists(ARCHIVE_STATE):
        with open(ARCHIVE_STATE, "r", encoding="utf-8") as f:
            archive_state = json.load(f)
    archive_state["archived_sessions"][session_id] = {
        "platform": platform,
        "archived_at": datetime.now().isoformat(),
        "files_created": files,
    }
    with open(ARCHIVE_STATE, "w", encoding="utf-8") as f:
        json.dump(archive_state, f, indent=2, ensure_ascii=False)
```

## 黄金规则

1. ❌ 绝不覆盖手写文件
2. ❌ 绝不修改 `mt/`
3. ❌ 绝不删文件
4. ✅ 必须加 frontmatter
5. ✅ 必须用 wikilink
6. ✅ 必须**询问老大**再自动归档（避免误判）
7. ✅ 必须更新 MOC

## 🔗 配合

- mem0 - 短事实库
- obsidian skill - 通用 vault 工具
- vault-curator (本 skill) - 写 ai-managed
- mt5-ea-dev (待建) - 基于 mt vault

## 维护记录

- v1.0 (2026-06-10): 基础 Inbox/提炼/经验/skill/MOC 工作流
- v2.0 (2026-06-10): + 工作流 0 自动监控 + 工作流 5 自动归档 DM 链接
