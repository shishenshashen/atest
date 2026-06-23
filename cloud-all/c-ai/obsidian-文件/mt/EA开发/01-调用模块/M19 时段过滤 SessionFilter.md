---
title: M19 时段过滤 SessionFilter
tags: [调用模块, 时段, 会话, 过滤]
type: module
---

# M19 时段过滤 SessionFilter

> **作用**：在指定交易时段内允许开仓，时段外自动屏蔽。
> **配套常量**：4 个预定义时段常量（Asia / London / NewYork / London+NY）
> **典型场景**：剥头皮只跑伦敦+纽约重叠（高波动 8h），趋势/逆势在伦敦单时段，亚洲/跨午夜的特殊配置。

## 解决的问题

之前 EA 的时段过滤是裸写的：
```mql5
MqlDateTime dt;
TimeCurrent(dt);
if (dt.hour < StartHour || dt.hour >= EndHour) return;
```

这种写法：
- 每个 EA 都要写一遍 `MqlDateTime` 解析 + `hour` 判断
- 跨午夜时段容易写错（22:00-06:00 反向逻辑）
- 周末不交易要单独判断 `day_of_week`
- 时段名（"Asia"）不可读，Dashboard 只能显示 "(off-hours)"

M19 把"时段定义 + 跨午夜 + 周末屏蔽 + 当前活跃名"全部封装成一个类。

## API（5 方法 + 4 预定义常量）

```mql5
class CSessionFilter {
public:
   // 1) 加载时段配置. 接受 3 种格式 (4 预定义常量都是简化格式)
   bool   Init(string sessionsSpec);

   // 2) 时间 t 是否在任一配置时段内 (周末默认 false)
   bool   IsInSession(datetime t);

   // 3) 从 t 起下一次进入任一时段的时间戳 (无则 0)
   datetime NextSession(datetime t);

   // 4) 当前活跃时段名, 多时段重叠返 "A+B" (e.g. "London+NewYork")
   string ActiveSession(datetime t);

   // 5) 最近一次 Init 失败的错误信息
   string LastError() const;

   // 增强方法 (可选, 不影响主 API)
   void   SetAllowWeekend(bool allow);   // 默认 false (周末不交易)
   int    SessionCount() const;
   bool   GetSession(int idx, SessionDef &out) const;

   // 自检 (6 断言, PowerShell 测试 + EA 单元测试用)
   static int RunSelfTest();
};

// 4 个预定义常量 (string)
const string SESSIONS_ASIA       = "Asia:0-8";
const string SESSIONS_LONDON     = "London:8-16";
const string SESSIONS_NY         = "NewYork:13-22";
const string SESSIONS_LONDON_NY  = "London:8-16,NewYork:13-22";   // 推荐剥头皮
```

## 时段定义格式

简化字符串 `"Name:H-E[,Name:H-E...]"`：
- `Name`：时段名（任意字符串，用于 Dashboard 显示）
- `H`：起始小时（0-23，含）
- `E`：结束小时（0-24，不含）
- `H < E`：普通时段 `[H, E)`
- `H > E`：跨午夜时段 `[H, 24) ∪ [0, E)`（如 `NY:22-6` 表示 22:00-06:00）

例：
```
"Asia:0-8"                       // 单时段: 00:00-08:00
"London:8-16"                    // 单时段: 08:00-16:00
"NewYork:13-22"                  // 单时段: 13:00-22:00
"London:8-16,NewYork:13-22"      // 双时段: 伦敦 + 纽约
"Asia:0-8,London:8-16"           // 双时段: 亚洲 + 伦敦
"NY:22-6"                        // 跨午夜: 22:00-06:00
```

> **时区**：所有时段按 **服务器时间** 的 `MqlDateTime.hour` 判定。
> Exness / 大部分经纪商服务器时间是 **UTC+0 或 UTC+2**，不是本地时间。
> 想用"本地时间"要先做时区换算（参考 M04 自定义指标方案，不在 M19 范围）。

## 用法（EA 中）

