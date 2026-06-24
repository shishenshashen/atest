---
title: M05 新 K 线检测 NewBar
tags: [调用模块, 事件]
type: module
---

# M05 新 K 线检测 NewBar

> **作用**：避免每个 tick 都跑信号，**只在 K 线收盘那一瞬触发**。
> **99% 的 EA 都需要**。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                              M05_NewBar.mqh       |
//|                              EA 开发知识库 - 新 K 线检测            |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 新 K 线检测：iTime 变化即新 K 线                                  |
//| 用法：if (NB.IsNewBar()) { ... }                                  |
//+------------------------------------------------------------------+
class CNewBar {
private:
   ENUM_TIMEFRAMES _period;
   datetime        _lastBar;

public:
   CNewBar() : _period(PERIOD_CURRENT), _lastBar(0) {}

   // 初始化（OnInit 里）
   void Init(ENUM_TIMEFRAMES period = PERIOD_CURRENT) {
      _period  = period;
      _lastBar = 0;   // 第一次 IsNewBar() 必然 true
   }

   // 当前是不是新 K 线？
   //  返回 true 表示"这根是新出现的"
   //  返回 false 表示"还是上一根"
   bool IsNewBar() {
      datetime cur = iTime(_Symbol, _period, 0);
      if (cur == 0) return false;
      if (cur != _lastBar) {
         _lastBar = cur;
         return true;
      }
      return false;
   }

   // 强制重置（时间框架切换时用）
   void Reset() { _lastBar = 0; }

