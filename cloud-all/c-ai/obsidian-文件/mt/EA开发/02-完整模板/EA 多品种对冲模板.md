---
title: EA 多品种对冲模板
tags: [EA, 模板, 多品种, 对冲]
type: template
---

# EA 多品种对冲模板

> 思路：监控多个品种，每个品种独立跑相同策略；或做相关性对冲（多 EURUSD + 空 GBPUSD）。
> **解决单 EA 只能绑一个图表的问题**。

## 实战 EA 引用

> **本模板的实物参考**：2 个 EA——主推荐 `MeanReversion_EA.mq5`（多品种均值回归），备选 `ScalperEA.mq5`（73 KB 多品种剥头皮重构）。
> - `MeanReversion_EA.mq5` (`MQL5/Experts/minimax-ea/`, 12.7 KB / 320 行, **13 模块全集含 M18+M19**) — `#include` L9-L21 / object L54-L64（**11 个对象**：M16 Cleanup + M07 Positions 走 static 调不占 object 槽）/ OnInit L79：`ind.AddRSI/AddBands/AddADX/AddATR` L84-L87 + `M19.Init(InpSessionPreset)` L93 + `M19.SetAllowWeekend(InpAllowWeekend)` L97 / `M18.SetDefaultDays(30)` L109 + `M18.Init(syms)` L110 + `M18.LoadHistoricalCloses(syms[i], 30)` L113（4 品种历史 close 加载）
>   - 4 品种 (XAUUSDm 主图 + EURUSDm + GBPUSDm + USDJPYm 跨品种监控)
>   - OnTick L140：`M19.IsInSession(TimeCurrent())` L161（London+NY 8-22 UTC, 周末 BLOCK）+ `M18.IsHedgeExposed(_Symbol, Magic, InpCorrThreshold)` L167（threshold=0.7）
>   - 链向：`[[实战/MeanReversion_EA 接入报告]]`（320L / 13 模块 / M10 三类触发器范本）
> - `ScalperEA.mq5` (`MQL5/Experts/_archive/me-ea/`, **73.0 KB / 1759 行**, 多周期布林带+网格加仓+移动止损) — Node.js fs 实读：**0 MQL5Kit `#include`** / OnInit L207 / OnTick L253 / OnTimer L381 / CheckEntry L856
>   - ⚠️ 73 KB 实物较重，**未做 N4 复活**——待 `[[实战/ScalperEA 复活 (N4, 阻塞 console 1)]]` 启动时按 BBTrendEA SOP 12 步模板做接入
> - 链向：`[[实战/MeanReversion_EA 接入报告]]` / `[[实战/ScalperEA 复活 (N4, 阻塞 console 1)]]` / `[[实战/M18 多品种对冲实战]]`（M18 spec 实战段）/ `[[实战/M19 时段过滤实战]]`（M19 spec 实战段）

