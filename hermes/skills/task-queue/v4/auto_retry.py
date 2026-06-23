"""
task-queue/auto_retry.py  v1 (2026-06-15)
- 决策树：escalate 触发后先自救，再推老大
- 复用 tq_queue.requeue_from_archive

决策顺序（按 retry_count）：
  retry_count=0 → rewrite_prompt （在 goal 后追加 "⚠️ 之前已超时，请聚焦核心交付"）
  retry_count=1 → extend_timeout （timeout × 2）
  retry_count=2 → downgrade_role （按 ROLE_DOWNGRADE 表降一档）
  retry_count≥3 → 不再重试，返回 False（推老大）

返回：
  {
    "retried": True/False,
    "strategy": "rewrite_prompt"|...|None,
    "task_id": "...",
    "retry_count_new": int,
    "reason": "...",
    "skipped_reason": str (若 skipped)
  }
"""
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
import tq_queue as tq  # noqa: E402


# Role 降级表（重 → 轻）
ROLE_DOWNGRADE = {
    "researcher": "general",
    "coder":      "general",
    "general":    "ops",
    "tester":     "ops",
    "ops":        "ops",   # 兜底，不变
}


# 改写 prompt 的附加语（v1：固定话术；v2：可调 LLM 重写）
PROMPT_RETRY_SUFFIX = (
    "\n\n---\n"
    "⚠️ [auto_retry] 这是你第 {retry_count} 次重试。"
    "之前已超时/失败，请：\n"
    "1. 更聚焦于核心交付，别在边缘优化上耗时间\n"
    "2. 跳过非必要步骤（如文档/测试如果不影响核心功能）\n"
    "3. 完成后立即调 finalize()，别等剩余步骤\n"
)


def _build_rewrite_goal(original_goal: str, retry_count: int) -> str:
    """简单追加重试提示。v2 可换成 LLM 重写。"""
    suffix = PROMPT_RETRY_SUFFIX.format(retry_count=retry_count + 1)
    return original_goal + suffix


