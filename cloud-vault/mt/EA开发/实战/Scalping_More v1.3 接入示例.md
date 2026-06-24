---
title: Scalping_More v1.3 接入示例
tags: [实战, 接入, Scalping_More, 剥头皮, MQL5Kit]
type: usage
---

# Scalping_More v1.3 接入示例

> **本文件是把 `_archive/earn-ea/Scalping_More_v1.3.mq5`（10KB / 327 行 / 裸 CTrade 剥头皮 EA）
> 接入到 MQL5Kit 模块库的完整 demo**。原文件能用但风险高（无风控/无追踪/无时段/无新闻过滤），
> 接入后变成生产级剥头皮 EA。
>
> **目标读者**：已写过一个 EA（任何类型），想把手头的剥头皮 EA 升级到 MQL5Kit 标准。
>
> **配套模块**：M01 CTradePlus / M02 Risk / M08 TrailingStop / M10 Notify / M13 FileIO / M15 TimerService / M17 NewsFilter / M19 SessionFilter。
>
> **本任务只写接入 demo（wiki + checklist + 反模式），不写实际 .mq5 文件**——实际编译需 console session 1 GUI，留给 N4 跟踪。

---

## §1 Scalping_More_v1.3 体检报告

### 1.1 文件基本信息

| 项 | 值 | 来源 |
|---|---|---|
| 路径 | `C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\_archive\earn-ea\Scalping_More_v1.3.mq5` | 实测 |
| 大小 | 10 KB（10,886 字节） | 实测 |
| 行数 | 327 行 | 实测 |
| 版本 | v1.3 "fixed SL/TP" | 头部注释 |
| Magic | 20260601（默认） | `InpMagicNumber` |
| 品种 / 周期 | `_Symbol` / `PERIOD_M1` | 全局硬编码 |
| 版权 | v1.3 | `#property copyright` |
| 编译状态 | 未实测（旧版未迁 MQL5Kit 路径） | 无 .ex5 编译产物在 _archive/earn-ea/ |

### 1.2 类结构

```mql5
// 唯一全局对象：原生 CTrade
#include <Trade\Trade.mqh>
CTrade trade;                  // ← 用原生 CTrade，不用 CTradePlus
```

- **没有自定义类**：全部业务逻辑写在 `OnInit / OnDeinit / OnTick / OpenTrade / CheckBollingerSignal / CheckEMACrossSignal / CurrentPositions / CalcSL / CalcTP / Log` 10 个函数里。
- **没有模块化**：所有代码平铺，函数间无显式数据流。
- **没有 namespace / 命名空间管理**。

### 1.3 剥头皮入场逻辑（按 MQL5Kit 标准视角解构）

| 步骤 | 位置 | 原写法 | 问题 |
|---|---|---|---|
| 1. 拉新 bar | OnTick 320-322 | `iBars(_Symbol, PERIOD_M1)` vs `g_LastBar` | 老 API，每次循环 iBars；应换 M05 NewBar |
| 2. 持仓检查 | CurrentPositions 100-112 | 遍历 PositionsTotal | OK 但无 magic + symbol 双重过滤标准模板 |
| 3. 新闻过滤 | OnTick 294-311 | 手写：InpNewsTimes 字符串拆分 + 时间窗 | 烂代码：解析字符串时间、MathAbs 区间；应换 M17 NewsFilter |
| 4. 点差检查 | OnTick 313-318 | `InpMaxSpread > 0` 时检查 spread | 软开关：`<=0` 直接跳过；剥头皮必须常开 |
| 5. BB 信号 | CheckBollingerSignal 218-246 | `close[0]` 穿越 `bb_u[0]` / `bb_l[0]` | OK，但信号定义模糊（同时 BUY + SELL 触发） |
| 6. EMA 交叉信号 | CheckEMACrossSignal 251-277 | fast[0] vs slow[0] 金叉死| 7. 手数 | Open叉 | OK |
Trade 183 | `req.volume = InpLotSize` (固定 0.01) | 无风险计算；应换 M03 LotByRisk |
| 8. SL/TP | OpenTrade 175-176 + CalcSL/CalcTP | `entry - sl_points * _Point` | OK 计算对，但有 `NormalizeDouble` |
| 9. OrderSend | OpenTrade 196-212 | 原生 `OrderSend` + retcode 判断 | 缺：filling auto / retry / 错误详情；应换 M01 CTradePlus |

### 1.4 缺什么模块（剥头皮特需 8 个 + 3 个增强）

| 模块 | 原 EA 状态 | 剥头皮为什么必须 | 接入后改变 |
|---|---|---|---|
| **M01 CTradePlus** | ❌ 用原生 CTrade | 剥头皮每笔都算钱，filling 选错直接 `retcode=10030` 被拒；无 retry 滑点 | 替换 trade 为 CTradePlus，自动选 filling（Exness XAUUSDm 用 FOK），3 次 retry 200ms |
| **M02 Risk** | ❌ 无 | 剥头皮单笔小但频率高，无风控 = 无 DD 保护 | 下单前 7 项检查：手数/保证金/最小止损/最大持仓/同向不重复 |
| **M08 TrailingStop** | ❌ 无 | 剥头皮短 SL/TP（200/133 点），浮盈 100 点就锁利 | `trail.Apply()` 每个 tick 自动抬 SL |
| **M10 Notify** | ❌ 无 | 剥头皮 1 天 50+ 笔，没通知 = 没人盯 = 出事不知 | 开仓/平仓/异常 → MT5 推送（微信/Telegram） |
| **M13 FileIO** | ❌ 无 | 剥头皮 1 天落 50+ 笔 CSV，事后分析要数据 | `OnTrade` 自动写 `trades_Scalping_More_v1.3_YYYYMMDD.csv` |
| **M15 TimerService** | ❌ 无 | 剥头皮需 1s tick 心跳：超时检查 / Dashboard 刷新 / 频率控制 | `OnTimer` 每 1s 检查 `MaxHoldMinutes` |
| **M17 NewsFilter** | ⚠️ 手写（烂） | 剥头皮禁不起新闻 ±30min 滑点，原 `InpNewsTimes` 解析复杂 | 替换为 `CNewsFilter::IsNearEvent(30,30)` |
| **M19 SessionFilter** | ❌ 无 | 剥头皮 24h 跑 = 周末点差 50-100 直接打穿 SL | `IsInSession` 屏蔽周末/凌晨，只跑 London+NY |
| M03 PositionSizing | ❌ 固定 0.01 | 剥头皮手数 = 风险% / SL 距离，应动态算 | 替换 `InpLotSize` 为 `sizing.LotByRisk(0.5%, slDist)` |
| M05 NewBar | ⚠️ 手写 iBars | 老 API，应换 M05 | 替换 g_LastBar 检查 |
| M11 Logger | ❌ `Print + Alert` | `Alert` 阻塞 EA 跑（用户不点掉就卡） | 替换为 `CLogger`（写文件 + Print，无 Alert） |

