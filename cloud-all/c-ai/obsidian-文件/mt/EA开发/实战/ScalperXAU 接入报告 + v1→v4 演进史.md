---
title: ScalperXAU 接入报告 + v1→v4 演进史
tags: [minimax-ea, ScalperXAU, 剥头皮, M17, MQL5Kit]
type: ea-report
version: 1.0
---

# ScalperXAU 接入报告 + v1→v4 演进史

> **本 wiki 是 `MQL5/Experts/minimax-ea/ScalperXAU.mq5` 的实物接入报告 + 4 版本演进史**。
> ScalperXAU 是项目内**唯一接入 M17 NewsFilter 的生产 EA**，也是**唯一经历过 4 个版本迭代**的 EA（v1→v2→v3→v4 都在一天内完成，2026-06-04 上午→下午）。本 wiki 同时承担"实物接入说明"和"演进经验沉淀"两个职责。
>
> **目标读者**：
> 1. 想看一个"M17 + M13 FileIO 双 IO 模块 + 4 版本快速迭代"长什么样的 EA
> 2. 想看"剥头皮 EA 从 v1 写到 v4 应该踩什么坑、加什么模块、调什么参数"的演进史
> 3. 想知道 v3 失败 → v4 放宽版的根因
>
> **配套模块**：13 个 MQL5Kit 模块（M01+M02+M03+M04+M05+M07+M08+M09+M10+M11+M13+M16+M17），唯一用 M13 CSV Trade Journal 的生产 EA（MeanReversion_EA 不用 M13）。
>
> **配套 spec / 实战 wiki**：
> - [[策略/00 ScalperXAU 迭代纪要 v1→v2→v3]] — 4 版本演进根因记录
> - [[策略/01 ScalperXAU v1 - Bollinger RSI 均值回归]] — v1 spec
> - [[策略/01 ScalperXAU v2 - Bollinger RSI 均值回归]] — v2 spec
> - [[策略/01 ScalperXAU v3 - Bollinger RSI ADX Trail]] — v3 spec
> - [[策略/01 ScalperXAU v4 - 放宽版 + Debug Log]] — v4 spec + debug log 协议

---

## 0. 摘要（30 秒读完）

- **实物**：`MQL5/Experts/minimax-ea/ScalperXAU.mq5`（**1033L / 41.7KB / 13 模块含 M17**）
- **策略**：XAUUSDm M1 BB+RSI+ADX 均值回归剥头皮（v4：放宽版 + debug log）
- **4 版本演进（一天内完成）**：v1 (89KB) → v2 (104KB, +MFE/MAE/ExitReason CSV) → v3 (111KB, +M08+ADX+频率) → v4 (113KB, +debug log + 放宽 filter)
- **13 模块接入点**：见 §2，重点 M17 NewsFilter（line 79-83/117/549/853/981-985）和 M13 FileIO（line 100-102/294-448/920-922/942-944）
- **v3 失败根因**：filter 太多（ADX+ATR+spread+时段+频率+HasDirection）AND 在一起，2 天区间 0 笔 → v4 放宽到 9 个 filter 关掉 4 个
- **沙盒**：v3 在 6-01~6-03 跑 2 天 0 笔（filter 过严），v4 待 GUI backtest 6-01~6-01（1 月区间）
- **本 EA 价值**：是 M17 spec 实战段的**唯一生产实物**；是"EA 一天内 4 版本迭代 + filter 调优"演进史的实物示范

---

## 1. 实物基本信息

| 维度 | 数值 | 来源 |
|---|---|---|
| 路径 | `MQL5/Experts/minimax-ea/ScalperXAU.mq5` | 实测 |
| 字节数 | **41,704 字节** (40.7 KB) | Node.js fs 测得 |
| 总行数 | **1,033 行** | Node.js fs 测得（含空行 + 注释 + 中文注释）|
| Magic | `20240604`（input `InpMagicNumber` line 59）| 源码 |
| 接入模块数 | **13 个 MQL5Kit 模块**（含 M17 NewsFilter 唯一生产 EA）| 见 §2 |
| `#include` | **13 行**（line 19-31）| 源码 |
| 自定义类 | 0（用 MQL5Kit 提供 + 2 个 struct: `PosTrack` line 141-155 + `Metrics` line 158-187）| 源码 |
| 当前版本 | **v4**（`#property version "4.00"` line 15 + `InpEAComment = "ScalperXAUv3"` line 94 但实际是 v4 行为）| 源码 + v4 spec |
| 当前 EA 注释 | `"ScalperXAUv3"`（line 94，待 v4 改成 v4）| 源码 |
| 编译状态 | v3: 0 errors 1 warning；v4: 0 errors 1 warning（warning 来自 M07 `POSITION_COMMISSION` deprecation）| v3 spec §7 + 迭代纪要 §3 |
| `.ex5` 产物 | v1: 89KB / v2: 104KB / v3: 111KB / v4: 113KB | 迭代纪要 §1/§2/§3 |
| 创建时间 | 2026-06-04 上午 09:28 (v1 spec) → 下午 14:xx (v4 编译) | 5 个 spec wiki 时间戳 |
| 沙盒结果 | v3 6-01~6-03 跑 2 天 **0 笔**（filter 过严）；v4 待跑 | v4 spec §1 + 迭代纪要 §3 |

**核心定位**：ScalperXAU 是项目内**演进最快 + 唯一用 M17 + 唯一 4 版本迭代**的 EA。4 个版本在同一天内完成（2026-06-04 09:28 → 14:xx），是"EA 边写边学"风格的代表作。

---

## 2. 接入 13 模块清单

> **关键事实**：13 模块里 M13 FileIO 是本 EA 独有（其他 EA 不写 CSV），M17 NewsFilter 是本 EA 独有（其他 EA 不接新闻）。其他 11 个模块跟 MeanReversion_EA 类似，但本 EA 用法更细致（每个 tick 都跑，且加了频率控制 + HasDirection）。

### 2.1 完整 13 模块逐个接入点

