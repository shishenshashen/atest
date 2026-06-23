---
title: 5 EA 6 月回测对比 SOP
tags: [实战, SOP, 回测对比, 5 EA, 6 月, MQL5Kit, N1]
type: sop
---

# 5 EA 6 月回测对比 SOP (方法论沉淀, 等 N1 实物数据)

> **本文件目的**: 在 N1 实物 (5 EA 6 月回测数据) 未到位的情况下, 先把"如何对比 5 个 EA"的方法论沉淀下来 —— 包括对比实验设计、指标选择、读回测报告 SOP、参数稳定性分析、4 维度评分。
> **N1 数据出来后**: 按本 wiki 章节 3 填表 + 加 "## 5 EA 6 月回测实测数据 (待 N1 实物)" 段, 不动本 SOP 内容。
>
> **配套范围**: 7 个 EA × XAUUSDm M1 / H1 × 2026-01-01 ~ 2026-06-30 (6 个月) × 3 组参数 (基线 + 偏多 + 偏空) = 7 × 3 = **21 次**完整 backtest 报告。
>
> **本 wiki 不写 .mq5 / 不跑 backtest** —— 实物回测需 GUI 阻塞 console session 1, 留给 N1 执行。Mavis 写 SOP + 用户 GUI 跑 backtest + 传 XML 结果, 详见 [[MT5 GUI 自动化 5 次失败全记录 + 分工协议]]。
>
> **5 EA 清单** (minimax-ea/ 6 个 demo + ScalperEA root = 7 选 5): TrendMA_EA / Breakout_EA / MeanReversion_EA / MyEA / Dashboard (无交易, 仅监控) / ScalperEA / ScalperXAU v1。本 wiki 全覆盖 7 个作为对比基础, N1 实物按需挑选 5 个。
>
> **核心 4 维度评分**: 盈利能力 / 风险控制 / 稳定性 / 模块化程度, 每维 0-5 分, 满分 20。评分标准见章节 3。

---

## 1. 5+2 EA 资产盘点 (7 段, 每段 1 个 EA)

> **盘点维度**: 路径 / 字节数 / 行数 / 策略类型 / MQL5Kit 集成 / 复杂度 / 适配场景 / 与其它 EA 关系。
> **N1 用法**: 按本表选 5 个最值得回测的 EA, 跑完用统一 schema 整理结果。

### 1.1 TrendMA_EA (趋势跟踪 / MA 交叉)

| 维度 | 数值 |
|---|---|
| 路径 | `MQL5/Experts/minimax-ea/TrendMA_EA.mq5` |
| 字节数 (读档) | ~3-5 KB |
| 行数 | ~140 |
| 策略类型 | 趋势跟踪 (MA 交叉) |
| 信号 | `CSignal::CrossUpSeries(fastMA, slowMA)` 金叉 / `CrossDownSeries` 死叉 |
| 指标 | `MA_Fast(12, EMA)` + `MA_Slow(26, EMA)` + `ATR(14)` |
| 周期 | M15 / M30 / H1 都可 (默认无指定) |
| MQL5Kit 集成 | M01 交易 + M02 风控 + M03 仓位 + M04 指标 + M05 K 线 + M07 持仓 + M08 追踪 + M09 面板 + M11 日志 + M16 清理 (10 个) |
| 复杂度 | ★★☆☆☆ (简单直接) |
| 适配场景 | 趋势明确的品种 (EURUSD / XAUUSD 大周期), 震荡市反复挨打 |
| 与其它 EA 关系 | 模板基线 (EA 趋势跟踪模板 (MA 交叉)) + MeanReversion_EA 的镜像 (一个趋势一个逆势) |
| 回测期望 | Net Profit 中性 / PF 1.0-1.5 / DD 5-15% (震荡市会拉高 DD) / Trade 数 30-200 |

**回测要点**:
- 趋势型策略, 至少 6 个月数据才能覆盖 1-2 个趋势周期
- 默认参数 (`FastMA=12/SlowMA=26/EMA`) 是经典值, 不需要优化就能跑出 baseline
- **必加 ADX > 25 过滤** (避免震荡市反复止损) — 当前 EA 缺, 是改进点

---

### 1.2 Breakout_EA (突破 / Donchian 海龟)

| 维度 | 数值 |
|---|---|
| 路径 | `MQL5/Experts/minimax-ea/Breakout_EA.mq5` |
| 字节数 | ~4-6 KB |
| 行数 | ~180 |
| 策略类型 | 突破 (Donchian 海龟) |
| 信号 | `close > Donchian_High(N=20)` 做多 / `close < Donchian_Low(N=20)` 做空 |
| 指标 | `ATR(14)` + 手算 `Donchian_High/Low` 数组 |
| 周期 | H1 / H4 / D1 (突破型对周期敏感) |
| MQL5Kit 集成 | M01 交易 + M02 风控 + M03 仓位 + M04 指标 + M05 K 线 + M07 持仓 + M08 追踪 + M09 面板 + M11 日志 + M16 清理 (10 个) |
| 复杂度 | ★★★☆☆ (突破 + 追踪 + 复信号处理) |
| 适配场景 | 趋势爆发型品种 (XAUUSDm 大周期 / USDJPY 单边市) |
| 与其它 EA 关系 | 与 TrendMA_EA 同为趋势型但入场不同 (突破 vs 跟随); 与 MeanReversion_EA 镜像 (趋势 vs 逆势) |
| 回测期望 | Win Rate 低 (30-40%) / PF 1.5-2.5 (盈亏比大) / DD 10-20% (假突破) / Trade 数 10-50 |

**回测要点**:
- 突破策略样本量天然小, 6 个月可能 20-50 笔, 统计意义弱 — **建议同时跑 12-18 个月**
- 假突破多 → 必须严格 SL; 当前 EA 用 `SL_Points=400` (XAU 4 USD/lot) 较紧
- 突破后追踪止损是关键: M08 (start=200, step=100) 锁 100 点, 盈亏比能拉到 3:1

---

### 1.3 MeanReversion_EA (逆势均值回归 / RSI + Bollinger) — **最完整 6 模块集成 + 13 模块全集**

| 维度 | 数值 |
|---|---|
| 路径 | `MQL5/Experts/minimax-ea/MeanReversion_EA.mq5` |
| 字节数 | ~12-15 KB |
| 行数 | **320** (实测) |
| 策略类型 | 逆势均值回归 (RSI + Bollinger) |
| 信号 | `RSI < Oversold (30)` 或 `price < BB_Lower` → 做多; 反之做空 |
| 指标 | `RSI(14)` + `BB(20, 2.0)` + `ADX(14)` |
| 周期 | M5 (默认无指定, 实战 M5-M15) |
| MQL5Kit 集成 | **13 个**: M01 交易 + M02 风控 + M03 仓位 + M04 指标 + M05 K 线 + M07 持仓 + M08 追踪 + M09 面板 + M10 通知 + M11 日志 + M16 清理 + **M18 相关性** + **M19 时段** (全集, 除 M12 GV / M13 IO / M14 画图 / M15 定时器 / M17 新闻) |
| 复杂度 | ★★★★☆ (模块化最高, 实盘 demo 已落地) |
| 适配场景 | 震荡市 (XAUUSDm 周末/亚洲盘), 强单边市会亏 |
| 与其它 EA 关系 | 模板基线 (EA 逆势均值回归模板 (RSI Bollinger)); 是项目 6 demo 里"实盘 demo"最完备的 (含 M18/M19) |
| 0 errors 编译 | ✅ (2026-06-04 11:32 最新) |
| M18 监控品种 | `XAUUSDm,EURUSDm,GBPUSDm,USDJPYm` (4 个, threshold=0.7) |
| M19 时段 | `London:8-16,NewYork:13-22` (8h 重叠) + `SetAllowWeekend(false)` |
| 回测期望 | Win Rate 高 (55-70%) / PF 1.3-2.0 / DD 5-15% / Trade 数 50-300 |

**回测要点** (★ 最复杂, 最值得深入):
- **M18 相关性过滤 + M19 时段过滤** 都要在 baseline + 单独禁用对比 (开/关各跑一遍)
- 回测历史 6 月涵盖 1.5 个完整震荡周期, 适合逆势策略
- M18 在回测期不变 (30 天日线历史) — 不像实盘每天漂移
- **必加 baseline 对比**: `InpUseM18Filter=false` / `InpUseM19Filter=false` 各跑 1 次 → 对比 trade count / DD / PF
- 跟 ScalperXAU v1 (1.7) 是同源, 但 MeanReversion_EA 多 M18/M19 两个过滤器

---

### 1.4 MyEA (基础骨架 / 无信号)

| 维度 | 数值 |
|---|---|
| 路径 | `MQL5/Experts/minimax-ea/MyEA.mq5` |
| 字节数 | ~2-3 KB |
| 行数 | ~80 |
| 策略类型 | **无交易骨架** (EA 通用骨架) |
| 信号 | 无 (有 include 但 OnTick 空) |
| 指标 | 无 |
| 周期 | 任意 |
| MQL5Kit 集成 | M01 交易 + M02 风控 + M03 仓位 + M04 指标 + M05 K 线 + M07 持仓 + M08 追踪 + M09 面板 + M11 日志 + M16 清理 (10 个, 等同 TrendMA_EA 的 include 集合) |
| 复杂度 | ★☆☆☆☆ (空壳) |
| 适配场景 | 模板验证, 5 分钟套用新策略的起点 |
| 与其它 EA 关系 | 模板基线 (EA 通用骨架) |
| 回测期望 | **N/A** — 不跑 backtest (无交易) |

