# 小神龙工作流总体设计 v3

> **作者**: 小神龙 (Hermes Agent) · **日期**: 2026-06-11 · **状态**: 待老大拍板
> **核心一句话**: 从"被动监控假死"升级为"主动推进 + 节奏化交付"，1 个 AI + 1 个人，最小治理最大收益。

---

## 0. 总体架构（1 张图）

```
                        ┌─────────────────────────────────────┐
                        │  老大 (你)                          │
                        │  - 下指令                           │
                        │  - 收 escalate                      │
                        │  - 决定要不要重试                   │
                        │  - 拍板 CRITICAL                    │
                        └──────────┬──────────────────────────┘
                                   │ 指令 / 拍板
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 0: 会话入口（每次自动）                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐          │
│  │ consume_pending│→ │ show_watchdog  │→ │ roll_call      │          │
│  │ 拉积压告警     │  │ 状态+假死任务  │  │ 列活跃+4问review│          │
│  └────────────────┘  └────────────────┘  └────────────────┘          │
└──────────────────────────────────────────────────────────────────────┘
                                   ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 1: 任务登记（你说"做 X"自动跑）                                │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐          │
│  │ 4 问 checklist │→ │ 任务等级         │→ │ 拆 todo (≤7)   │          │
│  │ 必答 4 个问题   │  │ S/M/L/CRITICAL  │  │ 入 task-queue   │          │
│  └────────────────┘  └────────────────┘  └────────────────┘          │
└──────────────────────────────────────────────────────────────────────┘
                                   ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 2: 执行推进（watchdog 3 档主动推进）                            │
│                                                                       │
│     1×stale              2×stale              3×stale / 卡住          │
│   ┌─────────┐          ┌─────────┐          ┌─────────┐            │
│   │  nudge  │   →      │  ping   │   →      │escalate │            │
│   │温柔提醒  │          │ 明确质问 │          │ 推老大   │            │
│   │ 子 agent│          │ 子 agent │          │ 你拍板  │            │
│   │ 必回执  │          │ 必答卡哪 │          │  重试?  │            │
│   └─────────┘          └─────────┘          │  换思路?│            │
│                                              │  取消?  │            │
│                                              └─────────┘            │
└──────────────────────────────────────────────────────────────────────┘
                                   ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 3: 验证（自动 verify + 你 review）                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐          │
│  │ verify_task()  │→ │ 你 review      │→ │ 不自动重试      │          │
│  │ sha256+size+path│  │ 人工 gate      │  │ 只重试网络错误  │          │
│  └────────────────┘  └────────────────┘  └────────────────┘          │
└──────────────────────────────────────────────────────────────────────┘
                                   ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 4: 沉淀（每日 23:00 自动跑）                                    │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐          │
│  │ daily_review   │→ │ Cortex-lite    │→ │ 推老大日报     │          │
│  │ 假死率/最慢    │  │ 超时 3 次降     │  │ 你看到可决策的  │          │
│  │ 失败/验证      │  │ 默认 timeout   │  │ 趋势            │          │
│  └────────────────┘  └────────────────┘  └────────────────┘          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 1. 设计哲学（为什么这样）

### 1.1 三条不可妥协的原则

| # | 原则 | 来源 |
|---|---|---|
| P1 | **0 编造**（API/行号/产物） | user profile |
| P2 | **0 敷衍**（做了就是做了，没做就是没做） | user profile |
| P3 | **速度敏感**（治理不能拖慢交付） | user profile |

### 1.2 三个借鉴对象的取舍

| 来源 | 学什么 | 不学什么 |
|---|---|---|
| **scale-engine** | 证据闭环（verify_task）、任务等级、Cortex-lite | 6 阶段、6 角色、3 引擎、npm CLI 化 |
| **project-scaffold** | 4 问 checklist、Makefile 入口、S 级豁免、resume | 强制建任务目录、3 个 AGENTS/CLAUDE/CONTEXT 重复 |
| **task-queue v2**（已实现） | mutate 重入、archive 分文件、verify_task、role 默认 | 静默假死（要补主动推进） |

### 1.3 我们**不**做的事（明确放弃）

- ❌ **不**做 6 阶段状态机（`define→plan→build→verify→review→ship`）——**4 层**足够
- ❌ **不**做 6 角色审查——你 1 个 reviewer
- ❌ **不**做 OWASP/STRIDE 审计——MT5 EA 不在公网
- ❌ **不**做 Token 预算度量——你比量化指标敏感
- ❌ **不**做自动重试（业务错误）——掩盖问题
- ❌ **不**做多 AI harness 适配——只用 Hermes
- ❌ **不**做强制任务目录——queue.jsonl 就是目录
- ❌ **不**装 scale-engine npm CLI

---

## 2. Layer 0：会话入口（每次自动）

### 2.1 触发

**每次** Hermes 会话开始时（不论是手动开新会话还是自动续期）**自动**跑。

### 2.2 三个动作（顺序）

| # | 动作 | 目的 | 输出 |
|---|---|---|---|
| 1 | `consume_pending()` | 拉 watchdog 积压的告警（nudge/ping/escalate/fail） | 推给老大（屏幕顶 + 微信/飞书） |
| 2 | `watchdog status` | watchdog 在不在？interval？最后扫描时间？ | 一行 + 子 agent 数 |
| 3 | `roll_call()` | 列所有 active 任务，每条带"4 问 review"标记 | 表格 |

### 2.3 4 问 review 标记

每个 active 任务标一个**健康度**：

| 标记 | 含义 | 你要不要介入 |
|---|---|---|
| 🟢 green | started < 1×stale，进度正常 | 不用 |
| 🟡 yellow | 1×stale < now < 2×stale，已 nudge | 看一眼 |
| 🟠 orange | 2×stale < now < 3×stale，已 ping | 可能要介入 |
| 🔴 red | > 3×stale / 子 agent 说卡 / 已 escalate | **你必看** |

### 2.4 入口的"展示格式"（给 Hermes 的 prompt 模板）

```
## 老大，会话已开