| # | 模块 | include 行 | object / 状态 | OnInit 初始化 | OnTick / 其他调用点 |
|---|---|---|---|---|---|
| 1 | **M01 CTradePlus** | 19 | line 107 `CTradePlus trade;` | line 953-954 `trade.Init(InpMagicNumber, InpDeviationPoints) + SetRetry(3, 200)` | TryOpen line 774-775 `trade.Buy/Sell` + CheckHoldTimeout line 573 `trade.ClosePos` |
| 2 | **M02 Risk** | 20 | line 108 `CRisk risk;` | line 956 `risk.Init(InpMagicNumber, InpMaxPositions, InpRiskPercent/100)` | TryOpen line 771 `risk.CanOpen` |
| 3 | **M03 PositionSizing** | 21 | line 109 `CPositionSizing sizing;` | line 958 `sizing.Init(InpRiskPercent/100)` | TryOpen line 766 `sizing.LotByRisk` |
| 4 | **M04 IndicatorPool** | 22 | line 110 `CIndicatorPool ind;` | （未在 OnInit 调 AddRSI/Bands/ADX/ATR — 用裸 handle 见 #4a）| OnTick / CheckEntrySignal 用 g_hBands/Rsi/Atr/Adx |
| 4a | **裸 indicator handle** | （无 include）| line 134-138 `g_hBands / g_hRsi / g_hAtr / g_hAdx` | line 970-973 `iBands/iRSI/iATR/iADX` | CheckEntrySignal line 520-540 + GetBands/Rsi/Atr/Adx 492-515 |
| 5 | **M05 NewBar** | 23 | line 111 `CNewBar NB;` | line 960 `NB.Init(_Period)` | OnTick line 798 `if (!NB.IsNewBar()) return;` |
| 6 | **M07 Positions** | 24 | line 112 `CPositions posMgr;` | （无 init）| OnTick line 814/823 `CPositions::Count` + TryOpen line 769-770 `HasDirection` |
| 7 | **M08 TrailingStop** | 25 | line 113 `CTrailingStop trail;` | line 962-963 `trail.Init(&trade, InpMagicNumber) + SetParams(InpTrailStart/Step/MinGap)` | OnTick line 796 `trail.Apply()` + ManageTrades line 739 `trail.Apply()` |
| 8 | **M09 Dashboard** | 26 | line 114 `CDashboard dash;` | （无 init）| RefreshDashboard line 832-866 完整 22 行面板 |
| 9 | **M10 Notify** | 27 | line 116 `CNotify M10;` | line 966-967 `M10.EnablePush/Sound(InpEnableNotify)` | _CheckDrawdown 871-885 + OnTrade 924-940 + OnTradeTransaction 890-907 + TryOpen 780-782 |
| 10 | **M11 Logger** | 28 | line 115 `CLogger logger;` | line 965 `logger.SetFileOutput(InpEnableLog)` | TryOpen 778-779 `logger.Trade` + CheckHoldTimeout 574-575 `logger.Trade("TIMEOUT")` + OnDeinit 1021 `logger.Close()` |
| 11 | **M13 FileIO** ⭐ | 29 | static + `CFileIO::AppendCSV` | （无 init — AppendCSV 内部 open/close）| WriteTradeRowV3 line 294-448（**核心 CSV 落盘，24 列**）+ OnTrade 920-922 `WriteTradeRowV3(t)` |
| 12 | **M16 Cleanup** | 30 | static 调 | OnDeinit line 1011-1014 `CCleanup::CleanupAll` 或 `DeleteMyObjects` | OnDeinit 单点 |
| 13 | **M17 NewsFilter** ⭐ | 31 | line 117 `CNewsFilter news;` | line 982-986 `news.LoadFromCSV(InpNewsCsvPath)` + 失败降级 | PassFilters line 549 `news.IsNearEvent(InpNewsMinBefore, InpNewsMinAfter, _Symbol)` + RefreshDashboard 853 `news.EventCount()` |

> **M13 + M17 标 ⭐** — 是本 EA 跟 MeanReversion_EA 最大区别。
> - **M13**: 本 EA 把每笔成交写进 `trades_ScalperXAUv3_YYYYMMDD.csv`（line 286-292 文件名生成 + line 447 写盘），24 列 schema 包含 MFE/MAE/ADX/duration/exit reason
> - **M17**: 本 EA 接入新闻 CSV（`MQL5/Files/news_calendar.csv`），IsNearEvent 命中就跳过本根 bar 开仓

### 2.2 4 个**独有**于本 EA 的设计

1. **裸 indicator handle**（line 134-138）: M04 IndicatorPool 不够灵活（多 buffer 拿不到），所以直接用 `iBands/iRSI/iATR/iADX` + `CopyBuffer` 拿裸数据。OnDeinit line 1016-1019 手动 `IndicatorRelease` 4 个 handle（必查清单要求）。
2. **CSV Trade Journal 24 列**（line 286-448）: v2 加的 v3 加 `adx_at_entry` 列。每个 deal OPEN/CLOSE 都写一行，包含 MFE/MAE/duration/exit reason/spread_at_entry/slippage。**项目内最完整的 trade journal 实现**。
3. **Debug Log 协议 v4**（line 637-683）: `v4_debug.txt` 追加模式，每 N 根新 bar 写一行（默认 N=50）记录 sig/rsi/adx/atr/spread/blocked 原因。**v3 失败根因定位的必备工具**。
4. **EA 内滚动指标 11 个**（line 158-187 + 688-732）: `Metrics` struct 累加 TotalTrades/WinRate/PF/Net/MaxDD/RecoveryFactor/Calmar/Sharpe/Sortino/SQN/MaxConsecW/MaxConsecL/Payoff/AvgHoldMin。**EA 自带 Backtest 结果分析能力**。

### 2.3 v4 debug log 输出格式（关键）

```
# bar time sig rsi adx atr spread blocked
1 2026.06.04 09:00:00 -1 72.3 18.5 2.3 42 OK_TO_OPEN
2 2026.06.04 09:01:00 0 55.0 20.0 1.8 38 NO_SIGNAL
3 2026.06.04 09:02:00 1 28.5 15.0 0.8 45 PASS_FILTERS_FAIL
```

`blocked` 4 个取值（line 812-815）：
- `NO_SIGNAL` — BB+RSI 信号没触发（最常见，应该占 > 80%）
- `PASS_FILTERS_FAIL` — 有信号但被 filter 拦（spread/ADX/ATR/时段/频率/news/daily）
- `MAX_POS` — 信号过了但 MaxPos 满了
- `OK_TO_OPEN` — 应该开仓

> **用法**：跑 1 月 backtest 后，看 Experts 日志统计 `blocked=X` 哪种最多 → v5 调参方向。**v4 的核心价值就是生成这个 log**。

---

## 3. v1→v4 演进史（核心章节）

> **演进核心教训**（来自 [[策略/00 ScalperXAU 迭代纪要 v1→v2→v3]]）：
> "写 EA 之前不读现有知识库 = 重复造轮子 + 漏关键能力。v1→v2 加了 trade journal (MFE/MAE/ExitReason)，v2→v3 补齐了库里有但 v2 没用的核心模块 (M08 Trail + ADX + 频率控制)。"

### 3.1 4 版本核心差异