```mql5
//+------------------------------------------------------------------+
//|                                    MultiSymbol_EA.mq5            |
//|                              多品种 / 对冲 EA                      |
//+------------------------------------------------------------------+
#property copyright "MyEA"
#property version   "1.00"
#property strict

#include <MQL5Kit/M01_CTradePlus.mqh>
#include <MQL5Kit/M02_Risk.mqh>
#include <MQL5Kit/M03_PositionSizing.mqh>
#include <MQL5Kit/M04_IndicatorPool.mqh>
#include <MQL5Kit/M05_NewBar.mqh>
#include <MQL5Kit/M07_Positions.mqh>
#include <MQL5Kit/M11_Logger.mqh>
#include <MQL5Kit/M16_Cleanup.mqh>

//--- 多品种配置
input group "=== 监控品种 ==="
input string SymbolsToTrade = "EURUSD,GBPUSD,XAUUSD";   // 逗号分隔
input ulong  Magic = 20260601;

input group "=== 策略 ==="
input int    FastMA = 12;
input int    SlowMA = 26;
input int    SL_Points = 200;
input int    TP_Points = 400;
input double RiskPct = 0.01;
input int    MaxTotalPos = 5;        // 所有品种合计最大持仓

CTradePlus      trade;
CRisk           risk;
CPositionSizing sizing;
CNewBar         NB;
CLogger         log;

string _symbols[];
int   _nSymbols;

//+------------------------------------------------------------------+
int OnInit() {
   trade.Init(Magic, 30);
   risk.Init(Magic, 1, RiskPct);
   sizing.Init(RiskPct);
   NB.Init(_Period);

   // 解析品种列表
   _ParseSymbols();

   // 把所有品种加入 Market Watch
   for (int i = 0; i < _nSymbols; i++) {
      SymbolSelect(_symbols[i], true);
   }

   // 用 OnTimer 100ms 轮询
   EventSetMillisecondTimer(200);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   if (reason == REASON_PROGRAM || reason == REASON_REMOVE) {
      // 注意：删所有品种的本 EA 挂单
      for (int i = 0; i < _nSymbols; i++) {
         _CleanupSymbol(_symbols[i]);
      }
   }
   log.Close();
   Comment("");
}

//+------------------------------------------------------------------+
void OnTimer() {
   // 对每个品种：判断新 K 线 + 入场
   for (int i = 0; i < _nSymbols; i++) {
      string sym = _symbols[i];
      if (!SymbolExist(sym)) continue;
      _CheckSymbol(sym);
   }
}

//+------------------------------------------------------------------+
void _CheckSymbol(string sym) {
   // 总持仓数限制
   if (CPositions::Count(Magic) >= MaxTotalPos) return;

   // 这个品种是否已有持仓？
   if (CPositions::CountMine(Magic, sym) > 0) return;

   // 取这个品种最近两根 MA
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if (CopyRates(sym, _Period, 0, 3, rates) < 3) return;

   int hFast = iMA(sym, _Period, FastMA, 0, MODE_EMA, PRICE_CLOSE);
   int hSlow = iMA(sym, _Period, SlowMA, 0, MODE_EMA, PRICE_CLOSE);
   if (hFast == INVALID_HANDLE || hSlow == INVALID_HANDLE) return;

   double f[2], s[2];
   ArraySetAsSeries(f, true);
   ArraySetAsSeries(s, true);
   if (CopyBuffer(hFast, 0, 0, 2, f) < 2) { IndicatorRelease(hFast); IndicatorRelease(hSlow); return; }
   if (CopyBuffer(hSlow, 0, 0, 2, s) < 2) { IndicatorRelease(hFast); IndicatorRelease(hSlow); return; }

   // 交叉
   bool crossUp   = f[1] <= s[1] && f[0] > s[0];
   bool crossDown = f[1] >= s[1] && f[0] < s[0];

   if (crossUp) {
      // 在这个品种上下多单
      _OpenOnSymbol(sym, ORDER_TYPE_BUY);
   } else if (crossDown) {
      _OpenOnSymbol(sym, ORDER_TYPE_SELL);
   }

   IndicatorRelease(hFast);
   IndicatorRelease(hSlow);
}

//+------------------------------------------------------------------+
void _OpenOnSymbol(string sym, ENUM_ORDER_TYPE type) {
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   if (ask == 0 || bid == 0) return;

   double price = (type == ORDER_TYPE_BUY) ? ask : bid;
   double sl = (type == ORDER_TYPE_BUY) ? price - SL_Points * _Point
                                        : price + SL_Points * _Point;
   double tp = (type == ORDER_TYPE_BUY) ? price + TP_Points * _Point
                                        : price - TP_Points * _Point;

   // 用该品种的 tick value 算手数
   double tickSize  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double slDist = MathAbs(price - sl);
   if (tickSize == 0 || slDist == 0) return;

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * RiskPct;
   double lot = riskMoney * tickSize / (slDist * tickValue);

   // 规范化
   double minL = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double maxL = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   double stepL = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   if (stepL > 0) lot = MathFloor(lot / stepL) * stepL;
   lot = MathMax(minL, MathMin(maxL, lot));
   if (lot <= 0) return;

   // 简化风控：直接下单
   // （生产环境应：先检查该品种的最小止损距离/保证金等）

   if (type == ORDER_TYPE_BUY) {
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action = TRADE_ACTION_DEAL;
      req.symbol = sym;
      req.volume = lot;
      req.type   = ORDER_TYPE_BUY;
      req.price  = ask;
      req.sl     = sl;
      req.tp     = tp;
      req.deviation = 30;
      req.magic  = Magic;
      req.type_filling = _GetFilling(sym);
      if (OrderSend(req, res) && res.retcode == TRADE_RETCODE_DONE)
         log.Trade("BUY", sym, lot, ask, 0, "MultiSymbol金叉");
   } else {
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action = TRADE_ACTION_DEAL;
      req.symbol = sym;
      req.volume = lot;
      req.type   = ORDER_TYPE_SELL;
      req.price  = bid;
      req.sl     = sl;
      req.tp     = tp;
      req.deviation = 30;
      req.magic  = Magic;
      req.type_filling = _GetFilling(sym);
      if (OrderSend(req, res) && res.retcode == TRADE_RETCODE_DONE)
         log.Trade("SELL", sym, lot, bid, 0, "MultiSymbol死叉");
   }
}

ENUM_ORDER_TYPE_FILLING _GetFilling(string sym) {
   long f = SymbolInfoInteger(sym, SYMBOL_FILLING_MODE);
   if (f & SYMBOL_FILLING_FOK) return ORDER_FILLING_FOK;
   if (f & SYMBOL_FILLING_IOC) return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
}

bool SymbolExist(string sym) {
   bool custom = false;
   return SymbolExist(sym, custom);
}

void _ParseSymbols() {
   string parts[];
   int n = StringSplit(SymbolsToTrade, ',', parts);
   ArrayResize(_symbols, n);
   for (int i = 0; i < n; i++) {
      StringTrimLeft(parts[i]);
      StringTrimRight(parts[i]);
      _symbols[i] = parts[i];
   }
   _nSymbols = n;
}

void _CleanupSymbol(string sym) {
   for (int i = OrdersTotal() - 1; i >= 0; i--) {
      ulong t = OrderGetTicket(i);
      if (t == 0) continue;
      if (OrderGetInteger(ORDER_MAGIC) != Magic) continue;
      if (OrderGetString(ORDER_SYMBOL) != sym) continue;
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action = TRADE_ACTION_REMOVE;
      req.order   = t;
      OrderSend(req, res);
   }
}
//+------------------------------------------------------------------+
```