🚨 积压告警: {N} 条（详情见下）
🟢 watchdog: pid {PID} interval {INTERVAL}s 最后扫描 {TIME}
📋 活跃任务: {COUNT} 个

| 健康度 | task_id | 角色 | 等级 | 目标 | 进度 | 卡了多久 |
|---|---|---|---|---|---|---|
| 🟢 | t-... | coder | L | 实现 X | 3/7 | - |
| 🟡 | t-... | ops | M | 跑命令 | 1/3 | 4m |
| 🔴 | t-... | researcher | L | 调研 Y | 0/5 | 12m 已 escalate |

⚡ 需要你拍板: {N} 个（见 🔴 行的具体内容）
```

---

## 3. Layer 1：任务登记（你说"做 X"自动跑）

### 3.1 4 问 checklist（**启动子 agent 前必填**）

> 来源：project-scaffold "回答 4 个问题"

每个任务入队时**强制**带这 4 个字段（不填不入队）：

| 问 | 字段 | 示例 |
|---|---|---|
| 1. 解决啥 | `goal` | "把 MT5 EA 反编译补注释" |
| 2. 影响啥 | `files` (or `scope`) | ["src/EA.mq5", "docs/spec.md"] |
| 3. 验证啥 | `verify_plan` | ["compile pass", "backtest 30 天"] |
| 4. 沉淀啥 | `deliverable` | "改后的 .mq5 + 编译日志 + journal entry" |

### 3.2 任务等级（**S/M/L/CRITICAL**）

> 来源：project-scaffold 任务等级

| 等级 | 场景 | 必做 | 默认 timeout | 默认 heartbeat | 治理强度 |
|---|---|---|---|---|---|
| **S** | typo、注释、小文档 | 最小验证 + 4 问简版 | 60s | 20s | 0 仪式（不写探索记录） |
| **M** | 脚本、小功能、普通 bug | 4 问全 + explore 记录 | 600s | 60s | 1 次 watchdog nudge 容忍 |
| **L** | 跨模块、架构、模板 | 4 问全 + plan 文档 + 影响面 | 1800s | 120s | 2 次 nudge + 1 次 ping 容忍 |
| **CRITICAL** | 数据/权限/安全/生产 | 4 问全 + 人工拍板 + 回滚方案 | 3600s | 120s | 0 自动重试，**任何** escalate 必到老大 |

### 3.3 拆解（**≤7 步原则**）

你说"做 X"，AI 拆成 todo 时：
- **≤ 7 步**（否则人类认知超载，参考 Miller's Law）
- 每步**独立** task_id（可独立心跳、独立 archive）
- 第 1 步必须**有可验证的产物**（不能是"先思考一下"）

### 3.4 入队

每个 todo 调 `tq.enqueue(goal, level, files, verify_plan, deliverable, ...)`。

---

## 4. Layer 2：执行推进（核心：3 档主动推进）

### 4.1 三档推进矩阵

| 档位 | 触发条件 | watchdog 动作 | 子 agent 必做 | 老大被打扰？ |
|---|---|---|---|---|
| **档 1: nudge** | 1×stale < gap < 2×stale | 写 `nudges/{task_id}.json` 标 `kind=nudge` | 启动时读 nudges → 必回 "RESPONDING_TO_NUDGE running X/N" | ❌ 不打扰 |
| **档 2: ping** | 2×stale < gap < 3×stale | 写 nudges 标 `kind=ping` | 必回 "RESPONDING_TO_PING，卡在: 1) 难点 2) 还要多久" | ⚠️ 子 agent 自己判断要不要喊老大 |
| **档 3: escalate** | gap > 3×stale / 子 agent 主动说卡住 / nudge+ping 都无效 | push 告警 + 写 journal 一行 | （子 agent 已被冻结等你） | ✅ **必打扰**，你拍板 |

**其中 `stale = 1 × heartbeat_sec`**（典型 60-120s）

### 4.2 nudge 文件协议

```
~/.hermes/task-queue/nudges/
└── {task_id}.json   ← 每次 watchdog 推进覆盖写
```

```json
{
  "task_id": "t-20260611-...",
  "kind": "nudge|ping|escalate",
  "at": 1781159000,
  "gap_sec": 240,
  "last_heartbeat": 1781158760,
  "msg": "5 分钟无新心跳，请报告进度和遇到的困难"
}
```

子 agent 启动时（或下次心跳时）`consume_nudges(task_id)` → 看到 nudge → 必回执 + 删 nudge。

### 4.3 子 agent 行为契约（agent_goal.md 必加段）

```
## 收到 nudge/ping 必做
1. 启动时**必读** ~/.hermes/task-queue/nudges/{task_id}.json
2. 如果有 nudge 且你还没回执 → 立即回 "RESPONDING_TO_NUDGE"
3. 必须报告：
   - 当前进度 X/N
   - 卡在哪（具体文件名/行号/问题描述）
   - 还要多久（秒）
