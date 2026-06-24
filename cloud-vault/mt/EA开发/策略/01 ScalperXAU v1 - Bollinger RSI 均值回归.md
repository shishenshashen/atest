# v1 ScalperXAU — Bollinger Band + RSI 均值回归剥头皮

> **状态**: 设计中 (2026-06-04 09:28)  
> **目标**: 实盘 demo 账户跑 XAUUSDm M1, 日均交易 5-15 笔, Net Profit > 0, PF > 1.3, Max DD < 15%, Win Rate > 55%

## 1. 策略类型

**均值回归 (Mean Reversion) 剥头皮** — 比趋势跟随更适合剥头皮, 进出快, 不扛单

### 核心思想
XAUUSDm 短期价格围绕均值 (BB 中轨) 震荡, 触及 BB 边界 + RSI 极端 = 短期超买超卖 → 逆向开仓 → 回归中轨即获利

### 不选趋势/突破的理由
- 突破策略需要等待明确方向, 持仓时间长, 不符合"剥头皮"定义
- 突破假信号多, SL/TP 设宽了亏, 设窄了被扫
- XAUUSDm 1M 趋势延续性差, 数据支撑少

## 2. 入场信号 (M1 K 线起头判断, 用 [1] 历史 bar)

### BUY 信号 (同时满足)
1. `close[1] <= BB_lower[1]` — 上一根 K 线触及/跌破 BB 下轨
2. `RSI[1] < InpRsiOversold` — 默认 30, RSI 超卖确认
3. `spread < InpMaxSpreadPoints` — 默认 50 points (0.50 USD), 防点差陷阱
4. `M17.IsNearEvent(30, 30) == false` — 高影响新闻 ±30 min 内不开仓
5. 当前持仓数 < `InpMaxPositions` — 默认 3
6. 当日已开仓数 < `InpMaxTradesPerDay` — 默认 20
7. 当日 PnL > `-InpMaxDailyDrawdownPct * Balance / 100` — 默认 -3%
8. 当前小时 ∈ `[InpSessionStartHour, InpSessionEndHour)` — 默认 8-23 UTC (伦敦+纽约)

### SELL 信号
1. `close[1] >= BB_upper[1]` — 上一根 K 线触及/突破 BB 上轨
2. `RSI[1] > InpRsiOverbought` — 默认 70
3-8. 同上

## 3. 出场 (优先级从高到低)

### 优先级 1: SL/TP 命中
- SL: `InpSlPoints` (默认 50 points = 0.50 USD/lot) — 固定, 不随 ATR 调整 (剥头皮要简单)
- TP: `InpTpPoints` (默认 100 points = 1.00 USD/lot) — RR 1:2

### 优先级 2: 时间止损
- 开仓后 `InpMaxHoldMinutes` (默认 30 min) 未平 → 市价平仓
- 防止 BB 触碰后单边走出变短线

### 优先级 3: 反向信号
- BUY 持仓中, 出现 SELL 信号 → 不直接反转, 平多观望 (反转会放大回撤)

## 4. 风控

| 项 | 默认 | 备注 |
|---|---|---|
| 账户风险/笔 | 0.5% | M03.LotByRiskDefault 算手数 |
| 最大同时持仓 | 3 | |
| 日内最大亏损 | -3% | 触发当日停止 |
| 日内最大交易 | 20 | 防止过度交易 |
| MagicNumber | 20240604 | 跟其它 EA 区分 |

## 5. 过滤器

| 过滤器 | 模块 | 阈值 | 失败动作 |
|---|---|---|---|
| Spread | M04 直接读 SymbolInfoDouble | < 50 points | 跳过本根 |
| 新闻 (高影响) | M17.IsNearEvent | ±30 min 内无 | 跳过本根 |
| 时段 | 直接判断 hour | 8-23 UTC | 跳过本根 |
| ATR 区间 | M04.iATR(14) | > 0.5 USD && < 5 USD | 跳过 (太静/太乱) |
| 周五尾盘 | 直接判断 dayOfWeek + hour | 周五 20:00 UTC 后不开新仓 | 跳过 |

## 6. 仓位管理 (M03)

- `M03.PositionSizing.LotByRiskDefault(slPoints)` — 0.5% 风险算手数
- 最小手数 0.01, 最大 0.5 (XAU 限制)
- Step 0.01, 向上取整

## 7. 模块依赖 (MQL5Kit 全部就位)

