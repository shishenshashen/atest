"""
task-queue/queue.py  v2 (2026-06-11)
任务队列：active 索引 + 按天 archive 归档。
- 活跃任务放 queue.json（O(1) 扫/查/写）
- 终态任务按 created_at 日期归档到 archive/{date}.jsonl
- 所有 mutation 走单一 mutate(fn) 函数，重入安全
- 按 agent_role 给默认 timeout/heartbeat
- mark_timeout 写 status="timeout"（不再伪装 failed）
"""
import json
import gzip
import os
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime

# 跨平台文件锁
if sys.platform == "win32":
    import msvcrt
    class _Lock:
        def __init__(self, path: Path):
            self.path = path
            self._fd = None
        def __enter__(self):
            self._fd = open(self.path, "a+")
            while True:
                try:
                    msvcrt.locking(self._fd.fileno(), msvcrt.LK_LOCK, 1)
                    return self
                except OSError:
                    time.sleep(0.05)
        def __exit__(self, *a):
            try:
                self._fd.seek(0)
                msvcrt.locking(self._fd.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                # Windows 锁释放失败是 OS 级问题（句柄已被别的进程关掉等）
                # 不能 swallow raise，否则下次同进程可能死锁
                raise
            except Exception:
                # 编码/IO 等非锁问题 — 锁状态我们管不了，但不应让锁死
                # 至少打 log（由调用方在更外层 _log）
                pass
            self._fd.close()
else:
    import fcntl
    class _Lock:
        def __init__(self, path: Path):
            self.path = path
            self._fd = None
        def __enter__(self):
            self._fd = open(self.path, "w")
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX)
            return self
        def __exit__(self, *a):
            try:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            except OSError:
                raise
            except Exception:
                pass
            self._fd.close()

# ---------- 路径 ----------
QUEUE_DIR = Path.home() / ".hermes" / "task-queue"
QUEUE_FILE = QUEUE_DIR / "queue.json"           # active 索引（dict: task_id -> task）
LOCK_FILE = QUEUE_DIR / "queue.lock"
ARCHIVE_DIR = QUEUE_DIR / "archive"             # 按天 jsonl
NUDGES_DIR = QUEUE_DIR / "nudges"               # watchdog → 子 agent 通信（v3）
CORTEX_FILE = QUEUE_DIR / "cortex.json"         # Cortex-lite 自调参（v3）
LOG_DIR = QUEUE_DIR / "logs"

# ---------- 状态常量 ----------
STATUS_QUEUED = "queued"
STATUS_STARTED = "started"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
STATUS_TIMEOUT = "timeout"
STATUS_CANCELLED = "cancelled"

TERMINAL_STATUSES = {STATUS_DONE, STATUS_FAILED, STATUS_TIMEOUT, STATUS_CANCELLED}
ALL_STATUSES = {STATUS_QUEUED, STATUS_STARTED, STATUS_RUNNING, *TERMINAL_STATUSES}

# ---------- 任务等级 (S/M/L/CRITICAL) ----------
LEVEL_S = "S"             # typo/注释/小文档，0 仪式
LEVEL_M = "M"             # 脚本/小功能/普通 bug
LEVEL_L = "L"             # 跨模块/架构/模板
LEVEL_CRITICAL = "CRITICAL"  # 数据/权限/安全/生产/破坏性

ALL_LEVELS = {LEVEL_S, LEVEL_M, LEVEL_L, LEVEL_CRITICAL}
LEVEL_DEFAULT = LEVEL_M  # 不传时默认 M

# Level → 治理强度表
LEVEL_PROFILE = {
    LEVEL_S:         {"min_4q": False, "max_retries": 5, "label": "S (轻量)"},
    LEVEL_M:         {"min_4q": False, "max_retries": 3, "label": "M (标准)"},
    LEVEL_L:         {"min_4q": True,  "max_retries": 2, "label": "L (重)"},
    LEVEL_CRITICAL:  {"min_4q": True,  "max_retries": 0, "label": "CRITICAL (人工)"},
}

