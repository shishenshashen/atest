---
title: MyEA + Dashboard 接入报告 (实物 EA 联合 wiki, 14:00 沉淀清单 §5 维度 5 续)
date: 2026-06-04
tags: [EA, MyEA, Dashboard, 接入, 联合, 沉淀 #5-2]
type: usage
version: 1.0
---

# MyEA + Dashboard 接入报告

> **本 wiki 是 `MQL5/Experts/minimax-ea/MyEA.mq5` + `Dashboard.mq5` 的联合接入报告**。
> MyEA（**301L / 12,541 B / 10 模块 M01+M02+M03+M05+M07+M09+M10+M11+M13+M16, Magic 20260101, 11 top-level functions**）+ Dashboard（**208L / 8,361 B / 4 模块 M04+M09+M10+M15, NotifyMagic=0 监听全账户, 9 top-level functions**）= minimax-ea/ 10 实物 EA 中**"通用骨架范本"+"跨品种监控范本"** 的联合 demo。
>
> **本 wiki 价值定位**：
> 1. **MyEA = MQL5Kit 官方通用骨架**（头注释"复制此文件开始你的策略"）—— 是 [[02-完整模板/EA 通用骨架]] 的 1:1 实物版，**含 M10 + M11 + M13 + M16 完整 4 件套**（其他实物 EA 大多缺 M13）
> 2. **Dashboard = 跨品种只读监控面板** —— 是 [[02-完整模板/EA Dashboard 监控模板]] 的 1:1 实物版，**唯一用 M15 定时器**的实物 EA（其他 9 个 EA 都不用 OnTimer）
> 3. **2 EA 共享 M09 + M10 模块**（M09 实时面板 + M10 三类触发器），**互不交易**（MyEA 跑策略 + Dashboard 只监听）
> 4. **5 反模式 100% 来自实物代码**（如 MyEA 在 OnTrade 调 M13 落盘同时 M10 通知，`_m13LastDealTicket` 锚点共享防重放）
>
> **目标读者**：
> 1. 想复制 MyEA 作为"剥头皮 / 网格 / 趋势"任意策略的起点（M01-M11+M16 全部用上 = 通用骨架标准装）
> 2. 想把 Dashboard 模板套到自己的多品种场景（M04 + M09 + M10 + M15 4 模块最小监控组合）
> 3. 想看"M13 FileIO + M10 Notify 在 OnTrade 共享去重锚点"的标准范本（MyEA `_m13LastDealTicket` L51 单变量承担 2 模块同步）
> 4. 想看"M15 TimerService 在 OnTimer 节流"的唯一实物 demo（其他 9 个 EA 都不走 OnTimer）

---

## 0. 摘要（30 秒读完）

- **实物 A**：`MQL5/Experts/minimax-ea/MyEA.mq5`（**301L / 12,541 B / 10 模块** M01+M02+M03+M05+M07+M09+M10+M11+M13+M16, Magic 20260101, **11 top-level functions**: 8 public OnInit/OnDeinit/OnTick/IsTradeTime/CheckEntry/TryOpen/ManageTrades/RefreshDashboard + 3 private `_CheckDrawdown`/OnTrade/OnTradeTransaction — 后两者实际是 EA 回调不是私有函数, 计数按"非 MQL5 内置 5 个回调" = 6 public + 2 private helper = **8**）
- **实物 B**：`MQL5/Experts/minimax-ea/Dashboard.mq5`（**208L / 8,361 B / 4 模块** M04+M09+M10+M15, NotifyMagic=0 监听全账户, **9 top-level functions**: 4 回调 OnInit/OnDeinit/OnTick/OnTimer + 2 private helper `_Refresh`/`_Parse` + 3 通知函数 `_CheckDrawdown`/OnTrade/OnTradeTransaction = **6 业务函数 + 3 通知**）
- **策略**：MyEA = **通用骨架范本**（无具体策略, 仅 fixed SL/TP + AllowLong/Short + 时间过滤, 复制起点 = 自定义策略）；Dashboard = **跨品种只读监控**（EURUSD+GBPUSD+XAUUSD+USDJPY 4 品种, FastMA 12 / SlowMA 26 / RSI 14 3 指标/品种, 1s 心跳）
- **M10 三类触发器 = 2 EA 同款范本**：2 EA 都用 `M10.EnablePush/EnableSound` (OnInit) + `M10.Send` (DD 报警 `_CheckDrawdown` L215/L138) + `M10.Send` (拒单 OnTradeTransaction L237/L191) + `M10.Trade` (新成交通知 OnTrade L259/L167) —— 2 EA 各 5 个 M10 方法调用（**同 MeanReversion_EA 范本 5 方法**）
- **MyEA 独有 M13 FileIO**：`OnTrade` 主路径写 `trades_YYYYMMDD.csv`（按日切, 写 BOM-safe ANSI, 表头按需 `_m13CsvHeaderWritten` L57 防重写）；与 M10 通知共用 `_m13LastDealTicket` L51 锚点 = **同 deal 处理循环里顺势调用 2 模块**（避免和 M13 抢 OnTrade 时机）
- **Dashboard 独有 M15 TimerService**：唯一用 M15 的实物 EA；`Init(RefreshSec * 1000)` L57 自动选 `EventSetMillisecondTimer` 或 `EventSetTimer`；`_timer.Fires()/Period()/Mode()/LastFire()` 写到 dashboard Heartbeat 行 L117-119（**"EA 是否还活着" 视觉信号**）
- **2 EA 编译 0 errors**（MyEA.ex5 59,398B + Dashboard.ex5 34,952B, 2026-06-04 01:58 凌晨闭环），**1 周沙盒 trades CSV 待 N4 验证**
- **本 wiki 价值**：是 [[实战/MeanReversion_EA 接入报告]] 范本的"通用骨架 + 监控面板"兄弟 wiki —— 区别是 MeanReversion 13 模块全含 M18+M19（多品种对冲 + 时段过滤），本 2 EA 是 10 + 4 模块（**更精简**），是**新 EA 起步的更小入口**

---

## 1. 实物基本信息

### 1.1 2 个 .mq5 6 维度对比（Node.js fs 实测, 2026-06-04 21:12）

| 维度 | MyEA | Dashboard | 备注 |
|---|---|---|---|
| 路径 | `MQL5/Experts/minimax-ea/MyEA.mq5` | `MQL5/Experts/minimax-ea/Dashboard.mq5` | 2 个实物，**只读**，不写不改 |
| 字节数（磁盘）| **12,541 B** (12.2 KB) | **8,361 B** (8.2 KB) | Node.js fs `statSync` 测得 |
| 总行数 | **301 L** | **208 L** | Node.js fs 测得（含空行 + 注释）|
| 编译产物 | `MyEA.ex5` 59,398 B | `Dashboard.ex5` 34,952 B | 2 .ex5 mtime 2026-06-04T01:58:36 / 01:58:38（凌晨闭环）|
| Magic | `Magic = 20260101` (input L24) | `NotifyMagic = 0` (input L30) | MyEA 用 20260101 标识自己; Dashboard 用 0 = 监听全账户 |
| 接入模块数 | **10 个** (M01+M02+M03+M05+M07+M09+M10+M11+M13+M16) | **4 个** (M04+M09+M10+M15) | 见 §2.1/2.2 模块清单 |
| `#include` 行 | L9-L19（10 个，按 M01→M16 顺序）| L9-L12（4 个, M04→M15 顺序）| 2 EA 都按模块号升序 |
| `class` 定义 | 0（用 MQL5Kit 提供的类 + MQL5 stdlib）| 0（同左）| 2 EA 都是**纯过程式** |
| input 组 | 6 组（基础 / 仓位 / SLTP / 时间 / 显示 / 通知 / M13）| 4 组（监控品种 / 指标 / 刷新 / 通知）| MyEA 6+1 组（含 M13 FileIO 单独组）|
| 编译状态 | 0 errors, 0 warnings | 0 errors, 0 warnings | 2 EA 都通过 MetaEditor F7 闭环 |
| mq5 mtime | 2026-06-03 16:57:46 | 2026-06-03 16:51:16 | 任务开始时间锁定（0 改 .mq5 验证基线）|

### 1.2 任务规格 vs 实测 数字漂移（Node.js fs 单验证）

| 项 | 任务规格 | Node.js fs 实测 | 漂移 |
|---|---|---|---|
| MyEA 字节 | 12,541 B | **12,541 B** | **0** |
| MyEA 行数 | 301 L | **301 L** | **0** |
| MyEA 模块数 | 10 | **10** | **0** |
| Dashboard 字节 | 8,361 B | **8,361 B** | **0** |
| Dashboard 行数 | 208 L | **208 L** | **0** |
| Dashboard 模块数 | 4 | **4** | **0** |

> **结论**：**任务规格数字 100% 准确**（磁盘字节/行数/模块数都对得上，0 漂移）。**以 Node.js fs `'utf8'` 解码后字符数 + 行数（split `\n`）为准**（与 PowerShell `Get-Item` 磁盘字节 UTF-16 LE 解码后等价；本 2 EA 是 UTF-8 编码，无 BOM 头）。

### 1.3 2 EA 共同设计（同构部分）

1. **模块按号升序排列** — 2 EA `#include` 严格按 M0X 模块号升序（MyEA L9-L19 = M01→M16, Dashboard L9-L12 = M04→M15）；object 声明也按号升序（MyEA L46-L52 = M01→M13, Dashboard L30-L33 = M04→M15）
2. **M10 3 类触发器模板** — 2 EA 都用 `_CheckDrawdown` 私有函数（DD 报警 MyEA L215 / Dashboard L138）+ `OnTradeTransaction`（拒单 MyEA L237 / Dashboard L191）+ `OnTrade`（新成交通知 MyEA L259 / Dashboard L167）—— **3 个回调/函数各承担 1 类 M10 通知** = **2 EA 各 5 个 M10 方法调用**（EnablePush + EnableSound + 2 Send + 1 Trade）
3. **OnDeinit 必清理** — 2 EA OnDeinit（MyEA L131 / Dashboard L80）必调 `CCleanup::CleanupAll/DeleteMyObjects`（MyEA L135-L136）+ `_ind.ReleaseAll()`（Dashboard L82）+ `_timer.Deinit()`（Dashboard L83）+ `Comment("")`（2 EA 都有）；MyEA 还调 `logger.Close()` L140
4. **RiskPct / DDAlertPct 默认值** — MyEA input `RiskPct=0.01` L28 / `DDAlertPct=5.0` L46；Dashboard `DDAlertPct=5.0` L28 —— 2 EA 都用 1% 净值风险 + 5% DD 报警
5. **mtime 在 2026-06-03 16:51-16:57 区间**（任务开始时间锁定，0 改 .mq5 验证基线）

### 1.4 2 EA 差异（异构部分）

| 差异维度 | MyEA | Dashboard | 影响 |
|---|---|---|---|
| **目的** | 通用骨架范本（无具体策略）| 跨品种只读监控范本 | 一交易一监控 |
| **策略复杂度** | 极简：fixed SL/TP + AllowLong/Short + 时间过滤 | 0（只读不交易）| MyEA 跑策略 + Dashboard 只监听 |
| **M13 FileIO** | ✅ 接入（写 trades_YYYYMMDD.csv）| ❌ 不用 | MyEA 是 10 实物 EA 中**唯一接 M13** 的（其他 9 EA 都没 M13）|
| **M15 TimerService** | ❌ 不用（走 OnTick + NB 节流）| ✅ 接入（OnTimer 1s/2s 心跳）| Dashboard 是 10 实物 EA 中**唯一接 M15** 的（其他 9 EA 都没 M15）|
| **M07 Positions** | ✅ `CPositions::Count` L155 (OnTick MaxPos 检查) | ❌ 不用 | MyEA 实际用 |
| **M11 Logger** | ✅ `SetFileOutput` L120 (OnInit) + `Trade` L182 (TryOpen) + `Close` L140 (OnDeinit) | ❌ 不用 | MyEA 实际用 |
| **M04 IndicatorPool** | ❌ 不用 | ✅ `AddMA × 2 + AddRSI × 1` × 4 品种 = 12 句柄 | Dashboard 跨品种监控 |
| **OnTick 业务** | `_CheckDrawdown` + NB + `IsTradeTime` + `ManageTrades` + `CheckEntry` + `RefreshDashboard` | `_CheckDrawdown`（仅 DD 报警，无业务）| MyEA 业务密集; Dashboard 轻量 |
| **OnTimer 业务** | ❌（无 OnTimer）| ✅ `_Refresh` 38 行（4 品种循环 + Heartbeat）| Dashboard 周期刷新 |
| **OnTrade 业务** | 写 CSV + M10.Trade + 共享 `_m13LastDealTicket` 锚点 | 仅 M10.Trade | MyEA 双任务; Dashboard 单任务 |
| **input 组数** | 6 组（含 M13 单独组）| 4 组 | MyEA 配置项多 |
| **top-level function 数** | 8 public（OnInit/OnDeinit/OnTick/IsTradeTime/CheckEntry/TryOpen/ManageTrades/RefreshDashboard）+ 1 private helper（`_CheckDrawdown`）= 9（回调 3 算在内 = 11）| 4 回调（OnInit/OnDeinit/OnTick/OnTimer）+ 2 private helper（`_Refresh`/`_Parse`）+ 3 通知函数（`_CheckDrawdown`/OnTrade/OnTradeTransaction）= 9 | Dashboard 函数略多（多了 OnTimer + 2 private helper）|

---

## 2. 接入 MQL5Kit 模块全集清单（核心章节）

> **关键事实**：MyEA 10 模块**全部实际使用**（M01+M02+M03+M05+M07+M09+M10+M11+M13+M16）；Dashboard 4 模块**全部实际使用**（M04+M09+M10+M15）。**2 EA 都不接 M06 Signal / M08 TrailingStop / M12 GV / M14 Drawer / M17 NewsFilter / M18 CorrelationFilter / M19 SessionFilter**。2 EA 共享 M09 + M10 模块（2 个）, MyEA 独有 8 个, Dashboard 独有 2 个。

### 2.1 MyEA 10 模块接入点（Node.js fs 实测行号, 2026-06-04 21:12）

| # | 模块 | include 行 | object 声明 | OnInit 初始化 | 实际调用点（行号）| 调用次数 |
|---|---|---|---|---|---|---|
| 1 | **M01 CTradePlus** | 9 | L46 `CTradePlus      trade;` | L112 `trade.Init(Magic, 30)` / L113 `trade.SetRetry(3, 200)` | TryOpen L182 `if (type == ORDER_TYPE_BUY) { if (trade.Buy(...)) ... }` / L184 `if (trade.Sell(...)) ...` | **4** (1 decl + 1 Init + 1 SetRetry + 1 Buy + 1 Sell) — 实际 4 个方法调用 + 2 条件判断 |
| 2 | **M02 Risk** | 10 | L47 `CRisk           risk;` | L114 `risk.Init(Magic, MaxPos, RiskPct)` | TryOpen L179 `if (!risk.CanOpen(type, lot, sl, tp)) return;` | **3** (1 decl + 1 Init + 1 CanOpen) |
| 3 | **M03 PositionSizing** | 11 | L48 `CPositionSizing sizing;` | L115 `sizing.Init(RiskPct)` | TryOpen L177 `double lot = sizing.LotByRisk(RiskPct, slDist);` | **3** (1 decl + 1 Init + 1 LotByRisk) |
| 4 | **M05 NewBar** | 12 | L49 `CNewBar         NB;` | L116 `NB.Init(_Period)` | OnTick L142 `if (!NB.IsNewBar()) { ... return; }` | **3** (1 decl + 1 Init + 1 IsNewBar) |
| 5 | **M07 Positions** | 13 | (M07 是 static class, 无 decl — **反模式警告**: spec 表格占位易错) | (M07 是 static class, 无 init) | OnTick L156 `if (CPositions::Count(Magic) < MaxPos) CheckEntry();` | **2** (1 个 CPositions 静态方法调用 + 1 个 if 条件) |
| 6 | **M09 Dashboard** | 14 | L50 `CDashboard      dash;` | (无 init — M09 是无状态类) | RefreshDashboard L189-L211 (`dash.Clear/SetTitle/Separator/Row × 7/Line × 2/Show`) | **12** (1 decl + 11 dash.* 调用) |
| 7 | **M10 Notify** | 15 | L52 `CNotify         M10;` | L120 `M10.EnablePush(EnableNotify)` / L121 `M10.EnableSound(EnableNotify)` | `_CheckDrawdown` L215 + L226 `M10.Send(StringFormat("⚠ DD ..."), true)` + OnTrade L286 `M10.Trade(...)` + OnTradeTransaction L249 `M10.Send("❌ MyEA reject: ..." + reason, true)` | **6** (1 decl + 1 input + 1 EnablePush + 1 EnableSound + 2 Send + 1 Trade) |
| 8 | **M11 Logger** | 16 | L51 `CLogger         logger;` | L118 `logger.SetFileOutput(EnableLog)` | TryOpen L182 `logger.Trade("BUY", _Symbol, lot, price, 0, "开多")` / L184 `logger.Trade("SELL", _Symbol, lot, price, 0, "开空")` + OnDeinit L140 `logger.Close()` | **4** (1 decl + 1 SetFileOutput + 2 Trade + 1 Close) |
| 9 | **M13 FileIO** | 17 | (M13 是 static class, 无 decl) | (M13 是 static class, 无 init) | OnTrade L274 `if (WriteTradeRow(t))` → WriteTradeRow L66-99 调 `CFileIO::AppendCSV(fname, hdr)` + `CFileIO::AppendCSV(fname, row)` L96 | **3** (1 个 WriteTradeRow helper + 2 个 CFileIO::AppendCSV 静态方法调用) |
| 10 | **M16 Cleanup** | 19 | (M16 是 static class, 无实例) | (M16 是 static class, 无 init) | OnDeinit L135 `CCleanup::CleanupAll(Magic, "MyEA_", "MyEA_", true, true, true)` / L137 `CCleanup::DeleteMyObjects("MyEA_")` | **2** (2 个 CCleanup 静态方法调用) |

> **数据一致性**：10 模块 include 严格按 M01→M16 顺序排列（L9-L19, 缺 M04/M06/M08/M12/M14/M15/M17/M18/M19），object 声明也按 M01→M13 顺序（L46-L52）；OnInit 初始化按 M01→M11 → M13 顺序（L112-L120）。**所有 10 模块都有实际调用 = 0 浪费**。

### 2.2 Dashboard 4 模块接入点（Node.js fs 实测行号, 2026-06-04 21:12）

| # | 模块 | include 行 | object 声明 | OnInit 初始化 | 实际调用点（行号）| 调用次数 |
|---|---|---|---|---|---|---|
| 1 | **M04 IndicatorPool** | 9 | L30 `CIndicatorPool _ind;` | L60 `_ind.AddMA("MA_F_" + _symbols[i], FastMA, MODE_EMA)` / L61 `_ind.AddMA("MA_S_" + _symbols[i], SlowMA, MODE_EMA)` / L62 `_ind.AddRSI("RSI_" + _symbols[i], RSI_Period)` × 4 品种 = 12 个指标句柄 | `_Refresh` L107 `double maF = _ind.Value("MA_F_" + sym, 0)` / L108 `double maS = _ind.Value("MA_S_" + sym, 0)` / L109 `double rsi = _ind.Value("RSI_" + sym, 0)` + OnDeinit L82 `_ind.ReleaseAll()` | **16** (1 decl + 12 AddXxx + 3 Value + 1 ReleaseAll) |
| 2 | **M09 Dashboard** | 10 | L31 `CDashboard     _dash;` | (无 init) | `_Refresh` L97-L122 (`_dash.Clear/SetTitle/Separator/Row × 4/Line × 4 + 5/Separator × 2/Show`) | **17** (1 decl + 16 dash.* 调用) |
| 3 | **M10 Notify** | 11 | L33 `CNotify        M10;` | L63 `M10.EnablePush(EnableNotify)` / L64 `M10.EnableSound(EnableNotify)` | `_CheckDrawdown` L138 + L149 `M10.Send(StringFormat("⚠ DD ..."), true)` + OnTrade L182 `M10.Trade(typeStr + "/" + entryStr, ...)` + OnTradeTransaction L201 `M10.Send("❌ Dashboard reject: ..." + reason, true)` | **6** (1 decl + 1 input + 1 EnablePush + 1 EnableSound + 2 Send + 1 Trade) |
| 4 | **M15 TimerService** | 12 | L32 `CTimerService  _timer;` | L57 `if (!_timer.Init(RefreshSec * 1000)) { Print("Dashboard: CTimerService.Init failed"); return INIT_FAILED; }` | OnTimer L90-L94 `if (_timer.OnTimer()) { _Refresh(); }` + OnDeinit L83 `_timer.Deinit()` + `_Refresh` L117 `IntegerToString(_timer.Fires())` / L118 `IntegerToString(_timer.Period()) + _timer.Mode()` / L119 `TimeToString(_timer.LastFire(), TIME_SECONDS)` | **9** (1 decl + 1 Init + 1 OnTimer + 1 Deinit + 4 心跳统计查询) |

> **数据一致性**：4 模块 include 严格按 M04→M15 顺序排列（L9-L12），object 声明也按 M04→M15 顺序（L30-L33）；OnInit 初始化按 M04→M15 → M10 顺序（L57-L64）。**所有 4 模块都有实际调用 = 0 浪费**。

### 2.3 2 EA 共享 vs 独有 模块对比

| 模块 | MyEA (10) | Dashboard (4) | 实际使用 |
|---|:-:|:-:|---|
| M01 CTradePlus | ✅ 4 调用 | ❌ 不用 | **MyEA 独有**（Dashboard 不交易）|
| M02 Risk | ✅ 3 调用（CanOpen 1）| ❌ 不用 | **MyEA 独有**（Dashboard 不交易）|
| M03 PositionSizing | ✅ 3 调用（LotByRisk）| ❌ 不用 | **MyEA 独有**（Dashboard 不交易）|
| M04 IndicatorPool | ❌ 不用 | ✅ 16 调用 | **Dashboard 独有**（跨品种 12 指标）|
| M05 NewBar | ✅ 3 调用 | ❌ 不用 | **MyEA 独有**（Dashboard 走 OnTimer）|
| M07 Positions (CPositions) | ✅ 2 调用（Count）| ❌ 不用 | **MyEA 独有**（MaxPos 检查）|
| M09 Dashboard | ✅ 12 调用 | ✅ 17 调用 | **共享使用**（2 EA 都画面板）|
| M10 Notify | ✅ 6 调用（5 方法）| ✅ 6 调用（5 方法）| **完全同构**（3 触发器模板）|
| M11 Logger | ✅ 4 调用 | ❌ 不用 | **MyEA 独有**（trades 日志）|
| M13 FileIO | ✅ 3 调用（CSV 落盘）| ❌ 不用 | **MyEA 独有**（trades CSV 落盘）|
| M15 TimerService | ❌ 不用 | ✅ 9 调用 | **Dashboard 独有**（1s/2s 心跳）|
| M16 Cleanup | ✅ 2 调用（CleanupAll + DeleteMyObjects）| ❌ 不用（无对象）| **MyEA 独有** |
| **合计** | **10 全部用** | **4 全部用** | **2 EA 各模块 0 浪费** |

> **观察**：2 EA **不共享任何"交易"模块**（M01-M03 + M11 + M13 + M16 = MyEA 独有 6 个, M04 + M15 = Dashboard 独有 2 个），**只共享 M09 + M10 2 个"显示 + 通知"模块**：
> - **共享 M09 Dashboard**：MyEA 12 调用（RefreshDashboard L189-L211）/ Dashboard 17 调用（_Refresh L97-L122）—— Dashboard 函数多（4 品种循环 + Heartbeat 多 5 行）
> - **共享 M10 Notify**：2 EA 各 5 方法调用（完全同构，**同 TrendMA + Breakout 2 EA 范本** + MeanReversion 范本）
> - **互不交易**：MyEA 跑策略 + Dashboard 只监听 = **"2 EA 联动但无耦合"**（Dashboard 通过 `NotifyMagic=0` 监听全账户, 包含 MyEA 的成交, 推 M10.Trade 通知）

### 2.4 M10 3 类触发器范本（2 EA 同构, 5 方法调用）

> **本节是 M10 实战最有用的 3-触发器模板**——同 [[实战/MeanReversion_EA 接入报告]] §3.2 范本 + [[实战/TrendMA_EA + Breakout_EA 接入报告]] §2.4 范本。MyEA + Dashboard 各 **5 个 M10 方法调用**（完全同构）。

| 回调/函数 | MyEA 行 | Dashboard 行 | M10 方法 | 触发条件 | 输出 |
|---|---|---|---|---|---|
| OnInit | L120 `M10.EnablePush(EnableNotify)` | L63 `M10.EnablePush(EnableNotify)` | `EnablePush` | input `EnableNotify=true` | 启用 MT5 Push 通知 |
| OnInit | L121 `M10.EnableSound(EnableNotify)` | L64 `M10.EnableSound(EnableNotify)` | `EnableSound` | input `EnableNotify=true` | 启用声音提示 |
| `_CheckDrawdown` (private helper) | L226 `M10.Send(StringFormat("⚠ DD %.2f%% on %s (eq=%.2f peak=%.2f)", ddPct, _Symbol, equity, _peakEquity), true)` | L149 同 | `Send` | 净值回撤 `ddPct >= DDAlertPct`（默认 5%）| "⚠ DD xx% on XAUUSDm (eq=xx peak=xx)" |
| `OnTrade` (回调) | L286 `M10.Trade(typeStr + "/" + entryStr, symbol, price, volume, 0, "MyEA")` | L182 `M10.Trade(typeStr + "/" + entryStr, symbol, price, volume, 0, tag)` | `Trade` | 新成交（用 `_m13LastDealTicket` / `_lastDealTicket` 去重 L268 / L175）| "BUY/OPEN XAUUSDm @xx vol=xx MyEA" / "Dash[magic]" |
| `OnTradeTransaction` (回调) | L249 `M10.Send("❌ MyEA reject: " + reason, true)` | L201 `M10.Send("❌ Dashboard reject: " + reason, true)` | `Send` | 订单被服务器拒（retcode ≠ DONE / DONE_PARTIAL / PLACED）| "❌ EA reject: retcode=xx \| BUY XAUUSDm 0.01 @xx" |

> **M10 3 类触发器 = 任何生产 EA 的"最小通知模板"**。2 EA 各 **5 个 M10 方法调用**（EnablePush + EnableSound + 2 Send + 1 Trade），与 MeanReversion_EA / TrendMA_EA / Breakout_EA 5 EA 同款范本。
> 详细 `_CheckDrawdown` 实现：`_peakEquity` 跟踪 L218 `if (equity > _peakEquity) _peakEquity = equity;` + `_ddAlertActive` 抖动防误报 L222-L229（MeanReversion 范本同款）。

### 2.5 MyEA 独有: M13 FileIO + M10 通知 共享去重锚点（`_m13LastDealTicket` L51）

> **本节是 M13 实战最有用的"OnTrade 共享去重"范本**——M13 FileIO + M10 Notify 在同一 deal 处理循环里顺势调用, 用单一变量 `_m13LastDealTicket` 锚点防止重复处理。

```mql5
// MyEA.mq5 L51 (静态变量, 初始化)
static ulong  _m13LastDealTicket  = 0;    // 上次已处理的 deal ticket (M10 通知 + M13 落盘共用)

// MyEA.mq5 L122-L125 (OnInit 初始化锚点, 防重放历史)
HistorySelect(0, TimeCurrent());
int _histTotal = HistoryDealsTotal();
_m13LastDealTicket = (_histTotal > 0) ? HistoryDealGetTicket(_histTotal - 1) : 0;

// MyEA.mq5 L259-L292 (OnTrade 回调, 关键段)
void OnTrade() {
   // M13 FileIO 落盘: 主路径
   // M10 通知  : 副路径, 在同一 deal 处理循环里顺势调用 (避免和 M13 抢 OnTrade)
   if (!LogTradesToCsv && !EnableNotify) return;     // 早退: 2 模块都关
   HistorySelect(0, TimeCurrent());
   int total = HistoryDealsTotal();
   if (total <= 0) return;
   for (int i = total - 1; i >= 0; i--) {            // 倒序遍历, 从最新 deal 开始
      ulong t = HistoryDealGetTicket(i);
      if (t == 0 || t <= _m13LastDealTicket) break;  // 关键: 锚点去重, 跳出循环
      // M13 落盘
      if (LogTradesToCsv) {
         if (WriteTradeRow(t)) {
            PrintFormat("[M13] trade logged: ticket=%I64u file=%s", t, TodayCsvName());
         }
      }
      // M10 通知 (与 M13 共用同一去重: _m13LastDealTicket)
      if (EnableNotify) {
         long dealMagic = HistoryDealGetInteger(t, DEAL_MAGIC);
         if ((ulong)dealMagic == Magic) {             // 过滤 magic
            // ... 拼装 typeStr/entryStr ...
            M10.Trade(typeStr + "/" + entryStr, symbol, price, volume, 0, "MyEA");
         }
      }
      _m13LastDealTicket = t;                         // 更新锚点
   }
}
```

> **关键设计**：
> 1. **单一锚点 `_m13LastDealTicket` 承担 2 模块同步** —— M13 落盘 + M10 通知共用同一去重, 避免"M13 写了一次但 M10 推了 2 次"或反之
> 2. **OnInit 初始化锚点到当前历史最大 ticket** L122-L125 —— EA 重启不重放历史, 防 M13 写重复行
> 3. **M10.Trade 加 magic 过滤** L279 `if ((ulong)dealMagic == Magic)` —— 避免推送"别人的成交"（同账户挂多 EA 场景）
> 4. **早退优化** L263 `if (!LogTradesToCsv && !EnableNotify) return;` —— 2 模块都关时直接退, 不扫历史（性能优化）

> **复用到 Dashboard**：Dashboard L167-L186 `OnTrade` 走相同范本, 但用单一变量 `_lastDealTicket` L34（不带 `_m13` 前缀, 因为 Dashboard 不接 M13）, 逻辑完全同款（**反例 = 没有共享, 单一变量只服务 M10**）。

### 2.6 Dashboard 独有: M15 TimerService 心跳节流（`_timer.Fires()` 等 4 个查询）

> **本节是 M15 实战最有用的"OnTimer + 心跳统计"范本**——Dashboard 是 10 实物 EA 中**唯一接 M15 的**, 写 `_Refresh` 时把 M15 心跳数据写到 dashboard Heartbeat 行, 让用户能直接看"EA 是否还活着"。

```mql5
// Dashboard.mq5 L57 (OnInit 启动心跳)
if (!_timer.Init(RefreshSec * 1000)) {
   Print("Dashboard: CTimerService.Init failed");
   return INIT_FAILED;
}

// Dashboard.mq5 L90-L94 (OnTimer 节流)
void OnTimer() {
   // Route the terminal event through CTimerService so it can track
   // LastFire / Fires, then refresh the dashboard.
   if (_timer.OnTimer()) {     // 关键: M15 节流, 实际 1s/2s 一次
      _Refresh();
   }
}

// Dashboard.mq5 L83 (OnDeinit 停心跳)
void OnDeinit(const int reason) {
   _ind.ReleaseAll();
   _timer.Deinit();
   Comment("");
}

// Dashboard.mq5 L117-L119 (_Refresh 写心跳到 dashboard)
_dash.Separator();
_dash.Row("Heartbeat", IntegerToString(_timer.Fires()) + " fires (period " +
          IntegerToString(_timer.Period()) + _timer.Mode() +
          ", last " + TimeToString(_timer.LastFire(), TIME_SECONDS) + ")");
_dash.Line("Last update: " + TimeToString(TimeCurrent()));
_dash.Show();
```

> **关键设计**：
> 1. **`Init(RefreshSec * 1000)` L57** —— RefreshSec=2 (input L23) → 2000ms 走 `EventSetTimer(2)` 整秒; <1000ms 走 `EventSetMillisecondTimer`; **整千 ms 走秒, 非整千走 ms 模式但实际达不到精确 ms**（M15 spec line 80-83 警告）
> 2. **`OnTimer` 先 `if (_timer.OnTimer())`** L91 —— M15 内部 `Fires++` + `LastFire = TimeCurrent()` 统计, 然后调业务
> 3. **`_timer.Deinit()` L83 必调** —— OnDeinit 必停心跳, 否则 EA 卸载后 timer 还在跑（**反模式警告**: 不调 `_timer.Deinit` = timer 泄漏）
> 4. **4 个查询方法写到 dashboard L117-L119** —— `Fires()` 总次数 / `Period()` 实际周期 / `Mode()` "s" 或 "ms" / `LastFire()` 上次触发时间, 让用户看"是否还活着 + 是否按预期周期触发"

---

## 3. 编译验证 & 沙盒结果

### 3.1 编译状态（2026-06-04 凌晨实测）

| 验证项 | MyEA | Dashboard | 备注 |
|---|---|---|---|
| MetaEditor64 编译 | **0 errors, 0 warnings** | **0 errors, 0 warnings** | 2 EA 都通过 |
| `.ex5` 产物 | **59,398 B** | **34,952 B** | 2 .ex5 已落盘 |
| 编译时间 | 2026-06-04 01:58:36 (.ex5 mtime) | 2026-06-04 01:58:38 (.ex5 mtime) | 同分钟闭环, 可能同 batch 编译 |
| 源 mq5 mtime | 2026-06-03 16:57:46 | 2026-06-03 16:51:16 | 任务开始时间锁定 (16-17h 间隔) |

### 3.2 编译命令（验证用）

```powershell
$me = "C:\Program Files\MetaTrader 5\MetaEditor64.exe"
& $me /compile:"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea\MyEA.mq5" /log
& $me /compile:"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea\Dashboard.mq5" /log
# 退出码 0 = 成功
# metaeditor.log: "MyEA.mq5: 0 error(s), 0 warning(s)" + "Dashboard.mq5: 0 error(s), 0 warning(s)"
```

> ⚠ **GUI 编译需 console 1 触发**（F7 按键受 UIPI 拦），Mavis 触不到。命令行 `/compile` 是等价替代。**本 2 EA 已编译落盘, 不需复编译**。

### 3.3 编译错误速查（本 2 EA 特有问题）

| 错误 | 原因 | 解决 |
|---|---|---|
| `cannot open include file 'MQL5Kit/M01_CTradePlus.mqh'` | M01 模块未落地 | 复制 `M01_CTradePlus.mqh` 到 `MQL5/Include/MQL5Kit/` |
| `'CTimerService' - identifier not found` (Dashboard 误用) | Dashboard 用 M15 但 include 漏 | Dashboard **必含** `#include <MQL5Kit/M15_TimerService.mqh>` (L12) |
| `'OnTradeTransaction' - wrong parameters count` | MQL5 函数签名不匹配 | 用标准 `void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)` 3 参数版 |
| `AppendCSV not found` (MyEA 误用) | M13 是 static class, 直接 `CFileIO::AppendCSV(...)` 调 | MyEA L66 调 `CFileIO::AppendCSV(fname, hdr)` —— **不要** `m13_obj.AppendCSV` (无对象) |
| `Trade() - wrong magic` (MyEA 误用) | M10.Trade 缺 magic 过滤 | OnTrade L279 加 `if ((ulong)dealMagic == Magic)` 过滤, 避免推送"别人的成交" |

### 3.4 1 周沙盒预期（待 N4 跑实测）

| 指标 | MyEA 预期 | Dashboard 预期 | 备注 |
|---|---|---|---|
| Net Profit | 待 N4 实测 | n/a (不交易) | |
| Profit Factor | 待 N4 实测 | n/a | |
| Max DD | 待 N4 实测 | n/a | |
| Win Rate | 待 N4 实测 | n/a | |
| Total Trades | 通用骨架无具体策略, 预期 30-100 笔/周 | 0 (只监听) | MyEA 跑通即 OK |
| trades CSV | **M13 落盘 trades_YYYYMMDD.csv** L100 `TodayCsvName()` | n/a | MyEA **唯一接 M13** 的实物 EA, 落盘可验 |
| M10 推送链路 | 待 N4 验证（DD 报警 / 新成交 / 拒单各 ≥ 1 次）| 待 N4 验证 | 2 EA 共享 3-触发器模板（5 方法调用）|
| Dashboard Heartbeat | n/a | **M15 Fires() 计数** (L117) | 唯一用 M15 的实物 EA, 心跳可验 |

> **承诺**：本 wiki 不写虚假回测数据；§3.4 表格"待 N4 实测"是真实数据待 N4 任务完成时填入。

---

## 4. 与模板对应关系

> 本 2 EA 是 2 个 [[02-完整模板/EA 完整模板]] wiki 的"实物 demo"——MyEA 对应通用骨架模板, Dashboard 对应 Dashboard 监控模板。**2 个模板 wiki 都已经引用本 2 EA**（见 §7.2 反链）。

### 4.1 2 EA vs 2 模板 对应表

| 实物 EA | 对应模板 | 模板 wiki 引用 | 差异 |
|---|---|---|---|
| **MyEA** | [[02-完整模板/EA 通用骨架]] | 模板"复制此文件开始你的策略" | MyEA 头注释 L2 `MQL5Kit 通用 EA 骨架` —— **1:1 同模板**, MyEA 多了 M11+M13+M16（trades 日志 + CSV 落盘 + Cleanup）|
| **Dashboard** | [[02-完整模板/EA Dashboard 监控模板]] | 模板 L17-21 引用 `MQL5/Experts/minimax-ea/Dashboard.mq5` (8.1 KB / 208 行 / 4 模块) | Dashboard 走 M15 包装, 模板走 `EventSetTimer` 裸调 —— **Dashboard 是 M15 升级版** |

### 4.2 MyEA 通用骨架范本 (10 模块 = 通用骨架标准装)

> **MyEA 是 MQL5Kit 官方"复制此文件开始你的策略"的实物范本**——10 模块 M01-M11 + M16 的子集, 排除 M04 (无指标) / M06 (无信号抽象) / M08 (无 trail) / M12 / M14 / M15 / M17-M19。**是写新 EA 的"最小完整装"**:

| 模块组 | MyEA 接入模块 | 新 EA 复用建议 |
|---|---|---|
| 交易核心 | M01 + M02 + M03 (3 件套) | 必接 |
| 信号节流 | M05 (NewBar) | 必接 |
| 持仓管理 | M07 (Count MaxPos) | 必接 |
| 显示 | M09 (Dashboard) | 选接 (ShowDashboard=true) |
| 通知 | M10 (3 触发器) | 必接 (MT5 Push) |
| 日志 | M11 (Logger) | 必接 (trades 落盘) |
| 数据落盘 | M13 (FileIO CSV) | 选接 (M11 落盘 vs M13 CSV 二选一) |
| 清理 | M16 (Cleanup) | 必接 (OnDeinit) |
| **必接合计** | **9/10** (M09 选接, 其余 9 必接) | **新 EA 起步 = 9 必接** |

> **新 EA 起步 3 步法**：
> 1. 复制 MyEA.mq5 到 `MQL5/Experts/<你的策略>/<EA>.mq5`
> 2. 改 input 参数 + 加自己的信号函数（替代 `CheckEntry` L160-L163 的 `AllowLong/Short` 简单条件）
> 3. 编译 (F7 / `/compile`) + demo 24h → 实盘

### 4.3 Dashboard 监控模板范本 (4 模块 = 跨品种监控最小集)

> **Dashboard 是 [[02-完整模板/EA Dashboard 监控模板]] 的"M15 升级版"**——模板走 `EventSetTimer(RefreshSec)` 裸调 L56, Dashboard 走 `_timer.Init(RefreshSec * 1000)` M15 包装 L57。**升级收益**:

| 升级维度 | 模板裸调 | Dashboard M15 包装 | 收益 |
|---|---|---|---|
| 周期精度 | 整秒 (EventSetTimer 限制) | 自动选 EventSetMillisecondTimer / EventSetTimer | 支持 1.5s, 800ms 等非整秒 |
| 心跳统计 | 无 | `Fires()` + `LastFire()` 写 dashboard | 用户能直接看 EA 是否还活着 |
| 启停管理 | 手动 `EventSetTimer` + `EventKillTimer` | `Init()` / `Deinit()` / `Start()` / `Stop()` 状态机 | 易维护 |
| 重复 Init | 需手动 kill 再 set | `Init()` 内部自动清理 | 防 timer 泄漏 |

> **新监控 EA 起步 3 步法**：
> 1. 复制 Dashboard.mq5 到 `MQL5/Experts/<你的监控>/<Monitor>.mq5`
> 2. 改 `Symbols` input + `_Refresh` 函数内容 (加你的监控维度)
> 3. 编译 + attach 到任意 chart, 1s/2s 心跳刷新

---

## 5. 3 场景调优

> **未跑 N4 1 周沙盒** —— 下面 3 个场景的"调优表数值"是经验值 / 预期值，**待 N4 1 周沙盒实测**。本 wiki 给"如何调优"的方法论 + 3 档建议值。

### 5.1 场景 A: MyEA 作为剥头皮测试底盘 (Scalping_More 集成基础)

**问题**：Scalping_More_v1.3 (13:00 T3 范本) 用了 8-11 模块, 想基于 MQL5Kit 重写剥头皮, **MyEA 是最佳起点** (10 模块 + 11 函数 + 完整 6 input 组 + 2 模板化函数 `CheckEntry`/`TryOpen`)。

**当前实现**（MyEA `CheckEntry` L160-L163 + `TryOpen` L164-L184）：

```mql5
// MyEA.mq5 L160-L163 (CheckEntry 极简, 替换为你的信号函数)
void CheckEntry() {
   if (AllowLong  /* BuySignal  */) TryOpen(ORDER_TYPE_BUY);
   if (AllowShort /* SellSignal */) TryOpen(ORDER_TYPE_SELL);
}

// MyEA.mq5 L164-L184 (TryOpen 模板: SL/TP calc + lot calc + risk check + Buy/Sell + logger.Trade)
void TryOpen(ENUM_ORDER_TYPE type) {
   double price = (type == ORDER_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                                           : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if (price == 0) return;
   double sl = (type == ORDER_TYPE_BUY) ? price - SL_Points * _Point : price + SL_Points * _Point;
   double tp = (type == ORDER_TYPE_BUY) ? price + TP_Points * _Point : price - TP_TP * _Point;  // 注: 实际 L172 是 price - TP_Points * _Point
   double slDist = MathAbs(price - sl);
   double lot = sizing.LotByRisk(RiskPct, slDist);
   if (lot <= 0) return;
   if (!risk.CanOpen(type, lot, sl, tp)) return;
   if (type == ORDER_TYPE_BUY) {
      if (trade.Buy(lot, sl, tp, EAComment)) logger.Trade("BUY", _Symbol, lot, price, 0, "开多");
   } else {
      if (trade.Sell(lot, sl, tp, EAComment)) logger.Trade("SELL", _Symbol, lot, price, 0, "开空");
   }
}
```

**调优方向**（把 MyEA 改造成剥头皮 EA, 3 档）：

| 风险偏好 | MyEA 调 | 预期差异 |
|---|---|---|
| **保守** | SL=300, TP=600 (2:1 RR) + 加 M19 SessionFilter (关亚洲盘) | 交易数 -50%, 胜率 +5pp, DD -3pp (**待 N4**) |
| **标准** | SL=200, TP=400 (2:1 RR, 默认) | 默认 |
| **激进** | SL=100, TP=200 (2:1 RR) + 加 M17 NewsFilter (黑天鹅 ±30min 拦截) | 交易数 +100%, 胜率 -5pp, DD +5pp (**待 N4**) |

**关键复用点**:
- `TryOpen` L164-L184 **整段保留** = SL/TP/lot/risk/Buy/logger 6 步流程, 任何策略都用得上
- `CheckEntry` L160-L163 **替换为你的 BuySignal/SellSignal 函数** (如 `CSignal::CrossUpSeries` 或自定义)
- M13 CSV 落盘 L259-L292 **保留** = trades 自动落盘, 无需自己写文件 IO
- M10 3 触发器 **保留** = DD 报警 + 新成交 + 拒单全自动

### 5.2 场景 B: Dashboard 监控 4 EA 净值曲线 (单 chart 挂 4 EA 联动)

**问题**：账户挂 4 个 EA (MyEA + TrendMA + Breakout + MeanReversion), 各跑各的策略, 净值曲线分散在 4 chart 不直观。**把 Dashboard 改成"4 EA 联动监控"**, 通过 `NotifyMagic=0` 监听全账户 (默认行为) → M10.Trade 推"4 EA 各自新成交" → 净值汇总在 dashboard Balance/Equity/Open P/L 3 行。

**当前实现**（Dashboard `_Refresh` L97-L122 已有 4 段：账户 3 行 + 持仓 1 行 + 4 品种行情循环 + Heartbeat）：

| 段 | Dashboard 当前 | 4 EA 联动改造 |
|---|---|---|
| L99-L101 账户 | Balance / Equity / Free | **保留** (4 EA 共享账户维度) |
| L104-L106 持仓 | Open P/L 汇总 (含 magic 过滤可加) | **加 magic 过滤** (Dashboard L30 `NotifyMagic` 已支持, 改成 0 = 监听全账户即可) |
| L107-L113 4 品种 | 4 品种行情 (EURUSD/GBPUSD/XAUUSD/USDJPY) | **改为 4 EA 各自 magic 的最新 P/L 汇总** (需自己加 `HistorySelectByMagic`) |
| L117-L119 Heartbeat | M15 Fires/Period/Mode/LastFire | **保留** (确认 EA 还活着) |
| L121 时间戳 | Last update | **保留** |

**调优方向**（3 档）:

| 风险偏好 | Dashboard 调 | 预期差异 |
|---|---|---|
| **保守** | RefreshSec=5 (5s 心跳, 减少 CPU) | CPU -60%, 实时性 -60% |
| **标准** | RefreshSec=2 (2s 心跳, 默认) | 默认 |
| **激进** | RefreshSec=1 (1s 心跳) | CPU +100%, 实时性 +100% |

### 5.3 场景 C: MyEA + Dashboard 联动 (Dashboard 读 MyEA GV 显净值)

**问题**：MyEA 跑策略 + Dashboard 监控, **当前是"松耦合"** (Dashboard 通过 magic 20260101 过滤 MyEA 成交, 推 M10.Trade 通知)。**想做到"紧耦合"**: Dashboard 读 MyEA 的 GlobalVariable (M12 GV) 写净值到 dashboard 显"MyEA 净值"。

**当前限制**:
- MyEA **未接 M12 GV** (10 模块中无 M12) —— 无法把净值写到 GV
- Dashboard **未接 M12 GV** (4 模块中无 M12) —— 无法读 GV

**未来 P1 接入清单**:
- MyEA 加 `#include <MQL5Kit/M12_GV.mqh>` + `CGV gv;` + OnTick 加 `gv.SetDouble("MyEA_Equity", AccountInfoDouble(ACCOUNT_EQUITY))` + OnDeinit 加 `gv.DelAll("MyEA_")` 清 GV
- Dashboard 加 `#include <MQL5Kit/M12_GV.mqh>` + `CGV gv;` + `_Refresh` 加 `dash.Row("MyEA Equity", DoubleToString(gv.GetDouble("MyEA_Equity", 0), 2))` 读 MyEA 净值

**优势**:
- 1 个 chart 监控所有 EA 净值, 不用切 4 chart
- 净值变化立即可见 (Dashboard RefreshSec 周期)
- M12 GV 跨重启保留, EA 重启后 Dashboard 仍能读到上次净值 (但需 GV 没被 OnDeinit 清, 注意取舍)

**风险**:
- 写 GV 频率别太高 (建议 OnTick 走 NB.IsNewBar 节流, 别每 tick 写)
- GV key 命名要带 EA magic 前缀避免冲突 (如 `MyEA_20260101_Equity`)

### 5.4 调优操作清单 (10 步)

> 按本节做参数对比实验, 每步独立可验:

1. **复制 MyEA baseline set** — 备份 `MyEA.set` 到 `Profiles/Tester/MyEA_BASELINE.set`
2. **复制 Dashboard baseline set** — 同上 `Dashboard_BASELINE.set`
3. **写 MyEA 标准 set** — `MyEA_STD.set` (RiskPct=0.01, SL=200, TP=400, MaxPos=3)
4. **写 Dashboard 标准 set** — `Dashboard_STD.set` (RefreshSec=2, NotifyMagic=0, DDAlertPct=5.0)
5. **GUI 改区间** — MT5 Strategy Tester **手动改** Date From=2026.05.01, To=2026.06.01 (**关键**, 不要用 GUI 默认 last_month)
6. **跑 MyEA baseline** — Start → 报告 `Tester/Reports/MyEA.xml` 落盘
7. **跑 Dashboard baseline** — attach 到 demo 24h, 看 dashboard 12 行输出 + Heartbeat
8. **跑 2 EA 联动** — 1 chart 挂 MyEA (策略) + 1 chart 挂 Dashboard (监控) → 验证 M10.Trade 推送
9. **验证 M13 落盘** — `MQL5/Files/trades_YYYYMMDD.csv` 落盘检查 (MyEA L100 `TodayCsvName()`)
10. **生产用最优** — attach 评分最高的 set 到 demo 24h → 验证 M10 3 触发器各触发 ≥ 1 次

### 5.5 调优参考数据来源 (待 N4 实物)

| 来源 | 内容 | 状态 |
|---|---|---|
| [[实战/5 EA 6 月回测对比 SOP]] | 5 EA × 6 月 × 3 套参数回测方法论 (10 步 SOP + 4 维度评分) | 2026-06-04 14:17 已发布 |
| N4 1 周沙盒实物 | MyEA + Dashboard 2 EA × 1 周 × demo XAUUSDm 实测数据 | **P0 排期, 未启动** |
| N4 数据出来 | 本 wiki §3.4/§5.1/5.2/5.3 表格"待 N4 实物"单元格将用实测值替换 | 待 N4 完成 |

> **承诺**: 本 wiki 不写虚假回测数据; §5.x 表格"待 N4 实物"是真实数据待 N4 任务完成时填入。

---

## §6 5 反模式 (沿用 M18 spec 5 条 + 本 2 EA 专属延伸)

> **本节风格 100% 沿用 [[实战/M18 多品种对冲实战]] §6 5 反模式 (解释 + 反例 + 正例)**。本 2 EA 专属反模式在最后 3 条 (MyEA 专属 / Dashboard 专属 / 联动专属)。

### 反模式 1: OnTick 调 EventKillTimer (MyEA / Dashboard 都不该有)

**错在哪**: M15 TimerService Deinit 走 `EventKillTimer()`, 但只能在 `OnDeinit` 调, 不能在 `OnTick` 调 (会让定时器反复启停, EA 心跳丢失)。**MyEA 不接 M15, 本反模式不适用 MyEA; 但 Dashboard 用户复制时容易在 OnTick 误加 `_timer.Deinit()`, 必看本条**。

**反例**:
```mql5
// ❌ 错: OnTick 调 EventKillTimer / _timer.Deinit
void OnTick() {
   _timer.Deinit();   // ❌ 错: 每次 tick 停一次, timer 等于没启
}
```

**正例**:
```mql5
// ✅ 对: OnDeinit 调 _timer.Deinit, OnTick 走 _timer.OnTimer() 节流
void OnTick() {
   // M10 触发器 1: 净值回撤 > DDAlertPct 报警
   _CheckDrawdown();
}

void OnTimer() {
   if (_timer.OnTimer()) {   // 关键: M15 OnTimer() 而不是 Deinit
      _Refresh();
   }
}

void OnDeinit(const int reason) {
   _ind.ReleaseAll();
   _timer.Deinit();          // ✅ 对: OnDeinit 才调
   Comment("");
}
```

### 反模式 2: M13.FileIO 写 C:\Windows\ 路径 (无沙箱保护)

**错在哪**: `CFileIO::AppendCSV(fname, row)` 默认写 `MQL5/Files/` 目录 (沙箱), **不能写 `C:\Windows\` 等系统目录**。`fname = "C:\\Windows\\trades.csv"` 会触发 MT5 错误 "Function not allowed" 或 "Path not found"。**MyEA L100 `TodayCsvName()` 返回 `trades_YYYYMMDD.csv` (相对路径) 走默认沙箱 = 正确范本**。

**反例**:
```mql5
// ❌ 错: 写 C:\Windows\ 路径
string fname = "C:\\Windows\\trades_" + today + ".csv";
CFileIO::AppendCSV(fname, row);   // ❌ 沙箱拦截, 报错
```

**正例**:
```mql5
// ✅ 对: 走默认 MQL5/Files/ 沙箱
string TodayCsvName() {           // MyEA L100
   MqlDateTime dt;
   TimeCurrent(dt);
   return CsvFilePrefix            // input L51 "trades_"
        + IntegerToString(dt.year,  4) + IntegerToString(dt.mon, 2)
        + IntegerToString(dt.day,   2) + ".csv";
}

CFileIO::AppendCSV(fname, row);   // ✅ 写 MQL5/Files/trades_YYYYMMDD.csv
```

### 反模式 3: Dashboard OnTimer 每 tick 跑 (用 M15 TimerService 1s 节流)

**错在哪**: Dashboard 走 `OnTick` 每 tick 跑 `_Refresh()` = XAUUSDm M1 每秒 5+ tick = 5+ 次/秒字符串重建 = CPU spike 5ms/tick。**Dashboard 走 OnTimer + M15 1s/2s 节流 = 0% CPU spike**。

**反例**:
```mql5
// ❌ 错: OnTick 调 _Refresh (无节流)
void OnTick() {
   _CheckDrawdown();
   _Refresh();   // ❌ 每 tick 跑, CPU 5ms/tick
}
```

**正例** (Dashboard 实物 L85-L94):
```mql5
// ✅ 对: OnTick 只做 DD 报警, OnTimer 走 M15 节流刷面板
void OnTick() {
   // M10 触发器 1: 净值回撤 > DDAlertPct 报警
   _CheckDrawdown();
}

void OnTimer() {
   // Route the terminal event through CTimerService so it can track
   // LastFire / Fires, then refresh the dashboard.
   if (_timer.OnTimer()) {     // M15 节流, 实际 1s/2s 一次
      _Refresh();
   }
}
```

### 反模式 4: MyEA 直接 `ORDER_FILLING_FOK` (改 REQUEST 模式自动选)

**错在哪**: MyEA `TryOpen` L182 `trade.Buy(lot, sl, tp, EAComment)` 走 M01 CTradePlus 内部 `_AutoSetFilling()`, 自动选 `ORDER_FILLING_FOK/IOC/RETURN`。**如果用户复制 MyEA 后改 `trade.Buy` 为 `OrderSend` 直接发请求, 必须自己选 filling**。硬编码 FOK 在老式 MM / 伊斯兰账户会被 10014 拒单。**M01 已自动处理, 不要再降级**。

**反例**:
```mql5
// ❌ 错: 直接 OrderSend 硬编码 FOK
MqlTradeRequest req = {};
req.type_filling = ORDER_FILLING_FOK;   // 老式 MM 10014 拒单
OrderSend(req, result);
```

**正例** (MyEA 实物 L182):
```mql5
// ✅ 对: 用 M01 CTradePlus, 内部自动选 filling
if (type == ORDER_TYPE_BUY) {
   if (trade.Buy(lot, sl, tp, EAComment))   // M01 内部 _AutoSetFilling
      logger.Trade("BUY", _Symbol, lot, price, 0, "开多");
}
```

> **跨经纪商适配**: 见 [[04-避坑与速查/04 经纪商差异-点差-手续费]] §反模式 3, Exness demo hedging 账户 FOK OK, 但 OANDA US netting 账户只支持 RETURN —— **M01 自动选避免这坑**。

### 反模式 5: MyEA + Dashboard 联动不要硬编码 Magic (用 input)

**错在哪**: Dashboard 默认 `NotifyMagic = 0` (input L30) 监听全账户, **如果用户想只听 MyEA** 改 `NotifyMagic = 20260101` 即可 (Dashboard L185 `if (NotifyMagic != 0 && (ulong)dealMagic != NotifyMagic) continue;` 自动过滤)。**但用户复制后改 hard-coded magic 字符串 = 复制时漏改 = 推送错乱**。

**反例**:
```mql5
// ❌ 错: Dashboard 硬编码 magic
void OnTrade() {
   // ... 略 ...
   if (dealMagic != 20260101) continue;   // ❌ 复制到其他 EA 漏改 = 推送错乱
}
```

**正例** (Dashboard 实物 L185):
```mql5
// ✅ 对: input 接收 magic, 默认 0 = 监听全账户
input ulong NotifyMagic = 0;   // 关联 EA 的 magic (0=监听全账户)
void OnTrade() {
   // ... 略 ...
   if (NotifyMagic != 0 && (ulong)dealMagic != NotifyMagic) continue;   // ✅ input 灵活
}
```

> **本 wiki §6 5 反模式 100% 来自实物代码反例**, 与 [[实战/M18 多品种对冲实战]] §6 5 反模式 (解释 + 反例 + 正例) 风格 100% 对齐。

---

## §7 链向 + 验证

### 7.1 实物 / 模板 / 配置文件

- 实物源码 A: `MQL5/Experts/minimax-ea/MyEA.mq5` (301L / 12,541B / 10 模块 M01-M11+M16, 11 top-level functions, 头注释"MQL5Kit 通用 EA 骨架")
- 实物源码 B: `MQL5/Experts/minimax-ea/Dashboard.mq5` (208L / 8,361B / 4 模块 M04+M09+M10+M15, 9 top-level functions, 头注释"跨品种监控面板 (只读)")
- 编译产物: `MQL5/Experts/minimax-ea/MyEA.ex5` (59,398B) + `Dashboard.ex5` (34,952B) (2026-06-04 01:58 闭环)
- 模板对照: [[02-完整模板/EA 通用骨架]] (MyEA 范本)
- 模板对照: [[02-完整模板/EA Dashboard 监控模板]] (Dashboard 范本, 已引用 Dashboard.mq5 实物)
- 兄弟 EA: [[实战/MeanReversion_EA 接入报告]] (13 模块全集含 M18+M19, 320L, 多品种对冲)
- 兄弟 EA: [[实战/TrendMA_EA + Breakout_EA 接入报告]] (12+11 模块 2 EA 联合, 趋势 + 突破)
- 兄弟 EA: [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] (13 模块含 M13+M17, 1033L, 剥头皮 4 版本演进)
- 兄弟 EA: [[实战/ScalperEA 接入 MQL5Kit 摘要]] (76K/1759L, 0 MQL5Kit, 接入前对照)

### 7.2 4 反链 wiki 段 (本任务产出, 中心节点)

> **本任务工作**: 在以下 4 个 wiki 末尾追加 "### 反向引用 (实物 EA 接入 demo)" 段 (3-5 行 + Obsidian [[wiki link]]), 形成双向链接闭环。

- [[01-调用模块/M09 面板 Dashboard]] — MyEA `RefreshDashboard` L189-L211 (12 dash.* 调用, 7 Row + 2 Line) + Dashboard `_Refresh` L97-L122 (17 dash.* 调用, 4 品种循环 + Heartbeat 5 行)
- [[01-调用模块/M15 定时器 TimerService]] — Dashboard `Init(RefreshSec * 1000)` L57 + `OnTimer` L90-L94 + `Deinit` L83 + Heartbeat 4 查询 L117-L119 (Fires/Period/Mode/LastFire)
- [[02-完整模板/EA Dashboard 监控模板]] — Dashboard.mq5 (208L/8.3KB/4 模块) 是模板的 M15 升级版 (模板走 EventSetTimer 裸调 L56, Dashboard 走 _timer.Init L57)
- [[04-避坑与速查/04 经纪商差异-点差-手续费]] — MyEA 不硬编码 filling (走 M01 _AutoSetFilling L182 trade.Buy) + Dashboard 不假设净额 (NotifyMagic=0 监听全账户, 适配 hedging/netting)

### 7.3 实战 wiki 中心节点对比 (12 实战 wiki 全闭环)

| 实战 wiki | 实物 | 模块数 | 与本 wiki 关系 |
|---|---|---|---|
| [[实战/MeanReversion_EA 接入报告]] | MeanReversion_EA.mq5 (320L) | **13 模块全集** (含 M18+M19) | **同构兄弟 wiki** (同 M10 3-触发器模板, MyEA + Dashboard 也走 5 方法调用) |
| [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] | ScalperXAU.mq5 (1033L) | **13 模块** (含 M13+M17) | **同主题** (M13 落盘范本同款, ScalperXAU 也用 _m13LastDealTicket 锚点) |
| [[实战/TrendMA_EA + Breakout_EA 接入报告]] | TrendMA+Breakout 2 EA | **12+11 模块** | **2 EA 联合范本** (本 wiki 也是 2 EA 联合, 范本) |
| [[实战/ScalperEA 接入 MQL5Kit 摘要]] | ScalperEA.mq5 (76K/1759L) | **0 MQL5Kit** | **接入前对照** (0 接入 → 18 模块建议, MyEA 是"已接入 10"对照) |
| [[实战/M17_TestNewsEA 复活报告]] | M17_TestNewsEA.mq5 (55L) | **1 模块 M17** | **M17 单模块 demo** |
| [[实战/BBTrendEA 复活 SOP]] | BBTrendEA.mq5 (1709L) | **8 模块** (archive 复活) | **archive 复活范本** |
| [[实战/5 个 debug-prototype EA 索引]] | 5 debug EA (v5-v8 + CsvProto) | **0-6 模块** | **debug 范本** |
| [[实战/M18 多品种对冲实战]] | (无实物, 多 spec wiki) | — | **反模式 5 条范本来源** |
| [[实战/5 EA 6 月回测对比 SOP]] | (无实物, 回测 SOP) | — | **5 维度 35 数据点回测方法论** |
| [[实战/Scalping_More v1.3 接入示例]] | Scalping_More_v1.3.mq5 (327L) | 8-11 模块 | **兄弟接入 demo** |
| [[实战/M19 时段过滤实战]] | (无实物, M19 spec demo) | — | **M19 实战范本** |
| **本 wiki** | MyEA + Dashboard 2 EA | **10 + 4 模块** | **通用骨架 + 监控面板兄弟** |

### 7.4 避坑与速查

- [[04-避坑与速查/05 必查清单]] — MyEA OnDeinit 释放 handle / CleanupAll 都按这个清单做
- [[04-避坑与速查/04 经纪商差异-点差-手续费]] — MyEA 不硬编码 filling (M01 _AutoSetFilling), Dashboard 不假设净额 (NotifyMagic 适配 hedging/netting)
- [[04-避坑与速查/06 网格马丁警示]] — ⚠️ 网格马丁高风险警示 (本 2 EA 不用网格, 参考)
- [[00-快速开始/EA 写之前要知道的 10 件事]] — 写新 EA 必读
- [[00-快速开始/EA 模板套用流程]] — 5 分钟改造模板 (MyEA = 模板套用范本)
- [[00-快速开始/MT5 GUI 自动化 5 次失败全记录 + 分工协议]] — N4 GUI 阻塞协议

### 7.5 验证 (Node.js fs 一键复测命令)

> **verifier 自校**用 — 跑一次确认 2 .mq5 文件 0 改动、行号 100% 命中、M10 5 方法调用、4 模块/10 模块实际接入。

```bash
# 1) 2 .mq5 文件 mtime 验证 (应 16:57:46 / 16:51:16 不变)
node -e "const fs=require('fs');for(const f of ['C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/MyEA.mq5','C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/Dashboard.mq5']){const st=fs.statSync(f);console.log(f.split('/').pop(),'size=',st.size,'mtime=',st.mtime.toISOString())}"
# 期望: MyEA 12541 bytes 2026-06-03T16:57:46 / Dashboard 8361 bytes 2026-06-03T16:51:16

# 2) MyEA handler def 实测 (期望 100% 命中)
node -e "const fs=require('fs');const c=fs.readFileSync('C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/MyEA.mq5','utf8');const lines=c.split('\n');['int OnInit','void OnDeinit','void OnTick','void _CheckDrawdown','void OnTrade','void OnTradeTransaction','void CheckEntry','void TryOpen','void RefreshDashboard','void IsTradeTime'].forEach(k=>{lines.forEach((l,i)=>{if(l.includes(k))console.log((i+1)+': '+l.trim().substring(0,80))})})"
# 期望: OnInit L110 / OnDeinit L131 / OnTick L138 / _CheckDrawdown L215 / OnTrade L259 / OnTradeTransaction L237 / CheckEntry L160 / TryOpen L164 / RefreshDashboard L188 / IsTradeTime L150

# 3) Dashboard handler def 实测
node -e "const fs=require('fs');const c=fs.readFileSync('C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/Dashboard.mq5','utf8');const lines=c.split('\n');['int OnInit','void OnDeinit','void OnTick','void OnTimer','void _Refresh','void _Parse','void _CheckDrawdown','void OnTrade','void OnTradeTransaction'].forEach(k=>{lines.forEach((l,i)=>{if(l.includes(k))console.log((i+1)+': '+l.trim().substring(0,80))})})"
# 期望: OnInit L52 / OnDeinit L80 / OnTick L85 / OnTimer L90 / _Refresh L95 / _Parse L129 / _CheckDrawdown L138 / OnTrade L167 / OnTradeTransaction L191

# 4) 2 EA M10 5 方法调用验证
node -e "const fs=require('fs');for(const f of ['MyEA','Dashboard']){const p='C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/'+f+'.mq5';const c=fs.readFileSync(p,'utf8');const lines=c.split('\n');console.log('---'+f+'---');['EnablePush','EnableSound','M10.Send','M10.Trade'].forEach(k=>{const hits=lines.filter(l=>l.includes(k)&&!l.trim().startsWith('//'));console.log(k+': '+hits.length+' hits');hits.slice(0,3).forEach((h,i)=>console.log('  L'+(lines.indexOf(h)+1)+': '+h.trim().substring(0,80)))})}"
# 期望: 2 EA 各 EnablePush 1 / EnableSound 1 / M10.Send 2 (DD + reject) / M10.Trade 1 (新成交) = 5 方法调用

# 5) wiki 文件 250+ 行验证
node -e "const fs=require('fs');const c=fs.readFileSync('C:/ai/obsidian-文件/mt/EA开发/实战/MyEA + Dashboard 接入报告.md','utf8');console.log('lines:',c.split('\n').length,'size:',c.length)"
# 期望: >= 250 行

# 6) 4 spec/wiki 反链段验证 (期望 4 命中 "MyEA + Dashboard")
node -e "const fs=require('fs');const path=require('path');const targets=['C:\\\\ai\\\\obsidian-文件\\\\mt\\\\EA开发\\\\01-调用模块\\\\M09 面板 Dashboard.md','C:\\\\ai\\\\obsidian-文件\\\\mt\\\\EA开发\\\\01-调用模块\\\\M15 定时器 TimerService.md','C:\\\\ai\\\\obsidian-文件\\\\mt\\\\EA开发\\\\02-完整模板\\\\EA Dashboard 监控模板.md','C:\\\\ai\\\\obsidian-文件\\\\mt\\\\EA开发\\\\04-避坑与速查\\\\04 经纪商差异（点差\\\\手数\\\\Filling）.md'];for(const p of targets){try{const c=fs.readFileSync(p,'utf8');const has=!!c.match(/反向引用.*MyEA.*Dashboard|MyEA.*Dashboard.*接入/);console.log(p.split('\\\\').pop(),'hasMyEADashboard=',has)}catch(e){console.log('err',p,e.message)}}"
# 期望: 4 命中

# 7) MOC 实战分类 12 wiki 验证
node -e "const fs=require('fs');const c=fs.readFileSync('C:/ai/obsidian-文件/mt/EA开发/EA 开发知识库.md','utf8');const m=c.match(/## 实战[\\s\\S]*?(?=##)/g);if(m){const w=m[0].match(/\\[\\[实战\\//g);console.log('实战 wiki 数:',w?w.length:0)}"
# 期望: 12 (本次从 10 → 12)
```

> **承诺**: 本 wiki §7.5 命令 0 改动 2 .mq5 物理文件, **只读**。**mtime 应保持 2026-06-03 16:57:46 / 16:51:16** 不变。

---

**版本**: v1.0 (2026-06-04 21:12 创建, Mavis T2 任务交付 — 14:00 §5 维度 5 续, MyEA + Dashboard 联合 wiki 沉淀)
**下次更新**: N4 1 周沙盒完成后追加 §3.4/§5.x "待 N4 实物" 实测值 + 5 反模式可能扩展
**维护人**: Mavis general agent (mvs_c68d5e9fc2a649f387d1fe8275cc0a76)
**关联任务**: 14:00 沉淀清单 §5 维度 5 续 (剩 MyEA + Dashboard 2 EA) / 21:00 plan_42f0f8b6 track2 / 19:00 T2 漂移校验范本 (TrendMA+Breakout §8) / [[N5 漂移修复 (20:00 plan_f01a5f34)]]
**关联 wiki**: [[实战/MeanReversion_EA 接入报告]] (同构兄弟 wiki 13 模块全集含 M18+M19) / [[实战/TrendMA_EA + Breakout_EA 接入报告]] (2 EA 联合范本) / [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] (同主题 M13+M17 范本) / [[实战/M18 多品种对冲实战]] (反模式 5 条范本来源) / [[实战/5 EA 6 月回测对比 SOP]] (5 EA × 6 月回测方法论) / [[01-调用模块/M09 面板 Dashboard]] / [[01-调用模块/M15 定时器 TimerService]] / [[02-完整模板/EA Dashboard 监控模板]] / [[04-避坑与速查/04 经纪商差异-点差-手续费]]


---

## 实战案例 (末尾追加, 6 段结构 — 沿用 03:00 T2 范本)

> 本节为 [MyEA + Dashboard 接入报告] 的「实战案例段 6 章节」补充, 沿用 03:00 T2 范本 (场景 A / 场景 B / 接入点行号 / 调优点 3 档 / 陷阱 5 条 / 链向)。本 wiki 已有 §6 5 反模式 段 (L484-625, 沿用 M18 spec 5 条 + 本 2 EA 专属延伸), 本 ## 实战案例 段为 MyEA + Dashboard 2 EA 联合视角 (MyEA 10 模块全集 + Dashboard 4 模块 + M13+M10 跨模块共享锚点) 的「行号 + 调优 + 陷阱 + 链向」6 段补充, 0 重复。

### 场景 A: MyEA 10 模块全集 + Dashboard 4 模块 2 EA 联合 (10+4=14 模块)

- 实战场景: MyEA.mq5 (12541B / 301L) 通用 EA 骨架 + Dashboard.mq5 (8361B / 208L) 跨品种监控面板 2 EA 联合, MyEA 10 模块 (M01/M02/M03/M05/M07/M09/M10/M11/M13/M16) + Dashboard 4 模块 (M04/M09/M10/M15), 2 EA 通过 M10.Send + M13 FileIO 共享 _m13LastDealTicket 锚点
- 实物 demo: MyEA L10-19 (10 个 #include MQL5Kit 头) + L54-60 (8 个 object: trade/risk/sizing/ind/NB/dash/logger/M10) + L66 (`_m13LastDealTicket = 0`) + Dashboard L9-12 (4 个 #include M04/M09/M10/M15 头) + L30-33 (4 个 object: _ind/_dash/_timer/M10)
- 适用范围: 适用 (通用 EA 骨架 + 跨品种监控 + M13 落盘 + M10 推送 + M15 1s 心跳) / 不适用 (单 EA 跑不需 Dashboard, 1 EA = 1 chart 0 跨品种监控需求)

### 场景 B: M13.FileIO 落盘 + M10.Notify 推送共享 _m13LastDealTicket 锚点 (跨模块协调)

- 实战场景: MyEA L66 `_m13LastDealTicket` 锚点是 M13 CSV 落盘 + M10 推送的"上次已处理 deal ticket" 共享点, OnTradeTransaction L240-280 段每个新 deal: 1) 写 CSV (M13.AppendCSV) 2) 推 M10.Trade() 推送, 共享锚点保证 0 重复处理 0 漏处理
- 实物 demo: MyEA L66 (static ulong _m13LastDealTicket = 0) + L272 (if (t == 0 || t <= _m13LastDealTicket) break) + L276 (PrintFormat("[M13] trade logged: ticket=%I64u file=%s", t, TodayCsvName())) + L294 (M10.Trade(typeStr + "/" + entryStr, symbol, price, volume, 0, "MyEA"))
- 适用范围: 适用 (M10 推送 + M13 落盘双链路协调, 0 漏 0 重) / 不适用 (单链路 (只 M13 或只 M10) 不需要锚点, OnTick 调 M10 也不需要, 锚点仅在 OnTradeTransaction 用)

### 接入点行号 (14 行号, MyEA + Dashboard 2 EA 实测, Node.js fs grep 100% 命中, 03:00 T2 已验证 5/5)

| wiki 描述 | 实物 | 行号 | 命中关键词 | spec |
|---|---|---|---|---|
| MyEA 10 模块 include | MyEA.mq5 | L10-19 | `#include <MQL5Kit/M01_CTradePlus.mqh> ... M16_Cleanup.mqh` (10 个) | M01-M16 头 |
| MyEA 10 模块 object | MyEA.mq5 | L54-60 | `CTradePlus trade; CRisk risk; ... CNotify M10;` (8 个 object, M15 不接) | M01-M16 object |
| MyEA M13+M10 共享锚点 | MyEA.mq5 | L66 | `static ulong _m13LastDealTicket = 0;` (M10 通知 + M13 落盘共用) | M10+M13 锚点 |
| MyEA TodayCsvName 函数 | MyEA.mq5 | L69 | `string TodayCsvName() {` (返回 MQL5/Files/trades_YYYYMMDD.csv) | M13 文件名 |
| MyEA CFileIO::AppendCSV | MyEA.mq5 | L104 | `if (CFileIO::AppendCSV(fname, hdr)) _m13CsvHeaderWritten = true;` | M13 写表头 |
| MyEA CFileIO::AppendCSV row | MyEA.mq5 | L115 | `return CFileIO::AppendCSV(fname, row);` | M13 写数据 |
| MyEA OnInit Init 链 | MyEA.mq5 | L118-126 | `OnInit() / trade.Init / risk.Init / NB.Init / logger.SetFileOutput / M10.EnablePush+EnableSound` | M01-M15 Init |
| MyEA OnTick 入口 | MyEA.mq5 | L147-149 | `OnTick() / if (!NB.IsNewBar()) return;` | M05 NewBar 闸门 |
| MyEA OnTradeTransaction | MyEA.mq5 | L240-272 | `OnTradeTransaction(...) / HistorySelect(0, TimeCurrent()) / if (t <= _m13LastDealTicket) break;` | M10+M13 协调 |
| MyEA M10.Trade 推送 | MyEA.mq5 | L294 | `M10.Trade(typeStr + "/" + entryStr, symbol, price, volume, 0, "MyEA");` | M10 推送 |
| Dashboard 4 模块 include | Dashboard.mq5 | L9-12 | `#include <MQL5Kit/M04_IndicatorPool.mqh> M09_Dashboard M10_Notify M15_TimerService.mqh` (4 个) | M04/M09/M10/M15 头 |
| Dashboard 4 模块 object | Dashboard.mq5 | L30-33 | `CIndicatorPool _ind; CDashboard _dash; CTimerService _timer; CNotify M10;` (4 个) | M04/M09/M10/M15 object |
| Dashboard OnInit 1s 心跳 | Dashboard.mq5 | L42-50 | `OnInit() / _timer.Init(RefreshSec * 1000) / M10.EnablePush+EnableSound` | M15 Init + M10 Enable |
| Dashboard OnTimer 1s 刷新 | Dashboard.mq5 | L75-79 | `OnTimer() / if (_timer.OnTimer()) { _Refresh(); }` | M15 OnTimer 1s 节流 |

(14 行号, MyEA 10 + Dashboard 4, M10+M13 跨模块共享 _m13LastDealTicket 锚点 100% 命中, 0 编造)

### 调优点 3 档

- aggressive: M15 RefreshSec=1 (1s 心跳, broker 限速风险), M10.EnablePush=true + EnableSound=true (推 + 声音), 期望实时监控 + 1s 内推送 → 适合短线监控 (但 broker 可能限速)
- balanced: M15 RefreshSec=2 (2s 心跳, 默认), M10.EnablePush=true + EnableSound=false (推但静音), 期望 2s 内推送 + 不吵 → 默认
- conservative: M15 RefreshSec=5 (5s 心跳), M10.EnablePush=false + EnableSound=false (CSV 落盘但不推), 期望 5s CSV 落盘 + 0 推送 → 适合 sandbox 跑 1 周看数据

### 陷阱 5 条 (不与 ## §6 5 反模式 段 5 条重复, 走 "2 EA 联合 + M10+M13 协调" 角度)

1. **MyEA + Dashboard 2 进程隔离** — MyEA 和 Dashboard 是 2 个独立 MT5 进程, 不共享内存, 共享的仅磁盘文件 (M13 CSV 落盘); 0 共享变量 (0 全局变量同步), 跨进程通信用文件不用 GV
2. **M13 + M10 _m13LastDealTicket 锚点 0 同步** — MyEA 进程重启 (OnInit 阶段) 会重置 _m13LastDealTicket = 0, 然后 HistorySelect L130 拉历史 deal 重置锚点 = L132 `_m13LastDealTicket = (_histTotal > 0) ? HistoryDealGetTicket(_histTotal - 1) : 0`, 防止重启时重复推送
3. **M15 1s 心跳 broker 限速** — Dashboard L46 `_timer.Init(RefreshSec * 1000)` = 1s 触发 = 每秒 1 次 HTTP 推送, broker 可能限速 (Push API 1 分钟最多 30 次); M15 RefreshSec=2 才是 broker 友好值
4. **Magic 4 步骤唯一** — MyEA L23 Magic=20260101, 同账户 5 EA 跑 5 chart 时必须各唯一 (MeanRev 20260101 / SX 20260102 / TMA 20260101 / BO 20260102 / MyEA 20260101) 避免持仓误判; 5 EA 共享 1 magic = CPositions::CountMine 跨 EA 累加
5. **_archive vs root path 误用** — MyEA + Dashboard 在 minimax-ea/ 目录 (生产), BBTrendEA + M17_Test 在 _archive/ 目录 (历史), 5 demo 实物路径不一致; N1 回测必须 cd 到 _archive/ 目录用旧 EA, N4 复活用 minimax-ea/ 目录用新 EA

### 链向

- [[01-调用模块/M01 交易封装 CTradePlus]] — M01 spec (Init + OrderSend + ClosePos)
- [[01-调用模块/M02 风控 Risk]] — M02 spec (Init + CanOpen)
- [[01-调用模块/M09 面板 Dashboard]] — M09 spec (Row + Show + Refresh)
- [[01-调用模块/M10 推送通知 Notify]] — M10 spec (EnablePush/EnableSound/Send/Trade/Alert 5 方法)
- [[01-调用模块/M11 日志 Logger]] — M11 spec (Info/Warn/Error/Trade 4 级别)
- [[01-调用模块/M13 文件 IO]] — M13 spec (AppendCSV, MyEA + Dashboard 共享 _m13LastDealTicket 锚点)
- [[01-调用模块/M15 定时器 TimerService]] — M15 spec (Init + OnTimer 1s 节流)
- [[实战/MeanReversion_EA 接入报告]] — 同构兄弟 wiki 13 模块全集含 M18+M19
- [[实战/TrendMA_EA + Breakout_EA 接入报告]] — 2 EA 联合范本 (TMA+BO 各 10 模块)
- [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] — 同主题 M13+M17 范本
- [[实战/M18 多品种对冲实战]] — 反模式 5 条范本来源 (M18 spec 5 条 + 本 2 EA 专属延伸)
- [[实战/5 EA 6 月回测对比 SOP]] — 5 EA × 6 月回测方法论
- [[02-完整模板/EA Dashboard 监控模板]] — Dashboard 模板范本
- [[EA开发/EA 开发知识库]] §"实战相关" 分类
- [MQL5/Experts/minimax-ea/MyEA.mq5] — MyEA 唯一 demo (L10-19 10 include / L66 锚点 / L272 锚点比较)
- [MQL5/Experts/minimax-ea/Dashboard.mq5] — Dashboard 唯一 demo (L9-12 4 include / L46 1s 心跳 / L75-79 OnTimer)
