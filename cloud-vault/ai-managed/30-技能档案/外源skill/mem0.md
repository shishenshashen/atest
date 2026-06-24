---
title: mem0 · 外源技能索引
tags: [skill, 外源, mem0, AI与自动化]
type: skill-reference
installed: 2026-06-10
source: mem0ai/mem0 (GitHub)
installed-via: manual copy (Hermes not in 71-agent list)
---

# 🧠 mem0 · AI 记忆层

> **Y Combinator S24**，业界最知名的 AI 记忆中间件。
> 让 LLM 应用有"长期记忆"。

## 🔗 链接

- **官网**: https://mem0.ai
- **GitHub**: https://github.com/mem0ai/mem0
- **新算法论文 (2026-04)**: https://mem0.ai/research
- **评测代码**: https://github.com/mem0ai/memory-benchmarks
- **skill 源**: https://github.com/mem0ai/mem0/tree/main/skills/

## 📊 性能（新算法 April 2026）

| Benchmark | Old | New |
|-----------|-----|-----|
| LoCoMo | 71.4 | **91.6** |
| LongMemEval | 67.8 | **94.8** |
| BEAM (1M) | - | **64.1** |
| BEAM (10M) | - | **48.6** |

## 🚀 三种部署

| 方式 | 适用 | 难度 |
|------|------|------|
| **Library** (`pip install mem0ai`) | 测试原型 | ⭐ |
| **Self-Hosted Server** (`docker compose`) | 团队生产 | ⭐⭐ |
| **Cloud Platform** (app.mem0.ai) | 零运维 | ⭐ |

## 🛠️ 装到 Hermes 的实际操作（2026-06-10）

1. 跑 `npx skills add https://github.com/mem0ai/mem0 --skill mem0`
2. 仓库克隆到 `/tmp/skills-xxx/mem0/`
3. **Hermes 不在 agent 列表**，手动 `cp` SKILL.md 到 `~/.hermes/skills/mem0/`
4. 类似可以装 `mem0-cli` / `mem0-integrate` / `mem0-test-integration` / `mem0-vercel-ai-sdk`

## 💼 接入 Hermes 的方式

### 走 cloud（已实现 ✅）
```bash
hermes config set memory.provider mem0
echo "MEM0_API_KEY=*** >> ~/.hermes/.env
```
- Provider: `mem0` active
- API: `https://api.mem0.ai/v1/`
- 老大账号: `979964957@qq.com`
- 当前 user: `hermes-wandf`，16 条事实

### 走 REST API（直接调用）
```python
import urllib.request, json
req = urllib.request.Request("https://api.mem0.ai/v1/memories/",
    data=json.dumps({"messages":[...],"user_id":"hermes-wandf"}).encode(),
    headers={"Authorization":"Token m0-...","Content-Type":"application/json"})
urllib.request.urlopen(req)
```

## 🎯 适用场景

- ✅ 给 chatbot 加长期记忆
- ✅ 多用户个性化
- ✅ 跨会话保留上下文
- ✅ 长期项目跟进（几月-几年）
- ❌ 短期/会话级（用会话上下文更快）
- ❌ 完全本地化要求（要走 library + 本地 LLM）

## ⚠️ 已知坑

- **走境外 API**：GFW 影响要测（本机访问正常）
- **JSON 转义**：写 Windows 路径用 `chr(92)` 拼反斜杠
- **异步队列**：写入后 PENDING，要 sleep 5-10 秒再查
- **fact extraction**：依赖平台 LLM，不可控
- **npx skills 不认 Hermes**：必须手动 cp

## 📚 相关文档

- `vault:ai-managed/20-经验沉淀/2026-06/2026-06-10_mem0外置记忆库集成.md` - 实战记录
- `vault:mt/` 老大 MT5 EA 知识库（可能未来用 mem0 索引）

## 🔄 未来改进

- 装 `mem0-cli`（命令行操作）
- 装 `mem0-integrate`（一键整合到现有项目）
- 配 local 模式（避免上云）
- 写 `mt5-ea-dev` skill（基于 mt vault）