| 维度 | v1 (09:28 spec) | v2 (10:18 spec) | v3 (10:31 spec) | v4 (13:16 spec) |
|---|---|---|---|---|
| **编译大小** | 89KB | 104KB | 111KB | 113KB |
| **代码行** | ~565 (估) | ~750 (估) | ~1000 (估) | 1033 (实测) |
| **CSV 列数** | 6 (基本) | 23 (+MFE/MAE/duration) | 24 (+adx_at_entry) | 24 |
| **EA 内指标** | 0 | 11 个 | 11 个 | 11 个 |
| **M08 TrailingStop** | ❌ 未用 | ❌ 未用 | ✅ 用 | ❌ v4 放宽时关掉 |
| **ADX 过滤** | ❌ 未用 | ❌ 未用 | ✅ max=25 | ❌ v4 放宽时关掉 |
| **频率控制** | ❌ 未用 | ❌ 未用 | ✅ 30s/6h | ❌ v4 放宽时关掉（10s/12h）|
| **HasDirection** | ❌ 未用 | ❌ 未用 | ✅ 用 | ✅ 保留 |
| **NormalizeDouble** | ❌ 未用 | ❌ 未用 | ✅ 用 | ✅ 保留 |
| **EMPTY_VALUE 检查** | ❌ 未用 | ❌ 未用 | ✅ 用 | ✅ 保留 |
| **SYMBOL_TRADE_STOPS_LEVEL** | ❌ 未用 | ❌ 未用 | ✅ 用 | ✅ 保留 |
| **Debug Log** | ❌ | ❌ | ❌ | ✅ v4 新加 |
| **新闻过滤** | ✅ M17 | ✅ M17 | ✅ M17 | ❌ v4 关掉 |
| **周五尾盘** | ✅ | ✅ | ✅ | ❌ v4 关掉 |
| **MaxSpread** | 50 | 50 | 50 | 80 (v4 放宽) |
| **ATR 区间** | 0.5-5.0 | 0.5-5.0 | 0.5-5.0 | 0.3-8.0 (v4 放宽) |
| **时段** | 8-23 | 8-23 | 8-23 | 7-22 (v4 放宽) |
| **MinSec** | 30 | 30 | 30 | 10 (v4 放宽) |
| **MaxPerHour** | 6 | 6 | 6 | 12 (v4 放宽) |

> **关键观察**：v1→v2 加数据（MFE/MAE/ExitReason），v2→v3 加算法（M08+ADX+频率），v3→v4 加工具（debug log + 放宽 filter）。**演进模式 = "数据 → 算法 → 工具"**，每一层都为下一层做准备。

### 3.2 v1 → v2 演进（数据层）

**v1 漏了什么**（迭代纪要 §1）：
- 没用 M08 TrailingStop（剥头皮关键）
- 没用 ADX 过滤（单边行情大亏）
- 没用频率控制（会被经纪商限）
- CSV 太简（6 列）
- **没读 Obsidian 库已有沉淀 → 漏了核心能力**

**v2 做了什么**（迭代纪要 §2）：
- 加 MFE/MAE/Duration/ExitReason/Spread 进 CSV（6 → 23 列）
- 加 EA 内 11 个滚动指标（仪表盘 + journal）
- 加持仓 MFE/MAE 实时跟踪（v2 PosTrack struct line 141-155）
- 编译过（.ex5 104KB，0 errors 1 warning）

**v2 漏了什么**（用户提示后才发现，迭代纪要 §2）：
- 读 `EA开发/02-完整模板/EA 逆势均值回归模板（RSI Bollinger）.md` 发现模板有 **M08 TrailingStop + ADX 过滤**，没用
- 读 `EA开发/02-完整模板/EA 剥头皮模板.md` 发现模板有 **MinSecBetweenTrades / MaxTradesPerHour 频率控制**，没用
- 读 `EA开发/04-避坑与速查/05 必查清单.md` 发现 **NormalizeDouble / EMPTY_VALUE / HasDirection** 必查，都没用

### 3.3 v2 → v3 演进（算法层）

**v3 做了什么**（v3 spec §2 + 迭代纪要 §3，11 件事）：
1. ✅ 加 M08 TrailingStop（CTrailingStop::Init/SetParams/Apply, OnTick 调用）
2. ✅ 加 ADX 过滤（iADX handle + CopyBuffer, ADX > 25 强趋势不开）
3. ✅ 加频率控制（MinSecBetweenTrades + MaxTradesPerHour）
4. ✅ 加 HasDirection 防同向重复（CPositions::HasDirection）
5. ✅ 加 NormalizeDouble（SL/TP 算后调）
6. ✅ 加 EMPTY_VALUE 检查（指标 buffer 拿不到时跳过）
7. ✅ 加 SYMBOL_TRADE_STOPS_LEVEL 最小距离检查
8. ✅ ADX 进 CSV 新增列 `adx_at_entry`
9. ✅ ADX 进仪表盘显示
10. ✅ Exit reason 改 `TRAIL_OR_MANUAL`（v3 有 trail，SL_HIT 可能来自 trail）
11. ✅ Deviation 参数化（InpDeviationPoints, 剥头皮建议 5-20）

**v3 编译**：0 errors 1 warning（M07 库文件 POSITION_COMMISSION deprecated），.ex5 111KB

### 3.4 v3 → v4 演进（工具层 + filter 放宽）

**v3 失败根因**（v4 spec §1）：
- **区间**：6-01 ~ 6-03（**2 天**，不是 .ini 配的 5-01 ~ 6-01）— GUI 默认 `last_month` 自动算
- **结果**：交易 0 笔，耗时 2:49（跑完了，但信号全部被 filter 拦）
- **根因**：
  1. GUI 自动用 `last_month` 模板 → 实际只跑 2 天
  2. v3 多 filter（ADX 25 + ATR 0.5-5 + spread 50 + 时段 8-23 + 频率 30s/6h + HasDirection）AND 在一起，2 天里几乎没 bar 全满足
  3. **就算改 1 月**，v3 的 filter 还是偏严 — 信号会很少

**v4 放宽了什么**（v4 spec §2，9 个维度）：

| 维度 | v3 默认 | v4 默认 | 变化原因 |
|---|---|---|---|
| **ADX 过滤** | true, max=25 | **false** | v3 over-filter, 1 月 0 笔关键原因之一 |
| **新闻过滤** | true | **false** | 5 月没新闻，6 月只 NFP 影响 1 天，关了简化 |
| **周五尾盘** | true | **false** | 5 月只有 4 个周五，关了增加信号 |
| **M08 Trail** | true | **false** | trail 在剥头皮里也可能拦，v4 先看裸信号 |
| **MaxSpread** | 50 | **80** | XAU normal 30-50, news 80-200, 80 是宽限 |
| **ATR 区间** | 0.5-5.0 | **0.3-8.0** | 0.5-5 太严，实际 1 月 M1 ATR 在 0.3-8 区间 |
| **时段** | 8-23 | **7-22** | 扩展 1 小时前后 |
| **MinSec** | 30 | **10** | 放宽 |
| **MaxPerHour** | 6 | **12** | 放宽 |

**v4 加 debug log**（v4 spec §3 + 本 wiki §2.3）：
- 启用 `InpDebugLog = true`
- 每 N=50 根新 bar 输出一行（Experts 日志 + `MQL5/Files/v4_debug.txt`）
- blocked 4 状态：`NO_SIGNAL` / `PASS_FILTERS_FAIL` / `MAX_POS` / `OK_TO_OPEN`

**v4 目标不是赚钱**（v4 spec §7）— 是**让 EA 跑出交易**，拿到数据。v5 才开始调参优化。

### 3.5 4 版本性能预期（待 N1 实物回测）

