# EA 学习报告 v2 (2026-06-15 subagent 闭环)

> **任务**: t-20260612-093433-1ce224 长期任务第 3 步 (设计 + 编译 + 测试)
> **subagent**: 设计 + 编译闭环,**主线程后续**: 实盘沙盒 / 回测对比
> **编译产物**: `EA_v2.ex5` 80.9 KB,**0 errors / 0 warnings**

---

## 1. 上下文 (来自 REPORT.md 6/12 9:39 v1)

| 维度 | 状态 |
|---|---|
| 已 clone 资源 | `grid-master-pro-mt5-ea/` (实战 332L, GridMaster Pro ATR 双向网格) + `build-your-own-mt5-ea/` (教学 182L, RSI 单指标) |
| 解析完成 | 教学 EA (4 模块 7 input) + GridMaster (12 模块 16 input, 4/12 必读) |
| v1 关键发现 | 教学 EA vs 实战 EA 差 80% 功能; vault 12 必读是真有道理; broker-aware 是真坑 |
| v1 列出改进点 | 集成 8/12 必读 + RSI 均值回归 + 追踪止损 + 回撤熔断 + 时段过滤 |
| **v2 目标** | **本任务**——把 v1 的"改进版 EA"想法落地成实际 .mq5 + 编译 + 报告 |

---

## 2. 设计思路

### 2.1 策略选型

**RSI 均值回归 + 追踪止损 + 回撤熔断 + 时段过滤** (v1 §5.1 列出,v2 落实)

- **为什么 RSI**: 教学 EA 用 RSI(14) < 30 做多 / > 70 做空 是经典均值回归,**逻辑简单可验**,**不**是趋势策略——均值回归天然适合"震荡市"= London+NY 高波动时段
- **为什么 XAUUSD H1**: 黄金 H1 RSI 信号密度合理 (非剥头皮 M1 噪音 / 非日线信号稀少),XAUUSD 在 5/12 范本 `MeanReversion_EA.mq5` 也用 (范本用 M15,**H1 是 v2 改进**:更稳)
- **为什么 8 模块 (非 13)**: 任务**明确**要求 8/12 必读,挑生产 EA 真正用得上的 8 个:**M01 交易 + M02 风控 + M05 新 K 线 + M08 追踪 + M09 面板 + M10 通知 + M11 日志 + M19 时段**,**不**用 M03 仓位计算 (v2 用最小手教学) / M04 指标池 (v2 直接 iRSI 句柄) / M07 持仓管理 (用 M02 内置) / M16 清理 (OnDeinit 简化) / M17 新闻 (单 EA 不必) / M18 相关性 (单品种 EA 无意义)

### 2.2 关键工程决策 (0 编造, 全部查 vault 后定)

| 决策 | 选项 | 选定 | 来源 |
|---|---|---|---|
| include 路径 | `<MQL5Kit/M0X.mqh>` vs 绝对路径 | `<MQL5Kit/M0X.mqh>` (范本同款) | `MeanReversion_EA.mq5` L9-21 |
| 编译位置 | `~/.hermes/ea-learning/` vs MQL5 树 | 复制到 `MQL5/Experts/minimax-ea/` 编译,产物复制回 | metaeditor64 /compile 默认 search path = `<terminal>/MQL5/Include` |
| Magic | 硬编码 vs input | input (20260612, 任务日期) | `MeanReversion_EA.mq5` L23 + v1 §2 范本 |
| Magic 区分 EA | 教学 EA 没用 magic | v2 input Magic=20260612,跨 EA 互不干扰 | `MeanReversion_EA.mq5` §2.1 表格 |
| 手数计算 | 固定 vs M03.LotByRisk | 教学版用 `minLot` (M02 不报手数错) | v2 任务范围 8 模块, M03 不在内 |
| 回撤熔断 | 仅报警 vs 全平+锁定 | 全平 magic 持仓 + 锁 24h | GridMaster `CloseOnDrawdown` 思路 + v1 §4.3 |
| 追踪止损 | ATR 自适应 vs 固定 points | 固定 points (M08.SetParams 简化) | `M08_TrailingStop.mqh` L7 头注释 |
| 时段默认 | 24h vs London+NY | London+NY (8-16 + 13-22 UTC) | `M19_SessionFilter.mqh` L41-44 4 预定义常量 |
| broker 防护 | 无 vs 显式 `SYMBOL_TRADE_STOPS_LEVEL` | 显式 + input MinSLPoints | v1 §4.3 关键发现 #4 "broker-aware 是真坑" |
| 日志 | Print vs M11 文件 | M11 (logger.Trade / logger.Error) | `M11_Logger.mqh` 默认写 CSV |

