---
title: M04 指标句柄管理 IndicatorPool
tags: [调用模块, 指标]
type: module
---

# M04 指标句柄管理 IndicatorPool

> **作用**：把所有 `iMA/iRSI/iATR/iMACD/iBands/iStochastic` 句柄集中管理，按需获取。
> **坑**：指标句柄全局缓存，避免每次 OnTick 都 `iMA(...)` 创建新句柄导致 MT5 卡死。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                        M04_IndicatorPool.mqh      |
//|                              EA 开发知识库 - 指标句柄池            |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 指标句柄池                                                        |
//| - OnInit 调 Add() 一次                                          |
//| - OnTick 调 Get(名称) 拿句柄 + 用 CopyBuffer 取数                |
//| - OnDeinit 调 ReleaseAll()                                       |
//+------------------------------------------------------------------+
class CIndicatorPool {
private:
   struct IndItem {
      string  name;       // 句柄名字（自己取，便于查找）
      int     handle;     // iMA/iRSI/iATR 返回的句柄
      int     bufferNum;  // 第几个 buffer（MACD 有 3 个）
   };
   IndItem _items[];
   int     _count;

   // 找句柄
   int _Find(string name) {
      for (int i = 0; i < _count; i++)
         if (_items[i].name == name) return i;
      return -1;
   }

public:
   CIndicatorPool() : _count(0) {}

   //+--- 添加 MA 句柄 ------------------------------------------------+
   //  name: 内部名字，比如 "MA20"
   //  period: 平均周期
   //  method: MODE_SMA / MODE_EMA / MODE_SMMA / MODE_LWMA
   //  applied: PRICE_CLOSE / OPEN / HIGH / LOW / MEDIAN / TYPICAL / WEIGHTED
   int AddMA(string name, int period, int method = MODE_SMA,
             int applied = PRICE_CLOSE, int shift = 0) {
      int h = iMA(_Symbol, _Period, period, shift, method, applied);
      return _Add(name, h, 0);
   }

   //+--- 添加 EMA（常用快速 MA）--------------------------------------+
   int AddEMA(string name, int period, int applied = PRICE_CLOSE) {
      return AddMA(name, period, MODE_EMA, applied);
   }

   //+--- 添加 RSI 句柄 -----------------------------------------------+
   int AddRSI(string name, int period, int applied = PRICE_CLOSE) {
      int h = iRSI(_Symbol, _Period, period, applied);
      return _Add(name, h, 0);
   }

   //+--- 添加 ATR 句柄（止损计算必用）--------------------------------+
   int AddATR(string name, int period) {
      int h = iATR(_Symbol, _Period, period);
      return _Add(name, h, 0);
   }

   //+--- 添加 MACD 句柄 ---------------------------------------------+
   //  bufferNum: 0=MAIN, 1=SIGNAL
   int AddMACD(string name, int fast, int slow, int signal, int applied=PRICE_CLOSE) {
      int h = iMACD(_Symbol, _Period, fast, slow, signal, applied);
      return _Add(name, h, 0);  // 用 0 和 1 buffer
   }

   //+--- 添加 Bollinger Bands ---------------------------------------+
   //  bufferNum: 0=BASE, 1=UPPER, 2=LOWER
   int AddBands(string name, int period, double deviation, int applied=PRICE_CLOSE) {
      int h = iBands(_Symbol, _Period, period, 0, deviation, applied);
      return _Add(name, h, 0);
   }

   //+--- 添加 Stochastic --------------------------------------------+
   //  bufferNum: 0=MAIN, 1=SIGNAL
   int AddStoch(string name, int k, int d, int slowing, int method=MODE_SMA) {
      int h = iStochastic(_Symbol, _Period, k, d, slowing, method, STO_LOWHIGH);
      return _Add(name, h, 0);
   }

   //+--- 添加 ADX（趋势强度）----------------------------------------+
   //  bufferNum: 0=MAIN, 1=PLUSDI, 2=MINUSDI
   int AddADX(string name, int period) {
      int h = iADX(_Symbol, _Period, period);
      return _Add(name, h, 0);
   }

   //+--- 添加自定义指标（已编译 ex5）---------------------------------+
   int AddCustom(string name, string indName, int bufferNum = 0) {
      int h = iCustom(_Symbol, _Period, indName);
      return _Add(name, h, bufferNum);
   }