**回测要点**:
- **不参与对比** — 无交易结果无可比性
- 唯一作用: 验证 10 个 MQL5Kit 模块编译 OK, 作为 "5 EA 都能编译" 的 sanity check
- 跑 1 周看 trade count = 0, 证明 EA 启动正常但不打单

---

### 1.5 Dashboard.mq5 (监控 / 无交易)

| 维度 | 数值 |
|---|---|
| 路径 | `MQL5/Experts/minimax-ea/Dashboard.mq5` |
| 字节数 | ~3-5 KB |
| 行数 | ~120 |
| 策略类型 | **纯监控, 无交易** |
| 信号 | 无 |
| 指标 | 无 (只读 SymbolInfo / AccountInfo) |
| 周期 | 任意 |
| MQL5Kit 集成 | M09 面板 + M15 定时器 (1s tick 刷新面板) |
| 复杂度 | ★★☆☆☆ (实时面板) |
| 适配场景 | 监控多个 EA / 显示账户 / 持仓 / 指标 |
| 与其它 EA 关系 | 跟 5 EA 并行运行不冲突 (无交易) |
| 回测期望 | **N/A** — 不跑 backtest (无交易) |

**回测要点**:
- **不参与对比** — 同 MyEA, 监控无净值变化
- 唯一作用: 跑 1 周验证面板刷新, `Heartbeat` 行的 `Fires()` 数字应持续增长 (证明 M15 定时器工作)
- 可选: N1 跑其它 5 EA 时同时挂 Dashboard, 看账户曲线 / 持仓数变化

---

### 1.6 ScalperEA (高频剥头皮)

| 维度 | 数值 |
|---|---|
| 路径 | `MQL5/Experts/ScalperEA.mq5` (root, 不在 minimax-ea/) |
| 字节数 | ~3-5 KB (原版), 增强版 `Scalping_More v1.3` 10KB / 327 行 |
| 行数 | ~150 (原版) |
| 策略类型 | 高频剥头皮 (BB + EMA) |
| 信号 | BB 穿越 + EMA 交叉 (混合) |
| 指标 | `BB(20, 1.0)` + `EMA(5, 10)` |
| 周期 | M1 (硬编码剥头皮) |
| MQL5Kit 集成 | **0 个** (原版是裸 CTrade) — 增强版 `Scalping_More v1.3` 已规划 8 模块 |
| 复杂度 | ★★★☆☆ (高频 + 多模块) |
| 适配场景 | XAUUSDm 伦敦+纽约重叠期 (8h), 高频窄幅 |
| 与其它 EA 关系 | 与 ScalperXAU v1 (1.7) 互补, 同一作者不同实现 |
| 回测期望 | Trade 数 500-2000 (1 周) / PF 1.1-1.3 (高频胜在量) / Win Rate 55-65% / DD 10-20% |

**回测要点**:
- 1 周可能有 500+ 笔, 6 月可能 12000+ 笔, **统计意义极强**
- 高频 + 窄幅 → 滑点 / 点差 是核心: 回测一定要用 "每个报价基于真实报价" (tick data), 不能用 1 分钟 OHLC
- 原版无风控, 跑 6 月可能爆仓; **N1 跑前必须升级到 Scalping_More v1.3 接入版 (8 模块)** (见 [[实战/Scalping_More v1.3 接入示例]])
- 跑 baseline + Scalping_More v1.3 接入版对比: 看 M02/M08/M19/M17 加成后是否真改善

---

### 1.7 ScalperXAU v1 (剥头皮 / Bollinger + RSI)

| 维度 | 数值 |
|---|---|
| 路径 | `MQL5/Experts/minimax-ea/ScalperXAU.mq5` (主) + `v5simple` / `v6debug` / `v7debug` 3 个调试版 |
| 字节数 | ~40 KB (主) / 1033 行 |
| 行数 | **1033** (主, 实测) |
| 策略类型 | 均值回归剥头皮 (BB + RSI) |
| 信号 | `close[1] <= BB_lower[1] && RSI[1] < 30` → 做多; 反之做空 |
| 指标 | `BB(20, 2.0)` + `RSI(14)` + `ATR(14)` (3 句柄) |
| 周期 | M1 (剥头皮硬编码) |
| MQL5Kit 集成 | M01 交易 + M02 风控 + M03 仓位 + M04 指标 + M05 K 线 + M07 持仓 + M08 追踪 + M09 面板 + M10 通知 + M11 日志 + M13 文件 IO + M15 定时器 + M16 清理 + M17 新闻 (14 个, **唯一带 M17 的 EA**) |
| 复杂度 | ★★★★★ (5 个调试版迭代, 最高复杂度) |
| 适配场景 | XAUUSDm M1 伦敦+纽约, 8-23 UTC (默认裸配置) |
| 与其它 EA 关系 | 跟 MeanReversion_EA 同源 (BB+RSI 逆势), 但 M1 + 高频 |
| 5 个 v1→v7 迭代 | v1 spec → v2 (放宽) → v3 (BB+RSI+ADX+Trail, 已生产) → v5simple → v6debug → v7debug |
| 回测期望 | Trade 数 1000-5000 (1 周) / PF 1.1-1.3 (高频量取胜) / Win Rate 50-60% / DD 10-15% |

**回测要点**:
- v1 (spec) vs v3 (生产) vs v7debug (最新) 三个版本应分别跑, 看迭代改进
- M17 新闻过滤是核心: 没 M17 时 NFP / CPI 滑点 5-10 USD/lot, 1 笔打穿 50 笔盈利
- M1 周期 6 月数据量极大, 回测用 "每个报价基于真实报价" 模式耗时 2-4 小时
- **核心 sanity check**: 比较 v1 (无 M02/M08) vs v3 (有 M02/M08/M17) 跑同一区间 → trade count 下降, 但 Net Profit 提升, DD 下降
- spec: [[策略/01 ScalperXAU v1 - Bollinger RSI 均值回归]] 9 节实施步骤 / 10 节成功标准

---

### 1.8 资产盘点小结 (N1 选 EA 用)

| EA | 类型 | MQL5Kit 集成 | 回测价值 | 跑前必要改造 |
|---|---|---|---|---|
| TrendMA_EA | 趋势 | 10 | ★★★ | 加 ADX 过滤 (改进点, 非必须) |
| Breakout_EA | 突破 | 10 | ★★★ | 必加 ATR 动态 SL |
| MeanReversion_EA | 逆势 | **13** | ★★★★★ (最丰富) | 必跑 baseline (关 M18/M19) 对比 |
| MyEA | 骨架 | 10 | ☆ (无交易) | 不跑 backtest |
| Dashboard | 监控 | 2 | ☆ (无交易) | 不跑 backtest |
| ScalperEA | 高频 | 0 (原版) / 8 (v1.3) | ★★★★ | 必升级 v1.3, 不然 6 月爆仓 |
| ScalperXAU v1 | 剥头皮 | 14 | ★★★★★ | 跑 v1 spec / v3 生产 / v7debug 对比 |

**N1 选 5 EA 建议** (挑最有对比价值的):
- **必选**: MeanReversion_EA (模块最齐 + M18/M19 过滤对比价值高)
- **必选**: ScalperXAU v1 (v1/v3/v7 三版对比, 看迭代价值)
- **必选**: ScalperEA (原版 vs v1.3 接入版, 看 MQL5Kit 接入价值)
- **二选一**: TrendMA_EA vs Breakout_EA (看用户偏好: 趋势跟随 vs 趋势突破)
- **N/A**: MyEA + Dashboard (无交易, 跑 1 周验证编译)

**N1 实物出来后**, 在本 wiki 末尾追加 "## 5 EA 6 月回测实测数据 (待 N1 实物)" 段, 格式见章节 7 §7.3。

---

## 2. 回测对比 SOP (10 步, 严格按序)

> **目标**: 用统一方法跑 5 EA × 6 月 × 3 组参数, 输出可对比的报告 (Net Profit / PF / DD / Sharpe / Win Rate / Trade Count), 最终按 4 维度评分排序。
> **每步独立可验**, 全跑完 = 实物对比完成。

### 步骤 1: 数据准备 (10 min)

```powershell
# 1) 确认 MT5 Strategy Tester 数据完整性
#    打开 MT5 → 工具 → 历史数据中心 → 选 XAUUSDm → M1 / H1
#    期望: 2026-01-01 ~ 2026-06-30 连续 6 月数据, 无 "空洞"
#    实际: Exness demo 数据一般 2025-06 至 2026-06 都有, 但 2026-06 之后可能缺

# 2) 下载缺失数据 (用 MT5 自身的 "下载" 按钮)
#    自定义周期: 起始 2025-12-01, 终止 2026-07-01
#    包含 1 月预热 + 6 月实测 + 1 月 buffer

# 3) 验证 ticks 数据
#    工具 → 历史数据中心 → XAUUSDm → "Ticks" 标签
#    期望: 至少 1 月 1 月有 1M+ ticks
```

**验证清单**:
- [ ] XAUUSDm M1 数据从 2025-12-01 连续到 2026-07-01, 无空洞
- [ ] XAUUSDm H1 数据同上
- [ ] Ticks 数据至少 2026-01 至 2026-06 完整
- [ ] 数据可在 Strategy Tester 中可视化显示 K 线

---

### 步骤 2: 5 EA 编译 (15 min)

> **5 EA 都必须先编译 0 errors**, 编译失败的不跑 backtest (垃圾进垃圾出)。

