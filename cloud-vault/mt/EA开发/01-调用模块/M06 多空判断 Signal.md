---
title: M06 多空判断 Signal
tags: [调用模块, 信号]
type: module
---

# M06 多空判断 Signal

> **作用**：把"金叉死叉 / 突破 / RSI 极值"等常见信号封装成可复用函数。
> **避免每个 EA 重复写交叉判断**。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                              M06_Signal.mqh       |
//|                              EA 开发知识库 - 信号判断              |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 信号工具集：交叉、突破、RSI 极值、MACD 状态等                     |
//+------------------------------------------------------------------+
class CSignal {
public:
   //+--- 双线交叉：上穿/下穿 -----------------------------------------+
   //  prevFast: 上一根的快线
   //  prevSlow: 上一根的慢线
   //  curFast:  当前快线
   //  curSlow:  当前慢线
   static bool CrossUp(double prevFast, double prevSlow,
                       double curFast,  double curSlow) {
      return prevFast <= prevSlow && curFast > curSlow;
   }
   static bool CrossDown(double prevFast, double prevSlow,
                         double curFast,  double curSlow) {
      return prevFast >= prevSlow && curFast < curSlow;
   }

   //+--- 数组上交叉：用两根 K 线对比 ----------------------------------+
   static bool CrossUpSeries(const double &fast[], const double &slow[]) {
      // 数组必须已 SetAsSeries(true)
      return CrossUp(fast[1], slow[1], fast[0], slow[0]);
   }
   static bool CrossDownSeries(const double &fast[], const double &slow[]) {
      return CrossDown(fast[1], slow[1], fast[0], slow[0]);
   }

   //+--- 突破：当前 > 阻力位且前一根 < 阻力位 -------------------------+
   static bool BreakUp(double cur, double prev, double level) {
      return prev <= level && cur > level;
   }
   static bool BreakDown(double cur, double prev, double level) {
      return prev >= level && cur < level;
   }

   //+--- RSI 极值 --------------------------------------------------+
   static bool IsOverbought(double rsi, double level = 70) { return rsi > level; }
   static bool IsOversold  (double rsi, double level = 30) { return rsi < level; }

   //+--- MACD 状态 --------------------------------------------------+
   //  histogram = main - signal
   static bool MACDHistogramPositive(double macdMain, double macdSignal) {
      return (macdMain - macdSignal) > 0;
   }
   static bool MACDHistogramTurnUp(double prevMain, double prevSignal,
                                   double curMain,  double curSignal) {
      return (prevMain - prevSignal) <= 0 && (curMain - curSignal) > 0;
   }
   static bool MACDHistogramTurnDown(double prevMain, double prevSignal,
                                     double curMain,  double curSignal) {
      return (prevMain - prevSignal) >= 0 && (curMain - curSignal) < 0;
   }

   //+--- Bollinger Bands 触碰/突破 ----------------------------------+
   static bool TouchUpperBand(double price, double upper) {
      return price >= upper;
   }
   static bool TouchLowerBand(double price, double lower) {
      return price <= lower;
   }

   //+--- 趋势：价格 > MA = 多 ---------------------------------------+
   static bool PriceAboveMA(double price, double ma) { return price > ma; }
   static bool PriceBelowMA(double price, double ma) { return price < ma; }

   //+--- K 线形态 --------------------------------------------------+
   static bool IsBullishCandle(double o, double c) { return c > o; }
   static bool IsBearishCandle(double o, double c) { return c < o; }
   static bool IsDoji(double o, double c, double tolerance = 0.0001) {
      return MathAbs(c - o) <= tolerance;
   }

   //+--- 三连阳 / 三连阴 --------------------------------------------+
   //  rates 数组：rates[0] 最新, rates[1] 前一根, ...
   //  需要至少 3 根
   static bool IsThreeWhiteSoldiers(const MqlRates &r[]) {
      return r[0].close > r[0].open
          && r[1].close > r[1].open
          && r[2].close > r[2].open;
   }
   static bool IsThreeBlackCrows(const MqlRates &r[]) {
      return r[0].close < r[0].open
          && r[1].close < r[1].open
          && r[2].close < r[2].open;
   }

