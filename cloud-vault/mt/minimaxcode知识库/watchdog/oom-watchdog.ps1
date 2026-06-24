<#
oom-watchdog.ps1
Mavis/OpenCode 资源看门狗

触发：mavis cron "oom-watchdog" 每 2 分钟
目的：解决 2026-06-03 15:00 闪退事件——
  14:59 时 7 个 OpenCode 进程并发跑，总内存 1.3GB+，
  导致 daemon 整体挂掉（旧 root session "No running process and recovery failed"）。

检查 + 处置：
  1. 单 OpenCode 进程内存 > 1.5 GB → kill
  2. OpenCode 总内存 > 4 GB → 按 StartTime 杀最老的，降到 < 3 GB
  3. OpenCode 进程数 > 5 → 杀最老的，降到 ≤ 5
  4. daemon 15321 端口未监听 → 标记 down（cron agent 决定是否重启）

输出：JSON 单行到 stdout（mavis cron agent 解析用），同时写日志到 mavis-watchdog.log。

使用：
  powershell -NoProfile -ExecutionPolicy Bypass -File oom-watchdog.ps1
#>

$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# ---- 阈值 ----
$MAX_OPENCODE_COUNT     = 5
$MAX_OPENCODE_SINGLE_MB = 1536    # 1.5 GB
$MAX_OPENCODE_TOTAL_MB  = 4096    # 4 GB
$KEEP_OPENCODE_TOTAL_MB = 3072    # 杀到 3 GB 以下
$DAEMON_PORT            = 15321

# ---- 路径 ----
$LogDir  = "C:\Users\Administrator\.mavis\logs"
$LogFile = Join-Path $LogDir "mavis-watchdog.log"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

function Write-Log {
    param([string]$Level, [string]$Message)
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $LogFile -Value "[$ts] [$Level] $Message" -Encoding UTF8
}

# ---- 取 OpenCode 进程（手动 foreach filter + 缓存关键字段，避免 PS 5.1 多行 Where-Object 解析坑 + 进程中途死掉时字段访问异常）----
function Get-OcSnapshot {
    $raw = @(Get-Process -Name "opencode","OpenCode" -ErrorAction SilentlyContinue)
    $arr = New-Object System.Collections.ArrayList
    foreach ($p in $raw) {
        # 二次验证：路径含 opencode.exe 且内存 > 0
        $pathOK = $false
        if ($p.Path) { if ($p.Path -like '*\opencode.exe') { $pathOK = $true } }
        $wsOK = $false
        try { if ($p.WorkingSet64 -gt 0) { $wsOK = $true } } catch { }
        if ($pathOK -or $wsOK) {
            $snapshot = New-Object PSObject -Property @{
                Id           = 0
                StartTimeStr = ""
                WsMB         = 0.0
                CPU          = 0.0
            }
            try { $snapshot.Id = [int]$p.Id } catch { }
            try { $snapshot.StartTimeStr = $p.StartTime.ToString("HH:mm:ss") } catch { $snapshot.StartTimeStr = "?" }
            try { $snapshot.WsMB = [math]::Round($p.WorkingSet64 / 1MB, 1) } catch { $snapshot.WsMB = 0.0 }
            try { $snapshot.CPU = [math]::Round($p.CPU, 2) } catch { $snapshot.CPU = 0.0 }
            [void]$arr.Add($snapshot)
        }
    }
    # 按 StartTime 升序（手动，避开 Sort-Object 在进程快死时的崩溃）
    $sorted = @($arr | Sort-Object @{Expression={ if ($_.StartTimeStr -eq "?") { "99:99:99" } else { $_.StartTimeStr } }})
    return ,$sorted
}

# 抓 3 次快照（每次循环后重新拉，因为有进程死了）
$ocProcs = Get-OcSnapshot
$procCount = $ocProcs.Count
$totalMB = 0.0
foreach ($x in $ocProcs) { $totalMB += [double]$x.WsMB }
$totalMB = [math]::Round($totalMB, 1)

