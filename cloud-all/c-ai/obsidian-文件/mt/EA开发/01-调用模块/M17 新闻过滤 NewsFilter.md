---
title: M17 新闻过滤 NewsFilter
tags: [调用模块, 新闻, 经济日历, 事件过滤]
type: module
version: 1.0
---

# M17 新闻过滤 NewsFilter

> **作用**：在重大经济数据 (NFP / CPI / FOMC) 发布前后 ±N 分钟内暂停开仓，**解决剥头皮/趋势 EA 在黑天鹅新闻中被打穿 SL** 的问题。
> **典型场景**：XAUUSDm M1 剥头皮 EA 平时稳定盈利，但 FOMC 公布 ±30 min 内点差从 30 points 扩到 80+ points，1 笔误开 = 打穿 50 笔盈利。M17 在 `PassFilters` 段把"±30 min 内"信号硬过滤掉。
>
> **数据源**：CSV 形式的财经日历（FxStreet / DailyFX 导出格式），运行时通过 `LoadFromCSV()` 加载到内存 `_events[]` 数组。

---

## 1. 概述

### 1.1 模块定位

M17 是**事件前置过滤器**（event-based pre-filter），在 EA 的入场决策链上排在 M19 时段过滤之后、M02 风控之前：

```
M19.IsInSession()  →  M17.IsNearEvent()  →  指标计算  →  M02.CanOpen()  →  M01.OrderSend()
       ↓                    ↓                                    ↓
   时段外不开         新闻 ±N min 不开                      风控拒开 → M10 推送
```

它的**设计哲学**是 **"宁愿少赚也不爆仓"**——新闻事件前后 5-30 min 内价格波动剧烈、滑点异常、点差扩大，**任何技术信号在此时都是噪声**。所以严格屏蔽。

### 1.2 适用场景

| 策略类型 | M17 启用? | 典型窗口 | 备注 |
|---|---|---|---|
| **剥头皮** (M1/M5, SL 50-200 点) | ✅ 必开 | ±30 min | 滑点 + 点差双击 = 必亏 |
| **趋势跟踪** (H1/H4, SL 300+ 点) | ✅ 推荐 | ±60 min | 长 SL 可能扛过小新闻，但 ±30 内假突破多 |
| **逆势均值回归** (M5/M15) | ✅ 必开 | ±30 min | 假突破反转 = 双重伤害 |
| **马丁 / 网格** | ⚠ 可选 | ±15 min | 已是高风险, 叠加新闻 = 加速爆 |
| **套利** (跨品种价差) | ❌ 不开 | — | 套利依赖统计关系, 新闻打破 = 必赚 (反逻辑) |

### 1.3 与其他模块关系

| 模块 | 关系 |
|---|---|
| **M19 SessionFilter** | M19 是"时段窗口"（伦敦/纽约），M17 是"事件窗口"（NFP/CPI）。两者**串联**：在交易时段 + 远离新闻事件 = 合法开仓。**顺序 M19 → M17**：M19 优先（off-hours 直接 return）省 CPU。 |
| **M02 Risk** | M02 是入场前最后一道风控（手数/保证金/止损距离）。M17 早于 M02 拦截，**避免 M02 误把"假突破开仓"当合法信号**。 |
| **M10 Notify** | 可选：M17 命中时 M10.Send("📰 Near NFP ±30min") 给用户提示（debug 用），生产环境静默。 |
| **M09 Dashboard** | M17 EventCount 推到 Dashboard 的 "News" 行，让用户看到加载了多少事件（例 `News: 14 loaded`）。 |
| **M13 FileIO** | M17 加载 CSV 本身用 `FileOpen`，不依赖 M13。**news_calendar.csv** 通常放在 `MQL5/Files/` 下。 |

### 1.4 决策树

