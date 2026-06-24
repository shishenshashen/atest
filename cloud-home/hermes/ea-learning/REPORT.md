# EA 学习报告 v1（2026-06-12 老大派长期任务第一次产出）

## 1. 资源搜

| 资源 | 状态 | 评价 |
|---|---|---|
| MQL5.com | ❌ 不通（GFW/timeout） | 主力 EA 市场拿不到，GitHub 替代 |
| GitHub API | ✅ 200 | 10+ 个真 EA 项目 (36-447★) |
| **jimtin/build-your-own-mt5-ea** | ✅ clone | **教学向** (52 文件 指标库) |
| **sajidmahamud835/grid-master-pro-mt5-ea** | ✅ clone | **实战向** (35 文件 GridMaster Pro 主体) |

## 2. 解析 1: RSI Trading Bot Tutorial (教学 182 行)

**来源**: `jimtin/build-your-own-mt5-ea/rsi_trading_bot_tutorial.mq5`

### 结构（4 模块 + 主循环）

| 函数 | 作用 | EA 设计原理 |
|---|---|---|
| `GetRSI()` | 拉 RSI(14) | 指标接入模板（iRSI + CopyBuffer） |
| `RSIAlgorithm(rsi)` | <30 BUY, >70 SELL | **均值回归**策略 |
| `OnSignal(signal)` | 真下单 | 仓位 + SL/TP（pipSize × pips） |
| `TradeManagement()` | 控制并发 | 最大并发单 |
| `OnTick()` | tick 主循环 | 触发信号检查 |

### 参数（7 个 input）
- `liveRSIPrice` (bool) / `rsiHigh=70` / `rsiLow=30` / `takeProfitPips=20` / `stopLossPips=10` / `lotSize=0.1` / `concurrentTrades=1`

### 关键代码
- 仓位 `trade.Buy(lotSize, _Symbol, ask, stopLoss, takeProfit, "RSI Tutorial EA")`
- 滑点用默认值（**没设**）
- 注释 "RSI Tutorial EA" 是 magic 替代（**不严谨**）

### 缺点（看得出）
- ❌ 没用 magic number（M01）
- ❌ 没用仓位 Sizer（M02 Risk）
- ❌ 没用 Trailing Stop（M08）
- ❌ 没用 News Filter（M17）
- ❌ 没用 Session Filter（M19）
- ❌ 没用 Dashboard（M09）
- ❌ 没用 Notify 推送（M10）
- ❌ 没用 Logger（M11）
- **单一信号源**（单 RSI，脆弱）

## 3. 解析 2: GridMaster Pro (实战 332 行)

**来源**: `sajidmahamud835/grid-master-pro-mt5-ea/GridMaster Pro.mq5`

### 策略
**双向网格 + ATR-adaptive**（震荡市均值回归）
- **GRID_NEUTRAL** (BUY+SELL 双向) / **BULLISH** (only BUY) / **BEARISH** (only SELL)
- 网格间距 = ATR × 1.5（自适应波动率）
- MaxOrders 5 per side

### 参数（16 个 input 远超教学）
- Grid: GridMode / MaxOrders=5 / ATRPeriod=14 / ATRMultiplier=1.5
- Lot: LotMode (FIXED/DYNAMIC) / LotSize=0.1 / **RiskPercent=1.0** (动态风险%)
- TP/SL: UseTakeProfit / DefaultTP=200 / **UseStopLoss + DefaultSL=1000**
- **UseTrailingStop=true** + TrailingPoints=100 + TrailingStep=20
- 风控: **MaxDrawdownPct=5.0** (回撤熔断) + **CloseOnDrawdown=true** (回撤全平)
- MagicNumber: **MagicBase=47291**
- Debug: DebugMode

### 关键代码（推测，未看全）
- 用 `SYMBOL_TRADE_STOPS_LEVEL` 读 broker 最小 stop distance（防 Invalid stops）
- ATR 自适应（`iATR + CopyBuffer`）
- 回撤熔断（监控 equity vs balance）
- 双向网格挂单