| 模块 | 用途 |
|---|---|
| M01_CTradePlus | 开/平仓, magic, slippage |
| M02_Risk | 账户余额/净值查询, 日内 PnL |
| M03_PositionSizing | 0.5% 风险算手数 |
| M04_IndicatorPool | BB(20,2) + RSI(14) + ATR(14) 句柄 |
| M05_NewBar | M1 K 线起头检测 |
| M06_Signal | 入场信号聚合 (本 EA 自实现, 不用 M06) |
| M07_Positions | 持仓查询/平仓 |
| M10_Notify | 异常推送 (DD > 5% / 拒单 / 断连) |
| M11_Logger | 运行日志 |
| M13_FileIO | trades_YYYYMMDD.csv 落盘 |
| M15_TimerService | 1s tick 定时器 (持仓超时检测) |
| M16_Cleanup | OnDeinit 清理 |
| M17_NewsFilter | 新闻过滤 (需先 MQL5/Files/news_calendar.csv 存在) |

## 8. 输入参数 (EA input 完整列表)

```
=== 策略 ===
InpBbPeriod           = 20         // BB 周期
InpBbDeviation       = 2.0        // BB 标准差倍数
InpRsiPeriod          = 14         // RSI 周期
InpRsiOversold        = 30         // RSI 超卖阈值
InpRsiOverbought      = 70         // RSI 超买阈值

=== 出场 ===
InpSlPoints           = 50         // SL (points, 1 point = 0.01 USD on XAU)
InpTpPoints           = 100        // TP
InpMaxHoldMinutes     = 30         // 时间止损

=== 风控 ===
InpRiskPercent        = 0.5        // 账户风险/笔
InpMaxPositions       = 3          // 最大同时持仓
InpMaxTradesPerDay    = 20         // 日内最大交易
InpMaxDailyDrawdownPct = 3.0      // 日内最大亏损 %

=== 过滤 ===
InpMaxSpreadPoints    = 50         // 最大点差 (points)
InpAtrMin             = 0.5        // ATR 最小值 (USD)
InpAtrMax             = 5.0        // ATR 最大值 (USD)
InpSessionStartHour   = 8          // 起始小时 (UTC)
InpSessionEndHour     = 23         // 结束小时 (UTC)

=== 元 ===
InpMagicNumber        = 20240604
InpEnableNewsFilter   = true
```

## 9. 实施步骤 (来自 user 09:27 IM)

1. ✅ 写 spec 文档 (本文件)
2. ⏳ 用 mcp-mt5 `mt5_describe_strategy` 或手写生成 EA 源码
3. ⏳ 写到 `MQL5/Experts/minimax-ea/ScalperXAU.mq5` + SKILL.md
4. ⏳ `MetaEditor64 /compile:` 0 errors 验证
5. ⏳ 写 `MQL5/Profiles/Tester/ScalperXAU.set` 默认参数
6. ⏳ Backtest: XAUUSDm M1, "Every tick based on real ticks", 2026-05-01 ~ 2026-06-01 (1 个月)
7. ⏳ 抓报告: Net Profit / Profit Factor / Max DD / Total Trades / Win Rate
8. ⏳ Demo live 跑 4-24h, attach 到 XAUUSDm M1
9. ⏳ 抓 trades_YYYYMMDD.csv + mt5_journal_stats
10. ⏳ 分析: 哪些笔赢/亏, 信号质量, 滑点, spread 实测
11. ⏳ 优化 v2: 调参重 backtest (BB/RSI/SL/TP 各 ±20%)
12. ⏳ 迭代直到目标 (Net Profit > 0, PF > 1.3, Max DD < 15%, Win Rate > 55%)

## 10. 目标成功标准 (Pass Criteria)

| 指标 | 目标 | 失败线 |
|---|---|---|
| Net Profit (backtest 1m) | > 0 | < 0 |
| Profit Factor | > 1.3 | < 1.0 |
| Max DD % | < 15% | > 25% |
| Win Rate | > 55% | < 45% |
| Avg Trade | > 0.3 USD | < 0 |
| Total Trades | 50-500 (1m) | < 30 (过少, 统计无效) |
| Backtest 编译 0 errors | 必须 | 必须 |

## 11. 已知风险 / 限制

- **CLI 编译无法看到具体哪行错误** — 失败要靠源分析 + 历史同类 fix 模式
- **GUI backtest 需 console session 1** — MT5 Strategy Tester 需 GUI 操作, 跨 session 受 UIPI 拒. 我用 CLI 触发 backtest 可能需要尝试
- **新闻 CSV 需手动准备** — `MQL5/Files/news_calendar.csv` 需用户先填, 否则 M17 总是返 false (无影响, 等于关闭新闻过滤)
- **Demo 账户需用户回 console session 1 点 "Allow Algo Trading"** — 首次 attach EA 时弹窗, 我跨 session 点不到
- **24h demo 期间 MT5 需保持运行** — 不能关 terminal64

## 12. 相关链接

- MQL5Kit 模块: `MQL5/Include/MQL5Kit/M01-M17`
- mcp-mt5 server: 27 tools 端到端 OK
- 历史任务: plan_bbbdc7f5 (ScalperEA 接入 M10/M13/M17) — 本 EA 在那基础上做
- 任务中心: `C:\ai\obsidian-文件\mt\00-任务调度中心\`