# ---------- role 默认值（不传 timeout/heartbeat/level 时用）----------
# 每个 role: (timeout_sec, heartbeat_sec, default_level)
ROLE_DEFAULTS = {
    "ops":         (120,   30,   LEVEL_S),
    "tester":      (600,   60,   LEVEL_M),
    "general":     (600,   60,   LEVEL_M),
    "researcher":  (1800,  120,  LEVEL_L),
    "coder":       (3600,  120,  LEVEL_L),
}

# ---------- 内部工具 ----------
def _ensure_dirs():
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    NUDGES_DIR.mkdir(parents=True, exist_ok=True)
    if not QUEUE_FILE.exists():
        QUEUE_FILE.write_text("{}", encoding="utf-8")
    if not CORTEX_FILE.exists():
        CORTEX_FILE.write_text("{}", encoding="utf-8")


def _log(msg: str):
    _ensure_dirs()
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    ts = datetime.now().strftime("%H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def _date_str(ts: int = None) -> str:
    return datetime.fromtimestamp(ts or time.time()).strftime("%Y-%m-%d")


# ---------- 重入安全的统一 mutation ----------
def mutate(fn):
    """
    单一 mutation 入口。所有改任务数据的函数都走这里。
    1. 加锁
    2. 读 active dict
    3. 调 fn(tasks) 让调用方在锁内做读+改（一次性）
    4. 自动归档所有终态任务（status in TERMINAL_STATUSES）
    5. 写回 active
    6. 释放锁

    fn 签名: fn(tasks: dict) -> None
    fn 可以修改 tasks 里的字段；mutate 会自动找出新增的终态任务归档。
    """
    _ensure_dirs()
    with _Lock(LOCK_FILE):
        if not QUEUE_FILE.exists():
            tasks = {}
        else:
            try:
                tasks = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
            except Exception:
                tasks = {}
        # 调用户函数
        fn(tasks)
        # 自动归档：遍历找出 status 终态的
        to_archive = [tid for tid, t in tasks.items()
                      if t.get("status") in TERMINAL_STATUSES]
        archived = 0
        for tid in to_archive:
            _archive_task(tasks.pop(tid))
            archived += 1
        # 写回 active
        tmp = QUEUE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(tasks, ensure_ascii=False, indent=2,
                                  sort_keys=True),
                       encoding="utf-8")
        os.replace(tmp, QUEUE_FILE)
    return tasks, archived


def _archive_task(task: dict):
    """写一行到 archive/{date}.jsonl。"""
    date_str = _date_str(task.get("created_at"))
    f = ARCHIVE_DIR / f"{date_str}.jsonl"
    with open(f, "a", encoding="utf-8") as out:
        out.write(json.dumps(task, ensure_ascii=False) + "\n")


def _gen_task_id() -> str:
    return f"t-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


def _new_task(goal, agent_role, timeout_sec, heartbeat_sec, context, parent):
    now = int(time.time())
    return {
        "task_id": _gen_task_id(),
        "parent": parent,
        "agent_role": agent_role,
        "goal": goal,
        "context": context or {},
        "status": STATUS_QUEUED,
        "created_at": now,
        "updated_at": now,
        "last_heartbeat": now,
        "heartbeat_sec": heartbeat_sec,
        "timeout_sec": timeout_sec,
        "progress": {"current": 0, "total": 0, "message": ""},
        "retry_count": 0,
        "max_retries": 3,
        "result": None,
        "error": None,
    }


