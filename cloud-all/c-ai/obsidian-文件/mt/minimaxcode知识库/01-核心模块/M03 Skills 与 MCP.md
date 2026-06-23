---
title: M03 Skills 与 MCP
tags: [skill, MCP, integration]
created: 2026-06-03
---

# M03 Skills 与 MCP

## 区别

| 维度    | Skill                       | MCP Server                |
| ----- | --------------------------- | ------------------------- |
| 形态    | Markdown 知识（流程 / 最佳实践）       | 可执行工具（CLI / 进程）            |
| 加载方式  | `skill` tool（按需注入上下文）       | `bash` tool 调 `mavis mcp` |
| 谁维护  | 用户/agent 自己写                | 第三方 / daemon 内置            |
| 例子   | `mavis`, `plan-mode`        | `cu`, `matrix`, `playwright` |

## 加载 Skill

```bash
# 按需加载
skill(name="mavis")          # 加载 mavis 入口
skill(name="skill-creator")  # 加载创建 skill 的 skill
```

> Skill 一旦加载，对应 SKILL.md 全文注入到上下文。**别没事乱加载**——会很占 token。

## MCP 调用方式

### Native tools（直调）

MCP server 注册的 "Native tools" 是直接函数，不需要 CLI 包装：

```python
# 已经是模型直接可用的工具
describe_images(...)
videos_understand(...)
audios_understand(...)
web_search(...)
```

### CLI 包装（一般 MCP）

非 native 的工具走 `mavis mcp`：

```bash
# 列出某 server 的所有工具
mavis mcp tools cu

# 调用工具
mavis mcp call cu desktop_screenshot '{}'

# 看 schema
mavis mcp tools cu desktop_left_click
```

## 已注册的 MCP servers（当前）

| Server         | 能力                                       | Native tools                       |
| -------------- | ---------------------------------------- | ---------------------------------- |
| `cu`           | 桌面自动化（鼠标/键盘/截屏/窗口）                    | — （全部走 CLI）                       |
| `matrix`       | 视频/音频理解、图像生成、TTS、音乐、Web 搜索              | `web_search`, `describe_images`, `videos_understand`, `audios_understand` |
| `playwright`   | 浏览器自动化（无状态，匿名）                          | —                                  |
| `trash`        | 可恢复删除（替代 `rm`）                          | `trash`                            |
| `mavis-browser` | 用用户真实 Chrome（带 cookie）—— 加载 `mavis-browser` skill 后用 | —                                  |

## 选型原则

- **需要登录态 / cookie / 扩展** → `mavis-browser`（真实 Chrome）
- **匿名爬公开网页** → `playwright` MCP
- **截图桌面 / 操控 Windows GUI** → `cu` MCP
- **需要 Web 搜索 / 生成图片** → `matrix`（native tools）
- **删除文件** → `trash`（永远不要 `rm`）

## 踩坑速记

1. `mavis mcp call` 的 JSON 参数必须是合法 JSON 字符串——反斜杠要先转义。
2. 看到 `Tool not found` → `mavis mcp tools <server>` 查真实名字。
3. 看到 `Server not connected` → `mavis mcp ls` 看 server 健康状态，必要时 `mavis mcp restart <server>`。
4. Native tool 名和 CLI 路径不能混用——别用 `mavis mcp call matrix web_search`（应该直调 `web_search` 函数）。
