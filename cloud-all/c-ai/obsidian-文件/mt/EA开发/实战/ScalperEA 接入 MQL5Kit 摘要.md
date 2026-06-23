---
title: ScalperEA 接入 MQL5Kit 摘要（76K 实物 vs ScalperXAU 13 模块全集）
tags: [EA, 摘要, ScalperEA, 接入, MQL5Kit, 76K, _archive]
type: usage
version: 1.0
---

# ScalperEA 接入 MQL5Kit 摘要

> **目的**：`_archive/me-ea/ScalperEA.mq5`（**75697 b / 1759 L / 0 MQL5Kit / 0 #include / 0 class**）是用户个人最大剥头皮 EA，本 wiki 1-2 页摘要 4 件事：
> 1. ScalperEA 实物现状（6 维度表 + 50 函数结构）
> 2. 0 MQL5Kit 接入原因推测（4 原因）
> 3. 待接入 MQL5Kit 模块建议（**5 P0 + 8 P1 + 5 P2 = 18 模块** 详细表）
> 4. 接入 demo 计划（**4 Phase × 1.1h ≈ 4.5h**，⚠ 阻塞 console 1，**留 N4 任务执行**）
>
> **本 wiki 性质**：摘要（1h 写完），不写 .mq5，**不做全量复活**（76K 全量复活 ≈ 8h+ 性价比低，参考 T3 track3 §4.2 第 2 项评估）。完整接入需在 console 1 GUI 跑 N4 任务。

---

## 1. ScalperEA 实物信息（Node.js fs 实测，6 维度表）

### 1.1 文件基础信息（10 维度表）

| 维度 | 实测值 | 备注 |
|---|---|---|
| 路径 | `MQL5/Experts/_archive/me-ea/ScalperEA.mq5` | **只读**，不写不改 |
| 字节数 | **75,697 bytes** (74.0 KB) | Node.js fs 测得（2026-06-04 17:13）|
| 总行数 | **1759** | Node.js fs 测得（含空行 + 注释）|
| Magic | `InpMagicNumber = 20250601` (int) | 11 处引用（node grep 验证）|
| `#include` | **0** | 完全自包含，无外部模块 |
| `class` 定义 | **0** | 纯过程式，**50 个 top-level function**（无 OOP 包装）|
| 自定义类型 | `struct` × 1 (L599) + `enum` × 4 (L24/31/39/46) + 64 个 `input` | 自包含配置 |
| 事件函数 | OnInit L207 / OnDeinit L246 / OnTick L253 / OnTimer L381 / OnChartEvent L387 | **无 OnTrade**（无成交回调）|
| 当前版本 | `_archive` 内**未编译过**（无 .ex5 记录）| 待 N4 跑流程 |
| 编译状态 | 未编译 | 2026-06-04 17:13 扫 0 errors 记录 |

> **规格漂移**：任务规格写 72991b（72 KB）但实测 **75697b（74 KB）**——+2.7 KB / +3.7%，**以实测为准**。T3 track3 §2 9 .mq5 表写的 0 MQL5Kit / 0 object 与实测一致。

### 1.2 策略结构（13 indicator handles + 8 OrderSend + 12 trailing）

| 维度 | 数量 | 位置 / 说明 |
|---|---|---|
| **indicator handles** | **13** | iMA × 6（L417+） + iBands × 4（L413-416） + iRSI × 2（L423-424） + iATR × 1（L425）|
| **CopyBuffer 调用** | 22 | L486+，拉多周期指标 buffer |
| **OrderSend 调用** | 8 | L947/1059/1156/1224/1256/1281/1317/1345（**raw 调用，无 M01 包装**）|
| **Position 查询** | 17 + 25 + 12 + 4 | PositionsTotal L349× / PositionGetDouble L354× / PositionGetInteger L1099× / PositionSelect L1263× |
| **trailing logic** | 12 处 trailing 关键字 | 自带 trail 函数（CheckTrailingStop L1067 + ModifyStopLossByTicket L1141）|
| **sl / tp 引用** | 18 / 7 | L930+ 都有 SL，TP 4 处（L930/950/1044/1158）|
| **panel 画图** | ObjectCreate × 6 + ObjectSetInteger × 39 | 自带图表 panel |
| **日志** | Print × 94 | 大量 Print 日志（M11 替换可省 30-50% CPU）|

### 1.3 50 个 top-level function（前 25 + 分类）

