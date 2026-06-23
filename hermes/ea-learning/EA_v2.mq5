//+------------------------------------------------------------------+
//|                                            EA_v2.mq5              |
//|        8 模块集成教学版 (M01+M02+M05+M08+M09+M10+M11+M19)         |
//|        策略: XAUUSD H1 RSI 均值回归 + 追踪止损 + 回撤熔断 + 时段过滤 |
//+------------------------------------------------------------------+
#property copyright "MQL5Kit-hermes"
#property version   "1.00"
#property strict
#property description "EA-learning v2: 8/12 vault 必读模块集成, XAUUSD H1 RSI 均值回归."
#property description "策略: H1 RSI(14) < 30 做多, > 70 做空; M08 追踪止损; M02 回撤熔断; M19 时段过滤."

//--- 8 个 MQL5Kit 必读模块 include (按 vault 12 必读顺序) -----------
#include <MQL5Kit/M01_CTradePlus.mqh>
#include <MQL5Kit/M02_Risk.mqh>
#include <MQL5Kit/M05_NewBar.mqh>
#include <MQL5Kit/M08_TrailingStop.mqh>
#include <MQL5Kit/M09_Dashboard.mqh>
#include <MQL5Kit/M10_Notify.mqh>
#include <MQL5Kit/M11_Logger.mqh>
#include <MQL5Kit/M19_SessionFilter.mqh>

//+------------------------------------------------------------------+
//| Inputs                                                            |
//+------------------------------------------------------------------+
input ulong  Magic = 20260612;                // 魔术号 (EA-learning 任务日期)

input group "=== 指标 (RSI 均值回归) ==="
input int    RSI_Period       = 14;           // RSI 周期
input int    RSI_Oversold     = 30;           // 超卖阈值 (做多信号)
input int    RSI_Overbought   = 70;           // 超买阈值 (做空信号)
input ENUM_TIMEFRAMES Timeframe = PERIOD_H1;  // 周期 (默认 H1)

input group "=== 仓位 (M02 风控) ==="
input double RiskPct          = 0.01;         // 单笔风险占账户比 (1%)
input int    MaxPositions     = 3;            // 最大同向持仓数
input int    SL_Points        = 500;          // 止损 points (XAUUSD 1pt=0.01)
input int    TP_Points        = 800;          // 止盈 points
input int    MinSLPoints      = 100;          // 最小止损 points (broker 防护)

input group "=== 追踪止损 (M08) ==="
input bool   UseTrailing      = true;         // 启用 M08 追踪止损
input int    TrailStartPts    = 300;          // 浮盈 > N points 激活追踪
input int    TrailStepPts     = 150;          // SL 每次收紧 N points
input int    TrailMinGapPts   = 20;           // 最小移动间隔 (防抖动)

input group "=== 回撤熔断 (M02 加强) ==="
input bool   UseDrawdownKill  = true;         // 启用回撤熔断
input double DDAlertPct       = 5.0;          // 净值回撤报警阈值 (%)
input double DDKillPct        = 15.0;         // 净值回撤熔断阈值 (全平) %
input int    DDLockHours      = 24;           // 熔断后锁定小时数

input group "=== 时段过滤 (M19) ==="
input bool   UseSessionFilter = true;         // 启用 M19 时段过滤
input string SessionPreset    = "London:8-16,NewYork:13-22";  // 时段预设 (Asia:0-8 / London:8-16 / NewYork:13-22)
input bool   AllowWeekend     = false;        // 允许周末交易 (默认 false)

input group "=== 通知 (M10) ==="
input bool   EnableNotify     = true;         // 启用推送通知
input string LogPrefix        = "EA_v2";      // 日志文件前缀 (M11)

//+------------------------------------------------------------------+
//| Globals (8 个模块 object 声明)                                    |
//+------------------------------------------------------------------+
CTradePlus     trade;     // M01 交易封装 (Init / Buy / Sell)
CRisk          risk;      // M02 风控 (Init / CanOpen / CountMyPositions)
CNewBar        NB;        // M05 新 K 线 (Init / IsNewBar)
CTrailingStop  trail;     // M08 追踪止损 (Init / SetParams / Apply)
CDashboard     dash;      // M09 面板 (SetTitle / Row / Separator / Show)
CNotify        notify;    // M10 通知 (EnablePush / Send / Trade)
CLogger        logger;    // M11 日志 (Info / Warn / Error / Trade / Close)
CSessionFilter M19;       // M19 时段过滤 (Init / IsInSession / ActiveSession / SessionCount)

