"""
task-queue/archive_compress.py
压缩 N 天前的 archive jsonl → gz，节省磁盘。
用法：
    python archive_compress.py [--days 7] [--dry-run]
cron: 每日 02:00 跑一次
"""
import sys
import gzip
import shutil
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

QUEUE_DIR = Path.home() / ".hermes" / "task-queue"
ARCHIVE_DIR = QUEUE_DIR / "archive"


def compress_one(jsonl_path: Path, dry_run: bool = False) -> dict:
    """压缩一个 jsonl → jsonl.gz，删除原文件。"""
    gz_path = jsonl_path.with_suffix(".jsonl.gz")
    if gz_path.exists():
        return {"skipped": "gz already exists", "path": str(jsonl_path)}
    if dry_run:
        return {"would_compress": str(jsonl_path),
                "size": jsonl_path.stat().st_size}

    # gzip 压缩
    with open(jsonl_path, "rb") as f_in:
        with gzip.open(gz_path, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)
    orig_size = jsonl_path.stat().st_size
    gz_size = gz_path.stat().st_size
    ratio = gz_size / orig_size if orig_size else 0
    # 删原文件
    jsonl_path.unlink()
    return {
        "compressed": str(jsonl_path),
        "to": str(gz_path),
        "orig_bytes": orig_size,
        "gz_bytes": gz_size,
        "ratio": f"{ratio:.1%}",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7,
                    help="压缩 N 天前的 jsonl（默认 7）")
    ap.add_argument("--dry-run", action="store_true",
                    help="只看不真压")
    args = ap.parse_args()

    if not ARCHIVE_DIR.exists():
        print(f"archive dir 不存在: {ARCHIVE_DIR}")
        return 0

    cutoff = datetime.now() - timedelta(days=args.days)
    results = []
    for p in sorted(ARCHIVE_DIR.glob("*.jsonl")):
        # 文件名格式: YYYY-MM-DD.jsonl
        try:
            file_date = datetime.strptime(p.stem, "%Y-%m-%d")
        except ValueError:
            continue
        if file_date >= cutoff:
            continue
        r = compress_one(p, dry_run=args.dry_run)
        r["date"] = p.stem
        results.append(r)

    if not results:
        print(f"没有 {args.days} 天前的 .jsonl 文件")
        return 0

    print(f"=== archive 压缩 (>{args.days} 天, dry_run={args.dry_run}) ===")
    for r in results:
        if "compressed" in r:
            print(f"  ✓ {r['date']}: {r['orig_bytes']} → {r['gz_bytes']} ({r['ratio']})")
        elif "would_compress" in r:
            print(f"  [dry] {r['date']}: {r['size']}B")
        else:
            print(f"  - {r['date']}: {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