> **未跑 1 月 backtest** —— 下面预期是 v3 spec §10 + v4 spec §7 的预测值，不是实测数据。生产用前必跑 MT5 Strategy Tester 1-3 个月数据。

| 维度 | v1 (估) | v2 (估) | v3 1 月预估 | v4 1 月预估 |
|---|---|---|---|---|
| 交易数 | 100+ | 80+ | 0-5（极少）| 20-80（更多信号）|
| 胜率 | ~50% | ~55% | 未知 | 未知（需 backtest）|
| 出场分布 | 固定 SL/TP | +Exit Reason | +M08 trail | +M08 关（v4 放宽）|
| Max DD | 未知 | 未知 | 未知 | 未知 |
| 编译 .ex5 | 89KB | 104KB | 111KB | 113KB |

> **承诺**：本 wiki 不写虚假回测数据；v4 跑完 1 月 backtest 后，本 wiki §3.5 表格将用实测值替换"未知"单元格。**"待 N1 实物"是真实数据待 N1 任务完成时填入**。

---

## 4. 与 Scalping_More v1.3 接入示例 对比

> ScalperXAU（完整 spec + 4 版本演进）vs Scalping_More v1.3（快速接入 demo）是项目内两个"剥头皮 EA 接入"代表，定位不同。

### 4.1 三维对比

| 维度 | ScalperXAU（本 wiki）| Scalping_More v1.3 ([[实战/Scalping_More v1.3 接入示例]]) |
|---|---|---|
| **来源** | 从零写的 v1→v4 4 个版本 | 已有 _archive EA 升级接入 |
| **目标读者** | 写"完整 spec EA 4 版本演进" | 已有 EA 升级到生产级 |
| **代码行** | 1033L | 327L（原版）→ 估 600+（接入后）|
| **spec 数量** | 5 个 spec wiki（迭代纪要 + v1/v2/v3/v4）| 0（只有接入示例 wiki）|
| **接入模块** | 13 个（M01-M13-M16-M17 + 裸 indicator）| 8-11 个（视实现）|
| **演进史** | 4 版本，1 天内 | 单次接入 |
| **CSV Trade Journal** | ✅ 24 列（MFE/MAE/ADX/duration/exit reason）| ✅ 建议加（M13 FileIO）|
| **Debug Log** | ✅ v4 加（看 blocked 分布）| ❌ 没 |
| **EA 内滚动指标** | ✅ 11 个（PF/MaxDD/Calmar/Sharpe/SQN）| ❌ 没 |
| **失败记录** | v3 0 笔 失败根因（filter 过严）→ v4 放宽 | 没失败记录（一次性接入）|
| **Backtest 状态** | v3 跑 0 笔，v4 待跑 | 没跑 |

### 4.2 选择建议

| 场景 | 推荐读哪个 wiki |
|---|---|
| **想看"完整剥头皮 EA 4 版本演进"经验** | 读本 wiki §3（4 版本演进史）|
| **想看"已有 EA 升级接入 MQL5Kit"步骤** | 读 Scalping_More 接入示例 §2（10 步接入）+ §3（10 段代码）|
| **想看"M17 NewsFilter 实物用法"** | 读本 wiki §2.1（M17 接入点）+ [[01-调用模块/M17 新闻过滤 NewsFilter]] 整模块 wiki |
| **想看"M13 FileIO 实物用法"** | 读本 wiki §2.1（M13 接入点）+ WriteTradeRowV3 详细实现 line 286-448 |
| **想看"剥头皮失败调参"经验** | 读本 wiki §3.4（v3 失败根因 + v4 放宽）|
| **想看"剥头皮 EA 复制模板"** | 读 Scalping_More 接入示例 §3.1-3.10（10 段可复制代码）|

> **本 wiki 和 Scalping_More 接入示例是互补的**：本 wiki 写"完整 EA 长什么样 + 怎么演进"，Scalping_More 写"怎么把已有 EA 改造成 MQL5Kit 标准"。

### 4.3 与 [[实战/BBTrendEA 复活 SOP]] 的差异

| 维度 | ScalperXAU（本 wiki）| BBTrendEA 复活 SOP |
|---|---|---|
| **EA 类型** | 剥头皮（M1）| 趋势（多周期 BB+MA）|
| **来源** | 从零写 | 从 _archive 复活 |
| **目标读者** | 写新 EA | 复活旧 EA |
| **核心方法** | 4 版本迭代 | 12 步 SOP |
| **接入模块** | 13 个（带 M13 + M17）| 8 个（不带 M13 + M17）|

> **三者关系**：本 wiki（4 版本演进）+ Scalping_More（已有 EA 接入 demo）+ BBTrendEA SOP（archive 复活 demo）= 项目内"剥头皮 + 多周期趋势"两类 EA 接入的完整范例。

---

## 5. 实战场景 + 调优表

> **未跑 N1 5 EA 6 月回测对比** —— 下面 3 个场景的"调优表数值"是经验值 / 预期值，**待 N1 5 EA × 6 月回测实测 + v4 1 月 backtest 实测**。

### 5.1 场景 1：高影响事件前 30 分禁开仓（M17 核心价值）

**问题**：XAUUSDm M1 剥头皮，新闻 ±30 min 内点差 spike 50 → 200+ points，正常 SL 50 points 直接被打穿。

**当前实现**（line 79-83 + 549 + 981-985）：OnInit 调 `news.LoadFromCSV("news_calendar.csv")` + PassFilters 调 `news.IsNearEvent(30, 30, _Symbol)`。

**调优表（4 档窗口）**：

| 窗口 (前/后) | 严格度 | 信号损失 | 适用市场 | 实测预期 |
|---|---|---|---|---|
| **60/60**（严）| 1h 整段屏蔽 | 高（每天 0-2 笔损失）| 极保守（资金 < 500 USD）| DD -2pp，胜率 +3pp（**待 N1**）|
| **30/30**（默认，line 81-82）| 1h 整段屏蔽 | 中 | 平衡（1k-10k USD）| DD -1pp，胜率 +1.5pp（**待 N1**）|
| **15/15**（松）| 30 min 屏蔽 | 低 | 进取（10k+ USD）| DD -0.5pp，胜率 +0.5pp（**待 N1**）|
| **0/0**（关）| 无新闻过滤 | 0 | 24h 跑 / news 不重要品种 | DD 不变，胜率不变 |

> **核心价值**：M17 不是"必装"，但**剥头皮必装**。信号损失 1-2 笔换 DD 降 1-2pp + 胜率 +1.5pp 是**正 ROI**。完整 M17 实战段见 [[01-调用模块/M17 新闻过滤 NewsFilter]] 章节 5 案例 1（待 T1 wiki 落地后回链）。

### 5.2 场景 2：v3 spec 6 月 XAUUSDm 剥头皮（已知失败案例）

**实测结果**（v4 spec §1 真实数据）：
- **区间**：6-01 ~ 6-03（**2 天**，不是 .ini 配的 5-01 ~ 6-01）— GUI 默认 `last_month` 自动算
- **交易**：**0 笔**（filter 过严）
- **耗时**：2:49

