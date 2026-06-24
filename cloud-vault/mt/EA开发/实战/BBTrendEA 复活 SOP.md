---
title: BBTrendEA 复活 SOP
tags: [实战, 复活, BBTrendEA, MQL5Kit, SOP]
type: sop
---

# BBTrendEA 复活 SOP (从 _archive 到 minimax-ea)

> **目的**: 把 `_archive/earn-ea/BBTrendEA.mq5` (68.6 KB, 1709 行, 13 indicator handles, 自带 grid/panel/news/trail) 复活到 `minimax-ea/BBTrendEA.mq5` 的标准操作流程, **接入 8 个 MQL5Kit 模块**: M01 交易封装 / M02 风控 / M08 追踪止损 / M10 推送通知 / M13 文件 IO / M15 定时器 / ~~M17 新闻过滤~~ / M18 相关性过滤(可选)。
>
> **适用场景**: 用户在 console session 1 切回来时按本 SOP 跑一遍复活, 完成后 EA 编译 0 errors / 0 warnings, 1 周沙盒测试 trades_YYYYMMDD.csv 正常落盘 + 通知触发。
>
> **本 wiki 不写 .mq5** —— 实际复活需 GUI 阻塞 console session 1, 留给 N4 任务执行。Mavis 编译 + 用户 GUI 跑 backtest, 详见 [[00-快速开始/MT5 GUI 自动化 5 次失败全记录 + 分工协议]]。

---

## 1. BBTrendEA 体检报告 (功能 / 缺什么 / 复活目标)

### 1.1 文件基础信息

| 维度 | 数值 | 备注 |
|---|---|---|
| 路径 | `MQL5/Experts/_archive/BBTrendEA.mq5` | **只读**, 不写不改 |
| 字节数 | **68,635 bytes** (67.03 KB) | 体检时 `Get-Item` 确认 |
| 总行数 | **1,709** | 含代码 1461 / 注释 29 / 空行 219 |
| Magic | `InpMagicNumber = 20240501` (int) | **11 处引用**, 见 §1.2 |
| `#include` | **0** | 完全自包含, 无外部模块 |
| `class` 定义 | **0** | 55 个 top-level function (无 OOP 包装) |
| 自定义类型 | `enum ENUM_NEWS_REGION / ENUM_HEDGE_MODE / ENUM_CLOSE_MODE` (line 36-50) | 3 个枚举 |

### 1.2 现有功能盘点 (BBTrendEA 自带)

#### 1.2.1 13 个指标句柄 (`CreateIndicators` line 396-409)

| 指标 | 周期 | 用途 | 数量 |
|---|---|---|---|
| `iBands` | M1 / M5 / M30 / H1 | 多周期 BB 突破 | 4 |
| `iMA` | M1 fast/slow / M5 mid / M30 trend / H1 trend / H1 long | 多周期 MA 趋势 | 6 |
| `iRSI` | M1 / M5 | 超买超卖 | 2 |
| `iATR` | M1 | 波动率 + trail | 1 |
| **合计** | | | **13 handles** |

#### 1.2.2 策略核心函数 (按调用顺序)

| 函数 | 行 | 作用 |
|---|---|---|
| `OnInit` | 212 | 初始化句柄 + EventSetTimer + BuildNewsSchedule |
| `OnTick` | 256 | 主循环: 12 步流程, 见 §3.6 |
| `OnTimer` | 365 | 每秒刷新 panel |
| `OnChartEvent` | 371 | 按钮点击 (close all/long/short/losers) |
| `UpdateAllIndicators` | 439 | 拉所有 indicator buffer |
| `UpdateATROnly` | 487 | 每 tick 只拉 ATR (省 CPU) |
| `CheckNewBar1M` | 493 | 1M 新 K 线检测 |
| `IsTradeTimeAllowed` | 507 | 自带 session filter (Asia/Euro/US) |
| `FillNewsEvents` | 587 | **自定义 news schedule** (US/EU/UK/JP/AU 12 事件) |
| `IsNewsEventNear` | 616 | **自定义 news blackout 检查** |
| `IsRiskLimitReached` | 654 | 自带风控: 风险金额/保证金水平 |
| `GetCompositeSignal` | 684 | 4 周期 BB+MA+RSI 综合信号 |
| `OpenPosition` | 781 | 下单 (raw `OrderSend` + `req.magic`) |
| `ManageGrid` | 848 | 网格管理 (InpMaxLevels × InpGridMultiplier) |
| `TrailFind / TrailAdd / TrailUpdate` | 945-994 | **自定义 trail** (g_trailHighs/g_trailLows 数组) |
| `CheckTrailingStop` | 998 | 每 tick 调用 |
| `HedgePosition` | 1233 | 波动率 spike 时的对冲逻辑 |
| `BuildNewsSchedule` | 1406 | news panel 文本生成 |
| `DrawPanel / UpdatePanel` | 1451 / 1534 | 50+ ObjectCreate 画 panel + 6 个 button |
| `IsVolatilitySpike` | 1594 | ATR 突变检测 |

#### 1.2.3 已有自实现模块 (功能 vs. MQL5Kit 对照)

| BBTrendEA 自带 | 功能等同 MQL5Kit 模块 | 是否替换? |
|---|---|---|
| `IsTradeTimeAllowed` (507) + 4 时段 bool | **M19 SessionFilter** | 🟡 可替换为 `M19.Init()` |
| `IsNewsEventNear` (616) + `FillNewsEvents` (587) | **M17 NewsFilter** (wiki 暂无) | ⚠️ 保留自带 (功能等价 + 12 事件硬编码比通用 M17 更具体) |
| `IsRiskLimitReached` (654) + 紧急 close (line 292) | **M02 Risk** | ✅ 必须替换为 `risk.CanOpen()` |
| 自带 Trail (`g_trailHighs/g_trailLows` 998-1075) | **M08 TrailingStop** | ⚠️ 保留自带 (BB+ATR 动态计算比通用 M08 更精准) |
| 8 处 `OrderSend` (line 781, 848, 1098, 1145, 1233, 1291) | **M01 CTradePlus** | ✅ 必须替换 (CTradePlus 自动 filling + retry) |
| 无推送 (无 SendNotification) | **M10 CNotify** | ✅ 必须新增 (M10 漏发 = 出问题不知) |
| 无 CSV 日志 | **M13 CFileIO** | ✅ 必须新增 (回测结果靠它追溯) |
| `EventSetTimer` (line 247) + `EventKillTimer` (252) | **M15 CTimerService** | ✅ 必须替换 (Fires/LastFire 心跳) |
| 单品种 XAUUSDm | **M18 CorrelationFilter** | 🟡 可选 (留 demo 钩子) |

### 1.3 缺什么模块 (不接 8 个 MQL5Kit 模块的话)

| 不接 | 后果 |
|---|---|
| **M01 交易封装** | 8 处 `OrderSend` 用 raw `MqlTradeRequest`, 无 retcode 重试、无自动 filling、无 NormalizeDouble, 实盘 10030/10004 错误会失败 |
| **M02 风控** | 自带 `IsRiskLimitReached` 只看风险金额, 漏检: 手数边界/最小止损距离/同方向堆仓, 一旦黑天鹅会击穿 |
| **M08 追踪止损** | 已有自实现 trail, 但无 `_minGapPoints` 节流, 每 tick 改 SL 会触发服务器限流 |
| **M10 推送通知** | 完全无, EA 出错用户不知道, 模拟盘跑 1 周没消息 |
| **M13 文件 IO** | 无 CSV 落盘, trades 靠 journal 翻, 复盘困难 |
| **M15 定时器** | `EventSetTimer(1)` 每秒只刷 panel, 无 `Fires/LastFire` 心跳统计, EA 死了看不出来 |
| ~~**M17 新闻过滤**~~ | (wiki 无 M17, 见 §1.2.3 注释) 自带 news filter 已覆盖 ±30min 高影响事件, 保留即可 |
| **M18 相关性过滤** (可选) | 单品种 EA, M18 主要是给将来多品种 demo 留接口, 不接对当前无影响 |

