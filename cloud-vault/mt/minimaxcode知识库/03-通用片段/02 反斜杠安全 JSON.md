---
title: 02 反斜杠安全 JSON
tags: [snippet, JSON, PowerShell, escape]
created: 2026-06-03
---

# 02 反斜杠安全 JSON

## 问题

PowerShell 字符串拼接构造 JSON 时，**反斜杠不会被自动转义**：

```powershell
$path = "C:\Users\foo\bar"
$body = '{"path":"' + $path + '"}'
Write-Host $body
# {"path":"C:Usersfoobar"}      # 错！\U \f \b 被解析成转义
```

收到的 daemon 看到 `C:Usersfoobar`，不是合法路径 → 500。

## 方案 1：hashtable + ConvertTo-Json（推荐）

```powershell
$body = @{path=$path; enabled=$true; name="test"} | ConvertTo-Json -Compress
# {"path":"C:\\Users\\foo\\bar","enabled":true,"name":"test"}
```

✅ 反斜杠、中文、引号全部自动转义。

## 方案 2：双反斜杠手动转

```powershell
$pathEscaped = $path -replace '\\', '\\'
$body = '{"path":"' + $pathEscaped + '"}'
```

❌ 容易漏转（中文、引号、特殊字符都要管）。

## 方案 3：用 ConvertTo-Json 不用 -Compress

```powershell
$body = @{path=$path} | ConvertTo-Json
```

✅ 一样安全，但 body 是多行——某些 server 不接受。

→ 永远加 `-Compress`。

## 方案 4：手工构造 JSON 用 [System.Text.Json]

```powershell
Add-Type -AssemblyName System.Text.Json
$body = [System.Text.Json.JsonSerializer]::Serialize(@{path=$path; enabled=$true})
```

✅ 跨 PS 版本行为一致，输出永远合法。
❌ PS 5.1 默认没装 `System.Text.Json`——要 .NET Core/5+。

## 嵌套对象

```powershell
$body = @{
  enabled = $true
  options = @{
    workspaceDir = $path
    timeout      = 30
    tags         = @("test","dev")
  }
} | ConvertTo-Json -Compress -Depth 10
```

→ `-Depth 10` 确保嵌套对象不被截断。

## 数组

```powershell
# PS 5.1: ConvertTo-Json 数组会变字符串！加 -AsArray
$body = @(@{a=1},@{a=2}) | ConvertTo-Json -Compress -AsArray
# [{"a":1},{"a":2}]
```

## 错误自查表

| 现象                              | 原因                  | 修复                           |
| ------------------------------- | ------------------- | ---------------------------- |
| `Unexpected token in JSON`     | 反斜杠 / 引号没转义        | 用 hashtable + `ConvertTo-Json` |
| `{"path":"C:Users"}`           | 字符串拼接，`\U` 被解析     | 同上                           |
| 中文乱码                            | 文件编码非 UTF-8        | 写入用 [[02-实战模板/T03 Daemon API 客户端]] 里的 .NET 方法 |
| daemon 返 500 但本地 curl 正常        | body 里有不可见 BOM 字符 | 写入无 BOM                      |
| `ConvertTo-Json : Invalid JSON primitive` | hashtable 有 $null 值 | 过滤 null：`@{a=$v} | Where-Object {$_} | ConvertTo-Json` |
