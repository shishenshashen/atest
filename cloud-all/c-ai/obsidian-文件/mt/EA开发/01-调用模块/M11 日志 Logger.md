---
title: M11 日志 Logger
tags: [调用模块, 日志]
type: module
---

# M11 日志 Logger

> **作用**：把日志同时输出到控制台（Print）和文件（CSV），便于复盘。
> **特性**：自动按日期分文件、自动加时间戳、可写结构化字段。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                              M11_Logger.mqh       |
//|                              EA 开发知识库 - 日志                  |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 日志：Print + 写文件                                              |
//| 文件路径：MQL5/Files/EA_log_YYYYMMDD.csv                          |
//+------------------------------------------------------------------+
class CLogger {
private:
   string _prefix;       // 日志前缀（比如 "MyEA"）
   int    _fileHandle;    // 文件句柄（0 = 未开）
   string _currentDate;   // 当前文件日期
   bool   _toFile;        // 是否写文件

   // 取日志文件名（按天分）
   string _GetFileName() {
      string d = TimeToString(TimeCurrent(), TIME_DATE);
      StringReplace(d, ".", "");   // 20251104
      return _prefix + "_" + d + ".csv";
   }
   // 打开/切换文件
   void _OpenIfNeeded() {
      string d = TimeToString(TimeCurrent(), TIME_DATE);
      if (d == _currentDate && _fileHandle != 0) return;
      if (_fileHandle != 0) FileClose(_fileHandle);
      _currentDate = d;
      _fileHandle  = FileOpen(_GetFileName(),
                              FILE_WRITE|FILE_READ|FILE_CSV|FILE_SHARE_READ|FILE_COMMON,
                              ',');
      if (_fileHandle == INVALID_HANDLE) {
         Print("Logger: 文件打开失败 err=", GetLastError());
         _fileHandle = 0;
      } else {
         // 写表头（仅新文件）
         if (FileSize(_fileHandle) == 0) {
            FileWrite(_fileHandle, "Time", "Level", "Tag", "Message");
         }
      }
   }

public:
   CLogger(string prefix = "EA", bool toFile = true)
      : _prefix(prefix), _fileHandle(0), _toFile(toFile) {}

   // 开关文件输出
   void SetFileOutput(bool v) { _toFile = v; }

   //+--- 普通日志 ---------------------------------------------------+
   void Info (string tag, string msg) { _Log("INFO",  tag, msg); }
   void Warn (string tag, string msg) { _Log("WARN",  tag, msg); }
   void Error(string tag, string msg) { _Log("ERROR", tag, msg); }

   //+--- 直接写：交易事件 -------------------------------------------+
   void Trade(string action, string symbol, double lot, double price,
              double pnl = 0, string extra = "") {
      string m = StringFormat("%s %s %.2f @%.5f", action, symbol, lot, price);
      if (pnl != 0) m += StringFormat(" P/L=%.2f", pnl);
      if (extra != "") m += " " + extra;
      _Log("TRADE", "trade", m);
   }

