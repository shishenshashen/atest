"""
task-queue/cortex.py  v1 (2026-06-11)
Cortex-lite 自调参：只动 timeout，3 规则：
1. 某 role 累计 timeout ≥ 3 次 → 该 role 默认 timeout × 0.5
2. 某 role 连续 10 次 done → 该 role 默认 timeout × 1.2（仅 L/CRITICAL）
3. 手动调过 → 重置自动调参（老大拍板优先）

存到 ~/.hermes/task-queue/cortex.json
"""
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# 跨平台锁
if sys.platform == "win32":
    import msvcrt
    class _Lock:
        def __init__(self, path):
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
            except Exception:
                pass
            self._fd.close()
else:
    import fcntl
    class _Lock:
        def __init__(self, path):
            self.path = path
            self._fd = None
        def __enter__(self):
            self._fd = open(self.path, "w")
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX)
            return self
        def __exit__(self, *a):
            try:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            self._fd.close()


CORTEX_FILE = Path.home() / ".hermes" / "task-queue" / "cortex.json"
LOCK_FILE = Path.home() / ".hermes" / "task-queue" / "cortex.lock"

# 调参阈值
TIMEOUT_DOWN_THRESHOLD = 3   # 累计超时 N 次 → 降
TIMEOUT_DOWN_FACTOR = 0.5    # 降为原值的 50%
SUCCESS_UP_THRESHOLD = 10    # 连续成功 N 次 → 升（保守）
SUCCESS_UP_FACTOR = 1.2      # 升为原值的 120%
MIN_TIMEOUT = 30             # 不低于 30s（再低意义不大）
MAX_TIMEOUT_FACTOR = 3.0     # 升不超过原默认的 3x

# 哪类 level 才升（保守：只 L/CRITICAL）
LEVELS_ALLOW_UP = {"L", "CRITICAL"}


def _ensure():
    CORTEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CORTEX_FILE.exists():
        CORTEX_FILE.write_text("{}", encoding="utf-8")


def _read() -> dict:
    _ensure()
    with _Lock(LOCK_FILE):
        try:
            return json.loads(CORTEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}


def _write(data: dict):
    _ensure()
    with _Lock(LOCK_FILE):
        tmp = CORTEX_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2,
                                  sort_keys=True), encoding="utf-8")
        import os
        os.replace(tmp, CORTEX_FILE)


def _get_role_state(data: dict, role: str) -> dict:
    return data.setdefault(role, {
        "auto_timeout": None,       # 自动调后的 timeout
        "manual_timeout": None,     # 手动指定的（覆盖 auto）
        "manual_override": False,   # 手动优先级最高
        "consecutive_done": 0,      # 连续 done 次数
        "total_timeout": 0,         # 累计 timeout 次数
        "last_adj_at": 0,           # 最后调参时间戳
        "last_adj_kind": None,      # "down" / "up" / "manual" / "reset"
    })


def record_timeout(role: str) -> dict:
    """
    某 role 任务 timeout 了 → 计数 +1。
    累计 ≥ TIMEOUT_DOWN_THRESHOLD → 自动降 timeout。
    返回更新后的 state + 是否触发降级。
    """
    data = _read()
    st = _get_role_state(data, role)

    if st["manual_override"]:
        # 手动拍过板，不动 auto
        st["last_adj_kind"] = "skipped (manual override)"
        st["last_adj_at"] = int(time.time())
        _write(data)
        return {"state": st, "auto_adjusted": False, "reason": "manual_override"}

    st["total_timeout"] += 1
    st["consecutive_done"] = 0  # 重置连续 done
    auto_adjusted = False
    reason = ""

    if st["total_timeout"] >= TIMEOUT_DOWN_THRESHOLD:
        # 计算新 timeout
        if st["auto_timeout"] is None:
            from tq_queue import ROLE_DEFAULTS  # 导入原始默认
            def_t = ROLE_DEFAULTS.get(role, ROLE_DEFAULTS["general"])[0]
            new_t = max(MIN_TIMEOUT, int(def_t * TIMEOUT_DOWN_FACTOR))
        else:
            new_t = max(MIN_TIMEOUT, int(st["auto_timeout"] * TIMEOUT_DOWN_FACTOR))

        st["auto_timeout"] = new_t
        st["last_adj_at"] = int(time.time())
        st["last_adj_kind"] = "down"
        st["total_timeout"] = 0  # 重置累计，下一轮
        auto_adjusted = True
        reason = f"timeout x{TIMEOUT_DOWN_THRESHOLD} → auto_timeout={new_t}s"

    _write(data)
    return {"state": st, "auto_adjusted": auto_adjusted, "reason": reason}


