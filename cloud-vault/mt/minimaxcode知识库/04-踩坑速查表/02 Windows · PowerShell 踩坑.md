---
title: 02 Windows / PowerShell 踩坑
tags: [pitfall, PowerShell, Windows, scheduled-task]
created: 2026-06-03
---

# 02 Windows / PowerShell 踩坑

> 来源：agent memory，已实战验证。

## P-08 `$_` 在 mavis 工具里被错解析

**症状**：

```powershell
Get-ChildItem | Where-Object { $_.Length -gt 1MB }
# 报错：在表达式中发现意外的标记
```

**根因**：PowerShell 5.1+ 在某些上下文（特别在 mavis shell 的 bash tool 内联调用时）会错解析 `$_`。

**修复**：

```powershell
# 方案 1：先存到变量
Get-ChildItem | ForEach-Object {
  $x = $_
  if ($x.Length -gt 1MB) { $x.Name }
}

# 方案 2：把脚本写到 .ps1 文件
powershell.exe -NoProfile -File "C:\path\to\script.ps1"
```

## P-09 UTF-8 BOM 阻塞 PS 5.1 解析

**症状**：脚本在"看起来无害"的位置报语法错：

```
在表达式中发现意外的标记"}""
```

**根因**：文件含 UTF-8 BOM（不止一个 BOM 时尤其严重）。

**修复**：

```powershell
# 用 .NET 显式无 BOM 写入
[System.IO.File]::WriteAllText(
  "C:\path\to\file.ps1",
  $content,
  [System.Text.UTF8Encoding]::new($false)
)

# 或
Get-Content "C:\path\to\file.ps1" | Set-Content -Encoding UTF8NoBOM
```

## P-10 `New-ScheduledTaskTrigger -AtStartup -Delay` 不支持

**症状**：

```
A parameter cannot be found that matches parameter name 'Delay'.
```

**根因**：PS 5.1 的 cmdlet 不支持 `-Delay`。

**修复**：去掉 `-Delay`；要用延迟，改用 `schtasks` 命令行：

```powershell
# 错
New-ScheduledTaskTrigger -AtStartup -Delay "PT1M"

# 对
New-ScheduledTaskTrigger -AtStartup

# 或
schtasks /Create /TN Foo /SC ONSTART /DELAY 0001:00 /TR "..." /F
```

## P-11 `RestartCount` / `RestartInterval` 必须在 `Register-ScheduledTask` 设

**症状**：`schtasks` 创建的任务没有"失败自动重启"。

**根因**：`schtasks` 命令不支持这两个参数。

**修复**：

```powershell
# 1. schtasks 创建基础任务
schtasks /Create /TN MavisCUKeepAlive /SC ONSTART /RL HIGHEST /RU SYSTEM /TR "..." /F

# 2. PowerShell 补充设置
$task = Get-ScheduledTask -TaskName "MavisCUKeepAlive"
$task.Settings.RestartCount = 3
$task.Settings.RestartInterval = "PT1M"
$task | Set-ScheduledTask
```

> `RestartInterval` 用 ISO 8601 duration：`"PT1M"` = 1 分钟、`"PT5M"` = 5 分钟。

## P-12 `Invoke-WebRequest` 字符串拼接 JSON 丢反斜杠

**症状**：daemon 返 500，错误"Unexpected token in JSON"。

**根因**：PowerShell 字符串拼接不转义 `\`。

**修复**：hashtable + `ConvertTo-Json -Compress`：

```powershell
$body = @{path="C:\Users\foo"; enabled=$true} | ConvertTo-Json -Compress
Invoke-WebRequest -Method PUT -Uri $url -Body $body -ContentType "application/json"
```

→ 详见 [[03-通用片段/02 反斜杠安全 JSON]]。

## P-13 计划任务工作目录是 `C:\Windows\System32`

**症状**：脚本里 `.\config.json` 找不到文件，任务历史却显示"成功"。

**根因**：计划任务运行时 `cwd` 跟脚本所在目录无关。

**修复**：

```powershell
# 脚本开头固定工作目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir
```

或永远用绝对路径。

## P-14 SYSTEM 身份跑 CU 失败

**症状**：`SYSTEM` 身份的计划任务跑 CU 脚本，截屏失败。

**根因**：`SYSTEM` 跑在 session 0，跟用户桌面（session 1+）隔离。

**修复**：

- 改 trigger 为 `-AtLogOn` 而非 `-AtStartup`
- 用用户身份（`$env:USERDOMAIN\$env:USERNAME`）跑
- 在任务计划程序 UI 勾「只在用户登录时运行」
