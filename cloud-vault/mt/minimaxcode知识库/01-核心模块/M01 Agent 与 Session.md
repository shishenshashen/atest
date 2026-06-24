---
title: M01 Agent 与 Session
tags: [agent, session, communication]
created: 2026-06-03
---

# M01 Agent 与 Session

## 概念区分

| 概念         | 持久化？ | 数量   | 角色                              |
| ---------- | ----- | ---- | ------------------------------- |
| **Agent**  | 是（盘）  | 少量   | 角色定义（worker / orchestrator）   |
| **Session** | 否（内存） | 很多   | 一次任务 = 一个 session tree        |
| **Scratchpad** | 是（盘） | 每树 1 | root session 的白板，跨子 session 共享  |

## Session 树

- **Root session**：用户启动的"主"任务
- **Branch session**：通过 `Task` tool 或显式派发产生的子任务
- 父子通过 `mavis communication` 通信（**不是** `mavis session`）

```
Root（用户）─── Branch A（worker general）
            └─ Branch B（worker trader）
            └─ Branch C（worker researcher）
```

## Agent 类型

| agentName   | agentRole   | 用途                                |
| ----------- | ----------- | --------------------------------- |
| `general`   | worker      | 通用任务，能干但不是专家                      |
| `coder`     | worker      | 写代码、跑测试、改 bug                     |
| `researcher` | worker      | 调研、抓资料、对比方案                       |
| `trader`    | worker      | MT5/EA 交易相关（你专用的）                |
| `pm`        | orchestrator | 拆任务、派活、汇总（如果配置了）                 |

## 父子通信协议

**子 → 父**（汇报结果）：

```bash
mavis communication send --to <parent-session-id> --content "任务完成，结果是 X"
```

**父 → 子**（不常见，子任务一般是自驱的）：

```bash
mavis communication send --to <child-session-id> --content "补充要求：..."
```

## "finished" 的含义

> `finished` ≠ session 关闭

- `finished` = 空闲 / 可路由
- 关闭 session 需要显式 `mavis session close` 或等待 daemon 重启

## 何时该升级到专用 agent

> 引用：general agent 的守则

当出现以下信号，立即向 PM 提议建专用 agent：

- 反复涉及 **同一项目的连续历史**（你无法靠一次性 prompt 还原）
- 任务明显属于 **固定流水线**（每天/每周重复同类活）
- 跨多次 session 都要读 **同一批项目知识**（AGENTS.md / 知识库）

专用 agent 会**自己维护**项目记忆，不会每次让 general 重新调研。

## 实操清单

- [ ] 启动任务前 `mavis session list` 看是否有正在跑的同类任务
- [ ] 子任务完成后**主动汇报**到 parent（不要等问）
- [ ] 阻塞时**立即**上报，不要原地打转
- [ ] 任务结束判断：交付物完成 + 已汇报 = 完工
