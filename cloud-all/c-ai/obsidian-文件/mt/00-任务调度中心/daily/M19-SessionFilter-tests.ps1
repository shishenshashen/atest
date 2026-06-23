# M19-SessionFilter-tests.ps1
# PowerShell unit tests for M19 SessionFilter module.
#
# 4 test cases (per track2 N3 task spec):
#   TC1 Weekend:         Sat 2026-06-06 12:00 UTC -> IsInSession(London+NY) = false (no weekend)
#   TC2 Weekday Asia:    Wed 2026-06-03 03:00 UTC -> IsInSession(Asia)        = true  (3:00 in [0,8))
#   TC3 Weekday L+NY:    Wed 2026-06-03 15:00 UTC -> IsInSession(London+NY)   = true  (15:00 in [13,22))
#   TC4 Weekday off:     Wed 2026-06-03 23:30 UTC -> IsInSession(Asia only)   = false (23:00 not in [0,8))
#
# 验证方式:
#   - PowerShell 端用与 M19 完全一致的简化算法 (Get-SessionInRange 辅助函数)
#     重实现 IsInSession 逻辑, 跟 .mqh 端 RunSelfTest() 配套;
#   - MQL5 端通过 MetaEditor 编译验证 0 errors, 然后 EA 在 Strategy Tester
#     跑出的 [INFO]/[PASS] 行由 journal 抓取 (见 M19 wiki §5 单元测试);
#   - 本脚本只验证"逻辑契约", 不依赖 MT5 instance, 离线可跑.
#
# 用法:
#   pwsh C:\ai\obsidian-文件\mt\00-任务调度中心\daily\M19-SessionFilter-tests.ps1
#   pwsh ... -TestCase TC1,TC2  # 仅跑指定 case

[CmdletBinding()]
param(
    [string[]]$TestCase = @('TC1','TC2','TC3','TC4'),
    [switch]$VerboseMode
)

#----------------------------- helpers ----------------------------------------

# Get-DayOfWeek: 输入 DateTime, 返 0=Sun..6=Sat (跟 MqlDateTime.day_of_week 一致)
function Get-DayOfWeek {
    param([datetime]$dt)
    # .NET DayOfWeek: Sunday=0 .. Saturday=6
    return [int]$dt.DayOfWeek
}

# Test-Session <preset> <datetime> <expected>
#   preset   : "Asia:0-8" / "London:8-16" / "NewYork:13-22" / "London:8-16,NewYork:13-22" / 自定义
#   datetime : DateTime 对象 (用 [datetime]'...' 字面量构造)
#   expected : $true / $false
# 返: $true 表示测试通过, $false 失败
function Test-Session {
    param(
        [string]$preset,
        [datetime]$dt,
        [bool]$expected
    )

    $actual = $false  # 默认值, 周末或无匹配时段时保持 false
    # 1) 解析 preset -> 多个 [name, start, end] 时段
    $entries = $preset.Split(',')
    $sessions = @()
    foreach ($e in $entries) {
        $colon = $e.IndexOf(':')
        if ($colon -le 0) {
            Write-Warning "bad preset entry: $e"
            return $false
        }
        $name = $e.Substring(0, $colon).Trim()
        $range = $e.Substring($colon + 1).Trim()
        $dash = $range.IndexOf('-')
        if ($dash -le 0) {
            Write-Warning "bad range in entry: $e"
            return $false
        }
        $startH = [int]$range.Substring(0, $dash)
        $endH   = [int]$range.Substring($dash + 1)
        $sessions += [pscustomobject]@{ name=$name; start=$startH; end=$endH }
    }

    # 2) 周末: 默认 false (跟 M19._allowWeekend=false 一致)
    $dow = Get-DayOfWeek $dt
    if ($dow -eq 0 -or $dow -eq 6) {
        $actual = $false
    } else {
        # 3) 小时落在任一时段内
        # 注意: 用 [int]($dt.Hour) 强制 cast, 避免 PowerShell 解析成 [int]$dt
        $h = [int]($dt.Hour)  # 用 server local hour 跟 MqlDateTime.hour 假定一致
        $actual = $false
        foreach ($s in $sessions) {
            $in = $false
            $sStart = [int]($s.start)
            $sEnd   = [int]($s.end)
            if ($sStart -lt $sEnd) {
                $in = ($h -ge $sStart -and $h -lt $sEnd)
            } else {
                # 跨午夜: [start, 24) ∪ [0, end)
                $in = ($h -ge $sStart -or $h -lt $sEnd)
            }
            if ($in) { $actual = $true; break }
        }
    }

    $pass = ($actual -eq $expected)
    $color = if ($pass) { 'Green' } else { 'Red' }
    $symbol = if ($pass) { '[PASS]' } else { '[FAIL]' }
    $expStr = if ($expected) { 'true' } else { 'false' }
    $actStr = if ($actual)   { 'true' } else { 'false' }
    $msg = "  $symbol preset='$preset' dt=$($dt.ToString('yyyy-MM-dd HH:mm')) dow=$dow h=$($dt.Hour) expected=$expStr actual=$actStr"
    Write-Host $msg -ForegroundColor $color
    return $pass
}

