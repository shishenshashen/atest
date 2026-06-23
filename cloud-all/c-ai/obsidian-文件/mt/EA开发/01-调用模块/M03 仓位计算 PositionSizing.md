---
title: M03 仓位计算 PositionSizing
tags: [调用模块, 仓位, 资金]
type: module
---

# M03 仓位计算 PositionSizing

> **作用**：根据"账户净值 + 风险比例 + 止损距离"自动算手数。
> 用法：`double lot = sizing.LotByRisk(0.01, slDistance);`

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                        M03_PositionSizing.mqh     |
//|                              EA 开发知识库 - 仓位计算              |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 仓位计算：根据风险比例、止损距离、手数边界，输出合法手数           |
//+------------------------------------------------------------------+
class CPositionSizing {
private:
   double _riskPct;         // 风险占净值比例（0.01 = 1%）

public:
   CPositionSizing() : _riskPct(0.01) {}
   void Init(double riskPct) { _riskPct = riskPct; }

   //+--- 核心：按风险比例算手数 --------------------------------------+
   //  riskPct: 比如 0.01 = 1%
   //  slDistance: 止损价格距离（绝对值），比如 50 * _Point
   //  返回：规范化后的手数
   double LotByRisk(double riskPct, double slDistance) {
      if (slDistance <= 0) {
         Print("仓位计算：止损距离 <= 0");
         return 0;
      }
      double equity   = AccountInfoDouble(ACCOUNT_EQUITY);
      double riskMoney = equity * riskPct;

      double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      if (tickSize == 0) {
         Print("仓位计算：tick size = 0");
         return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      }
      // 1 点/手 的账户货币价值
      double pointVal = tickValue / tickSize;
      // 风险金额 / (止损距离 × 每点价值) = 手数
      double lot = riskMoney / (slDistance * pointVal);

      return _Normalize(lot);
   }

   // 默认风险比例
   double LotByRiskDefault(double slDistance) {
      return LotByRisk(_riskPct, slDistance);
   }

   //+--- 固定金额风险 --------------------------------------------------+
   //  riskMoney: 直接指定可亏多少美元
   double LotByMoney(double riskMoney, double slDistance) {
      if (slDistance <= 0) return 0;
      double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
      double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
      if (tickSize == 0) return 0;
      double pointVal  = tickValue / tickSize;
      double lot = riskMoney / (slDistance * pointVal);
      return _Normalize(lot);
   }

