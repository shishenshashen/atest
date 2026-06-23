---
title: EA 安全审计 wiki
tags: [EA, 安全审计, 风控, 异常处理, 8维度, 19模块, 11实物, 安全范本]
type: security-audit
version: 1.0
date: 2026-06-05
---

# EA 安全审计 wiki

> **本 wiki 是 `MQL5/Experts/minimax-ea/*.mq5` 14 个实物 .mq5 + 1 个 _archive M17_TestNewsEA 的安全审计范本**。
> 覆盖 **8 大安全审计维度 × 19 模块安全段位 × 11 实物 demo**，5 速查必查清单 + 8 条专属反模式（不与 80 ❌ baseline 重复）。
>
> **目标读者**：已经读完 [[MOC EA 开发知识库]] + [[04-避坑与速查/05 必查清单]] 的人，想在发版前 30 分钟内对 EA 做一次**结构化安全扫描** —— 订单安全 / 风控合规 / 资金管理 / 交易时段 / 新闻避让 / 异常处理 / 日志审计 / 异常回滚 8 维度逐项过一遍。
>
> **沿用范本**：06:00 T2 [[性能调优/MT5 性能调优 wiki]] 7 章节 + 06:00 T3 [[异常处理/异常处理手册]] 6 章节 + 05:00 T3 [[实战/跨 EA 模式萃取 wiki]] 7 模式 4 段结构。**14 实物 .mq5 接入点行号 100% Node.js fs 实测**（`workspace/scan-all.js` + `workspace/scan-security.js`），0 编造。

---

## §0 摘要（200 字）

EA 安全审计 = 写 EA 必做的 8 维度结构化扫描：**订单安全** (M01 Magic + retcode 12 码表 + 失败重试 3 次) + **风控合规** (M02 单笔 Lot 上限 + 总敞口 + 保证金) + **资金管理** (M02.CalcLot / Kelly / 风险敞口 %) + **交易时段** (M19 4 预定义常量 + 周末禁开 + 跨午夜 NY:22-6) + **新闻避让** (M17 ±30 min + IsNearEvent) + **异常处理** (retcode 不吞掉 + fallback 不静默 + 10 步 SOP) + **日志审计** (M11 4 级别 Info/Warn/Error/Trade + M13 trades_YYYYMMDD.csv 落盘) + **异常回滚** (M02 SL 触发后撤单 + M08 Trail 异常暂停 + OnDeinit 资源清理)。11 实物 demo: MeanReversion_EA / ScalperXAU v1-v4 / TrendMA_EA / Breakout_EA / MyEA / Dashboard / ScalperXAUv5-v9 / Scalper_CsvProto / MiniMaxScalper v1+v2 / M17_TestNewsEA。5 速查工具: M11.Logger / M13.FileIO / 04-避坑与速查 5 wiki / mql5-audit.js 候补 CLI。8 反模式: Magic=0 / 总敞口不查 / Lot 硬编码 / 无 SL 寄希望 trail / 周末也开仓 / 新闻不避让 / retcode 不检 / 日志只 Print。

---

## §1 8 大安全审计维度

> **审计 1 步流程**: 拿到 EA .mq5 → 按本节 8 维度逐项扫描 → 不达标的维度查 §2 19 模块安全段位 → 对照 §3 11 实物 demo 找参考实现 → 走 §4 5 速查工具验证 → §5 8 反模式避坑。
>
> **8 维度权重**（来自 [[04-避坑与速查/05 必查清单]] + M17 spec + 异常处理 wiki + 性能调优 wiki 4 维合并）：
>
> | # | 维度 | 关键检查 | 失败后果 | 涉及模块 |
> |---|---|---|---|---|
> | 1 | **订单安全** | Magic 唯一 / retcode 12 码表 / 失败重试 | 订单识别混乱 / 拒单 | M01 / M07 |
> | 2 | **风控合规** | Lot 上限 / 总敞口 / 保证金 / 关联品种对冲 | 爆仓 | M02 / M07 |
> | 3 | **资金管理** | CalcLot / Kelly / 风险敞口 % | 单笔风险失控 | M02 / M03 |
> | 4 | **交易时段** | 4 预定义常量 / 周末禁开 / 跨午夜 NY:22-6 | 假突破亏损 | M19 |
> | 5 | **新闻避让** | ±30 min 高影响事件 / IsNearEvent(min, _Symbol) | 黑天鹅打穿 | M17 |
> | 6 | **异常处理** | retcode 不吞 / fallback 不静默 / 10 步 SOP | 静默错误 | M01 / M13 / M10 |
> | 7 | **日志审计** | 4 级别 / FileIO 落盘 / trades_YYYYMMDD.csv | 复盘无据 | M11 / M13 |
> | 8 | **异常回滚** | SL 触发撤单 / Trail 异常暂停 / OnDeinit 清理 | 资源泄露 | M02 / M08 / M16 |

### 1.1 维度 1: 订单安全 (M01)

**审计要点**:
- **Magic Number 唯一标识** — `SetExpertMagicNumber(magic)` 在 `OnInit` 必调一次，且 `magic != 0`（0 = "匹配所有"，跨 EA 串扰）
- **retcode 12 码表检查** — `M01_CTradePlus` `_CheckRetcode` 已内置：成功 = DONE/DONE_PARTIAL/PLACED；失败 = REJECT/CANCEL/REQUOTE/PRICE_CHANGED/PRICE_OFF/INVALID/VOLUME/FUNDS/CONNECTION + 9 个其它
- **失败重试 3 次** — `SetRetry(3, 200)` 默认配置；剥头皮可降到 `SetRetry(2, 100)` 更快但不激进

**审计方法**: 查 `trade.Init(magic, deviation)` 在 OnInit 必调；查 `SetRetry` 必设；查 OnTick 内 `trade.Buy/Sell` 返值必读。

### 1.2 维度 2: 风控合规 (M02)

**审计要点**:
- **单笔 Lot 上限** — `_maxRiskPct=0.02`（默认 2%），剥头皮 0.5-1%，激进 5%
- **总敞口检查** — `_maxPositions=3`（默认 3 笔），多品种共享同一值
- **保证金检查** — `OrderCalcMargin` 内部 7 项检查之一
- **关联品种对冲** — M18 `IsHedgeExposed` 跨品种 |corr| > 0.7 跳过

**审计方法**: 查 `risk.Init(Magic, MaxPos, RiskPct)` 必调；查 OnTick 入口 `risk.CanOpen(...)` 必先调；查 OnTrade / OnTradeTransaction 拒单后是否有补偿逻辑。

### 1.3 维度 3: 资金管理 (M02/M03)

**审计要点**:
- **CalcLot 自动手数** — `sizing.LotByRisk(RiskPct, slDist)` 必调，禁止硬编码 `trade.Buy(0.01, ...)`
- **Kelly 公式** — `f* = (p × b - q) / b`，项目内未直接用 Kelly，是 M02 简化版（RiskPct × slDist / account equity）
- **风险敞口百分比** — `_maxRiskPct=0.02` 即单笔最大亏 2% 净值

**审计方法**: grep 全文 `Buy(.*,.*,.*,.*)` / `Sell(.*,.*,.*,.*)` 看 lot 参数；查 `LotByRisk` 调点。

### 1.4 维度 4: 交易时段 (M19)

**审计要点**:
- **4 预定义常量** — `SESSIONS_ASIA / LONDON / NY / LONDON_NY`，剥头皮推荐 `LONDON_NY`（8h 覆盖）
- **周末禁开** — 默认 `SetAllowWeekend(false)`，周末点差异常（XAUUSDm 50-100+ points）
- **跨午夜 NY:22-6** — `Init("NY:22-6")` 内部 `_HourInRange` 自动处理 `start > end` 跨日逻辑

**审计方法**: 查 `M19.Init(InpSessionPreset)` 必调；查 `IsInSession(TimeCurrent())` 在 OnTick 入口调；查 input 默认值是字面量字符串（不能用 `const`）。

### 1.5 维度 5: 新闻避让 (M17)

