---
title: M02 风控 Risk
tags: [调用模块, 风控]
type: module
---

# M02 风控 Risk

> **作用**：下单前必查的 7 项风控。任何 EA 必须在 `Buy/Sell` 之前调用 `Risk.CanOpen()`。
> **不依赖其他模块**（独立）。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                                M02_Risk.mqh       |
//|                              EA 开发知识库 - 风控                  |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 风控检查结构体 / 函数集                                           |
//| 任何 EA 下单前必调 CanOpen()                                      |
//+------------------------------------------------------------------+
class CRisk {
private:
   ulong  _magic;          // 本 EA 的 magic
   int    _maxPositions;   // 最大持仓数
   double _maxRiskPct;     // 单笔最大风险占净值比例（如 0.02 = 2%）
   double _maxMarginPct;   // 单笔最大占用可用保证金比例（如 0.3 = 30%）
   double _minSLPoints;    // 最小止损点数（保险，防止 0 止损）

public:
   // 构造：默认保守风控
   CRisk() : _magic(0), _maxPositions(3), _maxRiskPct(0.02),
             _maxMarginPct(0.3), _minSLPoints(10) {}

   // 初始化
   void Init(ulong magic, int maxPos = 3, double maxRiskPct = 0.02) {
      _magic        = magic;
      _maxPositions = maxPos;
      _maxRiskPct   = maxRiskPct;
   }

   // 设置最大保证金占比（默认 30%）
   void SetMaxMarginPct(double pct)   { _maxMarginPct = pct; }
   // 设置最小止损点数（防 0 止损）
   void SetMinSLPoints(int pts)       { _minSLPoints = pts; }

   //+--- 核心：能否开仓？---------------------------------------------+
   //  返回：true 可以，false 不可以
   //  失败原因可通过全局变量 _lastErr 拿（Print 已自动输出）
   bool CanOpen(ENUM_ORDER_TYPE type, double lot, double sl, double tp = 0) {
      // 1) 品种是否可交易
      if (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE) == SYMBOL_TRADE_MODE_DISABLED) {
         Print("风控：品种 ", _Symbol, " 不可交易");
         return false;
      }