   //+--- 综合：AND/OR 多个信号 ---------------------------------------+
   //  把多个 bool 用一个值表达
   static bool AllOf(int n, bool &arr[]) {
      for (int i = 0; i < n; i++) if (!arr[i]) return false;
      return true;
   }
   static bool AnyOf(int n, bool &arr[]) {
      for (int i = 0; i < n; i++) if (arr[i]) return true;
      return false;
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M04_IndicatorPool.mqh>
#include <MQL5Kit/M06_Signal.mqh>

CIndicatorPool ind;
CSignal S;   // 静态类，不需要实例化

int OnInit() {
   ind.AddEMA("MA_Fast", 12);
   ind.AddEMA("MA_Slow", 26);
   ind.AddRSI("RSI", 14);
   return INIT_SUCCEEDED;
}

void OnTick() {
   // 拿最近两根的指标值
   double fast[2], slow[2], rsi[2];
   ind.Values("MA_Fast", fast, 2);
   ind.Values("MA_Slow", slow, 2);
   ind.Values("RSI",     rsi,  2);

   // 金叉 + RSI 不在超买 = 做多
   if (S.CrossUpSeries(fast, slow) && !S.IsOverbought(rsi[0], 70)) {
      // 开多
   }
   // 死叉 + RSI 不在超卖 = 做空
   if (S.CrossDownSeries(fast, slow) && !S.IsOversold(rsi[0], 30)) {
      // 开空
   }
}
```

## 进阶：组合信号

```mql5
bool cond[3];
cond[0] = S.CrossUpSeries(fast, slow);
cond[1] = S.IsOversold(rsi[0], 40);
cond[2] = macdHist > 0;
if (S.AllOf(3, cond)) {
   // 三个条件都满足
}
```

## 必看陷阱
- `CrossUp` 必须在**两根 K 线**之间判断（`[1]` 和 `[0]`），单根判断不出"穿越"
- 突破判断用 `<=` 和 `>`，**不能用 `==`**，价格几乎不可能正好等于水平
- RSI 阈值（70/30）只是参考，强势趋势可以放宽到 80/20
- MACD 死叉/金叉建议用 `MACDHistogramTurnUp/Down` 而不是直接比较 main 和 signal 的相对位置

---

## 实战案例

- **TrendMA_EA.mq5 MA 交叉信号**（接入点：line 14 `M06_Signal.mqh` include / line 52 `CNewBar NB` M05 节流 / line 91-103 OnTick / line 107 `CSignal::CrossUpSeries` / line 111 `CrossDownSeries` CheckEntry / line 119+124 CheckExit 反向交叉平仓）
  - 关键 API：`CSignal::CrossUpSeries(double &fast[], double &slow[])` / `CrossDownSeries` / `CrossUp(prevFast, prevSlow, curFast, curSlow)` / `BreakUp(cur, prev, level)` / `IsOverbought(rsi, 70)` / `AllOf(n, cond[])`
  - 调优：MA_Fast=12 / MA_Slow=26 / `MA_Method=MODE_EMA` 是中周期趋势 EA 标准配置（input line 26-28）；`_fastArr[3]` / `_slowArr[3]` 必须 `SetAsSeries(true)` 后 `ind.Values(name, arr, 3)` 拿 3 根（line 62+98-99）
  - 链向：[[02-完整模板/EA 趋势跟踪模板 (MA 交叉)]] / [[实战/BBTrendEA 复活 SOP]]（line 58-70 4 周期 MA 趋势 + 6 个 iMA 句柄）/ [[实战/ScalperXAU 接入报告 + v1→v4 演进史]]（v1 BB+RSI+MA 均值回归 v3+v4 演进）