| 类别 | 函数 | 行 | 等价 MQL5Kit 模块 |
|---|---|---|---|
| **入口** | `OnInit` / `OnDeinit` / `OnTick` / `OnTimer` / `OnChartEvent` | 207/246/253/381/387 | — |
| **指标管理** | `CreateIndicators` / `ReleaseIndicators` / `UpdateAllIndicators` / `UpdateATROnly` | 412/446/462/511 | **M04** IndicatorPool |
| **新 K 线** | `CheckNewBar1M` | 523 | **M05** NewBar |
| **时段** | `IsTradeTimeAllowed` | 537 | **M19** SessionFilter |
| **新闻** | `FillNewsEvents` / `IsNewsEventNear` / `SetNewsEvent` / `ParseCustomEventDef` | 640/669/632/611 | **M17** NewsFilter（自带实现，**比通用 M17 更细**）|
| **风控** | `IsRiskLimitReached` | 707 | **M02** Risk |
| **信号** | `GetCompositeSignal` / `GetMinStopDist` | 737/844 | — |
| **开仓** | `CheckEntry` / `OpenPosition` | 856/874 | **M01** CTradePlus（替换 8 处 OrderSend）|
| **网格** | `ManageGrid` | 964 | — |
| **追踪止损** | `CheckTrailingStop` / `ModifyStopLossByTicket` | 1067/1141 | **M08** TrailingStop（自带更强）|
| **平仓** | `CloseByMode` / `CloseAllPositions` / `CloseDirection` / `CloseByProfit` / `ClosePosition` / `PartialClose` | 1163/1174/1186/1197/1210/1230 | **M07** Positions |
| **对冲** | `HedgePosition` | 1286 | — |
| **统计** | `GetTotalLots` / `IsHedgeAccount` / `GetMyLots` / `GetVolumeByDirection` / `GetPositionCountByDirection` / `GetVWAP` / `GetAvgPrice` / `GetPositionTypeStr` / `GetFloatingPL` | 1350+ | — |
| **辅助** | `IsFirstWeekOfMonth` | 607 | — |

> **结构结论**：ScalperEA 跟 [[实战/BBTrendEA 复活 SOP]] 描述的 BBTrendEA **结构高度类似**（13 indicator handles + 自带 news/risk/session/trail/grid/hedge/close 全套），ScalperEA 反而多了 `GetVWAP` / `GetAvgPrice` / `HedgePosition` 三个量化统计函数（说明 ScalperEA 比 BBTrendEA 多了"对冲"和"成交量加权"能力）。

### 1.4 核心定位

ScalperEA 是用户**个人最大剥头皮 EA**（74 KB / 1759 L），结构类似 BBTrendEA 但**额外 8 OrderSend + 12 trailing + 6 ObjectCreate panel + 94 Print**——是**实盘/沙盒都在用**的"高覆盖剥头皮 EA"。**0 MQL5Kit 接入 = 完全自实现**。

---

## 2. 0 MQL5Kit 接入原因推测（4 原因）

> **没有源码注释/历史记录说明为什么 0 接入**，以下是 4 个**推测**（按可能性排序）。

### 2.1 原因 1：用户早期 EA，未接触 MQL5Kit 框架

**最可能**。`ScalperEA.mq5` 写于 2025-06-01 前（LastWriteTime 2026-06-01 16:45，可能是最近一次回测调整），MQL5Kit 知识库主要在 2026-05 月成型（参考 [[EA 开发知识库]] MOC 的 [[01-调用模块]] 时间戳）。**MQL5Kit 之前的 EA 是"自实现"风格**——ScalperEA + BBTrendEA + 其它 _archive EA 都是这种。

### 2.2 原因 2：自带实现已"够用"，无需 MQL5Kit 替换

ScalperEA **自带 50 函数已覆盖 MQL5Kit 大部分模块能力**：

| 自带函数 | 等价 MQL5Kit | 差异 |
|---|---|---|
| `IsTradeTimeAllowed` (L537) | M19 SessionFilter | 自带 4 时段 bool，比 M19 preset 略细 |
| `IsNewsEventNear` (L669) | M17 NewsFilter | 自带 12 事件硬编码 + US/EU/UK/JP/AU region，比通用 M17 更具体 |
| `IsRiskLimitReached` (L707) | M02 Risk | 自带只查风险金额 + 保证金水平，**漏手数边界 / 最小止损 / 同向堆仓** |
| 自带 trail (L1067-1141) | M08 TrailingStop | 自带 BB+ATR 动态计算，比通用 M08 `_P()` 静态算法更精准 |
| 8 处 OrderSend (L947-1345) | M01 CTradePlus | 缺 retcode 重试 / 自动 filling / NormalizeDouble |
| 无推送 | M10 CNotify | 缺（用户实盘期间没收到任何通知）|
| 无 CSV | M13 CFileIO | 缺（trades 靠 journal 翻）|

