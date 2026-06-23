---
title: M05 Computer Use (CU)
tags: [CU, computer-use, desktop, automation]
created: 2026-06-03
---

# M05 Computer Use (CU)

## 是什么

CU 是 Mavis 的**桌面自动化能力**，让 agent 能：

- 截屏（`desktop_screenshot` / `desktop_zoom` / `desktop_screenshot_region`）
- 操作鼠标（`desktop_left_click` / `desktop_double_click` / `desktop_left_click_drag`）
- 键入文本 / 按键（`desktop_type` / `desktop_key`）
- 滚动（`desktop_scroll`）
- 列出 / 聚焦 / 移动 / 调整窗口（`desktop_window_*`）
- 读 / 写剪贴板（`desktop_clipboard_*`）

## 坐标系

- 坐标是 **0-1000 归一化** 的屏幕坐标
- `[0,0]` = 左上，`[500,500]` = 中心，`[1000,1000]` = 右下
- 是相对**当前主显示器 / 截图内容**，不是绝对像素
- 窗口边界仍是**绝对像素**

## 打开 / 关闭 CU

```powershell
# 持久化（写盘）
mavis config set beta.cuMode true

# 运行时（立即翻内存状态）
Invoke-WebRequest -Method PUT http://localhost:15321/mavis/api/cu/enabled `
  -Body '{"enabled":true,"workspaceDir":"C:\Users\Administrator\.mavis\sessions"}' `
  -ContentType "application/json"

# 查询当前状态
Invoke-WebRequest http://15321:15321/mavis/api/cu/enabled
# 或
(Invoke-WebRequest http://localhost:15321/mavis/api/cu/enabled).Content | ConvertFrom-Json
```

## 三个必知陷阱

### 1. Renderer 自动关闭

任何窗口最小化/恢复 → renderer PUT `enabled=false`。
**必须**有 keep-alive 守护（见 [[02-实战模板/T01 CU keep-alive 守护脚本]]）。

### 2. RDP session 不能截屏

`desktop_screenshot` 等走 nut.js native binding，RDP session（session 2+）抛 "Failed to capture screen"。
**必须**用户在 console session（session 1）登录。

### 3. `desktop_window_list` 不受影响

它走不同 API，所以 RDP 下仍可用——可以用来"先看看窗口"再切回 console 操作。

## 典型剧本

```powershell
# 1. 截屏看当前桌面
mavis mcp call cu desktop_screenshot '{}' | Out-File screenshot.json

# 2. 在图像上找一个按钮（用 describe_images 工具）
describe_images -image_info @(@{file="screenshot.png"; prompt="Where is the 'Save' button?"})

# 3. 点击按钮
mavis mcp call cu desktop_left_click '{"x":500,"y":600}'

# 4. 等待 1 秒
mavis mcp call cu desktop_wait '{"ms":1000}'

# 5. 再次截屏验证
mavis mcp call cu desktop_screenshot '{}'
```

## 适用 vs 不适用

| 适用                    | 不适用                 |
| --------------------- | ------------------- |
| 桌面 GUI 软件没有 API / 命令行 | 能用 API 解决的（更快更稳）    |
| 一次性"看图找按钮"           | 高频操作（截屏慢、token 贵）   |
| MT5 MetaEditor 点 F7 编译 | 能用 mql5-cli / 文件监听解决 |
| 注册表 / 控制面板小工具         | PowerShell `Set-ItemProperty` 即可 |

## 安全注意

- **Type 文本前确认焦点**——`desktop_left_click` 一次到目标输入框
- **避免在锁屏 / 屏保下操作**——可能误触
- **敏感信息不落截屏**——`describe_images` 不会回传，但 base64 在本地有临时文件
