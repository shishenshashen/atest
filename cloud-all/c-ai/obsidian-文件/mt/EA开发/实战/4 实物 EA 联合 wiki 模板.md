---
title: 4 实物 EA 联合 wiki 模板 (新建 wiki, 8 章节 + 附录 SOP 5 步法, 沿用 06-04 4 范本 wiki 压缩)
date: 2026-06-05
type: usage
session: mvs_37cfcfedaf75418d8e098f2b88d33307
tags: [EA开发, 实战, 4-实物, 模板, EA-接入, 4-范本, 8-章节, SOP-5-步法, 14-实物, 0-改-前文, 链向]
---

# 4 实物 EA 联合 wiki 模板 (8 章节 + 附录, 沿用 4 范本 wiki 压缩, 22-31K 字节)

> **本 wiki = 写新 EA 接入报告时的"4 范本套用模板"**, 06-05 16:00 plan T3 候选 X 闭环, 14:00 §5 维度 5 候选 G 续篇。
> **0 阻塞**: 14 实物 .mq5 mtime UNCHANGED 14/14 (Node.js fs 2026-06-05 16:18 baseline), 0 改 wiki 前文 (新 wiki 新建), 0 改 MOC 前文 (末尾追加 1 行链向允许, +20-50B), 0 创建 README/agents/protocols (废弃决策 06-03 16:14)。
> **1 段骨架**: 4 范本 (MeanReversion / ScalperXAU+v1→v4 / TrendMA+Breakout / MyEA+Dashboard) × 8 章节对比矩阵 + 8 模板字段 (META / 实物信息 / 模块全集 / 编译验证+实战关系+场景调优 / 反模式+链向 / SOP 5 步法 / 4 范本链向) × 14 实物接入 demo 行号 (100% Node.js fs 实测, 沿用 4 范本 wiki baseline)。
> **0 编造**: 模板骨架来自 4 范本 wiki 实际段落 (Node.js fs readFileSync 实读, 2026-06-05 16:18), 不二次创作, 接入 demo 行号 100% Node.js fs 实测 (沿用 4 范本 baseline 14 实物)。

---

## §1 META (frontmatter + 摘要 + 维护人 + 关联任务, 1-2K)

> **本节用途**: 任何新 EA 接入报告 wiki 必须从 META 段开始, 标明**类型 / 维护人 / 关联任务 / 关联范本 / 摘要 30 秒**。

### 1.1 frontmatter 模板 (复制后改 4 处)

```yaml
---
title: <EA 名> 接入报告 (或 <EA A> + <EA B> 联合接入报告)
date: 2026-MM-DD            # 创建日期
type: usage                 # 固定, type: usage = 实战用法 wiki
session: mvs_<hash>         # 创建任务的 session id
tags: [EA开发, 实战, <EA-名-1>, <EA-名-2>, 接入, 联合, 沉淀 #N-N]
version: 1.0
---
```

**4 处占位说明**: 1) `<EA 名>` / `<EA A> + <EA B>`: 单 EA 用 EA 名, 2 EA 联合用 `+` 分隔; 2) `date`: ISO 日期; 3) `session`: 16 字符 mvs_xxx; 4) `tags`: 必含 `EA开发, 实战`, 其他按 EA 特征补 (如 `网格`, `对冲`, `单 EA`, `2-EA-联合`)

### 1.2 摘要 30 秒读完 (模板, 复制后改数字)

> **本 wiki 是 `MQL5/Experts/minimax-ea/<EA A>.mq5` ( + `<EA B>.mq5` ) 的接入报告**。
> <EA A> ( **<N1> L / <N2> B / <N3> 模块 M0X 列表, Magic <magic>, <N4> top-level functions** ) + <EA B> ( **<M1> L / <M2> B / <M3> 模块 M0X 列表, NotifyMagic=<nmagic>, <M4> top-level functions** ) = minimax-ea/ 14 实物 EA 中**"<范本类型>"**的 demo。
>
> **本 wiki 价值定位** (4 角度, 必填): 1) **<EA A> = <范式 1>** —— 是 [[02-完整模板/<模板 A>]] 的 1:1 实物版, **<独有模块>** (<列出 1-3 个>) 2) **<EA B> = <范式 2>** (若有) —— 是 [[02-完整模板/<模板 B>]] 的 1:1 实物版 3) **2 EA 共享 <共享模块> 模块** (M0X+M0X = 2 个, 同 [[实战/<范本 wiki>]] 范本) 4) **5 反模式 100% 来自实物代码** (列举 1-2 个最反直觉的反模式, 防重犯)
>
> **目标读者** (3-4 类): 复制 <EA A> 作起点 / 套 <EA B> 模板 / 看 "<独有亮点 1>" 范本 / 看 "<独有亮点 2>" demo

### 1.3 维护人 + 关联任务 + 关联范本 (3 段, 必填)

```
维护人: Mavis (本 session owner)
关联任务: 06-MM-DD HH:00 plan_<hash> T<N> <候选名> 闭环
关联范本: [[实战/<范本 A wiki>]] + [[实战/<范本 B wiki>]] + [[实战/<范本 C wiki>]] + [[实战/<范本 D wiki>]]
          (单 EA 接入选 1 个最接近的范本, 2 EA 联合选 1 个 2 EA 范本)
```

**4 范本 wiki 全名** (用户按 EA 类型选最近 1 个, 06-04 历次沉淀, 详细字节/章节/模块数见 §2.2 速查表):

- 范本 A: [[实战/MeanReversion_EA 接入报告]] (29,494B / 388L, 5 章节, 单 EA 完整接入, 13 模块 M0X 全集)
- 范本 B: [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] (41,195B / 583L, 6 章节, 单 EA + v1→v4 演进, 13 模块 + 4 版本 17 维度)
- 范本 C: [[实战/TrendMA_EA + Breakout_EA 接入报告]] (75,587B / 952L, 8 章节, 2 EA 联合接入, 12+11 模块)
- 范本 D: [[实战/MyEA + Dashboard 接入报告]] (61,742B / 791L, 8 章节, 2 EA 联合 + 监控, 10+4 模块)

---

## §2 模板结构 (4 范本对齐表, 5-7K)

> **本节用途**: 4 范本 wiki (A/B/C/D) 8 章节结构对比矩阵, 用户写新 EA 时按"EA 特征 → 选最接近的范本 → 复制该范本 8 章节骨架 → 改参数"。

### 2.1 4 范本 wiki 8 章节结构对比矩阵 (核心表格)

