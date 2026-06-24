"""
mt5-ea-dev/queries.py
懒加载查询 EA 知识库。绝不二次创作，所有数据从 vault 读。
"""
import os
import re
import sys
from pathlib import Path
from typing import Optional

VAULT = Path(r"C:\ai\obsidian-文件\mt")
EA_DEV = VAULT / "EA开发"


# ---------- 12 必读模块索引 ----------
MODULES_12 = {
    "M01": {"name": "交易封装 CTradePlus",
            "path": EA_DEV / "01-调用模块" / "M01 交易封装 CTradePlus.md"},
    "M02": {"name": "风控 Risk",
            "path": EA_DEV / "01-调用模块" / "M02 风控 Risk.md"},
    "M05": {"name": "新 K 线检测 NewBar",
            "path": EA_DEV / "01-调用模块" / "M05 新 K 线检测 NewBar.md"},
    "M08": {"name": "追踪止损 TrailingStop",
            "path": EA_DEV / "01-调用模块" / "M08 追踪止损 TrailingStop.md"},
    "M09": {"name": "面板 Dashboard",
            "path": EA_DEV / "01-调用模块" / "M09 面板 Dashboard.md"},
    "M10": {"name": "推送通知 Notify",
            "path": EA_DEV / "01-调用模块" / "M10 推送通知 Notify.md"},
    "M11": {"name": "日志 Logger",
            "path": EA_DEV / "01-调用模块" / "M11 日志 Logger.md"},
    "M13": {"name": "文件 IO",
            "path": EA_DEV / "01-调用模块" / "M13 文件 IO.md"},
    "M17": {"name": "新闻过滤 NewsFilter",
            "path": EA_DEV / "01-调用模块" / "M17 新闻过滤 NewsFilter.md"},
    "M18": {"name": "相关性过滤 CorrelationFilter",
            "path": EA_DEV / "01-调用模块" / "M18 相关性过滤 CorrelationFilter.md"},
    "M19": {"name": "时段过滤 SessionFilter",
            "path": EA_DEV / "01-调用模块" / "M19 时段过滤 SessionFilter.md"},
}


# ---------- 4 实物范本索引 ----------
TEMPLATES_4 = {
    "A_mean_reversion": {
        "name": "MeanReversion_EA 单 EA 接入",
        "path": EA_DEV / "实战" / "MeanReversion_EA 接入报告.md",
        "size_target": 17.7 * 1024,  # 期望字节（验证用）
    },
    "B_scalper_v1_v4": {
        "name": "ScalperXAU 接入 + v1→v4 演进",
        "path": EA_DEV / "实战" / "ScalperXAU 接入报告 + v1→v4 演进史.md",
        "size_target": 41 * 1024,
    },
    "C_trend_breakout": {
        "name": "TrendMA_EA + Breakout_EA 联合",
        "path": EA_DEV / "实战" / "TrendMA_EA + Breakout_EA 接入报告.md",
        "size_target": 40.4 * 1024,
    },
    "D_dashboard": {
        "name": "MyEA + Dashboard 接入",
        "path": EA_DEV / "实战" / "MyEA + Dashboard 接入报告.md",
        "size_target": 53.9 * 1024,
    },
}


# ---------- 反模式关键词 → 范本/速查映射 ----------
ANTIPATTERN_KEYWORDS = {
    "grid": ("grid_martin", "网格马丁"),
    "martin": ("grid_martin", "网格马丁"),
    "martingale": ("grid_martin", "马丁"),
    "no_sl": ("no_stop_loss", "无止损"),
    "scalp": ("scalper_risk", "剥头皮风险"),
    "overfit": ("overfit", "过拟合"),
    "magic": ("magic_number", "魔术号"),
    "single": ("single_symbol_risk", "单品种风险"),
    "leverage": ("leverage_high", "高杠杆"),
    "news": ("news_ignore", "忽略新闻"),
    "session": ("session_ignore", "忽略时段"),
}


def get_module_api(module_id: str) -> dict:
    """
    查 12 必读模块 API。**不**编，所有内容从 vault 读。
    返回 {name, path, exists, size, head (前 200 行), key_apis (从 head 提取)}
    """
    if module_id not in MODULES_12:
        raise KeyError(f"未知模块: {module_id}. 已知: {list(MODULES_12.keys())}")
    m = MODULES_12[module_id]
    p = m["path"]
    if not p.exists():
        return {
            "id": module_id, "name": m["name"], "path": str(p),
            "exists": False, "size": 0, "head": "", "key_apis": [],
            "error": f"vault 文件不存在: {p}",
        }
    size = p.stat().st_size
    head = p.read_text(encoding="utf-8", errors="ignore")
    # 提取 API 名称（粗略：找 `foo::bar` `foo.bar()` `foo(...)` 模式）
    api_pattern = re.compile(r"[A-Z]\w*::\w+|\b\w+\s*\([^)]*\)")
    apis = list(set(api_pattern.findall(head[:5000])))[:20]  # 最多 20 个
    return {
        "id": module_id,
        "name": m["name"],
        "path": str(p),
        "exists": True,
        "size": size,
        "head_preview": head[:3000],  # 头 3K
        "key_apis": apis,
        "full_content_avail": True,  # 真要看全文 read 即可
    }


