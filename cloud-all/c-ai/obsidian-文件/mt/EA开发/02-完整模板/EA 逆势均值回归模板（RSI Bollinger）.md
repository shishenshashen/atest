---
title: EA 逆势均值回归模板（RSI Bollinger）
tags: [EA, 模板, 逆势, 均值回归]
type: template
---

# EA 逆势均值回归模板（RSI / Bollinger）

> 思路：价格远离均值（RSI 超买超卖 / 触及布林带）→ 反向入场博回归。
> **适合震荡市**，单边行情慎用。

## 实战 EA 引用

> **本模板的实物参考**：2 个 EA 同源——XAUUSDm 单品种剥头皮（`ScalperXAU`）+ 多品种均值回归（`MeanReversion_EA`）。
> - `ScalperXAU.mq5` (`MQL5/Experts/minimax-ea/`, 41.7 KB / 1033 行, **13 模块含 M17**) — `#include` L19-L31 / object L107-L117（11 个对象：`CTradePlus/CRisk/CPositionSizing/CIndicatorPool/CNewBar/CPositions/CTrailingStop/CDashboard/CLogger/CNotify/CNewsFilter`）/ 裸 indicator handle `g_hBands/g_hRsi/g_hAtr/g_hAdx` L135-L138 + `GetBands/GetRsi/GetAtr/GetAdxMain` L492-L515 / `CheckEntrySignal` L520 / `PassFilters` L545 + `news.IsNearEvent(30,30,_Symbol)` L549
>   - 4 版本演进 v1→v4: v1 (89KB) → v2 (+MFE/MAE/ExitReason CSV) → v3 (+M08+ADX+频率) → v4 (+debug log + 放宽 filter) / v3 0 笔失败 → v4 放宽 9 维度
> - `MeanReversion_EA.mq5` (`MQL5/Experts/minimax-ea/`, 12.7 KB / 320 行, **13 模块全集含 M18+M19**) — `#include` L9-L21 / object L54-L64（**11 个对象**：`CTradePlus/CRisk/CPositionSizing/CIndicatorPool/CNewBar/CTrailingStop/CDashboard/CLogger/CNotify/CCorrelationFilter/CSessionFilter` — M16 Cleanup + M07 Positions 走 static 调不占 object 槽）/ OnInit L79：`ind.AddRSI/AddBands/AddADX/AddATR` L84-L87 + `M19.Init` L93 + `M18.SetDefaultDays(30)` L109 + `M18.Init` L110 + `M18.LoadHistoricalCloses` L113
>   - 4 品种相关性监控 + M19 London+NY 时段 + M18 0.7 阈值
> - 链向：`[[实战/ScalperXAU 接入报告 + v1→v4 演进史]]` / `[[实战/MeanReversion_EA 接入报告]]` / `[[实战/Scalping_More v1.3 接入示例]]`