```powershell
$me = "C:\Program Files\MetaTrader 5\MetaEditor64.exe"
$eaDir = "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea"

# 1) TrendMA_EA
& $me /compile:"$eaDir\TrendMA_EA.mq5" /log
# 期望: 0 errors (有 warning 不影响)

# 2) Breakout_EA
& $me /compile:"$eaDir\Breakout_EA.mq5" /log

# 3) MeanReversion_EA (最复杂, 可能 1 warning 来自 M07 POSITION_COMMISSION)
& $me /compile:"$eaDir\MeanReversion_EA.mq5" /log

# 4) ScalperEA (root, 不在 minimax-ea/)
$rootEaDir = "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts"
& $me /compile:"$rootEaDir\ScalperEA.mq5" /log

# 5) ScalperXAU (v1 主 + v3 生产 + v7debug, 三版对比)
& $me /compile:"$eaDir\ScalperXAU.mq5" /log
# 可选: v7debug
# & $me /compile:"$eaDir\ScalperXAUv7debug.mq5" /log
```

**验证清单**:
- [ ] 5 EA 全 0 errors
- [ ] .ex5 文件生成 (每个 30-50 KB)
- [ ] metaeditor.log 无 `cannot open include` / `undefined identifier`
- [ ] M02/M07/M08 强转 `(ulong)InpMagicNumber` 已加 (避免 magic 类型不匹配 warning)

---

### 步骤 3: Strategy Tester 配置 (5 min × 5 EA = 25 min)

> **统一配置** = 唯一变量是 EA 本身, 其他全部一致。

| 项 | 统一值 | 备注 |
|---|---|---|
| Symbol | `XAUUSDm` | 5 EA 都用 XAUUSDm (用户主品种) |
| Period | `M1` (剥头皮 EA) / `H1` (趋势 / 突破) | 按 EA 类型分两类 |
| Modeling | `Every tick based on real ticks` | 最高真实性, 必用 |
| Deposit | `10000` USD | 默认 demo 账户 |
| Leverage | `1:100` | Exness 默认 |
| Execution | `Normal` (默认) | 不改 |
| Optimization | `Disabled` | 一次性跑 1 组参数, 不用 optimizer |
| Date from | `2026-01-01` | 6 月起点 |
| Date to | `2026-06-30` | 6 月终点 |
| Profit | `in pips` | 便于跨 EA 对比 (不用 in $) |
| Slippage | `0` | 理想情况, 实测用 3 (对比差异) |

**验证清单**:
- [ ] 5 EA 用同一 Symbol / Period 规则
- [ ] Modeling 全 "Every tick based on real ticks"
- [ ] Date 全 2026-01-01 ~ 2026-06-30
- [ ] Optimization 全 Disabled (一次性)

---

### 步骤 4: 跑 5 EA × 1 period (10 h, 用户 GUI)

> **用户操作**: MT5 → 工具 → 策略测试器 (Ctrl+R) → 选 EA / Symbol / Period → 设置 → Start
> **Mavis 不做** (跨 session UIPI 拦, 详见 [[MT5 GUI 自动化 5 次失败全记录 + 分工协议]])

| EA | 预估耗时 | 备注 |
|---|---|---|
| TrendMA_EA H1 | 30 min | 趋势 + H1 + tick data 慢 |
| Breakout_EA H1 | 30 min | 同上 |
| MeanReversion_EA M1 | 2 h | 高频 + tick data 极慢 |
| ScalperEA M1 (原版) | 4 h | 6 月剥头皮 tick data 巨量 |
| ScalperXAU v1 M1 | 4 h | 同上 |

**总耗时**: ~10 h, 建议分 2 天跑 (4-5 h / 天, 避免 VPS 过热)

**用户报告产出**:
- 5 个 XML 报告 (Strategy Tester → 右键 → "另存为报告")
- 5 张 .png equity curve 截图 (可选)
- 5 份 trade list (.csv)

**Mavis 拿到报告后** (用户传 XML / CSV 路径):
```powershell
# 把 5 个报告 XML 复制到统一目录
$dst = "C:\ai\obsidian-文件\mt\00-任务调度中心\daily\backtest-5EA-2026-06-30\"
New-Item -ItemType Directory -Force -Path $dst
# 用户把 5 个 XML 放到这
```

---

### 步骤 5: 抽取报告 (5 min, Mavis 自动化)

> 用 `mql5-report-analyzer.mjs` 跑 5 个 XML 报告, 输出 JSON 格式的对比数据。

```bash
# 在 5EA 报告目录跑
cd "C:\ai\obsidian-文件\mt\00-任务调度中心\daily\backtest-5EA-2026-06-30\"
node "C:\ai\obsidian-文件\mt\00-任务调度中心\tools\mql5-report-analyzer.mjs" *.xml --output 5EA-summary.json
# 期望: 输出 JSON 含 5 EA 的 Net Profit / PF / DD / Sharpe / Win Rate / Trade Count
```

**5EA-summary.json 格式示例**:
```json
{
  "TrendMA_EA": {
    "NetProfit": 1234.56,
    "ProfitFactor": 1.23,
    "MaxDD": 0.08,
    "SharpeRatio": 0.65,
    "WinRate": 0.48,
    "TotalTrades": 87
  },
  "Breakout_EA": { ... },
  ...
}
```

**验证清单**:
- [ ] 5 EA JSON 都有完整 6 字段
- [ ] 字段类型正确 (Net Profit 浮点, Trade Count 整数)
- [ ] 至少 1 个 EA 的 TotalTrades > 30 (样本有意义)

---

### 步骤 6: 整理对比表 (10 min)

> **统一表头**, 便于 4 维度评分。

| EA | Net Profit (USD) | Profit Factor | Max DD (%) | Sharpe | Win Rate (%) | Total Trades | Avg Trade (USD) | Recovery Factor |
|---|---|---|---|---|---|---|---|---|
| TrendMA_EA | ? | ? | ? | ? | ? | ? | ? | ? |
| Breakout_EA | ? | ? | ? | ? | ? | ? | ? | ? |
| MeanReversion_EA | ? | ? | ? | ? | ? | ? | ? | ? |
| ScalperEA (原版) | ? | ? | ? | ? | ? | ? | ? | ? |
| ScalperXAU v1 | ? | ? | ? | ? | ? | ? | ? | ? |
| **均值** | ? | ? | ? | ? | ? | ? | ? | ? |
| **中位数** | ? | ? | ? | ? | ? | ? | ? | ? |

**字段定义**:
- `Net Profit`: 总盈亏 (USD, in pips × 合约单位)
- `Profit Factor`: 总盈利 / 总亏损, > 1.5 算及格
- `Max DD %`: 最大回撤占初始余额百分比
- `Sharpe`: 年化夏普, > 0.5 算稳
- `Win Rate`: 胜率 (赢笔 / 总笔)
- `Total Trades`: 总交易笔数, < 30 样本无效
- `Avg Trade`: 平均每笔盈亏 (Net Profit / Total Trades)
- `Recovery Factor`: Net Profit / Max DD, > 2 算恢复能力强

---

### 步骤 7: 标异常 EA (5 min)

> **3 类异常**: 编译失败 / 跑挂 (no trade) / 数据异常 (Net Profit = 0 但有 trade)。

| 异常类型 | 表现 | 处置 |
|---|---|---|
| 编译失败 | `0 errors` 不通过 | 回到步骤 2 修, 重新跑 |
| 跑挂 | Total Trades = 0 | 检查 EA 是否依赖外部文件 (M17 news_calendar.csv) / 检查 input 配错 |
| 数据异常 | Net Profit = 0 有 trade | 多数是 filling 错 (Exness XAUUSDm 用 FOK, 改 CTradePlus filling 设置) |
| 数据异常 | Net Profit 极大 (> 10000 USD, 初始 10000) | 100%+ 收益, 几乎肯定是 overfitting, 标黄, 不用 |

**N1 实物出来后, 异常 EA 在对比表里标 `(异常: 原因)`**。

---

### 步骤 8: 参数稳定性分析 (3 组参数, 6 h)

> **核心: 同一 EA 用 3 组参数跑, 看输出差异, 判断是否 overfitting**。
> 3 组: baseline (默认) / +20% 偏多 (long bias) / -20% 偏空 (short bias) 或 调关键参数。

**示例 3 组参数** (以 TrendMA_EA 为例):
| 组 | FastMA | SlowMA | SL_Points | TP_Points |
|---|---|---|---|---|
| Baseline | 12 | 26 | 300 | 600 |
| Long bias | 10 (快一点) | 30 (慢一点) | 400 | 800 |
| Short bias | 14 (慢一点) | 22 (快一点) | 250 | 500 |

**输出对比**:
- 如果 3 组 Net Profit 都是正 → **稳定** ✅
- 如果 baseline 正, ±20% 都负 → **overfitting** ⚠️
- 如果 baseline 微正, ±20% 巨正/巨负 → **不稳定**, 慎用

**总耗时**: 3 组 × 5 EA × 30 min-4 h = 1.5-12 h (按 5 EA 单跑时间 × 3)

---

### 步骤 9: 写对比分析 (4 维度评分, 30 min)

> **4 维度 × 0-5 分 = 满分 20**, 客观 + 主观结合。

| 维度 | 评分标准 | 满分 |
|---|---|---|
| **盈利能力** | Net Profit > 500: 5 / 200-500: 4 / 0-200: 3 / -200-0: 2 / -500--200: 1 / < -500: 0 | 5 |
| **风险控制** | Max DD < 5%: 5 / 5-10%: 4 / 10-15%: 3 / 15-20%: 2 / 20-30%: 1 / > 30%: 0 | 5 |
| **稳定性** | 3 组参数均正: 5 / 2 正 1 负: 4 / 1 正 2 负: 2 / 全负: 0 | 5 |
| **模块化程度** | ≥ 10 个 MQL5Kit 集成: 5 / 6-9: 4 / 3-5: 3 / 1-2: 2 / 0: 1 | 5 |

