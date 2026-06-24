---
title: 00 minimaxcode 是什么
tags: [overview, minimaxcode]
created: 2026-06-03
---

# minimaxcode 是什么

## 定位

`minimaxcode知识库` 是一个 **Mavis（agent 框架）使用手册**，主题聚焦在：

- **Mavis 本身**：daemon / renderer / agent / session / memory / skill / cron
- **Computer Use（CU）**：桌面自动化（鼠标、键盘、截屏、窗口）
- **配置**：daemon 端口、CU toggle、UAC、RDP session
- **自动化**：计划任务、开机自启、keep-alive 守护
- **踩坑**：从实战中沉淀的 PowerShell / Windows / API 调用陷阱

## 读者

- 第一次接触 Mavis / CU 的用户
- 部署 Mavis 到生产环境（开机自启、长期托管）
- 排查"CU 自动关闭"、"daemon 启动卡住"、"PowerShell 脚本莫名失败"等问题的工程师

## 与 `mt\EA开发\` 的关系

| 维度     | `mt\EA开发\`     | `minimaxcode知识库\`  |
| ------ | ------------- | ----------------- |
| 主题     | MQL5 EA 开发     | Mavis / CU / 自动化    |
| 章节命名   | `00-快速开始` 等   | 同（保持兼容）            |
| 模块前缀   | `Mxx`（模块）     | `Mxx` / `Txx`      |
| 速查表    | `04-踩坑速查表`    | 同                  |
| 文件编码   | UTF-8（无 BOM）  | UTF-8（无 BOM）       |
| Frontmatter | 最小           | title / tags / created |

> 结构故意保持一致，方便 Obsidian 双向链接与 Dataview 查询互通。

## 写作规范

1. **中文为主**，代码、路径、CLI 保留英文。
2. **可复用优先**：贴可直接 `Run-File` 跑的脚本；不贴伪代码。
3. **每个坑都给出**：症状 → 根因 → 修复 → 验证命令。
4. **有反面才有正面**：每张卡都来自一次真实失败。

## 更新频率

- 每次 session 出现新坑 → 24 小时内补到 [[04-踩坑速查表/]]
- 每次实战脚本可复用 → 提炼到 [[02-实战模板/]]
- 每月做一次"过期页"巡检（半年以上未访问的，标记 ⚠️）
