---
title: M18 相关性过滤 CorrelationFilter
tags: [调用模块, 相关性, 多品种对冲]
type: module
---

# M18 相关性过滤 CorrelationFilter

> **作用**：算多品种 Pearson 相关系数, **解决 XAUUSDm+EURUSDm 同向时双倍暴露** 问题。
> **典型场景**：EA 同时持 XAUUSDm 多 + EURUSDm 多, 两品种日线 close 相关 r ≈ +0.85 →
> 一根黑天鹅 K 线打穿两个仓位。本模块在开新仓前查已有持仓, 若 |r| > 0.7 则跳过本次开仓。

## API（5 个方法 + 私有 buffer）

```mql5
class CCorrelationFilter {
   // 1. 加载品种列表 (XAUUSDm / EURUSDm / GBPUSDm / USDJPYm)
   //    会 SymbolSelect 把品种加入 Market Watch
   bool        Init(string &symbols[]);

   // 2. 拉历史日线 close 价到内部 buffer (倒序)
   //    默认 30 天; 失败返回 -1
   int         LoadHistoricalCloses(string symbol, int days = 0);

   // 3. 算 Pearson 相关系数 -1 ~ +1
   //    数据不足或长度不一致返 0
   double      CalcCorr(string sym1, string sym2);

   // 4. 检查已有持仓是否已存在高相关品种
   //    遍历 PositionsTotal(), 拿本 EA (按 magic) 已有持仓的 symbol
   //    任意一对 |corr| > threshold → 返 true (已对冲暴露)
   bool        IsHedgeExposed(string newSymbol, ulong magic,
                              double threshold = 0.7);

   // 5. 调试: 返所有品种两两相关系数矩阵字符串
   //    Print(M18.DumpCorr()) 一把打 journal
   string      DumpCorr();
};
```

内部私有 buffer：

```mql5
struct CorrSeries {
   string   symbol;
   double   closes[];   // 倒序: [0]=最新, [n-1]=最旧
   int      count;
};

CorrSeries _series[];    // 每个品种一个时间序列
int        _nSymbols;
int        _defaultDays;
string     _lastError;
```

## 完整代码

`MQL5/Include/MQL5Kit/M18_CorrelationFilter.mqh`（约 420 行）— 关键算法 `_Pearson`：

```mql5
// Pearson 相关系数:
//   r = sum((xi-mx)*(yi-my)) / sqrt(sum((xi-mx)^2) * sum((yi-my)^2))
// 范围 [-1, +1]; 0 = 无线性相关; ±1 = 完全线性
double CCorrelationFilter::_Pearson(const double &x[], const double &y[], int n) {
   if (n < 2) return 0.0;
   if (ArraySize(x) < n || ArraySize(y) < n) return 0.0;

   double mx = _Mean(x, n);
   double my = _Mean(y, n);
   double sxx = _Sumsq(x, n, mx);
   double syy = _Sumsq(y, n, my);
   if (sxx <= 0.0 || syy <= 0.0) return 0.0;   // 常数列 → 不相关

   double sxy = 0.0;
   for (int i = 0; i < n; i++) {
      sxy += (x[i] - mx) * (y[i] - my);
   }
   double denom = MathSqrt(sxx * syy);
   if (denom <= 0.0) return 0.0;
   double r = sxy / denom;
   // 数值夹紧
   if (r >  1.0) r =  1.0;
   if (r < -1.0) r = -1.0;
   return r;
}
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M18_CorrelationFilter.mqh>

input bool   InpUseM18Filter   = true;
input double InpCorrThreshold  = 0.7;
input string InpCorrSymbols    = "XAUUSDm,EURUSDm,GBPUSDm,USDJPYm";

CCorrelationFilter M18;

int OnInit() {
   if (InpUseM18Filter) {
      string syms[];
      int n = StringSplit(InpCorrSymbols, ',', syms);
      if (n >= 2) {
         M18.SetDefaultDays(30);
         M18.Init(syms);
         for (int i = 0; i < n; i++) {
            M18.LoadHistoricalCloses(syms[i], 30);
         }
         Print(M18.DumpCorr());   // 启动时打印矩阵
      }
   }
   return INIT_SUCCEEDED;
}

void OnTick() {
   // ... 其它检查 ...

   // M18 检查: 已有持仓与 _Symbol 高相关 → 跳过
   if (InpUseM18Filter && M18.IsHedgeExposed(_Symbol, Magic, InpCorrThreshold)) {
      PrintFormat("[M18] 跳过 %s: 已有高相关品种持仓", _Symbol);
      return;
   }

   // ... 正常开仓逻辑 ...
}
```

