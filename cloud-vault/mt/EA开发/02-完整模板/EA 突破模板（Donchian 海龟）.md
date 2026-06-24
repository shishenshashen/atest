---
title: EA 突破模板（Donchian 海龟）
tags: [EA, 模板, 突破, 海龟, Donchian]
type: template
---

# EA 突破模板（Donchian / 海龟）

> 经典海龟策略：N 日新高做多，N 日新低做空。
> 趋势型策略，胜率低但盈亏比大。

## 实战 EA 引用

> **本模板的实物参考**：`Breakout_EA.mq5`（`MQL5/Experts/minimax-ea/`，9.1 KB / 237 行，**11 模块**）。
> - 实物源：`MQL5/Experts/minimax-ea/Breakout_EA.mq5` (Node.js fs 实读 2026-06-04)
> - 接入点：`#include <MQL5Kit/...>` L9-L19（M01/M02/M03/M04/M05/M07/M08/M09/M10/M11/M16 — 无 M06 Signal）/ object L50-L58（9 个对象）
> - OnInit L68：`ind.AddBands("Donchian_Hi"/"Donchian_Lo", DonchianPeriod, 2.0)` L73-74（仅作图）/ `ind.AddEMA("HTF_EMA", HTF_EMA_Period)` L75 / `ind.AddADX("ADX", ADX_Period)` L76 / `trail.SetParams(TrailStart, TrailStep, 10)` L78（参数来自 input L43-45，**非硬编码 200/100/20**）
> - OnTick L95：`CopyHigh/CopyLow` L106-107 算 Donchian 通道 → `ind.Value("HTF_EMA"/"ADX")` L117/L126 过滤 → `_RefreshDash` L149
> - 链向：`[[实战/Breakout_EA wiki (P2)]]` / `[[实战/BBTrendEA 复活 SOP]]`（海龟+多周期 BB 趋势的 archive 复活范本）

