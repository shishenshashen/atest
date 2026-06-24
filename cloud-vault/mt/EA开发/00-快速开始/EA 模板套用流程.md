---
title: EA 模板套用流程
tags: [EA, 流程]
type: workflow
---

# EA 模板套用流程（5 分钟改造成你的策略）

## 步骤
1. **打开 MetaEditor（F4）**，新建 EA：`File → New → Expert Advisor`，名字比如 `MyTrendEA`
2. **删空文件**，把 [[02-完整模板/EA 趋势跟踪模板（MA 交叉）]] 整段粘进去
3. **改 input 参数**（顶部那一堆 `input` 块）：
   - `Lot` 改成 `0.01` 或你想要的
   - `Magic` 改成你 EA 专属的整数（不同策略不能重复）
   - `MA_Fast`、`MA_Slow` 改成你要的周期
4. **编译**（F7），右下角 0 errors
5. **MT5 回测**（Ctrl+R）：
   - Symbol 选品种
   - Period 选时间
   - Modeling 选 "Every tick based on real ticks"
   - 点 Start
6. **看回测结果**：净值曲线、Sharpe、最大回撤、交易笔数
7. **模拟账户跑 1-2 周**
8. **实盘**：换服务器、保持小资金

## 调参建议
- 一次只改一个参数，看效果
- 优先调出场（SL/TP）而不是入场
- 多时间框架验证（同一逻辑跑 H1/H4 都跑）

## 模板的"在哪里改什么"
| 想改什么 | 在模板哪里 |
|---|---|
| 入场信号 | `bool GetSignal()` 函数 |
| 出场逻辑 | `void ManageTrades()` 函数 |
| 仓位计算 | `double CalcLot()` 函数 |
| 止损止盈距离 | input 顶部的 `SL_Points` / `TP_Points` |
| 指标 | input 顶部的指标相关 input + `int OnInit()` 里的句柄创建 |
| 时间过滤 | `bool IsTradeTime()` 函数 |
| 发送通知 | `SendNotification(...)` 那行 |