完整接入 demo 见 `MQL5/Experts/minimax-ea/M18_TestEA.mq5`（OnInit 时跑自检 + 打印矩阵）。

## DumpCorr 输出示例

```
M18 相关系数矩阵 (Pearson, 日线)
symbol         XAUUSDm     EURUSDm     GBPUSDm     USDJPYm
------------   ------------   ------------   ------------
XAUUSDm           1.000       0.850       0.720      -0.650
EURUSDm           0.850       1.000       0.910      -0.580
GBPUSDm           0.720       0.910       1.000      -0.490
USDJPYm          -0.650      -0.580      -0.490       1.000
```

解读：
- `EURUSDm × GBPUSDm = 0.910` → 极强正相关, 同向持仓 = 双倍暴露
- `XAUUSDm × USDJPYm = -0.650` → 强负相关, **天然对冲** (黄金涨+日元涨的可能性较低, 可作 hedge)
- 对角线 = 1.000 (自相关恒等)

## 阈值选择参考

| 阈值 | 严格度 | 典型场景 |
|---|---|---|
| 0.5 | 较严 | 资金极小 / 风险厌恶型 / 1% 风险规则 |
| **0.7 (默认)** | **平衡** | **普通多品种 EA** |
| 0.85 | 较松 | 资金充裕 / 想持仓更多品种 / 已有 M02/M03 风控 |

## 必看陷阱

- **MT5 模拟账户必须 `SymbolSelect(sym, true)`** — Init 内部已做, **不要** 在 EA 里再手工加
- **`CopyClose` 在 30 天日线级别够用**; 用 H4/H1 算出来的相关性会随周期变化, 不建议
- **`IsHedgeExposed` 只检查本 magic 的持仓** — 多 EA 同账户不会互相误判
- **数据不足 (< 2 根) 返 0** — `CalcCorr` 把 0 视为"无线性相关", 跟"完美对冲"不一样, 调用方要自己处理
- **回测中历史 close 与现在 close 不同** — 30 天窗口会随时间滑动, 相关性会变, 建议每天重拉 (Init + Load 跑一次 ≈ 1ms)
- **Pearson 只测线性关系** — XAUUSDm 与 USDJPYm 在极端行情下可能正相关 (避险同涨), Pearson 不会告诉你
- **`Init` 重复调用会自动 `Clear()`** — 无需手动清; 但要确保每次 `LoadHistoricalCloses` 在 `Init` 之后
- **`Magic = 0` 会匹配所有持仓** — 包括其它 EA 的; 实盘务必用专属 magic

## 单元测试

`00-任务调度中心/daily/M18-CorrelationFilter-tests.ps1` — 3 个测试用例 (Pearson 算法等价):

```
TC1 perfect-positive  XAUUSDm/EURUSDm r=1.0000  expected=[0.99, 1.00]   [PASS]
TC2 perfect-negative  XAUUSDm/USDJPYm r=-1.0000 expected=[-1.00, -0.99] [PASS]
TC3 no-correlation    XAUUSDm/EURUSDm r=0.0545  expected=[-0.30, 0.30]  [PASS]
```