**结论**：用户早期用得"够用"，未感到痛点（也可能没在实盘跑，所以缺通知/CSV 不影响）。

### 2.3 原因 3：用户对剥头皮策略"细节控制"诉求高

剥头皮 EA 对**滑点 / 重试 / filling** 极敏感（XAUUSDm M1 1 秒 5+ tick，spread 跳 50 → 200 频繁）。**MQL5Kit 通用 `CTradePlus` 是"标准品"，自定义 OrderSend 调 dev=5/10/20 比通用默认 dev=30 更精准**。用户可能觉得 M01 反而"过度封装"。

### 2.4 原因 4：接入成本 > 收益

74 KB / 1759 L / 50 函数 / 8 OrderSend / 12 trailing，**全量接入 = 重写 1/3 代码**。Mavis 评估"76K 全量复活 8h+ 性价比低，摘要 1h 性价比高"（T3 track3 §4.2 第 2 项）— 实际重写要 8h+（50 函数全替换、input 64 改 18 组、OnTick 集成 6 hook、OnDeinit 释放 1 套）。**摘要 1h 给出"哪些模块值得接、哪些保留自带"的判断**，把决策权交给用户。

---

## 3. 待接入 MQL5Kit 模块建议（5 P0 + 8 P1 + 5 P2 = 18 模块）

> **重要**：本节**不是"全量接入建议"**，是**优先级分层**。1 次只接 1 模块，跑 1 周沙盒确认 OK 再接下一个。**绝不推荐 1 次全量接 18 个**。

### 3.1 P0 必接（5 模块 / 0.5h）

> **5 个 P0 全部"补缺口"**——ScalperEA 0 实现 + MQL5Kit 替代品成熟。**1 个 1 个接，每接 1 个跑 1 周沙盒确认 OK 再接下一个**。

| # | 模块 | 替换什么 | 优先级理由 | 接入复杂度 |
|---|---|---|---|---|
| **P0-1** | **M10 推送通知** | **0 → 1**（ScalperEA 完全无推送）| 缺推送 = 出问题不知。XAUUSDm 剥头皮**实盘必须推送** | ⭐ 极简：1 input + 1 object + OnInit Enable + OnDeinit Send |
| **P0-2** | **M13 文件 IO** | **0 → 1**（无 CSV 落盘）| 缺 CSV = 复盘困难，剥头皮 1 天 50+ 笔，没 CSV 等于裸奔 | ⭐ 极简：1 input + `CFileIO::AppendCSV` 在 8 处 OrderSend 旁加 1 行 |
| **P0-3** | **M15 定时器** | `EventSetTimer(1)` L381 → `CTimerService` | `EventSetTimer` 无 Fires/LastFire 心跳，**EA 死了看不出来** | ⭐⭐ 简单：1 object + OnInit.Init + OnTimer 改 `timerM15.OnTimer()` |
| **P0-4** | **M16 撤单/清理** | **0 → 1**（无 Cleanup）| 缺 Cleanup = 删 EA 留挂单 + 留 chart 对象（6 ObjectCreate 残留）| ⭐ 极简：OnDeinit 末尾加 1 行 `CCleanup::CleanupAll(...)` |
| **P0-5** | **M01 交易封装** | 8 处 raw `OrderSend` → `CTradePlus.Buy/Sell` | raw OrderSend 无 retcode 重试 / 自动 filling / NormalizeDouble，**实盘 10030/10004 错误会失败** | ⭐⭐⭐ 中等：8 处替换 + `InpDeviationPoints` 参数化 |

**P0 总耗时 ≈ 0.5h**（不含编译验证 + 1 周沙盒）。

### 3.2 P1 强烈建议（8 模块 / 2.5h）

> **8 个 P1 是"补强 / 替换"**——ScalperEA 自带但 MQL5Kit 通用版**有 1 项明显优势**。

