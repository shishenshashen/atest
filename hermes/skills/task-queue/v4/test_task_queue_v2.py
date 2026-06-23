"""
test_task_queue_v2.py - 端到端验证 v2 全链路
覆盖：
  1. 入队 + 启动心跳
  2. 进展心跳
  3. done + 真实产物（path+size+sha256-64） + verify_task
  4. finalize() 自动 verify
  5. 多任务并发（5 个同时假死）→ 批量 mark_timeout
  6. dispatch 失败必 raise（hermes CLI 不在）
  7. journal 去重（同一 task 写两次）
  8. mark_timeout 写 status="timeout"（不伪装 failed）
  9. role 默认 timeout/heartbeat
  10. 老数据迁移（再跑一遍幂等）
  11. pending_notices consume
"""
import sys
import time
import json
import hashlib
import importlib
from pathlib import Path

ROOT = Path.home() / ".hermes" / "skills" / "task-queue"
sys.path.insert(0, str(ROOT))

# 清掉之前可能 import 的模块缓存，确保测的是新代码
for mod in ["queue", "journal", "watchdog", "push", "dispatch", "review"]:
    if mod in sys.modules:
        del sys.modules[mod]

import tq_queue as tq
import journal as tq_journal
import dispatch as tq_dispatch
import push as tq_push
import review as tq_review
# 借用 journal 的内部函数
_entry_marker = tq_journal._entry_marker
_remove_existing_entry = tq_journal._remove_existing_entry

PASS = []
FAIL = []

def check(name, ok, detail=""):
    if ok:
        PASS.append(name)
        print(f"  ✓ {name}")
    else:
        FAIL.append((name, detail))
        print(f"  ✗ {name}  → {detail}")

# ---------- 清环境（不影响 archive） ----------
def reset_active():
    """清 active 队列，archive 留作历史。"""
    (Path.home() / ".hermes" / "task-queue" / "queue.json").write_text(
        "{}", encoding="utf-8")

# ==================== Test 1: 入队 + 启动心跳 ====================
print("\n" + "=" * 60)
print("Test 1: 入队 + 启动心跳 + 进展心跳")
print("=" * 60)
reset_active()
task = tq.enqueue("找出 ~/.hermes/skills 最大 3 个 .py", agent_role="ops")
check("1.1 enqueue 成功", task["task_id"].startswith("t-"))
check("1.2 role 默认 timeout", task["timeout_sec"] == 120, f"got {task['timeout_sec']}")
check("1.3 role 默认 heartbeat", task["heartbeat_sec"] == 30, f"got {task['heartbeat_sec']}")
check("1.4 初始 status=queued", task["status"] == "queued")

t = tq.heartbeat(task["task_id"], status="started", message="子 agent 已起")
check("1.5 启动心跳 status=started", t["status"] == "started")

for i in range(1, 4):
    t = tq.heartbeat(task["task_id"], progress_current=i, progress_total=3,
                     message=f"扫描第 {i} 批")
check("1.6 进展心跳 progress=3/3", t["progress"]["current"] == 3)

# ==================== Test 2: done + 真实产物 + verify ====================
print("\n" + "=" * 60)
print("Test 2: done + 真实产物 + verify_task")
print("=" * 60)
skill_dir = Path.home() / ".hermes" / "skills"
files = sorted(skill_dir.rglob("*.py"),
               key=lambda p: -p.stat().st_size)[:3]
artifacts = []
for f in files:
    size = f.stat().st_size
    h = hashlib.sha256(f.read_bytes()).hexdigest()  # 完整 64 位
    artifacts.append({"path": str(f), "size": size, "hash": h})

# 标 done
tq.mark_done(task["task_id"], result={"summary": "top3", "artifacts": artifacts})
t_done = tq.get(task["task_id"])
check("2.1 done 状态", t_done["status"] == "done")

# 标 done 后归档了，应从 active 移到 archive
active_ids = {t["task_id"] for t in tq.list_active()}
check("2.2 done 后移出 active", task["task_id"] not in active_ids)

# archive 里有
in_archive = False
af = Path.home() / ".hermes" / "task-queue" / "archive" / (time.strftime("%Y-%m-%d") + ".jsonl")
if af.exists():
    for line in af.read_text(encoding="utf-8").splitlines():
        if task["task_id"] in line:
            in_archive = True
            break
check("2.3 done 写入 archive", in_archive)

# verify_task
v = tq_dispatch.verify_task(task["task_id"])
check("2.4 verify_task 全部 ok", v["verified"] is True, str(v))

