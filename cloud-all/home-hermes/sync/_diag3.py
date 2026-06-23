"""trace src_set 内容"""
import os
from pathlib import Path

EXCLUDE_PATTERNS = [
    ".git/", "__pycache__/", ".mavis",
    "node_modules/", ".venv/", "venv/", "github-mirror/",
]

def should_exclude(rel):
    rel = rel.replace("\\", "/")
    for pat in EXCLUDE_PATTERNS:
        if pat in rel:
            return True
    return False

src = Path(r"C:\Users\Administrator\.hermes")
dst = Path(r"C:\Users\Administrator\.hermes\github-mirror\atest\hermes")

src_set = set()
digest_files = []
digest_dirs = []

# 1. walk src
for root, dirs, files in os.walk(src):
    rel_root = os.path.relpath(root, src)
    if rel_root == ".":
        rel_root = ""
    new_dirs = []
    for d in dirs:
        rp = (rel_root + "\\" + d) if rel_root else d
        if not should_exclude(rp):
            new_dirs.append(d)
    dirs[:] = new_dirs
    for d in new_dirs:
        rp = (rel_root + "\\" + d) if rel_root else d
        src_set.add(rp)
        if "digest" in rp.lower():
            digest_dirs.append(rp)
    for f in files:
        rel = (rel_root + "\\" + f) if rel_root else f
        if should_exclude(rel):
            continue
        src_set.add(rel)
        if "digest" in rel.lower():
            digest_files.append(rel)

print(f"src_set 总数: {len(src_set)}")
print(f"digest 文件: {len(digest_files)}")
print(f"digest 目录: {len(digest_dirs)}")
print()
print("前 10 个 digest 路径在 src_set:")
for r in (digest_files + digest_dirs)[:10]:
    print(f"  {r!r}")

# 2. 现在 check dst 里 digest 子目录
print()
print("dst 实际状态:")
dst_digest = dst / "digest"
if dst_digest.exists():
    for root, dirs, files in os.walk(dst_digest):
        rel_root = os.path.relpath(root, dst)
        if rel_root == ".":
            rel_root = ""
        for d in dirs:
            r = (rel_root + "\\" + d) if rel_root else d
            in_set = r in src_set
            print(f"  DIR  {r!r}  in_src_set={in_set}")
        for f in files:
            r = (rel_root + "\\" + f) if rel_root else f
            in_set = r in src_set
            print(f"  FILE {r!r}  in_src_set={in_set}")