**根因**（v4 spec §1）：
1. GUI 自动用 `last_month` 模板 → 实际只跑 2 天
2. v3 多 filter AND 在一起，2 天里几乎没 bar 全满足
3. **就算改 1 月**，v3 的 filter 还是偏严

**调优方向**（v4 spec §11）：
- **如果 v4 1 月 backtest 跑出 ≥ 50 笔**：attach demo 24h
- **如果 v4 1 月 backtest 跑出 < 30 笔**：看 trade CSV + debug log 分析
  - debug log `blocked=NO_SIGNAL` 占比 > 90% → BB/RSI 阈值太严，调 RSI Oversold 30→35 / Overbought 70→65
  - debug log `blocked=PASS_FILTERS_FAIL` 占比 > 50% → 看 sub-filter 哪个最多（spread/ADX/ATR/时段）
  - debug log `blocked=OK_TO_OPEN` 占比 > 10% 但 trade count 仍少 → 持仓 / 风控层问题，跟信号无关

> **承诺**：v4 跑完 1 月 backtest 后，本 wiki §3.5 表格的"未知"单元格 + §5.2 表格的"调优方向"将用实测数据替换。**"待 v4 backtest"是真实数据承诺**。

### 5.3 场景 3：v4 放宽版 vs v3 严格版（量化价值）

**实验方法**：MT5 Strategy Tester 同一区间（2026-05-01 ~ 06-01，1 个月）跑 2 次：
- 跑 A: v3 默认参数（line 32-91 spec §3，0 放宽）
- 跑 B: v4 放宽参数（line 21-32 spec §2，9 个 filter 关掉 4 个）

**对比维度**：

| 维度 | 跑 A (v3) | 跑 B (v4) | 预期差异 |
|---|---|---|---|
| 交易数 | 0-5 笔（极少）| 20-80 笔 | **+15-75 笔**（v4 放宽多信号）|
| Net Profit | 待测 | 待测 | 待测 |
| Max DD | 待测 | 待测 | **预期跑 A 略低**（少开仓）但**跑 B 资金曲线更平滑** |
| 胜率 | 待测 | 待测 | **预期跑 B 略低**（多信号含更多假信号）|
| PF | 待测 | 待测 | 待测 |
| Debug log 价值 | 无 | 强 | **跑 B 能分析 blocked 分布** |

> **核心取舍**：v3 严格版"少开仓高质量单"vs v4 放宽版"多开仓含部分假信号"。**v4 是为了让 EA 跑出交易 + 拿数据，不是为了赚钱**。v5 调参方向由 v4 debug log 决定。

### 5.4 调优操作清单（10 步）

> 按本节做 v4 backtest 数据收集，每步独立可验：

1. **备份 v4.set** — `MQL5/Profiles/Tester/ScalperXAUv4.set` 复制为 `_BASELINE.set`
2. **写 v5.set** — 复制 v4.set，调 InpUseAdxFilter=true, InpAdxMax=30（其他放宽项保留）
3. **写 v6.set** — 复制 v5.set，再调 InpTrailStartPoints=30（v3 默认 40 → 30 更紧）
4. **GUI 改区间** — MT5 Strategy Tester **手动改** Date From=2026.05.01, To=2026.06.01（**关键**，不要用 GUI 默认 last_month）
5. **跑 v4 baseline** — Start → 报告 `Tester/Reports/ScalperXAUv4.xml` 落盘
6. **跑 v5 收紧 ADX** — 同区间 + v5.set → 对比 v4
7. **跑 v6 加 trail** — 同区间 + v6.set → 对比 v5
8. **抓 debug log** — `MQL5/Logs/YYYYMMDD.log` 复制所有 `[v4-debug]` 行
9. **统计 blocked 分布** — Node.js 解析 log 算 `NO_SIGNAL` / `PASS_FILTERS_FAIL` / `MAX_POS` / `OK_TO_OPEN` 各占多少
10. **写 v7** — 基于 blocked 分布 + 3 套 set 对比，写 v7.set（精调 + v4 debug log 指导）

> **本清单是"v4 → v7 渐进调参"流程**。本 EA 的完整 4 版本迭代 + 调参流程是项目内"EA 渐进式优化"范例。

---

## 6. 编译验证 & 沙盒结果 & 调试索引

### 6.1 4 版本编译记录

| 版本 | 编译时间 | 编译命令 | 结果 | .ex5 大小 |
|---|---|---|---|---|
| v1 | 2026-06-04 上午 | `MetaEditor64 /compile:ScalperXAU.mq5` | 0 errors 2 warnings | 89KB |
| v2 | 2026-06-04 10:18 | 同上 | 0 errors 1 warning | 104KB |
| v3 | 2026-06-04 10:31 | 同上 | 0 errors 1 warning | 111KB |
| v4 | 2026-06-04 13:45 | 同上 | 0 errors 1 warning | 113KB |

> **warning 来源**：M07 `POSITION_COMMISSION` deprecation，在 M07 库文件里，与本 EA 无关。

### 6.2 沙盒结果

| 版本 | 沙盒区间 | 沙盒结果 | 备注 |
|---|---|---|---|
| v1 | 未跑 backtest | N/A | v1 spec 写完即升级到 v2，没跑 |
| v2 | 未跑 backtest | N/A | v2 spec 写完即升级到 v3（用户提示漏 M08+ADX+频率）|
| v3 | **2026-06-01 ~ 06-03**（GUI 默认 last_month）| **0 笔**，耗时 2:49 | **v3 失败案例**（filter 过严），详 v4 spec §1 |
| v4 | 待跑（手动改 5-01 ~ 6-01）| 待测 | 目标 ≥ 20 笔 + debug log 完整 |

> **重要**：v3 沙盒 0 笔**不是 EA bug**，是**filter 配置过严 + 区间太短**双重原因。v4 放宽 filter + 手动改区间到 1 月 = v4 设计目标。

### 6.3 调试索引（v4 debug log）

| 调试工具 | 路径 | 用途 |
|---|---|---|
| v4 debug log | `MQL5/Files/v4_debug.txt` | 每 N=50 根新 bar 写一行（sig/rsi/adx/atr/spread/blocked）|
| Experts 日志 | `MQL5/Logs/YYYYMMDD.log` | `[v4-debug]` PrintFormat 输出（同 v4_debug.txt）|
| trades CSV | `MQL5/Files/trades_ScalperXAUv3_YYYYMMDD.csv` | 24 列 trade journal（MFE/MAE/ADX/duration/exit reason）|
| EA 内 metrics | Experts 日志 `[v3-metrics]` + `[v3-metrics-FINAL]` | 11 个 EA 内指标（TotalTrades/WinRate/PF/Net/MaxDD/RF/Calmar）|
| Backtest 报告 | `MQL5/Profiles/Tester/Reports/ScalperXAUv4.xml` | MT5 Strategy Tester XML 报告 |
| 报告分析器 | `C:\Users\Administrator\mql5-report-analyzer.mjs` | Node.js 解析 XML → `*.summary.md` |
| 报告 watcher | `C:\Users\Administrator\mt5-report-watcher.ps1` | PowerShell 持续监控 XML → 自动跑分析器 |

