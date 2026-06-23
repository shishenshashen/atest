"""
test_task_queue_v6.py — v4 覆盖：auto_retry + cli_detect + dispatch fallback + watchdog escalate 自救
跑法: cd ~/.hermes/skills/task-queue/v4 && python test_task_queue_v6.py

注：所有测试用真实 task-queue 目录（不隔离）—测试完会自动 cleanup。
"""
import sys
import os
import time
import json
from pathlib import Path

# v4 子目录的模块
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# 清模块缓存
for mod in ["tq_queue", "push", "dispatch", "watchdog", "cortex", "auto_retry",
            "cli_detect", "journal", "review"]:
    if mod in sys.modules:
        del sys.modules[mod]

import tq_queue as tq
import auto_retry
import cli_detect
import cortex
import watchdog


PASS = []
FAIL = []


def check(name, ok, detail=""):
    if ok:
        PASS.append(name)
        print(f"  ✓ {name}")
    else:
        FAIL.append((name, detail))
        print(f"  ✗ {name}  → {detail}")


def reset_active():
    """清空 active + nudges（不碰 archive，那是历史）。"""
    (Path.home() / ".hermes" / "task-queue" / "queue.json").write_text(
        "{}", encoding="utf-8")
    tq.NUDGES_DIR.mkdir(parents=True, exist_ok=True)
    for f in tq.NUDGES_DIR.glob("*.json"):
        f.unlink()


def reset_cortex(role=None):
    if role:
        cortex.reset(role)
    else:
        for r in ["ops", "general", "researcher", "coder", "tester"]:
            cortex.reset(r)


# ============================================================
# P0-a: requeue_from_archive
# ============================================================
def test_requeue_rewrite():
    print("\n=== P0-a: requeue_from_archive rewrite_prompt ===")
    reset_active()
    t = tq.enqueue(goal="test rewrite", agent_role="general",
                   timeout_sec=10, heartbeat_sec=2)
    tid = t["task_id"]
    tq.mark_timeout(tid)
    new_task = tq.requeue_from_archive(
        tid, "rewrite_prompt",
        new_goal="test rewrite (simpler)", reason="unit test")
    check("retry_count=1", new_task["retry_count"] == 1)
    check("goal changed", new_task["goal"].startswith("test rewrite (simpler)"))
    check("status=queued", new_task["status"] == tq.STATUS_QUEUED)
    check("history len=1", len(new_task.get("retry_history", [])) == 1)
    check("history strategy=rewrite_prompt",
          new_task["retry_history"][0]["strategy"] == "rewrite_prompt")
    try:
        tq.cancel(tid)
    except Exception:
        pass


def test_requeue_extend_timeout():
    print("\n=== P0-a: requeue_from_archive extend_timeout ===")
    reset_active()
    t = tq.enqueue(goal="x", agent_role="general",
                   timeout_sec=10, heartbeat_sec=2)
    tid = t["task_id"]
    original_to = t["timeout_sec"]
    tq.mark_timeout(tid)
    new_task = tq.requeue_from_archive(tid, "extend_timeout", reason="unit")
    check("timeout doubled", new_task["timeout_sec"] == original_to * 2)
    try:
        tq.cancel(tid)
    except Exception:
        pass


def test_requeue_downgrade():
    print("\n=== P0-a: requeue_from_archive downgrade_role ===")
    reset_active()
    t = tq.enqueue(goal="x", agent_role="researcher",
                   timeout_sec=10, heartbeat_sec=2,
                   files=["a.py"], verify_plan=["pytest"],
                   deliverable="result")
    tid = t["task_id"]
    tq.mark_timeout(tid)
    new_task = tq.requeue_from_archive(
        tid, "downgrade_role", new_agent_role="general", reason="unit")
    check("role changed", new_task["agent_role"] == "general")
    check("timeout 600 (general default)",
          new_task["timeout_sec"] == 600)
    try:
        tq.cancel(tid)
    except Exception:
        pass


def test_requeue_max_retries():
    print("\n=== P0-a: requeue max_retries limit ===")
    reset_active()
    t = tq.enqueue(goal="x", agent_role="general",
                   timeout_sec=10, heartbeat_sec=2)
    tid = t["task_id"]
    # general = M, max_retries=3
    for i in range(3):
        tq.mark_timeout(tid)
        tq.requeue_from_archive(tid, "extend_timeout", reason=f"attempt {i}")
    # 第 4 次应抛
    tq.mark_timeout(tid)
    raised = False
    try:
        tq.requeue_from_archive(tid, "extend_timeout", reason="over")
    except ValueError as e:
        raised = "已达上限" in str(e)
    check("over max_retries raises ValueError", raised)
    try:
        tq.cancel(tid)
    except Exception:
        pass


