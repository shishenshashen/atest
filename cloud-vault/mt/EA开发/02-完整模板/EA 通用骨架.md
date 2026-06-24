---
title: EA 通用骨架
tags: [EA, 模板, 骨架]
type: template
---

# EA 通用骨架

> **最干净的起点**。啥也不做但能编译能跑。
> **怎么用**：复制全文到 MetaEditor, 编译。

## 实战 EA 引用

> **本骨架是 `minimax-ea/` 8 个实物的共同基础模板**——所有实物 EA 都从本骨架起步, 按需 `#include` 模块。
> - `MyEA.mq5` (11.7K, 10 模块) — `MQL5/Experts/minimax-ea/MyEA.mq5`, `#include` L10-L19, object L54-L60, OnInit L118
> - `Scalper_CsvProto.mq5` (4.2K, 1 模块 M13) — `#include` L14, OnTrade L79 (CSV 落盘最小原型)
> - `ScalperXAU.mq5` (41.7K, 13 模块含 M17) — `#include` L19-L31, object L107-L117, 4 版本演进 v1→v4
> - `Dashboard.mq5` (8.1K, 4 模块) — `#include` L9-L12, OnInit L42, OnTimer L75 + `_Refresh` L83
> - `Breakout_EA.mq5` (9.1K, 11 模块) — `#include` L9-L19, object L50-L58, OnInit L68
> - `TrendMA_EA.mq5` (8.9K, 12 模块) — `#include` L9-L20, object L48-L56, OnInit L64
> - `MeanReversion_EA.mq5` (12.7K, 13 模块含 M18+M19) — `#include` L9-L21, object L54-L64
>
> **链向（实物接入报告 / wiki）**：`[[实战/MyEA wiki (P2)]]` / `[[实战/Scalper_CsvProto wiki (P2)]]` / `[[实战/ScalperXAU 接入报告 + v1→v4 演进史]]` / `[[实战/Dashboard wiki (P2)]]` / `[[实战/Breakout_EA wiki (P2)]]` / `[[实战/TrendMA_EA wiki (P2)]]` / `[[实战/MeanReversion_EA 接入报告]]`

