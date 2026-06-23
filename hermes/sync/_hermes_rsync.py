"""_hermes_rsync.py - Windows/Linux 跨平台目录同步 (替 rsync).
行为: 从 src 镜像到 dst, 删除 dst 中 src 没有的, 跳过 exclude 规则.
用法: python _hermes_rsync.py --src <dir> --dst <dir>
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

# 跳过这些 (路径含以下片段)
EXCLUDE_PATTERNS = [
    ".git/",
    "__pycache__/",
    ".mavis",
    "node_modules/",
    ".venv/",
    "venv/",
    "github-mirror/",  # 防仓内递归 (sync 仓本身)
]

# 跳过这些文件名 (glob)
EXCLUDE_GLOBS = [
    "*.pyc", "*.pyo", "*~", "*.tmp", "*.log.gz",
    ".DS_Store", "Thumbs.db",
]


def should_exclude(rel: str) -> bool:
    rel = rel.replace("\\", "/")
    for pat in EXCLUDE_PATTERNS:
        if pat in rel:
            return True
    from fnmatch import fnmatch
    base = os.path.basename(rel)
    for pat in EXCLUDE_GLOBS:
        if fnmatch(base, pat):
            return True
    return False


def sync(src: Path, dst: Path):
    src = src.resolve()
    dst = dst.resolve()
    dst.mkdir(parents=True, exist_ok=True)

    copied, skipped, removed = 0, 0, 0
    src_set = set()

    # 1. 走 src, 拷到 dst
    for root, dirs, files in os.walk(src):
        rel_root = os.path.relpath(root, src)
        if rel_root == ".":
            rel_root = ""
        # 排除目录
        dirs[:] = [d for d in dirs if not should_exclude(
            (rel_root + "/" + d) if rel_root else d
        )]
        for d in dirs:
            src_set.add(os.path.join(rel_root, d) if rel_root else d)
        for f in files:
            rel = (rel_root + "/" + f) if rel_root else f
            if should_exclude(rel):
                skipped += 1
                continue
            src_p = Path(root) / f
            dst_p = dst / rel
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_p, dst_p)
            src_set.add(rel)
            copied += 1

    # 2. 走 dst, 删 src 没有的
    for root, dirs, files in os.walk(dst):
        rel_root = os.path.relpath(root, dst)
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

    print(f"[sync] src={src}")
    print(f"[sync] dst={dst}")
    print(f"[sync] copied={copied}  skipped={skipped}  removed={removed}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True)
    p.add_argument("--dst", required=True)
    args = p.parse_args()
    sync(Path(args.src), Path(args.dst))
