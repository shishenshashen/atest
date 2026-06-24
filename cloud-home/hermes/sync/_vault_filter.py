"""_vault_filter.py - 智能过滤 Obsidian vault, 只传核心知识.
按 P0 灵魂, 不传临时数据.
不传: 队列.md, 归档.md, daily/*.md, 99-临时, .opencode, node_modules
可传: EA开发, 技能档案, 项目档案, 10-提炼, 90-索引, Monthly, Weekly, MOC
"""
import os
import shutil
from pathlib import Path, PurePosixPath

# vault 内不传的目录/文件 (相对 vault 根)
VAULT_EXCLUDE = {
    "00-任务调度中心/队列.md",       # 自动生成
    "00-任务调度中心/归档.md",       # 自动生成
    "00-任务调度中心/daily",          # daily 临时记录 (~3MB)
    "ai-managed/99-临时",             # 临时
    "ai-managed/20-经验沉淀/2026-06/Daily",  # 6 月 daily 临时
    "ai-managed/20-经验沉淀/2026-05/Daily",  # 5 月 daily 临时 (如果有)
    "ai-managed/20-经验沉淀/2026-04/Daily",  # 4 月 daily 临时 (如果有)
    "ai-managed/00-Inbox",            # 剪藏入口 (暂不传, 内容易过时)
    "ai-managed/20-经验沉淀/2026-06/Weekly/_pdf",  # PDF 临时 (~320K)
    "ai-managed/20-经验沉淀/2026-05/Weekly/_pdf",
    ".opencode",                      # node_modules + 配置 (~M级)
    "node_modules",
    "__pycache__",
    ".git",
    ".trash",
    "trash",
    "dl",                             # 临时下载
    "30-技能档案/.obsidian",          # Obsidian 系统目录
    "40-项目档案/.obsidian",
    "EA开发/.obsidian",
    "_pdf",                            # 通用 PDF 临时目录
    "_tmp",
    ".tmp",
}

# vault 内一定传的目录 (核心)
# 注意: 实际 vault 路径是 obsidian-文件/mt/EA开发, 即 "mt/EA开发"
VAULT_INCLUDE_KEY = {
    "mt/EA开发",
    "mt/minimaxcode知识库",
    "mt/01-调用模块",
    "mt/02-完整模板",
    "mt/04-避坑与速查",
    "mt/05-高级设计模式",
    "ai-managed/10-提炼",
    "ai-managed/30-技能档案",
    "ai-managed/40-项目档案",
    "ai-managed/90-索引",
    "ai-managed/20-经验沉淀/2026-06/Monthly",  # 月总结
    "ai-managed/20-经验沉淀/2026-06/Weekly",   # 周总结
    "ai-managed/20-经验沉淀/2026-05/Monthly",
    "ai-managed/20-经验沉淀/2026-05/Weekly",
    "ai-managed/98-已处理",                     # 旧但已处理 (知识)
}


def is_excluded(rel_posix: str) -> bool:
    """检查是否在排除列表."""
    for ex in VAULT_EXCLUDE:
        if rel_posix == ex or rel_posix.startswith(ex + "/"):
            return True
    return False


def is_included(rel_posix: str) -> bool:
    """核心目录 - 必传 (前缀匹配, 'mt' 包含 'mt/EA开发')."""
    for inc in VAULT_INCLUDE_KEY:
        if rel_posix == inc or rel_posix.startswith(inc + "/"):
            return True
    # 父链 (例如 'mt' 是 'mt/EA开发' 的祖先, 'ai-managed' 是 'ai-managed/10-提炼' 的祖先)
    # 从短到长查父链: rel_posix="ai-managed/20-经验沉淀" 的祖先 "ai-managed" 应被认为要传
    for inc in VAULT_INCLUDE_KEY:
        # 取出 inc 的顶层目录 (e.g. "ai-managed/10-提炼" -> "ai-managed")
        top = inc.split("/")[0]
        # rel_posix 是 top 或 top/...
        if rel_posix == top or rel_posix.startswith(top + "/"):
            return True
    return False


def sync_vault(src: Path, dst: Path, label: str = "vault"):
    """智能过滤 vault: 排除 + 核心包含."""
    src = src.resolve()
    dst = dst.resolve()
    dst.mkdir(parents=True, exist_ok=True)

    copied, skipped, removed = 0, 0, 0
    src_set = set()

    for root, dirs, files in os.walk(src):
        rel_root = rel = os.path.relpath(root, src).replace("\\", "/")
        if rel_root == ".":
            rel_root = ""
        # 决策: 进入这目录吗?
        keep_dirs = []
        for d in dirs:
            sub_rel = (rel_root + "/" + d) if rel_root else d
            if is_excluded(sub_rel):
                continue
            if is_included(sub_rel):
                keep_dirs.append(d)
            else:
                # 既不在 include 也不在 exclude - 跳过
                # (比如 ai-managed/20-经验沉淀/2026-06/Daily)
                # 兜底: 不传
                continue
        dirs[:] = keep_dirs

        for d in keep_dirs:
            sub_rel = (rel_root + "/" + d) if rel_root else d
            src_set.add(sub_rel)
        for f in files:
            f_rel = (rel_root + "/" + f) if rel_root else f
            if is_excluded(f_rel):
                skipped += 1
                continue
            # 必须在 include 路径下
            in_inc = False
            for inc in VAULT_INCLUDE_KEY:
                if f_rel == inc or f_rel.startswith(inc + "/"):
                    in_inc = True
                    break
            if not in_inc:
                skipped += 1
                continue
            src_p = Path(root) / f
            dst_p = dst / PurePosixPath(f_rel)
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src_p, dst_p)
                src_set.add(f_rel)
                copied += 1
            except (PermissionError, OSError) as e:
                print(f"  [skip-locked] {f_rel}: {e}")
                skipped += 1

    # 清理 dst 多余
    for root, dirs, files in os.walk(dst):
        rel_root = os.path.relpath(root, dst).replace("\\", "/")
        if rel_root == ".":
            rel_root = ""
        for f in files:
            f_rel = (rel_root + "/" + f) if rel_root else f
            if f_rel not in src_set:
                (Path(root) / f).unlink()
                removed += 1
        for d in dirs:
            d_rel = (rel_root + "/" + d) if rel_root else d
            if d_rel not in src_set:
                try:
                    shutil.rmtree(Path(root) / d)
                except OSError:
                    pass
                removed += 1

    print(f"[vault-sync] {label}: copied={copied}  skipped={skipped}  removed={removed}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: _vault_filter.py <src_vault> <dst>")
        sys.exit(1)
    sync_vault(Path(sys.argv[1]), Path(sys.argv[2]))
