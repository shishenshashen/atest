"""
test_task_queue_v4.py — Phase 2 覆盖：level + 4 问 + cortex-lite
跑法: python test_task_queue_v4.py
"""
import sys
import time
import json
import importlib
from pathlib import Path

ROOT = Path.home() / ".hermes" / "skills" / "task-queue"
sys.path.insert(0, str(ROOT))

# 清模块缓存
for mod in ["queue", "journal", "watchdog", "push", "dispatch", "review", "cortex"]:
    if mod in sys.modules:
        del sys.modules[mod]

import tq_queue as tq
import cortex as tq_cortex
import watchdog as tq_wd

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
    (Path.home() / ".hermes" / "task-queue" / "queue.json").write_text(
        "{}", encoding="utf-8")
    # 清 nudges
    tq.NUDGES_DIR.mkdir(parents=True, exist_ok=True)
    for f in tq.NUDGES_DIR.glob("*.json"):
        f.unlink()
    # 重置 cortex
    for r in ["ops", "general", "coder", "tester", "researcher"]:
        tq_cortex.reset(r)


# L 任务必填 4 问
L_FILES = ["x.py"]
L_VERIFY = ["pytest"]
L_DELIVER = "x.py + 报告"


# 简化 enqueue：自动填 L 任务的 4 问
def enq(goal, **kw):
    if kw.get("agent_role") in ("researcher", "coder") and "files" not in kw:
        kw["files"] = L_FILES
        kw["verify_plan"] = L_VERIFY
        kw["deliverable"] = L_DELIVER
    return tq.enqueue(goal, **kw)


def backdate(task_id, secs):
    tq.mutate(lambda tasks: tasks.update({
        task_id: {**tasks[task_id],
                  "last_heartbeat": int(time.time()) - secs}
    }))


# ==================== Test V4-1: level 默认值表 ====================
print("\n" + "=" * 60)
print("Test V4-1: role → level 默认映射")
print("=" * 60)
reset_active()
expected_levels = {"ops": "S", "tester": "M", "general": "M",
                   "researcher": "L", "coder": "L"}
for role, exp_lv in expected_levels.items():
    t = enq(f"test {role}", agent_role=role)
    check(f"V4-1.x {role} → {exp_lv}",
          t["level"] == exp_lv, f"got {t['level']}")


# ==================== Test V4-2: 显式 level 覆盖 ====================
print("\n" + "=" * 60)
print("Test V4-2: 显式 level 覆盖默认")
print("=" * 60)
reset_active()
t = enq("override", agent_role="coder", level="S")
check("V4-2.1 coder 显式 S", t["level"] == "S")
t2 = tq.enqueue("override2", agent_role="ops", level="CRITICAL",
                files=["x"], verify_plan=["y"], deliverable="z")
check("V4-2.2 ops 显式 CRITICAL", t2["level"] == "CRITICAL")

# ==================== Test V4-3: 非法 level ====================
print("\n" + "=" * 60)
print("Test V4-3: 非法 level 报错")
print("=" * 60)
reset_active()
try:
    t = tq.enqueue("bad", level="X")
    check("V4-3.1 非法 level 应报", False, "没报")
except ValueError as e:
    check("V4-3.1 非法 level 应报", "invalid level" in str(e), str(e)[:80])


# ==================== Test V4-4: S 不必填 4 问 ====================
print("\n" + "=" * 60)
print("Test V4-4: S/M 任务不强制 4 问")
print("=" * 60)
reset_active()
t_s = tq.enqueue("S 任务", agent_role="ops")
check("V4-4.1 S 不传 4 问 OK", t_s["level"] == "S"
      and t_s["files"] == [] and t_s["verify_plan"] == []
      and t_s["deliverable"] == "")

t_m = tq.enqueue("M 任务", agent_role="general")
check("V4-4.2 M 不传 4 问 OK", t_m["level"] == "M")


# ==================== Test V4-5: L 必填 4 问 ====================
print("\n" + "=" * 60)
print("Test V4-5: L 任务 4 问必填校验")
print("=" * 60)
reset_active()

