# ScalperXAU v2 - Bollinger Band + RSI 均值回归剥头皮 (XAUUSDm M1)

> v2 升级重点: Trade Journal 增强 + EA 内滚动指标 + MFE/MAE/Duration/Exit Reason
> 
> v1 → v2 改动: 6 列 CSV → 23 列 CSV (MFE/MAE/Duration/ExitReason/Spread/Slippage);
> 加 11 个 EA 内滚动指标 (仪表盘 + journal); 加 SQN 累积; 仪表盘实时显示

## 1. 策略核心

均值回归 + 剥头皮。XAUUSDm 1 分钟 K 线。
- 触发: 价格触及 BB 上下轨
- 过滤: RSI 超买/超卖 (避免假信号)
- 风控: 固定 SL/TP (RR 1:2) + 单笔风险 0.5% + 最大持仓数 + 日内最大亏损

## 2. v1 → v2 升级对照

| 维度 | v1 | v2 |
|------|-----|-----|
| 编译大小 | 89KB | 104KB |
| CSV 列数 | 6 | 23 |
| Trade Journal | time/symbol/type/volume/price/profit | + open_time/close_time/duration_sec/sl_price/tp_price/exit_reason/mfe_pips/mae_pips/spread_at_entry/slippage_pts/magic/order_id/comment |
| EA 内指标 | 无 | TotalTrades/WinRate/PF/Net/MaxDD/RecoveryFactor/Calmar/Sharpe/AvgWin/AvgLoss/MaxConsecW/MaxConsecL |
| 持仓 MFE/MAE | 无 | 每个 M1 bar 持续更新, 平仓时写入 CSV |
| 出场原因分类 | 无 | SL_HIT / TP_HIT / TIMEOUT / MANUAL_OR_SIGNAL (CSV 字段) |
| 仪表盘 | 11 行 | 18 行 (含指标) |
| 错误版本兼容 | BB/RSI/ATR 直接 iBands/iRSI/iATR | 同 v1 (M04.Values 拿不到多 buffer) |

## 3. CSV Schema (v2)

```csv
time,symbol,direction,type,volume,price,profit,swap,commission,net_pnl,
open_time,close_time,duration_sec,sl_price,tp_price,
exit_reason,mfe_pips,mae_pips,spread_at_entry,slippage_pts,magic,order_id,comment
```

| 字段 | 说明 |
|------|------|
| `time` | deal 成交时间 |
| `direction` | BUY / SELL (只在 close 行填, 反映仓位方向) |
| `type` | BUY / SELL (deal 类型) |
| `duration_sec` | 持仓秒数 |
| `exit_reason` | `SL_HIT` / `TP_HIT` / `TIMEOUT` (>30min) / `MANUAL_OR_SIGNAL` |
| `mfe_pips` | Maximum Favorable Excursion (期间最大有利偏移, points) |
| `mae_pips` | Maximum Adverse Excursion (期间最大不利偏移, points) |
| `spread_at_entry` | 入场时 spread (points) |

## 4. EA 内滚动指标 (仪表盘 + journal)

EA 在 `OnTrade` 里逐笔累加:

| 指标 | 公式 | 用途 |
|------|------|------|
| TotalTrades | 已平仓笔数 | 样本量 |
| WinRate | wins / totalTrades | 信号质量 |
| ProfitFactor | grossProfit / grossLoss | 整体盈利能力 |
| Net | grossProfit - grossLoss | 净盈亏 |
| MaxDD | max((peak - eq) / peak) | 最大回撤 |
| RecoveryFactor | net / maxDDAbs | 净值/回撤 |
| Calmar | (net% / maxDD%) | 年化收益/回撤 |
| Sharpe | 简化版, 用 avgR / stdR (待补完) | 风险调整后收益 |
| MaxConsecW/L | 最长连续赢/亏 | 心理承压 |
| AvgWin / AvgLoss | 平均盈/亏 | 期望单笔 |
| Payoff | avgWin / avgLoss | 盈亏比 |

## 5. 输入参数 (24 个)

```
=== 策略 ===        InpBbPeriod=20 / InpBbDeviation=2.0 / InpRsiPeriod=14 / InpRsiOversold=30 / InpRsiOverbought=70
=== 出场 ===        InpSlPoints=50 / InpTpPoints=100 (RR 1:2) / InpMaxHoldMinutes=30
=== 风控 ===        InpRiskPercent=0.5% / InpMaxPositions=3 / InpMaxTradesPerDay=20 / InpMaxDailyDrawdownPct=3% / InpMagicNumber=20240604
=== 过滤 ===        InpMaxSpreadPoints=50 / InpAtrMin=0.5 / InpAtrMax=5.0 / InpSessionStartHour=8 / InpSessionEndHour=23 / InpFridayNoTradeAfter20=true
=== 新闻 ===        InpEnableNewsFilter=true / InpNewsMinBefore=30 / InpNewsMinAfter=30 / InpNewsCsvPath="news_calendar.csv"
=== v2 指标 ===     InpComputeMetricsInEA=true / InpMetricsLogEveryNTrades=10
=== 显示/日志 ===   InpEAComment="ScalperXAUv2" / InpShowDashboard=true / InpEnableLog=true / InpEnableNotify=true / InpDdAlertPct=5.0
=== CSV ===         InpLogTradesToCsv=true / InpCsvFilePrefix="trades_ScalperXAUv2_"
```

