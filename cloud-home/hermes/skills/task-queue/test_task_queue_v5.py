"""
test_task_queue_v5.py — Phase 3 覆盖：ship 闭环 + push_done_summary
跑法: python test_task_queue_v5.py
"""
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path.home() / ".hermes" / "skills" / "task-queue"
sys.path.insert(0, str(ROOT))

# 清模块缓存
for mod in ["queue", "journal", "watchdog", "push", "dispatch", "review", "cortex"]:
    if mod in sys.modules:
        del sys.modules[mod]

import tq_queue as tq
import push as tq_push
import dispatch as tq_dispatch

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
    tq.NUDGES_DIR.mkdir(parents=True, exist_ok=True)
    for f in tq.NUDGES_DIR.glob("*.json"):
        f.unlink()
    notice = Path.home() / ".hermes" / "task-queue" / "pending_notices.json"
    notice.write_text("[]", encoding="utf-8")


# ==================== Test V5-1: push_done_summary 基础 ====================
print("\n" + "=" * 60)
print("Test V5-1: push_done_summary 基础推送")
print("=" * 60)
reset_active()
t = tq.enqueue("V5-1 推送测试", agent_role="ops")
tq.heartbeat(t["task_id"], status="running")
tq.mark_done(t["task_id"], result={
    "summary": "ok",
    "artifacts": [
        {"path": "C:/test/a.py", "size": 100, "hash": "abcd1234"},
        {"path": "C:/test/b.py", "size": 200, "hash": "efgh5678"},
    ]
})

got = tq.get(t["task_id"])
res = tq_push.push_done_summary(got, journal_path="~/.hermes/journal/2026-06-11.md",
                                 verify_result={"verified": True})
check("V5-1.1 push 不报错", "notice" in res)
notice = Path.home() / ".hermes" / "task-queue" / "pending_notices.json"
ns = json.loads(notice.read_text(encoding="utf-8"))
check("V5-1.2 notice 收到 1 条", len(ns) == 1, f"got {len(ns)}")
check("V5-1.3 notice level=info", ns[0]["level"] == "info")
check("V5-1.4 msg 含 task_id", got["task_id"] in ns[0]["msg"])
check("V5-1.5 msg 含 '任务完成'", "任务完成" in ns[0]["msg"])
check("V5-1.6 msg 含 level=[S]", "[S]" in ns[0]["msg"])
check("V5-1.7 msg 含产物", "a.py" in ns[0]["msg"] and "b.py" in ns[0]["msg"])
check("V5-1.8 msg 含 ✅ verify ok", "✅ verify ok" in ns[0]["msg"])
check("V5-1.9 msg 含 journal 路径", "journal" in ns[0]["msg"])


# ==================== Test V5-2: push_done_summary 无产物 ====================
print("\n" + "=" * 60)
print("Test V5-2: 无产物场景")
print("=" * 60)
reset_active()
t = tq.enqueue("V5-2 无产物", agent_role="ops")
tq.heartbeat(t["task_id"], status="running")
tq.mark_done(t["task_id"], result={"summary": "no artifacts"})

got = tq.get(t["task_id"])
tq_push.push_done_summary(got)
ns = json.loads(notice.read_text(encoding="utf-8"))
check("V5-2.1 无产物也推", len(ns) >= 1)
check("V5-2.2 提示 (无)", "(无)" in ns[-1]["msg"])


# ==================== Test V5-3: push_done_summary 含 verify 失败 ====================
print("\n" + "=" * 60)
print("Test V5-3: verify 失败时也推")
print("=" * 60)
reset_active()
t = tq.enqueue("V5-3 verify 失败", agent_role="ops")
tq.heartbeat(t["task_id"], status="running")
tq.mark_done(t["task_id"], result={"artifacts": []})

got = tq.get(t["task_id"])
tq_push.push_done_summary(got, verify_result={"verified": False, "error": "file not found"})
ns = json.loads(notice.read_text(encoding="utf-8"))
check("V5-3.1 verify 失败也推", len(ns) >= 1)
check("V5-3.2 msg 含 ❌", "❌" in ns[-1]["msg"])


# ==================== Test V5-4: ship() done 完整闭环 ====================
print("\n" + "=" * 60)
print("Test V5-4: ship() 完整闭环（done）")
print("=" * 60)
reset_active()
t = tq.enqueue("V5-4 ship 闭环", agent_role="general",
              files=["x.py"], verify_plan=["pytest"],
              deliverable="x.py + log")
tq.heartbeat(t["task_id"], status="running")
# 真实产物
real_artifact = Path.home() / "tmp_v5_test.txt"
real_artifact.write_text("hello v5", encoding="utf-8")
real_h = hashlib.sha256(real_artifact.read_bytes()).hexdigest()
real_s = real_artifact.stat().st_size
tq.mark_done(t["task_id"], result={
    "artifacts": [{"path": str(real_artifact), "size": real_s, "hash": real_h}]
})

# 调 ship
res = tq_dispatch.ship(t["task_id"], summary="v5 ship test")
check("V5-4.1 status=done", res["status"] == "done")
check("V5-4.2 journal 有", res.get("journal") is not None)
check("V5-4.3 verify 有", res.get("verify") is not None)
check("V5-4.4 verify.verified=True", res["verify"]["verified"] is True,
      str(res["verify"]))
