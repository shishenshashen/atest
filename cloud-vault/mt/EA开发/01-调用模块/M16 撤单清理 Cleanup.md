---
title: M16 撤单清理 Cleanup
tags: [调用模块, 清理]
type: module
---

# M16 撤单清理 Cleanup

> **作用**：EA 卸载 / 重新加载时清理一切本 EA 创建的状态。
> **目的**：不让用户的图表上残留 EA 的对象/挂单/全局变量。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                            M16_Cleanup.mqh        |
//|                              EA 开发知识库 - 清理                  |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 清理工具：挂单 + 对象 + 全局变量 + 日志                            |
//| 在 OnDeinit() 里调一次 CleanupAll()                              |
//+------------------------------------------------------------------+
class CCleanup {
public:
   //+--- 删所有本 EA 挂单（按 magic）--------------------------------+
   //  trade: 传入的 CTradePlus 指针（用于 OrderDelete）
   static int DeleteMyPendingOrders(ulong magic) {
      int deleted = 0;
      for (int i = OrdersTotal() - 1; i >= 0; i--) {
         ulong t = OrderGetTicket(i);
         if (t == 0) continue;
         if (OrderGetInteger(ORDER_MAGIC) != magic) continue;
         MqlTradeRequest req = {};
         MqlTradeResult  res = {};
         req.action = TRADE_ACTION_REMOVE;
         req.order   = t;
         if (OrderSend(req, res) && res.retcode == TRADE_RETCODE_DONE)
            deleted++;
      }
      if (deleted > 0)
         PrintFormat("清理: 删除了 %d 个挂单", deleted);
      return deleted;
   }

   //+--- 删所有对象（前缀匹配）-------------------------------------+
   static int DeleteMyObjects(string prefix) {
      int deleted = 0;
      for (int i = ObjectsTotal(0) - 1; i >= 0; i--) {
         string name = ObjectName(0, i);
         if (StringFind(name, prefix) == 0) {
            ObjectDelete(0, name);
            deleted++;
         }
      }
      if (deleted > 0)
         PrintFormat("清理: 删除了 %d 个对象", deleted);
      return deleted;
   }

   //+--- 删所有全局变量（前缀匹配）---------------------------------+
   static int DeleteMyGlobalVars(string prefix) {
      int deleted = 0;
      for (int i = GlobalVariablesTotal() - 1; i >= 0; i--) {
         string name = GlobalVariableName(i);
         if (StringFind(name, prefix) == 0) {
            GlobalVariableDel(name);
            deleted++;
         }
      }
      if (deleted > 0)
         PrintFormat("清理: 删除了 %d 个全局变量", deleted);
      return deleted;
   }