   //+--- 拿句柄 ------------------------------------------------------+
   int Get(string name) {
      int idx = _Find(name);
      return (idx >= 0) ? _items[idx].handle : INVALID_HANDLE;
   }

   //+--- 取最近一根的值（最常用）-------------------------------------+
   double Value(string name, int shift = 0) {
      int h = Get(name);
      if (h == INVALID_HANDLE) return EMPTY_VALUE;
      double buf[];
      ArraySetAsSeries(buf, true);
      if (CopyBuffer(h, 0, 0, shift + 1, buf) <= 0) return EMPTY_VALUE;
      return buf[shift];
   }

   //+--- 取多根 ------------------------------------------------------+
   int Values(string name, double &buf[], int count) {
      int h = Get(name);
      if (h == INVALID_HANDLE) return 0;
      ArraySetAsSeries(buf, true);
      return CopyBuffer(h, 0, 0, count, buf);
   }

   //+--- 取 MACD 的 main 或 signal -----------------------------------+
   double MACDValue(string name, int mainOrSignal /*0 or 1*/, int shift = 0) {
      int h = Get(name);
      if (h == INVALID_HANDLE) return EMPTY_VALUE;
      double buf[];
      ArraySetAsSeries(buf, true);
      if (CopyBuffer(h, mainOrSignal, 0, shift + 1, buf) <= 0) return EMPTY_VALUE;
      return buf[shift];
   }

