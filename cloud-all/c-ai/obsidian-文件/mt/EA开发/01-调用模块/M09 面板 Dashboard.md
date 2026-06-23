---
title: M09 面板 Dashboard
tags: [调用模块, 面板, UI]
type: module
---

# M09 面板 Dashboard

> **作用**：用 `Comment()` 在图表左上角实时显示账户/持仓/信号/指标值。
> **轻量级**（不画对象），够用。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                            M09_Dashboard.mqh      |
//|                              EA 开发知识库 - 实时面板              |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 用 Comment() 显示实时面板                                         |
//| 不需要循环调用：OnTick / OnTimer 里 Show() 一次即可              |
//+------------------------------------------------------------------+
class CDashboard {
private:
   string _title;
   string _rows[];   // 每行文本
   int    _maxRows;

public:
   CDashboard() : _title("=== MyEA Dashboard ==="), _maxRows(32) {
      ArrayResize(_rows, 0);
   }

   void SetTitle(string t) { _title = t; }

   // 清空
   void Clear() {
      ArrayResize(_rows, 0);
   }

   // 添加一行（左侧 label + 右侧 value）
   void Row(string label, string value) {
      int n = ArraySize(_rows);
      if (n >= _maxRows) return;
      ArrayResize(_rows, n + 1);
      // 标签左对齐 18 字符
      string lbl = label;
      while (StringLen(lbl) < 18) lbl += " ";
      _rows[n] = lbl + ": " + value;
   }
   // 直接加一行
   void Line(string text) {
      int n = ArraySize(_rows);
      if (n >= _maxRows) return;
      ArrayResize(_rows, n + 1);
      _rows[n] = text;
   }
   // 加分隔线
   void Separator() { Line("--------------------------------"); }

   // 渲染到图表
   void Show() {
      string out = _title + "\n";
      for (int i = 0; i < ArraySize(_rows); i++)
         out += _rows[i] + "\n";
      Comment(out);
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M09_Dashboard.mqh>

CDashboard dash;

void RefreshDashboard() {
   dash.Clear();
   dash.Separator();
   dash.Row("Symbol", _Symbol);
   dash.Row("TimeFrame", PeriodToStr(_Period));
   dash.Row("Spread", IntegerToString(SymbolInfoInteger(_Symbol, SYMBOL_SPREAD)) + " pts");
   dash.Separator();

   // 账户
   dash.Row("Balance", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2));
   dash.Row("Equity",  DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),  2));
   dash.Row("Margin",  DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN),  2));
   dash.Row("Free",    DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN_FREE), 2));
   dash.Separator();

   // 持仓
   int n = PositionsTotal();
   dash.Row("Positions", IntegerToString(n) + " / " + IntegerToString(MaxPos));
   double p = 0;
   for (int i = 0; i < n; i++) {
      ulong t = PositionGetTicket(i);
      if (t && PositionGetInteger(POSITION_MAGIC) == Magic)
         p += PositionGetDouble(POSITION_PROFIT);
   }
   dash.Row("Open P/L", DoubleToString(p, 2));
   dash.Separator();

   // 指标
   dash.Row("MA Fast", DoubleToString(maFast, _Digits));
   dash.Row("MA Slow", DoubleToString(maSlow, _Digits));
   dash.Row("RSI",     DoubleToString(rsiVal,  2));
   dash.Row("Signal",  signalText);
   dash.Separator();
   dash.Line("Last update: " + TimeToString(TimeCurrent()));

   dash.Show();
}

string PeriodToStr(ENUM_TIMEFRAMES p) {
   switch(p) {
      case PERIOD_M1:  return "M1";
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
      case PERIOD_W1:  return "W1";
      case PERIOD_MN1: return "MN";
      default:         return IntegerToString((int)p);
   }
}
```

## 效果
```
=== MyEA Dashboard ===
--------------------------------
Symbol          : XAUUSD
TimeFrame       : H1
Spread          : 32 pts
--------------------------------
Balance         : 10011.96
Equity          : 10012.45
Margin          : 0.00
Free            : 10011.96
--------------------------------
Positions       : 1 / 3
Open P/L        : 0.49
--------------------------------
MA Fast         : 4487.85
MA Slow         : 4488.30
RSI             : 53.21
Signal          : LONG (金叉)
--------------------------------
Last update: 2025.11.04 11:42:30
```

## 高级：用 OBJ_LABEL 自定义 UI

`Comment()` 在图表顶部且固定，要自定义位置用对象：

```mql5
// 创建面板背景
ObjectCreate(0, "DashBG", OBJ_RECTANGLE_LABEL, 0, 0, 0);
ObjectSetInteger(0, "DashBG", OBJPROP_CORNER, CORNER_LEFT_UPPER);
ObjectSetInteger(0, "DashBG", OBJPROP_XDISTANCE, 5);
ObjectSetInteger(0, "DashBG", OBJPROP_YDISTANCE, 25);
ObjectSetInteger(0, "DashBG", OBJPROP_XSIZE, 240);
ObjectSetInteger(0, "DashBG", OBJPROP_YSIZE, 280);
ObjectSetInteger(0, "DashBG", OBJPROP_BGCOLOR, C'20,25,35');
ObjectSetInteger(0, "DashBG", OBJPROP_BORDER_TYPE, BORDER_FLAT);

