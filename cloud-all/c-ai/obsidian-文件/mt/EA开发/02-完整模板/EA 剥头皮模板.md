---
title: EA 剥头皮模板
tags: [EA, 模板, 剥头皮, 高频]
type: template
---

# EA 剥头皮模板

> 思路：抓 5-15 点的快速反弹/回调，要求**极低点差**、**极快执行**。
> ⚠️ 多数经纪商禁止剥头皮或限制。ECN/STP 账户跑。

## 实战 EA 引用

> **本模板的实物参考**：`ScalperXAU.mq5`（`MQL5/Experts/minimax-ea/`，41.7 KB / 1033 行，**13 模块含 M17**）。
> - 实物源：`MQL5/Experts/minimax-ea/ScalperXAU.mq5` (Node.js fs 实读 2026-06-04)
> - 接入点：`#include <MQL5Kit/...>` L19-L31（M01/M02/M03/M04/M05/M07/M08/M09/M10/M11/M13/M16/M17）/ object L107-L117（**11 个对象**：`CTradePlus/CRisk/CPositionSizing/CIndicatorPool/CNewBar/CPositions/CTrailingStop/CDashboard/CLogger/CNotify/CNewsFilter`）
> - 裸 indicator handle：`g_hBands/g_hRsi/g_hAtr/g_hAdx` L135-L138 + `GetBands/GetRsi/GetAtr/GetAdxMain` L492-L515
> - 信号链：OnTick L789 → `CheckEntrySignal` L520（L520-540）→ `PassFilters` L545 + `news.IsNearEvent(InpNewsMinBefore, InpNewsMinAfter, _Symbol)` L549 → `TryOpen` L745
> - 4 版本演进：v1 (89KB) → v2 (104KB, +MFE/MAE/ExitReason CSV) → v3 (111KB, +M08+ADX+频率) → v4 (113KB, +debug log + 放宽 filter)
> - v3 失败案例：6-01~6-03 跑 2 天 0 笔（filter 过严）→ v4 放宽 9 个维度加 debug log 协议
> - 链向：`[[实战/ScalperXAU 接入报告 + v1→v4 演进史]]` / `[[实战/Scalping_More v1.3 接入示例]]`（archive 接入 demo）/ `[[策略/00 ScalperXAU 迭代纪要 v1→v2→v3]]`

