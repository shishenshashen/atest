---
title: WhichLLM · 微信文章介绍
tags: [外源, AI与自动化, 本地LLM, WhichLLM, 工具]
type: extracted-article
source: 微信公众号"小G"
original-url: https://mp.weixin.qq.com/s/LyC-UCccObAeyERhzNdzcw
received-via: 微信 DM (Hermes 微信机器人)
received-at: 2026-06-10 12:36:39
processed-at: 2026-06-10
vault: ai-managed
---

# 🛠️ WhichLLM · 挑本地 LLM 的开源小工具

> **来源**：微信公众号"小G"（2026-06-10 老大微信分享）
> **原始链接**：https://mp.weixin.qq.com/s/LyC-UCccObAeyERhzNdzcw
> **GitHub**：`github.com/Andyyyy64/whichllm`

## 🎯 一句话

**根据你的显卡/内存，自动从 Hugging Face 挑出"跑得下 + 跑得快 + 评分高"的最优本地 LLM**，不只看参数大小。

## ✨ 核心功能

| 功能 | 命令 | 用途 |
|------|------|------|
| 自动检测硬件 | `whichllm` | 看现有机器能跑啥 |
| 模拟显卡 | `uvx whichllm@latest --gpu "RTX 4090"` | 升级前"试车" |
| 升级对比 | `whichllm upgrade "RTX 4090" "RTX 5090"` | 两卡直接 PK |
| 一键聊天 | `whichllm run` | 自动下载最佳模型开聊 |
| 代码片段 | `whichllm snippet "qwen 7b"` | 输出可复制 Python |
| 任务过滤 | `--task coding/vision/math` | 按场景筛选 |
| JSON 输出 | `--json` | 接 Ollama 等自动化 |
| 规划需求 | `whichllm plan "llama 3 70b"` | 告诉你需要啥硬件 |

## 📊 实际推荐示例（RTX 4090）

- 🥇 **Qwen3.6-27B** (Q5_K_M) — score 92.8, 27 t/s
- 🥈 Qwen3-32B (Q4_K_M) — score 83.0, 31 t/s

> 32B 不一定赢 27B，因为新版 + 基准更高。**这就是它和"看大小"工具的区别**。

## 🧠 排序依据

- 实时 Hugging Face 数据
- 多源基准（LiveBench / Arena ELO / Aider）
- **模型新旧** + **证据可信度** 加权
- 避免被过时或自吹的数据坑

## 🚀 安装

```bash
# 零配置试用
uvx whichllm@latest

# 模拟显卡
uvx whichllm@latest --gpu "RTX 4090"

# 装上
uv tool install whichllm
```

## 🤔 给老大提个醒（AI 补充）

- **支持**：NVIDIA / AMD / Apple Silicon / 纯 CPU
- **格式**：GGUF / AWQ / GPTQ
- **坑点**：
  - 速度估算是**理论值**（基于硬件参数），真实运行会因系统/后端不同有差异
  - **建议先小模型测试**，再上主力
  - 数据是**实时**的（依赖 HF API），离线用不了
  - 文章没说 license，需要查 GitHub

## 🔗 相关

- [[30-技能档案/外源skill/WhichLLM]] - 如果后面装了 skill 链过来
- `ai-managed/00-Inbox/` - 通过微信 DM 接收的来源标记
