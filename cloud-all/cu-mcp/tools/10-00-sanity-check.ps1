# 10:00 cron 7-dim sanity check
$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== 1. Current time ==="
Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

Write-Host "`n=== 2. CU keep-alive HB (last 3 lines) ==="
$hb = Select-String -Path 'C:\Users\Administrator\cu_keepalive.log' -Pattern '^HB' | Select-Object -Last 3
foreach ($line in $hb) { Write-Host $line.Line }

Write-Host "`n=== 3. MT5 processes ==="
Get-Process -Name terminal64,MetaEditor64,metatester64 | Select-Object Name,Id,@{Name='Mem_MB';Expression={[int]($_.WorkingSet64/1MB)}} | Format-Table -AutoSize

Write-Host "`n=== 4. mavis team plan list ==="
& mavis team plan list 2>&1 | Select-Object -First 30

Write-Host "`n=== 5. mavis session list (status fields) ==="
& mavis session list 2>&1 | Out-File -FilePath C:\Users\Administrator\cu-mcp\tools\session-list-10-00.json -Encoding utf8
Get-Content C:\Users\Administrator\cu-mcp\tools\session-list-10-00.json | Select-String -Pattern '"sessionId"|"status"|"title"' | Select-Object -First 40

Write-Host "`n=== 6. Lock files ==="
$locks = Get-ChildItem 'C:\Users\Administrator\.mavis\plans\' -Filter '*.lock'
if ($locks.Count -gt 0) {
    $locks | Select-Object Name,Length | Format-Table -AutoSize
} else {
    Write-Host "0 lock files"
}

Write-Host "`n=== 7. keep-alive processes ==="
$ka = Get-Process -Name node -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*cu_keepalive*' }
if ($ka.Count -gt 0) {
    $ka | Select-Object Id,@{Name='Cmd';Expression={$_.CommandLine.Substring(0,[Math]::Min(80,$_.CommandLine.Length))}} | Format-Table -AutoSize
} else {
    Write-Host "0 keep-alive processes"
}
