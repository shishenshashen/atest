---
title: MQL5 编译错误速修
type: fix-case
tags: [mql5, mt5, compile-error, ea]
date: 2026-06-03
applies-to: MQL5 严格模式（所有新版 MetaTrader 5）
---

# MQL5 编译错误速修

> **场景**: 4 个 minimax-ea EA 卡在 11 errors 区间不动，从 11:47 的 100+ 错误降到 11:53 的
> 11-15 错误后停滞。修了 5 个文件后 0 errors。
> 根因不是代码逻辑，而是 MQL5 编译器严格性 + 重命名/类型/常量三类常见坑。

## 一、3 类常见编译错误

| 类别 | 错误码 | 根因 | 修法 |
|---|---|---|---|
| **变量名冲突** | `error 282: identifier already used` | 用了 MQL5 内置函数名当变量 | 改名 |
| **枚举类型不匹配** | `error 262: cannot convert enum` | 内置函数要 `ENUM_*` 但收到 `int` | 形参/实参加 enum 类型 |
| **常量名拼错** | `error 256: undeclared identifier` | 旧 MQL4 习惯写错 retcode 常量 | 查 `MQL5\Include\Trade\Trade.mqh` |

## 二、MQL5 内置函数名黑名单（不能当变量名）

```cpp
log()        // math.log 自然对数
Comment()    // 图表注释
Print()      // 打印
Alert()      // 弹窗
SendMail()   // 发邮件
ObjectCreate() // 图形对象
```

**判定方法**: 编译报 `error 282: identifier 'X' already used` + `info built-in 'X'`，就说明 X
是内置函数。

**修法**: rename。我用 `logger` 替 `log`、`EAComment` 替 `Comment`。

## 三、内置指标的形参类型（必须严格）

| 函数 | 形参 2 | 形参 3 | 形参 4 | 形参 5 |
|---|---|---|---|---|
| `iMA` | `ENUM_TIMEFRAMES` | `int ma_period` | `int ma_shift` | `ENUM_MA_METHOD` |
| `iRSI` | `ENUM_TIMEFRAMES` | `int period` | `ENUM_APPLIED_PRICE` | — |
| `iBands` | `ENUM_TIMEFRAMES` | `int period` | `int bands_shift` | `double deviation` |
| `iStochastic` | `ENUM_TIMEFRAMES` | `int %K period` | `int %D period` | `int slowing` |
| `iADX` | `ENUM_TIMEFRAMES` | `int adx_period` | — | — |
| `iMACD` | `ENUM_TIMEFRAMES` | `int fast_ema` | `int slow_ema` | `int signal` |

**坑**: 你写 `int method = MODE_SMA;` 看起来通用，但 MQL5 编译器在把 `method` 传给 `iMA(..., ENUM_MA_METHOD method, ...)` 时会报 `error 262`。

**修法**: 形参直接用枚举类型

```cpp
// 错
int AddMA(string name, int period, int method = MODE_SMA, int applied = PRICE_CLOSE, int shift = 0) {
   return _Add(name, iMA(_Symbol, _Period, period, shift, method, applied), 0);
}

// 对
int AddMA(string name, int period, ENUM_MA_METHOD method = MODE_SMA, ENUM_APPLIED_PRICE applied = PRICE_CLOSE, int shift = 0) {
   return _Add(name, iMA(_Symbol, _Period, period, shift, method, applied), 0);
}
```

## 四、TRADE_RETCODE 常量名（容易写错的）

MQL5 实际名（2024+ 版）：

```
TRADE_RETCODE_REJECT
TRADE_RETCODE_CANCEL
TRADE_RETCODE_REQUOTE
TRADE_RETCODE_DONE
TRADE_RETCODE_DONE_PARTIAL
TRADE_RETCODE_PLACED
TRADE_RETCODE_ERROR
TRADE_RETCODE_TIMEOUT
TRADE_RETCODE_INVALID
TRADE_RETCODE_INVALID_VOLUME      ← 不是 VOLUME
TRADE_RETCODE_INVALID_PRICE
TRADE_RETCODE_INVALID_STOPS
TRADE_RETCODE_INVALID_FILL
TRADE_RETCODE_INVALID_EXPIRATION
TRADE_RETCODE_TRADE_DISABLED
TRADE_RETCODE_MARKET_CLOSED
TRADE_RETCODE_NO_MONEY            ← 不是 FUNDS
TRADE_RETCODE_PRICE_CHANGED
TRADE_RETCODE_PRICE_OFF
TRADE_RETCODE_ORDER_CHANGED
TRADE_RETCODE_TOO_MANY_REQUESTS
TRADE_RETCODE_NO_CHANGES
TRADE_RETCODE_LOCKED
TRADE_RETCODE_FROZEN
TRADE_RETCODE_CONNECTION
TRADE_RETCODE_ONLY_REAL
TRADE_RETCODE_LIMIT_ORDERS
TRADE_RETCODE_LIMIT_VOLUME
TRADE_RETCODE_POSITION_CLOSED
TRADE_RETCODE_INVALID_ORDER
TRADE_RETCODE_CLOSE_ORDER_EXIST
TRADE_RETCODE_LIMIT_POSITIONS
```

