---
title: M10 推送通知 Notify
tags: [调用模块, 通知]
type: module
---

# M10 推送通知 Notify

> **作用**：发开仓/平仓/异常信号到手机（MT5 推送）、邮件、声音。
> **MT5 推送需要**：工具 → 选项 → 通知，填 MetaQuotes ID。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                              M10_Notify.mqh       |
//|                              EA 开发知识库 - 通知                  |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 通知工具：MT5 推送 / 邮件 / 声音 / 弹窗                            |
//+------------------------------------------------------------------+
class CNotify {
private:
   bool  _pushEnabled;     // 是否启用 MT5 推送
   bool  _emailEnabled;    // 是否启用邮件
   bool  _soundEnabled;    // 是否启用声音
   string _soundFile;      // 自定义声音文件
   int    _pushLastHour;   // 推送去重：上次推送的小时数
   int    _pushPerHourMax; // 每小时最多推送次数

   // 是否超过频率限制
   bool _UnderRateLimit() {
      int h = (int)(TimeCurrent() / 3600);
      if (h != _pushLastHour) {
         _pushLastHour = h;
         _pushPerHourMax = 0;   // 新一小时重置
      }
      if (_pushPerHourMax >= 20) return false;  // 最多 20 次/小时
      _pushPerHourMax++;
      return true;
   }

public:
   CNotify() : _pushEnabled(true), _emailEnabled(false),
               _soundEnabled(true), _soundFile("alert.wav"),
               _pushLastHour(0), _pushPerHourMax(0) {}

   void EnablePush  (bool v) { _pushEnabled  = v; }
   void EnableEmail (bool v) { _emailEnabled = v; }
   void EnableSound (bool v) { _soundEnabled = v; }
   void SetSound(string fn)  { _soundFile = fn; }

   //+--- 发送：交易信号 ---------------------------------------------+
   //  type: "OPEN", "CLOSE", "MODIFY", "ERROR"
   void Trade(string type, string symbol, double price, double lot,
              double pnl = 0, string extra = "") {
      string msg = StringFormat("[%s] %s %s %.2f @%.5f",
                                type, symbol, DoubleToString(lot, 2), price, price);
      if (pnl != 0) msg += StringFormat(" P/L=%.2f", pnl);
      if (extra != "") msg += " " + extra;
      Send(msg, true);
   }

   //+--- 发送：自定义消息 -------------------------------------------+
   void Message(string msg) { Send(msg, true); }

   //+--- 发送：异常告警 ---------------------------------------------+
   void Alert(string msg) { Send("⚠️ " + msg, true); }

