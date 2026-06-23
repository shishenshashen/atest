---
title: 01 30 分钟跑通 Mavis + CU
tags: [quickstart, Mavis, CU, daemon]
created: 2026-06-03
---

# 30 分钟跑通 Mavis + CU

## 前置检查

```powershell
# PowerShell 5.1+（Windows 自带即可）
$PSVersionTable.PSVersion

# 15321 是 mavis daemon 默认端口
Test-NetConnection localhost -Port 15321
```

> 看到 `TcpTestSucceeded : True` 说明 daemon 在线。

## 1. 启动 daemon

```powershell
# 找 daemon 可执行文件
Get-Command mavis -ErrorAction SilentlyContinue
# 若未安装：参考官方 README 安装
mavis daemon start
```

## 2. 打开 CU

CU 默认是关的。**配置文件 + API 都要改**：

```powershell
# 配置文件（持久化）
mavis config set beta.cuMode true

# 内存状态（立即生效）
Invoke-WebRequest -Method PUT `
  http://localhost:15321/mavis/api/cu/enabled `
  -Body '{"enabled":true,"workspaceDir":"C:\Users\Administrator\.mavis\sessions"}' `
  -ContentType "application/json"
```

> 路径前缀是 `/mavis/`（不是 `/api/`）。详见 [[04-踩坑速查表/01 CU 相关踩坑]]。

## 3. 验证 CU 能截屏

切到 **本地 console session（session 1）** 登录，不要用 RDP（session 2+）。

```powershell
# 调用 MCP：cu/desktop_screenshot
# 看到 base64 图片即成功
```

如果只看到 `Failed to capture screen`，回到 console 重新登录 → 详见 [[04-踩坑速查表/01 CU 相关踩坑]]。

## 4. 跑一个最小 agent

```powershell
# 注册并启动一个 worker
mavis agent run general --prompt "echo hello"
```

## 5. 安装 keep-alive（关键）

CU 会在窗口最小化/恢复时被自动关掉，必须用 keep-alive 守护：

```powershell
# 参考 02-实战模板/T01 CU keep-alive 守护脚本
# 注册为开机计划任务 → 02-实战模板/T02 开机自启计划任务
```

## 验收清单

- [ ] `Test-NetConnection localhost -Port 15321` 成功
- [ ] `mavis config get beta.cuMode` 返回 `true`
- [ ] `desktop_screenshot` 在 console session 返回图片
- [ ] keep-alive 脚本每 30s 打印 `[cu] enabled: true`