# ---------- 公共 API ----------
def enqueue(goal: str, agent_role: str = "general",
            timeout_sec: int = None, heartbeat_sec: int = None,
            level: str = None,
            files: list = None,
            verify_plan: list = None,
            deliverable: str = None,
            context: dict = None, parent: str = None) -> dict:
    """
    入队一个任务。
    - timeout/heartbeat/level 不传时按 role 默认。
    - L/CRITICAL 必填 4 问（files/verify_plan/deliverable）。
    - CRITICAL 额外要求 4 问**详细**（verify_plan ≥ 1 条具体命令，deliverable 非空）。
    """
    # 1) 解 role 默认
    def_t, def_h, def_level = ROLE_DEFAULTS.get(agent_role, ROLE_DEFAULTS["general"])
    if level is None: level = def_level

    # 2) Cortex-lite：读 cortex 调过的 timeout（仅当用户没显式传时）
    if timeout_sec is None:
        try:
            import cortex as tq_cortex
            timeout_sec = tq_cortex.get_adjusted_timeout(agent_role, def_t)
        except Exception:
            timeout_sec = def_t
    if heartbeat_sec is None: heartbeat_sec = def_h

    # 2) 校验 level
    if level not in ALL_LEVELS:
        raise ValueError(f"invalid level: {level} (must be in {ALL_LEVELS})")

    # 3) L/CRITICAL 必填 4 问
    profile = LEVEL_PROFILE[level]
    if profile["min_4q"]:
        missing = []
        if not files: missing.append("files")
        if not verify_plan: missing.append("verify_plan")
        if not deliverable: missing.append("deliverable")
        if missing:
            raise ValueError(
                f"level={level} 必须填 4 问 (缺: {', '.join(missing)})。"
                f"4 问=1.解决啥(goal)/2.影响啥(files)/3.验证啥(verify_plan)/4.沉淀啥(deliverable)"
            )

    # 4) CRITICAL 额外：verify_plan 至少 1 条 deliverable 非空
    if level == LEVEL_CRITICAL:
        if not deliverable or not str(deliverable).strip():
            raise ValueError("CRITICAL 任务 deliverable 必须非空（给老大看）")

    def _do(tasks):
        t = _new_task(goal, agent_role, timeout_sec, heartbeat_sec,
                      context, parent)
        t["level"] = level
        t["files"] = files or []
        t["verify_plan"] = verify_plan or []
        t["deliverable"] = deliverable or ""
        tasks[t["task_id"]] = t

    tasks, _ = mutate(_do)
    task = tasks[next(tid for tid in tasks
                      if tasks[tid]["goal"] == goal
                      and tasks[tid]["created_at"] >= int(time.time()) - 2)]
    _log(f"ENQUEUE {task['task_id']} role={agent_role} level={level} "
         f"timeout={timeout_sec}s hb={heartbeat_sec}s")
    return task


def heartbeat(task_id: str, progress_current: int = None,
              progress_total: int = None, message: str = "",
              status: str = STATUS_RUNNING) -> dict:
    """更新心跳。在锁内一次性 read+write。"""
    if status not in ALL_STATUSES:
        raise ValueError(f"invalid status: {status}")
    now = int(time.time())
    out = {"updated": None}

    def _do(tasks):
        if task_id not in tasks:
            raise KeyError(f"task not found: {task_id}")
        t = tasks[task_id]
        t["last_heartbeat"] = now
        t["updated_at"] = now
        t["status"] = status
        if progress_current is not None:
            t["progress"]["current"] = progress_current
        if progress_total is not None:
            t["progress"]["total"] = progress_total
        if message:
            t["progress"]["message"] = message
        out["updated"] = t

    mutate(_do)
    _log(f"HEARTBEAT {task_id} status={status} "
         f"progress={progress_current}/{progress_total} msg={message}")
    return out["updated"]


def mark_done(task_id: str, result: dict = None,
              archive: bool = True) -> dict:
    """标 done。archive=True（默认）会从 active 移到 archive。"""
    now = int(time.time())
    out = {"updated": None}

    def _do(tasks):
        if task_id not in tasks:
            raise KeyError(f"task not found: {task_id}")
        t = tasks[task_id]
        t["status"] = STATUS_DONE
        t["result"] = result or {}
        t["updated_at"] = now
        t["last_heartbeat"] = now
        out["updated"] = t

    mutate(_do)
    _log(f"DONE {task_id} result_keys={list((result or {}).keys())}")
    return out["updated"]


def mark_failed(task_id: str, error: str,
                reason: str = "agent_reported",
                archive: bool = True) -> dict:
    """标 failed。"""
    now = int(time.time())
    out = {"updated": None}

    def _do(tasks):
        if task_id not in tasks:
            raise KeyError(f"task not found: {task_id}")
        t = tasks[task_id]
        t["status"] = STATUS_FAILED
        t["error"] = {"reason": reason, "msg": error, "at": now}
        t["updated_at"] = now
        out["updated"] = t

    mutate(_do)
    _log(f"FAILED {task_id} reason={reason} error={error[:200]}")
    return out["updated"]