# ==================== Test 3: finalize 自动 verify ====================
print("\n" + "=" * 60)
print("Test 3: finalize() 自动调 verify_task()")
print("=" * 60)
# 先入队一个新 task，走完整 finalize
reset_active()
task2 = tq.enqueue("finalize 测试", agent_role="tester")
f1 = Path.home() / "tmp_finalize_test.txt"
f1.write_text("hello world 12345", encoding="utf-8")
h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
s1 = f1.stat().st_size
# 不先 mark_done，让 finalize 来 mark + verify
res = tq_dispatch.finalize(task2["task_id"],
                            summary="finalize 跑通",
                            artifacts=[{"path": str(f1), "size": s1, "hash": h1}])
check("3.1 finalize 返回 journal path", "journal" in res)
check("3.2 finalize 返回 verify", "verify" in res)
check("3.3 verify=True 且 verified", res["verify"] and res["verify"].get("verified") is True, str(res["verify"]))

# 看 task 的 result.verify 写进去了
t2_archived = None
for line in af.read_text(encoding="utf-8").splitlines()[-20:]:
    if task2["task_id"] in line:
        t2_archived = json.loads(line)
        break
check("3.4 archive 里 task.result.verify 写入了",
      t2_archived and t2_archived.get("result", {}).get("verify", {}).get("verified") is True)

# ==================== Test 4: 多任务并发假死 + 批量 mark ====================
print("\n" + "=" * 60)
print("Test 4: 5 个并发假死任务 → 批量 mark_timeout")
print("=" * 60)
reset_active()
stuck_ids = []
for i in range(5):
    t = tq.enqueue(f"并发假死 #{i}", agent_role="stresstest",
                   timeout_sec=2, heartbeat_sec=1)
    stuck_ids.append(t["task_id"])

time.sleep(4)  # 全部超时

# 跑 watchdog 单次
result = tq_dispatch.__dict__  # 用 tq_dispatch 不好调 watchdog 的 private
# 直接调 queue 层
stale = tq.find_stale()
check("4.1 find_stale 找 5 个", len(stale) == 5, f"got {len(stale)}")

archived = tq.mark_timeouts_batch(stuck_ids)
check("4.2 batch mark 5 个", len(archived) == 5)

# 看 status 真写 timeout
for tid in stuck_ids:
    t = tq.get(tid)
    assert t["status"] == "timeout", f"{tid} status={t['status']}"
check("4.3 5 个都是真 timeout 状态", True)

# 看 active 移走了
remaining = tq.list_active()
check("4.4 active 已清空", len(remaining) == 0)

# ==================== Test 5: dispatch 失败必 raise ====================
print("\n" + "=" * 60)
print("Test 5: hermes CLI 缺失时 dispatch 必 raise")
print("=" * 60)
reset_active()

# monkeypatch 模拟 hermes 不在
real_which = tq_dispatch._hermes_cli_exists
tq_dispatch._hermes_cli_exists = lambda: False
try:
    try:
        tq_dispatch.dispatch("测试派发", agent_role="ops",
                             require_dispatch=True)
        check("5.1 hermes 不在时必 raise DispatchError", False, "没 raise")
    except tq_dispatch.DispatchError as e:
        check("5.1 hermes 不在时必 raise DispatchError", True, str(e)[:80])
finally:
    tq_dispatch._hermes_cli_exists = real_which

# 看任务被 mark_failed
found = None
for line in af.read_text(encoding="utf-8").splitlines()[-20:]:
    try:
        t = json.loads(line)
        if "测试派发" in t.get("goal", ""):
            found = t
            break
    except Exception:
        pass
check("5.2 失败任务被 mark_failed", found is not None)
check("5.3 失败 reason=dispatch_no_hermes_cli",
      found and found.get("error", {}).get("reason") == "dispatch_no_hermes_cli")

# pending_notices 也应有 error
notices_file = Path.home() / ".hermes" / "task-queue" / "pending_notices.json"
notices = json.loads(notices_file.read_text(encoding="utf-8"))
has_dispatch_err = any("hermes CLI 不在 PATH" in n["msg"] for n in notices)
check("5.4 推送了 dispatch 失败告警", has_dispatch_err)

# ==================== Test 6: journal 去重 ====================
print("\n" + "=" * 60)
print("Test 6: journal 同一 task 写两次 → 不重复")
print("=" * 60)
reset_active()
task6 = tq.enqueue("journal 去重测试", agent_role="general")
tq.mark_done(task6["task_id"], result={"artifacts": []})

# 写两次
tq_journal.write_journal(task6["task_id"], summary="第一次")
md = tq_journal.write_journal(task6["task_id"], summary="第二次（覆盖）")