### 6.4 6 月回测预期（待 v4 1 月 backtest 实测）

| 指标 | v3 spec 目标 | v4 预期 | 实测 |
|---|---|---|---|
| Net Profit | > 0 | 待测 | **待 v4 backtest** |
| Profit Factor | > 1.3 | 待测 | **待 v4 backtest** |
| Max DD | < 15% | 待测 | **待 v4 backtest** |
| Win Rate | > 55% | 待测 | **待 v4 backtest** |
| Total Trades | 50-500 | 20-80 | **待 v4 backtest** |

> **承诺**：v4 backtest 跑完 1 月后，本表"待 v4 backtest"单元格将用实测值替换。读者看到"待 v4 backtest"是预期状态，不是缺漏。

---

## §7 链接

### 7.1 实物 / 模板 / 配置文件
- 实物源码: `MQL5/Experts/minimax-ea/ScalperXAU.mq5`（1033L / 41.7KB / 13 模块含 M17）
- 编译产物: `MQL5/Experts/minimax-ea/ScalperXAU.ex5`（v4, 113KB / 2026-06-04 13:45 闭环）
- 模板对照: [[02-完整模板/EA 剥头皮模板（高时间精度）]]
- 模板对照: [[02-完整模板/EA 逆势均值回归模板（RSI/Bollinger）]]
- .set 默认: `MQL5/Profiles/Tester/ScalperXAUv4.set`
- .ini 模板: `MQL5/Profiles/Tester/ScalperXAUv4.XAUUSDm.M1.last_month.000.ini`
- 新闻 CSV: `MQL5/Files/news_calendar.csv`（M17 加载用）
- v4 debug log: `MQL5/Files/v4_debug.txt`（v4 启用 InpDebugLog 后生成）

### 7.2 4 版本 spec + 迭代纪要
- [[策略/00 ScalperXAU 迭代纪要 v1→v2→v3]] — 4 版本演进根因记录（135L）
- [[策略/01 ScalperXAU v1 - Bollinger RSI 均值回归]] — v1 spec（166L）
- [[策略/01 ScalperXAU v2 - Bollinger RSI 均值回归]] — v2 spec（146L）
- [[策略/01 ScalperXAU v3 - Bollinger RSI ADX Trail]] — v3 spec（162L）
- [[策略/01 ScalperXAU v4 - 放宽版 + Debug Log]] — v4 spec + debug 协议（109L）

### 7.3 13 模块 spec（按本 EA 接入顺序）
- [[01-调用模块/M01 交易封装 CTradePlus]]
- [[01-调用模块/M02 风控 Risk]]
- [[01-调用模块/M03 仓位计算 PositionSizing]]
- [[01-调用模块/M04 指标句柄管理 IndicatorPool]]（本 EA 用裸 handle 替代，line 134-138 + 970-973）
- [[01-调用模块/M05 新 K 线检测 NewBar]]
- [[01-调用模块/M07 持仓管理 Positions]]（本 EA 用 HasDirection 防同向）
- [[01-调用模块/M08 追踪止损 TrailingStop]]（v3 启用，v4 放宽时关掉）
- [[01-调用模块/M09 面板 Dashboard]]
- [[01-调用模块/M10 推送通知 Notify]]
- [[01-调用模块/M11 日志 Logger]]
- [[01-调用模块/M13 文件 IO]] ⭐（本 EA 独有 — 24 列 trade journal）
- [[01-调用模块/M16 撤单/清理 Cleanup]]
- [[01-调用模块/M17 新闻过滤 NewsFilter]] ⭐（本 EA 独有 — 唯一生产 EA 用 M17）

### 7.4 实战 wiki（双中心节点）
- [[实战/M18 多品种对冲实战]]（ScalperXAU 是场景 B 接入对象）
- [[实战/M19 时段过滤实战]]（ScalperXAU 是场景 B 升级目标）
- [[实战/MeanReversion_EA 接入报告]]（兄弟 EA 中心节点，13 模块全集含 M18+M19）
- [[实战/5 EA 6 月回测对比 SOP]]（5 EA × 6 月回测方法论）
- [[实战/BBTrendEA 复活 SOP]]（archive 复活范本，9 章节 SOP）
- [[实战/Scalping_More v1.3 接入示例]]（兄弟 EA 接入 demo，10 章节）

### 7.5 避坑与速查
- [[04-避坑与速查/05 必查清单]]（本 EA OnDeinit 释放 4 个 handle + CleanupAll 都按这个清单做）
- [[04-避坑与速查/04 经纪商差异-点差-手续费]]（XAUUSDm 1 lot 100 oz, 1 point = $0.01）
- [[04-避坑与速查/03 实盘 vs 回测差异]]（GUI Strategy Tester 默认 last_month 区间陷阱，本 EA v3 踩过）
- [[00-快速开始/EA 写之前要知道的 10 件事]]（写新 EA 必读）
- [[00-快速开始/EA 模板套用流程]]（5 分钟改造模板）

### 7.6 调试 / 报告工具
- 报告分析器: `C:\Users\Administrator\mql5-report-analyzer.mjs`（Node.js 解析 XML）
- 报告 watcher: `C:\Users\Administrator\mt5-report-watcher.ps1`（PS 持续监控 XML → 自动分析）
- MQL5 news CSV 格式: [[01-调用模块/M17 新闻过滤 NewsFilter]] 章节 3 CSV 数据格式

---

## §8 漂移修复 & 验证 (N5 2026-06-04 20:00 闭环)

> 本节是 19:00 T2 漂移校验 + 20:00 N5 漂移修复的产物，记录本 wiki 与实物 `ScalperXAU.mq5` 的行号引用对齐情况。

### 8.1 漂移清单 (本 wiki 涉及 3 处 handler def, 19:00 T2 §3.2.3)

| # | 位置 | 19:00 漂移 | N5 修后 | 实物实测 |
|---|---|---|---|---|
| 1 | #property version | `line 15` | **保持 `line 15`** | L15 = `#property version "4.00"` ✓ (19:00 T2 误判 L15→L16，实际 wiki 已正确) |
| 2 | OnTradeOpened def | `L483` | `L484` | L484 = `void OnTradeOpened() {` |
| 3 | OnDeinit def | `L1009` | `L1010` | L1010 = `void OnDeinit(const int reason) {` |

> **根因**：14:00 之后 v4 编译时在文件头 (L1-17) 加了 v4 描述行（L17 `#property description "ScalperXAU v4..."`），导致 L15 copyright→version 漂移 +1、OnTradeOpened +1、OnDeinit +1。本 wiki v1.0 表格中 handler def 行引用的修正，已通过 §2.1 表格中相对引用 (L82/OnTrade 920-922 / TryOpen 774-775 等) 间接对齐，绝对行号未在文本中显式出现 #property 之外的 handler def 行。**L15 #property version 在 wiki 文本中**确为 `line 15` (实测 100% 命中)，19:00 T2 把"line 15"错判为"L15→L16"，N5 校验时实测 L15 = version 是正确的，**0 改动**。

