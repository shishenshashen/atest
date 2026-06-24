# ScalperXAU v4 - 放宽版 + Debug Log (XAUUSDm M1 剥头皮)

> v3 → v4 关键: v3 over-filter 导致 0 笔 (实测 6-01~6-03 2 天区间)
> v4 放宽: 关 ADX/新闻/周五尾盘/trail; 扩大 ATR/spread/时段; 提高频率
> v4 加 debug log: 每个新 bar 输出 sig/RSI/ADX/ATR/spread + 拦原因

## 1. v3 失败诊断

v3 backtest 实测结果（用户 13:16 跑）：
- **区间**：6-01 ~ 6-03（**2 天**，不是我 .ini 配的 5-01 ~ 6-01）— GUI 默认 `last_month` 自动算
- **交易 0 笔**
- **耗时 2:49**（跑完了，但信号全部被 filter 拦）

**根因**：
1. GUI 自动用 `last_month` 模板 → 实际只跑 2 天
2. v3 多 filter（ADX 25 + ATR 0.5-5 + spread 50 + 时段 8-23 + 频率 30s/6h + HasDirection）AND 在一起，2 天里几乎没 bar 全满足
3. **就算改 1 月**，v3 的 filter 还是偏严 — 信号会很少

## 2. v4 相对 v3 的放宽

| 维度 | v3 默认 | v4 默认 | 变化原因 |
|------|--------|--------|---------|
| **ADX 过滤** | true, max=25 | **false** | v3 over-filter, 1 月 0 笔关键原因之一 |
| **新闻过滤** | true | **false** | 5 月没新闻, 6 月只 NFP 影响 1 天, 关了简化 |
| **周五尾盘** | true | **false** | 5 月只有 4 个周五, 关了增加信号 |
| **M08 Trail** | true | **false** | trail 在剥头皮里也可能拦, v4 先看裸信号 |
| **MaxSpread** | 50 | **80** | XAU normal 30-50, news 80-200, 80 是宽限 |
| **ATR 区间** | 0.5-5.0 | **0.3-8.0** | 0.5-5 太严, 实际 1 月 M1 ATR 在 0.3-8 区间 |
| **时段** | 8-23 | **7-22** | 扩展 1 小时前后 |
| **MinSec** | 30 | **10** | 放宽 |
| **MaxPerHour** | 6 | **12** | 放宽 |

## 3. v4 新增: Debug Log

| Input | 默认 | 说明 |
|-------|------|------|
| `InpDebugLog` | true | 启用详细调试日志 |
| `InpDebugLogEveryNBars` | 20 | 每 20 根新 bar 输出 1 行（M1 20 根 = 20 min） |

**输出格式**（Experts 日志）：
```
[v4-debug] bar=20 sig=-1 rsi=72.3 adx=18.5 atr=2.3 spread=42 blocked=OK_TO_OPEN
[v4-debug] bar=40 sig=0 rsi=55.0 adx=20.0 atr=1.8 spread=38 blocked=NO_SIGNAL
[v4-debug] bar=60 sig=1 rsi=28.5 adx=15.0 atr=0.8 spread=45 blocked=PASS_FILTERS_FAIL
```

**blocked 取值**：
- `NO_SIGNAL` — BB+RSI 信号没触发
- `PASS_FILTERS_FAIL` — 有信号但被 filter 拦 (spread/ADX/ATR/时段/频率/news/daily)
- `MAX_POS` — 信号过了但 MaxPos 满了
- `OK_TO_OPEN` — 应该开仓

**用途**：跑 1 月 backtest 后，看 Experts 日志统计 `blocked=X` 哪种最多 → v5 调参方向

## 4. 跑 v4 backtest 步骤（**关键**）

⚠️ **不要用 GUI 默认的 `last_month` 区间**（会自动算成 2-3 天），手动改：

1. **MetaEditor 重开 ScalperXAU.mq5** → 看到 v4 → 点 **编写** 编译（v4 已编译过 0 errors 1 warning，但保险再编）
2. **MT5 Ctrl+R 开 Strategy Tester**
3. 字段配置（**GUI 里手动改**）：
   - Expert: `ScalperXAU`
   - Symbol: `XAUUSDm`
   - Period: `M1`
   - **Date From: `2026.05.01`**（**手动改**）
   - **Date To: `2026.06.01`**（**手动改**）
   - Modeling: `1 分钟 OHLC`
4. **Inputs → Load** → 选 `ScalperXAUv4.set`
5. 点 **Start**

**耗时预估**：1 月 M1 + Modeling=1 = 5-10 min（比 v3 2 天 2:49 慢，但能拿到真数据）

## 5. v4 文件位置

- **EA 源码/编译**：`MQL5/Experts/minimax-ea/ScalperXAU.mq5` / `.ex5`（v4, 113KB）
- **.set**：`MQL5/Profiles/Tester/ScalperXAUv4.set`
- **.ini**：`MQL5/Profiles/Tester/ScalperXAUv4.XAUUSDm.M1.last_month.000.ini`（5-01~6-01，**但仍要 GUI 改**）

## 6. 跑完给我什么

1. **报告 XML 路径**（`Tester\Reports\ScalperXAUv4.xml`）
2. **Experts 日志**（`MQL5/Logs/20260604.log`）— 截屏或复制 `v4-debug` 行（看 blocked 分布）
3. （可选）MT5 Strategy Tester GUI 截图

我会：
1. 跑 `mql5-report-analyzer.mjs` 出 summary
2. 统计 debug log 看哪个 filter 拦最多
3. 出 v5 调参建议（精确放宽/收紧）
4. 写 v5 EA + 编译

## 7. v4 vs v3 性能预期

| 维度 | v3 1 月预估 | v4 1 月预估 |
|------|------------|------------|
| 交易数 | 0-5（极少） | 20-80（更多信号） |
| 胜率 | 未知 | 未知（需 backtest） |
| 出场分布 | 未知 | 未知（需 backtest） |
| DD | 未知 | 未知 |

**v4 目标不是赚钱** — 是**让 EA 跑出交易**，拿到数据。v5 才开始调参优化。

## 8. 接受"用户跑 backtest 传结果"分工

| 我做 | 你做 |
|------|------|
| 写 v4 EA + debug log + 编译 | GUI 改日期到 1 月 + Load v4 .set + Start |
| 写 v4 .set + .ini | 跑完传：报告 XML 路径 + Experts 日志（v4-debug 行） |
| 基于结果写 v5 | |