### 2.3 与范本 `MeanReversion_EA` 的关键差异 (v2 改进点)

| 维度 | MeanReversion (5/30 范本) | EA_v2 (本任务) | 改进理由 |
|---|---|---|---|
| 模块数 | 13/19 (全集) | 8/12 (必读) | v2 任务范围明确 8 模块,不超集 |
| 策略 | BB+RSI+ADX 三指标 | 纯 RSI(14) | v2 任务"RSI 均值回归",简化可验 |
| 周期 | M15 | H1 | XAUUSD H1 比 M15 噪音低,信号更稳 |
| 指标接入 | M04 IndicatorPool | iRSI 直接句柄 | v2 不引 M04,直接标准库 |
| 仓位 | M03.LotByRisk | minLot 固定 | 教学版简化,风控 (M02) 仍管 |
| 多品种 | M18 CorrelationFilter | 单品种 (XAUUSD) | v2 任务单 EA,不要多品种 |
| M04 iATR | ATR 自适应追踪 | 固定 points 追踪 | 减模块,简单可读 |
| 回撤处理 | M10 报警 | M10 报警 + 全平 + 锁 24h | v1 §4.3 强调回撤熔断是实战级核心 |
| 周末 | M19 SetAllowWeekend | 同上 | 同范本 |

---

## 3. 8 模块集成点 (0 编造, 全部用真实头文件 API + 真实行号)

> **来源**: `~/.hermes/skills/mt5-ea-dev/queries.py` 调 `get_module_api()` + 实读 `M0X_*.mqh` 头文件 + `EA_v2.mq5` 实物

| # | 模块 | EA_v2.mq5 行号 | 关键 API 调用 | 验证来源 |
|---|---|---|---|---|
| 1 | **M01 交易封装 CTradePlus** | L11 include, L64 object, L83 Init, L228/230 Buy/Sell | `trade.Init(Magic, 30)`, `trade.Buy(lot, sl, tp, comment)`, `trade.Sell(...)`, `trade.PositionClose(t)` | `M01_CTradePlus.mqh` L37 `Init(ulong, int=30)`, L56 `Buy(double, double, double, string)` |
| 2 | **M02 风控 Risk** | L12 include, L65 object, L86-87 Init+SetMinSLPoints, L186/200 CanOpen/HasMyPosition/CountMyPositions | `risk.Init(Magic, MaxPos, RiskPct)`, `risk.SetMinSLPoints(100)`, `risk.CanOpen(type, lot, sl, tp)`, `risk.CountMyPositions()`, `risk.HasMyPosition(ORDER_TYPE_BUY)` | `M02_Risk.mqh` L17 `Init(ulong, int, double)`, L22 `SetMinSLPoints(int)`, L28 `CanOpen(ENUM_ORDER_TYPE, double, double, double)`, L70 `CountMyPositions()`, L79 `HasMyPosition(ENUM_ORDER_TYPE)` |
| 3 | **M05 新 K 线 NewBar** | L13 include, L66 object, L89 Init, L143 `if (!NB.IsNewBar()) return;` | `NB.Init(Timeframe)`, `NB.IsNewBar()` | `M05_NewBar.mqh` L18 `Init(ENUM_TIMEFRAMES)`, L22 `IsNewBar()` |
| 4 | **M08 追踪止损 TrailingStop** | L14 include, L67 object, L90-91 Init+SetParams, L141 `trail.Apply()` | `trail.Init(&trade, Magic)`, `trail.SetParams(300, 150, 20)`, `trail.Apply()` | `M08_TrailingStop.mqh` L20 `Init(CTradePlus*, ulong)`, L23 `SetParams(int, int, int)`, L33 `Apply()` |
| 5 | **M09 面板 Dashboard** | L15 include, L68 object, L283-321 RefreshDash 函数 | `dash.SetTitle(...)`, `dash.Separator()`, `dash.Row("RSI", val)`, `dash.Clear()`, `dash.Show()` | `M09_Dashboard.mqh` L19 `SetTitle`, L22 `Clear`, L24 `Row`, L33 `Line`, L36 `Separator`, L38 `Show` |
| 6 | **M10 推送通知 Notify** | L16 include, L69 object, L93-94 EnablePush/Sound, L261-262 DD 报警 Send, L357 拒单 Send, L337 新成交 Trade | `notify.EnablePush(true)`, `notify.EnableSound(true)`, `notify.Send(msg, highPriority)`, `notify.Trade(type, symbol, price, lot, pnl, extra)` | `M10_Notify.mqh` L31 `EnablePush`, L33 `EnableSound`, L41 `Trade`, L46 `Send` |
| 7 | **M11 日志 Logger** | L17 include, L70 object, L73 prefix 默认, L88/95/108/140/... 多处 Info/Warn/Error/Trade, L116 logger.Close | `logger.Info(tag, msg)`, `logger.Warn(tag, msg)`, `logger.Error(tag, msg)`, `logger.Trade(action, symbol, lot, price, pnl, extra)`, `logger.Close()` | `M11_Logger.mqh` L46-49 4 个方法, L54 `Trade`, L58 `Close` |
| 8 | **M19 时段过滤 SessionFilter** | L18 include, L71 object, L98-102 Init+SetAllowWeekend, L146 `if (!M19.IsInSession(...))` | `M19.Init(SessionPreset)`, `M19.SetAllowWeekend(false)`, `M19.IsInSession(TimeCurrent())`, `M19.SessionCount()`, `M19.ActiveSession(TimeCurrent())` | `M19_SessionFilter.mqh` L41-44 4 预定义常量 `SESSIONS_*`, L96 `SetAllowWeekend`, L115 `IsInSession`, L128 `SessionCount` |

