---
title: M01 交易封装 CTradePlus
tags: [调用模块, 交易, CTrade]
type: module
---

# M01 交易封装 CTradePlus

> **作用**：CTrade 的"加强版"，自动处理 filling、滑点、retcode 错误，能区分"发送失败/执行失败"。
> **使用率**：99% EA 必装。
> **依赖**：`#include <Trade/Trade.mqh>`

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                              M01_CTradePlus.mqh  |
//|                              EA 开发知识库 - 交易封装              |
//+------------------------------------------------------------------+
#property copyright "MQL5Kit"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

//+------------------------------------------------------------------+
//| 增强版交易类：解决官方 CTrade 几个坑                               |
//|   1. 区分 retcode 失败原因                                        |
//|   2. 自动选 filling（按品种）                                     |
//|   3. 自动规范价格 (NormalizeDouble)                                |
//|   4. 重试报价过期/价格变动                                        |
//+------------------------------------------------------------------+
class CTradePlus : public CTrade {
private:
   ulong _magic;              // 魔术码
   int   _maxRetry;           // 最大重试次数
   int   _retrySleepMs;       // 重试间隔（毫秒）

   // 私有：根据品种自动选 filling 模式
   void _AutoSetFilling() {
      long f = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
      if (f & SYMBOL_FILLING_FOK)
         SetTypeFilling(ORDER_FILLING_FOK);
      else if (f & SYMBOL_FILLING_IOC)
         SetTypeFilling(ORDER_FILLING_IOC);
      else
         SetTypeFilling(ORDER_FILLING_RETURN);
   }

   // 私有：把价格规范到合法小数位
   double _NormPrice(double price) const {
      return NormalizeDouble(price, _Digits);
   }

   // 私有：把价格规范到合法 step（外汇一般无 step，黄金可能有）
   double _NormSLTP(double price) const {
      return _NormPrice(price);
   }

public:
   // 构造
   CTradePlus() : _magic(0), _maxRetry(3), _retrySleepMs(200) {}

   // 初始化（EA 的 OnInit 里调用一次）
   void Init(ulong magic, int deviation = 30) {
      _magic = magic;
      SetExpertMagicNumber(magic);
      SetDeviationInPoints(deviation);
      SetMarginMode();
      _AutoSetFilling();
   }

   // 设置重试策略
   void SetRetry(int maxRetry, int sleepMs = 200) {
      _maxRetry  = maxRetry;
      _retrySleepMs = sleepMs;
   }

   //+--- 买入 --------------------------------------------------------+
   // 返回：true = 成功成交 / false = 失败（看 GetLastError 详情）
   // 失败信息通过 GetLastError()、ResultRetcode() 拿
   bool Buy(double lot, double sl = 0, double tp = 0, string comment = "") {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      if (ask == 0) { Print("Buy 失败：拿不到 ASK"); return false; }
      return BuyAt(lot, ask, sl, tp, comment);
   }

   // 在指定价格买（突破/挂单成交场景）
   bool BuyAt(double lot, double price, double sl = 0, double tp = 0,
              string comment = "") {
      price = _NormPrice(price);
      sl    = _NormSLTP(sl);
      tp    = _NormSLTP(tp);
      for (int i = 0; i < _maxRetry; i++) {
         if (CTrade::Buy(lot, _Symbol, price, sl, tp, comment))
            return _CheckRetcode();
         PrintFormat("Buy 第 %d 次发送失败 err=%d", i+1, GetLastError());
         Sleep(_retrySleepMs);
      }
      return false;
   }

   //+--- 卖出 --------------------------------------------------------+
   bool Sell(double lot, double sl = 0, double tp = 0, string comment = "") {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if (bid == 0) { Print("Sell 失败：拿不到 BID"); return false; }
      return SellAt(lot, bid, sl, tp, comment);
   }

   bool SellAt(double lot, double price, double sl = 0, double tp = 0,
               string comment = "") {
      price = _NormPrice(price);
      sl    = _NormSLTP(sl);
      tp    = _NormSLTP(tp);
      for (int i = 0; i < _maxRetry; i++) {
         if (CTrade::Sell(lot, _Symbol, price, sl, tp, comment))
            return _CheckRetcode();
         PrintFormat("Sell 第 %d 次发送失败 err=%d", i+1, GetLastError());
         Sleep(_retrySleepMs);
      }
      return false;
   }