   // 当前 K 线的开盘时间
   datetime CurrentBarTime() const { return _lastBar; }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M05_NewBar.mqh>

CNewBar NB;

int OnInit() {
   NB.Init(_Period);
   return INIT_SUCCEEDED;
}

void OnTick() {
   if (!NB.IsNewBar()) return;   // 不是新 K 线，不处理
   // ... 这里是 K 线收盘后才执行的逻辑 ...
   CheckSignal();
   ManageTrades();
}
```

## 多时间框架

```mql5
CNewBar NB_M5, NB_H1;

int OnInit() {
   NB_M5.Init(PERIOD_M5);
   NB_H1.Init(PERIOD_H1);
   return INIT_SUCCEEDED;
}

void OnTick() {
   if (NB_H1.IsNewBar()) {
      // 只在 H1 收盘时做大趋势判断
   }
   if (NB_M5.IsNewBar()) {
      // M5 收盘做入场
      CheckEntry();
   }
}
```

## OnTimer + NewBar 组合（轮询模式）

如果 OnTick 触发太频繁，**改用 OnTimer 100ms 轮询**：

```mql5
int OnInit() {
   EventSetMillisecondTimer(100);
   NB.Init(_Period);
   return INIT_SUCCEEDED;
}

void OnTimer() {
   if (!NB.IsNewBar()) return;
   // ...
}
```

## 必看陷阱
- **EA 第一次启动时 `IsNewBar()` 返回 true**（`_lastBar=0`），避免错过第一根
- **时间框架切换后必须 Reset()**，否则 `_lastBar` 残留旧周期的 K 线时间
- 实盘中"新 K 线"= 服务器推送新报价的那一 tick
- 回测中"新 K 线"= 测试器在 K 线收盘时触发 OnTick
- **不要在 NewBar 内部 Print 高频数据**（会卡）

## 替代方案对比
| 方法 | 优 | 劣 |
|---|---|---|
| **iTime 对比（推荐）** | 准、稳 | 第一次需要 init |
| `Volume[0]==0` | 也行 | 期货不适用 |
| `Bars(_Symbol, _Period)` 增加 | 简单 | 时间框架切换不准 |
| OnTimer 周期 | 灵活 | 多一道调度 |

---

## 实战案例

> **本节汇总 M05 NewBar 在真实 EA 场景的接入经验和完整代码模板**。
> spec wiki (上面) 讲 API + 理论；本节讲"已经跑通的 MA 交叉只在 K 线闭合触发 / 多 EA 隔离 / OnTick 顶部接入"。

### 实战摘要（点开 wiki 前先看这段）

- **场景 A TrendMA_EA.mq5 MA 交叉只在 K 线闭合时判断**（239 行，12 模块集成）：M05 `NB.Init(_Period)` 在 OnInit line 68；`!NB.IsNewBar()` 在 OnTick 入口 line 93 — 不是新 K 线直接 return（不跑 CheckEntry/CheckExit）；M08 追踪止损和 Dashboard 在 line 94-95 仍每 tick 跑（不依赖 NewBar）。
- **场景 B MeanReversion_EA.mq5 多周期多 EA 隔离**（320 行）：M05 `NB.Init(_Period)` 在 OnInit line 83；`!NB.IsNewBar()` 在 OnTick line 146 — MeanReversion_EA 只用单 `NB`（跟随 chart TF），多 TF 场景用 `NB_M5` / `NB_H1` 两个实例。
- **即抄代码**：`if (!NB.IsNewBar()) return;` 必须放在 OnTick **顶部**（指标读 + 信号判断 + 下单之前），**不挡 M08 追踪止损**。
- **5+ 已知陷阱**：`!NB.IsNewBar()` 错放在 OnTick 底部（导致每 tick 跑 1 次指标） / 多 EA 共享 `NB` 实例（跨 EA 串扰 `_lastBar`） / `NB.Init` 漏调（`_lastBar=0` 第一次返 true 是想要的，但要在 OnInit 调一次） / 时间框架切换不 `Reset()`（`_lastBar` 残留旧周期 K 线时间） / `IsNewBar` 内部 Print 高频数据卡顿。
- **5 条反模式**：`Volume[0]==0` 判断新 K 线（期货不适用） / `Bars(_Symbol, _Period)` 自增（时间框架切换不准） / `!NB.IsNewBar()` 当 M08 追踪止损的 guard / 把 `NB` 声明在 `OnTick` 里（每次 tick 重建 `_lastBar=0` 永远返 true） / 多 EA 共享 `NB` 全局。

### 实物 demo EA 接入（趋势 MA 交叉）

**`MQL5/Experts/minimax-ea/TrendMA_EA.mq5`**（239 行，12 模块集成，趋势 MA 交叉）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 13** `#include <MQL5Kit/M05_NewBar.mqh>`
- **line 52** `CNewBar NB;` 全局对象（与 M01 trade / M02 risk / M04 ind 同区，48-55 行）
- **line 68** `NB.Init(_Period);` — OnInit 内，跟随 chart TF（默认 H1）
- **line 93** `if (!NB.IsNewBar()) { ... return; }` — OnTick 顶部 guard

**关键设计**（line 91-103）：
```mql5
void OnTick() {
   _CheckDrawdown();   // line 92 每次 tick 检查回撤 (独立于 NewBar)
   if (!NB.IsNewBar()) {                       // line 93
      if (UseTrailing) trail.Apply();          // line 94 追踪每 tick 跑
      if (ShowDashboard) RefreshDash();        // line 95 面板每 tick 刷
      return;                                  // line 96
   }
   if (ind.Values("MA_Fast", _fastArr, 3) < 3) return;  // line 98 信号判断
   if (ind.Values("MA_Slow", _slowArr, 3) < 3) return;  // line 99
   CheckEntry();   // line 100 只在新 K 线跑入场
   CheckExit();    // line 101 只在新 K 线跑出场
   if (ShowDashboard) RefreshDash();           // line 102 新 K 线也刷一次
}
```

**陷阱对应**：`!NB.IsNewBar()` 的"else 分支"（line 94-95）放 M08 追踪 + Dashboard 是正确的 — 它们**不依赖 K 线收盘**，每 tick 都该跑。

### 实物 demo EA 接入（多周期多 EA 隔离）

**`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`**（320 行，13 模块集成，多品种均值回归）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 13** `#include <MQL5Kit/M05_NewBar.mqh>`
- **line 58** `CNewBar NB;` 全局对象
- **line 83** `NB.Init(_Period);` — OnInit 内
- **line 146** `if (!NB.IsNewBar()) return;` — OnTick 顶部 guard

**关键设计**：MeanReversion_EA 只用**单 `NB`**（跟随 chart TF，M5/H1/M15 由用户挂图表时选）。要 H1 趋势 + M5 入场的"多周期"必须声明两个 `CNewBar` 实例：

```mql5
CNewBar NB_H1, NB_M5;   // 两个实例, 各自 _lastBar, 不串扰

int OnInit() {
   NB_H1.Init(PERIOD_H1);  // line X H1 周期
   NB_M5.Init(PERIOD_M5);  // line X M5 周期
   return INIT_SUCCEEDED;
}

void OnTick() {
   if (NB_H1.IsNewBar()) {
      // 只在 H1 收盘时做大趋势判断
      RefreshTrendBias();
   }
   if (NB_M5.IsNewBar()) {
      // M5 收盘做入场信号
      CheckEntry();
   }
}
```

**多 EA 隔离**：每个 EA（每个 .mq5 文件 = 一个 .ex5 实例 = 一个全局 `NB`）互不影响 — broker 端按进程隔离。但**单 EA 内多 `CNewBar` 实例**必须每个 TF 一份（见上）。

### 即抄代码（OnInit + OnTick 接入骨架）

```mql5
// 1) include
#include <MQL5Kit/M05_NewBar.mqh>

// 2) 全局
CNewBar NB;        // 单 TF 简单场景
// CNewBar NB_H1, NB_M5;   // 多 TF 复杂场景, 各自一份

int OnInit() {
   NB.Init(_Period);   // 跟随 chart TF (剥头皮 M1 / 趋势 H1 / 逆势 M15)
   // NB_H1.Init(PERIOD_H1);
   // NB_M5.Init(PERIOD_M5);
   return INIT_SUCCEEDED;
}

void OnTick() {
   _CheckDrawdown();   // 独立于 NewBar, 每 tick 跑
   
   if (!NB.IsNewBar()) {
      // 不是新 K 线: 仍可跑 M08 追踪 + Dashboard
      if (UseTrailing) trail.Apply();
      if (ShowDashboard) RefreshDash();
      return;          // 信号判断/入场/出场 跳过
   }
   
   // 新 K 线: 跑信号 + 入场
   if (ind.Values("MA_Fast", _fastArr, 3) < 3) return;
   CheckEntry();
   CheckExit();
   if (ShowDashboard) RefreshDash();
}
```

### 实战陷阱（5+ 来自实物 EA）

1. **`!NB.IsNewBar()` 错放在 OnTick 底部** — 应该在顶部。TrendMA_EA line 93 是正确范本。错放底部 = 每 tick 跑 1 次 `ind.Values` + `CheckEntry`，高 CPU + 重复开仓风险。
2. **多 EA 共享 `NB` 实例** — 跨 EA 串扰 `_lastBar`。**M05 没有 static 全局副作用**，但 `CNewBar` 内部 `_lastBar` 状态在每个 EA 进程是隔离的；问题出在"一个 EA 文件想跑多 symbol"（多 symbol chart 挂同一 EA），此时**每个 chart 一个 .ex5 进程 = 各自 NB**（安全）。
3. **`NB.Init` 漏调** — 第一次 `IsNewBar()` 永远返 true（`_lastBar=0`）。但**漏调 Init 在多 TF 场景不报错**（`_lastBar=0` → `iTime != 0` → 返 true，逻辑"碰巧"对）。建议在 OnInit 必调（实物 EA 100% 调）。
4. **时间框架切换不 `Reset()`** — `_lastBar` 残留旧周期 K 线时间，下次 `IsNewBar` 比较的是"新周期 iTime vs 旧周期 iTime"，可能永远不等 / 立刻等。**只有动态切换 TF 的 EA 才需要 `Reset()`**，固定 chart 的 EA 不需要。
5. **`IsNewBar` 内部 Print 高频数据** — `Print(iTime(...))` 每 tick 跑 1 次（即使不新 K 线也跑），journal 会爆炸。把 Print 放在 `if (NB.IsNewBar()) { Print(...); }` 内（只在 true 分支打）。
6. **M19/M17 之类的"开仓前过滤器"应放在 `!NB.IsNewBar()` 之后** — 见 MeanReversion_EA line 146 → 161-172 顺序：先 NewBar guard → 再 ADX/M19/M18 过滤 → 再入场。

### 反模式（5 条禁止）

1. **`Volume[0]==0` 判断新 K 线** — 期货 tick volume 不适用，1 分钟 K 线内 `Volume[0]` 累积为非 0。M05 iTime 对比是**通用解**。
2. **`Bars(_Symbol, _Period)` 自增** — 简单但时间框架切换不准（Period 改后 Bars 可能不变），且第一次启动时（重启终端）Bar 总数会跳变。
3. **`!NB.IsNewBar()` 当 M08 追踪止损的 guard** — 追踪止损**不依赖 K 线收盘**（浮盈变化是 tick 级），错误 guard 等于"只在 K 线收盘时追踪"，追踪频率下降 99%。TrendMA_EA line 94 正确做法：M08 追踪放在 `!NB.IsNewBar()` 的 else 分支内。
4. **把 `NB` 声明在 `OnTick` 里** — 每次 tick 重建 `_lastBar=0` 永远返 true → 每 tick 都跑入场逻辑 → 重复开仓。
5. **多 EA 共享 `NB` 全局** — `CNewBar` 是 per-EA 全局（per .ex5 进程），跨 EA 共享在 MT5 架构上不发生（每 EA 是独立进程）。但**一个 EA 文件想跑多 symbol 时**必须依赖 broker 端 chart 隔离（多 chart = 多进程 = 多 NB）。

### 链向（待 T3 写 wiki）

- **[[实战/TrendMA_EA wiki]]** — TrendMA_EA.mq5 12 模块接入完整实战（MA 交叉只在 H1 收盘判断 / M08 追踪不依赖 NewBar）
- **[[实战/MeanReversion_EA wiki]]** — MeanReversion_EA.mq5 13 模块接入完整实战（多周期多 EA 隔离 / M19 + M18 在 NewBar guard 之后串联）
- **[[M02 风控 Risk]]** — `risk.CanOpen` 在 NewBar guard 之后调
- **[[M04 指标句柄管理 IndicatorPool]]** — `ind.Values` 在 NewBar guard 之后调（节省 tick 算力）
- **[[M08 追踪止损 TrailingStop]]** — `trail.Apply` **不依赖** NewBar，应放在 `!IsNewBar` 的 else 分支
- **[[M19 时段过滤 SessionFilter]]** — M19 在 NewBar guard 之后（off-hours 直接 RefreshDash return）
- **[[M06 多空判断 Signal]]** — `CSignal::CrossUpSeries` 在 NewBar guard 之后调
- **[[10 件事 §10]]** — 别在 OnTick 里重计算（M05 NewBar + M04 句柄是组合方案）
