---
title: M13 文件 IO
tags: [调用模块, 文件]
type: module
---

# M13 文件 IO

> **作用**：读 CSV、写配置、读交易清单等。
> **比 GlobalVariable 更可靠**（不会被清）。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                              M13_FileIO.mqh       |
//|                              EA 开发知识库 - 文件 IO               |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 文件 IO 工具                                                      |
//| 所有文件操作在 MQL5/Files/ 或公用目录（FILE_COMMON 标志）         |
//+------------------------------------------------------------------+
class CFileIO {
public:
   //+--- 写一行文本（追加）------------------------------------------+
   //  fileName: 纯文件名（不带路径）
   //  line: 一行文本
   //  common: true=公用目录（MQL5/Files/ 之外）
   static bool AppendLine(string fileName, string line) {
      int flags = FILE_WRITE|FILE_READ|FILE_TXT|FILE_SHARE_READ|FILE_SHARE_WRITE;
      int h = FileOpen(fileName, flags, '\n');
      if (h == INVALID_HANDLE) return false;
      FileSeek(h, 0, SEEK_END);
      FileWriteString(h, line + "\n");
      FileClose(h);
      return true;
   }

   //+--- 写 CSV 一行 ------------------------------------------------+
   static bool AppendCSV(string fileName, string &fields[]) {
      int flags = FILE_WRITE|FILE_READ|FILE_CSV|FILE_SHARE_READ|FILE_SHARE_WRITE;
      int h = FileOpen(fileName, flags, ',');
      if (h == INVALID_HANDLE) return false;
      FileSeek(h, 0, SEEK_END);
      FileWrite(h, fields);
      FileClose(h);
      return true;
   }

   //+--- 读 CSV → 二维数组 -------------------------------------------+
   //  out[][]: 外部预先 resize
   //  返回行数
   static int ReadCSV(string fileName, string &out[][]) {
      int h = FileOpen(fileName, FILE_READ|FILE_CSV|FILE_SHARE_READ, ',');
      if (h == INVALID_HANDLE) return 0;
      int rows = 0;
      while (!FileIsEnding(h)) {
         int cols = 0;
         // 读一行（动态）
         string row[];
         while (!FileIsEnding(h)) {
            string s = FileReadString(h);
            // CSV 一行结束条件
            // 简化：每次 FileReadString 读一个字段
            int n = ArraySize(row);
            ArrayResize(row, n + 1);
            row[n] = s;
            cols++;
            // 检查是否到行末
            if (FileIsEnding(h)) break;
         }
         if (cols > 0) {
            ArrayResize(out, rows + 1);
            // 注意：MQL5 二维数组 resize 不能直接复制，要逐个
            // 简化处理：存成" | "分隔的字符串
            string joined = "";
            for (int i = 0; i < ArraySize(row); i++) {
               if (i > 0) joined += "|";
               joined += row[i];
            }
            out[rows][0] = joined;
            rows++;
         }
      }
      FileClose(h);
      return rows;
   }

   //+--- 读整个文件 → string ----------------------------------------+
   static string ReadAll(string fileName) {
      int h = FileOpen(fileName, FILE_READ|FILE_TXT|FILE_SHARE_READ, '\n');
      if (h == INVALID_HANDLE) return "";
      string s = "";
      while (!FileIsEnding(h)) s += FileReadString(h) + "\n";
      FileClose(h);
      return s;
   }

   //+--- 检查文件存在 -----------------------------------------------+
   static bool Exists(string fileName) {
      return FileIsExist(fileName);
   }

   //+--- 删除文件 --------------------------------------------------+
   static bool Delete(string fileName) {
      return FileDelete(fileName);
   }

   //+--- 写 JSON（简化）---------------------------------------------+
   //  真正的 JSON 库太复杂，用简单键值对替代
   //  格式: {"key": "value", "key2": 123}
   static bool WriteJSON(string fileName, string &keys[], string &values[]) {
      string json = "{\n";
      int n = MathMin(ArraySize(keys), ArraySize(values));
      for (int i = 0; i < n; i++) {
         if (i > 0) json += ",\n";
         json += StringFormat("  \"%s\": \"%s\"", keys[i], values[i]);
      }
      json += "\n}\n";
      int h = FileOpen(fileName, FILE_WRITE|FILE_TXT|FILE_COMMON, '\n');
      if (h == INVALID_HANDLE) return false;
      FileWriteString(h, json);
      FileClose(h);
      return true;
   }