Write-Log "INFO" "OpenCode 进程数=$procCount, 总内存=${totalMB}MB"

# ---- 2a. 单进程超内存 ----
$killedList = New-Object System.Collections.ArrayList
$reasonList = New-Object System.Collections.ArrayList
foreach ($p in @($ocProcs)) {
    if ($p.WsMB -gt $MAX_OPENCODE_SINGLE_MB) {
        [void]$reasonList.Add("single_pid=$($p.Id) ws=$($p.WsMB)MB > ${MAX_OPENCODE_SINGLE_MB}MB")
        try {
            Stop-Process -Id $p.Id -Force -ErrorAction Stop
            [void]$killedList.Add([int]$p.Id)
            Write-Log "WARN" "Killed opencode PID=$($p.Id) (ws=$($p.WsMB)MB) reason=single_memory"
        } catch {
            Write-Log "ERROR" "Failed to kill PID=$($p.Id): $($_.Exception.Message)"
        }
    }
}

# 重新拉
$ocProcs = Get-OcSnapshot
$procCount = $ocProcs.Count
$totalMB = 0.0
foreach ($x in $ocProcs) { $totalMB += [double]$x.WsMB }
$totalMB = [math]::Round($totalMB, 1)

# ---- 2b. 总内存超限 ----
if ($totalMB -gt $MAX_OPENCODE_TOTAL_MB) {
    [void]$reasonList.Add("total=${totalMB}MB > ${MAX_OPENCODE_TOTAL_MB}MB")
    foreach ($p in @($ocProcs)) {
        $curTotal = 0.0
        foreach ($x in $ocProcs) { $curTotal += [double]$x.WsMB }
        $curTotal = [math]::Round($curTotal, 1)
        if ($curTotal -le $KEEP_OPENCODE_TOTAL_MB) { break }
        try {
            Stop-Process -Id $p.Id -Force -ErrorAction Stop
            [void]$killedList.Add([int]$p.Id)
            Write-Log "WARN" "Killed opencode PID=$($p.Id) (ws=$($p.WsMB)MB) reason=total_memory (cur=${curTotal}MB)"
            # 从数组中移除
            $newArr = New-Object System.Collections.ArrayList
            foreach ($x in $ocProcs) { if ($x.Id -ne $p.Id) { [void]$newArr.Add($x) } }
            $ocProcs = @($newArr)
        } catch {
            Write-Log "ERROR" "Failed to kill PID=$($p.Id): $($_.Exception.Message)"
        }
    }
    # 重新算
    $procCount = $ocProcs.Count
    $totalMB = 0.0
    foreach ($x in $ocProcs) { $totalMB += [double]$x.WsMB }
    $totalMB = [math]::Round($totalMB, 1)
}

# ---- 2c. 进程数超限 ----
if ($procCount -gt $MAX_OPENCODE_COUNT) {
    [void]$reasonList.Add("count=$procCount > $MAX_OPENCODE_COUNT")
    $toKill = $procCount - $MAX_OPENCODE_COUNT
    $i = 0
    foreach ($p in $ocProcs) {
        if ($i -ge $toKill) { break }
        try {
            Stop-Process -Id $p.Id -Force -ErrorAction Stop
            [void]$killedList.Add([int]$p.Id)
            Write-Log "WARN" "Killed opencode PID=$($p.Id) (ws=$($p.WsMB)MB, start=$($p.StartTimeStr)) reason=count_exceeded"
        } catch {
            Write-Log "ERROR" "Failed to kill PID=$($p.Id): $($_.Exception.Message)"
        }
        $i++
    }
    $ocProcs = Get-OcSnapshot
    $procCount = $ocProcs.Count
    $totalMB = 0.0
    foreach ($x in $ocProcs) { $totalMB += [double]$x.WsMB }
    $totalMB = [math]::Round($totalMB, 1)
}

