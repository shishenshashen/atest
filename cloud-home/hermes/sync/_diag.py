"""诊断 _hermes_rsync 为啥 digest 拷不过去"""
import os

EXCLUDE_PATTERNS = [
    ".git/",
    "__pycache__/",
    ".mavis",
    "node_modules/",
    ".venv/",
    "venv/",
    "github-mirror/",
]


def should_exclude(rel):
    rel = rel.replace("\\", "/")
    for pat in EXCLUDE_PATTERNS:
        if pat in rel:
            return True
    return False


src = r"C:\Users\Administrator\.hermes"
print(f"EXCLUDE: {EXCLUDE_PATTERNS}")
print(f"src: {src}")
print(f"src exists: {os.path.exists(src)}")
print()
# 只看 digest 路径
excluded_dirs = []
excluded_files = []
copied = 0
for root, dirs, files in os.walk(src):
    rel = os.path.relpath(root, src)
    if rel == ".":
        rel = ""
    # 看 digest 相关
    if "digest" not in rel.lower() and "ea-learning" not in rel.lower():
        continue
    # 应用 exclude
    new_dirs = []
    for d in dirs:
        rp = (rel + "/" + d) if rel else d
        if should_exclude(rp):
            excluded_dirs.append(rp)
        else:
            new_dirs.append(d)
    dirs[:] = new_dirs
    for f in files:
        rp = (rel + "/" + f) if rel else f
        if should_exclude(rp):
            excluded_files.append(rp)
        else:
            copied += 1
print(f"excluded dirs ({len(excluded_dirs)}):")
for d in excluded_dirs[:5]:
    print(f"  {d}")
print(f"excluded files ({len(excluded_files)}):")
for f in excluded_files[:5]:
    print(f"  {f}")
print(f"copied would-be: {copied}")