def record_done(role: str, level: str) -> dict:
    """
    某 role 任务成功 done。
    连续 ≥ SUCCESS_UP_THRESHOLD 次 + level ∈ LEVELS_ALLOW_UP → 自动升 timeout（保守）。
    """
    data = _read()
    st = _get_role_state(data, role)

    if st["manual_override"]:
        st["consecutive_done"] += 1
        st["last_adj_kind"] = "skipped (manual override)"
        st["last_adj_at"] = int(time.time())
        _write(data)
        return {"state": st, "auto_adjusted": False, "reason": "manual_override"}

    st["consecutive_done"] += 1
    auto_adjusted = False
    reason = ""

    if (st["consecutive_done"] >= SUCCESS_UP_THRESHOLD
            and level in LEVELS_ALLOW_UP):
        from tq_queue import ROLE_DEFAULTS
        def_t = ROLE_DEFAULTS.get(role, ROLE_DEFAULTS["general"])[0]
        # 当前值：auto_timeout 优先，否则 def_t
        cur = st["auto_timeout"] or def_t
        new_t = int(cur * SUCCESS_UP_FACTOR)
        # 上限：原默认的 3x
        if new_t > def_t * MAX_TIMEOUT_FACTOR:
            new_t = int(def_t * MAX_TIMEOUT_FACTOR)

        if new_t > cur:  # 真的升了
            st["auto_timeout"] = new_t
            st["last_adj_at"] = int(time.time())
            st["last_adj_kind"] = "up"
            st["consecutive_done"] = 0
            auto_adjusted = True
            reason = f"done x{SUCCESS_UP_THRESHOLD} (level={level}) → auto_timeout={new_t}s"
        else:
            st["consecutive_done"] = 0  # 也重置

    _write(data)
    return {"state": st, "auto_adjusted": auto_adjusted, "reason": reason}


def get_adjusted_timeout(role: str, default_timeout: int) -> int:
    """enqueue() 调用：拿 cortex 调过的 timeout（无则用 default）。"""
    data = _read()
    st = data.get(role)
    if not st:
        return default_timeout
    # 手动优先
    if st.get("manual_override") and st.get("manual_timeout"):
        return st["manual_timeout"]
    # auto 其次
    if st.get("auto_timeout"):
        return st["auto_timeout"]
    return default_timeout


def set_manual(role: str, timeout_sec: int) -> dict:
    """老大手动指定：覆盖 auto，老大拍板优先。"""
    data = _read()
    st = _get_role_state(data, role)
    st["manual_timeout"] = timeout_sec
    st["manual_override"] = True
    st["last_adj_at"] = int(time.time())
    st["last_adj_kind"] = "manual"
    st["consecutive_done"] = 0
    st["total_timeout"] = 0
    _write(data)
    return st


def reset(role: str) -> dict:
    """重置某 role 的所有 cortex 调参。"""
    data = _read()
    if role in data:
        del data[role]
    _write(data)
    return {}


def get_state(role: str) -> dict:
    return _read().get(role, {})


def get_all() -> dict:
    return _read()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "show":
        print(json.dumps(get_all(), ensure_ascii=False, indent=2))
    elif cmd == "reset":
        for r in sys.argv[2:]:
            reset(r)
            print(f"reset {r}")
    elif cmd == "set":
        # set ops 300
        role, t = sys.argv[2], int(sys.argv[3])
        st = set_manual(role, t)
        print(json.dumps(st, ensure_ascii=False, indent=2))
    elif cmd == "test-timeout":
        for r in sys.argv[2:]:
            print(r, record_timeout(r))
    elif cmd == "test-done":
        for r in sys.argv[2:]:
            print(r, record_done(r, "L"))
    else:
        print(__doc__)