content = md.read_text(encoding="utf-8")
# 找 task6 自己的 entry 段（前后 --- 分隔）
import re
task6_marker = _entry_marker(task6["task_id"])
pattern = re.compile(rf"## \[[^\]]+\] [A-Z]+ · {re.escape(task6_marker)}.*?(?=\n---)", re.DOTALL)
m = pattern.search(content)
own_entry = m.group(0) if m else ""
count_first = own_entry.count("第一次")
count_second = own_entry.count("第二次")
check("6.1 旧 entry 已删", count_first == 0, f"count={count_first}")
check("6.2 新 entry 写入", count_second == 1, f"count={count_second}")
check("6.3 该 task_id 在 journal 只出现 1 次",
      content.count(task6["task_id"]) == 1, f"count={content.count(task6['task_id'])}")

# ==================== Test 7: role 默认值表 ====================
print("\n" + "=" * 60)
print("Test 7: role → 默认 timeout/heartbeat 表")
print("=" * 60)
expected = {
    "ops":        (120, 30),
    "tester":     (600, 60),
    "general":    (600, 60),
    "researcher": (1800, 120),
    "coder":      (3600, 120),
}
# v2 老测试：L 角色必填 4 问（Phase 2 改的），这里只测 timeout/heartbeat 默认值
# 所以给 L 角色传 4 问字段占位
L_FILL = {"files": ["x.py"], "verify_plan": ["pytest"], "deliverable": "x.py"}
for role, (et, eh) in expected.items():
    kw = dict(L_FILL) if role in ("researcher", "coder") else {}
    t = tq.enqueue(f"role test {role}", agent_role=role, **kw)
    check(f"7.x role={role} timeout={et}", t["timeout_sec"] == et,
          f"got {t['timeout_sec']}")
    check(f"7.x role={role} heartbeat={eh}", t["heartbeat_sec"] == eh,
          f"got {t['heartbeat_sec']}")

# 显式传覆盖默认
t_override = tq.enqueue("override", agent_role="ops", timeout_sec=10, heartbeat_sec=2)
check("7.y 显式 timeout 覆盖默认", t_override["timeout_sec"] == 10)
check("7.y 显式 heartbeat 覆盖默认", t_override["heartbeat_sec"] == 2)

# ==================== Test 8: 迁移幂等 ====================
print("\n" + "=" * 60)
print("Test 8: migrate_from_legacy 幂等")
print("=" * 60)
m1 = tq.migrate_from_legacy()
check("8.1 第二次跑迁移跳过", m1.get("skipped") in ("empty", "already new format", "no legacy file"),
      str(m1))

# ==================== Test 9: consume_pending ====================
print("\n" + "=" * 60)
print("Test 9: consume_pending 主动消费")
print("=" * 60)
# 先 push 一条
tq_push.push("测试 consume 用的通知", level="info")
consumed = tq_push.consume_pending()
check("9.1 消费到 1 条", len(consumed) >= 1, f"got {len(consumed)}")
# 消费后文件清空
notices_after = json.loads(notices_file.read_text(encoding="utf-8"))
check("9.2 消费后 notice 文件清空", len(notices_after) == 0, f"got {len(notices_after)}")

# ==================== Test 10: watchdog 完整跑通 ====================
print("\n" + "=" * 60)
print("Test 10: watchdog run_once 端到端")
print("=" * 60)
reset_active()
# 入队一个超时任务
fake_task = tq.enqueue("watchdog e2e", agent_role="watchdogtest",
                       timeout_sec=3, heartbeat_sec=1)
time.sleep(4)

# 调 watchdog.run_once（不依赖子进程，验证核心逻辑）
import watchdog as tq_wd
res = tq_wd.run_once()
# v3 改名了：stale_count → timeouts
check("10.1 run_once 找到 1 个 stale",
      res.get("timeouts", res.get("stale_count", 0)) == 1, str(res))
check("10.2 pushed=1",
      res.get("timeout_pushed", res.get("pushed", 0)) == 1, str(res))
# 看推送
notices = json.loads(notices_file.read_text(encoding="utf-8"))
has_watchdog = any("任务假死" in n["msg"] and "watchdogtest" in n["msg"]
                   for n in notices)
check("10.3 推送了假死告警", has_watchdog)

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
    print("\n🎉 全部通过！task-queue v2 上线")
    print("""
    新能力清单：
    ✓ 队列分文件（active dict + archive jsonl）无限增长不爆
    ✓ 单一 mutate(fn) 重入安全
    ✓ 批量 mark_timeout（一次锁）
    ✓ watchdog start 启动后真验证
    ✓ dispatch 派发失败必 raise + 推送
    ✓ journal 写前查重覆盖
    ✓ role 默认 timeout/heartbeat
    ✓ mark_timeout 写真 status=timeout
    ✓ finalize 自动 verify_task
    ✓ pending_notices 主动消费
    """)
