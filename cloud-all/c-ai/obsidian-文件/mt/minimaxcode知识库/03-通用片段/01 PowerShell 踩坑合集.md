---
title: 01 PowerShell 踩坑合集
tags: [snippet, PowerShell, pitfall, Windows]
created: 2026-06-03
---

# 01 PowerShell 踩坑合集

> 提炼自 `~/.mavis/agents/mavis/memory/MEMORY.md`，所有条目都来自真实失败。

## `$_` 在管道里被错解析

**症状**：

```powershell
Get-ChildItem | Where-Object { $_.Length -gt 1MB }
# 报错：在表达式中发现意外的标记
```

**根因**：PowerShell 5.1+ 在某些上下文（特别嵌套在字符串里、或被 mavis shell 包装时）会把 `$_` 解析错。

**修复**：

```powershell
# 方案 1：先存到变量
Get-ChildItem | ForEach-Object {
  $x = $_
  if ($x.Length -gt 1MB) { $x.Name }
}

# 方案 2：把脚本写到 .ps1 文件，用 powershell.exe -File 调
# powershell.exe -NoProfile -File "C:\path\to\script.ps1"
```

## UTF-8 BOM 让脚本报"语法错"

**症状**：

```
在表达式中发现意外的标记"}""
```

但出错位置看起来**毫无问题**。

**根因**：文件含多个 UTF-8 BOM（eg. 复制粘贴、git 自动转换），PS 5.1 在 BOM 后插入"看不见"的字符。

**修复**：

```powershell
# 方案 1：用 .NET 显式无 BOM
[System.IO.File]::WriteAllText(
  "C:\path\to\file.ps1",
  $content,
  [System.Text.UTF8Encoding]::new($false)
)

# 方案 2：先读再写（PS 6+ 才有 UTF8NoBOM）
Get-Content "C:\path\to\file.ps1" | Set-Content -Encoding UTF8NoBOM
```

## 字符串拼接构造 JSON → daemon 收到坏 JSON

**症状**：

```powershell
$path = "C:\Users\foo\bar"
$body = '{"path":"' + $path + '"}'
Invoke-WebRequest ... -Body $body
# daemon 返 500，日志：Unexpected token in JSON at position 12
```

**根因**：PowerShell 字符串拼接不转义 `\`。`$path` 里的 `\` 直接进 JSON。

**修复**：

```powershell
$body = @{path=$path} | ConvertTo-Json -Compress
```

详见 [[03-通用片段/02 反斜杠安全 JSON]]。

## `New-ScheduledTaskTrigger -AtStartup -Delay` 报参数错

**症状**：

```
A parameter cannot be found that matches parameter name 'Delay'.
```

**根因**：PS 5.1 的 `New-ScheduledTaskTrigger` 不支持 `-Delay`。

**修复**：

```powershell
# 错
New-ScheduledTaskTrigger -AtStartup -Delay "PT1M"

# 对：去掉 -Delay，trig 就是启动时触发；用其他机制延迟
New-ScheduledTaskTrigger -AtStartup
# 或：用 schtasks 命令行（支持 /DELAY）
schtasks /Create /TN Foo /SC ONSTART /DELAY 0001:00 ...
```

## 计划任务的工作目录不是脚本目录

**症状**：任务历史显示"成功"，但脚本里相对路径的 `.\config.json` 找不到。

**根因**：任务运行时 `cwd` 是 `C:\Windows\System32`。

**修复**：脚本里永远用绝对路径，或在脚本开头：

```powershell
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir
```

## 计划任务里看不到 GUI 窗口

**症状**：`AtStartup` 触发的任务，CU 报"Failed to capture screen"。

**根因**：`SYSTEM` 身份跑在 session 0，跟用户桌面隔离。

**修复**：

- 选项 A：trigger 改 `-AtLogOn`，让用户在登录时触发
- 选项 B：UI 设「只在用户登录时运行」「用户已登录时触发」

## 一行 inline `Get-Process | Where` 在 mavis 工具里失败

**症状**：在 `bash` tool 里写 powershell 复合命令时，`$_` 解析失败。

**根因**：mavis shell 对 `$` 字符的转义。

**修复**：把逻辑写进 .ps1 文件再 `-File` 执行；不要在 bash inline 里搞复杂 PS 表达式。