//+------------------------------------------------------------------+
//| 内部状态                                                          |
//+------------------------------------------------------------------+
static ulong   _lastDealTicket = 0;
static double  _peakEquity     = 0.0;
static bool    _ddAlertActive  = false;
static bool    _ddKillActive   = false;
static datetime _ddKillUntil   = 0;
static int     _rsiHandle      = INVALID_HANDLE;

//+------------------------------------------------------------------+
//| OnInit: 8 模块按 M01→M19 顺序初始化                                 |
//+------------------------------------------------------------------+
int OnInit() {
   // M01 交易封装: magic + 滑点 30 points
   trade.Init(Magic, 30);

   // M02 风控: 同一 magic 限 MaxPositions, 风控 RiskPct
   risk.Init(Magic, MaxPositions, RiskPct);
   risk.SetMinSLPoints(MinSLPoints);

   // M05 新 K 线: H1 周期检测
   NB.Init(Timeframe);

   // M08 追踪止损: 绑定 trade + magic
   trail.Init(&trade, Magic);
   trail.SetParams(TrailStartPts, TrailStepPts, TrailMinGapPts);

   // M10 通知: 默认开 Push + Sound
   notify.EnablePush(EnableNotify);
   notify.EnableSound(EnableNotify);

   // M11 日志: 前缀 EA_v2, 默认写文件
   logger.Info("init", StringFormat("EA_v2 启动: Magic=%I64u RSI(%d) H1", Magic, RSI_Period));

   // M19 时段过滤
   if (UseSessionFilter) {
      if (!M19.Init(SessionPreset)) {
         PrintFormat("EA_v2: M19 Init failed: %s", M19.LastError());
         logger.Error("init", "M19 Init failed: " + M19.LastError());
         return INIT_FAILED;
      }
      M19.SetAllowWeekend(AllowWeekend);
      PrintFormat("EA_v2: M19 Init OK preset='%s' sessions=%d weekend=%s",
                  SessionPreset, M19.SessionCount(), AllowWeekend ? "ALLOW" : "BLOCK");
   }

   // RSI 指标句柄
   _rsiHandle = iRSI(_Symbol, Timeframe, RSI_Period, PRICE_CLOSE);
   if (_rsiHandle == INVALID_HANDLE) {
      Print("EA_v2: RSI 句柄创建失败 err=", GetLastError());
      logger.Error("init", "RSI 句柄创建失败");
      return INIT_FAILED;
   }

   // 初始化回撤基线
   _peakEquity   = AccountInfoDouble(ACCOUNT_EQUITY);
   _ddAlertActive = false;
   _ddKillActive  = false;
   _ddKillUntil   = 0;

   // 启动横幅
   PrintFormat("EA_v2 启动: Magic=%I64u TF=%s RSI(%d) RiskPct=%.2f UseTrail=%s UseM19=%s DDKill=%.1f%%",
               Magic, PeriodToStr(Timeframe), RSI_Period, RiskPct,
               UseTrailing ? "ON" : "off",
               UseSessionFilter ? "ON" : "off",
               DDKillPct);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| OnDeinit: 释放资源                                                |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   if (_rsiHandle != INVALID_HANDLE) {
      IndicatorRelease(_rsiHandle);
      _rsiHandle = INVALID_HANDLE;
   }
   dash.Clear();
   Comment("");
   logger.Info("deinit", StringFormat("EA_v2 停止 reason=%d", reason));
   logger.Close();
}