#----------------------------- test cases ------------------------------------

$results = @()
$pass = 0
$fail = 0

Write-Host "`n=== M19 SessionFilter PowerShell 单元测试 ===" -ForegroundColor Cyan
Write-Host "时区假设: server local time == UTC (跟 MqlDateTime.hour 假定一致)" -ForegroundColor DarkGray
Write-Host ""

if ($TestCase -contains 'TC1') {
    Write-Host "TC1 周末: Sat 2026-06-06 12:00 UTC + London+NY -> 期望 false (周末不交易)" -ForegroundColor Yellow
    $r = Test-Session -preset "London:8-16,NewYork:13-22" -dt ([datetime]'2026-06-06 12:00') -expected $false
    $results += [pscustomobject]@{ Case='TC1'; Pass=$r }
}
if ($TestCase -contains 'TC2') {
    Write-Host "TC2 工作日 Asia: Wed 2026-06-03 03:00 UTC + Asia -> 期望 true (3:00 ∈ [0,8))" -ForegroundColor Yellow
    $r = Test-Session -preset "Asia:0-8" -dt ([datetime]'2026-06-03 03:00') -expected $true
    $results += [pscustomobject]@{ Case='TC2'; Pass=$r }
}
if ($TestCase -contains 'TC3') {
    Write-Host "TC3 工作日 London+NY overlap: Wed 2026-06-03 15:00 UTC + London+NY -> 期望 true (15:00 ∈ [13,22))" -ForegroundColor Yellow
    $r = Test-Session -preset "London:8-16,NewYork:13-22" -dt ([datetime]'2026-06-03 15:00') -expected $true
    $results += [pscustomobject]@{ Case='TC3'; Pass=$r }
}
if ($TestCase -contains 'TC4') {
    Write-Host "TC4 工作日 off-hours: Wed 2026-06-03 23:30 UTC + Asia only -> 期望 false (23:00 ∉ [0,8))" -ForegroundColor Yellow
    $r = Test-Session -preset "Asia:0-8" -dt ([datetime]'2026-06-03 23:30') -expected $false
    $results += [pscustomobject]@{ Case='TC4'; Pass=$r }
}

#----------------------------- summary ----------------------------------------

$pass = ($results | Where-Object { $_.Pass }).Count
$fail = ($results | Where-Object { -not $_.Pass }).Count
Write-Host ""
Write-Host "=== 汇总: $pass passed, $fail failed, total $($results.Count) ===" -ForegroundColor $(if ($fail -eq 0) { 'Green' } else { 'Red' })
if ($fail -gt 0) {
    Write-Host ""
    Write-Host "失败的 case:" -ForegroundColor Red
    $results | Where-Object { -not $_.Pass } | ForEach-Object { Write-Host "  - $($_.Case)" -ForegroundColor Red }
    exit 1
}
exit 0