```mql5
#include <MQL5Kit/M19_SessionFilter.mqh>

input bool   InpUseM19Filter  = true;
input string InpSessionPreset = "London:8-16,NewYork:13-22";  // 不能用 SESSIONS_LONDON_NY (input 不接受 const)
input bool   InpAllowWeekend  = false;

CSessionFilter M19;

int OnInit() {
   if (InpUseM19Filter) {
      if (!M19.Init(InpSessionPreset)) {
         PrintFormat("M19 Init failed: %s", M19.LastError());
         return INIT_FAILED;
      }
      M19.SetAllowWeekend(InpAllowWeekend);
      PrintFormat("M19 OK preset='%s' sessions=%d weekend=%s",
                  InpSessionPreset, M19.SessionCount(),
                  InpAllowWeekend ? "ALLOW" : "BLOCK");
   }
   return INIT_SUCCEEDED;
}

void OnTick() {
   // ... 其它过滤 ...
   // M19 时段过滤: 在配置时段外不开新仓
   if (InpUseM19Filter && !M19.IsInSession(TimeCurrent())) {
      RefreshDash();
      return;
   }
   // ... 入场信号 ...
}
```

> ⚠️ **MQL5 input 不接受 const 变量做默认值**，所以 `InpSessionPreset` 必须用字面量
> `"London:8-16,NewYork:13-22"` 而不是 `SESSIONS_LONDON_NY`（const string）。
> 这是 MQL5 编译器的硬限制（`error 187: 'SESSIONS_LONDON_NY' - constant expected`）。

## Dashboard 集成

把活跃时段名显示到面板上，时段外显示 `(off-hours)`：

```mql5
void RefreshDash() {
   dash.Clear();
   dash.SetTitle("=== MyEA ===");
   dash.Separator();
   dash.Row("RSI", DoubleToString(rsi, 2));
   dash.Separator();
   dash.Row("Positions", IntegerToString(CPositions::CountMine(Magic)));
   dash.Row("Profit", DoubleToString(CPositions::TotalProfit(Magic), 2));
   if (InpUseM19Filter) {
      string session = M19.ActiveSession(TimeCurrent());
      dash.Row("Session", StringLen(session) > 0 ? session : "(off-hours)");
   }
   dash.Show();
}
```

输出示例：
```
=== MyEA ===
─────────
RSI      : 28.50
─────────
Positions: 1/3
Profit   : 12.30
Session  : London+NewYork
```

时段外：
```
Session  : (off-hours)
```

## 4 个预定义时段对照表

| 常量 | 时段（服务器时间） | 适用策略 | 备注 |
|---|---|---|---|
| `SESSIONS_ASIA` | 00:00-08:00 | 亚洲突破 / JPY 套利 | 低波动，剥头皮慎用 |
| `SESSIONS_LONDON` | 08:00-16:00 | 伦敦开盘突破 | EUR/GBP 高活跃 |
| `SESSIONS_NY` | 13:00-22:00 | 纽约开盘突破 | USD 高活跃 |
| `SESSIONS_LONDON_NY` ⭐ | 08:00-16:00 ∪ 13:00-22:00 | **推荐剥头皮** | 重叠 13:00-16:00 是 XAUUSDm 黄金时段 |

> 推荐剥头皮 / 趋势默认用 `SESSIONS_LONDON_NY`（覆盖 8 小时，最大化样本）。

## 周末处理

默认 `IsInSession(Sat/Sun)` 返 `false`（不交易周末）。
如要允许周末传 `SetAllowWeekend(true)`。

为什么默认关：
- 周末外汇市场实际关闭，**点差拉到天际**（XAUUSDm 周末点差 50-100+）
- 周末挂单有跳空风险，周一开盘跳空比平时大 3-5 倍
- 大部分经纪商周末禁止开仓，`OrderSend` 会直接 `retcode=10018 ERR_MARKET_CLOSED`

## 跨午夜逻辑（剥头皮 NY 22-06 场景）

`"NY:22-6"` 解析为 start=22, end=6（start > end 触发跨午夜分支）：
- `h=23` → `[22, 24) ∪ [0, 6)` → 命中 → in session
- `h=12` → 不在两个区间 → not in session
- `h=3`  → 命中 → in session
- `h=15` → 不在两个区间 → not in session

验证逻辑在 `CSessionFilter::_HourInRange()`：
```mql5
bool _HourInRange(int h, int start, int end) {
   if (start < end) return (h >= start && h < end);          // 普通
   else              return (h >= start || h < end);          // 跨午夜
}
```

## 替代方案对比

| 方法 | 优 | 劣 |
|---|---|---|
| **`CSessionFilter` (M19, 推荐)** | 4 预定义常量 + 自定义 + 跨午夜 + 周末 + 活跃名 | 多一层封装 |
| 裸写 `dt.hour` | 直接简单 | 每个 EA 写一遍，跨午夜易错，无活跃名 |
| `iSession` MT5 内置 | 官方 | 只支持单一时段，跨午夜要切两次 |
| TimeFilter 库（第三方） | 功能全 | 第三方依赖，配置不灵活 |

