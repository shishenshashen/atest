---
title: M06 Hook 系统
tags: [hook, Mavis, guard, tool-call, before, after]
created: 2026-06-03
---

# M06 Hook 系统

## 是什么

Hook 是挂在 **工具调用生命周期** 上的拦截器，可以在不修改 agent 内部代码的情况下：

- **改写工具参数**（before）—— 自动补全路径、强制脱敏
- **拒绝工具调用**（before）—— 拦截 `rm -rf`、拦截 `git push --force`、拦截外网下载
- **审计工具调用**（after）—— 写日志、做合规留痕
- **追加上下文**（after）—— 调用成功后向 session 注入提醒

## 类型与触发时机

| Hook 类型 | 触发时机           | 常见用途                |
| ------- | -------------- | ------------------- |
| `before`| 工具被调用前，参数已 parse | 参数改写 / 拒绝 / 注入默认值 |
| `after` | 工具调用成功后（含 result）| 日志 / 二次处理 / 通知      |
| `error` | 工具调用失败时        | 错误统计 / 自动重试 / 降级   |

> 不支持 `around`（环绕式）—— 改写太多会破坏 agent 推理可解释性。

## Hook 文件位置

```
~/.mavis/hooks/<agentName>/<hookName>.json
```

或放在项目内：

```
<repo>/.mavis/hooks/<hookName>.json
```

文件示例（拒绝 `rm -rf`）：

```json
{
  "name": "guard-destructive-rm",
  "agentName": "general",
  "event": "before",
  "matcher": {
    "toolName": "bash",
    "toolArgs.command": "rm\\s+(-[a-zA-Z]*[fF][a-zA-Z]*\\s+)*-?-[rR][fF]\\b"
  },
  "action": "deny",
  "message": "rm -rf 被 hook 拦截。改用 mavis-trash。"
}
```

## 注册与启用

```bash
# 列出已注册 hook
mavis hook list --agent general --human

# 干跑测试：模拟一个 bash 调用看 hook 行为
mavis hook test general:guard-destructive-rm --input '{
  "agentName":"general",
  "sessionId":"ses_test",
  "toolName":"bash",
  "toolArgs":{"command":"rm -rf C:/temp"}
}'

# 启用 / 禁用
mavis hook enable general:guard-destructive-rm
mavis hook disable general:guard-destructive-rm

# 删除
mavis hook delete general:guard-destructive-rm
```

## 三个实战 hook

### 1. 拦截 `rm -rf`，强制走 trash

```json
{
  "name": "force-trash",
  "agentName": "general",
  "event": "before",
  "matcher": {
    "toolName": "bash",
    "toolArgs.command": "rm\\s+(-[a-zA-Z]*[rR][fF]|-[a-zA-Z]*f[a-zA-Z]*-[rR])"
  },
  "action": "deny",
  "message": "禁止 rm -rf。请改用 mavis-trash <paths>，自动进回收站。"
}
```

### 2. 拦截 `git push --force` 到 main/master

```json
{
  "name": "block-force-push-main",
  "agentName": "general",
  "event": "before",
  "matcher": {
    "toolName": "bash",
    "toolArgs.command": "git\\s+push\\s+.*--force.*(main|master)"
  },
  "action": "deny",
  "message": "禁止 force push 到 main/master。"
}
```

### 3. 记录所有 bash 调用

```json
{
  "name": "audit-bash",
  "agentName": "general",
  "event": "after",
  "matcher": { "toolName": "bash" },
  "action": "log",
  "logFile": "C:\\Users\\Administrator\\.mavis\\logs\\bash-audit.log",
  "format": "{ts}\t{sessionId}\t{toolArgs.command}\t{resultStatus}"
}
```

## 写 hook 的三条铁律

1. **必须给反馈**：d  eny 一定要写 `message`，否则模型不知道为什么失败，会原地打转。
2. **正则要 anchor**：用 `^git\\s+push` 而不是 `git\\s+push`，避免误匹配注释。
3. **测试后再启用**：用 `mavis hook test` 干跑至少 3 个 case（命中 / 未命中 / 边缘），再 enable。

## 与 Skill 的区别

| 维度     | Hook               | Skill              |
| ------ | ------------------ | ------------------ |
| 触发     | 工具调用时（被动）          | 模型主动加载（按需）         |
| 作用     | 拦截 / 改写 / 审计       | 注入流程 / 知识          |
| 编写者    | 平台用户 / 管理员         | 模型 / agent 自己      |
| 失败的影响  | 直接拒绝工具调用（强）        | 提示性（弱）             |
| 典型场景   | 安全护栏、合规审计、参数补全     | 写文档模板、API 用法、流程指引 |

## 调试：看 hook 触发日志

```bash
# daemon 端日志
Get-Content C:\Users\Administrator\.mavis\logs\daemon.log -Tail 50 `
  | Select-String -Pattern "hook" -SimpleMatch

# hook 自身的日志（取决于你的 hook 配置）
Get-Content C:\Users\Administrator\.mavis\logs\bash-audit.log -Tail 20
```

## 常见故障

- **Hook 不生效** → 路径错了或 `agentName` 不匹配；`mavis hook list` 确认
- **Hook 改写后参数错** → `matcher` 的 JSON path 拼错；用 `mavis hook test` 看实际 payload
- **模型无视 deny message** → message 写得太模糊；明确告诉它"为什么拒绝 + 应该用什么替代"
- **Hook 跑得太慢** → 写文件 / 调外部 API 的 hook 加 timeout 字段

→ 详细坑见 [[04-踩坑速查表/04 Hook · Skill 踩坑]]