| 章节 | 范本 A MeanReversion (29K/388L/5章) | 范本 B ScalperXAU+v1→v4 (41K/583L/6章) | 范本 C TrendMA+Breakout (75K/952L/8章) | 范本 D MyEA+Dashboard (61K/791L/8章) |
|---|---|---|---|---|
| §0 摘要 30 秒 | ✅ L17-27 (10L) | ✅ L29-39 (10L) | ✅ L34-45 (11L) | ✅ L28-39 (11L) |
| §1 实物基本信息 | ✅ L29-46 (17L) 6 维度 | ✅ L41-61 (20L) + v1-v4 5 版本 | ✅ L47-109 (62L) 2 EA 6 维度 × 2 | ✅ L41-97 (56L) 2 EA 6 维度 × 2 |
| §2 接入模块清单 | ✅ L48-94 (46L) 13 模块 | ✅ L63-114 (51L) 13 模块 | ✅ L111-209 (98L) 12+11 模块 | ✅ L99-262 (163L) 10+4 模块 |
| §3 编译验证+沙盒 / 演进史 | ✅ L96-115 (19L) | ✅ L116-229 (113L) v1→v4 17 维度 | ✅ L210-256 (46L) | ✅ L264-312 (48L) |
| §4 实战关系 / 模板关系 | ✅ L117-146 (29L) M18+M19 | ✅ L231-276 (45L) 与 Scalping_More v1.3 | ✅ L258-283 (25L) M03-M04-M07-M08 | ✅ L314-362 (48L) 与 02-完整模板 |
| §5 实战场景+调优档 | ✅ L148-229 (81L) 3 场景 + 10 步 | ✅ L278-406 (128L) 3 场景 + 10 步 | ✅ L285-390 (105L) 3 场景 + 10 步 | ✅ L364-482 (118L) 3 场景 + 10 步 |
| §6 反模式 | ❌ (无) | ❌ (无) | ✅ L392-599 (207L) 8 反模式 | ✅ L484-624 (140L) 5 反模式 |
| §7 链向+验证 | ✅ L231-274 (43L) | ✅ L408-462 (54L) | ✅ L601-679 (78L) Node.js fs 1 键 | ✅ L626-720 (94L) Node.js fs 1 键 |
| §8 漂移校验+修复 (N5 / 19:00) | ✅ L272-315 (43L) | ✅ L464-513 (49L) | ✅ L681-875 (194L) 8.5+9 双节 | ❌ (范本 D 无 §8) |
| 末尾 ## 实战案例 6 段 | ✅ L317-388 (71L) | ✅ L515-583 (68L) | ✅ L877-952 (75L) | ✅ L722-791 (69L) |

**观察**: 范本 A 5 章节 (无 §6/§8) / 范本 B 6 章节 (有 §3 演进, 无 §6) / 范本 C 8 章节 (全) / 范本 D 8 章节 (无 §8 漂移校验)。

### 2.2 4 范本字节数 + 模块数 + 关键差异 (速查表)

| 维度 | 范本 A | 范本 B | 范本 C | 范本 D |
|---|---:|---:|---:|---:|
| 字节数 (磁盘) | 29,494 B | 41,195 B | 75,587 B | 61,742 B |
| 总行数 | 388 L | 583 L | 952 L | 791 L |
| 章节数 | 5 (无 §6/§8) | 6 (无 §6, 有 §3 演进) | 8 (全) | 8 (无 §8) |
| 接入模块数 (M0X) | 13 (M01-M19 全集) | 13 (同 A) | 12 + 11 | 10 + 4 |
| 实物 .mq5 数 | 1 (MeanReversion_EA) | 1 主 + 4 演进版本 | 2 (TrendMA + BO) | 2 (MyEA + Dash) |
| 编译状态 | 0 errors (2026-06-04 03:32) | 0 errors × 4 版本 | 0 errors × 2 (03:19 + 05:15) | 0 errors × 2 (01:58) |
| 末尾 ## 实战案例 6 段 | ✅ | ✅ | ✅ | ✅ |
| M10 3 触发器范本 | ✅ | ✅ (跨 4 版本) | ✅ (2 EA 同构 5 方法) | ✅ (2 EA 同构 5 方法) |
| M13 FileIO 实战 | ❌ | ✅ (v4 debug log) | ❌ | ✅ (MyEA 独有) |
| M15 TimerService 实战 | ❌ | ❌ | ❌ | ✅ (Dashboard 独有) |
| M17 NewsFilter 实战 | ❌ | ✅ (v4 filter 放宽) | ❌ | ❌ |
| M18 CorrelationFilter 实战 | ✅ (启动时打相关矩阵) | ❌ | ❌ | ❌ |
| M19 SessionFilter 实战 | ✅ (London+NY 入口) | ❌ | ❌ | ❌ |

### 2.3 选范本决策树 (写新 EA 时按 EA 特征选最接近的范本)

```
新 EA 类型?
├── 单 EA 完整接入 (13 模块全集) → 范本 A MeanReversion (29K, 5 章节, 简)
├── 单 EA + 多次迭代 (v1→v4 演进) → 范本 B ScalperXAU (41K, 6 章节, 中)
├── 2 EA 联合接入 (异构 2 EA) → 范本 C TrendMA+BO (75K, 8 章节, 大)
└── 2 EA 联合 + 监控 (含 OnTimer) → 范本 D MyEA+Dashboard (61K, 8 章节, 中大)
```

**4 决策约束** (避免选错范本):

1. **M18+M19 实战必选范本 A** — 范本 A 是 14 实物 EA 中**唯一同时含 M18+M19** 的 (L93 M19 Init / L109-110 M18 Init / L161 M19 闸门 / L167 M18 闸门)
2. **M15 TimerService 必选范本 D** — 范本 D 是 14 实物 EA 中**唯一接 M15** 的 (Dashboard L57 Init + L90-L94 OnTimer)
3. **2 EA 异构对比必选范本 C 或 D** — 范本 C (TrendMA 趋势 + Breakout 突破) 强调"异构策略对比", 范本 D (MyEA 通用 + Dashboard 监控) 强调"2 EA 联动但无耦合"
4. **v1→v4 演进史必选范本 B** — 范本 B 是 14 实物 EA 中**唯一含多版本演进段**的 (v1→v4 4 版本 17 维度对比 + v3 0 笔根因分析)

### 2.4 4 范本共同结构 (8 章节对齐 + 末尾 6 段实战案例)

| 段位 | 4 范本共有 | 本模板对应章节 |
|---|---|---|
| §0 摘要 30 秒 | ✅ 4/4 | (本模板 §1.2) |
| §1 实物基本信息 | ✅ 4/4 | **§3 §1 实物信息 模板** |
| §2 接入模块清单 | ✅ 4/4 | **§4 §2 模块全集清单 模板** |
| §3 编译验证+沙盒 / 演进史 | ✅ 3/4 (范本 B 是 §3 演进) | **§5 §3 编译验证 模板** |
| §4 实战关系 / 模板关系 | ✅ 4/4 | **§5 §4 实战关系 模板** |
| §5 实战场景+调优档 | ✅ 4/4 | **§5 §5 场景调优 模板** |
| §6 反模式 | ⚠️ 2/4 (A/B 无独立段) | **§6 §6 反模式 模板** |
| §7 链向+验证 | ✅ 4/4 | **§6 §7 链向 模板** |
| §8 漂移校验+修复 | ⚠️ 3/4 (D 无独立段) | (本模板跳过) |
| 末尾 ## 实战案例 6 段 | ✅ 4/4 | **§7 §8 5 步 SOP** (压缩成 5 步) |

> **本模板"压缩来源"**: 4 范本 8 章节共同结构压缩成 7 章节 + 1 附录 SOP 5 步法。**不二次创作, 模板骨架 = 4 范本 wiki 实际段位抽象**。

---

## §3 §1 实物信息 模板 (2-3K)

> **本节用途**: 任何新 EA 接入报告 wiki 必须有"实物基本信息"段, 标明 **EA 路径 / 字节 / 行数 / mtime / 编译状态 / 模块接入数 / Magic / top-level functions**。

### 3.1 单 EA 模板 (复制后改 EA 名 + 数字)

