---
title: M15 定时器 TimerService (心跳)
tags: [调用模块, 定时, 心跳]
type: module
---

# M15 定时器 TimerService

> **作用**：统一封装 MT5 定时器，**比 OnTick 节能**（OnTick 可能每秒上百次，Timer 可以精确控制节奏）。
> **配套指标**：`Fires`（累计触发次数）+ `LastFire`（上次触发时间） → 任何 EA 都能展示 **心跳**。

## API（8 个方法 + 2 个增强）

```mql5
class CTimerService {
public:
   bool   Init(int period_ms);    // 设置周期（毫秒）；自动选 EventSetMillisecondTimer 或 EventSetTimer
   void   Deinit();               // 停掉定时器（OnDeinit 里调）
   bool   OnTimer();              // 在 EA 的 OnTimer 里调一次；返回 true=当前活跃
   bool   IsActive() const;       // 是否已注册到 MT5
   void   Start();                // 手动启动（Stop 之后用）
   void   Stop();                 // 暂停（保留配置，可再 Start）
   datetime LastFire() const;     // 上次触发时间（服务器时间）
   int    Fires() const;          // 累计触发次数

   // 增强方法（可选，不影响主 API）
   int    Period() const;         // 实际周期（毫秒）
   string Mode() const;           // "ms"=走毫秒定时器；"s"=走秒定时器
};
```

## 用法（EA 中）

```mql5
#include <MQL5Kit/M15_TimerService.mqh>

CTimerService _timer;

int OnInit() {
   if (!_timer.Init(2000)) {       // 2 秒一次
      Print("timer init failed");
      return INIT_FAILED;
   }
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   _timer.Deinit();
}

void OnTimer() {
   if (_timer.OnTimer()) {
      // 这里就是「心跳」业务
      PrintFormat("heartbeat #%lld at %s", _timer.Fires(),
                  TimeToString(_timer.LastFire(), TIME_SECONDS));
   }
}
```

## 在 Dashboard（只读监控）里

`Dashboard.mq5` 展示了完整用法 —— 定时器驱动面板刷新，并通过 `Fires()`/`LastFire()` 在面板上画一条 "Heartbeat" 行：

```mql5
_dash.Row("Heartbeat", IntegerToString(_timer.Fires()) + " fires (period " +
           IntegerToString(_timer.Period()) + _timer.Mode() +
           ", last " + TimeToString(_timer.LastFire(), TIME_SECONDS) + ")");
```

输出示例：
```
Heartbeat : 42 fires (period 2000ms, last 2026.06.04 00:22:31)
```

## 周期选择逻辑

| `Init(period_ms)` | 实际走的 MT5 API | 限制 |
|---|---|---|
| `< 1000` | `EventSetMillisecondTimer(period_ms)` | MQL5 范围 20-1024ms（<20 被夹到 20） |
| `>= 1000` 且 `%1000==0` | `EventSetTimer(period_ms/1000)` | MQL5 范围 1-60s |
| `>= 1000` 但不是整千 | `EventSetMillisecondTimer(period_ms)` | 实际达不到精确 ms（MQL5 不支持 >1024ms 的 ms 定时器） |

> ⚠️ 2500ms 这种"非整秒"周期会被 `Period()` 报 2500，但 `Mode()` 报 `ms`，**实际**走的还是 EventSetMillisecondTimer，可能到不了 1024ms 上限 — **保守用法**：要么用 `<=1024ms` 的整数毫秒，要么用 `>=1000` 的整秒。

## 与直接 `EventSetTimer` 的区别

| | `EventSetTimer` 原生 | `CTimerService` 包装 |
|---|---|---|
| 周期精度 | 整秒 | 毫秒（自动选 API） |
| 心跳统计 | 需要自己写 | 内置 `Fires()` / `LastFire()` |
| 启动/停止 | `EventSetTimer` + `EventKillTimer` | `Start()` / `Stop()` 状态管理 |
| 重复 Init | 需手动 kill 再 set | `Init()` 内部自动清理 |

## 必看陷阱

- **`OnTick` 和 `OnTimer` 二选一**（MT5 规则）—— EA 用了 OnTick，OnTimer 就被忽略
- **`OnTimer` 必须在 OnInit 之后才会被调用**，所以 `Init()` 之前不要访问定时器相关方法
- **不要在 `OnTimer` 里做长时间阻塞操作**（MT5 同一时刻只有一个 timer 事件）
- **重启 EA / 切换图表**会触发 `OnDeinit` → 自动 `Deinit()`，但 `Fires` 计数器会被清零
- **Init 失败**通常是因为 `EventSetMillisecondTimer` 的参数越界（<20 或 >1024）—— `Init` 内部会夹到合法范围

