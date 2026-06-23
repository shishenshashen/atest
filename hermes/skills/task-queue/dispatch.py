"""
task-queue/dispatch.py  v2 (2026-06-11)
- P1-5: hermes CLI 找不到 / 派发失败必 raise 或 push，不再静默吞
- P2-9: finalize() 自动调 verify_task()，把已写代码接上
- 用 push.py 统一推送
"""
import sys
import os
import time
import json
import shutil
import hashlib
import subprocess
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
import tq_queue as tq  # noqa: E402
import journal as tq_journal  # noqa: E402
import push as tq_push  # noqa: E402

TEMPLATES = Path(__file__).parent / "templates"


def render_goal(task: dict) -> str:
    tpl = (TEMPLATES / "agent_goal.md").read_text(encoding="utf-8")
    files = task.get("files") or []
    verify_plan = task.get("verify_plan") or []
    deliverable = task.get("deliverable") or ""
    level = task.get("level") or "M"
    # 渲染 list 字段：每行一个
    files_str = "\n".join(f"- {f}" for f in files) if files else "(无)"
    verify_str = "\n".join(f"- {v}" for v in verify_plan) if verify_plan else "(无)"
    if not deliverable.strip():
        deliverable = "(无 — S/M 任务未填)"
    return (
        tpl
        .replace("{{TASK_ID}}", task["task_id"])
        .replace("{{GOAL}}", task["goal"])
        .replace("{{CONTEXT}}", json.dumps(task.get("context", {}),
                                            ensure_ascii=False, indent=2))
        .replace("{{HEARTBEAT_SEC}}", str(task["heartbeat_sec"]))
        .replace("{{ETA_SECONDS}}", str(task["timeout_sec"]))
        .replace("{{LEVEL}}", level)
        .replace("{{FILES}}", files_str)
        .replace("{{VERIFY_PLAN}}", verify_str)
        .replace("{{DELIVERABLE}}", deliverable)
    )


class DispatchError(Exception):
    """派发失败。父级必 catch。"""


def _hermes_cli_exists() -> bool:
    return shutil.which("hermes") is not None


def dispatch(goal: str, agent_role: str = "general",
             timeout_sec: int = None, heartbeat_sec: int = None,
             context: dict = None, parent: str = None,
             sync: bool = False,
             require_dispatch: bool = True) -> dict:
    """
    派发一个子任务。
    - 入队（按 role 自动用默认 timeout/heartbeat）
    - 渲染 goal
    - 调 hermes delegate CLI
    - 返回 task

    require_dispatch=True (默认): 派发失败必 raise DispatchError，
       父级必须 catch 或自己 abort，不能假装派了。
    require_dispatch=False: 入队但不真派发（用于父级自己执行的场景），
       会 push 一条 warn 提醒老大。
    """
    task = tq.enqueue(
        goal=goal, agent_role=agent_role,
        timeout_sec=timeout_sec, heartbeat_sec=heartbeat_sec,
        context=context, parent=parent,
    )

    if not require_dispatch:
        tq_push.push(
            f"⚠️ 入队但未真派发: {task['task_id']}\n"
            f"原因: require_dispatch=False\n"
            f"目标: {goal[:100]}",
            level="warn",
        )
        return task

    # 渲染 goal
    rendered_goal = render_goal(task)

    # P1-5: 验证 hermes CLI 在 PATH
    if not _hermes_cli_exists():
        # 立即标 failed + push 告警
        tq.mark_failed(
            task["task_id"],
            error="hermes CLI not in PATH; cannot dispatch",
            reason="dispatch_no_hermes_cli",
        )
        tq_push.push(
            f"❌ 派发失败: {task['task_id']}\n"
            f"原因: hermes CLI 不在 PATH\n"
            f"目标: {goal[:100]}\n"
            f"修法: 把 hermes 加到 PATH，或设 HERMES_BIN 环境变量",
            level="error",
        )
        raise DispatchError(
            f"hermes CLI not in PATH; task {task['task_id']} marked failed"
        )

    # 调 hermes delegate
    cmd = [
        "hermes", "delegate", "run",
        "--goal", rendered_goal,
        "--task-id", task["task_id"],
        "--heartbeat", str(task["heartbeat_sec"]),
    ]

    try:
        if sync:
            result = subprocess.run(
                cmd, capture_output=True,
                encoding="gbk", errors="ignore",
                timeout=task["timeout_sec"] + 30,
            )
            if result.returncode != 0:
                tq.mark_failed(
                    task["task_id"],
                    error=f"hermes delegate exit {result.returncode}: "
                          f"{result.stderr[:500]}",
                    reason="dispatch_nonzero_exit",
                )
                tq_push.push(
                    f"❌ 派发失败: {task['task_id']}\n"
                    f"hermes delegate 退出码 {result.returncode}\n"
                    f"stderr: {result.stderr[:300]}",
                    level="error",
                )
                raise DispatchError(
                    f"hermes delegate exit {result.returncode}"
                )
            tq.mark_done(task["task_id"],
                         result={"raw": result.stdout[-2000:]})
        else:
            subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
    except FileNotFoundError as e:
        # 罕见：which 找到 hermes 但 Popen 找不到（PATH 竞争）
        tq.mark_failed(task["task_id"],
                       error=f"FileNotFoundError: {e}",
                       reason="dispatch_popen_fail")
        tq_push.push(
            f"❌ 派发失败: {task['task_id']}\n"
            f"Popen FileNotFoundError: {e}",
            level="error",
        )
        raise DispatchError(f"Popen fail: {e}")
    except Exception as e:
        tq.mark_failed(task["task_id"],
                       error=f"dispatch exception: {e}",
                       reason="dispatch_exception")
        tq_push.push(
            f"❌ 派发异常: {task['task_id']}\n{type(e).__name__}: {e}",
            level="error",
        )
        raise DispatchError(f"{type(e).__name__}: {e}")

    return task