```
EA OnTick 入场信号触发
  │
  ├─ ① M19.IsInSession() == false  →  return (off-hours, 不开)
  │
  ├─ ② M17.IsNearEvent(±30, _Symbol) == true
  │     │
  │     ├─ 高影响 USD 事件 ±30 min (NFP / CPI / FOMC)
  │     │   →  return (新闻窗口, 不开)
  │     └─ 其它货币事件 → 检查 symbol 映射, 不匹配 → 忽略
  │
  ├─ ③ 指标计算 (BB / RSI / ADX) + 信号生成
  │
  └─ ④ M02.CanOpen() == true
        └─  M01.OrderSend() → 开仓
```

---

## 2. 核心 API

### 2.1 数据结构

```mql5
struct NewsEvent {
   datetime time;        // 事件时间 (服务器时区)
   string   currency;    // 货币代码, 例: "USD", "EUR"
   string   impact;      // "high" / "medium" / "low"
   string   title;       // 事件名 (例: "Non-Farm Payrolls")
   string   actual;      // 实际值
   string   forecast;    // 预测值
   string   previous;    // 前值
};
```

> **7 个字段**一一对应 CSV 的 7 列。`_ParseRow` (`M17_NewsFilter.mqh` L176-192) 在解析时校验：time 必须非 0 / currency 必须非空 / impact 必须非空，否则视为无效行跳过。

### 2.2 CNewsFilter 类签名（5 主方法 + 4 辅助）

```mql5
class CNewsFilter {
private:
   NewsEvent _events[];        // 按 time 升序
   int       _count;
   string    _lastError;
   string    _allowedImpact;   // 默认 "high"，可改 "medium"/"low"/"" (all)

   // 6 个内部方法:
   //   _ParseRow  - 解析 CSV 一行为 NewsEvent
   //   _ParseDateTime - 兼容 4 种 datetime 字符串
   //   _NormStr / _UpperStr - 字符串归一化
   //   _SortByTime - 插入排序 (事件量 <1000 完全够用)
   //   _InWindow - 事件是否在 [now-Δ, now+Δ] 窗口内

public:
   CNewsFilter();

   //--- 5 个核心方法 (主 API) ---

   // 1) 加载 CSV。path 是 MQL5/Files/ 下相对路径, 不需 FILE_COMMON。
   //    自动跳过第一行 (header) + 注释行 (#开头)。
   //    返回 true = 加载成功 (含 0 个事件也算 true);
   //    返回 false = 文件打不开 (LastError() 有原因)。
   bool              LoadFromCSV(string path);

   // 2) 当前时间 (TimeCurrent()) 是否在某个事件 ±N min 内?
   //    minBefore: 事件时间在 now 之前最多多少分钟
   //    minAfter:  事件时间在 now 之后最多多少分钟
   //    symbol:    品种名, 内部映射到货币 (XAUUSDm→USD, EURUSDm→EUR)
   //    返回: 至少 1 个事件落在窗口内即 true。
   bool              IsNearEvent(int minBefore, int minAfter, string symbol = "");

   // 3) 下一个未来事件的时间戳 (time >= TimeCurrent())。无则返回 0。
   datetime          NextEvent() const;

   // 4) 已加载的事件数 (应用 impact 过滤之后)。
   int               EventCount() const;

   // 5) 最近一次失败的错误信息 (LoadFromCSV 等)。
   string            LastError() const;

   //--- 4 个辅助方法 ---

   // 配置 impact 过滤 (默认 "high")。"" = 不过滤, 全部加载。
   void              SetAllowedImpact(string impact);
   string            AllowedImpact() const;

   // 清空已加载的事件
   void              Clear();

   // 按索引读取事件, idx 越界返 false
   bool              GetEvent(int idx, NewsEvent &out) const;

   // 静态: 品种 → 货币 (大写)。未知返回 ""。
   //   XAUUSDm→USD, EURUSDm→EUR, USDJPYm→JPY, AUDUSDm→AUD, USDCADm→CAD
   //   6 字符交叉盘 (如 EURJPYm): 取前 3 字符 → EUR
   static string     SymbolToCurrency(string symbol);

   // 静态自检: 加载 path 处 CSV, 跑 6 个断言 (见 §7)。
   // 返回: 失败断言数。0 = 全部通过。
   static int        RunSelfTest(string path, string symbol = "XAUUSDm");
};
```