4. 严禁：
   - 假装"还在跑"（heartbeat 编造）
   - 反复发同一份回执
   - 说"快好了"但不更新进度
```

### 4.4 心跳规则（**已实现**，保持）

| 时间 | 动作 |
|---|---|
| 启动 30s 内 | `started` + ETA |
| 每 heartbeat_sec | `running X/N` + 一句话状态 |
| 完成 | `done` + artifacts |
| 失败 | `failed` + 真实错误 traceback |

### 4.5 超时检测（**已实现**，保持）

`gap = now - last_heartbeat > timeout_sec` → 标 `status="timeout"`（独立 status，不再伪装 failed）→ push 告警。

---

## 5. Layer 3：验证（自动 + 人工 gate）

### 5.1 自动 verify_task（**已实现**，加强）

每个 done 任务**必填** artifacts：

| 字段 | 类型 | 要求 |
|---|---|---|
| `path` | str | **绝对路径**，`Path(p).resolve()` 验证存在 |
| `size` | int | `Path(p).stat().st_size` 真实值 |
| `hash` | str | **完整 sha256 64 位**（不是前 8 位） |

verify_task 检查三者**全对**才算 verified。**任一不对** → 任务实际是 failed（即使 status=done）。

### 5.2 4 问 vs verify_task

| 4 问里的"验证啥" | verify_task 验真 |
|---|---|
| "compile pass" | 跑命令 `metac trader /compile:src/EA.mq5`，exit 0 + 产物存在 |
| "backtest 30 天" | 跑 backtest 30 天，导出 report，hash 进 artifacts |

**这层是 v3 的扩展点**：v2 只 verify sha256，v3 加 `verify_command`——watchdog finalize 时自动跑。

### 5.3 你的 review（人工 gate）

- **M/L** 任务：你看 journal entry + artifacts 列表 → 标 "approved" / "rejected"
- **CRITICAL** 任务：你看完整 journal + 跑自己验证 → 才能 mark approved

### 5.4 不自动重试原则

| 错误类型 | watchdog 动作 |
|---|---|
| **网络/超时**（model 503、subprocess TimeoutExpired） | ✅ 自动重试 1 次（标 retry_reason=transient） |
| **业务错误**（AI 报告"找不到 X 文件"、"代码编译失败"） | ❌ **绝不**自动重试 → 标 failed + 推老大 |
| **验证失败**（hash 不对、size 不对） | ❌ 标 failed（这是 AI 编造的强证据）→ 推老大 |

---

## 6. Layer 4：沉淀（每日 + 学习）

### 6.1 daily review（**23:00 cron**）

输出 `~/.hermes/reviews/daily-{date}.md`：

| 指标 | 含义 | 目标 |
|---|---|---|
| 总任务数 | 当日 created | - |
| 完成率 | done / total | ≥ 70% |
| 假死率 | timeout / total | < 10% |
| 验证失败率 | verify fail / done | < 5% |
| 平均耗时 | sum(updated - created) for done | 趋势对比上周 |
| 最慢任务 | top 3 longest done | - |
| 等级分布 | S/M/L/CRITICAL 各几个 | - |
| 等级完成率 | 各等级 done 率 | 找"哪级最容易假死" |

### 6.2 weekly review（**周日 22:00**）

对比上周，给出**可决策的洞察**：
- 哪类任务假死率上升？
- 哪类任务平均耗时上升？
- nudge 命中率（多少次 nudge 触发了真回执 vs 假回执）
- Cortex-lite 调整的 role timeout 是否有效

### 6.3 Cortex-lite（**自调参**）

> 来源：scale-engine Cortex 简化版

**规则**（**只**自动调，不调别的）：

| 信号 | 触发 | 动作 |
|---|---|---|
| 某 role 累计 timeout ≥ 3 次 | watch 累计 | 该 role 默认 timeout × 0.5（**只**对该 session 生效） |
| 某 role 连续 10 次 done | watch 连续 | 该 role 默认 timeout × 1.2（保守，**只**对 L/CRITICAL 生效） |
| 你手动调过 timeout | 任何时候 | 重置自动调参（**你**拍板优先） |

存到 `~/.hermes/task-queue/cortex.json`：

```json
{
  "ops": {"auto_timeout": 60, "manual_override": false, "last_auto_adj": 1781159000},
  "coder": {"auto_timeout": 1800, "manual_override": true, "manual_timeout": 3600}
}
```

**为什么**只调 timeout 不调别的：timeout 是**唯一**直接影响假死率的参数；其他参数（heartbeat、retry）动一下风险大。

---

## 7. 数据流与状态机

### 7.1 task 状态机

```
                    enqueue()
                        ↓
                   ┌─────────┐
                   │ queued  │
                   └────┬────┘
              heartbeat("started")  → (30s 内必到，否则 watchdog nudge)
                        ↓
                   ┌─────────┐
        ┌──────────│ started │──────────┐
        │          └────┬────┘          │
   heartbeat           heartbeat        watchdog timeout
   (running)           (running)              │
        │                │                   ↓
        ↓                ↓              ┌─────────┐
   ┌─────────┐     ┌─────────┐         │ timeout │
   │ running │←───→│ running │         └────┬────┘
   └────┬────┘     └────┬────┘              │
        │                │                   ↓
   mark_done       mark_failed           archive
        ↓                ↓                   │
   ┌─────────┐     ┌─────────┐              │
   │  done   │     │ failed  │              │
   └────┬────┘     └────┬────┘              │
        │                │                   │
        ↓                ↓                   ↓
   ┌──────────────────────────────────────────┐
   │              archive/{date}.jsonl        │
   └──────────────────────────────────────────┘