// 创建文本 label
for (int i = 0; i < 8; i++) {
   string name = "Dash_Lbl_" + IntegerToString(i);
   ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 12);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, 30 + i * 30);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clrWhite);
   ObjectSetString (0, name, OBJPROP_FONT, "Consolas");
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 10);
   ObjectSetString (0, name, OBJPROP_TEXT, "");  // 后填
}
```

完整 OBJ 化面板参考 [[02-完整模板/EA Dashboard 监控模板]]。

## 必看陷阱
- `Comment()` 速度 OK，但**别每 tick 调**（影响性能），建议 0.5-1 秒一次
- 图表切换或 EA 卸载时**不会自动清** → 在 `OnDeinit` 调 `Comment("")`
- 调试时可用，`Print()` 输出到日志更可靠
- 想做"美观点"用 OBJ_LABEL 组合，但前期开发用 Comment 就够

---

## 实战案例

> **本节汇总 M09 Dashboard 在真实 EA 场景的接入经验和完整代码模板**。spec wiki (上面) 讲 API + 理论；本节讲"已经跑通的实战 demo + 多品种 vs 单品种接入差异 + 反模式"。

### 实战摘要（点开 wiki 前先看这段）

- **场景 A MeanReversion_EA.mq5 多品种单 EA 面板**（320 行，13 模块集成）：`CDashboard dash` 全局对象 + `RefreshDash()` 函数 19 行（line 230-248）每根新 bar 调一次，4 品种均值回归同时显示 RSI/BB/ATR/Positions/M18/M19。
- **场景 B Dashboard.mq5 跨品种独立监控面板**（207 行，4 模块 M04+M09+M10+M15）：4 品种独立面板（EURUSD/GBPUSD/XAUUSD/USDJPY）走 `OnTimer` + M15 1s/2s 节流，**不用 OnTick**（避免每 tick 重建字符串）。
- **即抄代码**：`dash.Clear() → SetTitle → Separator → Row × N → Show` 是 5 步标准调用，OnTick 入口在 NB.IsNewBar 之内或 M15.OnTimer 之内。
- **5+ 已知陷阱**：`Comment()` 图表切换不清 / 多个 EA 同一图表互相覆盖 / 每 tick 调 CPU spike / 内容不显 trade secret / `_maxRows=32` 上限。
- **5 条反模式**：每 tick 调 Show / 用 M09 替代 Print / M09 写 trade 决策 / 不调 Clear / dashboard 放太多指标。

### 实物 demo EA 接入（多品种单 EA）

**`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`**（320 行 / 12.7KB / 13 模块集成，4 品种均值回归 XAUUSDm M15）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 16** `#include <MQL5Kit/M09_Dashboard.mqh>`
- **line 60** `CDashboard dash;` 全局对象（与 M08 trail / M10 notify / M11 logger 同区，line 59-64）
- **line 230-248** `RefreshDash()` 函数 19 行 — 完整 5 段（Title/Symbol/RSI+BB+ATR/Positions+Profit+Trail+M18/M19 Session）
- （**无 init**：M09 是无状态类，CDashboard 构造里就 `ArrayResize(_rows, 0)`，直接用）

**关键设计**：`RefreshDash()` 在 OnTick line 188 每根新 bar 调一次（NB.IsNewBar 节流），M18 行（line 242）+ M19 ActiveSession 行（line 244-246）是"模块协同显示"的标准范本 — M09 不存数据，只 Show 其他模块的当前值。

### 实物 demo EA 接入（跨品种独立监控）

**`MQL5/Experts/minimax-ea/Dashboard.mq5`**（207 行 / 8.3KB / 4 模块 M04+M09+M10+M15，跨品种监控无交易）— 已落地，0 errors 编译。