   //+--- 关闭文件（OnDeinit）----------------------------------------+
   void Close() {
      if (_fileHandle != 0) {
         FileClose(_fileHandle);
         _fileHandle = 0;
      }
   }

private:
   void _Log(string level, string tag, string msg) {
      string line = StringFormat("%s|%s|%s|%s",
                                 TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
                                 level, tag, msg);
      Print(line);
      if (!_toFile) return;
      _OpenIfNeeded();
      if (_fileHandle != 0)
         FileWrite(_fileHandle,
                   TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
                   level, tag, msg);
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M11_Logger.mqh>

CLogger log;

int OnInit() {
   log.Info("init", "EA 启动");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   log.Info("deinit", "EA 停止 reason=" + IntegerToString(reason));
   log.Close();   // 必调
}

void OnTick() {
   if (/* 入场 */) {
      log.Trade("BUY", _Symbol, 0.01, ask, 0, "金叉信号");
   }
   if (/* 出场 */) {
      log.Trade("CLOSE", _Symbol, 0.01, bid, profit, "止盈");
   }
}
```

## 输出格式
- 控制台：`2025.11.04 11:42:30|INFO|init|EA 启动`
- 文件（`MQL5/Files/EA_log_20251104.csv`）：
  ```csv
  Time,Level,Tag,Message
  2025.11.04 11:42:30,INFO,init,EA 启动
  2025.11.04 11:42:35,TRADE,trade,BUY XAUUSD 0.01 @4488.715 金叉信号
  2025.11.04 11:45:00,TRADE,trade,CLOSE XAUUSD 0.01 @4490.464 P/L=0.49 止盈
  ```

## 必看陷阱
- `FILE_COMMON` 标志 = 文件在终端公用目录（所有 EA 共用），不写 = 在 MQL5/Files/ 下
- **文件指针要 Close**，否则日志会丢最后几行
- Print() 在策略测试器中输出到「日志」标签，不会到文件
- 调试时建议关文件输出（`SetFileOutput(false)`）加速
- **别在 OnTick 里高频写文件**（影响性能），建议 1-5 秒一次

---

## 实战案例

> **本节汇总 M11 Logger 在真实 EA 场景的接入经验和"双输出 + OnDeinit 释放"完整范本**。spec wiki (上面) 讲 API + 理论；本节讲"已经跑通的实战 demo + 4 level 分类 + 与 M10/M13 协同 + 反模式"。

### 实战摘要（点开 wiki 前先看这段）

- **场景 A MeanReversion_EA.mq5 OnTick 日志 + 双输出**（320 行，13 模块集成）：`logger.Trade` 在 OnTick 入口（line 202/205）+ `OnDeinit` 释放（line 136），文件 + Print 双输出。
- **场景 B ScalperXAU.mq5 v2 升级 logger 协议**（1033 行，13 模块含 M17+M13）：4 类 logger 调用（`logger.Trade("BUY/SELL")` line 778-779 + `logger.Trade("TIMEOUT")` line 574-575 + `OnDeinit` line 1021 + `OnClosedDealMetrics` EA 内指标 Print）。
- **场景 C MyEA.mq5 最小 M11 范本**（300 行，10 模块）：`logger.Trade` + `OnDeinit logger.Close()`，是 5 行最小可工作版本。
- **即抄代码**：`logger.SetFileOutput(true)` + `logger.Trade(action, sym, lot, price, pnl, extra)` + `OnDeinit logger.Close()` 三件套。
- **5+ 已知陷阱**：OnDeinit 不 Close 丢日志 / OnTick 高频写盘 / FILE_COMMON 跨 EA 共享 / 4 level 分类 / Strategy Tester 输出到日志不写文件。
- **5 条反模式**：用裸 Print 替代 / 写盘频率 > 1 秒 / 不 Close 文件 / 日志字段无分类 tag / logger 当 M10 用（推送走 M10）。

### 实物 demo EA 接入（多品种 OnTick 日志）

**`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`**（320 行 / 12.7KB / 13 模块集成，4 品种均值回归 XAUUSDm M15）— 已落地，0 errors 编译。

接入点（5 处）：
- **line 18** `#include <MQL5Kit/M11_Logger.mqh>`
- **line 61** `CLogger logger;` 全局对象
- **line 124-128** OnInit 内 `Print("MeanReversion EA 启动: ...")` — 用裸 `Print` 不是 `logger.Info`，是因为 `logger.Info` 会写盘（OnInit 阶段频繁），MeanReversion_EA 选 Print 简化（不写盘）
- **line 202** `logger.Trade("BUY", _Symbol, lot, price, 0, "超卖做多")` — OnTick `OpenPos` 入口
- **line 205** `logger.Trade("SELL", _Symbol, lot, price, 0, "超买做空")` — 同上
- **line 136** `logger.Close();` — **OnDeinit 必调**，否则日志丢最后几行（spec 警告）

**关键设计**：**`logger.Trade()` 是 M11 的核心 API**（spec line 71-77）— 自动按 `Time|TRADE|trade|...` 格式写文件 + Print 双输出。`pnl=0` 写开仓（不显示 PnL），`pnl>0` 写平仓（带 PnL=xx）。MeanReversion_EA 走 4 品种单 EA，每笔成交都 1 行日志，日均 5 笔（保守）。

### 实物 demo EA 接入（剥头皮高频 + 4 类日志）

**`MQL5/Experts/minimax-ea/ScalperXAU.mq5`**（1033 行 / 41.7KB / 13 模块含 M17+M13，4 版本演进）— 已落地，0 errors 编译。

接入点（5 处）：
- **line 28** `#include <MQL5Kit/M11_Logger.mqh>`
- **line 115** `CLogger logger;` 全局对象
- **line 965** `logger.SetFileOutput(InpEnableLog);` — OnInit 必调，`InpEnableLog` 用户可关
- **line 778-779** `logger.Trade(type == ORDER_TYPE_BUY ? "BUY" : "SELL", _Symbol, lot, price, 0, InpEAComment);` — `TryOpen` 开仓入口
- **line 574-575** `logger.Trade("TIMEOUT", _Symbol, lot, price, 0, "时间止损");` — `CheckHoldTimeout` 强平入口（**M11 第 4 类日志：timeout 区别于 BUY/SELL**）
- **line 728-730** `[v3-metrics]` 格式 `PrintFormat(...)` — OnClosedDealMetrics 每 10 笔 EA 内指标
- **line 1021** `logger.Close();` — OnDeinit
- **line 1025-1029** `[v3-metrics-FINAL]` 格式 — OnDeinit 打 EA 内 11 个指标 final 值

**关键设计**：ScalperXAU v2 → v3 升级时**扩展 logger 协议** — 加了 "TIMEOUT" 第 4 类日志（剥头皮 30 分钟没平强平记为 `TIMEOUT`），跟 BUY/SELL/CLOSE 区分开。`OnClosedDealMetrics`（line 688-732）是 M11 + EA 内 metrics 的"组合用法" — **M11 写文件，Print 实时显示**（Metrics 走 Print 不用 M11 写盘，因为每 10 笔就 Print 一次不频繁）。

### 实物 demo EA 接入（最小 M11 范本）

**`MQL5/Experts/minimax-ea/MyEA.mq5`**（300 行 / 11.7KB / 10 模块，通用 EA 骨架）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 17** `#include <MQL5Kit/M11_Logger.mqh>`
- **line 59** `CLogger logger;` 全局对象
- **line 124** `logger.SetFileOutput(EnableLog);` — OnInit
- **line 190** `logger.Trade("BUY", _Symbol, lot, price, 0, "开多");` — `TryOpen` 入口
- **line 193** `logger.Trade("SELL", _Symbol, lot, price, 0, "开空");` — 同上
- **line 143** `logger.Close();` — OnDeinit

**关键设计**：MyEA 是 M11 **最小 5 行可工作版本**（SetFileOutput + Trade × 2 + Close）。如果新写 EA 只想记录成交，从 MyEA 复制 4 行即可上手。

### 即抄代码（最小 5 行范本）

```mql5
// 1) include
#include <MQL5Kit/M11_Logger.mqh>

// 2) 全局
CLogger logger;
input bool EnableLog = true;

// 3) OnInit 启动
int OnInit() {
   logger.SetFileOutput(EnableLog);    // 用户可关
   logger.Info("init", "EA 启动");     // 启动日志, 自动写盘
   return INIT_SUCCEEDED;
}

// 4) OnTick 成交入口
void OnTick() {
   if (/* 入场条件 */) {
      if (trade.Buy(lot, sl, tp, "MyEAv1")) {
         logger.Trade("BUY", _Symbol, lot, price, 0, "金叉信号");
         //                                                ↑ extra 字段
      }
   }
}

// 5) OnDeinit 释放
void OnDeinit(const int reason) {
   logger.Info("deinit", "EA 停止 reason=" + IntegerToString(reason));
   logger.Close();     // 必调, 否则日志丢最后几行
}
```

### 即抄代码（4 level 分类范本）

```mql5
// CLogger 提供 4 个 level 方法, 选对应 level
logger.Info ("init",    "EA 启动 magic=20260101");      // 启动 / 状态
logger.Warn ("warning", "spread 50 > 30 阈值");          // 警告
logger.Error("err",     "Buy 失败 retcode=10030");       // 错误
logger.Trade("BUY",     "XAUUSD 0.01 @4488.715 金叉");   // 交易事件

// OnTick 高频别用 Info/Warn/Error (会写盘), 改用 Print
Print("[debug] rsi=", rsi, " bbUpper=", bbUpper);  // Print 不写盘
```

### 实战陷阱（5+ 来自实物 EA）

1. **OnDeinit 不 Close 丢日志** — spec line 142-143 警告。**MyEA line 143 / MeanReversion_EA line 136 / ScalperXAU line 1021** 都在 OnDeinit 必 `logger.Close()`。MT5 退 EA 时如果直接杀进程，文件句柄没 Close = 最后 5-10 行丢。
2. **OnTick 高频写盘** — spec line 146 警告"建议 1-5 秒一次"。**严格：M11 logger 只在 Trade 事件（开仓/平仓/timeout）写盘**，OnTick 内部状态变化用 `Print` 不写盘。ScalperXAU 1 天 50+ 笔成交 = 50+ 行日志（合理），1 秒 5+ tick × 60 秒 = 300 Print 不写盘（合理）。
3. **`FILE_COMMON` 跨 EA 共享** — spec line 142 警告。**不传 `FILE_COMMON` = 写在 `MQL5/Files/<ea_name>_<date>.csv`**，不冲突。ScalperXAU `InpCsvFilePrefix = "trades_ScalperXAUv3_"`（line 102）+ MeanReversion_EA `MqlDateTime` 路径（**注意：M11 spec line 45 `FILE_COMMON` 默认开** = 写在公用目录）。
4. **4 level 分类** — spec line 66-68 `Info/Warn/Error` + `Trade`。**别只用 `Info`**，剥头皮 1 天 50+ 笔成交用 `Trade` 跟 `Info("init", ...)` 区分，事后 `grep "TRADE" MyEA_20251104.csv` 找所有成交。ScalperXAU 用 `Trade("BUY")` / `Trade("TIMEOUT")` 两种 action 区分。
5. **Strategy Tester 输出到「日志」标签** — spec line 144 警告。**回测时 `Print` 输出到「日志」标签不写文件**，`logger.SetFileOutput(true)` 也不写。**回测时只看 Experts 日志的「日志」标签，不查 MQL5/Files/ 下文件**（回测完后文件可能有，但不全）。
6. **`_OpenIfNeeded` 文件按日切** — spec line 39-56 内部实现。**EA 跨日 23:59 → 00:00 切文件时关闭旧文件开新文件**，文件名 `EA_log_20251104.csv` → `EA_log_20251105.csv`。MT5 重启 / 切换账户时同样切新文件（按 TimeCurrent 当天日期）。

### 反模式（5 条禁止）

1. **用裸 `Print()` 替代 M11** — 复盘要数据，`Print` 输出到 Experts 日志**不可二次分析**（要 PS/Node.js 解析日志文本）。**M11 logger 写 CSV 是结构化数据**，`node csv-parse` 直接读。
2. **写盘频率 > 1 秒一次** — XAUUSDm M1 每秒 5+ tick，每次写盘 `FileOpen` + `FileWrite` + `FileClose` 累 5-10 ms。**M11 写盘只在成交时**（开仓/平仓/timeout），OnTick 状态变化用 `Print`。
3. **不 `Close()` 文件** — `OnDeinit` 必 `logger.Close()`。MyEA / MeanReversion_EA / ScalperXAU 三个 EA 都遵守（line 143 / 136 / 1021），**这是 M11 spec 的硬性要求**。
4. **日志字段无分类 tag** — `Info/Warn/Error/Trade` 4 个 level 不混用，事后 grep 找关键事件。**严格**：启动 = `Info` / 异常 = `Error` / 成交 = `Trade` / 警告 = `Warn`。
5. **logger 当 M10 用** — logger 写文件，**不是推送**。**异常推送走 M10.Send**（DD 报警/拒单），**事后审计走 M11 logger.Trade**（每笔成交记录）。两者**不替代**。

### 链向

- **[[实战/MeanReversion_EA 接入报告]]** — 场景 A 实物, OpenPos line 191-207 + logger.Trade line 202/205
- **[[实战/ScalperXAU 接入报告 + v1→v4 演进史]]** — 场景 B 实物, v2 → v3 logger 协议升级 + 4 类日志 + EA 内 metrics
- **[[实战/MyEA wiki (P2)]]** — 场景 C 实物, 最小 5 行 M11 范本（SetFileOutput + Trade × 2 + Close）
- **[[实战/BBTrendEA 复活 SOP]]** — BBTrendEA 接入 8 模块, M11 可选（本任务没列）— 8 模块版本时不用 M11 直接 Print 也 OK
- **[[实战/Dashboard wiki (P2)]]** — Dashboard.mq5 4 模块无 M11, OnTrade 内 M10.Send 替代
- **[[M10 推送通知 Notify]]** — 异常推送走 M10.Send, 日常成交走 M11.logger.Trade, 两者协同
- **[[M13 文件 IO]]** — M11 logger 是"日志 CSV"范本, M13 FileIO 是"交易 CSV"范本, 两个 CSV 路径不冲突
- **[[EA 写之前要知道的 10 件事]]** — §"调试 vs 复盘"区分: 调试用 Print, 复盘用 M11 logger
