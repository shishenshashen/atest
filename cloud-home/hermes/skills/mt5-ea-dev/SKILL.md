---
name: mt5-ea-dev
description: MT5 EA (MQL5) 开发知识库。提供 8 范式 / 12 必读（M01-M19）/ 4 实物范本 / 5 步法 / 6 反模式 / 8 性能维度 / 4 异常维度的懒加载索引 + 实时查询 vault。trigger: 老大说 EA/MT5/MQL5/EA开发/写EA/编译/编译报错/反模式/性能调优 任何关键词必加载。
version: 1.0
author: 小神龙
created: 2026-06-11
---

# mt5-ea-dev skill v1

**vault 真实位置**：`C:\ai\obsidian-文件\mt\EA开发\`（342 个 .md，**不**复制到 skill，全部懒加载）

**核心哲学**（与 task-queue 一致）：**0 编造**——所有 API/行号/字节数必从 vault 读，**绝不**靠记忆生成。

---

## ⚠️ 强制行为规则

1. **API/行号/字节数 必查 vault**——`{vault}/EA开发/01-调用模块/M0X *.md` 或 `verifier_check.js` / `verify_antipatterns.js`
2. **报"找不到"比编好**——vault 查不到就说"没找到",**不**凭印象写
3. **跨会话缓存**——`~/.hermes/mt5-ea-dev/cache/` 缓存最近 50 次查询（避免每次重读大文件）
4. **改 vault 后必跑 `cache_clear`**——`python ~/.hermes/skills/mt5-ea-dev/cache.py clear`

---

## 文件结构

```
~/.hermes/skills/mt5-ea-dev/
├── SKILL.md          (本文件)
├── index.py          (索引查询入口)
├── queries.py        (查询函数: 必读/范本/反模式/性能)
├── cache.py          (查询缓存)
└── templates/
    ├── 写EA-5步法.md
    └── EA接入报告-模板.md
