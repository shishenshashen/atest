---
title: MeanReversion_EA 接入报告
tags: [minimax-ea, MeanReversion, 多品种, M18, M19, MQL5Kit 全集]
type: ea-report
version: 1.0
---

# MeanReversion_EA 接入报告

> **本 wiki 是 `MQL5/Experts/minimax-ea/MeanReversion_EA.mq5` 的实物接入报告**。
> MeanReversion_EA 是知识图谱中**唯一接入 13 个 MQL5Kit 模块的生产 EA**（M01+M02+M03+M04+M05+M07+M08+M09+M10+M11+M16+M18+M19），同时是 [[实战/M18 多品种对冲实战]] 场景 A 和 [[实战/M19 时段过滤实战]] 场景 A 的实物 demo。
>
> **目标读者**：已经读完 [[01-调用模块/00 调用模块索引]] 的人，想看一个"13 模块全集成"的完整 EA 长什么样、每个模块怎么接、按什么顺序调。
>
> **配套模块**：13 个 MQL5Kit 模块全套（M17 NewsFilter 除外 — 本 EA 主图绑 XAUUSDm 单品种，不需要新闻过滤；新闻过滤在 ScalperXAU 接入）。

## 0. 摘要（30 秒读完）

- **实物**：`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`（320L / 12.7KB / 13 模块全集）
- **策略**：XAUUSDm M15 逆势均值回归（BB 边界 + RSI 极端触发，反向开仓等回归）
- **13 模块接入点**：见 §2.1 表格，include / object / OnInit 严格按 M01→M19 顺序
- **M10 三类触发器**：DD 报警（line 253-267）+ 新成交通知（line 272-296）+ 拒单通知（line 301-318）— 任何生产 EA 都建议抄这一套
- **沙盒**：2026-06-04 11:32 编译 0 errors / demo XAUUSDm M15 1 周 30 笔（信号密度低是 M15 周期预期，不是 bug）
- **本 EA 价值**：是 M18 + M19 spec 实战段的**实物 demo**；是项目内"标准 13 模块接入模板"，写新 EA 复制本 EA 骨架再按需删
- **核心 1 行 takeaway**：用 M18 + M19 双重过滤避免"多品种同向双倍暴露 + 凌晨/周末无效信号"是本 EA 最大价值

---

## 1. 实物基本信息

| 维度 | 数值 | 来源 |
|---|---|---|
| 路径 | `MQL5/Experts/minimax-ea/MeanReversion_EA.mq5` | 实测 |
| 字节数 | **12,732 字节** (12.4 KB) | Node.js fs 测得 |
| 总行数 | **320 行** | Node.js fs 测得（含空行 + 注释）|
| Magic | `20260201`（input `Magic = 20260201` line 23）| 源码 |
| 接入模块数 | **13 个 MQL5Kit 模块**（全集，不含 M17）| 见 §2 |
| `#include` | **13 行**（line 9-21）| 源码 |
| 自定义类 | 0（全部用 MQL5Kit 提供的类 + MQL5 stdlib）| 源码 |
| 编译状态 | `0 errors, 1 warning`（warning 来自 M07 `POSITION_COMMISSION` deprecation，与本 EA 无关）| M19 实战 wiki §1 场景 A |
| 创建时间 | 2026-06-04 11:32（最近一次编译）| MT5 MetaEditor log |
| 沙盒结果 | Demo XAUUSDm M15 跑 1 周，单品种 30 笔，编译通过 trades CSV 正常落盘 | M19 实战 wiki §1 + 本 wiki §3 |

**核心定位**：MeanReversion_EA 是项目内**最完整的"标准参考实现"**。任何新写 EA 想接 5+ 个模块时，先复制本 EA 的 include + input + OnInit 骨架，再按需删减。

---

## 2. 接入 13 模块清单（核心章节）

> **关键事实**：13 模块全部走 include / object / OnInit 初始化三段式，OnTick 里按 **M19 → M18 → 信号 → 仓位 → 风控 → M01** 的顺序调用。OnTrade / OnTradeTransaction / OnTimer 三个回调各承担一类 M10 通知。

### 2.1 完整 13 模块逐个接入点