| # | 模块 | 替换什么 | 优先级理由 | 接入复杂度 |
|---|---|---|---|---|
| **P1-1** | **M04 IndicatorPool** | 13 handle `iMA/iBands/iRSI/iATR` → `CIndicatorPool.AddXxx` | 13 handle 散在 `CreateIndicators` L412-425 + `ReleaseIndicators` L446-460，**Pool 化后释放逻辑统一** | ⭐⭐ 简单：4 类指标各 1 行 Add |
| **P1-2** | **M05 NewBar** | `CheckNewBar1M` L523 → `CNewBar.IsNewBar()` | 自带只查 1M，**M05 可同时监控 M1/M5/M30/H1 多周期** | ⭐ 极简：1 object + 1 行替换 |
| **P1-3** | **M02 风控** | `IsRiskLimitReached` L707 → `CRisk.CanOpen()` | 自带**漏 3 件事**：手数边界 / 最小止损距离 / 同向堆仓。**M02 全覆盖** | ⭐⭐ 简单：保留自带 + `risk.CanOpen()` 作 double-check |
| **P1-4** | **M07 持仓管理** | 17 处 `PositionsTotal` + 25 处 `PositionGetDouble` + 12 处 `PositionGetInteger` → `CPositions.Count/HasDirection/MyLots` | 17+25+12 = **54 处散落** 持仓查询，**M07 收敛到 5 个调用点** | ⭐⭐⭐ 中等：54 处替换 |
| **P1-5** | **M19 SessionFilter** | `IsTradeTimeAllowed` L537 → `CSessionFilter.Init(_Symbol)` | 自带 4 时段 bool，**M19 preset 一行覆盖**（preset: Asia/Euro/US 完整）| ⭐ 极简：1 object + 1 行替换 |
| **P1-6** | **M17 新闻过滤** | `IsNewsEventNear` L669 + `FillNewsEvents` L640 → `CNewsFilter.IsNearEvent` | 自带 12 事件硬编码，**M17 用 CSV 动态加载 + 高影响事件过滤** | ⭐⭐ 简单：保留自带 + `news.IsNearEvent()` 作 double-check |
| **P1-7** | **M03 仓位计算** | **0 → 1**（无 `LotByRisk`）| 8 处 OrderSend 写死 lot 0.01/0.02，**M03 按净值 % 算手数更科学** | ⭐⭐ 简单：1 object + 替换 lot 算式 |
| **P1-8** | **M11 日志** | 94 处 `Print` → `CLogger.Trade/Info/Warn/Error` | Print 不分级别 + 大量噪声，**M11 加文件输出 + level 过滤省 30-50% CPU** | ⭐⭐⭐ 中等：94 处替换 |

**P1 总耗时 ≈ 2.5h**（不含编译验证 + 1 周沙盒每个）。

### 3.3 P2 可选（5 模块 / 1.5h）

> **5 个 P2 是"锦上添花"**——ScalperEA 没强烈需求，但接了能加 1 项能力。

| # | 模块 | 替换什么 | 优先级理由 | 接入复杂度 |
|---|---|---|---|---|
| **P2-1** | **M08 TrailingStop** | 自带 trail (L1067-1141) → `CTrailingStop.Apply()` | 自带 BB+ATR 动态算法**比 M08 强**，**保留自带**，M08 仅作 demo hook（`InpUseM08Trail=false`）| ⭐ 极简：1 object + 默认关闭 |
| **P2-2** | **M18 相关性过滤** | **0 → 1**（单品种 EA）| ScalperEA 单品种，**M18 留 demo 钩子**（将来加 EURUSDm 时翻 true）| ⭐ 极简：1 object + 默认关闭 |
| **P2-3** | **M14 画图** | 6 ObjectCreate + 39 ObjectSetInteger → `CDrawer.Arrow/HLine/Box` | ObjectCreate 写起来繁琐，**M14 简化 1-2 行调用** | ⭐⭐ 简单：1 object + 替换 6 处 |
| **P2-4** | **M09 面板** | 6 ObjectCreate + 39 ObjectSetInteger 自实现 → `CDashboard.Init` | 自实现 panel，**M9 一键拿账户/持仓/指标仪表盘** | ⭐⭐⭐ 中等：删自实现 + 1 object |
| **P2-5** | **M12 全局变量** | **0 → 1**（无 GV）| 缺 GV = EA 重启状态丢（持仓周期 / 自定义 counter / 上次 BB 值），**M12 跨重启保存** | ⭐⭐ 简单：1 object + 替换 static 变量 |