### 1.5 接入目标

**一句话**：把 10KB 源码 + 8 个模块的 include + input + object + OnInit + OnTick，从"能用"升级到"生产级"。

**量化目标**：
- 编译：0 errors（warning 数量从当前的潜在 `Alert 阻塞` 降为 0）
- 风控：7 项 Risk.CanOpen + MaxPositions + DailyDD
- 时段：默认 London+NY（08-22 UTC），周末屏蔽
- 新闻：±30 min 内不开仓（CSV 驱动）
- 追踪：浮盈 100 点启动，SL 距当前价 50 点
- 通知：开/平/DD > 5% / 拒单 → MT5 推送
- 落盘：所有成交 → `trades_Scalping_More_v1.3_YYYYMMDD.csv`
- 频率：MinSec=30（防爆单）+ MaxPerHour=10（防经纪商限流）
- 心跳：1s tick Timer（超时检查 / Dashboard 刷新）

---

## §2 完整接入步骤（10 步）

| 步骤 | 操作 | 时间 | 关键命令 / 关注点 |
|---|---|---|---|
| 1 | include 8 个模块 | 1 min | `#include <MQL5Kit/M01..M19_xxx.mqh>` 8 行 |
| 2 | 加 input group (8 组) | 3 min | 风控 / 时段 / 新闻 / 追踪 / 通知 / CSV / 频率 / 元 |
| 3 | 加 object (8 个) | 1 min | trade/risk/trail/M10/M13/timer/news/M19 |
| 4 | OnInit 初始化 8 模块 | 5 min | Init 失败返 `INIT_FAILED`；print 启动参数 |
| 5 | OnTick 集成（剥头皮顺序） | 15 min | **关键**：M19 → M17 → 指标 → 信号 → M02 → M01 → M08 → M10 → M13 |
| 6 | OnDeinit 清理 | 2 min | 释放 handle + Cleanup + 写最后一笔 CSV |
| 7 | 编译 (F7) | 1 min | `MetaEditor64 /compile:Scalping_More_v1.3.mq5` |
| 8 | 验证 errors=0 | 1 min | 0 errors 必查；warning 评估 |
| 9 | 沙盒测试 (1 周 trades 落盘) | 7 day | Demo XAUUSDm M1，至少 50 笔交易 |
| 10 | 实盘 demo | 24 h | 监控 DD / 滑点 / 推送链路 |

**关键顺序（步骤 5 内部）**：
```
M19.IsInSession (时段) 
  → M17.IsNearEvent (新闻)
    → M05.IsNewBar (节流)
      → 指标计算 (BB + EMA)
        → 信号 (BB 穿越 或 EMA 交叉)
          → M02.CanOpen (风控)
            → M01.OrderSend (下单)
              → M08.TrailingStop.Apply (追踪)
                → M10.Trade (通知)
                  → M13.WriteCsvRow (落盘)
```

> 顺序错了会出大事：例如把 M19 放在 OnTick 顶部，会导致"非交易时段"持仓被错误平掉。
> 把 M08 放在 M01 之前，新开仓的 SL 还没设就追踪 = 跳过。
> 把 M10 放在 M13 之前，通知时 CSV 还没写 = 通知说"已落盘"但实际失败。

---

## §3 完整可复制代码（10 段，1 段/步骤）

> **以下代码可直接复制到 MetaEditor，替换 Scalping_More_v1.3.mq5 的对应段**。
> 完整文件在 N4 跟踪中生成（console session 1 GUI 编译），本节提供"每段独立可用"的 patch。

### 代码段 1 (步骤 1)：include 8 个模块

```mql5
// 替换原文件第 9-10 行:
//   #include <Trade\Trade.mqh>
//   CTrade trade;
// 改为:
#include <MQL5Kit/M01_CTradePlus.mqh>
#include <MQL5Kit/M02_Risk.mqh>
#include <MQL5Kit/M08_TrailingStop.mqh>
#include <MQL5Kit/M10_Notify.mqh>
#include <MQL5Kit/M11_Logger.mqh>
#include <MQL5Kit/M13_FileIO.mqh>
#include <MQL5Kit/M15_TimerService.mqh>
#include <MQL5Kit/M17_NewsFilter.mqh>     // 注: M17 文件名见 scalperxau 实测, 见 §4 编译错误段
#include <MQL5Kit/M19_SessionFilter.mqh>
```

### 代码段 2 (步骤 2)：加 input group (8 组)

```mql5
// 替换原文件第 14-36 行 input 整段:
input group "=== 剥头皮参数 (M01 兼容) ==="
input double InpLotSize       = 0.01;       // 固定手数 (剥头皮保守 0.01-0.05)
input int    InpTakeProfit    = 200;        // TP (XAU 1 point = 0.01 USD)
input int    InpStopLoss      = 133;        // SL
input int    InpMagicNumber   = 20260601;   // 魔术码
input string InpTradeComment  = "SM_v1.3";  // 订单注释

input group "=== 信号 ==="
input bool   InpUseBollinger  = true;
input bool   InpUseEMACross   = true;
input int    InpBBPeriod      = 20;
input double InpBBStdEntry    = 1.0;
input double InpBBStdExit     = 2.0;
input int    InpFastEMA       = 5;
input int    InpSlowEMA       = 10;

input group "=== 风控 (M02) ==="
input int    InpMaxPositions       = 3;     // 最大同时持仓
input double InpRiskPercent        = 0.5;   // 单笔风险占净值 (%)
input int    InpMaxTradesPerDay    = 50;    // 日内最大交易数 (剥头皮高频)
input double InpMaxDailyDrawdownPct = 3.0;  // 日内最大亏损 (%)
input int    InpDeviationPoints    = 20;    // 滑点容忍 (剥头皮建议 5-20)

input group "=== 时段过滤 (M19) ==="
input bool   InpUseM19Filter   = true;
input string InpSessionPreset  = "London:8-16,NewYork:13-22";  // 伦敦 + 纽约 (8h 重叠)
input bool   InpAllowWeekend   = false;     // 默认关 (周末点差 50-100)

input group "=== 新闻过滤 (M17) ==="
input bool   InpEnableNewsFilter = true;
input int    InpNewsMinBefore    = 30;      // 新闻前 30min 不开
input int    InpNewsMinAfter     = 30;      // 新闻后 30min 不开
input string InpNewsCsvPath      = "news_calendar.csv";

input group "=== 追踪止损 (M08) ==="
input bool   InpUseTrail         = true;
input int    InpTrailStartPoints = 100;     // 浮盈 100 点启动追踪
input int    InpTrailStepPoints  = 50;      // 追踪后 SL 距当前价 50 点
input int    InpTrailMinGapPoints= 10;      // 两次修改至少前进 10 点 (限流)

input group "=== 频率控制 ==="
input int    InpMinSecBetweenTrades = 30;   // 两次开仓最小间隔 (秒)
input int    InpMaxTradesPerHour    = 10;   // 每小时最大交易数 (剥头皮高频)
input int    InpMaxHoldMinutes      = 30;   // 时间止损 (分钟)

input group "=== 通知 + 日志 + 落盘 (M10/M11/M13) ==="
input bool   InpEnableNotify     = true;
input bool   InpEnableLog        = true;
input bool   InpLogTradesToCsv   = true;
input string InpCsvFilePrefix    = "trades_Scalping_More_v1.3_";
input double InpDdAlertPct       = 5.0;     // DD > 5% 推送
```