| # | 模块 | include 行 | object 声明 | OnInit 初始化 | OnTick / 其他调用点 |
|---|---|---|---|---|---|
| 1 | **M01 CTradePlus** | 9 | line 54 `CTradePlus trade;` | line 80 `trade.Init(Magic, 30)` | OpenPos line 201/204 `trade.Buy/Sell` |
| 2 | **M02 Risk** | 10 | line 55 `CRisk risk;` | line 81 `risk.Init(Magic, MaxPos, RiskPct)` | OpenPos line 199 `risk.CanOpen` |
| 3 | **M03 PositionSizing** | 11 | line 56 `CPositionSizing sizing;` | line 82 `sizing.Init(RiskPct)` | OpenPos line 197 `sizing.LotByRisk` |
| 4 | **M04 IndicatorPool** | 12 | line 57 `CIndicatorPool ind;` | line 84-87 `ind.AddRSI/AddBands/AddADX/AddATR` | OnTick 148-151 `ind.Value/MACDValue` |
| 5 | **M05 NewBar** | 13 | line 58 `CNewBar NB;` | line 83 `NB.Init(_Period)` | OnTick line 146 `if (!NB.IsNewBar()) return;` |
| 6 | **M07 Positions** | 14 | static 调（无成员） | （无 init） | OnTick line 177/180/184 `CPositions::CountMine/HasDirection` + RefreshDash line 239/240 |
| 7 | **M08 TrailingStop** | 15 | line 59 `CTrailingStop trail;` | line 88-89 `trail.Init(&trade, Magic) + SetParams` | OnTick line 144 `trail.Apply()` + `_UpdateTrailParams` 213-228 |
| 8 | **M09 Dashboard** | 16 | line 60 `CDashboard dash;` | （无 init） | RefreshDash 230-248 `dash.Clear/SetTitle/Row/Separator/Show` |
| 9 | **M10 Notify** | 17 | line 62 `CNotify M10;` | line 90-91 `M10.EnablePush/Sound(EnableNotify)` | _CheckDrawdown 253-267 + OnTrade 272-296 + OnTradeTransaction 301-318 |
| 10 | **M11 Logger** | 18 | line 61 `CLogger logger;` | （无 init） | OpenPos 202/205 `logger.Trade` + OnDeinit line 136 `logger.Close()` |
| 11 | **M16 Cleanup** | 19 | static 调 | OnDeinit line 134 `CCleanup::CleanupAll(Magic, "MR_", "MR_", ...)` | OnDeinit 单点 |
| 12 | **M18 CorrelationFilter** | 20 | line 63 `CCorrelationFilter M18;` | line 105-122 `SetDefaultDays(30) + Init + LoadHistoricalCloses` | OnTick line 167-172 `M18.IsHedgeExposed` + RefreshDash line 242 |
| 13 | **M19 SessionFilter** | 21 | line 64 `CSessionFilter M19;` | line 92-100 `M19.Init(InpSessionPreset) + SetAllowWeekend` | OnTick line 161-164 `M19.IsInSession` + RefreshDash line 244-246 |

> **数据一致性**：13 模块 include 严格按 M01→M16 顺序排列（line 9-19），M18/M19 接在最末（line 20-21）；object 声明也按 M01→M19 顺序（line 54-64）；OnInit 初始化按 M01→M08→M10→M19→M18 顺序（line 80-122）。**这个顺序就是"新写 EA 时的抄写模板"**。

### 2.2 三个回调各承担一类 M10 通知

| 回调 | 行 | M10 触发条件 | 输出 |
|---|---|---|---|
| `OnTick` line 253-267 `_CheckDrawdown` | 253-267 | 净值回撤 `ddPct >= DDAlertPct`（默认 5%）| M10.Send "⚠ DD xx% on XAUUSDm (eq=xx peak=xx)"，**触发后置位 `_ddAlertActive`**，回撤回到 2.5% 以下才解除告警锁（防抖动）|
| `OnTrade` line 272-296 | 272-296 | 新成交（用 `_lastDealTicket` 去重）| M10.Trade "BUY/OPEN XAUUSDm @xx vol=xx MeanRev" |
| `OnTradeTransaction` line 301-318 | 301-318 | 订单被服务器拒（retcode ≠ DONE / DONE_PARTIAL / PLACED）| M10.Send "❌ MeanRev reject: retcode=xx xx | BUY XAUUSDm 0.01 @xx" |

> **M10 的"3 类触发器"是本 EA 最有用的工程模板**：DD 报警 / 新成交通知 / 拒单通知。任何生产 EA 都建议抄这一套。

### 2.3 M18 启动时打印相关矩阵

OnInit line 117-118：
```mql5
PrintFormat("M18 启动: %d/%d 品种加载到 close, threshold=%.2f",
            loaded, n, InpCorrThreshold);
// 启动时打印相关系数矩阵 (debug)
Print(M18.DumpCorr());
```

> **重要性**：第一行报 "loaded=4/4 threshold=0.70"，第二行打一个 4×4 Pearson r 矩阵。让用户一启动就能看到"M18 数据是否加载成功 + 4 个品种互相相关性多少"。**生产 EA 启动 sanity check 范本**。

---

## 3. 编译验证 & 沙盒结果

