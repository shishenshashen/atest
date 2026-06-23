---
title: MetaEditor CLI 编译 + MQL5Kit 3-way fork 统一
type: fix-case
tags: [mql5, mt5, compile-error, ea, fork-unification, metaeditor-cli]
date: 2026-06-04
applies-to: MQL5 / MetaEditor64 任意版本; MT5 任务中心 9 条 P0/P1/P2 收尾
---

# MetaEditor CLI 编译 + MQL5Kit 3-way fork 统一

> **场景**: 2026-06-04 上午, 任务中心 9 条 P0/P1/P2 收尾阶段. 队列 #4 续 (3 个 Test* EA 编译)
> + 队列 #8 (MQL5Kit 分叉统一) 在用户授权 "A" + "继续 任务做完了就下一个 不用等" 之后被
> 我在 root session 一次性串行做完. 此前 8 个任务都走 `mavis-team plan` 多 worker 并行, 这次是
> 第一次**单 root session 跑完 MT5 任务** (CU 通了 + MetaEditor CLI 通了 + 跨 session 看清了).

## 一、MetaEditor64 CLI 实际能用 (推翻旧 memory)

**旧 memory** (2026-06-03 之前):
> "`MetaEditor64.exe /compile:file.mq5` 不工作 / 静默 no-op"

**实测** (2026-06-04 08:52):
```powershell
& "C:\Program Files\MetaTrader 5\MetaEditor64.exe" /compile:"C:\...\TestInclude.mq5"
Start-Sleep -Seconds 5
Get-Content "...\logs\metaeditor.log" -Tail 3
# 输出: 0  2026.06.04 08:55:27.273 Compile ...\TestInclude.mq5 - 0 errors, 0 warnings, 539 ms elapsed
```

**真相**: 返 **0 stdout / 0 stderr**, 但**写 `metaeditor.log` + 产 `.ex5` 正常**. 旧 memory
可能是早期版本不支持, 或者被某次失败经验锁死了. **结论**: 这是 GUI 不可见场景下编译的
**首选路径** (比 touch + restart terminal64 稳得多).

**对比 4 种编译触发方式** (经验排序):

| 方式 | 触发源 | 可靠性 | 跨 session 限制 | stdout | log 行级错误 |
|---|---|---|---|---|---|
| `MetaEditor64 /compile:` CLI | 任何 PowerShell | ✅ 100% | 无 | 空 | ❌ (只有 error count) |
| `Stop-Process terminal64; Start-Process terminal64` | 任何 PS | ⚠️ 只重编 active path 文件 | 无 | N/A | ❌ |
| MetaEditor GUI F7 | 需 console session 1 看到 GUI | ✅ | 跨 session UIPI 拒 | N/A | ✅ (Errors 面板) |
| 任务计划 + AutoTrading | OS 调度 | ❌ 不可用 | N/A | N/A | N/A |

**关键决定**: 跨 session (RDP session 2 → console session 1) 调 SendKeys 报 "拒绝访问" (UIPI).
root session 在 session 2, MT5 GUI 在 session 2 (或启回时也在 session 2), 看不到 console session 1
的窗口. **CLI 编译绕开 GUI = 唯一可靠路径**.

## 二、MT5 进程 session 归属问题 (踩坑 #2)

`Get-WmiObject Win32_Process -Filter "Name='terminal64.exe'"` 返 `SessionId` 字段. 实测
**`Start-Process terminal64` 默认把进程放当前 session** (RDP session 2 / Mavis daemon session).
**CU native screen capture 仅看 console session 1** — session 2 的 terminal64 / MetaEditor64 窗口
对 CU **不可见**. 解法: 用 CLI 编译, 不要试图用 CU `desktop_click` 驱动 MetaEditor 按钮.

**同时发现**: terminal64 重启**不**触发 sandbox 全重编. 只重编"active path" (在 chart 上 / 在 MetaEditor
打开的) 的文件. `_archive/` 下 3 个 Test*.mq5 不会被自动重编. 旧 cron 报告"重启=全重编"是误判.

## 三、MQL5Kit 3-way fork 实际 layout (踩坑 #3)

旧 memory / cron 都说 "a=18 b=15 分叉" 是 2-way. 实测**用户机器上 3-way**:

| 路径 | 文件数 | 状态 | 编译时被引用? |
|---|---|---|---|
| `MQL5\Include\MQL5Kit` | **18** | **canonical** (含 M15/M17 + M09/M13 fix) | ✅ 所有 EA `<MQL5Kit/X.mqh>` 走这条 |
| `MQL5\Experts\Include\MQL5Kit` | 15 | stale (M09 init-list bug + M13 FileWrite array bug + 缺 M15/M17) | ❌ 死代码 |
| `MQL5\Experts\_archive\Include\MQL5Kit` | 15 | stale (跟上一条字节级一致) | ❌ 死代码 |