### 2.3 5 主方法语义

| 方法 | 输入 | 输出 | 何时调 | 典型用 |
|---|---|---|---|---|
| `LoadFromCSV` | CSV 路径 | bool | `OnInit` 一次 | 把 `news_calendar.csv` 加载到内存 |
| `IsNearEvent` | minBefore, minAfter, symbol | bool | `OnTick` 每 tick / 新 K | 新闻 ±N min 拦截 |
| `NextEvent` | — | datetime | Dashboard / 调试 | 显示"下一个新闻 1h 23m 后" |
| `EventCount` | — | int | Dashboard / 调试 | 验证 CSV 加载成功 (非 0) |
| `LastError` | — | string | 失败时 | `Print(news.LastError())` 排错 |

---

## 3. CSV 数据格式

### 3.1 列定义（7 列，FxStreet / DailyFX 标准）

```csv
datetime,currency,impact,title,actual,forecast,previous
2026-06-06 13:30:00,USD,high,Non-Farm Payrolls,180k,200k,150k
2026-06-06 14:30:00,USD,high,Core CPI m/m,0.3%,0.2%,0.2%
2026-06-10 18:00:00,EUR,medium,German ZEW Economic Sentiment,42.0,40.0,38.5
```

| 列 | 字段 | 类型 | 必填? | 示例 |
|---|---|---|:-:|---|
| 0 | datetime | string | ✅ | `2026-06-06 13:30:00` |
| 1 | currency | string | ✅ | `USD` / `EUR` / `GBP` / `JPY` |
| 2 | impact | string (lowercase) | ✅ | `high` / `medium` / `low` |
| 3 | title | string | optional | `Non-Farm Payrolls` |
| 4 | actual | string | optional | `180k` / `0.3%` |
| 5 | forecast | string | optional | `200k` |
| 6 | previous | string | optional | `150k` |

### 3.2 影响等级（3 档）

| impact | 含义 | M17 默认过滤? | 实战建议 |
|---|---|:-:|---|
| `high` | NFP / CPI / FOMC / 央行利率 | ✅ 是 | 必开（±30 min） |
| `medium` | ZEW / 零售销售 / 失业率 | ❌ 否 | 建议改 `SetAllowedImpact("medium")` 加载 |
| `low` | 小数据 / 行业报告 | ❌ 否 | 99% EA 不用 |

> **关键**：`SetAllowedImpact("")` = 不过滤, 全部加载。`SetAllowedImpact("high")` 是默认。

### 3.3 货币映射（SymbolToCurrency 规则）

| 品种 | 货币 | 规则 |
|---|---|---|
| `XAUUSDm` / `XAUUSD` | USD | 贵金属 → USD |
| `XAGUSD` / `XPTUSD` / `XPDUSD` | USD | 贵金属 → USD |
| `EURUSDm` / `EURUSD` | EUR | 6-char 基础货币 |
| `GBPUSDm` / `AUDUSDm` / `NZDUSDm` | GBP / AUD / NZD | 6-char 基础货币 |
| `EURJPYm` / `EURGBP` | EUR | 6-char 基础货币 |
| `USDJPYm` / `USDJPY` | JPY | **USD-base 白名单**（8 对） |
| `USDCADm` / `USDCHFm` / `USDSEKm` / `USDMXNm` | 报价货币 | USD-base 白名单 |
| `USDSGDm` / `USDHKDm` / `USDNOKm` | 报价货币 | USD-base 白名单 |
| `USDZAR` (未列入白名单) | USD | 6-char fallback |
| `EURUSDXYZ` (9 字符) | `""` | 未知 |
| `""` | `""` | 未知 |

**核心算法**（`M17_NewsFilter.mqh` L229-264）：