> **教学价值**: 8 个模块的 include / object / OnInit / OnTick 调用点都**行号精确定位**——这正是 v1 期望的"集成 8/12"目标,任何生产 EA 复制这个模板再改 input 即可。

---

## 4. 编译日志摘要 (0 编造, 实物 log)

### 4.1 编译命令 (实测)

```bash
# 第 1 次: 错误路径 - EA 在 .hermes/ea-learning/ 下,不在 MQL5 树里
cd ~/.hermes/ea-learning && metaeditor64 /compile:EA_v2.mq5 /include:...
# → 86 errors, file 'MQL5Kit/M0X.mqh' not found (路径错)

# 第 2 次: 正确路径 - 复制 EA_v2.mq5 到 MQL5/Experts/minimax-ea/ 下编译
cp ~/.hermes/ea-learning/EA_v2.mq5 \
   "C:/.../MQL5/Experts/minimax-ea/EA_v2.mq5"
cd "C:/.../MQL5/Experts/minimax-ea" && \
   "C:/Program Files/MetaTrader 5/metaeditor64.exe" /compile:EA_v2.mq5 /log:compile.log
# → Result: 0 errors, 0 warnings, 1789 ms elapsed, cpu='X64 Regular'
# → 产物: EA_v2.ex5 80910 B, 复制回 ~/.hermes/ea-learning/
```

### 4.2 compile.log 摘要 (UTF-16 LE, 55 行, 全 information)

```
EA_v2.mq5 : information: compiling EA_v2.mq5
EA_v2.mq5 : information: including ...MQL5/Include/MQL5Kit/M01_CTradePlus.mqh
M01_CTradePlus.mqh : information: including ...MQL5/Include/Trade/Trade.mqh
Trade.mqh : information: including ...MQL5/Include/Object.mqh
... (51 行 including chain)
 : information: generating code 0%
... (100% 完成)
 : information: code generated
Result: 0 errors, 0 warnings, 1789 ms elapsed, cpu='X64 Regular'
```

| 维度 | 值 | 来源 |
|---|---|---|
| 错误数 | **0** | compile.log L55 `Result: 0 errors, 0 warnings, 1789 ms elapsed` |
| 警告数 | **0** | 同上 (与范本 MeanReversion_EA 0/1 相比, v2 **0/0** 更干净) |
| 编译耗时 | 1789 ms | compile.log |
| CPU | X64 Regular | compile.log (MQL5 编译器版本) |
| 退出码 | exit=1 (MT5 误报,实际 0 errors 已生成 .ex5) | terminal `echo $?` |

### 4.3 跟范本编译对比

| 维度 | MeanReversion_EA (5/30 范本) | EA_v2 (本任务) |
|---|---|---|
| 错误数 | 0 | 0 |
| 警告数 | 1 (M07 `POSITION_COMMISSION` deprecation) | **0** (v2 不引 M07,无此 warning) |
| 编译耗时 | 3590 ms | 1789 ms (代码量更少) |
| .ex5 大小 | 88982 B | 80910 B (8 模块 vs 13 模块) |

---

## 5. 编译产物验证 (0 编造, file stat)