   //+--- 按余额百分比 --------------------------------------------------+
   //  percentOfBalance: 用余额的多少% 作为保证金来开仓
   double LotByBalancePercent(double percentOfBalance, double leverage = 0) {
      if (leverage == 0) leverage = (double)AccountInfoInteger(ACCOUNT_LEVERAGE);
      double contract = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
      double marginRate = 0;
      // 用当前 ASK 作为近似价
      double price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      if (price == 0) return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      // 简化：用 1 / leverage 估算
      double money = AccountInfoDouble(ACCOUNT_BALANCE) * percentOfBalance;
      double lot   = money * leverage / (contract * price);
      return _Normalize(lot);
   }

private:
   // 规范化手数到 [min, max] 并按 step 取整
   double _Normalize(double lot) {
      double minL  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double maxL  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
      double stepL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      if (stepL > 0) lot = MathFloor(lot / stepL) * stepL;
      lot = MathMax(minL, MathMin(maxL, lot));
      // 修浮点误差
      lot = NormalizeDouble(lot, 2);
      return lot;
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M01_CTradePlus.mqh>
#include <MQL5Kit/M02_Risk.mqh>
#include <MQL5Kit/M03_PositionSizing.mqh>

CTradePlus       trade;
CRisk            risk;
CPositionSizing  sizing;

input double RiskPct = 0.01;  // 1% 每笔

int OnInit() {
   trade.Init(Magic);
   risk.Init(Magic, MaxPos, RiskPct);
   sizing.Init(RiskPct);
   return INIT_SUCCEEDED;
}

void OnTick() {
   if (/* 入场信号 */) {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl  = ask - 100 * _Point;     // 100 点止损
      double tp  = ask + 200 * _Point;     // 200 点止盈
      double slDist = ask - sl;             // 100 * _Point

      // 自动算手数：风险 1%，止损 100 点 → 0.10 手（假设黄金 1 点价值 $1）
      double lot = sizing.LotByRisk(RiskPct, slDist);

      if (lot > 0 && risk.CanOpen(ORDER_TYPE_BUY, lot, sl, tp)) {
         trade.Buy(lot, sl, tp, "long");
      }
   }
}
```

## 各种算法对比
| 方法 | 公式 | 适用 |
|---|---|---|
| `LotByRisk` | `equity × 风险% / (止损×点价值)` | **最推荐** |
| `LotByMoney` | `风险金额 / (止损×点价值)` | 想精确控制每笔亏多少美元 |
| `LotByBalancePercent` | `余额×%×杠杆 / (合约×价)` | 简单粗暴 |

## 不同品种的"点价值"参考
- 黄金（XAUUSD）: 1 标准手 1 点（0.01）= $1.0
- 外汇（如 EURUSD）: 1 标准手 1 pip（0.0001）≈ $10
- 指数（如 US30）: 各异
- 加密币: 各异

**不要硬编码**！永远用 `SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE)`。

## 必看陷阱
- 计算出来的 lot 必须 `MathFloor(lot / step) * step`，不能四舍五入
- 止损距离 = 0 会触发除零
- 某些经纪商 `SYMBOL_TRADE_TICK_SIZE` 在点差不稳定时是 0，需要 fallback
- **黄金和外汇的点值算法不同**，但本模块对所有品种通用（用 tick value 即可）

---

## 实战案例

> **本节汇总 M03 PositionSizing 在真实 EA 场景的接入经验和完整代码模板**。
> spec wiki (上面) 讲 API + 理论；本节讲"已经跑通的剥头皮高频 1% 风险 + 多品种 4 品种同 sizing + 反模式"。

### 实战摘要（点开 wiki 前先看这段）

- **场景 A ScalperXAU.mq5 剥头皮高频 1% 风险**（1032 行，13 模块集成）：M03 `sizing` 实例承担所有开仓手数计算；`sizing.Init(InpRiskPercent / 100.0)` 在 OnInit line 958；`sizing.LotByRisk(InpRiskPercent / 100.0, slDist)` 在 `TryOpen()` line 766 — `InpRiskPercent=0.5%` 默认（剥头皮小仓位），`slDist=InpSlPoints=50` points（XAUUSDm 0.5 USD）。
- **场景 B MeanReversion_EA.mq5 多品种 4 品种同 sizing**（320 行，13 模块集成）：M03 `sizing.Init(RiskPct)` 在 OnInit line 82（RiskPct=0.01 input line 33）；`sizing.LotByRisk(RiskPct, slDist)` 在 `OpenPos()` line 197（SL_Points=200 points line 35）；4 品种（XAUUSDm/EURUSDm/GBPUSDm/USDJPYm）共用一个 sizing 实例，靠 `SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE)` 自动适配每个品种的点值（黄金 1 点 $1，外汇 1 pip $10，差异是 10x）。
- **即抄代码**：`double lot = sizing.LotByRisk(riskPct, slDist);` — `slDist` 必须是 `MathAbs(price - sl)` 算出来的绝对价格距离（不是 points 数字）。如果传 50（points）给 slDist，结果会 100x 大。
- **5+ 已知陷阱**：`slDist` 传错单位（points vs price） / `_Normalize` 用 `MathFloor` 不是 `MathRound`（永远是低估） / `SYMBOL_TRADE_TICK_SIZE=0` 时 fallback 到 `SYMBOL_VOLUME_MIN` / 多品种 EA 切换 `_Symbol` 必须每次重算（sizing 内部按 `_Symbol` 算） / `LotByBalancePercent` 是"按余额比例"不是"按风险"，剥头皮不要用。
- **5 条反模式**：硬编码 `pointVal = 10` 写死外汇 / `lot = (riskMoney * 100) / slDist` 裸算 / `lot = 0.01` 固定手数（不调 risk%） / `LotByBalancePercent` 用于剥头皮（保证金不足风险） / 把 sizing 声明在 OnTick 里（每 tick 重建 _riskPct 丢失）。

### 实物 demo EA 接入（剥头皮高频）

**`MQL5/Experts/minimax-ea/ScalperXAU.mq5`**（1032 行，13 模块集成，剥头皮 XAUUSDm M1）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 21** `#include <MQL5Kit/M03_PositionSizing.mqh>`
- **line 109** `CPositionSizing sizing;` 全局对象（与 M01 trade / M02 risk / M04 ind / M07 posMgr / M08 trail 同一区声明，100-110 行）
- **line 958** `sizing.Init(InpRiskPercent / 100.0);` — OnInit 内，`InpRiskPercent=0.5`（input line 51，剥头皮小仓位默认）
- **line 766** `double lot = sizing.LotByRisk(InpRiskPercent / 100.0, slDist);` — `TryOpen()` 函数内（745-784 行），`slDist = MathAbs(price - slPrice)`（line 765）