## 6. 调参 variants (3 套)

| 名称 | BB | RSI | SL/TP | Risk | MaxPos | Trades/Day | 适用 |
|------|----|----|-------|------|--------|------------|------|
| **Balanced** (default) | 20/2.0 | 14 / 30,70 | 50/100 | 0.5% | 3 | 20 | 普通市场 |
| **Aggressive** (AGG) | 15/1.8 | 10 / 25,75 | 30/60 | 1.0% | 4 | 40 | 高波动, 多信号 |
| **Conservative** (CON) | 30/2.5 | 21 / 35,65 | 80/160 | 0.3% | 2 | 10 | 低波动, 少信号 |

`InpBbPeriod=20||20||10||40||N` 格式: `value||default||start||step||end||N` 是 MT5 .set 优化格式, GUI 加载即可。

## 7. 实施步骤 (Status)

1. ✅ v1 EA 写完 + 编译过 (.ex5 89KB, 9 步 plan 第 1 步)
2. ✅ v2 EA 写完 + 编译过 (.ex5 104KB, 24 input, 23 列 CSV, 11 个 EA 内指标)
3. ✅ .set 模板 + 3 套调参 variant
4. ✅ .ini 配置文件 (Modeling=1 1min OHLC, 2026.05.01-06.01)
5. ⏳ GUI backtest 跑 (用户点 "回测" 按钮, ~1-2 min)
6. ⏳ 报告分析 (Node mql5-report-analyzer.mjs, 4 目标自动判定)
7. ⏳ 调参 (基于报告换 .set, 重 backtest)
8. ⏳ 模拟盘 24h (attach EA → XAUUSDm M1, 抓 trades CSV)
9. ⏳ live 数据分析 + 调参 + 再跑 24h, 直到达目标

## 8. 成功标准

| 目标 | 阈值 | 说明 |
|------|------|------|
| Net Profit | > 0 | 整体盈利 |
| Profit Factor | > 1.3 | 总盈利/总亏损 |
| Max Drawdown | < 15% | 最大回撤 |
| Win Rate | > 55% | 胜率 |
| Sharpe Ratio | > 1.0 (附加) | 风险调整后 |
| Total Trades | ≥ 50 (附加) | 样本量 |

## 9. 文件位置

- EA 源码: `MQL5/Experts/minimax-ea/ScalperXAU.mq5` (v2)
- 编译产物: `MQL5/Experts/minimax-ea/ScalperXAU.ex5` (v2)
- .set 默认: `MQL5/Profiles/Tester/ScalperXAUv2.set`
- .set 激进: `MQL5/Profiles/Tester/ScalperXAUv2_AGG.set`
- .set 保守: `MQL5/Profiles/Tester/ScalperXAUv2_CON.set`
- .ini 模板: `MQL5/Profiles/Tester/ScalperXAUv2.XAUUSDm.M1.last_month.000.ini`
- 新闻 CSV: `MQL5/Files/news_calendar.csv`
- 报告分析器: `C:\Users\Administrator\mql5-report-analyzer.mjs`
- 报告 watcher: `C:\Users\Administrator\mt5-report-watcher.ps1`

## 10. Backtest 工作流 (推荐)

```powershell
# 1. 跑 watcher 持续监控 (一次性也行)
.\mt5-report-watcher.ps1 -Once

# 2. MT5 GUI 点 "回测" → Strategy Tester 自动从 .ini 加载 → Start

# 3. 跑完自动写 XML 到 Tester/Reports/ScalperXAUv2.xml

# 4. watcher 检测到新 XML → 自动跑分析 → 输出 .summary.md

# 5. 看 summary.md → 调参 → 改 .set → 重 backtest
```

## 11. 实盘 / 模拟盘 24h 验证

```powershell
# attach EA 到 XAUUSDm M1 (MT5 GUI 拖拽 或 Navigator → Expert Advisors → ScalperXAU)
# 24h 后抓 trades CSV: MQL5/Files/trades_ScalperXAUv2_YYYYMMDD.csv
# 用 Node 解析 CSV → 算 v2 指标 → 对比 backtest
# 偏差 > 30% 触发调参
```