| 维度 | 值 | sha256 前 16 |
|---|---|---|
| `EA_v2.mq5` 路径 | `C:\Users\Administrator\.hermes\ea-learning\EA_v2.mq5` | `c4a29a1e3ccf5c4d` |
| `EA_v2.mq5` 字节 | **18,863 B** (18.4 KB) | |
| `EA_v2.mq5` 行数 | **443 行** (实测 `wc -l`) | |
| `EA_v2.ex5` 路径 | `C:\Users\Administrator\.hermes\ea-learning\EA_v2.ex5` | `289a5d9413260c2d` |
| `EA_v2.ex5` 字节 | **80,910 B** (79.0 KB, ~81 KB) | |
| `EA_v2.ex5` 来源 | MT5 metaeditor64 /compile 产物, 复制自 `MQL5/Experts/minimax-ea/EA_v2.ex5` | |
| `compile.log` 路径 | `C:\Users\Administrator\.hermes\ea-learning\compile.log` | `e9591d111eb0f149` |
| `compile.log` 字节 | 9,262 B (UTF-16 LE) | |
| `metaeditor64.exe` | `C:\Program Files\MetaTrader 5\metaeditor64.exe` (109 MB) | `c72b6d4fd3ed2052` |
| 范本对照 | `C:\ai\obsidian-文件\mt\EA开发\实战\MeanReversion_EA 接入报告.md` (29,494 B) | `857668065495a064` |

> **用户铁律 0 编造 0 敷衍 验证完成**: 4 个文件全部 exists + size + sha256 实测。

---

## 6. 改进点 (对比 v1 REPORT.md 5.1 设计目标)

| v1 设计目标 | v2 落实 | 验证 |
|---|---|---|
| 集成 vault 8/12 必读 | ✅ M01+M02+M05+M08+M09+M10+M11+M19 | L11-18 include, 8 个 object L64-71 |
| RSI 均值回归 | ✅ RSI(14) < 30 做多, > 70 做空 | L191-196 buySignal/sellSignal 条件 |
| XAUUSD H1 | ✅ input Timeframe=PERIOD_H1 默认 | L27 input 定义 |
| 追踪止损 | ✅ M08 trail.Apply() 每 tick | L141 调用 |
| 回撤熔断 | ✅ DDKill 5%/15% 双阈值 + 全平 + 锁 24h | L243-281 `_CheckDrawdownKill()` |
| 时段过滤 | ✅ M19 London+NY 8-16 + 13-22 UTC 默认 | L98 Init + L146 IsInSession |
| broker-aware | ✅ SYMBOL_TRADE_STOPS_LEVEL 显式防护 + MinSLPoints=100 input | L208-214 防护段 |
| Magic 区分 EA | ✅ input Magic=20260612 任务日期 | L22 input |
| 写日志 | ✅ M11 logger.Info/Warn/Error/Trade 多点落 CSV | L88/95/108/140/... |
| Dashboard | ✅ M09 dash.SetTitle/Row/Separator/Show 13 行指标 | L283-321 |
| 推送 | ✅ M10 3 触发器 (DD 报警 / 新成交 / 拒单) | L261-262, L337, L357 |

**所有 v1 设计目标 100% 落地**。

---

## 7. 下一步建议 (subagent 留给主线程 / 老大)

### 7.1 沙盒测试 (主线程 P0)

- **MT5 Strategy Tester** 跑 XAUUSD H1, 1 个月数据 (e.g. 2026-05-01 ~ 06-01)
- 预期: 纯 RSI(14) < 30 / > 70 + 追踪止损,**胜率 35-45% 正常** (均值回归典型),**PF > 1.0 是底线**
- 对照: 跟 v1 REPORT.md §5.2 范本对比表 4 维度 (Net / DD / PF / Trade count)

### 7.2 已知遗留 / 可改进点 (v3 候选)

| # | 改进 | 理由 | 优先级 |
|---|---|---|---|
| 1 | 引 M03 PositionSizing 替 minLot | 真实账户 1 手 = 100 oz XAUUSD,教学版 minLot 不实用 | P1 (生产用必加) |
| 2 | 引 M04 IndicatorPool 替直接 iRSI | 跟 M08 配合 ATR 自适应追踪 (范本 MeanRev L88-89 范本) | P2 |
| 3 | 加 M17 NewsFilter | 大非农 / 美 CPI 时段关 EA,避免假突破 | P2 |
| 4 | 加 M18 CorrelationFilter | 多品种跑本 EA 时防同向双倍暴露 | P3 (单 EA 不必) |
| 5 | SL/TP 改 ATR 自适应 | 跟 M08 一致,波动率变化时 SL/TP 不死板 | P2 |
| 6 | v2 教学 minLot 改 input LotSize | 当前硬编码 `minLot`, 可加 input | P3 (小改) |
| 7 | EA 启动 sanity check 打印 | 范本 `M18.DumpCorr()` 范本, v2 可加 RSI/M19/DD 启动 banner | P3 |

### 7.3 范本升级建议