```mql5
//+------------------------------------------------------------------+
//|                                    Breakout_EA.mq5                 |
//|                              突破 / 海龟 EA                        |
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
input ulong  Magic = 20260301;

input group "=== Donchian ==="
input int    Donchian_N = 20;           // N 日新高/低
input int    Donchian_Exit_N = 10;      // 突破反向则平仓的 N

input group "=== 仓位/风控 ==="
input double RiskPct  = 0.01;
input int    MaxPos   = 2;
input int    SL_Points = 400;
input int    TP_Points = 0;             // 0 = 不用 TP，靠追踪

input group "=== 追踪止损（ATR 倍数）==="
input bool   UseTrailing = true;
input double TrailATR_Mult = 2.0;       // SL 距最高/最低 N 倍 ATR

//--- 全局
CTradePlus      trade;
CRisk           risk;
CPositionSizing sizing;
CIndicatorPool  ind;
CNewBar         NB;
CTrailingStop   trail;
CDashboard      dash;
CLogger         log;

double _highArr[100], _lowArr[100];

//+------------------------------------------------------------------+
int OnInit() {
   trade.Init(Magic, 30);
   risk.Init(Magic, MaxPos, RiskPct);
   sizing.Init(RiskPct);
   NB.Init(_Period);
   ind.AddATR("ATR", 14);
   trail.Init(&trade, Magic);
   trail.SetParams(200, 100, 20);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   if (reason == REASON_PROGRAM || reason == REASON_REMOVE)
      CCleanup::CleanupAll(Magic, "BO_", "BO_", true, true, true);
   log.Close();
   Comment("");
}

void OnTick() {
   if (!NB.IsNewBar()) {
      if (UseTrailing) trail.Apply();
      return;
   }

   // 拉 N 根高低
   int n = Donchian_N + 1;
   ArrayResize(_highArr, n);
   ArrayResize(_lowArr,  n);
   ArraySetAsSeries(_highArr, true);
   ArraySetAsSeries(_lowArr,  true);
   CopyHigh(_Symbol, _Period, 1, Donchian_N, _highArr);
   CopyLow (_Symbol, _Period, 1, Donchian_N, _lowArr);
   // _highArr[0] 是上一根的 high，要用 Donchian_N 内的最大
   // CopyHigh 之后 _highArr[0..N-1]，但不包括当前未关闭的 K 线
   // N 日新高 = max(_highArr[0..N-1])
   int maxN = ArrayMaximum(_highArr, 0, Donchian_N);
   int minN = ArrayMinimum(_lowArr,  0, Donchian_N);
   double donchianHigh = _highArr[maxN];
   double donchianLow  = _lowArr[minN];
   double close = iClose(_Symbol, _Period, 0);

   CheckEntry(close, donchianHigh, donchianLow);
   CheckExit(close, donchianHigh, donchianLow);
}

//+------------------------------------------------------------------+
void CheckEntry(double close, double high, double low) {
   if (CPositions::CountMine(Magic) >= MaxPos) return;

   // N 日新高 → 做多
   if (close > high) {
      if (!CPositions::HasDirection(Magic, POSITION_TYPE_BUY))
         OpenPos(ORDER_TYPE_BUY, close);
   }
   // N 日新低 → 做空
   if (close < low) {
      if (!CPositions::HasDirection(Magic, POSITION_TYPE_SELL))
         OpenPos(ORDER_TYPE_SELL, close);
   }
}

//+------------------------------------------------------------------+
void CheckExit(double close, double high, double low) {
   // 简化：突破反向后平仓
   // 完整版：Donchian_Exit_N 日反向突破
   if (CPositions::HasDirection(Magic, POSITION_TYPE_BUY)) {
      // ... 计算反向 Donchian ...
   }
}

//+------------------------------------------------------------------+
void OpenPos(ENUM_ORDER_TYPE type, double price) {
   double sl = (type == ORDER_TYPE_BUY) ? price - SL_Points * _Point
                                        : price + SL_Points * _Point;
   double tp = (TP_Points > 0) ? ((type == ORDER_TYPE_BUY) ? price + TP_Points * _Point
                                                            : price - TP_Points * _Point)
                               : 0;
   double slDist = MathAbs(price - sl);
   double lot = sizing.LotByRisk(RiskPct, slDist);
   if (lot <= 0) return;
   if (!risk.CanOpen(type, lot, sl, tp)) return;

   if (type == ORDER_TYPE_BUY) {
      if (trade.Buy(lot, sl, tp, "BO_Long"))
         log.Trade("BUY", _Symbol, lot, price, 0, "Donchian新高");
   } else {
      if (trade.Sell(lot, sl, tp, "BO_Short"))
         log.Trade("SELL", _Symbol, lot, price, 0, "Donchian新低");
   }
}
//+------------------------------------------------------------------+
```

## 核心思想
- **Donchian High** = 最近 N 根（不含当前）的最高价
- **Donchian Low** = 最近 N 根的最低价
- 当前 K 线收盘 > Donchian High → **突破新高 → 做多**
- 当前 K 线收盘 < Donchian Low → **突破新低 → 做空**

## 海龟策略原版参数
- 入场周期：20 日
- 出场周期：10 日
- 加仓：每涨 0.5 ATR 加一仓，最多 4 仓
- 止损：2 ATR

## 必看陷阱
- **假突破**：价格突破 N 日高点后又跌回来 → 严格止损
- **滑点**：突破瞬间点差扩大，`slippage` 设大点
- **时间框架**：日线突破比小时线更可靠
- **震荡市会反复止损** → 加大 N，或加 ADX 过滤

## 改进方向
- 加 ATR 动态止损（`TrailATR_Mult * ATR`）
- 加量能过滤（突破时成交量 > 20 日均量 × 1.5）
- 加趋势过滤（只在 200 日均线上方做多）
- 多时间框架：H4 突破 → H1 入场