def verify_task(task_id: str) -> dict:
    """
    验证 task 产物真实性。
    P2-9: finalize() 现在会自动调这个。
    """
    task = tq.get(task_id)
    if not task:
        return {"verified": False, "error": "task not found"}
    if task["status"] != tq.STATUS_DONE:
        return {"verified": False, "error": f"task not done: {task['status']}"}

    result = task.get("result") or {}
    artifacts = result.get("artifacts", [])
    if not artifacts:
        return {"verified": True, "artifacts": [],
                "warning": "task done but no artifacts declared"}

    verified = []
    for a in artifacts:
        p = Path(a.get("path", ""))
        if not p.exists():
            verified.append({"path": str(p), "ok": False,
                             "reason": "file not found"})
            continue
        actual_size = p.stat().st_size
        declared_size = a.get("size", -1)
        size_ok = actual_size == declared_size

        hash_ok = True
        actual_hash = ""
        declared_hash = a.get("hash", "")
        if declared_hash:
            # 模板说子 agent 给 full sha64，父级会截前 8
            # verify 也用前 8 比对
            if len(declared_hash) >= 8:
                actual_hash = hashlib.sha256(p.read_bytes()).hexdigest()[:8]
                hash_ok = actual_hash == declared_hash[:8]
            else:
                hash_ok = False

        verified.append({
            "path": str(p),
            "ok": size_ok and hash_ok,
            "declared_size": declared_size,
            "actual_size": actual_size,
            "declared_hash_prefix": declared_hash[:8],
            "actual_hash_prefix": actual_hash,
        })

    all_ok = all(v["ok"] for v in verified)
    return {"verified": all_ok, "artifacts": verified}


