---
title: 写 EA 必走流程 5 步法 (15:00 候选 T5 新建, 直接服务用户 IM 第 5 条 '写 EA 必读 obsidian 知识库, 沉淀为知识点, 去优化')
date: 2026-06-05
type: guide
tags: [EA开发, 写EA-必走流程, 5-步法, MOC-入口, 4-范本, 12-必读, 4-片段, 5-速查-反模式, 服务用户-IM-第-5-条, 11-00-R1-实战段, 14-00-R2-验证段, 15-00-R3-调试段]
---

# 写 EA 必走流程 5 步法 (15:00 候选 T5 新建)

> **服务**: 用户 IM 第 5 条 "你不是有obisidian吗 那上面有已经成型的mql5的知识点和模块化的方案,你写ea的时候要去读相关文件。这个沉淀为知识点,去优化"
> **沿用**: 11:00 R1 实战段 + 14:00 R2 验证段 + 15:00 R3 调试段 历次 5 步法系统化
> **维护**: Mavis orchestrator + general worker (15:00 候选 T5 T4 owner 顺手做, 0.1h 闭环)

---

## 摘要 (30 秒读完)

写 EA 时必走 5 步流程, 漏一步出错: (1) 看 MOC 总入口 → (2) 看 4 实物范本 → (3) 读 12 必读 → (4) 用 4 通用片段 → (5) 避 5 速查 + 9 反模式. 5 步顺序必走, 跟 11:00 R1 + 14:00 R2 + 15:00 R3 历次巡检沉淀一致, 11:00 R1 实战段讲"接入/调优/陷阱", 14:00 R2 验证段讲"如何一键复测", 15:00 R3 调试段讲"调试场景/步骤/陷阱".

---

## Step 1: 看 MOC (总入口) — 找对应知识分类

**入口**: [[EA开发/EA 开发知识库]] (MOC 8 范式 + 70 wiki 链向, 42,974B)

8 范式分类 (沿用 13:00 候选 P MOC v2 重写):
1. **写 EA 入口** → 找对应知识分类 (eg. 逆势均值回归 → 写 EA 入口 → 12 必读 M01-M19 选)
2. **模板套用** → 8 模板 (通用骨架 / MA 交叉 / RSI Bollinger / Donchian 突破 / 网格马丁警示 / 剥头皮 / 多品种对冲 / Dashboard 监控) 选最接近范本
3. **模块调用** → 12 必读 M01-M19 + MQL5Kit 19 模块全集接入 demo
4. **通用片段** → 4 片段 (01 下单类 / 02 读取类 / 03 画图类 0/0EA 跳过 / 04 实用函数) 10 段摘要
5. **反模式避坑** → 5 速查 wiki (01-05) ## 反模式 段 + 9 反模式 wiki (06-08 + 跨 EA 模式萃取) ## 反模式 段 + 80 ❌ 集中展示
6. **性能调优** → [[EA开发/性能调优/MT5 性能调优 wiki]] (06:00 候选 S 闭环, 8 性能维度 × 19 模块段位)
7. **异常处理** → [[EA开发/异常处理/异常处理手册]] (06:00 候选 T 闭环, 4 异常维度 × 19 模块段位)
8. **高级设计** → [[EA开发/05-高级设计模式/高级 EA 设计模式 wiki]] (07:00 候选 V 闭环, 7+1=8 模式 6 章节)

---

## Step 2: 看 4 实物范本 wiki — 选最接近范本, 1-2h 改参数

**4 范本 wiki** (沿用 06-04 15:00+17:00+18:00+21:00 历次沉淀):

