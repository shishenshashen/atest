---
title: M07 持仓管理 Positions
tags: [调用模块, 持仓]
type: module
---

# M07 持仓管理 Positions

> **作用**：把"遍历持仓/按 magic 过滤/按品种过滤/取最大浮盈"这些常用操作集中起来。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                            M07_Positions.mqh      |
//|                              EA 开发知识库 - 持仓管理              |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 持仓工具集：遍历、过滤、统计                                       |
//+------------------------------------------------------------------+
class CPositions {
public:
   //+--- 统计本 EA 的持仓数（按 magic） ------------------------------+
   static int Count(ulong magic) {
      int n = 0;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) == magic) n++;
      }
      return n;
   }

   //+--- 统计本 EA 本品种的持仓数 -----------------------------------+
   static int CountMine(ulong magic, string symbol = NULL) {
      if (symbol == NULL) symbol = _Symbol;
      int n = 0;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) != magic) continue;
         if (PositionGetString(POSITION_SYMBOL) != symbol) continue;
         n++;
      }
      return n;
   }

   //+--- 是否存在指定方向的持仓 -------------------------------------+
   static bool HasDirection(ulong magic, ENUM_POSITION_TYPE type,
                            string symbol = NULL) {
      if (symbol == NULL) symbol = _Symbol;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) != magic) continue;
         if (PositionGetString(POSITION_SYMBOL) != symbol) continue;
         if ((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == type)
            return true;
      }
      return false;
   }

   //+--- 拿第一个匹配的 ticket（找不到返回 0）------------------------+
   static ulong FindFirst(ulong magic, string symbol = NULL,
                          ENUM_POSITION_TYPE type = -1) {
      if (symbol == NULL) symbol = _Symbol;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) != magic) continue;
         if (PositionGetString(POSITION_SYMBOL) != symbol) continue;
         if (type != -1 &&
             (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) != type)
            continue;
         return t;
      }
      return 0;
   }

   //+--- 计算本 EA 的总浮盈 -----------------------------------------+
   static double TotalProfit(ulong magic) {
      double p = 0;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) == magic)
            p += PositionGetDouble(POSITION_PROFIT);
      }
      return p;
   }

   //+--- 计算本 EA 的总浮盈 + 手续费 + 隔夜利息 ----------------------+
   static double TotalNet(ulong magic) {
      double p = 0;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) != magic) continue;
         p += PositionGetDouble(POSITION_PROFIT)
           + PositionGetDouble(POSITION_SWAP)
           + PositionGetDouble(POSITION_COMMISSION);
      }
      return p;
   }

   //+--- 最大单笔浮盈 ---------------------------------------------+
   static double MaxProfit(ulong magic) {
      double m = -DBL_MAX;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) != magic) continue;
         double p = PositionGetDouble(POSITION_PROFIT);
         if (p > m) m = p;
      }
      return (m == -DBL_MAX) ? 0 : m;
   }

   //+--- 浮亏最深的 -----------------------------------------------+
   static double MaxLoss(ulong magic) {
      double m = DBL_MAX;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) != magic) continue;
         double p = PositionGetDouble(POSITION_PROFIT);
         if (p < m) m = p;
      }
      return (m == DBL_MAX) ? 0 : m;
   }

   //+--- 收集所有本 EA 的 ticket 到数组 ------------------------------+
   static int Collect(ulong magic, ulong &tickets[]) {
      ArrayResize(tickets, PositionsTotal());
      int n = 0;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) == magic)
            tickets[n++] = t;
      }
      ArrayResize(tickets, n);
      return n;
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M07_Positions.mqh>

ulong Magic = 20260101;