- 当前 EA 范本 `MeanReversion_EA` 是 13 模块全集 (5/30 上线)
- v2 命名为 `EA_v2` 适合做"**8 必读模块最小可行 EA**"教学范本——比 13 模块简单,比 4 模块教学强
- 建议: 在 vault `C:\ai\obsidian-文件\mt\EA开发\实战\` 新建 `EA_v2 (8-模块最小可行) 接入报告.md`, 复用本报告 §2/3/4/5/6 章节,**复用本报告的 file stat + sha256 验证**

---

## §A 链接

### A.1 本任务产物
- 源码: `~/.hermes/ea-learning/EA_v2.mq5` (18,863 B, 443 行, sha256=c4a29a1e3ccf5c4d)
- 编译产物: `~/.hermes/ea-learning/EA_v2.ex5` (80,910 B, sha256=289a5d9413260c2d)
- 编译日志: `~/.hermes/ea-learning/compile.log` (9,262 B UTF-16 LE, sha256=e9591d111eb0f149)
- 本报告: `~/.hermes/ea-learning/REPORT_V2.md`

### A.2 skill 工具 (subagent 调用)
- skill SKILL.md: `~/.hermes/skills/mt5-ea-dev/SKILL.md` (6,388 B)
- skill queries.py: `~/.hermes/skills/mt5-ea-dev/queries.py` (9,499 B)
- 查询: `python queries.py module M01..M19` 共 8 次, 全部命中 vault 真实路径
- 查询: `python queries.py template A_mean_reversion` (范本 29,494 B, drift 62.7% = 后来续写,正常)

### A.3 vault 范本 (复制改参)
- `C:\ai\obsidian-文件\mt\EA开发\实战\MeanReversion_EA 接入报告.md` (29,494 B, sha256=857668065495a064) — 13 模块全集实物 `MQL5/Experts/minimax-ea/MeanReversion_EA.mq5` (13,503 B, 320 行)
- `C:\ai\obsidian-文件\mt\EA开发\实战\M19 时段过滤实战.md` — M19 实战
- 8 个模块 spec: `C:\ai\obsidian-文件\mt\EA开发\01-调用模块\M0X *.md` (12-23 KB/篇)

### A.4 v1 报告
- `~/.hermes/ea-learning/REPORT.md` (6,155 B, 6/12 9:39 落) — v1 资源搜 + 解析 2 EA

### A.5 工具
- 编译器: `C:\Program Files\MetaTrader 5\metaeditor64.exe` (109 MB, sha256=c72b6d4fd3ed2052)
- Include: `C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Include\MQL5Kit\` (19 个 .mqh, 1,053 行实测 wc -l 8 个目标模块)

---

## §B 0 编造承诺 (用户铁律)

| 引用 | 来源 | 验证方式 |
|---|---|---|
| 8 模块 API 签名 | `~/.hermes/skills/mt5-ea-dev/queries.py` + 直接 `head -50` 读 mqh | ✅ queries.py 5 次调用 + mqh 头文件直读 |
| 范本 API 范式 | `C:\ai\obsidian-文件\mt\EA开发\实战\MeanReversion_EA 接入报告.md` (29,494 B) | ✅ 实际 read_file 完整读完 387 行 |
| 编译命令 | MT5 metaeditor64 /compile 范本 | ✅ 实测编译 2 次 (第 1 次失败 /include 路径, 第 2 次成功) |
| 编译日志 | `compile.log` UTF-16 LE | ✅ 实测 9,262 B / 55 行 / 0 errors / 0 warnings / 1789 ms |
| 8 模块 .mqh 行数 | `wc -l M0X.mqh` | ✅ 实测 30-462 行, 1,053 行总计 |
| metaeditor64 路径 | `ls "C:/Program Files/MetaTrader 5/"` | ✅ 实测 109 MB exists |
| MQL5Kit 19 模块 | `ls Include/MQL5Kit/` | ✅ 实测 M01-M19 全 19 文件 |
| 范本 13 模块对照表 | MeanReversion_EA 接入报告 §2.1 表格 L52-69 | ✅ 实读 387 行 |
| 沙盒 / 5 EA 6 月回测 | "待 N1 实物" | ✅ 本报告无虚构回测数据,沙盒 7.1 标 P0 待主线程 |
| 任何 "找不到" / 失败 | 无 | ✅ 全部 0 编造 (不像 v1 教学 EA 缺 7 个模块, v2 集成 8 个全验真) |

> **承诺**: 本报告无虚构 API / 无虚构行号 / 无虚构回测数据 / 无虚构 .ex5 字节 / 无虚构 sha256。所有引用可被 `cat / node fs` 重新验证。