**权威表位置**: `MQL5\Include\Trade\Trade.mqh` line 1290-1380（`RequestRetcodeDescription` 函数里的 switch case）。

## 五、boolean 表达式（MQL5 严格模式）

```cpp
// 错: f & FLAG 是 long 不是 bool
long f = SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
if (f & SYMBOL_FILLING_FOK) SetTypeFilling(ORDER_FILLING_FOK);  // warning 39

// 对
if ((f & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK) SetTypeFilling(ORDER_FILLING_FOK);
```

只是 warning，不阻塞编译。但严格模式会标记。

## 六、空注释破坏表达式（次要但很坑）

```cpp
// 错: && 后面是注释占位，编译失败
if (AllowLong && /* BuySignal  */) TryOpen(ORDER_TYPE_BUY);
if (AllowShort && /* SellSignal */) TryOpen(ORDER_TYPE_SELL);

// 对: 直接去掉占位
if (AllowLong)  TryOpen(ORDER_TYPE_BUY);
if (AllowShort) TryOpen(ORDER_TYPE_SELL);
```

报错: `error 223: '&&' - operand expected` + `warning 69: empty controlled statement`

## 七、批量验证脚本（PowerShell）

```powershell
# 编译指定 mq5 列表并解析行级错误
$files = @(
  "C:\path\to\EA1.mq5",
  "C:\path\to\EA2.mq5"
)
foreach ($f in $files) {
  $log = "C:\path\to\compile_$((Get-Item $f).BaseName).log"
  if (Test-Path $log) { Clear-Content $log }

  # metaeditor64 不会自动退出，必须 10s 后强杀
  $p = Start-Process 'C:\Program Files\MetaTrader 5\metaeditor64.exe' `
    -ArgumentList "/compile:`"$f`" /log:`"$log`"" -NoNewWindow -PassThru
  Start-Sleep -Seconds 10
  if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }

  # 解析行级错误
  $content = Get-Content $log -Raw
  $content | Select-String -Pattern '\(\d+,\d+\) : error \d+' | ForEach-Object { $_.Matches.Value }
  if ($content -match 'Result: (.+?)$') { Write-Host "[$((Get-Item $f).BaseName)] $($matches[1])" }
}
```

**注意**:
- `metaeditor64.exe /compile` **不会自动退出**（GUI 卡在编辑器里），必须 `Stop-Process` 强杀
- `/log:<path>` 输出包含行号 + 错误码 + 错误描述，比 GUI 错误面板可解析得多
- `Start-Sleep -Seconds 10` 是经验值，简单 EA 够用，复杂 EA 可调大

## 八、本次任务实际改的 5 个文件

| 文件 | 改了什么 | 行数 |
|---|---|---|
| `MQL5Kit/M01_CTradePlus.mqh` | retcode 名 (2 处) + boolean 表达式 (2 处) | line 26-28, 220-221 |
| `MQL速修/M04_IndicatorPool.mqh` | 7 个 Add* 形参 int → enum | line 26-46 |
| `TrendMA_EA.mq5` | `log` → `logger` | line 50, 73, 130, 133 |
| `MyEA.mq5` | `log` → `logger` + `Comment` → `EAComment` + 删空注释 | 5+3+2 处 |
| `MeanReversion_EA.mq5` | `log` → `logger` | line 44, 61, 108, 111 |

## 九、相关链接

- 完整任务进度: [[worker-A-编译修复]]
- MQL5 retcode 完整定义: `C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Include\Trade\Trade.mqh` line 1290-1380
- metaeditor64 入口: `C:\Program Files\MetaTrader 5\metaeditor64.exe`
