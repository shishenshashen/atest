---
name: task-queue
description: 长任务队列 + 心跳 watchdog + 主动推进 3 档 + 4 问必填 + Cortex-lite 自调参 + 推送 + 复盘。用于根治"派子 agent 后假死"+"主动推进"+"治理" 三个老大痛点。所有 ≥2 分钟的子任务必走本 skill 派发。
version: 3.0
author: 小神龙
created: 2026-06-11
updated: 2026-06-11
tested: 107/107 端到端通过（v2 43 + v3 33 + v4 31）
---

# task-queue v3+Phase 2：根治假死 + 主动推进 + 治理

老大反馈 3 个痛点，本 skill 一次解决：
1. **假死** — 子 agent 跑着跑着没动静，父级不知道
2. **不主动** — 假死后没人推
3. **没治理** — 任务随便派，没 4 问没等级没复盘

---

## 核心架构（4 层 + 1 入口）

```
                  老大
                   ↑ 推 escalate / 收 notice
                   ↓ 拍板 / 下指令
┌────────────────────────────────────────────────┐
│ L0 入口：consume_pending + roll_call + status   │ 自动跑
├────────────────────────────────────────────────┤
│ L1 登记：4 问必填 + 等级 S/M/L/CRITICAL         │ enqueue
├────────────────────────────────────────────────┤
│ L2 推进：1×stale→nudge │ 2×stale→ping         │ watchdog 主动
│         3×stale→escalate │ ≥timeout→timeout    │
├────────────────────────────────────────────────┤
│ L3 验证：自动 verify_task + 你 review + 不重试  │ finalize
├────────────────────────────────────────────────┤
│ L4 沉淀：23:00 日报 + Cortex-lite 自调 + 推你   │ review + cortex
└────────────────────────────────────────────────┘
```

---

## 何时加载本 skill

- 派 `delegate_task` 之前（必加载）
- 启动 `terminal(background=true)` 长任务之前（必加载）
- 跑每日/每周复盘时
- **会话开头** 必先 `consume_pending()` 拉积压告警

## 核心文件

| 文件 | 作用 |
|---|---|
| `queue.py` | 任务队列（active dict + archive jsonl + mutate + nudge API + level） |
| `watchdog.py` | 后台 watchdog（4 档分类 + 启动验证 + 调 cortex） |
| `push.py` | 共享推送通道（飞书/wecom/notice + consume_pending） |
| `journal.py` | 任务结束写 journal（去重覆盖 + 等级分布） |
| `dispatch.py` | 父级派发统一入口（4 问 + DispatchError + verify_task） |
| `review.py` | 日/周复盘（用 push.py） |
| `cortex.py` | Cortex-lite 自调参（3 规则） |
| `tq.py` | 跨平台 CLI（start/stop/status/review/consume/test） |
| `templates/agent_goal.md` | 子 agent 契约（含 nudge 协议 + 4 问） |
| `cron/daily_review.json` | 23:00 + 周日 22:00 触发复盘 |
| `test_task_queue_v2.py` | 43 项测试 |
| `test_task_queue_v3.py` | 33 项测试（v3 主动推进） |
| `test_task_queue_v4.py` | 31 项测试（Phase 2 4 问 + level + cortex） |

## 数据目录

```
~/.hermes/
├── task-queue/
│   ├── queue.json              ← active 索引（dict: task_id → task）
│   ├── queue.lock              ← 文件锁（msvcrt/fcntl）
│   ├── archive/{date}.jsonl    ← 终态任务按天归档
│   ├── nudges/{task_id}.json   ← watchdog → 子 agent 通信
│   ├── pending_notices.json    ← 飞书/wecom 推送兜底（消费后清空）
│   ├── watchdog.pid            ← watchdog 进程 pid
│   ├── cortex.json             ← Cortex-lite 自调参状态
│   ├── watchdog-stdout.log     ← watchdog 子进程 stdout
│   └── logs/{date}.log         ← watchdog 日志
├── journal/{date}.md           ← 任务留痕
└── reviews/
    ├── daily-{date}.md         ← 每日复盘
    └── weekly-{date}.md        ← 周报
```

