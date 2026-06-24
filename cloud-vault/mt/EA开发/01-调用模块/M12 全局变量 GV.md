---
title: M12 全局变量 GV
tags: [调用模块, 持久化]
type: module
---

# M12 全局变量 GV

> **作用**：把状态（最后交易时间、当日盈亏、启动余额等）**持久化**到 MT5 终端。
> 终端重启后值还在。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                                 M12_GV.mqh        |
//|                              EA 开发知识库 - 全局变量              |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 全局变量：MT5 客户端级 key-value 存储                              |
//| 跨重启保持，重启 MT5 也还在                                      |
//| 比 GlobalVariableSet 更现代的替代：使用 MQL5 内置文件 API         |
//+------------------------------------------------------------------+
class CGV {
private:
   string _prefix;

public:
   CGV(string prefix = "MyEA") { _prefix = prefix + "_"; }

   // 拼 key：prefix + name
   string _K(string name) { return _prefix + name; }

   //+--- 写 ------------------------------------------------------+
   bool Set(string name, double value) {
      return GlobalVariableSet(_K(name), value);
   }
   bool Set(string name, string value) {
      // 字符串用 hash 存
      ulong hash = StringGetCharacter(value, 0);
      for (int i = 1; i < StringLen(value); i++)
         hash = (hash << 5) + hash + StringGetCharacter(value, i);
      return GlobalVariableSet(_K(name), (double)hash);
   }
   bool Set(string name, datetime value) {
      return GlobalVariableSet(_K(name), (double)value);
   }

   //+--- 读 ------------------------------------------------------+
   double Get(string name, double def = 0) {
      if (!GlobalVariableCheck(_K(name))) return def;
      return GlobalVariableGet(_K(name));
   }
   string GetStr(string name, string def = "") {
      // 简化：只存 double，字符串需要外部编码
      double v = Get(name, 0);
      if (v == 0) return def;
      return DoubleToString(v, 0);
   }
   datetime GetDt(string name, datetime def = 0) {
      return (datetime)(long)Get(name, (double)def);
   }

   //+--- 是否存在 ------------------------------------------------+
   bool Exists(string name) { return GlobalVariableCheck(_K(name)); }

   //+--- 删 ------------------------------------------------------+
   bool Del(string name) { return GlobalVariableDel(_K(name)); }

   //+--- 批量删自己的 -------------------------------------------+
   void DelAll() {
      int total = GlobalVariablesTotal();
      for (int i = total - 1; i >= 0; i--) {
         string name = GlobalVariableName(i);
         if (StringFind(name, _prefix) == 0) GlobalVariableDel(name);
      }
   }

   //+--- 持久化到文件（备选，更可靠）-------------------------------+
   //  全局变量偶尔会因终端异常丢失，写文件更稳
   bool SaveToFile(string filename, string &keys[], double &values[]) {
      int h = FileOpen(filename, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if (h == INVALID_HANDLE) return false;
      FileWrite(h, "key", "value");
      int n = MathMin(ArraySize(keys), ArraySize(values));
      for (int i = 0; i < n; i++) FileWrite(h, keys[i], values[i]);
      FileClose(h);
      return true;
   }

   bool LoadFromFile(string filename, string &keys[], double &values[]) {
      int h = FileOpen(filename, FILE_READ|FILE_CSV|FILE_COMMON, ',');
      if (h == INVALID_HANDLE) return false;
      // 跳过表头
      if (!FileIsEnding(h)) { FileReadString(h); FileReadString(h); }
      ArrayResize(keys, 0); ArrayResize(values, 0);
      while (!FileIsEnding(h)) {
         string k = FileReadString(h);
         if (FileIsEnding(h)) break;
         double v = FileReadNumber(h);
         int n = ArraySize(keys);
         ArrayResize(keys,   n + 1);
         ArrayResize(values, n + 1);
         keys[n]   = k;
         values[n] = v;
      }
      FileClose(h);
      return true;
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M12_GV.mqh>

CGV gv;

int OnInit() {
   // 启动时：记录启动时间、当日起点余额
   datetime startTime = (datetime)TimeCurrent();
   gv.Set("StartTime", startTime);
   gv.Set("StartBalance", AccountInfoDouble(ACCOUNT_BALANCE));
   gv.Set("LastTradeTime", 0);
   return INIT_SUCCEEDED;
}

void OnTick() {
   // 用 GV 拿"启动时间"
   datetime startTime = gv.GetDt("StartTime");
   Print("EA 已运行 ", TimeCurrent() - startTime, " 秒");

   // 一天只开一次
   datetime lastTrade = gv.GetDt("LastTradeTime");
   if (TimeCurrent() - lastTrade < 86400) return;  // 24h 内不下单

   // ... 交易 ...
   gv.Set("LastTradeTime", TimeCurrent());
}

void OnDeinit(const int reason) {
   gv.DelAll();   // 卸载时清理
}
```

## 何时用全局变量 vs 文件
| 需求 | 推荐 |
|---|---|
| 临时状态（< 1 周） | 全局变量 |
| 关键配置（API key、账户） | **文件** |
| 回测结果、性能数据 | **文件**（CSV 方便 Excel 分析）|
| 跨终端同步 | 都不行（用云）|

## 必看陷阱
- **全局变量名全局唯一**，加前缀避免冲突
- 终端卸载或重装可能清掉 GV → 重要数据写文件
- 文件名要带路径（`FILE_COMMON` 标志用公用目录）
- `FileReadString` / `FileReadNumber` 调用顺序必须跟写入顺序一致

---

## 实战案例

- **当前 minimax-ea/ 0/10 EA 使用 M12**（P2 频次，仅 spec 范本）
  - 关键 API：`CGV::Set(string name, double value)` / `Get(string name, double def=0)` / `Del(string name)` / `DelAll()` / `Exists(string name)` / `SaveToFile` / `LoadFromFile`（spec line 37-105）
  - 调优：用 M16 `CCleanup::CleanupAll(magic, objPrefix, gvPrefix, true, true, true)` 统一清理（spec line 83-91），避免 OnDeinit 漏 GV → 重启后留垃圾
  - 链向：[[M16 撤单清理 Cleanup]]（`DeleteMyGlobalVars(prefix)` spec line 63-75 倒序遍历）/ [[实战/MeanReversion_EA 接入报告]]（line 60+136 M11 logger 替代 GV 做持久化）/ [[00-快速开始/EA 写之前要知道的 10 件事]] §5 持久化选 GV 还是文件