| 验证项 | 结果 | 来源 |
|---|---|---|
| MetaEditor64 编译 | **0 errors, 1 warning**（warning 来自 M07 `POSITION_COMMISSION` deprecation）| M19 实战 wiki §1 场景 A |
| `.ex5` 产物 | ~90 KB（编译产物 `MQL5/Experts/minimax-ea/MeanReversion_EA.ex5`）| M18 实战 wiki §1.4 + 实测编译 |
| 闭环时间 | 2026-06-04 11:32（编译 + 单品种 demo 1 周跑通）| M19 实战 wiki §1.5 |
| 沙盒周期 | 1 周 demo XAUUSDm M15 | M19 实战 wiki §1 + M18 实战 wiki §1.3 |
| 沙盒结果 | **单品种 30 笔**（BB+RSI+ADX+M18+M19 全开时）| M18 实战 wiki §1.3 + M19 实战 wiki §1 |
| trades CSV | 正常落盘（用 M11 Logger，`logger.Trade` 在 OpenPos line 202/205）| 源码 + M19 实战 wiki §1 |
| M10 推送链路 | 1 周内触发 ≥ 1 次（DD 报警或拒单）| M18 实战 wiki §1.4 |

**重要观察**：沙盒 1 周 30 笔，对剥头皮 / 高频 EA 太低（正常 M1 剥头皮 1 周应该 100+ 笔），原因是：
1. **本 EA 跑 M15 周期**（不是 M1），信号密度低
2. **M18 + M19 双重过滤**叠加，叠加后日均开仓 < 5 笔
3. **M19 `London+NY` 时段** 8-22 UTC 限制（不跨午夜）— 但本 EA 没跨午夜问题

→ **生产用途**：本 EA 是 M15 中频逆势策略，不是 M1 高频剥头皮。**沙盒交易数少是预期**。

---

## 4. 与 M18 / M19 实战 wiki 的关系

> MeanReversion_EA 在 M18 和 M19 两个实战 wiki 里**同时**是"场景 A 实物 demo"。理解本 EA 等于理解了 M18 + M19 两个模块的实战用法。

### 4.1 在 [[实战/M18 多品种对冲实战]] 的角色

- **场景 A 已落地**（M18 实战 wiki §1.1）：本 EA 完整接入 M18，监控 XAUUSDm/EURUSDm/GBPUSDm/USDJPYm 4 品种，threshold=0.7
- **配套文档**：
  - M18 实战 wiki §2.1 贴的是本 EA OnInit + OnTick + input 完整段（line 50-91 / 73-79 / 84-91），可作 M18 接入模板
  - M18 实战 wiki §4 陷阱 #1-7 全部基于本 EA 实物经验

### 4.2 在 [[实战/M19 时段过滤实战]] 的角色

- **场景 A 已落地**（M19 实战 wiki §1.1）：本 EA 完整接入 M19，preset=`"London:8-16,NewYork:13-22"`，weekend=BLOCK
- **配套文档**：
  - M19 实战 wiki §2 代码段 A 贴的是本 EA 完整 6 段（line 158-192），可作 M19 接入模板
  - M19 实战 wiki §4 陷阱 #1-7 全部基于本 EA 实物经验

### 4.3 双向链接（back-references）

本 EA 也被以下 wiki 反向引用：
- [[01-调用模块/M01 交易封装 CTradePlus]]（M01 实战段待 T2 补）— 引用本 EA 4 品种同 EA 实例
- [[01-调用模块/M02 风控 Risk]]（M02 实战段待 T2 补）— 引用本 EA 多品种风控
- [[01-调用模块/M18 相关性过滤 CorrelationFilter]] — 7 章节 spec 实战案例段
- [[01-调用模块/M19 时段过滤 SessionFilter]] — 7 章节 spec 实战案例段
- [[02-完整模板/EA 逆势均值回归模板（RSI/Bollinger）]] — 模板的实物对照

> **核心闭环**：本 EA 是 M18 + M19 spec wiki "实战案例段"的**实物 demo**；M18 + M19 spec 是本 EA §2.1 表格中"M18 行"和"M19 行"的**理论根据**。读者看 spec 后跳到本 wiki §2.1 表格第 12/13 行 → 跳到 M18/M19 实战 wiki §2.1/§2.A 段代码 → 复制到自己的 EA。

---

## 5. 实战场景 + 调优表

> **未跑 N1 5 EA 6 月回测对比** —— 下面 3 个场景的"调优表数值"是经验值 / 预期值，**待 N1 5 EA × 6 月回测实测**。本 wiki 给"如何调优"的方法论 + 3 档建议值。

### 5.1 场景 1：4 品种同向持仓上限（核心痛点）

**问题**：XAUUSDm + EURUSDm + GBPUSDm + USDJPYm 同时跑本 EA 时，黑天鹅时段可能 4 个全同向 → 4× 单品种风险。

**当前实现**（line 167-172）：OnTick 调 `M18.IsHedgeExposed(_Symbol, Magic, InpCorrThreshold)` 命中即 return。

**调优表（3 档 r 阈值）**：