---

## 4 层详解

### L0：会话入口（自动）

**触发**：每次 Hermes 会话开始。

**3 个动作**：
1. `consume_pending()` 拉 watchdog 积压告警
2. `tq.py status` 看 watchdog + 活跃任务
3. 列所有 active 任务（带健康度 4 色）

**4 色健康度**：

| 颜色 | 含义 | 你要介入吗 |
|---|---|---|
| 🟢 green | started < 1×stale | 不用 |
| 🟡 yellow | 1×stale ≤ gap < 2×stale，已 nudge | 看一眼 |
| 🟠 orange | 2×stale ≤ gap < 3×stale，已 ping | 可能要介入 |
| 🔴 red | gap ≥ 3×stale / 子 agent 说卡 / 已 escalate | **必看** |

### L1：任务登记

**父级 agent 必走 `tq.enqueue()`**：

```python
from queue import enqueue

# S 任务（轻量，无 4 问）
t = enqueue(goal="修个 typo", agent_role="ops")

# M 任务（4 问可选）
t = enqueue(goal="改个 bug", agent_role="general",
            files=["src/x.py"],
            verify_plan=["pytest tests/x_test.py"],
            deliverable="改后的 x.py + 测试日志")

# L 任务（4 问必填，否则 ValueError）
t = enqueue(goal="重构调度器", agent_role="researcher",
            files=["dispatch.py", "queue.py"],
            verify_plan=["pytest", "integration test", "perf bench"],
            deliverable="新架构 + 性能报告")

# CRITICAL（4 问必填 + deliverable 非空 + 0 自动重试）
t = enqueue(goal="生产 EA 上线", agent_role="coder", level="CRITICAL",
            files=["prod/EA_v10.mq5"],
            verify_plan=["compile pass", "backtest 30 days", "drawdown < 15%"],
            deliverable="EA_v10.mq5 + backtest_report.html")
```

**等级 S/M/L/CRITICAL 必做**：

| 等级 | 必做 | 适用 |
|---|---|---|
| S | 最小验证 + 影响面 1 句话 | typo / 注释 / 小文档 |
| M | 4 问全 + 至少 1 次心跳汇报 | 脚本 / 小功能 / 普通 bug |
| L | 4 问全 + 影响面验证 + 回滚方案 | 跨模块 / 架构 / 模板 |
| CRITICAL | 4 问全 + 人工确认 + 完整验证 + **不许**自动重试 | 数据 / 权限 / 安全 / 生产 |

**role → level 默认映射**：

| role | 默认 level | timeout | heartbeat |
|---|---|---|---|
| ops | S | 120s | 30s |
| tester | M | 600s | 60s |
| general | M | 600s | 60s |
| researcher | L | 1800s | 120s |
| coder | L | 3600s | 120s |

### L2：执行推进（核心：3 档主动推进）

**watchdog 每 60s 扫一次**，按 `gap = now - last_heartbeat` 分类：

| gap 区间 | 档 | watchdog 动作 | 推老大？ |
|---|---|---|---|
| 1×stale ≤ gap < 2×stale | **nudge** | 写 `nudges/{id}.json` 标 `kind=nudge` | ❌ |
| 2×stale ≤ gap < 3×stale | **ping** | 写 nudges 标 `kind=ping` | ❌ |
| 3×stale ≤ gap < timeout | **escalate** | 写 nudges 标 `kind=escalate` + push | ✅ |
| gap ≥ timeout | **timeout** | `mark_timeout` + push | ✅ |

**子 agent 必做**（agent_goal.md 模板内）：

```python
from queue import consume_nudges
nudges = consume_nudges(task_id)
# 收到 nudge → 回 "RESPONDING_TO_NUDGE: 当前在干 X"
# 收到 ping   → 回 "RESPONDING_TO_PING: (1)进度X/N (2)卡在:具体 (3)还要:秒"
# 收到 escalate → **立即冻结**，等老大拍板
```