**关键设计**：`InpRiskPercent / 100.0` 是**百分转小数**的范本（input 用 % 直观，API 用小数 0.005 严谨）。`InpSlPoints=50`（line 42）XAUUSDm 50 points = 0.5 USD 止损距离 = 0.005 × 10000 / 0.5 × $1.0 = 0.1 手（100 USD 净值下）。

**剥头皮 vs 趋势 调参 3 档**（实物 EA 参数化）：
- **保守剥头皮**：`InpRiskPercent = 0.3` (0.3% 单笔) / `InpSlPoints = 50` (50 points = 0.5 USD)
- **标准剥头皮**：`InpRiskPercent = 0.5` (0.5% 默认) / `InpSlPoints = 50`
- **激进剥头皮**：`InpRiskPercent = 1.0` (1% 单笔) / `InpSlPoints = 30` (30 points 紧止损 = 0.3 USD)

### 实物 demo EA 接入（多品种同 sizing）

**`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`**（320 行，13 模块集成，多品种均值回归）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 11** `#include <MQL5Kit/M03_PositionSizing.mqh>`
- **line 56** `CPositionSizing sizing;` 全局对象（与 M01 trade / M02 risk / M04 ind / M05 NB / M08 trail 同一区声明，54-64 行）
- **line 82** `sizing.Init(RiskPct);` — OnInit 内，RiskPct=0.01（input line 33）
- **line 197** `double lot = sizing.LotByRisk(RiskPct, slDist);` — `OpenPos()` 函数内（191-207 行），`slDist = MathAbs(price - sl)`（line 196），`sl=price - SL_Points * _Point`（line 192，SL_Points=200）

**关键设计**：4 品种（XAUUSDm/EURUSDm/GBPUSDm/USDJPYm）共用**同一个 `sizing` 实例**。每次 `OpenPos()` 触发时，`sizing` 内部按**当前 `_Symbol`** 读 `SYMBOL_TRADE_TICK_VALUE` 和 `SYMBOL_TRADE_TICK_SIZE`，自动适配每个品种的点值：
- XAUUSDm: tick_size=0.01, tick_value=0.01 → 1 point = $1.0
- EURUSDm: tick_size=0.00001, tick_value=0.00001 → 1 point = $0.1（5 位报价）
- USDJPYm: tick_size=0.001, tick_value=0.001 → 1 point ≈ $0.01（3 位小数）

**陷阱对应**：4 品种共用 sizing 不需要 4 个实例。**关键**是 sizing 内部**每次都按当前 `_Symbol` 读 tick value**（lot 计算公式 `lot = riskMoney / (slDist * pointVal)` line 53 中的 `pointVal` 是动态查的）。如果 EA 用 `SymbolSelect` 切 symbol，sizing 不需要切实例。

### 即抄代码（OnInit + OnTick 接入骨架）

