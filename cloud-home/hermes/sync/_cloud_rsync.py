"""_cloud_rsync.py - 同步 hermes-home (含 state.db / config / memories / .env).
不同于 _hermes_rsync.py: 不过滤 .git/ 模式 (hermes-home 本身不是 git 仓).
"""
import argparse
import os
import shutil
import sys
from pathlib import Path, PurePosixPath

# 跳过的: 缓存/日志/开发工具/备份
EXCLUDE_PATTERNS = [
    "__pycache__/",
    "node_modules/",
    ".venv/",
    "venv/",
    "lsp/",         # LSP 缓存 46M
    ".git/",
]

# 大目录: 镜像 cache / skills 也不传 (本地重新 init 即可)
EXCLUDE_DIRS_LARGE = [
    "lsp",          # 46M LSP 缓存
    "cache",        # 232K 缓存
    "image_cache",  # 图像缓存
    "audio_cache",  # 音频缓存
    "uploads",      # 3.5M 上传文件 (看需要)
    "logs",         # 2.3M 日志
    ".env.backups", # 秘钥备份
    "hashline",     # 临时 hash
    "gateway-service",
    "hooks",
    "hooks-output",
    "ms-playwright",# Playwright 浏览器
    "skills",       # 39M skills (本地重新 git clone 即可, 不传)
    ".git",
    ".github",
]

EXCLUDE_GLOBS = [
    "*.pyc", "*.pyo", "*~", "*.tmp", "*.log.gz", "*.lock",
    ".DS_Store", "Thumbs.db",
]


def should_exclude(rel_posix: str) -> bool:
    for pat in EXCLUDE_PATTERNS:
        if pat in rel_posix:
            return True
    for d in EXCLUDE_DIRS_LARGE:
        if rel_posix == d or rel_posix.startswith(d + "/"):
            return True
    from fnmatch import fnmatch
    base = os.path.basename(rel_posix)
    for pat in EXCLUDE_GLOBS:
        if fnmatch(base, pat):
            return True
    return False


def to_posix(rel: str) -> str:
    return rel.replace("\\", "/")


def sync(src: Path, dst: Path):
    src = src.resolve()
    dst = dst.resolve()
    dst.mkdir(parents=True, exist_ok=True)

    copied, skipped, removed = 0, 0, 0
    src_set = set()

    for root, dirs, files in os.walk(src):
        rel_root = to_posix(os.path.relpath(root, src))
        if rel_root == ".":
            rel_root = ""
        # 排除
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
            shutil.copy2(src_p, dst_p)
            src_set.add(rel)
            copied += 1

    # 删除 dst 中 src 没有的
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

    print(f"[cloud-sync] src={src}")
    print(f"[cloud-sync] dst={dst}")
    print(f"[cloud-sync] copied={copied}  skipped={skipped}  removed={removed}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True)
    p.add_argument("--dst", required=True)
    args = p.parse_args()
    sync(Path(args.src), Path(args.dst))