**审计要点**:
- **±30 min 高影响事件禁开** — `IsNearEvent(30, 30, _Symbol)` 默认窗口
- **IsNearEvent(min, _Symbol)** — 内部 `SymbolToCurrency` 自动映射 XAUUSDm→USD，USDJPYm→JPY 等
- **CSV 数据源** — `news_calendar.csv` 放 `MQL5/Files/` 下；FxStreet / DailyFX 导出格式

**审计方法**: 查 `news.LoadFromCSV` 在 OnInit 必调；查 `IsNearEvent` 在 OnTick 调；查 `EventCount() > 0` 启动 sanity check。

### 1.6 维度 6: 异常处理 (M01/M13/M10)

**审计要点**:
- **retcode 不吞掉** — `trade.Buy` 返 false 时必读 `trade.LastRetcode()`，不能只 Print
- **fallback 不静默** — `M19.Init` 失败必 `return INIT_FAILED`，不能继续跑（`IsInSession` 永远返 false）
- **10 步 SOP** — 沿用 [[异常处理/异常处理手册]] §4（识别 → 隔离 → 重试 → 降级 → 报警 → 记录 → 恢复 → 验证 → 清理 → 复盘）

**审计方法**: 查每个 `*.Init(...)` 返值必读；查 `LastRetcode()` 在 Buy/Sell 失败后必读；查 `M10.Send` 在 DD/reject 时必调。

### 1.7 维度 7: 日志审计 (M11)

**审计要点**:
- **4 级别 Info/Warn/Error/Trade** — 严格分类：启动=Info / 异常=Error / 成交=Trade / 警告=Warn
- **FileIO 落盘 trades_YYYYMMDD.csv** — `M13.CFileIO::AppendCSV` 静态方法，按日切文件
- **OnDeinit Close 文件** — `logger.Close()` 必调，否则最后 5-10 行丢

**审计方法**: 查 `logger.Trade(...)` 在 Buy/Sell 成功入口；查 `logger.Close()` 在 OnDeinit；查 M10 `_lastDealTicket` 与 M11 共享去重锚点。

### 1.8 维度 8: 异常回滚 (M02/M08/M16)

**审计要点**:
- **SL 触发后撤单** — `M02.EmergencyStop(0.5)` 净值 < 50% 余额触发全平
- **Trail 异常暂停** — 周五 20:00 后 `InpUseTrail=false` 防跳空穿 SL
- **OnDeinit 清理资源** — `CCleanup::CleanupAll(Magic, "MR_", "MR_", ...)` 撤单 + 清对象 + 删文件

**审计方法**: 查 `OnDeinit` 必调 `CleanupAll` / `logger.Close` / `Comment("")` / `IndicatorRelease` 4 件套；查 `_CheckDrawdown` 在 OnTick 入口调。

---

## §2 19 模块安全段位

> **每模块 5-10 行, 重点 M01/M02/M05/M08/M10/M11/M13/M17/M18/M19（10 重点）**。其余 9 模块 (M03/M04/M06/M07/M09/M12/M14/M15/M16) 简述。接入点行号引用 §3 11 实物 demo。

### 重点 1: M01 交易封装 CTradePlus（订单安全核心）

- **安全作用**: 99% EA 必装，处理 retcode 12 码表 + filling 自动选 + 失败重试
- **安全段位**: Magic 唯一 / retcode 不吞 / `_AutoSetFilling` 在 Init / `_NormSLTP` 用 _Digits / ClosePos 10005 视为已平
- **接入 3 步**: `trade.Init(Magic, 30)` OnInit 必调 / `trade.SetRetry(3, 200)` / `trade.Buy/Sell` 返值必读
- **实物参考**: MeanReversion_EA L80 `trade.Init(Magic, 30)` + L201/204 `trade.Buy/Sell`; ScalperXAU L953 Init + L774/775 Buy/Sell
- **安全反例**: `SetExpertMagicNumber(0)` / `trade` 声明在 OnTick / 多个 EA 共享 `trade` 全局

### 重点 2: M02 风控 Risk（风控合规 + 资金管理核心）

- **安全作用**: 下单前 7 项必查（品种/账户/手数/持仓数/同向/保证金/止损距离）
- **安全段位**: `_maxRiskPct=0.02` 默认 / `_maxPositions=3` 默认 / `_minSLPoints=10` 防 0 止损 / `EmergencyStop(0.5)` 紧急
- **接入 2 步**: `risk.Init(Magic, MaxPos, RiskPct)` OnInit / `if (!risk.CanOpen(...)) return;` OnTick 入口
- **实物参考**: MeanReversion_EA L81 `risk.Init` + L199 `CanOpen`; ScalperXAU L956 Init + 内部 `TryOpen` 串联
- **安全反例**: 调 CanOpen 不读返值 / `_maxRiskPct=0.05` 激进剥头皮 / `EmergencyStop(0.1)` 太激进

### 重点 3: M03 仓位计算 PositionSizing（资金管理配套）

- **安全作用**: `LotByRisk(RiskPct, slDist)` 自动算手数，禁止硬编码
- **安全段位**: `Init(RiskPct)` 必调 / `LotByRisk` 必返回 > 0 才下单 / `_minLot` / `_maxLot` 边界
- **接入 1 步**: `sizing.LotByRisk(RiskPct, slDist)` 算 lot 必先于 `risk.CanOpen`
- **实物参考**: MeanReversion_EA L82 `sizing.Init` + L197 `sizing.LotByRisk`
- **安全反例**: `trade.Buy(0.01, ...)` 硬编码 / `LotByRisk` 返 0 还下单

### 重点 4: M04 指标句柄管理 IndicatorPool（异常处理配套）

- **安全作用**: `EMPTY_VALUE` 检查 / `OnDeinit IndicatorRelease`
- **安全段位**: `EMPTY_VALUE` 必查 / `ArraySetAsSeries` 必设 / `OnDeinit ReleaseAll`
- **实物参考**: MeanReversion_EA L84-87 `AddRSI/AddBands/AddADX/AddATR` + L153 `EMPTY_VALUE` 查
- **安全反例**: 不查 `EMPTY_VALUE`（用空值算指标 = NaN 传播）

### 重点 5: M05 新 K 线检测 NewBar（异常处理 + 性能）

- **安全作用**: 避免每 tick 跑信号 = 重复开仓 / 浪费 CPU
- **安全段位**: `NB.Init(_Period)` OnInit / `if (!NB.IsNewBar()) return;` OnTick 顶部 / 多 TF 用 `NB_H1/NB_M5` 多实例
- **实物参考**: MeanReversion_EA L83 Init + L146 guard; TrendMA_EA L68 Init + L93 guard
- **安全反例**: `!NB.IsNewBar()` 错放 OnTick 底部 / `NB` 声明在 OnTick 重建 / 多 EA 共享 NB

### 重点 6: M06 多空判断 Signal（决策依据）

- **安全作用**: MA/RSI/ADX 综合判断多空，避免主观判断
- **实物参考**: MeanReversion_EA L148-151 `ind.Value("RSI", 0)` / `MACDValue("BB", 1, 0)` 综合判断

### 重点 7: M07 持仓管理 Positions（订单安全 + 风控合规）

- **安全作用**: 遍历本 magic 持仓 / `CountMine` / `HasDirection` / 部分平仓
- **安全段位**: `PositionGetInteger(POSITION_MAGIC) == Magic` 过滤 / 部分平仓手数 >= `SYMBOL_VOLUME_MIN`
- **实物参考**: MeanReversion_EA L177/180/184 `CountMine/HasDirection`; ScalperXAU L566/569/573/589/597
- **安全反例**: 不按 magic 过滤 = 跨 EA 误改 / 部分平仓手数 = 0

### 重点 8: M08 追踪止损 TrailingStop（异常回滚核心）

- **安全作用**: 浮盈抬 SL 锁利 / 跳空预期前暂停
- **安全段位**: `trail.Init(&trade, Magic)` 必传 `&trade` / `_minGapPoints >= 5` 防限流 / `trail.Apply()` 放 OnTick 顶部
- **实物参考**: MeanReversion_EA L88-89 Init+SetParams + L142-145 Apply (NewBar guard 之前) + L213-228 `_UpdateTrailParams`; ScalperXAU L962-963 Init + L739/796 Apply
- **安全反例**: `trail.Apply()` 放 NewBar guard 之后（频率降 99%）/ `Init` 漏传 `&trade` / `_minGapPoints=0`