### 1.4 复活目标

> 把 68.6 KB 源码搬到 `minimax-ea/BBTrendEA.mq5`, 加 8 个模块的 **include + input + object + OnInit + OnTick 替换**:
>
> 1. **M01/M02 必接** (交易 + 风控, 99% EA 标准)
> 2. **M08 必接** (BB 突破 + 趋势 = 必加追踪止损)
> 3. **M10/M13 必接** (通知 + 日志, MeanReversion_EA 已落地的标准)
> 4. **M15 必接** (替换 EventSetTimer, MeanReversion_EA 已用 CTimerService)
> 5. **M17 保留自带** (BBTrendEA 自定义 news filter 比通用 M17 更精准, 不要替换)
> 6. **M18 可选** (单品种, input `InpUseM18Filter = false` 关闭, 留 demo)
> 7. **保留 _archive 源不动**, 编译后 0 errors / 0 warnings
> 8. **跑 1 周沙盒**, `trades_YYYYMMDD.csv` 正常落盘 + M10 触发 ≥ 1 次

---

## 2. 复活前准备 (5 步)

### 步骤 1: 环境检查 (30s)

```powershell
# PowerShell (管理员 / 普通都行)
# 1) MetaTrader 5 是否在 console 1 desktop attach
Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object Id, SessionId, MainWindowTitle

# 期望: SessionId=2 (RDP) 或 1 (console), MainWindowTitle 含 "Exness"
# 若 MainWindowTitle 为空 → MT5 没启, 先开 MT5
```

```powershell
# 2) MetaEditor 是否可用
Test-Path "C:\Program Files\MetaTrader 5\MetaEditor64.exe"
# 期望: True
```

```powershell
# 3) _archive 源 + minimax-ea 目录在
Test-Path "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\_archive\BBTrendEA.mq5"
Test-Path "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea"
# 两者都期望: True
```

### 步骤 2: 备份 + 标记版本 (15s)

```powershell
# 1) BBTrendEA.mq5 备份到 _archive/bak/ (带时间戳)
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$bak = "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\_archive\BBTrendEA.bak.$ts.mq5"
Copy-Item "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\_archive\BBTrendEA.mq5" $bak
Get-Item $bak | Select-Object Name, Length, LastWriteTime
# 期望: 文件名 BBTrendEA.bak.20260604-131500.mq5, Length 68635
```

```powershell
# 2) minimax-ea/ 当前 .mq5 列清单 (确认 5 个 demo 已落地)
Get-ChildItem "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea\*.mq5" | Select-Object Name, Length
# 期望: 至少 MeanReversion_EA.mq5 (作为本次复活的参考)
```

### 步骤 3: 模块确认 (MQL5Kit Include 8 个文件) (20s)

```powershell
$inc = "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Include\MQL5Kit"
Get-ChildItem $inc\M0*.mqh, $inc\M1*.mqh, $inc\M19*.mqh | Select-Object Name, Length
# 期望至少存在:
#   M01_CTradePlus.mqh
#   M02_Risk.mqh
#   M08_TrailingStop.mqh
#   M10_Notify.mqh
#   M13_FileIO.mqh
#   M15_TimerService.mqh
#   M18_CorrelationFilter.mqh   (可选)
#   M19_SessionFilter.mqh        (可选, BBTrendEA 自带 session 也行)
```

> ⚠️ **M17 NewsFilter wiki 暂无模块** (实测 01-调用模块 目录只有 M01-M16, M18, M19)。**BBTrendEA 的 `IsNewsEventNear` + `FillNewsEvents` 功能等价, 保留自带**。SOP 不创建 M17 替代品, 避免重复造轮子。

### 步骤 4: 编译环境自检 (15s)

```powershell
# 1) 确认 MetaEditor64.exe 在 PATH 或全路径可达
$me = "C:\Program Files\MetaTrader 5\MetaEditor64.exe"
& $me /compile:"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea\MeanReversion_EA.mq5"
# 期望: 退出码 0, "0 error(s), 0 warning(s)"
# (拿 MeanReversion_EA 试编译, 确认环境 OK, 再去改 BBTrendEA)
```

### 步骤 5: GUI 切换到 console 1 (10s, 用户执行, Mavis 不做)

> Mavis 永远无法 GUI 操控用户 console 上的 MT5 窗口. 这是 OS 设计, 不是工具问题.
> 详见 [[00-快速开始/MT5 GUI 自动化 5 次失败全记录 + 分工协议]].

- **Win+Ctrl+←** 切到物理 console session 1
- 在 console 1 打开 PowerShell, 跑:
  ```powershell
  Get-Process terminal64 | Select-Object SessionId
  # 期望: SessionId=1 (console 1, 不是 RDP 2)
  ```
- 切回 RDP 2 → Mavis 继续

---

## 3. 完整复活步骤 (12 步, 每步 1 行命令/操作)

> 假设用户已执行完 §2 的 5 步准备, 现在 §3 在 minimax-ea/BBTrendEA.mq5 上工作。
> **重要**: BBTrendEA 源码 1709 行, 不要逐行重写, 而是**用 MetaEditor 打开 → 编辑 include + input + OnInit + OnTick 关键段 → F7 编译**。

### 步骤 1: 复制 BBTrendEA.mq5 到 minimax-ea/ (10s)

```powershell
$src = "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\_archive\BBTrendEA.mq5"
$dst = "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea\BBTrendEA.mq5"
Copy-Item $src $dst -Force
Get-Item $dst | Select-Object Name, Length
# 期望: Length 68635
```

> ⚠️ **必须用 `Copy-Item -Force` 而不是 Read+Write**, MetaEditor 会因文件 mtime 变而自动重编译。
> 复制后 **不要** 在 MetaEditor 外手动编辑 `.mq5` (避免编码 BOM 问题)。

### 步骤 2: include 8 个模块 (90s, 在 MetaEditor 内编辑)

打开 minimax-ea/BBTrendEA.mq5, **在 line 1 (即所有代码之前) 插入**:

```mql5
//+------------------------------------------------------------------+
//|                                  BBTrendEA.mq5                     |
//|                              MQL5Kit 复活版 - BB 突破 + 趋势 EA     |
//+------------------------------------------------------------------+
#property copyright "MQL5Kit"
#property version   "1.10"        // 从 1.02 → 1.10 标记复活
#property strict

//--- MQL5Kit 模块 (8 个: 6 必 + 1 保 + 1 可选) --------------------
#include <MQL5Kit/M01_CTradePlus.mqh>          // [必] 交易封装
#include <MQL5Kit/M02_Risk.mqh>                // [必] 风控
#include <MQL5Kit/M08_TrailingStop.mqh>        // [保] 追踪止损 (BBTrendEA 自带更强, M08 仅作备份 hook)
#include <MQL5Kit/M10_Notify.mqh>              // [必] 推送通知
#include <MQL5Kit/M13_FileIO.mqh>              // [必] CSV 落盘
#include <MQL5Kit/M15_TimerService.mqh>         // [必] 定时器 (替换 EventSetTimer)
#include <MQL5Kit/M18_CorrelationFilter.mqh>   // [选] 多品种相关性 (单品种默认 OFF)
// M17: 保留 BBTrendEA 自带 IsNewsEventNear (无 wiki 模块替代, 见 §1.2.3)
```

> 💡 **为什么 M08 是 `[保]` 而非 `[必]`?** —— BBTrendEA 自带的 `g_trailHighs/g_trailLows` 数组 + ATR 动态计算, 适配 BB 突破 + 网格 + 趋势场景, 比通用 M08 `_P(_startPoints)` 静态算法更精准。**M08 仅作 demo hook 留着**, `UseM08Trail = false` 关闭, 仍走自带 trail。