```mql5
//+------------------------------------------------------------------+
//|                                  MeanReversion_EA.mq5             |
//|                              逆势均值回归 EA                       |
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
#include <MQL5Kit/M08_TrailingStop.mqh>
#include <MQL5Kit/M09_Dashboard.mqh>
#include <MQL5Kit/M11_Logger.mqh>
#include <MQL5Kit/M16_Cleanup.mqh>

//--- 输入
input group "=== 基础 ==="
input ulong  Magic = 20260201;

input group "=== 指标 ==="
input int    RSI_Period     = 14;
input int    RSI_Overbought = 70;       // RSI 超买线
input int    RSI_Oversold   = 30;       // RSI 超卖线
input int    BB_Period      = 20;       // 布林带周期
input double BB_Deviation   = 2.0;      // 标准差倍数

input group "=== 仓位 ==="
input double RiskPct   = 0.01;
input int    MaxPos    = 3;
input int    SL_Points = 200;
input int    TP_Points = 150;

input group "=== 过滤 ==="
input bool   UseADXFilter = true;
input int    ADX_Max      = 25;         // ADX > 25 = 强趋势，不开

//--- 全局
CTradePlus      trade;
CRisk           risk;
CPositionSizing sizing;
CIndicatorPool  ind;
CNewBar         NB;
CTrailingStop   trail;
CDashboard      dash;
CLogger         log;

//+------------------------------------------------------------------+
int OnInit() {
   trade.Init(Magic, 30);
   risk.Init(Magic, MaxPos, RiskPct);
   sizing.Init(RiskPct);
   NB.Init(_Period);

   ind.AddRSI("RSI", RSI_Period);
   ind.AddBands("BB", BB_Period, BB_Deviation);
   ind.AddADX("ADX", 14);

   trail.Init(&trade, Magic);
   trail.SetParams(100, 50, 10);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   if (reason == REASON_PROGRAM || reason == REASON_REMOVE)
      CCleanup::CleanupAll(Magic, "MR_", "MR_", true, true, true);
   log.Close();
   Comment("");
}

//+------------------------------------------------------------------+
void OnTick() {
   if (!NB.IsNewBar()) {
      trail.Apply();
      if (dash.SetTitle != NULL) RefreshDash();  // 简化
      return;
   }

   double rsi = ind.Value("RSI", 0);
   double bbUpper = ind.Get("BB") != INVALID_HANDLE
                  ? ind.MACDValue("BB", 1, 0)   // buffer 1 = upper
                  : 0;
   double bbLower = ind.MACDValue("BB", 2, 0);  // buffer 2 = lower
   double bbMid   = ind.MACDValue("BB", 0, 0);  // buffer 0 = middle

   if (rsi == EMPTY_VALUE || bbMid == EMPTY_VALUE) return;

   // ADX 过滤：强趋势不开
   if (UseADXFilter) {
      double adx = ind.Value("ADX", 0);
      if (adx > ADX_Max) return;
   }

   CheckEntry(rsi, bbUpper, bbLower);
   RefreshDash();
}

//+------------------------------------------------------------------+
void CheckEntry(double rsi, double bbUpper, double bbLower) {
   if (CPositions::CountMine(Magic) >= MaxPos) return;

   double price = (SymbolInfoDouble(_Symbol, SYMBOL_BID)
                 + SymbolInfoDouble(_Symbol, SYMBOL_ASK)) / 2.0;

   // 超卖 → 做多
   if (rsi < RSI_Oversold || price < bbLower) {
      if (!CPositions::HasDirection(Magic, POSITION_TYPE_BUY)) {
         OpenPos(ORDER_TYPE_BUY, price);
      }
   }
   // 超买 → 做空
   if (rsi > RSI_Overbought || price > bbUpper) {
      if (!CPositions::HasDirection(Magic, POSITION_TYPE_SELL)) {
         OpenPos(ORDER_TYPE_SELL, price);
      }
   }
}

//+------------------------------------------------------------------+
void OpenPos(ENUM_ORDER_TYPE type, double price) {
   double sl = (type == ORDER_TYPE_BUY) ? price - SL_Points * _Point
                                        : price + SL_Points * _Point;
   double tp = (type == ORDER_TYPE_BUY) ? price + TP_Points * _Point
                                        : price - TP_Points * _Point;
   double slDist = MathAbs(price - sl);
   double lot = sizing.LotByRisk(RiskPct, slDist);
   if (lot <= 0) return;
   if (!risk.CanOpen(type, lot, sl, tp)) return;

   if (type == ORDER_TYPE_BUY) {
      if (trade.Buy(lot, sl, tp, "MR_Long"))
         log.Trade("BUY", _Symbol, lot, price, 0, "超卖做多");
   } else {
      if (trade.Sell(lot, sl, tp, "MR_Short"))
         log.Trade("SELL", _Symbol, lot, price, 0, "超买做空");
   }
}

//+------------------------------------------------------------------+
void RefreshDash() {
   dash.Clear();
   dash.SetTitle("=== MeanReversion ===");
   dash.Separator();
   dash.Row("RSI",  DoubleToString(ind.Value("RSI", 0), 2));
   dash.Row("BB Up",DoubleToString(ind.MACDValue("BB", 1, 0), _Digits));
   dash.Row("BB Lo",DoubleToString(ind.MACDValue("BB", 2, 0), _Digits));
   dash.Separator();
   dash.Row("Positions", IntegerToString(CPositions::CountMine(Magic))
                          + "/" + IntegerToString(MaxPos));
   dash.Row("Profit", DoubleToString(CPositions::TotalProfit(Magic), 2));
   dash.Show();
}
//+------------------------------------------------------------------+
```

## 关键参数

### RSI 阈值
- 经典：70/30（一般震荡）
- 强势震荡：80/20（更严）
- 弱势震荡：60/40（更频繁）

### Bollinger
- 周期 20 + deviation 2.0 是经典
- 周期 10 + deviation 1.5 灵敏
- 周期 30 + deviation 2.5 稳定

### ADX 过滤
- ADX > 25：明确有趋势，**不开**逆势单
- ADX < 20：盘整，适合逆势
- 关闭过滤 → 永远开（更激进）

## 关键风险
- **强单边行情会一直亏**（RSI 钝化在超买/超卖区域）
- 必须加 ADX 过滤
- 严格控制最大持仓数
- **必须设止损**（均值回归失败 → 趋势延续 → 大亏）

## 何时不用
- 重大新闻前后（NFP、CPI、央行利率）
- 强趋势品种（如 2022 USD/JPY 单边涨）
- 周一月开盘