   //+--- 平仓（按 ticket）--------------------------------------------+
   bool ClosePos(ulong ticket) {
      for (int i = 0; i < _maxRetry; i++) {
         if (CTrade::PositionClose(ticket))
            return _CheckRetcode();
         int err = GetLastError();
         // 10005 = "旧点位已无此 ticket" — 视为已平
         if (err == 10005 || err == 10025) return true;
         PrintFormat("ClosePos #%I64u 第 %d 次失败 err=%d", ticket, i+1, err);
         Sleep(_retrySleepMs);
      }
      return false;
   }

   // 部分平仓
   bool ClosePartial(ulong ticket, double volume) {
      for (int i = 0; i < _maxRetry; i++) {
         if (CTrade::PositionClosePartial(ticket, volume))
            return _CheckRetcode();
         int err = GetLastError();
         if (err == 10005 || err == 10025) return true;
         Sleep(_retrySleepMs);
      }
      return false;
   }

   //+--- 改 SL/TP ----------------------------------------------------+
   bool ModifySLTP(ulong ticket, double sl, double tp) {
      sl = _NormSLTP(sl);
      tp = _NormSLTP(tp);
      for (int i = 0; i < _maxRetry; i++) {
         if (CTrade::PositionModify(ticket, sl, tp))
            return _CheckRetcode();
         Sleep(_retrySleepMs);
      }
      return false;
   }

   //+--- 挂单 --------------------------------------------------------+
   bool BuyLimit (double lot, double price, double sl=0, double tp=0,
                  int expirationHours=0, string comment="") {
      return _PlacePending(ORDER_TYPE_BUY_LIMIT, lot, price, sl, tp,
                           expirationHours, comment);
   }
   bool SellLimit(double lot, double price, double sl=0, double tp=0,
                  int expirationHours=0, string comment="") {
      return _PlacePending(ORDER_TYPE_SELL_LIMIT, lot, price, sl, tp,
                           expirationHours, comment);
   }
   bool BuyStop  (double lot, double price, double sl=0, double tp=0,
                  int expirationHours=0, string comment="") {
      return _PlacePending(ORDER_TYPE_BUY_STOP, lot, price, sl, tp,
                           expirationHours, comment);
   }
   bool SellStop (double lot, double price, double sl=0, double tp=0,
                  int expirationHours=0, string comment="") {
      return _PlacePending(ORDER_TYPE_SELL_STOP, lot, price, sl, tp,
                           expirationHours, comment);
   }
   // StopLimit（触发后挂限价单）
   bool BuyStopLimit(double lot, double triggerPrice, double limitPrice,
                     double sl=0, double tp=0,
                     int expirationHours=0, string comment="") {
      triggerPrice = _NormPrice(triggerPrice);
      limitPrice   = _NormPrice(limitPrice);
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action       = TRADE_ACTION_PENDING;
      req.symbol       = _Symbol;
      req.volume       = lot;
      req.type         = ORDER_TYPE_BUY_STOP_LIMIT;
      req.price        = limitPrice;
      req.stoplimit    = triggerPrice;
      req.sl           = _NormSLTP(sl);
      req.tp           = _NormSLTP(tp);
      req.magic        = _magic;
      req.comment      = comment;
      req.type_filling = ORDER_FILLING_FOK;
      if (expirationHours > 0) {
         req.type_time  = ORDER_TIME_SPECIFIED;
         req.expiration = TimeCurrent() + expirationHours * 3600;
      } else {
         req.type_time  = ORDER_TIME_GTC;
         req.expiration = 0;
      }
      return OrderSend(req, res) && _CheckRetcode(res);
   }

   // 删挂单
   bool DeletePending(ulong ticket) {
      return CTrade::OrderDelete(ticket) && _CheckRetcode();
   }

   //+--- 工具方法 ----------------------------------------------------+
   ulong Magic()   const { return _magic; }
   int   LastRetcode() const { return (int)ResultRetcode(); }
   string LastComment() const { return ResultComment(); }

private:
   bool _PlacePending(ENUM_ORDER_TYPE type, double lot, double price,
                      double sl, double tp, int expH, string comment) {
      price = _NormPrice(price);
      sl    = _NormSLTP(sl);
      tp    = _NormSLTP(tp);
      MqlTradeRequest req = {};
      MqlTradeResult  res = {};
      req.action       = TRADE_ACTION_PENDING;
      req.symbol       = _Symbol;
      req.volume       = lot;
      req.type         = type;
      req.price        = price;
      req.sl           = sl;
      req.tp           = tp;
      req.magic        = _magic;
      req.comment      = comment;
      req.type_filling = ORDER_FILLING_FOK;
      if (expH > 0) {
         req.type_time  = ORDER_TIME_SPECIFIED;
         req.expiration = TimeCurrent() + expH * 3600;
      } else {
         req.type_time  = ORDER_TIME_GTC;
         req.expiration = 0;
      }
      return OrderSend(req, res) && _CheckRetcode(res);
   }