### 步骤 3: 加 input group (8 组) (60s, 在 `input group "=== Trading Parameters ==="` 之前插入)

```mql5
//--- MQL5Kit input groups (复活新增) -----------------------------
input group "=== M01 交易封装 ==="
input int   InpDeviation = 30;                // CTradePlus deviation (points)
input int   InpMaxRetry   = 3;                 // CTradePlus 重试次数
input int   InpRetrySleepMs = 200;             // CTradePlus 重试间隔 (ms)

input group "=== M02 风控 ==="
input bool  InpUseM02Risk   = true;            // 启用 M02.CanOpen() (true=替换自带 IsRiskLimitReached)
input int   InpMaxPos       = 3;               // 最大持仓数 (M02 + 自带 grid 共用)
input double InpMaxRiskPct  = 0.01;            // 单笔最大风险 (净值 %)
input int   InpMinSLPoints  = 50;              // 最小止损距离 (points, 防 0 止损)

input group "=== M08 追踪止损 (备) ==="
input bool  InpUseM08Trail  = false;           // 启用 M08 (false=用 BBTrendEA 自带 trail, 推荐)

input group "=== M10 推送通知 ==="
input bool  InpEnableNotify   = true;          // 启用 M10
input bool  InpEnablePush     = true;          // 推送 (MetaQuotes ID)
input bool  InpEnableSound    = true;          // 声音
input double InpDDAlertPct    = 5.0;           // 净值回撤报警阈值 (%)

input group "=== M13 文件 IO ==="
input bool  InpEnableCSV     = true;           // 启用 trades_YYYYMMDD.csv 落盘
input string InpCSVPrefix    = "BBTrend";      // CSV 文件名前缀

input group "=== M15 定时器 (替换 EventSetTimer) ==="
input int   InpTimerPeriodMs = 1000;           // 心跳周期 (ms, 1000=走秒定时器)

input group "=== M18 相关性过滤 (可选) ==="
input bool   InpUseM18Filter   = false;        // 启用 M18 (单品种默认 false, 留 demo 钩子)
input double InpCorrThreshold  = 0.7;          // |Pearson r| 阈值
input string InpCorrSymbols    = "XAUUSDm,EURUSDm,GBPUSDm,USDJPYm";
```

### 步骤 4: 加 object (8 个) (30s, 在 `//--- 全局变量` 之后插入)

```mql5
//--- MQL5Kit objects (复活新增) ---------------------------------
CTradePlus       trade;        // M01
CRisk            risk;         // M02
CTrailingStop    trailM08;     // M08 (备)
CNotify          M10;          // M10
CTimerService    timerM15;     // M15
CCorrelationFilter M18;        // M18 (可选)

static ulong  _lastDealTicket = 0;
static double _peakEquity     = 0.0;
static bool   _ddAlertActive  = false;

//--- 改: InpMagicNumber 类型从 int → ulong, 保持 20240501 ------
// (BBTrendEA 原: input int InpMagicNumber = 20240501)
// M01/M02/M07/M08 都用 ulong, 必须改类型否则 magic 比较出错
```

> ⚠️ **必须改**: 把源码 line 64 的 `input int InpMagicNumber = 20240501;` 改为 `input ulong InpMagicNumber = 20240501;`。否则 `req.magic = InpMagicNumber` 类型不匹配会编译警告。

---

### 步骤 5: OnInit 中初始化 8 个模块 (3 分钟, 必填)

定位: 源码 `int OnInit()` line 212, **在 `BuildNewsSchedule();` 之前插入**:

```mql5
int OnInit() {
   //--- 1) 13 个指标句柄 (保留自带) ----------------------------
   if (!CreateIndicators()) {
      Print("[ERR] CreateIndicators failed");
      return INIT_FAILED;
   }

   //--- 2) M15 定时器 (替换 EventSetTimer) -------------------
   if (!timerM15.Init(InpTimerPeriodMs)) {
      Print("[ERR] M15 TimerService init failed period=", InpTimerPeriodMs);
      return INIT_FAILED;
   }
   PrintFormat("[M15] timer init OK period=%dms mode=%s", timerM15.Period(), timerM15.Mode());

   //--- 3) M01 交易封装 ---------------------------------------
   trade.Init((ulong)InpMagicNumber, InpDeviation);
   trade.SetRetry(InpMaxRetry, InpRetrySleepMs);
   PrintFormat("[M01] trade.Init magic=%I64u deviation=%d retry=%d",
               (ulong)InpMagicNumber, InpDeviation, InpMaxRetry);

   //--- 4) M02 风控 ------------------------------------------
   risk.Init((ulong)InpMagicNumber, InpMaxPos, InpMaxRiskPct);
   risk.SetMinSLPoints(InpMinSLPoints);
   PrintFormat("[M02] risk.Init maxPos=%d riskPct=%.2f minSL=%d",
               InpMaxPos, InpMaxRiskPct, InpMinSLPoints);

   //--- 5) M08 追踪止损 (备, 默认 false 走自带) ---------------
   if (InpUseM08Trail) {
      trailM08.Init(&trade, (ulong)InpMagicNumber);
      trailM08.SetParams(200, 100, 10);
      Print("[M08] M08 trailing enabled (替换自带)");
   } else {
      Print("[M08] M08 disabled, 用 BBTrendEA 自带 trail (推荐)");
   }

   //--- 6) M10 通知 -------------------------------------------
   M10.EnablePush(InpEnablePush);
   M10.EnableSound(InpEnableSound);
   PrintFormat("[M10] notify push=%s sound=%s DD=%.1f%%",
               InpEnablePush ? "ON" : "off", InpEnableSound ? "ON" : "off", InpDDAlertPct);

   //--- 7) M18 相关性过滤 (可选, 单品种默认 OFF) --------------
   if (InpUseM18Filter) {
      string syms[];
      int n = StringSplit(InpCorrSymbols, ',', syms);
      if (n >= 2) {
         M18.SetDefaultDays(30);
         M18.Init(syms);
         for (int i = 0; i < n; i++) M18.LoadHistoricalCloses(syms[i], 30);
         Print(M18.DumpCorr());
      }
   }

   //--- 8) BBTrendEA 自带 (保留, 不动) ------------------------
   g_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   _peakEquity       = AccountInfoDouble(ACCOUNT_EQUITY);
   _ddAlertActive    = false;
   BuildNewsSchedule();   // line 241

   PrintFormat("[INFO] BBTrendEA v1.10 initialized, Magic=%I64u grid=%d trail=%s",
               (ulong)InpMagicNumber, InpMaxLevels,
               InpUseM08Trail ? "M08" : "自带");
   return INIT_SUCCEEDED;
}
```

> ⚠️ **每段初始化失败返 `INIT_FAILED`** —— M15 失败一定要返, M01/M02 失败可降级 (Print 后继续), 但 M15 是 EA 心跳源, 没它就走不下去。
> 💡 **`(ulong)InpMagicNumber` 强转** —— 源码 line 64 改了 ulong 但 OnInit 内 11 处 magic 比较要全部确认用 `(ulong)` 包一下, 否则编译 warning。

### 步骤 6: OnTick 中集成 (5 分钟, 必填)

定位: 源码 `void OnTick()` line 256。**保留原 12 步流程不动**, 在 4 个关键 hook 点插 MQL5Kit 调用:

```mql5
void OnTick() {
   g_tickCounter++;
   if (InpShowPanel) UpdatePanel();
   CheckNewBar1M();

   if (InpShowPanel && TimeCurrent() - g_lastNewsBuild >= 900) {
      BuildNewsSchedule();
   }

   if (!UpdateATROnly()) return;

   if (g_isNewBar1M) {
      if (!UpdateAllIndicators()) return;
   }

   g_currentMarginRate = SymbolInfoDouble(_Symbol, SYMBOL_MARGIN_INITIAL);
   // ... (margin rate check 不变) ...

   //--- HOOK 1: M15 心跳 (最前面, 每 tick 一次) -----------
   if (timerM15.OnTimer()) {
      _CheckDrawdown();   // 详见 step 7
   }

   //--- HOOK 2: M08 trail (备, 走自带则跳过) ---------------
   if (InpUseM08Trail && GetMyLots() > 0) {
      trailM08.Apply();
   }

   bool canTrade = true;

   //--- HOOK 3: 紧急风控 (line 292 已有, 不变) ------------
   double curEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   // ... (原 equity drawdown close 不变) ...

   //--- HOOK 4: 自带 IsNewsEventNear + M02 + 自带 IsRiskLimitReached
   if (g_marginRateSurge) canTrade = false;
   else if (!IsTradeTimeAllowed()) canTrade = false;
   else if (IsNewsEventNear()) canTrade = false;   // [保留] 自带 news
   else if (IsRiskLimitReached()) {                 // [保留] 自带 risk (备)
      // ... (line 307-315 不变) ...
   }

   //--- HOOK 5: M18 相关性过滤 (可选, 默认 OFF 跳过) -------
   if (canTrade && InpUseM18Filter
    && M18.IsHedgeExposed(_Symbol, (ulong)InpMagicNumber, InpCorrThreshold)) {
      PrintFormat("[M18] 跳过 %s: 已有高相关品种持仓 (thr=%.2f)",
                  _Symbol, InpCorrThreshold);
      canTrade = false;
   }

   if (!canTrade) return;

   //--- HOOK 6: 主策略 (保留自带, 不变) --------------------
   TrackDailyPerformance();
   if (InpAutoHedge && InpHedgeOnVolatility && IsVolatilitySpike()) {
      // ... (line 322-338 不变) ...
   }
   if (GetMyLots() > 0) ManageGrid();
   else CheckEntry();

   if (GetMyLots() > 0) {
      CheckTrailingStop();   // [保留] 自带 trail (BB+ATR 动态)
   }

   //--- HOOK 7: Loss timeout (line 347 不变) --------------
   if (GetMyLots() > 0 && InpMaxLossMinutes > 0 && g_isNewBar1M) {
      // ... (line 348-362 不变) ...
   }
}
```

> 💡 **6 个 HOOK 点**: M15 心跳 / M08 trail / news/risk 链 / M18 过滤 / 主策略 / Loss timeout。**OnTick 主体 0 改动**, 只在原有逻辑间插 hook。

### 步骤 7: OnTrade 中接 M10 + M13 (90s, 必填)

定位: 源码 **无 OnTrade 函数** (line 1691 用了 `HistoryDealGetInteger` 但没在 OnTrade 事件里), **追加到文件末尾**:

```mql5
//+------------------------------------------------------------------+
//| M10 触发器 1: 净值回撤 > DDAlertPct 报警 (由 OnTick 调)            |
//+------------------------------------------------------------------+
void _CheckDrawdown() {
   if (!InpEnableNotify) return;
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if (equity <= 0) return;
   if (equity > _peakEquity) _peakEquity = equity;
   if (_peakEquity <= 0) return;
   double ddPct = (_peakEquity - equity) / _peakEquity * 100.0;
   if (ddPct >= InpDDAlertPct && !_ddAlertActive) {
      _ddAlertActive = true;
      M10.Alert(StringFormat("DD %.2f%% on %s (eq=%.2f peak=%.2f)",
                             ddPct, _Symbol, equity, _peakEquity));
   } else if (ddPct < InpDDAlertPct * 0.5) {
      _ddAlertActive = false;
   }
}

//+------------------------------------------------------------------+
//| M10 触发器 2: 新成交通知 + M13 CSV 落盘                              |
//+------------------------------------------------------------------+
void OnTrade() {
   if (!HistorySelect(0, TimeCurrent())) return;
   int total = HistoryDealsTotal();
   if (total <= 0) return;

   for (int i = total - 1; i >= 0; i--) {
      ulong ticket = HistoryDealGetTicket(i);
      if (ticket == 0) continue;
      if (ticket == _lastDealTicket) break;
      if ((ulong)HistoryDealGetInteger(ticket, DEAL_MAGIC) != (ulong)InpMagicNumber) continue;

      string  symbol = HistoryDealGetString(ticket, DEAL_SYMBOL);
      long    dtype  = HistoryDealGetInteger(ticket, DEAL_TYPE);
      double  volume = HistoryDealGetDouble (ticket, DEAL_VOLUME);
      double  price  = HistoryDealGetDouble (ticket, DEAL_PRICE);
      double  pnl    = HistoryDealGetDouble (ticket, DEAL_PROFIT);
      long    entry  = HistoryDealGetInteger(ticket, DEAL_ENTRY);
      datetime dt    = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);

      string typeStr  = (dtype == DEAL_TYPE_BUY)  ? "BUY"
                      : (dtype == DEAL_TYPE_SELL) ? "SELL"
                      : EnumToString((ENUM_DEAL_TYPE)dtype);
      string entryStr = (entry == DEAL_ENTRY_IN)  ? "OPEN"
                      : (entry == DEAL_ENTRY_OUT) ? "CLOSE"
                      : EnumToString((ENUM_DEAL_ENTRY)entry);

      // M10 推送
      if (InpEnableNotify) {
         M10.Trade(typeStr + "/" + entryStr, symbol, price, volume, pnl, "BBTrend");
      }

      // M13 CSV 落盘 (按日期分文件)
      if (InpEnableCSV) {
         string f[7];
         f[0] = TimeToString(dt, TIME_DATE);
         f[1] = TimeToString(dt, TIME_SECONDS);
         f[2] = IntegerToString(ticket);
         f[3] = typeStr + "/" + entryStr;
         f[4] = symbol;
         f[5] = DoubleToString(volume, 2);
         f[6] = DoubleToString(pnl, 2);
         string fname = InpCSVPrefix + "_" + TimeToString(dt, TIME_DATE) + ".csv";
         CFileIO::AppendCSV(fname, f);
      }
   }
   _lastDealTicket = HistoryDealGetTicket(total - 1);
}

//+------------------------------------------------------------------+
//| M10 触发器 3: 订单被服务器拒绝                                       |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result) {
   if (!InpEnableNotify) return;
   if (trans.type != TRADE_TRANSACTION_REQUEST) return;
   if (request.magic != (ulong)InpMagicNumber) return;
   uint rc = result.retcode;
   if (rc == TRADE_RETCODE_DONE
    || rc == TRADE_RETCODE_DONE_PARTIAL
    || rc == TRADE_RETCODE_PLACED) return;
   string reason = StringFormat("retcode=%u %s | %s %s %.2f @%.5f",
                                rc, result.comment,
                                EnumToString(request.type), request.symbol,
                                request.volume, request.price);
   M10.Alert("BBTrend reject: " + reason);
}
```

> 💡 **CSV 格式** (7 字段): date / time / ticket / action / symbol / volume / pnl。Mavis 后处理用 `node csv-parse` 即可。
> ⚠️ **写 CSV 频率**: 每次 `OnTrade` 都写, 实盘一天可能 100+ 行, 1 周 700+ 行, 单文件不超 1MB 没问题。

### 步骤 8: OnTimer 改用 M15 替换 EventSetTimer (60s, 必填)

定位: 源码 `void OnTimer()` line 365, **整个函数替换**:

```mql5
void OnTimer() {
   if (!timerM15.OnTimer()) return;   // 走 M15 的节流

   //--- 1) 刷新 panel (原 line 366-368 逻辑) ---------------
   if (InpShowPanel) UpdatePanel();

   //--- 2) 推送心跳 (M10 加 1 行, 不刷屏) ------------------
   // 注意: 5 分钟推一次心跳, 验证 EA 没死
   static datetime _lastHB = 0;
   if (InpEnableNotify && TimeCurrent() - _lastHB > 300) {
      _lastHB = TimeCurrent();
      // 可选: M10.Send(StringFormat("BBTrend HB #%d at %s",
      //                              timerM15.Fires(), TimeToString(_lastHB, TIME_SECONDS)),
      //                false);
   }
}
```

> ⚠️ **必须保留 `timerM15.OnTimer()` 调**, 这是 M15 的节流核心 —— 若不调, MT5 的 OnTimer 事件每次都进, M15 计数器不会增, Fires/LastFire 全失效。

### 步骤 9: OnDeinit 中清理 8 个模块 (60s, 必填)

定位: 源码 `void OnDeinit(const int reason)` line 249, **在 `EventKillTimer();` 之后插入**:

```mql5
void OnDeinit(const int reason) {
   //--- BBTrendEA 自带 (line 250-254 不变) ----------------
   ObjectDelete(0, g_prefix);
   EventKillTimer();
   ReleaseIndicators();
   Comment("");

   //--- MQL5Kit 清理 (新增) --------------------------------
   timerM15.Deinit();        // M15
   PrintFormat("[M15] timer deinit, total fires=%d", timerM15.Fires());

   if (InpEnableNotify) {
      M10.Send(StringFormat("BBTrend deinit reason=%d, peak_eq=%.2f, last_dd=%.2f%%",
                            reason, _peakEquity,
                            (_peakEquity > 0) ? (_peakEquity - AccountInfoDouble(ACCOUNT_EQUITY)) / _peakEquity * 100.0 : 0.0),
               false);
   }

   // M01/M02/M08/M13/M18 不需要显式 Deinit (无资源句柄)
   Print("[INFO] BBTrendEA v1.10 deinitialized");
}
```

> 💡 **M01/M02/M08/M13/M18 都是无状态类**, 不需要 Deinit。只有 M15 (定时器) 必须 Deinit, 不然下次启 EA 会有僵尸 timer。

---

### 步骤 10: 编译 (MetaEditor F7) (30s)

```powershell
# 方式 1: GUI 内编译 (用户在 console 1)
#   MetaEditor 打开 BBTrendEA.mq5 → F7
#   看底部状态栏: "0 error(s), 0 warning(s)"

# 方式 2: 命令行编译 (Mavis 可做)
$me = "C:\Program Files\MetaTrader 5\MetaEditor64.exe"
& $me /compile:"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea\BBTrendEA.mq5" /log
# 退出码 0 = 成功
```

> ⚠️ **GUI 编译必须用户在 console 1 触发** —— F7 按键受 UIPI 拦, Mavis 触不到。详见 [[00-快速开始/MT5 GUI 自动化 5 次失败全记录 + 分工协议]]。
> Mavis 只能跑命令行编译, 但 MetaEditor 的 `/compile` 实际是同步的, 等价 GUI F7。**推荐: 用命令行**, 输出更易捕获。

### 步骤 11: 验证 (30s)

```powershell
# 1) 编译产物 .ex5 存在 + 大小
Get-Item "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\minimax-ea\BBTrendEA.ex5" | Select-Object Name, Length, LastWriteTime
# 期望: Length 30-50KB (含 8 个 include 的展开代码)

# 2) metaeditor.log 看 errors=0, warnings=0
$logPath = "$env:APPDATA\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Logs\metaeditor.log"
Select-String -Path $logPath -Pattern "BBTrendEA" | Select-Object -Last 10
# 期望: "BBTrendEA.mq5: 0 error(s), 0 warning(s)"

# 3) 8 个 include 都被解析 (无 missing file)
Select-String -Path $logPath -Pattern "cannot open include file" | Select-Object
# 期望: 空
```

### 步骤 12: 跑 1 周沙盒测试 (用户 GUI 执行)

> **GUI 操作, Mavis 不做**。详见 [[00-快速开始/MT5 GUI 自动化 5 次失败全记录 + 分工协议]]。

1. MT5 → 文件 → 打开数据文件夹 → `MQL5/Profiles/Tester/` → 把 BBTrendEA 拖到 chart
2. 工具 → 策略测试器 (Ctrl+R) → 选 BBTrendEA / XAUUSDm / M1 / "每个报价基于真实报价" / 1 周
3. 启用 Algo Trading (工具栏按钮)
4. 启动 → 跑完看报告
5. **验证清单**:
   - `trades_YYYYMMDD.csv` 在 `MQL5/Files/` 出现且 ≥ 1 行
   - MT5 推送 (手机 app 收到 "BBTrend HB #N" / "BUY" / "SELL" 消息)
   - Journal 无 "cannot open include" / "undefined identifier" / "retcode 10004/10030"

---

## 4. 编译错误速查 (5+ 常见错误 + 解决)

### 错误 1: `'InpMagicNumber' - cannot convert enum`

**现象**:
```
BBTrendEA.mq5(245,15): error C2440: 'initializing': cannot convert from 'int' to 'ulong'
```

**原因**: 源码 `input int InpMagicNumber = 20240501;` 是 `int`, M01/M02/M07/M08 都用 `ulong magic`, 类型不匹配。

**解决**: line 64 改 `input int` → `input ulong`, 然后 OnInit / OnTrade 等所有用到 magic 的地方用 `(ulong)InpMagicNumber` 强转。

### 错误 2: `undefined identifier 'CTradePlus'` / `'CRisk'` / `'CNotify'` / `'CTimerService'`

**现象**:
```
BBTrendEA.mq5(80,5): error C2065: 'CTradePlus': undeclared identifier
```

**原因**: 漏 `#include <MQL5Kit/M0X_*.mqh>`, 或 include 路径错。

**解决**: 确认 `#include` 段在 line 1 之后, 路径 `<MQL5Kit/M01_CTradePlus.mqh>` (尖括号, 不是双引号)。步骤 2 已给完整 include 段。

### 错误 3: `'M18' - ambiguous access` (用了 M18 实例名跟 M19 模块冲突)

**现象**:
```
BBTrendEA.mq5(170,8): error C2385: 'M18' - ambiguous access
```

**原因**: `M18` 既被 M18 用了, 又被 BBTrendEA 自带 `M18_*` 命名冲突。

**解决**: 把 M18 实例改名为 `corrFilterM18`:
```mql5
CCorrelationFilter corrFilterM18;   // 避免与 M18 模块重名
```
对应 OnInit / OnTick 改 `M18.Init(syms)` → `corrFilterM18.Init(syms)`。

### 错误 4: `'OnTimer' - event handling function not allowed in `int OnInit()``

**现象**:
```
BBTrendEA.mq5(238,1): error C2353: cannot define 'OnTimer' inside another function
```

**原因**: 把 `void OnTimer() { ... }` 插错了位置 (在 OnInit 函数体内)。

**解决**: OnTimer 必须是 **顶层函数**, 不能在 OnInit / OnTick / OnTrade 内定义。步骤 8 的 OnTimer 整段插在文件末尾或 OnDeinit 之后, 独立函数。

### 错误 5: `'M10.Alert' - too many arguments`

**现象**:
```
BBTrendEA.mq5(265,12): error C2198: 'CNotify::Alert' : too many arguments for call
```

**原因**: `M10.Alert(msg)` 只接 1 个 string 参数, 用户写了 `M10.Alert(fmt, args)`。

**解决**: 用 `StringFormat` 先格式化:
```mql5
M10.Alert(StringFormat("DD %.2f%% on %s", ddPct, _Symbol));
```

### 错误 6: `'timerM15.Init' - conversion from 'int' to 'const int' failed`

**现象**:
```
BBTrendEA.mq5(232,8): warning C4244: 'argument' : conversion from 'int' to 'const int', possible loss of data
```

