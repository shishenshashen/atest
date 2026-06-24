"""_state_db_pack.py - 把 state.db 压缩成 .gz (51MB -> ~10MB)
排除 .db-shm 和 .db-wal (SQLite 临时, 删了不影响)
"""
import sys, gzip, os, sqlite3
from pathlib import Path

def pack(src_db, dst_gz):
    src = Path(src_db)
    dst = Path(dst_gz)
    if not src.exists():
        print(f"[err] {src} not exist")
        return 1
    # SQLite 先 WAL checkpoint, 避免丢未提交数据
    try:
        con = sqlite3.connect(str(src))
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        con.close()
    except Exception as e:
        print(f"[warn] checkpoint: {e}")
    # 删 .db-shm 和 .db-wal (checkpoint 后无影响)
    # 注意: 如果 hermes-agent 还在用, 会 PermissionError - 跳过
    for ext in ("-shm", "-wal"):
        p = src.with_name(src.name + ext)
        if p.exists():
            try:
                p.unlink()
                print(f"  rm {p.name}")
            except PermissionError:
                print(f"  [skip] {p.name} (locked by hermes-agent)")
                # 不影响 gz, .db 主体已完整
    # gzip 压缩
    with open(src, "rb") as f_in:
        with gzip.open(dst, "wb", compresslevel=6) as f_out:
            while chunk := f_in.read(1024 * 1024):
                f_out.write(chunk)
    src_size = src.stat().st_size
    dst_size = dst.stat().st_size
    print(f"[pack] {src.name} {src_size/1024/1024:.2f} MB -> {dst.name} {dst_size/1024/1024:.2f} MB  ({dst_size/src_size*100:.1f}%)")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: _state_db_pack.py <src.db> <dst.db.gz>")
        sys.exit(1)
    sys.exit(pack(sys.argv[1], sys.argv[2]))