//+------------------------------------------------------------------+
//| OnTick: 主循环 (M02 回撤熔断 → M08 追踪 → M05 新 K 线 → M19 → 信号 → M02 → M01) |
//+------------------------------------------------------------------+
void OnTick() {
   // 1) 每次 tick: 回撤熔断检查 (优先, 不管新 K 线)
   if (UseDrawdownKill) {
      if (_CheckDrawdownKill()) {
         // 熔断中: 禁止开仓, 走 dashboard 让用户看到熔断状态
         RefreshDash();
         return;
      }
   }

   // 2) 每次 tick: M08 追踪止损 (锁浮盈)
   if (UseTrailing) {
      trail.Apply();
   }

   // 3) 新 K 线: 才进入信号逻辑 (M05)
   if (!NB.IsNewBar()) {
      return;
   }

   // 4) M19 时段过滤: 非交易时段不开仓 (持仓由 M08 继续管理)
   if (UseSessionFilter && !M19.IsInSession(TimeCurrent())) {
      RefreshDash();
      return;
   }

   // 5) 取 RSI
   double rsiBuf[];
   ArraySetAsSeries(rsiBuf, true);
   if (CopyBuffer(_rsiHandle, 0, 0, 2, rsiBuf) < 2) {
      logger.Warn("rsi", "CopyBuffer RSI 失败");
      return;
   }
   double rsi = rsiBuf[0];
   if (rsi == EMPTY_VALUE) return;

   // 6) M02 持仓数闸门
   if (risk.CountMyPositions() >= MaxPositions) {
      RefreshDash();
      return;
   }

   // 7) RSI 均值回归信号
   bool buySignal  = (rsi < RSI_Oversold) && !risk.HasMyPosition(ORDER_TYPE_BUY);
   bool sellSignal = (rsi > RSI_Overbought) && !risk.HasMyPosition(ORDER_TYPE_SELL);

   if (buySignal) {
      OpenPos(ORDER_TYPE_BUY, rsi);
   } else if (sellSignal) {
      OpenPos(ORDER_TYPE_SELL, rsi);
   }

   RefreshDash();
}

//+------------------------------------------------------------------+
//| OpenPos: 计算 SL/TP → 调 M02.CanOpen → 调 M01.Buy/Sell → 调 M11 logger.Trade |
//+------------------------------------------------------------------+
void OpenPos(ENUM_ORDER_TYPE type, double rsi) {
   double price = (type == ORDER_TYPE_BUY)
                ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if (price == 0) {
      logger.Warn("open", "拿不到报价");
      return;
   }

   // SL/TP 偏移
   double sl = (type == ORDER_TYPE_BUY) ? price - SL_Points * _Point
                                       : price + SL_Points * _Point;
   double tp = (type == ORDER_TYPE_BUY) ? price + TP_Points * _Point
                                       : price - TP_Points * _Point;

   // broker 最小 stop distance 防护
   long   minStopPts = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist    = minStopPts * _Point;
   if (minDist > 0 && MathAbs(price - sl) < minDist) {
      PrintFormat("EA_v2: SL 距 %.5f < broker 最小 %.5f, 跳过", MathAbs(price - sl), minDist);
      logger.Warn("open", StringFormat("SL 距 %.5f < broker 最小 %.5f", MathAbs(price - sl), minDist));
      return;
   }

   // 手数: 简化固定 RiskPct 对应手数, 不引 M03 (本任务只 8 模块)
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double stepLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double lot     = minLot;  // 教学版用最小手, 真实账户用 M03.LotByRisk

   // M02 风控闸门
   if (!risk.CanOpen(type, lot, sl, tp)) {
      logger.Warn("open", "M02 风控拒绝开仓");
      return;
   }

   // M01 下单
   string comment = (type == ORDER_TYPE_BUY) ? "RSI_Long" : "RSI_Short";
   bool ok = false;
   if (type == ORDER_TYPE_BUY) {
      ok = trade.Buy(lot, sl, tp, comment);
   } else {
      ok = trade.Sell(lot, sl, tp, comment);
   }

   if (ok) {
      string reason = (type == ORDER_TYPE_BUY)
                    ? StringFormat("RSI %.2f < %d", rsi, RSI_Oversold)
                    : StringFormat("RSI %.2f > %d", rsi, RSI_Overbought);
      logger.Trade((type == ORDER_TYPE_BUY ? "BUY" : "SELL"),
                   _Symbol, lot, price, 0, reason);
   } else {
      logger.Error("open", StringFormat("下单失败 type=%s lot=%.2f", EnumToString(type), lot));
   }
}