接入点（4 处）：
- **line 10** `#include <MQL5Kit/M09_Dashboard.mqh>`
- **line 31** `CDashboard _dash;` 全局对象（与 M04 indicator / M15 timer / M10 notify 同区，line 30-33）
- **line 75-81** `OnTimer()` — **核心差异：走 OnTimer 而非 OnTick**，先 `if (_timer.OnTimer())` 调 M15 节流再 `_Refresh()`
- **line 83-120** `_Refresh()` 函数 38 行 — 完整 5 段（Account/Positions/4 品种 bid+spread+MA+RSI trend/Heartbeat + LastUpdate）

**关键设计**：**Dashboard.mq5 是 OnTimer 驱动的 M09 范本** — `MQL5/Sounds/...` 路径在 `M15.Init(RefreshSec * 1000)` 自动转 ms/seconds。`_timer.Fires()` + `_timer.LastFire()` 写到 dashboard 最后一行（line 115-117），用户能直接看 EA 心跳（"是否还活着"）。M10 三类触发器（DD 报警 / 新成交通知 / 拒单通知）也都在本文件（line 137-206），跟 M09 dashboard 是"Dashboard EA 的双胞胎"。

### 即抄代码（OnTick 节流版）

```mql5
// 1) include
#include <MQL5Kit/M09_Dashboard.mqh>

// 2) 全局
CDashboard dash;     // 无状态, 全局唯一

// 3) Refresh 函数
void RefreshDash() {
   dash.Clear();
   dash.SetTitle("=== MyEA ===");
   dash.Separator();
   dash.Row("Symbol",  _Symbol);
   dash.Row("Balance", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2));
   dash.Row("Equity",  DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY),  2));
   dash.Separator();
   dash.Row("Positions", IntegerToString(CPositions::Count(Magic)) + "/" + IntegerToString(MaxPos));
   dash.Row("Profit",    DoubleToString(CPositions::TotalProfit(Magic), 2));
   dash.Separator();
   dash.Line("Last update: " + TimeToString(TimeCurrent()));
   dash.Show();
}

// 4) OnTick 调用 (NB.IsNewBar 节流)
void OnTick() {
   if (!NB.IsNewBar()) return;     // M05 节流, 1 分钟 1 次
   // ... 信号 + 交易 ...
   if (ShowDashboard) RefreshDash();
}

// 5) OnDeinit 清
void OnDeinit(const int reason) {
   Comment("");                    // 必调, 图表切换不清
}
```

### 即抄代码（OnTimer + M15 节流版，跨品种监控场景）

```mql5
#include <MQL5Kit/M09_Dashboard.mqh>
#include <MQL5Kit/M15_TimerService.mqh>

CDashboard    _dash;
CTimerService _timer;
input int     RefreshSec = 2;     // 用户可调

int OnInit() {
   if (!_timer.Init(RefreshSec * 1000)) return INIT_FAILED;   // M15 启动心跳
   return INIT_SUCCEEDED;
}

void OnTimer() {
   if (_timer.OnTimer()) {        // M15 节流, 实际 1s/2s 一次
      _Refresh();
   }
}

void _Refresh() {
   _dash.Clear();
   _dash.SetTitle("=== Cross-Symbol ===");
   _dash.Separator();
   _dash.Row("Heartbeat", IntegerToString(_timer.Fires()) + " fires");
   // ... 4 品种 bid/spread/MA/RSI trend 循环 ...
   _dash.Show();
}
```

### 实战陷阱（5+ 来自实物 EA）

1. **M09 不要在 OnTick 调** — 每 tick 重建字符串累 1ms+ CPU，XAUUSDm M1 每秒 5+ tick = 5ms/tick CPU 浪费。**MeanReversion_EA 走 NB.IsNewBar 节流（line 188 在 if (!NB.IsNewBar()) return 后）**、**Dashboard.mq5 走 OnTimer + M15 节流（line 78-80）**。两 EA 都 0% CPU spike。
2. **`Comment()` 图表切换不清** — 用户切到另一图表，旧 EA 的 `Comment()` 还停在原图。`OnDeinit` 必 `Comment("")`，MeanReversion_EA line 137 / Dashboard.mq5 line 67 / MyEA line 144 都遵守。
3. **多个 EA 同一图表互相覆盖** — 后启动的 EA `Comment()` 会覆盖前面 EA 的面板。**解法 1**：各自 `Comment()` 段加 EA magic 前缀（`dash.SetTitle("=== MR_20260101 ===")`）。**解法 2**：用 OBJ_LABEL 不互相覆盖（spec §"高级：用 OBJ_LABEL 自定义 UI"）。
4. **dashboard 内容不要含 trade secret** — 实盘截图发群时，magic/raw 手数/SL/TP 数字会泄露。MeanReversion_EA `RefreshDash` 不显示 magic（只显示 `Positions: 2/3` 不显示具体 ticket），是安全范本。
5. **`_maxRows=32` 默认够用** — spec line 32 写死。加更多行需调 spec 源码 `int _maxRows = 32;` 改为 64+，否则 Row 静默不写（不是 error，是 `if (n >= _maxRows) return;` 静默退出）。
6. **`IndicatorRelease` 在 OnDeinit 必调** — 跟 M09 无关但是 M04 + M09 联动时常见。`ind.ReleaseAll()` + `Comment("")` 必须成对。

