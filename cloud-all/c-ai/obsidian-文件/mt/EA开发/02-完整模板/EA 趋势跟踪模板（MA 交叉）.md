---
title: EA 趋势跟踪模板（MA 交叉）
tags: [EA, 模板, 趋势跟踪, MA]
type: template
---

# EA 趋势跟踪模板（MA 交叉）

> 经典策略：快 MA 上穿慢 MA → 做多；快 MA 下穿慢 MA → 做空。
> **可立即编译运行**（绑 M01/M02/M03/M04/M05 即可）。

## 实战 EA 引用

> **本模板的实物参考**：`TrendMA_EA.mq5`（`MQL5/Experts/minimax-ea/`，8.9 KB / 239 行，**12 模块**）。
> - 实物源：`MQL5/Experts/minimax-ea/TrendMA_EA.mq5` (Node.js fs 实读 2026-06-04)
> - 接入点：`#include <MQL5Kit/...>` L9-L20（M01/M02/M03/M04/M05/M06/M07/M08/M09/M10/M11/M16）/ object 声明 L48-L56（9 个对象）/ OnInit L64（`ind.AddMA("MA_Fast"/"MA_Slow",...)` L69-70 + `trail.SetParams(TrailStart, TrailStep, 10)` L72）
> - OnTick L91：`ind.Values("MA_Fast"/"MA_Slow", _fastArr/_slowArr, 3)` L98-99 → `CheckEntry` L100 → `CSignal::CrossUpSeries/CrossDownSeries` L107/L111
> - 链向：`[[实战/TrendMA_EA wiki (P2)]]` / `[[EA 开发知识库]]` §完整模板索引

