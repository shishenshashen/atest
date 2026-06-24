"""
task-queue/push.py  v2 (2026-06-11)
统一推送通道：飞书 webhook / 企业微信 webhook / 本地 notice.json 兜底。
watchdog.py / dispatch.py / review.py 都用这个，不重复实现。
"""
import os
import sys
import time
import json
import urllib.request
from pathlib import Path

QUEUE_DIR = Path.home() / ".hermes" / "task-queue"
NOTICE_FILE = QUEUE_DIR / "pending_notices.json"
LOG_DIR = QUEUE_DIR / "logs"

MAX_NOTICES = 200  # 多了就截留（提升到 200，老版本 50 太少）


def _log_to(log_path: Path, msg: str):
    """可选：写一行到指定日志。"""
    if not log_path:
        return
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def push(msg: str, level: str = "info", log_path: Path = None) -> dict:
    """
    多通道推送，返回每通道的成功/失败。
    1. 飞书 webhook（FEISHU_WEBHOOK_URL）
    2. 企业微信 webhook（WECOM_WEBHOOK_URL）
    3. 本地 notice 文件（兜底）
    任何通道失败不影响其他。
    """
    result = {"feishu": None, "wecom": None, "notice": None}
    payload = json.dumps({
        "msg_type": "text",
        "content": {"text": f"[task-queue/{level}] {msg}"}
    }, ensure_ascii=False)

    # 1) 飞书
    feishu = os.environ.get("FEISHU_WEBHOOK_URL")
    if feishu:
        try:
            req = urllib.request.Request(
                feishu, data=payload.encode("utf-8"),
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5).read()
            result["feishu"] = "ok"
        except Exception as e:
            result["feishu"] = f"fail: {e}"

    # 2) 企微
    wecom = os.environ.get("WECOM_WEBHOOK_URL")
    if wecom:
        try:
            req = urllib.request.Request(
                wecom, data=payload.encode("utf-8"),
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5).read()
            result["wecom"] = "ok"
        except Exception as e:
            result["wecom"] = f"fail: {e}"

    # 3) 兜底
    result["notice"] = _write_notice(msg, level)

    _log_to(log_path, f"PUSH [{level}] {msg}")
    return result


def _write_notice(msg: str, level: str) -> str:
    """写本地 notice 文件，Hermes 下次会话会消费。"""
    NOTICE_FILE.parent.mkdir(parents=True, exist_ok=True)
    notices = []
    if NOTICE_FILE.exists():
        try:
            notices = json.loads(NOTICE_FILE.read_text(encoding="utf-8"))
        except Exception:
            notices = []
    notices.append({
        "at": int(time.time()),
        "level": level,
        "msg": msg,
    })
    notices = notices[-MAX_NOTICES:]
    NOTICE_FILE.write_text(
        json.dumps(notices, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return "ok"


def push_done_summary(task: dict, journal_path: str = None,
                     verify_result: dict = None) -> dict:
    """
    推送"任务完成"总结给老大。Phase 3 ship 闭环的核心。
    - 包含: task_id / role / level / 目标 / 耗时 / 产物 / 验证结果
    - level=info 级别（不是 error）
    - 推完返回 push 结果（同 push()）

    不会重复推：调一次就一次。如想再推，老大手动重调。
    """
    tid = task.get("task_id", "?")
    role = task.get("agent_role", "?")
    level = task.get("level", "M")
    goal = task.get("goal", "")[:80]
    created = task.get("created_at", 0)
    updated = task.get("updated_at", 0)
    dur = max(0, updated - created)
    dur_str = f"{dur // 60}m{dur % 60}s" if dur >= 60 else f"{dur}s"

    # 产物摘要
    arts = (task.get("result") or {}).get("artifacts", [])
    art_lines = ""
    for a in arts[:5]:  # 最多 5 个
        path = a.get("path", "?")
        size = a.get("size", 0)
        h = a.get("hash", "")[:8]
        verify = a.get("verify", a.get("note", ""))
        art_lines += f"  - {path} ({size}B, sha={h})\n"
    if not art_lines:
        art_lines = "  (无)\n"
    if len(arts) > 5:
        art_lines += f"  ... 还有 {len(arts) - 5} 个\n"

    # verify 摘要
    verify_str = ""
    if verify_result:
        if verify_result.get("verified"):
            verify_str = "✅ verify ok"
        else:
            verify_str = f"❌ verify 失败: {verify_result.get('error', '?')}"
    elif task.get("result", {}).get("verify"):
        v = task["result"]["verify"]
        if v.get("verified"):
            verify_str = "✅ verify ok"
        else:
            verify_str = f"❌ verify 失败"

    # journal 路径
    journal_str = f"\njournal: {journal_path}" if journal_path else ""

    msg = (
        f"✅ 任务完成 [{level}] {tid}\n"
        f"角色: {role} | 耗时: {dur_str} | 目标: {goal}\n"
        f"产物:\n{art_lines}"
        f"验证: {verify_str or '—'}{journal_str}"
    )

    log_path = Path.home() / ".hermes" / "task-queue" / "logs" / "ship.log"
    return push(msg, level="info", log_path=log_path)


def consume_pending() -> list:
    """
    读 + 清空 pending_notices.json，返回内容。
    Hermes 会话开头调一次，把积压告警摆给老大。
    """
    if not NOTICE_FILE.exists():
        return []
    try:
        notices = json.loads(NOTICE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    # 清空
    try:
        NOTICE_FILE.write_text("[]", encoding="utf-8")
    except Exception:
        pass
    return notices


def consume_since(since_ts: int) -> list:
    """消费 from since_ts 之后的，不清空。"""
    if not NOTICE_FILE.exists():
        return []
    try:
        notices = json.loads(NOTICE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [n for n in notices if n.get("at", 0) >= since_ts]


if __name__ == "__main__":
    from datetime import datetime
    cmd = sys.argv[1] if len(sys.argv) > 1 else "consume"
    if cmd == "consume":
        ns = consume_pending()
        print(f"共 {len(ns)} 条待消费：")
        for n in ns:
            ts = datetime.fromtimestamp(n['at']).strftime('%H:%M:%S')
            print(f"  [{n['level']}] {ts}  {n['msg'][:100]}")
    elif cmd == "test":
        push("测试推送 by task-queue/push.py", level="info")
        print("ok")
    else:
        print(__doc__)
