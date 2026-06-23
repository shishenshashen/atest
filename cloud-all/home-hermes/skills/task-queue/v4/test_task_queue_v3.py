"""
test_task_queue_v3.py — 覆盖主动推进 3 档
跑法: python test_task_queue_v3.py
"""
import sys
import time
import json
import importlib
from pathlib import Path

ROOT = Path.home() / ".hermes" / "skills" / "task-queue"
sys.path.insert(0, str(ROOT))

# 清模块缓存
for mod in ["queue", "journal", "watchdog", "push", "dispatch", "review"]:
    if mod in sys.modules:
        del sys.modules[mod]

import tq_queue as tq
import watchdog as tq_wd
import push as tq_push

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


# ==================== Test V3-1: 写 nudge + 消费 ====================
print("\n" + "=" * 60)
print("Test V3-1: write_nudge + consume_nudges")
print("=" * 60)
reset_active()
t = tq.enqueue("nudge api test", agent_role="ops",
               timeout_sec=30, heartbeat_sec=5)
n = tq.write_nudge(t["task_id"], tq.NUDGE_KIND_NUDGE, gap_sec=10)
check("V3-1.1 write_nudge 返回 kind", n["kind"] == "nudge")
check("V3-1.2 写入了 nudges/{id}.json",
      (tq.NUDGES_DIR / f"{t['task_id']}.json").exists())

consumed = tq.consume_nudges(t["task_id"])
check("V3-1.3 consume 拿到 nudge", len(consumed) == 1 and consumed[0]["kind"] == "nudge")
check("V3-1.4 consume 后文件被删",
      not (tq.NUDGES_DIR / f"{t['task_id']}.json").exists())

again = tq.consume_nudges(t["task_id"])
check("V3-1.5 再次消费返回空", again == [])

# peek 不消费
tq.write_nudge(t["task_id"], tq.NUDGE_KIND_PING, gap_sec=20)
peeked = tq.peek_nudge(t["task_id"])
again_after_peek = tq.consume_nudges(t["task_id"])
check("V3-1.6 peek 不消费", peeked["kind"] == "ping")
check("V3-1.7 peek 后仍能 consume",
      len(again_after_peek) == 1 and again_after_peek[0]["kind"] == "ping")

# ==================== Test V3-2: 档位分类 ====================
print("\n" + "=" * 60)
print("Test V3-2: run_once 档位分类")
print("=" * 60)
reset_active()

# heartbeat=2s, timeout=30s
# 1×stale=2s, 2×stale=4s, 3×stale=6s
# 入队 3 个任务：fresh / nudge / ping / escalate / timeout
t_fresh = tq.enqueue("fresh", agent_role="ops", timeout_sec=30, heartbeat_sec=2)
tq.heartbeat(t_fresh["task_id"], status="running", message="刚跑")
# 修改 last_heartbeat 模拟时间过去
def backdate(task_id, secs):
    """把 last_heartbeat 改到 N 秒前。"""
    tq.mutate(lambda tasks: tasks.update({
        task_id: {**tasks[task_id],
                  "last_heartbeat": int(time.time()) - secs}
    }))

# nudge 档：gap = 1.5 × heartbeat = 3s（介于 1×stale 和 2×stale 之间）
t_nudge = tq.enqueue("nudge-level", agent_role="ops", timeout_sec=30, heartbeat_sec=2)
tq.heartbeat(t_nudge["task_id"], status="running")
backdate(t_nudge["task_id"], 3)

# ping 档：gap = 2.5 × heartbeat = 5s
t_ping = tq.enqueue("ping-level", agent_role="ops", timeout_sec=30, heartbeat_sec=2)
tq.heartbeat(t_ping["task_id"], status="running")
backdate(t_ping["task_id"], 5)

# escalate 档：gap = 3.5 × heartbeat = 7s
t_esc = tq.enqueue("esc-level", agent_role="ops", timeout_sec=30, heartbeat_sec=2)
tq.heartbeat(t_esc["task_id"], status="running")
backdate(t_esc["task_id"], 7)

