"""
task-queue/cli_detect.py  v1 (2026-06-15)
探测本地有哪些 agent CLI 可用，结果缓存到 ~/.hermes/.cli_capabilities.json。

支持的 CLI:
  - hermes      (Nous Research Hermes Agent 本体)
  - claude      (Anthropic Claude Code)
  - codex       (OpenAI Codex CLI)
  - aider       (aider)
  - cursor-agent (Cursor Agent CLI)

dispatch.py 会按这个 fallback 链自动找可用的。

用法:
  from cli_detect import detect, get_best_cli

  caps = detect(force_refresh=True)
  print(caps)
  # {"hermes": True, "claude": False, "codex": False, "aider": False, "cursor-agent": False,
  #  "best": "hermes", "detected_at": 1234567890}

  cli = get_best_cli()  # "hermes" or "claude" or "codex" ...
"""
import sys
import os
import json
import shutil
import time
import subprocess
from pathlib import Path
from typing import Optional


CACHE_FILE = Path.home() / ".hermes" / ".cli_capabilities.json"
CACHE_TTL = 3600  # 1 小时过期


# fallback 链优先级
FALLBACK_CHAIN = ["hermes", "claude", "codex", "cursor-agent", "aider"]


# 每个 CLI 的版本探测命令（可选）
VERSION_CMDS = {
    "hermes": ["hermes", "--version"],
    "claude": ["claude", "--version"],
    "codex": ["codex", "--version"],
    "cursor-agent": ["cursor-agent", "--version"],
    "aider": ["aider", "--version"],
}


def _read_cache() -> Optional[dict]:
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if time.time() - data.get("detected_at", 0) > CACHE_TTL:
            return None  # 过期
        return data
    except Exception:
        return None


def _write_cache(caps: dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(caps, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, CACHE_FILE)


def _probe_cli(name: str) -> dict:
    """探测单个 CLI：路径 + 版本（如果支持）。"""
    path = shutil.which(name)
    if not path:
        # Windows 上有时 .exe 后缀要手动加
        path = shutil.which(name + ".exe")
    if not path:
        return {"available": False, "path": None, "version": None}

    version = None
    if name in VERSION_CMDS:
        try:
            cmd = VERSION_CMDS[name]
            r = subprocess.run(cmd, capture_output=True,
                               timeout=5,
                               encoding="utf-8", errors="ignore")
            if r.returncode == 0:
                version = (r.stdout or r.stderr).strip().split("\n")[0][:80]
        except Exception:
            pass  # 版本探测失败不影响 available
    return {"available": True, "path": path, "version": version}


def detect(force_refresh: bool = False) -> dict:
    """
    探测所有 CLI，返回 dict：
      {
        "hermes": {"available": bool, "path": str|None, "version": str|None},
        "claude": {...},
        ...
        "best": "hermes" | "claude" | ... | None,
        "detected_at": int
      }
    """
    if not force_refresh:
        cached = _read_cache()
        if cached:
            return cached

    caps = {"detected_at": int(time.time())}
    for name in FALLBACK_CHAIN:
        caps[name] = _probe_cli(name)

    # 选 best（按 FALLBACK_CHAIN 顺序第一个 available）
    caps["best"] = None
    for name in FALLBACK_CHAIN:
        if caps.get(name, {}).get("available"):
            caps["best"] = name
            break

    _write_cache(caps)
    return caps


def get_best_cli(force_refresh: bool = False) -> Optional[str]:
    """返回 fallback 链第一个可用的 CLI 名（"hermes"/"claude"/...），或 None。"""
    return detect(force_refresh=force_refresh).get("best")


def get_cli_path(name: str, force_refresh: bool = False) -> Optional[str]:
    """返回指定 CLI 的可执行路径。"""
    caps = detect(force_refresh=force_refresh)
    return caps.get(name, {}).get("path")


def summary() -> str:
    """人类可读的多行字符串。"""
    caps = detect()
    lines = ["[cli_capabilities]"]
    for name in FALLBACK_CHAIN:
        c = caps.get(name, {})
        mark = "✅" if c.get("available") else "❌"
        ver = c.get("version") or "—"
        path = c.get("path") or "—"
        lines.append(f"  {mark} {name:14s} {path}  ({ver})")
    lines.append(f"  best: {caps.get('best') or '(none)'}")
    return "\n".join(lines)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "show":
        print(summary())
    elif cmd == "refresh":
        caps = detect(force_refresh=True)
        print(summary())
    elif cmd == "best":
        print(get_best_cli())
    else:
        print(__doc__)