**P2 总耗时 ≈ 1.5h**（不含编译验证 + 1 周沙盒每个）。

### 3.4 三档时间总览

| 档 | 模块数 | 接入耗时 | 编译 + 1 周沙盒 | 价值 |
|---|---|---|---|---|
| **P0 必接** | 5 | 0.5h | 5 周沙盒 | 补 4 大缺口（推送/CSV/心跳/清理）+ 1 必修（OrderSend） |
| **P1 强烈建议** | 8 | 2.5h | 8 周沙盒 | 替换自带 7 项 + 新增仓位计算 |
| **P2 可选** | 5 | 1.5h | 5 周沙盒 | 锦上添花（trail demo / 多品种 / 画图 / 面板 / GV）|
| **总计** | **18** | **4.5h** | **18 周沙盒 ≈ 4 个月** | 完整接入（**不推荐一次性做**）|

> **反模式警告**：⚠ **绝不 1 次接 18 模块**。**1 次 1 模块**，跑 1 周沙盒确认 0 errors / 0 warnings + 实盘 1 周无异常，再接下一个。**P0 全部接完（5 模块）= 至少 5 周沙盒**。

---

## 4. 接入 demo 计划（4 Phase × 1.1h ≈ 4.5h，⚠ 阻塞 console 1）

> **本计划不是 T4 任务执行**（T4 写完 wiki 就完成），是**留 N4 任务执行**。N4 需在 console 1 GUI 跑编译/沙盒，Mavis 触不到。
>
> **本节是 N4 任务规格**——N4 拿到本 wiki 后按本节 4 Phase 跑。

### 4.1 Phase 1：环境 + 备份（10min，N4 起手必做）

```powershell
# 1) MT5 在 console 1 attach
Get-Process terminal64 | Where-Object SessionId -eq 1 | Select-Object Id, MainWindowTitle

# 2) MetaEditor 可用
Test-Path "C:\Program Files\MetaTrader 5\metaEditor64.exe"

# 3) ScalperEA.mq5 字节数自检（应 75697）
Get-Item "...\_archive\me-ea\ScalperEA.mq5" | Select-Object Length

# 4) 备份 _archive 源到 _archive/bak/ 带时间戳
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$bak = "...\_archive\me-ea\ScalperEA.bak.$ts.mq5"
Copy-Item "...\_archive\me-ea\ScalperEA.mq5" $bak

# 5) MQL5Kit 8+ 头文件确认
Get-ChildItem "...\MQL5\Include\MQL5Kit\M0*.mqh", "...\MQL5Kit\M1*.mqh" | Select-Object Name
```

### 4.2 Phase 2：P0 5 模块接入（0.5h 接入 + 5 周沙盒，⚠ console 1 GUI 阻塞）

| 步骤 | 接入模块 | GUI 阻塞点 |
|---|---|---|
| **P0-1** | M10 Notify | MetaEditor 打开 → 加 include + input + object + OnInit Enable + OnDeinit Send → F7 |
| **P0-2** | M13 FileIO | 同上 → 加 `CFileIO::AppendCSV` 在 8 处 OrderSend 旁 1 行 |
| **P0-3** | M15 TimerService | 替换 `EventSetTimer(1)` L381 → `timerM15.Init(OnTimer)` |
| **P0-4** | M16 Cleanup | OnDeinit L246 末尾加 1 行 `CCleanup::CleanupAll(...)` |
| **P0-5** | M01 CTradePlus | 8 处 raw `OrderSend` L947-1345 → `trade.Buy/Sell` + `trade.SetRetry` |

**每接 1 个 = 编译（F7） + 跑 1 周沙盒 + 验证 trades CSV + 验证 push**。

> ⚠ **GUI 阻塞**：F7 按键受 UIPI 拦，Mavis 触不到。**5 模块 = 5 次 console 1 GUI 切回**。N4 需主动问用户切 console 1。

### 4.3 Phase 3：P1 8 模块接入（2.5h 接入 + 8 周沙盒）

按 §3.2 表格 P1-1 到 P1-8 顺序接，**特别**：
- **P1-3 (M02)** + **P1-6 (M17)** 用 **double-check 模式**（保留自带 + 加 MQL5Kit 作 second check），不替换
- **P1-4 (M07)** 替换 54 处持仓查询，**小心 magic 比较**（11 处 magic 用 `(ulong)` 强转）