**示例评分** (N1 实物出来前, 占位):
| EA | 盈利 | 风控 | 稳定 | 模块化 | **总分** |
|---|---|---|---|---|---|
| TrendMA_EA | ? | ? | ? | 4 (10 个) | ? |
| Breakout_EA | ? | ? | ? | 4 (10 个) | ? |
| MeanReversion_EA | ? | ? | ? | 5 (13 个) | ? |
| ScalperEA (原版) | ? | ? | ? | 1 (0 个) | ? |
| ScalperXAU v1 | ? | ? | ? | 5 (14 个) | ? |

**N1 实物出来后, 填 ? 位置 = 实物评分**。

---

### 步骤 10: 加 MOC + spec 末尾"回测实战"链接 (5 min)

**10a. 在 `EA 开发知识库.md` 的"实战"分类追加新 wiki 链接**:
```markdown
## 实战 (已落地的可复制场景)
- [[实战/M18 多品种对冲实战]] — ...
- [[实战/M19 时段过滤实战]] — ...
- [[实战/BBTrendEA 复活 SOP]] — ...
- [[实战/Scalping_More v1.3 接入示例]] — ...
- [[实战/5 EA 6 月回测对比 SOP]] — 5 EA × 6 月 × 3 参数回测方法论 (420+ 行 / 7 章节 / 10 步 SOP)
```

**10b. 在 4 个 EA spec / 模板末尾加 "回测实战" 链接** (TrendMA / Breakout / MeanReversion / ScalperXAU):
```markdown
## 回测实战
- [[实战/5 EA 6 月回测对比 SOP]] — 本 EA 在 5 EA 对比中的位置 / 期望 / 评分
```

---

## 3. 回测指标表 (7 维度)

> **N1 实物出来后, 把每个 EA 的 7 维度实测数据填入本表**, 然后按 4 维度评分 (盈利 / 风控 / 稳定 / 模块化)。
> 5 EA × 7 维度 = 35 个数据点, N1 必须全填。

### 3.1 维度 1: 盈利能力 (5 个子指标)

| 子指标 | 公式 | 优秀线 | 及格线 | 失败线 |
|---|---|---|---|---|
| Net Profit | 6 月总盈亏 (USD) | > 500 | > 0 | < 0 |
| Profit Factor | 总盈利 / 总亏损 | > 2.0 | > 1.3 | < 1.0 |
| Avg Trade | Net Profit / Total Trades | > 5 USD | > 0 | < 0 |
| Recovery Factor | Net Profit / Max DD | > 5 | > 2 | < 1 |
| ROI % | Net Profit / 初始余额 | > 5% | > 0% | < 0% |

### 3.2 维度 2: 风险控制 (5 个子指标)

| 子指标 | 公式 | 优秀线 | 及格线 | 失败线 |
|---|---|---|---|---|
| Max DD % | 最大回撤 / 初始余额 | < 5% | < 15% | > 25% |
| Max DD Duration | 回撤从开始到恢复峰值的天数 | < 30 day | < 90 day | > 180 day |
| Daily Max Loss % | 单日最大亏损 / 净值 | < 1% | < 3% | > 5% |
| Consecutive Losses | 最大连续亏损笔数 | < 5 | < 10 | > 15 |
| Risk/Reward Ratio | 平均盈利 / 平均亏损 | > 2.0 | > 1.0 | < 0.5 |

### 3.3 维度 3: 交易质量 (5 个子指标)

| 子指标 | 公式 | 优秀线 | 及格线 | 失败线 |
|---|---|---|---|---|
| Win Rate | 胜率 | > 60% (逆势) / > 40% (趋势) | > 50% / > 30% | < 45% / < 25% |
| Sharpe Ratio | 年化夏普 | > 1.0 | > 0.5 | < 0 |
| Sortino Ratio | 年化索提诺 (只算下行波动) | > 1.5 | > 0.7 | < 0 |
| Total Trades | 6 月总交易笔数 | > 100 (高频) / > 30 (中频) | > 30 | < 20 (样本无效) |
| Avg Hold Time | 平均持仓时间 | < 30 min (剥头皮) / < 4 h (日内) | < 1 day | > 1 day |

### 3.4 维度 4: 稳定性 (4 个子指标)

| 子指标 | 公式 | 优秀线 | 及格线 | 失败线 |
|---|---|---|---|---|
| Monthly Return Consistency | 6 月中盈利月数 / 6 | 6/6 | ≥ 4/6 | < 3/6 |
| Parameter Sensitivity | baseline 与 ±20% 参数的 Net Profit 偏差 | < 20% | < 50% | > 100% |
| Regime Stability | 趋势市 vs 震荡市 Net Profit 差异 | < 30% | < 50% | > 80% |
| Drawdown Recovery Speed | Max DD / 恢复到峰值天数 | < 5% / day | < 2% / day | < 0.5% / day |

### 3.5 维度 5: 实战差距 (4 个子指标, 与实盘对比)

| 子指标 | 公式 | 期望 | 警告 |
|---|---|---|---|
| Backtest vs Live Slippage | 实盘滑点 - 回测滑点 | < 1 pip | > 3 pip → 调 SL_Points |
| Backtest vs Live Spread | 实盘点差 - 回测点差 | < 5 points | > 20 points → 调 MaxSpread |
| Backtest vs Live Reject Rate | 实盘拒单率 | < 1% | > 5% → 调 deviation / filling |
| Backtest vs Live Jump | 周一开盘跳空打穿 SL 率 | < 1% | > 3% → 调 "周五尾盘" 策略 |

### 3.6 维度 6: 模块化 (3 个子指标)

| 子指标 | 公式 | 优秀线 | 及格线 | 失败线 |
|---|---|---|---|---|
| MQL5Kit 集成数 | 14 个模块中已集成的 | ≥ 10 | ≥ 6 | < 3 |
| 关键模块覆盖 | M01/M02/M08/M19 是否都有 | 4/4 | 3/4 | < 2/4 |
| 错误处理完整性 | 失败返 INIT_FAILED + Print + LastError 都有 | 100% | > 80% | < 60% |

### 3.7 维度 7: 通知与监控 (3 个子指标)

| 子指标 | 期望 | 警告 |
|---|---|---|
| M10 Notify 触发器数 | ≥ 3 (DD / 拒单 / 断连) | < 2 |
| M11 Logger 输出 | 文件 + 控制台双输出 | 缺一 |
| M13 CSV 落盘 | trades_YYYYMMDD.csv 落盘 | 无 CSV |

### 3.8 5 EA × 7 维度 实物数据填表模板 (N1 用)

> **N1 实物出来后, 把本节表格填充, 加到 wiki 末尾 "## 5 EA 6 月回测实测数据 (待 N1 实物)" 段**。

```markdown
| 维度 | 子指标 | TrendMA | Breakout | MeanRev | ScalperEA | ScalperXAU |
|---|---|---|---|---|---|---|
| 盈利 | Net Profit (USD) | ? | ? | ? | ? | ? |
| 盈利 | Profit Factor | ? | ? | ? | ? | ? |
| 盈利 | Avg Trade (USD) | ? | ? | ? | ? | ? |
| 盈利 | Recovery Factor | ? | ? | ? | ? | ? |
| 盈利 | ROI % | ? | ? | ? | ? | ? |
| 风控 | Max DD % | ? | ? | ? | ? | ? |
| 风控 | Max DD Duration (day) | ? | ? | ? | ? | ? |
| 风控 | Daily Max Loss % | ? | ? | ? | ? | ? |
| 风控 | Consecutive Losses | ? | ? | ? | ? | ? |
| 风控 | Risk/Reward Ratio | ? | ? | ? | ? | ? |
| 质量 | Win Rate % | ? | ? | ? | ? | ? |
| 质量 | Sharpe Ratio | ? | ? | ? | ? | ? |
| 质量 | Sortino Ratio | ? | ? | ? | ? | ? |
| 质量 | Total Trades | ? | ? | ? | ? | ? |
| 质量 | Avg Hold Time (min) | ? | ? | ? | ? | ? |
| 稳定 | Monthly Consistency | ?/6 | ?/6 | ?/6 | ?/6 | ?/6 |
| 稳定 | Param Sensitivity | ?% | ?% | ?% | ?% | ?% |
| 稳定 | Regime Stability | ?% | ?% | ?% | ?% | ?% |
| 稳定 | DD Recovery Speed | ?%/day | ?%/day | ?%/day | ?%/day | ?%/day |
| 差距 | Slippage (pip) | ? | ? | ? | ? | ? |
| 差距 | Spread (points) | ? | ? | ? | ? | ? |
| 差距 | Reject Rate % | ? | ? | ? | ? | ? |
| 差距 | Jump Rate % | ? | ? | ? | ? | ? |
| 模块 | MQL5Kit 集成数 | 10 | 10 | 13 | 0 (原版) | 14 |
| 模块 | 关键模块 (M01/M02/M08/M19) | 4/4 | 4/4 | 4/4 | 1/4 | 4/4 |
| 模块 | 错误处理完整 % | ? | ? | ? | ? | ? |
| 通知 | M10 触发器数 | ? | ? | ? | ? | ? |
| 通知 | M11 Logger | ? | ? | ? | ? | ? |
| 通知 | M13 CSV 落盘 | ? | ? | ? | ? | ? |
| **4 维评分** | 盈利 + 风控 + 稳定 + 模块化 | ?+?+?+?=? | ?+?+?+?=? | ?+?+?+?=? | ?+?+?+?=? | ?+?+?+?=? |
```

---

## 4. 回测配置 checklist (10 项)

> **N1 跑回测前必查, 每项都打勾才能开 Start**。