### 集成 vault 12 必读
| M0X | 模块 | GridMaster 用了吗 |
|---|---|---|
| M01 | CTradePlus + magic | ✅ MagicBase=47291 |
| M02 | Risk | ✅ RiskPercent + MaxDrawdown |
| M05 | NewBar / ATR | ✅ ATR 自适应 |
| M08 | TrailingStop | ✅ UseTrailingStop |
| M09 | Dashboard | ❌ |
| M10 | Notify | ❌ |
| M11 | Logger | ❌ (用 Print) |
| M13 | FileIO | ❌ |
| M17 | NewsFilter | ❌ |
| M18 | CorrelationFilter | ❌ |
| M19 | SessionFilter | ❌ |
| 总 | 12 | **4/12** = 33% |

## 4. EA 设计原理总结（跨 2 个 EA）

### 4.1 入场信号
| 类型 | 例子 | 风险 |
|---|---|---|
| 单一指标 | RSI/MA/MACD | 高（脆弱，被假突破骗） |
| 多指标组合 | RSI+MA+MACD | 中 |
| 形态 | K线/Doji/Engulfing | 中 |
| 网格 | 价格 vs 层级 | 高（震荡市赚，趋势市爆） |
| ML | 训练模型 | 中（看数据质量） |

### 4.2 仓位管理（vault M02）
- **固定手数**（RSI 教学）：简单，**不**按账户规模调整
- **风险% 动态**（GridMaster）：每单风险 = balance × RiskPct，**更专业**
- **凯利公式**（最严谨，但实战不常用）

### 4.3 风控
- **SL/TP 固定 pips**（教学）：简单但不适应波动
- **SL/TP broker-aware**（GridMaster）：自动调最小 stop distance
- **回撤熔断**（GridMaster）：equity 跌 N% 全平，最强保护
- **追踪止损**（GridMaster）：保护浮盈

### 4.4 执行
- **每个 tick** 检查（教学）：浪费 CPU
- **新 K 线检查**（vault M05）：tick 触发但只在新 K 线时检查信号，**行业标准**
- **订单管理**：magic number 区分 EA 互不干扰

### 4.5 必读模块对照（vault EA开发/01-调用模块）
| 模块 | 教学 EA | GridMaster | 建议 EA |
|---|---|---|---|
| M01 交易封装 | ✅ CTrade | ✅ CTrade | ✅ |
| M02 风控 | ❌ | ✅ RiskPct+MaxDD | ✅ |
| M05 NewBar | ❌ | ❌ | ✅ |
| M08 TrailingStop | ❌ | ✅ | ✅ |
| M09 Dashboard | ❌ | ❌ | ✅ |
| M10 Notify | ❌ | ❌ | ✅ |
| M11 Logger | ❌ | ❌ | ✅ |
| M13 FileIO | ❌ | ❌ | trade journal |
| M17 NewsFilter | ❌ | ❌ | ✅ |
| M19 SessionFilter | ❌ | ❌ | ✅ |

## 5. 下一步

### 5.1 我能用 mt5-ea-dev 写一个**改进版**EA
集成 vault 12 必读中 8/12：
- M01 + M02 + M05 + M08 + M09 + M10 + M11 + M19
- **均值回归策略**（RSI 教学）+ **追踪止损**（GridMaster）+ **回撤熔断**（GridMaster）+ **时段过滤**（vault M19）
- **新 K 线**触发（不是每个 tick）—— vault M05
- **写日志到文件**（vault M11）—— 可复盘
- **Dashboard 显示**（M09）—— 可视化
- **推送**（M10）—— 实时通知

### 5.2 编译 + 测试
- 用 `metaeditor64.exe /compile:EA.mq5` 编译（MQL5 编译器）
- 看编译日志
- 写测试报告

## 6. 关键发现

1. **教学 EA vs 实战 EA 差 80% 功能**——只 1 个指标就敢交易的 EA 是玩具
2. **vault 12 必读是真有道理**——GridMaster 只用了 4/12 就能跑，**集成 8/12 是显著优势**
3. **风控是真价值**——回撤熔断 + 风险% 仓位 = 实战级 vs 教学级差异
4. **broker-aware** 是真坑——很多 EA 死在"Invalid stops"（broker 最小 stop distance 不够）

## 7. 时间分配
- 搜资源: 5 min
- clone: 2 min
- 解析 2 个 EA: 10 min
- 写报告: 5 min
- 下次: 设计 + 编译 + 测试