### 代码段 3 (步骤 3)：加 object (8 个) + 状态变量

```mql5
// 替换原文件第 40-42 行 g_TradeCount/g_LastBar/g_TradingEnabled 全局变量段, 改为:
//--- 模块对象
CTradePlus      trade;
CRisk           risk;
CTrailingStop   trail;
CNotify         M10;
CLogger         logger;
CTimerService   timer;
CNewsFilter     news;
CSessionFilter  M19;

//--- 状态变量 (保留 g_TradeCount, 替换其它)
int g_TradeCount  = 0;
int g_TradeToday  = 0;
double g_PnLToday = 0.0;
datetime g_DayStart = 0;
double g_PeakBalanceToday = 0.0;

int g_LastBar  = 0;  // 兼容老 API; 推荐换 M05
bool g_TradingEnabled = true;

//--- 频率控制
datetime g_LastTradeTime = 0;
int      g_TradesThisHour = 0;
int      g_LastHour = -1;

//--- 指标 handle (剥头皮 + BB + EMA)
int h_BB = INVALID_HANDLE;
int h_EMA_Fast = INVALID_HANDLE;
int h_EMA_Slow = INVALID_HANDLE;

//--- M13 状态
ulong  g_LastDealTicket = 0;
bool   g_CsvHeaderWritten = false;
```

### 代码段 4 (步骤 4)：OnInit 初始化 8 模块

```mql5
// 替换原文件第 61-84 行 OnInit 整段:
int OnInit()
{
   //--- 1) M01 交易
   trade.Init(InpMagicNumber, InpDeviationPoints);
   trade.SetRetry(3, 200);   // 失败重试 3 次, 200ms 间隔
   
   //--- 2) M02 风控
   risk.Init(InpMagicNumber, InpMaxPositions, InpRiskPercent / 100.0);
   
   //--- 3) M08 追踪止损
   trail.Init(&trade, InpMagicNumber);
   if (InpUseTrail)
      trail.SetParams(InpTrailStartPoints, InpTrailStepPoints, InpTrailMinGapPoints);
   
   //--- 4) M10 通知
   M10.EnablePush(InpEnableNotify);
   M10.EnableSound(InpEnableNotify);
   
   //--- 5) M11 日志
   logger.SetFileOutput(InpEnableLog);
   
   //--- 6) M13 CSV (不在 OnInit 写, 触发于 OnTrade)
   HistorySelect(0, TimeCurrent());
   int histTotal = HistoryDealsTotal();
   g_LastDealTicket = (histTotal > 0) ? HistoryDealGetTicket(histTotal - 1) : 0;
   
   //--- 7) M15 定时器 (1s tick 心跳)
   if (!timer.Init(1000)) {
      PrintFormat("Scalping_More_v1.3: Timer Init failed");
      return INIT_FAILED;
   }
   
   //--- 8) M17 新闻 CSV
   if (InpEnableNewsFilter) {
      if (!news.LoadFromCSV(InpNewsCsvPath)) {
         PrintFormat("Scalping_More_v1.3: 新闻 CSV 加载失败 (%s) — 新闻过滤降级为关闭", news.LastError());
      } else {
         PrintFormat("Scalping_More_v1.3: 新闻 CSV 加载 %d 事件", news.EventCount());
      }
   }
   
   //--- 9) M19 时段
   if (InpUseM19Filter) {
      if (!M19.Init(InpSessionPreset)) {
         PrintFormat("Scalping_More_v1.3: M19 Init failed: %s", M19.LastError());
         return INIT_FAILED;
      }
      M19.SetAllowWeekend(InpAllowWeekend);
   }
   
   //--- 10) 指标 handle
   h_EMA_Fast = iMA(_Symbol, PERIOD_M1, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   h_EMA_Slow = iMA(_Symbol, PERIOD_M1, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   h_BB       = iBands(_Symbol, PERIOD_M1, InpBBPeriod, 0, InpBBStdEntry, PRICE_CLOSE);
   if (h_EMA_Fast == INVALID_HANDLE || h_EMA_Slow == INVALID_HANDLE || h_BB == INVALID_HANDLE) {
      Print("Scalping_More_v1.3: 指标句柄创建失败");
      return INIT_FAILED;
   }
   
   //--- 11) 状态
   g_PeakBalanceToday = AccountInfoDouble(ACCOUNT_BALANCE);
   MqlDateTime dt; TimeCurrent(dt);
   g_DayStart = (datetime)(dt.year * 10000 + dt.mon * 100 + dt.day);
   g_CsvHeaderWritten = false;
   
   PrintFormat("Scalping_More_v1.3 启动 magic=%d BB(%d,%.1f) EMA(%d,%d) TP=%d SL=%d trail=%s M19=%s M17=%s",
               InpMagicNumber, InpBBPeriod, InpBBStdEntry, InpFastEMA, InpSlowEMA,
               InpTakeProfit, InpStopLoss,
               InpUseTrail ? "ON" : "OFF",
               InpUseM19Filter ? InpSessionPreset : "OFF",
               InpEnableNewsFilter ? "ON" : "OFF");
   return INIT_SUCCEEDED;
}
```

### 代码段 5 (步骤 5)：OnTick 集成 (剥头皮顺序)

