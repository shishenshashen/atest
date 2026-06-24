"""Daily digest v3 - 1 张图, 高密度, 简洁风格 (借 daily-digest skill 模板 + ASCII 进度条).
不再走 PDF 路线, 直接 markdown -> HTML -> PNG (用 Playwright/Selenium-like 拍图, 或用 Pillow 绘).
本版用 Pillow (稳定, 离线, 老大 8 个必装依赖之一).
"""
import sys, json, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pillow_heif import register_heif_opener
register_heif_opener()


# 字体
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT_PATH_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_FAMILY_BODY = "msyh"
FONT_FAMILY_BOLD = "msyhbd"

# 颜色 (借 daily-digest skill 的 莫兰迪 + 米白, 不要 Linear 深紫)
COL_BG = (250, 248, 245)       # 米白底 (warm)
COL_BG_CARD = (255, 255, 255)  # 白卡片
COL_TEXT = (38, 38, 38)
COL_TEXT_MUTED = (130, 130, 130)
COL_TEXT_SUBTLE = (175, 175, 175)
COL_ACCENT = (217, 119, 87)    # 暖橙 (温和, 不是 Linear 紫)
COL_ACCENT_BG = (252, 232, 220)
COL_OK = (106, 153, 78)
COL_WARN = (217, 119, 87)
COL_BAD = (192, 57, 43)
COL_DIVIDER = (225, 220, 213)
COL_BAR_BG = (235, 228, 220)
COL_BAR_FG = (217, 119, 87)


def get_font(size, bold=False):
    path = FONT_PATH_BOLD if bold else FONT_PATH
    if not Path(path).exists():
        path = FONT_PATH
    return ImageFont.truetype(path, size)


def wrap_text(draw, text, font, max_width):
    """简易 wrap, 中文按字符宽度算."""
    out = []
    line = ""
    for ch in text:
        test = line + ch
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and line:
            out.append(line)
            line = ch
        else:
            line = test
    if line:
        out.append(line)
    return out


def draw_bar(draw, x, y, w, h, value, max_val, color):
    """画进度条 0-100."""
    draw.rectangle([x, y, x + w, y + h], fill=COL_BAR_BG, outline=None)
    if max_val > 0:
        fw = int(w * min(value, max_val) / max_val)
        if fw > 0:
            draw.rectangle([x, y, x + fw, y + h], fill=color, outline=None)


def parse_digest_md(md_text):
    """借 daily-digest 模板的 10 段, 解析 markdown."""
    sections = []
    current = None
    for line in md_text.split('\n'):
        line = line.rstrip()
        if line.startswith('# '):
            sections.append({'type': 'title', 'content': line[2:].strip()})
            current = None
        elif line.startswith('## '):
            current = {'type': 'h2', 'title': line[3:].strip(), 'items': []}
            sections.append(current)
        elif line.startswith('### '):
            if current is None:
                current = {'type': 'h2', 'title': '', 'items': []}
                sections.append(current)
            current = {'type': 'h3', 'title': line[4:].strip(), 'parent': current}
            sections.append(current)
        elif line.startswith('- '):
            target = current if current else {'type': 'list', 'items': []}
            if 'items' not in target:
                target['items'] = []
            target['items'].append(line[2:].strip())
            if target not in sections:
                sections.append(target)
        elif line.startswith('---'):
            sections.append({'type': 'hr'})
        elif line.strip() == '':
            continue
        else:
            if current and 'content' not in current:
                current['content'] = line
    return sections