## 关键设计

### 用 OnTimer 轮询，不要用 OnTick
- 绑一个图表（AUDUSD），但能处理其他品种
- `EventSetMillisecondTimer(200)` 5Hz 轮询
- `EventSetTimer(1)` 1Hz 也可以

### 品种筛选
- 加流动性的品种（EURUSD, GBPUSD, XAUUSD, USDJPY）
- 避开点差极大或交易时段太短的品种

### 手数计算
- 每个品种的 tick value 不同 → 单独算
- 共享一个 `RiskPct` 账户级风控

### 防止相互干扰
- 一个品种用了 magic=1234，另一个 EA 用 magic=5678 → 互不干扰
- `CPositions::Count(Magic)` 只统计本 EA

## 对冲策略示例

```mql5
// 多 EURUSD + 空 GBPUSD（正相关性，多空对冲）
input string LongSymbol  = "EURUSD";
input string ShortSymbol = "GBPUSD";

void OnTimer() {
   if (CrossUp(LongSymbol))   OpenSymbol(LongSymbol,  BUY);
   if (CrossDown(LongSymbol)) OpenSymbol(LongSymbol,  SELL);
   if (CrossUp(ShortSymbol))  OpenSymbol(ShortSymbol, SELL);
   if (CrossDown(ShortSymbol)) OpenSymbol(ShortSymbol, BUY);
}
```

## 必看陷阱
- **手数计算跨品种必须独立**（黄金和外汇的合约单位不同）
- `AccountInfoDouble(ACCOUNT_MARGIN_FREE)` 是**整个账户的**，多品种会争抢
- **行情推送 ≠ OnTick**：当前图表不一定是 EURUSD，但其他品种也会更新
- 用 `SymbolInfoTick` 主动拉报价更稳
- VPS 上的 VPS 处理器可能忙不过来 5 个品种 × 1Hz 轮询