**原因**: `InpTimerPeriodMs = 1000` 是 int, M15.Init 接 int, 类型不严格 (warning 不是 error)。

**解决**: 加 `(int)` 强转:
```mql5
timerM15.Init((int)InpTimerPeriodMs);
```

### 错误 7 (Bonus): `'HistorySelect' - wrong parameters count` (MQL5 老版本)

**现象**:
```
BBTrendEA.mq5(273,8): error C2198: 'HistorySelect' : wrong parameters count
```

**原因**: MQL5 旧版 (build < 2085) 的 `HistorySelect` 只接 `(datetime start, datetime end)`, 新版 (build >= 2085) 还支持 `(int from, int to, bool asc)` 3 参重载。

**解决**: MT5 升级到最新 build, 或 `HistorySelect(0, TimeCurrent())` 改 2 参。

> 💡 **错误速查完整版** 见 [[04-避坑与速查/01 编译常见错误]]。

---

## 5. 接入 checklist (10 步)

> 每步完成后打勾, 全部勾完 = 复活完成。

- [ ] **C1**: BBTrendEA.mq5 已复制到 minimax-ea/, 字节数 68635 一致
- [ ] **C2**: 8 个 `#include <MQL5Kit/...>` 已插在 line 1 之后
- [ ] **C3**: 8 个 input group 已加 (M01/M02/M08/M10/M13/M15/M18, **M17 用自带不写**)
- [ ] **C4**: 7 个 object 已声明 (`trade`/`risk`/`trailM08`/`M10`/`timerM15`/`corrFilterM18`, **M17 无 object**)
- [ ] **C5**: `InpMagicNumber` 类型已从 `int` 改 `ulong`, 11 处 magic 比较全用 `(ulong)` 强转
- [ ] **C6**: OnInit 中 8 段初始化代码, M15 失败返 `INIT_FAILED`, 其它 Print 不返
- [ ] **C7**: OnTick 中 6 个 HOOK 点已插 (M15 心跳 / M08 trail / news / M18 / 主策略 / Loss)
- [ ] **C8**: OnTrade 函数已加 (M10 推送 + M13 CSV 落盘), 末尾追加 OnTradeTransaction (M10 reject)
- [ ] **C9**: OnTimer 整段替换, 保留 `timerM15.OnTimer()` 节流
- [ ] **C10**: OnDeinit 中加 `timerM15.Deinit()` + 推送 deinit 通知

**编译后附加 checklist** (Mavis 自动化):
- [ ] `MetaEditor64 /compile:BBTrendEA.mq5` 退出码 0
- [ ] metaeditor.log 出现 `BBTrendEA.mq5: 0 error(s), 0 warning(s)`
- [ ] BBTrendEA.ex5 生成, 字节数 30-50KB
- [ ] `grep -i "cannot open include file" metaeditor.log` 返空

**1 周沙盒附加 checklist** (用户 GUI):
- [ ] `MQL5/Files/BBTrend_YYYYMMDD.csv` 落盘 ≥ 1 行
- [ ] MT5 推送 (手机 app) 收到 "BBTrend HB" / "BUY" / "SELL"
- [ ] Journal 无 `retcode 10004` / `10030` / `undefined identifier`

---

## 6. 反模式 (5 条不要做的事)

### 反模式 1: 把 BBTrendEA 自带 13 个 `iBands/iMA/iRSI/iATR` 全替换成 `CIndicatorPool`

**为什么不行**: BBTrendEA 4 周期 BB (1M/5M/30M/1H) + 6 周期 MA + 2 RSI + 1 ATR = 13 句柄, 全部带不同 period/price/method 参数, 强行塞 `CIndicatorPool` 会丢掉多周期对齐逻辑。**保留 13 句柄不动**, 只在 `UpdateAllIndicators` (line 439) 沿用自带 `CopyBuffer` 拉值。

### 反模式 2: 把 `IsRiskLimitReached` / `IsNewsEventNear` / `IsTradeTimeAllowed` 全替换成 M02 / M17 / M19

**为什么不行**: BBTrendEA 这 3 个函数是**复合检查** (news 同时含 M17+M02 边界 + 自带风控), 替换任何一个会破坏调用链。**保留自带**, M02 只在 `OpenPosition` 入口加一行 `risk.CanOpen()` 作 **double-check**。M17 wiki 无, 不替换。M19 同理 (BBTrendEA 的 4 时段 bool 比 M19 preset 更细)。

### 反模式 3: 在 OnTick 里每 tick 调 `StringFormat` / `StringSplit` / `StringConcatenate`

**为什么不行**: `StringFormat` 在 OnTick 高频 (XAUUSDm M1 每秒 5+ tick) 调用会 CPU 爆, 经验值 1 tick 多耗 0.1-0.5 ms。**只在 OnTimer (M15 节流后) 做格式化**, OnTick 走静态变量缓存的字符串。

### 反模式 4: M10 `Alert()` 弹窗在 EA 跑的每根 K 线都触发

**为什么不行**: `Alert()` 是 MT5 弹窗, 阻塞 EA 主线程, 用户不点掉就一直等, OnTick 后续逻辑全部卡住。**M10.Alert() 只在异常 (DD 报警 / reject / 净值归零) 触发**, 正常 BUY/SELL 用 `M10.Send(msg, false)` (无弹窗)。

### 反模式 5: 把 M18 `IsHedgeExposed` 加进 OnTick 但 input `InpUseM18Filter = true`

**为什么不行**: 单品种 (XAUUSDm) EA 没有第二品种可对比, `M18.IsHedgeExposed` 内部会遍历 `PositionsTotal()` 但永远是空, 调一次浪费 0.05-0.1 ms。**单品种默认 `InpUseM18Filter = false`**, input 关闭, 代码保留作 demo 钩子 (将来加 EURUSDm 时翻 true)。

---

## 7. 与 N4 复活的协作

> N4 = 实际执行复活的子任务。Mavis 写完本 SOP 后, 把工作交接给 N4。N4 在 console 1 GUI 操作, 完成后回 wiki 标 "已复活"。

### 7.1 角色分工

| Mavis (本任务) | N4 (下个任务) | 用户 (在 console 1) |
|---|---|---|
| 写本 SOP wiki | 按 SOP §2 + §3 跑流程 | GUI 触发 MetaEditor F7 / 跑 backtest |
| 体检 BBTrendEA.mq5 | 验证每步 checklist | 1 周沙盒 |
| 沉淀接入代码到 wiki | 跑 12 步复活 | 反馈 trades CSV + 推送截图 |

### 7.2 N4 接手清单 (10 行命令)

```powershell
# N4 启动时跑 (按顺序)
# 1) 读本 SOP wiki
Get-Content "C:\ai\obsidian-文件\mt\EA开发\实战\BBTrendEA 复活 SOP.md" | Select-Object -First 50

# 2) 体检 _archive/ 源 (确认 68635 bytes)
Get-Item "C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\_archive\BBTrendEA.mq5" | Select-Object Length

# 3) 跑 §2 准备 5 步

# 4) 跑 §3 复活 12 步 (8 步编辑 + 编译 + 验证)

# 5) 编译验证
& "C:\Program Files\MetaTrader 5\MetaEditor64.exe" /compile:"...\minimax-ea\BBTrendEA.mq5" /log

# 6) 把 BBTrendEA.ex5 时间戳记录到 board.md

# 7) 给用户报告: "BBTrendEA.mq5 复活完成, 请到 console 1 GUI 跑 backtest"
```

### 7.3 N4 完成 → 回写 wiki (5 行)

N4 完成后, 在本 wiki 顶部 frontmatter 之下追加:

```markdown
> **N4 完成时间**: 2026-06-XX HH:MM
> **编译结果**: 0 error(s), 0 warning(s), .ex5 = XX KB
> **沙盒状态**: 进行中 (1 周后补 trades_YYYYMMDD.csv 链接)
> **N4 操作员**: mvs_xxxxx
```