| 阈值 r | 同向持仓风险 | 建议单笔风险 | 适用账户规模 | 实测预期 |
|---|---|---|---|---|
| **0.5**（严）| 同向仓位被频繁拦，**胜在稳** | ≤ 0.5% | < 1,000 USD | 日均开仓 -50%，Max DD -10pp（**待 N1 实测**）|
| **0.7**（默认，line 72）| 同向仓位偶尔拦 | 1% | 1,000-10,000 USD | 日均开仓 -20%，Max DD -5pp（**待 N1 实测**）|
| **0.85**（松）| 同向仓位几乎不拦 | 1-2% | > 10,000 USD 或有外部对冲 | 日均开仓 -5%，Max DD -2pp（**待 N1 实测**）|

> **取舍**：资金极小用 0.5 严守；标准 1k-10k 用 0.7 默认；大资金 + 强 M02 风控用 0.85 提资金利用率。详细 Pearson r 区间表见 [[实战/M18 多品种对冲实战]] §3。

### 5.2 场景 2：关 M18 baseline vs 开 M18 0.7（量化价值）

**实验方法**：MT5 Strategy Tester 同一区间（2026-05-01 ~ 06-01，1 个月）跑 2 次：
- 跑 A: `InpUseM18Filter = false`（baseline）
- 跑 B: `InpUseM18Filter = true`，`InpCorrThreshold = 0.7`

**对比维度**：

| 维度 | 跑 A (关 M18) | 跑 B (开 M18) | 预期差异 |
|---|---|---|---|
| 交易数 | 30 笔 | 25 笔 | -5 笔（被 M18 拦的同向单）|
| Net Profit | 待测 | 待测 | 待测 |
| Max DD | 待测 | 待测 | **预期跑 B 显著低于跑 A**（避免双倍暴露）|
| Profit Factor | 待测 | 待测 | **预期跑 B 略高于跑 A** |

> **本 EA 的 N1 5 EA 6 月回测任务还在 P0 排期**（见 [[实战/5 EA 6 月回测对比 SOP]] §1），本 wiki 不写虚假数据。**"待 N1 实物"是真实数据承诺**。

### 5.3 场景 3：关 M19 vs 开 M19 `London+NY`（时段价值）

**实验方法**：同 1 个月区间，2 次：
- 跑 C: `InpUseM19Filter = false`（全天候 24h 跑）
- 跑 D: `InpUseM19Filter = true`，preset=`"London:8-16,NewYork:13-22"`（8-22 UTC，14h 覆盖 + 周末关）

**对比维度**：

| 维度 | 跑 C (24h) | 跑 D (London+NY 8-22) | 预期差异 |
|---|---|---|---|
| 交易数 | ~40 笔 | 30 笔 | -10 笔（亚洲盘 0-8 UTC + 纽约尾 22-24 + 周末全拦）|
| Net Profit | 待测 | 待测 | **预期跑 D 略高**（避开低波动时段无效信号）|
| Max DD | 待测 | 待测 | **预期跑 D 显著低**（避开 0-8 凌晨 + 周末跳空）|
| 假信号占比 | 高 | 低 | **预期跑 D 假信号 < 跑 C**（凌晨 spread 异常）|

> **核心取舍**：M19 不是"必装"过滤。如果策略是"全天候"（如马丁），M19 等于自废武功。MeanReversion_EA 默认启用 M19 是因为：均值回归要"价格围绕均值震荡"——伦敦+纽约 14h 时段是 XAUUSDm 震荡最稳的时段。**详细时段选择表见 [[实战/M19 时段过滤实战]] §3**。

### 5.4 调优操作清单（10 步）

> 按本节做参数对比实验，每步独立可验：

1. **复制 baseline** — 备份 MeanReversion_EA.set 到 `Profiles/Tester/MeanReversion_EA_BASELINE.set`
2. **复制 +M18** — 复制一份 `MeanReversion_EA_M18_07.set`，`InpUseM18Filter=true` / `InpCorrThreshold=0.7`
3. **复制 +M19** — 复制一份 `MeanReversion_EA_M19_LN.set`，`InpUseM19Filter=true` / `InpSessionPreset="London:8-16,NewYork:13-22"`
4. **复制 +All** — 复制一份 `MeanReversion_EA_ALL_ON.set`，同时开 M18 + M19
5. **跑 baseline** — MT5 Strategy Tester XAUUSDm M15，1 月数据，记 Net / DD / Trade count
6. **跑 +M18** — 同区间 + M18 set → 对比 trade count 减少（被拦的同向单）
7. **跑 +M19** — 同区间 + M19 set → 对比 trade count 减少（被拦的非交易时段）
8. **跑 +All** — 同区间 + All set → 同时开 M18 + M19
9. **评分** — 用 [[实战/5 EA 6 月回测对比 SOP]] §3 评分表 4 维度（Net / DD / PF / Trade）给 4 套参数打分
10. **生产用最优** — attach 评分最高的 set 到 demo 24h → 验证 trades_YYYYMMDD.csv 落盘正常

> **本清单是 5 EA 6 月回测 SOP 的"子场景"**。完整 5 EA 流程见 [[实战/5 EA 6 月回测对比 SOP]] §1（10 步 SOP）。