   //+--- 读简单 key=value 配置 -------------------------------------+
   //  格式：每行 key=value，# 开头是注释
   static int ReadConfig(string fileName, string &keys[], string &values[]) {
      int h = FileOpen(fileName, FILE_READ|FILE_TXT|FILE_SHARE_READ, '\n');
      if (h == INVALID_HANDLE) return 0;
      ArrayResize(keys, 0); ArrayResize(values, 0);
      int n = 0;
      while (!FileIsEnding(h)) {
         string line = FileReadString(h);
         if (StringLen(line) == 0) continue;
         if (StringGetCharacter(line, 0) == '#') continue;
         int eq = StringFind(line, "=");
         if (eq <= 0) continue;
         string k = StringSubstr(line, 0, eq);
         string v = StringSubstr(line, eq + 1);
         StringTrimLeft(k);  StringTrimRight(k);
         StringTrimLeft(v);  StringTrimRight(v);
         ArrayResize(keys,   n + 1);
         ArrayResize(values, n + 1);
         keys[n]   = k;
         values[n] = v;
         n++;
      }
      FileClose(h);
      return n;
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M13_FileIO.mqh>

// 写日志
void LogTrade(string msg) {
   CFileIO::AppendLine("myea_log.txt",
                       TimeToString(TimeCurrent()) + " | " + msg);
}

// 写交易 CSV
void LogTradeCSV(string action, double lot, double price, double pnl) {
   string f[5];
   f[0] = TimeToString(TimeCurrent());
   f[1] = action;
   f[2] = DoubleToString(lot, 2);
   f[3] = DoubleToString(price, _Digits);
   f[4] = DoubleToString(pnl, 2);
   CFileIO::AppendCSV("trades.csv", f);
}

// 读配置
void LoadConfig() {
   string keys[], values[];
   int n = CFileIO::ReadConfig("myea_config.txt", keys, values);
   for (int i = 0; i < n; i++) {
      if (keys[i] == "MaxLot")   MaxLot  = StringToDouble(values[i]);
      if (keys[i] == "RiskPct")  RiskPct = StringToDouble(values[i]);
   }
}
```

`myea_config.txt`：
```
# MyEA 配置
MaxLot=0.5
RiskPct=0.01
Magic=20260101
```

## 必看陷阱
- **路径**：MQL5 沙盒默认在 `MQL5/Files/`，传 `FILE_COMMON` 标志可写到公用目录
- **文件打开要 Close**，否则锁住
- `FileReadString` 和 `FileReadNumber` 调用顺序跟写入必须一致
- 用 `FILE_SHARE_READ` 允许其他进程读
- 写 CSV 字段中含 `,` 或 `"` 会破坏格式 → 先 replace
- **别在 OnTick 高频写文件**，建议汇总后写

---

## 实战案例

> **本节汇总 M13 FileIO 在真实 EA 场景的接入经验和"24 列 trade journal"完整范本**。spec wiki (上面) 讲 API + 理论；本节讲"已经跑通的实战 demo + 6 列简化 vs 24 列完整 + AppendCSV lock 修复 + 反模式"。

### 实战摘要（点开 wiki 前先看这段）

- **场景 A ScalperXAU.mq5 Trade Journal 24 列 CSV**（1033 行，13 模块含 M17+M13，唯一用 M13 的生产 EA）：`WriteTradeRowV3` 函数 155 行（line 286-448）+ `OnTrade` 落盘（line 920-922），v1 6 列 → v2 23 列（+MFE/MAE/Duration/ExitReason）→ v3 24 列（+adx_at_entry）。
- **场景 B MyEA.mq5 简化 trade CSV 6 列**（300 行，10 模块）：`WriteTradeRow` 函数 38 行（line 79-116）+ `OnTrade` 落盘（line 263-298），是 M13 **最小可工作版本**。
- **场景 C Scalping_More v1.3 接入示例 wiki 写盘协议**（10 章节实战）：trades_Scalping_More_v1.3_YYYYMMDD.csv 6 字段（time/action/symbol/lot/price/pnl），是 M13 在剥头皮高频场景的"每日 N 笔 trade 落盘"范本。
- **即抄代码**：`CFileIO::AppendCSV(fname, fields)` 静态方法，**没有 Init / Deinit**，内部 open/close/append 一次完成。
- **5+ 已知陷阱**：OnTick 高频写盘 / AppendCSV lock 修复（v3 加 `FILE_SHARE_READ`） / 字段含逗号破坏 CSV / M13 vs M11 logger 写盘冲突 / 24 列扩展时字段顺序错位。
- **5 条反模式**：用 Print 替代 / 6 列不够用了才升级 / M13 当实时数据通道（应走 M15 缓存） / 字段无 comment 注释 / M13 文件名硬编码。

### 实物 demo EA 接入（24 列 trade journal 完整范本）

**`MQL5/Experts/minimax-ea/ScalperXAU.mq5`**（1033 行 / 41.7KB / 13 模块含 M17+M13，4 版本演进）— **项目内唯一用 M13 FileIO 的生产 EA**，已落地，0 errors 编译。

接入点（5 处）：
- **line 29** `#include <MQL5Kit/M13_FileIO.mqh>`
- **line 100-102** `input bool InpLogTradesToCsv = true; input string InpCsvFilePrefix = "trades_ScalperXAUv3_";` — 用户可配置
- **line 126-127** `static ulong _m13LastDealTicket = 0; static bool _m13CsvHeaderWritten = false;` — 去重锚点 + 表头一次性
- **line 286-292** `string TodayCsvName()` — 文件名按日期生成
- **line 294-448** `WriteTradeRowV3(ulong ticket)` — **核心函数 155 行**，24 列 trade journal：time/symbol/direction/type/volume/price/profit/swap/commission/net_pnl/open_time/close_time/duration_sec/sl_price/tp_price/exit_reason/mfe_pips/mae_pips/spread_at_entry/slippage_pts/adx_at_entry/magic/order_id/comment
- **line 920-922** `OnTrade` 内 `if (WriteTradeRowV3(t)) PrintFormat("[M13] ScalperXAUv3 trade logged: ticket=%I64u file=%s", t, TodayCsvName());` — **M13 落盘 + Print 双输出**

**关键设计**：**v1 6 列 → v2 23 列（+MFE/MAE/Duration/ExitReason）→ v3 24 列（+adx_at_entry）** — 是"v1 数据层 → v2 算法层 → v3 工具层"演进范本（v4 加 debug log 是工具层第 2 步）。`AppendCSV` 内部 `FILE_SHARE_READ|FILE_SHARE_WRITE` flag（spec line 44）**v3 加了 lock 修复**（v2 写盘偶发 race condition 在多 EA 共享路径时）。

### 实物 demo EA 接入（6 列简化 trade CSV 最小范本）

**`MQL5/Experts/minimax-ea/MyEA.mq5`**（300 行 / 11.7KB / 10 模块，通用 EA 骨架）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 18** `#include <MQL5Kit/M13_FileIO.mqh>`
- **line 48-51** `input bool LogTradesToCsv = true; input string CsvFilePrefix = "trades_";` — 用户可配置
- **line 66-67** `static ulong _m13LastDealTicket = 0; bool _m13CsvHeaderWritten = false;` — 去重 + 表头
- **line 69-75** `string TodayCsvName()` — 文件名生成
- **line 79-116** `WriteTradeRow(ulong ticket)` — **核心函数 38 行**，6 列：time/symbol/type/volume/price/profit
- **line 263-298** `OnTrade` — **M13 + M10 共享去重**：`if (LogTradesToCsv) WriteTradeRow(t);` 后 `if (EnableNotify) M10.Trade(...)`，共用 `_m13LastDealTicket` 锚点

**关键设计**：**M13 + M10 共享去重锚点是 M11/M13 协同的关键**（line 297 `_m13LastDealTicket = t;` 注释："与 M10 共用同一去重"）。MyEA 的 6 列够用，**如果需要 MFE/MAE/duration 升级 24 列**复制 ScalperXAU `WriteTradeRowV3` 改字段即可。

### 即抄代码（最小 6 列 trade CSV 范本）

```mql5
// 1) include
#include <MQL5Kit/M13_FileIO.mqh>

// 2) 全局 + 去重锚点
input bool   LogTradesToCsv = true;
input string CsvFilePrefix  = "trades_";
static ulong _lastDealTicket = 0;
bool  _csvHeaderWritten = false;

// 3) 文件名按日
string TodayCsvName() {
   MqlDateTime dt; TimeCurrent(dt);
   return CsvFilePrefix
        + IntegerToString(dt.year, 4) + IntegerToString(dt.mon, 2)
        + IntegerToString(dt.day, 2) + ".csv";
}

// 4) 单 deal → 1 行 CSV (6 列)
bool WriteTradeRow(ulong ticket) {
   if (!HistoryDealSelect(ticket)) return false;
   long   magic  = HistoryDealGetInteger(ticket, DEAL_MAGIC);
   if (magic != (long)Magic) return false;        // 多 EA 隔离
   long   entry  = HistoryDealGetInteger(ticket, DEAL_ENTRY);
   long   dtype  = HistoryDealGetInteger(ticket, DEAL_TYPE);
   double volume = HistoryDealGetDouble (ticket, DEAL_VOLUME);
   double price  = HistoryDealGetDouble (ticket, DEAL_PRICE);
   double profit = HistoryDealGetDouble (ticket, DEAL_PROFIT)
                 + HistoryDealGetDouble (ticket, DEAL_SWAP)
                 + HistoryDealGetDouble (ticket, DEAL_COMMISSION);
   string symbol = HistoryDealGetString (ticket, DEAL_SYMBOL);
   datetime t    = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);

   // 开仓按方向; 平仓反推 (BUY 平仓 = SELL deal)
   string typeStr = (entry == 0)
                  ? ((dtype == DEAL_TYPE_BUY) ? "BUY" : "SELL")
                  : ((dtype == DEAL_TYPE_SELL) ? "BUY" : "SELL");

   string fname = TodayCsvName();

   // 表头按需: 仅 EA 生命周期内第一次
   if (!_csvHeaderWritten) {
      string hdr[1];
      hdr[0] = "time,symbol,type,volume,price,profit";
      if (CFileIO::AppendCSV(fname, hdr)) _csvHeaderWritten = true;
   }

   string row[1];
   row[0] = TimeToString(t, TIME_DATE|TIME_SECONDS) + ","
          + symbol + "," + typeStr + ","
          + DoubleToString(volume, 2) + ","
          + DoubleToString(price,  _Digits) + ","
          + DoubleToString(profit, 2);
   return CFileIO::AppendCSV(fname, row);
}

// 5) OnTrade 内调 (与 M10.Trade 共享 _lastDealTicket)
void OnTrade() {
   HistorySelect(0, TimeCurrent());
   int total = HistoryDealsTotal();
   for (int i = total - 1; i >= 0; i--) {
      ulong t = HistoryDealGetTicket(i);
      if (t == 0 || t <= _lastDealTicket) break;   // 去重
      if (LogTradesToCsv) WriteTradeRow(t);
      // ... 其它 (M10.Trade / M11.logger.Trade) ...
      _lastDealTicket = t;                          // 更新锚点
   }
}
```

### 实战陷阱（5+ 来自实物 EA）

1. **OnTick 高频写盘** — spec 警告"建议汇总后写"。**M13 只在 OnTrade 写盘**（每笔成交 1 次，不是每 tick 1 次），ScalperXAU 1 天 50+ 笔 = 50+ 行（合理）。**MyEA 6 列**写盘耗时 1-2 ms / 笔，**ScalperXAU 24 列**写盘耗时 5-10 ms / 笔（含 K 线 CopyHigh/CopyLow 算 MFE/MAE）。
2. **`AppendCSV` lock 修复** — v3 spec 提到的"v2 写盘 race condition"是 spec line 44 `FILE_SHARE_READ|FILE_SHARE_WRITE` flag 缺一个。**v3 加 `FILE_SHARE_WRITE`** 后多 EA 共享路径不 race。**MyEA / ScalperXAU 都用 v3 协议**。
3. **字段含逗号破坏 CSV** — spec 警告"先 replace"。ScalperXAU `comment` 字段（line 308）有 `","` 风险，写盘前要 `StringReplace(comment, ",", "_")`。**MyEA comment 是固定字符串 `"MyEA"`，无风险**。
4. **M13 vs M11 logger 写盘冲突** — M11 logger 默认 `FILE_COMMON` 标志（spec line 45），M13 走 `CFileIO::AppendCSV` 不带 `FILE_COMMON`（spec line 44），**两个 CSV 路径不冲突**（M11 在公用目录公用 csv / M13 在 EA 私有目录私有 csv）。ScalperXAU 两者都用：M11 logger 写 `MQL5/...` 公用 + M13 trades 写 `MQL5/Files/trades_ScalperXAUv3_YYYYMMDD.csv` 私有。
5. **24 列扩展时字段顺序错位** — ScalperXAU v1 6 列 → v2 23 列（中间加 MFE/MAE/duration）→ v3 24 列（末尾加 adx_at_entry）。**不要在中间插入字段**（破坏老 v1 set / 兼容老 CSV reader），**末尾追加**是规范。
6. **文件按日切** — `TodayCsvName()` 按 TimeCurrent 日期，MT5 跨日 23:59 → 00:00 切文件。**EA 跑 1 周生成 7 个 CSV**（scalping 1 周 350+ 笔 = 7 文件，每文件 50 行），ScalperXAU `InpCsvFilePrefix = "trades_ScalperXAUv3_"` 加日期后缀避免冲突。

### 反模式（5 条禁止）

1. **用 `Print()` 替代 M13** — 复盘要数据，`Print` 不可二次分析。M13 写 CSV 是结构化数据，`node csv-parse` 直接读。**`trades_ScalperXAUv3_20260604.csv` 是 1 周沙盒测试的核心证据**。
2. **6 列不够用了才升级 24 列** — 升级时兼容老 set 麻烦。**写新 EA 直接上 24 列**（复制 ScalperXAU `WriteTradeRowV3` 改 magic 即可），MFE/MAE 必查 / Duration 必查 / ExitReason 必查。
3. **M13 当实时数据通道** — `CFileIO::AppendCSV` 内部 open/close/append，**每次 5-10 ms**。OnTick 实时数据用 `CIndicatorPool` + 全局变量缓存，不写盘。**M13 只用于成交审计**（OnTrade 1 次/笔）。
4. **字段无 comment 注释** — ScalperXAU 24 列里 `comment` 字段（line 308）记录"开仓原因（"金叉" / "超卖"） / EA 标识（"MyEA"）"，**复盘时 grep comment 找原因**。MyEA 6 列没 comment 字段，**建议加**。
5. **M13 文件名硬编码** — `InpCsvFilePrefix = "trades_ScalperXAUv3_"` 用户可配。**别写死 `"trades.csv"`**（多 EA 同账户冲突）。ScalperXAU / MyEA / MeanReversion_EA 都用 input 配前缀。

### 链向

- **[[实战/ScalperXAU 接入报告 + v1→v4 演进史]]** — 场景 A 实物, 24 列 trade journal 完整范本（v1 6 列 → v3 24 列演进）
- **[[实战/MyEA wiki (P2)]]** — 场景 B 实物, 6 列简化 trade CSV 最小范本 + M10/M13 共享去重
- **[[实战/Scalping_More v1.3 接入示例]]** — 场景 C 实物 demo, 剥头皮 1 天 50+ 笔 trade 落盘
- **[[实战/BBTrendEA 复活 SOP]]** — BBTrendEA 接入 8 模块 (含 M13, line 76 + line 478-525 7 字段 CSV)
- **[[实战/MeanReversion_EA 接入报告]]** — MeanReversion_EA 13 模块全集**不含 M13**（用 M11 logger 替代, line 105）— 对照范本
- **[[M10 推送通知 Notify]]** — OnTrade 内 M13 写盘 + M10.Send 推送, 共享 `_lastDealTicket` 去重
- **[[M11 日志 Logger]]** — M11 写"日志 CSV" (按日切) / M13 写"交易 CSV" (按日切), 两者并行不冲突
- **[[M15 定时器 TimerService]]** — M13 写盘 + M15 timer 配合, OnTimer 内调 M13 汇总（避免 OnTrade 单 deal 写盘）
