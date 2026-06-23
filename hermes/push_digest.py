"""daily-digest 全链路推送器 v2.
pipeline: digest.md -> PDF -> PNG -> GitHub raw (永久) -> outbox.json -> 通知通道
通道: 优先 ~/.hermes/channel.json;否则 落本地 + 打印 share_text 备用
"""
import json
import sys
import time
from pathlib import Path

HERMES = Path.home() / ".hermes"
DIGEST = HERMES / "digest"
RENDERER = HERMES / "daily_renderer_v2.py"
PDF2PNG = HERMES / "digest" / "_tools" / "pdf_to_png.py"  # 复用今天的实现, 后续搬
GH_UPLOADER = HERMES / "upload_to_github.py"
CHANNEL = HERMES / "channel.json"
TEMPLATE = HERMES / "digest" / "_tools" / "channel.template.json"


def render_pdf(date_str: str, md_path: Path, pdf_path: Path, title: str) -> Path:
    """调 daily_renderer_v2.py 产 PDF.  用 sys.executable 避免 PATH 中其他 python 缺包."""
    import subprocess
    r = subprocess.run(
        [sys.executable, str(RENDERER), str(md_path), str(pdf_path), title],
        capture_output=True, text=True, encoding="utf-8"
    )
    if r.returncode != 0 or not pdf_path.exists():
        raise RuntimeError(f"renderer failed: {r.stderr or r.stdout}")
    return pdf_path


def render_pngs(pdf_path: Path, out_dir: Path, zoom: float = 1.5) -> list:
    """PDF -> 多张 PNG, 落 out_dir.  返回 PNG 路径列表."""
    import subprocess
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / "page"
    r = subprocess.run(
        [sys.executable, str(PDF2PNG), str(pdf_path), str(base) + ".png", str(zoom)],
        capture_output=True, text=True, encoding="utf-8"
    )
    if r.returncode != 0:
        raise RuntimeError(f"pdf_to_png failed: {r.stderr or r.stdout}")
    pngs = sorted(out_dir.glob("page_*.png"))
    return pngs


def push_to_github(date_str: str, png_paths: list) -> list:
    """PNG -> GitHub raw.  返回 [{page, url, size, sha256_prefix}, ...]"""
    import upload_to_github
    return upload_to_github.push_pngs(date_str, png_paths)


def load_channel() -> dict | None:
    """优先 ~/.hermes/channel.json,否则 template."""
    for path in (CHANNEL, TEMPLATE):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
    return None


def notify(channel_cfg: dict, outbox: dict) -> dict:
    """按 active_channel 推送. 无凭证只落本地."""
    import urllib.request
    if not channel_cfg:
        return {"status": "no_channel", "note": "落本地 outbox.json"}
    active = channel_cfg.get("active_channel")
    if not active:
        return {"status": "local_only", "note": "active_channel 未设"}
    channels = channel_cfg.get("channels", {})
    target = channels.get(active)
    if not target or not target.get("enabled"):
        return {"status": "disabled", "channel": active}
    if "PLACEHOLDER" in str(target):
        return {"status": "placeholder", "channel": active, "note": "老大还没填 key"}
    ctype = target.get("type")
    text = outbox.get("share_text", "")
    try:
        if ctype == "feishu_webhook":
            body = {"msg_type": "text", "content": {"text": text}}
            req = urllib.request.Request(target["url"],
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"})
        elif ctype == "wechat_work_webhook":
            body = {"msgtype": "text", "text": {"content": text}}
            req = urllib.request.Request(target["url"],
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"})
        elif ctype == "telegram":
            url = f"https://api.telegram.org/bot{target['bot_token']}/sendMessage"
            body = {"chat_id": target["chat_id"], "text": text}
            req = urllib.request.Request(url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"})
        else:
            return {"status": "unknown_type", "type": ctype}
        with urllib.request.urlopen(req, timeout=15) as r:
            return {"status": "pushed", "channel": active, "http": r.status, "body": r.read().decode("utf-8", "ignore")[:200]}
    except Exception as e:
        return {"status": "fail", "channel": active, "error": str(e)}


def main(date_str: str = None):
    date_str = date_str or time.strftime("%Y-%m-%d")
    date_dir = DIGEST / date_str
    md_path = date_dir / "content.md"
    if not md_path.exists():
        print(f"[ERR] no content.md at {md_path}")
        return 1
    pdf_path = date_dir / "daily.pdf"
    title = f"Daily Digest · {date_str}"
    print(f"[1/4] rendering PDF from {md_path} ...")
    render_pdf(date_str, md_path, pdf_path, title)
    print(f"  -> {pdf_path} ({pdf_path.stat().st_size} B)")

    print(f"[2/4] PDF -> PNG ...")
    pngs = render_pngs(pdf_path, date_dir)
    for p in pngs:
        print(f"  -> {p.name} ({p.stat().st_size} B)")
    if not pngs:
        print(f"[ERR] no PNG generated")
        return 1

    print(f"[3/4] pushing {len(pngs)} PNGs to GitHub raw ...")
    images = push_to_github(date_str, pngs)
    for img in images:
        print(f"  -> page {img['page']}: {img['url']}")

    # 写 outbox.json
    outbox = {
        "date": date_str,
        "title": title,
        "title_zh": title,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "host": "permanent · GitHub raw · shishenshashen/atest",
        "total_pages": len(pngs),
        "pdf": {
            "path": str(pdf_path),
            "size_bytes": pdf_path.stat().st_size,
        },
        "images": [
            {
                "page": img["page"],
                "title": f"page {img['page']}",
                "url": img["url"],
                "size_bytes": img["size"],
            }
            for img in images
        ],
    }
    # share_text
    lines = [
        f"📊 小神龙日报 {date_str}",
        f"📁 {len(pngs)} 页 (永久公网·GitHub raw)",
        "",
    ]
    for img in images:
        lines.append(f"{img['page']}️⃣ {img['url']}")
    outbox["share_text"] = "\n".join(lines)
    outbox_path = date_dir / "outbox.json"
    outbox_path.write_text(json.dumps(outbox, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> outbox.json ({outbox_path.stat().st_size} B)")

    # commit outbox 也上 gh
    import upload_to_github
    import shutil
    repo = upload_to_github.DEFAULT_REPO_DIR
    target = repo / "digest" / date_str / "outbox.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(outbox_path, target)
    upload_to_github.ensure_repo(repo, upload_to_github.DEFAULT_REPO_URL, upload_to_github.DEFAULT_BRANCH)
    import subprocess
    subprocess.run(["git", "add", str(target.relative_to(repo))], cwd=str(repo), check=True, capture_output=True, text=True, encoding="utf-8")
    subprocess.run(["git", "commit", "-m", f"digest: {date_str} outbox (auto)"], cwd=str(repo), capture_output=True, text=True, encoding="utf-8")
    push = subprocess.run(["git", "push", "origin", upload_to_github.DEFAULT_BRANCH], cwd=str(repo), capture_output=True, text=True, encoding="utf-8")
    if push.returncode == 0:
        print(f"  -> outbox.json pushed to GitHub")
    else:
        print(f"  -> outbox push skipped (可能 no changes)")

    print(f"[4/4] notifying ...")
    ch = load_channel()
    result = notify(ch, outbox)
    print(f"  -> {result}")
    log = date_dir / "push_log.json"
    log.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ DONE: {date_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
