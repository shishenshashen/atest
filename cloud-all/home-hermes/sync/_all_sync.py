"""_all_sync.py - 全量同步 (除凭证 + 系统级缓存)
同步: ~/.hermes + hermes-home + C:/ai + AppData/Roaming/obsidian + Desktop + .claude + .config + cu-mcp
不传: .ssh (凭证) / .local (缓存) / .cache (缓存) / .bun (重装即重生)
"""
import argparse
import os
import shutil
import sys
from pathlib import Path, PurePosixPath

# 凭证 - 永远不传
EXCLUDE_PATTERNS = [
    ".ssh/",
    ".env",
    ".env.backups/",
    "*.key", "*.pem",
]

# 大缓存 - 不传 (重装即重生, 不是"所有"工作内容)
EXCLUDE_DIRS_LARGE = [
    "lsp",
    "node_modules",
    ".venv", "venv",
    "__pycache__",
    "image_cache",
    "audio_cache",
    "ms-playwright",  # Playwright 浏览器二进制
    ".git",  # 仓内 .git 单独处理
    ".claude/projects",  # Claude 会话历史 (~M级, 重生成即可)
    "github-mirror",  # ⭐ 防仓内递归 (sync 仓本身, 8 块之一)
    "hermes-agent",    # ⭐ 30 MB 已 clone 仓库, 重 clone 即可
    # ⭐ 各种深层 cache (含敏感命令历史)
    "cache",           # 通用 cache
    "terminal",        # terminal snapshot (含命令历史, 可能含 secret)
    "documents",       # 文档缓存
    ".trash",
    "trash",
]

EXCLUDE_GLOBS = [
    "*.pyc", "*.pyo", "*~", "*.tmp", "*.log.gz", "*.lock",
    "lockfile", "*.lockfile",  # Obsidian lockfile (占用)
    "*.exe", "*.msi", "*.dmg",  # 安装包
    "Thumbs.db", "Desktop.ini", ".DS_Store",
]


def should_exclude(rel_posix: str) -> bool:
    # .env 单文件
    base = os.path.basename(rel_posix)
    if base in (".env", ".envrc"):
        return True
    for pat in EXCLUDE_PATTERNS:
        if pat in rel_posix:
            return True
    for d in EXCLUDE_DIRS_LARGE:
        if rel_posix == d or rel_posix.startswith(d + "/"):
            return True
    from fnmatch import fnmatch
    for pat in EXCLUDE_GLOBS:
        if fnmatch(base, pat):
            return True
    return False


def to_posix(rel: str) -> str:
    return rel.replace("\\", "/")


def sync(src: Path, dst: Path, top_label: str = None):
    """sync 单个 src -> dst."""
    src = src.resolve()
    dst = dst.resolve()
    dst.mkdir(parents=True, exist_ok=True)

    copied, skipped, removed = 0, 0, 0
    src_set = set()

    for root, dirs, files in os.walk(src):
        rel_root = to_posix(os.path.relpath(root, src))
        if rel_root == ".":
            rel_root = ""
        new_dirs = []
        for d in dirs:
            rp = (rel_root + "/" + d) if rel_root else d
            if not should_exclude(rp):
                new_dirs.append(d)
        dirs[:] = new_dirs
        for d in new_dirs:
            rp = (rel_root + "/" + d) if rel_root else d
            src_set.add(rp)
        for f in files:
            rel = (rel_root + "/" + f) if rel_root else f
            if should_exclude(rel):
                skipped += 1
                continue
            src_p = Path(root) / f
            dst_p = dst / PurePosixPath(rel)
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src_p, dst_p)
                src_set.add(rel)
                copied += 1
            except (PermissionError, OSError) as e:
                # 文件被占用 (Obsidian lock / Windows handle) - 跳
                print(f"  [skip-locked] {rel}: {e}")
                skipped += 1

    # 清理 dst 中多余
    for root, dirs, files in os.walk(dst):
        rel_root = to_posix(os.path.relpath(root, dst))
        if rel_root == ".":
            rel_root = ""
        for f in files:
            rel = (rel_root + "/" + f) if rel_root else f
            if rel not in src_set:
                (Path(root) / f).unlink()
                removed += 1
        for d in dirs:
            rel = (rel_root + "/" + d) if rel_root else d
            if rel not in src_set:
                try:
                    shutil.rmtree(Path(root) / d)
                except OSError:
                    pass
                removed += 1

    label = top_label or src.name
    print(f"[all-sync] {label}: copied={copied}  skipped={skipped}  removed={removed}")


if __name__ == "__main__":
    """用法: python _all_sync.py <dst_base>
    默认同步 5 大块: ~/.hermes, hermes-home, C:/ai, obsidian, .claude, .config, cu-mcp, Desktop
    """
    p = argparse.ArgumentParser()
    p.add_argument("--dst", required=True, help="同步目标基目录")
    args = p.parse_args()

    dst_base = Path(args.dst)

    # 1. ~/.hermes
    src = Path.home() / ".hermes"
    if src.exists():
        sync(src, dst_base / "home-hermes", top_label="~/.hermes")

    # 2. hermes-home
    src = Path(r"C:\Users\Administrator\AppData\Roaming\cn.org.hermesagent.desktop\runtime\hermes-home")
    if src.exists():
        sync(src, dst_base / "hermes-home", top_label="hermes-home")

    # 3. C:/ai
    src = Path(r"C:\ai")
    if src.exists():
        # 不传 dl (Downloads 临时) + 30-技能档案 可能大
        sync(src, dst_base / "c-ai", top_label="C:/ai")

    # 4. obsidian 配置
    src = Path(r"C:\Users\Administrator\AppData\Roaming\obsidian")
    if src.exists():
        sync(src, dst_base / "obsidian-config", top_label="AppData/Roaming/obsidian")

    # 5. .claude
    src = Path.home() / ".claude"
    if src.exists():
        sync(src, dst_base / "home-claude", top_label="~/.claude")

    # 6. .config
    src = Path.home() / ".config"
    if src.exists():
        sync(src, dst_base / "home-config", top_label="~/.config")

    # 7. cu-mcp
    src = Path.home() / "cu-mcp"
    if src.exists():
        sync(src, dst_base / "cu-mcp", top_label="~/cu-mcp")

    # 8. .bashrc.d
    src = Path.home() / ".bashrc.d"
    if src.exists():
        sync(src, dst_base / "home-bashrc-d", top_label="~/.bashrc.d")

    print("[all-sync] done")