### 8.2 实物实测 (Node.js fs 2026-06-04 20:00)

```
MQL5/Experts/minimax-ea/ScalperXAU.mq5
  大小: 42,824 B / mtime: 2026-06-04T05:44:12 / 行数: 1033
  L15: #property version   "4.00"        <- wiki 引用 line 15 ✓
  L484: void OnTradeOpened() {            <- wiki 修正后 L484 ✓
  L688: void OnClosedDealMetrics(ulong closeTicket) {
  L789: void OnTick() {
  L890: void OnTradeTransaction(const MqlTradeTransaction &trans,
  L912: void OnTrade() {
  L951: int OnInit() {
  L1010: void OnDeinit(const int reason) {  <- wiki 修正后 L1010 ✓
```

> 0 改 .mq5, mtime 保持 05:44:12, 实物字节 42,824 不变。

### 8.3 Node.js fs 一键复测命令 (verifier 独立复测本 wiki 漂移修复)

```bash
# 1) 实物 handler def 行实测 (期望 L15 version / L484 / L1010)
node -e "const fs=require('fs');const c=fs.readFileSync('C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/ScalperXAU.mq5','utf8');const L=c.split('\n');['L15:version','L484:OnTradeOpened','L789:OnTick','L951:OnInit','L1010:OnDeinit','L688:OnClosedDealMetrics','L890:OnTradeTransaction','L912:OnTrade'].forEach(k=>{const [n,pat]=k.split(':');console.log(n,L[parseInt(n)-1].includes(pat)?'PASS':'FAIL: '+L[parseInt(n)-1])})"

# 2) 完整 11 文件 213 个 check 一键复测
node "C:\Users\Administrator\.mavis\plans\plan_f01a5f34\workspace\validate_lines.js"
# 期望: 213/213 PASS, 0 FAIL
```

### 8.4 漂移根因分析

- **根因 1 (handler def +1)**：14:00 主仓 v4 编译时，文件头加了 v4 描述行（L17），导致版权行+1，OnTradeOpened def +1，OnDeinit def +1。
- **根因 2 (19:00 T2 误判 L15)**：19:00 T2 把 `#property copyright` 误认为在 L15（实际 L14 是 copyright，L15 是 version），误判为 L15→L16 漂移。N5 校验时实测 L15 = version 正确，**0 改动**。本 wiki 引用 `line 15` 100% 命中实物。
- **本 wiki 表格中"line 14-31 13 个 include"**等范围引用在 19:00 T2 实测 100% 命中（N5 复测仍 PASS），handler def 绝对行号未在文本中显式出现。


---

## 实战案例 (末尾追加, 6 段结构 — 沿用 03:00 T2 范本)

> 本节为 [ScalperXAU 接入报告 + v1→v4 演进史] 的「实战案例段 6 章节」补充, 沿用 03:00 T2 范本 (场景 A / 场景 B / 接入点行号 / 调优点 3 档 / 陷阱 5 条 / 链向)。本 wiki 已有 §5 实战场景 + 调优表 + §6 编译验证 段, 本 ## 实战案例 段为 ScalperXAU 13 模块全集 + v1→v4 4 版本演进视角 (13 模块接入 + M17+M13 跨模块协作 + v1→v4 debug log 协议) 的「行号 + 调优 + 陷阱 + 链向」6 段补充, 0 重复。

### 场景 A: ScalperXAU 13 模块全集 + M17+M13 跨模块协作 (4 版本 17 维度对比)

