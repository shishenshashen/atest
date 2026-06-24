"""
task-queue/review.py  v2 (2026-06-11)
- 用 push.py 统一推送
- timeout 状态独立统计（不再永远 0%）
- 增加 consume_pending：会话开头调用
"""
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))
import tq_queue as tq  # noqa: E402
import journal as tq_journal  # noqa: E402
import push as tq_push  # noqa: E402

REVIEW_DIR = Path.home() / ".hermes" / "reviews"
QUEUE_LOG_DIR = Path.home() / ".hermes" / "task-queue" / "logs"


def daily_review(date_str: str = None, push_notify: bool = True) -> Path:
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    out = REVIEW_DIR / f"daily-{date_str}.md"

    body = tq_journal.render_daily(date_str)
    extra = []

    extra.append("\n\n## 📈 近 7 天趋势")
    for i in range(7):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        tasks = tq.list_by_date(d)
        if tasks:
            tot = len(tasks)
            timeout = sum(1 for t in tasks if t["status"] == tq.STATUS_TIMEOUT)
            done = sum(1 for t in tasks if t["status"] == tq.STATUS_DONE)
            extra.append(f"- {d}: 总 {tot}, 完成 {done}, 假死 {timeout} "
                         f"({timeout / tot * 100:.0f}%)")
        else:
            extra.append(f"- {d}: (无任务)")

    tasks_today = tq.list_by_date(date_str)
    tot = len(tasks_today)
    timeout = sum(1 for t in tasks_today if t["status"] == tq.STATUS_TIMEOUT)
    fake_death_rate = (timeout / tot * 100) if tot else 0

    extra.append(f"\n\n## ✅ 验收")
    extra.append(f"- 假死率: {fake_death_rate:.1f}% (目标: <10%)")
    extra.append(f"- 失败推送: {'已配置 webhook' if os.environ.get('FEISHU_WEBHOOK_URL') or os.environ.get('WECOM_WEBHOOK_URL') else '仅本地 notice（建议配飞书/企微）'}")
    extra.append(f"- journal: 今日 {'已生成' if (Path.home() / '.hermes' / 'journal' / f'{date_str}.md').exists() else '未生成'}")

    full = body + "\n".join(extra) + "\n"
    out.write_text(full, encoding="utf-8")

    if push_notify and (timeout > 0 or fake_death_rate > 10):
        tq_push.push(
            f"📊 日报 {date_str}\n假死率 {fake_death_rate:.1f}%\n详情 {out}",
            level="warn",
            log_path=QUEUE_LOG_DIR / f"review-{date_str}.log",
        )

    return out


def weekly_review(push_notify: bool = True) -> Path:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now()
    week_end = today.strftime("%Y-%m-%d")
    week_start = (today - timedelta(days=6)).strftime("%Y-%m-%d")
    prev_start = (today - timedelta(days=13)).strftime("%Y-%m-%d")
    prev_end = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    out = REVIEW_DIR / f"weekly-{week_end}.md"

    def stats(start: str, end: str) -> dict:
        all_tasks = []
        d = datetime.strptime(start, "%Y-%m-%d")
        end_d = datetime.strptime(end, "%Y-%m-%d")
        while d <= end_d:
            all_tasks.extend(tq.list_by_date(d.strftime("%Y-%m-%d")))
            d += timedelta(days=1)
        tot = len(all_tasks)
        return {
            "total": tot,
            "done": sum(1 for t in all_tasks if t["status"] == tq.STATUS_DONE),
            "failed": sum(1 for t in all_tasks if t["status"] == tq.STATUS_FAILED),
            "timeout": sum(1 for t in all_tasks if t["status"] == tq.STATUS_TIMEOUT),
            "fake_death_rate": (sum(1 for t in all_tasks if t["status"] == tq.STATUS_TIMEOUT) / tot * 100) if tot else 0,
        }

    cur = stats(week_start, week_end)
    prev = stats(prev_start, prev_end)

    trend_total = cur["total"] - prev["total"]
    trend_fdr = cur["fake_death_rate"] - prev["fake_death_rate"]

    body = f"""# 📊 周报 · {week_start} ~ {week_end}

## 对比上周

| 指标 | 本周 | 上周 | 变化 |
|---|---|---|---|
| 总任务 | {cur['total']} | {prev['total']} | {trend_total:+d} |
| 完成 | {cur['done']} | {prev['done']} | {cur['done'] - prev['done']:+d} |
| 失败 | {cur['failed']} | {prev['failed']} | {cur['failed'] - prev['failed']:+d} |
| 假死 | {cur['timeout']} | {prev['timeout']} | {cur['timeout'] - prev['timeout']:+d} |
| 假死率 | {cur['fake_death_rate']:.1f}% | {prev['fake_death_rate']:.1f}% | {trend_fdr:+.1f}% |

## 验收

- 假死率本周 < 10%: {'✅' if cur['fake_death_rate'] < 10 else '❌'} ({cur['fake_death_rate']:.1f}%)
- 假死率环比下降: {'✅' if trend_fdr < 0 else '⚠️'} (差 {trend_fdr:+.1f}%)

## 7 天明细

"""
    for i in range(7):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        tasks = tq.list_by_date(d)
        if tasks:
            tot = len(tasks)
            timeout = sum(1 for t in tasks if t["status"] == tq.STATUS_TIMEOUT)
            done = sum(1 for t in tasks if t["status"] == tq.STATUS_DONE)
            body += f"- {d}: 总 {tot}, 完成 {done}, 假死 {timeout}\n"
        else:
            body += f"- {d}: (无任务)\n"

    out.write_text(body, encoding="utf-8")

    if push_notify:
        tq_push.push(
            f"📊 周报 {week_start}~{week_end}\n"
            f"任务 {cur['total']} (上周 {prev['total']}, {trend_total:+d})\n"
            f"假死率 {cur['fake_death_rate']:.1f}% "
            f"(上周 {prev['fake_death_rate']:.1f}%, {trend_fdr:+.1f}%)\n"
            f"详情 {out}",
            level="info",
            log_path=QUEUE_LOG_DIR / f"review-{week_end}.log",
        )

    return out


def consume_pending_for_session() -> list:
    """
    会话开头调一次。把积压的 pending_notices 摆出来。
    返回 list，Hermes 自己渲染给老大。
    """
    return tq_push.consume_pending()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "daily"
    if cmd == "daily":
        p = daily_review(push_notify="--no-push" not in sys.argv)
        print(f"saved: {p}")
    elif cmd == "weekly":
        p = weekly_review(push_notify="--no-push" not in sys.argv)
        print(f"saved: {p}")
    elif cmd == "consume":
        ns = consume_pending_for_session()
        print(f"共 {len(ns)} 条积压通知")
        for n in ns:
            ts = datetime.fromtimestamp(n['at']).strftime('%H:%M:%S')
            print(f"  [{n['level']}] {ts}  {n['msg'][:100]}")
    else:
        print(__doc__)