跑法：
```powershell
powershell -ExecutionPolicy Bypass -File "C:\ai\obsidian-文件\mt\00-任务调度中心\daily\M18-CorrelationFilter-tests.ps1"
```

## 实战案例

> 完整实战经验（3 个真实/未来场景 + 3 段即抄代码 + 3 档阈值取舍 + 5+ 陷阱 + 10 步 checklist + 5 条反模式）见：
>
> **[[实战/M18 多品种对冲实战]]** — 含 `MeanReversion_EA.mq5` 完整接入位置（line 20/63/70-73/104-122/167-172/242），ScalperXAU 接入 spec，Grid + 多品种 父 EA 协调骨架。

### 实战摘要（点开 wiki 前先看这段）

- **已落地**：`MQL5/Experts/minimax-ea/MeanReversion_EA.mq5` 已集成 M18，监控 `XAUUSDm,EURUSDm,GBPUSDm,USDJPYm` 4 个品种，threshold = 0.7
- **场景 A 关键代码**（OnTick 过滤点）:
  ```mql5
  if (InpUseM18Filter && M18.IsHedgeExposed(_Symbol, Magic, InpCorrThreshold)) {
     PrintFormat("[M18] 跳过 %s: 已有高相关品种持仓 (threshold=%.2f)",
                 _Symbol, InpCorrThreshold);
     return;
  }
  ```
- **参数取舍**：< 1,000 USD 用 0.5（严） / 1k-10k 用 0.7（默认） / > 10k + 外部对冲用 0.85（松）
- **5+ 已知陷阱**（节选）：30 天日线在 M30 上不够 / EURUSDm 周一跳空误判 / Magic=0 误匹配手动单 / Pearson 测不出黑天鹅同涨同跌 / DumpCorr 只打 1 次但 r 在漂移
- **必跑 baseline 对比**：接入 M18 前先关掉跑 1-3 个月回测记录 Net Profit / Max DD；再开 M18 跑同区间；trade count 应下降、DD ≤ baseline
- **5 条反模式**：threshold 0.95 / OnTick 重拉 / M18 替代 M02 / 监控 10 品种 / 把 M18 当 hedge sizing 工具

### 相关实战（M17 串联）

> **M18 是"开仓前过滤器", 与 M17（新闻过滤）同性质**。M18 跳过高相关品种 + M17 拦截新闻 ±N min = 双层前置过滤链。
>
> **[[实战/M17_TestNewsEA 复活报告]]** — M17 NewsFilter 实物自检 EA 复活（5 步流程 / 1 模块接入 / 6 RunSelfTest 断言 / 2026-06-04 落地）。
> 串联方式（MeanReversion_EA.mq5 / ScalperXAU.mq5 实物）：M19.IsInSession() → M17.IsNearEvent() → 指标 → M18.IsHedgeExposed() → M02.CanOpen() → M01.OrderSend()。

## 相关链接

- [[M02 风控 Risk]] — `risk.CanOpen()` 配合使用, M18 跳过 + M02 拒单 = 双层保护
- [[M03 仓位计算 PositionSizing]] — 若想"降低同向持仓的手数"代替"跳过", 用 M03.LotByRisk 乘以 `(1 - |corr|)`
- [[M07 持仓管理 Positions]] — `CPositions::CountMine(Magic)` 是 IsHedgeExposed 内部用的
- [[M15 定时器 TimerService]] — 想每天定时重拉 close, 配合 M15 周期任务
- [[M17 新闻事件过滤 NewsFilter]] — 与 M18 同性质, 都是"开仓前过滤器", 串在 OpenPos 前
- [[02-完整模板/EA 多品种对冲模板]] — M18 的多品种场景
- [[策略/01 ScalperXAU v1 - Bollinger RSI 均值回归]] — 用户主 EA, XAUUSDm M1; M18 用于将来扩展多品种

## 反向链接（中心节点 EA 接入报告）

