"""把 digest PNG push 到 GitHub raw (永久公网).
- 依赖: ~/.ssh/id_ed25519_hermes (6/9 配, ssh -T 验证通过)
- 默认 repo: shishenshashen/atest (6/9 创, smoke-test 专用)
- 默认 branch: main
- 默认 path: digest/{date}/
- 不依赖 uguu.se (3h TTL 已废)
"""
import subprocess
import sys
import shutil
from pathlib import Path

DEFAULT_REPO_URL = "git@github.com:shishenshashen/atest.git"
DEFAULT_BRANCH = "main"
DEFAULT_REPO_DIR = Path.home() / ".hermes" / "github-mirror" / "atest"
DEFAULT_REPO_USER_NAME = "OrientWan"
DEFAULT_REPO_USER_EMAIL = "shishenshashen@users.noreply.github.com"


def _run(cmd, cwd=None, check=True):
    """Run a shell command, return CompletedProcess."""
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode != 0:
        raise RuntimeError(
            f"cmd failed: {' '.join(cmd)}\nstdout: {r.stdout}\nstderr: {r.stderr}"
        )
    return r


def ensure_repo(repo_dir: Path, repo_url: str, branch: str) -> Path:
    """确保仓库已 clone + 是最新 + branch 正确。"""
    if not (repo_dir / ".git").exists():
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", "--depth", "1", "-b", branch, repo_url, str(repo_dir)])
    else:
        # fetch latest
        try:
            _run(["git", "fetch", "--depth", "1", "origin", branch], cwd=str(repo_dir))
            _run(["git", "reset", "--hard", f"origin/{branch}"], cwd=str(repo_dir))
        except RuntimeError:
            # network blip; trust local
            pass
    # set identity (per-repo, 不会污染全局)
    _run(["git", "config", "user.name", DEFAULT_REPO_USER_NAME], cwd=str(repo_dir))
    _run(["git", "config", "user.email", DEFAULT_REPO_USER_EMAIL], cwd=str(repo_dir))
    return repo_dir


def push_pngs(date_str: str, png_paths: list, commit_msg: str = None,
              repo_dir: Path = None, branch: str = DEFAULT_BRANCH) -> list:
    """
    1. cp png 到 {repo}/digest/{date_str}/
    2. git add + commit + push
    3. 返回 [{page, filename, url, size, sha256_prefix}, ...]
    """
    import hashlib
    repo_dir = repo_dir or DEFAULT_REPO_DIR
    ensure_repo(repo_dir, DEFAULT_REPO_URL, branch)
    target_dir = repo_dir / "digest" / date_str
    target_dir.mkdir(parents=True, exist_ok=True)

    results = []
    files_to_add = []
    for i, src in enumerate(png_paths, 1):
        src = Path(src)
        if not src.exists():
            raise FileNotFoundError(src)
        dst = target_dir / src.name
        shutil.copy2(src, dst)
        files_to_add.append(str(dst.relative_to(repo_dir)))
        size = dst.stat().st_size
        sha = hashlib.sha256(dst.read_bytes()).hexdigest()[:16]
        results.append({
            "page": i,
            "filename": src.name,
            "url": f"https://raw.githubusercontent.com/shishenshashen/atest/{branch}/digest/{date_str}/{src.name}",
            "size": size,
            "sha256_prefix": sha,
        })

    # git add
    _run(["git", "add"] + files_to_add, cwd=str(repo_dir))
    # 检 nothing to commit
    status = _run(["git", "status", "--porcelain"], cwd=str(repo_dir), check=False)
    if not status.stdout.strip():
        # 已经有这个文件, 跳过 commit
        return results

    msg = commit_msg or f"digest: {date_str} ({len(png_paths)} images)"
    _run(["git", "commit", "-m", msg], cwd=str(repo_dir))
    push = _run(["git", "push", "origin", branch], cwd=str(repo_dir))
    return results


def get_latest_commit(repo_dir: Path = None, branch: str = DEFAULT_BRANCH) -> str:
    repo_dir = repo_dir or DEFAULT_REPO_DIR
    r = _run(["git", "rev-parse", "HEAD"], cwd=str(repo_dir))
    return r.stdout.strip()


if __name__ == "__main__":
    # 调试: python upload_to_github.py 2026-06-15 path1.png [path2.png ...]
    if len(sys.argv) < 3:
        print("Usage: upload_to_github.py <date_str> <png1> [png2 ...]")
        sys.exit(1)
    date_str = sys.argv[1]
    paths = sys.argv[2:]
    try:
        results = push_pngs(date_str, paths)
        commit = get_latest_commit()
        print(f"Pushed {len(results)} images to GitHub raw.")
        print(f"Latest commit: {commit}")
        for r in results:
            print(f"  page {r['page']}: {r['url']}  ({r['size']} B, sha={r['sha256_prefix']})")
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