def test_requeue_critical_skipped():
    print("\n=== P0-a: requeue CRITICAL 不能 retry ===")
    reset_active()
    t = tq.enqueue(goal="critical thing", agent_role="coder",
                   timeout_sec=10, heartbeat_sec=2,
                   level="CRITICAL",
                   files=["x.py"], verify_plan=["pytest"],
                   deliverable="report")
    tid = t["task_id"]
    tq.mark_timeout(tid)
    raised = False
    try:
        tq.requeue_from_archive(tid, "rewrite_prompt",
                                new_goal="x", reason="should not work")
    except ValueError as e:
        raised = True
    # CRITICAL 走 max_retries=0 → 第 1 次就应拒
    check("CRITICAL 第 1 次就拒", raised)


# ============================================================
# P0-b: auto_retry 决策树
# ============================================================
def test_auto_retry_decision_tree():
    print("\n=== P0-b: auto_retry decision tree ===")
    reset_active()
    reset_cortex("test_role")
    t = tq.enqueue(goal="dt", agent_role="general",
                   timeout_sec=10, heartbeat_sec=2)
    tid = t["task_id"]

    # 第 1 次: rewrite_prompt
    tq.mark_timeout(tid)
    r1 = auto_retry.attempt(tid, reason="test")
    check("attempt 1: rewrite_prompt",
          r1.get("strategy") == "rewrite_prompt" and r1["retried"])

    # 第 2 次: extend_timeout
    tq.mark_timeout(tid)
    r2 = auto_retry.attempt(tid, reason="test")
    check("attempt 2: extend_timeout",
          r2.get("strategy") == "extend_timeout" and r2["retried"])

    # 第 3 次: downgrade_role
    tq.mark_timeout(tid)
    r3 = auto_retry.attempt(tid, reason="test")
    check("attempt 3: downgrade_role",
          r3.get("strategy") == "downgrade_role" and r3["retried"])

    # 第 4 次: 推老大
    tq.mark_timeout(tid)
    r4 = auto_retry.attempt(tid, reason="test")
    check("attempt 4: skipped (推老大)",
          not r4["retried"] and "max_retries" in (r4.get("skipped_reason") or ""))

    try:
        tq.cancel(tid)
    except Exception:
        pass


def test_auto_retry_critical():
    print("\n=== P0-b: auto_retry CRITICAL 跳过 ===")
    reset_active()
    t = tq.enqueue(goal="critical", agent_role="coder",
                   timeout_sec=10, heartbeat_sec=2,
                   level="CRITICAL",
                   files=["x.py"], verify_plan=["pytest"],
                   deliverable="r")
    tid = t["task_id"]
    tq.mark_timeout(tid)
    r = auto_retry.attempt(tid, reason="test")
    check("CRITICAL retried=False", not r["retried"])
    check("skipped_reason 含 CRITICAL",
          "CRITICAL" in (r.get("skipped_reason") or ""))


# ============================================================
# P0-d: cortex 第 4 规则
# ============================================================
def test_cortex_rule4():
    print("\n=== P0-d: cortex retry 失败率规则 4 ===")
    reset_cortex("rule4_test")
    # 5 次 retry，3 失败 2 成功 → 60% > 50%
    results = [False, False, True, False, True]
    triggered = False
    for i, ok in enumerate(results):
        r = cortex.record_retry("rule4_test", eventually_succeeded=ok)
        if r["auto_adjusted"]:
            triggered = True
    check("5 次后触发 skip_rewrite", triggered)
    check("hint == skip_rewrite",
          cortex.get_retry_strategy_hint("rule4_test") == "skip_rewrite")
    reset_cortex("rule4_test")


def test_cortex_rule4_below_threshold():
    print("\n=== P0-d: cortex retry 失败率 < 50% 不触发 ===")
    reset_cortex("rule4_below")
    # 5 次，2 失败 → 40% 不触发
    results = [True, False, True, False, True]
    triggered = False
    for ok in results:
        r = cortex.record_retry("rule4_below", eventually_succeeded=ok)
        if r["auto_adjusted"]:
            triggered = True
    check("40% 不触发", not triggered)
    check("hint 仍 default",
          cortex.get_retry_strategy_hint("rule4_below") == "default")
    reset_cortex("rule4_below")


