---
title: M07 IM 桥接（Feishu / Telegram）
tags: [IM, feishu, lark, telegram, bridge, router]
created: 2026-06-03
---

# M07 IM 桥接（Feishu / Telegram）

## 是什么

IM 桥把 **IM 消息** 路由到 **agent session**：

- 用户在飞书 / TG 群里 @bot 发消息 → daemon 创建/复用 session → 派给 agent → 答案回传
- 一个 IM channel 对应一个或多个 session（按 chat / user 维度）

```
Feishu/TG  ──webhook/long-poll──>  mavis IM bridge  ──>  mavis daemon  ──>  agent
                                                                         │
                                          response  <──────  assistant  ←┘
```

## 三种路由策略

| 策略               | 行为                    | 适用                |
| ---------------- | --------------------- | ----------------- |
| `one-session`    | 整个 channel 共享一个 session | 私聊、个人助理          |
| `per-chat`       | 每个 chat 一个 session     | 群聊、话题不交叉         |
| `per-user`       | 每个 IM user 一个 session  | 多租户、强隔离          |

## 启用飞书桥接

```bash
# 1. 创建飞书应用（用 lark-cli 引导）
lark-cli config init
lark-cli auth login     # 第一次需要扫码

# 2. 启用桥接
mavis im enable feishu --bot-name "mavis" --route-strategy per-chat

# 3. 配回调地址（在飞书后台"事件订阅"页面）
# URL:    https://<your-domain>/mavis/api/im/feishu/webhook
# Token:  <mavis 自动生成，看 mavis im status feishu>

# 4. 验证
mavis im status feishu
```

## 启用 Telegram 桥接

```bash
# 1. 跟 @BotFather 拿 token
# /newbot → 拿到 123456:ABCDEF

# 2. 配置
mavis im enable telegram \
  --bot-token "123456:ABCDEF" \
  --route-strategy per-chat

# 3. 验证：给 bot 发 /start，应该收到 daemon 转发的 hello
```

## 路由配置文件位置

```
~/.mavis/im/<channel>.yaml
```

示例（飞书）：

```yaml
channel: feishu
routeStrategy: per-chat
defaultAgent: general
welcomeMessage: |
  你好，我是 mavis。直接发消息即可。
rules:
  - match:
      chatType: p2p       # 私聊
    target: general
  - match:
      chatType: group      # 群
      mentionBot: true     # 必须 @bot
    target: coder
  - match:
      chatType: group
      keywords: ["交易", "MT5", "XAUUSD"]
    target: trader        # 路由到专用交易 agent
```

## 关键事实

1. **私聊 vs 群聊**：
   - 私聊：bot 默认回复（无需 @）
   - 群聊：必须 @bot 才回复（在 `mentionBot: true` 模式下）

2. **消息分片**：
   - 飞书 / TG 单条消息有长度限制（飞书 4KB / TG 4096 字符）
   - daemon 自动分片回传（按段落 / 换行拆）

3. **图片 / 文件**：
   - 用户发图 → daemon 下载到 workspace → 当作附件传给 agent
   - agent 发的图片 / 文件 → 上传到 IM（飞书有 `im/v1/images` 等接口）

4. **速率限制**：
   - 飞书：1000 次/分钟 per app
   - TG：30 次/秒 per bot
   - daemon 内置 retry + backoff

## 三种消息类型

| 类型       | 触发            | 用途                  |
| -------- | ------------- | ------------------- |
| text     | 普通文字          | 90% 用例              |
| post     | 富文本（飞书特有）     | 带链接 / @人            |
| card     | 卡片（飞书 / TG inline）| 表格、按钮、状态展示         |
| image    | 图片            | 截屏、图表回传             |

## IM ↔ session 状态

| IM 端动作     | daemon 端行为                                |
| ---------- | ----------------------------------------- |
| 私聊首发       | 创建 root session，绑定 chatId → sessionId   |
| 私聊后续消息     | 复用同一 session（带 TTL；超时会 rotate）         |
| 群 @bot     | 同上，但 session 标题前缀 "group:xxx"          |
| 用户撤回 / 删消息 | session 不变（已读，immutable）                 |
| 频道长时间不活跃   | session 进入 `finished`；下次发消息起新 session    |

## 调试

```bash
# 看 IM 桥接状态
mavis im ls

# 看某个 chat 的 session 绑定
mavis im session feishu --chat-id oc_xxx

# 主动发一条测试消息
mavis im send feishu --to oc_xxx --text "ping from mavis"

# 关闭桥接
mavis im disable feishu
```

## 何时不用 IM 桥

- **隐私 / 机密对话** —— IM 厂商会留存消息
- **极高频触发** —— IM 桥会撑不住（速率限制 + session 上下文膨胀）
- **需要长 transaction** —— IM 异步、多轮回话容易断

## 必避的坑

- 私聊首条必须给清晰欢迎语 —— 用户会乱发（图片、表情包），容易让 agent 误判任务
- 群聊必须显式 `mentionBot: true` —— 否则会被所有消息淹没
- `defaultAgent: general` 是兜底 —— 不要用专用 agent 当兜底（专用 agent 任务特定）

→ 详细坑见 [[04-踩坑速查表/05 IM 集成踩坑]]