def get_template(template_id: str) -> dict:
    """查 4 实物范本。**验真**：检查 size 是否接近预期（防止 vault 改了没发现）。"""
    if template_id not in TEMPLATES_4:
        raise KeyError(f"未知范本: {template_id}. 已知: {list(TEMPLATES_4.keys())}")
    t = TEMPLATES_4[template_id]
    p = t["path"]
    if not p.exists():
        return {
            "id": template_id, "name": t["name"], "path": str(p),
            "exists": False, "size": 0,
            "error": f"vault 文件不存在: {p}",
        }
    actual = p.stat().st_size
    expected = t["size_target"]
    drift = abs(actual - expected) / expected if expected else 0
    head = p.read_text(encoding="utf-8", errors="ignore")
    return {
        "id": template_id,
        "name": t["name"],
        "path": str(p),
        "exists": True,
        "size": actual,
        "size_target": expected,
        "size_drift": drift,
        "size_drift_ok": drift < 0.3,  # 30% 以内
        "head_preview": head[:3000],
    }


def get_antipattern(keyword: str) -> dict:
    """
    查反模式：先按关键词匹配 → 返回对应速查 wiki 路径。
    **不**给反模式内容（那是 vault 内的 wiki 自己写）。
    """
    k = keyword.lower().strip()
    for key, (ap_id, label) in ANTIPATTERN_KEYWORDS.items():
        if k == key or k in key or key in k:
            # 找匹配 wiki
            antipattern_dir = EA_DEV / "04-避坑与速查"
            if antipattern_dir.exists():
                # 找文件名含关键词的
                matches = list(antipattern_dir.rglob(f"*{label}*"))
                if not matches:
                    matches = list(antipattern_dir.rglob(f"*{key}*"))
                if matches:
                    return {
                        "keyword": keyword,
                        "antipattern_id": ap_id,
                        "label": label,
                        "wiki_path": str(matches[0]),
                        "wiki_exists": matches[0].exists(),
                    }
            return {
                "keyword": keyword, "antipattern_id": ap_id, "label": label,
                "wiki_path": None,
                "note": "vault 04-避坑与速查/ 下未找到对应 wiki",
            }
    return {"keyword": keyword, "error": f"未知反模式关键词: {keyword}",
            "known_keywords": list(ANTIPATTERN_KEYWORDS.keys())}


def get_moc() -> dict:
    """MOC 总入口 = EA 开发知识库.md"""
    p = EA_DEV / "EA 开发知识库.md"
    if not p.exists():
        return {"path": str(p), "exists": False, "error": "MOC 不存在"}
    content = p.read_text(encoding="utf-8", errors="ignore")
    # 提取 [[wiki 链向]] 数
    links = re.findall(r"\[\[([^\]]+)\]\]", content)
    return {
        "path": str(p),
        "exists": True,
        "size": p.stat().st_size,
        "wiki_link_count": len(links),
        "wiki_links_sample": links[:20],
        "head_preview": content[:2000],
    }


def get_5_step_method() -> dict:
    """5 步法 = 写 EA 必走流程 5 步法.md"""
    p = EA_DEV / "写 EA 必走流程 5 步法.md"
    if not p.exists():
        return {"path": str(p), "exists": False, "error": "5 步法文件不存在"}
    return {
        "path": str(p),
        "exists": True,
        "size": p.stat().st_size,
        "full_content_avail": True,
    }


# ---------- CLI 入口 ----------
if __name__ == "__main__":
    import json
    cmd = sys.argv[1] if len(sys.argv) > 1 else "moc"
    if cmd == "moc":
        print(json.dumps(get_moc(), ensure_ascii=False, indent=2)[:2000])
    elif cmd == "module":
        mid = sys.argv[2] if len(sys.argv) > 2 else "M08"
        r = get_module_api(mid)
        print(f"  name: {r.get('name')}")
        print(f"  path: {r.get('path')}")
        print(f"  size: {r.get('size')}B")
        print(f"  exists: {r.get('exists')}")
        print(f"  key_apis: {r.get('key_apis', [])[:10]}")
    elif cmd == "template":
        tid = sys.argv[2] if len(sys.argv) > 2 else "B_scalper_v1_v4"
        r = get_template(tid)
        print(f"  name: {r.get('name')}")
        print(f"  path: {r.get('path')}")
        print(f"  size: {r.get('size')}B (target {r.get('size_target', 0):.0f}B, drift {r.get('size_drift', 0):.1%})")
        print(f"  size_ok: {r.get('size_drift_ok')}")
    elif cmd == "antipattern":
        kw = sys.argv[2] if len(sys.argv) > 2 else "martin"
        r = get_antipattern(kw)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif cmd == "5step":
        r = get_5_step_method()
        print(f"  path: {r['path']}")
        print(f"  size: {r['size']}B")
    elif cmd == "list":
        print("=== 12 必读 ===")
        for k, v in MODULES_12.items():
            exists = "✓" if v["path"].exists() else "✗"
            print(f"  {exists} {k}: {v['name']}")
        print("=== 4 范本 ===")
        for k, v in TEMPLATES_4.items():
            exists = "✓" if v["path"].exists() else "✗"
            print(f"  {exists} {k}: {v['name']}")
    else:
        print(__doc__)
