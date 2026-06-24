---
title: M14 画图 Drawer
tags: [调用模块, 画图]
type: module
---

# M14 画图 Drawer

> **作用**：在图表上画买卖箭头、水平止损线、矩形背景等。
> **比 ObjectCreate 简单**，名字自动加前缀避免冲突。

## 完整代码

```mql5
//+------------------------------------------------------------------+
//|                                             M14_Drawer.mqh       |
//|                              EA 开发知识库 - 画图                  |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| 画图工具：自动命名 + 前缀清理                                     |
//+------------------------------------------------------------------+
class CDrawer {
private:
   string _prefix;   // 名字前缀（避免与其他 EA 冲突）
   int    _counter;  // 内部计数器

public:
   CDrawer(string prefix = "MyEA") : _prefix(prefix), _counter(0) {}

   // 唯一名字
   string Next(string label) {
      _counter++;
      return _prefix + "_" + label + "_" + IntegerToString(_counter);
   }

   //+--- 箭头（买卖信号）-------------------------------------------+
   //  shift: K 线索引（0=最新）
   //  code: 233=上, 234=下, 159=左, 160=右, 174=星
   bool Arrow(string name, datetime t, double price, int code, color clr) {
      string n = _prefix + "_" + name;
      ObjectCreate(0, n, OBJ_ARROW, 0, t, price);
      ObjectSetInteger(0, n, OBJPROP_ARROWCODE, code);
      ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, n, OBJPROP_WIDTH, 3);
      ChartRedraw(0);
      return true;
   }

   // 画买入箭头（最常用）
   bool BuyArrow(datetime t, double price) {
      return Arrow("Buy", t, price, 233, clrLime);
   }
   // 画卖出箭头
   bool SellArrow(datetime t, double price) {
      return Arrow("Sell", t, price, 234, clrRed);
   }
   // 上箭头（提示）
   bool UpArrow(datetime t, double price, color clr = clrYellow) {
      return Arrow("Up", t, price, 233, clr);
   }
   // 下箭头
   bool DownArrow(datetime t, double price, color clr = clrOrange) {
      return Arrow("Down", t, price, 234, clr);
   }

   //+--- 水平线 ----------------------------------------------------+
   bool HLine(string name, double price, color clr, int width = 1,
              ENUM_LINE_STYLE style = STYLE_SOLID) {
      string n = _prefix + "_" + name;
      ObjectCreate(0, n, OBJ_HLINE, 0, 0, price);
      ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, n, OBJPROP_WIDTH, width);
      ObjectSetInteger(0, n, OBJPROP_STYLE, style);
      ObjectSetInteger(0, n, OBJPROP_BACK, false);
      ChartRedraw(0);
      return true;
   }

   // 更新水平线位置
   bool HLineUpdate(string name, double price) {
      string n = _prefix + "_" + name;
      if (ObjectFind(0, n) < 0) return false;
      ObjectSetDouble(0, n, OBJPROP_PRICE, price);
      ChartRedraw(0);
      return true;
   }

   //+--- 垂直线（事件标记）----------------------------------------+
   bool VLine(string name, datetime t, color clr) {
      string n = _prefix + "_" + name;
      ObjectCreate(0, n, OBJ_VLINE, 0, t, 0);
      ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, n, OBJPROP_STYLE, STYLE_DOT);
      ObjectSetInteger(0, n, OBJPROP_WIDTH, 1);
      ChartRedraw(0);
      return true;
   }

   //+--- 趋势线（两点）--------------------------------------------+
   bool Trend(string name, datetime t1, double p1,
              datetime t2, double p2, color clr, int width = 2) {
      string n = _prefix + "_" + name;
      ObjectCreate(0, n, OBJ_TREND, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, n, OBJPROP_WIDTH, width);
      ObjectSetInteger(0, n, OBJPROP_RAY_RIGHT, false);
      ChartRedraw(0);
      return true;
   }

   //+--- 矩形（高亮区域）------------------------------------------+
   bool Rect(string name, datetime t1, double p1,
             datetime t2, double p2, color clr, bool fill = true) {
      string n = _prefix + "_" + name;
      ObjectCreate(0, n, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, n, OBJPROP_FILL, fill);
      ObjectSetInteger(0, n, OBJPROP_BACK, true);
      ChartRedraw(0);
      return true;
   }

   //+--- 文本标签（按时间/价格）-----------------------------------+
   bool Text(string name, datetime t, double price, string text, color clr) {
      string n = _prefix + "_" + name;
      ObjectCreate(0, n, OBJ_TEXT, 0, t, price);
      ObjectSetString (0, n, OBJPROP_TEXT, text);
      ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
      ObjectSetString (0, n, OBJPROP_FONT, "Arial");
      ObjectSetInteger(0, n, OBJPROP_FONTSIZE, 10);
      ChartRedraw(0);
      return true;
   }

   //+--- 删除一个对象 ---------------------------------------------+
   bool Remove(string name) {
      string n = _prefix + "_" + name;
      return ObjectDelete(0, n);
   }

   //+--- 删除所有本 EA 的对象 -------------------------------------+
   void RemoveAll() {
      int total = ObjectsTotal(0);
      for (int i = total - 1; i >= 0; i--) {
         string name = ObjectName(0, i);
         if (StringFind(name, _prefix) == 0) ObjectDelete(0, name);
      }
      ChartRedraw(0);
   }

   //+--- 统计本 EA 的对象数 ---------------------------------------+
   int CountMyObjects() {
      int n = 0;
      int total = ObjectsTotal(0);
      for (int i = 0; i < total; i++) {
         if (StringFind(ObjectName(0, i), _prefix) == 0) n++;
      }
      return n;
   }
};
//+------------------------------------------------------------------+
```