| 范本 | 路径 | 字节 | 章节 | 适用场景 |
|---|---|---|---|---|
| **范本 A** (单 EA) | `EA开发/实战/MeanReversion_EA 接入报告.md` | 17.7K/205L/5 章 | 实物 / 13 模块 / 编译 / M18+M19 / 3 场景 | 单 EA 完整接入 (XAUUSDm 逆势均值回归) |
| **范本 B** (单 EA + 演进) | `EA开发/实战/ScalperXAU 接入报告 + v1→v4 演进史.md` | 29.8K/350L/6 章 | 实物 / 13 模块 / v1→v4 演进 4 版本 17 维度对比 / v3 0 笔根因 / 3 场景 | 单 EA 演进 (XAUUSDm 剥头皮 v1→v4) |
| **范本 C** (2 EA 联合) | `EA开发/实战/TrendMA_EA + Breakout_EA 接入报告.md` | 40.4K/366L/8 章 | 实物 / 12+11 模块 / 编译 / M03-M08 / 3 场景 / 5 反模式 / 链向 | 2 EA 联合 (趋势 + 突破, 互补) |
| **范本 D** (2 EA + 监控) | `EA开发/实战/MyEA + Dashboard 接入报告.md` | 53.9K/718L/8 章 | 实物 / 14 模块 / 编译 / M09-M15-M10 / 3 场景 / 5 反模式 / 链向 | 2 EA 联合 + Dashboard 监控 |

**新增 (15:00 候选 X 闭环后)**: 4 实物 EA 联合 wiki 模板 (新建 1 wiki, 7 章节 + 1 附录, 22-31K 字节), 给用户写新 EA 接入报告 5 步 SOP.

**操作**: 复制最接近范本 → 实物信息改 (EA 名/路径/字节/行数/mtime) → 模块清单改 (必 Node.js fs 实测 14 实物行号) → 编译验证跑 → MOC 加链向

---

## Step 3: 读 12 必读 wiki — 0 编造 API

**12 必读 wiki** (沿用 `mql5-wiki-12-必读.md` §2 必读清单):

| # | 必读 wiki | 关键 API |
|---|---|---|
| 1 | [[EA开发/01-调用模块/M01 交易封装 CTradePlus]] | CTradePlus::Init / Buy / Sell / ClosePos |
| 2 | [[EA开发/01-调用模块/M02 风控 Risk]] | Risk.CanOpen(type, lot, sl, tp) |
| 3 | [[EA开发/01-调用模块/M05 新 K 线检测 NewBar]] | IsNewBar() 单线 demo (11 EA 频次 287) |
| 4 | [[EA开发/01-调用模块/M08 追踪止损 TrailingStop]] | SetParams(start, step, minGap) + Apply() (MeanRev 1.5×ATR 1×ATR demo) |
| 5 | [[EA开发/01-调用模块/M09 面板 Dashboard]] | Dashboard.Row(...) + Show() + Refresh() (MeanRev L237-247 demo) |
| 6 | [[EA开发/01-调用模块/M10 推送通知 Notify]] | Notify.Send(msg, highPriority) / Trade / Alert 3 类触发器 |
| 7 | [[EA开发/01-调用模块/M11 日志 Logger]] | logger.Info/Warn/Error/Trade 4 级别 (SX L321-322 demo) |
| 8 | [[EA开发/01-调用模块/M13 文件 IO]] | CFileIO::AppendCSV(fileName, fields) (SX L341 trade journal demo) |
| 9 | [[EA开发/01-调用模块/M17 新闻过滤 NewsFilter]] | IsNearEvent(±min, _Symbol) + LoadFromCSV() + 6 自检断言 |
| 10 | [[EA开发/01-调用模块/M18 相关性过滤 CorrelationFilter]] | IsHedgeExposed / thr= 阈值调优 (r=0.6/0.7/0.8) (MeanRev L20 demo) |
| 11 | [[EA开发/01-调用模块/M19 时段过滤 SessionFilter]] | 4 预定义常量 (Asia/London/NY/Off) + 跨午夜 NY:22-6 (MeanRev L161 demo) |
| 12 | [[EA开发/EA 开发知识库]] (MOC 总索引) | 必读 L1-L100, 实战 wiki 链向 + 速查 wiki 链向 + 实战相关链向 3 分类 |

**0 编造 API**: 必先 grep wiki 现有 API, 沿用 12 必读 wiki 方法名, 不二次创作.

---

## Step 4: 用 4 通用片段 — 不重复造轮子

**4 片段 wiki** (沿用 [[EA开发/03-通用片段/00 片段目录]] 4 片段 10 段摘要):

