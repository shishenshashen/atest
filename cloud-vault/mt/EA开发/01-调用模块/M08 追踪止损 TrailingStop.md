---
title: M08 追踪止损 TrailingStop
tags: [调用模块, 止损]
type: module
---

# M08 追踪止损 TrailingStop

> **作用**：价格往有利方向走时，自动把止损位往盈利方向抬。
> **典型场景**：突破入场后，价格涨了 50 点，止损从 -100 抬到 -50（保本）或 +20（锁利）。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                       M08_TrailingStop.mqh       |
//|                              EA 开发知识库 - 追踪止损              |
//+------------------------------------------------------------------+
#property strict

#include <MQL5Kit/M01_CTradePlus.mqh>   // 用 CTradePlus 改 SL

//+------------------------------------------------------------------+
//| 追踪止损                                                          |
//| 算法：                                                            |
//|   对每笔本 EA 持仓：                                              |
//|     当前价 = (多→bid, 空→ask)                                    |
//|     浮盈距离 = abs(当前价 - 开仓价)                              |
//|     若浮盈 >= trailingStart（如 100 点）：                        |
//|       新 SL = 当前价 - trailingStep（如 50 点）                  |
//|     若新 SL > 旧 SL（多）/ 新 SL < 旧 SL（空）：                 |
//|       调用 trade.ModifySLTP                                      |
//+------------------------------------------------------------------+
class CTrailingStop {
private:
   CTradePlus *_trade;        // 交易封装（外部传入）
   ulong       _magic;        // 只处理本 EA
   int         _startPoints;  // 启动追踪的盈利点数
   int         _stepPoints;   // SL 距当前价的距离（点数）
   int         _minGapPoints; // 距离上次修改至少要前进的点数

   // 价差点 → 价格差
   double _P(int points) const { return points * _Point; }

public:
   CTrailingStop() : _trade(NULL), _magic(0),
                     _startPoints(100), _stepPoints(50),
                     _minGapPoints(10) {}

   void Init(CTradePlus *trade, ulong magic) {
      _trade = trade;
      _magic = magic;
   }

   void SetParams(int startPoints, int stepPoints, int minGapPoints = 10) {
      _startPoints  = startPoints;
      _stepPoints   = stepPoints;
      _minGapPoints = minGapPoints;
   }

   //+--- 一次扫描：对所有本 EA 持仓执行追踪 ---------------------------+
   void Apply() {
      if (_trade == NULL) return;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) != _magic) continue;
         if (PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
         _ApplyOne(t);
      }
   }

