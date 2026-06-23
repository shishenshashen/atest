"""
task-queue/watchdog.py  v2 (2026-06-11)
- run_once: 批量 mark_timeout 一次锁，不漏报
- start: 启动后 sleep + 验证子进程真活着（防 Popen 假启动）
- push: 抽到顶层 push.py，多模块共享
- 共享 _push_notice: 飞书/wecom/notice 兜底
"""
import os
import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime

QUEUE_DIR = Path.home() / ".hermes" / "task-queue"
PID_FILE = QUEUE_DIR / "watchdog.pid"
LOG_DIR = QUEUE_DIR / "logs"
NOTICE_FILE = QUEUE_DIR / "pending_notices.json"
STARTUP_WAIT_SEC = 3  # 启动后等多少秒再验证子进程活着

sys.path.insert(0, str(Path(__file__).parent))
import tq_queue as tq  # noqa: E402
import push as tq_push  # noqa: E402  ← 抽出来


def _log(msg: str):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"watchdog-{datetime.now().strftime('%Y-%m-%d')}.log"
    ts = datetime.now().strftime("%H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def _format_stale_msg(task: dict, gap: int) -> str:
    return (
        f"⏰ 任务假死: {task['task_id']}\n"
        f"角色: {task['agent_role']}\n"
        f"目标: {task['goal'][:100]}\n"
        f"心跳断: {gap}秒前 (阈值 {task['timeout_sec']}s)\n"
        f"进度: {task['progress']}"
    )


def run_once() -> dict:
    """
    单次扫描。v3 三档主动推进：
    - 找所有 stale 任务（gap > heartbeat_sec）
    - 按 gap 分档：
        1×stale ≤ gap < 2×stale → nudge  （温柔提醒，AI 间）
        2×stale ≤ gap < 3×stale → ping    （明确质问，AI 间）
        3×stale ≤ gap < timeout  → escalate（推老大）
        gap ≥ timeout            → mark_timeout + 推老大（原有行为）
    - 每档单独 push，nudge/ping 不打扰老大
    """
    now = int(time.time())
    all_stale = []
    # 找所有"心跳陈旧但未超时"的任务（gap < timeout 但 gap > heartbeat）
    for t in tq.list_active():
        gap = now - t["last_heartbeat"]
        if gap > t["heartbeat_sec"]:  # 已经陈旧
            all_stale.append((t, gap))

    nudges = []
    pings = []
    escalates = []
    timeouts = []

    for task, gap in all_stale:
        stale_window = task["heartbeat_sec"]  # 1×stale
        timeout = task["timeout_sec"]
        if gap >= timeout:
            timeouts.append((task, gap))
        elif gap >= 3 * stale_window:
            escalates.append((task, gap))
        elif gap >= 2 * stale_window:
            pings.append((task, gap))
        else:  # gap >= 1*stale 但 < 2*stale
            nudges.append((task, gap))

    # 1) nudges 写文件（子 agent 启动会消费）
    for task, gap in nudges:
        try:
            tq.write_nudge(task["task_id"], tq.NUDGE_KIND_NUDGE, gap_sec=gap)
        except Exception as e:
            _log(f"nudge write fail {task['task_id']}: {e}")

    # 2) pings 写文件
    for task, gap in pings:
        try:
            tq.write_nudge(task["task_id"], tq.NUDGE_KIND_PING, gap_sec=gap)
        except Exception as e:
            _log(f"ping write fail {task['task_id']}: {e}")

    # 3) escalates 写文件 + 推老大（v4: 先调 auto_retry 自救，再推）
    for task, gap in escalates:
        task_id = task["task_id"]
        try:
            # === v4 修复：先自救 ===
            # 步骤: mark_failed → auto_retry.attempt() → 成功静默，失败才推
            try:
                tq.mark_failed(task_id, error=f"escalate_gap={gap}s",
                               reason="auto_retry_then_escalate")
            except Exception as e:
                _log(f"escalate mark_failed fail {task_id}: {e}")
                continue

            try:
                import auto_retry as tq_auto_retry
                retry_result = tq_auto_retry.attempt(
                    task_id, reason=f"watchdog_escalate_gap={gap}s")
            except Exception as e:
                _log(f"auto_retry import/run fail {task_id}: {e}")
                retry_result = {"retried": False,
                                "skipped_reason": f"auto_retry exception: {e}"}

            if retry_result.get("retried"):
                # 自救成功：仅 log，不推老大（但写 nudge 给子 agent）
                _log(f"AUTO_RETRY_OK {task_id} strategy={retry_result['strategy']} "
                     f"retry_count={retry_result['retry_count_new']}")
                try:
                    tq.write_nudge(task_id, tq.NUDGE_KIND_NUDGE,
                                   msg=f"watchdog auto-retried you: "
                                       f"strategy={retry_result['strategy']}, "
                                       f"retry#{retry_result['retry_count_new']}, "
                                       f"don't give up")
                except Exception as e:
                    _log(f"post-retry nudge write fail {task_id}: {e}")
                # 给老大 info-level 通知（不刷屏）
                try:
                    tq_push.push(
                        f"♻️ 自动重试: {task_id}\n"
                        f"角色: {task['agent_role']} 等级: {task.get('level', '?')}\n"
                        f"策略: {retry_result['strategy']} (第 {retry_result['retry_count_new']} 次)\n"
                        f"原因: 心跳断 {gap}s (3×stale)\n"
                        f"→ 已重置为 queued，等子 agent 重启",
                        level="info",
                    )
                except Exception as e:
                    _log(f"post-retry push fail {task_id}: {e}")
                continue  # 下一个 task，不推老大

            # === 自救失败 / 跳过：推老大 ===
            try:
                tq.write_nudge(task_id, tq.NUDGE_KIND_ESCALATE, gap_sec=gap)
            except Exception as e:
                _log(f"escalate nudge write fail {task_id}: {e}")

            skip = retry_result.get("skipped_reason", "")
            try:
                tq_push.push(
                    f"🚨 任务升级到 escalate: {task_id}\n"
                    f"角色: {task['agent_role']} 等级: {task.get('level', '?')}\n"
                    f"目标: {task['goal'][:100]}\n"
                    f"心跳断: {gap}秒前 (3×stale={3 * task['heartbeat_sec']}s)\n"
                    f"进度: {task['progress']}\n"
                    f"自救结果: {skip or 'auto_retry 未启用'}\n"
                    f"→ 子 agent 已冻结，等你拍板（重试/换思路/取消）",
                    level="error",
                    log_path=LOG_DIR / f"watchdog-{datetime.now().strftime('%Y-%m-%d')}.log",
                )
            except Exception as e:
                _log(f"escalate push fail {task_id}: {e}")
        except Exception as e:
            _log(f"escalate outer fail {task_id}: {e}")

    # 4) timeouts 标 + 推（v2 原有行为）
    timeout_ids = [t["task_id"] for t, _ in timeouts]
    archived = []
    if timeout_ids:
        archived = tq.mark_timeouts_batch(timeout_ids)
    # 4.5) Cortex-lite：累计超时 → 自动调参
    cortex_adjusts = []
    for task, _ in timeouts:
        if task["task_id"] in archived:
            try:
                import cortex as tq_cortex
                r = tq_cortex.record_timeout(task["agent_role"])
                if r.get("auto_adjusted"):
                    cortex_adjusts.append({
                        "role": task["agent_role"],
                        "new_timeout": r["state"].get("auto_timeout"),
                        "reason": r["reason"],
                    })
                    _log(f"CORTEX_ADJ {task['agent_role']}: {r['reason']}")
            except Exception as e:
                _log(f"cortex record_timeout fail: {e}")
    pushed = 0
    push_errors = []
    for task, gap in timeouts:
        if task["task_id"] not in archived:
            continue
        msg = _format_stale_msg(task, gap)
        try:
            tq_push.push(msg, level="error",
                         log_path=LOG_DIR / f"watchdog-{datetime.now().strftime('%Y-%m-%d')}.log")
            pushed += 1
        except Exception as e:
            push_errors.append({"task_id": task["task_id"], "err": str(e)})
            _log(f"push fail {task['task_id']}: {e}")

    return {
        "scanned_at": now,
        "stale_total": len(all_stale),
        "nudges": len(nudges),
        "pings": len(pings),
        "escalates": len(escalates),
        "timeouts": len(timeouts),
        "timeout_pushed": pushed,
        "push_errors": push_errors,
        "cortex_adjusts": cortex_adjusts,
    }


def purge_stale_on_startup(stale_threshold: int = 10):
    """
    启动时清理 active 中"超 10×timeout 没心跳"的脏数据。
    - 防 test 残留 / 防前次 watchdog 异常退出留下陈旧任务。
    - 用 cancel（不是 timeout）—因为是启动期"清场"不是"判定超时"。
    """
    now = int(time.time())
    purged = []
    for t in tq.list_active():
        gap = now - t.get("last_heartbeat", now)
        threshold = t.get("timeout_sec", 60) * stale_threshold
        if gap > threshold:
            try:
                tq.cancel(t["task_id"])
                purged.append((t["task_id"], gap, threshold))
            except Exception as e:
                _log(f"purge fail {t['task_id']}: {e}")
    if purged:
        _log(f"startup purge: {len(purged)} stale tasks cancelled")
        for tid, gap, th in purged[:10]:  # 最多 log 10 条
            _log(f"  purged {tid} gap={gap}s threshold={th}s")
    return len(purged)


def run_forever(interval_sec: int = 60):
    """主循环。"""
    _log(f"watchdog start, interval={interval_sec}s, pid={os.getpid()}")
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    # P1-8: 启动时清陈旧 active 任务
    try:
        n_purged = purge_stale_on_startup()
        if n_purged:
            print(f"  ⚠️  启动清场: 取消了 {n_purged} 个陈旧 active 任务（>10×timeout 没心跳）")
    except Exception as e:
        _log(f"startup purge error: {e}")
    try:
        while True:
            try:
                run_once()
            except Exception as e:
                _log(f"loop error: {e}")
            time.sleep(interval_sec)
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()


def is_running() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        if sys.platform == "win32":
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, encoding="gbk", errors="ignore"
            ).stdout
            if str(pid) in out:
                return pid
        else:
            try:
                os.kill(pid, 0)
                return pid
            except OSError:
                pass
    except Exception:
        pass
    return None