void OnTick() {
   // 持仓数
   int n = CPositions::Count(Magic);
   Print("本 EA 持仓: ", n);

   // 已有做多持仓则不重复开多
   if (CPositions::HasDirection(Magic, POSITION_TYPE_BUY)) return;

   // 总浮盈
   double totalP = CPositions::TotalProfit(Magic);
   if (totalP < -200) {  // 亏超 200 美元
      // 全部平仓
      ulong tkts[];
      CPositions::Collect(Magic, tkts);
      for (int i = 0; i < ArraySize(tkts); i++) {
         trade.ClosePos(tkts[i]);
      }
   }
}
```

## 必看陷阱
- `PositionGetInteger` 不需要先 `PositionSelect`，但 `PositionGetTicket` 之后**某些属性要重新查**（实测用 `PositionGetXxx` 都会自动重 select，但为了稳，循环里调一次 `PositionSelectByTicket`）
- **遍历同时平仓**必须**倒序**（`PositionsTotal()-1` 到 0），否则索引会跳
- magic=0 也会被匹配（手动单也用 magic=0），小心冲突

---

## 实战案例

> **本节汇总 M07 Positions 在真实 EA 场景的接入经验和完整代码模板**。
> spec wiki (上面) 讲 API + 理论；本节讲"已经跑通的多品种 4 品种持仓管理 + 剥头皮 HasDirection 防对冲 + 反模式"。

### 实战摘要（点开 wiki 前先看这段）

- **场景 A MeanReversion_EA.mq5 4 品种持仓管理**（320 行，13 模块集成）：M07 是**纯 static class**（spec line 23-147）—— 无实例，全是 `CPositions::CountMine(Magic)` / `CPositions::HasDirection(Magic, type)` 静态调用；接入点 5 处：line 14 include / line 177 `CountMine` 持仓数 / line 180 `HasDirection(BUY)` 防同向 / line 184 `HasDirection(SELL)` 防同向。
- **场景 B ScalperXAU.mq5 单品种剥头皮 HasDirection 防对冲**（1032 行）：M07 `posMgr` 实例**也声明了**（line 112）但**只用了 static 入口**（line 769-770 `CPositions::HasDirection(InpMagicNumber, BUY/SELL)`）—— 单品种剥头皮 = 0/1 笔同向持仓，`HasDirection` 直接挡掉重复开仓。
- **即抄代码**：`CPositions::HasDirection(Magic, POSITION_TYPE_BUY)` 在入场条件之后、`trade.Buy` 之前调；`CPositions::CountMine(Magic) >= MaxPos` 在入场条件最顶部调。
- **5+ 已知陷阱**：`magic=0` 会匹配手动单（实测冲突） / `PositionGetTicket` 之后要 `PositionSelectByTicket` 重 select / 遍历同时平仓必须倒序 / `CPositions` 是 static 不需要实例（声明了不调不算错） / `Count` vs `CountMine` 区别（前者跨品种，后者限定本 `_Symbol`）。
- **5 条反模式**：`CountMine` 不传 symbol 参数（默认 `_Symbol` 跨品种场景错乱） / 遍历同时平仓用正序（索引跳变漏单） / `magic=0` 当 EA 自己的 magic / 把 `CPositions` 误以为需要实例 / `HasDirection` 后不读返回值直接下单。

### 实物 demo EA 接入（多品种 4 品种）

**`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`**（320 行，13 模块集成，多品种均值回归）— 已落地，0 errors 编译。

接入点（5 处）：
- **line 14** `#include <MQL5Kit/M07_Positions.mqh>`
- **line 75-77** `static ulong _lastDealTicket = 0;` — 模块无实例（`CPositions` 是 static class）
- **line 177** `if (CPositions::CountMine(Magic) >= MaxPos) return;` — OnTick 新 K 线分支，**入场上限**
- **line 180** `&& !CPositions::HasDirection(Magic, POSITION_TYPE_BUY)` — OnTick 入场条件，**多单同向防重复**
- **line 184** `&& !CPositions::HasDirection(Magic, POSITION_TYPE_SELL)` — OnTick 入场条件，**空单同向防重复**

**关键设计**：
```mql5
// OnTick line 174-186 (4 品种均值回归核心)
double price = (SymbolInfoDouble(_Symbol, SYMBOL_ASK)
              + SymbolInfoDouble(_Symbol, SYMBOL_BID)) / 2.0;

if (CPositions::CountMine(Magic) >= MaxPos) return;     // line 177 总持仓上限

if ((rsi < RSI_Oversold || price < bbLower)
 && !CPositions::HasDirection(Magic, POSITION_TYPE_BUY)) {   // line 180
   OpenPos(ORDER_TYPE_BUY, price);
}
if ((rsi > RSI_Overbought || price > bbUpper)
 && !CPositions::HasDirection(Magic, POSITION_TYPE_SELL)) {  // line 184
   OpenPos(ORDER_TYPE_SELL, price);
}
```