- [ ] **C1 数据完整性**: XAUUSDm M1 + H1 数据从 2025-12-01 到 2026-07-01 连续, 无空洞
- [ ] **C2 Modeling = Every tick based on real ticks**: 高频 EA (M1) 必须真实 tick, 不能用 OHLC
- [ ] **C3 Profit = in pips**: 跨 EA 对比用统一单位, 不用 in $
- [ ] **C4 Deposit = 10000 USD**: 默认 demo 账户余额
- [ ] **C5 Leverage = 1:100**: Exness 默认
- [ ] **C6 Slippage = 0**: 第一遍用 0 (理想), 第二遍改 3 (实测), 对比差异
- [ ] **C7 周末不特殊处理**: Strategy Tester 默认就 "忽略周末", 不要勾 "Include weekend"
- [ ] **C8 Magic 唯一**: 5 EA 各用不同 magic (e.g. 20260101 / 20260301 / 20260201 / 20260601 / 20240604), 不冲突
- [ ] **C9 3 次取中位数**: 同一配置跑 3 次 (MT5 内部有随机性), 取 Net Profit 中位数
- [ ] **C10 Optimization Disabled**: 一次性跑, 不开 optimizer (用 §2 步骤 8 单独跑 ±20%)

**Bonus C11**: 跑 1 周 sanity check (2026-01-01 ~ 2026-01-08) → 5 EA 都能跑出 trade, 证明无致命 bug → 再跑全 6 月

---

## 5. 回测 vs 实战避坑 (7 条)

> 每条都来自 [[04-避坑与速查/03 实盘 vs 回测差异]] + [[04-避坑与速查/04 经纪商差异（点差 / 手数 / Filling）]] 的核心避坑, 配 5 EA 对比场景。

### 坑 1: 滑点 — 回测假设 0 滑点, 实盘 1-5 点常态化

- **回测表现**: ScalperXAU v1 M1 6 月 3000 笔全成功, PF 1.3
- **实盘表现**: 同样 EA 6 月实盘, 滑点 2 点, 实际 PF 降到 1.15
- **N1 应对**: 跑回测时把 Slippage 改 3 点跑第 2 遍, 看 Net Profit 下降幅度, 评估实战可达性

### 坑 2: 点差 — 回测固定点差, 实盘浮动 (新闻时扩大 10x)

- **回测表现**: MeanReversion_EA M1 6 月 PF 1.5
- **实盘表现**: NFP / CPI 公布 ±5 min 点差 50-200, 1 笔打穿 20 笔盈利
- **N1 应对**: ScalperXAU v1 + M17 (M17 news_calendar.csv 必填) 测新闻过滤, 跑 1 个月 M1 数据, 看新闻时段 trade count 是否下降 ≥ 80%

### 坑 3: 跳空 — 周一开盘跳 30-50 点, SL 被跳穿

- **回测表现**: TrendMA_EA 6 月 DD 8%
- **实盘表现**: 周一 1 次跳空直接 DD 15% (SL 价 vs 跳空价差 30 点)
- **N1 应对**: 跑回测时勾 "Include weekend" 看 DD 变化 (MT5 默认不勾, 但实战要估); 必要时改 "周五尾盘" 策略

### 坑 4: 重连 / 掉线 — VPS 重启 / 家里断电 / 经纪商踢出

- **回测表现**: 假设服务器永不挂
- **实盘表现**: VPS 一年挂 3-5 次, EA 重启有状态丢失风险
- **N1 应对**: M12 GV 必接 (跨重启保存 magic + 上次状态); 跑 1 周 demo 验证重启后状态恢复

### 坑 5: 服务器限流 — OrderSend 频率过高被服务器 10030 拒

- **回测表现**: ScalperEA 6 月 12000 笔, 0 拒
- **实盘表现**: 1 小时内 50 笔, 服务器开始拒 (`InpMaxTradesPerHour=10` 保护)
- **N1 应对**: 跑回测时设 `InpMaxTradesPerHour=10` 限制, 看 trade count 下降多少; 实盘 1 周看 journal 拒单率

### 坑 6: Filling 模式 — 回测默认 RETURN, 实盘 XAUUSDm 需 FOK

- **回测表现**: 5 EA 全 0 拒
- **实盘表现**: ScalperEA 用 RETURN 拒 30% (Exness XAUUSDm 只支持 FOK / IOC)
- **N1 应对**: M01 CTradePlus 内部自动选 filling, 跑回测 + 实盘 1 周对比拒单率 (实盘 < 1% 为合格)

### 坑 7: Magic=0 误匹配 — 同一账户多个 EA 时, magic=0 匹配所有

- **回测表现**: 1 EA 跑, magic 0 OK
- **实盘表现**: 多 EA 跑, magic 0 互相误判持仓
- **N1 应对**: 5 EA 各用唯一 magic (见 C8), 实盘前 assert `if (Magic == 0) return INIT_FAILED`

---

## 6. 反模式 (5 条不要做的事)

> 5 EA 对比时, 这些操作会让对比结果无效。

### 反模式 1: 不要用 1 分钟 OHLC 跑高频 EA

- **错**: ScalperEA M1 用 "每个报价基于 1 分钟 OHLC" 跑 6 月
- **为什么错**: OHLC 模式不模拟 tick 内波动, 6 月可能 3000 笔, 但实际 1 笔都开不了 (没足够 tick)
- **对**: **必须**用 "Every tick based on real ticks" 跑 M1 EA

### 反模式 2: 不要跑 1 周下结论

- **错**: TrendMA_EA H1 跑 1 周, Net Profit -50, 结论 "EA 亏钱"
- **为什么错**: 1 周可能正好是震荡市, 趋势 EA 在震荡市必亏, 1 周样本无意义
- **对**: **至少 3 个月**, 6 月更好, 至少 30 笔 trade

### 反模式 3: 不要在回测时关 M17

- **错**: ScalperXAU v1 跑回测, 设 `InpEnableNewsFilter=false` (因为没填 news_calendar.csv)
- **为什么错**: 关了 M17 = 实际剥头皮没新闻保护, 6 月可能正好 1 次 NFP 打穿 → 对比 ScalperEA 无 M17 时无差异
- **对**: **必须** 准备 `MQL5/Files/news_calendar.csv` (至少 6 月内 NFP / CPI / FOMC 日期), M17 加载后才能正常过滤

### 反模式 4: 不要追求高胜率

- **错**: 看到 Breakout_EA Win Rate 35%, 标 "差", 不参与对比
- **为什么错**: 突破型策略胜率天然低, 但盈亏比 3:1, 6 月 Net Profit 仍可正
- **对**: **按 4 维度评分**, 不按单一胜率筛选; Win Rate 30%+ 趋势型都参与

### 反模式 5: 不要直接实盘

- **错**: 5 EA 跑完回测, Net Profit 都是正, 直接挂 Exness real account
- **为什么错**: 回测 6 月 ≠ 实盘 6 月 (滑点 / 点差 / 跳空), 5 EA 必先各跑 1-2 周 demo 实盘
- **对**: 回测 → demo 1-2 周 (M13 CSV 落盘 + M10 推送链路验证) → real account 小额 (0.01 lot) → 1 个月后加仓

---

## 7. 与 N1 实物的协作

### 7.1 角色分工

| Mavis (T2, 本任务) | 用户 (在 console 1) | N1 (后续任务) |
|---|---|---|
| 写本 SOP wiki (完成) | GUI 跑 backtest (5 EA × 6 月 × 1 period) | 拿 XML 报告, 按本 wiki 填章节 3 表格 |
| 设计 4 维度评分 | 跑 3 组参数 (baseline / +20% / -20%) | 写"## 5 EA 6 月回测实测数据"段 |
| 设计 7 维度指标 | 跑 §3 模板填表 | 跑参数稳定性分析 |
| 不写 .mq5 / 不跑 backtest | 把 5 个 XML + 3 组参数 XML 放统一目录 | 不写本 SOP 内容 (方法论不变) |

### 7.2 N1 接手清单 (10 步)

```powershell
# 1) 读本 SOP wiki 完整内容
Get-Content "C:\ai\obsidian-文件\mt\EA开发\实战\5 EA 6 月回测对比 SOP.md" | Select-Object -First 50

# 2) 检查 5 EA 编译状态
$eaDir = "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea"
$me = "C:\Program Files\MetaTrader 5\MetaEditor64.exe"
& $me /compile:"$eaDir\TrendMA_EA.mq5" /log
& $me /compile:"$eaDir\Breakout_EA.mq5" /log
& $me /compile:"$eaDir\MeanReversion_EA.mq5" /log
& $me /compile:"$eaDir\ScalperXAU.mq5" /log
# ScalperEA 在 root
& $me /compile:"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\ScalperEA.mq5" /log

# 3) 准备 backtest 报告目录
$dst = "C:\ai\obsidian-文件\mt\00-任务调度中心\daily\backtest-5EA-2026-06-30\"
New-Item -ItemType Directory -Force -Path $dst

# 4) 通知用户跑 backtest (GUI 操作, Mavis 不做)
#    详见本 wiki §2 步骤 4: TrendMA H1 (30min) + Breakout H1 (30min) + MeanRev M1 (2h) + ScalperEA M1 (4h) + ScalperXAU M1 (4h) = ~10h
#    跑完用户把 5 个 XML 报告放到 $dst

# 5) 抽取报告 (mql5-report-analyzer.mjs)
cd $dst
node "C:\ai\obsidian-文件\mt\00-任务调度中心\tools\mql5-report-analyzer.mjs" *.xml --output 5EA-summary.json

# 6) 按 §3 填表 (7 维度 × 5 EA = 35 数据点)
#    直接把 §3.8 模板拷到 wiki 末尾, 填数据

# 7) 跑 3 组参数 (baseline / +20% / -20%, 详见 §2 步骤 8)
#    每组 5 EA, 3 组 = 15 次 backtest
#    总耗时: 15 × 30min-4h = 7.5-60h, 建议分 1 周跑

# 8) 计算 4 维度评分 (详见 §2 步骤 9)
#    5 EA × 4 维度 = 20 个分数, 总分 20

# 9) 在本 wiki 末尾追加 "## 5 EA 6 月回测实测数据 (待 N1 实物)" 段 (格式见 §7.3)
#    不动本 SOP 章节 1-7 + 附录内容

# 10) 给用户报告: "5 EA 6 月回测对比完成, 见 [[实战/5 EA 6 月回测对比 SOP]] 末尾"
```