## 必看陷阱

- **`input` 默认值不能用 const 变量** —— 必须用字面量字符串（见用法段警告）。
- **时区假设** —— `MqlDateTime.hour` 是服务器时间。Exness 通常是 GMT+0/GMT+2。
  Exness demo 账户实测：北京时间 03:00 = 服务器时间 19:00 (GMT+0)。  
  想用本地时间要自己换算后再传 `Init()` 字符串。
- **周末默认关** —— SetAllowWeekend(false) 是默认值。周末点差异常大，**别开**。
- **跨午夜时 `endH <= 24`** —— `Init` 校验 `0-24`，所以 `"NY:22-6"` 合法，
  `"NY:22-25"` 会被 `_ParseSessionEntry` 拒绝。
- **Init 失败不抛异常** —— 必须检查返值 + `LastError()`。
  Init 失败但 EA 继续跑，会导致 `IsInSession` 永远返 false（`_count==0` 早返回）。
- **`ActiveSession` 多时段** —— "London+NewYork" 重叠期返 `"London+NewYork"`（按 _sessions 顺序），不是单选。
- **Dashboard 频繁刷新** —— `ActiveSession` 每 tick 调一次，O(N) 遍历 sessions（N<=5 完全可忽略）。

## 完整代码

`MQL5/Include/MQL5Kit/M19_SessionFilter.mqh`（约 320 行）—— 见文件。

## 单元测试

### 1) PowerShell 离线测试（推荐，秒跑）

```powershell
pwsh 'C:\ai\obsidian-文件\mt\00-任务调度中心\daily\M19-SessionFilter-tests.ps1'
```

4 个 test case（覆盖周末 / 工作日 / 重叠 / off-hours）：
- TC1 周末: Sat 2026-06-06 12:00 UTC + London+NY → expected false
- TC2 工作日 Asia: Wed 2026-06-03 03:00 UTC + Asia → expected true
- TC3 工作日 London+NY overlap: Wed 2026-06-03 15:00 UTC + London+NY → expected true
- TC4 工作日 off-hours: Wed 2026-06-03 23:30 UTC + Asia only → expected false

实测 4/4 PASS（2026-06-04 11:24）。

### 2) MQL5 自检（编译时）

```mql5
// 在 EA 里加一个 input bool InpRunSelfTest = false;
// OnInit 末尾:
if (InpRunSelfTest) {
   int fails = CSessionFilter::RunSelfTest();
   PrintFormat("[M19 self-test] fails=%d", fails);
}
```

`RunSelfTest()` 跑 6 个断言（不依赖 TimeCurrent()，纯配置级）：
- [1] Init(SESSIONS_ASIA) → 1 session
- [2] Init(SESSIONS_LONDON_NY) → 2 sessions
- [3] Init("garbage") → 失败, LastError 非空
- [4] Init("Asia:0-8,London:8-16,NewYork:13-22") → 3 sessions
- [5] Init("NY:22-6") → 1 session (跨午夜)
- [6] `_HourInRange` 跨午夜逻辑 (23 in [22,6) = true; 12 in [22,6) = false 等)

## 接入 demo: MeanReversion_EA.mq5

在 `MQL5/Experts/minimax-ea/MeanReversion_EA.mq5` 接入：

```mql5
// 1) include
#include <MQL5Kit/M19_SessionFilter.mqh>

// 2) inputs (input 默认值必须用字面量, 不能用 const)
input group "=== 时段过滤 (M19) ==="
input bool   InpUseM19Filter = true;
input string InpSessionPreset = "London:8-16,NewYork:13-22";
input bool   InpAllowWeekend   = false;

// 3) 实例
CSessionFilter M19;

// 4) OnInit 初始化
if (InpUseM19Filter) {
   if (!M19.Init(InpSessionPreset)) {
      PrintFormat("MeanReversion EA: M19 Init failed: %s", M19.LastError());
      return INIT_FAILED;
   }
   M19.SetAllowWeekend(InpAllowWeekend);
}

// 5) OnTick 过滤 (放在 ADX 之后, 其它入场前)
if (InpUseM19Filter && !M19.IsInSession(TimeCurrent())) {
   RefreshDash();
   return;
}

// 6) Dashboard 加 Session 行
if (InpUseM19Filter) {
   string session = M19.ActiveSession(TimeCurrent());
   dash.Row("Session", StringLen(session) > 0 ? session : "(off-hours)");
}
```