# timeout 档：gap > timeout
t_to = tq.enqueue("timeout-level", agent_role="ops", timeout_sec=5, heartbeat_sec=2)
tq.heartbeat(t_to["task_id"], status="running")
backdate(t_to["task_id"], 6)

# 清空 notice
notice = Path.home() / ".hermes" / "task-queue" / "pending_notices.json"
if notice.exists():
    notice.write_text("[]", encoding="utf-8")

result = tq_wd.run_once()
print(f"  result: {json.dumps(result, ensure_ascii=False)}")
check("V3-2.1 nudges=1", result["nudges"] == 1, str(result))
check("V3-2.2 pings=1", result["pings"] == 1, str(result))
check("V3-2.3 escalates=1", result["escalates"] == 1, str(result))
check("V3-2.4 timeouts=1", result["timeouts"] == 1, str(result))
check("V3-2.5 timeout_pushed=1", result["timeout_pushed"] == 1, str(result))

# 看 nudge 文件
nudge_file = tq.NUDGES_DIR / f"{t_nudge['task_id']}.json"
check("V3-2.6 nudge 写文件", nudge_file.exists())
ping_file = tq.NUDGES_DIR / f"{t_ping['task_id']}.json"
check("V3-2.7 ping 写文件", ping_file.exists())
esc_file = tq.NUDGES_DIR / f"{t_esc['task_id']}.json"
check("V3-2.8 escalate 写文件", esc_file.exists())

# escalate 应该推了
notices = json.loads(notice.read_text(encoding="utf-8"))
esc_pushed = any("escalate" in n["msg"] for n in notices)
check("V3-2.9 escalate 推送了", esc_pushed)

# timeout 推了
to_pushed = any("任务假死" in n["msg"] for n in notices)
check("V3-2.10 timeout 推送了", to_pushed)

# fresh 任务不应有 nudge
fresh_nudge = tq.NUDGES_DIR / f"{t_fresh['task_id']}.json"
check("V3-2.11 fresh 任务无 nudge", not fresh_nudge.exists())

# ==================== Test V3-3: 子 agent 必答契约 ====================
print("\n" + "=" * 60)
print("Test V3-3: 子 agent 必答契约（模拟）")
print("=" * 60)
reset_active()
t = tq.enqueue("agent contract test", agent_role="ops",
               timeout_sec=30, heartbeat_sec=2)

# watchdog 写 nudge
tq.write_nudge(t["task_id"], tq.NUDGE_KIND_NUDGE, gap_sec=3)

# 模拟子 agent 启动
nudges = tq.consume_nudges(t["task_id"])
check("V3-3.1 子 agent 看到 nudge", len(nudges) == 1)
check("V3-3.2 是 nudge 档", nudges[0]["kind"] == "nudge")

# 子 agent 必回 "RESPONDING_TO_NUDGE"
tq.heartbeat(t["task_id"], status="running",
             message="RESPONDING_TO_NUDGE: 正在跑第 2 步")
back = tq.get(t["task_id"])
check("V3-3.3 心跳含 RESPONDING 标记",
      "RESPONDING_TO_NUDGE" in back["progress"]["message"])

# ==================== Test V3-4: 升级档位（nudge → ping → escalate）====================
print("\n" + "=" * 60)
print("Test V3-4: 档位升级（nudge → ping → escalate）")
print("=" * 60)
reset_active()
t = tq.enqueue("level escalate", agent_role="ops",
               timeout_sec=30, heartbeat_sec=2)
tq.heartbeat(t["task_id"], status="running")

# 1) 写 nudge
tq.write_nudge(t["task_id"], tq.NUDGE_KIND_NUDGE, gap_sec=2)
nudge1 = tq.peek_nudge(t["task_id"])
check("V3-4.1 第一次写 nudge", nudge1["kind"] == "nudge")

# 2) 覆盖写 ping（升级）
tq.write_nudge(t["task_id"], tq.NUDGE_KIND_PING, gap_sec=4)
nudge2 = tq.peek_nudge(t["task_id"])
check("V3-4.2 覆盖为 ping", nudge2["kind"] == "ping")