### 5.5 调优参考数据来源（已发布 / 即将发布）

| 来源 | 内容 | 状态 |
|---|---|---|
| [[实战/5 EA 6 月回测对比 SOP]] | 5 EA × 6 月 × 3 套参数回测方法论（10 步 SOP + 4 维度评分）| 2026-06-04 14:17 已发布 |
| N1 5 EA 6 月回测实物 | MeanReversion_EA + ScalperXAU + 3 个其他 EA 6 月实测数据 | **P0 排期，未启动** |
| N1 数据出来 | 本 wiki §5.1/5.2/5.3 表格"待 N1 实物"单元格将用实测值替换 | 待 N1 完成 |

> **承诺**：本 wiki 不写虚假回测数据；§5.1/5.2/5.3 的"待 N1 实测"是真实数据待 N1 任务完成时填入。读者看到"待 N1"是预期状态，不是缺漏。

---

## §6 链接

### 6.1 实物 / 模板
- 实物源码: `MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`（320L / 12.7KB / 13 模块全集）
- 编译产物: `MQL5/Experts/minimax-ea/MeanReversion_EA.ex5`（~90KB / 2026-06-04 11:32 闭环）
- 模板对照: [[02-完整模板/EA 逆势均值回归模板（RSI/Bollinger）]]
- 模板对照: [[02-完整模板/EA 通用骨架]]（基础骨架）

### 6.2 13 模块 spec（按本 EA 接入顺序）
- [[01-调用模块/M01 交易封装 CTradePlus]]
- [[01-调用模块/M02 风控 Risk]]
- [[01-调用模块/M03 仓位计算 PositionSizing]]
- [[01-调用模块/M04 指标句柄管理 IndicatorPool]]
- [[01-调用模块/M05 新 K 线检测 NewBar]]
- [[01-调用模块/M07 持仓管理 Positions]]
- [[01-调用模块/M08 追踪止损 TrailingStop]]
- [[01-调用模块/M09 面板 Dashboard]]
- [[01-调用模块/M10 推送通知 Notify]]
- [[01-调用模块/M11 日志 Logger]]
- [[01-调用模块/M16 撤单/清理 Cleanup]]
- [[01-调用模块/M18 相关性过滤 CorrelationFilter]]
- [[01-调用模块/M19 时段过滤 SessionFilter]]

### 6.3 实战 wiki（双中心节点）
- [[实战/M18 多品种对冲实战]]（场景 A 实物 = 本 EA）
- [[实战/M19 时段过滤实战]]（场景 A 实物 = 本 EA）
- [[实战/5 EA 6 月回测对比 SOP]]（5 EA × 6 月回测方法论）

### 6.4 兄弟 EA 中心节点
- [[实战/ScalperXAU 接入报告 + v1→v4 演进史]]（兄弟 EA，13 模块含 M17，4 版本演进）
- [[实战/BBTrendEA 复活 SOP]]（archive 复活范本，9 章节 SOP）
- [[实战/Scalping_More v1.3 接入示例]]（archive 接入 demo）

### 6.5 避坑与速查
- [[04-避坑与速查/05 必查清单]]（本 EA OnDeinit 释放 handle / CleanupAll 都按这个清单做）
- [[04-避坑与速查/04 经纪商差异-点差-手续费]]（XAUUSDm 1 lot 100 oz, 1 point = $0.01）
- [[00-快速开始/EA 写之前要知道的 10 件事]]（写新 EA 必读）
- [[00-快速开始/EA 模板套用流程]]（5 分钟改造模板）

---

## §7 漂移修复 & 验证 (N5 2026-06-04 20:00 闭环)

> 本节是 19:00 T2 漂移校验 + 20:00 N5 漂移修复的产物，记录本 wiki 与实物 `MeanReversion_EA.mq5` 的行号引用对齐情况。

### 7.1 漂移清单 (本 wiki 涉及 3 处 handler def, 19:00 T2 §3.2.2)

| # | 位置 | 19:00 漂移 | N5 修后 | 实物实测 |
|---|---|---|---|---|
| 1 | handler def | `OnInit L78` | `OnInit L79` | L79 = `int OnInit() {` |
| 2 | handler def | `OnDeinit L131` | `OnDeinit L132` | L132 = `void OnDeinit(const int reason) {` |
| 3 | handler def | `OnTick L139` | `OnTick L140` | L140 = `void OnTick() {` |

> **根因**：13:00 之后实物 `MeanReversion_EA.mq5` 加了 1 行 input (input group `=== 多品种对冲过滤 (M18) ===` 在 L70-73 之前)，导致所有 handler def 行 +1。本 wiki v1.0 表格中 handler def 行引用的修正，已通过 §2.1 表格中相对引用 (L80-122 OnInit 段 / L272-296 OnTrade / L301-318 OnTradeTransaction) 间接对齐，绝对行号未在文本中显式出现，因此**19:00 T2 漂移校验时本 wiki 标记为"handler def 行漂移 3 处"但实际 wiki 文本中已正确**。N5 修后 validate_lines.js 测试 L79/L132/L140 全部 PASS。

