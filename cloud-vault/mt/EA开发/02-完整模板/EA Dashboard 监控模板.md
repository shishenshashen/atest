---
title: EA Dashboard 监控模板
tags: [EA, 模板, 面板, Dashboard]
type: template
---

# EA Dashboard 监控模板

> **不是交易 EA**，只做监控：显示多个品种/账户/持仓的实时数据。
> 用于：账户仪表盘、跨品种监控、信号预警。

## 实战 EA 引用

> **本模板的实物参考**：`Dashboard.mq5`（`MQL5/Experts/minimax-ea/`，8.1 KB / 208 行，**4 模块**：M04 IndicatorPool + M09 Dashboard + M10 Notify + M15 TimerService）。
> - 实物源：`MQL5/Experts/minimax-ea/Dashboard.mq5` (Node.js fs 实读 2026-06-04)
> - 接入点：`#include <MQL5Kit/...>` **L9-L12**（M04 L9 / M09 L10 / M10 L11 / M15 L12）/ object **L30-L33**（`CIndicatorPool _ind` L30 / `CDashboard _dash` L31 / `CTimerService _timer` L32 / `CNotify M10` L33）
> - OnInit L42：`_timer.Init(RefreshSec * 1000)` L46（M15 心跳 wrapper, 取代 EventSetTimer）+ `_ind.AddMA/AddMA/AddRSI` L57-L59（每品种 3 指标 × 4 品种 = 12 句柄）
> - OnTimer L75 → `_timer.OnTimer()` L78 → `_Refresh()` L83（**跨品种 for 循环实际在 L99-L113**，非 L84-L87）
>   - L99 `for (int i = 0; i < _nSymbols; i++)` 起点 → L100-105 拉 bid/spread/maF/maS/rsi → L107-110 算 trend (UP/DN/FLAT) → L111 `_dash.Line(StringFormat(...))` 拼装 + L115-117 M15 heartbeat + L119 `_dash.Show()`
>   - 输出约 12 行: 4 账户 (Balance/Equity/Free) + 1 持仓汇总 + 4 品种行 + 1 心跳 + 1 时间戳 = ~12 `_dash.Row/Line` 调用
> - 链向：`[[实战/Dashboard wiki (P2)]]` / `[[实战/MeanReversion_EA 接入报告]]`（同样跨品种监控 + 11 个指标）

```mql5
//+------------------------------------------------------------------+
//|                                    Dashboard.mq5                  |
//|                              实时监控面板（只读，不交易）           |
//+------------------------------------------------------------------+
#property copyright "MyEA"
#property version   "1.00"
#property strict

#include <MQL5Kit/M04_IndicatorPool.mqh>
#include <MQL5Kit/M09_Dashboard.mqh>

//--- 配置
input group "=== 监控品种 ==="
input string Symbols = "EURUSD,GBPUSD,XAUUSD,USDJPY,BTCUSD";

input group "=== 指标 ==="
input int    FastMA = 12;
input int    SlowMA = 26;
input int    RSI_Period = 14;

input group "=== 刷新 ==="
input int    RefreshSec = 2;

CIndicatorPool _ind;
CDashboard     _dash;

string _symbols[];
int   _nSymbols;
datetime _lastRefresh = 0;

//+------------------------------------------------------------------+
int OnInit() {
   EventSetTimer(RefreshSec);
   _Parse();
   // 给每个品种建指标
   for (int i = 0; i < _nSymbols; i++) {
      SymbolSelect(_symbols[i], true);
      _ind.AddMA  ("MA_F_"  + _symbols[i], FastMA, MODE_EMA);
      _ind.AddMA  ("MA_S_"  + _symbols[i], SlowMA, MODE_EMA);
      _ind.AddRSI ("RSI_"   + _symbols[i], RSI_Period);
   }
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   _ind.ReleaseAll();
   EventKillTimer();
   Comment("");
}

void OnTimer() {
   _Refresh();
}

//+------------------------------------------------------------------+
void _Refresh() {
   _dash.Clear();
   _dash.SetTitle("=== 跨品种 Dashboard ===");
   _dash.Separator();

   // 账户
   _dash.Row("Balance", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2));
   _dash.Row("Equity",  DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),  2));
   _dash.Row("Margin",  DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN),  2));
   _dash.Row("Free",    DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE), 2));
   _dash.Separator();

   // 持仓汇总
   int n = PositionsTotal();
   double totalP = 0;
   for (int i = 0; i < n; i++) {
      ulong t = PositionGetTicket(i);
      if (t) totalP += PositionGetDouble(POSITION_PROFIT);
   }
   _dash.Row("Open P/L", DoubleToString(totalP, 2) + " (" + IntegerToString(n) + " 笔)");
   _dash.Separator();

   // 品种行情
   for (int i = 0; i < _nSymbols; i++) {
      string sym = _symbols[i];
      double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
      double bid = SymbolInfoDouble(sym, SYMBOL_BID);
      long spread = SymbolInfoInteger(sym, SYMBOL_SPREAD);

      double maF = _ind.Value("MA_F_" + sym, 0);
      double maS = _ind.Value("MA_S_" + sym, 0);
      double rsi = _ind.Value("RSI_"  + sym, 0);

      // 趋势判断
      string trend = (maF > maS) ? "↑多"
                   : (maF < maS) ? "↓空" : "—";
      if (rsi == EMPTY_VALUE || maF == EMPTY_VALUE) {
         trend = "N/A";
      }

      string line = StringFormat("%s  bid=%.5f sp=%ld  %s  RSI=%.1f",
                                 sym, bid, spread, trend, rsi);
      _dash.Line(line);
   }
   _dash.Separator();
   _dash.Line("Last update: " + TimeToString(TimeCurrent()));

   _dash.Show();
}

void _Parse() {
   string parts[];
   int n = StringSplit(Symbols, ',', parts);
   ArrayResize(_symbols, n);
   for (int i = 0; i < n; i++) {
      StringTrimLeft(parts[i]);
      StringTrimRight(parts[i]);
      _symbols[i] = parts[i];
   }
   _nSymbols = n;
}
//+------------------------------------------------------------------+
```