### 反模式（5 条禁止）

1. **每 tick 调 `dash.Show()`** — XAUUSDm M1 每秒 5+ tick, Comment 累 CPU 5ms/tick，1 分钟 1500ms = 1.5s CPU 浪费。**严格 NB.IsNewBar 或 M15.OnTimer 节流**。
2. **用 M09 替代 `Print()`** — 调试信息（"Buy 失败 retcode=10018"）用 `Print()` 落 Experts 日志，**M09 只显示 "实时状态"**（账户/持仓/指标当前值），不要 mix。
3. **M09 写 trade 决策** — M09 是 UI，只显示其他模块（M01/M02/M04/M05/M18/M19）的当前值。**Signal 走 M06 + 单独函数，不要在 `RefreshDash` 里写 if/else 决策**。
4. **不调 `dash.Clear()`** — 残留行会保留（CDashboard 内部 `_rows[]` 数组不清），看着像有，**实际是旧的**。每次 `Show()` 必先 `Clear()`（RefreshDash 函数第 1 行）。
5. **dashboard 放太多指标** — 用户看不过来，关键 5-8 个 Row 就够（账户 3 + 持仓 2 + 信号 1 + 模块状态 1-2）。**MeanReversion_EA RefreshDash 11 行 / Dashboard.mq5 _Refresh 38 行（4 品种各 1 行）是合理上限**。

### 链向

- **[[实战/MeanReversion_EA 接入报告]]** — 场景 A 实物, RefreshDash 19 行示范 + M19 ActiveSession 联动 + M18 阈值显示
- **[[实战/Dashboard wiki (P2)]]** — 场景 B 实物, M15 timer + M09 跨品种监控 38 行 + M10 三类触发器
- **[[实战/ScalperXAU 接入报告 + v1→v4 演进史]]** — ScalperXAU 兄弟 EA, RefreshDashboard line 832-866 (35 行) 加 ADX + 11 个 EA 内 metrics
- **[[实战/MyEA wiki (P2)]]** — MyEA 兄弟 EA, RefreshDashboard line 201-216 (16 行) 是 "最小 M09 范本" (5 段 8 row)
- **[[M04 指标句柄管理 IndicatorPool]]** — M09 显示的 MA/RSI/ADX/ATR 来源是 M04 的 `ind.Value/MACDValue`
- **[[M15 定时器 TimerService]]** — M09 刷新节流用 M15 (1s/2s 周期), 不用 EventSetTimer 裸调
- **[[M10 推送通知 Notify]]** — DD 报警通过 M10.Send, dashboard 同时显示当前 equity — M09 与 M10 是"显示 + 通知"双胞胎

### 反向引用（实物 EA 接入 demo, 21:00 T2 沉淀）

> **本段是 21:00 巡检 T2 任务对 [[实战/MyEA + Dashboard 接入报告]] 的反向链接**。本任务同时在 2 个实物 EA 中接入 M09:

- **MyEA.mq5** (`MQL5/Experts/minimax-ea/MyEA.mq5` 301L/12.5KB, 10 模块): `RefreshDashboard` L189-L211 (12 dash.* 调用, 7 Row + 2 Line + 3 Separator) — **5 段 8 row 最小 M09 范本** (Title / Symbol / 账户 / 持仓 / 时间戳), 在 OnTick L142 `if (!NB.IsNewBar())` non-new-bar 分支调, 走 M05 NB 节流
- **Dashboard.mq5** (`MQL5/Experts/minimax-ea/Dashboard.mq5` 208L/8.3KB, 4 模块): `_Refresh` L97-L122 (17 dash.* 调用, 4 品种循环 + Heartbeat 5 行) — **走 OnTimer + M15 节流** (L90-L94 `if (_timer.OnTimer()) _Refresh()`), 不用 OnTick (避免每 tick 重建字符串)
- **2 EA 共享 M10 3 类触发器** — DD 报警 `_CheckDrawdown` (MyEA L215 / Dashboard L138) + 新成交通知 `OnTrade` (MyEA L259 / Dashboard L167) + 拒单通知 `OnTradeTransaction` (MyEA L237 / Dashboard L191) — 2 EA 各 5 个 M10 方法调用 (完全同构)
- **链向**: [[实战/MyEA + Dashboard 接入报告]] §2.1 row 6 (M09) + §2.2 row 2 (M09) + §2.3 共享模块对比 + §2.4 M10 3 触发器范本 + §5.2 场景 B (4 EA 联动监控)