def finalize(task_id: str, summary: str = "", error: str = None,
             artifacts: list = None,
             verify: bool = True,
             push_summary: bool = True) -> dict:
    """
    收尾：写 journal + 验证产物 + 归档 + 推总结。
    P2-9: verify=True 时自动调 verify_task()，结果写进 result.verify。
    Phase 3: push_summary=True 且 done 后自动 push_done_summary。
    父级在收到子 agent 的 done/failed 后必调。
    """
    task = tq.get(task_id)
    if not task:
        raise KeyError(task_id)

    verify_result = None
    # 先看任务状态（在 active 还是在 archive）
    in_active = task_id in {t["task_id"] for t in tq.list_active()}

    # error 分支
    if error and task["status"] == tq.STATUS_FAILED:
        pass  # 已经是 failed，不重复 mark
    elif error and task["status"] == tq.STATUS_TIMEOUT:
        pass  # 已经是 timeout，不重复 mark（最终态）
    elif error:
        tq.mark_failed(task_id, error)
    elif in_active:
        # 还在 active：标 done，会自动归档
        result = task.get("result") or {}
        if artifacts:
            result["artifacts"] = artifacts
        tq.mark_done(task_id, result)
        # 归档后从 archive 拿回来做 verify
        if verify:
            verify_result = verify_task(task_id)
            # 写 verify 进 archive 那一行
            _append_verify_to_archive(task_id, verify_result)
    elif task["status"] == tq.STATUS_DONE:
        # 已经在 archive 里的 done
        if verify:
            verify_result = verify_task(task_id)
            _append_verify_to_archive(task_id, verify_result)

    md = tq_journal.write_journal(task_id, summary=summary,
                                  artifacts=artifacts, error=error)

    # Phase 3: 自动推 done 总结（仅 done 状态，failed/timeout 不推）
    push_result = None
    if push_summary and not error:
        final_task = tq.get(task_id)  # 重读拿最新 verify
        if final_task and final_task.get("status") == tq.STATUS_DONE:
            try:
                import push as tq_push
                push_result = tq_push.push_done_summary(
                    final_task, journal_path=str(md),
                    verify_result=verify_result)
            except Exception as e:
                push_result = {"error": f"push_done_summary fail: {e}"}

    return {
        "journal": str(md),
        "verify": verify_result,
        "push": push_result,
    }


def ship(task_id: str, summary: str = "", error: str = None,
         artifacts: list = None, verify: bool = True) -> dict:
    """
    Phase 3 ship 闭环：1 行走完 verify + journal + 推总结。
    = finalize() 的语义糖。
    - done → 推 info 级别总结
    - failed/timeout → 不调 finalize 内置 push（已知 finalize 不推失败）
                   → 但 ship 自己查 status，若 failed 推一条 warn 级别

    返回: {journal, verify, push, status}
    """
    res = finalize(task_id, summary=summary, error=error,
                   artifacts=artifacts, verify=verify,
                   push_summary=True)
    final = tq.get(task_id)
    status = final.get("status") if final else "?"
    res["status"] = status

    # failed 也推一条（warn）
    if status in (tq.STATUS_FAILED, tq.STATUS_TIMEOUT):
        try:
            import push as tq_push
            res["push_fail"] = tq_push.push(
                f"❌ 任务终态 [{status}] {task_id}\n"
                f"角色: {final.get('agent_role','?')} 等级: {final.get('level','?')}\n"
                f"目标: {final.get('goal','')[:80]}\n"
                f"错误: {error or final.get('error',{}).get('msg','?')}",
                level="warn",
            )
        except Exception as e:
            res["push_fail"] = {"error": str(e)}

    return res


def _write_verify(task_id: str, verify_result: dict):
    """mutate 用的内部函数：把 verify 结果写进 task.result.verify。"""
    def _fn(tasks):
        if task_id not in tasks:
            return
        t = tasks[task_id]
        r = t.get("result") or {}
        r["verify"] = verify_result
        t["result"] = r
        t["updated_at"] = int(time.time())
    return _fn


def _append_verify_to_archive(task_id: str, verify_result: dict):
    """
    把 verify 结果追加到 archive/{date}.jsonl 的对应 task 行。
    archive 是 jsonl 追加模式，没法改行——所以重写当日文件。
    简单粗暴但够用（每日文件最多几万行）。
    """
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    af = tq.ARCHIVE_DIR / f"{date_str}.jsonl"
    if not af.exists():
        return
    lines = af.read_text(encoding="utf-8").splitlines()
    new_lines = []
    found = False
    for line in lines:
        if not line.strip():
            new_lines.append(line)
            continue
        try:
            t = json.loads(line)
            if t.get("task_id") == task_id:
                r = t.get("result") or {}
                r["verify"] = verify_result
                t["result"] = r
                t["updated_at"] = int(time.time())
                line = json.dumps(t, ensure_ascii=False)
                found = True
            new_lines.append(line)
        except Exception:
            new_lines.append(line)
    if found:
        af.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        try:
            t = dispatch("示例任务：找出 C:/ai 目录最大的 5 个文件",
                         agent_role="ops", timeout_sec=120, heartbeat_sec=30,
                         require_dispatch=False)
            print(json.dumps(t, ensure_ascii=False, indent=2))
        except DispatchError as e:
            print(f"DISPATCH FAIL: {e}")
    else:
        print(__doc__)
