# ScalperXAU v3 - Bollinger RSI ADX Trail 均值回归 (XAUUSDm M1)

> v3 升级: 加 M08 TrailingStop + ADX 过滤 + 频率控制 + HasDirection + NormalizeDouble + EMPTY_VALUE 检查
>
> v1→v2: 加 MFE/MAE/ExitReason + EA 内指标 (23 列 CSV)
> v2→v3: 加 M08 trail + ADX + 频率控制 (3 个关键能力, 库里有 v2 没用)

## 1. 策略核心

均值回归 + 剥头皮 + 追踪止损。XAUUSDm M1。
- **触发**: 价格触及 BB 上下轨
- **过滤**: RSI 超买/超卖 + ADX<25 (非强趋势)
- **风控**: 固定 SL/TP (RR 1:2) + 浮盈追踪止损 + 单笔 0.5% + 最大持仓 3 + 频率限制
- **防同向**: HasDirection (同方向不开新仓)

## 2. v3 升级 (相对 v2)

| 模块 | 用途 | 默认参数 |
|------|------|----------|
| **M08 TrailingStop** | 浮盈抬 SL 锁利 | start=40, step=20, minGap=10 |
| **ADX 过滤** | 强趋势不开逆势 | period=14, max=25 |
| **频率控制** | 防经纪商限 | minSec=30, maxPerHour=6 |
| **HasDirection** | 防同向重复 | - |
| **NormalizeDouble** | SL/TP 精度 | _Digits |
| **EMPTY_VALUE 检查** | 指标失效跳过 | - |
| **SYMBOL_TRADE_STOPS_LEVEL** | 最小止损距离 | 经纪商限制 |
| **CSV 新增** | adx_at_entry 列 | - |
| **仪表盘新增** | ADX 行 | - |

## 3. 完整 input 参数 (32 个)

```
=== 策略 ===        InpBbPeriod=20 / InpBbDeviation=2.0 / InpRsiPeriod=14 / InpRsiOversold=30 / InpRsiOverbought=70

=== 出场 固定 ===   InpSlPoints=50 / InpTpPoints=100 (RR 1:2) / InpMaxHoldMinutes=30

=== 出场 M08 ===    InpUseTrail=true / InpTrailStartPoints=40 / InpTrailStepPoints=20 / InpTrailMinGapPoints=10

=== 风控 ===        InpRiskPercent=0.5% / InpMaxPositions=3 / InpMaxTradesPerDay=20
                    InpMaxDailyDrawdownPct=3% / InpMagicNumber=20240604 / InpDeviationPoints=20

=== 过滤 ===        InpMaxSpreadPoints=50 / InpAtrMin=0.5 / InpAtrMax=5.0
                    InpSessionStartHour=8 / InpSessionEndHour=23 / InpFridayNoTradeAfter20=true

=== ADX ===         InpUseAdxFilter=true / InpAdxPeriod=14 / InpAdxMax=25

=== 频率 ===        InpMinSecBetweenTrades=30 / InpMaxTradesPerHour=6

=== 新闻 ===        InpEnableNewsFilter=true / InpNewsMinBefore=30 / InpNewsMinAfter=30 / InpNewsCsvPath="news_calendar.csv"

=== 指标 ===        InpComputeMetricsInEA=true / InpMetricsLogEveryNTrades=10

=== 显示 ===        InpEAComment="ScalperXAUv3" / InpShowDashboard=true / InpEnableLog=true
                    InpEnableNotify=true / InpDdAlertPct=5.0

=== CSV ===         InpLogTradesToCsv=true / InpCsvFilePrefix="trades_ScalperXAUv3_"
```

## 4. CSV Schema (v3, 24 列)

```csv
time,symbol,direction,type,volume,price,profit,swap,commission,net_pnl,
open_time,close_time,duration_sec,sl_price,tp_price,
exit_reason,mfe_pips,mae_pips,spread_at_entry,slippage_pts,adx_at_entry,
magic,order_id,comment
```

新增 `adx_at_entry` 列 (ADX 当时主值)。

## 5. Exit Reason 分类 (v3)

| 原因 | 触发 | CSV 字段 |
|------|------|----------|
| `OPEN` | 入口 deal | `SL_HIT` (v2 改 `TRAIL_OR_MANUAL`) |
| `SL_HIT` | 固定 SL 触发 | ✓ |
| `TP_HIT` | 固定 TP 触发 | ✓ |
| `TRAIL_OR_MANUAL` | 追踪止损触发 OR 信号反向 OR 手动 | ✓ |
| `TIMEOUT` | 持仓 > MaxHoldMinutes | 由 M10 通知, CSV 不写 (timeout 后真 close 才是 CLOSE) |

## 6. 调参 variants (3 套 v3)

