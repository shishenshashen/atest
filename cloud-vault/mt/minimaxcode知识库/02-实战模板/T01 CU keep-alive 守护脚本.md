---
title: T01 CU keep-alive 守护脚本
tags: [template, CU, keep-alive, PowerShell]
created: 2026-06-03
---

# T01 CU keep-alive 守护脚本

## 用途

CU 在窗口最小化/恢复时会被 renderer 自动关掉。这个脚本**每 30 秒** PUT 一次 `enabled=true`，保持 CU 始终在线。

## 文件

保存为 `C:\Users\Administrator\.mavis\bin\cu-keepalive.ps1`：

```powershell
<#
.SYNOPSIS
  Mavis CU keep-alive daemon
.DESCRIPTION
  每 30s 调 PUT /mavis/api/cu/enabled 保持 CU 开启
  写日志到 C:\Users\Administrator\.mavis\logs\cu-keepalive.log
#>

$ErrorActionPreference = "Stop"
$LogDir = "C:\Users\Administrator\.mavis\logs"
$LogFile = Join-Path $LogDir "cu-keepalive.log"
$DaemonUrl = "http://localhost:15321/mavis/api/cu/enabled"
$Workspace = "C:\Users\Administrator\.mavis\sessions"

# 确保日志目录存在
if (-not (Test-Path $LogDir)) {
  New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

function Write-Log($msg) {
  $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $PID, $msg
  Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

# 启动横幅
Write-Log "=== CU keep-alive started, workspace=$Workspace ==="

while ($true) {
  try {
    # 关键：hashtable + ConvertTo-Json -Compress 避免反斜杠丢失
    $body = @{enabled=$true; workspaceDir=$Workspace} | ConvertTo-Json -Compress

    $resp = Invoke-WebRequest -Method PUT `
      -Uri $DaemonUrl `
      -Body $body `
      -ContentType "application/json" `
      -TimeoutSec 5 `
      -UseBasicParsing

    Write-Log ("PUT enabled=true -> HTTP {0}" -f $resp.StatusCode)
  } catch {
    Write-Log ("PUT failed: {0}" -f $_.Exception.Message)
    # daemon 死了？等待后重试
    Start-Sleep -Seconds 5
  }

  Start-Sleep -Seconds 30
}
```

> UTF-8 **无 BOM** 写入（参考 [[03-通用片段/01 PowerShell 踩坑合集]]）。

## 注册为开机自启

参考 [[02-实战模板/T02 开机自启计划任务]]：

```powershell
# 一次性执行（管理员 PowerShell）
$script = "C:\Users\Administrator\.mavis\bin\cu-keepalive.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName "MavisCUKeepAlive" `
  -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
```

## 验证

```powershell
# 1. 看任务在不在
Get-ScheduledTask -TaskName "MavisCUKeepAlive"

# 2. 看最近日志
Get-Content C:\Users\Administrator\.mavis\logs\cu-keepalive.log -Tail 10

# 3. 手动确认 CU 在线
(Invoke-WebRequest http://localhost:15321/mavis/api/cu/enabled).Content
```

## 调参

| 参数             | 默认      | 调整建议                                |
| -------------- | ------- | ----------------------------------- |
| `Start-Sleep`  | 30s     | 太密（<10s）会被 daemon throttle；太疏会偶发关闭 |
| `-TimeoutSec`  | 5       | daemon 慢启动时调到 10                    |
| `RestartCount` | 3       | 看机器稳定性；笔记本可以 5                     |

## 故障排查

- 日志无 `PUT` 行 → 计划任务没启动 → `Get-ScheduledTask` 看状态
- 日志全是 `failed` → daemon 端口死了 → `Test-NetConnection`
- 日志说"成功"但 CU 仍关 → renderer 又来了一次 `false` → 检查别的窗口（屏保、通知中心）
