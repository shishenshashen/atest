---
title: T03 Daemon API 客户端
tags: [template, daemon, API, PowerShell, JSON]
created: 2026-06-03
---

# T03 Daemon API 客户端

## 场景

从 PowerShell 直接调 mavis daemon 的 HTTP API。
常见目标：

- 查 / 翻 CU 状态
- 触发一个 agent session
- 查询 session 列表 / 状态
- 调自定义 skill endpoint

## 通用客户端函数

保存为 `C:\Users\Administrator\.mavis\bin\mavis-api.ps1`：

```powershell
<#
.SYNOPSIS
  极简 mavis daemon API 客户端
#>

$script:DaemonBase = "http://localhost:15321"
$script:DefaultHeaders = @{
  "Content-Type" = "application/json"
  "Accept"       = "application/json"
}

function Invoke-MavisApi {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)] [ValidateSet("GET","POST","PUT","DELETE")] [string]$Method,
    [Parameter(Mandatory)] [string]$Path,
    [hashtable]$Body,
    [int]$TimeoutSec = 10
  )

  $uri = $script:DaemonBase + $Path
  $params = @{
    Method      = $Method
    Uri         = $uri
    Headers     = $script:DefaultHeaders
    TimeoutSec  = $TimeoutSec
    UseBasicParsing = $true
  }

  if ($PSBoundParameters.ContainsKey("Body")) {
    # hashtable + ConvertTo-Json -Compress：自动处理反斜杠、中文
    $params.Body = $Body | ConvertTo-Json -Compress -Depth 10
  }

  try {
    $resp = Invoke-WebRequest @params
    if ($resp.Content) {
      return $resp.Content | ConvertFrom-Json
    }
    return $null
  } catch {
    throw "Mavis API call failed: $($_.Exception.Message)"
  }
}

# 常用封装
function Get-MavisCuStatus {
  Invoke-MavisApi -Method GET -Path "/mavis/api/cu/enabled"
}

function Set-MavisCuEnabled {
  param([bool]$Enabled, [string]$WorkspaceDir = "C:\Users\Administrator\.mavis\sessions")
  Invoke-MavisApi -Method PUT -Path "/mavis/api/cu/enabled" -Body @{
    enabled     = $Enabled
    workspaceDir = $WorkspaceDir
  }
}

function Get-MavisSessionList {
  Invoke-MavisApi -Method GET -Path "/mavis/api/sessions"
}

# 导出
Export-ModuleMember -Function Invoke-MavisApi, Get-MavisCuStatus, Set-MavisCuEnabled, Get-MavisSessionList
```

## 使用

```powershell
# 加载
. "C:\Users\Administrator\.mavis\bin\mavis-api.ps1"

# 1. 查 CU 状态
Get-MavisCuStatus
# { enabled: true, workspaceDir: "...", updatedAt: "..." }

# 2. 打开 CU
Set-MavisCuEnabled -Enabled $true

# 3. 关闭 CU
Set-MavisCuEnabled -Enabled $false

# 4. 列 session
Get-MavisSessionList | Format-Table id, role, status, createdAt

# 5. 自定义调用
Invoke-MavisApi -Method GET -Path "/mavis/api/agents"
```

## 必避的坑

### ❌ 用字符串拼接构造 body

```powershell
# 错！反斜杠和中文会被吞
$body = '{"workspaceDir":"' + $workspace + '","enabled":true}'
```

### ✅ 用 hashtable + ConvertTo-Json

```powershell
$body = @{workspaceDir=$workspace; enabled=$true} | ConvertTo-Json -Compress
```

> 详细原因见 [[03-通用片段/02 反斜杠安全 JSON]]。

### ❌ 路径前缀写 `/api/`

```powershell
# 错
Invoke-MavisApi -Path "/api/cu/enabled"

# 对
Invoke-MavisApi -Path "/mavis/api/cu/enabled"
```

### ❌ 忘了 `-UseBasicParsing`

老 Windows 没装 IE 时会卡死。永远加 `-UseBasicParsing`。

## 调试技巧

```powershell
# 看真实 HTTP 状态码和 body
try {
  $resp = Invoke-WebRequest -Uri "http://localhost:15321/mavis/api/cu/enabled" -UseBasicParsing
  Write-Host "Status: $($resp.StatusCode)"
  Write-Host "Body: $($resp.Content)"
} catch {
  Write-Host "Error: $($_.Exception.Message)"
  if ($_.Exception.Response) {
    $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
    Write-Host "Server body: $($reader.ReadToEnd())"
  }
}
```

## 与 curl 互转

| PowerShell                                       | curl                                                     |
| ------------------------------------------------ | -------------------------------------------------------- |
| `Invoke-MavisApi -Method GET -Path "/mavis/api/agents"` | `curl http://localhost:15321/mavis/api/agents`             |
| `Invoke-MavisApi -Method PUT -Path "/mavis/api/cu/enabled" -Body @{enabled=$true}` | `curl -X PUT http://localhost:15321/mavis/api/cu/enabled -H "Content-Type: application/json" -d '{"enabled":true}'` |