def _log_has_marker(pid: int, marker: str = "watchdog start") -> bool:
    """子进程日志里有没有"watchdog start"标记。"""
    log_file = LOG_DIR / f"watchdog-{datetime.now().strftime('%Y-%m-%d')}.log"
    if not log_file.exists():
        return False
    try:
        content = log_file.read_text(encoding="gbk", errors="ignore")
        return marker in content
    except Exception:
        return False


def start(interval_sec: int = 60):
    """
    启动 watchdog。
    P0-4 修：启动后 sleep + is_running + 查日志，验证子进程真活着。
    失败要 push 告警，不静默。
    """
    existing = is_running()
    if existing:
        print(f"watchdog already running pid={existing}")
        return

    if sys.platform == "win32":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        CREATE_NO_WINDOW = 0x08000000
        # 关键：让子进程自己开 stdout 文件（不传 fd，避开 close_fds 关闭继承句柄）
        # 子进程的 _log() 会自动写 logs/，run-forever 也会 print，但 print 没重定向就丢了
        # 解决：Popen 用 CREATE_NEW_PROCESS_GROUP + DETACHED + CREATE_NO_WINDOW，
        #       不传 stdout=，子进程 print 输出到 OS 默认（无控制台 → 丢但 Popen.PIPE 不会撑爆）
        #       真正可观察的日志在 logs/watchdog-{date}.log（_log 函数写的）
        proc = subprocess.Popen(
            [sys.executable, "-u", __file__, "run-forever", str(interval_sec)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=DETACHED_PROCESS
                        | CREATE_NEW_PROCESS_GROUP
                        | CREATE_NO_WINDOW,
            close_fds=True,
        )
        child_pid = proc.pid
    else:
        proc = subprocess.Popen(
            [sys.executable, __file__, "run-forever", str(interval_sec)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        child_pid = proc.pid

    # === P0-4: 启动后真验证 ===
    time.sleep(STARTUP_WAIT_SEC)
    actual = is_running()

    if not actual:
        # 启动失败
        tq_push.push(
            f"❌ watchdog 启动失败: Popen 创建后 {STARTUP_WAIT_SEC}s 内进程消失\n"
            f"child_pid={child_pid} interval={interval_sec}s",
            level="error",
            log_path=LOG_DIR / f"watchdog-{datetime.now().strftime('%Y-%m-%d')}.log",
        )
        print(f"❌ watchdog 启动失败 (child_pid={child_pid})，告警已 push")
        return

    if not _log_has_marker(actual, "watchdog start"):
        tq_push.push(
            f"⚠️ watchdog 进程在但未写启动日志: pid={actual}\n"
            f"可能卡在 import 或 mutex。请手动查 ~/.hermes/task-queue/logs/",
            level="error",
            log_path=LOG_DIR / f"watchdog-{datetime.now().strftime('%Y-%m-%d')}.log",
        )
        print(f"⚠️ watchdog 进程在但未确认存活 pid={actual}")
        return

    print(f"✅ watchdog launched & verified pid={actual} interval={interval_sec}s")


def stop():
    pid = is_running()
    if not pid:
        print("watchdog not running")
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                       capture_output=True, encoding="gbk", errors="ignore")
    else:
        os.kill(pid, 15)
    if PID_FILE.exists():
        PID_FILE.unlink()
    print(f"watchdog stopped (pid={pid})")


def status():
    pid = is_running()
    if pid:
        has_marker = _log_has_marker(pid, "watchdog start")
        print(f"RUNNING pid={pid} (log_marker={'✓' if has_marker else '✗'})")
    else:
        print("STOPPED")
    # v3: 三档分类展示
    now = int(time.time())
    active = tq.list_active()
    nudge_l = []
    ping_l = []
    esc_l = []
    timeout_l = []
    for t in active:
        gap = now - t["last_heartbeat"]
        sw = t["heartbeat_sec"]
        if gap >= t["timeout_sec"]:
            timeout_l.append((t, gap))
        elif gap >= 3 * sw:
            esc_l.append((t, gap))
        elif gap >= 2 * sw:
            ping_l.append((t, gap))
        elif gap >= sw:
            nudge_l.append((t, gap))

    if nudge_l or ping_l or esc_l or timeout_l:
        print(f"\n⚠️  假死相关任务: {len(nudge_l)+len(ping_l)+len(esc_l)+len(timeout_l)}")
        for t, gap in timeout_l:
            print(f"  🔴 TIMEOUT  {t['task_id']} ({t['agent_role']}) gap={gap}s")
        for t, gap in esc_l:
            print(f"  🟠 ESCALATE {t['task_id']} ({t['agent_role']}) gap={gap}s")
        for t, gap in ping_l:
            print(f"  🟡 PING     {t['task_id']} ({t['agent_role']}) gap={gap}s")
        for t, gap in nudge_l:
            print(f"  🟢 NUDGE    {t['task_id']} ({t['agent_role']}) gap={gap}s")
    else:
        print("✓ 没有假死相关任务")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "start":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        start(interval)
    elif cmd == "stop":
        stop()
    elif cmd == "status":
        status()
    elif cmd == "run-once":
        result = run_once()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif cmd == "run-forever":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        run_forever(interval)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