def mark_timeout(task_id: str, archive: bool = True) -> dict:
    """标 timeout（独立 status，不再伪装 failed）。"""
    now = int(time.time())
    out = {"updated": None}

    def _do(tasks):
        if task_id not in tasks:
            raise KeyError(f"task not found: {task_id}")
        t = tasks[task_id]
        t["status"] = STATUS_TIMEOUT  # 真写 timeout
        t["error"] = {"reason": "watchdog_timeout",
                      "msg": "no heartbeat for > timeout window",
                      "at": now}
        t["updated_at"] = now
        out["updated"] = t

    mutate(_do)
    _log(f"TIMEOUT {task_id}")
    return out["updated"]


def cancel(task_id: str, archive: bool = True) -> dict:
    now = int(time.time())
    out = {"updated": None}

    def _do(tasks):
        if task_id not in tasks:
            raise KeyError(f"task not found: {task_id}")
        t = tasks[task_id]
        t["status"] = STATUS_CANCELLED
        t["updated_at"] = now
        out["updated"] = t

    mutate(_do)
    _log(f"CANCEL {task_id}")
    return out["updated"]


# ============================================================
# v4: requeue_from_archive — escalate 自救用
# ============================================================
RETRY_STRATEGY_PROMPT = "rewrite_prompt"   # 改写 prompt 重试
RETRY_STRATEGY_TIMEOUT = "extend_timeout"  # 拉大 timeout
RETRY_STRATEGY_DOWNGRADE = "downgrade_role"  # 降级 role


