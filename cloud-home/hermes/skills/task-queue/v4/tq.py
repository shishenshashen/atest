#!/usr/bin/env python
"""
tq - task-queue v3 命令行入口（跨平台）
用法：
    tq start
    tq stop
    tq status
    tq review
    tq consume
    tq test
    tq help
"""
import sys
import subprocess
from pathlib import Path

ROOT = Path.home() / ".hermes" / "skills" / "task-queue"

CMDS = {
    "start":   ["python", str(ROOT / "watchdog.py"), "start", "60"],
    "stop":    ["python", str(ROOT / "watchdog.py"), "stop"],
    "status":  ["python", str(ROOT / "watchdog.py"), "status"],
    "review":  ["python", str(ROOT / "review.py"), "daily", "--no-push"],
    "test":    ["python", str(ROOT / "test_task_queue_v5.py")],
    "compress": ["python", str(ROOT / "archive_compress.py"), "--days", "7"],
}


def ship_task(task_id: str):
    """调 dispatch.ship(task_id) - Phase 3 单一入口。"""
    sys.path.insert(0, str(ROOT))
    import json
    for m in ["tq_queue", "push", "dispatch", "journal", "watchdog", "review", "cortex"]:
        if m in sys.modules:
            del sys.modules[m]
    import dispatch as tq_dispatch
    res = tq_dispatch.ship(task_id)
    # 简化输出给 CLI
    out = {
        "task_id": task_id,
        "status": res.get("status"),
        "journal": res.get("journal"),
        "verify_verified": (res.get("verify") or {}).get("verified"),
        "push_ok": bool(res.get("push")),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if res.get("status") in ("done",) else 1


def consume():
    import json
    sys.path.insert(0, str(ROOT))
    from push import consume_pending
    from datetime import datetime
    ns = consume_pending()
    print(f"共 {len(ns)} 条积压通知")
    for n in ns:
        ts = datetime.fromtimestamp(n['at']).strftime('%H:%M:%S')
        print(f"  [{n['level']}] {ts}  {n['msg'][:100]}")


HELP = """task-queue v3 — 主动推进 + 心跳 + 复盘 + ship 闭环

  tq start           启动 watchdog（后台，60s 扫描）
  tq stop            停 watchdog
  tq status          看状态 + 活跃任务健康度
  tq review          生成今日 review（不推）
  tq consume         拉积压告警并清空
  tq test            跑端到端测试
  tq compress        压缩 7 天前的 archive jsonl → gz
  tq ship <task_id>  Phase 3 ship 闭环（verify+journal+推总结 1 行）
  tq help            帮助
"""


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "-h", "--help"):
        print(HELP)
        return 0
    cmd = sys.argv[1]
    if cmd == "consume":
        consume()
        return 0
    if cmd == "ship":
        if len(sys.argv) < 3:
            print("用法: tq ship <task_id>")
            return 1
        return ship_task(sys.argv[2])
    if cmd not in CMDS:
        print(f"未知命令: {cmd}\n")
        print(HELP)
        return 1
    return subprocess.call(CMDS[cmd], cwd=str(ROOT))


if __name__ == "__main__":
    sys.exit(main())