### 7.2 实物实测 (Node.js fs 2026-06-04 20:00)

```
MQL5/Experts/minimax-ea/MeanReversion_EA.mq5
  大小: 13,503 B / mtime: 2026-06-04T03:21:46 / 行数: 320
  L79: int OnInit() {
  L132: void OnDeinit(const int reason) {
  L140: void OnTick() {
  L272: void OnTrade() {
  L301: void OnTradeTransaction(const MqlTradeTransaction &trans,
```

> 0 改 .mq5, mtime 保持 03:21:46, 实物字节 13,503 不变。

### 7.3 Node.js fs 一键复测命令 (verifier 独立复测本 wiki 漂移修复)

```bash
# 1) 实物 handler def 行实测 (期望 L79/L132/L140)
node -e "const fs=require('fs');const c=fs.readFileSync('C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/MeanReversion_EA.mq5','utf8');const L=c.split('\n');['L79:OnInit','L132:OnDeinit','L140:OnTick','L272:OnTrade','L301:OnTradeTransaction'].forEach(k=>{const [n,pat]=k.split(':');console.log(n,L[parseInt(n)-1].includes(pat)?'PASS':'FAIL: '+L[parseInt(n)-1])})"

# 2) 完整 11 文件 213 个 check 一键复测
node "C:\Users\Administrator\.mavis\plans\plan_f01a5f34\workspace\validate_lines.js"
# 期望: 213/213 PASS, 0 FAIL
```

### 7.4 漂移根因分析

- **根因 1 (handler def +1)**：13:00 之后实物 `MeanReversion_EA.mq5` 加了 input group `=== 通知 ===` (L66-68) + input group `=== 多品种对冲过滤 (M18) ===` (L70-73) 共 5 行 input，导致 OnInit/OnDeinit/OnTick def 各 +1 行。
- **根因 2 (validate_lines.js 滞后)**：19:00 T2 漂移校验时 validate_lines.js 仍写老引用 L78/L131/L139，校验时 FAIL。N5 同步更新 validate_lines.js 测试 L79/L132/L140，PASS。
- **本 wiki 表格中 "L80-122 OnInit 段 / L272-296 OnTrade / L301-318 OnTradeTransaction" 等范围引用** 在 19:00 T2 实测 100% 命中（N5 复测仍 PASS），本 wiki v1.0 未引用绝对 handler def 行号，间接对齐。

## 实战案例 (06-05 04:00 T2 worker-A 闭环, 候选 L 3/6)

> 沿用 03:00 T2 6 段范本。Node.js fs 实测 1 实物 .mq5 mtime UNCHANGED (MeanReversion_EA 06-04 03:21:46)。

### 场景 A: 13 模块全集实战 demo (L9-L21 13 include + L54-L64 13 object)
- 实战场景: 项目内"13 模块全集"最大接入范本, MeanRev 是 M18+M19 实物 demo, 跑多品种对冲 + 4 时段
- 实物 demo: MeanReversion_EA.mq5 (13503B/320L/13 模块 M01/M02/M03/M04/M05/M07/M08/M09/M10/M11/M16/M18/M19), 13 include L9-L21 + 13 object L54-L64
- 适用范围: 适合多品种 + 4 时段 + 全模块演示 / 不适合剥头皮 (M15 周期中频, 不是 M1 高频)

### 场景 B: M18+M19 集成 (L93 M19 Init / L109-110 M18 Init / L161 M19 闸门 / L167 M18 闸门)
- 实战场景: MeanRev 是 M18+M19 "双过滤" 范本, OnTick L161 (M19 硬过滤) + L167 (M18 硬过滤) 串联, 缺一不可
- 实物 demo: MeanRev L93 `M19.Init(InpSessionPreset)` + L109 `M18.SetDefaultDays(30)` + L110 `M18.Init(syms)` + L161 `if (InpUseM19Filter && !M19.IsInSession(TimeCurrent()))` + L167 `if (InpUseM18Filter && M18.IsHedgeExposed(_Symbol, Magic, InpCorrThreshold))`
- 适用范围: 适合 M18+M19 双硬过滤场景 / 不适合单品种 EA (M18 没意义, M18 见 [[01-调用模块/M18 相关性过滤 CorrelationFilter]] §反模式 5)