### L3：验证

**自动 verify_task**（finalize 时）：

| 字段 | 类型 | 要求 |
|---|---|---|
| `path` | str | 绝对路径，`Path(p).resolve()` 验证存在 |
| `size` | int | `Path(p).stat().st_size` 真实值 |
| `hash` | str | **完整 sha256 64 位**（不是前 8 位） |

**不自动重试**：
- ✅ 网络/超时错误 → 自动重试 1 次（标 `retry_reason=transient`）
- ❌ 业务错误 → **绝不**自动重试，标 failed + 推老大

### L4：沉淀

**每日 23:00 daily_review** 输出：
- 任务总数 / 完成率 / 假死率
- 4 档健康度分布
- **按等级 (S/M/L/CRITICAL) 分布** + 假死率
- 平均耗时
- 最慢 TOP3
- 规则违反 TOP3

**Cortex-lite 自调参**（watchdog 累计 3 次 timeout 后触发）：

| 规则 | 触发 | 动作 |
|---|---|---|
| 1. 降级 | 某 role 累计 timeout ≥ 3 | 该 role auto_timeout × 0.5（不低于 30s） |
| 2. 升级 | 某 role 连续 10 次 done 且 L/CRITICAL | 该 role auto_timeout × 1.2（不超原默认 3x） |
| 3. 手动 | 老大手动设值 | 重置自动调参，manual 优先 |

存到 `~/.hermes/task-queue/cortex.json`，enqueue 时读 `get_adjusted_timeout()`。

---

## 数据流与状态机

```
                enqueue()
                    ↓
               ┌─────────┐
               │ queued  │ ← heartbeat("started")
               └────┬────┘
        heartbeat       watchdog 1×stale
        (running)            ↓
            ↓           ┌────────┐
       ┌─────────┐      │ NUDGE  │ ← 写文件
       │ running │←────→└────────┘
       └────┬────┘      
            │            watchdog 2×stale
       mark_done              ↓
            ↓           ┌────────┐
       ┌─────────┐      │  PING  │ ← 写文件
       │  done   │      └────────┘
       └────┬────┘
            │            watchdog 3×stale
       archive               ↓
            ↓           ┌──────────┐
       ┌────────┐        │ESCALATE  │ ← 写文件 + 推
       │ done   │        └──────────┘
       │ archive│
       └────────┘            watchdog ≥timeout
                              ↓
                         ┌─────────┐
                         │ timeout │ ← mark + 推
                         └────┬────┘
                              ↓
                         archive
```

---

## 父级 agent 必走

```python
from queue import enqueue, list_active, get
from dispatch import dispatch, finalize, DispatchError
from push import consume_pending
import cortex

# === 会话开头 ===
notices = consume_pending()           # L0 拉积压告警
for n in notices:
    print(f"[{n['level']}] {n['msg']}")

# === 派任务 ===
try:
    task = enqueue(goal="...", agent_role="coder",
                   files=[...], verify_plan=[...], deliverable="...")
except ValueError as e:                # L 缺 4 问会报
    print(f"入队失败: {e}"); raise

# === 跟踪活跃任务 ===
active = list_active()
for t in active:
    age = time.time() - t['last_heartbeat']
    print(f"{t['task_id']} gap={age}s status={t['status']}")

# === 收尾 ===
finalize(task_id, summary="...",
         artifacts=[{"path": "...", "size": 1234, "hash": "sha256-64位"}])
# finalize 自动：
#   - mark_done（如还在 active）
#   - verify_task() 校验 path/size/sha256
#   - 写 journal
#   - 写 verify 结果进 archive

# === Cortex 手动调 ===
cortex.set_manual("coder", 3600)       # 老大拍板 timeout
cortex.reset("coder")                  # 重置自动调参
```

---

## Makefile / tq.py 入口