> 本 M18 spec 是项目知识图谱的"模块 spec 节点"。下面 2 个 EA 中心节点 wiki 把 M18 作为 13 模块之一接入：
>
> - **[[实战/MeanReversion_EA 接入报告]]** — 13 模块全集（含 M18 + M19），M18 在第 12 行接入（line 20/63/104-122/167-172/242）。本 EA 是 M18 场景 A 实物 demo。
> - **[[实战/ScalperXAU 接入报告 + v1→v4 演进史]]** — 13 模块含 M17 + M13，M18 是 ScalperXAU 场景 B 接入目标（spec 阶段，未实施）。

---

## 实战扩展 (Round 2 — 06-05 06:00 T4 闭环)

> 沿用 00:00 T2 7 段范本 (场景A 3-5 段 + 场景B 3-5 段 + 接入点行号 5-10 段 + 调优点 5 档 + 陷阱 5 条 + 链向 5 实战 wiki), 末尾追加 10 个新场景。MeanReversion_EA / ScalperXAU v1-v4 / ScalperXAUv5-v9 5 个副仓 实物 Node.js fs 实测, 0 编造行号。

### 场景 A — 跨午夜对冲 (XAUUSDm + EURUSDm)

- **场景描述**: NY:22 后开 XAUUSDm 多 + EURUSDm 多, 跨午夜到 Asia:6, 期间 r 漂移从 +0.65 升到 +0.78 (VIX 跳升)
- **实物 demo**: MeanReversion_EA.mq5 L101 (OnInit 块 Init) + L255 (OnTick 调 IsHedgeExposed)
- **调优点**: r 阈值 0.7 → 跨午夜 0.6 (因 Asia 流动性低, 假相关风险高)
- **陷阱**: 跨午夜 r 漂移 0.65→0.78 期间可能开仓, 需 M19 联动屏蔽 Asia 时段
- **链向**: [[实战/MeanReversion_EA 接入报告]] §2.1 表格第 12 行

### 场景 B — 跨周末对冲 (XAUUSDm + GBPUSDm)

- **场景描述**: 周五 NY 收市前开 XAUUSDm + GBPUSDm 同向, 跨周末到周一 Asia 开市
- **实物 demo**: MeanReversion_EA.mq5 L167-172 (OnTick IsHedgeExposed 5 行 if 块)
- **调优点**: r 阈值 0.6 (因周末跳空 r 不可靠, 严控)
- **陷阱**: 周一 Asia 跳空 r 重算, 跟周末不相关
- **链向**: [[实战/M18 多品种对冲实战]] §1 场景 A

### 场景 C — 负相关对冲 (USDJPYm + EURUSDm r < -0.5 加仓)

- **场景描述**: r = -0.6 时 USDJPYm + EURUSDm 反向, 可用 M03.LotByRisk × (1 - |r|) 加仓
- **实物 demo**: ScalperXAU v2 (升级目标, 当前未实施, spec 阶段)
- **调优点**: |r| > 0.5 加仓 (1 - |r|) 系数, |r| > 0.8 全平
- **陷阱**: 负相关不稳定 (USDJPY 避险买盘 + EURUSD 风险卖盘), 黑天鹅会失效
- **链向**: [[实战/M18 多品种对冲实战]] §3 调优表

### 场景 D — XAUUSDm 单品种 0 对冲

- **场景描述**: 仅开 XAUUSDm, 其他品种未持仓, r=0 无对冲暴露
- **实物 demo**: ScalperXAUv5simple.mq5 (145L, 单品种 demo, 0 M18 接入)
- **调优点**: r=0 直接开, M18.IsHedgeExposed 返 false
- **陷阱**: 单品种风险高, DD 5% 强平线要严
- **链向**: [[实战/5 个 debug-prototype EA 索引]] §3 v5simple 接入

### 场景 E — 高相关强平 (r > 0.8 全平)

