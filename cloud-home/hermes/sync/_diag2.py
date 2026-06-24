"""trace 哪个 rel 路径导致 digest 没拷"""
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

copied = 0
sample = []
for root, dirs, files in os.walk(src):
    rel_root = os.path.relpath(root, src)
    if rel_root == ".":
        rel_root = ""
    new_dirs = []
    for d in dirs:
        rp = (rel_root + "/" + d) if rel_root else d
        if not should_exclude(rp):
            new_dirs.append(d)
    dirs[:] = new_dirs
    for f in files:
        rel = (rel_root + "/" + f) if rel_root else f
        if should_exclude(rel):
            continue
        src_p = Path(root) / f
        dst_p = dst / rel
        # 试 mkdir
        try:
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            copied += 1
            if "digest" in rel.lower() and copied < 5:
                sample.append((rel, src_p, dst_p, dst_p.exists()))
        except Exception as e:
            print(f"FAIL: {rel}: {e}")

print(f"\ntotal copied (would-be): {copied}")
print("\nsample digest paths:")
for rel, sp, dp, ex in sample:
    print(f"  rel={rel}")
    print(f"    src={sp} exists={sp.exists()}")
    print(f"    dst={dp} exists={ex}")