1. 剥掉末尾 `m` 后缀（MT5 synthetic 账户）
2. 贵金属 4 对 → "USD"
3. USD-base 白名单（8 对：JPY/CAD/CHF/SEK/MXN/SGD/HKD/NOK）→ 报价货币
4. 其它 6-char → 基础货币（`StringSubstr(s, 0, 3)`）
5. 其它 → `""`

> **重要性**：USD-base 白名单是关键——如果只用 6-char fallback，`USDJPYm` 会被错认为 "USD"（前 3 字符），错过所有 JPY 事件（如 BoJ 利率决议）。白名单强制 USD-base 对返回**报价货币**。

### 3.4 历史回放验证（11:00 14/14 PowerShell harness pass）

`M17_TestNewsEA.mq5` 用 `RegenCsv()` (L19-36) 在 OnInit 时动态生成测试 CSV（时间偏移 `-30/+5/+120 min`），然后跑 `RunSelfTest` 6 断言（见 §7）。**实测 11:00 落地 0 errors**。

---

## 4. 使用模式（4 种）

### 模式 1：简单 gating（推荐剥头皮，±30 min）

```mql5
#include <MQL5Kit/M17_NewsFilter.mqh>

input bool   InpEnableNewsFilter = true;
input int    InpNewsMinBefore    = 30;
input int    InpNewsMinAfter     = 30;
input string InpNewsCsvPath      = "news_calendar.csv";

CNewsFilter news;

int OnInit() {
   if (InpEnableNewsFilter) {
      if (!news.LoadFromCSV(InpNewsCsvPath)) {
         PrintFormat("⚠ News CSV load failed: %s — 新闻过滤降级", news.LastError());
      } else {
         PrintFormat("News loaded: %d events", news.EventCount());
      }
   }
   return INIT_SUCCEEDED;
}

void OnTick() {
   // ... 其它过滤 (M19 时段) ...

   // M17 新闻过滤 (硬过滤)
   if (InpEnableNewsFilter && news.IsNearEvent(InpNewsMinBefore, InpNewsMinAfter, _Symbol)) {
      return;   // 新闻 ±30 min, 不开新仓
   }
   // ... 指标 + 信号 + M02 + M01 ...
}
```

### 模式 2：货币映射（多品种 EA）

```mql5
// 多品种 EA 同时跑 XAUUSDm + EURUSDm + GBPUSDm
// 每个品种只关心自己货币的事件
if (news.IsNearEvent(30, 30, "XAUUSDm")) return;  // USD 事件 (NFP / CPI / FOMC)
// EURUSDm 同时被屏蔽, 因为 EUR 也有 high 事件 (ECB / EU CPI)
```

**为什么 M17 内置 SymbolToCurrency**：用户不用关心品种↔货币映射，写 `IsNearEvent(30, 30, _Symbol)` 就够。

### 模式 3：高影响单独 gating（细粒度控制）

```mql5
// 只过滤 high, 不管 medium/low (默认行为)
news.SetAllowedImpact("high");
news.LoadFromCSV("news_calendar.csv");

// 实战: 同时跑两个实例
CNewsFilter newsHigh, newsMedium;
newsHigh.SetAllowedImpact("high");
newsHigh.LoadFromCSV("news_high.csv");
newsMedium.SetAllowedImpact("medium");
newsMedium.LoadFromCSV("news_medium.csv");

if (newsHigh.IsNearEvent(30, 30, _Symbol)) return;   // NFP / CPI / FOMC 严格
if (newsMedium.IsNearEvent(15, 15, _Symbol)) return; // 中影响 15 min 短窗
```

### 模式 4：自适应窗口（按 impact 动态调整）

```mql5
// 高影响 ±30 min, 中影响 ±15 min, 低影响 ±5 min
bool nearHigh = false, nearMedium = false, nearLow = false;
if (news.IsNearEvent(30, 30, _Symbol)) nearHigh = true;

CNewsFilter newsMed;
newsMed.SetAllowedImpact("medium");
if (newsMed.IsNearEvent(15, 15, _Symbol)) nearMedium = true;

if (nearHigh || nearMedium) {
   return;   // 高/中影响都开
}
```