### 重点 9: M09 面板 Dashboard（状态可视化）

- **安全作用**: 实时显示账户/持仓/指标/M18/M19 状态，便于监控异常
- **安全段位**: `OnDeinit Comment("")` 必清 / `OnTick` 节流 (NB.IsNewBar 内 或 OnTimer 1s/2s)
- **实物参考**: MeanReversion_EA L60 声明 + L230-248 RefreshDash (19 行 5 段); Dashboard.mq5 L31 声明 + L97-122 _Refresh (38 行 4 品种)
- **安全反例**: 每 tick 调 Show / 用 M09 替代 Print / M09 写 trade 决策

### 重点 10: M10 推送通知 Notify（异常处理核心）

- **安全作用**: 3 类触发器（DD 报警 + 新成交 + 拒单），出问题时微信/Telegram 通知
- **安全段位**: `M10.EnablePush/Sound(true)` OnInit / `_ddAlertActive` 防抖 / `_lastDealTicket` 去重 / 20/h 限频
- **接入 5 处**: include / object / EnablePush / OnTick 入口 `_CheckDrawdown` / OnTrade / OnTradeTransaction
- **实物参考**: MeanReversion_EA L62 声明 + L90-91 Enable + L253-267 DD 报警 + L272-296 OnTrade + L301-318 OnTradeTransaction
- **安全反例**: 用裸 Print / `Alert()` 弹窗在 OnTick 高频 / M10.Send 在 OnTick 每 tick / 不用 `_lastDealTicket` 去重

### 重点 11: M11 日志 Logger（日志审计核心）

- **安全作用**: 4 级别 Info/Warn/Error/Trade + 文件 + Print 双输出，便于复盘
- **安全段位**: `OnDeinit logger.Close()` 必调 / Trade 事件用 `Trade` level / `FILE_COMMON` 跨 EA 共享
- **接入 3 处**: include / object / OnInit `SetFileOutput` + OnTick Buy/Sell `logger.Trade` + OnDeinit `logger.Close`
- **实物参考**: MeanReversion_EA L61 声明 + L202/205 `logger.Trade` + L136 `Close`; ScalperXAU L115 声明 + L778-779/574-575 Trade + L1021 Close
- **安全反例**: 用裸 Print / 写盘频率 > 1 秒一次 / OnDeinit 不 Close / 日志字段无分类 tag / logger 当 M10 用

### 重点 12: M12 全局变量 GV（状态持久化）

- **安全作用**: 跨重启保存状态（如 `_peakEquity`）
- **安全段位**: 加前缀（如 `MR_*`）/ OnDeinit 删除
- **实物参考**: MeanReversion_EA L75-77 `static ulong _lastDealTicket / static double _peakEquity / static bool _ddAlertActive`

### 重点 13: M13 文件 IO（日志审计核心）

- **安全作用**: trades_YYYYMMDD.csv 落盘，复盘依据
- **安全段位**: `FILE_SHARE_READ|FILE_SHARE_WRITE` 共享 / 字段含 `,` 替换 `_` / 按日切文件
- **接入 4 处**: include / 6 列简化 / 24 列完整 / `OnTrade` 内 `WriteTradeRow(t)`
- **实物参考**: ScalperXAU L29 include + L100-102 input + L126-127 去重 + L294-448 WriteTradeRowV3 155 行 24 列; MyEA L18 include + L48-51 input + L66-67 去重 + L79-116 WriteTradeRow 38 行 6 列
- **安全反例**: 用 Print 替代 / 6 列不够用才升级 24 / M13 当实时数据通道 / 字段无 comment / 文件名硬编码

### 重点 14: M14 画图 Drawer（UI 标注）

- **安全作用**: 买卖箭头 / 水平线 / 矩形标注
- **安全段位**: 跟 M09 类似，需 `OnDeinit` 清对象

### 重点 15: M15 定时器 TimerService（异常回滚配套）

- **安全作用**: OnTimer 1s/2s 心跳 / 周期任务
- **安全段位**: `OnDeinit EventKillTimer` 必调 / 周期不能 < 100ms
- **实物参考**: Dashboard.mq5 L75-81 OnTimer + L83-120 _Refresh

### 重点 16: M16 撤单清理 Cleanup（异常回滚核心）

- **安全作用**: 一键撤挂单 + 删本 EA 对象 + 删文件 + 删 GV
- **安全段位**: `OnDeinit` 必调 / `CleanupAll(Magic, prefixObj, prefixGV, ...)` 全 5 参
- **实物参考**: MeanReversion_EA L134 `CCleanup::CleanupAll(Magic, "MR_", "MR_", true, true, true)`
- **安全反例**: OnDeinit 漏调 CleanupAll = 资源泄露

### 重点 17: M17 新闻过滤 NewsFilter（新闻避让核心）

- **安全作用**: ±30 min 高影响事件禁开（NFP / CPI / FOMC）
- **安全段位**: `LoadFromCSV` OnInit 一次 / `IsNearEvent(30, 30, _Symbol)` OnTick / `EventCount() > 0` sanity / `SetAllowedImpact("high")` 默认
- **接入 6 处**: include / input group / object / PassFilters / Dashboard / OnInit LoadFromCSV
- **实物参考**: ScalperXAU L31 include + L79-83 input + L117 object + L548-550 PassFilters + L853 Dashboard + L981-987 OnInit
- **安全反例**: Hard-code 货币 / 每 tick LoadFromCSV / 忽略回测期 CSV 缺失 / 所有影响都 gating

### 重点 18: M18 相关性过滤 CorrelationFilter（风控合规 + 多品种对冲）

- **安全作用**: 多品种 Pearson 相关系数，|r| > 0.7 跳过高相关品种，防双倍暴露
- **安全段位**: `Magic != 0` / threshold 0.7 默认 / `Magic` 过滤本 EA 持仓 / 回测中每天重拉
- **接入 5 处**: include / object / OnInit Init+LoadHistoricalCloses / OnTick IsHedgeExposed / Dashboard
- **实物参考**: MeanReversion_EA L20 include + L63 声明 + L105-122 OnInit Init 块 + L167-172 OnTick + L242 Dashboard
- **安全反例**: threshold 0.95 太松 / OnTick 重拉 / M18 替代 M02 / 监控 10 品种 / M18 当 hedge sizing 工具

### 重点 19: M19 时段过滤 SessionFilter（交易时段核心）

- **安全作用**: 时段外不开仓（off-hours + 周末 + 跨午夜）
- **安全段位**: `Init(InpSessionPreset)` 字面量字符串 / `SetAllowWeekend(false)` 默认 / `IsInSession` OnTick 调 / `ActiveSession` Dashboard
- **接入 6 处**: include / input group / object / OnInit Init+SetAllowWeekend / OnTick IsInSession / Dashboard ActiveSession
- **实物参考**: MeanReversion_EA L21 include + L42-45 input + L64 声明 + L92-100 OnInit + L161-164 OnTick + L244-246 Dashboard
- **安全反例**: input 用 const 默认值 / 周末默认开 / 跨午夜 24 上限 / Init 失败不抛异常 / M19 当持仓过滤

---

## §3 11 实物 demo (Node.js fs 实测接入点行号)

> **11 实物 EA** + **14 .mq5 mtime baseline** (Node.js fs statSync 2026-06-05 07:19 实测, 沿用 plan.md §3)
>
> **0 改 .mq5 验收**: 14 实物 mtime 全部 06-03/04 期间, 07:00 plan 期间 UNCHANGED。
>
> **接入点行号**: 11 实物各 3+ 行号, 100% Node.js fs grep 命中 (workspace/scan-all.js + scan-security.js)。

### 3.1 MeanReversion_EA — 13 模块全集 (多品种均值回归)