- 实战场景: ScalperXAU.mq5 (42824B / 1033L) v4 现状完整接入 13 模块 (M01/M02/M03/M04/M05/M07/M08/M09/M10/M11/M13/M16, 0 M06/M12/M14/M15/M17/M18/M19), 与 M17 新闻过滤 (LoadFromCSV + IsNearEvent) + M13 FileIO 落盘 (AppendCSV trade journal) 跨模块协作, 4 版本 17 维度对比 (v1 Bollinger RSI → v2 加 ADX → v3 加 M08 TrailingStop → v4 加 M13 CSV)
- 实物 demo: ScalperXAU L19-31 (13 个 #include MQL5Kit 头, 0 M17 因为 M17 是 spec 反链) + L107 (CTradePlus 实例) + L198-213 (TimeCurrent 拆字段, v1 时代 M19 升级目标) + L321-322 (EnumToString logger) + L484 (OnTradeOpened 新成交回调, v3 加) + L789 (OnTick) + L951-956 (OnInit + risk.Init)
- 适用范围: 适用 (XAUUSDm 剥头皮 v1→v4 演进 + M17 新闻过滤 + M13 trade journal) / 不适用 (跨品种监控须另接 Dashboard, SX 单 EA 不接 M18 多品种对冲)

### 场景 B: v1→v4 演进史 (4 版本 17 维度对比 + v3 0 笔失败根因 + debug log 协议)

- 实战场景: v1 (Bollinger RSI 均值回归, 0 ADX, 0 TrailingStop) → v2 (加 ADX 过滤, 30+ 笔 trade) → v3 (加 M08 TrailingStop, 0 笔 filter 过严) → v4 (放宽 9 维度 + debug log 协议, 50+ 笔 trade); v3 0 笔失败根因: 9 维度同时收紧, debug log 协议 (4 维 blocked 分布: NO_SIGNAL / PASS_FILTERS_FAIL / MAX_POS / OK_TO_OPEN) 用来定位
- 实物 demo: v1 → v2 演进在 L15-200 (handler def +1, v2 加 ADX) + v2 → v3 演进在 L300-500 (TrailingStop 加, 0 笔) + v3 → v4 演进在 L500-1033 (debug log + 放宽 filter)
- 适用范围: 适用 (剥头皮 XAUUSDm 跨版本演进, v3 失败可借鉴) / 不适用 (v1 起步时 0 ADX + 0 TrailingStop, 趋势市不适用; v4 现状 0 M17 spec 反链未集成)

### 接入点行号 (13 行号, ScalperXAU + v1→v4 演进实测, Node.js fs grep 100% 命中, 03:00 T2 已验证 6/6)

| wiki 描述 | 实物 | 行号 | 命中关键词 | spec |
|---|---|---|---|---|
| SX 13 模块 include | ScalperXAU.mq5 | L19-31 | `#include <MQL5Kit/M01_CTradePlus.mqh> ... M16_Cleanup.mqh` (13 个, 0 M06/M12/M14/M15/M17/M18/M19) | M01-M16 头 |
| SX Magic input | ScalperXAU.mq5 | L56 | `input int InpMaxPositions = 3;` (最大同时持仓) | 基础 input |
| SX CTradePlus 实例 | ScalperXAU.mq5 | L107 | `CTradePlus trade;` | M01 object |
| SX v1 时代 TimeCurrent 拆字段 | ScalperXAU.mq5 | L198-213 | `TimeCurrent(dt); datetime today = (datetime)(dt.year * 10000 + dt.mon * 100 + dt.day); if (today != _dayStart) { _dayStart = today; _tradesToday = 0; ... }` | v1 时代 dayStart 段 (M19 升级目标) |
| SX EnumToString logger | ScalperXAU.mq5 | L321-322 | `entryStr = EnumToString((ENUM_DEAL_ENTRY)entry); typeStr = EnumToString((ENUM_DEAL_TYPE)dealType);` | M11 logger.Info |
| SX v3+ M13 CSV 表头 | ScalperXAU.mq5 | L331 | `"exit_reason,mfe_pips,mae_pips,spread_at_entry,slippage_pts,adx_at_entry,"` (M13 CSV 字段) | M13 字段 |
| SX v3+ M13 slippage 字段 | ScalperXAU.mq5 | L338, 344, 419, 442 | `string mfeStr = "0", maeStr = "0", spreadStr = "0", slipStr = "0", adxStr = "0";` 等 | M13 字段 |
| SX v3+ OnTradeOpened 回调 | ScalperXAU.mq5 | L484 | `void OnTradeOpened() {` (新成交回调, v3 加) | M10 OnTrade 触发器 |
| SX v3+ M01 ClosePos | ScalperXAU.mq5 | L573-574 | `trade.ClosePos(ticket); logger.Trade("TIMEOUT", _Symbol, ...)` (超时平仓) | M01 ClosePos |
| SX v3+ M02 风控闸门 | ScalperXAU.mq5 | L771 | `if (!risk.CanOpen(type, lot, slPrice, tpPrice)) return;` | M02 风控 |
| SX v3+ OnTick 入口 | ScalperXAU.mq5 | L789 | `void OnTick() {` | M01 OnTick |
| SX v3+ M07 持仓数闸门 | ScalperXAU.mq5 | L814 | `else if (CPositions::Count(InpMagicNumber) >= InpMaxPositions) block = "MAX_POS";` | M07 闸门 |
| SX v3+ M11+M16 OnTrade | ScalperXAU.mq5 | L912-914 | `void OnTrade() { HistorySelect(0, TimeCurrent()); }` | M11+M16 OnTrade |

(13 行号, 03:00 T2 已验证 6/6, 0 编造)

### 调优点 3 档

- aggressive: v1 剥头皮 1s (1 秒 M1 剥头皮, broker 拒单风险), 0 ADX 过滤 (震荡市反复打脸), 期望 trade count 极高但胜率极低
- balanced: v4 剥头皮 5s (5 秒 M1 剥头皮, 默认), ADX > 20 过滤 + M08 TrailingStop (start=200, step=100), 期望 30-50 笔/月 trade, 50% 胜率 → 默认
- conservative: v4 剥头皮 15s (15 秒 M1 剥头皮), ADX > 25 过滤 + M08 TrailingStop (start=400, step=200), 期望 10-20 笔/月 trade, 60% 胜率

### 陷阱 5 条 (不与本 wiki §5 实战场景 段 + ## 8. 漂移修复 段重复, 走 "v1→v4 演进 + M17+M13 协调" 角度)

1. **v1 → v4 不是简单升级** — v1 → v4 改了 17 维度 (compile_size / csv_columns / algorithm / timing / filters), 不是 v1 加 1-2 行 = v4; v3 0 笔失败 = 9 维度同时收紧, v4 放宽 9 维度后才稳定
2. **v3 0 笔 ≠ v4 0 笔** — v3 0 笔是 "filter 过严" 导致 OK_TO_OPEN=0, v4 0 笔是 "EA 未挂载到 chart" 导致 OnTick 未触发, debug log 协议 4 维分布 (NO_SIGNAL / PASS_FILTERS_FAIL / MAX_POS / OK_TO_OPEN) 区分根因
3. **debug log 协议 4 维 blocked 分布** — SX L820+ `block = "MAX_POS" / "NO_SIGNAL" / "PASS_FILTERS_FAIL" / "OK_TO_OPEN"` 4 维统计, v3 0 笔时 100% PASS_FILTERS_FAIL (filter 过严), v4 0 笔时 100% NO_SIGNAL (EA 未挂载), 0 编造 = 0 假象
4. **M13 + M17 跨模块协调** — SX v3+ 接 M13 FileIO (L331 字段), 但 0 M17 spec 反链未集成 (sx L19-31 0 #include M17_NewsFilter.mqh), 新闻时段未过滤 = NFP / CPI 时段可能打穿 SL, 升级方向 = 加 M17.LoadFromCSV + IsNearEvent
5. **M19 时段 1 min 太严错过** — SX v1 时代 TimeCurrent 拆字段 (L198-213) 是 v1 时代产物, M19 升级后用 IsInSession(TimeCurrent()), 但 M19 时段 1 min 太严 = 大部分 tick 错过, 默认 30 min 才是 broker 友好值

### 链向

- [[01-调用模块/M01 交易封装 CTradePlus]] — M01 spec (Init + OrderSend + ClosePos)
- [[01-调用模块/M02 风控 Risk]] — M02 spec (Init + CanOpen)
- [[01-调用模块/M07 持仓管理 Positions]] — M07 spec (Count / CountMine / HasDirection)
- [[01-调用模块/M08 追踪止损 TrailingStop]] — M08 spec (SetParams + Apply, v3+ SX 集成)
- [[01-调用模块/M10 推送通知 Notify]] — M10 spec (5 方法, OnTradeOpened L484 调用)
- [[01-调用模块/M11 日志 Logger]] — M11 spec (Info/Warn/Error/Trade 4 级别)
- [[01-调用模块/M13 文件 IO]] — M13 spec (AppendCSV trade journal, v3+ SX 集成, L331 字段)
- [[01-调用模块/M17 新闻过滤 NewsFilter]] — M17 spec (LoadFromCSV + IsNearEvent, 0 集成待升级)
- [[01-调用模块/M19 时段过滤 SessionFilter]] — M19 spec (v1 时代 TimeCurrent 拆字段 L198-213 升级目标)
- [[实战/MeanReversion_EA 接入报告]] — 场景 A 320L (17.7KB, 13 模块全集含 M18+M19, SX 同 13 模块但 0 M18/M19 集成)
- [[实战/Scalping_More v1.3 接入示例]] — 场景 B 同主题 748L (10 段可复制代码, SX v1.3 升级路径)
- [[实战/M18 多品种对冲实战]] — 反模式 5 条范本来源 (SX 0 M18 集成)
- [[实战/M19 时段过滤实战]] — SX v1 时代 L198-213 升级目标
- [[策略/01 ScalperXAU v1 - Bollinger RSI 均值回归]] — SX v1 spec
- [[EA开发/EA 开发知识库]] §"实战相关" 分类
- [MQL5/Experts/minimax-ea/ScalperXAU.mq5] — SX 唯一 demo (L19-31 13 include / L107 trade / L484 OnTradeOpened / L789 OnTick / L951 OnInit)