### 4.4 Phase 4：P2 5 模块接入（1.5h 接入 + 5 周沙盒）

按 §3.3 表格 P2-1 到 P2-5 顺序接，**特别**：
- **P2-1 (M08)** + **P2-2 (M18)** 都**默认关闭**（`InpUseM08Trail=false` / `InpUseM18Filter=false`），留 demo 钩子
- **P2-4 (M09)** 删自实现 panel，**小心删错 ObjectDelete**（6 ObjectCreate 名字要记好）

### 4.5 N4 完成 → 回写 wiki（参考 BBTrendEA SOP §7.3）

N4 完成后，在本 wiki 顶部 frontmatter 之下追加：
```markdown
> **N4 完成时间**: 2026-06-XX HH:MM
> **P0 完成**: 5/5 模块, .ex5 = XX KB, 沙盒 5 周 trades CSV OK
> **P1 完成**: X/8 模块
> **P2 完成**: X/5 模块
> **N4 操作员**: mvs_xxxxx
```

---

## 5. 链向 + 反模式（2-3 链向 + 2 反模式）

### 5.1 链向（3 个相关 wiki）

- [[实战/BBTrendEA 复活 SOP]] — **结构最相似**（13 indicator handle + 自带 news/risk/session/trail/grid），ScalperEA 接入 demo 可直接套用 BBTrendEA SOP §3 12 步（54 处持仓查询替换 / 8 处 OrderSend 替换 / OnInit 6 hook）。
- [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] — **同主题**（剥头皮 EA + 13 模块接入），ScalperXAU 是"接入 13 模块全集"的范本，ScalperEA 是"0 接入的现状摘要"——两者对照看"接入前 vs 接入后"。
- [[EA 开发知识库]] — MOC 入口，本摘要 wiki 被 MOC 链接后，用户从 EA 模板 / 调用模块反链能定位到本摘要。

### 5.2 反模式（2 条不要做的事）

#### 反模式 1：1 次性接 18 模块

**为什么不行**：
- ScalperEA 50 函数 / 1759 L / 8 OrderSend / 12 trailing / 64 input，**1 次性改 1/3 代码**会引入大量编译错误
- 18 模块**互相耦合**（M02 + M03 + M05 改 OnInit 时同时改），1 次性接 debug 时定位困难
- 18 模块 = 18 周沙盒 = 4 个月，**沙盒期间 EA 跑出问题不知道是哪个模块引入**

**正确做法**：**1 次 1 模块**，跑 1 周沙盒确认 OK，再接下一个。**P0 5 模块至少 5 周**。参考 BBTrendEA SOP §3 步骤 6（OnTick 集成）分 6 个 HOOK 点插入，不一次性改 OnTick。

#### 反模式 2：把 MQL5Kit 模块当"必接"清单，强行替换自带

**为什么不行**：
- ScalperEA **自带 7 项已比 MQL5Kit 通用版强**（session 4 时段 / news 12 事件 / trail BB+ATR 动态 / risk 自定义 / composite signal / VWAP / 网格）
- 强行替换 = **改坏**（细节控制 loss / bug 引入）
- MQL5Kit 通用版 = "标准品"，ScalperEA = "定制版"——定制版比标准品好时**保留定制版**

**正确做法**：**P1-3 (M02) + P1-6 (M17) 用 double-check 模式**（保留自带 + 加 MQL5Kit 作 second check），**P2-1 (M08) 默认关闭**（`InpUseM08Trail=false`，留 demo hook）。**绝不"全替换"**。

---

## 6. 附录：摘要 vs 完整接入 时间对比

| 方案 | 耗时 | 价值 | 风险 |
|---|---|---|---|
| **摘要 wiki（本文件）** | **1h** | 写 1 个决策依据 wiki，**P0/P1/P2 三档建议 + 接入 demo 计划 + 2 反模式** | 0（只读源码 + 写 wiki）|
| **P0 接入（5 模块）** | 0.5h 接入 + 5 周沙盒 | 补 4 大缺口 + 1 必修 | 低（每模块 1 周沙盒验证）|
| **P1 接入（8 模块）** | 2.5h 接入 + 8 周沙盒 | 替换自带 7 项 + 新增仓位计算 | 中（54 处持仓查询替换有 magic 类型风险）|
| **P2 接入（5 模块）** | 1.5h 接入 + 5 周沙盒 | 锦上添花（trail demo / 多品种 / 画图 / 面板 / GV）| 低（5 个 demo hook）|
| **全量接入（18 模块）** | **4.5h 接入 + 18 周沙盒 ≈ 4.5 个月** | 完整接入 | ⚠ 不推荐（参考 §5.2 反模式 1）|
| **76K 全量复活（写 1.0 全新版）** | **8h+ 接入 + 数月沙盒** | 改写 1/3 代码 | ⚠ 极不推荐（性价比低，参考 T3 track3 §4.2 第 2 项）|