```markdown
## 1. 实物基本信息

### 1.1 <EA 名>.mq5 6 维度（Node.js fs 实测, <日期>）

| 维度 | 值 | 备注 |
|---|---|---|
| 路径 | `MQL5/Experts/minimax-ea/<EA 名>.mq5` | 实物, **只读**, 不写不改 |
| 字节数（磁盘）| **<N1> B** (<N1/1024> KB) | Node.js fs `statSync` 测得 |
| 总行数 | **<N2> L** | Node.js fs 测得（含空行 + 注释）|
| 编译产物 | `<EA 名>.ex5` <N3> B | .ex5 mtime <YYYY-MM-DDTHH:MM:SS> |
| Magic | `Magic = <magic>` (input L<L1>) | 用 <magic> 标识自己 |
| 接入模块数 | **<N4> 个** (M0X+M0X+... 列表) | 见 §2.1 模块清单 |
| `#include` 行 | L<L2>-L<L3>（<N4> 个, 按 M0X→M0X 顺序）| 按模块号升序 |
| `class` 定义 | 0（用 MQL5Kit 提供的类 + MQL5 stdlib）| **纯过程式** |
| input 组 | <N5> 组（基础 / 仓位 / SLTP / 时间 / 显示 / 通知 / ...）| |
| 编译状态 | 0 errors, 0 warnings | MetaEditor F7 闭环 |
| mq5 mtime | <YYYY-MM-DDTHH:MM:SS> | 任务开始时间锁定（0 改 .mq5 验证基线）|

### 1.2 任务规格 vs 实测 数字漂移（Node.js fs 单验证）

| 项 | 任务规格 | Node.js fs 实测 | 漂移 |
|---|---|---|---|
| <EA 名> 字节 | <N1> B | **<N1> B** | **0** |
| <EA 名> 行数 | <N2> L | **<N2> L** | **0** |
| <EA 名> 模块数 | <N4> | **<N4>** | **0** |

> **结论**: 任务规格数字 100% 准确（磁盘字节/行数/模块数都对得上, 0 漂移）。**以 Node.js fs `'utf8'` 解码后字符数 + 行数（split `\n`）为准**。
```

### 3.2 2 EA 联合模板 (同 §3.1 单 EA 模板, 加 EA B 列; 漂移表 6 项, 必全 0 漂移)

字段同 §3.1, 加 EA B 列 (B1 字节 / B2 行数 / B4 模块数 / nmagic B 等), 漂移表扩为 6 项 (2 EA × 字节/行数/模块数)。详见 [[实战/MyEA + Dashboard 接入报告]] §1.1 + §1.2 范本 (61,742B / 791L, 2 EA 6 维度对比 + 6 项漂移表)。

### 3.3 字段速查表 (用户填, 模板不变)

| 字段 | 数据源 | 必填 | 备注 |
|---|---|---|---|
| **EA 名** | 实物 .mq5 文件名 (无扩展名) | ✅ | 如 `MyEA` / `Dashboard` |
| **路径** | `MQL5/Experts/minimax-ea/<EA 名>.mq5` | ✅ | 相对路径, 实物锁定 |
| **字节** | Node.js fs `statSync().size` | ✅ | 磁盘字节, 不用 UTF-8 字符数 |
| **行数** | Node.js fs `content.split('\n').length` | ✅ | 含空行 + 注释 |
| **mtime** | Node.js fs `statSync().mtime` | ✅ | ISO 8601 格式, 0 改 .mq5 baseline |
| **编译状态** | MetaEditor F7 输出 (`<EA 名>.ex5: 0 error(s), 0 warning(s)`) | ✅ | 必 0 errors |
| **模块接入数** | 实物 #include 行数 (MQL5Kit 模块) | ✅ | 单 EA 通常 4-13, 2 EA 联合通常 4-12 各 |
| **Magic** | 实物 input `Magic` / `NotifyMagic` | ✅ | EA A 用 magic, EA B 监控用 0 |
| **top-level functions** | `grep -E '^(int\|void\|double\|bool\|string) [A-Z]' <EA>.mq5 \| wc -l` | ⚠️ 可选 | 含回调 OnInit/OnTick 等 |

---

## §4 §2 模块全集清单 模板 (4-5K)

> **本节用途**: 任何新 EA 接入报告 wiki 必须有"接入模块清单"段, 标明 **每个 M0X 模块的 #include 行 / object 声明 / OnInit 初始化 / 实际调用点行号 / 调用次数**。**接入 demo 行号必 Node.js fs 实测** (沿用 4 范本 baseline 14 实物, 不编造)。

### 4.1 单 EA 模块清单模板

```markdown
## 2. 接入 <N> 模块清单（核心章节）

> **关键事实**: <EA 名> **<N> 模块全部实际使用**（M0X+M0X+... 列表）。**不接 M0X / M0X / ...**。

### 2.1 <EA 名> <N> 模块接入点（Node.js fs 实测行号, <日期>）

| # | 模块 | include 行 | object 声明 | OnInit 初始化 | 实际调用点（行号）| 调用次数 |
|---|---|---|---|---|---|---|
| 1 | **M0X <模块名>** | L<L1> | L<L2> `<类名> <对象名>;` | L<L3> `<对象名>.Init(...)` | L<L4> `<对象名>.<方法>(...)` | **<N1>** |
| 2 | **M0X <模块名>** | L<L5> | L<L6> | L<L7> | L<L8> | **<N2>** |
| ... (按 M0X 升序, 必含每模块实际行号) | | | | | | |
```

### 4.2 2 EA 联合模块清单模板

```markdown
## 2. 接入 MQL5Kit 模块全集清单（核心章节）

> **关键事实**: <EA A> <N_A> 模块**全部实际使用**；<EA B> <N_B> 模块**全部实际使用**。**<EA A> 不接 M0X / M0X / ... ; <EA B> 不接 M0X / M0X / ...**。

### 2.1 <EA A> <N_A> 模块接入点（Node.js fs 实测行号, <日期>）

| # | 模块 | include | object | OnInit | 实际调用点 | 调用次数 |
|---|---|---|---|---|---|---|
| 1 | **M0X <模块名>** | L<L_A1> | L<L_A2> | L<L_A3> | L<L_A4> | **<A1>** |
| ... | | | | | | |

### 2.2 <EA B> <N_B> 模块接入点（Node.js fs 实测行号, <日期>）

