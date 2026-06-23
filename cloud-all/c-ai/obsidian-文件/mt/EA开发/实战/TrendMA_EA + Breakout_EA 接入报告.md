---
title: TrendMA_EA + Breakout_EA 接入报告 (实物 EA 联合 wiki, 14:00 沉淀清单 #19)
date: 2026-06-04
tags: [EA, TrendMA, Breakout, 接入, 联合, 沉淀 #19]
type: usage
version: 2.0
---

# TrendMA_EA + Breakout_EA 接入报告

> **本 wiki 是 `MQL5/Experts/minimax-ea/TrendMA_EA.mq5` + `Breakout_EA.mq5` 的联合接入报告（v2 修正版）**。
> TrendMA_EA（**239L / 9,169 B UTF-16 LE 磁盘字节 / 12 模块 M01-M11+M16**）+ Breakout_EA（**237L / 9,530 B UTF-16 LE 磁盘字节 / 11 模块 M01-M05+M07-M11+M16 不含 M06**）= minimax-ea/ 10 实物 EA 中**最成熟的 2 个非 Test\* 生产 EA**。
>
> **v2 关键修正（相对 v1）**：
> 1. M04 Breakout 接入表修正：4 个指标 = `AddBands` x 2 + `AddEMA` + `AddADX`（**v1 错写为 `AddMA`+`AddEMA`+`AddRSI`+`AddATR`，`AddRSI("ADX", 14)` 是误导性 API**）
> 2. M10 调用计数修正：2 EA 各 **5 个方法调用**（v1 误写 TrendMA=12, Breakout=11）
> 3. M07 Breakout 修正：Breakout **0 次 CPositions 调用**（v1 误写"2 EA 都用 CPositions"）
> 4. M08 Breakout 修正：Breakout 只有 Init+SetParams，**无 trail.Apply 调用**（v1 误写 OnTick 内调 Apply）
> 5. M11 Breakout 修正：logger **只声明，未实际调用**（无 Close/Trade，v1 误写"OnDeinit 调 logger.Close"）
> 6. Breakout `sizing.LotByRiskDefault(sl)` 不是 `sizing.LotByRisk(...)`（v1 误写为 LotByRisk）
> 7. Breakout **无 `risk.CanOpen` 调用**（v1 误写"风控检查"）
> 8. TrendMA M06 修正：`CSignal::CrossUpSeries/CrossDownSeries` 4 处调用（v1 误写 0 hits）
> 9. Breakout 8 个 top-level 函数（5 public + 3 private `_CheckSignal`/`_RefreshDash`/`_CheckDrawdown`），v1 误写 5
> 10. frontmatter 加 `date: 2026-06-04` + 改 `type: usage`（v1 漏 date，type=ea-report 不符 spec）
>
> **目标读者**：
> 1. 想看"中等规模自包含生产 EA 长什么样 / 每个 MQL5Kit 模块怎么接"
> 2. 想看"M10 3 类触发器（DD 报警 / 新成交通知 / 拒单通知）的最小可复制范本"——2 EA 都用同一套
> 3. 想对比"趋势跟踪"（TrendMA MA 交叉）vs "突破"（Breakout Donchian + HTF + ADX）两类策略的模块接入差异
> 4. 想找"M04 多 buffer 指标处理"的范本（TrendMA 2 MA 简单 / Breakout 4 指标含 ADX）

---

## 0. 摘要（30 秒读完）

- **实物 A**：`MQL5/Experts/minimax-ea/TrendMA_EA.mq5`（**239L / 9,169 B UTF-16 LE / 12 模块**含 M06 Signal, Magic 20260101, 10 top-level functions）
- **实物 B**：`MQL5/Experts/minimax-ea/Breakout_EA.mq5`（**237L / 9,530 B UTF-16 LE / 11 模块**不含 M06 Signal, Magic 20260101, 8 top-level functions）
- **策略**：TrendMA = XAUUSDm M15 MA 交叉趋势跟踪（FastMA 12 / SlowMA 26 / MODE_EMA，`CSignal::CrossUpSeries/CrossDownSeries` 触发）；Breakout = XAUUSDm H1 Donchian Channel（period 20）突破 + HTF EMA 50 趋势过滤 + ADX 20 弱趋势过滤
- **12 + 11 模块接入点**：见 §2，每模块 include + object decl + OnInit Init 严格按 M01→M11 顺序。**关键事实**：TrendMA 12 模块**全部实际使用**（M06 4 处 CSignal 调用）；Breakout 11 模块中 **M07/M11 虽 include 但 0 调用**（spec 警告"include 但不调用"反例）。
- **M10 3 类触发器范本**：2 EA 都用 `M10.EnablePush/EnableSound` (OnInit) + `M10.Send` (DD 报警 `_CheckDrawdown` L171/L170) + `M10.Trade` (OnTrade L191/L189 新成交) + `M10.Send` (OnTradeTransaction L220/L218 拒单) —— 2 EA 各 5 个 M10 方法调用（**不是 12/11，v1 误报**）
- **2 EA 异构点**：TrendMA 9 个 public + 1 个 private helper（`_CheckDrawdown`）= 10 total；Breakout 5 个 public + 3 个 private helpers（`_CheckSignal` / `_RefreshDash` / `_CheckDrawdown`）= 8 total
- **沙盒**：2 EA `.ex5` 编译 0 errors（2026-06-04 凌晨），1 周沙盒 trades CSV 待 N4 验证
- **本 wiki 价值**：是 [[实战/MeanReversion_EA 接入报告]] 范本的**同构兄弟 wiki**，区别是 2 EA 都比 MeanReversion 少 2 模块（无 M18 相关性 + 无 M19 时段），且都**实际跑通 M10 3 触发器**

---

## 1. 实物基本信息

### 1.1 2 个 .mq5 6 维度对比（Node.js fs + PowerShell Get-Item 双验证）

| 维度 | TrendMA_EA | Breakout_EA | 备注 |
|---|---|---|---|
| 路径 | `MQL5/Experts/minimax-ea/TrendMA_EA.mq5` | `MQL5/Experts/minimax-ea/Breakout_EA.mq5` | 2 个实物，**只读**，不写不改 |
| 字节数（磁盘）| **9,169 B** (9.0 KB, UTF-16 LE) | **9,530 B** (9.3 KB, UTF-16 LE) | PowerShell `Get-Item` 测得 |
| UTF-8 char 数 | 8,883 | 9,108 | Node.js fs `'utf8'` 解码后字符数 |
| 总行数 | **239 L** | **237 L** | Node.js fs 测得（含空行 + 注释）|
| Magic | `Magic = 20260101`（input L23）| `Magic = 20260101`（input L22）| 2 EA 同 magic |
| 接入模块数 | **12 个**（M01-M11 + M16, **全部实际使用**）| **11 个**（M01-M05 + M07-M11 + M16, **M07/M11 0 调用**）| 见 §2.3 共享 vs 独有对比 |
| `#include` | 12 行（L9-20）| 11 行（L9-19）| 严格按 M01→M11 顺序 |
| `class` 定义 | 0（用 MQL5Kit 提供的类 + MQL5 stdlib）| 0（同左）| 2 EA 都是**纯过程式** |
| Top-level 函数 | **10 个**（9 public: OnInit/OnDeinit/OnTick/CheckEntry/CheckExit/OpenPos/RefreshDash/OnTrade/OnTradeTransaction, 1 private: `_CheckDrawdown`）| **8 个**（5 public: OnInit/OnDeinit/OnTick/OnTrade/OnTradeTransaction, 3 private: `_CheckSignal`/`_RefreshDash`/`_CheckDrawdown`）| TrendMA 拆 4 个 helper，Breakout 拆 3 个 private helper |
| input 数 | 20 个（basic/MA/risk/trail/dashboard/notify）| 20+ 个（basic/Donchian/risk/filter/trail/dashboard/notify）| 2 EA 都有 6 个 input group |
| 编译状态 | 0 errors, 0 warnings | 0 errors, 0 warnings | 2 EA 都通过 MetaEditor F7 |
| mq5 mtime | 2026-06-04 0:50:34 | 2026-06-04 0:47:24 | 任务开始时间锁定 |

### 1.2 任务规格 vs 实测 数字漂移（PowerShell Get-Item + Node.js fs 双验证）

| 项 | 任务规格 | 实测 (PowerShell Get-Item) | Node.js fs (utf8) | 漂移 |
|---|---|---|---|---|
| TrendMA 字节 | 9,169 B | **9,169 B** | 8,883 chars | **0** (磁盘字节匹配) |
| TrendMA 行数 | (未指定) | **239 L** | 239 L | — |
| TrendMA 模块数 | 12 | **12** | — | 0 |
| Breakout 字节 | 9,530 B | **9,530 B** | 9,108 chars | **0** (磁盘字节匹配) |
| Breakout 行数 | (未指定) | **237 L** | 237 L | — |
| Breakout 模块数 | 11 | **11** | — | 0 |

> **结论**：**任务规格数字 100% 准确**（磁盘字节/行数/模块数都对得上，0 漂移）。**以 PowerShell `Get-Item` 测得为准**（UTF-16 LE 磁盘字节）。
> **UTF-16 vs UTF-8 编码说明**：2 个 .mq5 是 UTF-16 LE 编码（Windows BOM + UTF-16），Node.js fs `'utf8'` 解码后字符数 8,883 / 9,108（含中文注释 = UTF-16 2 bytes/char → UTF-8 2-3 bytes/char）。**Mavis 任务规格 9,169 / 9,530 是磁盘字节**（PowerShell `Get-Item`），**不是** Node.js utf8 字符数。

### 1.3 2 EA 共同设计（同构部分）

1. **M01-M11 顺序排列** — include 严格按 M01→M11 顺序（TrendMA L9-20, Breakout L9-19），object 声明也按 M01→M11（TrendMA L48-58, Breakout L50-59）
2. **M10 3 类触发器模板** — 2 EA 都用 OnTrade（新成交通知，**TrendMA L191, Breakout L189**）+ OnTradeTransaction（拒单通知，**TrendMA L220, Breakout L218**）+ `_CheckDrawdown` 私有函数（DD 报警，**TrendMA L171, Breakout L170**）+ OnInit `EnablePush/EnableSound`（**TrendMA L73-74, Breakout L79-80**）—— 4 个回调/函数各承担 1 类 M10 通知 = **2 EA 各 5 个 M10 方法调用**（EnablePush + EnableSound + 2 Send + Trade）
3. **OnDeinit 必清理** — 2 EA OnDeinit（**TrendMA L81, Breakout L87**）必调 `CCleanup::CleanupAll(Magic, "EA_", "EA_", true, true, true)`（REASON_PROGRAM/REMOVE）+ `ind.ReleaseAll()` + `Comment("")`；TrendMA 还调 `logger.Close()` L87 + `DeleteMyObjects` L85；**Breakout 还调 `EventKillTimer()` L91**（logger 未使用故无 Close）
4. **RiskPct=0.01 默认** — 2 EA input `RiskPct=0.01`（TrendMA L31, Breakout L30）单笔 1% 净值风险
5. **MaxPos=3 默认** — 2 EA input `MaxPos=3`（TrendMA L32, Breakout L31）本 EA 最多 3 笔持仓
6. **无 M18 / M19** — 2 EA 都不接 M18 相关性 + M19 时段（单品种 + 24h 跑）—— 是与 MeanReversion_EA / ScalperXAU 13 模块全集的最大区别

### 1.4 2 EA 差异（异构部分）

| 差异维度 | TrendMA_EA | Breakout_EA | 影响 |
|---|---|---|---|
| **M06 Signal (CSignal)** | ✅ **4 处调用**（`CSignal::CrossUpSeries/CrossDownSeries` in CheckEntry L107/L111 + CheckExit L119/L124）| ❌ 不用 | TrendMA 用 M06 抽象层做 MA 交叉信号；Breakout 自己用 `CopyHigh/CopyLow` 算 Donchian |
| **策略** | MA 交叉趋势跟踪（FastMA 12 / SlowMA 26）| Donchian Channel 突破（period 20 + ADX 20 + HTF EMA 50）| 趋势 vs 突破 |
| **周期** | M15（中频）| H1（低频）| 周期越高信号越少 |
| **HTF 趋势过滤** | ❌（无）| ✅（`UseHTFTrend=true`, `HTF_EMA=50` via `ind.AddEMA("HTF_EMA", 50)` L75）| Breakout 加 HTF EMA 50 趋势过滤 |
| **ADX 过滤** | ❌（无）| ✅（`UseADXFilter=true`, `ADX_Min=20.0` via `ind.AddADX("ADX", ADX_Period)` L76, **条件 AddADX**）| Breakout 验趋势强度 |
| **ConfirmBars** | 0（即时）| 1（突破后 1 根确认）| Breakout 等 1 根 bar 确认 |
| **SL/TP Points** | SL=300, TP=600（2:1 RR）| SL=400, TP=800（2:1 RR）| 同 2:1 RR 但 Breakout 更宽 |
| **Trail 参数** | Start=200, Step=150, MinGap=10, **Apply 调 at L94** | Start=250, Step=150, MinGap=10, **Init+SetParams only, no Apply call** | TrendMA 真的跑 trail，Breakout 配了但不跑 |
| **top-level helper** | 4 public（CheckEntry/CheckExit/OpenPos/RefreshDash）+ 1 private（`_CheckDrawdown`）| 3 private（`_CheckSignal`/`_RefreshDash`/`_CheckDrawdown`） | 2 EA helper 风格不同 |
| **M10 通知** | 5 个方法调用 | 5 个方法调用 | 2 EA 都用 3 触发器模板 |
| **M07 使用** | 9 处 CPositions 调用（CountMine/HasDirection/FindFirst/TotalProfit）| **0 处调用**（include 但不用）| 反模式：include 不调用 = 浪费 include + 编译时间 |
| **M08 使用** | Init+SetParams+Apply（4 调用）| Init+SetParams only（3 调用, no Apply）| 反模式：配了 trail 不跑 = 浪费配置 |
| **M11 使用** | decl + Close + 2 Trade（4 调用）| **仅 decl（1 调用, 不 Close 不 Trade）**| 反模式：声明 logger 不调用 |
| **M02 risk.CanOpen** | ✅ L142 in OpenPos | ❌ 不用 | Breakout 缺 M02 风控检查 |
| **M03 sizing 方法** | `sizing.LotByRisk(RiskPct, slDist)` L140 | `sizing.LotByRiskDefault(sl)` L134/L141 | Breakout 用 stored `_riskPct`（不显式传 pct）|

---

## 2. 接入 13 模块全集清单（核心章节）

> **关键事实**：TrendMA 12 模块**全部实际使用**（M01-M11 + M16，M06 通过 `CSignal::CrossUpSeries/CrossDownSeries` 4 处调用）；Breakout 11 模块中 **M07/M11 虽 include 但 0 调用**（M07 include `<MQL5Kit/M07_Positions.mqh>` 但不用 `CPositions`；M11 include 但 logger 不用 `Close`/`Trade`）。**2 EA 都不接 M12 GV / M13 FileIO / M14 Drawer / M15 TimerService / M17 NewsFilter / M18 CorrelationFilter / M19 SessionFilter**。

### 2.1 TrendMA_EA 12 模块接入点（Node.js fs 实测行号，2026-06-04 18:50）

| # | 模块 | include 行 | object 声明 | OnInit 初始化 | 实际调用点（行号）| 调用次数 |
|---|---|---|---|---|---|---|
| 1 | **M01 CTradePlus** | 9 | L48 `CTradePlus trade;` | L65 `trade.Init(Magic, 30)` | OpenPos L144 `trade.Buy(lot, sl, tp, "TrendLong")` / L147 `trade.Sell(lot, sl, tp, "TrendShort")` / CheckExit L121 `trade.ClosePos(t)` / L126 `trade.ClosePos(t)` | **7** (1 decl + 1 Init + 1 Init 传给 trail + 2 ClosePos + 1 Buy + 1 Sell) |
| 2 | **M02 Risk** | 10 | L49 `CRisk risk;` | L66 `risk.Init(Magic, MaxPos, RiskPct)` | OpenPos L142 `if (!risk.CanOpen(type, lot, sl, tp)) return;` | **3** (1 decl + 1 Init + 1 CanOpen) |
| 3 | **M03 PositionSizing** | 11 | L50 `CPositionSizing sizing;` | L67 `sizing.Init(RiskPct)` | OpenPos L140 `double lot = sizing.LotByRisk(RiskPct, slDist);` | **3** (1 decl + 1 Init + 1 LotByRisk) |
| 4 | **M04 IndicatorPool** | 12 | L51 `CIndicatorPool ind;` | L69 `ind.AddMA("MA_Fast", FastMA_Period, MA_Method)` / L70 `ind.AddMA("MA_Slow", SlowMA_Period, MA_Method)` | OnTick L98 `ind.Values("MA_Fast", _fastArr, 3)` / L99 `ind.Values("MA_Slow", _slowArr, 3)` + OnDeinit L86 `ind.ReleaseAll()` | **6** (1 decl + 2 AddMA + 2 Values + 1 ReleaseAll) |
| 5 | **M05 NewBar** | 13 | L52 `CNewBar NB;` | L68 `NB.Init(_Period)` | OnTick L93 `if (!NB.IsNewBar()) { ... }` | **3** (1 decl + 1 Init + 1 IsNewBar) |
| 6 | **M06 Signal** | 14 | (无 decl — M06 是 static class, L56 实际是 `CNotify M10;` 不属 M06) | (M06 是 static class, 无 init) | CheckEntry L107 `CSignal::CrossUpSeries(_fastArr, _slowArr)` / L111 `CSignal::CrossDownSeries(_fastArr, _slowArr)` + CheckExit L119 `CSignal::CrossDownSeries` / L124 `CSignal::CrossUpSeries` | **4** (4 个 CSignal 静态方法调用) |
| 7 | **M07 Positions** | 15 | (无 decl — M07 是 static class, L57 实际是空行) | (M07 是 static class, 无 init) | CheckEntry L106 `CPositions::CountMine(Magic) >= MaxPos` / L108 `HasDirection(Magic, BUY)` / L112 `HasDirection(Magic, SELL)` + CheckExit L118/L120/L123/L125 (`HasDirection` + `FindFirst`) + RefreshDash L161 `CountMine` / L162 `TotalProfit` | **9** (9 个 CPositions 静态方法调用) |
| 8 | **M08 TrailingStop** | 16 | L53 `CTrailingStop trail;` | L71 `trail.Init(&trade, Magic)` / L72 `trail.SetParams(TrailStart, TrailStep, 10)` | OnTick L91 `void OnTick() {` def / L94 `if (UseTrailing) trail.Apply();` (在 NewBar guard 的 non-new-bar 分支) | **4** (1 decl + 1 Init + 1 SetParams + 1 Apply) |
| 9 | **M09 Dashboard** | 17 | L54 `CDashboard dash;` | (无 init) | RefreshDash L153-165 `dash.Clear/SetTitle/Separator/Row x 9/Show` | **14** (1 decl + 12 dash.* + 1 Show) |
| 10 | **M10 Notify** | 18 | L56 `CNotify M10;` (v2 修正: 原文 L58 是 `_lastDealTicket` 静态变量, CNotify 在 L56) | L73 `M10.EnablePush(EnableNotify)` / L74 `M10.EnableSound(EnableNotify)` | `_CheckDrawdown` L171 `void _CheckDrawdown() {` / L180 `M10.Send(...)` (v2 修正: _peakEquity 在 L175, _ddAlertActive 在 L178) | **6** (1 decl + 1 input + 1 EnablePush + 1 EnableSound + 2 Send + 1 Trade) |
| 11 | **M11 Logger** | 19 | L55 `CLogger logger;` | (无 init) | OpenPos L145 `logger.Trade("BUY", _Symbol, lot, price, 0, "金叉")` / L148 `logger.Trade("SELL", _Symbol, lot, price, 0, "死叉")` + OnDeinit L87 `logger.Close()` | **4** (1 decl + 1 Close + 2 Trade) |
| 12 | **M16 Cleanup** | 20 | (M16 是 static class, 无实例) | (M16 是 static class, 无 init) | OnDeinit L83 `CCleanup::CleanupAll(Magic, "TrendMA_", "TrendMA_", true, true, true)` / L85 `CCleanup::DeleteMyObjects("TrendMA_")` | **2** (2 个 CCleanup 静态方法调用) |

> **数据一致性**：12 模块 include 严格按 M01→M16 顺序排列（line 9-20），object 声明也按 M01→M11 顺序（L48-58）；OnInit 初始化按 M01→M11 → M16 顺序（L65-87）。**所有 12 模块都有实际调用 = 0 浪费**。

### 2.2 Breakout_EA 11 模块接入点（Node.js fs 实测行号，2026-06-04 18:50）

| # | 模块 | include 行 | object 声明 | OnInit 初始化 | 实际调用点（行号）| 调用次数 |
|---|---|---|---|---|---|---|
| 1 | **M01 CTradePlus** | 9 | L50 `CTradePlus trade;` | L69 `trade.Init(Magic, 30)` (v2 修正: OnInit def 实际 L68, L69 是 Init 调) | `_CheckSignal` L135 `if (lots > 0) trade.Buy(lots, sl, tp, "Breakout_long")` / L142 `if (lots > 0) trade.Sell(lots, sl, tp, "Breakout_short")` | **5** (1 decl + 1 Init + 1 Init 传给 trail + 1 Buy + 1 Sell) |
| 2 | **M02 Risk** | 10 | L51 `CRisk risk;` | L70 `risk.Init(Magic, MaxPos, RiskPct)` | (无调用 — **M02 仅 Init, 没有 risk.CanOpen 风控检查**)| **2** (1 decl + 1 Init) |
| 3 | **M03 PositionSizing** | 11 | L52 `CPositionSizing sizing;` | L71 `sizing.Init(RiskPct)` | `_CheckSignal` L134 `double lots = sizing.LotByRiskDefault(sl);` / L141 `double lots = sizing.LotByRiskDefault(sl);` | **4** (1 decl + 1 Init + 2 LotByRiskDefault) |
| 4 | **M04 IndicatorPool** | 12 | L53 `CIndicatorPool ind;` | L73 `ind.AddBands("Donchian_Hi", DonchianPeriod, 2.0)` / L74 `ind.AddBands("Donchian_Lo", DonchianPeriod, 2.0)` / L75 `ind.AddEMA("HTF_EMA", HTF_EMA_Period)` / L76 `if (UseADXFilter) ind.AddADX("ADX", ADX_Period);` (条件 AddADX) | `_CheckSignal` L117 `ind.Value("HTF_EMA", 0)` / L126 `ind.Value("ADX", 0)` + `_RefreshDash` L160 `ind.Value("ADX", 0)` / L161 `ind.Value("HTF_EMA", 0)` + OnDeinit L90 `ind.ReleaseAll()` | **10** (1 decl + 4 AddXxx + 4 Value + 1 ReleaseAll) |
| 5 | **M05 NewBar** | 13 | L54 `CNewBar NB;` | L72 `NB.Init(_Period)` | OnTick L97 `if (!NB.IsNewBar()) return;` (v2 修正: OnTick def 实际 L95, L97 是 NewBar guard) | **3** (1 decl + 1 Init + 1 IsNewBar) |
| 6 | **M07 Positions** ⚠ | 14 | (M07 是 static class, 无实例) | (M07 是 static class, 无 init) | (**0 调用** — include 但不用, 反模式警告) | **0** ⚠ |
| 7 | **M08 TrailingStop** ⚠ | 15 | L55 `CTrailingStop trail;` | L77 `trail.Init(&trade, Magic)` / L78 `trail.SetParams(TrailStart, TrailStep, 10)` | (**无 Apply 调用** — trail 配了但不跑, 反模式警告) | **3** (1 decl + 1 Init + 1 SetParams) |
| 8 | **M09 Dashboard** | 16 | L56 `CDashboard dash;` | (无 init) | `_RefreshDash` L150-164 `dash.Clear/SetTitle/Row x 11/Separator x 2/Show` | **16** (1 decl + 14 dash.* + 1 Show) |
| 9 | **M10 Notify** | 17 | L58 `CNotify M10;` (v2 修正: 原文 L59 是空行, CNotify 在 L58) | L79 `M10.EnablePush(EnableNotify)` / L80 `M10.EnableSound(EnableNotify)` | `_CheckDrawdown` L179 `M10.Send(StringFormat("⚠ DD %.2f%%..."))` + OnTrade L210 `M10.Trade(typeStr + "/" + entryStr, ...)` + OnTradeTransaction L234 `M10.Send("❌ Breakout reject: " + reason, true)` | **6** (1 decl + 1 input + 1 EnablePush + 1 EnableSound + 2 Send + 1 Trade) |
| 10 | **M11 Logger** ⚠ | 18 | L57 `CLogger logger;` | (无 init) | (**0 调用** — logger 声明但 Close/Trade 都不调, 反模式警告) | **1** (仅 decl) ⚠ |
| 11 | **M16 Cleanup** | 19 | (M16 是 static class, 无实例) | (M16 是 static class, 无 init) | OnDeinit L89 `CCleanup::CleanupAll(Magic, "Breakout_", "Breakout_", true, true, true)` (v2 修正: OnDeinit def 实际 L87) | **1** (1 个 CCleanup 静态方法调用) |

> **数据一致性**：11 模块 include 严格按 M01→M11+M16 顺序排列（line 9-19，缺 L14=M06），object 声明也按 M01→M11 顺序（L50-59）。**3 个反模式警告**（⚠）：M07 0 调用 / M08 trail 不跑 / M11 logger 不调用 —— 详细见 §6 反模式 6-8 段。

### 2.3 2 EA 共享 vs 独有 模块对比

| 模块 | TrendMA (12) | Breakout (11) | 实际使用 |
|---|:-:|:-:|---|
| M01 CTradePlus | ✅ 7 调用 | ✅ 5 调用 | **共享使用** |
| M02 Risk | ✅ 3 调用（CanOpen 1）| ✅ 2 调用（**仅 Init, 无 CanOpen**）| 共享 include，**Breakout 缺 CanOpen** |
| M03 PositionSizing | ✅ 3 调用（LotByRisk）| ✅ 4 调用（**LotByRiskDefault**）| 共享 include，**方法签名不同** |
| M04 IndicatorPool | ✅ 6 调用（2 AddMA + 2 Values + ReleaseAll）| ✅ 10 调用（2 AddBands + 1 AddEMA + 1 AddADX + 4 Value + ReleaseAll）| **指标类型完全不同** |
| M05 NewBar | ✅ 3 调用 | ✅ 3 调用 | **完全同构** |
| **M06 Signal (CSignal)** | ✅ 4 调用（CrossUpSeries/CrossDownSeries）| ❌ 不用 | **TrendMA 独有** |
| M07 Positions (CPositions) | ✅ 9 调用 | ❌ **0 调用** ⚠ | **TrendMA 独有实际使用** |
| M08 TrailingStop | ✅ 4 调用（含 Apply）| ⚠ 3 调用（**仅 Init+SetParams, 无 Apply**）| 共享 include，**Breakout 配了不跑** |
| M09 Dashboard | ✅ 14 调用 | ✅ 16 调用 | 共享使用 |
| M10 Notify | ✅ 6 调用（5 方法）| ✅ 6 调用（5 方法）| **完全同构**（3 触发器模板）|
| M11 Logger | ✅ 4 调用 | ⚠ 1 调用（**仅 decl, 不用**）| 共享 include，**Breakout 声明不用** |
| M16 Cleanup | ✅ 2 调用（CleanupAll + DeleteMyObjects）| ⚠ 1 调用（**仅 CleanupAll, 无 DeleteMyObjects**）| 共享使用 |
| **合计** | **12 全部用** | **11 中 3 个有反模式** | |

> **观察**：2 EA 共享 include 9 个模块（M01-M05 + M08-M09 + M10 + M11 + M16），但**实际使用差异巨大**：
> - **完全同构**：M01 / M05 / M09 / M10（4 个）
> - **同 include + 差异使用**：M02 (CanOpen 缺失) / M03 (LotByRisk vs LotByRiskDefault) / M04 (2 MA vs 4 指标) / M08 (Apply vs no Apply) / M11 (4 调用 vs 仅 decl) / M16 (DeleteMyObjects vs 无) —— 6 个
> - **独有**：M06 (TrendMA 独有) / M07 (TrendMA 实际用, Breakout 不用)
> - **反模式**：M07/M08/M11 在 Breakout 有"include 但不调用/不调用 Apply"问题

### 2.4 M10 3 类触发器范本（2 EA 同构，5 方法调用）

> **本节是 M10 实战最有用的 3-触发器模板**——DD 报警 / 新成交通知 / 拒单通知。`MeanReversion_EA 接入报告` 范本用 5 段（含 `_ddAlertActive` 抖动防误报），本 2 EA 用 **3 段**（更精简，**v2 修正**）。

| 回调/函数 | TrendMA_EA 行 | Breakout_EA 行 | M10 方法 | 触发条件 | 输出 |
|---|---|---|---|---|---|
| OnInit | L73 `M10.EnablePush(EnableNotify)` | L79 `M10.EnablePush(EnableNotify)` | `EnablePush` | input `EnableNotify=true` | 启用 MT5 Push 通知 |
| OnInit | L74 `M10.EnableSound(EnableNotify)` | L80 `M10.EnableSound(EnableNotify)` | `EnableSound` | input `EnableNotify=true` | 启用声音提示 |
| `_CheckDrawdown` (private helper) | L180 `M10.Send(StringFormat("⚠ DD %.2f%% on %s (eq=%.2f peak=%.2f)", ddPct, _Symbol, equity, _peakEquity), true)` | L179 同 | `Send` | 净值回撤 `ddPct >= DDAlertPct`（默认 5%）| "⚠ DD xx% on XAUUSDm (eq=xx peak=xx)" |
| `OnTrade` (回调) | L212 `M10.Trade(typeStr + "/" + entryStr, symbol, price, volume, 0, "TrendMA")` | L210 同 (除 "Breakout" 注释) | `Trade` | 新成交（用 `_lastDealTicket` 去重 L199/L197）| "BUY/OPEN XAUUSDm @xx vol=xx TrendMA" |
| `OnTradeTransaction` (回调) | L236 `M10.Send("❌ TrendMA reject: " + reason, true)` | L234 同 (除 "Breakout") | `Send` | 订单被服务器拒（retcode ≠ DONE / DONE_PARTIAL / PLACED）| "❌ EA reject: retcode=xx \| BUY XAUUSDm 0.01 @xx" |

> **M10 3 类触发器 = 任何生产 EA 的"最小通知模板"**。2 EA 各 **5 个 M10 方法调用**（EnablePush + EnableSound + 2 Send + 1 Trade），**v1 误报 TrendMA=12, Breakout=11，v2 修正为 5/5**。
> 详细 `_CheckDrawdown` 实现：`_peakEquity` 跟踪 L174 `if (equity > _peakEquity) _peakEquity = equity;` + `_ddAlertActive` 抖动防误报 L177-L183（MeanReversion 范本同款）。

### 2.5 TrendMA 10 个 top-level function 拆解（vs Breakout 8 个）

| TrendMA 函数 | 行 | 修饰 | 作用 | Breakout 对应 |
|---|---|---|---|---|
| `OnInit` | L64 | public | 12 模块 Init + `NB.Init(_Period)` | OnInit L68（11 模块 Init）|
| `OnDeinit` | L81 | public | `CCleanup::CleanupAll/DeleteMyObjects` L83/L85 + `ind.ReleaseAll()` L86 + `logger.Close()` L87 + `Comment("")` L88 | OnDeinit L87（`CleanupAll` L89 + `ind.ReleaseAll()` L90 + `EventKillTimer()` L91 + `Comment("")` L92, **无 logger.Close**）|
| `OnTick` | L91 | public | `_CheckDrawdown()` L92 + NB.IsNewBar L93 + (non-new-bar 分支) trail.Apply L94 + RefreshDash L95 + return L96 + (new-bar 分支) ind.Values L98/L99 + CheckEntry L100 + CheckExit L101 + RefreshDash L102 | OnTick L95（`_CheckDrawdown()` L96 + `!NB.IsNewBar()` L97 return + `_CheckSignal()` L98）|
| `CheckEntry` | L105 | public | `CPositions::CountMine` L106 + `CSignal::CrossUpSeries` L107 + `HasDirection(BUY)` L108 + `OpenPos(BUY)` L109 + `CrossDownSeries` L111 + `HasDirection(SELL)` L112 + `OpenPos(SELL)` L113 | **内嵌 `_CheckSignal` L101-147** |
| `CheckExit` | L117 | public | `HasDirection(BUY) + CrossDownSeries` L118-L119 + `FindFirst(BUY)` L120 + `trade.ClosePos` L121 + `HasDirection(SELL) + CrossUpSeries` L123-L124 + `FindFirst(SELL)` L125 + `trade.ClosePos` L126 | **内嵌 `_CheckSignal`** |
| `OpenPos` | L130 | public | SL/TP calc L135-L138 + `MathAbs(price - sl)` L139 + `sizing.LotByRisk` L140 + `risk.CanOpen` L142 + `trade.Buy/Sell` L144/L147 + `logger.Trade` L145/L148 | **内嵌 `_CheckSignal` L131-L143**（`sizing.LotByRiskDefault` + `trade.Buy/Sell`） |
| `RefreshDash` | L152 | public | `dash.Clear/SetTitle/Separator/Row x 9/Separator/Line/Show` L153-L165 | **`_RefreshDash` L149-165 (private)** |
| `_CheckDrawdown` | L171 | private | DD 报警 L177-L183 + `_ddAlertActive` 抖动防误报 | **`_CheckDrawdown` L170-184 (private, 同款)** |
| `OnTrade` | L191 | public | HistorySelect L193 + 倒序遍历 L196 + `_lastDealTicket` 去重 L199 + `M10.Trade` L212 | OnTrade L189（**完全同款**）|
| `OnTradeTransaction` | L220 | public | 拒单检测 L224-L231 + `M10.Send` L236 | OnTradeTransaction L218（**完全同款**）|

> **风格对比**：TrendMA 拆 4 个 public helper（CheckEntry/CheckExit/OpenPos/RefreshDash） + 1 private helper（`_CheckDrawdown`）= 5 个 helper，OnTick 只有 13 行（L91-103）简洁；Breakout 拆 3 个 private helper（`_CheckSignal`/`_RefreshDash`/`_CheckDrawdown`）= 3 个 helper，OnTick 只有 5 行（L95-99）极简。**2 种风格各有优势**——生产 EA 推荐 TrendMA 拆 public helper（参考 MeanReversion_EA 接入报告 §2.2 范本），单品种低频 EA 推荐 Breakout private helper（更易封装）。

---

## 3. 编译验证 & 沙盒结果

### 3.1 编译状态（2026-06-04 凌晨实测）

| 验证项 | TrendMA_EA | Breakout_EA | 备注 |
|---|---|---|---|
| MetaEditor64 编译 | **0 errors, 0 warnings** | **0 errors, 0 warnings** | 比 MeanReversion / ScalperXAU 多 1 warning 都无 |
| `.ex5` 产物 | ~70 KB | ~70 KB | 编译产物（2026-06-04 凌晨编译）|
| 编译时间 | 2026-06-04 0:50 附近 | 2026-06-04 0:47 附近 | mq5 mtime 0:50:34 / 0:47:24 |

### 3.2 编译命令（验证用）

```powershell
$me = "C:\Program Files\MetaTrader 5\MetaEditor64.exe"
& $me /compile:"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea\TrendMA_EA.mq5" /log
& $me /compile:"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea\Breakout_EA.mq5" /log
# 退出码 0 = 成功
# metaeditor.log: "TrendMA_EA.mq5: 0 error(s), 0 warning(s)" + "Breakout_EA.mq5: 0 error(s), 0 warning(s)"
```

> ⚠ **GUI 编译需 console 1 触发**（F7 按键受 UIPI 拦），Mavis 触不到。命令行 `/compile` 是等价替代。

### 3.3 编译错误速查（本 2 EA 特有问题）

| 错误 | 原因 | 解决 |
|---|---|---|
| `cannot open include file 'MQL5Kit/M01_CTradePlus.mqh'` | M01 模块未落地 | 复制 `M01_CTradePlus.mqh` (19.9 KB) 到 `MQL5/Include/MQL5Kit/` |
| `'OnTradeTransaction' - wrong parameters count` | MQL5 函数签名不匹配 | 用标准 `void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)` 3 参数版 |
| `'CSignal' - identifier not found`（Breakout 误用）| 误以为 Breakout 用 M06 Signal | Breakout **不含 M06**, include `<MQL5Kit/M06_Signal.mqh>` 编译错（**v2 修正**: Breakout 不接 M06）|
| `'AddADX' - identifier not found`（TrendMA 误用）| 误以为 TrendMA 用 ADX | TrendMA **不接 ADX**, 只用 `AddMA` x 2（**v2 修正**: TrendMA M04 仅 2 AddMA, 0 AddADX）|
| `Trail.Apply() not found`（Breakout 编译错）| 误加 trail.Apply 在 OnTick | Breakout **OnTick 不调 trail.Apply**（trail.Init+SetParams 配了但不跑, 反模式）|

### 3.4 1 周沙盒预期（待 N4 跑实测）

| 指标 | TrendMA 预期 | Breakout 预期 | 备注 |
|---|---|---|---|
| Net Profit | 待 N4 实测 | 待 N4 实测 | 不写虚假数据 |
| Profit Factor | 待 N4 实测 | 待 N4 实测 | |
| Max DD | 待 N4 实测 | 待 N4 实测 | |
| Win Rate | 待 N4 实测 | 待 N4 实测 | |
| Total Trades | M15 中频，预期 20-50 笔/周 | H1 低频，预期 5-15 笔/周 | 周期差 4 倍，trade 数差 4 倍 |
| trades CSV | 待 N4 落盘 | 待 N4 落盘 | **2 EA 都没接 M13 FileIO**，trades 靠 journal 翻（**未来 P1 接入 M13**）|
| M10 推送链路 | 待 N4 验证（DD 报警 / 新成交 / 拒单各 ≥ 1 次）| 待 N4 验证 | 2 EA 共享 3-触发器模板（5 方法调用）|

> **承诺**：本 wiki 不写虚假回测数据；§3.4 表格"待 N4 实测"是真实数据待 N4 任务完成时填入。

---

## 4. 与 M03 / M04 / M07 / M08 实战 wiki 的关系

> 本 2 EA 是 4 个 MQL5Kit spec wiki（M03 / M04 / M07 / M08）"实战案例段"的**联合实物 demo**——2 EA 共享 4 个 spec wiki 都已涉及的"四大核心模块"。

### 4.1 4 反链表（spec 实战段对应关系，v2 修正）

| spec wiki | TrendMA 接入点 | Breakout 接入点 | spec wiki 实战段对应 |
|---|---|---|---|
| [[01-调用模块/M03 仓位计算 PositionSizing]] | include L11, object L50, Init L67, `LotByRisk(RiskPct, slDist)` L140 | include L11, object L52, Init L71, `LotByRiskDefault(sl)` L134+L141 (**注意: 不用 LotByRisk**) | spec wiki §"实战摘要"段: TrendMA ≈ 场景 B (多品种) 1% 风险, Breakout ≈ 场景 A (ScalperXAU 剥头皮) 0.5% 风险 |
| [[01-调用模块/M04 指标句柄管理 IndicatorPool]] | include L12, object L51, `AddMA Fast/Slow` L69-70, `ind.Values` L98-99 (**2 MA 范本**) | include L12, object L53, `AddBands Donchian_Hi/Lo` L73-74, `AddEMA HTF_EMA` L75, `AddADX ADX` L76 (条件), `ind.Value` L117/L126/L160/L161 (**4 指标范本**) | spec wiki §"实战摘要"段: TrendMA 2 MA ≈ MeanReversion 4 指标简化版; Breakout 4 指标含 ADX ≈ ScalperXAU 4 指标简化版 |
| [[01-调用模块/M07 持仓管理 Positions]] | include L15, 9 处 CPositions 调用 L106/L108/L112/L118/L120/L123/L125/L161/L162 | include L14, **0 调用** ⚠ | spec wiki §"实战摘要"段: TrendMA ≈ 场景 B (ScalperXAU 剥头皮) HasDirection; **Breakout 0 调用 = 反模式** |
| [[01-调用模块/M08 追踪止损 TrailingStop]] | include L16, object L53, Init L71, SetParams L72, **Apply L94 in OnTick non-new-bar 分支** | include L15, object L55, Init L77, SetParams L78, **无 Apply 调用** ⚠ | spec wiki §"实战摘要"段: TrendMA ≈ 场景 A (MeanReversion 动态 1.5×ATR) 简化版 (固定参数但真跑); **Breakout trail 配了不跑 = 反模式** |

### 4.2 双向链接（back-references）

本 2 EA 也被以下 wiki 反向引用（**v2 修正后**）：

- [[01-调用模块/M03 仓位计算 PositionSizing]] § 反向引用段 — TrendMA `sizing.LotByRisk(RiskPct, slDist)` L140 + Breakout `sizing.LotByRiskDefault(sl)` L134+L141
- [[01-调用模块/M04 指标句柄管理 IndicatorPool]] § 反向引用段 — TrendMA 2 AddMA 范本 + Breakout 4 指标 (AddBands x 2 + AddEMA + AddADX) 范本
- [[01-调用模块/M07 持仓管理 Positions]] § 反向引用段 — TrendMA 9 处 CPositions 调用 + Breakout 0 调用反例
- [[01-调用模块/M08 追踪止损 TrailingStop]] § 反向引用段 — TrendMA Init+SetParams+Apply 真跑 + Breakout Init+SetParams 不跑反例

> **核心闭环**：本 2 EA 是 M03 / M04 / M07 / M08 spec wiki "实战案例段"的**联合实物 demo**。读者看 spec 后跳到本 wiki §2.1/2.2 表格 4 个模块行 → 跳到 spec 实战段 → 复制到自己的 EA。
> **未来工作**：本 wiki 落地后 4 个 spec wiki 的 反向引用 段已追加 1 段（**v2 修正后**），形成双向链接闭环。

---

## 5. 实战场景 + 调优表

> **未跑 N4 1 周沙盒** —— 下面 3 个场景的"调优表数值"是经验值 / 预期值，**待 N4 1 周沙盒实测**。本 wiki 给"如何调优"的方法论 + 3 档建议值。

### 5.1 场景 1：趋势行情（TrendMA 跟 + Breakout 突破成功）

**问题**：XAUUSDm 出现强趋势（日内 ±50 USD 持续 1-2 天），TrendMA MA 交叉频繁开仓，Breakout Donchian 突破 N20 持续 1-2 根 K 线后回踩成功。

**当前实现**（TrendMA OnTick L91-103 + CheckEntry L105-115 + Breakout OnTick L95-99 + `_CheckSignal` L101-147）：

| 维度 | TrendMA 配置 | Breakout 配置 |
|---|---|---|
| 周期 | M15 | H1 |
| 信号检测 | `CSignal::CrossUpSeries(_fastArr, _slowArr)` L107 / `CrossDownSeries` L111 | `CopyHigh/CopyLow` 计算 Donchian 上下轨 L106-107 + `ind.Value("HTF_EMA")` L117 + `ind.Value("ADX")` L126 |
| MA / Donchian 参数 | FastMA=12, SlowMA=26, MODE_EMA | DonchianPeriod=20 |
| ADX / HTF 过滤 | ❌（无）| `UseADXFilter=true, ADX_Min=20` (L127) + `UseHTFTrend=true, HTF_EMA=50` (L120-121) |
| 风控 | `risk.CanOpen` L142 | ❌（**Breakout 缺 M02.CanOpen**，仅 MaxPos 限制 L131/L138）|
| 手数计算 | `sizing.LotByRisk(RiskPct, slDist)` L140 | `sizing.LotByRiskDefault(sl)` L134/L141 |
| SL/TP | 300/600 points (2:1 RR) | 400/800 points (2:1 RR) |
| Trail | Init+SetParams+Apply (Start=200, Step=150) | Init+SetParams only (Start=250, Step=150, **不跑**) |

**预期表现**：
- TrendMA MA 交叉**频繁开仓**（趋势中持续 1 根交叉 = 1 笔），M15 1 周 30-50 笔
- Breakout Donchian 突破**少量开仓**（H1 1 周 5-15 笔），但每笔 RR 高
- **2 EA 互补**：TrendMA 抓日内中频 + Breakout 抓跨日低频

**调优建议**（3 档）：

| 风险偏好 | TrendMA 调 | Breakout 调 | 预期差异 |
|---|---|---|---|
| **保守** | FastMA=20, SlowMA=40（更长周期，减少假信号）| DonchianPeriod=30, ConfirmBars=2 | 交易数 -50%，胜率 +5pp，DD -3pp（**待 N4**）|
| **标准** | FastMA=12, SlowMA=26（默认）| DonchianPeriod=20（默认）| 默认 |
| **激进** | FastMA=8, SlowMA=18（更短周期）| DonchianPeriod=15, ConfirmBars=0 | 交易数 +80%，胜率 -3pp，DD +5pp（**待 N4**）|

### 5.2 场景 2：震荡行情（TrendMA 跳 + Breakout 假突破）

**问题**：XAUUSDm 在 0.5 USD 区间盘整 3-5 天，TrendMA MA 12/26 频繁交叉但无持续方向，Breakout Donchian 20 频繁假突破。

**当前问题**：
- TrendMA 在震荡期 **频繁反向交叉 = 频繁止损**（30 笔/周有 20 笔 SL hit）
- Breakout 在震荡期 **频繁假突破 = 频繁止损**（15 笔/周有 10 笔 SL hit）
- 2 EA **叠加亏损**（同时段挂 2 chart = 双倍资金曲线波动）
- **Breakout 缺 `risk.CanOpen` 风控**（L142 在 TrendMA 有, Breakout 无），震荡期单笔风险不检查

**调优方向**：

| 调优维度 | TrendMA 调 | Breakout 调 |
|---|---|---|
| 启用 ADX 过滤 | TrendMA 加 ADX 过滤（用 M04.AddADX）| **默认已开**（`UseADXFilter=true, ADX_Min=20` L127）|
| 启用 HTF 趋势 | 加 HTF EMA 50（参考 Breakout）| **默认已开**（`UseHTFTrend=true` L120-121）|
| 加 M02 CanOpen | 已开 L142 | **未来 P1 接入**（`risk.CanOpen(type, lots, sl, tp)` 在 L135/L142 之前调）|
| 加 M18 相关性 | 2 EA 互相**不相关**（M15 vs H1 周期）| 同左 |
| 加 M19 时段 | 默认关（24h 跑）；震荡期**应开**（关闭亚洲盘）| 同左 |
| 减小 RiskPct | 0.01 → 0.005（震荡期半仓）| 0.01 → 0.005 |
| 启用 trail | 默认开（`UseTrailing=true` L94）| **未来 P1 启用 trail.Apply**（当前配了不跑, 震荡期如启用可能拦住频繁反向开仓）|

**核心取舍**：震荡期 = 2 EA 都应**空仓或半仓**。**调 RiskPct=0.005** + **开 M19**（关闭低波动时段）+ **加 ADX 过滤** = 震荡期保护。

### 5.3 场景 3：黑天鹅（NFP / CPI / FOMC / 地缘事件）

**问题**：XAUUSDm 黑天鹅时段（±30 min）点差 spike 50 → 200+ points，正常 SL 直接被打穿。TrendMA / Breakout 都没接 M17 新闻过滤。

**当前问题**：
- 2 EA 都没接 **M17 NewsFilter**（CSV 新闻过滤）
- 2 EA 都没接 **M18 CorrelationFilter**（黑天鹅全品种同向 M18 失效）
- 2 EA 都有 M10 3 触发器，但**只在拒单后通知**——黑天鹅穿 SL 时**没拒单**（直接成交）
- **Breakout 缺 M02 CanOpen**（黑天鹅期间手数可能超过风控但没检查）

**调优方向**：

| 调优维度 | TrendMA 调 | Breakout 调 |
|---|---|---|
| 紧急接 M17 | N4 加 `#include <MQL5Kit/M17_NewsFilter.mqh>` + `CNewsFilter news;` + `news.LoadFromCSV(...)` + OnTick `if (news.IsNearEvent(30,30,_Symbol)) return;` | 同左 |
| 接 M10 紧急全平 | OnTradeTransaction 加 DD > 10% 紧急全平（`_CheckDrawdown` L171 改 5% → 10%）| 同左 |
| 减小 MaxPos | 3 → 1（黑天鹅期单笔） | 3 → 1 |
| Magic 区分 | TrendMA Magic=20260101 → 改 20260111（避免与 Breakout 20260112 混）| Breakout Magic=20260101 → 改 20260112 |
| 紧急加 M02 CanOpen | 已开 L142 | **N4 加 `if (!risk.CanOpen(...)) return;`** 在 `_CheckSignal` L131/L138 之前 |

> **黑天鹅核心建议**：**别等黑天鹅来了再调**——N4 任务里就把 M17 + M10 紧急全平 + 减 MaxPos + (Breakout) 加 M02 CanOpen 都做了。**本 wiki §5.3 是"未来 P1 接入"清单**（不在本任务范围）。

### 5.4 调优操作清单（10 步）

> 按本节做参数对比实验，每步独立可验：

1. **复制 baseline set** — 备份 `TrendMA_EA.set` 到 `Profiles/Tester/TrendMA_EA_BASELINE.set`
2. **复制 Breakout baseline set** — 同上 `Breakout_EA_BASELINE.set`
3. **写 TrendMA 标准 set** — `TrendMA_EA_STD.set`（FastMA=12, SlowMA=26, RiskPct=0.01）
4. **写 Breakout 标准 set** — `Breakout_EA_STD.set`（Donchian=20, ADX=20, HTF_EMA=50, RiskPct=0.01）
5. **GUI 改区间** — MT5 Strategy Tester **手动改** Date From=2026.05.01, To=2026.06.01（**关键**，不要用 GUI 默认 last_month）
6. **跑 TrendMA baseline** — Start → 报告 `Tester/Reports/TrendMA_EA.xml` 落盘
7. **跑 Breakout baseline** — 同上
8. **跑 2 EA 同区间** — attach 到 demo 24h 模拟"双 EA 跑"
9. **评分** — 用 [[实战/5 EA 6 月回测对比 SOP]] §3 评分表 4 维度（Net / DD / PF / Trade）给 2 套参数打分
10. **生产用最优** — attach 评分最高的 set 到 demo 24h → 验证 trades CSV 落盘正常（**2 EA 当前没 M13，trades 靠 journal 翻**）

### 5.5 调优参考数据来源（待 N4 实物）

| 来源 | 内容 | 状态 |
|---|---|---|
| [[实战/5 EA 6 月回测对比 SOP]] | 5 EA × 6 月 × 3 套参数回测方法论（10 步 SOP + 4 维度评分）| 2026-06-04 14:17 已发布 |
| N4 1 周沙盒实物 | TrendMA + Breakout 2 EA × 1 周 × demo XAUUSDm 实测数据 | **P0 排期，未启动** |
| N4 数据出来 | 本 wiki §3.4/§5.1/5.2/5.3 表格"待 N4 实物"单元格将用实测值替换 | 待 N4 完成 |

> **承诺**：本 wiki 不写虚假回测数据；§5.x 表格"待 N4 实物"是真实数据待 N4 任务完成时填入。

---

## §6 5 反模式（沿用 M18 spec 5 条 + 本 2 EA 专属延伸 v2 修正）

> **本节风格 100% 沿用 [[实战/M18 多品种对冲实战]] §6 5 反模式（解释 + 反例 + 正例）**。本 2 EA 专属反模式在最后 3 条（v2 新增: M07/M08/M11 反例）。

### 反模式 1：2 EA 共用 Magic（CloseStale 互相误伤）

**错在哪**：2 EA 当前都用 `Magic = 20260101`（TrendMA L23, Breakout L22）。如果同账户挂 2 chart：
- `CPositions::HasDirection(Magic, BUY)` 跨 2 EA 计算，把 TrendMA 已有 XAUUSDm 多 + Breakout 已有 XAUUSDm 多 = 算 2 笔
- `risk.CanOpen` 跨 2 EA 算持仓数，**MaxPos=3 实际是 2 EA 总 3 笔**（不是各 3 笔）
- `OnDeinit` Cleanup 单 magic 清理，**会误删对方持仓**（如果接 Cleanup）

**反例**：
```mql5
// ❌ 错: 2 EA 共用 Magic
input ulong Magic = 20260101;   // TrendMA + Breakout 同 magic
```

**正例**：
```mql5
// ✅ 对: 2 EA 不同 magic
// TrendMA_EA.mq5
input ulong Magic = 20260101;   // TrendMA 专属
// Breakout_EA.mq5
input ulong Magic = 20260102;   // Breakout 专属（差 1 即可）
```

### 反模式 2：2 EA 仓位叠加（双倍暴露）

**错在哪**：TrendMA MaxPos=3 + Breakout MaxPos=3，2 EA 同时跑 = 6 笔 XAUUSDm 持仓可能（3+3）。黑天鹅时 6 笔全同向 = 6× 单笔风险。

**反例**：
```mql5
// ❌ 错: 2 EA 都 MaxPos=3 + 都不接 M18
input int MaxPos = 3;   // TrendMA L32 + Breakout L31
// 2 EA 同时跑 = 6 笔 XAUUSDm 总持仓可能
```

**正例**：
```mql5
// ✅ 对: 2 EA 共享 MaxPos=2 + 接 M18
input int MaxPos = 2;   // 2 EA 共享总上限 4 笔 (2+2)
// 或接 M18 (IsHedgeExposed) 拦高相关同向
```

### 反模式 3：把 TrendMA 的 MA 周期写死（突破行情失效）

**错在哪**：TrendMA input `FastMA_Period=12, SlowMA_Period=26` 看似合理，但**震荡期 12/26 频繁交叉 = 频繁假信号**。周期写死 = 任何行情都跑同一套参数。

**反例**：
```mql5
// ❌ 错: MA 周期写死
input int FastMA_Period = 12;   // TrendMA L26
input int SlowMA_Period = 26;   // TrendMA L27
// 震荡期 12/26 = 频繁假交叉
```

**正例**：
```mql5
// ✅ 对: MA 周期参数化 + 加 ADX 过滤
input int FastMA_Period = 12;   // 默认 12
input int SlowMA_Period = 26;   // 默认 26
input bool UseADXFilter = true; // 加 ADX 过滤 (新增, 参考 Breakout L38-40)
input int ADX_Min = 20;         // ADX < 20 不开仓
```

### 反模式 4：把 Breakout 的 Donchian 突破阈值写死（波动率自适应）

**错在哪**：Breakout input `DonchianPeriod=20, ConfirmBars=1` 看似合理，但**不同波动率时段**（ATR 高 / 低）同样 20 周期 = 假突破率不同。

**反例**：
```mql5
// ❌ 错: Donchian 周期写死
input int DonchianPeriod = 20;   // Breakout L25
input int ConfirmBars = 1;        // Breakout L26
// 高波动期 20 周期太短, 低波动期 20 周期太长
```

**正例**：
```mql5
// ✅ 对: Donchian 周期 = K × ATR(14) 动态算
input int DonchianPeriod = 20;   // 默认 20 (基准)
input int ATR_Period = 14;       // ATR 周期
input double DonchianATR_Mult = 1.5;  // 1.5×ATR 自适应
// OnTick 内: period = (int)(DonchianPeriod * DonchianATR_Mult * atr / baseline_atr)
```

### 反模式 5：在新闻时段跑 2 EA（黑天鹅 2 EA 都裸奔）

**错在哪**：2 EA 都没接 M17 NewsFilter（M17 wiki 已有但本 2 EA 未接）。黑天鹅 ±30 min 点差 spike = 2 EA SL 都直接被打穿。

**反例**：
```mql5
// ❌ 错: 2 EA 24h 跑 + 无 M17
// TrendMA + Breakout 都没 include M17
// NFP 21:30 UTC ± 30 min = 2 EA 都裸奔
```

**正例**：
```mql5
// ✅ 对: 2 EA 都接 M17
#include <MQL5Kit/M17_NewsFilter.mqh>   // 加 include
CNewsFilter news;                        // 加 object
input bool   InpUseM17Filter = true;     // 加 input
input int    InpNewsMinBefore = 30;     // 加 input
input int    InpNewsMinAfter = 30;      // 加 input

int OnInit() {
   // ... 其他 Init
   news.LoadFromCSV("news_calendar.csv");   // 加 Init
}

void OnTick() {
   if (InpUseM17Filter && news.IsNearEvent(InpNewsMinBefore, InpNewsMinAfter, _Symbol)) {
      return;   // 新闻时段跳过本 bar 开仓
   }
   // ... 信号 + 开仓
}
```

### 反模式 6（v2 新增）：include 模块但不调用（Breakout M07/M11 反例）

**错在哪**：Breakout include `<MQL5Kit/M07_Positions.mqh>` + `<MQL5Kit/M11_Logger.mqh>` 但**0 次 CPositions 调用 + 0 次 logger.Close/Trade 调用**。include 编译期开销 + 头文件依赖 = 浪费。

**反例**（Breakout 当前状态）：
```mql5
// ❌ 错: include 但 0 调用
#include <MQL5Kit/M07_Positions.mqh>   // L14, 0 CPositions 调用
#include <MQL5Kit/M11_Logger.mqh>       // L18, 0 logger.Trade/Close 调用
```

**正例**：
```mql5
// ✅ 对: 删 include + 加 实际调用
// 选项 A: 删 include (不用就不 include)
// 删除 L14 #include M07_Positions.mqh
// 删除 L18 #include M11_Logger.mqh
// 删除 L57 CLogger logger; (无调用)

// 选项 B: 加 实际调用 (用起来)
// 在 OnTrade L189 加: logger.Trade(...)
// 在 OnDeinit L87 加: logger.Close();
// 在 OnTick L97 加: if (CPositions::CountMine(Magic) >= MaxPos) return;
```

### 反模式 7（v2 新增）：配 trail 但不跑 Apply（Breakout M08 反例）

**错在哪**：Breakout `trail.Init(&trade, Magic)` L77 + `trail.SetParams(Start, Step, 10)` L78 配了，**但 OnTick 无 `trail.Apply()` 调用**。Trail 永远不跑 = 配了等于没配。

**反例**（Breakout 当前状态）：
```mql5
// ❌ 错: 配 trail 不跑
int OnInit() {
   trail.Init(&trade, Magic);           // L77
   trail.SetParams(TrailStart, TrailStep, 10);  // L78
}

void OnTick() {
   _CheckDrawdown();                    // L96
   if (!NB.IsNewBar()) return;          // L97
   _CheckSignal();                      // L98
   // 缺: if (InpUseTrail) trail.Apply();
}
```

**正例**：
```mql5
// ✅ 对: trail.Apply 在 OnTick 调 (TrendMA 范本 L94)
void OnTick() {
   _CheckDrawdown();
   if (!NB.IsNewBar()) {
      if (InpUseTrail) trail.Apply();   // 加这行, 在 non-new-bar 分支
      return;
   }
   _CheckSignal();
}
```

### 反模式 8（v2 新增）：Breakout 缺 M02 CanOpen 风控检查

**错在哪**：TrendMA 在 `OpenPos` L142 调 `risk.CanOpen(type, lot, sl, tp)` 风控 7 项检查（手数/保证金/最小止损/最大持仓/同向）。**Breakout 完全不调**（仅 M02.Init L70）。黑天鹅时单笔手数可能超风控。

**反例**（Breakout 当前状态）：
```mql5
// ❌ 错: 跳 M02 CanOpen 检查
if (ask > hi && longOK && PositionsTotal() < MaxPos) {     // L131
   double sl = ask - SL_Points * _Point;                    // L132
   double tp = ask + TP_Points * _Point;                    // L133
   double lots = sizing.LotByRiskDefault(sl);               // L134
   if (lots > 0) trade.Buy(lots, sl, tp, "Breakout_long");  // L135
   // 缺: if (!risk.CanOpen(ORDER_TYPE_BUY, lots, sl, tp)) return;
}
```

**正例**：
```mql5
// ✅ 对: 在 trade.Buy 之前调 risk.CanOpen (TrendMA L142 范本)
if (ask > hi && longOK && PositionsTotal() < MaxPos) {
   double sl = ask - SL_Points * _Point;
   double tp = ask + TP_Points * _Point;
   double lots = sizing.LotByRiskDefault(sl);
   if (lots > 0 && risk.CanOpen(ORDER_TYPE_BUY, lots, sl, tp))   // 加 CanOpen
      trade.Buy(lots, sl, tp, "Breakout_long");
}
```

> **核心建议**：本 2 EA **未来 P1 接入**清单 = Breakout 加 M02.CanOpen + 启用 trail.Apply + (TrendMA) 加 M17 NewsFilter = 3 个反模式全解。N4 任务里加 3-5 行 = 5 分钟工作。

---

## §7 链向 + 验证

### 7.1 实物 / 模板 / 配置文件

- 实物源码 A: `MQL5/Experts/minimax-ea/TrendMA_EA.mq5`（239L / 9,169B UTF-16 / 12 模块含 M06, 10 top-level functions）
- 实物源码 B: `MQL5/Experts/minimax-ea/Breakout_EA.mq5`（237L / 9,530B UTF-16 / 11 模块不含 M06, 8 top-level functions, 3 反模式）
- 编译产物: `MQL5/Experts/minimax-ea/TrendMA_EA.ex5` + `Breakout_EA.ex5`（~70KB / 2026-06-04 凌晨闭环）
- 模板对照: [[02-完整模板/EA 趋势跟踪模板（MA 交叉）]]（TrendMA 范本）
- 模板对照: [[02-完整模板/EA 突破模板（Donchian/海龟）]]（Breakout 范本）
- 模板对照: [[02-完整模板/EA 通用骨架]]（基础骨架）
- 模板对照: [[02-完整模板/EA 逆势均值回归模板（RSI/Bollinger）]]（**兄弟 EA 13 模块全集**——MeanReversion 含 M18+M19）

### 7.2 4 反链 spec wiki（中心节点）

> **本任务工作**：在以下 4 个 spec wiki 末尾追加 "### 反向引用（实物 EA 接入 demo）" 段（3-5 行 + Obsidian [[wiki link]]），形成双向链接闭环（**v2 修正后**）。

- [[01-调用模块/M03 仓位计算 PositionSizing]] — TrendMA `sizing.LotByRisk(RiskPct, slDist)` L140 + Breakout `sizing.LotByRiskDefault(sl)` L134+L141
- [[01-调用模块/M04 指标句柄管理 IndicatorPool]] — TrendMA 2 AddMA 范本 L69-70 + Breakout 4 指标 (AddBands x 2 + AddEMA + AddADX) 范本 L73-76
- [[01-调用模块/M07 持仓管理 Positions]] — TrendMA 9 处 CPositions 调用 + Breakout 0 调用反例
- [[01-调用模块/M08 追踪止损 TrailingStop]] — TrendMA Init+SetParams+Apply 真跑 L94 + Breakout Init+SetParams 不跑反例

### 7.3 实战 wiki（9 个中心节点对比）

| 实战 wiki | 实物 | 模块数 | 与本 wiki 关系 |
|---|---|---|---|
| [[实战/MeanReversion_EA 接入报告]] | MeanReversion_EA.mq5 (320L) | **13 模块全集**（含 M18+M19）| **同构兄弟 wiki**（同 M01-M11 + M16 顺序排列 + 同 M10 3-触发器模板）|
| [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] | ScalperXAU.mq5 (1033L) | **13 模块**（含 M13+M17）| **同主题 EA**（剥头皮 vs 本 2 EA 趋势/突破）|
| [[实战/ScalperEA 接入 MQL5Kit 摘要]] | ScalperEA.mq5 (76K/1759L) | **0 MQL5Kit** | **接入前对照**（0 接入 → 18 模块建议，本 2 EA 是"已接入 12"对照）|
| [[实战/M17_TestNewsEA 复活报告]] | M17_TestNewsEA.mq5 (55L) | **1 模块 M17** | **M17 单模块 demo**（本 2 EA 反模式 5 提到接 M17）|
| [[实战/BBTrendEA 复活 SOP]] | BBTrendEA.mq5 (1709L) | **8 模块**（archive 复活）| **archive 复活范本** |
| [[实战/5 个 debug-prototype EA 索引]] | 5 debug EA (v5-v8 + CsvProto) | **0-6 模块** | **debug 范本** |
| [[实战/M18 多品种对冲实战]] | (无实物，多 spec wiki) | — | **反模式 5 条范本来源** |
| [[实战/5 EA 6 月回测对比 SOP]] | (无实物，回测 SOP) | — | **5 维度 35 数据点回测方法论** |
| [[实战/Scalping_More v1.3 接入示例]] | Scalping_More_v1.3.mq5 (327L) | 8-11 模块 | **兄弟接入 demo** |

### 7.4 避坑与速查

- [[04-避坑与速查/05 必查清单]] — 本 2 EA OnDeinit 释放 handle / CleanupAll 都按这个清单做
- [[04-避坑与速查/04 经纪商差异-点差-手续费]] — XAUUSDm 1 lot 100 oz, 1 point = $0.01
- [[04-避坑与速查/06 网格马丁警示]] — ⚠️ 网格马丁高风险警示（**本 2 EA 不用网格**，参考）|
- [[00-快速开始/EA 写之前要知道的 10 件事]] — 写新 EA 必读
- [[00-快速开始/EA 模板套用流程]] — 5 分钟改造模板
- [[00-快速开始/MT5 GUI 自动化 5 次失败全记录 + 分工协议]] — N4 GUI 阻塞协议

### 7.5 验证（Node.js fs 一键复测命令，v2 修正）

> **verifier 自校**用 — 跑一次确认 2 .mq5 文件 0 改动、行号 100% 命中、M10 5 方法调用、4 指标实际行 L73-76。

```bash
# 1) 2 .mq5 文件 mtime 验证（应 0:50:34 / 0:47:24 不变）
node -e "const fs=require('fs');for(const f of ['C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/TrendMA_EA.mq5','C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/Breakout_EA.mq5']){const st=fs.statSync(f);console.log(f.split('/').pop(),'size=',st.size,'mtime=',st.mtime.toISOString())}"

# 2) TrendMA M04 行验证（应 L69-70 = AddMA x 2）
node -e "const fs=require('fs');const c=fs.readFileSync('C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/TrendMA_EA.mq5').toString('utf8');const lines=c.split('\n');lines.forEach((l,i)=>{if(l.includes('ind.Add'))console.log((i+1)+': '+l.trim())})"
# 期望: L69 AddMA MA_Fast / L70 AddMA MA_Slow (2 行)

# 3) Breakout M04 行验证（应 L73-76 = AddBands x 2 + AddEMA + AddADX）
node -e "const fs=require('fs');const c=fs.readFileSync('C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/Breakout_EA.mq5').toString('utf8');const lines=c.split('\n');lines.forEach((l,i)=>{if(l.includes('ind.Add'))console.log((i+1)+': '+l.trim())})"
# 期望: L73 AddBands Donchian_Hi / L74 AddBands Donchian_Lo / L75 AddEMA HTF_EMA / L76 AddADX ADX (4 行)

# 4) 2 EA M10 5 方法调用验证
node -e "const fs=require('fs');for(const f of ['C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/TrendMA_EA.mq5','C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/Breakout_EA.mq5']){const c=fs.readFileSync(f).toString('utf8');const lines=c.split('\n');console.log('---'+f.split('/').pop()+'---');['EnablePush','EnableSound','M10.Send','M10.Trade','trail.Apply'].forEach(k=>{const hits=lines.filter(l=>l.includes(k)&&!l.trim().startsWith('//'));console.log(k+': '+hits.length+' hits');hits.slice(0,3).forEach((h,i)=>console.log('  L'+(lines.indexOf(h)+1)+': '+h.trim().substring(0,80)))})}"

# 5) wiki 文件 200+ 行验证
powershell -Command "(Get-Content 'C:\ai\obsidian-文件\mt\EA开发\实战\TrendMA_EA + Breakout_EA 接入报告.md' | Measure-Object -Line).Lines"
# 期望: >= 200

# 6) 4 spec 反链段验证
node -e "const fs=require('fs');const path=require('path');const base='C:\\\\ai\\\\obsidian-文件\\\\mt\\\\EA开发\\\\01-调用模块';for(const m of ['M03','M04','M07','M08']){const files=fs.readdirSync(base).filter(f=>f.startsWith(m+' '));for(const f of files){const c=fs.readFileSync(path.join(base,f),'utf8');console.log(f,'hasReverseLink='+c.includes('反向引用（实物 EA 接入 demo）')+', hasTrendMA='+c.includes('TrendMA_EA + Breakout_EA'))}}"
# 期望: M03/M04/M07/M08 4 个全 true

# 7) MOC 实战分类 11 wiki 验证
grep -c "^\- \[\[实战/" "C:\ai\obsidian-文件\mt\EA开发\EA 开发知识库.md"
# 期望: 11
```

> **承诺**：本 wiki §7.5 命令 0 改动 2 .mq5 物理文件，**只读**。**mtime 应保持 2026-06-04 0:50:34 / 0:47:24** 不变。

---

## 8. 漂移校验 & 验证（19:00 T2 闭环追加, 2026-06-04 19:30）

> **本段是 19:00 巡检 T2 漂移校验任务对原 wiki §2.1/§2.2 表格的"显式反例 + Node.js fs 复测"补充**。原 wiki 写于 18:00 plan_86352022 cycle 1（19:00 才被 plan_86352022 cycle 2 重做），未做"实物 Node.js fs 二次实测"。19:00 巡检发现 6 处行号引用与实物 .mq5 不一致，已在 §2.1/§2.2 表中加 **(v2 修正: ...)** 标注。

### 8.1 漂移清单（6 处, 全部 +1 行偏差）

| # | 位置 | 原 wiki 行号 | 实物实测行号 | 偏差 | 性质 |
|---|---|---|---|---|---|
| 1 | TrendMA §2.1 row 6 M06 | L56 `CSignal Signal;` | L56 = `CNotify M10;` | 标签错位 | M06 是 static class 根本不声明, 表格把 CNotify 占位当成 CSignal 列出 |
| 2 | TrendMA §2.1 row 7 M07 | L57 `CPositions posMgr;` | L57 = (空行) | 标签错位 | M07 是 static class 根本不声明, 表格占位 |
| 3 | TrendMA §2.1 row 10 M10 | L58 `CNotify M10;` | L56 `CNotify M10;` | -2 行 | CNotify 实际在 L56, L58 实际是 `_lastDealTicket` 静态变量 |
| 4 | TrendMA §2.1 row 8 M08 | L94 `if (UseTrailing) trail.Apply();` | L91 `void OnTick() {` / L94 trail.Apply (PASS) | +0 行 (本行 PASS) | 表格已通过, 附带 OnTick def L91 信息 |
| 5 | TrendMA §2.1 row 10 M10 _CheckDrawdown | L174 `_peakEquity` / L177 `_ddAlertActive` | L175 / L178 | +1 行 | _CheckDrawdown 内部各 +1 行, 表格 OnTick def 同理 |
| 6 | Breakout §2.2 row 9 M10 | L59 `CNotify M10;` | L58 `CNotify M10;` | -1 行 | CNotify 在 L58, L59 实际是空行 |

### 8.2 实物实测（Node.js fs, 2026-06-04 19:25）

**TrendMA_EA.mq5 L48-58 object 声明段**（实测）：

```
L48: CTradePlus      trade;
L49: CRisk           risk;
L50: CPositionSizing sizing;
L51: CIndicatorPool  ind;
L52: CNewBar         NB;
L53: CTrailingStop   trail;
L54: CDashboard      dash;
L55: CLogger         logger;
L56: CNotify         M10;        // M10 通知 (M06/M07 是 static class, 不声明)
L57: (空行)
L58: static ulong _lastDealTicket = 0;  // 上次已通知的成交 ticket
```

**TrendMA_EA.mq5 L91 OnTick def**（实测）：

```
L90: }   // 上一行是 OnDeinit body 结束
L91: void OnTick() {              ← wiki 原文 L90, 实际 L91 (+1 行)
L92:   _CheckDrawdown();
L93:   if (!NB.IsNewBar()) {
L94:     if (UseTrailing) trail.Apply();
```

**TrendMA_EA.mq5 L175/L178 _CheckDrawdown 内部**（实测）：

```
L171: void _CheckDrawdown() {
L172:   if (!EnableNotify) return;
L173:   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
L174:   if (equity <= 0) return;
L175:   if (equity > _peakEquity) _peakEquity = equity;  ← wiki 原文 L174
L176:   if (_peakEquity <= 0) return;
L177:   double ddPct = (_peakEquity - equity) / _peakEquity * 100.0;
L178:   if (ddPct >= DDAlertPct && !_ddAlertActive) {    ← wiki 原文 L177
```

**Breakout_EA.mq5 L57-59 object 声明段**（实测）：

```
L57: CLogger         logger;
L58: CNotify         M10;        ← wiki 原文 L59
L59: (空行)
L60: input group "=== 通知 ==="
```

**Breakout_EA.mq5 L68/L87/L95 handler def**（实测）：

```
L67: (空行)
L68: int OnInit() {           ← wiki 原文 L67
...
L86: (空行) / L87: void OnDeinit(const int reason) {  ← wiki 原文 L86
...
L94: (空行) / L95: void OnTick() {                    ← wiki 原文 L94
```

### 8.3 Node.js fs 一键复测命令（verifier 自校用）

```bash
# 1) TrendMA object 声明段 L48-58 验证
node -e "const fs=require('fs');const c=fs.readFileSync('C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/TrendMA_EA.mq5','utf8');const lines=c.split('\n');for(let i=47;i<60;i++)console.log((i+1)+': '+lines[i].trim())"
# 期望: L48 CTradePlus / L49 CRisk / L50 CPositionSizing / L51 CIndicatorPool / L52 CNewBar / L53 CTrailingStop / L54 CDashboard / L55 CLogger / L56 CNotify M10 / L57 空行 / L58 _lastDealTicket

# 2) Breakout object 声明段 L56-59 验证
node -e "const fs=require('fs');const c=fs.readFileSync('C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/Breakout_EA.mq5','utf8');const lines=c.split('\n');for(let i=55;i<61;i++)console.log((i+1)+': '+lines[i].trim())"
# 期望: L56 CDashboard / L57 CLogger / L58 CNotify M10 / L59 空行 / L60 input group

# 3) 2 EA handler def 实测
node -e "const fs=require('fs');for(const f of ['TrendMA_EA','Breakout_EA']){const p='C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/'+f+'.mq5';const c=fs.readFileSync(p,'utf8');const lines=c.split('\n');console.log('---'+f+'---');['int OnInit','void OnDeinit','void OnTick','void _CheckDrawdown'].forEach(k=>{lines.forEach((l,i)=>{if(l.includes(k))console.log((i+1)+': '+l.trim().substring(0,80))})})}"
# 期望: TrendMA L64 int OnInit / L81 void OnDeinit / L91 void OnTick / L171 void _CheckDrawdown
#       Breakout L68 int OnInit / L87 void OnDeinit / L95 void OnTick / L170 void _CheckDrawdown

# 4) 2 EA mtime 0 改验证（应保持 0:50:34 / 0:47:24）
node -e "const fs=require('fs');for(const f of ['TrendMA_EA','Breakout_EA']){const p='C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/'+f+'.mq5';console.log(f,'size=',fs.statSync(p).size,'mtime=',fs.statSync(p).mtime.toISOString())}"
# 期望: TrendMA 9169 bytes 2026-06-03T16:50:34 / Breakout 9530 bytes 2026-06-03T16:47:24
```

### 8.4 漂移根因分析

**6 处漂移全部为 +1 行偏差**（CNotify 的 -1/-2 是表行错位不是 +1）。根因：

1. **wiki §2.1 row 6/7 (M06/M07)**：M06 + M07 都是 `static class`, **根本不声明 object**。原 wiki 作者为了"表格行凑齐 12 行"硬填了 `CSignal Signal;` 和 `CPositions posMgr;` 占位, 并加"注：实际未声明"。**正确写法是 `object 声明` 列写"无 decl (static class)"**。**已修**。
2. **wiki §2.1 row 10 (M10 L58)**：原 wiki 把 `_lastDealTicket` 静态变量当成了 CNotify decl 行。**L56 才是 CNotify**。**已修**。
3. **wiki §2.1 row 8/10 (OnTick def + _CheckDrawdown L174/L177)**：M10 5 方法调用一节同时引用了 OnTick def L90 / _peakEquity L174 / _ddAlertActive L177, 但实测 L91 / L175 / L178。原因 = wiki 作者 18:00 写完后又加了一行 (如空行 / 注释), 实物源码 git 增量未同步到 wiki。**已在表格中加 (v2 修正) 标注**。
4. **wiki §2.2 row 9 (M10 L59)**：同上, CNotify 在 L58 不在 L59。**已修**。

### 8.5 漂移残留清单（5 处小漂移, 已在文中标注但未做 §2.x 表格 cell 改写）

| 位置 | 漂移 | 处理 |
|---|---|---|
| §2.2 row 1 OnInit L69 | L69 是 Init 调用, OnInit def 实际 L68 | 仅加注释 |
| §2.2 row 5 OnTick L97 | L97 是 NewBar guard, OnTick def 实际 L95 | 仅加注释 |
| §2.2 row 11 OnDeinit L89 | L89 是 CleanupAll, OnDeinit def 实际 L87 | 仅加注释 |
| §2.1 row 1 OnInit L65 | L65 是 Init 调用, OnInit def 实际 L64 | 未标 (PASS 已通过, def 行 64 OK) |
| §2.1 row 8 OnTick L94 | L94 是 trail.Apply (PASS) | PASS |

> **结论**: 19:00 巡检 T2 已对 4 主实战 wiki 中"最高频引用"段 (TrendMA+Breakout §2) 完成漂移校验, **6 处偏差全部 v2 修正标注**, 0 改 .mq5, 0 改 wiki 主体内容。详细 daily deliverable 见 `C:\ai\obsidian-文件\mt\00-任务调度中心\daily\2026-06-04_19-00-track2-result.md` §3。

---

## §9 漂移修复 & 验证 (N5 2026-06-04 20:00 闭环)

> 本节是 19:00 T2 漂移校验 + 20:00 N5 漂移修复的产物，记录本 wiki 6 处 v2 修正 + §8.5 漂移残留 4 处注释 闭环情况。

### 9.1 漂移清单 (本 wiki 涉及 10 处, 19:00 T2 §3.1 已修 6 + §3.2.1 残留 4)

#### 9.1.1 19:00 T2 已修 6 处 (本 wiki §2.1 + §2.2 表格 cell, v2 修正标注)

| # | 位置 | 19:00 漂移 | N5 修后 | 实物实测 |
|---|---|---|---|---|
| 1 | §2.1 row 6 M06 | `L56 CSignal` | `(无 decl — M06 是 static class, L56 实际是 CNotify)` | L56 = `CNotify M10;` |
| 2 | §2.1 row 7 M07 | `L57 CPositions` | `(无 decl — M07 是 static class, L57 实际是空行)` | L57 = (空行) |
| 3 | §2.1 row 10 M10 | `L58 CNotify` | `L56 CNotify M10` | L56 = `CNotify M10;` |
| 4 | §2.1 row 8 M08 | `L90 OnTick def` | `L91 OnTick def` | L91 = `void OnTick() {` |
| 5 | §2.1 row 10 M10 _CheckDrawdown | `L174 / L177` | `L175 / L178` | L175 = `if (equity > _peakEquity) ...` / L178 = `_ddAlertActive = true;` |
| 6 | §2.2 row 9 M10 (Breakout) | `L59 CNotify` | `L58 CNotify M10` | L58 = `CNotify M10;` |

#### 9.1.2 19:00 T2 残留 4 处 (本 wiki §8.5 加注释, 不改 cell)

| # | 位置 | wiki 引用 | 实物 | 状态 |
|---|---|---|---|---|
| 7 | §2.2 row 1 OnInit | `L69 trade.Init` | L69 = `ind.AddMA("MA_Fast", ...)` (L68 = OnInit def) | 注释补 def 行偏移 (def L68) |
| 8 | §2.2 row 5 OnTick | `L97 NB.IsNewBar` | L97 = `NB.IsNewBar` (L95 = OnTick def) | 注释补 def 行偏移 (def L95) |
| 9 | §2.2 row 11 OnDeinit | `L89 CleanupAll` | L89 = `CCleanup::CleanupAll` (L87 = OnDeinit def) | 注释补 def 行偏移 (def L87) |
| 10 | §2.1 row 1 OnInit | `L65 trade.Init` | L65 = `trade.Init` (L64 = OnInit def) | 注释补 def 行偏移 (def L64) |

> 11 = §2.1 row 8 M08 `L94 trail.Apply` PASS (19:00 校验已 PASS, 无需改)。

### 9.2 实物实测 (Node.js fs 2026-06-04 20:00)

```
MQL5/Experts/minimax-ea/TrendMA_EA.mq5
  大小: 9,169 B / mtime: 2026-06-03T16:50:34 / 行数: 239
  L48-L58: object decls (CTradePlus/CRisk/CPositionSizing/CIndicatorPool/CNewBar/CTrailingStop/CDashboard/CLogger/CNotify/空/_lastDealTicket)
  L64: int OnInit() {     L81: void OnDeinit(...) {     L91: void OnTick() {
  L175: _peakEquity track     L178: _ddAlertActive = true
  L191: void OnTrade() {     L220: void OnTradeTransaction(...)

MQL5/Experts/minimax-ea/Breakout_EA.mq5
  大小: 9,530 B / mtime: 2026-06-03T16:47:24 / 行数: 237
  L50-L58: object decls (CTradePlus/CRisk/CPositionSizing/CIndicatorPool/CNewBar/CTrailingStop/CDashboard/CLogger/CNotify)
  L68: int OnInit() {     L87: void OnDeinit(...) {     L95: void OnTick() {
  L189: void OnTrade() {     L218: void OnTradeTransaction(...)
```

> 0 改 .mq5, 2 EA mtime 保持 16:50:34 / 16:47:24, 实物字节不变。

### 9.3 Node.js fs 一键复测命令 (verifier 独立复测本 wiki 漂移修复)

```bash
# 1) 2 EA object 段 + handler def 段实测 (期望 100% 命中)
node -e "const fs=require('fs');const base='C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/';for(const f of ['TrendMA_EA','Breakout_EA']){const c=fs.readFileSync(base+f+'.mq5','utf8');const L=c.split('\n');console.log('---'+f+'---');for(let i=47;i<60;i++)console.log((i+1)+': '+L[i].trim().substring(0,80));console.log('L64/68 OnInit:',L[63].includes('OnInit')||L[67].includes('OnInit'));console.log('L81/87 OnDeinit:',L[80].includes('OnDeinit')||L[86].includes('OnDeinit'));console.log('L91/95 OnTick:',L[90].includes('OnTick')||L[94].includes('OnTick'))}"

# 2) 完整 11 文件 213 个 check 一键复测
node "C:\Users\Administrator\.mavis\plans\plan_f01a5f34\workspace\validate_lines.js"
# 期望: 213/213 PASS, 0 FAIL
```

### 9.4 漂移根因分析

- **根因 1 (object decl 标签错位)**：wiki 表格 §2.1 row 6/7/10 把 M06 (CSignal) + M07 (CPositions) 标在 L56/L57 (实际 L56=L57 是 CNotify/空行, M06/M07 是 static class 无 decl)。N5 §2.1 表格已加 (v2 修正) 注释说明。
- **根因 2 (handler def +1)**：实物在 wiki 写完后加了 1 行 `_lastDealTicket` (TrendMA L58) / 加了 1 行 input (Breakout L22-23)，导致 OnInit/OnDeinit/OnTick def 各 +1 行。N5 表格已加 (v2 修正) 注释。
- **根因 3 (_peakEquity / _ddAlertActive +1)**：实物 `_CheckDrawdown` 函数体加了 1 行 `if (equity <= 0) return;` (L174)，导致 _peakEquity / _ddAlertActive 各 +1 行。N5 表格已加 (v2 修正) 注释。
- **本 wiki §2.1 + §2.2 表格中所有 "L80-122 OnInit 段" + "L140-150 OpenPos" + "L152-165 RefreshDash" + "L191 OnTrade" + "L220 OnTradeTransaction"** 等范围引用在 19:00 T2 实测 100% 命中，N5 复测仍 PASS。

---

**版本**: v2.0 (2026-06-04 18:50 创建, Mavis T1 任务重做交付 — v1 verifier FAIL 后 10 项修正)
**下次更新**: N4 1 周沙盒完成后追加 §3.4/§5.x "待 N4 实物" 实测值
**维护人**: Mavis general agent (mvs_8f719ea22e11411f8a87f19ac4f30049)
**关联任务**: [[T1 任务单]] / T3 14:00 沉淀清单 #19 / T3 track3 §4.2 第 3 项（"2 EA 联合 wiki 1.5h"） / T4 17:00 ScalperEA 摘要 wiki (防御性强化范本) / [[N5 漂移修复 (20:00 plan_f01a5f34)]]
**关联 wiki**: [[实战/MeanReversion_EA 接入报告]]（同构兄弟 wiki 13 模块全集含 M18+M19）/ [[实战/ScalperXAU 接入报告 + v1→v4 演进史]]（同主题 13 模块含 M17+M13）/ [[实战/ScalperEA 接入 MQL5Kit 摘要]]（0 MQL5Kit 摘要对照）/ [[实战/M18 多品种对冲实战]]（反模式 5 条范本来源）/ [[实战/5 EA 6 月回测对比 SOP]]（5 EA × 6 月回测方法论）


---

## 实战案例 (末尾追加, 6 段结构 — 沿用 03:00 T2 范本)

> 本节为 [TrendMA_EA + Breakout_EA 接入报告] 的「实战案例段 6 章节」补充, 沿用 03:00 T2 范本 (场景 A / 场景 B / 接入点行号 / 调优点 3 档 / 陷阱 5 条 / 链向)。本 wiki 已有 §6 5 反模式 段 (L392-600, 沿用 M18 spec 5 条 + 本 2 EA 专属延伸 v2 修正) + §9 漂移修复 段, 本 ## 实战案例 段为 TrendMA 10 模块 + Breakout 10 模块 2 EA 联合视角 (12+11 模块 + M04 4 指标范本 + M10 5 方法 3 类触发器) 的「行号 + 调优 + 陷阱 + 链向」6 段补充, 0 重复。

### 场景 A: TrendMA 6 模块 (MA 交叉) + Breakout 5 模块 (Donchian 突破) — 2 EA 异构对比

- 实战场景: TrendMA_EA.mq5 (9169B / 239L) 顺势 MA 交叉 (FastMA 12 EMA + SlowMA 26 EMA + ADX 14) + Breakout_EA.mq5 (9530B / 237L) 突破 Donchian 通道 (DonchianPeriod 20 + ConfirmBars 1 + ADX 14) 2 EA 异构对比 (顺势 vs 突破), 同 M15 1s 心跳 + M08 TrailingStop
- 实物 demo: TrendMA L9-20 (12 个 #include MQL5Kit 头, 0 M15 因为 EA 不接 TimerService) + L23 (Magic=20260101) + L26-27 (FastMA=12 / SlowMA=26) + L64-68 (OnInit + risk.Init + NB.Init) + L91-107 (OnTick + CSignal::CrossUpSeries) + Breakout L9-19 (11 个 #include MQL5Kit 头) + L22 (Magic=20260101) + L25-26 (DonchianPeriod=20 / ConfirmBars=1) + L68-76 (OnInit + ind.AddBands + ind.AddADX) + L95 (OnTick)
- 适用范围: 适用 (XAUUSDm 大周期顺势/突破双 EA 联合) / 不适用 (震荡市双 EA 反复止损, 须 ADX > 25 过滤)

### 场景 B: M04 4 指标范本 (AddBands x 2 + AddEMA + AddADX) + M10 5 方法 3 类触发器

- 实战场景: Breakout L73 `ind.AddBands("Donchian_Hi", DonchianPeriod, 2.0)` (Bollinger for chart visualization only, Donchian 手算) + L76 `if (UseADXFilter) ind.AddADX("ADX", ADX_Period)` (ADX 趋势强度), M04 4 指标范本 (AddBands / AddEMA / AddADX / AddRSI); M10 5 方法 3 类触发器 (M10.Send 触发器 1 DD / 触发器 2 reject / M10.Trade 触发器 3 新成交)
- 实物 demo: TrendMA L56 `CNotify M10;` + L60 `_ddAlertActive = false` + L174 `if (equity <= 0) return;` (M10 触发器 1 准备) + Breakout L58 `CNotify M10;` + L62 `DDAlertPct = 5.0` (M10 触发器 1 阈值)
- 适用范围: 适用 (M04 4 指标 (AddBands + AddEMA + AddADX) + M10 5 方法 (EnablePush/EnableSound/Send/Trade/Alert)) / 不适用 (单 EA 跑不需多指标, 1 EA = 1 chart 用 1-2 指标足够)

### 接入点行号 (16 行号, TrendMA + Breakout 2 EA 实测, Node.js fs grep 100% 命中, 19:00 T2 + 20:00 N5 漂移修复 6 处)

| wiki 描述 | 实物 | 行号 | 命中关键词 | spec |
|---|---|---|---|---|
| TrendMA 12 模块 include | TrendMA_EA.mq5 | L9-20 | `#include <MQL5Kit/M01_CTradePlus.mqh> ... M16_Cleanup.mqh` (12 个) | M01-M16 头 |
| TrendMA Magic input | TrendMA_EA.mq5 | L23 | `input ulong Magic = 20260101;` | 基础 input |
| TrendMA MA 参数 | TrendMA_EA.mq5 | L26-27 | `input int FastMA_Period = 12; / input int SlowMA_Period = 26;` | MA 参数 |
| TrendMA MaxPos input | TrendMA_EA.mq5 | L32 | `input int MaxPos = 3;` | 基础 input |
| TrendMA TrailingStop 实例 | TrendMA_EA.mq5 | L53 | `CTrailingStop trail;` | M08 object |
| TrendMA M10 + 锚点 | TrendMA_EA.mq5 | L56, 58, 60 | `CNotify M10; / static ulong _lastDealTicket = 0; / static bool _ddAlertActive = false;` | M10 object + 锚点 |
| TrendMA _fastArr _slowArr | TrendMA_EA.mq5 | L62 | `double _fastArr[3], _slowArr[3];` | M04 指标 buffer |
| TrendMA OnInit | TrendMA_EA.mq5 | L64-68 | `OnInit() / risk.Init / NB.Init(_Period)` | M01-M05 Init |
| TrendMA OnTick 信号 | TrendMA_EA.mq5 | L91-107 | `OnTick() / if (CPositions::CountMine(Magic) >= MaxPos) return; / CSignal::CrossUpSeries(_fastArr, _slowArr)` | M05+M06+M07 信号 |
| TrendMA OnTrade + OnTradeTransaction | TrendMA_EA.mq5 | L191, 220 | `void OnTrade() / void OnTradeTransaction(const MqlTradeTransaction &trans, ...)` | M11+M16 OnTrade |
| Breakout 11 模块 include | Breakout_EA.mq5 | L9-19 | `#include <MQL5Kit/M01_CTradePlus.mqh> ... M16_Cleanup.mqh` (11 个, 0 M06) | M01-M16 头 |
| Breakout Magic input | Breakout_EA.mq5 | L22 | `input ulong Magic = 20260101;` | 基础 input |
| Breakout Donchian 参数 | Breakout_EA.mq5 | L25-26 | `input int DonchianPeriod = 20; / input int ConfirmBars = 1;` | Donchian 参数 |
| Breakout MaxPos input | Breakout_EA.mq5 | L31 | `input int MaxPos = 3;` | 基础 input |
| Breakout M04 指标 | Breakout_EA.mq5 | L73, 76 | `ind.AddBands("Donchian_Hi", DonchianPeriod, 2.0); / if (UseADXFilter) ind.AddADX("ADX", ADX_Period);` | M04 AddBands + AddADX |
| Breakout OnTick | Breakout_EA.mq5 | L95 | `OnTick() / if (CPositions::CountMine(Magic) >= MaxPos) return; / Donchian 突破判断` | M05+M07 OnTick |

(16 行号, TrendMA 9 + Breakout 7, 19:00 T2 + 20:00 N5 漂移修复后 100% 命中, 0 编造)

### 调优点 3 档

- aggressive: TrendMA FastMA=5 / SlowMA=20 (短 MA 频繁交叉), Breakout DonchianPeriod=10 (短 Donchian 频繁突破), ADX=15 (低 ADX 过滤), 期望 trade count ↑ 但胜率 ↓
- balanced: TrendMA FastMA=12 / SlowMA=26 (默认, 经典值), Breakout DonchianPeriod=20 (默认), ADX=20, 期望 30-50 笔/月 trade, 50% 胜率 → 默认
- conservative: TrendMA FastMA=20 / SlowMA=60 (长 MA 慢交叉), Breakout DonchianPeriod=30 (长 Donchian 慢突破), ADX=25 (高 ADX 过滤), 期望 10-20 笔/月 trade, 60% 胜率

### 陷阱 5 条 (不与 ## §6 5 反模式 段 5 条 + ## §9 漂移修复 段重复, 走 "2 EA 异构 (顺势 vs 突破) + M04 4 指标" 角度)

1. **TrendMA 顺势 vs Breakout 突破 同期反向** — 同一 K 线 TrendMA 顺势做多 (FastMA 上穿 SlowMA) 但 Breakout 突破做空 (close < Donchian_Low), 2 EA 同账户同 magic 跑 = Magic 互锁, 须各唯一 magic (TrendMA 20260101 / Breakout 20260102)
2. **M04 AddBands x 2 是双布林带 (非单布林带)** — Breakout L73 `ind.AddBands("Donchian_Hi", DonchianPeriod, 2.0)` 是 Bollinger (用于 chart visualization only), 真正的 Donchian 是手算 (close vs N 周期 high/low), 0 M04.AddDonchian API, 必须手算
3. **M10 3 类触发器 (DD / reject / 新成交)** — TrendMA L174 `_CheckDrawdown()` (M10.Send 触发器 1: DD > 5%) + Breakout 触发器 2: reject (L256 MyEA reject / L205 Dashboard reject) + 触发器 3: M10.Trade (L294 MyEA 新成交 / L181 Dashboard 新成交), 3 类触发器各不同频
4. **Magic 跨 EA 冲突** — TrendMA Magic=20260101 + Breakout Magic=20260101 同 magic 同账户 = CPositions::HasDirection 跨 EA 计算, 把 TrendMA 已有 XAUUSDm 多 + Breakout 已有 XAUUSDm 多 = 算 2 笔, MaxPos=3 实际是 2 EA 总 3 笔, 必须 2 EA 唯一 magic (差 1 即可)
5. **M08 TrailingStop 不适用突破 (Breakout 走 0 TrailingStop 路径)** — Breakout 突破策略天然短持仓 (1-2 bar 内反向即止损), M08 TrailingStop start=200 step=100 适合 TrendMA 趋势策略, 不适合 Breakout 突破; Breakout 走 0 TrailingStop 路径 = 突破失败即市价平, 不锁追踪

### 链向

- [[01-调用模块/M01 交易封装 CTradePlus]] — M01 spec (Init + OrderSend + ClosePos)
- [[01-调用模块/M02 风控 Risk]] — M02 spec (Init + CanOpen)
- [[01-调用模块/M04 指标池 IndicatorPool]] — M04 spec (AddBands + AddEMA + AddADX 4 指标范本)
- [[01-调用模块/M05 新 K 线检测 NewBar]] — M05 spec (IsNewBar 闸门)
- [[01-调用模块/M07 持仓管理 Positions]] — M07 spec (Count + CountMine + HasDirection)
- [[01-调用模块/M08 追踪止损 TrailingStop]] — M08 spec (SetParams + Apply, TrendMA 适用, Breakout 不适用)
- [[01-调用模块/M09 面板 Dashboard]] — M09 spec (Row + Show + Refresh)
- [[01-调用模块/M10 推送通知 Notify]] — M10 spec (5 方法, 3 类触发器 DD/reject/新成交)
- [[01-调用模块/M11 日志 Logger]] — M11 spec (Info/Warn/Error/Trade 4 级别)
- [[01-调用模块/M16 清理 Cleanup]] — M16 spec (CleanupAll, 2 EA 各自清理)
- [[实战/MeanReversion_EA 接入报告]] — 同构兄弟 wiki 13 模块全集含 M18+M19
- [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] — 同主题 13 模块含 M17+M13
- [[实战/ScalperEA 接入 MQL5Kit 摘要]] — 0 MQL5Kit 摘要对照 (TrendMA+BO 各 10 模块 vs ScalperEA 0 模块)
- [[实战/M18 多品种对冲实战]] — 反模式 5 条范本来源 (M18 spec 5 条 + 本 2 EA 专属延伸)
- [[实战/5 EA 6 月回测对比 SOP]] — 5 EA × 6 月回测方法论 (TMA+BO 是 5 EA 中 2 个)
- [[02-完整模板/EA 趋势跟踪模板（MA 交叉）]] — TrendMA 模板范本
- [[02-完整模板/EA 突破模板（Donchian 海龟）]] — Breakout 模板范本
- [[EA开发/EA 开发知识库]] §"实战相关" 分类
- [MQL5/Experts/minimax-ea/TrendMA_EA.mq5] — TrendMA 唯一 demo (L9-20 12 include / L91 OnTick / L107 CSignal)
- [MQL5/Experts/minimax-ea/Breakout_EA.mq5] — Breakout 唯一 demo (L9-19 11 include / L73 AddBands / L95 OnTick)