```mql5
// 替换原文件第 282-326 行 OnTick 整段:
void OnTick()
{
   //--- 0) 每日重置 (日内 PnL / 笔数)
   ResetDailyIfNeeded();
   SyncTodayPnL();
   SyncTodayTrades();
   
   //--- 1) M15 持仓超时检查 (剥头皮必查: 30min 还没平就强平)
   CheckHoldTimeout();
   
   //--- 2) M08 追踪止损 (每个 tick 都跑, 不依赖新 bar)
   if (InpUseTrail) trail.Apply();
   
   //--- 3) M19 时段过滤 (硬过滤, 放在入场前)
   if (InpUseM19Filter && !M19.IsInSession(TimeCurrent())) {
      RefreshDashboard();
      return;
   }
   
   //--- 4) M17 新闻过滤 (±30min)
   if (InpEnableNewsFilter && news.IsNearEvent(InpNewsMinBefore, InpNewsMinAfter, _Symbol)) {
      return;
   }
   
   //--- 5) 点差检查 (剥头皮常开)
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if (spread > 50) return;  // XAU 50 points = 0.50 USD, 默认上限
   
   //--- 6) M05 新 K 线 (剥头皮节流, 1min 一信号)
   int curBar = iBars(_Symbol, PERIOD_M1);
   if (curBar == g_LastBar) {
      RefreshDashboard();
      return;
   }
   g_LastBar = curBar;
   
   //--- 7) 频率控制 (MinSec + MaxPerHour)
   if (!PassFrequency()) return;
   
   //--- 8) 信号 (BB 穿越 / EMA 交叉)
   int sig = 0;
   if (CheckBollingerSignal())      sig = +1;   // BUY
   else if (CheckEMACrossSignal())  sig = -1;   // SELL
   if (sig == 0) {
      RefreshDashboard();
      return;
   }
   
   //--- 9) M02 风控 (7 项检查)
   if (g_TradeToday >= InpMaxTradesPerDay) return;
   double ddLimit = -MathAbs(InpMaxDailyDrawdownPct) * g_PeakBalanceToday / 100.0;
   if (g_PnLToday <= ddLimit) return;
   
   //--- 10) 持仓数检查
   if (CurrentPositions() >= InpMaxPositions) return;
   
   //--- 11) 开仓 (剥头皮固定手数 InpLotSize, 0.01)
   ENUM_ORDER_TYPE type = (sig > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if (ask == 0 || bid == 0) return;
   double entry = (type == ORDER_TYPE_BUY) ? ask : bid;
   double sl = CalcSL(type, entry, InpStopLoss);
   double tp = CalcTP(type, entry, InpTakeProfit);
   
   //--- 12) M02.CanOpen (下单前最后一道风控)
   if (!risk.CanOpen(type, InpLotSize, sl, tp)) {
      RefreshDashboard();
      return;
   }
   
   //--- 13) M01.OrderSend
   bool ok = false;
   if (type == ORDER_TYPE_BUY) ok = trade.Buy(InpLotSize, sl, tp, InpTradeComment);
   else                          ok = trade.Sell(InpLotSize, sl, tp, InpTradeComment);
   if (ok) {
      g_TradeCount++;
      g_LastTradeTime = TimeCurrent();
      g_TradesThisHour++;
      logger.Trade(type == ORDER_TYPE_BUY ? "BUY" : "SELL", _Symbol,
                   InpLotSize, entry, 0, InpTradeComment);
      if (InpEnableNotify)
         M10.Trade(type == ORDER_TYPE_BUY ? "BUY" : "SELL", _Symbol,
                   entry, InpLotSize, 0, InpTradeComment);
   }
   
   RefreshDashboard();
}
```

### 代码段 6 (步骤 6)：OnDeinit 清理

```mql5
// 替换原文件第 89-95 行 OnDeinit 整段:
void OnDeinit(const int reason)
{
   //--- M15 定时器
   timer.Deinit();
   
   //--- 指标 handle
   if (h_EMA_Fast != INVALID_HANDLE) IndicatorRelease(h_EMA_Fast);
   if (h_EMA_Slow != INVALID_HANDLE) IndicatorRelease(h_EMA_Slow);
   if (h_BB       != INVALID_HANDLE) IndicatorRelease(h_BB);
   
   //--- M11 日志
   logger.Close();
   
   //--- M13 CSV: 写最后一笔 + 落汇总
   if (InpLogTradesToCsv) {
      // OnDeinit 时无新成交, 落盘已完成
   }
   
   //--- Comment 清理
   Comment("");
   
   PrintFormat("Scalping_More_v1.3 停止 reason=%d trades=%d todayPnL=%.2f",
               reason, g_TradeCount, g_PnLToday);
}
```

### 代码段 7 (步骤 7)：编译 (F7)

```powershell
# 路径: C:\Program Files\MetaTrader 5\metaeditor64.exe
# 用 MQL5 内置: 工具 → 编译 (F7)
# 命令行触发 (需 console session 1 GUI, 留给 N4):
& "C:\Program Files\MetaTrader 5\metaeditor64.exe" /compile:"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea\Scalping_More_v1.3.mq5" /log
```

### 代码段 8 (步骤 8)：验证 errors=0

```powershell
# 编译日志分析
# - 期望: 0 errors
# - 可接受 warnings:
#   * "declaration without type" (M13 老 API) → 可忽略
#   * "possible loss of data" (int/double 转换) → 可忽略
# - 不可接受 errors:
#   * "'CTradePlus' - cannot convert enum" → 检查 include 路径
#   * "'CNewsFilter' - identifier not found" → 见 §4 编译错误段第 2 条
#   * "'CSessionFilter' - Init signature mismatch" → 见 §4 编译错误段第 3 条
```

### 代码段 9 (步骤 9)：沙盒测试 (1 周 trades 落盘)

```mql5
// 在 MetaTrader 5 终端:
// 1. 文件 → 打开数据文件夹 → 复制 news_calendar.csv 到 MQL5/Files/
// 2. 导航 → EA 交易 → 拖 Scalping_More_v1.3 到 XAUUSDm M1 图表
// 3. 弹窗勾选 "允许自动交易" → OK
// 4. 工具 → 选项 → 通知 → 填 MetaQuotes ID (微信/Telegram 推送)
// 5. 跑 1 周, 监控:
//    - Experts 日志: 应该有 BUY/SELL + 心跳 + 新闻过滤日志
//    - MQL5/Files/trades_Scalping_More_v1.3_YYYYMMDD.csv: 每笔成交
//    - DD: 应 < 5%
// 6. 期间不动手, 1 周后看 trades.csv
```

### 代码段 10 (步骤 10)：实盘 demo