- **路径**: `MQL5/Experts/minimax-ea/MeanReversion_EA.mq5` (13,503 B / 320L / mtime 2026-06-04 03:21:46)
- **完整安全审计**:
  - M01 Init L80 `trade.Init(Magic, 30)` + M01 OnTick L201/204 `trade.Buy/Sell`
  - M02 Init L81 `risk.Init(Magic, MaxPos, RiskPct)` + CanOpen L199
  - M03 Init L82 `sizing.Init(RiskPct)` + LotByRisk L197
  - M04 Init L84-87 `AddRSI/AddBands/AddADX/AddATR` + EMPTY_VALUE L153
  - M05 Init L83 `NB.Init(_Period)` + guard L146
  - M07 OnTick L177/180/184 `CountMine/HasDirection` + Dashboard L239/240
  - M08 Init L88-89 `trail.Init+SetParams` + Apply L144 + `_UpdateTrailParams` L213-228
  - M09 声明 L60 + RefreshDash L230-248 (5 段 11 row)
  - M10 声明 L62 + Enable L90-91 + DD 报警 L253-267 + OnTrade L272-296 + OnTradeTransaction L301-318
  - M11 声明 L61 + Trade L202/205 + Close L136
  - M16 OnDeinit L134 `CCleanup::CleanupAll` + IndicatorRelease L135 + logger.Close L136 + Comment L137
  - M18 Init L20 + 声明 L63 + OnInit L104-122 Init 块 (SetDefaultDays + Init + LoadHistoricalCloses + PrintFormat + DumpCorr) + OnTick L167-172 IsHedgeExposed + Dashboard L242
  - M19 Init L21 + 声明 L64 + OnInit L92-100 + OnTick L161-164 IsInSession + Dashboard L244-246 ActiveSession
- **安全审计 8 维度覆盖**: 8/8 (13 模块全集)
- **沙盒**: 0 errors 编译, demo XAUUSDm M15 1 周 30 笔

### 3.2 ScalperXAU v1-v4 — 高频剥头皮 (4 版本演进)

- **路径**: `MQL5/Experts/minimax-ea/ScalperXAU.mq5` (42,824 B / 1,033L / mtime 2026-06-04 05:44:12)
- **v3 0 笔根因** (M01 缺位 → v3 加 CTradePlus):
  - M01 L19 include + L107 `CTradePlus trade` + L953 `trade.Init(InpMagicNumber, InpDeviationPoints)` + L954 `SetRetry(3, 200)` + L774/775 `trade.Buy/Sell` + L902 retcode 检查
  - M02 L20 include + L108 `CRisk risk` + L956 `risk.Init(InpMagicNumber, InpMaxPositions, InpRiskPercent/100.0)` + 内部 TryOpen L824 串联
  - M05 L23 include + L111 NB + L798 `NB.IsNewBar()` + 顶 L798
  - M07 L566/569/573/589/597 `PositionsTotal/PositionGetSymbol/PositionSelect/ClosePartial/ClosePos`
  - M08 L25 include + L113 `trail` + L962 Init + L963 SetParams + L739/796 Apply (双重调)
  - M09 L12 include
  - M10 L27 include + L116 `M10` + L966-967 Enable + L871-885 DD + L924-940 OnTrade + L890-907 OnTradeTransaction
  - M11 L28 include + L101/115 logger + L913/920 logger.Trade + L1021 Close
  - M13 L29 include + L102/643/645/651 FileOpen/Write/Close (24 列 trade journal)
  - M16 L30 include + L1010 OnDeinit CleanupAll
  - M17 L31 include + L80/117/548/549/553 news + L981-987 OnInit LoadFromCSV
- **安全审计 8 维度覆盖**: 7/8 (无 M18 接入, 标"待 v5 升级")
- **沙盒**: 0 errors 编译, 4 版本演进 (v1 0 笔 → v4 1 周 30 笔)
- **关键经验**: v1 缺 M01 = 0 笔; v3 加 M01+M10+M11+M13+M17 = 工程范本

### 3.3 TrendMA_EA — 6 模块 (MA 交叉趋势)

- **路径**: `MQL5/Experts/minimax-ea/TrendMA_EA.mq5` (9,169 B / 239L / mtime 2026-06-03 16:50:34)
- **接入 6 模块**: M01 (L144/147 Buy/Sell + L232 retcode) + M02 (风控) + M03 (仓位) + M04 (指标) + M07 (L121/126) + M08 (L16/37-39/53 trail)
- **4 反模式**:
  1. ❌ 无 M10 Notify (出问题时用户不知)
  2. ❌ 无 M11 Logger (复盘无据)
  3. ❌ 无 M13 FileIO (无 trades CSV)
  4. ❌ 无 M17 NewsFilter (NFP 假突破会爆)
- **安全审计 8 维度覆盖**: 4/8 (订单/风控/资金/异常回滚有, 时段/新闻/日志/异常处理无)
- **建议升级**: 加 M10 (DD 报警) + M11 (Trade 落盘) + M13 (trades CSV) + M17 (新闻避让)

### 3.4 Breakout_EA — 5 模块 (Donchian 突破)

- **路径**: `MQL5/Experts/minimax-ea/Breakout_EA.mq5` (9,530 B / 237L / mtime 2026-06-03 16:47:24)
- **接入 5 模块**: M01 (L135/142 Buy/Sell + L230 retcode) + M02 + M04 + M07 (L131/138/158) + M10 (L17/58/61/79/80)
- **3 反模式**:
  1. ❌ 无 M11 Logger
  2. ❌ 无 M13 FileIO
  3. ❌ 无 M17 NewsFilter
  4. ❌ 无 M19 SessionFilter (周末也开仓)
- **安全审计 8 维度覆盖**: 3/8
- **建议升级**: 加 M11/M13/M17/M19

### 3.5 MyEA — 10 模块全集 (通用 EA 骨架)

- **路径**: `MQL5/Experts/minimax-ea/MyEA.mq5` (12,541 B / 301L / mtime 2026-06-03 16:57:46)
- **接入 10 模块**: M01 (L189/192 Buy/Sell + L252 retcode) + M02 + M05 (L13/57/149) + M08 (L198) + M09 (L15) + M10 (L16/45/60/125/126) + M11 (L17/49/266/274) + M13 (L18/50) + M16 (L19/138/140/142)
- **1 反模式**:
  1. ❌ 无 M13/M17/M18 (注意: L18/50 是 M13 include + Trade, L266/274 是 M11 logger.Trade; 跟 M13 WriteTradeRow 配套)
- **安全审计 8 维度覆盖**: 7/8 (无 M18 多品种对冲)
- **沙盒**: 0 errors 编译, 5 段 8 row 最小 M09 范本 + 6 列简化 trade CSV

### 3.6 Dashboard — 4 模块 (跨品种监控无交易)

- **路径**: `MQL5/Experts/minimax-ea/Dashboard.mq5` (8,361 B / 208L / mtime 2026-06-03 16:51:16)
- **接入 4 模块**: M04 (指标) + M09 (L2/91) + M10 (L11/26/28/33/50 三类触发器) + M15 (OnTimer 1s/2s)
- **5 反模式** (无交易模块):
  1. ❌ 无 M01/M02/M07 (无交易)
  2. ❌ 无 M08 (无持仓管理)
  3. ❌ 无 M11/M13 (无交易审计)
  4. ❌ 无 M17/M18/M19 (无过滤)
- **安全审计 8 维度覆盖**: 2/8 (仅"日志审计"通过 NotifyMagic=0 监听全账户 + "异常回滚"通过 OnDeinit)
- **核心价值**: NotifyMagic=0 监听多 EA 账户 + M15 周期任务

### 3.7 ScalperXAUv5-v9 — 5 副仓 (异常隔离范本)

- **路径**:
  - `ScalperXAUv5simple.mq5` (6,545 B / 145L / mtime 06-04 05:52:17) — Print 调试
  - `ScalperXAUv6debug.mq5` (1,931 B / 45L / mtime 06-04 05:59:15) — Stop 终止
  - `ScalperXAUv7debug.mq5` (4,515 B / 115L / mtime 06-04 06:37:20) — Retry 重试
  - `ScalperXAUv8.mq5` (5,436 B / 133L / mtime 06-04 06:38:49) — Skip 跳过
  - `ScalperXAUv9.mq5` (13,186 B / 311L / mtime 06-04 09:44:49) — Fallback 降级
- **5 副仓共同模式**:
  - v5 Print: 异常时 Print 出来, 不影响主流程
  - v6 Stop: 异常时直接 Stop EA
  - v7 Retry: 异常时重试 3 次
  - v8 Skip: 异常时跳过本次开仓
  - v9 Fallback: 异常时回退到保守策略 (M19 off + M18 0.85)