def requeue_from_archive(task_id: str, strategy: str = RETRY_STRATEGY_TIMEOUT,
                          new_goal: str = None,
                          new_agent_role: str = None,
                          new_timeout_sec: int = None,
                          new_heartbeat_sec: int = None,
                          reason: str = "") -> dict:
    """
    一步完成：从 archive 拽回 + 应用重试策略 + 重置状态到 queued。
    解决 mutate() 自动归档终态任务的问题。
    """
    if strategy not in {RETRY_STRATEGY_PROMPT, RETRY_STRATEGY_TIMEOUT,
                        RETRY_STRATEGY_DOWNGRADE}:
        raise ValueError(f"unknown strategy: {strategy}")

    _ensure_dirs()
    now = int(time.time())
    out = {"updated": None, "from_date": None,
           "retry_count_new": 0, "strategy": strategy}

    def _do(tasks):
        # 步骤 1: 已在 active 就直接用；否则从 archive 拽
        if task_id in tasks:
            t = tasks[task_id]
            out["from_date"] = "(already active)"
        else:
            found = None
            from_date = None
            for jsonl in sorted(ARCHIVE_DIR.glob("*.jsonl*"), reverse=True):
                opener = gzip.open if jsonl.suffix == ".gz" else open
                with opener(jsonl, "rt", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            tt = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if tt.get("task_id") == task_id:
                            found = tt
                            from_date = jsonl.stem.replace(".jsonl", "")
                            break
                if found:
                    break
            if not found:
                raise KeyError(f"task {task_id} not in active or any archive")
            t = found
            t.pop("_archived_at", None)
            tasks[task_id] = t
            out["from_date"] = from_date
            # 从 jsonl 物理删除这一行
            archive_file = ARCHIVE_DIR / f"{from_date}.jsonl"
            archive_file_gz = ARCHIVE_DIR / f"{from_date}.jsonl.gz"
            for f in [archive_file, archive_file_gz]:
                if not f.exists():
                    continue
                opener = gzip.open if f.suffix == ".gz" else open
                lines = []
                with opener(f, "rt", encoding="utf-8") as fp:
                    for line in fp:
                        if task_id not in line:
                            lines.append(line)
                with opener(f, "wt", encoding="utf-8") as fp:
                    fp.writelines(lines)

        # 步骤 2: 校验
        ALLOW_FROM = {STATUS_TIMEOUT, STATUS_FAILED}
        if t["status"] not in ALLOW_FROM:
            raise ValueError(
                f"task {task_id} status={t['status']} 不允许重试 "
                f"(只允许 {ALLOW_FROM})"
            )
        profile = LEVEL_PROFILE.get(t.get("level", LEVEL_M),
                                    LEVEL_PROFILE[LEVEL_M])
        max_retries = profile["max_retries"]
        old_retry = t.get("retry_count", 0)
        if old_retry >= max_retries:
            raise ValueError(
                f"task {task_id} retry_count={old_retry} 已达上限 {max_retries} "
                f"(level={t.get('level')})"
            )

        # 步骤 3: 应用策略
        history = t.get("retry_history", [])
        entry = {
            "at": now,
            "strategy": strategy,
            "reason": reason,
            "from_date": out["from_date"],
            "before": {
                "status": t["status"],
                "goal": t["goal"][:200],
                "agent_role": t["agent_role"],
                "timeout_sec": t["timeout_sec"],
            }
        }

        if strategy == RETRY_STRATEGY_PROMPT:
            if not new_goal:
                raise ValueError("rewrite_prompt 必须传 new_goal")
            t["goal"] = new_goal
            entry["after_goal_prefix"] = new_goal[:200]
        elif strategy == RETRY_STRATEGY_TIMEOUT:
            old_to = t["timeout_sec"]
            new_to = new_timeout_sec if new_timeout_sec else old_to * 2
            t["timeout_sec"] = new_to
            entry["before_timeout"] = old_to
            entry["after_timeout"] = new_to
        elif strategy == RETRY_STRATEGY_DOWNGRADE:
            if not new_agent_role:
                raise ValueError("downgrade_role 必须传 new_agent_role")
            old_role = t["agent_role"]
            t["agent_role"] = new_agent_role
            def_t, def_h, _ = ROLE_DEFAULTS.get(new_agent_role,
                                                ROLE_DEFAULTS["general"])
            t["timeout_sec"] = new_timeout_sec if new_timeout_sec else def_t
            t["heartbeat_sec"] = (new_heartbeat_sec if new_heartbeat_sec
                                  else def_h)
            entry["before_role"] = old_role
            entry["after_role"] = new_agent_role
            entry["after_timeout"] = t["timeout_sec"]
            entry["after_heartbeat"] = t["heartbeat_sec"]

        # 步骤 4: 重置状态 (mutate 不会归档 status=queued)
        t["status"] = STATUS_QUEUED
        t["last_heartbeat"] = now
        t["started_at"] = now
        t["updated_at"] = now
        t["error"] = None
        t["retry_count"] = old_retry + 1
        t["retry_history"] = history + [entry]

        # 清 nudge
        NUDGES_DIR.mkdir(parents=True, exist_ok=True)
        nudge_file = NUDGES_DIR / f"{task_id}.json"
        if nudge_file.exists():
            nudge_file.unlink()

        out["updated"] = t
        out["retry_count_new"] = t["retry_count"]

    mutate(_do)
    _log(f"REQUEUE_FROM_ARCHIVE {task_id} strategy={strategy} "
         f"retry_count={out['retry_count_new']} from={out['from_date']} "
         f"reason={reason[:50]}")
    return out["updated"]


def get(task_id: str) -> dict | None:
    """从 active 拿。拿不到自动去 archive 找。"""
    _ensure_dirs()
    with _Lock(LOCK_FILE):
        try:
            tasks = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            tasks = {}
        if task_id in tasks:
            return tasks[task_id]
    # 去 archive
    for f in sorted(ARCHIVE_DIR.glob("*.jsonl"), reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as inp:
                for line in inp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        t = json.loads(line)
                    except Exception:
                        continue
                    if t.get("task_id") == task_id:
                        return t
        except Exception:
            continue
    return None


def list_active() -> list:
    """返回 active 任务列表。"""
    _ensure_dirs()
    with _Lock(LOCK_FILE):
        try:
            tasks = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            tasks = {}
    # 过滤：只返 known status，且非终态
    out = []
    for t in tasks.values():
        s = t.get("status")
        if s not in ALL_STATUSES:
            continue  # 脏 status 跳过（不返不崩）
        if s in TERMINAL_STATUSES:
            continue
        out.append(t)
    return out


def list_by_date(date_str: str) -> list:
    """列某日 created 的所有任务（active + archive）。"""
    out = []
    # active
    _ensure_dirs()
    with _Lock(LOCK_FILE):
        try:
            tasks = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            tasks = {}
    for t in tasks.values():
        if _date_str(t["created_at"]) == date_str:
            out.append(t)
    # archive
    f = ARCHIVE_DIR / f"{date_str}.jsonl"
    f_gz = ARCHIVE_DIR / f"{date_str}.jsonl.gz"
    # 优先读 gz（已压缩），否则读 jsonl
    if f_gz.exists():
        opener = lambda: gzip.open(f_gz, "rt", encoding="utf-8")
    elif f.exists():
        opener = lambda: open(f, "r", encoding="utf-8")
    else:
        return out
    with opener() as inp:
        for line in inp:
            line = line.strip()
            if not line:
                continue
            try:
                t = json.loads(line)
                if _date_str(t["created_at"]) == date_str:
                    out.append(t)
            except Exception:
                continue
    return out


def find_stale(now: int = None) -> list:
    """返回 (task, gap) 列表，gap 是心跳断秒数。只看 active。"""
    now = now or int(time.time())
    stale = []
    for t in list_active():
        gap = now - t["last_heartbeat"]
        if gap > t["timeout_sec"]:
            stale.append((t, gap))
    return stale


def mark_timeouts_batch(task_ids: list) -> list:
    """批量标 timeout，1 次锁。返回成功标的任务列表。"""
    now = int(time.time())
    out = []

    def _do(tasks):
        for tid in task_ids:
            if tid in tasks and tasks[tid]["status"] not in TERMINAL_STATUSES:
                t = tasks[tid]
                t["status"] = STATUS_TIMEOUT
                t["error"] = {"reason": "watchdog_timeout",
                              "msg": "no heartbeat for > timeout window",
                              "at": now}
                t["updated_at"] = now
                out.append(tid)
        # 返回所有改了的 id 让 mutate 归档
        return out

    mutate(_do)
    _log(f"TIMEOUT_BATCH {len(out)} tasks")
    return out


def stats_today() -> dict:
    """今日统计（从 archive 算完态 + active 算进行中）。"""
    today = _date_str()
    all_today = list_by_date(today)
    by_status = {}
    for t in all_today:
        by_status.setdefault(t["status"], 0)
        by_status[t["status"]] += 1
    return {
        "date": today,
        "total": len(all_today),
        "by_status": by_status,
    }


# ---------- v3: nudge / ping / escalate API ----------
NUDGE_KIND_NUDGE = "nudge"          # 1×stale: 温柔提醒
NUDGE_KIND_PING = "ping"            # 2×stale: 明确质问
NUDGE_KIND_ESCALATE = "escalate"    # 3×stale: 推老大
NUDGE_KINDS = {NUDGE_KIND_NUDGE, NUDGE_KIND_PING, NUDGE_KIND_ESCALATE}


def write_nudge(task_id: str, kind: str, msg: str = None,
                last_heartbeat: int = None, gap_sec: int = None) -> dict:
    """
    watchdog 写 nudge 到 nudges/{task_id}.json。
    每次写覆盖（kind 可能升级：nudge → ping → escalate）。
    返回写入的 nudge dict。
    """
    if kind not in NUDGE_KINDS:
        raise ValueError(f"invalid nudge kind: {kind}")
    _ensure_dirs()
    task = get(task_id)
    if not task:
        raise KeyError(f"task not found: {task_id}")
    payload = {
        "task_id": task_id,
        "kind": kind,
        "at": int(time.time()),
        "last_heartbeat": last_heartbeat or task.get("last_heartbeat"),
        "gap_sec": gap_sec or (int(time.time()) - task.get("last_heartbeat", int(time.time()))),
        "msg": msg or _default_nudge_msg(kind, gap_sec),
    }
    f = NUDGES_DIR / f"{task_id}.json"
    f.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    _log(f"NUDGE_WRITE {task_id} kind={kind} gap={payload['gap_sec']}s")
    return payload


def _default_nudge_msg(kind: str, gap_sec) -> str:
    if kind == NUDGE_KIND_NUDGE:
        return f"{gap_sec}s 无新心跳，请报告进度"
    if kind == NUDGE_KIND_PING:
        return f"{gap_sec}s 无新心跳，请明确：(1) 当前进度 (2) 卡在哪 (3) 还要多久"
    return f"{gap_sec}s 无新心跳，父级已 escalate 推老大，请立即冻结等待"


def consume_nudges(task_id: str) -> list:
    """
    子 agent 启动时调用。返回所有未消费的 nudge 列表（按时间排序），
    同时**删除**该 task 的 nudge 文件（消费 = 拿走）。
    如果没 nudge 返回 []。
    """
    _ensure_dirs()
    f = NUDGES_DIR / f"{task_id}.json"
    if not f.exists():
        return []
    try:
        payload = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []
    # 消费 = 拿走
    f.unlink()
    _log(f"NUDGE_CONSUME {task_id} kind={payload.get('kind')}")
    return [payload]


def peek_nudge(task_id: str) -> dict | None:
    """看一眼不消费。"""
    f = NUDGES_DIR / f"{task_id}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def clear_nudge(task_id: str):
    """子 agent 回执后调，删 nudge（已被 consume_nudges 自动删，但暴露给显式清理）。"""
    f = NUDGES_DIR / f"{task_id}.json"
    if f.exists():
        f.unlink()


# ---------- 老数据迁移 ----------
def migrate_from_legacy():
    """
    把老 queue.json (list[dict]) 迁到新架构。
    已终态的 → archive/{date}.jsonl
    未终态的 → 新 queue.json
    幂等：再跑一次不重复。
    """
    legacy = QUEUE_DIR / "queue.json"
    if not legacy.exists():
        return {"migrated": 0, "skipped": "no legacy file"}
    _ensure_dirs()  # 确保 archive/ 存在

    # 读老格式（list）
    try:
        content = legacy.read_text(encoding="utf-8").strip()
        if not content or content == "{}":
            return {"migrated": 0, "skipped": "empty"}
        old = json.loads(content)
    except Exception as e:
        return {"migrated": 0, "error": f"parse fail: {e}"}

    if isinstance(old, dict):
        # 已经是新格式
        return {"migrated": 0, "skipped": "already new format"}

    if not isinstance(old, list):
        return {"migrated": 0, "error": "unknown format"}

    # 备份老文件
    bak = QUEUE_DIR / f"queue.json.legacy.bak.{int(time.time())}"
    legacy.rename(bak)
    # 新空文件
    legacy.write_text("{}", encoding="utf-8")

    # 分类
    n_archive = 0
    n_active = 0
    by_date_archive = {}

    for t in old:
        if not isinstance(t, dict) or "task_id" not in t:
            continue
        if t.get("status") in TERMINAL_STATUSES:
            date_str = _date_str(t.get("created_at"))
            by_date_archive.setdefault(date_str, []).append(t)
            n_archive += 1
        else:
            by_date_archive.setdefault("__active__", []).append(t)
            n_active += 1

    # 写 archive
    for date_str, ts in by_date_archive.items():
        if date_str == "__active__":
            continue
        f = ARCHIVE_DIR / f"{date_str}.jsonl"
        with open(f, "a", encoding="utf-8") as out:
            for t in ts:
                out.write(json.dumps(t, ensure_ascii=False) + "\n")

    # 写 active
    active = {t["task_id"]: t
              for t in by_date_archive.get("__active__", [])}
    legacy.write_text(json.dumps(active, ensure_ascii=False, indent=2,
                                 sort_keys=True), encoding="utf-8")

    return {"migrated": n_archive, "active_kept": n_active, "backup": str(bak)}


# ---------- CLI ----------
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for t in list_active():
            print(f"{t['task_id']}\t{t['status']}\t"
                  f"{datetime.fromtimestamp(t['last_heartbeat'])}\t"
                  f"{t['progress']}")
    elif cmd == "stale":
        for t, gap in find_stale():
            print(f"{t['task_id']}\tgap={gap}s\t{t['status']}\t{t['goal'][:60]}")
    elif cmd == "stats":
        print(json.dumps(stats_today(), ensure_ascii=False, indent=2))
    elif cmd == "migrate":
        print(json.dumps(migrate_from_legacy(), ensure_ascii=False, indent=2))
    elif cmd == "enqueue-demo":
        t = enqueue("demo task", agent_role="ops")
        print(t)
    else:
        print(__doc__)
