---
title: 03 网络与 Git 踩坑
tags: [pitfall, git, github, network, China]
created: 2026-06-03
---

# 03 网络与 Git 踩坑

> 来源：agent memory，已实战验证。

## P-15 GitHub 直连超时 / 卡死

**症状**：

```bash
git clone https://github.com/owner/repo.git
# Cloning into 'repo'...
# remote: Enumerating objects: ...  (hang here)
# fatal: unable to access '...': Failed to connect to github.com port 443: Timed out
```

**根因**：国内网络到 GitHub 不稳定，特别是 HTTPS clone 大仓库。

**修复**：加镜像前缀：

```bash
git clone https://ghfast.top/https://github.com/owner/repo.git
```

或：

```bash
git clone https://mirror.ghproxy.com/https://github.com/owner/repo.git
```

> ⚠️ 镜像仅用于"下载源代码"。**不要**用镜像 push（凭证会被中间人看到）。
> 仅在下载时使用镜像前缀。

## P-16 Mavis 启动卡 "Cloning Hermes repository"

**症状**：mavis daemon 启动时卡在 "Cloning Hermes repository"，一直不动。

**根因**：Hermes 是 mavis 内部依赖仓库，从 GitHub clone 失败。

**修复**：

```bash
# 1. 找到 mavis 安装目录下的 hermes clone 命令
# 2. 把 URL 加上 ghfast.top/ 前缀
git clone https://ghfast.top/https://github.com/<org>/hermes.git <hermes_dir>
# 3. 重新启动 daemon
```

## P-17 `git push` 走代理也慢

**症状**：clone 走镜像后变快，但 push 仍然慢。

**根因**：push 不应走镜像（见 P-15 警告）。

**修复**：

- push 走 SSH（`git@github.com:owner/repo.git`）
- 或配置 `git config --global http.proxy socks5://127.0.0.1:1080`
- 或在公司 VPN / 内网环境 push

## P-18 代理设置与 daemon 端口冲突

**症状**：开了代理后，mavis daemon 监听 15321 失败。

**根因**：代理软件占用 15321 端口不常见，但**环境变量**会让 daemon 走代理出去。

**修复**：

```powershell
# 让 mavis 不走代理
$env:NO_PROXY = "localhost,127.0.0.1,15321"
$env:no_proxy = $env:NO_PROXY   # 小写也设上

# 或在 mavis 配置里指定
mavis config set network.noProxy "localhost,127.0.0.1"
```

## P-19 `npm install` / `pnpm install` 走官方源慢

**症状**：装 node 依赖极慢或失败。

**修复**：

```bash
# 临时切淘宝镜像
npm config set registry https://registry.npmmirror.com
pnpm config set registry https://registry.npmmirror.com

# 或在 .npmrc
# registry=https://registry.npmmirror.com
```

## P-20 DNS 污染导致 GitHub 解析错

**症状**：

```bash
ping github.com
# Pinging github.com [xxx.xxx.xxx.xxx]  # 错的 IP
```

**修复**：

```powershell
# 临时改 hosts
# C:\Windows\System32\drivers\etc\hosts
# 140.82.112.3 github.com
# 185.199.108.133 raw.githubusercontent.com

# 或用 DoH（Windows 11）
# 设置 → 网络 → DNS over HTTPS
```

---

## 速查表

| 问题               | 首选方案              | 备选                  |
| ---------------- | ----------------- | ------------------- |
| GitHub clone 慢   | `ghfast.top/` 前缀 | `mirror.ghproxy.com` |
| GitHub push 慢    | SSH               | 公司 VPN              |
| Hermes clone 卡死  | 同上               | 手动下放到 mavis 缓存目录     |
| npm install 慢    | npmmirror         | cnpm                 |
| DNS 污染           | hosts            | DoH                  |
| daemon 走代理错     | `NO_PROXY` 环境变量   | 代理白名单               |