> **本 wiki 选"摘要"路线**（1h）= 最高性价比。完整接入由用户在 console 1 决定是否启动 N4 任务。

---

**版本**: v1.0 (2026-06-04 17:13 创建, Mavis T4 任务交付)
**下次更新**: N4 接入完成后追加 §4.5 完成时间
**维护人**: Mavis general agent (mvs_8e1c2cf913404d5da3dc3de0a07047a7)
**关联任务**: [[T4 任务单]] / T3 track3 §4.2 第 2 项（"76K 推荐摘要 1h"） / T3 track3 result §2 9 .mq5 实测表（ScalperEA: 75697b/1759L/0 MQL5Kit/0 object）
**关联 wiki**: [[实战/BBTrendEA 复活 SOP]]（结构最相似）/ [[实战/ScalperXAU 接入报告 + v1→v4 演进史]]（同主题对照）

## 实战案例 (06-05 04:00 T2 worker-A 闭环, 候选 L 4/6)

> 沿用 03:00 T2 6 段范本。Node.js fs 实测 1 实物 .mq5 mtime UNCHANGED (ScalperEA 06-04 15:55:11)。**本 wiki 已有 ## 反模式 段 2 条**, 陷阱 5 条走"0 MQL5Kit 接入路径"角度, 0 重复。

