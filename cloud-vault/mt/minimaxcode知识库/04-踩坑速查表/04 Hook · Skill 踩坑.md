---
title: 04 Hook / Skill 踩坑
tags: [pitfall, hook, skill, Mavis]
created: 2026-06-03
---

# 04 Hook / Skill 踩坑

> 来源：实战记录，持续补充。

## P-21 Hook 不生效

**症状**：

```bash
mavis hook list --agent general
# 看到 hook 存在
# 但工具调用没被拦截
```

**根因**：

- `agentName` 拼错（如 `general` vs `General`）
- hook 文件位置不对（必须在 `~/.mavis/hooks/<agentName>/<name>.json`）
- daemon 缓存了旧 hook 列表 → **重启 daemon**
- JSON 5 语法（注释、尾逗号）需要 daemon ≥ 0.8

**修复**：

```bash
# 1. 验证 hook 文件在
ls -la ~/.mavis/hooks/general/

# 2. 验证 JSON 合法
mavis hook test general:<hookName> --input '{...}'

# 3. 重启 daemon
mavis daemon restart
```

## P-22 Hook 改写后参数错

**症状**：

工具调用时参数被改了，但改得不正确（如路径前缀加了双反斜杠）。

**根因**：

`matcher` 的 JSON path 路径拼错；改写逻辑里**直接字符串拼接**导致转义问题。

**修复**：

```powershell
# 错：直接字符串拼接
$newPath = "C:\" + $oldPath

# 对：用 Path.Combine 或 hashtable
$newPath = Join-Path "C:\" $oldPath
$body = @{path = $newPath} | ConvertTo-Json -Compress
```

调试方法：`mavis hook test` 模拟一次，看实际 `output.toolArgs`。

## P-23 模型无视 deny message

**症状**：

Hook deny 了 `rm -rf`，message 写的是 "禁止 rm"，但模型接着又试一次 `rm -rf`（陷入循环）。

**根因**：

message 太模糊。模型不知道"为什么禁止 + 应该用什么替代"。

**修复**：

```json
{
  "action": "deny",
  "message": "禁止 rm -rf（不可逆、有数据丢失风险）。改用 'mavis-trash <paths>'：文件进回收站，30 天可恢复。"
}
```

> 三要素：① 是什么 ② 为什么 ③ 用什么替代

## P-24 Skill 加载爆 token

**症状**：

加载一个 skill 后，模型回复变慢、变长，单次调用 token 用量翻倍。

**根因**：

SKILL.md 写得太长（几千字 + 大量代码示例）。skill 一旦 `skill(name=...)` 就**全文注入**。

**修复**：

- SKILL.md 控制在 **< 1500 字**
- 长内容拆"主 SKILL.md" + "references/*.md"，按需 `read` 加载子文档
- 别在 SKILL.md 里贴完整代码 —— 改用 `bash` tool + `cat file` 引导模型去读

## P-25 Skill 路径找不到

**症状**：

`skill(name="my-skill")` 报 "skill not found"。

**根因**：

- skill 装在 `~/.mavis/skills/<name>/SKILL.md` 而不是 `<name>/skill.md`
- 文件名是 `Skill.md`（大写 S）—— 不同 OS 大小写敏感
- skill 目录缺 `SKILL.md` 入口

**修复**：

```
~/.mavis/skills/
└── my-skill/
    ├── SKILL.md          # 必填，frontmatter 必填 name + description
    └── references/       # 可选
        └── advanced.md
```

`SKILL.md` 必填 frontmatter：

```yaml
---
name: my-skill
description: 一句话讲清这个 skill 干什么、何时加载。
---
```

## P-26 MCP server 反复 disconnect

**症状**：

`mavis mcp ls` 显示 server 状态在 connected / disconnected 之间抖动。

**根因**：

- 第三方 MCP server 自身崩溃 → daemon 检测失败、retry
- daemon 给 server 的子进程 stdin / stdout 缓冲用尽
- 路径里有空格 / 中文，server 启动命令解析错

**修复**：

```bash
# 1. 看具体 server 日志
mavis mcp restart playwright
Get-Content C:\Users\Administrator\.mavis\logs\mcp-playwright.log -Tail 50

# 2. 路径含空格 → 用引号包
mavis mcp config playwright --command '"C:\Program Files\app\server.exe"'

# 3. 实在不行就降级到手动启 server
mcp-server.exe --port 15322 &
# daemon 里把 server URL 改成 http://localhost:15322
```

## P-27 hook regex 不 anchor 误匹配

**症状**：

Hook 想拦 `git push --force`，但把所有 `git push` 都拦了。

**根因**：

```json
"toolArgs.command": "git\\s+push\\s+.*--force"
```

`.*` 是贪婪的，加上不 anchor `^`，可能在 `echo "git push --force bad" | sh` 里也匹配。

**修复**：

```json
"toolArgs.command": "^git\\s+push\\s+.*--force"
```

并测试 3 个 case：

```bash
# 命中
mavis hook test general:block-force --input '{"toolArgs":{"command":"git push --force origin main"}}'

# 未命中
mavis hook test general:block-force --input '{"toolArgs":{"command":"git push origin main"}}'

# 边缘（注释里有 force）
mavis hook test general:block-force --input '{"toolArgs":{"command":"# git push --force\\necho done"}}'
```

## P-28 after-hook 写日志导致原工具失败

**症状**：

after-hook 想写审计日志，结果日志路径无权限 / 写失败，反过来让工具调用 mark as failed。

**根因**：

after-hook 异常未被捕获，**会冒泡到原工具调用结果**。

**修复**：

Hook 文件里所有 IO 套 `try / catch`，失败只 warn，不抛：

```json
{
  "action": "log",
  "logFile": "C:\\Users\\...\\audit.log",
  "onError": "swallow"  // 写日志失败不阻断原工具
}
```

> 实际写法看 daemon 版本支持的字段，0.8+ 支持 `onError: swallow | propagate`。

## P-29 Skill 互相依赖没说清

**症状**：

A skill 用到 B skill 的内容，但 SKILL.md 里没说 "需要先加载 B"。

**修复**：

在 SKILL.md 顶部写：

```markdown
> **依赖**：使用本 skill 前先 `skill(name="B")`
> 关联：把 B / C 等依赖 skill 的 SKILL.md 路径写在这里，方便人读。
```

并在 description 里加提示。

## 速查表

| 问题             | 第一查                       |
| -------------- | ------------------------- |
| Hook 不生效       | `mavis hook list` 看 agentName |
| Hook 改写错       | `mavis hook test` 模拟       |
| Skill 找不到      | 检查 `SKILL.md` 大写、路径、frontmatter |
| Skill 上下文爆     | 拆 references/             |
| MCP 抖动         | 看 server 日志、路径空格         |
| 模型无视 deny     | message 三要素（是什么/为什么/替代）  |

→ 关联：[[01-核心模块/M06 Hook 系统]]、[[01-核心模块/M03 Skills 与 MCP]]
