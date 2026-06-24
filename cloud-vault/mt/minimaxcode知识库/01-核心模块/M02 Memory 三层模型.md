---
title: M02 Memory 三层模型
tags: [memory, project, agent, user]
created: 2026-06-03
---

# M02 Memory 三层模型

## 三层结构

```
┌────────────────────────────────────────────────────┐
│  1. Project Memory（项目内）                         │
│     AGENTS.md / topic.md                            │
│     "只在当前项目成立的知识"                            │
│     e.g. "本仓库用 pnpm，不接受 npm"                  │
├────────────────────────────────────────────────────┤
│  2. Agent Memory（跨项目，agent 私有）                │
│     ~/.mavis/agents/<agentName>/memory/MEMORY.md    │
│     "换项目结论仍成立"                                  │
│     e.g. "PowerShell 5.1 字符串拼接会丢反斜杠"          │
├────────────────────────────────────────────────────┤
│  3. User Memory（用户级，所有 agent 共享）             │
│     ~/.mavis/memory/user.md                          │
│     "换用户结论会变"（更窄）                            │
│     e.g. "用户用 zh-Hans，短句风格"                    │
└────────────────────────────────────────────────────┘
```

## 三问决策法

写之前**先问自己**：

1. **只在当前项目成立？** → Project Memory（AGENTS.md）
2. **换项目结论仍成立？** → Agent Memory（`mavis memory append`）
3. **换用户结论会变？** → User Memory（`mavis memory append --user`）

> 任何问题答案"否"时，**下沉到更窄层**。如不能跨项目复用，就别放 agent memory。

## 写入命令

```bash
# 1. Project：直接编辑文件
# ~/.mavis/agents/<agent>/workspace/<repo>/AGENTS.md
# 写完 commit

# 2. Agent：
mavis memory append <agentName> --content "### 主题 (日期)
Type: pitfall | fact | workflow | workaround
<内容>"

# 3. User（--reason 必填，跨项目理由）：
mavis memory append --user \
  --reason "用户跨项目都用中文短句风格" \
  --content "### 主题 (日期)
Type: preference
<内容>"
```

## 关键原则

1. **窄优先**：能放 project 不放 agent，能放 agent 不放 user。
2. **写少不写多**：每次 session 末尾自问"我学到了什么可复用的？"
3. **不要 session 内存**：session 内存已废弃，所有"短期记忆"走 scratchpad。
4. **memory 是 hint 不是 state**：用之前要重新验证。

## 正确 vs 错误示范

### ✅ 正确：PowerShell `$_` 解析踩坑
- 放哪里：**Agent Memory**（`general` agent）
- 理由：换任何项目用 PowerShell 5.1 都会遇到

### ❌ 错误：把项目特定的 git remote 放 user memory
- 应该放：Project Memory（`AGENTS.md`）
- 原因：换项目这个 remote 就不对了

### ❌ 错误：把"今天 MT5 下单被滑点 30 pips"放 agent memory
- 应该放：trader agent memory（且是 fact 而非 pitfall）
- 或更窄：项目 knowledge

## 清理节奏

- **每月**：扫一遍 agent memory，删除已过时 / 已修复的坑
- **每季**：合并重复条目；把项目级条目搬到对应 AGENTS.md
- **每次重大升级**：daemon 升级、PowerShell 大版本后回顾
