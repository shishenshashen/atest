---
title: M04 Cron 自提醒
tags: [cron, self-reminder, async, automation]
created: 2026-06-03
---

# M04 Cron 自提醒

## 何时必须建 cron

> **MANDATORY after any async handoff**

当你的回合里出现以下**任一**情况，**必须**在结束回合前建 cron：

- 推了 MR 但还没合并（CI 还在跑）
- 触发了后台批处理 / 定时作业
- 调用了外部 API 但结果没在本回合回来
- 等待人类确认 / 第三方回信

> 常见错误：把"push + auto-merge"当结束。**不是**——任务包含"确认 CI 过 + MR 合"。

## 怎么建

```bash
mavis cron self <name> --every <interval> --prompt "<提醒文本>"
```

**参数**：

| 参数      | 必选 | 说明                              |
| ------- | -- | ------------------------------- |
| `<name>` | 是  | cron 标识，daemon 内唯一              |
| `--every` | 是  | 间隔（`5m` / `30s` / `1h` / `1d`）  |
| `--prompt` | 是  | 每次触发时注入到 session 的 prompt       |

## 三个例子

### 1. 盯 CI

```bash
mavis cron self watch-ci-pr-42 \
  --every 5m \
  --prompt "检查 PR #42 的 CI 状态，若通过则 merge 并清理 cron"
```

### 2. 盯批处理作业

```bash
mavis cron self watch-nightly-export \
  --every 15m \
  --prompt "检查昨晚的导出任务是否完成（看 /data/export/2026-06-02.done），完成后清理 cron"
```

### 3. 盯 keep-alive 守护

```bash
mavis cron self cu-keepalive-supervisor \
  --every 10m \
  --prompt "如果 CU keep-alive 脚本进程不在了，重启它"
```

## 完成后必须清理

任务完成后**显式清理**，否则 cron 会永远跑下去（每次 session 都被打断）：

```bash
# 查看所有 cron
mavis cron list

# 删除指定 cron
mavis cron remove <name>
```

> 把清理动作**写进你自己的 prompt**——"完成后清理 cron `xxx`"，避免遗忘。

## 何时**不**用 cron

- `mavis team plan` 已有自己的 heartbeat / CycleReport / unresponsive 告警——**不要**再建 cron 来监控它。
- 同步、瞬时操作（创建文件、读文件、调本地 API 立刻拿结果）——不需要 cron。
- 任何"等用户回话"——走消息通知而不是 cron。

## 调试

```bash
# 手动触发一次（不等间隔）
mavis cron trigger <name>

# 看下一次触发时间
mavis cron list --verbose
```

## 踩坑速记

1. **cron 名不能含中文 / 空格**——ASCII + `-` / `_` 即可。
2. **prompt 不要过长**——每次触发都注入，长 prompt 会爆上下文。
3. **过期 cron 不清理 = 上下文泄漏**——每次结束都确认。
4. **`--every` 单位**：支持 `s/m/h/d`，**不**支持 `2h30m`，要换算成单值。
