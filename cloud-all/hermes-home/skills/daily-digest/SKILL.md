---
name: daily-digest
description: >
  Generate daily / weekly / monthly summary of user's activities. Trigger when
  user says: "做个 daily", "今天的总结", "做个 weekly", "这个月总结", or
  when triggered by cron at 22:00 daily / Sunday weekly / 1st monthly. Reads
  state.db, vault 20-经验沉淀/, mem0 cloud, and writes summary to
  $OBSIDIAN_VAULT_PATH/20-经验沉淀/<YYYY-MM>/<Daily|Weekly|Monthly>/<DATE>.md
  Then updates MOC.
license: MIT
metadata:
  author: 小神龙
  version: "1.0.0"
  category: productivity
  tags: "daily, weekly, monthly, summary, reflection, cron, knowledge-management"
platforms: [linux, macos, windows]
---

# Daily Digest · AI 自动每日/每周/每月总结

> **触发方式**：
> - 手动：用户说"做个 daily"、"总结今天"、"weekly"、"月度总结"
> - 自动：cron 每天 22:00 跑 daily，每周日 22:00 跑 weekly，每月 1 号 22:00 跑 monthly

## 📁 输出位置

```
$OBSIDIAN_VAULT_PATH/20-经验沉淀/<YYYY-MM>/
├── Daily/YYYY-MM-DD.md        # 每日
├── Weekly/YYYY-Www.md         # 每周 (ISO 周编号)
└── Monthly/YYYY-MM.md         # 每月
```

## 🔄 工作流

### 步骤 1：扫数据源

读取三个地方：

**A. state.db**（Hermes 本地数据库）：
- `messages` 表：今天所有 platform 的所有 session
- 统计：user msgs, assistant msgs, tool calls, sessions
- 提取：用户消息关键词（粗略主题分类）

**B. vault 20-经验沉淀/**：
- 今天新建的"事件型"反思（不是 Daily/Weekly/Monthly）
- 看 AI 已经自己写了什么

**C. mem0 云端**：
- 调 `/v1/memories/?user_id=hermes-wandf`
- 统计今天新增的事实

### 步骤 2：分析

- **重点**（做了什么）：合并用户消息主题 + 工具调用模式
- **知识范围**（学了什么）：关键词分类
- **广度**（vs 深度）：每个主题的触达度，按 0-100 评分
- **协作默契**：从 assistant 回复的纠错次数判断
- **金句**：用户消息里高信息量的句子（决定性陈述）

### 步骤 3：写文件

模板见 `references/templates/`：

**Daily 模板**：
- 🎯 今日重点
- 📚 知识范围
- 🌍 广度可视化（ASCII 进度条）
- 🤝 协作默契
- 💡 今日金句
- 📊 数据摘要
- ⚠️ TODO 清单
- 🔗 今日产出（链向 vault）
- 📈 对比昨日
- 🌙 明天怎么用我

**Weekly 模板**：
- 📊 本周数据汇总
- 🌍 主题趋势变化
- 🤝 协作模式总结
- 💡 关键决定
- 📁 vault 增长统计
- 🎯 下周建议

**Monthly 模板**：
- 🎯 本月里程碑
- 📚 知识体系成熟度
- 🤝 AI 协作默契演变
- 🔧 工具/skill 增长
- 💡 重大决定
- 🔮 下月方向

### 步骤 4：更新 MOC

`$OBSIDIAN_VAULT_PATH/90-索引/MOC.md`：
- Daily-MOC 段加新 daily
- Weekly-MOC 段加新 weekly
- Monthly-MOC 段加新 monthly

### 步骤 5：（可选）推送

- 通过 `hermes send` 发到飞书/微信
- 模板化消息：标题 + 3 个 bullet + vault 链接

## 🐍 Python 工具

`references/state_aggregator.py`：
- `aggregate_today() -> dict` - 扫 state.db，返回今日数据
- `aggregate_week(week_num) -> dict` - 扫一周
- `aggregate_month(year, month) -> dict`
- `extract_keywords(messages) -> Counter`
- `detect_quotes(messages) -> list[str]`

## ⏰ Cron 配置

`~/.hermes/cron/daily-digest.json`：
```json
{
  "name": "daily-digest-22h",
  "schedule": "0 22 * * *",
  "command": "hermes chat --skill daily-digest '生成今日 daily'",
  "enabled": true
}
```

`~/.hermes/cron/weekly-digest.json`：
```json
{
  "name": "weekly-digest-sunday",
  "schedule": "0 22 * * 0",
  "command": "hermes chat --skill daily-digest '生成 weekly'",
  "enabled": true
}
```

`~/.hermes/cron/monthly-digest.json`：
```json
{
  "name": "monthly-digest-first",
  "schedule": "0 22 1 * *",
  "command": "hermes chat --skill daily-digest '生成 monthly'",
  "enabled": true
}
```

## 🔗 配合

- **vault-curator** - 维护 vault 结构
- **obsidian** - 读写文件
- **mem0** - 提供"长期事实"补充

## 维护记录

- v1.0 (2026-06-10): 初版