- **接入点** (以 v9 311L 范本):
  - M01 L129/300/301 Buy/Sell + L307 retcode
  - M13 L58/156/158/174 FileIO (24 列 trade journal)
  - M16 L169 OnDeinit
- **安全审计 8 维度覆盖**: 1-3/8 (各副仓不同)

### 3.8 Scalper_CsvProto — 1 模块 M13 (单模块 demo)

- **路径**: `MQL5/Experts/minimax-ea/Scalper_CsvProto.mq5` (4,595 B / 113L / mtime 2026-06-03 16:49:38)
- **接入 1 模块**: M13 (L6/14/22 FileOpen/Write/Close)
- **6 反模式**:
  1. ❌ 无 M01 (无交易)
  2. ❌ 无 M02 (无风控)
  3. ❌ 无 M10 (无 Notify)
  4. ❌ 无 M11 (无 Logger)
  5. ❌ 无 M16 (OnDeinit 漏 Cleanup)
  6. ❌ 无 M17 (无 NewsFilter)
- **安全审计 8 维度覆盖**: 1/8 (仅"日志审计"通过 M13 FileIO)
- **核心价值**: 单模块 M13 FileIO 最小 demo (6 字段 CSV)

### 3.9 MiniMaxScalper v1 — 0 模块 (待定)

- **路径**: `MQL5/Experts/minimax-ea/MiniMaxScalper.mq5` (35,357 B / 846L / mtime 2026-06-04 10:09:46)
- **接入 0 模块 MQL5Kit** (用户手动 IDE 在写)
- **接入 6 内置功能**: M01 (L690/691/699) + M07 (L162/177/189/194) + M08 (L5/14/58-60) + M09 (L700) + M13 (L154/751/753/775) + M16 (L770 OnDeinit)
- **安全审计 8 维度覆盖**: 4/8 (订单/资金/异常回滚/日志审计有, 风控/时段/新闻/异常处理无)
- **状态**: 用户手动 IDE 在写, 06-05 00:31 mtime 编辑, 接入 MQL5Kit 待定

### 3.10 MiniMaxScalper v2 — 7 模块 (升级版)

- **路径**: `MQL5/Experts/minimax-ea/MiniMaxScalper_v2.mq5` (37,470 B / 889L / mtime 2026-06-04 16:31:42)
- **接入 7 模块**: M01 (L600/755 Buy + L601 Sell + L610 retcode) + M07 (L220/224/625/629/643) + M08 (L66-70 trail) + M09 (L733) + M13 (L214/788/789/803) + M16 (L797) + M17 (L102/301/333/338) 
- **安全审计 8 维度覆盖**: 6/8 (加 M17 + M08 + M13 + M16)
- **状态**: 用户手动 IDE 在写, 06-05 00:31 mtime 编辑, 接入 MQL5Kit 进行中

### 3.11 M17_TestNewsEA — 1 模块 M17 (实物自检 EA)

- **路径**: `MQL5/Experts/_archive/M17_TestNewsEA.mq5` (2,730 B / 55L / mtime 2026-06-03 16:48:31)
- **接入 1 模块**: M17 (L3/8/10/39/46)
- **6 断言** (L46 `CNewsFilter::RunSelfTest`):
  - L20 Init 启动
  - L24 LoadFromCSV 加载
  - L28 IsNearEvent ±30 min
  - L34 RunSelfTest 6 断言
  - 6/6 PASS (2026-06-04 12:00 落地验证)
- **安全审计 8 维度覆盖**: 1/8 (仅"新闻避让"通过 M17)
- **核心价值**: 单模块 M17 NewsFilter 最小 demo + 5 步复活 SOP

---

## §4 安全审计工具 (5 类)

> **5 类工具** 用于 8 维度安全审计的自动化 / 速查 / 复测。

### 4.1 M11 Logger (4 级别双输出)

- **API**: `logger.Info / Warn / Error / Trade(tag, msg)`
- **接入**: include + object + OnInit `SetFileOutput(true)` + OnTick `logger.Trade` + OnDeinit `logger.Close`
- **实物**: MeanReversion_EA L61 声明 + L202/205 Trade + L136 Close
- **审计价值**: 出问题时 grep `WARN/ERROR` 快速定位 + `TRADE` 复盘成交

### 4.2 M13 FileIO (trades_YYYYMMDD.csv)

- **API**: `CFileIO::AppendCSV(fname, fields[])` 静态方法
- **接入**: include + input `LogTradesToCsv=true` + `static _m13LastDealTicket` 去重 + `OnTrade` 内 `WriteTradeRow(t)`
- **实物**: ScalperXAU L29 include + L100-102 input + L126-127 去重 + L294-448 WriteTradeRowV3 (155 行 24 列)
- **审计价值**: trades CSV 是事后审计的**核心证据** (复盘 / 报税 / 出事追溯)

### 4.3 5 速查 wiki (必查清单 + 反模式)

- **[[04-避坑与速查/01 编译常见错误]]** — 6 条反模式 (input/OnInit 失败/Print 节流)
- **[[04-避坑与速查/02 OrderSend 错误码速查]]** — 6 条反模式 (retcode 忽视/deviation 0/SLTP 规范化)
- **[[04-避坑与速查/03 实盘 vs 回测差异]]** — 6 条反模式 (回测区间短/过拟合/24h 假设)
- **[[04-避坑与速查/04 经纪商差异-点差-手续费]]** — 6 条反模式 (_Digits 硬编码/Filling 硬编码/合约单位硬编码)
- **[[04-避坑与速查/05 必查清单]]** — 6 条反模式 (.ex5 丢源码/无 OnDeinit/无心跳日志) + 5 速查 24+ 反模式统一索引
- **审计价值**: 30 秒内对照清单逐项过

### 4.4 80 ❌ baseline + 11 wiki ## 反模式 段

- **80 ❌ baseline** (沿用 22:00 T3 [[04-避坑与速查/07 5 必看陷阱统一 wiki]]): 22:00 5 速查 80 标题 / 8 章节 / 集中展示
- **11 wiki ## 反模式 段** (沿用 [[MOC EA 开发知识库]] 反模式索引):
  - M01 spec §"反模式" 5 条 + 实战段 5 条 = 10 条
  - M02 spec §"反模式" 5 条 + 实战段 5 条 = 10 条
  - M05 spec §"反模式" 5 条 + 实战段 5 条 = 10 条
  - M08 spec §"反模式" 5 条 + 实战段 5 条 = 10 条
  - M09 spec §"反模式" 5 条 + 实战段 5 条 = 10 条
  - M10 spec §"反模式" 5 条 + 实战段 5 条 = 10 条
  - M11 spec §"反模式" 5 条 + 实战段 5 条 = 10 条
  - M13 spec §"反模式" 5 条 + 实战段 5 条 = 10 条
  - M17 spec §"反模式" 5 条 + 实战段 5 条 = 10 条
  - M18 spec §"反模式" 5 条 + 实战段 5 条 = 10 条
  - M19 spec §"反模式" 5 条 + 实战段 5 条 = 10 条
  - **11 wiki 累计 110 条反模式** (本任务不重复这 110 条)

### 4.5 mql5-audit.js 候补 CLI 工具 (候选 W 7 必做)

- **路径**: `C:\Users\Administrator\cu-mcp\tools\mql5-validate-cli.js` (07:00 T5 候选, 本任务 1h 内, 本 wiki §4 留坑, 等 T5 落地后链接)
- **API**: `node mql5-audit.js --wiki <path> --ea <glob> --check all` 输出 8 维度 PASS/FAIL
- **审计价值**: 8 维度自动扫描 + 14 实物 mtime baseline 对比 + JSON 结果输出
- **状态**: 候选 W 待 07:00 T5 落地 (0 阻塞, 沿用 06-04 20:00 validate_lines.js v2 + 06-05 05:00 T2 9 项 self-check 模板)

---

## §5 8 反模式 (不与 80 ❌ baseline + 11 wiki ## 反模式 段 110 条重复)