| 名称 | BB | RSI | SL/TP | Risk | MaxPos | Trail | ADX | 适用 |
|------|----|----|-------|------|--------|-------|-----|------|
| **Balanced** | 20/2.0 | 14/30,70 | 50/100 | 0.5% | 3 | 40/20 | 25 | 普通市场 |
| **Aggressive** | 15/1.8 | 10/25,75 | 30/60 | 1.0% | 4 | 25/15 | 22 | 高波动 |
| **Conservative** | 30/2.5 | 21/35,65 | 80/160 | 0.3% | 2 | 60/30 | 28 | 低波动 |

`.set` 文件: `MQL5/Profiles/Tester/ScalperXAUv3_*.set`

## 7. MQL5Kit 模块使用 (v3 集成 13 个)

| 模块 | v3 用法 |
|------|---------|
| M01 CTradePlus | `Init(magic, deviation)` / `Buy/Sell` / `ClosePos` / `ModifySLTP` (M08 用) |
| M02 Risk | `Init(magic, maxPos, riskPct)` / `CanOpen` |
| M03 PositionSizing | `Init(riskPct)` / `LotByRisk` |
| M04 IndicatorPool | 池化 (实际直接用 handle) |
| M05 NewBar | `Init(_Period)` / `IsNewBar` |
| M07 Positions | `Count` / `HasDirection` (v3 新加) |
| **M08 TrailingStop** | **v3 新加** `Init/SetParams/Apply` |
| M09 Dashboard | `Clear/SetTitle/Row/Separator/Show` |
| M10 Notify | `Trade/Send` (push+sound) |
| M11 Logger | `SetFileOutput/Trade/Close` |
| M13 FileIO | `AppendCSV` (v3 CSV 写) |
| M16 Cleanup | `CleanupAll/DeleteMyObjects` (OnDeinit) |
| M17 NewsFilter | `LoadFromCSV/IsNearEvent` |

## 8. 文件位置

- EA 源码: `MQL5/Experts/minimax-ea/ScalperXAU.mq5` (v3)
- 编译产物: `MQL5/Experts/minimax-ea/ScalperXAU.ex5` (v3, 111KB)
- .set 默认: `MQL5/Profiles/Tester/ScalperXAUv3.set`
- .set 激进: `MQL5/Profiles/Tester/ScalperXAUv3_AGG.set`
- .set 保守: `MQL5/Profiles/Tester/ScalperXAUv3_CON.set`
- .ini: `MQL5/Profiles/Tester/ScalperXAUv3.XAUUSDm.M1.last_month.000.ini`
- 新闻 CSV: `MQL5/Files/news_calendar.csv`
- 报告分析器: `C:\Users\Administrator\mql5-report-analyzer.mjs`
- 报告 watcher: `C:\Users\Administrator\mt5-report-watcher.ps1`

## 9. Backtest 工作流 (跟 v2 一样, 文件名换 v3)

```powershell
# 1. 跑 watcher 监控
.\mt5-report-watcher.ps1 -Once

# 2. MT5 GUI 点 "回测" → Strategy Tester 自动从 .ini 加载 → Start

# 3. 报告自动写到 Tester/Reports/ScalperXAUv3.xml

# 4. watcher 检测到 → 自动跑分析 → 输出 .summary.md
```

## 10. v3 vs v2 性能预期

| 维度 | v2 | v3 |
|------|-----|-----|
| 编译 size | 104KB | 111KB |
| 入场条件 | BB+RSI | BB+RSI+ADX |
| 频率 | 无限制 | 30s/6h |
| 出场 | 固定 SL/TP + timeout | 固定 SL/TP + M08 trail + timeout |
| 强趋势表现 | 大亏 (逆势) | 跳过 |
| 胜率 | ~55% | ~60% (ADX 排除逆势假信号) |
| 最大回撤 | ~12% | ~8% (trail 锁利) |

## 11. 后续迭代 (v4 计划)

跑完 v3 backtest + 24h demo 后, 基于实测数据:
- **如果 Net>0+PF>1.3+DD<15%+WR>55%**: attach demo 24h
- **如果没达**: 看 trade CSV:
  - ADX 是不是过滤太多 (入 < 30 笔) → 调 max 25→30
  - Trail 是不是太紧 → step 20→30
  - BB/RSI 阈值基于胜率分布调

## 12. 相关文档

- [[00 ScalperXAU 迭代纪要 v1→v2→v3]]
- [[M08 追踪止损 TrailingStop]]
- [[EA 逆势均值回归模板（RSI Bollinger）]]
- [[EA 剥头皮模板]]
- [[04 避坑 - 必查清单]]
- [[04 避坑 - 经纪商差异（点差\手数\Filling）]]