## 替代方案对比

| 方法 | 优 | 劣 |
|---|---|---|
| **CTimerService（推荐）** | 跨秒/毫秒统一、心跳统计、状态管理 | 多一层封装 |
| `EventSetTimer(秒)` | 直接、简单 | 只能整秒 |
| `EventSetMillisecondTimer` | 高频 | 范围 20-1024ms |
| `OnTick` 轮询 | 永远触发 | 高频伤 CPU |

## 完整代码

`MQL5/Include/MQL5Kit/M15_TimerService.mqh`（88 行）—— 见文件。

---

## 实战案例

- **Dashboard.mq5 1-2s 心跳 + 跨品种监控**（接入点：line 12 `M15_TimerService.mqh` include / line 32 `CTimerService _timer` 全局对象 / line 46 `_timer.Init(RefreshSec * 1000)` OnInit / line 66 `_timer.Deinit()` OnDeinit / line 75-81 `OnTimer()` 处理函数 / line 78 `if (_timer.OnTimer())` 节流 / line 115-117 `_timer.Fires()/Period()/Mode()/LastFire()` 写到 dashboard Heartbeat 行）
  - 关键 API：`CTimerService::Init(int ms)` / `OnTimer()` / `IsActive()` / `Start()` / `Stop()` / `Deinit()` / `Fires()` / `LastFire()` / `Period()` / `Mode()`（spec line 17-28）
  - 调优：`RefreshSec=2`（input line 23）→ `Init(2000)` 走 `EventSetTimer(2)` 整秒；<1000 走 `EventSetMillisecondTimer`；<20ms 自动夹到 20；>1024ms 的"非整千"周期会进 ms 模式但**实际达不到精确 ms**（spec line 77-83）
  - 链向：[[02-完整模板/EA Dashboard 监控模板]] / [[实战/BBTrendEA 复活 SOP]]（line 79 + 247 `EventSetTimer(1)` 每秒刷 panel → M15 替换，加 `Fires/LastFire` 心跳统计）/ [[M09 面板 Dashboard]]（M09 刷新节流用 M15 1s/2s 周期，OnTimer + M15 而不是 OnTick 每 tick 重建字符串）

### 反向引用（实物 EA 接入 demo, 21:00 T2 沉淀）

> **本段是 21:00 巡检 T2 任务对 [[实战/MyEA + Dashboard 接入报告]] 的反向链接**。M15 TimerService 在 minimax-ea/ 10 实物 EA 中**只有 1 个 EA 接入** (Dashboard.mq5), 属稀缺接入 demo:

- **Dashboard.mq5** (`MQL5/Experts/minimax-ea/Dashboard.mq5` 208L/8.3KB, 4 模块 M04+M09+M10+M15): `Init(RefreshSec * 1000)` L57 (M15 心跳 wrapper, RefreshSec=2 → 2000ms 走 `EventSetTimer(2)` 整秒) + `OnTimer` L90-L94 (`if (_timer.OnTimer()) _Refresh()` 节流) + `Deinit` L83 (OnDeinit 必停心跳) + Heartbeat 4 查询 L117-L119 (`Fires/Period/Mode/LastFire` 写到 dashboard, 用户能直接看"EA 是否还活着")
- **唯一性**: minimax-ea/ 10 实物 EA 中**只有 Dashboard.mq5 接 M15** — 其他 9 个 EA (MyEA / MeanReversion_EA / ScalperXAU / TrendMA_EA / Breakout_EA / BBTrendEA / M17_TestNewsEA / Scalper_CsvProto / ScalperXAUv5-v9) 全部走 OnTick + NB.IsNewBar 节流, **不走 OnTimer**
- **vs 模板裸调**: [[02-完整模板/EA Dashboard 监控模板]] L56 用 `EventSetTimer(RefreshSec)` 裸调, Dashboard 走 `_timer.Init(RefreshSec * 1000)` M15 包装 — 升级收益: 周期支持非整秒 (1.5s/800ms) + 心跳统计 + 启停状态机
- **链向**: [[实战/MyEA + Dashboard 接入报告]] §1.4 Dashboard 独有 M15 + §2.2 row 4 (M15) + §2.6 M15 实战 §OnTimer + §5.1 场景 A 调优 RefreshSec 3 档