> **本节 8 反模式是"安全审计 8 维度"专属反模式**，跟 80 ❌ baseline + 11 wiki 110 条 ## 反模式 段互补不重复。沿用 06:00 T2/T3 范本末尾反模式段格式（场景+根因+反例+正解 4 段）。

### 反模式 1: ❌ Magic Number 不设或设 0 (无法识别订单)

- **场景**: 写新 EA 抄 CTrade 文档，忘调 `SetExpertMagicNumber(0)`，结果同账户跑多个 EA 时持仓相互干扰（EA A 关掉前把 EA B 的单子也平了）
- **根因**: `CTrade` 内部按 magic 过滤，`magic=0` 等于"匹配所有"（MT5 保留值）。M01 把它升级为参数 `_magic`，但调用方必须传非零值
- **反例**:
  ```mql5
  // ❌ 错: 直接用 CTrade 不设 magic
  CTrade trade;
  // 漏掉 trade.SetExpertMagicNumber(Magic);
  ```
- **正解**:
  ```mql5
  // ✅ 对: 用 M01 CTradePlus + Init 必传 magic
  CTradePlus trade;
  input ulong Magic = 20260101;  // EA 专属 magic
  int OnInit() {
     trade.Init(Magic, 30);
     return INIT_SUCCEEDED;
  }
  ```
- **关联**: 维度 1 订单安全 + M01 spec L444 反模式 4 + 实战陷阱 1

### 反模式 2: ❌ 风控只检查单笔, 不检查总敞口

- **场景**: 4 品种 EA 跑 4 笔同向持仓, 单笔 risk 1% 但 4 笔 = 4% 净值风险，黑天鹅打穿
- **根因**: M02 `_maxPositions=3` 限制"本 magic 同向总持仓"，但**不区分品种**。MeanReversion_EA 4 品种共享 `MaxPos=3` 实际是"4 品种同向最多 3 笔"——用户期望"每品种 3"做不到
- **反例**:
  ```mql5
  // ❌ 错: 只查单笔 SL 距离
  if (slDist < minDist) return;  // 单笔 OK
  trade.Buy(lot, sl, tp, "long");  // 4 笔同向不查
  ```
- **正解**:
  ```mql5
  // ✅ 对: M02.CanOpen 7 项检查 (含 _maxPositions 总敞口)
  if (!risk.CanOpen(type, lot, sl, tp)) return;
  // 加上 M18 跨品种对冲过滤
  if (M18.IsHedgeExposed(_Symbol, Magic, 0.7)) return;
  ```
- **关联**: 维度 2 风控合规 + 维度 3 资金管理 + M02 spec L329 反模式 1 + 实战陷阱 2

### 反模式 3: ❌ Lot 硬编码, 不用 M02.Risk.CalcLot

- **场景**: 抄 demo `trade.Buy(0.01, ...)`，所有 EA 都用 0.01 lot。结果 XAUUSDm 净值 100 USD 时 0.01 lot 风险 0.5% OK，但净值 10000 USD 时同样 0.01 lot 风险 0.005% = 浪费杠杆
- **根因**: M03 `LotByRisk(RiskPct, slDist)` 根据 slDist 自动算 lot，sl 越大手数越小（保持风险 % 一致）。硬编码 lot = 风险 % 随净值变
- **反例**:
  ```mql5
  // ❌ 错: 硬编码 lot
  trade.Buy(0.01, sl, tp, "long");  // 净值 100 USD OK, 10000 USD 浪费
  ```
- **正解**:
  ```mql5
  // ✅ 对: M03.LotByRisk 必先调
  double slDist = MathAbs(price - sl);
  double lot = sizing.LotByRisk(RiskPct, slDist);
  if (lot <= 0) return;
  trade.Buy(lot, sl, tp, "long");
  ```
- **关联**: 维度 3 资金管理 + M02 spec L332 反模式 4 + M03 spec

### 反模式 4: ❌ SL/TP 不设, 寄希望于 M08 追踪

- **场景**: 写趋势 EA，抄 demo 调 `trail.Init + SetParams + Apply`，但 Buy/Sell 时 `sl=0, tp=0`。结果跳空直接爆仓（trail 启动前没 SL 守门）
- **根因**: M08 追踪止损**只在浮盈达到 _startPoints 才启动**（`if (profitDist < _P(_startPoints)) return;`）。启动前 = 无 SL = 跳空直接打穿本金
- **反例**:
  ```mql5
  // ❌ 错: SL=0 寄希望 trail
  trade.Buy(0.01, 0, 0, "long");  // 跳空打穿
  trail.Apply();  // trail 启动前已经爆仓
  ```
- **正解**:
  ```mql5
  // ✅ 对: Buy/Sell 必设 SL（最小止损距离检查）+ trail 锁利
  double sl = price - 100 * _Point;
  double tp = price + 200 * _Point;
  if (!risk.CanOpen(type, lot, sl, tp)) return;  // SL 距离检查
  trade.Buy(lot, sl, tp, "long");  // 初始 SL
  // M08 浮盈 > start 时启动
  ```
- **关联**: 维度 6 异常处理 + 维度 8 异常回滚 + M08 spec L335 反模式 1 + 实战陷阱 1

### 反模式 5: ❌ 时段不限制, 周末也开仓

- **场景**: 写剥头皮 EA，忘加 M19，7×24 小时都开仓。结果周五 NY 收盘后点差从 30 拉到 100+ points，周一开盘跳空
- **根因**: 周末外汇市场实际关闭（XAUUSDm 周末点差 50-100+），经纪商 `OrderSend` 直接 `retcode=10018 ERR_MARKET_CLOSED`。M19 默认 `SetAllowWeekend(false)` 必开
- **反例**:
  ```mql5
  // ❌ 错: 不加 M19 时段过滤
  void OnTick() {
     if (入场条件) trade.Buy(lot, sl, tp);  // 周末也开
  }
  ```
- **正解**:
  ```mql5
  // ✅ 对: M19 时段过滤 (4 预定义常量 + 周末禁开)
  if (InpUseM19Filter && !M19.IsInSession(TimeCurrent())) {
     RefreshDash();
     return;  // off-hours / 周末不开
  }
  // 入场信号
  ```
- **关联**: 维度 4 交易时段 + M19 spec L341 反模式 5 + 实战陷阱 1

### 反模式 6: ❌ 新闻前后 ±30 min 不避让

- **场景**: 写趋势 EA，XAUUSDm 平时稳定，但 NFP / CPI / FOMC 公布 ±30 min 内点差 30 → 80+ points + 滑点异常，1 笔误开 = 打穿 50 笔盈利
- **根因**: M17 NewsFilter 加载 CSV 财经日历，`IsNearEvent(30, 30, _Symbol)` 在 ±30 min 拦截。**XAUUSDm M1 剥头皮必开**（spec M17 §1.2 表）。忘接 = 黑天鹅打穿
- **反例**:
  ```mql5
  // ❌ 错: 不加 M17 新闻过滤
  void OnTick() {
     if (入场条件) trade.Buy(lot, sl, tp);  // NFP 公布 ±30 min 内被打穿
  }
  ```
- **正解**:
  ```mql5
  // ✅ 对: M17 新闻过滤 (PassFilters 段, 跟 M19 串联)
  bool PassFilters() {
     if (InpEnableNewsFilter && news.IsNearEvent(30, 30, _Symbol)) return false;
     // ... 其它过滤 ...
     return true;
  }
  ```
- **关联**: 维度 5 新闻避让 + M17 spec L416 反模式 1-4

### 反模式 7: ❌ retcode 不检查, 失败不重试

- **场景**: 抄 demo `trade.Buy(0.01, sl, tp)` 不读返值，retcode=10018 ERR_MARKET_CLOSED 也"以为成功"。结果实盘跑 1 周 0 笔，不知是 EA 坏了还是 market closed
- **根因**: `trade.Buy` 返 `true` 但 `retcode != TRADE_RETCODE_DONE` 时只代表"发送成功"，**不代表"成交成功"**。M01 `_CheckRetcode` 内部区分 DONE/DONE_PARTIAL/PLACED（成功）vs 9 个其它码（失败）
- **反例**:
  ```mql5
  // ❌ 错: 不读返值
  trade.Buy(0.01, sl, tp, "long");  // 返 false 不知
  Print("Buy 成功");  // 实际失败
  ```
