# Hermes Secret Redaction 吞字 — Workaround 文档

> Issue: https://github.com/NousResearch/hermes-agent/issues/33801 (open, P2)
> PR fix: https://github.com/NousResearch/hermes-agent/pull/33840 (`code_file=True` flag)
> 我们的评论: https://github.com/NousResearch/hermes-agent/issues/33801#issuecomment-4676953065

## 触发的字面量模式（Hermes 启发式 redaction）

| 模式 | 触发 | 备注 |
|---|---|---|
| `TOK_LITERAL=*** 后跟非空值` | ✅ 吞成 `***` | 整个 `KEY=*** 替) |
| `MY_TOK_LITERAL=*** MY_TOKEN`, `MY_CREDENTIAL`, `MY_AUTH_TOKEN` | ✅ 吞 | 标识符名含 `TOK`/`CREDENTIAL`/`AUTH_TOKEN` |
| `ghp_*`, `sk-*`, `AKIA*` | ❌ 不吞 | 字面量**保留**让 agent 用 |
| `password=*** 不吞 | | |
| 字符串 `chr(84)+chr(79)+chr(75)+chr(69)+chr(78)` | ❌ 不吞 | **绕开关键** |
| `MY_TOK_LITERAL=*** MY_TOK_LITERAL=*** LITERAL` 后缀）| ❌ 不吞 | 命名约定 |

## Workaround 策略

### 1. 标识符名加 `_LITERAL` / `_SAFE` / `_PLACEHOLDER` / `_EXAMPLE` / `_DUMMY` 后缀
```python
# Bad:  触发吞字
GITHUB_TOK = 'abc...'
MY_CREDENTIAL = 'abc...'

# Good: 不触发
GITHUB_TOK_LITERAL = 'abc...'  # (加 _LITERAL 后缀)
MY_CREDENTIAL_SAFE = 'abc...'
```

### 2. 真正的 secret 用 `chr()` 拼接构建名
```python
# 关键: 完全不在源码里出现 'TOK' 'EN' 'CREDENTIAL' 等字面
NAME = chr(84)+chr(79)+chr(75)+chr(69)+chr(78)  # = 'TOK_LITERAL'
VALUE = 'abc...'
exec(NAME + ' = VALUE')
```

### 3. ENV-style 赋值用 `_LITERAL` 后缀
```bash
# Bad:  DASHSCOPE_KEY=*** 被吞
DASHSCOPE_KEY_LITERAL=dummytoken123  # Good
```

### 4. `write_file` 内容里出现 `TOK=*** LITERAL` 后缀**或者用 `chr()` 拼接

### 5. 读 .env 用 chr() 拼接
```python
import os
env_path = r'C:\Users\Administrator\AppData\Roaming\cn.org.hermesagent.desktop\runtime\hermes-home\.env'
gh_tok = None
with open(env_path) as f:
    for line in f:
        if line.startswith('GITHUB_'):  # 这里没用 'TOK' 字面, 用 'GITHUB_' 同样能定位
            parts = line.split('=', 1)
            if len(parts) == 2:
                gh_tok = parts[1].strip()
            break

# 构造 Authorization header 用 chr() 拼接
auth = chr(84)+chr(111)+chr(107)+chr(101)+chr(110) + ' ' + gh_tok  # 'Token <token>'
```

## 已经用 workaround 重写的脚本

| 脚本 | 路径 | 状态 |
|---|---|---|
| `hermes_image_server.py` | `C:\Users\Administrator\AppData\Local\Temp\hermes_image_server.py` | ✅ 用 chr() 拼接 |
| `post_gh_comment.py` | `C:\Users\Administrator\AppData\Local\Temp\post_gh_comment.py` | ✅ 用 chr() 拼接 + .startswith('GITHUB_') |

## 老大的命名约定（推荐）

**所有新的 Python / Shell 脚本**：
- 敏感字面 identifier → 用 `_LITERAL` / `_SAFE` / `_DUMMY` / `_EXAMPLE` 后缀
- 真正的 secret value → 用 `chr()` 拼接构建
- ENV-style 赋值 → `_LITERAL` 后缀

## 维护记录

- v1 (2026-06-11): 初版, 老大拍板用"chr() 拼接 + 命名约定"组合
- 关联: memory: `MSYS` 各种已知坑 + hermes-python-on-windows-msys skill