**4 品种场景**（XAUUSDm/EURUSDm/GBPUSDm/USDJPYm）：
- `CountMine(Magic)` 默认 `symbol = _Symbol`（spec line 38）—— **限定本品种**持仓
- **多品种 EA 把 4 品种挂 4 个 chart**，每个 chart 的 EA 实例**自己** `CountMine(_Symbol)` —— 4 品种同 EA 共享 magic，靠 chart 隔离
- `MaxPos=3`（input line 34）—— **本品种**最多 3 笔同向（**不是 4 品种总 3 笔**；多品种总持仓由 M02 `_maxPositions` 跨品种控）
- **M02 在 line 199 `risk.CanOpen` 内**已经做了跨品种总持仓限制（spec M02 line 79-82 `CountMyPositions() >= _maxPositions`），M07 的 `CountMine` 是**本品种内**的二次过滤

**magic 误查陷阱**（spec 必看陷阱 line 182）：**`Magic = 0` 会匹配所有手动单**。MeanReversion line 23 `Magic = 20260201`（非零）—— 安全。**如果用户 input 改 `Magic = 0`**，M07 + M02 + M18 全部会查手动单，误把"手动 XAUUSDm 多"算成"EA 已有 XAUUSDm 多"，跳过入场。

### 实物 demo EA 接入（剥头皮单品种）

**`MQL5/Experts/minimax-ea/ScalperXAU.mq5`**（1032 行，13 模块集成，剥头皮 XAUUSDm M1）— 已落地，0 errors 编译。

接入点（5+ 处）：
- **line 24** `#include <MQL5Kit/M07_Positions.mqh>`
- **line 112** `CPositions posMgr;` — 全局对象**声明了但不用**（M07 是 static class，**不需要实例**）
- **line 769-770** `if (type == ORDER_TYPE_BUY && CPositions::HasDirection(InpMagicNumber, POSITION_TYPE_BUY)) return;` / `if (type == ORDER_TYPE_SELL && CPositions::HasDirection(InpMagicNumber, POSITION_TYPE_SELL)) return;` — `TryOpen()` 函数内（745-784 行）入场前最后一道防同向
- **line 814** `else if (CPositions::Count(InpMagicNumber) >= InpMaxPositions) block = "MAX_POS";` — OnTick v4 debug log 用
- **line 823** `&& CPositions::Count(InpMagicNumber) < InpMaxPositions` — OnTick 入场条件
- **line 852** `dash.Row("Positions", IntegerToString(CPositions::Count(InpMagicNumber)) + "/" + IntegerToString(InpMaxPositions));` — Dashboard 显示

**关键设计**（剥头皮 vs 多品种对比）：
- **单品种**剥头皮 = 0/1 笔持仓，`HasDirection` 直接挡"同向重复开仓"（line 769-770）—— **剥头皮的核心风控**
- **多品种** EA = 4 品种 × N 笔 = 4N 笔总持仓，`CountMine(Magic, _Symbol)` 限定本品种内计数
- **剥头皮用 `Count(Magic)`**（spec line 26-34，跨品种总持仓）；**多品种用 `CountMine(Magic, _Symbol)`**（spec line 37-48，本品种内）

**ScalperXAU 不需要 posMgr 实例**：
- `CPositions` 是**纯 static class**（spec line 23-147）—— 11 个方法全是 `static`
- 声明 `CPositions posMgr;` 在 line 112 不会编译错（空对象无副作用），但**永远不要用 `posMgr.HasDirection(...)`** —— static 方法必须 `CPositions::HasDirection(...)` 调
- `posMgr` 在 OnDeinit 不需要 `Release` / `delete`（无资源）

### 即抄代码（OnTick 接入骨架）