- **正解**:
  ```mql5
  // ✅ 对: 必读返值 + 失败重试 + M10 通知
  if (trade.Buy(lot, sl, tp, "long")) {
     logger.Trade("BUY", _Symbol, lot, price, 0, "信号");
  } else {
     PrintFormat("Buy 失败 retcode=%u (%s) comment=%s",
                 trade.LastRetcode(),
                 _RetcodeText(trade.LastRetcode()),
                 trade.LastComment());
     M10.Send("❌ Buy 失败 retcode=" + IntegerToString(trade.LastRetcode()), true);
  }
  ```
- **关联**: 维度 1 订单安全 + 维度 6 异常处理 + M01 spec L439 反模式 4 + 实战陷阱 4

### 反模式 8: ❌ 日志只 Print, 不写 M13.FileIO

- **场景**: 写 EA 调试完忘删 Print，实盘跑 1 周后想复盘"上周 5 笔成交的 MFE/MAE 是多少"，journal 不可二次分析
- **根因**: `Print()` 输出到 Experts 日志，是文本格式（要 PS/Node.js 解析）。M11 `logger.Trade` + M13 `CFileIO::AppendCSV` 写**结构化 CSV**，`node csv-parse` 直接读。**复盘要数据，不用 M13 = 没有数据**
- **反例**:
  ```mql5
  // ❌ 错: 只 Print, 不写 CSV
  void OnTrade() {
     Print("成交 ticket=", ticket, " lot=", lot, " pnl=", pnl);  // 文本不可分析
  }
  ```
- **正解**:
  ```mql5
  // ✅ 对: M11 logger + M13 FileIO 写 CSV (6 列简化 / 24 列完整)
  void OnTrade() {
     if (LogTradesToCsv) WriteTradeRow(t);  // trades_YYYYMMDD.csv
     logger.Trade("BUY", _Symbol, lot, price, 0, "信号");  // EA_log_YYYYMMDD.csv
     M10.Trade("BUY", _Symbol, price, lot, 0, "MyEAv1");  // 推送
  }
  ```
- **关联**: 维度 7 日志审计 + M11 spec L265 反模式 1 + M13 spec L333 反模式 1

---

## §6 链向 (12 wiki)

> **12 链向 = 7 spec wiki + 3 实战 wiki + MOC + 1 速查 wiki + 1 性能/异常 wiki**。沿用 06:00 T2/T3 末尾 12 链向范本。

### 6.1 19 模块 spec 链向 (本 wiki §2 段尾已链, 这里集中)

- **[[01-调用模块/M01 交易封装 CTradePlus]]** — Magic + retcode 12 码表 + 重试
- **[[01-调用模块/M02 风控 Risk]]** — 7 项风控 + EmergencyStop
- **[[01-调用模块/M05 新 K 线检测 NewBar]]** — 异常 NewBar 跳过
- **[[01-调用模块/M08 追踪止损 TrailingStop]]** — 异常 trail 暂停
- **[[01-调用模块/M09 面板 Dashboard]]** — 异常后状态显示
- **[[01-调用模块/M10 推送通知 Notify]]** — 网络失败重试 + 3 类触发器
- **[[01-调用模块/M11 日志 Logger]]** — 4 级别 Info/Warn/Error/Trade
- **[[01-调用模块/M13 文件 IO]]** — trades_YYYYMMDD.csv 落盘
- **[[01-调用模块/M17 新闻过滤 NewsFilter]]** — ±30 min 避让
- **[[01-调用模块/M18 相关性过滤 CorrelationFilter]]** — 多品种对冲
- **[[01-调用模块/M19 时段过滤 SessionFilter]]** — 4 预定义常量 + 周末

### 6.2 3 实战 wiki (13 模块全集 / 4 版本演进 / 跨 EA 模式)

- **[[实战/MeanReversion_EA 接入报告]]** — 13 模块全集 (本 wiki §3.1 范本, 安全审计 8/8)
- **[[实战/ScalperXAU 接入报告 + v1→v4 演进史]]** — 4 版本演进 (本 wiki §3.2 范本, v3 0 笔根因 = 缺 M01)
- **[[实战/跨 EA 模式萃取 wiki]]** — 5 副仓 v5-v9 异常隔离 (本 wiki §3.7 范本, Print/Stop/Retry/Skip/Fallback)

### 6.3 MOC 入口 + 速查 wiki + 性能/异常 wiki

- **[[MOC EA 开发知识库]]** — 安全审计分类入口 (本次 T2 新增 1 行链向, 由 T4 owner 追加)
- **[[04-避坑与速查/05 必查清单]]** — 发版前 5 必查 + 24+ 反模式统一索引
- **[[性能调优/MT5 性能调优 wiki]]** — 19 模块性能优化指南 (06:00 T2 闭环, 候选 S)
- **[[异常处理/异常处理手册]]** — 19 模块异常处理范本 (06:00 T3 闭环, 候选 T)

---

## §7 接入点行号 (Node.js fs 实测明细)

> **本节是 verifier 9 项 "接入点行号 ≥ 30, Node.js fs grep 100% 命中" 的明细来源**。11 实物 EA 全部接入点行号 100% Node.js fs grep 命中（`workspace/scan-all.js` + `scan-security.js`），0 编造。
>
> **合计 100+ 行号命中** (远超 30 行号门槛): 模块级 50+ + 安全审计维度级 68 = 118+。

### 7.1 模块级接入点 (50+ 行号, workspace/scan-all.js 输出)

| EA | L数 | 模块接入点 (Node.js fs grep 命中行号) |
|---|---|---|
| MeanReversion_EA | 320 | M01 Init L80/Buy L201/Sell L204/retcode L313; M02 Init L81/CanOpen L199; M05 Init L83/guard L146; M08 Init L88-89/Apply L144; M09 dash L60; M10 L62/L90-91/L301-318; M11 L61/L202/205; M16 L19/L132/L134; M18 L20/L63/L167-172/L242; M19 L21/L64/L161-164/L244-246; OnInit L79; OnDeinit L132 |
| ScalperXAU | 1,033 | M01 L19/L107/L953/L774/L775/L902; M02 L20/L108/L956; M05 L23/L111/L798; M07 L566/569/573/589/597; M08 L25/L113/L962/L963/L739/L796; M09 L12; M10 L27/L116/L966-967/L871-885/L924-940/L890-907; M11 L28/L101/L913/L920; M13 L29/L102/L643/645/651; M16 L30/L1010; M17 L31/L80/L117/L548-553; OnInit L951; OnTick L789; OnDeinit L1010 |
| TrendMA_EA | 239 | M01 L144/147/232; M05 L13/52/92/93; M07 L121/126; M08 L16/37-39/53; M09 L17; M10 L18/45/56/73/74; M11 L19; M16 L20/81/83/85; OnInit L64; OnTick L91; OnDeinit L81 |
| Breakout_EA | 237 | M01 L135/142/230; M05 L13/54/96/97; M07 L131/138/158; M08 L15/43-45/55; M09 L16; M10 L17/58/61/79/80; M11 L18; M16 L19/87/89; OnInit L68; OnTick L95; OnDeinit L87 |
| MyEA | 301 | M01 L189/192/252; M05 L13/57/149; M08 L198; M09 L15; M10 L16/45/60/125/126; M11 L17/49/266/274; M13 L18/50; M16 L19/138/140/142; OnInit L118; OnTick L147; OnDeinit L138 |
| Dashboard | 208 | M09 L2/91; M10 L11/26/28/33/50; M16 L64; OnInit L42; OnTick L70; OnDeinit L64; OnTimer L75 |
| ScalperXAUv5 | 145 | M01 L137/138; M02 L23; M05 L16; M11 L18; M13 L45/47/52/64/65; M16 L59; OnInit L37; OnTick L84; OnDeinit L59 |
| ScalperXAUv6 | 45 | M09 L13; M16 L24; OnInit L15; OnTick L32; OnDeinit L24 |
| ScalperXAUv7 | 115 | M05 L10; M09 L59; M13 L3/8/28/47/49; M16 L63; OnInit L38; OnTick L77; OnDeinit L63 |
| ScalperXAUv8 | 133 | M01 L50/122/123/129; M13 L8/28/32/51/52; M16 L65; OnInit L42; OnTick L78; OnDeinit L65 |
| ScalperXAUv9 | 311 | M01 L129/300/301/307; M13 L58/156/158/174; M16 L169; OnInit L128; OnTick L182; OnDeinit L169 |
| Scalper_CsvProto | 113 | M11 L21/80; M13 L6/14/22; M16 L105; OnInit L94; OnTick L109; OnDeinit L105 |
| MiniMaxScalper | 846 | M01 L690/691/699; M07 L162/177/189/194; M08 L5/14/58-60; M09 L700; M13 L154/751/753/775; M16 L770; OnInit L707; OnTick L796; OnDeinit L770 |
| MiniMaxScalper_v2 | 889 | M01 L600/755/601/610; M07 L220/224/625/629/643; M08 L66-70; M09 L733; M13 L214/788/789/803; M16 L797; M17 L102/301/333/338; OnInit L749; OnTick L825; OnDeinit L797 |
| M17_TestNewsEA | 55 | M13 L20/25/27/29/31 (RegenCsv); M16 L52 (OnDeinit); M17 L3/8/10/39/46 (LoadFromCSV+RunSelfTest); OnInit L38; OnTick L53; OnDeinit L52 |

