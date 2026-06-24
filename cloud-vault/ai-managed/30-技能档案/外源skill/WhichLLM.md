---
title: WhichLLM · 外源工具索引
tags: [skill, 外源, AI与自动化, 本地LLM, 工具]
type: skill-reference
source: github.com/Andyyyy64/whichllm
introduced-via: 微信公众号"小G" (2026-06-10 老大微信分享)
---

# 🛠️ WhichLLM · 挑本地 LLM 的开源小工具

> **GitHub**: `github.com/Andyyyy64/whichllm`
> **安装**: `uv tool install whichllm` 或 `uvx whichllm@latest`
> **首次发现**: 2026-06-10 老大微信分享文章

## 核心能力

- 自动检测硬件（NVIDIA/AMD/Apple Silicon/CPU）
- 根据真实基准（LiveBench/Arena ELO/Aider）+ 模型新旧，挑最优 LLM
- 支持模拟显卡（`--gpu "RTX 5090"`）
- 支持升级对比（`whichllm upgrade`）
- 支持一键启动对话（`whichllm run`）
- 输出 JSON 方便脚本化
- 支持任务过滤（`--task coding/vision/math`）

## 命令速查

```bash
whichllm                                      # 看本机最佳模型
whichllm --gpu "RTX 4090"                     # 模拟显卡
whichllm upgrade "RTX 4090" "RTX 5090"        # 升级对比
whichllm plan "llama 3 70b"                   # 跑这个模型要啥硬件
whichllm run                                  # 下载+启动对话
whichllm snippet "qwen 7b"                    # 输出 Python 代码
whichllm --task coding --json                 # 编程任务+JSON 输出
```

## 适用场景

- ✅ 准备装/升级显卡前的"试车"
- ✅ 不知道下哪个模型
- ✅ 不知道本地能跑啥
- ❌ 不知道**用啥**模型做啥事（这是选型问题，不是 WhichLLM 的范围）

## 老大用得上吗？

**看场景**：
- 老大有 OpenAI 账号、API key → 不用装 WhichLLM
- 老大想本地跑 LLM（隐私/省钱）→ **值得装**
- 老大机器显卡一般 → 强烈推荐，先跑一下

## 待办

- [ ] 看看 GitHub license
- [ ] 装上跑一次看实际效果
- [ ] 如果好，装成 npx skill

## 🔗 相关

- [[10-提炼/AI与自动化/2026-06-10_WhichLLM 挑本地LLM的开源工具|原文章提炼]]