```mql5
// 1) include
#include <MQL5Kit/M01_CTradePlus.mqh>
#include <MQL5Kit/M02_Risk.mqh>
#include <MQL5Kit/M03_PositionSizing.mqh>

// 2) inputs
input ulong  Magic   = 20260101;
input double RiskPct = 0.01;        // 1% 标准 / 0.5% 保守 / 2% 激进

// 3) 全局
CTradePlus      trade;
CRisk           risk;
CPositionSizing sizing;

int OnInit() {
   trade.Init(Magic, 30);
   risk.Init(Magic, 3, RiskPct);
   sizing.Init(RiskPct);             // 跟 risk 同一值
   return INIT_SUCCEEDED;
}

void OnTick() {
   if (/* 入场信号 */) {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl  = ask - 100 * _Point;             // 100 points
      double tp  = ask + 200 * _Point;
      double slDist = ask - sl;                    // ★ 必须是价格距离, 不是 points 数字
      double lot = sizing.LotByRisk(RiskPct, slDist);
      if (lot <= 0) return;
      if (!risk.CanOpen(ORDER_TYPE_BUY, lot, sl, tp)) return;
      trade.Buy(lot, sl, tp, "MyEAv1");
   }
}
```

### 实战陷阱（5+ 来自实物 EA）

1. **`slDist` 传错单位（points vs price）** — `sizing.LotByRisk(pct, 50)` 50 是 50 **price**（50.00 USD 对 XAUUSDm），不是 50 **points**。正确：`sizing.LotByRisk(pct, 50 * _Point)`（50 points = 0.50 USD）。ScalperXAU line 765 `slDist = MathAbs(price - slPrice)` 是正确范本（直接算价格差）。
2. **`_Normalize` 用 `MathFloor` 不是 `MathRound`（永远是低估）** — spec line 96 `lot = MathFloor(lot / step) * step`。**这是设计选择**——保守仓位优先（多 0.01 手不是事，少 0.01 手会出事）。如果用 `MathRound` 可能超过 `SYMBOL_VOLUME_MAX` 触发 fallback。
3. **`SYMBOL_TRADE_TICK_SIZE=0` 时 fallback 到 `SYMBOL_VOLUME_MIN`** — spec line 47-49。**会"开 0.01 手"作为 fallback**，不等同于"算不出来"。剥头皮场景如果 tick_size=0 是 broker bug，1 笔 fallback = 0.01 手可能违反风险规则。建议在 lot > 0 后**再用 `_Normalize` clamp 一次**（当前 spec 已做，line 97）。
4. **多品种 EA 切换 `_Symbol` 必须每次重算** — sizing 内部按 `_Symbol` 读 tick value，**不需要重新 Init**。但如果 EA 在 OnInit 时初始化 sizing 然后切 symbol，**sizing 实例本身不变**，每次调用 `LotByRisk` 都会重算（spec line 41-44 每次重读 `SymbolInfoDouble`）。
5. **`LotByBalancePercent` 是"按余额比例"不是"按风险"** — spec line 77-88。剥头皮不要用（保证金可能 100% 占用）。**仅适合趋势 EA 资金管理**（如"账户余额 10% 作为保证金开仓"），不适合剥头皮高频。
6. **`sizing.Init(RiskPct)` 漏调** — `_riskPct` 默认 0.01（spec line 29），但 `LotByRisk(riskPct, slDist)` 的 `riskPct` 参数**优先于** `_riskPct`（spec line 36 用传入参数，不读 `_riskPct`）。所以 `Init` 漏调不影响 `LotByRisk` 直接传参，但**影响 `LotByRiskDefault` 用 `_riskPct`**（spec line 59-61）。

### 反模式（5 条禁止）

