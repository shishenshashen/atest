"""
task-queue/journal.py  v2 (2026-06-11)
- 同一 task_id 同一天 → 覆盖（不追加）
- 渲染日报看 timeout 状态独立（不再伪装 failed）
"""
import sys
import time
import re
from pathlib import Path
from datetime import datetime

JOURNAL_DIR = Path.home() / ".hermes" / "journal"
sys.path.insert(0, str(Path(__file__).parent))
import tq_queue as tq  # noqa: E402


def _md_path(date_str: str = None) -> Path:
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    return JOURNAL_DIR / f"{date_str}.md"


def _fmt_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def _fmt_duration(start: int, end: int) -> str:
    sec = max(0, end - start)
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m{sec % 60}s"
    return f"{sec // 3600}h{(sec % 3600) // 60}m"


def _entry_marker(task_id: str) -> str:
    """用 task_id 做唯一标记，正则匹配用。"""
    return f"`{task_id}`"


def _render_entry(task: dict, status: str, summary: str,
                  artifacts: list, error: str, ts_now: str,
                  duration: str) -> str:
    art_lines = ""
    if artifacts:
        for a in artifacts:
            p = a.get("path", "?")
            s = a.get("size", "?")
            h = a.get("hash", "")
            art_lines += f"  - `{p}` ({s}B{h and f' sha256={h[:8]}'})\n"
    if not art_lines:
        art_lines = "  - (无)\n"

    err_block = ""
    if error:
        err_block = f"\n**错误**:\n```\n{error}\n```\n"

    return f"""
## [{ts_now}] {status.upper()} · {_entry_marker(task['task_id'])}

- **角色**: {task['agent_role']}
- **目标**: {task['goal']}
- **耗时**: {duration} (心跳间隔 {task['heartbeat_sec']}s, 超时阈值 {task['timeout_sec']}s)
- **进度**: {task['progress']}
- **重试**: {task['retry_count']}/{task['max_retries']}
- **摘要**: {summary or '(无)'}
- **产物**:
{art_lines}{err_block}
---
"""


def _remove_existing_entry(md: Path, task_id: str):
    """如果有同一 task 的旧 entry，删掉。"""
    if not md.exists():
        return
    try:
        content = md.read_text(encoding="utf-8")
    except Exception:
        return
    marker = _entry_marker(task_id)
    # 找以 "## [..] STATUS · `task_id`" 开头到下一个 "---" 结束
    pattern = re.compile(
        rf"\n## \[[^\]]+\] [A-Z]+ · {re.escape(marker)}\n.*?\n---\n",
        re.DOTALL
    )
    new_content, n = pattern.subn("", content)
    if n:
        md.write_text(new_content, encoding="utf-8")


def write_journal(task_id: str, status: str = None,
                  summary: str = "", artifacts: list = None,
                  error: str = None) -> Path:
    """
    写一条 journal 记录。
    P1-6 修：同一 task_id 同一天 → 覆盖（先删旧 entry 再追加）。
    """
    task = tq.get(task_id)
    if not task:
        raise KeyError(f"task not found: {task_id}")

    md = _md_path()
    date_str = datetime.now().strftime("%Y-%m-%d")
    ts_now = _fmt_ts(int(time.time()))
    duration = _fmt_duration(task["created_at"], int(time.time()))
    final_status = status or task["status"]

    # 1) 先去重（删旧 entry）
    _remove_existing_entry(md, task_id)

    # 2) 渲染新 entry
    entry = _render_entry(task, final_status, summary, artifacts,
                          error, ts_now, duration)

    # 3) 追加
    if not md.exists():
        header = f"# 📓 Journal · {date_str}\n\n本文件由 task-queue 自动生成。\n"
        md.write_text(header, encoding="utf-8")

    with open(md, "a", encoding="utf-8") as f:
        f.write(entry)

    return md


def render_daily(date_str: str = None) -> str:
    """渲染某日 journal 摘要（用于复盘报告）。"""
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    tasks = tq.list_by_date(date_str)

    if not tasks:
        return f"# {date_str} 无任务记录"

    total = len(tasks)
    by_status = {}
    by_level = {}
    durations_done = []
    for t in tasks:
        by_status.setdefault(t["status"], 0)
        by_status[t["status"]] += 1
        lv = t.get("level", "M")
        by_level.setdefault(lv, {"total": 0, "done": 0, "timeout": 0, "failed": 0})
        by_level[lv]["total"] += 1
        if t["status"] == tq.STATUS_DONE:
            by_level[lv]["done"] += 1
            durations_done.append(t["updated_at"] - t["created_at"])
        elif t["status"] == tq.STATUS_TIMEOUT:
            by_level[lv]["timeout"] += 1
        elif t["status"] == tq.STATUS_FAILED:
            by_level[lv]["failed"] += 1

    avg_dur = sum(durations_done) / len(durations_done) if durations_done else 0
    timeout_count = by_status.get(tq.STATUS_TIMEOUT, 0)
    fail_count = by_status.get(tq.STATUS_FAILED, 0)
    # 假死率 = timeout / total（用真 timeout 状态，不再是 0%）
    fake_death_rate = (timeout_count / total * 100) if total else 0

    lines = [
        f"# 📊 Daily Review · {date_str}",
        f"",
        f"- 总任务: **{total}**",
        f"- 完成: {by_status.get(tq.STATUS_DONE, 0)}",
        f"- 失败: {fail_count}",
        f"- 假死(超时): {timeout_count}",
        f"- **假死率: {fake_death_rate:.1f}%**",
        f"- 平均完成耗时: {_fmt_duration(0, int(avg_dur))}",
        f"",
        f"## 各状态分布",
    ]
    for s, n in sorted(by_status.items(), key=lambda x: -x[1]):
        lines.append(f"- {s}: {n}")

    if durations_done:
        sorted_tasks = sorted(
            [t for t in tasks if t["status"] == tq.STATUS_DONE],
            key=lambda x: -(x["updated_at"] - x["created_at"])
        )
        lines.append(f"\n## 最慢 TOP3")
        for t in sorted_tasks[:3]:
            dur = _fmt_duration(t["created_at"], t["updated_at"])
            lines.append(f"- {dur} · {t['agent_role']} · `{t['task_id']}` · {t['goal'][:60]}")

    violations = []
    for t in tasks:
        if t["status"] == tq.STATUS_TIMEOUT:
            violations.append(f"- {t['task_id']} 超时: 心跳断 {t['timeout_sec']}s 以上")
        if t["retry_count"] >= t["max_retries"]:
            violations.append(f"- {t['task_id']} 重试 {t['retry_count']} 次")

    # 等级分布段
    if by_level:
        lines.append(f"\n## 等级分布")
        for lv in ["S", "M", "L", "CRITICAL"]:
            if lv in by_level:
                st = by_level[lv]
                fdr = (st["timeout"] / st["total"] * 100) if st["total"] else 0
                lines.append(
                    f"- **{lv}**: 总 {st['total']}, "
                    f"完成 {st['done']}, 超时 {st['timeout']} (假死率 {fdr:.0f}%), "
                    f"失败 {st['failed']}"
                )
    if violations:
        lines.append(f"\n## 规则违反")
        lines.extend(violations[:10])
    else:
        lines.append(f"\n## 规则违反\n- (无)")

    return "\n".join(lines)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render-today"
    if cmd == "render-today":
        print(render_daily())
    elif cmd == "render":
        print(render_daily(sys.argv[2]))
    else:
        print(__doc__)