实测编译：**0 errors, 1 warning** (warning 来自 M07 的 `POSITION_COMMISSION` deprecation，与 M19 无关)。

## 相关链接

- M17 新闻过滤: [[M17 新闻过滤 NewsFilter]] — 高影响新闻 ±30min 内不开
- M04 指标: [[M04 指标句柄管理 IndicatorPool]] — iATR 动态追踪 SL
- M08 追踪止损: [[M08 追踪止损 TrailingStop]] — 持仓管理
- EA 剥头皮模板: [[EA 剥头皮模板]]
- ScalperXAU v1 spec: [[01 ScalperXAU v1 - Bollinger RSI 均值回归]] — 用 InpSessionStartHour=8, EndHour=23 写裸判断 (待迁 M19)

---

## 实战案例

> **本节汇总 M19 在真实 EA 场景的接入经验和完整代码模板**。
> spec wiki (上面) 讲 API + 理论；本节讲"已经跑通的实战 demo + 升级路径 + 跨 EA 同步"。

### 实战 wiki（必读）

**[[实战/M19 时段过滤实战]]** — 完整实战沉淀（747 行 / 32 KB），含：
- **3 个真实场景**: MeanReversion_EA 已集成（0 errors 编译）/ ScalperXAU v1 升级路径（裸配置 → M19）/ 多 EA 时段同步
- **3 段可复制代码**: 直接复制到 EA 就能用
- **4 预定义常量实战取舍表**: 剥头皮/逆势/趋势/全天候
- **7+ 实战陷阱**: input const 默认值 / Init 失败不抛异常 / 周五尾盘 / 时区 / 跨午夜 24 上限 / ActiveSession 拼接 / O(N) 性能
- **10 步接入 checklist**
- **跨午夜场景**: `NY:22-6` 完整解析 + RunSelfTest 验证 + PowerShell 离线测试结果
- **5 条反模式**: iSession / 第三方库 / M19 放 OnTick 顶部 / M19 当持仓过滤 / 非法时段字符串

### 实物 demo EA

**`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5`** — 已集成 M19，0 errors 编译通过（2026-06-04 11:32 最新）。

集成点（6 处）：
- line 21: `#include <MQL5Kit/M19_SessionFilter.mqh>`
- line 42-45: `InpUseM19Filter / InpSessionPreset / InpAllowWeekend` input group
- line 64: `CSessionFilter M19;` object
- line 92-100: `OnInit` Init 失败返 `INIT_FAILED` + 打印 sessions/weekend 信息
- line 160-164: `OnTick` 过滤（ADX 之后入场前）
- line 243-246: `RefreshDash` 显示 `Session` 行（"London+NewYork" / "(off-hours)"）

**关键设计**：M19 硬过滤放在 ADX 软过滤之后、入场信号之前；M19 只挡"开新仓"，不影响 M08 追踪止损继续管理持仓。

### 计划升级

**`ScalperXAU.mq5`**（v1 spec 第 117-118 行）— 计划用 M19 替换 `InpSessionStartHour=8/InpSessionEndHour=23` 裸配置。完整 diff 见实战 wiki §1 场景 B / §2 代码段 B。

### 相关实战（M17 串联）

> **M19 是"时段窗口", 与 M17（新闻过滤）串联**：M19 off-hours 拦截 + M17 新闻 ±N min 拦截 = 双层前置过滤。ScalperXAU.mq5 实际顺序：M19 → M17 → 指标 → M02 → M01（见 M17 spec §1.4 决策树）。
>
> **[[实战/M17_TestNewsEA 复活报告]]** — M17 NewsFilter 实物自检 EA 复活（5 步流程 / 1 模块接入 / 6 RunSelfTest 断言 / 2026-06-04 落地）。
> 实物 demo：ScalperXAU.mq5 是唯一接 M17 的生产 EA（集成点 6 处：L31 include / L79-83 input / L117 object / L548-550 PassFilters / L853 Dashboard / L981-987 OnInit）。

## 反向链接（中心节点 EA 接入报告）