# 5.1 缺全部
try:
    tq.enqueue("L 缺全部", agent_role="researcher")
    check("V4-5.1 L 缺 4 问应报", False, "没报")
except ValueError as e:
    check("V4-5.1 L 缺 4 问应报",
          "缺" in str(e) and "files" in str(e), str(e)[:80])

# 5.2 缺 deliverable
try:
    tq.enqueue("L 缺 deliverable", agent_role="researcher",
              files=["a.py"], verify_plan=["b"])
    check("V4-5.2 L 缺 deliverable 应报", False, "没报")
except ValueError as e:
    check("V4-5.2 L 缺 deliverable 应报",
          "deliverable" in str(e), str(e)[:80])

# 5.3 全填 OK
t = tq.enqueue("L 全填", agent_role="researcher",
              files=["a.py", "b.py"], verify_plan=["pytest"],
              deliverable="改后的 a.py + 测试报告")
check("V4-5.3 L 全填 OK", t["level"] == "L"
      and t["files"] == ["a.py", "b.py"])


# ==================== Test V4-6: CRITICAL 必填 + deliverable 非空 ====================
print("\n" + "=" * 60)
print("Test V4-6: CRITICAL 严格校验")
print("=" * 60)
reset_active()

# 6.1 缺 deliverable 必报
try:
    tq.enqueue("CRIT 缺", agent_role="general", level="CRITICAL",
              files=["x"], verify_plan=["y"], deliverable="")
    check("V4-6.1 CRIT 空 deliverable 应报", False, "没报")
except ValueError as e:
    check("V4-6.1 CRIT 空 deliverable 应报",
          "deliverable" in str(e), str(e)[:80])

# 6.2 全填 OK
t = tq.enqueue("CRIT OK", agent_role="general", level="CRITICAL",
              files=["a.mq5"], verify_plan=["compile pass"],
              deliverable="a.mq5 + compile.log")
check("V4-6.2 CRIT 全填 OK", t["level"] == "CRITICAL"
      and len(t["files"]) == 1)


# ==================== Test V4-7: cortex record_timeout 降级 ====================
print("\n" + "=" * 60)
print("Test V4-7: cortex.record_timeout 累计 3 次降级")
print("=" * 60)
reset_active()

# ops 默认 120，3 次后应降到 60
r1 = tq_cortex.record_timeout("ops")
check("V4-7.1 第 1 次不调", r1["auto_adjusted"] is False)
r2 = tq_cortex.record_timeout("ops")
check("V4-7.2 第 2 次不调", r2["auto_adjusted"] is False)
r3 = tq_cortex.record_timeout("ops")
check("V4-7.3 第 3 次降级", r3["auto_adjusted"] is True
      and r3["state"]["auto_timeout"] == 60,
      str(r3["state"]))

# cortex 影响 enqueue
t = tq.enqueue("after cortex", agent_role="ops")
check("V4-7.4 enqueue 拿到 cortex 调过的 60", t["timeout_sec"] == 60,
      f"got {t['timeout_sec']}")


# ==================== Test V4-8: cortex 手动覆盖 ====================
print("\n" + "=" * 60)
print("Test V4-8: cortex 手动覆盖")
print("=" * 60)
tq_cortex.reset("ops")
tq_cortex.set_manual("ops", 300)
t = tq.enqueue("manual test", agent_role="ops")
check("V4-8.1 手动 300 优先", t["timeout_sec"] == 300, f"got {t['timeout_sec']}")

# 显式传覆盖 cortex
t2 = tq.enqueue("explicit", agent_role="ops", timeout_sec=999)
check("V4-8.2 显式 999 覆盖 cortex", t2["timeout_sec"] == 999)


# ==================== Test V4-9: watchdog run_once 调 cortex ====================
print("\n" + "=" * 60)
print("Test V4-9: watchdog timeout 调 cortex")
print("=" * 60)
reset_active()
fake = tq.enqueue("wd cortex test", agent_role="ops",
                  timeout_sec=10, heartbeat_sec=2)