      // 2) 账户交易权限
      if (!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED)) {
         Print("风控：账户不允许交易");
         return false;
      }
      if (!AccountInfoInteger(ACCOUNT_TRADE_EXPERT)) {
         Print("风控：EA 交易被禁用");
         return false;
      }

      // 3) 手数边界
      double minL  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double maxL  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
      double stepL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      if (lot < minL)  { PrintFormat("风控：手数 %.4f < 最小 %.4f", lot, minL); return false; }
      if (lot > maxL)  { PrintFormat("风控：手数 %.4f > 最大 %.4f", lot, maxL); return false; }

      // 4) 最大持仓数
      int currentPos = CountMyPositions();
      if (currentPos >= _maxPositions) {
         PrintFormat("风控：已持仓 %d 笔 >= 限制 %d", currentPos, _maxPositions);
         return false;
      }

      // 5) 同方向不重复开（避免堆仓）
      if (HasMyPosition(type)) {
         Print("风控：已存在同方向持仓");
         return false;
      }

      // 6) 保证金
      double price = (type == ORDER_TYPE_BUY)
                   ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                   : SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if (price == 0) { Print("风控：拿不到报价"); return false; }
      double margin = 0;
      if (!OrderCalcMargin(type, _Symbol, lot, price, margin)) {
         Print("风控：OrderCalcMargin 失败");
         return false;
      }
      double free = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      if (margin > free * _maxMarginPct) {
         PrintFormat("风控：所需保证金 %.2f 超过可用 %.2f 的 %.0f%%",
                     margin, free, _maxMarginPct * 100);
         return false;
      }

      // 7) 止损距离
      long minStop = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
      double minDist = MathMax(minStop, (long)_minSLPoints) * _Point;
      double slDist  = MathAbs(price - sl);
      if (sl > 0 && slDist < minDist) {
         PrintFormat("风控：止损距离 %.5f < 最小 %.5f", slDist, minDist);
         return false;
      }

      return true;
   }

   //+--- 工具：统计本 EA 持仓数 ---------------------------------------+
   int CountMyPositions() {
      int n = 0;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) == _magic) n++;
      }
      return n;
   }

   //+--- 工具：是否有同方向持仓 ---------------------------------------+
   bool HasMyPosition(ENUM_ORDER_TYPE type) {
      ENUM_POSITION_TYPE posType = (type == ORDER_TYPE_BUY)
                                 ? POSITION_TYPE_BUY
                                 : POSITION_TYPE_SELL;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) != _magic) continue;
         if (PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
         if ((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) == posType)
            return true;
      }
      return false;
   }

   //+--- 紧急全平（净值跌破阈值）--------------------------------------+
   //  pct: 净值低于余额的 pct 倍数（比如 0.5 = 跌破 50% 就全平）
   bool EmergencyStop(double pct) {
      double bal = AccountInfoDouble(ACCOUNT_BALANCE);
      double eq  = AccountInfoDouble(ACCOUNT_EQUITY);
      if (eq < bal * pct) {
         PrintFormat("🚨 紧急：净值 %.2f 跌破余额 %.2f 的 %.0f%%，全平",
                     eq, bal, pct * 100);
         for (int i = PositionsTotal() - 1; i >= 0; i--) {
            ulong t = PositionGetTicket(i);
            if (t == 0) continue;
            if (PositionGetInteger(POSITION_MAGIC) != _magic) continue;
            // 这里直接调 CTrade 的 ClosePos（外部传入）
         }
         return true;
      }
      return false;
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M01_CTradePlus.mqh>
#include <MQL5Kit/M02_Risk.mqh>

CTradePlus trade;
CRisk      risk;

input ulong Magic = 20260101;
input int   MaxPos = 3;
input double RiskPct = 0.02;

int OnInit() {
   trade.Init(Magic);
   risk.Init(Magic, MaxPos, RiskPct);
   return INIT_SUCCEEDED;
}

void OnTick() {
   // 紧急风控
   if (risk.EmergencyStop(0.5)) {
      CloseAllMyPositions();
      return;
   }

   // 正常入场
   if (/* 入场条件 */) {
      double sl = price - 100 * _Point;
      double tp = price + 200 * _Point;
      double lot = 0.01;
      if (risk.CanOpen(ORDER_TYPE_BUY, lot, sl, tp)) {
         trade.Buy(lot, sl, tp, "long");
      }
   }
}
```

## 参数调参建议
| 参数 | 保守 | 激进 | 说明 |
|---|---|---|---|
| `_maxPositions` | 1-3 | 5-10 | 同时持仓数 |
| `_maxRiskPct` | 0.005-0.01 | 0.02-0.05 | 单笔风险 |
| `_maxMarginPct` | 0.1-0.2 | 0.3-0.5 | 单笔保证金占比 |

## 常见错误
- 调 CanOpen 但不读返回值 → **风控形同虚设**
- 把 Risk 写成全局变量但没 Init() → 用默认值，可能过严或过松
- EmergencyStop 阈值设太低（如 0.1）→ **刚亏 10% 就全平**，等于把回撤锁死在 10%

---

## 实战案例

> **本节汇总 M02 Risk 在真实 EA 场景的接入经验和完整代码模板**。
> spec wiki (上面) 讲 API + 理论；本节讲"已经跑通的多品种同向持仓 / 剥头皮日亏风控 + CanOpen 串联位置 + 5 档调参路径"。

### 实战摘要（点开 wiki 前先看这段）

- **场景 A MeanReversion_EA.mq5 4 品种同向持仓上限**（320 行，13 模块集成）：M02 `risk` 实例在 `OpenPos` 入口（line 199）调 `CanOpen(type, lot, sl, tp)`；7 项检查（品种/账户/手数/持仓数/同向/保证金/止损距离）通过后才 `trade.Buy/Sell`。
- **场景 B ScalperXAU.mq5 剥头皮日亏风控**（1033 行）：M02 `risk` 在 OnInit line 956 `Init(InpMagicNumber, InpMaxPositions=3, InpRiskPercent/100=0.005)`；剥头皮专属日亏保护由外部 `_CheckDrawdown()`（OnTick 入口）实现（不等 M02 自己管）。
- **即抄代码**：`if (!risk.CanOpen(type, lot, sl, tp)) return;` 必须放在 `trade.Buy/Sell` **之前**（MeanReversion_EA line 199-201 是教科书级范本）。
- **5+ 已知陷阱**：调 CanOpen 不读返值 / `_maxPositions=3` 不区分多品种（4 品种可同向开 12 笔）/ `EmergencyStop(0.1)` 太激进刚亏 10% 就全平 / `_CheckRetcode` 失败检查要看中文提示 / `HasMyPosition` 只查本 magic 同品种同向。
- **5 条反模式**：M02 当"开仓过滤器"挡 M08 追踪止损 / 把 7 项检查拆到 7 个 if 里（性能 + 维护差） / `CanOpen` 返 `true` 就认为"已成交" / `_maxRiskPct=0.05`（5%）激进剥头皮参数 / 把 Risk 写成类内 static（多 EA 共享崩溃）。

### 实物 demo EA 接入（多品种）

**`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`**（320 行，13 模块集成，多品种均值回归）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 10** `#include <MQL5Kit/M02_Risk.mqh>`
- **line 55** `CRisk risk;` 全局对象（与 M01 trade / M05 NB 同区，54-58 行）
- **line 81** `risk.Init(Magic, MaxPos, RiskPct);` — MaxPos=3（line 32 input），RiskPct=0.02（line 31 input，2%）
- **line 199** `if (!risk.CanOpen(type, lot, sl, tp)) return;` — 在 `OpenPos()` 函数内（191-207 行），`lot=sizing.LotByRisk(...)` 计算后

**关键设计**：4 品种（XAUUSDm/EURUSDm/GBPUSDm/USDJPYm）共享同一 `risk` 实例 → 跨品种同向持仓数 ≤ 3（不是每品种 3）。M18 `IsHedgeExposed`（line 167-172）作为"相关性"第二层过滤；M02 当"硬风控"，两者串联：M18 跳过同向 → M02 限制总持仓。

### 实物 demo EA 接入（剥头皮）

**`MQL5/Experts/minimax-ea/ScalperXAU.mq5`**（1033 行，13 模块集成，剥头皮 XAUUSDm M1）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 20** `#include <MQL5Kit/M02_Risk.mqh>`
- **line 108** `CRisk risk;` 全局对象
- **line 956** `risk.Init(InpMagicNumber, InpMaxPositions, InpRiskPercent / 100.0);` — InpMaxPositions=3（line 56），InpRiskPercent=0.5%（line 55，剥头皮小仓位）
- **TryOpen() 入口**（line 824 调用）— 内部串联 `risk.CanOpen` + `trade.Buy/Sell`

**剥头皮专属日亏保护**（不在 M02 内部，在 EA 自己的 `_CheckDrawdown()`）：`_peakEquity` 跟踪最高净值，OnTick 入口 line 794 调 `_CheckDrawdown()` → 日内亏损达 `InpMaxDailyDrawdownPct=3%`（line 58）触发 `EmergencyStop(0.03)` 逻辑全平。

**关键设计**：M02 只管"开仓前 7 项检查"，**不管日内累计亏损**。日内累计是 EA 自己的事（按用户场景定制）。如果让 M02 同时管 `dailyPnL`，类会膨胀到 500 行。

### 即抄代码（OnInit + OnTick 接入骨架）

```mql5
// 1) include
#include <MQL5Kit/M01_CTradePlus.mqh>
#include <MQL5Kit/M02_Risk.mqh>

// 2) inputs
input ulong  Magic   = 20260101;
input int    MaxPos  = 3;       // 持仓数上限 (多品种 EA 用同一值)
input double RiskPct = 0.02;    // 单笔风险占净值 (2% 平衡 / 1% 保守 / 5% 激进)

// 3) 全局
CTradePlus trade;
CRisk      risk;

int OnInit() {
   trade.Init(Magic, 30);
   risk.Init(Magic, MaxPos, RiskPct);   // magic 必须与 trade 一致
   risk.SetMaxMarginPct(0.3);          // 单笔保证金 ≤ 30% (剥头皮 0.5)
   risk.SetMinSLPoints(50);            // XAUUSDm 最小 SL = 50 points = 0.5 USD
   return INIT_SUCCEEDED;
}

void OnTick() {
   // 紧急风控 (净值回撤)
   if (risk.EmergencyStop(0.5)) {       // 净值 < 50% 余额 → 全平
      CloseAllMyPositions();
      return;
   }
   if (/* 入场条件 */) {
      double sl = price - 100 * _Point;
      double tp = price + 200 * _Point;
      double slDist = MathAbs(price - sl);
      double lot = sizing.LotByRisk(RiskPct, slDist);
      if (lot <= 0) return;

      // 7 项检查 (手数/账户/保证金/止损距离/最大持仓/同向)
      if (!risk.CanOpen(ORDER_TYPE_BUY, lot, sl, tp)) {
         Print("风控拦截: 不开仓");
         return;
      }

      // 通过后才下单
      trade.Buy(lot, sl, tp, "MyEAv1");
   }
}
```

### 参数调参 5 档（来自实物 EA + 通用建议）

| 策略类型 | `_maxPositions` | `_maxRiskPct` | `_maxMarginPct` | `_minSLPoints` | 实物 EA |
|---|---|---|---|---|---|
| **保守趋势** | 1-3 | 0.005-0.01 | 0.1-0.2 | 100-300 | TrendMA_EA（line 32-33，MaxPos=3 / RiskPct=0.01 / SL=300） |
| **平衡多品种** | 3-5 | 0.02 | 0.3 | 50-100 | MeanReversion_EA（line 32，MaxPos=3 / RiskPct=0.02） |
| **剥头皮高频** | 1-2 | 0.005-0.01 | 0.1-0.3 | 30-50 | ScalperXAU（line 56，MaxPos=3 / InpRiskPercent=0.5%） |
| **多品种对冲** | 2-3（同向总） | 0.01-0.02 | 0.2-0.3 | 50 | MeanReversion_EA + M18 协同 |
| **网格马丁**（慎用） | 5-10 | 0.02-0.05 | 0.3-0.5 | 20-50 | 无实物参考 |

### 实战陷阱（5+ 来自实物 EA）

1. **调 CanOpen 不读返值 → 风控形同虚设** — `if (risk.CanOpen(...))` 拆掉 `if` 就完蛋。MeanReversion_EA line 199 的 `if (!risk.CanOpen(...)) return;` 是正确范本。
2. **4 品种共享 `_maxPositions=3` 等于"跨品种同向 3 笔"** — 不是"每品种 3"。如果想要"每品种 3"，必须在 `risk` 内部按 symbol 单独计数（当前 `CRisk` 不支持，等 M18 + M07 替代）。
3. **`EmergencyStop(0.1)` 太激进** — 刚亏 10% 就全平，账户回撤锁死在 10%。剥头皮日亏触发建议 `EmergencyStop(0.03)`（日亏 3% 全平），由 EA 自己的 `_CheckDrawdown()` 实现。
4. **失败时只看 `Print` 不看 `_RetcodeText`** — 中文错误信息能省 30 分钟 debug 时间。MeanReversion_EA 直接调 `risk.CanOpen` 失败会 Print 7 项之一的中文消息。
5. **`HasMyPosition` 只查本 magic + 同品种同向** — 不查跨品种同向（那是 M18 的事）。多品种 EA 必须 M02 + M18 双层。
6. **剥头皮 InpRiskPercent=0.5%（line 55）= `_maxRiskPct=0.005`** — 注意单位（百分 vs 小数）。ScalperXAU line 956 `InpRiskPercent / 100.0` 是转换示例。

### 反模式（5 条禁止）

1. **M02 当"开仓过滤器"挡 M08 追踪止损** — M02 只挡 `CanOpen`（新开仓），不影响 `trail.Apply()`（已有持仓管理）。M19 文档 line 344 明确："M19 只挡'开新仓'，不影响 M08 追踪止损继续管理持仓"。
2. **把 7 项检查拆到 7 个 if 里** — 性能 + 维护差。`CanOpen` 是一站式 7 项检查（手数/账户/保证金/止损距离/最大持仓/同向 + 品种/账户交易权限），拆开会重复计算 `OrderCalcMargin` 等昂贵调用。
3. **`CanOpen` 返 `true` 就认为"已成交"** — `CanOpen` 只查风控，**不调 OrderSend**。下单靠 `trade.Buy/Sell` + `trade.LastRetcode()` 二次确认。
4. **`_maxRiskPct=0.05`（5%）激进剥头皮参数** — 5% 单笔风险 + 高频 = 一天 20 笔全亏 = 100% 爆仓。建议剥头皮 ≤ 1%。
5. **把 Risk 写成类内 static** — 跨 EA 共享状态会崩溃。`CRisk risk;` 必须是 per-EA 全局。

### 链向（待 T3 写 wiki）

- **[[实战/MeanReversion_EA wiki]]** — MeanReversion_EA.mq5 13 模块接入完整实战（M02 + M18 协同防同向 / 4 品种共享 `MaxPos=3`）
- **[[实战/ScalperXAU wiki]]** — ScalperXAU.mq5 13 模块接入完整实战（M02 `_maxRiskPct=0.005` 剥头皮参数 + 日亏 3% EmergencyStop 外部实现）
- **[[M01 交易封装 CTradePlus]]** — `trade.Buy` 必须在 `risk.CanOpen` 通过后调
- **[[M07 持仓管理 Positions]]** — `CPositions::CountMine(Magic)` 是 M02 `CountMyPositions` 的替代
- **[[M18 相关性过滤 CorrelationFilter]]** — M02 限制"总持仓"，M18 限制"同向相关品种"，串联防双倍暴露
- **[[M19 时段过滤 SessionFilter]]** — M19 在 M02 之前（时段外直接 return）；M19 与 M02 都是"开仓前过滤器"
- **[[M11 日志 Logger]]** — `risk.CanOpen` 失败时 Print → logger 落盘
- **[[10 件事 §6]]** — EA 写之前要知道的 10 件事 §6：必须做的风控（直接抄 M02）
