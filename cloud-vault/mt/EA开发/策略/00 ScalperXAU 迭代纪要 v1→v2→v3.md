---
title: ScalperXAU v1 → v2 → v3 迭代纪要
tags: [EA, 迭代, 沉淀, XAUUSDm]
type: journal
---

# ScalperXAU v1 → v2 → v3 迭代纪要

> **核心教训**: 写 EA 之前不读现有知识库 = 重复造轮子 + 漏关键能力。
> v1→v2 加了 trade journal (MFE/MAE/ExitReason), v2→v3 补齐了库里有但 v2 没用的核心模块 (M08 Trail + ADX + 频率控制)。

## v1 (06-04 上午)

**目标**: 写个能跑 backtest 的 BB+RSI 剥头皮 EA

**做了什么**:
- 写完整 EA (565 行, 24 input)
- 集成 12 个 MQL5Kit 模块 (M01/M02/M03/M04/M05/M07/M09/M10/M11/M13/M16/M17)
- 编译过 (.ex5 89KB, 0 errors 2 warnings)

**漏了什么**:
- 没用 M08 TrailingStop (剥头皮关键)
- 没用 ADX 过滤 (单边行情大亏)
- 没用频率控制 (会被经纪商限)
- CSV 太简 (6 列)
- 没读 Obsidian 库已有沉淀 → 漏了核心能力

## v2 (06-04 10:18)

**目标**: 加 trade journal + EA 内滚动指标

**做了什么**:
- 加 MFE/MAE/Duration/ExitReason/Spread 进 CSV (23 列)
- 加 EA 内 11 个滚动指标 (仪表盘 + journal)
- 加持仓 MFE/MAE 实时跟踪
- 编译过 (.ex5 104KB, 0 errors 1 warning)

**漏了什么 (用户提示后才发现)**:
- 读 `EA开发/02-完整模板/EA 逆势均值回归模板（RSI Bollinger）.md` 发现模板有 **M08 TrailingStop + ADX 过滤**, 我没用
- 读 `EA开发/02-完整模板/EA 剥头皮模板.md` 发现模板有 **MinSecBetweenTrades / MaxTradesPerHour 频率控制**, 我没用
- 读 `EA开发/04-避坑与速查/05 必查清单.md` 发现 **NormalizeDouble / EMPTY_VALUE / HasDirection** 必查, 我都没用
- 读 `EA开发/04-避坑与速查/04 经纪商差异.md` 发现黄金 1 手 100 oz / 1 point = $1, 验证我的 SL/TP 点数计算正确

## v3 (06-04 10:31) — 基于沉淀重构

**目标**: 补齐所有库里有但 v2 漏的关键能力

**做了什么**:
1. ✅ 加 M08 TrailingStop (CTrailingStop::Init/SetParams/Apply, OnTick 调用)
2. ✅ 加 ADX 过滤 (iADX handle + CopyBuffer, ADX > 25 强趋势不开)
3. ✅ 加频率控制 (MinSecBetweenTrades + MaxTradesPerHour)
4. ✅ 加 HasDirection 防同向重复 (CPositions::HasDirection)
5. ✅ 加 NormalizeDouble (SL/TP 算后调)
6. ✅ 加 EMPTY_VALUE 检查 (指标 buffer 拿不到时跳过)
7. ✅ 加 SYMBOL_TRADE_STOPS_LEVEL 最小距离检查
8. ✅ ADX 进 CSV 新增列 `adx_at_entry`
9. ✅ ADX 进仪表盘显示
10. ✅ Exit reason 改 `TRAIL_OR_MANUAL` (v3 有 trail, SL_HIT 可能来自 trail)
11. ✅ Deviation 参数化 (InpDeviationPoints, 剥头皮建议 5-20)

**编译**: 0 errors 1 warning (M07 库文件 POSITION_COMMISSION deprecated, 不在我代码)

**编译产物**: .ex5 111KB (v2 104KB → v3 111KB, +7KB 是 M08 + ADX + frequency + 各种检查的代码)