tq.heartbeat(fake["task_id"], status="running")
backdate(fake["task_id"], 15)  # 触发 timeout

# 清空 notice
notice = Path.home() / ".hermes" / "task-queue" / "pending_notices.json"
if notice.exists():
    notice.write_text("[]", encoding="utf-8")

res = tq_wd.run_once()
check("V4-9.1 run_once timeouts=1", res["timeouts"] == 1, str(res))
check("V4-9.2 cortex_adjusts 字段存在", "cortex_adjusts" in res, str(res.keys()))

# 此时 cortex.ops 应有 total_timeout=1（不到 3 不调）
state = tq_cortex.get_state("ops")
check("V4-9.3 cortex 累计 ops=1", state.get("total_timeout", 0) == 1,
      f"got {state.get('total_timeout')}")
check("V4-9.4 cortex 未调（累计 < 3）", state.get("auto_timeout") is None,
      f"auto_timeout={state.get('auto_timeout')}")


# ==================== Test V4-10: 累计 3 次 watchdog 触发 cortex 降级 ====================
print("\n" + "=" * 60)
print("Test V4-10: 累计 3 次 timeout → cortex 降级")
print("=" * 60)
reset_active()

# 制造 3 个 timeout
for i in range(3):
    f = tq.enqueue(f"batch {i}", agent_role="ops",
                   timeout_sec=10, heartbeat_sec=2)
    tq.heartbeat(f["task_id"], status="running")
    backdate(f["task_id"], 15)
    res = tq_wd.run_once()
    if i == 2:
        # 第 3 次应触发 cortex
        check(f"V4-10.1 第 3 次有 cortex 调参",
              len(res["cortex_adjusts"]) > 0, str(res["cortex_adjusts"]))

state = tq_cortex.get_state("ops")
check("V4-10.2 cortex auto_timeout=60",
      state.get("auto_timeout") == 60, f"got {state.get('auto_timeout')}")


# ==================== Test V4-11: render_daily 含等级分布 ====================
print("\n" + "=" * 60)
print("Test V4-11: journal render_daily 含等级分布")
print("=" * 60)
reset_active()
# 入队不同等级的任务
enq("S1", agent_role="ops")
enq("M1", agent_role="general", files=["a"], verify_plan=["b"],
    deliverable="c")
enq("L1", agent_role="researcher", files=["x.py"],
    verify_plan=["pytest"], deliverable="x.py")
# 标 done
for t in tq.list_active():
    tq.mark_done(t["task_id"], result={"artifacts": []})

import journal as tq_journal
report = tq_journal.render_daily(time.strftime("%Y-%m-%d"))
check("V4-11.1 报告含 '## 等级分布'", "## 等级分布" in report, "missing")
check("V4-11.2 报告含 S 等级", "**S**" in report, "missing S")
check("V4-11.3 报告含 M 等级", "**M**" in report, "missing M")
check("V4-11.4 报告含 L 等级", "**L**" in report, "missing L")


# ==================== 总结 ====================
print("\n" + "=" * 60)
print(f"✅ 通过: {len(PASS)}    ❌ 失败: {len(FAIL)}")
print("=" * 60)
if FAIL:
    print("\n失败详情:")
    for n, d in FAIL:
        print(f"  ✗ {n}: {d}")
    sys.exit(1)
else:
    print("\n🎉 全部通过！task-queue Phase 2 上线")
    print("""
    新能力（Phase 2）：
    ✓ 任务等级 S/M/L/CRITICAL（4 档）
    ✓ role → level 默认映射
    ✓ L/CRITICAL 必填 4 问（files/verify_plan/deliverable）
    ✓ CRITICAL 额外要求 deliverable 非空
    ✓ Cortex-lite：累计 3 次超时自动降 timeout
    ✓ Cortex-lite：手动 override 优先
    ✓ watchdog timeout 调 cortex
    ✓ render_daily 加等级分布
    """)