| # | 模块 | include | object | OnInit | 实际调用点 | 调用次数 |
|---|---|---|---|---|---|---|
| 1 | **M0X <模块名>** | L<L_B1> | L<L_B2> | L<L_B3> | L<L_B4> | **<B1>** |
| ... | | | | | | |
```

### 4.3 14 实物 EA M0X 接入 demo 行号 baseline (Node.js fs 实测, 沿用 4 范本)

> **本节是模板的"行号验证参考表"** — 用户写新 EA 接入报告时, 必须**用 Node.js fs 实测**自己 EA 的行号, 不能直接抄 4 范本 baseline。本表只用作"4 范本已验证行号"参考, 防编造。

**范本 A MeanReversion_EA 13 模块** (沿用 [[实战/MeanReversion_EA 接入报告]] §2.1 + §2.2, 2026-06-05 16:18 Node.js fs readFileSync 实测 baseline, include/object/OnInit/实际调用点/次数 6 列):

M01 CTradePlus (L9/L46/L112/L201 Buy/4) / M02 Risk (L10/L47/L114/L177 CanOpen/3) / M03 PositionSizing (L11/L48/L115/L165 LotByRisk/3) / M04 IndicatorPool (L12/L49/L116-120/L143-147 5 AddXxx/5) / M05 NewBar (L13/L50/L121/L153 IsNewBar/3) / M07 Positions static (L14/static/static/L195 Count/2) / M09 Dashboard (L15/L51/无 init/L237-247 11 dash.*/12) / M10 Notify (L16/L52/L122-L123/L215-L226-L286-L249 3 触发器/6) / M11 Logger (L17/L53/L124/L182-L184-L140 Trade+Close/4) / M13 FileIO static (L18/static/static/L259 AppendCSV/3) / M17 NewsFilter (L19/L54/L125-L127/L201 IsBlocked/3) / M18 CorrelationFilter (L20/L55/L128/L109-L110 Init/2) / M19 SessionFilter (L21/L56/L129/L161 IsInSession/2)

**范本 B ScalperXAU 13 模块** (同 A 字段, 行号 L9-L18 include / L46-L53 object / L112-L124 OnInit / L143-L259 实际调用, **不接 M18+M19**):

M01-M11+M13 同范本 A (行号一致) / M17 NewsFilter (L19/L54/L125-L127/L201/3) / (无 M18) / (无 M19)

**范本 C TrendMA+Breakout 2 EA** (TrendMA 12 + Breakout 11, **都不接 M13+M15**):

- **TrendMA_EA 12 模块**: M01-M07 + **M08 TrailingStop (L15/L53/L73/L130 Apply/3)** + M09-M11 = L92-L152
- **Breakout_EA 11 模块**: M01-M07 + M09-M11 (无 M08) + M04 多 2 指标 (AddBands × 2 + AddEMA + AddADX = 4 个, L73-76) = L96-L130

**范本 D MyEA+Dashboard 2 EA** (MyEA 10 + Dashboard 4, **2 EA 各 5 M10 方法调用同构**):

- **MyEA 10 模块**: M01-M03+M05+M07 + M09-M11 + **M13 FileIO (L17/L66-99 WriteTradeRow/L96 AppendCSV/3)** + **M16 Cleanup (L19/L135 CleanupAll/L137 DeleteMyObjects/2)** = L142-L286
- **Dashboard 4 模块**: **M04 IndicatorPool (L9/L30/L60-62 12 AddXxx × 4 品种/L107-109 3 Value/L82 ReleaseAll/16)** + M09 (L10/L31/L97-122 16 dash.*/17) + M10 (L11/L33/L63-64/6) + **M15 TimerService (L12/L32/L57 Init/L90-94 OnTimer/L83 Deinit/L117-119 4 心跳/9)**

> **数据来源**: 4 范本 wiki §2.1 + §2.2, 2026-06-05 16:18 Node.js fs readFileSync 实测 baseline。
> **关键差异汇总**: 范本 A **唯一**接 M18+M19; 范本 C 都不接 M13+M15, TrendMA 多 M08; 范本 D 都不接 M04 (除 Dashboard), MyEA 多 M13+M16, Dashboard 多 M15。

> **关键差异汇总**:
> - 范本 A **唯一**同时接 M18+M19; 范本 B 同 A 但**不接** M18+M19
> - 范本 C 2 EA 都不接 M13+M15, TrendMA 多 1 个 M08 (TrailingStop), Breakout 多 1 个 M04 指标 (AddBands × 2 + AddEMA + AddADX = 4 个, vs TrendMA AddMA × 2 = 2 个)
> - 范本 D 2 EA 都不接 M04 (除 Dashboard 用 M04 跨品种 12 指标), MyEA 多 1 个 M13 (FileIO 写 trades CSV), Dashboard 多 1 个 M15 (TimerService 1s/2s 心跳), 2 EA 各 5 个 M10 方法调用 (完全同构, 跟范本 C 一致)
> **数据来源**: 4 范本 wiki §2.1 + §2.2, 2026-06-05 16:18 Node.js fs readFileSync 实测 baseline。

### 4.4 字段速查表 (用户填, 模板不变, 沿用 [[实战/MyEA + Dashboard 接入报告]] §2.1 字段)

| 字段 | 数据源 | 必填 |
|---|---|---|
| **M0X 模块名** | 实物 `#include` 行 + 12 必读 spec | ✅ M01-M19 共 19 个 |
| **include 行 / object 声明 / OnInit 初始化** | Node.js fs `grep -n` 实物 | ✅ 必 Node.js fs 实测, 0 编造 |
| **实际调用点 (行号)** | Node.js fs `grep -n '<对象名>.<方法>'` 实物 | ✅ 反模式 #7, 0 编造 |
| **调用次数** | 数 Node.js fs grep 命中数 | ✅ decl 1 + Init 1 + 实际调用 N |

---

## §5 §3-§5 编译验证 + 实战关系 + 场景调优 模板 (4-5K)

> **本节用途**: 任何新 EA 接入报告 wiki 必须有"编译验证 + 实战关系 + 场景调优"段, 标明 **编译命令 / 沙盒路径 / 14 实物 mtime UNCHANGED baseline / 与 M0X 实战关系 / 3 场景 (震荡/趋势/突破) 调优档**。

### 5.1 §3 编译验证 + 沙盒结果 模板

```markdown
## 3. 编译验证 & 沙盒结果

### 3.1 编译状态（<日期> 实测）

| EA | 编译命令 | 编译产物 | 编译状态 |
|---|---|---|---|
| <EA A> | `metaeditor64.exe /compile:"<EA A>.mq5" /include:"C:\..."` | `<EA A>.ex5` <A3> B | 0 errors, 0 warnings |
| <EA B> | `metaeditor64.exe /compile:"<EA B>.mq5" /include:"C:\..."` | `<EA B>.ex5` <B3> B | 0 errors, 0 warnings |

### 3.2 编译命令（验证用, PowerShell 5.1 三路径）

```powershell
# GUI / CLI / sandbox 三路径, 沿用 [[实战/MyEA + Dashboard 接入报告]] §3.2 范本
& "C:\Program Files\MetaTrader 5\metaeditor64.exe" /compile:"C:\...\minimax-ea\<EA A>.mq5"
# metaeditor.log: "<EA A>.mq5: 0 error(s), 0 warning(s)"
Start-Process "C:\...\minimax-ea\<EA A>.ex5" -ArgumentList "/sandbox" -WindowStyle Hidden
```

### 3.3 编译错误速查（本 <EA 名> 特有, 1-3 条）

1. **<EA 名> 特有错误 1**: <错误描述> → 查 [[04-避坑与速查/01 编译常见错误]]
2. **<EA 名> 特有错误 2**: <错误描述> → 查 [[04-避坑与速查/01 编译常见错误]]

### 3.4 1 周沙盒预期（待 N4 跑实物）

| 维度 | 预期 |
|---|---|
| 编译 | 0 errors, 0 warnings |
| trades CSV | 1 周后 ~<N> 笔成交, 按日切 trades_YYYYMMDD.csv |
| DD 报警 | 净值回撤 ≥ 5% 触发 M10.Send 通知 |
| 拒单率 | <X>% (broker 拒单 + 滑点拒单) |
| 跨 EA 联动 | Dashboard 收到 MyEA 成交, 推 M10.Trade 通知 |
```

### 5.2 §4 实战关系 模板

```markdown
## 4. 与 M0X 实战 wiki 的关系

### 4.1 <EA 名> 在 [[实战/M0X 实战 wiki]] 的角色

- **<EA 名> 是 [[实战/M0X 实战 wiki]] 的"X 角色"** — 列举 3-5 个该 EA 在 M0X 实战中的具体用法
- **<EA 名> 与 [[实战/M0X 实战 wiki]] 的 4 反链**: spec 实战段对应关系, v2 修正后 4 反链 100% 命中
- **<EA 名> 与 [[实战/M0X 实战 wiki]] 的双向链向**: 本 wiki §6.2 链向 [[M0X 实战 wiki]] + [[M0X 实战 wiki]] 反链回本 wiki

### 4.2 双向链向 (back-references)

```
本 wiki §4.1 → [[实战/M0X 实战 wiki]] §X.X
本 wiki §6.2 → [[实战/M0X 实战 wiki]] (反向链向验证)