# 3) 覆盖写 escalate（再升级）
tq.write_nudge(t["task_id"], tq.NUDGE_KIND_ESCALATE, gap_sec=7)
nudge3 = tq.peek_nudge(t["task_id"])
check("V3-4.3 覆盖为 escalate", nudge3["kind"] == "escalate")

# 4) 子 agent 只能消费到最新的
consumed = tq.consume_nudges(t["task_id"])
check("V3-4.4 只消费到最新一条", len(consumed) == 1
      and consumed[0]["kind"] == "escalate")

# ==================== Test V3-5: 边界 — 不会因为子 agent 短暂没回就升级 ====================
print("\n" + "=" * 60)
print("Test V3-5: 边界")
print("=" * 60)
reset_active()
t = tq.enqueue("boundary", agent_role="ops",
               timeout_sec=30, heartbeat_sec=5)
tq.heartbeat(t["task_id"], status="running")
# 1s gap（远小于 1×stale=5s）
backdate(t["task_id"], 1)
result = tq_wd.run_once()
check("V3-5.1 1s gap 不触发任何档",
      result["nudges"] == 0 and result["pings"] == 0
      and result["escalates"] == 0 and result["timeouts"] == 0,
      str(result))

# 4s gap（介于 0 和 1×stale=5s 之间）
backdate(t["task_id"], 4)
result = tq_wd.run_once()
check("V3-5.2 4s gap (1×stale=5) 不触发 nudge",
      result["nudges"] == 0, str(result))

# ==================== Test V3-6: 子 agent consume 多次不重复 ====================
print("\n" + "=" * 60)
print("Test V3-6: 幂等消费")
print("=" * 60)
reset_active()
t = tq.enqueue("idempotent", agent_role="ops",
               timeout_sec=30, heartbeat_sec=2)
tq.write_nudge(t["task_id"], tq.NUDGE_KIND_NUDGE)
c1 = tq.consume_nudges(t["task_id"])
c2 = tq.consume_nudges(t["task_id"])
c3 = tq.consume_nudges(t["task_id"])
check("V3-6.1 第一次拿到 1 条", len(c1) == 1)
check("V3-6.2 第二次拿到 0", len(c2) == 0)
check("V3-6.3 第三次拿到 0", len(c3) == 0)

# ==================== Test V3-7: status() 三档展示 ====================
print("\n" + "=" * 60)
print("Test V3-7: status() 输出含四档")
print("=" * 60)
reset_active()
t1 = tq.enqueue("status test 1", agent_role="ops",
                timeout_sec=30, heartbeat_sec=2)
tq.heartbeat(t1["task_id"], status="running")
backdate(t1["task_id"], 3)  # nudge

t2 = tq.enqueue("status test 2", agent_role="ops",
                timeout_sec=30, heartbeat_sec=2)
tq.heartbeat(t2["task_id"], status="running")
backdate(t2["task_id"], 5)  # ping

t3 = tq.enqueue("status test 3", agent_role="ops",
                timeout_sec=30, heartbeat_sec=2)
tq.heartbeat(t3["task_id"], status="running")
backdate(t3["task_id"], 7)  # escalate

import io
import contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    tq_wd.status()
output = buf.getvalue()
check("V3-7.1 status 输出 NUDGE", "NUDGE" in output)
check("V3-7.2 status 输出 PING", "PING" in output)
check("V3-7.3 status 输出 ESCALATE", "ESCALATE" in output)

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
    print("\n🎉 全部通过！task-queue v3 主动推进上线")
    print("""
    v3 新能力：
    ✓ 写 nudge / 消费 nudge / peek nudge / 清 nudge
    ✓ run_once 3 档推进：nudge / ping / escalate
    ✓ 升级覆盖（nudge → ping → escalate）
    ✓ 边界：1s gap 不触发，4s gap 不触发 nudge
    ✓ 子 agent 必答契约：RESPONDING_TO_NUDGE/PING/ESCALATE
    ✓ status() 输出 4 档颜色
    """)