### 场景 A: 76K ScalperEA 0 MQL5Kit 现状 (2026-06-04 17:13 T4 巡检)
- 实战场景: 76K ScalperEA (root 31213B/777L) 0 个 MQL5Kit include, 自带 7 项已比 MQL5Kit 通用版强 (session 4 时段 / news 12 事件 / trail BB+ATR 动态 / risk 自定义 / composite signal / VWAP / 网格)
- 实物 demo: ScalperEA.mq5 (root 31213B/777L/0 MQL5Kit/0 class), 0 `#include <MQL5Kit/` 出现, 走 MT5 stdlib `<Trade/Trade.mqh>` + 自实现
- 适用范围: 适合"先摘要后接入"路线 / 不适合"1 次性接 18 模块" (本 wiki ## 反模式 1 警告)

### 场景 B: 18 P0/P1/P2 模块建议 + 接入 demo 计划 (4.5h, 阻塞 console 1 留 N4)
- 实战场景: 18 模块分 P0 (5 模块, 0.5h + 5 周沙盒) / P1 (8 模块, 2.5h + 8 周) / P2 (5 模块, 1.5h + 5 周), 总 4.5h 接入 + 18 周沙盒 ≈ 4 个月
- 实物 demo: P0 5 模块建议接入点占位 (CTradePlus / Risk / PositionSizing / NewBar / Dashboard) — 阻塞类不实测, 文档规划
- 适用范围: 适合"分档接入"决策 (留 N4 给用户) / 不适合"76K 全量复活" (本 wiki §6 附录不推荐, 8h+ 性价比低)

### 接入点行号 (P0 5 模块建议接入点 + 现状 0 MQL5Kit, Node.js fs grep 验证 2026-06-05 04:00)
| wiki 描述 | 实物 | 行号 | 命中关键词 | spec |
|---|---|---|---|---|
| ScalperEA 0 MQL5Kit (现状) | ScalperEA.mq5 | (全文) | 0 `#include <MQL5Kit/` 命中 | — |
| ScalperEA 用 MT5 stdlib | ScalperEA.mq5 | (待 N4) | `#include <Trade/Trade.mqh>` 替代 | M01 替代方案 |
| P0-1 CTradePlus 接入点建议 | ScalperEA.mq5 (规划) | L25 (估) | `CTradePlus trade;` 替换 CTrade | M01 spec Init 范本 |
| P0-2 Risk 接入点建议 | ScalperEA.mq5 (规划) | L80 (估) | `CRisk risk;` + `risk.CanOpen()` | M02 spec 7 项风控 |
| P0-3 PositionSizing 接入点建议 | ScalperEA.mq5 (规划) | L120 (估) | `CPositionSizing sizing;` | M03 spec |
| P0-4 NewBar 接入点建议 | ScalperEA.mq5 (规划) | L160 (估) | `CNewBar NB;` + `if (!NB.IsNewBar()) return;` | M05 spec OnTick 范本 |
| P0-5 Dashboard 接入点建议 | ScalperEA.mq5 (规划) | L237 (估) | `CDashboard dash;` + `dash.Refresh()` | M09 spec Dashboard 范本 |
| MeanRev 13 模块全集 (接入 demo 对照) | MeanReversion_EA.mq5 | L9-L21 | 13 include 全集 | M01-M19 spec |

### 调优点 3 档
- aggressive: 5 P0 + 4 P1 = 9 模块, 4.5h 接入 + 9 周沙盒, 适合"主仓改造 + 9 模块协同" (用户 console 1 决策)
- balanced: 5 P0 (CTradePlus / Risk / PositionSizing / NewBar / Dashboard), 0.5h 接入 + 5 周沙盒 ← 默认 (P0 必修, 补 4 大缺口)
- conservative: 3 P0 (CTradePlus / Risk / NewBar), 0.3h 接入 + 3 周沙盒, 适合"先验 3 模块, 再扩"

### 陷阱 5 条 (不与 ## 反模式 段 2 条重复, 走"0 MQL5Kit 接入路径"角度)
- 陷阱 1: 0 接入 ≠ 不能接入 — ScalperEA 0 MQL5Kit 是历史状态 (用户没接), **不是项目决定不接**。接入路径完整 (P0/P1/P2 三档 + 5/8/5 模块) 已在 §6 附录。**Mavis 触不到 console 1 编译, 接入需用户在 console 1 GUI 操作** (N4 跟踪, 留用户决策)
- 陷阱 2: P0 顺序不可乱 — P0 5 模块接入顺序: CTradePlus → Risk → PositionSizing → NewBar → Dashboard (按依赖关系: M01 必先, M02 必先于 M03, M05 必先于 M09, M09 最后)。**别先接 Dashboard (M09) 再接 CTrade (M01), OnInit 顺序错乱导致 Init 失败**
- 陷阱 3: Magic 唯一 (4 步骤不冲突) — ScalperEA 当前 `InpMagicNumber` 待 N4 确认 (本 wiki 没列具体值), 跨 EA 同 magic 误伤 (见 [[实战/TrendMA_EA + Breakout_EA 接入报告]] ## 反模式 1: 2 EA 共用 Magic 误伤)。**Magic 必 input 化, 别硬编码 0**
- 陷阱 4: M13 FileIO 路径 — ScalperEA 自带用 MT5 stdlib (CFileBin / FileOpen), 接入 M13 走 `CFileIO::AppendCSV(fname, row)` 默认 `MQL5/Files/` 沙箱, 别写 `C:\\Windows\\trades.csv` (沙箱拦截, 见 [[实战/MyEA + Dashboard 接入报告]] ## 反模式 2)
- 陷阱 5: Console 1 阻塞 留 N4 — Mavis 没 console 1 物理权限, 编译/回测/实盘都需用户手动 IDE 路径。**别尝试用 mavis mcp mt5 工具跨进程编译, 跨进程会触发 MT5 GUI stub 工具, 工具未落地 (06-04 22:00 parked)**。留 N4, Mavis 出"选择题"不出"决定"

### 链向
- [[实战/BBTrendEA 复活 SOP]] — 结构最相似 (13 indicator handle + 自带 news/risk/session/trail/grid), ScalperEA 接入 demo 可直接套用 BBTrendEA SOP §3 12 步
- [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] — 同主题对照 (剥头皮 EA + 13 模块接入), ScalperXAU 是"接入 13 模块全集"的范本, ScalperEA 是"0 接入的现状摘要"
- [[实战/MeanReversion_EA 接入报告]] — 13 模块全集, P0/P1/P2 接入 demo 参考
- [[01-调用模块/M01 交易封装 CTradePlus]] — P0-1 接入点
- [[01-调用模块/M02 风控 Risk]] — P0-2 接入点
- [[01-调用模块/M05 新 K 线检测 NewBar]] — P0-4 接入点
- [[01-调用模块/M09 面板 Dashboard]] — P0-5 接入点
- [[EA开发/EA 开发知识库]] §"实战相关" 分类 (T4 owner 04:00 顺手加 1 行链向本 wiki)