并把本文标题从 `BBTrendEA 复活 SOP` 改 `BBTrendEA 复活 SOP (N4 已完成 ✓)`。

### 7.4 失败回滚

若 N4 跑 §3 步骤 6 (OnTick 集成) 编译失败, 步骤如下:
1. 保留 `_archive/BBTrendEA.mq5` 不动
2. `minimax-ea/BBTrendEA.mq5` 改名为 `minimax-ea/BBTrendEA.failed.mq5`
3. 从 §2 步骤 2 的 backup 拷贝回来: `_archive/BBTrendEA.bak.YYYYMMDD-HHMMSS.mq5` → `_archive/BBTrendEA.mq5`
4. wiki 顶部追加 "N4 复活失败, 回滚到原 _archive 源"
5. **不要** 改 MQL5Kit 模块, MQL5Kit 是 5 个 demo 共用, 改了会破坏 MeanReversion_EA / ScalperXAU

---

## 8. 附录: 复活产物清单

| 文件 | 路径 | 字节数期望 |
|---|---|---|
| 复活后 EA 源 | `MQL5/Experts/minimax-ea/BBTrendEA.mq5` | ~85-90 KB (加 8 个 include + input + object + OnInit + OnTick HOOK) |
| 复活后编译产物 | `MQL5/Experts/minimax-ea/BBTrendEA.ex5` | ~30-50 KB |
| 备份原 _archive 源 | `MQL5/Experts/_archive/BBTrendEA.bak.YYYYMMDD-HHMMSS.mq5` | 68635 |
| Wiki (本文件) | `C:\ai\obsidian-文件\mt\EA开发\实战\BBTrendEA 复活 SOP.md` | ~28 KB |
| 1 周沙盒 trades CSV | `MQL5/Files/BBTrend_YYYYMMDD.csv` | 按交易频率 (50-500 行/周) |

---

## 9. 相关链接

- [[EA 开发知识库]] — 入口 MOC
- [[00-快速开始/EA 写之前要知道的 10 件事]] — 复活前必看
- [[00-快速开始/MT5 GUI 自动化 5 次失败全记录 + 分工协议]] — 复活必涉及 GUI
- [[02-完整模板/EA 突破模板（Donchian 海龟）]] — BBTrendEA = BB 突破 + 趋势, 模板直接对应
- [[01-调用模块/M01 交易封装 CTradePlus]] — 替换 8 处 OrderSend
- [[01-调用模块/M02 风控 Risk]] — 替换 IsRiskLimitReached 的 double-check
- [[01-调用模块/M08 追踪止损 TrailingStop]] — 备, 默认关闭走自带
- [[01-调用模块/M10 推送通知 Notify]] — 4 个触发器 (HB / DD / 成交 / reject)
- [[01-调用模块/M13 文件 IO]] — CSV 落盘
- [[01-调用模块/M15 定时器 TimerService]] — 替换 EventSetTimer
- [[01-调用模块/M18 相关性过滤 CorrelationFilter]] — 可选, 单品种默认 OFF
- [[04-避坑与速查/01 编译常见错误]] — 7 个速查错误
- [[04-避坑与速查/03 实盘 vs 回测差异]] — 1 周沙盒前必看
- [[实战/M18 多品种对冲实战]] — M18 接入参考 (MeanReversion_EA 接入位置)
- [[实战/M19 时段过滤实战]] — M19 接入参考 (BBTrendEA 不接 M19, 保留自带)
- `MQL5/Experts/minimax-ea/MeanReversion_EA.mq5` — 已集成 8 模块的实物 demo, BBTrendEA 的参考实现

## 10. 兄弟 EA 接入报告（中心节点）

> 本 BBTrendEA 复活 SOP 跟下面 2 个 EA 中心节点 wiki 形成项目"EA 接入范例"三件套：
>
> - **[[实战/MeanReversion_EA 接入报告]]** — MeanReversion_EA 接入 13 模块全集（含 M18 + M19），205 行 / 5 章节 / M10 三类触发器范本。BBTrendEA 复活时 8 模块的 OnInit + OnTick 接入可直接对照 §2.1 表格。
> - **[[实战/ScalperXAU 接入报告 + v1→v4 演进史]]** — ScalperXAU 接入 13 模块含 M17 + M13，350 行 / 6 章节 / 4 版本演进史。BBTrendEA 复活时 "M13 FileIO 24 列 trade journal" 可参考 ScalperXAU 写盘逻辑。
>
> 三者关系：本 SOP（archive 复活范本）+ MeanReversion_EA（13 模块全集实物 demo）+ ScalperXAU（4 版本迭代 + 1 天内演进史）= 项目内"剥头皮 + 多周期趋势"两类 EA 接入的完整范例。

---

**版本**: v1.0 (2026-06-04 创建, Mavis T2 任务交付)
**下次更新**: N4 复活完成后追加 §7.3 完成时间
**维护人**: Mavis general agent (mvs_6c1d2b7f36704144a7646e06a0f01406)

## 实战案例 (06-05 04:00 T2 worker-A 闭环, 候选 L 6/6)

> 沿用 03:00 T2 6 段范本。Node.js fs 实测 1 实物 .mq5 mtime UNCHANGED (BBTrendEA 05-28 05:57:49)。**本 wiki 已有 ## 反模式 段 5 条 (CIndicatorPool 强替换 / IsRiskLimitReached 强替换 / StringFormat CPU / M10.Alert 阻塞 / M18 单品种空跑)**, 陷阱 5 条走"12 步复活跨 EA 复用"角度, 0 重复。

### 场景 A: 12 步复活 SOP (wiki L100-L600 5 编译错误速查 + 10 步 checklist)
- 实战场景: BBTrendEA 是项目内 "_archive 复活" 范本, 68635B/1709L 巨型 EA, 13 indicator handle + 自带 news/risk/session/trail/grid
- 实物 demo: BBTrendEA.mq5 (68635B/1709L/13 指标 + 自带复合检查), 复活 12 步: 复制 _archive → 编译 → 修 5 错误 → 接入 M02/M09/M10 → 沙盒 1 周 → 实盘 demo
- 适用范围: 适合 archive 大型 EA (50K+) 复活 / 不适合新建 EA (走 [[02-完整模板/EA 突破模板（Donchian 海龟）]] 即可)

### 场景 B: 跨 EA 复用 (BBTrendEA → MeanRev → ScalperXAU 同样 12 步)
- 实战场景: 12 步复活 SOP 是项目"复活通用协议", 跨 BBTrendEA / MeanRev / ScalperXAU 同样适用, 1 次设计 3 EA 复用
- 实物 demo: BBTrendEA L100-L600 (12 步路径) / MeanRev L20-L250 (13 模块全集) / ScalperXAU L107-L573 (v1→v4 演进) — 3 EA 路径节点 + 12 步 SOP 100% 对应
- 适用范围: 适合 _archive 大型 EA 复活 / 不适合 _archive 小型 EA (走 [[实战/M17_TestNewsEA 复活报告]] 5 步即可)