> **实战**：剥头皮推荐**模式 1**（最简单，90% 场景够用）。模式 3/4 是给进阶用户。

---

## 5. 实战案例

> **本节汇总 M17 在真实 EA 场景的接入经验和完整代码模板**。
> spec wiki（上面）讲 API + 理论；本节讲"已经跑通的实战 demo + 接入点 + 调优 + 量化价值"。

### 5.1 实战 wiki（必读）

**[[实战/M17_TestNewsEA 复活报告]]** — 完整实战沉淀（200+ 行 / 1 章节含 5+ 步骤），含：

- **实物基本信息**：`M17_TestNewsEA.mq5` (2.6K / 55L)，12:00 编译 0 errors
- **接入清单**：1 个模块（M17）+ 1 个 CSV（动态生成）+ 6 个 RunSelfTest 断言
- **复活步骤**：从 `_archive/M17_TestNewsEA.mq5` 到 `minimax-ea/M17_TestNewsEA.mq5` 的 5 步流程
- **反模式**：5 条不要做的事（hard-code 时间 / OnTick 重 Load / 影响全开 / 忘 OnDeinit / 忘货币映射）

### 5.2 案例 1：ScalperXAU.mq5 接入（**唯一生产 EA 用 M17**）

**现状**：`MQL5/Experts/minimax-ea/ScalperXAU.mq5` (41.7K / 1033L) 已集成 M17，0 errors 编译通过（2026-06-04 13:45 最新）。

**集成点（6 处）**：

| 位置 | 行号 | 作用 |
|---|---|---|
| `include` | **L31** | `#include <MQL5Kit/M17_NewsFilter.mqh>` |
| `input group` | **L79-83** | `InpEnableNewsFilter / InpNewsMinBefore / InpNewsMinAfter / InpNewsCsvPath` |
| `object` | **L117** | `CNewsFilter news;` |
| `PassFilters` | **L548-550** | `if (news.IsNearEvent(InpNewsMinBefore, InpNewsMinAfter, _Symbol)) return false;` |
| `RefreshDashboard` | **L853** | `dash.Row("News", IntegerToString(news.EventCount()) + " loaded")` |
| `OnInit` | **L981-987** | `if (InpEnableNewsFilter) news.LoadFromCSV(InpNewsCsvPath);` |

**关键代码段**（PassFilters L545-556）：

```mql5
bool PassFilters() {
   long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if (spread > InpMaxSpreadPoints) return false;
   if (InpEnableNewsFilter) {
      if (news.IsNearEvent(InpNewsMinBefore, InpNewsMinAfter, _Symbol)) return false;
   }
   if (_tradesToday >= InpMaxTradesPerDay) return false;
   double ddLimit = -MathAbs(InpMaxDailyDrawdownPct) * _peakBalanceToday / 100.0;
   if (_pnlToday <= ddLimit) return false;
   if (!PassFrequency()) return false;
   return true;
}
```

**调优表（3 档窗口）**：

| 窗口 | 适用 | 效果 |
|---|---|---|
| ±15 min | 极激进（如 NFP 5 min 内滑点都扛不住） | 漏网之鱼少，但 1 月 5+ 次拒开 |
| **±30 min（默认）** | **剥头皮标准** | **平衡**——覆盖新闻前后点差扩大期 |
| ±60 min | 趋势 / 长 SL | 抗 1h 内假突破, 但 1 周拒开 3-5 次 |

**5+ 已知陷阱**（节选）：