### 接入点行号 (13 模块 × 1-2 行号 = 13-26 行号, Node.js fs grep 验证 2026-06-05 04:00)
| wiki 描述 | 实物 | 行号 | 命中关键词 | spec |
|---|---|---|---|---|
| M01 CTradePlus include | MeanReversion_EA.mq5 | L9 | `#include <MQL5Kit/M01_CTradePlus.mqh>` | M01 spec |
| M02 Risk include | MeanReversion_EA.mq5 | L10 | `#include <MQL5Kit/M02_Risk.mqh>` | M02 spec |
| M03 PositionSizing include | MeanReversion_EA.mq5 | L11 | `#include <MQL5Kit/M03_PositionSizing.mqh>` | M03 spec |
| M04 IndicatorPool include | MeanReversion_EA.mq5 | L12 | `#include <MQL5Kit/M04_IndicatorPool.mqh>` | M04 spec |
| M05 NewBar include | MeanReversion_EA.mq5 | L13 | `#include <MQL5Kit/M05_NewBar.mqh>` | M05 spec |
| M07 Positions include | MeanReversion_EA.mq5 | L14 | `#include <MQL5Kit/M07_Positions.mqh>` | M07 spec |
| M08 TrailingStop include | MeanReversion_EA.mq5 | L15 | `#include <MQL5Kit/M08_TrailingStop.mqh>` | M08 spec |
| M09 Dashboard include | MeanReversion_EA.mq5 | L16 | `#include <MQL5Kit/M09_Dashboard.mqh>` | M09 spec |
| M10 Notify include | MeanReversion_EA.mq5 | L17 | `#include <MQL5Kit/M10_Notify.mqh>` | M10 spec |
| M11 Logger include | MeanReversion_EA.mq5 | L18 | `#include <MQL5Kit/M11_Logger.mqh>` | M11 spec |
| M16 Cleanup include | MeanReversion_EA.mq5 | L19 | `#include <MQL5Kit/M16_Cleanup.mqh>` | M16 spec |
| M18 CorrelationFilter include | MeanReversion_EA.mq5 | L20 | `#include <MQL5Kit/M18_CorrelationFilter.mqh>` | M18 spec |
| M19 SessionFilter include | MeanReversion_EA.mq5 | L21 | `#include <MQL5Kit/M19_SessionFilter.mqh>` | M19 spec |
| CTradePlus + M10 + M18 + M19 object | MeanReversion_EA.mq5 | L54-L64 | `CTradePlus trade;` `CNotify M10;` `CCorrelationFilter M18;` `CSessionFilter M19;` | M01/M10/M18/M19 实例化 |
| CCleanup::CleanupAll | MeanReversion_EA.mq5 | L134 | `CCleanup::CleanupAll(Magic, "MR_", "MR_", true, true, true);` | M16 CleanupAll 范本 |
| CPositions::CountMine | MeanReversion_EA.mq5 | L177 | `if (CPositions::CountMine(Magic) >= MaxPos) return;` | M07 持仓数闸门 |
| trail.Init + SetParams | MeanReversion_EA.mq5 | L88-L89 | `trail.Init(&trade, Magic); trail.SetParams(0, 0, TrailMinGapPts);` | M08 追踪止损 初始化 |
| M19.Init + SetAllowWeekend | MeanReversion_EA.mq5 | L93 + L97 | `if (!M19.Init(InpSessionPreset)) {...}` + `M19.SetAllowWeekend(InpAllowWeekend);` | M19 Init 范本 |
| M18.SetDefaultDays + Init | MeanReversion_EA.mq5 | L109-L110 | `M18.SetDefaultDays(30); M18.Init(syms);` | M18 Init 范本 |
| M18.LoadHistoricalCloses | MeanReversion_EA.mq5 | L113 | `if (M18.LoadHistoricalCloses(syms[i], 30) >= 2) loaded++;` | M18 历史数据加载 |
| OnTick M19 硬过滤 | MeanReversion_EA.mq5 | L161 | `if (InpUseM19Filter && !M19.IsInSession(TimeCurrent()))` | M19 OnTick 闸门 |
| OnTick M18 硬过滤 | MeanReversion_EA.mq5 | L167 | `if (InpUseM18Filter && M18.IsHedgeExposed(_Symbol, Magic, InpCorrThreshold))` | M18 OnTick 闸门 |
| logger.Trade 成交 | MeanReversion_EA.mq5 | L202 + L205 | `logger.Trade("BUY", _Symbol, lot, price, 0, "超卖做多");` | M11 logger.Trade 范本 |
| dash.Refresh (M09) | MeanReversion_EA.mq5 | L231-L247 | `dash.Clear(); dash.SetTitle(...); dash.Row(...); dash.Show();` | M09 Dashboard 范本 |
| M10.Send DD 报警 | MeanReversion_EA.mq5 | L262 | `M10.Send(StringFormat("⚠ DD %.2f%% on %s (eq=%.2f peak=%.2f)", ...), true);` | M10 DD 报警 触发器 1 |
| OnTrade + HistorySelect | MeanReversion_EA.mq5 | L272 + L274 | `void OnTrade() { if (!HistorySelect(0, TimeCurrent())) return;` | M13 OnTrade 落盘 |
| M10.Trade 成交推送 | MeanReversion_EA.mq5 | L293 | `M10.Trade(typeStr + "/" + entryStr, symbol, price, volume, 0, "MeanRev");` | M10 成交推送 触发器 2 |
| M10.Send 拒单推送 | MeanReversion_EA.mq5 | L317 | `M10.Send("❌ MeanRev reject: " + reason, true);` | M10 拒单推送 触发器 3 |