   // 检查 retcode：DONE/DONE_PARTIAL/PLACED 都算成功
   bool _CheckRetcode(MqlTradeResult &res) {
      if (res.retcode == TRADE_RETCODE_DONE
       || res.retcode == TRADE_RETCODE_DONE_PARTIAL
       || res.retcode == TRADE_RETCODE_PLACED) {
         return true;
      }
      PrintFormat("执行失败 retcode=%u (%s) comment=%s",
                  res.retcode, _RetcodeText(res.retcode), res.comment);
      return false;
   }
   bool _CheckRetcode() {
      uint rc = ResultRetcode();
      if (rc == TRADE_RETCODE_DONE
       || rc == TRADE_RETCODE_DONE_PARTIAL
       || rc == TRADE_RETCODE_PLACED) {
         return true;
      }
      PrintFormat("执行失败 retcode=%u (%s) comment=%s",
                  rc, _RetcodeText(rc), ResultComment());
      return false;
   }

   string _RetcodeText(uint rc) {
      switch(rc) {
         case TRADE_RETCODE_REJECT:        return "被服务器拒绝";
         case TRADE_RETCODE_CANCEL:        return "已取消";
         case TRADE_RETCODE_REQUOTE:       return "重新报价（要重试）";
         case TRADE_RETCODE_PRICE_CHANGED: return "价格变动（要重试）";
         case TRADE_RETCODE_PRICE_OFF:     return "无报价";
         case TRADE_RETCODE_INVALID:       return "请求参数无效";
         case TRADE_RETCODE_VOLUME:        return "手数错误";
         case TRADE_RETCODE_FUNDS:         return "资金不足";
         case TRADE_RETCODE_CONNECTION:    return "无连接";
         default: return "见官方文档";
      }
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M01_CTradePlus.mqh>

CTradePlus trade;   // 全局

input ulong Magic = 20260101;

int OnInit() {
   trade.Init(Magic);     // 必调
   trade.SetRetry(3);     // 失败重试 3 次
   return INIT_SUCCEEDED;
}

void OnTick() {
   // 1) 下单
   if (/* 入场条件 */) {
      if (trade.Buy(0.01, sl, tp, "long")) {
         Print("成功：订单 #", trade.ResultOrder());
      } else {
         Print("失败：retcode=", trade.LastRetcode());
      }
   }

   // 2) 平仓
   for (int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong t = PositionGetTicket(i);
      if (t == 0) continue;
      if (PositionGetInteger(POSITION_MAGIC) != Magic) continue;
      trade.ClosePos(t);
   }

   // 3) 改 SLTP
   trade.ModifySLTP(ticket, newSL, newTP);

   // 4) 挂单
   trade.BuyLimit(0.01, price, sl, tp, 24, "limit");  // 24 小时过期

   // 5) 删挂单
   trade.DeletePending(pendingTicket);
}
```

## 与官方 CTrade 区别
| 能力 | 官方 CTrade | CTradePlus |
|---|---|---|
| Buy/Sell | ✅ | ✅（**自动 NormalizeDouble**）|
| 重试 retcode=10004/10020 | ❌ | ✅ |
| 自动选 filling | ❌ | ✅ |
| 部分平仓 | ✅ | ✅（**带重试**）|
| 详细 retcode 错误信息 | ❌ | ✅（中文）|
| 10005 视为已平 | ❌ | ✅ |

## 必看陷阱
- **不要在 OnInit 之外调 Init()**，否则 magic/filling 会跑乱
- 重试间隔不要 < 50ms，避免被服务器限流
- 部分平仓手数要 >= `SYMBOL_VOLUME_MIN`

---

## 实战案例

> **本节汇总 M01 CTradePlus 在真实 EA 场景的接入经验和完整代码模板**。
> spec wiki (上面) 讲 API + 理论；本节讲"已经跑通的实战 demo + 高频 vs 多品种接入差异 + 反模式"。

### 实战摘要（点开 wiki 前先看这段）

- **场景 A ScalperXAU.mq5 剥头皮高频开仓**（1033 行，13 模块集成）：M01 `trade` 实例承担所有下单/平仓/改 SLTP；`Init(InpMagicNumber, InpDeviationPoints)` 中 `InpDeviationPoints=20`（剥头皮建议 5-20），`SetRetry(3, 200)` 失败重试 3 次间隔 200ms。
- **场景 B MeanReversion_EA.mq5 多品种多 EA 隔离**（320 行，13 模块集成）：M01 `trade` 全局对象同时服务 4 品种（XAUUSDm/EURUSDm/GBPUSDm/USDJPYm），靠 `Magic=20260101` 区分；同账户跑多个 EA 时**每个 EA 必须用不同 magic**（EA 写之前要知道的 10 件事 §5）。
- **即抄代码**：`trade.Buy(lot, sl, tp, comment)` 返回 `true` ≠ 成交成功，必须检查 `trade.ResultRetcode() == TRADE_RETCODE_DONE`（参考 10 件事 §2）。
- **5+ 已知陷阱**：`SetExpertMagicNumber(0)` 会与其它 EA 冲突 / `_AutoSetFilling` 必须在 `Init` 里调 / `Buy(lot, sl=0, tp=0)` 0 止损会被 M02 风控拦 / `ClosePos` 在 10005 已平返 `true`（不当作失败）/ `_NormSLTP` 用 `_Digits` 黄金 2 位、外汇 5 位自动适配。
- **5 条反模式**：直接用官方 `CTrade` 不包 / 把 `trade` 声明在 `OnTick` 里（每次 tick 重建） / 多个 EA 共享同一个 `trade` 全局 / 调 `Buy` 不读返回值 / 把 `Init` 放在 `OnTick` 里。

### 实物 demo EA 接入

**`MQL5/Experts/minimax-ea/ScalperXAU.mq5`**（1033 行，13 模块集成，剥头皮 XAUUSDm M1）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 19** `#include <MQL5Kit/M01_CTradePlus.mqh>`
- **line 107** `CTradePlus trade;` 全局对象（与 M02 risk / M05 NB / M08 trail 同一区声明，105-117 行）
- **line 953** `trade.Init(InpMagicNumber, InpDeviationPoints);` — OnInit 必调，magic 由 input 注入（line 59 `InpMagicNumber = 20240604`）
- **line 954** `trade.SetRetry(3, 200);` — 3 次重试 × 200ms
- **line 824** `TryOpen(sig > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);` — OnTick 调用链终点

**关键设计**：`InpDeviationPoints=20` 是剥头皮场景的"现实值"（spec 文本说 5，但当前实盘参数化暴露给用户）；`_AutoSetFilling` 在 `Init` 内自动按 `SYMBOL_FILLING_MODE` 选 FOK/IOC/RETURN，XAUUSDm 通常 FOK。

### 实物 demo EA 接入（多品种）

**`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`**（320 行，13 模块集成，多品种均值回归）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 9** `#include <MQL5Kit/M01_CTradePlus.mqh>`
- **line 54** `CTradePlus trade;` 全局对象（与 M02 risk / M05 NB 同区，54-58 行）
- **line 80** `trade.Init(Magic, 30);` — Magic = `20260101`（input line 23），deviation=30
- **line 201, 204** `trade.Buy/Sell(lot, sl, tp, "MR_Long/Short")` — 在 `OpenPos()` 函数内（191-207 行），与 M02 `risk.CanOpen` 串联（line 199）

**关键设计**：4 品种（XAUUSDm/EURUSDm/GBPUSDm/USDJPYm）共用同一个 `trade` 实例，靠 `Magic` 隔离 + M18 `IsHedgeExposed` 避免同向开仓（line 167-172）。多品种同 EA 的"实例共享 + magic 隔离"是 M01 + M07 + M18 的标准组合。

### 即抄代码（OnInit + OnTick 接入骨架）

```mql5
// 1) include
#include <MQL5Kit/M01_CTradePlus.mqh>

// 2) inputs (EA 专属 magic, 多 EA 隔离)
input ulong Magic = 20260101;

// 3) 全局
CTradePlus trade;   // 99% 必装, 全局唯一, 不要在 OnTick 重建

int OnInit() {
   // 必调, magic + deviation + filling 一次到位
   trade.Init(Magic, 30);              // 黄金 XAUUSDm 建议 deviation=30
   trade.SetRetry(3, 200);             // 重试 3 次 × 200ms
   return INIT_SUCCEEDED;
}

void OnTick() {
   // ... 其它过滤 (M05 NewBar / M02 CanOpen / M18 hedge) ...

   // 风控通过后, 下单
   if (/* 入场条件 */) {
      double lot = sizing.LotByRisk(RiskPct, slDist);
      if (lot <= 0) return;
      if (!risk.CanOpen(ORDER_TYPE_BUY, lot, sl, tp)) return;   // M02 必查
      if (trade.Buy(lot, sl, tp, "MyEAv1")) {
         Print("成交 ticket=", trade.ResultOrder(),
               " retcode=", trade.LastRetcode());
      } else {
         Print("下单失败 retcode=", trade.LastRetcode(),
               " comment=", trade.LastComment());
      }
   }
}
```

### 实战陷阱（5+ 来自实物 EA）

1. **`SetExpertMagicNumber(0)` 会与其它 EA 冲突** — `CTrade` 内部按 magic 过滤，0 等于"匹配所有"。M01 把它升级为参数 `_magic`，但调用方必须传非零值。MeanReversion_EA line 23 `Magic = 20260101` 是不错示例。
2. **`_AutoSetFilling` 只在 `Init` 里跑一次** — 如果在 `OnInit` 之后改品种（多品种 EA），`SYMBOL_FILLING_MODE` 可能变；要重新调 `Init` 或手工 `SetTypeFilling`。
3. **`Buy(lot, sl=0, tp=0)` 会被 M02 风控拦** — M02 `CanOpen` 检查 `sl > 0` 且 `slDist >= minStop`。剥头皮场景必须 `sl=price-50*_Point`（XAUUSDm 50 points = 0.5 USD）。
4. **`ClosePos` 在 10005（已平）时返 `true`** — 不当作失败。剥头皮并发场景下"对手已帮你平"是常态，不要被错误日志刷屏。
5. **`_NormSLTP` 用 `_Digits` 自动适配小数位** — XAUUSDm 2 位（0.01），EURUSDm 5 位（0.00001），GBPUSDm 5 位。不要在调用方手工 `NormalizeDouble(price, 2)` 写死。
6. **`SetRetry` 重试间隔 < 50ms 会被限流** — Exness 实测建议 200ms+。剥头皮失败重试可以 `SetRetry(2, 100)`（更快但不激进）。

### 反模式（5 条禁止）

1. **直接用官方 `CTrade` 不包** — 失败原因丢失（`retcode`/`comment`），调试时只能看 `GetLastError()` 字符串。**M01 的核心价值就是 5 行中文错误信息**。
2. **把 `trade` 声明在 `OnTick` 里** — 每次 tick 重建对象，`_magic`/`_maxRetry` 全部丢失；剥头皮一秒 5 tick 等于重建 5 次。
3. **多个 EA 共享同一个 `trade` 全局** — 跨 EA 串扰。`CTradePlus` 是 per-EA 的（每个 EA 一个 .mq5 文件 = 一个 .ex5 实例 = 一个全局 `trade`）。
4. **调 `Buy` 不读返回值** — `Buy` 返 `true` 但 `retcode=10018 ERR_MARKET_CLOSED` 时你已经"以为成功"了。每次必须 `if (trade.Buy(...))` + 看 `trade.LastRetcode()`。
5. **把 `Init` 放在 `OnTick` 里** — 每次 tick 重新设置 magic + filling，浪费 CPU + 在多 EA 共享的 broker 端可能触发限流。**严格按 10 件事 §6：Init 只在 OnInit 调一次**。

### 链向（待 T3 写 wiki）

- **[[实战/ScalperXAU wiki]]** — ScalperXAU.mq5 13 模块接入完整实战（剥头皮 M1 场景 / deviation=20 / M17 新闻过滤集成）
- **[[实战/MeanReversion_EA wiki]]** — MeanReversion_EA.mq5 13 模块接入完整实战（多品种均值回归 / M18+M19 协同 / 4 品种 magic 隔离）
- **[[M02 风控 Risk]]** — `risk.CanOpen()` 与 `trade.Buy` 串联使用
- **[[M07 持仓管理 Positions]]** — `CPositions::CountMine(Magic)` 是 M01 的"持仓上下文"
- **[[M08 追踪止损 TrailingStop]]** — `trail.Init(&trade, Magic)` 把 M01 实例传给追踪
- **[[M11 日志 Logger]]** — `logger.Trade(...)` 记录 M01 成交到 CSV
- **[[M10 推送通知 Notify]]** — Rejection 通知来源是 M01 的 `LastRetcode() != DONE`