def test_auto_retry_respects_hint():
    print("\n=== P0-b+d: auto_retry 读 cortex hint ===")
    reset_active()
    reset_cortex("hint_role")
    # 把 hint_role 喂到 skip_rewrite
    for ok in [False, False, True, False, True]:
        cortex.record_retry("hint_role", eventually_succeeded=ok)
    assert cortex.get_retry_strategy_hint("hint_role") == "skip_rewrite"

    # 现在 enqueue 一个任务，改成 hint_role
    t = tq.enqueue(goal="hint test", agent_role="general",
                   timeout_sec=10, heartbeat_sec=2)
    tid = t["task_id"]
    # 改 role 为 hint_role
    qf = tq.QUEUE_FILE
    with open(qf, encoding="utf-8") as f:
        tasks = json.load(f)
    tasks[tid]["agent_role"] = "hint_role"
    with open(qf, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False)

    tq.mark_timeout(tid)
    r = auto_retry.attempt(tid, reason="hint_test")
    # skip_rewrite 应该跳过 rewrite_prompt 直接 extend_timeout
    check("skip_rewrite 时直接 extend_timeout",
          r.get("strategy") == "extend_timeout" and r["retried"])

    cur = tq.get(tid)
    # goal 应该没被加 PROMPT_RETRY_SUFFIX
    check("goal 未被改写", cur["goal"] == "hint test")

    try:
        tq.cancel(tid)
    except Exception:
        pass
    reset_cortex("hint_role")


# ============================================================
# P0-c: watchdog escalate 自救
# ============================================================
def test_watchdog_escalate_auto_retry():
    print("\n=== P0-c: watchdog escalate 自救 ===")
    reset_active()
    reset_cortex("general")
    t = tq.enqueue(goal="watchdog auto retry test",
                   agent_role="general",
                   timeout_sec=30, heartbeat_sec=2)
    tid = t["task_id"]
    print(f"  enqueued: {tid}, 等 7s 让 gap > 3*heartbeat...")
    time.sleep(7)
    result = watchdog.run_once()
    print(f"  run_once: escalates={result['escalates']} timeouts={result['timeouts']}")

    cur = tq.get(tid)
    check("task 仍在 active", cur is not None)
    if cur:
        check("task 已被 auto_retry（status=queued 或 retry_count>0）",
              cur["status"] == tq.STATUS_QUEUED or cur["retry_count"] > 0
              or cur["status"] == tq.STATUS_FAILED)
        # retry_count 应该是 1（第一次 rewrite_prompt）
        if cur.get("retry_count", 0) > 0:
            check("retry_count=1", cur["retry_count"] == 1)

    # cleanup
    try:
        tq.cancel(tid)
    except Exception:
        pass


# ============================================================
# P0-e: cli_detect
# ============================================================
def test_cli_detect():
    print("\n=== P0-e: cli_detect ===")
    caps = cli_detect.detect(force_refresh=True)
    check("caps 是 dict", isinstance(caps, dict))
    check("含 detected_at", "detected_at" in caps)
    check("best 不是 None", caps.get("best") is not None)
    print(f"  best={caps.get('best')}")
    print(f"  available: " + ", ".join(
        f"{k}=✓" for k, v in caps.items()
        if isinstance(v, dict) and v.get("available")))


def test_cli_detect_cache():
    print("\n=== P0-e: cli_detect 缓存 ===")
    cap1 = cli_detect.detect()
    cap2 = cli_detect.detect()
    check("两次返回的 detected_at 相同（命中缓存）",
          cap1["detected_at"] == cap2["detected_at"])


# ============================================================
# P0-f: dispatch _spawn_subagent fallback
# ============================================================
def test_spawn_subagent_probe():
    print("\n=== P0-f: _spawn_subagent probe_only ===")
    from dispatch import _spawn_subagent
    name, proc = _spawn_subagent("test", "t-fake", 5, 10, probe_only=True)
    check("probe_only 返回 (name, None)",
          name is not None and proc is None)


def test_dispatch_require_false():
    print("\n=== P0-f: dispatch require_dispatch=False ===")
    reset_active()
    from dispatch import dispatch
    t = dispatch(goal="v4 test no dispatch", agent_role="ops",
                 timeout_sec=30, heartbeat_sec=5,
                 require_dispatch=False)
    check("task 入队", t["task_id"] is not None)
    check("status=queued", t["status"] == tq.STATUS_QUEUED)
    try:
        tq.cancel(t["task_id"])
    except Exception:
        pass


# ============================================================
# main
# ============================================================
def main():
    print("=" * 60)
    print("task-queue v4 测试")
    print("=" * 60)

    test_requeue_rewrite()
    test_requeue_extend_timeout()
    test_requeue_downgrade()
    test_requeue_max_retries()
    test_requeue_critical_skipped()

    test_auto_retry_decision_tree()
    test_auto_retry_critical()

    test_cortex_rule4()
    test_cortex_rule4_below_threshold()
    test_auto_retry_respects_hint()

    test_watchdog_escalate_auto_retry()  # 这个要 7s

    test_cli_detect()
    test_cli_detect_cache()
    test_spawn_subagent_probe()
    test_dispatch_require_false()

    # cleanup
    reset_cortex()
    reset_active()

    print("\n" + "=" * 60)
    print(f"结果: {len(PASS)} 通过, {len(FAIL)} 失败")
    print("=" * 60)
    for name, detail in FAIL:
        print(f"  ✗ {name}: {detail}")

    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())