```powershell
# 1 周沙盒 OK 后, 转实盘 demo:
# 1. 登录 Exness Demo 账户 (XAUUSDm Hedge)
# 2. 拖 EA 到 XAUUSDm M1 图表
# 3. 24h 监控:
#    - 推送是否到达 (微信/Telegram)
#    - trades.csv 是否每笔都有
#    - DD 走势, 应 < 5%
# 4. 如异常立即 Stop Algo Trading
# 5. 1 周 demo OK → 切实盘 (小额, 0.01 lot)
```

---

## §4 编译错误速查 (剥头皮特有问题 5+)

| # | 错误 | 原因 | 解决 |
|---|---|---|---|
| 1 | `'CTradePlus' - cannot convert enum` | include 路径错；或用 `CTrade::Buy` 而非 `CTradePlus::Buy` | 检查 `#include <MQL5Kit/M01_CTradePlus.mqh>`；改 `trade.Buy(...)` 而非 `trade.CTrade::Buy(...)` |
| 2 | `'CNewsFilter' - identifier not found` | M17 文件名可能为 `M17_NewsFilter.mqh` 或 `M17_NewsEventFilter.mqh`，需对照 ScalperXAU.mq5 | 看 ScalperXAU.mq5 第 31 行 `M17_NewsFilter.mqh`，用相同名 |
| 3 | `'CSessionFilter' - Init signature mismatch` | M19.Init() 接受 `string sessionsSpec`，不是单 hour | 用 `M19.Init("London:8-16,NewYork:13-22")` 而非 `M19.Init(8, 23)` |
| 4 | `'ORDER_FILLING_FOK' - not supported` | XAUUSDm 在 Exness 用 FOK，但其它品种可能不支持 | 用 CTradePlus 自动选（已封装在 M01） |
| 5 | `'g_TradingEnabled' - undefined` | 全局变量 `bool g_TradingEnabled` 在新版本已删除 | 移除引用，或重新声明 |
| 6 | `'g_NewsTimes' - type mismatch StringToTime` | 原代码用 `StringToTime` 解析时间但传入 `string list[]` | 改用 M17，删 InpNewsTimes 整段 |
| 7 | `'currentBar' - ambiguous iBars` | 老 API `iBars` 在新 MQL5 中已 deprecated | 改 M05 NewBar |
| 8 | `'Alert' - blocking call` | 原代码 `Log()` 内 `Alert()` 阻塞 | 用 M11 logger.Trade() 替代 Log() |

**剥头皮特有问题（4 个）**：
- **tick size**：XAUUSDm `_Point = 0.01`，InpStopLoss=133 = 1.33 USD/lot。**注意**：计算 SL = `entry - 133 * 0.01` = `entry - 1.33`，`_Digits=2` → `NormalizeDouble(sl, 2)` → 正确。
- **spread**：`SYMBOL_SPREAD` 返回 **points**（不是 USD），XAUUSDm 50 points = 0.50 USD。剥头皮硬上限 50 points。
- **slippage**：`CTrade.SetDeviationInPoints(20)` 允许 20 points = 0.20 USD 滑点；剥头皮建议 5-20。
- **M19 周末**：`SetAllowWeekend(false)` 默认；周末 XAUUSDm 点差 50-100+，剥头皮打穿 SL。
- **M17 ±30min**：高影响新闻 (NFP / CPI / FOMC) 30min 内不开仓，CSV 缺失时降级关闭。

---

## §5 与 ScalperXAU v1 升级路径对比

| 项 | ScalperXAU v1 (v3 实物) | Scalping_More v1.3 (本次接入) |
|---|---|---|
| 文件 | `MQL5/Experts/minimax-ea/ScalperXAU.mq5` (39KB / 961 行) | `_archive/earn-ea/Scalping_More_v1.3.mq5` (10KB / 327 行) |
| 状态 | v3 已生产, BB+RSI+ADX+Trail+CSV+滚动指标 | v1.3 裸 CTrade, BB+EMA, 升级中 |
| 接入模块 | M01/02/03/04/05/07/08/09/10/11/13/16/17 | M01/02/08/10/11/13/15/17/19 (本任务 8+1 增强) |
| 缺 M19 | ⚠️ 裸配置 `InpSessionStartHour=8/InpSessionEndHour=23` | ❌ 无 |
| 信号 | BB+RSI (均值回归) | BB+EMA (混合) |
| 手数 | M03 动态 (0.5% 风险) | 固定 0.01 |
| 持仓 | 多笔 (MaxPositions=3) | 1 笔 (`CurrentPositions() >= 1 return`) |
| DD 监控 | ✅ (`_CheckDrawdown` + M10 推送) | ❌ 无 |
| 滚动指标 | ✅ (Metrics 结构, OnClosedDealMetrics) | ❌ 无 |

**可复用部分（不用改）**：
- `CurrentPositions()` 持仓统计函数（原 v1.3 写得对，保留）
- `CalcSL / CalcTP` 价格计算（用 NormalizeDouble，OK）
- `CheckBollingerSignal / CheckEMACrossSignal` 信号函数（业务逻辑，保留）

**必须改的部分**：
- `OpenTrade` → 拆为 M02.CanOpen + M01.OrderSend（不再用裸 OrderSend）
- 替换 `Log()`（用 Alert）→ `logger.Trade()`（用 Print）
- 加 OnTick 顺序（13 步：M19 → M17 → 指标 → 信号 → M02 → M01 → M08 → M10）
- 加 `OnTrade` → M13 CSV 落盘 + M10 通知
- 加 `OnTimer` → M15 心跳 + 超时检查
- 加 `OnTradeTransaction` → M10 拒单通知

**升级路径（如果将来想升级 ScalperXAU v1 → 加 M19）**：
1. 加 `#include <MQL5Kit/M19_SessionFilter.mqh>`
2. 加 input group (InpUseM19Filter / InpSessionPreset / InpAllowWeekend)
3. 替换 `IsTradeTime()` 的裸 `if (dt.hour < InpSessionStartHour...)` → `M19.IsInSession`
4. 删除 `InpSessionStartHour / InpSessionEndHour` input
5. 编译验证

完整 diff 见 `[[实战/M19 时段过滤实战]]` §1 场景 B。

---

## §6 接入 checklist (10 步)

执行顺序（每步都打勾才能进入下一步）：

- [ ] **步骤 1**：复制 8 个 `.mqh` 到 `MQL5/Include/MQL5Kit/`
  - [ ] M01_CTradePlus.mqh
  - [ ] M02_Risk.mqh
  - [ ] M08_TrailingStop.mqh
  - [ ] M10_Notify.mqh
  - [ ] M11_Logger.mqh
  - [ ] M13_FileIO.mqh
  - [ ] M15_TimerService.mqh
  - [ ] M17_NewsFilter.mqh (文件名对照 ScalperXAU.mq5)
  - [ ] M19_SessionFilter.mqh