```mql5
//+------------------------------------------------------------------+
//|                                       TrendMA_EA.mq5              |
//|                              趋势跟踪 EA（MA 交叉）                |
//+------------------------------------------------------------------+
#property copyright "MyEA"
#property version   "1.00"
#property strict

#include <MQL5Kit/M01_CTradePlus.mqh>
#include <MQL5Kit/M02_Risk.mqh>
#include <MQL5Kit/M03_PositionSizing.mqh>
#include <MQL5Kit/M04_IndicatorPool.mqh>
#include <MQL5Kit/M05_NewBar.mqh>
#include <MQL5Kit/M06_Signal.mqh>
#include <MQL5Kit/M07_Positions.mqh>
#include <MQL5Kit/M08_TrailingStop.mqh>
#include <MQL5Kit/M09_Dashboard.mqh>
#include <MQL5Kit/M11_Logger.mqh>
#include <MQL5Kit/M16_Cleanup.mqh>

//--- 输入
input group "=== 基础 ==="
input ulong  Magic = 20260101;

input group "=== MA 参数 ==="
input int    FastMA_Period = 12;       // 快线周期
input int    SlowMA_Period = 26;       // 慢线周期
input ENUM_MA_METHOD MA_Method = MODE_EMA;  // MA 类型

input group "=== 仓位/风控 ==="
input double RiskPct  = 0.01;
input int    MaxPos   = 3;
input int    SL_Points = 300;
input int    TP_Points = 600;

input group "=== 追踪止损 ==="
input bool   UseTrailing = true;
input int    TrailStart  = 200;
input int    TrailStep   = 150;

input group "=== 显示 ==="
input bool   ShowDashboard = true;

//--- 全局
CTradePlus      trade;
CRisk           risk;
CPositionSizing sizing;
CIndicatorPool  ind;
CNewBar         NB;
CTrailingStop   trail;
CDashboard      dash;
CLogger         log;

//--- 缓存
double _fastArr[3], _slowArr[3];

//+------------------------------------------------------------------+
int OnInit() {
   trade.Init(Magic, 30);
   risk.Init(Magic, MaxPos, RiskPct);
   sizing.Init(RiskPct);
   NB.Init(_Period);

   ind.AddMA("MA_Fast", FastMA_Period, MA_Method);
   ind.AddMA("MA_Slow", SlowMA_Period, MA_Method);
   ind.AddATR("ATR", 14);  // 可选：用 ATR 动态止损

   trail.Init(&trade, Magic);
   trail.SetParams(TrailStart, TrailStep, 10);

   Print("TrendMA EA 启动");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   if (reason == REASON_PROGRAM || reason == REASON_REMOVE)
      CCleanup::CleanupAll(Magic, "TrendMA_", "TrendMA_", true, true, true);
   else
      CCleanup::DeleteMyObjects("TrendMA_");
   log.Close();
   Comment("");
}

//+------------------------------------------------------------------+
void OnTick() {
   if (!NB.IsNewBar()) {
      if (UseTrailing) trail.Apply();
      if (ShowDashboard) RefreshDash();
      return;
   }

   // 取最近 3 根 MA
   if (ind.Values("MA_Fast", _fastArr, 3) < 3) return;
   if (ind.Values("MA_Slow", _slowArr, 3) < 3) return;

   // 入场
   CheckEntry();

   // 出场（简单的"反向交叉"平仓）
   CheckExit();

   if (ShowDashboard) RefreshDash();
}

//+------------------------------------------------------------------+
void CheckEntry() {
   int n = CPositions::CountMine(Magic);
   if (n >= MaxPos) return;

   // 金叉
   if (CSignal::CrossUpSeries(_fastArr, _slowArr)) {
      if (!CPositions::HasDirection(Magic, POSITION_TYPE_BUY)) {
         OpenPos(ORDER_TYPE_BUY);
      }
   }
   // 死叉
   if (CSignal::CrossDownSeries(_fastArr, _slowArr)) {
      if (!CPositions::HasDirection(Magic, POSITION_TYPE_SELL)) {
         OpenPos(ORDER_TYPE_SELL);
      }
   }
}

//+------------------------------------------------------------------+
void CheckExit() {
   // 多单：死叉出现 → 平多
   if (CPositions::HasDirection(Magic, POSITION_TYPE_BUY)
    && CSignal::CrossDownSeries(_fastArr, _slowArr)) {
      ulong t = CPositions::FindFirst(Magic, _Symbol, POSITION_TYPE_BUY);
      if (t != 0) trade.ClosePos(t);
   }
   // 空单：金叉出现 → 平空
   if (CPositions::HasDirection(Magic, POSITION_TYPE_SELL)
    && CSignal::CrossUpSeries(_fastArr, _slowArr)) {
      ulong t = CPositions::FindFirst(Magic, _Symbol, POSITION_TYPE_SELL);
      if (t != 0) trade.ClosePos(t);
   }
}

//+------------------------------------------------------------------+
void OpenPos(ENUM_ORDER_TYPE type) {
   double price = (type == ORDER_TYPE_BUY)
                ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if (price == 0) return;

   double sl = (type == ORDER_TYPE_BUY) ? price - SL_Points * _Point
                                        : price + SL_Points * _Point;
   double tp = (type == ORDER_TYPE_BUY) ? price + TP_Points * _Point
                                        : price - TP_Points * _Point;
   double slDist = MathAbs(price - sl);

   double lot = sizing.LotByRisk(RiskPct, slDist);
   if (lot <= 0) return;

   if (!risk.CanOpen(type, lot, sl, tp)) return;

   if (type == ORDER_TYPE_BUY) {
      if (trade.Buy(lot, sl, tp, "TrendLong"))
         log.Trade("BUY", _Symbol, lot, price, 0, "金叉");
   } else {
      if (trade.Sell(lot, sl, tp, "TrendShort"))
         log.Trade("SELL", _Symbol, lot, price, 0, "死叉");
   }
}

//+------------------------------------------------------------------+
void RefreshDash() {
   dash.Clear();
   dash.SetTitle("=== TrendMA ===");
   dash.Separator();
   dash.Row("Symbol", _Symbol);
   dash.Row("TF",     EnumToString(_Period));
   dash.Row("MA Fast", DoubleToString(_fastArr[0], _Digits));
   dash.Row("MA Slow", DoubleToString(_slowArr[0], _Digits));
   dash.Separator();
   dash.Row("Positions", IntegerToString(CPositions::CountMine(Magic))
                          + "/" + IntegerToString(MaxPos));
   dash.Row("Profit", DoubleToString(CPositions::TotalProfit(Magic), 2));
   dash.Separator();
   dash.Line(TimeToString(TimeCurrent()));
   dash.Show();
}
//+------------------------------------------------------------------+
```

## 调参建议

### 趋势型品种（EURUSD、XAUUSD 大周期）
- FastMA: 12-20
- SlowMA: 26-50
- SL_Points: ATR 的 1.5-2 倍
- TP_Points: SL 的 2 倍（盈亏比 2:1）

### 震荡型品种
- FastMA: 5-8
- SlowMA: 13-21
- 适当加大 SL，减小 TP
- 加上 RSI / Bollinger 过滤假突破

### 加过滤器（避免震荡市反复挨打）
- 加 RSI：只在 30-70 之间开仓
- 加 ADX：ADX > 25 才认作有趋势
- 加 ATR 最小波动：太小时不开仓

## 已知问题
- MA 交叉滞后（信号在 K 线收盘后才知道）
- 震荡市反复金叉死叉 → 加过滤器解决
- 单边大行情会触发多次交叉（用 trailing stop 锁利）

## 进阶
- 多时间框架：H4 定方向 → H1 入场 → M15 精确止损
- 仓位随趋势强度变化：ADX 高时加大手数
- 加 ATR 动态止损：SL = 1.5 × ATR
