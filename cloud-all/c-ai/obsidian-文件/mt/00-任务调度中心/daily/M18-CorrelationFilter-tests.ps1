#requires -Version 5.1
<#
.SYNOPSIS
  M18 CorrelationFilter - Pearson correlation PowerShell equivalent unit test

.DESCRIPTION
  Reproduces M18._Pearson() algorithm in PowerShell (no MT5/MetaEditor
  dependency), runs 3 test cases to validate math correctness:
    TC1: Perfect positive correlation (XAUUSDm/EURUSDm 30 days sync) -> r ~ +1.0
    TC2: Perfect negative correlation (XAUUSDm/USDJPYm 30 days reverse) -> r ~ -1.0
    TC3: No correlation       (XAUUSDm/EURUSDm 30 days pseudo-random) -> r in [-0.3, +0.3]

  This script is the algorithm-equivalent of M18_CorrelationFilter.mqh::_Pearson().
  "Dual-track validation": MQL5 module compiles + math is correct.

.NOTES
  Author:  MQL5Kit track1-m18-correlation
  Date:    2026-06-04
  Version: 1.0
#>

#--- Disable strict mode to avoid uninitialized variable warnings ---
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

#--- Counters -------------------------------------------------------
$script:Pass = 0
$script:Fail = 0

#====================================================================
# Function: Get-Pearson
#   r = sum((xi-mx)*(yi-my)) / sqrt(sum((xi-mx)^2) * sum((yi-my)^2))
# Param : two equal-length double arrays (n = X.Length)
# Return: Pearson correlation coefficient (-1 ~ +1)
#         0 if data insufficient or zero variance
#====================================================================
function Get-Pearson {
    param(
        [Parameter(Mandatory)][double[]] $X,
        [Parameter(Mandatory)][double[]] $Y
    )
    $n = $X.Count
    if ($n -ne $Y.Count) { return 0.0 }
    if ($n -lt 2)        { return 0.0 }

    $mx = ($X | Measure-Object -Average).Average
    $my = ($Y | Measure-Object -Average).Average

    $sxy = 0.0
    $sxx = 0.0
    $syy = 0.0
    for ($i = 0; $i -lt $n; $i++) {
        $dx = $X[$i] - $mx
        $dy = $Y[$i] - $my
        $sxy += $dx * $dy
        $sxx += $dx * $dx
        $syy += $dy * $dy
    }
    if ($sxx -le 0 -or $syy -le 0) { return 0.0 }
    $denom = [Math]::Sqrt($sxx * $syy)
    if ($denom -le 0) { return 0.0 }
    $r = $sxy / $denom
    # Numerical clamp
    if ($r -gt  1.0) { $r =  1.0 }
    if ($r -lt -1.0) { $r = -1.0 }
    return $r
}

#====================================================================
# Function: Test-Corr
#   Runs one test case, computes Pearson coefficient, checks range
#   - Prints [PASS]/[FAIL]
#   - Increments $script:Pass / $script:Fail
# Returns: $true = PASS, $false = FAIL
#====================================================================
function Test-Corr {
    param(
        [Parameter(Mandatory)][string]   $Name,
        [Parameter(Mandatory)][string]   $Sym1,
        [Parameter(Mandatory)][string]   $Sym2,
        [Parameter(Mandatory)][double[]] $Data1,
        [Parameter(Mandatory)][double[]] $Data2,
        [Parameter(Mandatory)][double]   $ExpectedLo,
        [Parameter(Mandatory)][double]   $ExpectedHi
    )

    $r = Get-Pearson -X $Data1 -Y $Data2
    $ok = ($r -ge $ExpectedLo -and $r -le $ExpectedHi)
    if ($ok) {
        $script:Pass++
        $status = '[PASS]'
    } else {
        $script:Fail++
        $status = '[FAIL]'
    }
    $line = "{0} {1} {2}/{3} r={4:N4}  expected=[{5:N2}, {6:N2}]" -f `
            $status, $Name, $Sym1, $Sym2, $r, $ExpectedLo, $ExpectedHi
    Write-Host $line
    return $ok
}

#====================================================================
# Prepare test data (synthetic close prices)
#====================================================================

#--- TC1: Perfect positive correlation -----------------------------
# XAUUSDm / EURUSDm 30-day close, perfectly synchronized (Y = 0.85*X + 100)
# Base 1900 USD, +0.5 USD per day
$xau = New-Object double[] 30
$eur = New-Object double[] 30
for ($i = 0; $i -lt 30; $i++) {
    $xau[$i] = 1900.0 + $i * 0.5
    $eur[$i] = 0.85 * $xau[$i] + 100.0   # Perfect positive
}

#--- TC2: Perfect negative correlation -----------------------------
# XAUUSDm / USDJPYm 30-day close, perfectly reversed (Y = -1.0*X + 200)
$jpy = New-Object double[] 30
for ($i = 0; $i -lt 30; $i++) {
    $jpy[$i] = -1.0 * $xau[$i] + 200.0   # Perfect negative
}

#--- TC3: No correlation (deterministic PRNG, N=30) ----------------
# Use Linear Congruential Generator (LCG) for reproducible sequence
$eurRand = New-Object double[] 30
$seed = 12345
for ($i = 0; $i -lt 30; $i++) {
    $seed = ($seed * 1103515245 + 12345) -band 0x7FFFFFFF
    $r01 = $seed / [double]([Math]::Pow(2, 31) - 1)   # 0..1
    # Simulate EURUSDm independent close 1.05~1.15
    $eurRand[$i] = 1.05 + $r01 * 0.10
}

#====================================================================
# Run tests
#====================================================================
Write-Host "================================================================"
Write-Host " M18 CorrelationFilter - Pearson algorithm PowerShell test"
Write-Host "================================================================"
Write-Host ("Start time: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Write-Host ""

# TC1
Test-Corr -Name "TC1 perfect-positive" `
          -Sym1 "XAUUSDm" -Sym2 "EURUSDm" `
          -Data1 $xau -Data2 $eur `
          -ExpectedLo 0.99 -ExpectedHi 1.00

# TC2
Test-Corr -Name "TC2 perfect-negative" `
          -Sym1 "XAUUSDm" -Sym2 "USDJPYm" `
          -Data1 $xau -Data2 $jpy `
          -ExpectedLo -1.00 -ExpectedHi -0.99

# TC3
Test-Corr -Name "TC3 no-correlation" `
          -Sym1 "XAUUSDm" -Sym2 "EURUSDm" `
          -Data1 $xau -Data2 $eurRand `
          -ExpectedLo -0.30 -ExpectedHi 0.30

#====================================================================
# Summary
#====================================================================
Write-Host ""
Write-Host "================================================================"
$total = $script:Pass + $script:Fail
Write-Host ("Result: {0} PASS, {1} FAIL (total {2})" -f $script:Pass, $script:Fail, $total)
Write-Host "================================================================"

if ($script:Fail -gt 0) {
    Write-Host "FAIL: some tests failed - Pearson implementation may have a bug" -ForegroundColor Red
    exit 1
} else {
    Write-Host "OK: all tests passed - M18._Pearson() algorithm validated" -ForegroundColor Green
    exit 0
}