```mql5
//+------------------------------------------------------------------+
//|                                    Scalper_EA.mq5                |
//|                              剥头皮 EA                            |
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
#include <MQL5Kit/M09_Dashboard.mqh>
#include <MQL5Kit/M11_Logger.mqh>
#include <MQL5Kit/M16_Cleanup.mqh>

//--- 输入
input ulong  Magic = 20260501;

input group "=== 信号 ==="
input int    BB_Period = 20;
input double BB_Dev = 2.0;
input int    RSI_Period = 7;
input int    RSI_OB = 80;
input int    RSI_OS = 20;

input group "=== 剥头皮参数 ==="
input int    TP_Points = 8;             // 极小止盈
input int    SL_Points = 15;            // 极小止损
input int    MaxSpread = 25;            // 最大允许点差（点）
input double RiskPct = 0.005;           // 极低风险

input group "=== 频率控制 ==="
input int    MinSecondsBetweenTrades = 30;
input int    MaxTradesPerHour = 10;

input group "=== 时间 ==="
input int    StartHour = 8;
input int    EndHour = 20;

CTradePlus      trade;
CRisk           risk;
CPositionSizing sizing;
CIndicatorPool  ind;
CNewBar         NB;
CDashboard      dash;
CLogger         log;

datetime _lastTradeTime = 0;
int      _tradesThisHour = 0;
int      _lastHour = -1;

int OnInit() {
   trade.Init(Magic, 5);   // 剥头皮 5 点滑点
   risk.Init(Magic, 5, RiskPct);
   sizing.Init(RiskPct);
   NB.Init(_Period);
   ind.AddRSI("RSI", RSI_Period);
   ind.AddBands("BB", BB_Period, BB_Dev);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   if (reason == REASON_PROGRAM || reason == REASON_REMOVE)
      CCleanup::CleanupAll(Magic, "SC_", "SC_", true, true, true);
   log.Close();
   Comment("");
}

void OnTick() {
   // 1) 点差检查
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if (spread > MaxSpread) return;

   // 2) 时间窗口
   MqlDateTime dt;
   TimeCurrent(dt);
   if (dt.hour < StartHour || dt.hour >= EndHour) return;

   // 3) 频率控制
   if (TimeCurrent() - _lastTradeTime < MinSecondsBetweenTrades) return;
   if (dt.hour != _lastHour) {
      _lastHour = dt.hour;
      _tradesThisHour = 0;
   }
   if (_tradesThisHour >= MaxTradesPerHour) return;

   // 4) K 线控制
   if (!NB.IsNewBar()) return;

   // 5) 信号
   double rsi = ind.Value("RSI", 0);
   double bbUpper = ind.MACDValue("BB", 1, 0);
   double bbLower = ind.MACDValue("BB", 2, 0);
   double bbMid   = ind.MACDValue("BB", 0, 0);
   if (rsi == EMPTY_VALUE || bbMid == EMPTY_VALUE) return;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   if (rsi < RSI_OS && ask <= bbLower
    && !CPositions::HasDirection(Magic, POSITION_TYPE_BUY)) {
      TryOpen(ORDER_TYPE_BUY, ask);
   }
   if (rsi > RSI_OB && bid >= bbUpper
    && !CPositions::HasDirection(Magic, POSITION_TYPE_SELL)) {
      TryOpen(ORDER_TYPE_SELL, bid);
   }
}

void TryOpen(ENUM_ORDER_TYPE type, double price) {
   double sl = (type == ORDER_TYPE_BUY) ? price - SL_Points * _Point
                                        : price + SL_Points * _Point;
   double tp = (type == ORDER_TYPE_BUY) ? price + TP_Points * _Point
                                        : price - TP_Points * _Point;
   double lot = sizing.LotByRisk(RiskPct, MathAbs(price - sl));
   if (lot <= 0) return;
   if (!risk.CanOpen(type, lot, sl, tp)) return;

   if (type == ORDER_TYPE_BUY) {
      if (trade.Buy(lot, sl, tp, "SC_Long")) {
         _lastTradeTime = TimeCurrent();
         _tradesThisHour++;
         log.Trade("BUY", _Symbol, lot, price, 0, "scalp");
      }
   } else {
      if (trade.Sell(lot, sl, tp, "SC_Short")) {
         _lastTradeTime = TimeCurrent();
         _tradesThisHour++;
         log.Trade("SELL", _Symbol, lot, price, 0, "scalp");
      }
   }
}
//+------------------------------------------------------------------+
```

## 关键参数

### 选品种
- 必须**点差极低**：ECN/STP 账户
- 推荐：EURUSD、GBPUSD、XAUUSD（部分经纪商点差低）
- 避免：股票、指数（点差大）

### TP/SL
- 经典：TP=8 点，SL=15 点
- 激进：TP=5 点，SL=8 点
- 保守：TP=12 点，SL=20 点

### 频率控制
- `MinSecondsBetweenTrades`：避免过度交易
- `MaxTradesPerHour`：经纪商和服务器都有限制
- 大多数经纪商允许 < 100 笔/天

## 致命陷阱
- ❌ **剥头皮被禁**：IC Markets 部分账户、Vantage 某些类型明文禁止
- ❌ **点差跳变**：凌晨/重大新闻时点差扩大，剥头皮会变"跳头皮"亏损
- ❌ **滑点**：订单发出去到成交之间的价格变动
- ❌ **限制订单数**：某些经纪商每分钟最多 20 笔
- ✅ **始终检查经纪商条款**

## 跑剥头皮必备
- ECN/STP 账户
- VPS（低延迟，离服务器近）
- 5ms 以内的网络
- 避免重大新闻时段