```mql5
// 1) include (static class, 无实例声明)
#include <MQL5Kit/M07_Positions.mqh>

input ulong Magic = 20260101;
input int   MaxPos = 3;

void OnTick() {
   if (CPositions::CountMine(Magic) >= MaxPos) return;       // ★ 顶部: 持仓上限
   
   if (/* 入场条件 BUY */) {
      if (CPositions::HasDirection(Magic, POSITION_TYPE_BUY)) return;  // ★ 防同向
      // ... sizing + risk + trade.Buy
   }
   if (/* 入场条件 SELL */) {
      if (CPositions::HasDirection(Magic, POSITION_TYPE_SELL)) return;
      // ... sizing + risk + trade.Sell
   }
}

void CloseAllMyPositions() {
   ulong tkts[];
   int n = CPositions::Collect(Magic, tkts);   // 收所有本 EA 的 ticket
   for (int i = n - 1; i >= 0; i--) {          // ★ 倒序遍历, 平仓不漏
      trade.ClosePos(tkts[i]);
   }
}
```

### 实战陷阱（5+ 来自实物 EA）

1. **`magic=0` 会匹配手动单** — spec 必看陷阱 line 182。**MeanReversion line 23 `Magic = 20260201`** 是不错示例。**实测**：`CPositions::HasDirection(0, BUY)` 会查所有手动 + EA 单。**新手用 magic=0 = 等于没过滤**。
2. **`PositionGetTicket` 之后要 `PositionSelectByTicket` 重 select** — spec 必看陷阱 line 180。**MT5 行为**：`PositionGetXxx` 在 `PositionGetTicket` 之后**有时**会自动重 select，**但不保证**所有 broker 端一致。**保险做法**：循环里调一次 `PositionSelectByTicket(ticket)`（spec line 75 `_ApplyOne` 在 M08 中已经这样做）。
3. **遍历同时平仓必须倒序** — spec 必看陷阱 line 181。`for (int i = PositionsTotal() - 1; i >= 0; i--)` 是正确范本。**正序遍历**：平仓后 `PositionsTotal()` 减少 1，但 `i++` 继续访问原索引 = 跳过一个未平仓位 = 漏平。ScalperXAU line 566-578 `CheckHoldTimeout` 是正确范本。
4. **`CPositions` 是 static 不需要实例** — spec line 23-147 全是 `static`。**声明 `CPositions posMgr;` 不会编译错**（空对象无影响），但**调用必须用 `CPositions::HasDirection(...)`**（ScalperXAU line 112 + line 769-770 是正确范本——声明但不用，调 static）。
5. **`Count` vs `CountMine` 区别** — spec line 26-34 `Count(magic)` 跨所有 symbol；spec line 37-48 `CountMine(magic, symbol)` 限定本 symbol。**多品种 EA 用 `CountMine`**（MeanReversion line 177 限定本 `_Symbol`）；**单品种剥头皮用 `Count`**（ScalperXAU line 814/823 跨 symbol = 0/1 笔，行为等价但语义清晰）。
6. **Dashboard `CountMine` 不传 symbol** — spec line 38 `if (symbol == NULL) symbol = _Symbol;` —— 默认本 chart 的 symbol。**多品种 EA 挂 4 个 chart**时，每个 chart 的 `CountMine` 自动用本 chart symbol。**单 EA 跑多 symbol（用 `SymbolSelect` 切）** 必须显式传 `CountMine(Magic, targetSymbol)`。

### 反模式（5 条禁止）

1. **`CountMine` 不传 symbol 参数（默认 `_Symbol` 跨品种场景错乱）** — 如果 EA 在 `OnTick` 里**主动切 symbol**（如 `SymbolSelect(_Symbol); SymbolInfoTick(_Symbol);`）后调 `CountMine(Magic)`，`symbol` 默认仍是**切之前的 `_Symbol`**，**不是当前激活的 symbol**。**安全做法**：`CountMine(Magic, _Symbol)` 显式传。
2. **遍历同时平仓用正序** — `for (int i = 0; i < PositionsTotal(); i++)` + 循环体 `trade.ClosePos(...)` = 平仓后索引跳变漏单。**永远倒序**（spec line 28 / line 40 / line 54 / line 69 / line 86 / line 96 / line 111 / line 124 / line 138）。
3. **`magic=0` 当 EA 自己的 magic** — spec 必看陷阱 line 182。等于"匹配所有" = 等于没过滤。多 EA 同账户会**互相误平**。**Magic 必须非零且唯一**（参考 [[00-快速开始/EA 写之前要知道的 10 件事]] §5）。
4. **把 `CPositions` 误以为需要实例** — spec 全文 11 个方法都是 `static`。**不要**写 `CPositions pos; pos.HasDirection(Magic, BUY);` —— 编译能过但**不是规范**。**统一用 `CPositions::HasDirection(Magic, BUY)`**。
5. **`HasDirection` 后不读返回值直接下单** — `if (CPositions::HasDirection(...))` 拆掉 `if` 直接 `trade.Buy(...)` = 同向开仓第二次。**Spec 设计意图**：`HasDirection` 返 `bool`，**调用方必须 if 守卫**。ScalperXAU line 769-770 `if (type == ... && CPositions::HasDirection(...)) return;` 是正确范本。