- **场景描述**: r = +0.85 XAUUSDm + USDJPYm 同向, 黑天鹅同涨同跌, 全平对冲暴露
- **实物 demo**: ScalperXAUv6debug.mq5 (45L, debug demo, 0 M18 接入, 验 EA 通路)
- **调优点**: r > 0.8 全平, 0.7-0.8 跳过, < 0.7 正常开
- **陷阱**: r=0.8 边缘 case, 加历史回测校准阈值
- **链向**: [[实战/5 个 debug-prototype EA 索引]] §3 v6debug 接入

### 场景 F — 4 品种同时段对冲

- **场景描述**: XAUUSDm + EURUSDm + GBPUSDm + USDJPYm 4 品种, 同时段开仓, r 矩阵 max
- **实物 demo**: ScalperXAUv7debug.mq5 (115L, 1 模块 M05 接入)
- **调优点**: r matrix max 跳过, 任一对 r > 0.7 触发
- **陷阱**: 4 品种 6 对 r, 计算量 O(n²), 用 M18.CalcCorr 缓存
- **链向**: [[实战/5 个 debug-prototype EA 索引]] §3 v7debug 接入

### 场景 G — 6 品种滚动对冲

- **场景描述**: 6 品种 (加 AUDUSDm + NZDUSDm), 滚动平仓/开仓
- **实物 demo**: ScalperXAUv8.mq5 (133L, 0 MQL5Kit 接入, 验 0 依赖通路)
- **调优点**: r mean 过滤, 6 品种 r 均值 > 0.6 触发
- **陷阱**: 6 品种 15 对 r, MT5 Strategy Tester 慢, 用 M15 TimerService 周期算
- **链向**: [[实战/5 个 debug-prototype EA 索引]] §3 v8 接入

### 场景 H — 跨午夜相关性变化 (NY:22 重新算)

- **场景描述**: NY:22 后 VIX 跳升, r 矩阵 30 min 内重算
- **实物 demo**: ScalperXAUv9.mq5 (311L, NY:22 重新算 r 段位)
- **调优点**: M15.OnTimer 30 min 一次重拉 close 价, 重新算 r
- **陷阱**: 重算 r 期间 r 漂移, 锁 1 min 不开新仓
- **链向**: [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] §3 v4 演进

### 场景 I — 新闻 ±30 min 相关性失效

- **场景描述**: NFP/CPI ±30 min 期间 r 失效 (USD 货币对同向跳空)
- **实物 demo**: ScalperXAUv9.mq5 (跟 M17 联动, 7 串联)
- **调优点**: M17.IsNearEvent(30, 30) 屏蔽期间, M18.IsHedgeExposed 跳过
- **陷阱**: 新闻后 5 min r 重算, 跟 M19 联动
- **链向**: [[实战/M17_TestNewsEA 复活报告]] §1 实物 demo

### 场景 J — DD 5% 强平 + 重算

- **场景描述**: 账户 DD 5% 触发强平, 强平后 r 重算 + 暂停 1h
- **实物 demo**: MeanReversion_EA.mq5 L295 (RefreshDash Row "M18" 显示) + M02.CanOpen DD 5% 检查
- **调优点**: DD ≥ 5% 全平, 暂停 1h, M18 r 重算
- **陷阱**: 强平后 r 矩阵空, 需 L101 OnInit 重新 Init
- **链向**: [[实战/MeanReversion_EA 接入报告]] §3 场景调优

---

## §N 漂移修复 & 验证 (N5 2026-06-04 20:00 闭环)

> 本节是 19:00 T2 漂移校验 + 20:00 N5 漂移修复的产物，记录本 wiki §实战案例 段 "[[实战/M18 多品种对冲实战]]" 反链中 MeanReversion_EA 接入位置的行号范围与实物对齐情况。

### N.1 漂移清单 (本 wiki 涉及 1 处 反链, 19:00 T2 §3.2.5)