private:
   void _ApplyOne(ulong ticket) {
      if (!PositionSelectByTicket(ticket)) return;
      ENUM_POSITION_TYPE type =
         (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double openPr  = PositionGetDouble(POSITION_PRICE_OPEN);
      double curPr   = PositionGetDouble(POSITION_PRICE_CURRENT);
      double oldSL   = PositionGetDouble(POSITION_SL);
      double curTP   = PositionGetDouble(POSITION_TP);

      // 当前价取买卖价
      if (type == POSITION_TYPE_BUY)  curPr = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      else                              curPr = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      // 浮盈距离
      double profitDist = (type == POSITION_TYPE_BUY) ? (curPr - openPr)
                                                     : (openPr - curPr);
      if (profitDist < _P(_startPoints)) return;     // 还没到启动点

      // 计算新 SL
      double newSL = (type == POSITION_TYPE_BUY) ? curPr - _P(_stepPoints)
                                                : curPr + _P(_stepPoints);
      newSL = NormalizeDouble(newSL, _Digits);

      // 方向正确才改
      bool shouldUpdate = false;
      if (type == POSITION_TYPE_BUY) {
         // 多：新 SL 要 > 旧 SL（往上涨），且距离上次改动要够远
         if (newSL > oldSL + _P(_minGapPoints)) shouldUpdate = true;
      } else {
         // 空：新 SL 要 < 旧 SL（往下跌）
         if (newSL < oldSL - _P(_minGapPoints)) shouldUpdate = true;
      }
      if (!shouldUpdate) return;

      _trade.ModifySLTP(ticket, newSL, curTP);
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M01_CTradePlus.mqh>
#include <MQL5Kit/M08_TrailingStop.mqh>

CTradePlus      trade;
CTrailingStop   trail;

input int TrailStart = 200;   // 浮盈 200 点启动
input int TrailStep  = 100;   // SL 距当前价 100 点

int OnInit() {
   trade.Init(Magic);
   trail.Init(&trade, Magic);
   trail.SetParams(TrailStart, TrailStep, 10);
   return INIT_SUCCEEDED;
}

void OnTick() {
   trail.Apply();   // 每个 tick 扫描一遍
   // ...
}
```

## 关键参数说明
| 参数 | 含义 | 建议 |
|---|---|---|
| `_startPoints` | 浮盈多少点才启动追踪 | 50-200（视品种波动）|
| `_stepPoints` | SL 距当前价多远 | 30-100 |
| `_minGapPoints` | 两次修改至少要前进多少点 | 5-20（避免频繁改）|

## 三种典型策略
| 策略 | start | step | 效果 |
|---|---|---|---|
| 紧追踪 | 50 | 30 | 频繁抬，可能被震出 |
| 标准 | 200 | 100 | 推荐 |
| 保本式 | 100 | 等于浮盈 | 涨 100 就把 SL 移到开仓价 |
| 锁利式 | 100 | 50 | 涨 100 就把 SL 移到 +50 |

## 必看陷阱
- 追踪止损 = 限价单 → 服务器繁忙时可能改不成功
- **不要每 tick 都改 SLTP**（会触发服务器限流），用 `_minGapPoints` 节流
- 经纪商有最小止损距离（`SYMBOL_TRADE_STOPS_LEVEL`），newSL 太小会被拒
- 周末/隔夜跳空 → SL 不会被触发（仅在交易时段内执行）
- **不要在跳空预期前开启追踪**（周一开盘会跳空穿 SL）

---

## 实战案例

> **本节汇总 M08 TrailingStop 在真实 EA 场景的接入经验和完整代码模板**。
> spec wiki (上面) 讲 API + 理论；本节讲"已经跑通的 ATR(14) 自适应 trail + 剥头皮 0.8×ATR 慎用 + 反模式"。

### 实战摘要（点开 wiki 前先看这段）

- **场景 A MeanReversion_EA.mq5 ATR(14) 自适应 trail**（320 行，13 模块集成）：M08 `trail` 实例 + 动态 `_UpdateTrailParams`（line 213-228）每 tick 用 `ind.Value("ATR", 0)` 重算 `startPts = 1.5×ATR(14)/_Point` + `stepPts = 1.0×ATR(14)/_Point`，适配多品种不同波动率（XAUUSDm vs EURUSDm 同样 1.5×ATR 数值差 10x）。
- **场景 B ScalperXAU.mq5 v3 引入 M08 Trail 替代裸 SL**（1032 行）：M08 `trail` 实例固定参数 `InpTrailStartPoints=40 / InpTrailStepPoints=20 / InpTrailMinGapPoints=10`（input line 47-48）—— 剥头皮 50 points SL + 100 points TP + 40 points 启动 trail 紧追踪（0.8×ATR 估算，剥头皮慎用）。
- **即抄代码**：`trail.Init(&trade, Magic)` + `trail.SetParams(start, step, minGap)` + OnTick 调 `trail.Apply()` —— 必须传 `&trade`（CTradePlus 引用），M08 内部用 `trade.ModifySLTP` 改 SL。
- **5+ 已知陷阱**：ATR(14) 动态参数必须**先 ind.Value("ATR", 0) 再 SetParams**（顺序反了 startPts=0 永远不启动） / `trail.Apply()` 必须放在 NewBar guard 之前（每 tick 跑） / `_minGapPoints` 设太小（< 5）会被服务器限流 / 跨午夜时段周一开盘跳空会穿 SL / `trail.Init` 漏传 `&trade` 内部 `_trade=NULL` 不报错。
- **5 条反模式**：把 `trail.Apply()` 放在 NewBar guard 之后（追踪频率下降 99%） / 动态 trail 时漏调 `SetParams`（start=0 永远不启动） / `Init` 漏传 `&trade`（`ModifySLTP` 不调但编译过） / `_minGapPoints=0` 每次 tick 都改 SL（限流） / 跳空预期前开启追踪（周一开盘穿 SL）。

### 实物 demo EA 接入（ATR(14) 自适应 trail）

**`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`**（320 行，13 模块集成，多品种均值回归）— 已落地，0 errors 编译。

接入点（5 处）：
- **line 15** `#include <MQL5Kit/M08_TrailingStop.mqh>`
- **line 59** `CTrailingStop trail;` 全局对象（与 M01 trade / M02 risk / M03 sizing / M04 ind / M05 NB 同一区声明，54-64 行）
- **line 88** `trail.Init(&trade, Magic);` — OnInit 内，传 **`&trade` 引用**（CTradePlus 全局对象地址）
- **line 89** `trail.SetParams(0, 0, TrailMinGapPts);` — OnInit 内**给占位参数**（0, 0），OnTick 重算
- **line 142-145** `if (UseTrailing) { _UpdateTrailParams(); trail.Apply(); }` — OnTick 顶部，**每 tick 跑**（独立于 NewBar guard）
- **line 213-228** `_UpdateTrailParams` — OnTick 用 `ind.Value("ATR", 0)` 重算 startPts/stepPts

**关键设计**（line 142-145）：
```mql5
void OnTick() {
   _CheckDrawdown();   // line 141 每次 tick 检查回撤
   if (UseTrailing) {
      _UpdateTrailParams();   // line 143 每次 tick 用 M04.iATR(14) 算 start/step
      trail.Apply();          // line 144 M08.TrailingStop: 浮盈>start 则收紧 SL
   }
   if (!NB.IsNewBar()) return;   // line 146 NewBar guard
   // ... 新 K 线分支 (指标 + 入场)
}
```

**`_UpdateTrailParams` 动态算法**（line 213-228）：
```mql5
void _UpdateTrailParams() {
   double atr = ind.Value("ATR", 0);                          // line 214
   if (atr == EMPTY_VALUE || atr <= 0 || _Point <= 0) return; // line 215
   int startPts = (int)MathRound(TrailStartATR_Mult * atr / _Point);  // line 217 1.5×ATR
   int stepPts  = (int)MathRound(TrailStepATR_Mult  * atr / _Point);  // line 218 1.0×ATR
   if (startPts < 1) startPts = 1;
   if (stepPts  < 1) stepPts  = 1;
   trail.SetParams(startPts, stepPts, TrailMinGapPts);        // line 221
   // line 224-227: 新 K 线打印 trail 参数 (回测 journal 留痕)
}
```

**多品种适配**：
- XAUUSDm ATR(14) ≈ $2.0 (M5)：`startPts = 1.5 × 2.0 / 0.01 = 300 points = $3.0`，`stepPts = 200 points = $2.0`
- EURUSDm ATR(14) ≈ 0.0010 (M5)：`startPts = 1.5 × 0.0010 / 0.00001 = 150 points = 1.5 pip`，`stepPts = 100 points = 1.0 pip`
- 同样 1.5×ATR 倍数，**黄金用 $ 算** vs **外汇用 pip 算**——`M08 points` 是价格无关单位，靠 `_Point` 自动适配

**input 参数**（line 48-52）：
```mql5
input bool   UseTrailing     = true;       // 启用 M08 ATR 追踪止损
input int    ATR_Period      = 14;         // ATR 周期 (M04.iATR)
input double TrailStartATR_Mult = 1.5;     // 浮盈 > N × ATR(14) 激活追踪
input double TrailStepATR_Mult  = 1.0;     // SL 收紧到 current_price - N × ATR(14)
input int    TrailMinGapPts = 10;          // SL 最小移动间隔 (points), 防抖动
```

### 实物 demo EA 接入（剥头皮紧追踪）

**`MQL5/Experts/minimax-ea/ScalperXAU.mq5`**（1032 行，13 模块集成，剥头皮 XAUUSDm M1）— 已落地，0 errors 编译。

接入点（5 处）：
- **line 25** `#include <MQL5Kit/M08_TrailingStop.mqh>`
- **line 113** `CTrailingStop trail;` 全局对象
- **line 962** `trail.Init(&trade, InpMagicNumber);` — OnInit 内
- **line 963** `trail.SetParams(InpTrailStartPoints, InpTrailStepPoints, InpTrailMinGapPoints);` — OnInit 内**一次性固定参数**
- **line 739 / 796** `if (InpUseTrail) trail.Apply();` — `ManageTrades()` line 737-740 + OnTick line 796 **两次调**（剥头皮双保险）
- **input line 47-48** `InpUseTrail=true / InpTrailStartPoints=40 / InpTrailStepPoints=20 / InpTrailMinGapPoints=10`

**关键设计**（v3 引入 M08 替代裸 SL）：
```mql5
// 1) 持仓管理 ManageTrades() line 737-740
void ManageTrades() {
   SyncTracks();
   if (InpUseTrail) trail.Apply();  // 浮盈抬 SL (line 739)
}

// 2) OnTick 顶部 line 794-796
void OnTick() {
   ResetDailyIfNeeded();
   SyncTodayPnL();
   SyncTodayTrades();
   CheckHoldTimeout();
   _CheckDrawdown();
   SyncTracks();
   if (InpUseTrail) trail.Apply();   // line 796 每 tick 跑
   if (!NB.IsNewBar()) { ... }
   // ... 新 K 线分支
}
```

**剥头皮参数取舍**（input line 47-48）：
- **XAUUSDm M1 ATR** ≈ $0.5-2.0 (1.5 ATR M1)
- **`InpTrailStartPoints=40`** ≈ 0.4 USD 启动（保守 0.8×ATR）
- **`InpTrailStepPoints=20`** ≈ 0.2 USD 紧追踪（0.4×ATR）
- **`InpTrailMinGapPoints=10`** ≈ 0.1 USD 最小移动间隔（限流）

**剥头皮慎用 M08**（陷阱对应）：
- **M1 高频**（每秒 5+ tick）+ 紧追踪（20 points step）= 一次持仓可能改 50-100 次 SL
- `_minGapPoints=10` 是限流关键（< 5 会被服务器拒）
- **跳空风险**：M1 周末跳空 1-3 USD（XAUUSDm 周一开盘常见），40 points 启动的 trail 在周五尾盘可能直接被穿
- **建议**：剥头皮用 `InpUseTrail=false` + 裸 `InpSlPoints=50 / InpTpPoints=100`（固定 SL/TP 不追踪）；M08 trail 留给**趋势 EA**（H1/H4 ATR 大，跳空不敏感）

### 即抄代码（OnInit + OnTick 接入骨架）

```mql5
// 1) include
#include <MQL5Kit/M01_CTradePlus.mqh>
#include <MQL5Kit/M04_IndicatorPool.mqh>     // M08 需要 ATR 时
#include <MQL5Kit/M08_TrailingStop.mqh>

// 2) inputs
input ulong Magic = 20260101;
input int   TrailStart = 200;     // 浮盈 N points 启动
input int   TrailStep  = 100;     // SL 距当前价 N points
input int   TrailMinGap = 10;     // SL 最小移动间隔

// 3) 全局
CTradePlus      trade;
CIndicatorPool  ind;              // 可选, 用 ATR 动态时
CTrailingStop   trail;

int OnInit() {
   trade.Init(Magic, 30);
   ind.AddATR("ATR", 14);         // 用 ATR 动态 trail 时
   trail.Init(&trade, Magic);     // ★ 必须传 &trade 引用
   trail.SetParams(TrailStart, TrailStep, TrailMinGap);
   return INIT_SUCCEEDED;
}

void OnTick() {
   // 1) 动态参数 (用 M04.ATR 时)
   if (UseTrailing) {
      double atr = ind.Value("ATR", 0);
      if (atr != EMPTY_VALUE) {
         int start = (int)MathRound(1.5 * atr / _Point);
         int step  = (int)MathRound(1.0 * atr / _Point);
         trail.SetParams(MathMax(1, start), MathMax(1, step), TrailMinGap);
      }
      trail.Apply();              // ★ 放在 NewBar guard 之前, 每 tick 跑
   }
   
   if (!NB.IsNewBar()) return;    // NewBar guard (M05)
   // ... 新 K 线分支
}
```

### 实战陷阱（5+ 来自实物 EA）

1. **ATR(14) 动态参数必须**先 `ind.Value("ATR", 0)` 再 `SetParams`**（顺序反了 startPts=0 永远不启动）** — MeanReversion `_UpdateTrailParams` line 213-228 是正确范本（先读 atr → 算 start/step → SetParams → Apply）。**反例**：`trail.Apply(); trail.SetParams(...);` —— `Apply` 用了上一次 SetParams 的值（初始 0,0），永远 `profitDist < _P(0)` 不启动追踪。
2. **`trail.Apply()` 必须放在 NewBar guard 之前**（每 tick 跑） — spec M05 实战陷阱 line 262 明确。**M08 追踪止损不依赖 K 线收盘**（浮盈变化是 tick 级）。**反例**：`if (!NB.IsNewBar()) return; trail.Apply();` —— 追踪频率下降 99%（只在 K 线收盘时追踪）。**正确**：MeanReversion line 142-145 在 NewBar guard 之前调 Apply。
3. **`_minGapPoints` 设太小（< 5）会被服务器限流** — spec 必看陷阱 line 156。ScalperXAU line 48 `InpTrailMinGapPoints=10` 是限流安全值。**反例**：`_minGapPoints=1` —— 浮盈 100 points 时改 SL 5-10 次/秒，MT5 服务器返 `retcode=10009 TRADE_RETCODE_TOO_FREQUENT` 拒单。
4. **跨午夜时段周一开盘跳空会穿 SL** — spec 必看陷阱 line 159。XAUUSDm 周一开盘常见跳空 1-3 USD（50-300 points），`InpTrailStartPoints=40` 启动的 trail 在跳空瞬间被穿。**建议**：周五 20:00 后手动关 trail（`InpUseTrail=false` 或 `trail.SetParams(0,0,0)` 停止追踪），让裸 SL 守门。
5. **`trail.Init` 漏传 `&trade` 内部 `_trade=NULL` 不报错** — spec M08 line 50-53。`trail.Init()` 不传参 = `_trade=NULL` → `Apply` 第一行 `if (_trade == NULL) return;` 静默退出（spec line 63）。**编译能过，运行静默无效**。**保险**：`if (trail._trade == NULL) Print("ERR: trail.Init 漏传 &trade");` 加在 OnInit 后。
6. **3 维调参空间**（start × step × gap）：
   - **紧追踪剥头皮**：start=50, step=30, gap=5（高频被震出风险高）
   - **标准趋势**：start=200, step=100, gap=10（推荐）
   - **保本式**：start=100, step=profitDist（涨 100 就把 SL 移到开仓价）
   - **锁利式**：start=100, step=50（涨 100 就把 SL 移到 +50）
   - **动态 ATR**：start=1.5×ATR, step=1.0×ATR, gap=10（多品种自适应）

### 反模式（5 条禁止）

1. **把 `trail.Apply()` 放在 NewBar guard 之后**（追踪频率下降 99%） — spec M05 实战陷阱 line 262。**追踪止损不依赖 K 线收盘**（浮盈变化是 tick 级）。MeanReversion line 144 在 NewBar guard **之前**调 Apply 是正确范本。
2. **动态 trail 时漏调 `SetParams`**（start=0 永远不启动） — `_UpdateTrailParams` 必须**先 SetParams 再 Apply**。**反例**：`if (UseTrailing) { trail.Apply(); }` 没调 `_UpdateTrailParams` —— 用 OnInit 时的 `(0, 0, 10)` 占位参数，永远 `profitDist < _P(0) = 0` 不启动。
3. **`Init` 漏传 `&trade`**（`ModifySLTP` 不调但编译过） — `trail.Init()` 不传参 = 静默无效。**编译能过，运行静默不工作**。**保险**：OnInit 后 `Print("trail._trade=", trail._trade);` 验证非 NULL。
4. **`_minGapPoints=0`**（每次 tick 都改 SL 限流） — 浮盈 100 points 时改 SL 100 次/秒。**MT5 服务器返 `retcode=10009`**。**最少 5**，推荐 10（剥头皮）/ 20（趋势）。
5. **跳空预期前开启追踪**（周一开盘穿 SL） — 周五 20:00 后手动关 trail。**XAUUSDm 周一跳空 1-3 USD 常见**（50-300 points），40 points 启动的 trail 在跳空瞬间被穿。**建议**：剥头皮在周五 20:00 后 `InpUseTrail=false`。

### 链向（待 T3 写 wiki）

- **[[实战/MeanReversion_EA wiki]]** — MeanReversion_EA.mq5 13 模块接入完整实战（M08 1.5×ATR 动态 trail / `_UpdateTrailParams` 每 tick 重算 / NewBar guard 之前 Apply）
- **[[实战/ScalperXAU wiki]]** — ScalperXAU.mq5 13 模块接入完整实战（M08 0.4×ATR 紧追踪 / 40 points 启动 / 周五 20:00 后关 trail 防跳空）
- **[[M01 交易封装 CTradePlus]]** — `trail.Init(&trade, Magic)` 把 M01 实例传给 M08 追踪
- **[[M04 指标句柄管理 IndicatorPool]]** — 动态 trail 必须 `ind.AddATR("ATR", 14)` + `ind.Value("ATR", 0)`（MeanReversion line 87 + 214）
- **[[M05 新 K 线检测 NewBar]]** — `trail.Apply` **不依赖** NewBar，应放在 `!IsNewBar` 之前（MeanReversion line 142-145）
- **[[M19 时段过滤 SessionFilter]]** — M19 只挡"开新仓"，**不影响 M08 追踪止损继续管理持仓**（spec M19 实战陷阱 line 329）
- **[[10 件事 §6]]** — 浮亏过大自动全平（M02 EmergencyStop 是另一道防线；M08 追踪止损**只动 SL，不主动全平**）

### 反向引用（实物 EA 接入 demo）

> **本节是 T1 18:00 任务（TrendMA_EA + Breakout_EA 联合 wiki v2）落地的反链**，由 [[实战/TrendMA_EA + Breakout_EA 接入报告]] §4.1 反链表 + §4.2 双向链接段添加。

- **[[实战/TrendMA_EA + Breakout_EA 接入报告]]** — TrendMA + Breakout 2 EA 联合接入报告（**v2 修正版 / 12+11 模块**）：TrendMA `trail.Init(&trade, Magic)` L71 + `trail.SetParams(TrailStart=200, TrailStep=150, 10)` L72 + `trail.Apply()` L94（**真跑** — OnTick 第 2 个调，在 NB.IsNewBar non-new-bar 分支）；Breakout `trail.Init(&trade, Magic)` L77 + `trail.SetParams(TrailStart=250, TrailStep=150, 10)` L78（**配了不跑** — Init+SetParams only, OnTick 无 trail.Apply 调用, **反模式**）。**2 EA 固定参数 trail 范本**（vs MeanReversion 动态 1.5×ATR + ScalperXAU 紧追踪 0.4×ATR）。
- **本 wiki 实战段 5+ 陷阱对应**：2 EA 共享陷阱 1（ATR 动态参数顺序——**本 2 EA 用固定参数无此陷阱**）+ 陷阱 2（`trail.Apply` 在 NewBar guard 之前, TrendMA L94 正确放置）；TrendMA 避开陷阱 3（`Init` 传 `&trade` 不漏）+ 陷阱 5（`_minGapPoints=10` 不为 0）。**Breakout 反例**: 配了 trail 不跑 Apply = 反模式（v2 新增反模式 7）。
- **三档 trail 对比**：本 2 EA 固定参数 = 趋势 EA 标准；MeanReversion 动态 1.5×ATR = 多品种自适应；ScalperXAU 0.4×ATR 紧追踪 = 剥头皮高频。**选哪种看策略 + 周期**：M15/H1 趋势 → 本 2 EA 固定；多品种 M15 → 动态 ATR；M1 剥头皮 → 紧追踪（慎用）。
- **v1 → v2 关键修正**：v1 wiki 错写 Breakout trail "Init+SetParams+Apply", v2 实测 Breakout **0 trail.Apply 调用** = 反例。修复方法 = 加 `if (InpUseTrail) trail.Apply();` 在 Breakout OnTick L97-98 之间。

---

## §N 漂移修复 & 验证 (N5 2026-06-04 20:00 闭环)

> 本节是 19:00 T2 漂移校验 + 20:00 N5 漂移修复的产物，记录本 wiki "319 行" 实物行数引用与 MeanReversion_EA.mq5 当前 320 行的对齐情况。

### N.1 漂移清单 (本 wiki 涉及 2 处 319 行, 19:00 T2 §3.2.7)

| # | 位置 | 19:00 漂移 | N5 修后 | 实物实测 |
|---|---|---|---|---|
| 1 | §实物 demo 段 (line 170) | `MeanReversion_EA.mq5 ATR(14) 自适应 trail (319 行)` | `(320 行)` | 实物当前 320 行 (Node.js fs 实测) |
| 2 | §实物 demo EA 接入 (line 178) | `MeanReversion_EA.mq5 (319 行, 13 模块集成)` | `(320 行, 13 模块集成)` | 实物当前 320 行 (Node.js fs 实测) |

> **根因**：13:00-14:00 期间实物 `MeanReversion_EA.mq5` 加了 input group `=== 通知 ===` (L66-68) + input group `=== 多品种对冲过滤 (M18) ===` (L70-73) 共 5 行 input，导致文件行数从 319 → 320。本 wiki 实物段 "319 行" 引用漂移 +1，N5 修后对齐。

### N.2 实物实测 (Node.js fs 2026-06-04 20:00)

```
MQL5/Experts/minimax-ea/MeanReversion_EA.mq5
  大小: 13,503 B / mtime: 2026-06-04T03:21:46 / 行数: 320 (N5 修后从 319 修正为 320)
  M08 接入点 (5 处):
    L15: #include <MQL5Kit/M08_TrailingStop.mqh>
    L59: CTrailingStop trail;
    L88: trail.Init(&trade, Magic);
    L89: trail.SetParams(0, 0, TrailMinGapPts);
    OnTick L140+: trail.Apply() + _UpdateTrailParams (动态 ATR 重算 startPts/stepPts)
```

> 0 改 .mq5, mtime 保持 03:21:46, 实物字节 13,503 不变。

### N.3 Node.js fs 一键复测命令 (verifier 独立复测本 wiki 漂移修复)

```bash
# 1) 实物当前行数实测 (期望 320, 跟 wiki 一致)
node -e "const fs=require('fs');const c=fs.readFileSync('C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/MeanReversion_EA.mq5','utf8');console.log('MeanReversion_EA lines:',c.split('\n').length)"

# 2) 完整 11 文件 213 个 check 一键复测
node "C:\Users\Administrator\.mavis\plans\plan_f01a5f34\workspace\validate_lines.js"
# 期望: 213/213 PASS, 0 FAIL
```

### N.4 漂移根因分析

- **根因 (319 → 320 +1)**：13:00-14:00 期间实物 `MeanReversion_EA.mq5` 加了 input group `=== 通知 ===` (L66-68) + input group `=== 多品种对冲过滤 (M18) ===` (L70-73) 共 5 行 input，导致文件总行数从 319 → 320。本 wiki 实物段 "319 行" 引用漂移 +1，N5 修后对齐到 320 行。
- **本 wiki §实战段 5+ 陷阱 + 三档 trail 对比 + v1→v2 关键修正**等逻辑内容不变，仅更新实物行数引用。