```mql5
//+------------------------------------------------------------------+
//|                                              MyEA.mq5              |
//|                              通用 EA 骨架                          |
//+------------------------------------------------------------------+
#property copyright "MyEA"
#property version   "1.00"
#property strict
#property description "通用 EA 骨架"

//--- 包含
#include <MQL5Kit/M01_CTradePlus.mqh>
#include <MQL5Kit/M02_Risk.mqh>
#include <MQL5Kit/M03_PositionSizing.mqh>
#include <MQL5Kit/M05_NewBar.mqh>
#include <MQL5Kit/M07_Positions.mqh>
#include <MQL5Kit/M09_Dashboard.mqh>
#include <MQL5Kit/M11_Logger.mqh>
#include <MQL5Kit/M16_Cleanup.mqh>

//--- 输入参数
input group "=== 基础 ==="
input ulong  Magic     = 20260101;     // 魔术码（每个 EA 唯一）
input string Comment   = "MyEA";       // 订单注释
input bool   AllowLong  = true;        // 允许做多
input bool   AllowShort = true;        // 允许做空

input group "=== 仓位 ==="
input double RiskPct   = 0.01;         // 单笔风险占净值比例（1%）
input int    MaxPos    = 3;            // 最大持仓数

input group "=== 止损止盈（点数）==="
input int    SL_Points = 200;          // 止损点数
input int    TP_Points = 400;          // 止盈点数

input group "=== 时间过滤 ==="
input int    StartHour = 8;            // 起始小时（服务器时间）
input int    EndHour   = 22;           // 结束小时

input group "=== 显示 ==="
input bool   ShowDashboard = true;     // 显示面板
input bool   EnableLog     = true;     // 写日志文件

//--- 全局对象
CTradePlus      trade;
CRisk           risk;
CPositionSizing sizing;
CNewBar         NB;
CDashboard      dash;
CLogger         log;

//+------------------------------------------------------------------+
//| 初始化                                                            |
//+------------------------------------------------------------------+
int OnInit() {
   // 1) 交易
   trade.Init(Magic, 30);
   trade.SetRetry(3, 200);

   // 2) 风控
   risk.Init(Magic, MaxPos, RiskPct);

   // 3) 仓位
   sizing.Init(RiskPct);

   // 4) 新 K 线
   NB.Init(_Period);

   // 5) 日志
   log.SetFileOutput(EnableLog);

   PrintFormat("MyEA 启动 magic=%I64u period=%s",
               Magic, EnumToString(_Period));
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| 卸载                                                              |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   // 清理
   if (reason == REASON_PROGRAM || reason == REASON_REMOVE) {
      CCleanup::CleanupAll(Magic, "MyEA_", "MyEA_", true, true, true);
   } else {
      CCleanup::DeleteMyObjects("MyEA_");
   }
   log.Close();
   Comment("");
}

//+------------------------------------------------------------------+
//| 主循环                                                            |
//+------------------------------------------------------------------+
void OnTick() {
   if (!NB.IsNewBar()) {
      // 1 秒一次的快速检查（追踪止损、面板）
      if (ShowDashboard) RefreshDashboard();
      return;
   }

   // 时间过滤
   if (!IsTradeTime()) return;

   // 1) 检查持仓
   ManageTrades();

   // 2) 检查入场
   if (CPositions::Count(Magic) < MaxPos) {
      CheckEntry();
   }

   // 3) 刷新面板
   if (ShowDashboard) RefreshDashboard();
}

//+------------------------------------------------------------------+
//| 时间过滤                                                          |
//+------------------------------------------------------------------+
bool IsTradeTime() {
   MqlDateTime dt;
   TimeCurrent(dt);
   if (StartHour < EndHour)
      return (dt.hour >= StartHour && dt.hour < EndHour);
   else  // 跨午夜
      return (dt.hour >= StartHour || dt.hour < EndHour);
}

//+------------------------------------------------------------------+
//| 入场检查                                                          |
//+------------------------------------------------------------------+
void CheckEntry() {
   if (AllowLong && /* BuySignal */) TryOpen(ORDER_TYPE_BUY);
   if (AllowShort && /* SellSignal */) TryOpen(ORDER_TYPE_SELL);
}

//+------------------------------------------------------------------+
//| 下单                                                              |
//+------------------------------------------------------------------+
void TryOpen(ENUM_ORDER_TYPE type) {
   double price = (type == ORDER_TYPE_BUY)
                ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if (price == 0) return;

   double sl = (type == ORDER_TYPE_BUY)
             ? price - SL_Points * _Point
             : price + SL_Points * _Point;
   double tp = (type == ORDER_TYPE_BUY)
             ? price + TP_Points * _Point
             : price - TP_Points * _Point;

   // 计算手数
   double slDist = MathAbs(price - sl);
   double lot    = sizing.LotByRisk(RiskPct, slDist);
   if (lot <= 0) return;

   // 风控检查
   if (!risk.CanOpen(type, lot, sl, tp)) return;

   // 下单
   if (type == ORDER_TYPE_BUY) {
      if (trade.Buy(lot, sl, tp, Comment))
         log.Trade("BUY", _Symbol, lot, price, 0, "开多");
   } else {
      if (trade.Sell(lot, sl, tp, Comment))
         log.Trade("SELL", _Symbol, lot, price, 0, "开空");
   }
}

//+------------------------------------------------------------------+
//| 持仓管理（追踪止损等）                                            |
//+------------------------------------------------------------------+
void ManageTrades() {
   // 简化：固定 SLTP，追踪止损需调用 CTrailingStop
   // 见 [[01-调用模块/M08 追踪止损 TrailingStop]]
}

//+------------------------------------------------------------------+
//| 面板                                                              |
//+------------------------------------------------------------------+
void RefreshDashboard() {
   dash.Clear();
   dash.SetTitle("=== MyEA ===");
   dash.Separator();
   dash.Row("Symbol", _Symbol);
   dash.Row("TF",     EnumToString(_Period));
   dash.Row("Spread", IntegerToString(SymbolInfoInteger(_Symbol, SYMBOL_SPREAD)));
   dash.Separator();
   dash.Row("Balance", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2));
   dash.Row("Equity",  DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),  2));
   dash.Separator();
   dash.Row("Positions", IntegerToString(CPositions::Count(Magic)) + "/" + IntegerToString(MaxPos));
   dash.Separator();
   dash.Line(TimeToString(TimeCurrent()));
   dash.Show();
}
//+------------------------------------------------------------------+
```

## 编译步骤
1. 把模块文件复制到 `MQL5/Include/MQL5Kit/` 目录
   - `M01_CTradePlus.mqh`
   - `M02_Risk.mqh`
   - `M03_PositionSizing.mqh`
   - `M05_NewBar.mqh`
   - `M07_Positions.mqh`
   - `M09_Dashboard.mqh`
   - `M11_Logger.mqh`
   - `M16_Cleanup.mqh`
2. 复制骨架到 `MQL5/Experts/MyEA.mq5`
3. MetaEditor (F4) → F7 编译
4. MT5 → 策略测试器 (Ctrl+R) → 选 MyEA → 跑

## 在骨架上扩展
| 想加什么 | 改哪 |
|---|---|
| 真实入场信号 | `CheckEntry()` 里的 `BuySignal` / `SellSignal` |
| 追踪止损 | `ManageTrades()` 调 `CTrailingStop::Apply()` |
| 指标 | OnInit 加 `CIndicatorPool`，OnTick 拿 `ind.Value(...)` |
| 推送通知 | 加 `CNotify`，在关键事件调 `notify.Trade(...)` |
| 画图 | 加 `CDrawer`，在信号触发处 `dr.BuyArrow(...)` |
| 定时任务 | 改用 `EventSetTimer(N)` 替代 `OnTick` |

## 必看
- **Magic 必改**（每个 EA 不同），不然多 EA 互相干扰
- **先在 Demo 账户跑**，跑通 1 周再上小资金
- 编译报"cannot open file"= 路径不对或 #include 写错