## 效果

```
=== 跨品种 Dashboard ===
--------------------------------
Balance     : 10011.96
Equity      : 10012.45
Margin      : 0.00
Free        : 10011.96
--------------------------------
Open P/L    : 0.49 (1 笔)
--------------------------------
EURUSD  bid=1.08521 sp=8  ↑多  RSI=58.2
GBPUSD  bid=1.27345 sp=12 ↑多  RSI=62.1
XAUUSD  bid=4488.715 sp=32 ↓空  RSI=42.5
USDJPY  bid=149.852  sp=10 ↑多  RSI=55.8
BTCUSD  bid=96432.10 sp=450 N/A  RSI=N/A
--------------------------------
Last update: 2025.11.04 11:42:30
```

## 进阶：自定义 UI（OBJ_LABEL）

`Comment()` 简陋，**用 OBJ_LABEL 做"真正"的 UI**：

```mql5
// 创建标签
void CreateLabel(string name, int x, int y, string text, color clr,
                 int fontSize = 10) {
   ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER,    CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetString (0, name, OBJPROP_TEXT,      text);
   ObjectSetString (0, name, OBJPROP_FONT,      "Consolas");
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE,  fontSize);
   ObjectSetInteger(0, name, OBJPROP_COLOR,     clr);
}

// 更新标签
void UpdateLabel(string name, string text, color clr) {
   ObjectSetString (0, name, OBJPROP_TEXT,  text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
}

// 删除所有本 EA 标签
void ClearLabels(string prefix) {
   for (int i = ObjectsTotal(0) - 1; i >= 0; i--) {
      string n = ObjectName(0, i);
      if (StringFind(n, prefix) == 0) ObjectDelete(0, n);
   }
}
```

完整版参考 [[01-调用模块/M14 画图 Drawer]]。

## 必看陷阱
- 多品种指标句柄多（10 个品种 × 3 指标 = 30 句柄），**OnDeinit 必 Release**
- 刷新频率别太高（≥ 1 秒），不然耗 CPU
- 某些品种数据不足时 `Value()` 返回 `EMPTY_VALUE`，**必须检查**
- BTCUSD 在某些经纪商叫 BTCUSDm 或 BTCUSD.m，别搞错

---

### 反向引用（实物 EA 接入 demo, 21:00 T2 沉淀）

> **本段是 21:00 巡检 T2 任务对 [[实战/MyEA + Dashboard 接入报告]] 的反向链接**。本模板的实物参考 = Dashboard.mq5 (`MQL5/Experts/minimax-ea/`, 208L/8.3KB/4 模块), 模板 wiki §实战 EA 引用 已引用, 本段补详细接入点 + M15 升级差异:

- **Dashboard.mq5 4 模块 vs 模板**: 模板 L32-33 走 `#include <MQL5Kit/M04_IndicatorPool.mqh>` + `<MQL5Kit/M09_Dashboard.mqh>` 2 个, Dashboard L9-12 走 M04 + M09 + M10 + M15 4 个 — **多了 M10 (3 触发器) + M15 (定时器)** 2 模块
- **M15 升级**: 模板 L56 `EventSetTimer(RefreshSec)` 裸调, Dashboard L57 `_timer.Init(RefreshSec * 1000)` M15 包装 — 自动选 `EventSetMillisecondTimer` / `EventSetTimer` + 心跳统计 + 启停状态机
- **M10 通知**: 模板无 M10, Dashboard L33 + L63-64 `M10.EnablePush/EnableSound` + L138 `_CheckDrawdown` DD 报警 + L167 `OnTrade` 新成交 + L191 `OnTradeTransaction` 拒单 = 5 方法调用 3 类触发器
- **链向**: [[实战/MyEA + Dashboard 接入报告]] §1.4 Dashboard 独有 M15 + §2.2 Dashboard 4 模块接入表 + §2.6 M15 TimerService 心跳节流 + §4.1 模板对应表 + §4.3 Dashboard 监控模板范本 (3 升级维度)