## 在 EA 里使用

```mql5
#include <MQL5Kit/M14_Drawer.mqh>

CDrawer dr;

int OnInit() {
   // 画固定止损位
   dr.HLine("SL_Daily", 4400, clrRed, 2, STYLE_DASH);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   dr.RemoveAll();   // 必调，清理所有本 EA 画的对象
}

void OnTick() {
   if (NB.IsNewBar()) {
      if (BuySignal) {
         dr.BuyArrow(iTime(_Symbol, _Period, 0), iClose(_Symbol, _Period, 0));
      } else if (SellSignal) {
         dr.SellArrow(iTime(_Symbol, _Period, 0), iClose(_Symbol, _Period, 0));
      }
      // 动态止损
      dr.HLineUpdate("SL_Active", currentSL);
   }
}
```

## Wingdings 箭头码速查
| 代码 | 形状 |
|---|---|
| 159 | 左箭头 |
| 160 | 右箭头 |
| 174 | 五角星 |
| 233 | 向上粗箭头（推荐 BUY）|
| 234 | 向下粗箭头（推荐 SELL）|
| 241 | 加号 |
| 242 | 叉号 |

## 必看陷阱
- **对象必须加前缀**，不然多个 EA 互相覆盖
- `RemoveAll` **OnDeinit 必调**，不然用户切时间框架会留下垃圾
- 画太多对象会卡（> 1000 个会明显卡）
- 颜色用 `clrXxx` 或 `C'R,G,B'` 自定义
- OBJ_BACK=true 让对象在 K 线下面，false 在上面

---

## 实战案例

- **当前 minimax-ea/ 0/10 EA 使用 M14**（P2 频次，仅 spec 范本）
  - 关键 API：`CDrawer::BuyArrow(datetime t, double price)` / `SellArrow` / `HLine(name, price, clr, width, style)` / `Rect(name, x1, y1, x2, y2, clr)` / `Label(name, x, y, text)` / `Next(label)` 唯一名生成（spec line 30-50 + 51-189）
  - 调优：画图用 `ObjectSetInteger/ObjectSetDouble` 原生，M14 仅作多对象批量管理 + 前缀隔离（`prefix="MyEA"` line 30 构造）；Wingdings 233/234 是 BUY/SELL 推荐箭头码
  - 链向：[[实战/BBTrendEA 复活 SOP]]（line 65 `DrawPanel/UpdatePanel` 50+ `ObjectCreate` 画 panel + 6 个 button，原生 MQL5 API 不是 M14，是 M14 的"反例"—— 复杂 panel 用原生物更灵活）/ [[04-避坑与速查/01 编译常见错误]]（OnDeinit 必 `ObjectDelete`）