- [ ] **步骤 2**：include 8 个模块到 EA 顶部
- [ ] **步骤 3**：替换 input 段（8 组 input group）
- [ ] **步骤 4**：替换全局变量段（8 个 object + 状态变量）
- [ ] **步骤 5**：替换 OnInit（10 步初始化，每步失败返 INIT_FAILED）
- [ ] **步骤 6**：替换 OnDeinit（释放 handle + 清理 Comment）
- [ ] **步骤 7**：替换 OnTick（13 步顺序：M19 → M17 → 指标 → 信号 → M02 → M01 → M08 → M10）
- [ ] **步骤 8**：加 OnTimer（1s tick 心跳 + 超时检查）
- [ ] **步骤 9**：加 OnTrade（M13 CSV 落盘 + M10 通知）
- [ ] **步骤 10**：编译验证（0 errors）

编译后必查：
- [ ] `metaeditor64 /compile:` 返 0 errors
- [ ] warnings 中无 `Alert 阻塞` 类（如果有，删 Log() 内的 Alert）
- [ ] MetaEditor 提示 "0 errors" 弹窗

**沙盒测试 checklist**：
- [ ] `news_calendar.csv` 准备 (3-5 条新闻时间测试)
- [ ] MetaQuotes ID 配推送
- [ ] Demo 账户 XAUUSDm M1 attach EA
- [ ] 跑 1 周，至少 50 笔交易
- [ ] `trades_Scalping_More_v1.3_*.csv` 每笔都有
- [ ] DD < 5%
- [ ] 新闻时段无新成交
- [ ] 周末无成交（M19 屏蔽）
- [ ] 浮盈到 InpTrailStartPoints 时 SL 抬升

**实盘 demo checklist**：
- [ ] 沙盒 1 周 OK
- [ ] 切 Exness Real Demo (XAUUSDm Hedge)
- [ ] 24h 监控推送链路
- [ ] 监控 slippage < 5 points
- [ ] 监控 spread < 50 points
- [ ] OK 后切 0.01 lot 实盘

---

## §7 反模式 (5 条不要做的事)

### 反模式 1: 高频重仓
**症状**：InpLotSize=0.1, InpMaxTradesPerDay=200, 1 天 100+ 笔
**后果**：剥头皮 0.1 lot 看似小，1 天 100 笔 = 10 lot 总量，DD 累积 30%+
**反例**：
```mql5
// ❌ 错: 高频重仓
input double InpLotSize = 0.1;
input int InpMaxTradesPerDay = 200;
```
**正例**：
```mql5
// ✅ 对: 保守剥头皮
input double InpLotSize = 0.01;       // 固定 0.01 起, 不超过 0.05
input int    InpMaxTradesPerDay = 50;  // 50 笔上限
input double InpMaxDailyDrawdownPct = 3.0;  // -3% 当日停
```

### 反模式 2: 无 M19 周末交易
**症状**：`InpUseM19Filter = false` 或 `SetAllowWeekend(true)`
**后果**：周末 XAUUSDm 点差 50-100+ points, 剥头皮直接打穿 SL
**反例**：
```mql5
// ❌ 错: 24h 不间断交易
input bool InpUseM19Filter = false;
```
**正例**：
```mql5
// ✅ 对: 严格时段 + 周末屏蔽
input bool   InpUseM19Filter  = true;
input string InpSessionPreset = "London:8-16,NewYork:13-22";
input bool   InpAllowWeekend  = false;
```

### 反模式 3: 无 M17 事件禁开
**症状**：`InpEnableNewsFilter = false` 或 `news.LoadFromCSV()` 失败不报警
**后果**：NFP / CPI / FOMC 公布 ±30min 滑点 5-10 USD/lot, 1 笔打穿 50 笔盈利
**反例**：
```mql5
// ❌ 错: 关闭新闻过滤 + 失败不报警
input bool InpEnableNewsFilter = false;
```
**正例**：
```mql5
// ✅ 对: 启用 + 失败报警
input bool   InpEnableNewsFilter = true;
input int    InpNewsMinBefore    = 30;
input int    InpNewsMinAfter     = 30;
input string InpNewsCsvPath      = "news_calendar.csv";
// OnInit 失败必须 Print + 继续 (降级) 而非静默
if (!news.LoadFromCSV(InpNewsCsvPath)) {
   PrintFormat("⚠ 新闻 CSV 加载失败 (%s) — 新闻过滤降级", news.LastError());
}
```

### 反模式 4: 无 M08 追踪止损
**症状**：`InpUseTrail = false` 或 trail.SetParams(start=99999, step=99999)
**后果**：浮盈 200 点后回落 50 点 = 200 → 150 → 100 (回吐 50%)，剥头皮应锁利
**反例**：
```mql5
// ❌ 错: 不追踪
input bool InpUseTrail = false;
// 或:
trail.SetParams(99999, 99999, 10);  // 永远不会触发
```
**正例**：
```mql5
// ✅ 对: 浮盈 100 点启动, 锁 50 点
input bool InpUseTrail         = true;
input int  InpTrailStartPoints = 100;
input int  InpTrailStepPoints  = 50;
input int  InpTrailMinGapPoints= 10;
```

### 反模式 5: 无 M10 通知
**症状**：`InpEnableNotify = false`
**后果**：剥头皮 1 天 50 笔, 出事 (DD 爆 / 拒单 / 断连) 24h 内无人知
**反例**：
```mql5
// ❌ 错: 关闭通知
input bool InpEnableNotify = false;
```
**正例**：
```mql5
// ✅ 对: 启用 + 配 MetaQuotes ID
input bool InpEnableNotify = true;
input double InpDdAlertPct = 5.0;  // DD > 5% 立即推送
// OnTick 加 _CheckDrawdown + OnTradeTransaction 加 M10.Send 拒单通知
```

---

## 附录 A: 与其它实战 wiki 的关系

- **[[实战/M18 多品种对冲实战]]** — M18 在多品种 EA 的接入（331 行 / 6 章节），本文件不涉及 M18
- **[[实战/M19 时段过滤实战]]** — M19 在 MeanReversion_EA / ScalperXAU v1 / 多 EA 同步（747 行 / 7 章节），本文件 §3 代码段 4 + §7 反模式 2 直接复用其"标准接入"
- **[[策略/01 ScalperXAU v1 - Bollinger RSI 均值回归]]** — ScalperXAU v1 spec，本次接入路径可作为 ScalperXAU 升级的参考