   //+--- 释放所有句柄 -----------------------------------------------+
   void ReleaseAll() {
      for (int i = 0; i < _count; i++)
         if (_items[i].handle != INVALID_HANDLE)
            IndicatorRelease(_items[i].handle);
      _count = 0;
      ArrayResize(_items, 0);
   }

private:
   int _Add(string name, int h, int bufNum) {
      if (h == INVALID_HANDLE) {
         Print("指标句柄创建失败：", name);
         return INVALID_HANDLE;
      }
      int idx = _Find(name);
      if (idx >= 0) {                       // 已存在 → 替换
         IndicatorRelease(_items[idx].handle);
         _items[idx].handle   = h;
         _items[idx].bufferNum = bufNum;
         return h;
      }
      _count++;
      ArrayResize(_items, _count);
      _items[_count-1].name      = name;
      _items[_count-1].handle    = h;
      _items[_count-1].bufferNum = bufNum;
      return h;
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M04_IndicatorPool.mqh>

CIndicatorPool ind;

input int FastMA = 12;
input int SlowMA = 26;
input int RSI_Period = 14;
input int ATR_Period = 14;

int OnInit() {
   ind.AddMA("MA_Fast", FastMA, MODE_EMA);
   ind.AddMA("MA_Slow", SlowMA, MODE_EMA);
   ind.AddRSI("RSI", RSI_Period);
   ind.AddATR("ATR", ATR_Period);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   ind.ReleaseAll();   // 必调
}

void OnTick() {
   // 拿最近值
   double maFast  = ind.Value("MA_Fast");
   double maSlow  = ind.Value("MA_Slow");
   double rsi     = ind.Value("RSI");
   double atr     = ind.Value("ATR", 1);  // 上一根已关闭的 ATR

   // 拿数组
   double maFastArr[20];
   int n = ind.Values("MA_Fast", maFastArr, 20);

   // 算动态止损 = 1.5 × ATR
   double slDist = 1.5 * atr;
   Print("MA Fast=", maFast, " Slow=", maSlow,
         " RSI=", rsi, " ATR(1)=", atr);
}
```

## 必看陷阱
- **每次 OnTick 都 iMA() 会让 MT5 内存爆炸** → 用本模块
- **OnDeinit 必须 ReleaseAll**，否则换时间框架后会留垃圾
- `EMPTY_VALUE`（DBL_MAX）表示该指标无值，**永远检查**
- 某些经纪商的历史数据 < 1000 根时 `CopyBuffer` 会失败
- 同一指标的多个周期（如 M5 和 H1）要分别建句柄

---

## 实战案例

> **本节汇总 M04 IndicatorPool 在真实 EA 场景的接入经验和完整代码模板**。
> spec wiki (上面) 讲 API + 理论；本节讲"已经跑通的 4 指标组合 + ScalperXAU 绕过 M04 走裸句柄的范本 + 反模式"。

### 实战摘要（点开 wiki 前先看这段）

- **场景 A MeanReversion_EA.mq5 4 指标组合**（320 行，13 模块集成）：M04 `ind` 实例管 4 个指标（RSI/BB/ADX/ATR），OnInit line 84-87 一次性 `AddRSI/AddBands/AddADX/AddATR`；OnTick line 148-151 拉 4 指标值用 `ind.Value/ind.MACDValue`（注意 BB 用 `MACDValue` 因为 BB 有 3 buffer 跟 MACD 同结构）。
- **场景 B ScalperXAU.mq5 4 指标用裸 iBands/iRSI/iATR/iADX 绕过 M04**（1032 行）：**include + object 都声明了**（line 22/110）但**实际用 4 个裸句柄**（line 135-138 `g_hBands/g_hRsi/g_hAtr/g_hAdx`）—— OnInit line 970-973 走 `iBands/iRSI/iATR/iADX`，OnTick line 492-515 走 `GetBands/GetRsi/GetAtr/GetAdxMain` 拉 buffer；`ind.ReleaseAll()` 在 OnDeinit line 1020 是空跑（pool 里啥也没有）。
- **即抄代码**：`ind.AddRSI(name, period)` + `ind.Value(name, shift)` 一行拿一个值；M04 句柄全局缓存，不会每 tick 重建。
- **5+ 已知陷阱**：`ind.Value` 永远检查 `EMPTY_VALUE`（DBL_MAX） / `AddBands` 只能从 buffer 0 拿（base/upper/lower 要走 `MACDValue` hack） / 同一指标多周期（M5+H1）要建多个句柄 / `OnDeinit` 漏 `ReleaseAll` 换 TF 后会泄漏 / 1000 根以下 broker 拉 buffer 失败。
- **5 条反模式**：每 tick 调 `iMA()` 重建句柄 / `ind` 声明在 OnTick 里（每次重建 pool 句柄全丢） / 多 buffer 指标硬塞 `ind.Value` 拿 / `AddBands` 后用 `ind.Value("BB")` 拿 base/upper/lower 三个值 / OnDeinit 不 `ReleaseAll`（换 TF 泄漏）。

### 实物 demo EA 接入（4 指标组合）

**`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`**（320 行，13 模块集成，多品种均值回归）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 12** `#include <MQL5Kit/M04_IndicatorPool.mqh>`
- **line 57** `CIndicatorPool ind;` 全局对象（与 M01 trade / M02 risk / M03 sizing / M05 NB / M08 trail 同一区声明，54-64 行）
- **line 84-87** `ind.AddRSI/AddBands/AddADX/AddATR` — OnInit 内一行一个
  ```mql5
  ind.AddRSI("RSI", RSI_Period);            // line 84
  ind.AddBands("BB", BB_Period, BB_Deviation);  // line 85
  ind.AddADX("ADX", 14);                    // line 86
  ind.AddATR("ATR", ATR_Period);            // line 87 (M04.iATR(14) — M08 阈值用)
  ```
- **line 148-151** `ind.Value/ind.MACDValue` — OnTick 新 K 线分支
  ```mql5
  double rsi     = ind.Value("RSI", 0);     // line 148 buffer 0
  double bbUpper = ind.MACDValue("BB", 1, 0);  // line 149 buffer 1 (upper)
  double bbLower = ind.MACDValue("BB", 2, 0);  // line 150 buffer 2 (lower)
  double bbMid   = ind.MACDValue("BB", 0, 0);  // line 151 buffer 0 (base/middle)
  ```

**关键设计**：BB 用 `ind.MACDValue` 是 M04 的"权宜之计"——spec 的 `Value/Values` 方法只支持 `buffer 0`（spec line 116-131），但 BB 有 3 个 buffer（base/upper/lower）。`MACDValue` 方法（spec line 134-141）原本是给 MACD 设计的（buffer 0/1 是 main/signal），但 BB 复用同一个 `CopyBuffer(h, bufferNum, ...)` 接口，**所以 `ind.MACDValue("BB", 1, 0)` 实测能拿 BB upper**。这是 M04 spec 的 API 复用范本。

**EMPTY_VALUE 检查**（line 153）：`if (rsi == EMPTY_VALUE || bbMid == EMPTY_VALUE) return;` —— 任何指标 buffer 拿不到值（broker 数据不足 / 指标未就绪）直接 return 跳过本 K 线。**这是 M04 spec 必看陷阱 line 222 的实战对应**。

**多 TF 场景**（spec line 82-100）：单 EA 多周期必须在 `CIndicatorPool` 内部开多个实例（每个 TF 一个 handle）：
```mql5
CIndicatorPool indM5, indH1;   // 两个 pool, 各自持 M5/H1 句柄
indM5.AddMA("MA_M5", 20, MODE_EMA);
indH1.AddMA("MA_H1", 50, MODE_EMA);
```

### 实物 demo EA 接入（绕过 M04 走裸句柄）

**`MQL5/Experts/minimax-ea/ScalperXAU.mq5`**（1032 行，13 模块集成，剥头皮 XAUUSDm M1）— 已落地，0 errors 编译。

接入点（5 处，**3 处是"绕过 M04"**）：
- **line 22** `#include <MQL5Kit/M04_IndicatorPool.mqh>` — include 仍然保留
- **line 110** `CIndicatorPool ind;` — 全局对象**仍然声明**（但池子是空的）
- **line 135-138** `int g_hBands = INVALID_HANDLE; int g_hRsi = INVALID_HANDLE; int g_hAtr = INVALID_HANDLE; int g_hAdx = INVALID_HANDLE;` — 4 个**裸句柄**（NOT M04）
- **line 970-973** OnInit 内 `g_hBands = iBands(_Symbol, _Period, InpBbPeriod, 0, InpBbDeviation, PRICE_CLOSE);` 4 行裸 iBands/iRSI/iATR/iADX
- **line 492-515** `GetBands/GetRsi/GetAtr/GetAdxMain` 函数 — 4 个辅助函数，**手工 `ArraySetAsSeries` + `CopyBuffer(g_hXxx, bufferNum, 0, count, ...)`**
- **line 1020** `ind.ReleaseAll();` — OnDeinit 内，**但 ind 池是空的**（从没 AddXxx）—— 是"空跑"

**关键设计**（绕过 M04 的原因）：
- BB 有 **3 buffer**（base/upper/lower），M04 的 `Value()` 只支持 buffer 0（spec line 116-123）—— **要拿 upper/lower 必须用 `MACDValue` hack**（如 MeanReversion line 149-151）
- ADX 有 **3 buffer**（main/+DI/-DI），spec 的 `AddADX` 只填 bufferNum=0（spec line 99）—— **+DI/-DI 拿不到**
- ScalperXAU v3 需要 ADX **2 个 buffer**（main + spread 监控），如果走 M04 只能拿 main，**+DI/-DI 走 `MACDValue("ADX", 1/2, 0)` hack 又跟 BB 的 3 buffer hack 冲突**（同 `MACDValue` 入口）

**作者选择**（v3 升级 v2 时）：**绕过 M04，直接用 4 个裸句柄**。ScalperXAU 是"剥头皮高频 debug log 协议"（v4 加的），需要稳定拿多 buffer + 不依赖 M04 的 buffer 0-only 限制。

**M04 适合 / 不适合**：
- ✅ **适合**：单 buffer 指标（MA / RSI / ATR / MACD main 0,1）—— 加 pool 一行拿值
- ❌ **不适合**：3 buffer 指标（BB / ADX）需要稳定拿多个 buffer —— 走裸句柄更直接

### 即抄代码（OnInit + OnTick 接入骨架）

```mql5
// 1) include
#include <MQL5Kit/M04_IndicatorPool.mqh>

// 2) 全局
CIndicatorPool ind;

int OnInit() {
   ind.AddMA("MA_Fast", 12, MODE_EMA);
   ind.AddMA("MA_Slow", 26, MODE_EMA);
   ind.AddRSI("RSI", 14);
   ind.AddATR("ATR", 14);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   ind.ReleaseAll();   // 必调, 否则换 TF 泄漏
}

void OnTick() {
   // 拿最近值
   double maFast = ind.Value("MA_Fast");
   double rsi    = ind.Value("RSI");
   if (maFast == EMPTY_VALUE || rsi == EMPTY_VALUE) return;   // ★ 必查
   
   // 拿多根
   double maFastArr[20];
   int n = ind.Values("MA_Fast", maFastArr, 20);
   
   // 算动态止损 = 1.5 × ATR
   double atr = ind.Value("ATR", 1);  // 上一根已关闭的 ATR
   double slDist = 1.5 * atr;
}
```

### 实战陷阱（5+ 来自实物 EA）

1. **`ind.Value` 永远检查 `EMPTY_VALUE`（DBL_MAX）** — spec line 222。MeanReversion line 153 `if (rsi == EMPTY_VALUE || bbMid == EMPTY_VALUE) return;` 是正确范本。**漏检查 EMPTY_VALUE = 浮点比较 1.7976931348623e+308**（几乎所有 < / > 都 true），下游 `if (rsi > 70)` 永远 true 或永远 false，EA 行为完全错乱。
2. **`AddBands` 后用 `ind.Value("BB")` 拿 base/upper/lower 三个值是错的** — spec line 116-123 的 `Value()` 只支持 buffer 0。**必须用 `ind.MACDValue("BB", 0/1/2, 0)` 拿 3 个 buffer**（MeanReversion line 149-151）。**命名误导**（`MACDValue` 不止给 MACD 用）。
3. **同一指标多周期（M5 + H1）必须建多个句柄** — spec line 82-100 的范本。**M04 的 `AddMA("MA", 20)` 默认用 `_Period`**，如果要在 M5 chart 拿 H1 数据，必须 `indH1.AddMA("MA", 20)` + `ArraySetAsSeries` 配合 `CopyBuffer`。**单 `ind` 实例不能跨 TF**。
4. **OnDeinit 漏 `ReleaseAll` 换 TF 后会留垃圾** — spec line 220。`OnDeinit(const int reason)` **不写 ind.ReleaseAll()** 第一次编译能过，**但**用户把 chart TF 从 H1 切到 H4 时，MT5 会重新 init EA，**老的 `ind` 句柄仍占用**（MT5 不会自动清理非托管句柄），多次切换后内存累积 → `CopyBuffer` 返 -1 → EA 行为错乱。
5. **1000 根以下 broker 拉 buffer 失败** — spec line 222。剥头皮 M1 1 年数据 = 35000+ 根，远超 1000；但**回测在"每个报价基于真实报价"模式 1 周数据**可能 < 1000 根（取决于 broker 历史），`CopyBuffer` 返 0（不是 -1），`Value()` 返 `EMPTY_VALUE` → 必须按 EMPTY_VALUE 处理（陷阱 1）。
6. **`AddADX` 拿 +DI/-DI 走 `MACDValue` hack** — spec line 99 `AddADX` 只填 bufferNum=0（MAIN）。拿 +DI 用 `ind.MACDValue("ADX", 1, 0)`，拿 -DI 用 `ind.MACDValue("ADX", 2, 0)`。ScalperXAU v3 不走 M04 是因为 ADX 多 buffer 跟 BB 多 buffer 在 `MACDValue` 入口冲突。

### 反模式（5 条禁止）

1. **每 tick 调 `iMA()` 重建句柄** — spec line 219 + 必看陷阱 1。**MT5 内部 iMA 句柄是 per-chart 缓存**，但每次调用都过桥到 indicator subsystem。剥头皮一秒 5 tick × 5 指标 = 25 次过桥/秒。**用 M04 缓存 = 1 次创建 + 永久复用**。
2. **`ind` 声明在 OnTick 里** — 每次 tick 重建对象，pool 里所有句柄丢失。下一行 `ind.Value("MA_Fast")` 找句柄失败返 `EMPTY_VALUE` → 行为错乱。**`ind` 必须是 per-EA 全局**（与 trade / risk 同生命周期）。
3. **多 buffer 指标硬塞 `ind.Value` 拿** — `ind.Value("BB")` 只能拿 buffer 0（base/middle），拿不到 upper/lower。**必须用 `ind.MACDValue("BB", 1, 0)`**。**反例**：`if (close > ind.Value("BB"))` 实际是 `close > middle`，不是 `close > upper`（line 122 `Value` buffer 0）。
4. **`AddBands` 后用 `ind.Value("BB")` 拿 base/upper/lower 三个值是错的** — 同陷阱 2 / 反模式 3 合并。**实测**：MeanReversion line 149-151 全用 `ind.MACDValue`，**没有**用 `ind.Value` 拿 BB。
5. **OnDeinit 不 `ReleaseAll`** — spec line 220。换 TF 泄漏。**编译能过，行为错乱，debug 难**（不会 crash，内存慢慢涨）。**必加**：`void OnDeinit(const int reason) { ind.ReleaseAll(); }`。

### 链向（待 T3 写 wiki）

- **[[实战/MeanReversion_EA wiki]]** — MeanReversion_EA.mq5 13 模块接入完整实战（M04 4 指标组合 / `MACDValue` hack 拿 BB 3 buffer / EMPTY_VALUE 检查）
- **[[实战/ScalperXAU wiki]]** — ScalperXAU.mq5 13 模块接入完整实战（**绕过 M04 走裸 iBands/iRSI/iATR/iADX** / ADX 多 buffer 限制 / `ind.ReleaseAll()` 空跑）
- **[[M05 新 K 线检测 NewBar]]** — `ind.Values` 在 NewBar guard 之后调（节省 tick 算力）
- **[[M08 追踪止损 TrailingStop]]** — `ind.Value("ATR", 0)` 每 tick 重算 trail.SetParams（MeanReversion `_UpdateTrailParams` line 213-228）
- **[[10 件事 §10]]** — 别在 OnTick 里重计算（M05 NewBar + M04 句柄是组合方案）
- **[[10 件事 §4]]** — 倒序数组的坑（`ArraySetAsSeries(buf, true)` 必须先调）

### 反向引用（实物 EA 接入 demo）

> **本节是 T1 18:00 任务（TrendMA_EA + Breakout_EA 联合 wiki v2）落地的反链**，由 [[实战/TrendMA_EA + Breakout_EA 接入报告]] §4.1 反链表 + §4.2 双向链接段添加。

- **[[实战/TrendMA_EA + Breakout_EA 接入报告]]** — TrendMA + Breakout 2 EA 联合接入报告（**v2 修正版 / 12+11 模块**）：TrendMA `ind.AddMA("MA_Fast", 12, MODE_EMA)` L69 + `ind.AddMA("MA_Slow", 26, MODE_EMA)` L70（**2 MA 范本**——单 buffer 用 `M04.Values` 拉 buffer 0, BB 3 buffer 不需要）；Breakout `ind.AddBands("Donchian_Hi", 20, 2.0)` L73 + `ind.AddBands("Donchian_Lo", 20, 2.0)` L74 + `ind.AddEMA("HTF_EMA", 50)` L75 + `if (UseADXFilter) ind.AddADX("ADX", 14)` L76（**4 指标范本**——2 AddBands for Donchian visualization + 1 AddEMA for HTF trend + 1 AddADX for trend strength, **ADX 用 AddADX 不是 AddRSI**）。
- **本 wiki 实战段 5+ 陷阱对应**：2 EA 共享陷阱 1（EMPTY_VALUE 检查 = 必查, Breakout L118 `if (htfEMA == EMPTY_VALUE) return;` 是范本）+ 陷阱 4（OnDeinit `ind.ReleaseAll` 已用, TrendMA L86 + Breakout L90）；TrendMA 2 MA 单 buffer 用 `M04.Values` 即可（**避开陷阱 3 命名误导**）；Breakout ADX 用专用 `AddADX` 完整（**避开陷阱 5 ADX +DI/-DI hack**, 本 EA ADX 只用 main）。
- **风格对比**：2 EA 跟 MeanReversion 4 指标组合对比——MeanReversion 用 `ind.MACDValue` hack 拿 BB 3 buffer（line 149-151），**本 2 EA 没 BB 不需要 hack**（更简单）。ScalperXAU 绕过 M04 走裸句柄（line 135-138），**本 2 EA 走标准 M04 池化**（更标准）。
- **v1 → v2 关键修正**：v1 wiki 错写 Breakout 用 `AddMA/AddEMA/AddRSI/AddATR`（`AddRSI("ADX", 14)` 是误导性 API），v2 实测为 `AddBands x 2 + AddEMA + AddADX`（**v2 修正: 实物 0 改动, wiki 0 编造**）。