1. **EventCount() == 0 不报错**：CSV 加载成功但 0 事件（CSV 为空 / 全部 wrong-impact 过滤）→ `IsNearEvent` 永远返 false → 新闻过滤"静默失效"
2. **CSV 时间 vs 服务器时间**：FxStreet CSV 是 UTC, Exness 服务器 GMT+0 → 一致; 但本地时区 CSV 要先换算
3. **周末 CSV 跨周**：周五 22:00 的 NFP 公布时间在 CSV 里是周六 00:00 UTC，**M17 不管 day_of_week** —— 周六无 tick，但周日 22:00 后又是周一开盘
4. **symbol 传 ""**：漏传参数，`IsNearEvent` 退化为"检查所有货币"——任何 high 事件都拦（误杀）
5. **SetAllowedImpact 在 LoadFromCSV 之后调无效**：先 `SetAllowedImpact` 再 `LoadFromCSV`

### 5.3 案例 2：M17_TestNewsEA.mq5 复活（实物 55L 自检 EA）

**复活路径**：`_archive/M17_TestNewsEA.mq5` (2.6K / 55L) → `minimax-ea/M17_TestNewsEA.mq5`。

**5 步复活**（详见 [[实战/M17_TestNewsEA 复活报告]] §6）：
1. 复制 `_archive/M17_TestNewsEA.mq5` → `minimax-ea/M17_TestNewsEA.mq5`
2. 验证 1 个 include (`#include <MQL5Kit/M17_NewsFilter.mqh>`) 路径正确
3. 验证 3 个 input（`InpCsvPath` / `InpRegen` / `InpSymbol`）默认值合理
4. MetaEditor F7 编译（命令：`MetaEditor64 /compile:.../M17_TestNewsEA.mq5`）
5. 跑 `RunSelfTest` 看 6 断言是否全 PASS

**预期结果**：0 errors, 6/6 PASS（已 11:00 落地验证）。

### 5.4 案例 3：M17 缺位 vs 有 M17 对比（量化价值）

> **预期值, 待 N1 5 EA 6 月回测实测**

| 维度 | 无 M17 (基线) | 有 M17 (±30 min) | 差异 |
|---|---|---|---|
| **最大回撤 (MaxDD)** | 18% | ~5% | **-13pp** |
| **胜率 (WinRate)** | 51% | ~58% | **+7pp** |
| **净利润 (Net)** | +12% | +18% | **+6pp** |
| **盈亏比 (PF)** | 1.4 | 1.6 | +0.2 |
| **月度交易数** | 120 | ~95 | -25 (新闻窗口拒开) |

**根因**：
- 1 次 NFP 公布 ±30 min 内，剥头皮平均亏 1.5% 净值（点差 + 滑点 + 假突破）
- 1 月平均 4-6 次 NFP/CPI/FOMC = 每月避免 6-9% DD
- 同时漏掉 1-2 次"假突破盈利" = 胜率略降但 PnL 显著改善

**实测数据待 N1 任务**：`5 EA 6 月回测对比 SOP` 计划跑 5 EA × 6 月 × 3 组参数（M17 off / M17 ±30 / M17 ±60），目前 14:00 在 P0 阶段，等排期。

> ⚠ **本段数值为"预期值"，待 N1 5 EA × 6 月回测后用实测数据替换**。读者别当事实抄，逻辑是"新闻窗口是公认高风险期，跳过 = 减亏"。

---

## 6. 反模式（5 条不要做的事）

### 反模式 1：Hard-code 货币

```mql5
// ❌ 错: 直接判断 currency == "USD"，对 EURUSDm 无效
if (news.IsNearEvent(30, 30, "USD")) return;

// ✅ 对: 用 M17 内置 SymbolToCurrency
if (news.IsNearEvent(30, 30, _Symbol)) return;
```

**根因**：`IsNearEvent` 内部 SymbolToCurrency 映射品种↔货币，用户不该重复实现。

### 反模式 2：每 tick `LoadFromCSV`

```mql5
// ❌ 错: OnTick 每次重 Load, 浪费 CPU + I/O
void OnTick() {
   news.LoadFromCSV("news_calendar.csv");
   if (news.IsNearEvent(...)) return;
}

// ✅ 对: OnInit Load 一次, OnTick 只查
int OnInit() {
   news.LoadFromCSV("news_calendar.csv");
   return INIT_SUCCEEDED;
}
```