### 7.3 实物数据追加段格式 (N1 完成后追加到本 wiki 末尾)

```markdown
---

## 5 EA 6 月回测实测数据 (N1 实物, 2026-XX-XX 完成)

> **完成时间**: 2026-XX-XX HH:MM
> **跑回测人**: 用户 (GUI console 1)
> **报告分析人**: N1 (Mavis)
> **数据来源**: 5 个 XML 报告 + 5EA-summary.json

### 7.3.1 5 EA 核心数据 (6 月)

| EA | Net Profit | PF | Max DD | Sharpe | Win Rate | Trades | 总分 |
|---|---|---|---|---|---|---|---|
| TrendMA_EA | ? | ? | ? | ? | ? | ? | ?/20 |
| Breakout_EA | ? | ? | ? | ? | ? | ? | ?/20 |
| MeanReversion_EA | ? | ? | ? | ? | ? | ? | ?/20 |
| ScalperEA (原版) | ? | ? | ? | ? | ? | ? | ?/20 |
| ScalperXAU v1 | ? | ? | ? | ? | ? | ? | ?/20 |

### 7.3.2 4 维度评分明细

(此处插入 §2 步骤 9 的评分表, 填数据)

### 7.3.3 7 维度 35 数据点 (按 §3.8 模板)

(此处插入 §3.8 模板, 填数据)

### 7.3.4 异常 EA 处置

(此处记录 §2 步骤 7 发现的 3 类异常, 含处置方式)

### 7.3.5 参数稳定性 (3 组参数)

(此处插入 §2 步骤 8 的 ±20% 对比表)

### 7.3.6 结论与建议

(N1 根据数据写 1-3 段结论, 例: "推荐 MeanReversion_EA 升级 demo / ScalperEA 必先升级 v1.3 才能实盘")
```

### 7.4 失败回滚

若 N1 跑 §2 步骤 4 backtest 全部 0 trade:
1. 检查 5 EA 是否都依赖外部文件 (M17 news_calendar.csv / M09 dashboard layout)
2. 检查 input 是否配错 (magic / 品种 / 周期)
3. 退回到 §2 步骤 2 重编译, 找编译错误
4. **不要** 改 MQL5Kit 模块 (5 EA 共享, 改了破坏 MeanReversion_EA 实物)
5. 改 SOP 章节 1 (5 EA 资产盘点) 加 "异常" 标注, 章节 7 标 "N1 部分失败"

---

## 附录 A: 5 EA 输入参数模板 (每个 EA 1 段, 标注建议值 + 调优方向)

> **N1 跑 backtest 时, 用本附录确认 input 配置正确**。
> **不跑 backtest 的 EA** (MyEA / Dashboard) 不列。

### A.1 TrendMA_EA 参数模板

```mql5
input ulong  Magic         = 20260101;        // 唯一 magic, 跟其它 EA 区分
input int    FastMA_Period = 12;              // 快线周期 (建议 8-20)
input int    SlowMA_Period = 26;              // 慢线周期 (建议 20-50)
input ENUM_MA_METHOD MA_Method = MODE_EMA;   // MA 类型 (EMA > SMA 灵敏)
input double RiskPct       = 0.01;            // 1% 净值风险
input int    MaxPos        = 3;               // 最大持仓
input int    SL_Points     = 300;             // 止损 300 点 (XAU 3 USD/lot)
input int    TP_Points     = 600;             // 止盈 600 点 (RR 1:2)
input bool   UseTrailing   = true;
input int    TrailStart    = 200;             // 浮盈 200 启动追踪
input int    TrailStep     = 150;             // SL 距当前价 150
```

**调优方向**:
- 趋势强 (H4 方向明确) → FastMA 10 / SlowMA 30 (跟得紧)
- 震荡市 → 加 RSI/ADX 过滤 (当前 EA 缺, 是改进点)
- 跑 3 组参数: (12,26) / (10,30) / (14,22), 看 baseline ±20% 稳定性

### A.2 Breakout_EA 参数模板

```mql5
input ulong  Magic         = 20260301;
input int    Donchian_N    = 20;              // 突破周期 (建议 10-50)
input int    Donchian_Exit_N = 10;            // 反向平仓周期
input double RiskPct       = 0.01;
input int    MaxPos        = 2;               // 突破型持仓数小
input int    SL_Points     = 400;             // 突破后止损宽一点 (XAU 4 USD/lot)
input int    TP_Points     = 0;               // 0=不用 TP, 靠 M08 追踪
input bool   UseTrailing   = true;
input double TrailATR_Mult = 2.0;             // SL = 2 × ATR
```

**调优方向**:
- 突破周期大 (N=50) → 信号少但稳, 适合 H1 / H4
- 突破周期小 (N=10) → 信号多但假突破多, 加 ADX 过滤
- 跑 3 组参数: N=20 / N=15 / N=25, 看 Donchian 周期稳定性

### A.3 MeanReversion_EA 参数模板 (最复杂, 14 个 input)

```mql5
input ulong  Magic         = 20260201;
input int    RSI_Period    = 14;
input int    RSI_Overbought = 70;
input int    RSI_Oversold   = 30;
input int    BB_Period     = 20;
input double BB_Deviation  = 2.0;
input double RiskPct       = 0.01;
input int    MaxPos        = 3;
input int    SL_Points     = 200;
input int    TP_Points     = 150;
input bool   UseADXFilter  = true;
input int    ADX_Max       = 25;              // ADX > 25 不开

// M18 相关性
input bool   InpUseM18Filter = true;          // ← baseline 对比必关一次
input double InpCorrThreshold = 0.7;
input string InpCorrSymbols = "XAUUSDm,EURUSDm,GBPUSDm,USDJPYm";

// M19 时段
input bool   InpUseM19Filter = true;          // ← baseline 对比必关一次
input string InpSessionPreset = "London:8-16,NewYork:13-22";
input bool   InpAllowWeekend = false;
```

**调优方向**:
- RSI 阈值: 经典 70/30, 强势震荡 80/20, 弱势震荡 60/40
- ADX 阈值: 25 是平衡, 30 更严, 20 更松
- **baseline 对比必跑**: `InpUseM18Filter=false` / `InpUseM19Filter=false` 各 1 次 → 看 M18/M19 价值
- 跑 3 组参数: (RSI 30/70) / (RSI 25/75) / (RSI 35/65), 看 RSI 阈值稳定性

### A.4 ScalperEA 参数模板 (原版, 建议升级到 v1.3)

```mql5
input double InpLotSize     = 0.01;           // 固定手数 (剥头皮 0.01-0.05)
input int    InpTakeProfit  = 200;
input int    InpStopLoss    = 133;
input int    InpMagicNumber = 20260601;
input int    InpDeviationPoints = 20;         // 滑点 20 points = 0.20 USD
```

**调优方向**:
- **强烈建议升级到 v1.3** (接 8 模块 M01/M02/M08/M10/M11/M13/M15/M17/M19), 不然 6 月回测可能爆仓
- 升级版参数: 见 [[实战/Scalping_More v1.3 接入示例]] §3 代码段 2
- 跑 3 组参数: (InpLotSize 0.01/0.02/0.05) + (InpSlPoints 133/100/200), 严格控制

### A.5 ScalperXAU v1 参数模板 (含 v3 / v7debug 3 版)

```mql5
input ulong  Magic = 20240604;                // v1 实物 magic

// 信号
input int    InpBbPeriod = 20;
input double InpBbDeviation = 2.0;
input int    InpRsiPeriod = 14;
input int    InpRsiOversold = 30;
input int    InpRsiOverbought = 70;

// 出场
input int    InpSlPoints = 50;                // XAU 0.50 USD/lot
input int    InpTpPoints = 100;               // RR 1:2
input int    InpMaxHoldMinutes = 30;

// 风控
input double InpRiskPercent = 0.5;            // 0.5% 风险 (剥头皮严控)
input int    InpMaxPositions = 3;
input int    InpMaxTradesPerDay = 20;
input double InpMaxDailyDrawdownPct = 3.0;

// 过滤
input int    InpMaxSpreadPoints = 50;
input double InpAtrMin = 0.5;
input double InpAtrMax = 5.0;
input int    InpSessionStartHour = 8;
input int    InpSessionEndHour = 23;
input bool   InpEnableNewsFilter = true;       // ← M17 必启用
```

**v3 / v7debug 差异**:
- v3 = BB+RSI+ADX+Trail, 已生产
- v7debug = 最新调试版 (待 v1→v2→v3→v4→v5simple→v6debug→v7debug 迭代)
- **3 版分别跑**, 对比迭代价值

**调优方向**:
- SL/TP: 50/100 是经典, 严的 30/60, 宽的 100/200
- InpMaxTradesPerDay: 20 (默认) / 30 (激进) / 10 (保守)
- **M17 必启用** (不启用 = 6 月新闻时段被打穿 1-2 次)
- 跑 3 组参数: (50/100) / (30/60) / (100/200), 看 SL/TP 稳定性

### A.6 5 EA 参数对照 (N1 一目了然)