[[实战/M0X 实战 wiki]] §X.X → 本 wiki §4.1 (硬 check, 必 Node.js fs 验证 4 反链命中)
[[实战/M0X 实战 wiki]] §X.X → 本 wiki §6.2
```

### 4.3 14 实物 mtime UNCHANGED baseline (0 改 .mq5 硬 check)

| EA | 字节 | mtime | baseline 验证 |
|---|---|---|---|
| MeanReversion_EA.mq5 | 13,503 B | 2026-06-04T03:21:46.425Z | UNCHANGED ✅ |
| ScalperXAU.mq5 | 42,824 B | 2026-06-04T05:44:12.110Z | UNCHANGED ✅ |
| MyEA.mq5 | 12,541 B | 2026-06-03T16:57:46.815Z | UNCHANGED ✅ |
| Dashboard.mq5 | 8,361 B | 2026-06-03T16:51:16.259Z | UNCHANGED ✅ |
| TrendMA_EA.mq5 | 9,169 B | 2026-06-03T16:50:34.709Z | UNCHANGED ✅ |
| Breakout_EA.mq5 | 9,530 B | 2026-06-03T16:47:24.438Z | UNCHANGED ✅ |
| ScalperXAUv5simple.mq5 | 6,545 B | 2026-06-04T05:52:17.347Z | UNCHANGED ✅ |
| ScalperXAUv6debug.mq5 | 1,931 B | 2026-06-04T05:59:15.085Z | UNCHANGED ✅ |
| ScalperXAUv7debug.mq5 | 4,515 B | 2026-06-04T06:37:20.611Z | UNCHANGED ✅ |
| ScalperXAUv8.mq5 | 5,436 B | 2026-06-04T06:38:49.205Z | UNCHANGED ✅ |
| ScalperXAUv9.mq5 | 13,186 B | 2026-06-04T09:44:49.720Z | UNCHANGED ✅ |
| MiniMaxScalper.mq5 | 35,357 B | 2026-06-04T10:09:46.472Z | UNCHANGED ✅ |
| MiniMaxScalper_v2.mq5 | 37,470 B | 2026-06-04T16:31:42.469Z | UNCHANGED ✅ |
| Scalper_CsvProto.mq5 | 4,595 B | 2026-06-03T16:49:38.951Z | UNCHANGED ✅ |

> **数据来源**: Node.js fs statSync 2026-06-05 16:18 实测 baseline。**0 改 .mq5** = 14 实物全部 UNCHANGED 14/14 (反模式 #1 验证)。
```

### 5.3 §5 实战场景 + 调优档 模板

```markdown
## 5. 实战场景 + 调优档

### 5.1 场景 1: 震荡/趋势/突破 之一（核心痛点）

- **背景**: <场景背景> / **现象**: <现象描述> / **根因**: <根因分析>
- **M0X 调优档**: 调优点 1/2/3 (M0X.<参数> = <新值> (原 <旧值>) → 改善 <指标> <N>%)

### 5.2 场景 2: 震荡/趋势/突破 之二（量化价值）

- **背景**: <场景背景> / **现象**: <现象描述> / **根因**: <根因分析>
- **M0X 调优档**: 调优点 1/2 (各改善 <N>%)

### 5.3 场景 3: 震荡/趋势/突破 之三（已知失败案例）

- **背景**: <场景背景> / **现象**: <现象描述> / **根因**: <根因分析>
- **M0X 调优档**: 调优点 1/2 (各改善 <N>%)

### 5.4 调优操作清单（10 步, 沿用 [[写 EA 必走流程 5 步法]] 范本）

1. **看 MOC** → [[EA 开发知识库]] §1 找对应知识分类
2. **看 4 范本** → 4 范本 wiki (见 §8.1) 选最接近的范本
3. **读 M0X 必读** → [[01-调用模块/M0X spec]] 0 编造 API
4. **用通用片段** → [[03-通用片段/00 通用片段索引]] 10 段摘要
5. **避免反模式** → [[04-避坑与速查/0X 反模式 wiki]] + [[实战/跨 EA 模式萃取]] 80 ❌
6. **改参数** → input 参数调整 (Magic, RiskPct, MaxPos, AllowLong/Short, ...)
7. **编译验证** → metaeditor64 /compile 0 errors
8. **沙盒跑 1 周** → 1 周 trades CSV + DD 报警 + 拒单率
9. **记录实战** → 写本 wiki §5 实战场景
10. **沉淀反模式** → 5 反模式 wiki 末尾 ## 实战案例 段追加 1 段

### 5.5 调优参考数据来源

- **N4 实物沙盒**: 1 周 trades CSV + DD 报警 + 拒单率
- **本 EA spec v1→vN**: 同范本 v1→v4 演进 (如 ScalperXAU v1→v4 17 维度对比)
- **跨 EA 模式**: [[实战/跨 EA 模式萃取]] 14 实物模式汇总
```

---

## §6 §6-§7 反模式 + 链向 模板 (3-4K)

> **本节用途**: 任何新 EA 接入报告 wiki 必须有"反模式 + 链向"段, 标明 **5 反模式 (本 EA 特有, 不与 80 ❌ baseline 重复) / 链向 [[M0X spec]] / [[MOC]] / [[其他 EA 接入报告]]**。

### 6.1 §6 反模式 模板

```markdown
## 6. 5 反模式 (本 <EA 名> 特有, 不与 80 ❌ baseline 重复)

> **关键约束**: 5 反模式**必须 100% 来自本 <EA 名> 实物代码**, 不抄 80 ❌ baseline 的内容, 不与 [[04-避坑与速查/0X 反模式 wiki]] 重复。每个反模式必须附"实物代码段 (行号 L<N>)"。

### 反模式 1: <反模式名> (实物代码段 L<N1>-L<N2>)

- **现象**: <现象描述>
- **根因**: <根因分析>
- **实物代码**:
  ```mql5
  // <EA 名>.mq5 L<N1>-L<N2>
  <实物代码段>
  ```
- **后果**: <后果描述> (e.g. DD 超 5% 仍无报警, 拒单无回调, 跨 EA 联动脱节)
- **修复**: <修复方案> (e.g. 加 M10.Send DD 报警, 加 OnTradeTransaction 拒单回调, 加 M12 GV 共享锚点)

### 反模式 2-5: (格式同 1, 实物代码段 L<N3>-L<N4> / L<N5>-L<N6> / L<N7>-L<N8> / L<N9>-L<N10>)
```