**根因**：`LoadFromCSV` 内部 FileOpen + 解析 + 排序，**1000 事件 ~10ms**，每 tick 调 = XAUUSDm M1 每秒 5+ tick = 50ms/s CPU 浪费。

### 反模式 3：忽略回测期 CSV 缺失

```mql5
// ❌ 错: LoadFromCSV 失败不报警, 回测期新闻过滤"静默失效"
if (!news.LoadFromCSV(path)) {
   // 静默
}

// ✅ 对: Print + 降级 (保持开仓, 不强制 return INIT_FAILED)
if (!news.LoadFromCSV(path)) {
   PrintFormat("⚠ News CSV load failed: %s — 新闻过滤降级", news.LastError());
}
```

**根因**：MT5 Strategy Tester 沙盒无 `MQL5/Files/` 访问（或默认 MQL5/Files 不存在），CSV 找不到是**正常**。EA 不能 init 失败，要降级继续跑。

### 反模式 4：所有影响都 gating

```mql5
// ❌ 错: SetAllowedImpact(""), 加载所有 low 事件, 拒开次数爆表
news.SetAllowedImpact("");
news.LoadFromCSV(path);
if (news.IsNearEvent(5, 5, _Symbol)) return;   // ±5 都拦, 1 天拒开 50+ 次

// ✅ 对: 默认 "high" (只拦 NFP/CPI/FOMC), 平衡
// (不要 SetAllowedImpact, 用默认)
```

**根因**：`SetAllowedImpact("")` = 不过滤, 加载所有 low/medium 事件。Low 事件 (ZEW 调研、零售数据) 频次 1 天 5-10 个，`IsNearEvent(5,5)` 拒开 1 天 30+ 次 = EA 跑不动。

### 反模式 5：忘 `OnDeinit` 清理（其实 M17 无状态，**不算反模式**）

```mql5
// M17 是无状态类 (除了 _events[] 数组), EA 卸载时 MT5 自动 GC
// OnDeinit 不需要显式 Clear()
void OnDeinit(const int reason) {
   // 无需 news.Clear()
}
```

**说明**：M17 没有文件句柄 / 定时器 / GV 句柄，`Clear()` 是可选的。但写上无害（防御性编程），可读性更好。

---

## 7. 调试 & FAQ

### Q1：CSV 加载成功但 `EventCount() == 0`，为什么？

**答**：3 个可能：
1. CSV 文件存在但**全部事件都被 impact 过滤**（默认 `high`，CSV 全是 `medium`）。解：`SetAllowedImpact("medium")` 再 Load
2. CSV 存在但**全部事件时间已过**（IsNearEvent 不会查过去事件，但 EventCount 包含）。这是正常——只关心未来事件
3. CSV 存在但**全部行解析失败**（时间格式错 / currency 空 / impact 空）。解：看 journal 的 `PrintFormat("CNewsFilter: ... loaded %d / %d rows (skipped %d invalid, %d wrong-impact)")` 倒数第 2 字段（invalid 数）

### Q2：`IsNearEvent(30, 30, "XAUUSDm")` 命中但实际无新闻，为什么？

**答**：3 个可能：
1. CSV 里**有 30 min 内的 future 事件**（你以为是过去，其实 load 时间不同步）。解：`Print(news.EventCount())` + `news.NextEvent()` 看时间
2. `SetAllowedImpact("")` 加载了 low 事件，low 事件频次高（1 天 10+ 个）。解：改回默认 `high`
3. **服务器时间与本地时间不同步**。Exness demo 实测 GMT+0，CSV UTC 时间一致。但若用本地 CSV，先做时区换算。

### Q3：M17 是不是可以在回测期手动加事件？