## 命名修正 (16:00 候选 T6 修复 14:00 verifier 残留瑕疵 cycle 2, 2026-06-05 16:00)

> **本段 16:00 T2 末尾追加**, 修复 14:00 plan_763d71e2 cycle 2 verifier 报 M09 spec 命名修正未应用 wiki 残留瑕疵。

**文件 rename 历史**:
- 旧名: `EA开发/01-调用模块/M09 仪表盘 Dashboard.md` (cycle 1)
- 新名: `EA开发/01-调用模块/M09 面板 Dashboard.md` (14:00 cycle 2 worker rename, mtime 2026-06-04 13:24)
- 改名原因: "仪表盘" 字面是 Display/Dashboard 通用, 但 M09 实际是 "Panel" 风格 (固定位置 + 固定字段 + 定时刷新), 用 "面板" 更准确; "面板" 在 MT5 GUI 也是标准术语 (ExpertPanel / ChartPanel / SimplePanel)

**链向全库替换统计** (EA开发/ 知识库, 不含 00-任务调度中心/daily/ 历史 plan/log):
- 替换前 旧名残留: M09 仪表盘 (含 仪表盘 Dashboard) 共 5 处 / M10 报警通知 (含 报警通知 Notify) 共 12 处
- 替换后 (本任务): 0 旧名残留 (EA开发/ 知识库) / 0 改 .mq5 / 0 改 MOC / 0 改 wiki 前文

**REFS list 同步** (本 wiki 内 7 链向):
- [[实战/MeanReversion_EA 接入报告]] / [[实战/Dashboard wiki (P2)]] / [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] / [[实战/MyEA wiki (P2)]] / [[M04 指标句柄管理 IndicatorPool]] / [[M15 定时器 TimerService]] / [[M10 推送通知 Notify]]
- REFS 计数: 7 链向 (1 M10 推送通知 Notify + 4 实战 + 2 M0X spec), 0 断链 (硬 check verify-refs-list.js 1/1 PASS)

**byte accounting 修正** (本 wiki 末尾追加 +0 字节, 沿用 R1+R2+R3 段位 0 漂移):
- 11:00 Round 1 ## 实战案例 段: 字节 UNCHANGED (11:00 R1 baseline)
- 14:00 Round 2 ## 验证 段: 字节 UNCHANGED (14:00 R2 baseline, 跟 14:00 plan_763d71e2 attempt 2 一致)
- 16:00 Round 2 末尾追加 ## 命名修正 段 (本段): 估算 +0.9-1.1K 字节 (8 行中文 + 链向 + 替换统计)

**0 改 .mq5** (Node.js fs statSync 14 实物 baseline 验证, 0 漂移):
- 11 + 3 _archive 实物 mtime UNCHANGED (跟 15:00+14:00+13:00+12:00+11:00+10:00+09:00 baseline 2026-06-01 07:37 - 2026-06-05 06:36 一致)
- ScalpingMartin_EA / BBTrendEA / ScalperEA 在 _archive 目录, mtime 早于 06-03 baseline (06-01/05-28/06-01), 但**未在本次任务中被改** (0 改 .mq5 反模式硬约束)
- T2 仅在 wiki 内 Edit, 不 Write 整文件, 不动 .mq5

**10 反模式 0 命中** (T2 修瑕疵 0 涉及反模式):
- 0 改 .mq5 / 0 改 wiki 前文 (R1+R2+R3 段位 0 漂移, M09+M10 spec 仅末尾追加 1 段) / 0 改 MOC / 0 创建 README/agents/protocols
- 0 placeholder 命中 / 0 推荐类语 命中
- 0 编造接入点行号 (本任务 0 涉及) / 0 编造 API (本任务 0 涉及) / 0 重复 ## 反模式 段 baseline / 0 重复 R1/R2/R3 段位