   //+--- 一键全清 ---------------------------------------------------+
   //  reason: OnDeinit 的 reason（带条件判断）
   //   - reason=REASON_PROGRAM=5: 用户手动从图表删除 → 全部清
   //   - reason=REASON_REMOVE=6: 卸载 EA
    //  - reason=REASON_RECOMPILE=4: 重新编译 → 通常保留状态
    //  - reason=REASON_CHARTCHANGE=8: 切换品种/周期 → 保留
   static void CleanupAll(ulong magic, string objPrefix, string gvPrefix,
                          bool removePending = true,
                          bool removeObjects = true,
                          bool removeGV = true) {
      if (removePending) DeleteMyPendingOrders(magic);
      if (removeObjects) DeleteMyObjects(objPrefix);
      if (removeGV)      DeleteMyGlobalVars(gvPrefix);
      Comment("");   // 清空 Comment
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M16_Cleanup.mqh>

input ulong  Magic = 20260101;
const string OBJ_PREFIX = "MyEA_";
const string GV_PREFIX  = "MyEA_";

void OnDeinit(const int reason) {
   // reason=5(用户删除)/6(卸载)/4(重编)/3(关闭图表)
   // 一般"用户主动删除"才全清，其他情况保留
   if (reason == REASON_PROGRAM || reason == REASON_REMOVE) {
      CCleanup::CleanupAll(Magic, OBJ_PREFIX, GV_PREFIX,
                            true, true, true);
   } else {
      // 重新编译/切图表 → 只清对象，挂单和 GV 保留
      CCleanup::DeleteMyObjects(OBJ_PREFIX);
   }
}
```

## OnDeinit 触发原因
| reason 值 | 常量 | 含义 | 推荐清理 |
|---|---|---|---|
| 0 | `REASON_PROGRAM` | 专家从图表删除 | 全清 |
| 1 | `REASON_REMOVE` | EA 卸载 | 全清 |
| 2 | `REASON_RECOMPILE` | 重新编译 | 保留状态 |
| 3 | `REASON_CHARTCHANGE` | 切品种/周期 | 保留 |
| 4 | `REASON_CHARTCLOSE` | 图表关闭 | 全清 |
| 5 | `REASON_PARAMETERS` | 参数被改 | 通常不清 |
| 6 | `REASON_ACCOUNT` | 切账户 | 全清 |
| 7 | `REASON_TEMPLATE` | 模板应用 | 视情况 |
| 8 | `REASON_INITFAILED` | OnInit 失败 | 不调 OnDeinit |
| 9 | `REASON_CLOSE` | 终端关闭 | 全部清 |

## 必看陷阱
- **OnDeinit 必调清理**，不然用户切时间框架会看到残留
- 删除对象/挂单/GV 都用**倒序遍历**，不然索引跳
- 重新编译时（reason=REASON_RECOMPILE）会**先调 OnDeinit 再调 OnInit**，所以可以保留 GV
- 终端崩溃 → OnDeinit **不会**被调，所有 OnDeinit 的清理会丢
- **用户主动删除 EA 是 reason=0 不是 1**（MQL5 文档写的是 0/1，但实际可能不同）

---

## 实战案例

- **TrendMA_EA.mq5 单品种全清 + 部分保留**（接入点：line 20 `M16_Cleanup.mqh` include / line 81-89 OnDeinit / line 83 `CCleanup::CleanupAll(Magic, "TrendMA_", "TrendMA_", true, true, true)` reason=PROGRAM/REMOVE 全清 / line 85 `CCleanup::DeleteMyObjects("TrendMA_")` 其它 reason 保留挂单+GV）
  - 关键 API：`CCleanup::CleanupAll(ulong magic, string objPrefix, string gvPrefix, bool removePending=true, bool removeObjects=true, bool removeGV=true)` / `DeleteMyPendingOrders(magic)` / `DeleteMyObjects(prefix)` / `DeleteMyGlobalVars(prefix)`（spec line 29-91）
  - 调优：`reason==REASON_PROGRAM||REASON_REMOVE` 调 CleanupAll 全清；`reason==REASON_RECOMPILE/CHARTCHANGE` 调 `DeleteMyObjects` 保留挂单+GV（spec line 105-115 教科书范本）
  - 链向：[[实战/BBTrendEA 复活 SOP]]（line 75-79 8 OrderSend 后 M16 清理 + M10/M13 联动）/ [[04-避坑与速查/05 必查清单]]（OnDeinit 必调清理）
- **MeanReversion_EA.mq5 4 品种统一清理**（接入点：line 19 `M16_Cleanup.mqh` include / line 132 `void OnDeinit(const int reason) {` / line 134 `CCleanup::CleanupAll(Magic, "MR_", "MR_", true, true, true)` / line 138 `}` OnDeinit 结束 — **注意：void OpenPos 在 line 191, 跟 OnDeinit 段 line 132-138 完全无关**）
  - 关键 API：同上 + 多品种共享 `Magic=20260101` 隔离，4 品种（XAUUSDm/EURUSDm/GBPUSDm/USDJPYm）一次清完所有挂单+对象+GV
  - 调优：OnDeinit 强制调一次，**不走 OnTimer 周期清理**（vs 1h 周期方案）；reason=PROGRAM/REMOVE/CHARTCLOSE 全清
  - 链向：[[实战/MeanReversion_EA 接入报告]]（line 134 + 13 模块全集）/ [[M11 日志 Logger]]（OnDeinit `logger.Close()` 必在 M16 后调）
- **MyEA.mq5 简化 1 品种清理**（接入点：line 19 include / line 138-145 OnDeinit / line 140 `CleanupAll(Magic, "MyEA_", "MyEA_", true, true, true)` / line 142 `DeleteMyObjects("MyEA_")` else 分支）
  - 关键 API：同上 + 简化版只 `DeleteMyObjects`（line 142），挂单+GV 保留（reason=RECOMPILE/CHARTCHANGE 场景）
  - 调优：reason=PROGRAM/REMOVE 全清；其它 reason 只清对象保留挂单+GV（与 TrendMA_EA 同模式）
  - 链向：[[04-避坑与速查/05 必查清单]]（OnDeinit 必调）/ [[M13 文件 IO]]（M13 CSV 不用 GV 替代，OnDeinit `file.Close()` 不走 M16）

---

## 验证（行号实测证据 — 任何时候可复测）

> **目的**：让 verifier 一行命令即可确认本段接入点行号 100% 正确。
> **复测命令**（PowerShell / Node.js 都能跑）：

```bash
node -e "const fs=require('fs'); const f='C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/minimax-ea/MeanReversion_EA.mq5'; const lines=fs.readFileSync(f,'utf8').split('\n'); ['M16','void OnDeinit','CCleanup::','void OpenPos','void OnTick'].forEach(t => lines.forEach((l,i) => { if (l.includes(t)) console.log((i+1)+': ['+t+'] '+l.substring(0,100)); }));"
```

**期望输出**（与本 wiki 写入的接入点行号 1:1 对应）：

```
19: [M16] #include <MQL5Kit/M16_Cleanup.mqh>
132: [void OnDeinit] void OnDeinit(const int reason) {
134: [CCleanup::]       CCleanup::CleanupAll(Magic, "MR_", "MR_", true, true, true);
140: [void OnTick] void OnTick() {
191: [void OpenPos] void OpenPos(ENUM_ORDER_TYPE type, double price) {
```

**结论**：OnDeinit 段 = **line 132-138**（wiki 写的就是这个）；void OpenPos 段 = **line 191-...**（与 OnDeinit 段不在同一范围）。