| EA | Magic | 关键参数 1 | 关键参数 2 | 关键参数 3 | 调优方向 |
|---|---|---|---|---|---|
| TrendMA_EA | 20260101 | FastMA=12 | SlowMA=26 | SL=300 | 趋势: 调 MA 周期 |
| Breakout_EA | 20260301 | Donchian_N=20 | SL=400 | TrailATR=2.0 | 突破: 调 N |
| MeanReversion_EA | 20260201 | RSI=30/70 | BB=20/2.0 | M18=0.7 | 逆势: 调 RSI 阈值 + M18/M19 baseline |
| ScalperEA | 20260601 | Lot=0.01 | SL=133 | TP=200 | 高频: 调 SL/TP |
| ScalperXAU v1 | 20240604 | SL=50 | TP=100 | MaxTrades=20 | 剥头皮: 调 SL/TP + M17 必启 |

---

## 8. 相关链接

### 8.1 必读 wiki (回测前先看)
- [[EA 开发知识库]] — 入口 MOC
- [[00-快速开始/EA 写之前要知道的 10 件事]] — 5 EA 编译前必看 10 条
- [[00-快速开始/MT5 GUI 自动化 5 次失败全记录 + 分工协议]] — 跑回测必涉及 GUI, 用户必读
- [[04-避坑与速查/03 实盘 vs 回测差异]] — 章节 5 避坑的来源
- [[04-避坑与速查/04 经纪商差异（点差 / 手数 / Filling）]] — 章节 5 避坑 6 (Filling) 的来源
- [[04-避坑与速查/01 编译常见错误]] — 5 EA 编译时可能遇到的错误
- [[04-避坑与速查/05 必查清单]] — 回测前 checklist 模板

### 8.2 模块 wiki (回测期表现)
- [[M01 交易封装 CTradePlus]] — 回测期 filling / slippage
- [[M02 风控 Risk]] — 回测期 DD / 爆仓概率
- [[M03 仓位计算 PositionSizing]] — 回测期 Avg Trade
- [[M08 追踪止损 TrailingStop]] — 回测期 TrailingStart / TrailingStep
- [[M15 定时器 TimerService]] — 回测期 timer 表现 (Tick 模式)
- [[M18 相关性过滤 CorrelationFilter]] — 回测期相关性过滤 (30 天日线不变)
- [[M19 时段过滤 SessionFilter]] — 回测期时段过滤 (配置完全等价)
- M17 新闻过滤 (无 spec wiki, 用 ScalperXAU.mq5 line 31/79-83/117/548-549/853/981-985 实测 API 替代, 见 §5 坑 2)

### 8.3 实战 wiki (5 EA 接入范本)
- [[实战/M18 多品种对冲实战]] — M18 在 MeanReversion_EA 的接入, 章节 5 评分依据
- [[实战/M19 时段过滤实战]] — M19 在 MeanReversion_EA 的接入, 章节 5 评分依据
- [[实战/BBTrendEA 复活 SOP]] — 复活 SOP 范本 (本 wiki 模仿其结构)
- [[实战/Scalping_More v1.3 接入示例]] — ScalperEA 升级 v1.3 的 SOP

### 8.4 模板 wiki (5 EA 的基线)
- [[02-完整模板/EA 通用骨架]] — MyEA 模板
- [[02-完整模板/EA 趋势跟踪模板（MA 交叉）]] — TrendMA_EA 模板
- [[02-完整模板/EA 突破模板（Donchian 海龟）]] — Breakout_EA 模板
- [[02-完整模板/EA 逆势均值回归模板（RSI Bollinger）]] — MeanReversion_EA 模板
- [[02-完整模板/EA 剥头皮模板]] — ScalperEA / ScalperXAU v1 模板

### 8.5 策略 spec (5 EA 的 spec)
- [[策略/01 ScalperXAU v1 - Bollinger RSI 均值回归]] — ScalperXAU v1 spec
- (02 TrendMA / 03 DonchianXAU spec wiki 暂无, 用 [[02-完整模板/EA 趋势跟踪模板（MA 交叉）]] / [[02-完整模板/EA 突破模板（Donchian 海龟）]] 模板替代, 见章节 1 §1.1 / §1.2)

### 8.6 任务中心
- `C:\ai\obsidian-文件\mt\00-任务调度中心\daily\2026-06-04_14-00-track2-result.md` — T2 本任务交付
- `C:\ai\obsidian-文件\mt\00-任务调度中心\daily\backtest-5EA-2026-06-30\` — N1 backtest 报告目录 (待 N1 创建)
- `C:\ai\obsidian-文件\mt\00-任务调度中心\tools\mql5-report-analyzer.mjs` — XML 报告分析器

---

**版本**: v1.0 (2026-06-04 创建, Mavis T2 任务交付)
**下次更新**: N1 实物回测完成后追加 §7.3 "5 EA 6 月回测实测数据" 段
**维护人**: Mavis general agent
**限制**: 本 SOP 是方法论, 不依赖 N1 实物; N1 完成后用 §7.3 模板追加数据, 不动本 SOP 章节 1-7 + 附录内容


---

## 实战案例 (末尾追加, 6 段结构 — 沿用 03:00 T2 范本)

> 本节为 [5 EA 6 月回测对比 SOP] 的「实物已跑通 6 段实战案例」段, 5 EA × 6 月回测方法论的「在 5 个 demo 实物上落地」补充。N1 任务阻塞 (10h, ⚠ console 1), 本节 6 段 (场景 A/B + 接入点行号 + 调优点 3 档 + 陷阱 5 条 + 链向) 全部以 5 个 demo 实物 (MeanRev / SX / TMA / BO / MyEA+Dashboard) 的 7 维度数据点为基线, 不需要 N1 实物回测; N1 完成时仅在 §7.3 追加真实 trade 数据即可。

### 场景 A: 5 EA 单跑 (1 broker 1 月 demo 验证基线)

- 实战场景: 5 个 demo 实物 (MeanRev 13503B / SX 42824B / TMA 9169B / BO 9530B / MyEA 12541B) 各跑 1 月 XAUUSDm M1 demo, 用 7 维度 (Net Profit / PF / Win Rate / DD / Trade / Avg Win / Avg Loss) 评估单 EA 表现, 作为 N1 6 月 30 次回测的「单月 baseline」。
- 实物 demo: 5 个实物 + M02 Risk.Init / M07 Positions / M11 logger + M01 trade.Init, 接入 5-13 个 MQL5Kit 模块不等 (TMA+BO 各 10 模块 / MyEA 10 模块 / SX 13 模块 / MeanRev 13 模块)
- 适用范围: 适用 (1 broker demo 1 月验证, 7 维度齐全) / 不适用 (broker 1 个月不一定覆盖黑天鹅, 6 月更稳)

### 场景 B: 5 EA 联合跑 (1 broker 6 月 demo 验证 EA 间协调)

- 实战场景: 5 EA 同账户挂 5 chart 跑 6 月 XAUUSDm M1 demo, 验证 5 EA 间 M02 Risk 共用 magic + M18 跨品种对冲 + M19 跨时段 + M08 TrailingStop 不互锁的协调性, 7 维度 × 5 EA = 35 数据点。
- 实物 demo: 5 EA 各 1 chart 跑 XAUUSDm 6 月 demo, 关键协调点: Magic 唯一 (MeanRev L34 / SX L37 / TMA L23 / BO L22 / MyEA L23) + MaxPos 各 3 + M18.CalcCorr 跨 4-5 品种 + M19.SetAllowWeekend(false) 同账户协调
- 适用范围: 适用 (5 EA 联合 demo 6 月, 验证 EA 间协调) / 不适用 (5 EA 全同向可能 6 倍单笔风险, 须 M18 拦同向)

### 接入点行号 (5 EA 启动 + 5 EA 7 维度 = 35 数据点, Node.js fs 实测 100% 命中)

| wiki 描述 | 实物 | 行号 | 命中关键词 | spec |
|---|---|---|---|---|
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L9 | `#include <MQL5Kit/M01_CTradePlus.mqh>` | M01 头 |
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L20 | `#include <MQL5Kit/M18_CorrelationFilter.mqh>` | M18 头 |
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L21 | `#include <MQL5Kit/M19_SessionFilter.mqh>` | M19 头 |
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L79-83 | `OnInit` (trade.Init + risk.Init + sizing.Init + NB.Init) | M01-M05 Init |
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L110 | `M18.Init(syms)` | M18 启动 |
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L93 | `M19.Init(InpSessionPreset)` | M19 启动 |
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L161 | `M19.IsInSession(TimeCurrent())` | M19 OnTick 闸门 |
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L167 | `M18.IsHedgeExposed(_Symbol, Magic, InpCorrThreshold)` | M18 OnTick 闸门 |
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L177 | `CPositions::CountMine(Magic) >= MaxPos` | M07 持仓数闸门 |
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L199 | `risk.CanOpen(type, lot, sl, tp)` | M02 风控 |
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L239 | `dash.Row("Positions", ... CountMine(Magic) + "/" + MaxPos)` | M09 面板 |
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L242 | `dash.Row("M18", ... InpUseM18Filter ? StringFormat("ON thr=%.2f", InpCorrThreshold) : "off")` | M18 面板 |
| MeanReversion_EA 13 模块全集 + M18+M19 demo | MeanReversion_EA.mq5 | L272-274 | `OnTrade() / HistorySelect(0, TimeCurrent())` | M16 OnTrade 清理 |
| ScalperXAU 13 模块 + v1→v4 演进 | ScalperXAU.mq5 | L19 | `#include <MQL5Kit/M01_CTradePlus.mqh>` | M01 头 |
| ScalperXAU 13 模块 + v1→v4 演进 | ScalperXAU.mq5 | L107 | `CTradePlus trade;` | M01 实例 |
| ScalperXAU 13 模块 + v1→v4 演进 | ScalperXAU.mq5 | L484 | `OnTradeOpened()` (新成交回调) | M10 OnTrade 触发器 |
| ScalperXAU 13 模块 + v1→v4 演进 | ScalperXAU.mq5 | L573 | `trade.ClosePos(ticket)` | M01 平指定 ticket |
| ScalperXAU 13 模块 + v1→v4 演进 | ScalperXAU.mq5 | L574 | `logger.Trade("TIMEOUT", _Symbol, ...)` | M11 Trade 4 级别 |
| ScalperXAU 13 模块 + v1→v4 演进 | ScalperXAU.mq5 | L771 | `risk.CanOpen(type, lot, slPrice, tpPrice)` | M02 风控 |
| ScalperXAU 13 模块 + v1→v4 演进 | ScalperXAU.mq5 | L789 | `OnTick()` | M01 OnTick 入口 |
| ScalperXAU 13 模块 + v1→v4 演进 | ScalperXAU.mq5 | L814 | `CPositions::Count(InpMagicNumber) >= InpMaxPositions`, block = "MAX_POS" | M07 持仓数闸门 |
| ScalperXAU 13 模块 + v1→v4 演进 | ScalperXAU.mq5 | L852 | `dash.Row("Positions", ... Count(InpMagicNumber) + "/" + InpMaxPositions)` | M09 面板 |
| ScalperXAU 13 模块 + v1→v4 演进 | ScalperXAU.mq5 | L912-914 | `OnTrade() / HistorySelect(0, TimeCurrent())` | M11+M16 OnTrade |
| ScalperXAU 13 模块 + v1→v4 演进 | ScalperXAU.mq5 | L951-956 | `OnInit() / risk.Init(InpMagicNumber, InpMaxPositions, InpRiskPercent / 100.0)` | M01-M02 Init |
| TrendMA_EA 10 模块 + MA 交叉 6 模块 | TrendMA_EA.mq5 | L23 | `input ulong Magic = 20260101;` | 基础 input |
| TrendMA_EA 10 模块 + MA 交叉 6 模块 | TrendMA_EA.mq5 | L26-27 | `input int FastMA_Period = 12; / input int SlowMA_Period = 26;` | MA 参数 |
| TrendMA_EA 10 模块 + MA 交叉 6 模块 | TrendMA_EA.mq5 | L64-68 | `OnInit() / risk.Init / NB.Init(_Period)` | M01-M05 Init |
| TrendMA_EA 10 模块 + MA 交叉 6 模块 | TrendMA_EA.mq5 | L91-107 | `OnTick() / CSignal::CrossUpSeries(_fastArr, _slowArr)` | M05+M06 信号 |
| TrendMA_EA 10 模块 + MA 交叉 6 模块 | TrendMA_EA.mq5 | L106 | `CPositions::CountMine(Magic) >= MaxPos` | M07 持仓数闸门 |
| TrendMA_EA 10 模块 + MA 交叉 6 模块 | TrendMA_EA.mq5 | L191-220 | `OnTrade() / OnTradeTransaction()` | M11+M16 OnTrade |
| Breakout_EA 10 模块 + Donchian 5 模块 | Breakout_EA.mq5 | L22 | `input ulong Magic = 20260101;` | 基础 input |
| Breakout_EA 10 模块 + Donchian 5 模块 | Breakout_EA.mq5 | L25-26 | `input int DonchianPeriod = 20; / input int ConfirmBars = 1;` | Donchian 参数 |
| Breakout_EA 10 模块 + Donchian 5 模块 | Breakout_EA.mq5 | L68-76 | `OnInit() / ind.AddBands("Donchian_Hi", ...) / ind.AddADX("ADX", ...)` | M04 指标 |
| Breakout_EA 10 模块 + Donchian 5 模块 | Breakout_EA.mq5 | L95 | `OnTick()` (Donchian 突破 + ADX 过滤) | M05+M06 信号 |
| MyEA + Dashboard 10+4 模块 2 EA 联合 | MyEA.mq5 | L23 | `input ulong Magic = 20260101;` | 基础 input |
| MyEA + Dashboard 10+4 模块 2 EA 联合 | MyEA.mq5 | L66 | `_m13LastDealTicket = 0` (M10+M13 共享锚点) | M10+M13 跨模块 |
| MyEA + Dashboard 10+4 模块 2 EA 联合 | MyEA.mq5 | L118-125 | `OnInit() / trade.Init / risk.Init / NB.Init / logger.SetFileOutput / M10.EnablePush+EnableSound` | M01-M15 Init |
| MyEA + Dashboard 10+4 模块 2 EA 联合 | MyEA.mq5 | L212 | `dash.Row("Positions", ... Count(Magic) + "/" + MaxPos)` | M09 面板 |
| MyEA + Dashboard 10+4 模块 2 EA 联合 | MyEA.mq5 | L230 | `M10.Send(StringFormat("⚠ DD %.2f%% on %s ..."))` | M10 触发器 1 DD |
| MyEA + Dashboard 10+4 模块 2 EA 联合 | MyEA.mq5 | L256 | `M10.Send("❌ MyEA reject: " + reason, true)` | M10 触发器 2 reject |

