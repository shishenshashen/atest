---
title: MT5 GUI 自动化 5 次失败全记录 + 分工协议
tags: [踩坑, GUI, 自动化, MT5, UIPI, session, 分工]
type: postmortem
---

# MT5 GUI 自动化 5 次失败全记录 + 最终分工

> **结论**：MT5 GUI backtest **无法用任何工具自动跑** (RDP/console session 隔离 + UIPI + Windows desktop isolation)。
> **最终分工**：Mavis 写 mql5 + 编译；用户 GUI 跑 backtest + 传结果。

## 5 次尝试全失败

### 1. metatester64.exe CLI 启动
- **预期**：terminal64/metatester64 启时跑 backtest
- **实测**：CPU 0%、60s 无进展、IPC dispatcher not started
- **失败原因**：挂死, 不写 report
- **沉淀日期**：2026-06-03

### 2. PowerShell SendKeys 跨进程
- **预期**：从 session 2 启 powershell, focus MT5 + SendKeys ctrl+r
- **实测**：`SendWait` 抛 "拒绝访问" 
- **失败原因**：**UIPI** 拦 input, session 2 进程不能向 console 1 desktop 注入 input
- **沉淀日期**：2026-06-03

### 3. Mavis CU MCP desktop_*
- **预期**：用 `desktop_window_focus` + `desktop_key` 操控 MT5
- **实测**：focus 返成功但不真切, ctrl+r 没效果, screenshot 间歇 "Failed to capture screen"
- **失败原因**：CU 进程 (Mavis daemon) 在 session 2, nut.js native binding 跨不过 UIPI / desktop boundary
- **沉淀日期**：2026-06-04

### 4. Mavis mcp mt5_run_backtest 9 GUI stub
- **预期**：mcp-mt5 server 提供的 9 个 GUI 工具
- **实测**：9 个工具全 `not_yet_implemented`
- **失败原因**：GUI stub 没实现
- **沉淀日期**：2026-06-04

### 5. driver + trigger (named pipe)
- **预期**：用户在 console 1 启 driver, Mavis trigger 它做 SendKeys
- **实测**：
  - driver **自报 sessionId=2** (用户实际在 RDP 2 启, 不是物理 console 1)
  - 即使切到 console 1 启, SendKeys **理论上**通 (同 desktop), 但**用户没在 console 1 启**
- **失败原因**：用户切不到 console 1 (只能 RDP 2 看屏幕), driver 实际在 session 2 跑, SendKeys 必然被 UIPI 拦
- **次要问题**: 
  - trigger.mjs JSON.parse 嵌套 + BOM 问题 (已修)
  - driver Add-Type 重复参数 `h` (已修)
  - driver parser 中文双引号 (用单引号修)
- **沉淀日期**：2026-06-04

## 根因（Windows session 隔离）

| 维度 | 状态 |
|------|------|
| Mavis daemon 进程 | session 2 (RDP) |
| MT5 (terminal64.exe) 进程 kernel | session 2 |
| MT5 窗口 attach | **console 1 desktop** (用户从物理 console 看) |
| RDP 2 进程能 GUI 操控 console 1 窗口? | **不能** (UIPI + 跨 desktop) |
| console 1 启的 powershell 能 SendKeys 到 MT5? | **能** (同 desktop) |
| 用户能切到 console 1 启 driver? | **能但要 Win+Ctrl+← 切物理 console**, 麻烦 |

**windows desktop isolation 是 OS 硬限制**, 不是工具问题. 任何进程跨 session 跨 desktop 操控窗口都被 UIPI 拦.

## 最终分工协议

| Mavis 做 | 用户做 |
|----------|--------|
| 写 EA (.mq5) | GUI 跑 backtest (Ctrl+R + Start) |
| 编译 (.ex5) | 复制 MT5 报告 XML 路径给 Mavis |
| 写 .set 调参 / .ini 模板 | |
| 写 spec / 沉淀到 Obsidian | |
| 写报告分析器 (mql5-report-analyzer.mjs) | |
| 基于 report XML 调参 + 写 v_n+1 | |
| 抓 trade journal CSV (live demo 24h 阶段) | GUI attach EA 到 chart (允许 Algo Trading) |

## 工具链产物（沉淀）

| 工具 | 路径 | 状态 |
|------|------|------|
| EA 编译 | `MetaEditor64 /compile:` CLI | **可用** |
| 报告分析 | `node mql5-report-analyzer.mjs` | **可用** |
| 报告 watcher | `mt5-report-watcher.ps1` | **可用** |
| GUI driver (待修) | `mt5-gui-driver.ps1` | **理论可用, 需 console 1 启** |
| GUI trigger | `mt5-gui-trigger.mjs` | **可用** (但 driver 必须 console 1) |

## 沉淀到 MEMORY 的关键认知

1. **MQL5 backtest 只能 GUI 跑** (CLI metatester64 挂死, MCP 9 stub not_yet_implemented)
2. **GUI 自动化受 UIPI + Windows session 隔离硬限制**, 跨 session 不能 SendKeys
3. **CU tool (Mavis mcp cu desktop_*) 跨 session 也不通**, focus/key 返 ok 但无效果
4. **MT5 进程 (terminal64) 即使在 session 2 跑, 窗口 attach 到 console 1 desktop**
5. **唯一可能 GUI 自动化: 进程在 console 1 desktop 跑** (用户切到 console 1 启)

## 避免下次重试的"红旗"

下次看到以下任一情况, **不要再试 GUI 自动化**, 立即走"用户跑 backtest"分工:
- "用 Python pyautogui"  ❌ 同样 UIPI 拦
- "用 VNC/RDP 转发"  ❌ 跨 desktop 一样
- "重启 MT5 加 CLI 启 backtest"  ❌ MT5 无此功能
- "写 EA 用 MQL5 TesterPass/TesterStatistics"  ❌ 这些是 EA 内的, 不能启动 backtest
- "找 Mavis mcp cu 替代"  ❌ 已试不通

## 接受现实

**Mavis 永远无法 GUI 操控用户 console 上的 MT5 窗口**. 这是 OS 设计, 不是工具问题. 

接受分工, 写好 EA, 编译好, 等用户跑 backtest 传结果.