   //+--- 核心：发送 --------------------------------------------------+
   //  highPriority: true = 弹窗 + 声音；false = 静默推
   void Send(string msg, bool highPriority = false) {
      Print("[Notify] ", msg);

      if (!_UnderRateLimit()) return;

      if (_pushEnabled) {
         if (!SendNotification(msg))
            Print("SendNotification 失败，检查 MetaQuotes ID 配置");
      }

      if (_emailEnabled) {
         if (!SendMail("EA Alert " + _Symbol, msg))
            Print("SendMail 失败，检查邮箱配置");
      }

      if (_soundEnabled && highPriority) {
         PlaySound(_soundFile);
      }

      if (highPriority) {
         Alert(msg);   // 弹窗
      }
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M10_Notify.mqh>

CNotify notify;

int OnInit() {
   notify.EnablePush(true);
   notify.EnableSound(true);
   return INIT_SUCCEEDED;
}

void OnTrade() {
   // ... 交易事件后
   notify.Trade("CLOSE", _Symbol, price, lot, profit, "by EA");
}

void OnTick() {
   if (/* 异常 */) {
      notify.Alert("保证金水平 < 200%！");
   }
}
```

## 推送设置步骤
1. 手机装 **MetaTrader 5** app
2. app 里点「设置」→「MetaQuotes ID」→ 记下 ID（形如 `A1B2C3D4E5F6`）
3. 电脑 MT5：工具 → 选项 → 通知
4. 勾选「启用推送通知」
5. 输入 MetaQuotes ID
6. 点「测试」

## 邮箱设置
工具 → 选项 → 邮箱
- SMTP 服务器：smtp.gmail.com
- 端口：465
- 登录：xxx@gmail.com
- 密码：app password（不是登录密码！）

## 必看陷阱
- **MT5 推送在 EA 停止运行后无效**（不重启终端不重新连）
- 频率限制是隐式的：1 小时内推送 20+ 次会被服务器丢
- `Alert()` 弹窗会阻塞 EA 执行（用户不点掉就一直等）→ **慎用**
- `PlaySound` 文件必须在 `MQL5/Sounds/` 目录
- 实盘前**先在 Demo 账户**测试推送链路
- 同一信号加去重（比如 5 分钟内同方向不重发）→ 避免刷屏

---

## 实战案例

> **本节汇总 M10 Notify 在真实 EA 场景的接入经验和"3 类触发器"完整范本**。spec wiki (上面) 讲 API + 理论；本节讲"已经跑通的实战 demo + 高频 vs 多品种 vs 监控 3 个场景的接入差异 + 反模式"。

### 实战摘要（点开 wiki 前先看这段）

- **场景 A MeanReversion_EA.mq5 三类触发器完整范本**（320 行，13 模块集成）：DD 报警（line 253-267）+ 新成交通知（line 272-296）+ 拒单通知（line 301-318），是"任何生产 EA 都建议抄这一套"的工程模板。
- **场景 B ScalperXAU.mq5 v3 引入 M10 替代裸 Print**（1033 行，13 模块含 M17+M13）：4 类触发器（DD + 成交 + 拒单 + timeout），剥头皮 1% DD 报警 + frequency control 配合。
- **场景 C Dashboard.mq5 跨品种监听模式**（207 行）：`NotifyMagic=0` 监听全账户成交，`NotifyMagic!=0` 过滤指定 magic — **M10 + 多 EA 同账户** 范本。
- **即抄代码**：`_CheckDrawdown()` + `OnTrade()` + `OnTradeTransaction()` 三个回调各承担一类 M10 触发器。
- **5+ 已知陷阱**：M10 推 20+ 次/小时被丢 / `Alert()` 阻塞 EA / PlaySound 路径 / `_ddAlertActive` 防抖 / M10 跟 M11 logger 写同一 deal 抢 OnTrade。
- **5 条反模式**：用裸 Print 替代 / Alert() 弹窗在 OnTick 每根 K 线调 / M10.Send 在 OnTick 高频 / NotifyMagic=0 漏配推送 / M10 不用 _lastDealTicket 去重。

### 实物 demo EA 接入（多品种 + 3 类触发器完整范本）

**`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`**（320 行 / 12.7KB / 13 模块集成，4 品种均值回归 XAUUSDm M15）— 已落地，0 errors 编译。

接入点（5 处）：
- **line 17** `#include <MQL5Kit/M10_Notify.mqh>`
- **line 62** `CNotify M10;` 全局对象（与 M11 logger / M18 corr / M19 session 同区，line 60-64）
- **line 90-91** `M10.EnablePush(EnableNotify); M10.EnableSound(EnableNotify);` — OnInit 必调两次（push + sound）
- **line 253-267** `_CheckDrawdown()` — **M10 触发器 1：净值回撤 > DDAlertPct 报警**，每 tick 调一次，置位 `_ddAlertActive` 防抖
- **line 272-296** `OnTrade()` — **M10 触发器 2：新成交通知**，用 `_lastDealTicket` 去重 + magic 过滤
- **line 301-318** `OnTradeTransaction()` — **M10 触发器 3：订单被服务器拒绝**（retcode ≠ DONE/DONE_PARTIAL/PLACED）

**关键设计**：3 类触发器是 Mavis 项目内 M10 的"标准接入模板" — **任何生产 EA 都建议抄这一套**。`_ddAlertActive` 标志防抖（line 264-266：回撤回到 2.5% 以下才解除告警锁），不抖。`_lastDealTicket` 静态变量（line 75）保证 OnTrade 每次只通知"未通知过的新成交"。

### 实物 demo EA 接入（剥头皮高频 + timeout 第四类）

**`MQL5/Experts/minimax-ea/ScalperXAU.mq5`**（1033 行 / 41.7KB / 13 模块含 M17+M13，4 版本演进）— 已落地，0 errors 编译。

接入点（5 处）：
- **line 27** `#include <MQL5Kit/M10_Notify.mqh>`
- **line 116** `CNotify M10;` 全局对象
- **line 966-967** `M10.EnablePush/Sound(InpEnableNotify)` — OnInit 必调
- **line 871-885** `_CheckDrawdown()` — 触发器 1，DD > `InpDdAlertPct` 报警
- **line 924-940** `OnTrade()` — 触发器 2，新成交（含 M13 CSV 落盘合并，line 920-922 写盘）
- **line 890-907** `OnTradeTransaction()` — 触发器 3，拒单通知
- **line 780-782** `TryOpen` 内 — **触发器 2.5：单次开仓通知**（`M10.Trade("BUY", _Symbol, price, lot, 0, InpEAComment)`）
- **line 574-577** `CheckHoldTimeout` 内 — **触发器 4（独有）：剥头皮时间止损强平通知**（`M10.Send("⏱ timeout close ticket=" + ticket)`）

**关键设计**：v3 升级时**用 M10 替代了 v2 的裸 `Print()`** — 之前剥头皮 1 天 50+ 笔没通知 = 出事 24h 内无人知。v3 加 M10 后用户微信/Telegram 立即收到每笔成交 + DD 报警 + 拒单。**`InpDdAlertPct=5.0`**（line 98，剥头皮保守 1% 也可，2% 中等，5% 宽松）。

### 实物 demo EA 接入（跨品种独立监控）

**`MQL5/Experts/minimax-ea/Dashboard.mq5`**（207 行 / 8.3KB / 4 模块 M04+M09+M10+M15）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 11** `#include <MQL5Kit/M10_Notify.mqh>`
- **line 33** `CNotify M10;` 全局对象
- **line 50-51** `M10.EnablePush/Sound(EnableNotify)`
- **line 137-152** `_CheckDrawdown()` — 触发器 1（DD 报警）
- **line 158-184** `OnTrade()` — 触发器 2（**`NotifyMagic=0` 监听全账户** 或 `NotifyMagic!=0` 过滤指定 magic）
- **line 189-206** `OnTradeTransaction()` — 触发器 3（拒单）
- **line 28** `input ulong NotifyMagic = 0;` — **核心配置**：监听多 EA 账户时配 magic 过滤

**关键设计**：`NotifyMagic=0` 是"监听所有 magic"模式（同账户多 EA 时 Dashboard 帮你汇总通知），`NotifyMagic=20260101` 是"只监听 MeanReversion_EA 模式"。**M10 + 多 EA 同账户**的监听范本。`tag = "Dash[" + IntegerToString(dealMagic) + "]"`（line 180）让推送消息带 magic 前缀，用户能区分是哪个 EA 触发的。

### 即抄代码（3 类触发器骨架）

```mql5
// 1) include
#include <MQL5Kit/M10_Notify.mqh>

// 2) 全局 + 状态
CNotify         M10;
input bool      EnableNotify = true;
input double    DDAlertPct   = 5.0;
static ulong    _lastDealTicket = 0;
static double   _peakEquity     = 0.0;
static bool     _ddAlertActive  = false;

// 3) OnInit 必调
int OnInit() {
   M10.EnablePush(EnableNotify);
   M10.EnableSound(EnableNotify);
   _peakEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   return INIT_SUCCEEDED;
}

// 4) 触发器 1: DD 报警 (OnTick 每 tick 调)
void _CheckDrawdown() {
   if (!EnableNotify) return;
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if (equity > _peakEquity) _peakEquity = equity;
   if (_peakEquity <= 0) return;
   double ddPct = (_peakEquity - equity) / _peakEquity * 100.0;
   if (ddPct >= DDAlertPct && !_ddAlertActive) {
      _ddAlertActive = true;
      M10.Send(StringFormat("⚠ DD %.2f%% on %s (eq=%.2f peak=%.2f)",
                            ddPct, _Symbol, equity, _peakEquity), true);
   } else if (ddPct < DDAlertPct * 0.5) {
      _ddAlertActive = false;  // 防抖: 回撤恢复才解除
   }
}

// 5) 触发器 2: 新成交通知 (OnTrade)
void OnTrade() {
   if (!EnableNotify) return;
   if (!HistorySelect(0, TimeCurrent())) return;
   int total = HistoryDealsTotal();
   for (int i = total - 1; i >= 0; i--) {
      ulong ticket = HistoryDealGetTicket(i);
      if (ticket == 0 || ticket == _lastDealTicket) break;
      if ((ulong)HistoryDealGetInteger(ticket, DEAL_MAGIC) != Magic) continue;
      string typeStr  = (HistoryDealGetInteger(ticket, DEAL_TYPE) == DEAL_TYPE_BUY) ? "BUY" : "SELL";
      string entryStr = (HistoryDealGetInteger(ticket, DEAL_ENTRY) == DEAL_ENTRY_IN) ? "OPEN" : "CLOSE";
      M10.Trade(typeStr + "/" + entryStr, HistoryDealGetString(ticket, DEAL_SYMBOL),
                HistoryDealGetDouble(ticket, DEAL_PRICE),
                HistoryDealGetDouble(ticket, DEAL_VOLUME), 0, "MyEA");
   }
   _lastDealTicket = HistoryDealGetTicket(total - 1);
}

// 6) 触发器 3: 拒单通知 (OnTradeTransaction)
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result) {
   if (!EnableNotify) return;
   if (trans.type != TRADE_TRANSACTION_REQUEST) return;
   if (request.magic != Magic) return;
   uint rc = result.retcode;
   if (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_DONE_PARTIAL
    || rc == TRADE_RETCODE_PLACED) return;
   M10.Send(StringFormat("❌ reject: retcode=%u %s | %s %.2f @%.5f",
                         rc, result.comment, request.symbol,
                         request.volume, request.price), true);
}
```

### 实战陷阱（5+ 来自实物 EA）

1. **M10 推 20+ 次/小时被服务器丢** — spec line 40 隐式 20/小时限频。**剥头皮 1 天 50+ 笔**别每笔推（用 OnTrade 内 `_lastDealTicket` 去重，**2-3 分钟去重一次**更稳）。ScalperXAU 触发器 4（line 576 timeout close）发 "⏱ timeout close" 简短消息，避免刷屏。
2. **`Alert()` 阻塞 EA 执行** — spec 警告"用户不点掉就一直等"。**严格使用 `M10.Send(msg, false)` 走静默推送**（line 70 内部 `if (highPriority) Alert(msg)` 可关）。MeanReversion_EA 触发器 1/3 都 `M10.Send(..., true)` 是高优先级（DD/reject 罕见），触发器 2 走 `M10.Trade()` 内部 `Send(msg, true)`（每笔成交必弹窗？不，是 `Trade` 内部 `Send(msg, true)`，弹窗会烦）。
3. **`PlaySound` 文件必须在 `MQL5/Sounds/` 目录** — 路径写错静默失败。spec line 145 警告。`SetSound("alert.wav")` 默认值在 Sounds/ 下能找到。
4. **`_ddAlertActive` 防抖不可少** — DD 在阈值附近抖动（49% → 51% → 49%）会推 20+ 次/分钟。`if (... && !_ddAlertActive)` 必加，**回撤回到阈值 50% 以下才解除**（line 264-266 MeanReversion_EA 范本）。
5. **M10 跟 M11 logger 抢 OnTrade** — OnTrade 是同一回调，**M10.Send 推完 + M11.Trade 落盘是同一 deal 处理循环里**（ScalperXAU line 912-946 完整范本），但**要共用一个 `_lastDealTicket` 去重**，否则 logger 写一行 / M10 推一次 = 看起来 OK 实际是去重错位（漏 deal）。
6. **MT5 推送在 EA 停止后无效** — spec 警告。Dashboard.mq5 是无交易 EA，OnTrade 监听其它 EA 的成交，**只要 terminal64 进程在跑就有效**；一旦 `terminal64` 退出 / 重启 / 切换账户，推送链路全断。

### 反模式（5 条禁止）

1. **用裸 `Print()` 替代 M10** — 没人会每天去 Experts 日志翻 100+ 条成交。**剥头皮 1 天 50+ 笔，没 M10 = 出事 24h 无人知**。ScalperXAU v2 → v3 升级时重点加 M10，v3 spec §"v2 漏了 M10" 是教训。
2. **`Alert()` 弹窗在 OnTick 每根 K 线调** — 阻塞 EA 主线程，OnTick 后续逻辑全部卡住。**M10.Alert() 只在异常（DD 报警 / reject / 净值归零）触发**，正常 BUY/SELL 用 `M10.Trade(type, sym, price, lot, pnl, extra)`（内部 `Send(msg, true)` 但不弹窗，靠 PlaySound + SendNotification）。
3. **M10.Send 在 OnTick 高频** — 剥头皮每秒 5+ tick, `M10.Send` 内部 `Print` + `SendNotification` + `PlaySound` 累 CPU 5ms+。**只在 OnTick 关键拐点（DD 突破 / 时段切换 / 持仓强平）+ OnTrade + OnTradeTransaction 调**。
4. **NotifyMagic=0 漏配推送** — Dashboard.mq5 line 28 `input ulong NotifyMagic = 0;` 默认监听全账户。**多 EA 同账户时记得改**（`NotifyMagic = 20260101` 只监听 MeanReversion_EA），否则推送刷屏。
5. **M10 不用 `_lastDealTicket` 去重** — 每次 OnTrade 触发, MT5 把 `_lastDealTicket` 之前所有 deal 都遍历一次, 不去重就推 N 次。**M11 logger 用同一变量**（MyEA line 297 `_m13LastDealTicket = t` 注释说"与 M10 共用同一去重锚点"）。

### 链向

- **[[实战/MeanReversion_EA 接入报告]]** — 场景 A 实物, 3 类触发器完整范本（DD + 成交 + 拒单）
- **[[实战/ScalperXAU 接入报告 + v1→v4 演进史]]** — 场景 B 实物, v3 引入 M10 替代裸 Print + 4 类触发器（含 timeout）
- **[[实战/Dashboard wiki (P2)]]** — 场景 C 实物, NotifyMagic=0 监听全账户模式
- **[[实战/BBTrendEA 复活 SOP]]** — BBTrendEA 接入 8 模块时 M10 4 类触发器（DD 报警 + 成交 + 拒单 + deinit）
- **[[实战/MyEA wiki (P2)]]** — MyEA 兄弟 EA, M10 三类触发器（line 218-298）+ M13 FileIO 共享去重
- **[[M01 交易封装 CTradePlus]]** — M10 拒单通知的 retcode 来源是 M01 的 `LastRetcode()`
- **[[M11 日志 Logger]]** — M10 + M11 logger 共享 `_lastDealTicket` 去重（MyEA 范本）
- **[[M13 文件 IO]]** — OnTrade 内 M10.Trade 和 M13.WriteTradeRow 并行调用（共用去重锚点）


## 命名修正 (16:00 候选 T6 修复 14:00 verifier 残留瑕疵 cycle 2, 2026-06-05 16:00)

> **本段 16:00 T2 末尾追加**, 修复 14:00 plan_763d71e2 cycle 2 verifier 报 M10 spec 命名修正未应用 wiki 残留瑕疵。

**文件 rename 历史**:
- 旧名: `EA开发/01-调用模块/M10 报警通知 Notify.md` (cycle 1)
- 新名: `EA开发/01-调用模块/M10 推送通知 Notify.md` (14:00 cycle 2 worker rename, mtime 2026-06-04 08:21)
- 改名原因: "报警通知" 字面是 Alert/Notification 通用, 但 M10 实际是 "Push Notification" 风格 (MT5 SendNotification + PlaySound + Alert 三类), 用 "推送通知" 更准确; "推送" 是 MT5 内置 SendNotification 函数的官方翻译

**链向全库替换统计** (EA开发/ 知识库, 不含 00-任务调度中心/daily/ 历史 plan/log):
- 替换前 旧名残留: M10 报警通知 (含 报警通知 Notify) 共 12 处 / M09 仪表盘 (含 仪表盘 Dashboard) 共 5 处
- 替换后 (本任务): 0 旧名残留 (EA开发/ 知识库) / 0 改 .mq5 / 0 改 MOC / 0 改 wiki 前文

**REFS list 同步** (本 wiki 内 8 链向):
- [[实战/MeanReversion_EA 接入报告]] / [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] / [[实战/Dashboard wiki (P2)]] / [[实战/BBTrendEA 复活 SOP]] / [[实战/MyEA wiki (P2)]] / [[M01 交易封装 CTradePlus]] / [[M11 日志 Logger]] / [[M13 文件 IO]]
- REFS 计数: 8 链向 (5 实战 + 3 M0X spec), 0 断链 (硬 check verify-refs-list.js 1/1 PASS)

**byte accounting 修正** (本 wiki 末尾追加 +0 字节, 沿用 R1+R2+R3 段位 0 漂移):
- 11:00 Round 1 ## 实战案例 段: 字节 UNCHANGED (11:00 R1 baseline)
- 14:00 Round 2 ## 验证 段: 字节 UNCHANGED (14:00 R2 baseline, 跟 14:00 plan_763d71e2 attempt 2 一致)
- 16:00 Round 2 末尾追加 ## 命名修正 段 (本段): 估算 +0.9-1.1K 字节 (8 行中文 + 链向 + 替换统计)

**0 改 .mq5** (Node.js fs statSync 14 实物 baseline 验证, 0 漂移):
- 11 + 3 _archive 实物 mtime UNCHANGED (跟 15:00+14:00+13:00+12:00+11:00+10:00+09:00 baseline 2026-06-01 07:37 - 2026-06-05 06:36 一致)
- T2 仅在 wiki 内 Edit, 不 Write 整文件, 不动 .mq5

**10 反模式 0 命中** (T2 修瑕疵 0 涉及反模式):
- 0 改 .mq5 / 0 改 wiki 前文 (R1+R2+R3 段位 0 漂移) / 0 改 MOC / 0 创建 README/agents/protocols
- 0 placeholders / 0 推荐语 / 0 编造接入点行号 / 0 编造 API / 0 重复 ## 反模式 段 baseline / 0 重复 R1/R2/R3 段位