# ---- 3. daemon 健康 ----
$daemonAlive   = $false
$daemonPid     = 0
$portListening = $false
try {
    $conn = @(Get-NetTCPConnection -LocalPort $DAEMON_PORT -State Listen -ErrorAction Stop)
    if ($conn.Count -gt 0) {
        $portListening = $true
        $daemonPid = [int]$conn[0].OwningProcess
        $daemonAlive = ($null -ne (Get-Process -Id $daemonPid -ErrorAction SilentlyContinue))
    }
} catch { }

# ---- 4. MiniMax Code 主进程 ----
$mainProcs = @(Get-Process -Name "MiniMax Code" -ErrorAction SilentlyContinue)
$mainCount = $mainProcs.Count
$mainWsSum = 0.0
foreach ($p in $mainProcs) { try { $mainWsSum += [double]$p.WorkingSet64 } catch { } }
$mainWsMB  = [math]::Round($mainWsSum / 1MB, 1)

# ---- 5. 系统内存压力 ----
$os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
$totalPhysMB = 0
$freePhysMB  = 0
if ($os) {
    try { $totalPhysMB = [math]::Round($os.TotalVisibleMemorySize / 1KB, 0) } catch { }
    try { $freePhysMB  = [math]::Round($os.FreePhysicalMemory / 1KB, 0) } catch { }
}
$memPressurePct = 0.0
if ($totalPhysMB -gt 0) { $memPressurePct = [math]::Round((1 - $freePhysMB / $totalPhysMB) * 100, 1) }

# ---- 6. 报告 ----
$procsOut = New-Object System.Collections.ArrayList
foreach ($p in $ocProcs) {
    [void]$procsOut.Add(@{
        pid   = [int]$p.Id
        start = [string]$p.StartTimeStr
        ws_mb = [double]$p.WsMB
        cpu   = [double]$p.CPU
    })
}
$killedOut = New-Object System.Collections.ArrayList
foreach ($kpid in $killedList) { [void]$killedOut.Add(@{ pid = [int]$kpid }) }
$reasonOut = @()
foreach ($r in $reasonList) { $reasonOut += [string]$r }

$report = @{
    ts           = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    opencode     = @{
        count    = $procCount
        total_mb = $totalMB
        procs    = @($procsOut)
    }
    killed       = @($killedOut)
    kill_reasons = $reasonOut
    daemon       = @{
        port      = $DAEMON_PORT
        listening = $portListening
        alive     = $daemonAlive
        pid       = $daemonPid
    }
    main_app     = @{
        name  = "MiniMax Code"
        count = $mainCount
        ws_mb = $mainWsMB
    }
    system       = @{
        total_phys_mb    = $totalPhysMB
        free_phys_mb     = $freePhysMB
        mem_pressure_pct = $memPressurePct
    }
    thresholds   = @{
        max_count     = $MAX_OPENCODE_COUNT
        max_single_mb = $MAX_OPENCODE_SINGLE_MB
        max_total_mb  = $MAX_OPENCODE_TOTAL_MB
        keep_total_mb = $KEEP_OPENCODE_TOTAL_MB
    }
}

$json = $report | ConvertTo-Json -Depth 6 -Compress
Write-Output $json

$killedStr = ""
foreach ($k in $killedList) { if ($killedStr) { $killedStr += "," }; $killedStr += [string]$k }
Write-Log "INFO" "summary: killed=$killedStr daemon_listening=$portListening mem_pressure=${memPressurePct}%"

# ---- 7. 严重情况 ----
if (-not $portListening) {
    Write-Log "CRIT" "daemon port $DAEMON_PORT NOT listening! 建议：触发应用重启 (Stop-Process 'MiniMax Code' 会被 Hermes-Setup 自动拉起)"
}
if ($memPressurePct -gt 90) {
    Write-Log "WARN" "系统内存压力 ${memPressurePct}%！free=${freePhysMB}MB / total=${totalPhysMB}MB"
}
