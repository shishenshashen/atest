---
title: EA 网格马丁模板
tags: [EA, 模板, 网格, 马丁, 高风险]
type: template
---

# EA 网格马丁模板

> ⚠️ **高风险策略**。马丁格尔亏损可能无限放大，**新手当学习用即可**。
> 思路：跌破 X 点就加仓（手数加倍），涨回均价就全平。

## 实战 EA 引用

> ⚠️ **马丁慎用警示**：逆势加仓，单边爆仓风险极高，实盘前必做 1 个月回测 + Demo 1 周沙盒 + 硬止损 HardStopLoss。
>
> **本模板的实物参考**：`ScalpingMartin_EA.mq5`（`MQL5/Experts/_archive/me-ea/`，**47.0 KB / 1288 行**，马丁 + 网格复合 EA）。
> - 实物源：`MQL5/Experts/_archive/me-ea/ScalpingMartin_EA.mq5`（**只读不写**——`_archive/` 是用户实物历史库）
> - 接入现状：⚠️ **零 MQL5Kit 模块**——Node.js fs 实读 2026-06-04：`#include <MQL5Kit/...>` 0 行 / object 1 个（`CTrade trade;` L58，原生 MQL5 `Trade.mqh` 而非 MQL5Kit `CTradePlus`）/ OnInit L187 / OnTick L307 / OnDeinit L291 / OnTimer L377
> - 53 KB 复杂度：自带 grid + martin + 自带 panel + 自带 session filter + 自带 news filter（**全部手写**），未走 MQL5Kit 标准模块
> - 接入状态：⚠️ **未做 N4 复活**——要从 `_archive/` 迁到 `minimax-ea/` 需要先理清 1288 行自带逻辑再按 BBTrendEA SOP 模板做 12 步接入，依赖 console 1 GUI
> - 实盘前必做：(1) 1 个月 MT5 Strategy Tester 回测 / (2) Demo 1 周沙盒验 trades CSV 落盘 / (3) HardStopLoss ≤ 账户 30% / (4) MaxPositions ≤ 50 / (5) **不要在新闻/NFP/CPI 前运行**
> - 链向：`[[实战/ScalpingMartin 复活 (N4, 阻塞 console 1)]]` / `[[实战/BBTrendEA 复活 SOP]]`（archive 复活 12 步范本，可作 N4 复活的参考）/ `[[04-避坑与速查/05 必查清单]]`（发版前 Checklist）