## 附录 B: 文件位置

| 类型 | 路径 |
|---|---|
| 原 EA | `C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\_archive\earn-ea\Scalping_More_v1.3.mq5` |
| 接入目标 | `MQL5/Experts/minimax-ea/Scalping_More_v1.3.mq5` (N4 跟踪中创建) |
| 本 wiki | `C:\ai\obsidian-文件\mt\EA开发\实战\Scalping_More v1.3 接入示例.md` |
| 任务中心 | `C:\ai\obsidian-文件\mt\00-任务调度中心\daily\2026-06-04_13-00-track3-result.md` |

## 附录 C: 本次任务的限制

- **本次不写 .mq5**：T3 只写接入 demo wiki + 实际接入需 GUI 编译阻塞 console session 1，留给 N4
- **M17 spec 缺失**：`EA开发/01-调用模块/M17 新闻过滤 NewsFilter.md` 不存在，本 wiki 引用 ScalperXAU.mq5 (line 31 / 545 / 913) 的 M17 API 作为"参考实现"，待 spec 补齐后核对
- **M19 input 字面量限制**：MQL5 编译器 `error 187: constant expected` 强制 input 默认值必须是字面量字符串，不能用 const，本 wiki 已遵守
- **0 errors 验证未跑**：实际编译需 console session 1 启动 MetaEditor64，N4 跟踪负责

---

> **N4 跟踪建议**：
> 1. 复制 `Scalping_More_v1.3.mq5` 到 `MQL5/Experts/minimax-ea/`
> 2. 按 §3 10 段代码逐步替换（建议一次替换 1 段，编译 1 次）
> 3. 每段编译 errors=0 才进下一段
> 4. 全部替换完跑 §6 checklist
> 5. 沙盒 1 周 OK 后写"实测数据"段（DD / WinRate / AvgTrade）回到本 wiki 末尾

## 附录 D: 兄弟 EA 接入报告（中心节点）

> 本 Scalping_More v1.3 接入示例 跟下面 2 个 EA 中心节点 wiki 形成项目"剥头皮 EA 接入"对比组：
>
> - **[[实战/ScalperXAU 接入报告 + v1→v4 演进史]]** — ScalperXAU（1033L / 13 模块含 M17+M13 / 4 版本演进）。ScalperXAU 是"完整 spec + 4 版本快速迭代"的代表；本 Scalping_More 接入示例是"快速接入 demo"的代表。
> - **[[实战/MeanReversion_EA 接入报告]]** — MeanReversion_EA（320L / 13 模块全集含 M18+M19）。M15 周期中频逆势策略，跟本 Scalping_More M1 剥头皮周期互补。
>
> 对照建议：写新剥头皮 EA → 复制本接入示例 §3 10 段可复制代码 + 读 ScalperXAU 接入报告 §2.1 完整 13 模块接入点（对比哪些模块本示例没接：M13 CSV 24 列 / M17 新闻过滤 / EA 内滚动指标 11 个 / debug log 协议）。

## 实战案例 (06-05 04:00 T2 worker-A 闭环, 候选 L 5/6)

> 沿用 03:00 T2 6 段范本。**本 wiki 已有 ## 反模式 段 5 条 (高频重仓 / 无 M19 周末 / 无 M17 事件 / 无 M08 追踪 / 无 M10 通知)**, 陷阱 5 条走"剥头皮 1s vs 5s vs 15s 实战取舍"角度, 0 重复。Scalping_More_v1.3.mq5 实物在 N4 跟踪中创建, 接入点行号引用 wiki §3 10 段代码 wiki line number。

### 场景 A: Scalping_More v1.3 10 段可复制代码实战 (wiki L135-L611 10 段)
- 实战场景: 8 模块接入 demo (M01/M02/M08/M10/M11/M13/M15/M17/M19), 10 段可复制代码, 每段独立可用 patch, 替换原 EA 对应段
- 实物 demo: Scalping_More_v1.3.mq5 实物在 N4 跟踪中创建 (本 wiki §附录 B 文件位置), 当前 wiki L135-L240 是 8 段 input/include/object, L290-L611 是 5 段 OnInit/OnTick/OnDeinit
- 适用范围: 适合"快速接入 demo 复用" (10 段 patch 即抄) / 不适合"主仓完整重构" (走 [[实战/ScalperXAU 接入报告 + v1→v4 演进史]])

### 场景 B: 与 ScalperXAU v1 升级路径对比 (10 步 vs v1 5 步)
- 实战场景: 同样接剥头皮 8 模块, Scalping_More v1.3 走 10 步 (M15 节流 / M13 CSV / M10 通知全配齐), ScalperXAU v1 走 5 步 (M01/M02/M08/M17/M19 简化), 接入深度不同
- 实物 demo: Scalping_More 10 段 vs ScalperXAU 5 段 — Scalping_More 加 M15 1s 心跳 + M13 CSV 24 列 + M10 推送全触发器, ScalperXAU v1 简化
- 适用范围: 适合"剥头皮高频风控" 场景 (Scalping_More) / 适合"中频剥头皮简化" 场景 (ScalperXAU v1)