check("V5-4.5 push 有", res.get("push") is not None)
ns = json.loads(notice.read_text(encoding="utf-8"))
# 最后一条是 ship 推的
ship_msg = [n["msg"] for n in ns if "v5 ship test" in n.get("msg", "")
            or t["task_id"] in n.get("msg", "")]
check("V5-4.6 ship 推了总结", len(ship_msg) >= 1)

# 清理
real_artifact.unlink()


# ==================== Test V5-5: ship() failed 推 warn ====================
print("\n" + "=" * 60)
print("Test V5-5: ship() 失败也推")
print("=" * 60)
reset_active()
t = tq.enqueue("V5-5 失败场景", agent_role="ops")
tq.heartbeat(t["task_id"], status="running")
# 标 failed
tq.mark_failed(t["task_id"], "测试失败原因", reason="test")

# ship with error
res = tq_dispatch.ship(t["task_id"], error="测试失败原因", summary="")
check("V5-5.1 status=failed", res["status"] == "failed")
check("V5-5.2 push_fail 有", res.get("push_fail") is not None)
ns = json.loads(notice.read_text(encoding="utf-8"))
failed_msg = [n for n in ns if n["level"] == "warn"]
check("V5-5.3 推了 warn", len(failed_msg) >= 1)
check("V5-5.4 warn 含 failed 状态", "failed" in failed_msg[-1]["msg"])


# ==================== Test V5-6: ship() timeout 推 warn ====================
print("\n" + "=" * 60)
print("Test V5-6: ship() timeout 推 warn")
print("=" * 60)
reset_active()
t = tq.enqueue("V5-6 timeout", agent_role="ops")
tq.heartbeat(t["task_id"], status="running")
# 模拟 watchdog 标 timeout
tq.mark_timeout(t["task_id"])

res = tq_dispatch.ship(t["task_id"], error="模拟 timeout")
check("V5-6.1 status=timeout", res["status"] == "timeout")
check("V5-6.2 push_fail 有", res.get("push_fail") is not None)
ns = json.loads(notice.read_text(encoding="utf-8"))
to_msg = [n for n in ns if "timeout" in n.get("msg", "")]
check("V5-6.3 推了 timeout 告警", len(to_msg) >= 1)


# ==================== Test V5-7: finalize 内部自动推 (Phase 3 默认) ====================
print("\n" + "=" * 60)
print("Test V5-7: finalize() 默认 push_summary=True")
print("=" * 60)
reset_active()
t = tq.enqueue("V5-7 finalize 默认推", agent_role="ops")
tq.heartbeat(t["task_id"], status="running")
tq.mark_done(t["task_id"], result={"artifacts": []})

# 调 finalize（不显式 push_summary）
res = tq_dispatch.finalize(t["task_id"], summary="")
check("V5-7.1 finalize 返回 push", "push" in res)
ns = json.loads(notice.read_text(encoding="utf-8"))
check("V5-7.2 finalize 自动推了总结", len(ns) >= 1)


# ==================== Test V5-8: finalize(push_summary=False) 不推 ====================
print("\n" + "=" * 60)
print("Test V5-8: finalize(push_summary=False) 关闭自动推")
print("=" * 60)
reset_active()
t = tq.enqueue("V5-8 关闭推", agent_role="ops")
tq.heartbeat(t["task_id"], status="running")
tq.mark_done(t["task_id"], result={"artifacts": []})

before = len(json.loads(notice.read_text(encoding="utf-8")))
tq_dispatch.finalize(t["task_id"], summary="", push_summary=False)
after = len(json.loads(notice.read_text(encoding="utf-8")))
check("V5-8.1 push_summary=False 不增加 notice", after == before,
      f"before={before} after={after}")


# ==================== Test V5-9: 产物 > 5 个截断 ====================
print("\n" + "=" * 60)
print("Test V5-9: 产物 > 5 截断")
print("=" * 60)
reset_active()
t = tq.enqueue("V5-9 多产物", agent_role="ops")
tq.heartbeat(t["task_id"], status="running")
arts = [{"path": f"C:/test/f{i}.py", "size": 100*i, "hash": f"h{i}"} for i in range(8)]
tq.mark_done(t["task_id"], result={"artifacts": arts})

got = tq.get(t["task_id"])
tq_push.push_done_summary(got)
ns = json.loads(notice.read_text(encoding="utf-8"))
msg = ns[-1]["msg"]
check("V5-9.1 截断提示出现", "还有 3 个" in msg, "missing '还有 3 个'")
check("V5-9.2 显示前 5 个", "f0.py" in msg and "f4.py" in msg)


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
    print("\n🎉 全部通过！task-queue Phase 3 ship 闭环上线")
    print("""
    新能力（Phase 3）：
    ✓ push_done_summary(task, verify_result, journal_path) 推完整总结
    ✓ finalize() 默认 push_summary=True 自动推
    ✓ finalize(push_summary=False) 关闭自动推
    ✓ ship(task_id) 1 行走完 verify+journal+推总结
    ✓ ship() 失败也推 warn 级别
    ✓ ship() timeout 也推 warn 级别
    ✓ 产物 > 5 截断展示
    ✓ tq.py CLI 加 ship 子命令
    """)