def render_digest_png(date_str, sections, out_path, width=1600, ratio=0.7):
    """1 张图渲染所有 sections."""
    height = int(width * ratio)  # 1120 默认
    img = Image.new('RGB', (width, height), COL_BG)
    draw = ImageDraw.Draw(img)

    f_h1 = get_font(38, bold=True)
    f_h2 = get_font(22, bold=True)
    f_h3 = get_font(17, bold=True)
    f_body = get_font(15)
    f_meta = get_font(13)
    f_emoji = get_font(22)

    # 顶部: 标题 + 日期
    y = 36
    title = next((s['content'] for s in sections if s['type']=='title'), f"Daily Digest · {date_str}")
    draw.text((48, y), title, font=f_h1, fill=COL_TEXT)
    y += 60
    draw.text((48, y), date_str, font=f_meta, fill=COL_TEXT_MUTED)
    # 顶部右侧: 计数 (P0/P1/P2 done/total)
    counters = {'P0': [0,0], 'P1': [0,0], 'P2': [0,0]}
    for s in sections:
        if s['type'] == 'h2' and s.get('title', '').startswith('P'):
            p = s['title'].split(' ')[0]
            if p in counters:
                counters[p][0] = sum(1 for i in s.get('items', []) if i.startswith('✅'))
                counters[p][1] = len(s.get('items', []))
    cx = width - 48
    for p, (done, total) in reversed(list(counters.items())):
        txt = f"{p}  {done}/{total}"
        bbox = draw.textbbox((0, 0), txt, font=f_h3)
        w = bbox[2] - bbox[0]
        draw.text((cx - w, 36), txt, font=f_h3, fill=COL_OK if done==total and total>0 else COL_TEXT_MUTED)
        cx -= w + 24
    y += 28
    draw.line([(48, y), (width-48, y)], fill=COL_DIVIDER, width=1)
    y += 18

    # 主体: sections
    col_w = (width - 48 * 2 - 24) // 2  # 双栏
    left_x = 48
    right_x = left_x + col_w + 24
    col_y = {left_x: y, right_x: y}
    col_h = height - y - 48

    for s in sections:
        if s['type'] == 'title':
            continue
        # 选矮的一列
        x = left_x if col_y[left_x] <= col_y[right_x] else right_x
        y0 = col_y[x]

        # 高度预估
        h = 0
        if s['type'] == 'h2':
            h += 38
        elif s['type'] == 'h3':
            h += 28
        elif s['type'] == 'hr':
            h += 16
        elif s['type'] == 'list':
            for item in s.get('items', []):
                wrapped = wrap_text(draw, '• ' + item, f_body, col_w - 16)
                h += 18 * len(wrapped) + 4
            h += 8
        if y0 + h > height - 48:
            continue  # 放不下就跳过 (应该不会)

        if s['type'] == 'h2':
            draw.text((x, y0), s['title'], font=f_h2, fill=COL_TEXT)
            col_y[x] = y0 + 38
        elif s['type'] == 'h3':
            draw.text((x, y0), s['title'], font=f_h3, fill=COL_ACCENT)
            col_y[x] = y0 + 26
        elif s['type'] == 'list':
            cy = y0
            for item in s.get('items', []):
                wrapped = wrap_text(draw, '• ' + item, f_body, col_w - 16)
                for w in wrapped:
                    color = COL_OK if item.startswith('✅') else (COL_TEXT if not item.startswith('❌') else COL_BAD)
                    draw.text((x, cy), w, font=f_body, fill=color)
                    cy += 18
                cy += 4
            col_y[x] = cy + 8
        elif s['type'] == 'hr':
            draw.line([(x, y0 + 8), (x + col_w, y0 + 8)], fill=COL_DIVIDER, width=1)
            col_y[x] = y0 + 16

    # 底栏: 小字 footer
    draw.text((48, height - 36), f"Generated by 小神龙 · {date_str} · 1-page summary",
              font=f_meta, fill=COL_TEXT_SUBTLE)
    img.save(out_path, 'PNG', optimize=True)
    return out_path


def to_webp(png_path, webp_path, quality=80):
    img = Image.open(png_path)
    img.save(webp_path, 'WEBP', quality=quality, method=6)
    return webp_path


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: render_digest_v3.py <md_file> <png_out> [webp_out] [width]")
        sys.exit(1)
    md_path = Path(sys.argv[1])
    png_out = Path(sys.argv[2])
    webp_out = Path(sys.argv[3]) if len(sys.argv) > 3 else png_out.with_suffix('.webp')
    width = int(sys.argv[4]) if len(sys.argv) > 4 else 1600
    md_text = md_path.read_text(encoding='utf-8')
    sections = parse_digest_md(md_text)
    date_str = md_path.parent.name
    render_digest_png(date_str, sections, png_out, width=width)
    to_webp(png_out, webp_out, quality=82)
    print(f"PNG:  {png_out}  ({png_out.stat().st_size} B)")
    print(f"WEBP: {webp_out}  ({webp_out.stat().st_size} B)")