```

**nudge / ping / escalate 是状态机的"边"——不改变 status，只写 nudges/ + push**。

### 7.2 持久化结构

```
~/.hermes/
├── task-queue/
│   ├── queue.json              ← active tasks (dict)
│   ├── queue.lock              ← 文件锁
│   ├── archive/{date}.jsonl    ← 终态任务按天归档
│   ├── nudges/{task_id}.json   ← watchdog → 子 agent 通信
│   ├── pending_notices.json    ← 飞书/wecom 推送兜底
│   ├── watchdog.pid            ← watchdog 进程 pid
│   ├── logs/{date}.log         ← watchdog 日志
│   └── cortex.json             ← Cortex-lite 自调参
├── journal/{date}.md           ← 任务留痕
└── reviews/
    ├── daily-{date}.md         ← 每日复盘
    └── weekly-{date}.md        ← 周报
```

---

## 8. Makefile 入口（5 个 target）

```makefile
.PHONY: start status review consume test

start:           ## 启动 watchdog（后台）
	python ~/.mavis/skills/task-queue/watchdog.py start 60

status:          ## 看 watchdog + 活跃任务
	python ~/.mavis/skills/task-queue/watchdog.py status
	@python -c "import sys; sys.path.insert(0, '$(HOME)/.mavis/skills/task-queue'); from queue import list_active; [print(t['task_id'], t['status'], t['progress']) for t in list_active()]"