| # | 片段 | 用途 | 频次 |
|---|---|---|---|
| 1 | [[EA开发/03-通用片段/01 下单类]] | 4 函数 (Buy/Sell/ClosePos/TrailingStop) | 47 次/8 EA |
| 2 | [[EA开发/03-通用片段/02 读取类]] | 9 函数 (IsNewBar/Ask/Bid/High/Low/Volume/iTime/iOpen/iClose) | 287 次/11 EA (最高频) |
| 3 | ~~03 画图类~~ | (0/0 EA 跳过, 决策落盘 06-05 00:00) | 0 |
| 4 | [[EA开发/03-通用片段/04 实用函数]] | 8 函数 (Print/Comment/Format/Conv/Time/Math/Str/Array) | 51 次/11 EA |

**0 重复造轮子**: 11 EA 频次共 385 次, 不重复造片段函数, 必先 grep [[EA开发/03-通用片段/00 片段目录]] 现有 4 片段 10 段摘要.

---

## Step 5: 避免反模式 — 5 速查 + 9 反模式 wiki + 80 ❌ 集中展示

**5 速查 wiki ## 反模式 段** (沿用 16:00+21:00 T4 5 速查反模式段位):

| # | 速查 wiki | 反模式数 | 侧重点 |
|---|---|---|---|
| 1 | [[EA开发/04-避坑与速查/01 编译常见错误]] | 21 ❌ | 编译错 (MQL5 头文件 / enum 重定义 / 闭合) |
| 2 | [[EA开发/04-避坑与速查/02 OrderSend 错误码速查]] | 9 ❌ | OrderSend 拒单 (retcode 10006/10018/10030) |
| 3 | [[EA开发/04-避坑与速查/03 实盘 vs 回测差异]] | 6 ❌ | 实盘 vs 回测 (spread/slippage/重连) |
| 4 | [[EA开发/04-避坑与速查/04 经纪商差异-点差-手续费]] | 7 ❌ | 4 broker spread 差 + filling 模式 |
| 5 | [[EA开发/04-避坑与速查/05 必查清单]] | 9 ❌ | 5 必查项漏查 + 6 retcode 永远不要 |

**9 反模式 wiki** (沿用 11:00 R1 实战段 + 14:00 R2 验证段 + 15:00 R3 调试段):

| # | 反模式 wiki | 11:00 R1 实战段 | 14:00 R2 验证段 | 15:00 R3 调试段 |
|---|---|---|---|---|
| 6 | [[EA开发/04-避坑与速查/06 网格马丁警示]] | 6 段 | +3.4K 验证段 | +1.5-2K 调试段 (紧凑版) |
| 7 | [[EA开发/04-避坑与速查/07 5 必看陷阱统一 wiki]] | 6 段 | +3.7K 验证段 | 待 15:00 R3 完整版 |
| 8 | [[EA开发/04-避坑与速查/08 5 速查调试小技巧 wiki]] | 6 段 | +3.4K 验证段 | +1.5-2K 调试段 (紧凑版) |
| 9 | [[EA开发/实战/跨 EA 模式萃取]] | 6 段 | +3.7K 验证段 | 待 15:00 R3 完整版 |
| + | [[EA开发/04-避坑与速查/06 网格马丁警示]] 等 5 wiki | 5 段实战段 | (14:00 R2 错位 5 wiki) | (15:00 R3 紧凑版 5 wiki 配对) |

**80 ❌ 集中展示**: 5 速查 ❌ 总 80 个 (16:00 T4 31 旧 + 21:00 T3 49 新) + 11 wiki ## 反模式 段 55 条 (16:00 T4 5 速查) = 135 baseline (worker 写新反模式必先 grep 0 重复)

**0 重复反模式**: 必先 grep 80 ❌ + 11 wiki ## 反模式 段 + 09:00+10:00+11:00+14:00 T3 5+5+5+? baseline, 0 重复

---

## 写 EA 出错 9 路径快速复测 (跟 14:00 R2 闭环 Node.js 9 脚本对齐)

写 EA 出错时, 直接跑对应 Node.js fs 一键复测脚本 (沿用 14:00 R2 闭环 9 脚本 + 15:00 R3 紧凑版 5 脚本):