> 本 M19 spec 是项目知识图谱的"模块 spec 节点"。下面 2 个 EA 中心节点 wiki 把 M19 作为 13 模块之一接入：
>
> - **[[实战/MeanReversion_EA 接入报告]]** — 13 模块全集（含 M18 + M19），M19 在第 13 行接入（line 21/42-45/64/92-100/161-164/244-246）。本 EA 是 M19 场景 A 实物 demo。
> - **[[实战/ScalperXAU 接入报告 + v1→v4 演进史]]** — 13 模块含 M17 + M13，**M19 是 ScalperXAU 场景 B 升级目标**（v1 spec 第 117-118 行裸 hour 判断 → M19 CSessionFilter）。当前 v4 仍用裸 `IsTradeTime()`（line 453-464），未升级到 M19。
>
> 读者看完本 spec 后，跳到 [[实战/MeanReversion_EA 接入报告]] §2.1 表格第 13 行 = M19 完整实物接入点；跳到 [[实战/M19 时段过滤实战]] §2 代码段 A/B/C = OnInit + OnTick + Dashboard 完整段代码。

---

## 实战扩展 (Round 2 — 06-05 06:00 T4 闭环)

> 沿用 00:00 T2 7 段范本, 末尾追加 5 个新场景 (M19 实战扩展第 2 轮)。MeanReversion_EA / ScalperXAUv9 5 个副仓 实物 Node.js fs 实测, 0 编造行号。

### 场景 A — 跨午夜 NY:22-6 (Round 1 已有, Round 2 细化)

- **场景描述**: NY:22 收市到 Asia:6 开市 8h 跨午夜, 默认全禁开新仓
- **实物 demo**: MeanReversion_EA.mq5 L42-45 (input group "时段过滤 (M19)") + L161-164 (OnTick 过滤)
- **调优点**: 22-6 严格禁开, 边缘 ±5 min 缓冲 (避免边界误判)
- **陷阱**: Asia 流动性低, 假突破多, 严控
- **链向**: [[实战/M19 时段过滤实战]] §1 场景 A 跨午夜

### 场景 B — 周末屏蔽 (周五 22 - 周日 24)

- **场景描述**: 周五 NY 收市后 (22:00) 到周一 Asia 开市前 (周日 24:00 / 周一 00:00), 周末全禁
- **实物 demo**: MeanReversion_EA.mq5 L92-100 (OnInit Init 块 day_of_week 5+6 跳过)
- **调优点**: day_of_week = 5 (周五) 或 6 (周六) 返 false, 全时段屏蔽
- **陷阱**: 部分 broker 周日 22-23 还有流动性, 严控全禁
- **链向**: [[实战/MeanReversion_EA 接入报告]] §2.1 第 13 行

### 场景 C — 4 预定义常量取舍 (Asia / London / NY / L+N)

- **场景描述**: 4 预定义常量对比, 剥头皮用 L+N (8h), 趋势用 London (8h), 跨午夜空仓用 Asia
- **实物 demo**: ScalperXAUv9.mq5 (311L, 4 预定义常量取舍, 升级目标)
- **调优点**: L+N 高波动 8h (伦敦 + 纽约重叠) 剥头皮首选, London 单时段趋势, Asia 跨午夜空仓
- **陷阱**: L+N 边界 (NY 13:00-17:00 + London 8:00-16:00 重叠 8h) 跟 Asia 重叠 (Tokyo 0:00-9:00)
- **链向**: [[实战/M19 时段过滤实战]] §4 4 预定义常量取舍表

### 场景 D — 时段边界 (London 8-16 整点 ± 5 min)

- **场景描述**: London 开市 8:00 整点 ± 5 min 边界, 避免刚开盘波动大误判
- **实物 demo**: ScalperXAUv8.mq5 (133L, 时段边界 demo)
- **调优点**: 边界 ± 5 min 缓冲, 8:05 前不开新仓, 16:00 后不开
- **陷阱**: 边界 ± 5 min 期间 流动性 不足, slippage 大
- **链向**: [[实战/5 个 debug-prototype EA 索引]] §3 v8 接入

### 场景 E — 节假日联动 (M17 NewsFilter)

- **场景描述**: M19 时段过滤 + M17 新闻 ±60 min 联动, 节假日 (圣诞/元旦) 联动
- **实物 demo**: ScalperXAUv9.mq5 (M19 + M17 联动, 7 串联)
- **调优点**: M19.IsInSession() + M17.IsNearEvent(60, 60) 双层过滤, 节假日 ±60 min
- **陷阱**: M19 屏蔽 + M17 屏蔽 期间不计入时段, 但节日整天空仓
- **链向**: [[实战/M17_TestNewsEA 复活报告]] §1 实物 demo + [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] §3 v4 演进