def attempt(task_id: str, original_goal: Optional[str] = None,
            reason: str = "auto_retry") -> dict:
    """
    决策树入口。
    - task_id: 要重试的任务（必须在 archive，status=timeout/failed）
    - original_goal: 可选，rewrite_prompt 时若 archive 里 goal 缺失/被截断可传
    - reason: 为什么触发重试（escalate/timeout/manual）

    cortex.get_retry_strategy_hint() 可影响决策：
      - "default": 标准 3 步（rewrite_prompt → extend_timeout → downgrade_role）
      - "skip_rewrite": 跳过 rewrite_prompt，第 1 次直接 extend_timeout

    返回 dict，retried=False 时 watchdog 应推老大。
    """
    # 0) 读 cortex 策略 hint
    hint = "default"
    try:
        import cortex as tq_cortex
        hint = tq_cortex.get_retry_strategy_hint(
            # 从 task 拿 role（下面会读 task，这里先 None）
            "general"
        )
    except Exception:
        pass

    # 1) 从 archive 拿当前 task（不动状态，只读）
    task = tq.get(task_id)
    if not task:
        return {
            "retried": False,
            "strategy": None,
            "task_id": task_id,
            "retry_count_new": 0,
            "reason": reason,
            "skipped_reason": "task not found in active or archive",
        }

    # 拿到真实 role 后再读 hint（覆盖）
    if task.get("agent_role"):
        try:
            hint = tq_cortex.get_retry_strategy_hint(task["agent_role"])
        except Exception:
            pass

    if task.get("status") not in {tq.STATUS_TIMEOUT, tq.STATUS_FAILED}:
        return {
            "retried": False,
            "strategy": None,
            "task_id": task_id,
            "retry_count_new": task.get("retry_count", 0),
            "reason": reason,
            "skipped_reason": f"task status={task.get('status')} 非终态，不需重试",
        }

    retry_count = task.get("retry_count", 0)
    level = task.get("level", tq.LEVEL_M)
    max_retries = tq.LEVEL_PROFILE.get(level, tq.LEVEL_PROFILE[tq.LEVEL_M])["max_retries"]

    # CRITICAL 永不自动重试
    if level == tq.LEVEL_CRITICAL:
        return {
            "retried": False,
            "strategy": None,
            "task_id": task_id,
            "retry_count_new": retry_count,
            "reason": reason,
            "skipped_reason": "CRITICAL 任务不自动重试（必人工拍板）",
        }

    if retry_count >= max_retries:
        return {
            "retried": False,
            "strategy": None,
            "task_id": task_id,
            "retry_count_new": retry_count,
            "reason": reason,
            "skipped_reason": f"已达 max_retries={max_retries} (level={level})",
        }

    # 决策树（受 cortex hint 影响）
    # hint == "skip_rewrite"：把 rewrite_prompt 这步跳过，让 retry_count==0 直接走 extend
    if hint == "skip_rewrite":
        # 把 retry_count 偏移 +1，跳到第二步
        effective_retry = retry_count + 1
    else:
        effective_retry = retry_count

    if effective_retry == 0:
        # 第一次：改 prompt
        goal_src = original_goal or task.get("goal", "")
        new_goal = _build_rewrite_goal(goal_src, retry_count)
        try:
            new_task = tq.requeue_from_archive(
                task_id,
                strategy=tq.RETRY_STRATEGY_PROMPT,
                new_goal=new_goal,
                reason=f"{reason}|retry#1=rewrite_prompt",
            )
            return {
                "retried": True,
                "strategy": "rewrite_prompt",
                "task_id": task_id,
                "retry_count_new": new_task["retry_count"],
                "reason": reason,
            }
        except Exception as e:
            return {
                "retried": False,
                "strategy": "rewrite_prompt",
                "task_id": task_id,
                "retry_count_new": retry_count,
                "reason": reason,
                "skipped_reason": f"requeue_from_archive failed: {e}",
            }

    elif effective_retry == 1:
        # 第二次：拉 timeout
        try:
            new_task = tq.requeue_from_archive(
                task_id,
                strategy=tq.RETRY_STRATEGY_TIMEOUT,
                reason=f"{reason}|retry#2=extend_timeout",
            )
            return {
                "retried": True,
                "strategy": "extend_timeout",
                "task_id": task_id,
                "retry_count_new": new_task["retry_count"],
                "reason": reason,
            }
        except Exception as e:
            return {
                "retried": False,
                "strategy": "extend_timeout",
                "task_id": task_id,
                "retry_count_new": retry_count,
                "reason": reason,
                "skipped_reason": f"requeue_from_archive failed: {e}",
            }

    elif effective_retry == 2:
        # 第三次：降级 role
        old_role = task.get("agent_role", "general")
        new_role = ROLE_DOWNGRADE.get(old_role, "ops")
        if new_role == old_role:
            # 已经最低档，不再降级，让老大拍板
            return {
                "retried": False,
                "strategy": None,
                "task_id": task_id,
                "retry_count_new": retry_count,
                "reason": reason,
                "skipped_reason": f"role={old_role} 已最低档，无可降级",
            }
        try:
            new_task = tq.requeue_from_archive(
                task_id,
                strategy=tq.RETRY_STRATEGY_DOWNGRADE,
                new_agent_role=new_role,
                reason=f"{reason}|retry#3=downgrade {old_role}→{new_role}",
            )
            return {
                "retried": True,
                "strategy": "downgrade_role",
                "task_id": task_id,
                "retry_count_new": new_task["retry_count"],
                "reason": reason,
            }
        except Exception as e:
            return {
                "retried": False,
                "strategy": "downgrade_role",
                "task_id": task_id,
                "retry_count_new": retry_count,
                "reason": reason,
                "skipped_reason": f"requeue_from_archive failed: {e}",
            }

    else:
        # 第 4+ 次：不重试
        return {
            "retried": False,
            "strategy": None,
            "task_id": task_id,
            "retry_count_new": retry_count,
            "reason": reason,
            "skipped_reason": f"retry_count={retry_count} 超出决策树（>=3），推老大",
        }


if __name__ == "__main__":
    # 简单冒烟
    import json
    print("auto_retry v1 — 决策树:")
    print("  retry 0 → rewrite_prompt")
    print("  retry 1 → extend_timeout (×2)")
    print("  retry 2 → downgrade_role")
    print("  retry 3+ → False（推老大）")
    print()
    print("用法:")
    print("  from auto_retry import attempt")
    print("  result = attempt(task_id, reason='watchdog_escalate')")
    print("  if not result['retried']:")
    print("      push_to_boss(result['skipped_reason'])")