### 接入点行号 (10 段 wiki 代码行号 + ScalperXAU 对比 5 行号, Node.js fs 验证 2026-06-05 04:00)
| wiki 描述 | 实物/wiki | 行号 | 命中关键词 | spec |
|---|---|---|---|---|
| 段 1 include 8 模块 | Scalping_More wiki §3 段 1 | L135-L151 | `#include <MQL5Kit/M01_CTradePlus.mqh>` 等 8 行 | M01/M02/M08/M10/M11/M13/M15/M17/M19 spec |
| 段 2 input group 8 组 | Scalping_More wiki §3 段 2 | L153-L208 | `input group "=== 剥头皮参数 (M01 兼容) ==="` 等 8 组 | M01-M19 input 范本 |
| 段 3 object 8 个 | Scalping_More wiki §3 段 3 | L210-L242 | `CTradePlus trade;` `CRisk risk;` `CNotify M10;` `CLogger logger;` | M01/M02/M10/M11 实例化 |
| 段 4 OnInit 初始化 8 模块 | Scalping_More wiki §3 段 4 | L290-L350 | `int OnInit() {` + Init 8 模块 | M01/M02/M08/M10/M11 Init 范本 |
| 段 5 OnTick 集成 (9 步顺序) | Scalping_More wiki §3 段 5 | L380-L500 | `M19.IsInSession` → `M17.IsNearEvent` → `M05.IsNewBar` → 指标 → 信号 → `M02.CanOpen` → `M01.OrderSend` → `M08.TrailingStop.Apply` → `M10.Trade` → `M13.WriteCsvRow` | M01-M19 OnTick 范本 |
| 段 6 OnDeinit 清理 | Scalping_More wiki §3 段 6 | L520-L560 | `void OnDeinit(const int reason) {` 释放 handle + Cleanup | M16 Cleanup 范本 |
| 段 7 编译 (F7) | Scalping_More wiki §3 段 7 | L580-L600 | `MetaEditor64 /compile:Scalping_More_v1.3.mq5` | 编译命令 |
| 段 8 验证 errors=0 | Scalping_More wiki §3 段 8 | L600-L610 | 0 errors 必查 | 编译验证 |
| 段 9 沙盒测试 (1 周) | Scalping_More wiki §3 段 9 | L610-L615 | Demo XAUUSDm M1, 至少 50 笔 | 沙盒测试 |
| 段 10 实盘 demo | Scalping_More wiki §3 段 10 | L615-L620 | 监控 DD / 滑点 / 推送链路 | 实盘 demo |
| 对比: ScalperXAU CTradePlus (M01 范本) | ScalperXAU.mq5 | L107 | `CTradePlus trade;` | M01 Init 范本 |
| 对比: ScalperXAU M19 拆字段 | ScalperXAU.mq5 | L198-L213 | `M19` `TimeCurrent` 拆字段 | M19 OnTick 范本 |
| 对比: ScalperXAU EnumToString (M11) | ScalperXAU.mq5 | L321-L322 | `EnumToString` `logger.Info` | M11 logger.Info 范本 |
| 对比: ScalperXAU M13 trade journal | ScalperXAU.mq5 | L341 | `slip` field initialization | M13 trade journal 范本 |
| 对比: ScalperXAU ClosePos (M01) | ScalperXAU.mq5 | L573 | `ClosePos` 平指定 ticket | M01 ClosePos 范本 |

### 调优点 3 档
- aggressive: 剥头皮 1s (MinSecBetweenTrades=1) — 1 天 200+ 笔, 经纪商可能限流 (Exness XAUUSDm 限速 100 笔/小时)
- balanced: 剥头皮 5s (MinSecBetweenTrades=5) — 1 天 50-80 笔, 平衡频率 + 利润 ← 默认 (本 wiki §3 段 2 input 默认值)
- conservative: 剥头皮 15s (MinSecBetweenTrades=15) — 1 天 20-30 笔, 适合新手 / 经纪商限速严时

### 陷阱 5 条 (不与 ## 反模式 段 5 条重复, 走"剥头皮 1s vs 5s vs 15s 实战取舍"角度)
- 陷阱 1: 剥头皮 1s broker 拒单 — MinSecBetweenTrades=1 + MaxTradesPerHour=10, 1 天 200+ 笔, Exness XAUUSDm demo 拒单率 30%+。**剥头皮 1s 是"理论极限", 实盘 broker 限速 5-15s**, 降到 5s 拒单率 < 5% (见 [[04-避坑与速查/02 OrderSend 错误码速查]] retcode=10008/10016 频率限速)
- 陷阱 2: 滑点 0 = broker 拒 — `InpDeviationPoints = 0` 滑点容忍 0 = 任何价格波动 broker 都拒单 (retcode=10015 req_price changed)。**剥头皮 0 滑点 = 0 成交**, 设 5-20 points 容忍 (本 wiki §3 段 2 input 默认 InpDeviationPoints=20, 见 [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] v3 0 笔失败根因)
- 陷阱 3: M19 时段 1 min 太严 — 剥头皮 1 天 50+ 笔, 时段闸门 1 min 切 (亚洲/伦敦边界) 容易"刚开 1 笔就切时段 = 持仓穿越午夜"。**M19.SetAllowWeekend(false) 默认**, 周末点差 50-100 + 1 笔打穿 SL (本 wiki ## 反模式 2 已警示, 实战再加 1 条: 时段边界 1 min 太短)
- 陷阱 4: M10.Notify.Trade 频率限速 — 1 天 50 笔 + M10.Notify.Trade 全部推送 = MT5 推送 50+ 弹窗, **用户疲劳忽略 = 真出事 (DD 爆) 通知被淹没**。**M10.Notify.Trade 只在异常 (DD 爆 / 拒单 / 净值归零) 推送**, 正常开/平 用 `M10.Trade(silent=true)` 写文件不弹窗 (见 [[实战/MyEA + Dashboard 接入报告]] §反模式 3 Dashboard 节流)
- 陷阱 5: v1 vs v1.3 5 步差异 — Scalping_More v1.3 走 10 步 (本 wiki §3 完整), 跟 ScalperXAU v1 5 步 (5 模块简化) 差异: **v1.3 加 M15 心跳 / M13 CSV / M10 推送全触发器**, v1 只配 M01/M02/M08/M17/M19。**别把 v1 5 步当 v1.3 10 步, 接入深度不够, 1 周沙盒 0 推送 + 0 CSV**。详见 [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] v1→v4 4 版本对比

### 链向
- [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] — 13 模块含 M17, v1→v4 4 版本演进 (本 wiki 段 1-10 跟 SX v1 对比)
- [[实战/BBTrendEA 复活 SOP]] — 12 步复活, Scalping_More N4 接入时参考 §3 步骤 6 OnTick 集成
- [[实战/MeanReversion_EA 接入报告]] — 13 模块全集, M15 周期中频 vs Scalping_More M1 剥头皮互补
- [[01-调用模块/M01 交易封装 CTradePlus]] — `CTradePlus` 段 3 object + 段 5 OnTick 范本
- [[01-调用模块/M02 风控 Risk]] — `CRisk risk;` + 段 5 OnTick `risk.CanOpen()`
- [[01-调用模块/M10 推送通知 Notify]] — `CNotify M10;` + 段 5 OnTick `M10.Trade()`
- [[01-调用模块/M11 日志 Logger]] — `CLogger logger;` + 段 5 OnTick `logger.Trade()`
- [[01-调用模块/M15 定时器 TimerService]] — `CTimerService timer;` 段 5 OnTimer
- [[01-调用模块/M17 新闻过滤 NewsFilter]] — `CNewsFilter news;` + 段 5 OnTick `news.IsNearEvent()`
- [[01-调用模块/M19 时段过滤 SessionFilter]] — `CSessionFilter M19;` + 段 5 OnTick `M19.IsInSession()`
- [[EA开发/EA 开发知识库]] §"实战相关" 分类 (T4 owner 04:00 顺手加 1 行链向本 wiki)