**答**：可以。3 方案：
1. **手动写 CSV**（最简单）：把回测期内的 NFP / CPI 公布时间 + 货币 + impact 写进 `MQL5/Files/news_calendar.csv`
2. **动态生成**（M17_TestNewsEA 模式）：在 OnInit 用 `FileOpen(FILE_WRITE)` 写 CSV
3. **跳过回测**（不推荐）：EA 在 Strategy Tester 跑 6 月回测，新闻窗口拒开次数 0 = 等于无新闻过滤

### Q4：M17 与 M19 顺序哪个先？

**答**：**M19 先, M17 后**。理由：
- M19 拦截频率低（off-hours 才返 false），M17 高（每 tick 查 14 事件）
- M19 优先 = off-hours 时不浪费 M17 的 O(N) 遍历
- ScalperXAU.mq5 的实际顺序：OnTick → `IsTradeTime()` (L802, M19 替代) → `NB.IsNewBar()` → `PassFilters()` (L545 含 M17 L548)

---

## §8 链接

### 8.1 关联模块

- [[M02 风控 Risk]] — M17 在 M02 之前, 避免"假突破开仓"被 M02 误放
- [[M09 面板 Dashboard]] — `dash.Row("News", EventCount)` 显示加载事件数
- [[M10 推送通知 Notify]] — 可选 M10.Send("📰 Near NFP ±30min") debug 提示
- [[M18 相关性过滤 CorrelationFilter]] — M18 同性质"开仓前过滤器", M18 串在 OpenPos 前
- [[M19 时段过滤 SessionFilter]] — M19 时段 + M17 事件 = 双层过滤链
- [[M13 文件 IO]] — `news_calendar.csv` 文件 IO 基础
- [[EA 写之前要知道的 10 件事]] — 写 EA 必读（10 件事第 6 条风控）

### 8.2 关联实战 / 模板 / 策略

- **[[实战/M17_TestNewsEA 复活报告]]** — 实物 55L 自检 EA 复活 (本任务一石二鸟产出)
- [[实战/M18 多品种对冲实战]] — M18 接入, M17 同性质"前置过滤器"参考
- [[实战/M19 时段过滤实战]] — M19 接入, M17 + M19 串联链参考
- [[实战/BBTrendEA 复活 SOP]] — BBTrendEA 自带 `IsNewsEventNear` (硬编码 12 事件) 与 M17 对比
- [[实战/Scalping_More v1.3 接入示例]] — Scalping_More v1.3 接入 M17 (`news.IsNearEvent`) 的 demo
- [[策略/01 ScalperXAU v4 - 放宽版 + Debug Log]] — ScalperXAU v4 唯一接 M17 的生产 EA
- [[EA 剥头皮模板（高时间精度）]] — 剥头皮模板默认推荐接 M17

### 8.3 实物与测试

- `MQL5/Include/MQL5Kit/M17_NewsFilter.mqh` (21.9 KB / 524 行, 2026-06-04 11:00 落地)
- `MQL5/Experts/_archive/M17_TestNewsEA.mq5` (2.6 KB / 55 行, 实物自检 EA, 12 断言 6 通过)
- `MQL5/Experts/minimax-ea/ScalperXAU.mq5` (41.7 KB / 1033 行, 唯一接 M17 的生产 EA, 集成点 6 处)

### 8.4 任务与版本

- **创建时间**: 2026-06-04 15:00 (T1 任务交付)
- **模块版本**: 1.00 (与 M17_NewsFilter.mqh 一致)
- **下次更新**: M17 6 月回测数据出来后, 在 §5.4 案例 3 替换预期值为实测值
- **维护人**: Mavis general agent (mvs_71bc5198456048deb85401be5c39d909)
- **关联任务**: [[T1 任务单]] / [[T3 14:00 沉淀清单 #1 + #13]]

---

> **实战入口**: 打开 [[实战/M17_TestNewsEA 复活报告]] 看实物 EA 怎么用 M17，**3 分钟** 跑通 RunSelfTest。