1. **硬编码 `pointVal = 10` 写死外汇** — XAUUSDm 1 point = $1.0，EURUSDm 1 pip = $10，**差 10x**。spec line 156 明确：**"永远用 `SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE)`"**。
2. **`lot = (riskMoney * 100) / slDist` 裸算** — 跳过 `_Normalize` clamp。算出来的 lot 可能超过 `SYMBOL_VOLUME_MAX` 或小于 `SYMBOL_VOLUME_MIN`，broker 会拒。**永远用 `sizing.LotByRisk`**（带 clamp）。
3. **`lot = 0.01` 固定手数（不调 risk%）** — 账户翻 10 倍仓位不翻 = 资金利用率下降；账户缩水 10 倍仓位不缩 = 爆仓风险。**风险% 是动态的**，固定手数违反 [[00-快速开始/EA 写之前要知道的 10 件事]] §6。
4. **`LotByBalancePercent` 用于剥头皮** — spec line 77-88 用余额 % 算保证金占用，剥头皮高频 = 一天 50 笔 × 5% 余额占用 = 250% 余额。**用 LotByRisk，剥头皮只关心单笔风险 %**。
5. **把 sizing 声明在 OnTick 里** — 每次 tick 重建对象，`_riskPct` 丢失回到默认 0.01。如果用户 input 改 0.5%，Init 后又被 OnTick 覆盖回 0.01。**sizing 必须是 per-EA 全局**（与 trade / risk 同生命周期）。

### 链向（待 T3 写 wiki）

- **[[实战/ScalperXAU wiki]]** — ScalperXAU.mq5 13 模块接入完整实战（剥头皮 M1 场景 / `InpRiskPercent=0.5%` / slDist 算价格距离范本）
- **[[实战/MeanReversion_EA wiki]]** — MeanReversion_EA.mq5 13 模块接入完整实战（4 品种同 sizing / tick value 自动适配 / M02 + M03 串联）
- **[[M01 交易封装 CTradePlus]]** — `sizing.LotByRisk` 的 lot 传给 `trade.Buy(lot, sl, tp, ...)`
- **[[M02 风控 Risk]]** — `risk.CanOpen` 在 sizing 算完 lot 之后调（sizing 算 → risk 查）
- **[[M08 追踪止损 TrailingStop]]** — sizing 算初始 lot，M08 追踪止损**不动 lot**（只动 SL）
- **[[10 件事 §6]]** — EA 写之前要知道的 10 件事 §6：单笔风险 ≤ 1-2% 净值（直接抄 M03.LotByRisk）

### 反向引用（实物 EA 接入 demo）

> **本节是 T1 18:00 任务（TrendMA_EA + Breakout_EA 联合 wiki v2）落地的反链**，由 [[实战/TrendMA_EA + Breakout_EA 接入报告]] §4.1 反链表 + §4.2 双向链接段添加。

- **[[实战/TrendMA_EA + Breakout_EA 接入报告]]** — TrendMA + Breakout 2 EA 联合接入报告（**v2 修正版 / 12+11 模块**）：TrendMA `sizing.LotByRisk(RiskPct, slDist)` L140（input `RiskPct=0.01` L31 / `SL_Points=300` L33 / slDist = `MathAbs(price - sl)` 价格距离范本）+ Breakout **`sizing.LotByRiskDefault(sl)`** L134+L141（**注意**: Breakout 不用 `LotByRisk(...)` 显式传 pct, 用 stored `_riskPct` 通过 `LotByRiskDefault`）。**最小 1% 风险 + 2:1 RR 范本**——2 EA 方法签名不同。
- **本 wiki 实战段 5+ 陷阱对应**：2 EA 共享陷阱 1（slDist 单位: `MathAbs(price - sl)` 价格距离不是 points 数字）+ 陷阱 5（sizing 是 per-EA 全局, **不是 per-tick**）；2 EA 都已避开陷阱 2（_Normalize MathFloor 范本已用）+ 陷阱 3（tick_size=0 fallback 已用）+ 陷阱 4（多品种切 _Symbol 已用）。
- **未来 P1 接入**：本 2 EA 当前没接 M13 FileIO + M19 SessionFilter + M17 NewsFilter——[[实战/TrendMA_EA + Breakout_EA 接入报告]] §6 反模式 5 提示"未来 P1 接入 M17"作为黑天鹅核心防御。