```

---

## 8 范式（MOC 总入口）

来源：vault `EA开发/EA 开发知识库.md` (44KB, 70 wiki 链向)

| # | 范式 | 入口 |
|---|---|---|
| 1 | **写 EA 入口** | 找对应知识分类 (eg. 逆势均值回归 → 12 必读 M01-M19 选) |
| 2 | **模板套用** | 8 模板 (通用骨架 / MA 交叉 / RSI Bollinger / Donchian / 网格马丁 / 剥头皮 / 多品种对冲 / Dashboard) |
| 3 | **模块调用** | 12 必读 M01-M19 + MQL5Kit 19 模块 |
| 4 | **通用片段** | 4 片段 (01 下单 / 02 读取 / 03 画图(EA跳过) / 04 实用函数) 10 段 |
| 5 | **反模式避坑** | 5 速查 wiki + 9 反模式 wiki + 80 ❌ 集中 |
| 6 | **性能调优** | `EA开发/性能调优/MT5 性能调优 wiki.md` (8 维度 × 19 模块) |
| 7 | **异常处理** | `EA开发/异常处理/异常处理手册.md` (4 异常维度 × 19 模块) |
| 8 | **高级设计** | `EA开发/05-高级设计模式/高级 EA 设计模式 wiki.md` (7+1 模式 6 章节) |

---

## 12 必读（核心 API 来源）

来源：`EA开发/01-调用模块/M0X *.md`

| # | 模块 | 关键 API |
|---|---|---|
| M01 | 交易封装 CTradePlus | Init / Buy / Sell / ClosePos |
| M02 | 风控 Risk | CanOpen(type, lot, sl, tp) |
| M05 | 新 K 线检测 NewBar | IsNewBar() 单线 demo |
| M08 | 追踪止损 TrailingStop | SetParams(start, step, minGap) + Apply() |
| M09 | 面板 Dashboard | Row(...) + Show() + Refresh() |
| M10 | 推送通知 Notify | Send(msg, highPriority) / Trade / Alert |
| M11 | 日志 Logger | Info/Warn/Error/Trade 4 级别 |
| M13 | 文件 IO | CFileIO::AppendCSV(fileName, fields) |
| M17 | 新闻过滤 NewsFilter | IsNearEvent(±min, _Symbol) + LoadFromCSV() + 6 自检 |
| M18 | 相关性过滤 CorrelationFilter | IsHedgeExposed / thr= 阈值 (0.6/0.7/0.8) |
| M19 | 时段过滤 SessionFilter | 4 预定义常量 (Asia/London/NY/Off) + NY:22-6 跨午夜 |

---

## 4 实物范本（复制改参数）

| 范本 | 路径 | 字节 | 适用 |
|---|---|---|---|
| **A** (单 EA) | `EA开发/实战/MeanReversion_EA 接入报告.md` | 17.7K | 单 EA (XAUUSDm 逆势均值回归) |
| **B** (单 EA 演进) | `EA开发/实战/ScalperXAU 接入报告 + v1→v4.md` | 29.8K | 单 EA 演进 (XAUUSDm 剥头皮 v1→v4) |
| **C** (2 EA 联合) | `EA开发/实战/TrendMA_EA + Breakout_EA 接入报告.md` | 40.4K | 趋势 + 突破 互补 |
| **D** (2 EA + 监控) | `EA开发/实战/MyEA + Dashboard 接入报告.md` | 53.9K | 2 EA + Dashboard |

**操作 SOP**：复制最接近范本 → 改实物信息（EA 名/路径/字节/行数/mtime）→ 改模块清单（**必 Node.js fs 实测**）→ 编译验证 → MOC 加链向。

---

## 5 步法（写 EA 必走）

来源：`EA开发/写 EA 必走流程 5 步法.md`

1. **看 MOC**（总入口）→ 找知识分类
2. **看 4 范本** → 选最接近，1-2h 改参数
3. **读 12 必读** → 0 编造 API（必先 grep wiki）
4. **用 4 片段** → 不重复造轮子
5. **避 5 速查 + 9 反模式 + 80 ❌**

**漏一步出错**。

---

## 反模式 + 性能 + 异常索引

- **5 速查 wiki**：`EA开发/04-避坑与速查/0[1-5] *.md`
- **9 反模式 wiki**：从 11 实物 EA 萃取的 80 ❌
- **8 性能维度** × **19 模块段位**
- **4 异常维度** × **19 模块段位**

---

## verifier 工具

- `C:\ai\obsidian-文件\mt\verifier_check.js`（2.3KB）— 检查 EA 接入报告结构
- `C:\ai\obsidian-文件\mt\verify_antipatterns.js`（790B）— 反模式扫描

---

## 父级 agent 必走

```python
import sys
sys.path.insert(0, r"C:\Users\Administrator\.hermes\skills\mt5-ea-dev")
from queries import get_module_api, get_antipattern, get_template

# 1) 查 M08 追踪止损 API（0 编造）
api = get_module_api("M08")
print(api["key_apis"])  # SetParams(start, step, minGap) + Apply()
print(api["demo_line"]) # MeanRev L341

# 2) 查"网格马丁"反模式
ap = get_antipattern("grid_martin")
print(ap["description"], ap["wiki_link"])

# 3) 查最接近的范本
tmpl = get_template("剥头皮")  # 命中 ScalperXAU
print(tmpl["path"])  # EA开发/实战/ScalperXAU 接入报告 + v1→v4.md
print(tmpl["size"])  # 29.8K
```

---

## 验收标准

- [ ] 任意 M0X 必读模块查询命中 vault 真实路径
- [ ] 反模式/性能/异常查询返回真实 wiki 链向
- [ ] 4 范本查询返回真实路径+字节
- [ ] 5 步法渲染可读
- [ ] 缓存命中率 > 30%（避免每次重读大文件）
- [ ] 任何"找不到" → 立即报错不编

---

## ⚠️ 老大注意

**memory 里我之前把这个 vault 叫"MT5 EA 知识库"是简写**，**实际**它还有 **minimaxcode 知识库**（Mavis/CU 自动化方向）。EA 开发是其中一个子目录。

写 EA 相关的活（编译报错、反模式、接入报告）→ 走本 skill（mt5-ea-dev）。
写 Mavis/CU 自动化相关的活 → 走 minimaxcode 知识库（**还没做 skill**，待办）。