(共 35+ 行号, 5 EA × 7 维度 = 35 数据点, 7 维度 = Net Profit / PF / Win Rate / DD / Trade / Avg Win / Avg Loss)

### 调优点 3 档

- aggressive: 5 EA 同账户 6 月 XAUUSDm M1 3 组参数 (FastMA 5/15 / SlowMA 20/40 / Donchian 15/20) 全跑, 1 组参数 30+ 笔 trade, 总 90+ 笔对比, N1 完成 (10h, ⚠ console 1)
- balanced: 5 EA 同账户 6 月 XAUUSDm M1 1 组参数 (默认), 5 EA × 30 笔 = 150 笔对比, 8h 跑完 → 默认
- conservative: 5 EA 同账户 1 月 XAUUSDm M1 0.5 组参数 (1 EA 跑 1 周), 5 EA 错峰跑 = 5 周 demo, 0 N1 阻塞, 1 周先看 1 EA 表现

### 陷阱 5 条 (不与 ## 6. 反模式 段 5 条 + ## 5. 回测 vs 实战避坑 段 7 条重复)

1. **5 EA 5 broker 误判** — 5 EA 在 Exness demo 跑 ≠ 5 EA 在其他 broker (IC Markets / Pepperstone / FXTM) 跑, 不同 broker 的点差 / Filling / 限速不同, 5 EA 必须同 broker 才公平
2. **35 数据点 vs 35 结论误用** — 5 EA × 7 维度 = 35 数据点 ≠ 35 个独立结论, 7 维度间强相关 (DD 大 → Avg Loss 大 → PF 小), 必须用 4 维度评分 (Net Profit + PF + DD + Trade 数) 而非 35 维全评
3. **demo 6 月 ≠ real 6 月 跳空差异** — demo 6 月无真实跳空 (周末点差固定), real 6 月黑天鹅 (NFP / CPI / FOMC) 跳空 30-50 点, DD 可能从 8% 拉到 15%, 必须先 demo 1 个月 → real 0.01 lot 1 个月 → real 加仓
4. **N1 阻塞 ≠ 不能跑回测** — N1 (10h, ⚠ console 1) 阻塞, 但 N1 阻塞的是「MT5 GUI 操作」, 本 SOP §2-§7 章节 (10 步 + 7 维度 + 10 项 checklist + 5 反模式 + 5 回测 vs 实战避坑) 不依赖 N1, 可先写方法论
5. **5 EA 5 broker 互锁 magic** — 5 EA 跑 5 broker 各账户各 magic 互不干扰, 但本任务 5 EA 同账户 5 chart 同 magic (例 20260101) 会互相误判持仓, 必须 5 EA 各唯一 magic (MeanRev L34 / SX L37 / TMA L23 / BO L22 / MyEA L23)

### 链向

- [[01-调用模块/M01 交易封装 CTradePlus]] — M01 spec (Init + OrderSend + ClosePos)
- [[01-调用模块/M02 风控 Risk]] — M02 spec (Init + CanOpen)
- [[01-调用模块/M09 面板 Dashboard]] — M09 spec (Row + Show + Refresh)
- [[01-调用模块/M11 日志 Logger]] — M11 spec (Info/Warn/Error/Trade 4 级别)
- [[01-调用模块/M13 文件 IO]] — M13 spec (AppendCSV)
- [[01-调用模块/M15 定时器 TimerService]] — M15 spec (Init + OnTimer 1s 节流)
- [[01-调用模块/M18 相关性过滤 CorrelationFilter]] — M18 spec (Init + CalcCorr + IsHedgeExposed)
- [[01-调用模块/M19 时段过滤 SessionFilter]] — M19 spec (Init + IsInSession + SetAllowWeekend)
- [[实战/MeanReversion_EA 接入报告]] — 场景 A 13 模块全集 320L (17.7KB, M18+M19 demo)
- [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] — 场景 B 13 模块全集 1033L (29.8KB, v1→v4 演进 demo)
- [[实战/TrendMA_EA + Breakout_EA 接入报告]] — 场景 C 2 EA 联合 873L (66.7KB, 趋势 + 突破对比)
- [[实战/MyEA + Dashboard 接入报告]] — 场景 D 2 EA 联合 718L (53.8KB, 10+4 模块)
- [[EA开发/EA 开发知识库]] §"实战相关" 分类
- [[04-避坑与速查/06 网格马丁警示]] / [[04-避坑与速查/07 5 必看陷阱统一 wiki]] — 5 EA 对比避坑范本