//+------------------------------------------------------------------+
//| _CheckDrawdownKill: 净值回撤熔断 (M02 加强版, 含全平+锁定期)          |
//+------------------------------------------------------------------+
bool _CheckDrawdownKill() {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if (equity <= 0) return false;

   // 更新峰值
   if (equity > _peakEquity) {
      _peakEquity = equity;
   }
   if (_peakEquity <= 0) return false;

   double ddPct = (_peakEquity - equity) / _peakEquity * 100.0;

   // 报警 (M10 触发器 1, 借鉴 MeanReversion_EA 范本 L253-267)
   if (EnableNotify && ddPct >= DDAlertPct && !_ddAlertActive) {
      _ddAlertActive = true;
      notify.Send(StringFormat("⚠ DD %.2f%% on %s (eq=%.2f peak=%.2f)",
                               ddPct, _Symbol, equity, _peakEquity), true);
      logger.Warn("dd", StringFormat("回撤报警 DD=%.2f%%", ddPct));
   } else if (ddPct < DDAlertPct * 0.5) {
      _ddAlertActive = false;
   }

   // 熔断: 全平所有 magic 持仓 + 锁定 N 小时
   if (ddPct >= DDKillPct && !_ddKillActive) {
      _ddKillActive = true;
      _ddKillUntil = TimeCurrent() + DDLockHours * 3600;
      // 全平
      int closed = 0;
      for (int i = PositionsTotal() - 1; i >= 0; i--) {
         ulong t = PositionGetTicket(i);
         if (t == 0) continue;
         if (PositionGetInteger(POSITION_MAGIC) != Magic) continue;
         if (PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
         if (trade.PositionClose(t)) closed++;
      }
      string msg = StringFormat("🔥 DDKill! DD=%.2f%% >= %.2f%%, 全平 %d 单, 锁 %d h",
                                ddPct, DDKillPct, closed, DDLockHours);
      notify.Send(msg, true);
      logger.Error("ddkill", msg);
      return true;
   }

   // 熔断锁定中
   if (_ddKillActive) {
      if (TimeCurrent() >= _ddKillUntil) {
         _ddKillActive = false;
         logger.Info("ddkill", StringFormat("DDKill 锁定到期 (锁了 %d h), 恢复交易", DDLockHours));
         notify.Send("✅ DDKill 锁定到期, EA_v2 恢复交易", false);
      }
      return true;
   }

   return false;
}

//+------------------------------------------------------------------+
//| RefreshDash: M09 面板刷新 (信号/持仓/熔断/时段)                      |
//+------------------------------------------------------------------+
void RefreshDash() {
   double rsiVal = EMPTY_VALUE;
   if (_rsiHandle != INVALID_HANDLE) {
      double buf[1];
      if (CopyBuffer(_rsiHandle, 0, 0, 1, buf) == 1) rsiVal = buf[0];
   }

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double ddPct  = (_peakEquity > 0) ? (_peakEquity - equity) / _peakEquity * 100.0 : 0.0;

   dash.Clear();
   dash.SetTitle("=== EA_v2 (8-Module) ===");
   dash.Separator();
   dash.Row("Symbol",     _Symbol);
   dash.Row("TF",         PeriodToStr(Timeframe));
   dash.Row("Magic",      IntegerToString((long)Magic));
   dash.Row("RSI(14)",    (rsiVal == EMPTY_VALUE) ? "n/a" : DoubleToString(rsiVal, 2));
   dash.Separator();
   dash.Row("Positions",  IntegerToString(risk.CountMyPositions()) + "/" + IntegerToString(MaxPositions));
   dash.Row("Equity",     DoubleToString(equity, 2));
   dash.Row("PeakEq",     DoubleToString(_peakEquity, 2));
   dash.Row("DD%",        DoubleToString(ddPct, 2) + "%");
   dash.Row("Trail",      UseTrailing ? StringFormat("ON start=%d step=%d", TrailStartPts, TrailStepPts) : "off");
   dash.Row("M19",        UseSessionFilter ? StringFormat("ON sessions=%d", M19.SessionCount()) : "off");
   dash.Separator();
   if (UseSessionFilter) {
      string session = M19.ActiveSession(TimeCurrent());
      dash.Row("ActiveSess", StringLen(session) > 0 ? session : "(off-hours)");
   }
   if (_ddKillActive) {
      int remain = (int)((_ddKillUntil - TimeCurrent()) / 3600);
      dash.Row("DDKill",    "🔥 LOCKED (" + IntegerToString(remain) + "h left)");
   } else {
      dash.Row("DDKill",    UseDrawdownKill ? StringFormat("arm @%.1f%%", DDKillPct) : "off");
   }
   dash.Row("M10 Notify", EnableNotify ? "ON" : "off");
   dash.Row("M11 Log",    "→ " + LogPrefix + "_YYYYMMDD.csv");
   dash.Show();
}

//+------------------------------------------------------------------+
//| OnTrade: M10 触发器 2 - 新成交通知 (借鉴 MeanReversion_EA 范本 L272-296) |
//+------------------------------------------------------------------+
void OnTrade() {
   if (!EnableNotify) return;
   if (!HistorySelect(0, TimeCurrent())) return;
   int total = HistoryDealsTotal();
   if (total <= 0) return;

   for (int i = total - 1; i >= 0; i--) {
      ulong ticket = HistoryDealGetTicket(i);
      if (ticket == 0) continue;
      if (ticket == _lastDealTicket) break;
      if ((ulong)HistoryDealGetInteger(ticket, DEAL_MAGIC) != Magic) continue;

      string  symbol = HistoryDealGetString(ticket, DEAL_SYMBOL);
      long    dtype  = HistoryDealGetInteger(ticket, DEAL_TYPE);
      double  volume = HistoryDealGetDouble (ticket, DEAL_VOLUME);
      double  price  = HistoryDealGetDouble (ticket, DEAL_PRICE);
      long    entry  = HistoryDealGetInteger(ticket, DEAL_ENTRY);
      string  typeStr = (dtype == DEAL_TYPE_BUY)  ? "BUY"
                      : (dtype == DEAL_TYPE_SELL) ? "SELL"
                      : EnumToString((ENUM_DEAL_TYPE)dtype);
      string  entryStr = (entry == DEAL_ENTRY_IN)  ? "OPEN"
                       : (entry == DEAL_ENTRY_OUT) ? "CLOSE"
                       : EnumToString((ENUM_DEAL_ENTRY)entry);
      notify.Trade(typeStr + "/" + entryStr, symbol, price, volume, 0, "EA_v2");
   }
   _lastDealTicket = HistoryDealGetTicket(total - 1);
}

//+------------------------------------------------------------------+
//| OnTradeTransaction: M10 触发器 3 - 拒单通知 (借鉴范本 L301-318)        |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result) {
   if (!EnableNotify) return;
   if (trans.type != TRADE_TRANSACTION_REQUEST) return;
   if (request.action != TRADE_ACTION_DEAL && request.action != TRADE_ACTION_PENDING) return;
   if (request.magic != Magic) return;
   uint rc = result.retcode;
   if (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_DONE_PARTIAL || rc == TRADE_RETCODE_PLACED) return;
   string reason = StringFormat("retcode=%u %s | %s %s %.2f @%.5f",
                                rc, result.comment,
                                EnumToString(request.type), request.symbol,
                                request.volume, request.price);
   notify.Send("❌ EA_v2 reject: " + reason, true);
   logger.Error("reject", reason);
}

//+------------------------------------------------------------------+
//| PeriodToStr: 周期枚举转字符串 (辅助 M09 Dashboard)                    |
//+------------------------------------------------------------------+
string PeriodToStr(ENUM_TIMEFRAMES p) {
   switch (p) {
      case PERIOD_M1:  return "M1";
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
      case PERIOD_W1:  return "W1";
      case PERIOD_MN1: return "MN";
      default:         return EnumToString(p);
   }
}
//+------------------------------------------------------------------+
