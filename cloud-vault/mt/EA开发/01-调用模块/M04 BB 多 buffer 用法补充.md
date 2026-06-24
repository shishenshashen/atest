---
title: M04 指标池 BB 多 buffer 用法补充
tags: [M04, 指标, BB, 沉淀, 库文档]
type: reference
---

# M04 指标池 BB 多 buffer 用法补充

> **核心问题**: 库里 `EA 逆势均值回归模板` 用 `ind.MACDValue("BB", 1, 0)` 拿 BB upper band,
> 这是 **错的 API** — `MACDValue` 是给 MACD 用的 (拿 MACD 主/信号/差值),
> BB 是 3-buffer 指标, 正确拿法是直接 `CopyBuffer(handle, 1, 0, count, arr)`。

## 库里的现状

`EA开发/01-调用模块/M04 指标句柄管理 IndicatorPool.md` 描述:
- `ind.Value(name, bar)` - 拿主 buffer
- `ind.MACDValue(name, buffer, bar)` - 拿 MACD 多 buffer

**但 BB 实际是 3-buffer 指标** (BASE_LINE=0, UPPER_BAND=1, LOWER_BAND=2), 用 `MACDValue` 拿 BB 是 API 误用。

## 库模板的错 (在 `EA 逆势均值回归模板（RSI Bollinger）.md`)

```mql5
// ❌ 错: MACDValue 是给 MACD 用的
double bbUpper = ind.MACDValue("BB", 1, 0);   // buffer 1 = upper?
double bbLower = ind.MACDValue("BB", 2, 0);   // buffer 2 = lower?
double bbMid   = ind.MACDValue("BB", 0, 0);   // buffer 0 = middle?
```

这个写法可能能跑 (因为 iBands 碰巧 buffer 顺序对), 但**语义错了**,
未来 M04 API 改了就坏。

## 正确写法 (ScalperXAU v3 用)

```mql5
// 1. 创建 handle (在 OnInit)
g_hBands = iBands(_Symbol, _Period, InpBbPeriod, 0, InpBbDeviation, PRICE_CLOSE);

// 2. 直接 CopyBuffer (不用 M04 中转, 走 MT5 原生 API)
bool GetBands(double &upper[], double &middle[], double &lower[], int count) {
   ArraySetAsSeries(upper,  true);
   ArraySetAsSeries(middle, true);
   ArraySetAsSeries(lower,  true);
   if (CopyBuffer(g_hBands, 0, 0, count, middle) <= 0) return false;  // 0 = BASE_LINE
   if (CopyBuffer(g_hBands, 1, 0, count, upper)  <= 0) return false;  // 1 = UPPER_BAND
   if (CopyBuffer(g_hBands, 2, 0, count, lower)  <= 0) return false;  // 2 = LOWER_BAND
   return true;
}
```

## 多 buffer 指标 → CopyBuffer 映射

| 指标 | 0 buffer | 1 buffer | 2 buffer |
|------|----------|----------|----------|
| **iBands** (BB) | BASE_LINE (中轨) | UPPER_BAND (上轨) | LOWER_BAND (下轨) |
| **iMACD** | MAIN_LINE (MACD) | SIGNAL_LINE (Signal) | HISTOGRAM (柱) |
| **iStochastic** | MAIN_LINE (%K) | SIGNAL_LINE (%D) | - |
| **iADX** | MAIN_LINE (ADX) | PLUSDI_LINE (+DI) | MINUSDI_LINE (-DI) |
| **iIchimoku** | TENKANSEN | KIJUNSEN | SENKOUSPANA / B |
| **iAlligator** | GATORJAW | GATORTEETH | GATORLIPS |

## 建议

1. **写新 EA**: 跳过 M04 池化, 直接 `iBands` + `CopyBuffer` 拿, 简单直接
2. **维护 M04 库**: 加 `ind.BandsValue(name, buffer, bar)` 方法, 替代错的 `MACDValue` 拿 BB
3. **改库模板**: 把 `EA 逆势均值回归模板` 里 `MACDValue("BB", ...)` 改成 `CopyBuffer(handle, ...)` 模式

## 通用经验

- M04 池化适合: 单 buffer 指标 (MA/EMA/RSI/ATR 等), `ind.Value("RSI", 0)` 一行拿
- M04 池化**不**适合: 多 buffer 指标 (BB/MACD/Stochastic/ADX), 直接走 `CopyBuffer` 更清楚
- 库 API 命名要带指标类型 (`BandsValue` / `MACDValue` / `StochValue`) 不能用 MACDValue 通用