| 写 EA 错 | 速查 wiki | Node.js 复测脚本 (14:00 R2 + 15:00 R3 紧凑版) |
|---|---|---|
| 编译错 | 01 编译 | `node mql5-build-validate.js` (14:00 R2) |
| OrderSend 拒单 | 02 OrderSend | `node mql5-trades-csv-scan.js` + `node mql5-trades-csv-debug-r3.js` (15:00 R3) |
| 实盘 vs 回测 差异 | 03 实盘 vs 回测 | `node mql5-journal-compare.js` + `node mql5-journal-compare-debug-r3.js` (15:00 R3) |
| 4 broker spread 差 | 04 经纪商 | `node mql5-symbol-info.js` |
| 5 必查项漏查 | 05 必查 | `node mql5-selfcheck-5items.js` + `node mql5-selfcheck-5items-debug-r3.js` (15:00 R3) |
| 网格马丁炸 | 06 网格马丁 | `node mql5-grid-martingale-warn.js` + `node mql5-grid-martingale-warn-debug-r3.js` (15:00 R3) |
| 80 ❌ 命中 | 07 必看陷阱 | `node mql5-80-antipattern-grep.js` |
| Print 不输出 | 08 速查调试 | `node mql5-debug-print-scan.js` + `node mql5-debug-print-scan-debug-r3.js` (15:00 R3) |
| 9 wiki 链向断 | 跨 EA 模式萃取 | `node mql5-9wiki-link-validate.js` (硬 check) |

**15 段统一 0 推荐语 + 0 placeholders + 0 编造接入点行号** (沿用 14:00 9 项反模式 + 加 R3 紧凑版 1 条 = 10 项)

---

## 写 EA 必走流程 5 步法 (顺序必走, 漏一步出错)

1. **看 MOC** → [[EA开发/EA 开发知识库]] 总入口, 8 范式 + 70 wiki 链向
2. **看 4 实物范本** → 4 范本 wiki (MeanRev / SX / TrendMA+BO / MyEA+Dash) + 15:00 候选 X 新建 [[实战/4 实物 EA 联合 wiki 模板]]
3. **读 12 必读** → 11 module spec + MOC, 0 编造 API
4. **用 4 通用片段** → [[EA开发/03-通用片段/00 片段目录]] 4 片段 10 段摘要
5. **避免反模式** → 5 速查 wiki ## 反模式 段 + 9 反模式 wiki ## 反模式 段 + 80 ❌ 集中展示 + 写 EA 出错 9 路径快速复测 (跟 14:00 R2 + 15:00 R3 紧凑版 9 + 5 Node.js 脚本对齐)

---

## 关联任务

- **15:00 候选 T5** (本 wiki): 写 EA 必走流程 5 步法 wiki, T4 owner 顺手做 0.1h 闭环, 直接服务用户 IM 第 5 条
- **15:00 候选 T4** (并行): 9 反模式 wiki Round 3 末尾 ## 调试案例 段 紧凑版 5 wiki 0.5h, 跟 14:00 R2 错位 5 wiki 配对, plan_f0e2bfda T2 worker-A 跑
- **15:00 候选 X** (候补): 4 实物 EA 联合 wiki 模板 1.5h, 沿用 4 范本 wiki 压缩
- **14:00 候选 T3** (已闭环): 9 反模式 wiki Round 2 末尾 ## 验证 段 1h 闭环 (plan_763d71e2 plan_complete=true, attempt 2 7 错行号 + 33 链向占位 + 2 M09/M10 命名 全 修, 11 Node.js 9/9 PASS 硬 check, 28/28 行号 Node.js fs 实测命中)
- **11:00 候选 T** (已闭环): 9 反模式 wiki Round 1 末尾 ## 实战案例 段 1h 闭环
- **08:00 候选 X** (已闭环): 4 范式 EA 联合 wiki 模板 0.5h 闭环 (沿用 06-04 15:00+17:00+18:00+21:00 4 范本 wiki 压缩, 0 改 MOC 前文)

---

**版本**: v1.0 (2026-06-05 15:25 闭环, 15:00 候选 T5 T4 owner 顺手做)
**维护人**: Mavis orchestrator (15:00 owner session `mvs_dae027af0b564b92921a59e3f12dc7b8`)
**关联任务**: 15:00 plan_f0e2bfda, 候选 T5, 写 EA 必走流程 5 步法 wiki, 0.1h 闭环