```bash
# Makefile（Linux/macOS）
make start    # 启动 watchdog（后台，60s 扫描）
make stop     # 停 watchdog
make status   # 看状态 + 活跃任务健康度
make review   # 今日 review（不推）
make consume  # 拉积压告警并清空
make test     # 跑 107 项测试

# tq.py（跨平台，Windows 用这个）
python ~/.hermes/skills/task-queue/tq.py start
python ~/.hermes/skills/task-queue/tq.py status
python ~/.hermes/skills/task-queue/tq.py consume
python ~/.hermes/skills/task-queue/tq.py review
python ~/.hermes/skills/task-queue/tq.py test
```

---

## 推送通道优先级

1. **飞书 webhook**（FEISHU_WEBHOOK_URL 环境变量）
2. **企业微信 webhook**（WECOM_WEBHOOK_URL 环境变量）
3. **本地 notice 文件**（`pending_notices.json`，Hermes 会话开头 consume_pending 消费）

失败/超时 **100% 推送**；nudge/ping **不打扰**老大。

---

## 验收标准（已达成）

- [x] 队列分文件不爆（active dict + archive jsonl）
- [x] mutation 重入安全（mutate(fn)）
- [x] 批量 mark_timeout（一次锁）
- [x] watchdog 启动后真验证子进程活着（sleep + log_marker）
- [x] dispatch 失败必 raise（DispatchError）
- [x] journal 写前查重覆盖
- [x] L/CRITICAL 必填 4 问（files/verify_plan/deliverable）
- [x] mark_timeout 写真 status="timeout"
- [x] finalize 自动 verify_task
- [x] consume_pending 主动消费
- [x] 主动推进 3 档（nudge/ping/escalate）+ 子 agent RESPONDING 契约
- [x] Cortex-lite 累计 3 次超时自动降 + 手动 override 优先
- [x] render_daily 加等级分布

## 测试覆盖

| 测试套 | 项数 | 内容 |
|---|---|---|
| v2 | 43 | 队列+mutate+verify+dispatch+journal+role 默认+迁移 |
| v3 | 33 | nudge 写消费 + 3 档分类 + 升级覆盖 + 边界 + status 4 色 |
| v4 | 31 | 4 问必填 + L/CRITICAL 校验 + level 默认 + cortex 降级 + render_daily 等级分布 |
| **总** | **107** | **全绿** |

## 部署状态

- watchdog: pid 6604 跑着，interval=60s
- 数据目录: `~/.hermes/task-queue/`（**不**放 `~/.mavis/`）
- 测试: `python ~/.hermes/skills/task-queue/test_task_queue_v4.py`

## 与其他仓库借鉴的关系

| 来源 | 学什么 | 不学什么 |
|---|---|---|
| scale-engine (npm) | 证据闭环（verify_task）、任务等级、Cortex-lite | 6 阶段、6 角色、3 引擎、npm CLI |
| project-scaffold | 4 问 checklist、Makefile 入口、S 级豁免 | 强制建任务目录、3 个 agent 文件重复 |
| task-queue v1/v2（自身） | 队列持久化、心跳契约、verify_task | 静默假死（v3 已根治） |

## Phase 演进

- ✅ **Phase 1** (v2)：队列分文件 + mutate + 4 档推送 + verify
- ✅ **Phase 2** (v3+Phase 2)：3 档主动推进 + 4 问 + 任务等级 + Cortex-lite
- ⏳ **Phase 3**：ship 闭环（verify → journal → 推 done 报告）+ Task DAG（parent/depends_on 拓扑排序）
- ⏳ **Phase 4**：跨 session resume（从 journal 重建 task 上下文）+ 多 Hermes 协调

## 设计哲学（不变量）

1. **0 编造**：路径/size/hash 不准编，没做就是没做
2. **0 敷衍**："已发"必须真验证
3. **速度敏感**：治理不能拖慢交付
4. **拍板在老大**：nudge/ping AI 间，escalate/timeout 才推你
5. **轻量优先**：不抄 scale-engine 全家桶，5 个 CLI 命令够用