### 链向（待 T3 写 wiki）

- **[[实战/MeanReversion_EA wiki]]** — MeanReversion_EA.mq5 13 模块接入完整实战（4 品种 `CountMine(_Symbol)` 限定本品种 / `HasDirection` 防同向 / magic 隔离）
- **[[实战/ScalperXAU wiki]]** — ScalperXAU.mq5 13 模块接入完整实战（单品种剥头皮 `HasDirection` 防对冲 / v4 debug log 协议 `MAX_POS` block 分类）
- **[[M01 交易封装 CTradePlus]]** — `trade.ClosePos(tkts[i])` 配合 `CPositions::Collect(Magic, tkts)` 一键平所有本 EA 持仓
- **[[M02 风控 Risk]]** — `risk.CanOpen` 内部已经 `CountMyPositions`（spec M02 line 78），M07 是其 static 替代
- **[[M08 追踪止损 TrailingStop]]** — `trail.Apply` 内部遍历 `PositionsTotal()` 找本 magic 持仓（spec M08 line 64-71），与 M07 互不冲突
- **[[M18 相关性过滤 CorrelationFilter]]** — `IsHedgeExposed` 内部用 `PositionsTotal()` 查本 magic 已有持仓（spec M18 line 32-33），与 M07 互不冲突
- **[[10 件事 §5]]** — magic + comment 隔离多策略（直接抄 M07.CountMine）

### 反向引用（实物 EA 接入 demo）

> **本节是 T1 18:00 任务（TrendMA_EA + Breakout_EA 联合 wiki v2）落地的反链**，由 [[实战/TrendMA_EA + Breakout_EA 接入报告]] §4.1 反链表 + §4.2 双向链接段添加。

- **[[实战/TrendMA_EA + Breakout_EA 接入报告]]** — TrendMA + Breakout 2 EA 联合接入报告（**v2 修正版 / 12+11 模块**）：**TrendMA 9 处 CPositions 调用**（CheckEntry L106/L108/L112 + CheckExit L118/L120/L123/L125 + RefreshDash L161/L162）；**Breakout 0 处 CPositions 调用**（include 但不用, **反例**）。**`MaxPos=3` 默认**（2 EA input L32/L31）+ **Magic=20260101 / 20260102**（同账户挂 2 chart 需手动改 magic 防互相误平）。
- **本 wiki 实战段 5+ 陷阱对应**：TrendMA 避开陷阱 1（`magic=0` 匹配手动单, 本 EA 用 20260101 非零安全）+ 陷阱 4（`CPositions` 是 static 不需要实例, TrendMA 实际未声明 `posMgr` object 但 L106+ 仍调 `CPositions::CountMine`, **正确范本**）+ 陷阱 5（`Count` vs `CountMine` 用对, TrendMA L106 用 `CountMine(_Symbol)` 限定本品种）；**Breakout 反例**: include M07 但不调 = 编译期浪费.
- **联合 wiki 反模式 6**：[[实战/TrendMA_EA + Breakout_EA 接入报告]] §6 反模式 6 (v2 新增) 提到"include 模块但不调用"——Breakout 0 CPositions 调用 + 0 logger 调用 = 浪费编译期 + 头文件依赖. 修复方法 = 选项 A 删 include / 选项 B 加实际调用.
- **联合 wiki 反模式 1**：[[实战/TrendMA_EA + Breakout_EA 接入报告]] §6 反模式 1 提到"2 EA 共用 Magic 会 CloseStale 互相误伤"——本 2 EA 当前都用 `Magic = 20260101`（TrendMA L23, Breakout L22），**生产用前必须改 1 个为 20260102**（差 1 即可）。