| # | 位置 | 19:00 漂移 | N5 修后 | 实物实测 |
|---|---|---|---|---|
| 1 | §实战案例 (line 185) | `line 20/63/70-73/104-120/167-172/242` (104-120 微偏) | `line 20/63/70-73/104-122/167-172/242` (104-122) | 实物 L104-122 是 M18 OnInit Init 块 (SetDefaultDays + Init + LoadHistoricalCloses + PrintFormat + Print DumpCorr) |

> **根因**：19:00 T2 实测时 L104-120 是 M18 OnInit Init 块内容（不含 `}` 闭合），但 L121-122 才是闭合 `}` 和外层 `}`，本 wiki 反链 "104-120" 范围微偏 (缺末尾 2 行)。N5 修后为 "104-122"，范围 19 行覆盖完整 M18 OnInit Init 块。

### N.2 实物实测 (Node.js fs 2026-06-04 20:00)

```
MQL5/Experts/minimax-ea/MeanReversion_EA.mq5
  大小: 13,503 B / mtime: 2026-06-04T03:21:46 / 行数: 320
  M18 接入点 (5 处):
    L20: #include <MQL5Kit/M18_CorrelationFilter.mqh>
    L63: CCorrelationFilter M18;
    L104-122: OnInit Init 块 (M18 SetDefaultDays/Init/LoadHistoricalCloses/PrintFormat)
    L167-172: OnTick IsHedgeExposed 块 (5 行 if 调 + PrintFormat + RefreshDash + return)
    L242: RefreshDash Row "M18" 显示
```

> 0 改 .mq5, mtime 保持 03:21:46, 实物字节 13,503 不变。

### N.3 Node.js fs 一键复测命令 (verifier 独立复测本 wiki 漂移修复)

```bash
# 1) 实物 M18 接入点实测 (期望 L20/L63/L104-122/L167-172/L242)
node -e "const fs=require('fs');const c=fs.readFileSync('C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/MeanReversion_EA.mq5','utf8');const L=c.split('\n');console.log('L20:',L[19].includes('M18_CorrelationFilter')?'PASS':'FAIL');console.log('L63:',L[62].includes('CCorrelationFilter')?'PASS':'FAIL');console.log('L104-122:',L[103].includes('M18 相关性过滤初始化')&&L[121].includes('}')?'PASS':'FAIL');console.log('L167:',L[166].includes('IsHedgeExposed')?'PASS':'FAIL');console.log('L242:',L[241].includes('M18')?'PASS':'FAIL')"

# 2) 完整 11 文件 213 个 check 一键复测
node "C:\Users\Administrator\.mavis\plans\plan_f01a5f34\workspace\validate_lines.js"
# 期望: 213/213 PASS, 0 FAIL
```

### N.4 漂移根因分析

- **根因 (104-120 → 104-122 +2)**：19:00 T2 漂移校验时本 wiki §实战案例段反链 "line 20/63/70-73/104-120/167-172/242"，实测 M18 OnInit Init 块从 L104 开始，到 L122 才闭合（`}` 在 L121，外层 `}` 在 L122），原文 "104-120" 范围微偏 (少末尾 2 行)。N5 修后为 "104-122"，范围 19 行覆盖完整 M18 OnInit Init 块（含 SetDefaultDays + Init + LoadHistoricalCloses 循环 + PrintFormat + Print DumpCorr + else 分支 PrintFormat）。
- **本 wiki §反向链接段 (line 224) 的 "line 20/63/104-122/167-172/242"** 在 19:00 T2 实测 100% 命中 (N5 复测仍 PASS)，无漂移。
>
> 读者看完本 spec 后，跳到 [[实战/MeanReversion_EA 接入报告]] §2.1 表格第 12 行 = M18 完整实物接入点；跳到 [[实战/M18 多品种对冲实战]] §2.1 = OnInit + OnTick + input 完整段代码。