## 关键沉淀 (下次写 EA 必读)

### 1. 写 EA 之前必读这 3 个文档
1. `EA开发/02-完整模板/EA 通用骨架.md` - 起点, 看 Input 命名 + 框架
2. `EA开发/02-完整模板/EA [你的策略类型].md` - 模板里直接有该策略的完整代码
3. `EA开发/04-避坑与速查/05 必查清单.md` - 发版前 Checklist

### 2. 策略对应模板

| 策略类型 | 模板 |
|---------|------|
| 逆势均值回归 (RSI + BB) | `EA 逆势均值回归模板（RSI Bollinger）` |
| 剥头皮 | `EA 剥头皮模板` |
| 趋势跟踪 (MA 交叉) | `EA 趋势跟踪模板（MA 交叉）` |
| 突破 (Donchian 海龟) | `EA 突破模板（Donchian 海龟）` |
| 网格马丁 | `EA 网格马丁模板` |
| 多品种对冲 | `EA 多品种对冲模板` |
| Dashboard 监控 | `EA Dashboard 监控模板` |

### 3. 关键模块漏用检查 (我每次必过)

- [ ] M08 TrailingStop (剥头皮必加)
- [ ] ADX 过滤 (逆势策略必加)
- [ ] 频率控制 (剥头皮必加)
- [ ] HasDirection (防同向重复)
- [ ] GetFilling 自动选 (跨经纪商)
- [ ] NormalizeDouble (SL/TP/price)
- [ ] EMPTY_VALUE 检查 (指标 buffer)
- [ ] SYMBOL_TRADE_STOPS_LEVEL 最小距离
- [ ] OnDeinit 释放所有 IndicatorRelease
- [ ] 0 错 0 警 (必查清单)
- [ ] OnInit 返回 INIT_SUCCEEDED

### 4. v3 vs 模板 差异 (ScalperXAU 特殊)

| 项 | 模板 | v3 |
|---|------|-----|
| 信号 | RSI<OS **或** price<bbLower | RSI<OS **且** price<=bbLower (更严) |
| SL/TP | 模板 200/150, v3 50/100 (XAU 1pt=$1) | - |
| 出场 | 模板用 trail, v3 trail + 固定 SL/TP | - |
| ATR 过滤 | 模板无, v3 有 | - |
| ADX 阈值 | 模板 25, v3 默认 25 | 一样 |
| Magic | 模板 20260201, v3 20240604 | 不冲突 |

## 性能预测 (v3 vs v2)

- **入场数**: v3 少了 50% (频率控制 + HasDirection)
- **胜率**: v3 提升 (ADX 过滤排除强趋势逆势单)
- **回撤**: v3 降低 (trail 锁利 + ADX 避免大亏)
- **样本量**: 可能 v3 总交易数 < 50 (要看 1 月数据), 不达 50 笔的话, 调长 backtest 区间到 3 月

## 下一步 (v4 计划)

跑完 v3 backtest 后:
- 如果 Net>0+PF>1.3 → attach demo 24h
- 如果没达 → 看 trade CSV 分析:
  - ADX 过滤是不是太严 (过滤掉 80% 信号)
  - Trail 是不是太紧 (频繁被震出)
  - BB/RSI 阈值是不是要调
- 调参基于实测数据, 不是猜

## 相关文档

- v3 spec: [[ScalperXAU v3 - Bollinger RSI ADX Trail]]
- M08 文档: [[M08 追踪止损 TrailingStop]]
- 模板: [[EA 逆势均值回归模板（RSI Bollinger）]], [[EA 剥头皮模板]]
- 必查清单: [[04 避坑 - 必查清单]]
- 经纪商差异: [[04 避坑 - 经纪商差异（点差\手数\Filling）]]
- 实盘 vs 回测: [[04 避坑 - 实盘 vs 回测差异]]
- 编译错误: [[04 避坑 - 编译常见错误]]