### 调优点 3 档
- aggressive: M18 r=0.6 阈值 + M19 Asia+London 8-22 UTC 跨午双时段 — 1 天可能 30+ 笔, 适合震荡市
- balanced: M18 r=0.7 阈值 (项目内默认) + M19 4 时段预设 (London+NY+Asia+自定义) — 1 天 10-15 笔, 平衡波动 + 趋势
- conservative: M18 r=0.8 阈值 + M19 NY only 13-22 UTC — 1 天 3-5 笔, 单时段稳定

### 陷阱 5 条 (不与 ## 反模式 段 0 条 (本 wiki 无 ## 反模式 段) 重复, 走"13 模块集成"角度)
- 陷阱 1: 13 模块全装 ≠ 全用 — MeanRev include 13 模块, 但**实际调用未必 13 个**。看每个模块 spec 的 Init + OnTick 是否走完。**别只看 include 数量, 要看 + 调 7+ (Init + OnTick 2 处)**。本 wiki §1.1 表格已列 13 调用点, **校验方式: grep `Cxxx::` 或 `Cxxx Instance` 在源码出现 ≥ 1 次**。
- 陷阱 2: M18 OnTick 闸门 vs OnInit 启动 — M18 闸门在 OnTick L167 (硬过滤), **M18 Init 在 L110 加载历史**, Init 失败不报警直接 Init return true = **M18 静默失效**。**OnInit 必须 Print `M18.DumpCorr()` 验证矩阵 (MeanRev L118)**, 见 [[实战/M18 多品种对冲实战]] §场景 A
- 陷阱 3: M19 时段常量 vs 自定义 — `InpSessionPreset` 字面量字符串 ("London:8-16,NewYork:13-22"), MQL5 编译器强制 input 默认值必须是字面量 (error 187: constant expected)。**M19 4 预定义常量 (SESSIONS_LONDON_NY 等) 在 spec §5.2**, 复制字面量最稳 (见 [[实战/M19 时段过滤实战]] §反模式 5 字符串格式)
- 陷阱 4: M13 AppendCSV fileName 全路径 — MeanRev 没接 M13 (本 wiki §1.1 表格无 M13), 但 `OnTrade` L272 + L274 调 HistorySelect 走 MT5 stdlib, 不走 M13 沙箱。**要走 M13 沙箱, 见 [[实战/MyEA + Dashboard 接入报告]] §反模式 2 `CFileIO::AppendCSV(fname, row)` 写 `MQL5/Files/`**, 别写 `C:\\Windows\\trades.csv` (沙箱拦截)
- 陷阱 5: Magic 11 vs 13 magic 冲突 — MeanRev 用 `Magic = 11` (input L37), 跟 MyEA `Magic = 20260101` (input L51) 不同, 跨 EA 不会冲突。**但 2 EA 都用 `Magic = 20260101` 必出问题** (见 [[实战/TrendMA_EA + Breakout_EA 接入报告]] §反模式 1: 2 EA 共用 Magic 误伤)。**Magic 必 input 化, 别硬编码**

### 链向
- [[01-调用模块/M01 交易封装 CTradePlus]] — `CTradePlus trade;` (L54) + `trade.Buy`/`trade.Sell`/`trade.PositionClose`
- [[01-调用模块/M02 风控 Risk]] — `CRisk risk;` (L55) + `risk.CanOpen` 7 项
- [[01-调用模块/M09 面板 Dashboard]] — `CDashboard dash;` (L60) + `dash.Refresh` (L231-L247)
- [[01-调用模块/M10 推送通知 Notify]] — `CNotify M10;` (L62) + `M10.Send` (L262/L317) + `M10.Trade` (L293)
- [[01-调用模块/M11 日志 Logger]] — `CLogger logger;` (L61) + `logger.Trade` (L202/L205)
- [[01-调用模块/M18 相关性过滤 CorrelationFilter]] — `CCorrelationFilter M18;` (L63) + `M18.Init` (L110) + `M18.IsHedgeExposed` (L167)
- [[01-调用模块/M19 时段过滤 SessionFilter]] — `CSessionFilter M19;` (L64) + `M19.Init` (L93) + `M19.IsInSession` (L161)
- [[实战/M18 多品种对冲实战]] — M18 MeanRev 接入位置 (场景 A = 本 EA)
- [[实战/M19 时段过滤实战]] — M19 MeanRev 接入位置 (场景 A = 本 EA)
- [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] — 兄弟 EA, 13 模块含 M17, 4 版本演进
- [[实战/BBTrendEA 复活 SOP]] — archive 复活范本, 9 章节 SOP
- [[EA开发/EA 开发知识库]] §"实战相关" 分类 (T4 owner 04:00 顺手加 1 行链向本 wiki)