review:          ## 生成今日 review（不推）
	python ~/.mavis/skills/task-queue/review.py daily --no-push

consume:         ## 拉所有积压告警并清空
	python -c "import sys; sys.path.insert(0, '$(HOME)/.mavis/skills/task-queue'); from push import consume_pending; [print(n) for n in consume_pending()]"

test:            ## 跑端到端测试
	python ~/.mavis/skills/task-queue/test_task_queue_v3.py
```

**5 个 target 规则**：
- 每个 target 1 行能跑完
- 不超过 5 个（**不**学 project-scaffold 几十个 target）
- 都有简短 help

---

## 9. 验收标准（可量化）

### 9.1 落地后 7 天内必须达成

| # | 指标 | 目标 | 怎么测 |
|---|---|---|---|
| 1 | 假死率 | < 10% | daily review |
| 2 | 失败推送到达率 | 100% | consume_pending 看积压 |
| 3 | journal 每日新增 | 100% 不漏 | `ls ~/.hermes/journal/` 看日期 |
| 4 | review 连续生成 | 7/7 天 | `ls ~/.hermes/reviews/` |
| 5 | 4 问必填率 | 100% 入队任务 | 抽查 10 个 task 看字段 |
| 6 | 任务等级覆盖 | S/M/L/CRITICAL 全有 | 周报统计 |
| 7 | verify_task 通过率 | > 80% | 抽查 done 任务 |
| 8 | Cortex-lite 命中率 | > 50% 的调整在 7 天内减少假死 | 对比调整前后的 role 假死率 |
| 9 | nudge 有效回执率 | > 70% (子 agent 看到 nudge 真回执) | 在测试场景统计 |
| 10 | escalate 假阳性 | < 5% (不该 escalate 的别推) | 你的反馈 |

### 9.2 7 天后看什么

- 你**被打扰**的次数（escalate + 失败推送）—— 应该 < 每天 1 次
- 你**说"对"**的次数（review approve）—— 应该 > 80%
- 任务完成到"真交付"的时间 —— 应该下降

---

## 10. 实施步骤（分 3 阶段，每阶段独立可验）

### 阶段 1：基础扩展（1-2 小时，今天可完）

| 任务 | 文件 | 估时 |
|---|---|---|
| 加 nudges/ 目录 + tq.nudge() API + tq.consume_nudges() | queue.py | 15 min |
| watchdog 3 档推进（stale→nudge / 2×stale→ping / 3×stale→escalate） | watchdog.py | 30 min |
| templates/agent_goal.md 加 nudge 契约 | templates/ | 10 min |
| dispatch 派发时自动注入 "启动时读 nudges/" 提示 | dispatch.py | 15 min |
| Makefile（5 target） | Makefile | 10 min |
| test_task_queue_v3.py 覆盖 nudge 流程 | test_task_queue_v3.py | 30 min |
| 跑全套测试（v2 43 + v3 8+） | - | 15 min |

**验证**：51+ 测试全绿 + 手动入队一个假死任务看 3 档真实触发

### 阶段 2：4 问 + 任务等级（半天）

| 任务 | 文件 | 估时 |
|---|---|---|
| enqueue() 加 level + files + verify_plan + deliverable 必填 | queue.py | 30 min |
| ROLE_DEFAULTS 加 level 字段 + level → timeout/heartbeat 表 | queue.py | 15 min |
| templates/agent_goal.md 加 4 问必答段 | templates/ | 15 min |
| Cortex-lite：watchdog 累计超时写 cortex.json | watchdog.py + cortex.py | 60 min |
| daily_review 加等级分布 + 假死率分子分母 | review.py | 20 min |
| 测试覆盖 | test | 30 min |

**验证**：入队一个 L 级任务看 4 问是否强校验 + 看 cortex.json 在 3 次超时后自动降级

### 阶段 3：长期沉淀（不急）

- verify_command：watchdog finalize 时跑你指定的验证命令
- 跨 session resume：从 journal 重建 task 上下文
- 多 Hermes 协调（如果将来你用 OpenCode）
- 周报自动推送到微信（配飞书 webhook）

---

## 11. 不确定的事（需要老大拍板）

| # | 决策点 | 我的推荐 | 备选 |
|---|---|---|---|
| 1 | nudge 阈值 (1×stale) 是否太频繁 | ✅ 用 1×stale | 老大可以调成 1.5× |
| 2 | 业务错误完全不自动重试是否过严 | ✅ 完全不重试（0 编造原则） | 允许 1 次重试但必报老大 |
| 3 | L/CRITICAL 默认 1800s/3600s 是否太长 | ✅ L=1800 CRITICAL=3600 | 老大自己改 ROLE_DEFAULTS |
| 4 | Cortex-lite 调整是否要 push 告知 | ✅ push 一行 "cortex auto-adj" | 静默不推 |
| 5 | 验证 v3 要不要先把 v2 现有的 dispatch.py / journal.py 也重测 | ✅ 重测，跑全套 v2+v3 | 只测 v3 新增 |
| 6 | Makefile 放 ~/.mavis/skills/task-queue/ 还是 ~/.hermes/task-queue/ | ✅ ~/.mavis/skills/（与现有 skill 同地） | 老大习惯地方 |
| 7 | 任务等级是 enqueue 必传还是不传默认 M | ✅ 不传默认 M（最少仪式） | 必传 |
| 8 | CRITICAL 任务是否要"双确认"（你确认一次 + 也要你最终 approve） | ✅ 是 | 简化 |

---

## 12. 回到老大最痛的那句话

> "**你要自动去推进任务**"

**这件事的设计回应**：

| 痛点 | 设计层 | 机制 |
|---|---|---|
| 假死没人推 | Layer 2 档 1 | watchdog 主动 nudge |
| 卡住没人推 | Layer 2 档 2 | watchdog 主动 ping，子 agent 必答卡哪 |
| 推不动没人推 | Layer 2 档 3 | watchdog escalate 推你 |
| 推了没效果 | Layer 2 不自动重试 | 永远你来定 |
| 推得没节奏 | Layer 1 任务等级 | S/M/L/CRITICAL 决定每档容忍时间 |
| 推的姿势不对 | Layer 1 4 问 | 子 agent 启动前就想清楚要做啥 |
| 推完没人接 | Layer 3 验证 | verify_task 真验真，不靠 AI 自报 |
| 推的历史没记录 | Layer 4 沉淀 | daily/weekly + Cortex-lite 越推越准 |

**核心**：从"被动监控"变成"**节奏化主动推进**"，但**拍板永远在你**。