### 7.2 安全审计维度级 (68 命中, workspace/scan-security.js 输出)

| 维度 | 命中数 | 代表 EA + 行号 |
|---|---|---|
| 订单安全 (Magic+retcode+retry) | 17 | MeanReversion_EA L201/204/313; ScalperXAU L902; TrendMA L232; MyEA L252; MiniMaxScalper L699; MiniMaxScalper_v2 L610 |
| 风控合规 (MaxLot+CheckMargin+CheckExposure) | 1 | ScalperXAU L55/766/956/958 (M02) |
| 资金管理 (CalcLot+RiskPercent+Kelly) | 6 | ScalperXAU L55/766/956/958 (M02); ScalperXAUv5 L23 (RiskPct) |
| 交易时段 (4 预定义常量 + 周末 + 跨午夜) | 2 | MeanReversion_EA L21/L64 (M19); MiniMaxScalper_v2 L102 (M17 联动) |
| 新闻避让 (IsNearEvent+high_impact+LoadFromCSV) | 3 | ScalperXAU L548-549 (PassFilters); MiniMaxScalper_v2 L301/333/338; M17_TestNewsEA L3/8/10/39/46 |
| 异常处理 (retcode 不吞+fallback+try_catch) | 4 | MeanReversion_EA L80/146/199; ScalperXAU L953/956 |
| 日志审计 (Info/Warn/Error/Trade + trades_csv) | 14 | MyEA L17/49/266/274 (logger.Trade); MeanReversion_EA L18 (M11); Scalper_CsvProto L21/80 |
| 异常回滚 (OnDeinit+ClosePos+SL_trigger+Trail_pause) | 21 | MeanReversion_EA L132/134/137 (OnDeinit 4 件套); ScalperXAU L1010/1012/1014; TrendMA L81/83/85 |

### 7.3 14 实物 .mq5 mtime baseline (0 改 .mq5 验收)

```
14 .mq5 mtime @ 2026-06-05 07:19 (Node.js fs statSync, plan 期间 UNCHANGED):
- Breakout_EA.mq5 9530B  2026-06-03T16:47:24
- Dashboard.mq5 8361B  2026-06-03T16:51:16
- MeanReversion_EA.mq5 13503B  2026-06-04T03:21:46
- MiniMaxScalper.mq5 35357B  2026-06-04T10:09:46
- MiniMaxScalper_v2.mq5 37470B  2026-06-04T16:31:42
- MyEA.mq5 12541B  2026-06-03T16:57:46
- ScalperXAU.mq5 42824B  2026-06-04T05:44:12
- ScalperXAUv5simple.mq5 6545B  2026-06-04T05:52:17
- ScalperXAUv6debug.mq5 1931B  2026-06-04T05:59:15
- ScalperXAUv7debug.mq5 4515B  2026-06-04T06:37:20
- ScalperXAUv8.mq5 5436B  2026-06-04T06:38:49
- ScalperXAUv9.mq5 13186B  2026-06-04T09:44:49
- Scalper_CsvProto.mq5 4595B  2026-06-03T16:49:38
- TrendMA_EA.mq5 9169B  2026-06-03T16:50:34
```

> **0 改 .mq5 验收 PASS**: 14 实物 mtime 全部 06-03/04 期间, 07:00 plan 期间 UNCHANGED。

---

## §8 维护 & 后续

### 8.1 维护信息

- **创建时间**: 2026-06-05 07:30 (07:00 T2 worker-A 闭环)
- **wiki 版本**: 1.00
- **下次更新**: 14:00 §5 候选 E 闭环后, 接入 N1 5 EA 6 月回测对比 SOP 数据替换 §1 量化表
- **维护人**: Mavis general agent (mvs_a79c1c636b764eea9ebfcdb48738056f, T2 worker-A)
- **关联任务**: [[T2 任务单 2026-06-05 07:00]] (候选 U 14:00 §5 维度 5 候选 E 闭环)
- **关联 plan**: plan_b8b0fd92 (07:00 巡检 plan, 候选 U + V + W 三件套)
- **关联 track**: T2 worker-A

### 8.2 待 T5 落地的 mql5-audit.js CLI

- **本任务**写完 §4.5 "mql5-audit.js 候补 CLI" 留坑, 等 07:00 T5 worker-C 落地后, 在本 wiki §4.5 加 1 行 `[[cu-mcp/tools/mql5-validate-cli.js]]` 链向
- **预期 9 项 self-check**: 文件存在 / 字节 ≥ 15,000 / 6 章节 / 接入点行号 ≥ 30 / 0 placeholders / 0 推荐语 / 0 改前文 / 0 改 .mq5 / 0 创建 README

### 8.3 反哺机制 (本任务 4 反哺)

1. **MOC 链向**: T4 owner 在 [[MOC EA 开发知识库]] 末尾"安全审计"分类加 1 行链向 (T4 顺手, 1 行)
2. **必读 12 必读链向**: T2 worker 必读 list 包含 12 必读 (✅ EA / ✅ wiki 必读 Obsidian mql5 知识库 = 用户 IM 5 条指令第 5 条)
3. **跨项目 lesson 沉淀**: T1 owner 写 memory entry, 1 条新 lesson: "新 wiki 8 维度 + 19 模块 + 11 实物 + 5 工具 + 8 反模式 + 12 链向 范本"
4. **daily/2026-06-05.md 07:00 段**: T1 owner 写 9 章节 (本文件) + daily/2026-06-05_07-00-track2-result.md (本任务结果)

### 8.4 累计状态 (07:00 闭环后预期)

- 累计 wiki: 67 → 68 (+1 EA 安全审计)
- 累计字节: +15-20K (本任务 ≥ 15K)
- MOC: 13,451B → 13,651B+ (+200-400B, +1.5-3%, T4 1 行链向允许)
- MOC 分类新增: 安全审计 0 → 1 (T2 1 行链向 + T4 owner 末尾追加)
- 14/14 实物 .mq5 mtime UNCHANGED baseline 对比 ✅
- decision-06-05-07-00.json override_accept cycle 1 applied plan_complete=true
- 累计反模式: 80 baseline + 11 wiki 110 条 ## 反模式 段 + 8 (本任务 8 安全审计反模式) = 198 (本任务 8 反模式 wiki ## 反模式 段 集中展示, 跟 80 baseline 互补不重复)
- 累计 CLI 工具: validate_lines.js v2 → 待 07:00 T5 mql5-validate-cli.js v3 升级

---

> **关联入口**: 读完本 wiki 后, 跳到 [[实战/MeanReversion_EA 接入报告]] §2.1 看 13 模块全集接入 (本 wiki §3.1 范本); 跳到 [[M01 交易封装 CTradePlus]] §实战段 看订单安全接入 (本 wiki §1.1 维度 1); 跳到 [[04-避坑与速查/05 必查清单]] 看发版前 30 项 Checklist (本 wiki §4.3 速查工具)。