```mql5
//+------------------------------------------------------------------+
//|                                    GridMartin_EA.mq5              |
//|                              网格 + 马丁格尔 EA                    |
//+------------------------------------------------------------------+
#property copyright "MyEA"
#property version   "1.00"
#property strict

#include <MQL5Kit/M01_CTradePlus.mqh>
#include <MQL5Kit/M02_Risk.mqh>
#include <MQL5Kit/M05_NewBar.mqh>
#include <MQL5Kit/M07_Positions.mqh>
#include <MQL5Kit/M11_Logger.mqh>
#include <MQL5Kit/M16_Cleanup.mqh>

//--- 输入
input ulong  Magic = 20260401;

input group "=== 网格 ==="
input int    GridStep = 200;            // 加仓间隔（点数）
input int    MaxLevels = 5;             // 最大加仓层数
input double LotMultiplier = 2.0;       // 每次加仓手数倍数
input double InitialLot = 0.01;
input int    TP_AvgPips = 100;          // 均价止盈（点数）

input group "=== 风控（务必启用）==="
input bool   UseHardStop = true;        // 硬止损
input double HardStopLoss = 5000;       // 浮亏到 X 美元全平
input int    MaxPositions = 50;

//--- 全局
CTradePlus trade;
CRisk      risk;
CNewBar    NB;
CLogger    log;

//--- 内部状态
datetime _lastBar = 0;
double   _startBalance = 0;

//+------------------------------------------------------------------+
int OnInit() {
   trade.Init(Magic, 30);
   NB.Init(_Period);
   _startBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   if (reason == REASON_PROGRAM || reason == REASON_REMOVE)
      CCleanup::CleanupAll(Magic, "GM_", "GM_", true, true, true);
   log.Close();
   Comment("");
}

void OnTick() {
   // 1) 硬止损检查（每个 tick 都做）
   if (UseHardStop) {
      double loss = -CPositions::TotalNet(Magic);
      if (loss >= HardStopLoss) {
         PrintFormat("🚨 硬止损触发 loss=%.2f, 全平", loss);
         CloseAll();
         return;
      }
   }

   // 2) 均价止盈检查
   CheckTakeProfit();

   // 3) 新 K 线：判断加仓
   if (!NB.IsNewBar()) return;
   CheckAddPosition();
}

//+------------------------------------------------------------------+
//| 加仓逻辑                                                          |
//+------------------------------------------------------------------+
void CheckAddPosition() {
   int n = CPositions::CountMine(Magic);
   if (n == 0) {
      // 无持仓，开第一笔（按当前信号）
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      // 简化：固定做多
      if (trade.Buy(InitialLot, 0, 0, "GridL1"))
         log.Trade("BUY", _Symbol, InitialLot, ask, 0, "L1");
      return;
   }
   if (n >= MaxLevels) return;
   if (n >= MaxPositions) return;

   // 找最新持仓的开仓价
   ulong lastTicket = CPositions::FindFirst(Magic, _Symbol);
   if (lastTicket == 0) return;
   if (!PositionSelectByTicket(lastTicket)) return;
   double lastPrice = PositionGetDouble(POSITION_PRICE_OPEN);
   ENUM_POSITION_TYPE lastType =
      (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

   double cur = (lastType == POSITION_TYPE_BUY)
              ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
              : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   // 价差（点数）
   double diff = (lastType == POSITION_TYPE_BUY)
               ? (lastPrice - cur) / _Point
               : (cur - lastPrice) / _Point;

   if (diff >= GridStep) {
      // 加仓：手数 = InitialLot * LotMultiplier^(n-1)
      double newLot = InitialLot * MathPow(LotMultiplier, n);
      // 规范化
      double minL  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double maxL  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
      double stepL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      newLot = MathMax(minL, MathMin(maxL,
                  MathFloor(newLot / stepL) * stepL));

      if (lastType == POSITION_TYPE_BUY) {
         if (trade.Buy(newLot, 0, 0, "GridL" + IntegerToString(n+1)))
            log.Trade("BUY", _Symbol, newLot, cur, 0,
                      "L" + IntegerToString(n+1) + " 加仓");
      } else {
         if (trade.Sell(newLot, 0, 0, "GridL" + IntegerToString(n+1)))
            log.Trade("SELL", _Symbol, newLot, cur, 0,
                      "L" + IntegerToString(n+1) + " 加仓");
      }
   }
}

//+------------------------------------------------------------------+
//| 均价止盈                                                          |
//+------------------------------------------------------------------+
void CheckTakeProfit() {
   if (CPositions::CountMine(Magic) < 2) return;  // 至少 2 笔才考虑

   // 算加权平均开仓价
   double totalVol = 0, sumPrice = 0;
   ulong tkts[];
   CPositions::Collect(Magic, tkts);
   for (int i = 0; i < ArraySize(tkts); i++) {
      if (!PositionSelectByTicket(tkts[i])) continue;
      double v = PositionGetDouble(POSITION_VOLUME);
      double p = PositionGetDouble(POSITION_PRICE_OPEN);
      totalVol += v;
      sumPrice += v * p;
   }
   if (totalVol == 0) return;
   double avgPrice = sumPrice / totalVol;

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   // 判断方向：所有持仓同一方向？简化：找第一笔的方向
   ulong first = tkts[0];
   if (!PositionSelectByTicket(first)) return;
   ENUM_POSITION_TYPE dir = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

   bool takeProfit = false;
   if (dir == POSITION_TYPE_BUY && bid >= avgPrice + TP_AvgPips * _Point)
      takeProfit = true;
   if (dir == POSITION_TYPE_SELL && ask <= avgPrice - TP_AvgPips * _Point)
      takeProfit = true;

   if (takeProfit) {
      PrintFormat("🎯 均价止盈触发 avg=%.5f bid=%.5f ask=%.5f",
                  avgPrice, bid, ask);
      CloseAll();
   }
}

//+------------------------------------------------------------------+
void CloseAll() {
   ulong tkts[];
   CPositions::Collect(Magic, tkts);
   for (int i = 0; i < ArraySize(tkts); i++) {
      trade.ClosePos(tkts[i]);
   }
}
//+------------------------------------------------------------------+
```

## 马丁格尔手数表
`LotMultiplier = 2.0`，初始 0.01：

| 层数 | 手数 | 累计手数 |
|---|---|---|
| 1 | 0.01 | 0.01 |
| 2 | 0.02 | 0.03 |
| 3 | 0.04 | 0.07 |
| 4 | 0.08 | 0.15 |
| 5 | 0.16 | 0.31 |
| 6 | 0.32 | 0.63 |

5 层之后风险已经爆表。

## 风险分析（必须看）
- 单边行情：价格一路向不利方向 → 不断加仓 → 资金耗尽
- 例如：XAUUSD 跌 1000 点（5 个 GridStep），亏损 ≈ 全部累计
- 硬止损必须设（建议 HardStopLoss < 账户 30%）

## 实盘必备
- ✅ 硬止损 HardStopLoss
- ✅ 最大层数 MaxLevels
- ✅ 最大持仓数 MaxPositions
- ✅ 资金检查：加仓前查 `AccountInfoDouble(ACCOUNT_MARGIN_FREE)`
- ❌ **不要在新闻/非农/CPI 前运行**
- ❌ **不要用 100% 资金**

## 改进
- 改成反马丁（亏损减仓、盈利加仓）— 胜率会高但盈亏比差
- 加 ADX 过滤（趋势市不开）
- 加 ATR 动态 GridStep（震荡小、趋势大）
- 多品种对冲（一组多 + 一组空）

## 历史业绩
马丁 EA 在 MT5 市场里被卖得很火，**绝大多数长期亏损**。这是已知事实。
