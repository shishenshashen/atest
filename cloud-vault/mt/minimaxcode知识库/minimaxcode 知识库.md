---
title: minimaxcode 知识库
tags: [home, index, minimaxcode, Mavis, CU]
created: 2026-06-03
updated: 2026-06-04
---

# minimaxcode 知识库

> 主题：**Mavis / Computer Use（CU）/ 配置 / 自动化 / 踩坑速查**
> 路径：`C:\ai\obsidian-文件\minimaxcode知识库\`
> 参考结构：`C:\ai\obsidian-文件\mt\EA开发\`

## 目录结构

```
minimaxcode知识库/
├── 00-快速开始/                 # 入门、必读、工具链
├── 01-核心模块/                 # Mavis 架构：Agent / Session / Memory / Skills / CU
├── 02-实战模板/                 # 可复制运行的 PowerShell 脚本模板
├── 03-通用片段/                 # 原子化、跨任务复用代码片段
├── 04-踩坑速查表/                # 从 agent memory 提炼的踩坑卡片
└── minimaxcode 知识库.md         # 本页（首页）
```

## 主题索引

### 00-快速开始
- [[00-快速开始/00 minimaxcode 是什么]] — 知识库定位、读者对象、维护约定
- [[00-快速开始/01 30 分钟跑通 Mavis + CU]] — 从零到 daemon + CU 渲染器在线
- [[00-快速开始/02 必备工具与权限]] — PowerShell 5.1、daemon 端口、UAC、RDP 限制

### 01-核心模块
- [[01-核心模块/00 架构总览]] — daemon ↔ renderer ↔ agent 三层关系
- [[01-核心模块/M01 Agent 与 Session]] — agent / session / 子会话 / 父会话通信
- [[01-核心模块/M02 Memory 三层模型]] — User / Agent / Project 三层写入规则
- [[01-核心模块/M03 Skills 与 MCP]] — Skill 加载、MCP 工具、第三方集成
- [[01-核心模块/M04 Cron 自提醒]] — `mavis cron self` 用法与坑
- [[01-核心模块/M05 Computer Use (CU)]] — 桌面自动化、坐标、enable 翻转
- [[01-核心模块/M06 Hook 系统]] — 工具调用前/后拦截，准入与改写
- [[01-核心模块/M07 IM 桥接（Feishu · Telegram）]] — 飞书 / TG 路由到 agent
- [[01-核心模块/M08 升级与迁移]] — daemon 升级、数据目录、配置兼容

### 02-实战模板
- [[02-实战模板/T01 CU keep-alive 守护脚本]] — 30s PUT 保持 CU 始终开启
- [[02-实战模板/T02 开机自启计划任务]] — schtasks + Register-ScheduledTask 完整模板
- [[02-实战模板/T03 Daemon API 客户端]] — Invoke-WebRequest + hashtable JSON 模板
- [[02-实战模板/T04 健康检查与自动恢复]] — 端口/进程/CU 状态 + 自愈脚本
- [[02-实战模板/T05 日志轮转守护]] — 按大小/按天切分，保留 N 份
- [[02-实战模板/T06 配置文件加载器]] — JSON/YAML 读取 + 校验 + 默认值

### 03-通用片段
- [[03-通用片段/01 PowerShell 踩坑合集]] — `$_` 解析 / BOM / 字符串拼接
- [[03-通用片段/02 反斜杠安全 JSON]] — hashtable + ConvertTo-Json -Compress
- [[03-通用片段/03 进程与服务管理]] — 找 PID、查端口、启停、重启
- [[03-通用片段/04 时间戳与日志格式化]] — ISO 8601、UTC、本地化、可读时长

### 04-踩坑速查表
- [[04-踩坑速查表/01 CU 相关踩坑]] — 自动关闭、RDP native 截屏失败
- [[04-踩坑速查表/02 Windows · PowerShell 踩坑]] — `$_`、BOM、计划任务 `-Delay`
- [[04-踩坑速查表/03 网络与 Git 踩坑]] — GitHub 镜像前缀、ghfast.top
- [[04-踩坑速查表/04 Hook · Skill 踩坑]] — 加载失败、改写无效、上下文溢出
- [[04-踩坑速查表/05 IM 集成踩坑]] — 飞书回调、Telegram 长轮询

### 01-修复案例 (fix-case)
- [[01-修复案例/MQL5 ctor 修复]] — 5 文件 0 errors 编译过的具体改法
- [[01-修复案例/MetaEditor CLI 编译 + MQL5Kit 3-way fork]] — 2026-06-04 MT5 任务中心 9 条收尾; CLI 编译绕开 GUI; 3-way fork 字节级统一

## 维护约定

- 任何 agent memory 里的新踩坑 → 24 小时内整理成 [[04-踩坑速查表/]] 卡片
- 任何验证可复用的脚本 → 进入 [[02-实战模板/]]
- 命名：`Mxx` 模块、`Txx` 模板、`xx 主题` 片段、`xx 主题踩坑` 速查
- Frontmatter 必填：`title / tags / created`（有改动追加 `updated`）
- **UTF-8 无 BOM** 写盘，参考 [[03-通用片段/01 PowerShell 踩坑合集]]