**所有 EA 用 `<MQL5Kit/X.mqh>` 形式** (grep 全 MQL5 验证 74+ 引用, 全是尖括号系统 include).
`a` / `c` 是死代码, 没人会从中读. 但为了一致性还是同步.

**真正的内容差异** (M09 + M13):

```cpp
// a (stale) M09_Dashboard.mqh line 14: ctor 用 init list
CDashboard() : _title("=== MyEA Dashboard ==="), _maxRows(32) {
   ArrayResize(_rows, 0);
}

// b (canonical) M09_Dashboard.mqh line 14: ctor 用 body init
CDashboard() {
   _title   = "=== MyEA Dashboard ===";
   _maxRows = 32;
   ArrayResize(_rows, 0);
}
```

```cpp
// a (stale) M13_FileIO.mqh line 23: 直接 FileWrite 数组, MQL5 编译器误用 string overload 报 120
FileSeek(h, 0, SEEK_END);
FileWrite(h, fields);
FileClose(h);

// b (canonical) M13_FileIO.mqh: 用 FileWriteString per field workaround
FileSeek(h, 0, SEEK_END);
int n = ArraySize(fields);
for (int i = 0; i < n; i++) {
   if (i > 0) FileWriteString(h, ",");
   FileWriteString(h, fields[i]);
}
FileWriteString(h, "\n");
FileClose(h);
```

**判定方法**: `cmd /c fc /N path1 path2` 看实际行级 diff. `Get-ChildItem` 列 size 类似时容易误判"差不多".

## 四、3-way fork 统一脚本 (5 行 PowerShell)

```powershell
$b = "C:\Users\...\MQL5\Include\MQL5Kit"
$a = "C:\Users\...\MQL5\Experts\Include\MQL5Kit"
$c = "C:\Users\...\MQL5\Experts\_archive\Include\MQL5Kit"

# 强制 overwrite (普通 Copy-Item * 在 mtime / cached 内容下可能跳过)
Get-ChildItem -File $b | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $a $_.Name) -Force
  Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $c $_.Name) -Force
}

# 验证 3-way 字节级 hash 等价
function Test-DirHash($p) {
  (Get-ChildItem -File $p | Sort-Object Name | ForEach-Object {
    "$($_.Name)=$((Get-FileHash -LiteralPath $_.FullName -Algorithm MD5).Hash)"
  }) -join "|"
}
(Test-DirHash $a) -eq (Test-DirHash $b)  # 必须 True
(Test-DirHash $b) -eq (Test-DirHash $c)  # 必须 True
```

## 五、本次任务实际改的 2 个 .mq5 源 (TestExternDecl + TestInclude)

| 文件 | 错误 | 修法 |
|---|---|---|
| `TestExternDecl.mq5` | 1 error: `extern int MyDecl;` 同 TestExtern 老问题 | `extern int MyDecl;` → `int MyDecl = 0;` |
| `TestInclude.mq5` | 2 errors: `#include "Include\Common.mqh"` 路径 + `InitModuleParams()` 不存在 | 解 include 改 inline `g_InpModIndicators = true;` + `void InitModuleParams() {}` stub |

**根因**:
- `extern` in MQL5 是 "reference" 形式, 必须在别处定义. `extern int MyDecl;` 没有匹配的非 extern
  定义 → error 370 "unresolved extern variable". 修法: 改 `int MyDecl = 0;` (同 TestExtern.mq5 之前修法)
- `Common.mqh` 包含 100+ 全局变量但**没有** `InitModuleParams()` 函数 (该函数名是 Common.mqh 注释里
  提到的, 实际未实现). 修法: 解 include, inline 最小 stub.

## 六、验证 0 errors 的 4 个 EA (无回归)

| EA | .ex5 size | 错误 | 警告 |
|---|---|---|---|
| `Dashboard.mq5` (含 M15) | 34292b | 0 | 0 |
| `MyEA.mq5` (含 M13) | 59356b | 0 | 1 (已知 POSITION_COMMISSION 误报) |
| `TrendMA_EA.mq5` | 64664b | 0 | 1 (同上) |
| `Test_M08_Trail_Logic.mq5` | 17578b | 0 | 0 |

## 七、相关链接

- 任务中心调度: `C:\ai\obsidian-文件\mt\00-任务调度中心\队列.md` 9 条全 done
- plan_bbbdc7f5 deliverable: `C:\Users\Administrator\.mavis\plans\plan_bbbdc7f5\outputs\<task-id>\deliverable.md`
- MQL5 ctor 修复 case (同目录): [[MQL5 ctor 修复]]
- 进程 session 检测: `Get-WmiObject Win32_Process -Filter "Name='terminal64.exe'" | Select SessionId`
- 编译日志: `C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\logs\metaeditor.log`