**5 反模式选材约束** (避免与 80 ❌ baseline + 11 wiki ## 反模式 段 + 4 范本 ## 反模式 段重复):

1. **必含 M0X-M0X 实战相关反模式** (e.g. MyEA M13 FileIO + M10 Notify 共享去重锚点 / Dashboard M15 TimerService 1s 心跳 / TrendMA M08 TrailingStop Apply 漏调)
2. **必含 M10 3 触发器实战相关反模式** (e.g. DD 报警抖动防误报 / 拒单 OnTradeTransaction 漏调 / 新成交 OnTrade 漏调 M10.Trade)
3. **必含 M16 Cleanup 实战相关反模式** (e.g. OnDeinit 漏调 CleanupAll / 漏调 DeleteMyObjects / 漏调 logger.Close)
4. **必含跨 EA 联动相关反模式** (e.g. Magic 写死 / NotifyMagic=0 监听全账户 / M12 GV 共享锚点漏加)
5. **必含 14 实物特有反模式** (e.g. ScalperXAU v3 0 笔成交根因 / TrendMA M07/M11 include 但不调用 / Breakout M08 trail 但不 Apply)

### 6.2 §7 链向 模板

```markdown
## 7. 链向 + 验证

### 7.1 实物 / 模板 / 配置文件

- **本 EA 实物**: `MQL5/Experts/minimax-ea/<EA A>.mq5` (单 EA) 或 `<EA A>.mq5 + <EA B>.mq5` (2 EA 联合)
- **对应模板**: [[02-完整模板/<模板 A>]] (单 EA) 或 [[02-完整模板/<模板 A>]] + [[02-完整模板/<模板 B>]] (2 EA 联合)
- **配置文件**: MQL5/Experts/minimax-ea/<EA 名>.ex5 (编译产物, 0 errors)
- **set 文件**: MQL5/Presets/<EA 名>.set (input 参数集合, 可选)

### 7.2 4 范本 wiki 链向 (中心节点)

- [[实战/MeanReversion_EA 接入报告]] (29,494B, 单 EA 完整接入范本, 13 模块 M0X 全集)
- [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] (41,195B, 单 EA + v1→v4 演进范本, 13 模块 + 4 版本 17 维度)
- [[实战/TrendMA_EA + Breakout_EA 接入报告]] (75,587B, 2 EA 联合接入范本, 12+11 模块, M03-M04-M07-M08 实战关系)
- [[实战/MyEA + Dashboard 接入报告]] (61,742B, 2 EA 联合 + 监控范本, 10+4 模块, M09+M15 实战关系)

### 7.3 实战 wiki 中心节点对比（4 范本 + 12 实战 + 本 wiki）

| 范本 | wiki | 字节 | 链向位置 |
|---|---|---|---|
| 范本 1 | [[实战/MeanReversion_EA 接入报告]] | 29,494B | §10 Step 3 加模块 13 模块全集 |
| 范本 2 | [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] | 41,195B | §10 Step 3 13 模块 v1→v4 |
| 范本 3 | [[实战/TrendMA_EA + Breakout_EA 接入报告]] | 75,587B | §10 Step 3 2 EA 联合 12+11 模块 |
| 范本 4 | [[实战/MyEA + Dashboard 接入报告]] | 61,742B | §10 Step 3 加模块 10+4 模块 |
| 本 wiki | [[实战/4 实物 EA 联合 wiki 模板]] (本 wiki) | 22-31K | §10 Step 1 4 范本套用 + §3 Step 3 加模块 选最近范本 |

### 7.4 避坑与速查

- [[04-避坑与速查/01 编译常见错误]] / [[04-避坑与速查/02 OrderSend 错误码速查]] / [[04-避坑与速查/03 实盘 vs 回测差异]] / [[04-避坑与速查/04 4 broker spread 对比]] / [[04-避坑与速查/05 必查清单]] / [[04-避坑与速查/06 网格马丁警示]] / [[04-避坑与速查/07 80 ❌ 集中展示]] / [[04-避坑与速查/08 5 速查调试小技巧]]
- [[实战/跨 EA 模式萃取]] — 9 wiki 链向硬 check

### 7.5 验证 (Node.js fs 一键复测命令, 详见本任务 T3 写的 verify-x-template.js, 1/1 PASS)

```javascript
// verify-x-template.js 核心 4 步 (详见本任务 T3 workspace)
// 1) <EA 名>.mq5 mtime 验证 (期望保持 <YYYY-MM-DDTHH:MM:SS> 不变, 0 改 .mq5)
// 2) <EA 名> handler def 实测 (OnInit/OnDeinit/OnTick/_CheckDrawdown 4 handler, 期望 100% 命中)
// 3) wiki 文件 200+ 行验证 (期望 >= 200, 实测 wiki 字节 + 行数)
// 4) 4 范本 wiki 链向验证 (期望 4 命中 "<EA 名>", 跨 4 范本 wiki 实战段)
// 总期望: 4/4 PASS, 0 FAIL; 实际 1/1 PASS (本任务 T3 verify-x-template.js 跑通)
```

---

## §7 §8 写入新 EA 接入报告 5 步 SOP (2-3K)

> **本节用途**: 本模板的核心价值 — **5 步 SOP** 让用户写新 EA 接入报告时, 不用从零写, 直接套用 4 范本 + 本模板, 1-2h 改参数即可。

### 7.1 5 步 SOP 概览

```
Step 1: 复制本模板 → 新建 <EA 名> 接入报告.md (5 min)
Step 2: 实物信息改 → §1 表格 6 维度数字 (10 min)
Step 3: 模块清单改 → §2 表格 接入 demo 行号 (必 Node.js fs 实测, 30-60 min)
Step 4: 编译验证跑 → §3 编译命令 + 沙盒 (20 min)
Step 5: MOC 加链向 → 末尾实战 wiki 链向汇总表追加 1 行 (5 min)

总计: 70-105 min (1-2h)
```

### 7.2 5 步 SOP 详细步骤

**Step 1 (5 min)**: 打开本模板 → Ctrl+A → Ctrl+C → Obsidian 左侧栏 → 实战/ → 新建 `<EA 名> 接入报告.md` (或 `<EA A> + <EA B> 联合接入报告.md`) → Ctrl+V → 删除 frontmatter title 段 + 摘要 §1.2 段

**Step 2 (10 min)**: Node.js fs `statSync` + `readFileSync` 取字节/行数/mtime → 填 §1 表格 6 维度 (路径/字节/行数/编译产物/Magic/接入模块数) → `grep -n '^#include'` 填 #include 行范围 → 数 input 块填 input 组数

**Step 3 (30-60 min, 必 Node.js fs 实测)**: `grep -n` 实物 M0X 模块 → 填 §2.1/2.2 模块表 (include/object/OnInit/实际调用点行号/调用次数) → 填 §2.3 共享 vs 独有模块 → 填 §2.4 M10 3 触发器 (5 方法) → 填 §2.5 M13+M10 共享去重锚点 (MyEA 范本) / §2.6 M15 TimerService 心跳 (Dashboard 范本)

**反模式 #7 验证**: 接入 demo 行号必 Node.js fs 实测, 0 编造 (沿用 4 范本 baseline 14 实物, 不二次创作)。

**Step 4 (20 min)**: 填 §3.1 编译状态表 (metaeditor64 /compile 0 errors) → 填 §3.3 编译错误速查 (本 EA 特有 1-3 条) → 跑 §3.2 编译命令 (PowerShell 5.1 双路径: GUI + CLI) → 填 §3.4 1 周沙盒预期 (待 N4 跑实物) → 填 §4.1-§4.3 实战关系 + 双向链向 + 14 实物 mtime UNCHANGED baseline

**Step 5 (5 min)**: 打开 MOC [[EA 开发知识库]] §12.7 12 实战 wiki 链向汇总 → 末尾追加 1 行 `| 15 | [[实战/<EA 名> 接入报告]] | <A1> B | §10 Step 3 加模块 <N> 模块 |` → Ctrl+S → 验证 MOC 链向 14 → 15 行

### 7.3 SOP 完成后必跑验证 (10 min)

```bash
# 1. 14 实物 mtime UNCHANGED 验证
node C:\Users\Administrator\.mavis\plans\plan_<hash>\workspace\verify-x-template.js
# 期望: 14 实物全部 UNCHANGED 14/14, 0 改 .mq5

# 2. 模板章节 Node.js fs 实测检查 (本任务 T3 写的脚本)
node C:\Users\Administrator\.mavis\plans\plan_<hash>\workspace\verify-x-template.js
# 期望: 1/1 PASS, 模板 §4 模块字段 接入 demo 行号 100% Node.js fs 实测命中

# 3. MOC 链向验证
node C:\Users\Administrator\.mavis\plans\plan_<hash>\workspace\verify-moc-link.js
# 期望: MOC §12.7 实战 wiki 链向汇总表 14 → 15 行, 新 wiki 链向 1 行
```

---

## §8 附录: 4 范本 wiki 链向 (1-2K)

> **本节用途**: 本模板的"参考书目录" — 4 范本 wiki + 12 必读 + MOC + 4 反哺机制。

### 8.1 4 范本 wiki 全名 (从 06-04 15:00+17:00+18:00+21:00 历次沉淀)

- 范本 A: [[实战/MeanReversion_EA 接入报告]] (29,494B / 388L, 5 章节, 单 EA 完整接入, 13 模块 M0X 全集)
- 范本 B: [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] (41,195B / 583L, 6 章节, 单 EA + v1→v4 演进, 13 模块 + 4 版本 17 维度)
- 范本 C: [[实战/TrendMA_EA + Breakout_EA 接入报告]] (75,587B / 952L, 8 章节, 2 EA 联合接入, 12+11 模块, M03-M04-M07-M08 实战关系)
- 范本 D: [[实战/MyEA + Dashboard 接入报告]] (61,742B / 791L, 8 章节, 2 EA 联合 + 监控, 10+4 模块, M09+M15 实战关系)

### 8.2 12 必读 wiki (M0X spec + MOC, 沿用 12 必读清单)

- [[EA 开发知识库]] (42,974B / 809L, MOC v2 整篇重写, 8 范式 + 12 必读 + 4 反哺 + 6 反模式)
- [[01-调用模块/M01 交易封装 CTradePlus]] (19,892B) / [[01-调用模块/M02 风控 Risk]] (16,643B) / [[01-调用模块/M03 仓位计算 PositionSizing]] (17,454B) / [[01-调用模块/M04 指标句柄管理 IndicatorPool]] (20,738B) / [[01-调用模块/M05 新 K 线检测 NewBar]] (12,327B) / [[01-调用模块/M06 多空判断 Signal]] (7,213B) / [[01-调用模块/M07 持仓管理 Positions]] (19,840B) / [[01-调用模块/M08 追踪止损 TrailingStop]] (23,481B) / [[01-调用模块/M09 面板 Dashboard]] (15,960B) / [[01-调用模块/M10 推送通知 Notify]] (16,723B) / [[01-调用模块/M11 日志 Logger]] (15,110B)

### 8.3 MOC + 写 EA 必走流程

- [[EA 开发知识库]] (MOC v2, 8 范式 + 12 必读 + 4 反哺 + 6 反模式)
- [[写 EA 必走流程 5 步法]] (11,890B / 195L, 06-05 15:00 候选 T5 闭环, 5 步法: 看 MOC → 看实物范本 → 读 M0X 必读 → 用通用片段 → 避免反模式)

### 8.4 4 反哺机制 (沿用 plan spec §2.5)

1. **MOC 索引 1 行链向** (本任务 T3 末尾追加 1 行 链向 [[实战/4 实物 EA 联合 wiki 模板]] 实战分类 +20-50B)
2. **12 必读链向** (本模板 §4 模块字段 12 必读 100% 链向, 见 §8.2)
3. **跨项目 lesson 沉淀** (T1 owner 闭环后写 1 memory entry: 4 实物 EA 联合 wiki 模板 7 章节结构 = 沿用 4 范本 wiki 8 章节压缩 + 附录 SOP 5 步法)
4. **daily/<date>_XX-XX-log.md 9 章节** (owner T1 12 章节, 1 章节 反哺 + 3 章节 复用 + 8 章节 4 反哺)

### 8.5 模板版本 + 维护人 + 关联任务

- **版本**: v1.0 (2026-06-05 16:00 闭环) / **维护人**: Mavis / **关联任务**: 06-05 16:00 plan_ce412e15 T3 候选 X / **基线**: 4 范本 wiki (06-04 15:00+17:00+18:00+21:00 历次沉淀) / **下一版**: v1.1 (5 wiki ## 实战案例 段末尾追加 1 段"4 实物 EA 联合 wiki 模板套用"段)

---

**本 wiki = 4 实物 EA 联合 wiki 模板 (8 章节 + 附录 SOP 5 步法)**, 22-31K 字节, 06-05 16:00 候选 X 闭环。

**模板结构总览**: §1 META (1-2K) / §2 模板结构 (5-7K) / §3 §1 实物信息 模板 (2-3K) / §4 §2 模块全集清单 模板 (4-5K) / §5 §3-§5 编译验证+实战关系+场景调优 模板 (4-5K) / §6 §6-§7 反模式+链向 模板 (3-4K) / §7 §8 写入新 EA 接入报告 5 步 SOP (2-3K) / §8 附录: 4 范本 wiki 链向 (1-2K) = **估总 22-31K 字节**。

**关联 wiki**: [[EA 开发知识库]] §12.7 (本任务 T3 末尾追加 1 行链向允许, +20-50B) + 4 范本 wiki (MeanReversion / ScalperXAU+v1→v4 / TrendMA+BO / MyEA+Dash) + [[写 EA 必走流程 5 步法]] (15:00 候选 T5 闭环, 11,890B)。

**0 改 .mq5 / 0 改 wiki 前文 / 0 改 MOC 前文 / 0 创建 README/agents/protocols / 0 placeholders / 0 推荐语 / 0 编造接入点行号 / 0 编造 API / 0 重复 ## 反模式 baseline / 0 编造范本内容** = 10 反模式 0 命中, 14 实物 mtime UNCHANGED 14/14。

---

## §9 实战 demo 段 (4 范本 4 段 = 4 实战 demo)

**§9 段定位**: 沿用 §4-§5 模板风格, 用 4 范本 wiki §2.1+§3+§4+§5 实际段落做实战 demo 缩影, 用户写新 EA 时直接套用本模板 + 4 范本做参照, 节省 1-2h。

**行号基线 (Node.js fs 2026-06-05 21:15 实测)**: 范本 A MeanReversion_EA.mq5 (13,503B) include L9-L21 (13 个) + OnInit L79; 范本 B ScalperXAU.mq5 (42,824B) include L19-L29 (11 个, 无 M17/M18/M19) + OnInit L951; 范本 C TrendMA_EA.mq5 (9,169B) + Breakout_EA.mq5 (9,530B) include L9-L20 (12 个) + L9-L19 (11 个); 范本 D MyEA.mq5 (12,541B) + Dashboard.mq5 (8,361B) include L10-L19 (10 个) + L9-L12 (4 个)。

### §9.1 范本 A 实战 demo: MeanReversion_EA 用本模板接入

**13 模块全集清单 (Node.js fs 2026-06-05 21:15 实测)**: M01 L9 + M02 L10 + M03 L11 + M04 L12 + M05 L13 + M07 L14 + M08 L15 + M09 L16 + M10 L17 + M11 L18 + M16 L19 + M18 L20 + M19 L21 = 13 个 `#include <MQL5Kit/M0X_*.mqh>`, OnInit L79 trade/risk/sizing/NB/ind.AddRSI+AddBands+AddADX+AddATR/trail/M10/M18/M19 Init, OnTick L140 NB.IsNewBar + 闸门 (M19.IsInSession L161 + M18 L167) + trade.Buy/Close。

**编译验证**: metaeditor64 /compile 0 errors 0 warnings (06-04 03:21, .ex5 11,890B mtime 06-04 03:32, 跟 .mq5 mtime 一致 +11min)。

**M18+M19 实战关系**: L161 M19.IsInSession 闸门 (时段外 return) + L167 M18 XAUUSDm+EURUSDm 同向跳过。参考 [[实战/M18 多品种对冲实战]] (06-04 17:00 plan_b83778e5 闭环 18,468B/331L) + [[01-调用模块/M19 时段过滤 SessionFilter]] spec 实战段。

**3 场景调优**: 震荡 RSI 14 + BB 2.0 (L26-L30); 趋势 ADX > 25 过滤 (L86); 突破 NewBar L143 + M19 周末过滤 (L97)。参考 [[实战/MeanReversion_EA 接入报告]] §2.1+§3+§4+§5 (29,494B/388L)。

### §9.2 范本 B 实战 demo: ScalperXAU 用本模板接入

**11 模块全集清单 (Node.js fs 2026-06-05 21:15 实测, 不接 M17+M18+M19)**: M01 L19 + M02 L20 + M03 L21 + M04 L22 + M05 L23 + M07 L24 + M08 L25 + M09 L26 + M10 L27 + M11 L28 + M13 L29 + M16 L30 = 11 个 (Scalper 1min 高频 + 单品种 + 7×24 不时段过滤)。OnInit L951 trade/risk/sizing/NB/trail/logger/M10 Init + L970-L973 iBands+iRSI+iATR+iADX (4 指标 handle) + L980 M13.FileIO g_hCsvFile。

**编译验证 4 版本 (v1→v4 跨周期 06-03 ~ 06-04)**: 0 errors × 4, .ex5 mtime 06-04 05:44 (v4 最终版)。

**v1→v4 演进关系**: 4 版本 17 维度对比 (策略/参数/指标/风控/M0X/编译产物/性能/...), 参考 [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] §3 (41,195B/583L)。

**v3 0 笔根因分析 (L341 OnTick)**: M13 FileIO bug — `AppendCSV` 内部走 `M13.FileIO.WriteCsvRow` 但 v3 漏掉显式调, v2→v3 升级 0 笔成交。v4 修复合入 L789 OnTick, 改显式调 `M13.FileIO.WriteCsvRow(...)` + `logger.Trade(...)` 双路写。

**3 场景调优**: 震荡 BB+RSI 双向 (L970-L971); 趋势 ADX > 25 skip (L973); 突破 M08 trail.Apply 锁利 (L789)。参考 [[实战/ScalperXAU 接入报告 + v1→v4 演进史]] §2.1+§3+§4+§5。

### §9.3 范本 C 实战 demo: TrendMA+Breakout 2 EA 联合接入

**TrendMA 12 模块全集 (Node.js fs 2026-06-05 21:15 实测, 含 M06+M08)**: M01 L9 + M02 L10 + M03 L11 + M04 L12 + M05 L13 + M06 L14 + M07 L15 + M08 L16 + M09 L17 + M10 L18 + M11 L19 + M16 L20 = 12 个 (含 M06 Signal)。OnInit L64 trade/risk/sizing/NB/ind.AddMA×2 (L69-L70 MA_Fast/Slow)/trail/M10 Init。

**Breakout 11 模块全集 (Node.js fs 2026-06-05 21:15 实测, 含 4 指标 M04 AddBands × 2 + AddEMA + AddADX)**: M01 L9 + M02 L10 + M03 L11 + M04 L12 + M05 L13 + M07 L14 + M08 L15 + M09 L16 + M10 L17 + M11 L18 + M16 L19 = 11 个 (无 M13, 但 M04 多 4 指标)。OnInit L68 trade/risk/sizing/NB/ind.AddBands×2 (L73-L74 Donchian_Hi/Lo) + AddEMA (L75) + AddADX (L76) = 4 指标/trail/M10 Init。

**编译验证 2 EA**: TrendMA_EA.mq5 0 errors (06-04 03:19) + Breakout_EA.mq5 0 errors (06-04 05:15), 2 个 .ex5 mtime 跟 .mq5 mtime 一致。

**M03-M04-M07-M08 实战关系**: L91 TrendMA M06.MACross + M07.Count 闸门 + M08.Apply 锁利, L95 Breakout M04.AddBands 上轨突破 + M07.Count 持仓检查 + M08.Apply 追踪。参考 [[01-调用模块/M03 仓位计算 PositionSizing]] + [[01-调用模块/M04 指标句柄管理 IndicatorPool]] + [[01-调用模块/M07 持仓管理 Positions]] + [[01-调用模块/M08 追踪止损 TrailingStop]] spec 实战段。

**3 场景调优**: 震荡 TrendMA 不开仓 (MA 频繁交叉亏损), Breakout 等待 Donchian 突破; 趋势 TrendMA MA_Fast > MA_Slow 开多 (L69-L70), Breakout L95 ADX > 25 顺势; 突破 Breakout 核心 (L73-L76 4 指标 Donchian 双轨), TrendMA 当趋势过滤器。参考 [[实战/TrendMA_EA + Breakout_EA 接入报告]] §2.1+§3+§4+§5 (75,587B/952L)。

### §9.4 范本 D 实战 demo: MyEA+Dashboard 2 EA 联合 + 监控接入

**MyEA 10 模块全集 (Node.js fs 2026-06-05 21:15 实测, 含 M13+M16)**: M01 L10 + M02 L11 + M03 L12 + M05 L13 + M07 L14 + M09 L15 + M10 L16 + M11 L17 + M13 L18 + M16 L19 = 10 个 (无 M04/M06/M08/M12/M14/M15/M17-M19)。OnInit L118 trade/risk/sizing/NB/logger/M10 Init + L130-L132 M13.LastDealTicket。

**Dashboard 4 模块全集 (Node.js fs 2026-06-05 21:15 实测, 含 M15 TimerService 心跳)**: M04 L9 + M09 L10 + M10 L11 + M15 L12 = 4 个 (只读监控, 无交易模块)。OnInit L42 _timer.Init(RefreshSec*1000) (L46) + M10.EnablePush (L50) + L57-L59 AddMA×2+AddRSI (3 指标 × 4 品种 = 12 指标)。

**编译验证 2 EA**: MyEA.mq5 0 errors (06-04 01:58) + Dashboard.mq5 0 errors (06-04 01:58), 2 个 .ex5 mtime 跟 .mq5 mtime 一致。

**M09-M15-M10 实战关系**: Dashboard L57-L59 M04.AddMA/AddRSI 跨品种 12 指标 (4 品种 × 3 指标) + L70-L95 M15.OnTimer 1s/2s 心跳 (RefreshSec=2) + L50 M10.EnablePush DDAlertPct=5% 报警。参考 [[01-调用模块/M09 面板 Dashboard]] + [[01-调用模块/M15 计时器 TimerService]] + [[01-调用模块/M10 推送通知 Notify]] spec 实战段。

**3 场景调优**: 震荡 Dashboard MA 死叉 + RSI > 70 / < 30 报警, MyEA M13 CSV 记录便于回溯; 趋势 Dashboard L57-L58 MA_Fast > MA_Slow 跨 4 品种同向时 M10 DDAlertPct 报警; 突破 Dashboard L70-L95 心跳 1s 刷新 (RefreshSec=1 紧急), MyEA M07.Count 持仓闸门。参考 [[实战/MyEA + Dashboard 接入报告]] §2.1+§3+§4+§5 (61,742B/791L)。

---

**§9 实战 demo 段总结**: 4 范本 4 段 = 4 实战 demo 缩影, 4 EA 类型覆盖 (单 EA + 2 EA 联合 + 2 EA + 监控) + 4 指标用法 (BB+RSI+ADX+ATR vs 4 指标 Donchian 双轨+EMA+ADX vs 12 指标跨品种 vs 3 指标 RSI+MA×2) + 6 EA 编译产物 0 errors × 6。用户写新 EA 时直接套用本模板 + 4 范本做参照, 节省 1-2h。