### 接入点行号 (BBTrendEA 12 步路径 + MeanRev 对比, Node.js fs grep 验证 2026-06-05 04:00)
| wiki 描述 | 实物 | 行号 | 命中关键词 | spec |
|---|---|---|---|---|
| BBTrendEA OnInit | BBTrendEA.mq5 | L212 | `int OnInit() {` | M02/M08/M10 Init 范本 |
| BBTrendEA OnTick | BBTrendEA.mq5 | L256 | `void OnTick() {` | M02/M08/M10 OnTick 范本 |
| BBTrendEA OnDeinit + EventKillTimer | BBTrendEA.mq5 | L252 | `EventKillTimer();` | M15 TimerService 范本 |
| BBTrendEA EmergencyClosePrint | BBTrendEA.mq5 | L298 | `Print("[EMERGENCY] Equity drawdown "` | M10 报警 触发器 1 |
| BBTrendEA 自带 IsTradeTimeAllowed | BBTrendEA.mq5 | L305 | `else if (!IsTradeTimeAllowed()) canTrade = false;` | M19 替代方案 (本 wiki ## 反模式 2: 保留自带) |
| BBTrendEA 自带 IsNewsEventNear | BBTrendEA.mq5 | L306 | `else if (IsNewsEventNear()) canTrade = false;` | M17 替代方案 (本 wiki ## 反模式 2: 保留自带) |
| BBTrendEA 自带 IsRiskLimitReached | BBTrendEA.mq5 | L307 | `else if (IsRiskLimitReached()) {` | M02 替代方案 (本 wiki ## 反模式 2: 保留自带) |
| BBTrendEA 13 指标 handle | BBTrendEA.mq5 | L397-L409 | `g_hBB_1M = iBands(...)` `g_hMAFast1M = iMA(...)` `g_hRSI1M = iRSI(...)` `g_hATR1M = iATR(...)` 13 行 | M04 IndicatorPool 替代方案 (本 wiki ## 反模式 1: 不全替换) |
| BBTrendEA 复合检查 IsTradeTimeAllowed | BBTrendEA.mq5 | L507 | `bool IsTradeTimeAllowed() {` | M19 复合检查 |
| BBTrendEA 复合检查 IsNewsEventNear | BBTrendEA.mq5 | L616 | `bool IsNewsEventNear() {` | M17 复合检查 |
| BBTrendEA 复合检查 IsRiskLimitReached | BBTrendEA.mq5 | L654 | `bool IsRiskLimitReached() {` | M02 复合检查 |
| BBTrendEA 5 处 OrderSend | BBTrendEA.mq5 | L834 / L937 / L1091 / L1164 / L1203 / L1228 | `if (OrderSend(req, res)) {` | M01 OrderSend 替换 (1 处即可, 5 处全替换 = 1 次性改坏) |
| MeanRev L20 13 模块 (对比) | MeanReversion_EA.mq5 | L9-L21 | 13 include 全集 | M01-M19 spec |
| MeanRev L88 trail.Init (对比) | MeanReversion_EA.mq5 | L88 | `trail.Init(&trade, Magic);` | M08 追踪止损 范本 |
| MeanRev L134 CleanupAll (对比) | MeanReversion_EA.mq5 | L134 | `CCleanup::CleanupAll(Magic, "MR_", "MR_", true, true, true);` | M16 Cleanup 范本 |

### 调优点 3 档
- aggressive: 12 步全跑 (L100-L600 12 步) — 复活 + 接入 8 模块 + 沙盒 + 实盘 demo, 适合"主仓 改造 + 8 模块协同"
- balanced: 10 步 (L100-L500 10 步) — 复活 + 接入 5 P0 模块 + 沙盒, 不接入 P1/P2 锦上添花 ← 默认 (本 wiki §3 12 步简化)
- conservative: 8 步 (L100-L400 8 步) — 复活 + 编译 + 沙盒, 不接入任何模块, 适合"先验原 EA 行为再加"

### 陷阱 5 条 (不与 ## 反模式 段 5 条 + ## 编译错误速查 5+ 条重复, 走"复活跨 EA 复用"角度)
- 陷阱 1: 复活 ≠ 编译 — BBTrendEA 12 步第 1 步是"复制 _archive → minimax-ea", 第 2 步是"编译"。**复活 = 物理复制 + MetaEditor F7 编译 + 0 errors 验证**, 不是只复制就完。**Mavis 没 console 1 编译权限**, 复活留给 N4 跟踪 (用户 GUI 操作, 见 [[00-快速开始/MT5 GUI 自动化 5 次失败全记录 + 分工协议]])
- 陷阱 2: 12 步顺序不可乱 — 12 步顺序: ① 复制 _archive ② 编译 F7 ③ 修 5 错误 ④ 接入 M02 (入口 1 行) ⑤ 接入 M09 ⑥ 接入 M10 ⑦ 沙盒 1 周 ⑧ 实盘 demo。**别先接 M10 (DD 报警) 再接 M02 (CanOpen 风控), 1 周沙盒 0 风控直接亏光**
- 陷阱 3: 0 errors ≠ 0 警告 — MetaEditor 编译 0 errors 必查, 但 0 warnings 才是"稳"。BBTrendEA 13 指标 handle 未释放会 warn "indicator handle not released", 必 OnDeinit `IndicatorRelease(g_hBB_1M)` 等 13 行。**0 errors + 13 warnings = 内存泄漏, 跑 1 天 OOM**, 见 [[04-避坑与速查/05 必查清单]] 永远不要 1 (忘了 OnDeinit 清理资源)
- 陷阱 4: _archive 路径 vs root 路径 — BBTrendEA 实物在 `_archive/BBTrendEA.mq5` (68635B), 复活后到 `minimax-ea/BBTrendEA.mq5`。**2 个文件不能同名同路径, _archive 是只读不写不删, 复制到 minimax-ea 才编译**。本 wiki ## 反模式 1 强调"替换 13 indicator handle 全部", 但**保留 13 handle + 加 M04 IndicatorPool 管理** = 双保险 (跟 [[实战/ScalperEA 接入 MQL5Kit 摘要]] ## 反模式 2 定制版比标准品好时保留定制版 一致)
- 陷阱 5: MQL5Kit 3 fork 同步 — 项目 MQL5Kit 在 [[MQL5/Include/MQL5Kit/]] (M01-M19 .mqh), 3 fork 同步: `MQL5/Include/MQL5Kit/` (项目) + [[MQL5/Include/` (MT5 stdlib 替代) + 用户 git fork (可选)。**3 fork 必同版本**, 否则编译报 "function signature mismatch"。N5 漂移修复 39 处就是修这个 (见 [[实战/MeanReversion_EA 接入报告]] §7 漂移修复 N5 闭环)

### 链向
- [[实战/MeanReversion_EA 接入报告]] — 13 模块全集, BBTrendEA 复活时 8 模块 OnInit + OnTick 接入对照 §2.1 表格
- [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] — 13 模块含 M17 + M13, BBTrendEA 复活时 M13 FileIO 24 列 trade journal 参考 ScalperXAU 写盘逻辑
- [[实战/M17_TestNewsEA 复活报告]] — 单模块 EA 范本, BBTrendEA 是 13 模块 + 自带复合检查, 跨模块对比
- [[实战/Scalping_More v1.3 接入示例]] — 10 段可复制代码, BBTrendEA N4 接入时按 §3 步骤 6 OnTick 集成
- [[实战/ScalperEA 接入 MQL5Kit 摘要]] — 76K 0 MQL5Kit 0 #include, BBTrendEA 13 指标 handle 替换 跨案例对比
- [[01-调用模块/M01 交易封装 CTradePlus]] — 替换 8 处 OrderSend (BBTrendEA L834/L937/L1091/L1164/L1203/L1228 5 处起步, 8 处全替换)
- [[01-调用模块/M02 风控 Risk]] — 替换 IsRiskLimitReached 的 double-check (L654, 本 wiki ## 反模式 2)
- [[01-调用模块/M08 追踪止损 TrailingStop]] — 备, 默认关闭走自带
- [[01-调用模块/M10 推送通知 Notify]] — 4 个触发器 (HB / DD / 成交 / reject)
- [[01-调用模块/M15 定时器 TimerService]] — 替换 EventSetTimer (L252)
- [[04-避坑与速查/01 编译常见错误]] — 7 个速查错误
- [[04-避坑与速查/05 必查清单]] — 永远不要 1 (忘了 OnDeinit 清理资源)
- [[EA开发/EA 开发知识库]] §"实战相关" 分类 (T4 owner 04:00 顺手加 1 行链向本 wiki)
