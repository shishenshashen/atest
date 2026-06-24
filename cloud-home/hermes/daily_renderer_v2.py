"""daily-digest skill · renderer v2 (Linear-style)
Cover page (dark banner + big date + stat row) + TOC + Linear-styled sections.
Chinese font: Microsoft YaHei (msyh.ttc, GB18030).
"""
import os
import re
import sys
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable

# Prefer Windows Microsoft YaHei (msyh.ttc) - covers GB18030, modern symbols
try:
    msyh_path = r'C:\Windows\Fonts\msyh.ttc'
    if os.path.exists(msyh_path):
        pdfmetrics.registerFont(TTFont('Body', msyh_path, subfontIndex=0))
        pdfmetrics.registerFont(TTFont('Body-Bold', msyh_path, subfontIndex=1))
        _FONT = 'Body'
        _FONT_BOLD = 'Body-Bold'
    else:
        raise FileNotFoundError('msyh.ttc not found')
except Exception as _e:
    print(f'[warn] YaHei not available ({_e}), falling back to STSong-Light', file=sys.stderr)
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    _FONT = 'STSong-Light'
    _FONT_BOLD = 'STSong-Light'

# Linear-style palette
COL_BG_DARK = colors.HexColor('#0f172a')
COL_ACCENT = colors.HexColor('#5e6ad2')
COL_ACCENT_LIGHT = colors.HexColor('#a5b4fc')
COL_TEXT = colors.HexColor('#1a1a1a')
COL_TEXT_MUTED = colors.HexColor('#8a8f98')
COL_TEXT_SUBTLE = colors.HexColor('#3a3f4a')
COL_DIVIDER = colors.HexColor('#e6e8eb')
COL_CODE_BG = colors.HexColor('#f6f8fa')
COL_TABLE_HEADER_BG = colors.HexColor('#0f172a')
COL_TABLE_HEADER_TEXT = colors.white
COL_BULLET = colors.HexColor('#5e6ad2')


# ====================================================================
# Section parser (from v1)
# ====================================================================

def parse_md_sections(md_text):
    sections = []
    lines = md_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            sections.append(("blank", ""))
            i += 1
            continue
        if line.startswith("---"):
            sections.append(("hr", None))
            i += 1
            continue
        if line.startswith("# "):
            sections.append(("h1", line[2:].strip()))
        elif line.startswith("## "):
            sections.append(("h2", line[3:].strip()))
        elif line.startswith("### "):
            sections.append(("h3", line[4:].strip()))
        elif line.startswith("- ") or line.startswith("* "):
            sections.append(("bullet", line[2:].strip()))
        elif re.match(r"^\d+\.\s", line):
            sections.append(("number", re.sub(r"^\d+\.\s+", "", line)))
        elif line.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            sections.append(("code", "\n".join(code)))
        elif "|" in line and i + 1 < len(lines) and re.match(r"^\|?[\s\-|:]+\|?$", lines[i+1]):
            header = [c.strip() for c in line.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and "|" in lines[i]:
                row = [c.strip() for c in lines[i].strip("|").split("|")]
                rows.append(row)
                i += 1
            sections.append(("table", (header, rows)))
            continue
        else:
            sections.append(("text", line))
        i += 1
    return sections


def html_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ====================================================================
# Style factories
# ====================================================================

def _style_h1():
    return ParagraphStyle('H1', fontName=_FONT_BOLD, fontSize=22,
                          textColor=COL_TEXT,
                          spaceBefore=4, spaceAfter=10, leading=26)


def _style_h2():
    return ParagraphStyle('H2', fontName=_FONT_BOLD, fontSize=15,
                          textColor=COL_ACCENT,
                          spaceBefore=14, spaceAfter=6, leading=20)


def _style_h3():
    return ParagraphStyle('H3', fontName=_FONT_BOLD, fontSize=12,
                          textColor=COL_TEXT_SUBTLE,
                          spaceBefore=10, spaceAfter=3, leading=16)


def _style_text():
    return ParagraphStyle('Body', fontName=_FONT, fontSize=10,
                          textColor=COL_TEXT, leading=15, spaceAfter=4)


def _style_bullet():
    return ParagraphStyle('Bullet', fontName=_FONT, fontSize=10,
                          textColor=COL_TEXT, leading=15,
                          leftIndent=20, bulletIndent=6, spaceAfter=3)


def _style_quote():
    return ParagraphStyle('Quote', fontName=_FONT, fontSize=10,
                          textColor=COL_TEXT_SUBTLE, leading=15,
                          leftIndent=12, rightIndent=12,
                          borderColor=COL_ACCENT, borderWidth=0,
                          borderPadding=8, spaceAfter=8,
                          backColor=colors.HexColor('#f8f9fc'))


def _style_code():
    return ParagraphStyle('Code', fontName=_FONT, fontSize=8,
                          textColor=COL_TEXT, leading=11,
                          backColor=COL_CODE_BG,
                          leftIndent=8, rightIndent=8,
                          borderColor=COL_DIVIDER,
                          borderWidth=0.5, borderPadding=6,
                          spaceAfter=0)


def _style_sub():
    return ParagraphStyle('sub', fontName=_FONT, fontSize=8,
                          textColor=COL_TEXT_MUTED, leading=10)


# ====================================================================
# Visual blocks
# ====================================================================

def _stat_box(value, label, color=None):
    """Linear-style stat card: large number, small label."""
    c = color or COL_ACCENT
    style_val = ParagraphStyle('statval', fontName=_FONT_BOLD, fontSize=26,
                               textColor=c, alignment=0, leading=28)
    style_lbl = ParagraphStyle('statlbl', fontName=_FONT, fontSize=7.5,
                               textColor=COL_TEXT_MUTED, alignment=0,
                               leading=10, spaceBefore=2)
    t = Table([[Paragraph(str(value), style_val)],
               [Paragraph(label, style_lbl)]],
              colWidths=[4.0*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafbfc')),
        ('BOX', (0, 0), (-1, -1), 0.5, COL_DIVIDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def _cover_block(date_str, weekday, title, subtitle, stats):
    """Linear-style cover page: dark gradient banner + big date + stat row."""
    flow = []
    # Dark banner
    style_lbl = ParagraphStyle('cover_lbl', fontName=_FONT_BOLD, fontSize=8,
                               textColor=COL_ACCENT_LIGHT, alignment=1, leading=12)
    banner = Table([[Paragraph('DAILY DIGEST', style_lbl)]],
                   colWidths=[17*cm], rowHeights=[3.0*cm])
    banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COL_BG_DARK),
        ('LINEBELOW', (0, 0), (-1, 0), 4, COL_ACCENT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    flow.append(banner)
    flow.append(Spacer(1, 1.4*cm))
    # Big date
    style_big = ParagraphStyle('big', fontName=_FONT_BOLD, fontSize=44,
                               textColor=COL_BG_DARK, leading=48,
                               alignment=0, spaceAfter=4)
    flow.append(Paragraph('%s · %s' % (date_str, weekday), style_big))
    # Title
    style_title = ParagraphStyle('ttl', fontName=_FONT_BOLD, fontSize=22,
                                 textColor=COL_TEXT, leading=26,
                                 spaceBefore=4, spaceAfter=8)
    flow.append(Paragraph(html_escape(title), style_title))
    # Subtitle
    style_sub2 = ParagraphStyle('sb2', fontName=_FONT, fontSize=11,
                                textColor=COL_TEXT_MUTED, leading=15,
                                spaceAfter=20)
    flow.append(Paragraph(html_escape(subtitle), style_sub2))
    # Stat row
    if stats:
        n = len(stats)
        avail = 17*cm
        col = avail / n
        stat_row = Table([[_stat_box(v, l, color=c) for v, l, c in stats]],
                         colWidths=[col] * n)
        stat_row.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        flow.append(stat_row)
    flow.append(Spacer(1, 1.5*cm))
    # Footer accent
    flow.append(HRFlowable(width='30%', thickness=2,
                           color=COL_ACCENT, hAlign='LEFT'))
    flow.append(Spacer(1, 0.2*cm))
    flow.append(Paragraph('由 AI (小神龙) 自动生成 · ' +
                          datetime.now().strftime('%Y-%m-%d %H:%M'),
                          _style_sub()))
    flow.append(PageBreak())
    return flow


def _toc_block(sections):
    """Linear-style TOC: numbered h1, dotted h2 indented."""
    flow = []
    flow.append(Paragraph('目录', _style_h1()))
    flow.append(Paragraph('CONTENTS', _style_sub()))
    flow.append(Spacer(1, 0.4*cm))
    items = [(t, c) for t, c in sections if t in ('h1', 'h2') and c]
    style_item = ParagraphStyle('toc1', fontName=_FONT_BOLD, fontSize=11,
                                textColor=COL_TEXT, leading=22)
    style_item_sub = ParagraphStyle('toc2', fontName=_FONT, fontSize=10,
                                    textColor=COL_TEXT_MUTED,
                                    leading=16, leftIndent=24)
    for i, (typ, content) in enumerate(items, 1):
        if typ == 'h1':
            flow.append(Paragraph('%02d &nbsp;&nbsp;%s' % (i, html_escape(content)),
                                  style_item))
        else:
            flow.append(Paragraph('· &nbsp;&nbsp;%s' % html_escape(content),
                                  style_item_sub))
    flow.append(Spacer(1, 0.4*cm))
    flow.append(HRFlowable(width='100%', thickness=0.5, color=COL_DIVIDER))
    flow.append(PageBreak())
    return flow


def _h2_header(text):
    """Section header with accent number prefix."""
    style_num = ParagraphStyle('h2n', fontName=_FONT_BOLD, fontSize=10,
                               textColor=COL_ACCENT_LIGHT, leading=14,
                               backColor=COL_BG_DARK, leftIndent=8, rightIndent=8)
    style_txt = ParagraphStyle('h2t', fontName=_FONT_BOLD, fontSize=15,
                               textColor=COL_BG_DARK, leading=20, leftIndent=0)
    return [Paragraph('§', style_num), Paragraph(html_escape(text), style_txt)]


def _render_ascii_bar(line):
    """ASCII progress bar → colored progress bar Table row.
    Example: 'AI 记忆  ████ 80%   ⭐ NEW'
    """
    if '█' not in line and '▏' not in line and '░' not in line:
        return None
    m = re.match(r'^(.+?)([█▏░▎ ]+)(.*)$', line)
    if not m:
        return None
    label, bar, val = m.group(1).strip(), m.group(2), m.group(3).strip()
    fill = bar.count('█') + bar.count('▏') * 0.5
    empty = bar.count('░') + bar.count(' ') + bar.count('▎') * 0.5
    total = max(1.0, fill + empty)
    pct = fill / total
    # Label cell
    style_lbl = ParagraphStyle('blbl', fontName=_FONT, fontSize=9,
                               textColor=COL_TEXT, leading=12)
    # Bar cell (visual progress)
    bar_data = [['', '']]
    bar_tbl = Table(bar_data, colWidths=[pct * 8*cm, (1 - pct) * 8*cm],
                    rowHeights=[0.4*cm])
    bar_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), COL_ACCENT),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#eef0f4')),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    # Value cell
    style_val = ParagraphStyle('bval', fontName=_FONT_BOLD, fontSize=9,
                               textColor=COL_ACCENT, alignment=2, leading=12)
    outer = Table([[Paragraph(html_escape(label), style_lbl),
                    bar_tbl,
                    Paragraph(html_escape(val), style_val)]],
                  colWidths=[4.0*cm, 8.5*cm, 3.5*cm])
    outer.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return outer


# ====================================================================
# Main build
# ====================================================================

def _extract_meta(md_text):
    """Parse YAML frontmatter → dict (best-effort)."""
    meta = {}
    if not md_text.startswith('---'):
        return meta
    parts = md_text.split('---', 2)
    if len(parts) < 3:
        return meta
    fm = parts[1].strip()
    for line in fm.split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            meta[k.strip()] = v.strip()
    return meta


def _parse_stats(md_text):
    """Extract stat box data from known patterns:
    - '**8 sessions**, **50 user msgs / 424 assistant / 403 tool calls**'
    - '广度 4 → 8（+100%）'
    """
    stats = []
    m = re.search(r'\*\*(\d+)\s+sessions?\*\*', md_text)
    if m:
        stats.append((m.group(1), 'SESSIONS', colors.HexColor('#5e6ad2')))
    m = re.search(r'\*\*(\d+)\s+user\s+msgs?\s*/\s*(\d+)\s+assistant', md_text)
    if m:
        stats.append((m.group(1) + 'u', 'USER MSGS', colors.HexColor('#22c55e')))
        stats.append((m.group(2), 'ASSISTANT', colors.HexColor('#0ea5e9')))
    m = re.search(r'(\d+)\s+tool\s+calls', md_text)
    if m:
        stats.append((m.group(1), 'TOOL CALLS', colors.HexColor('#f59e0b')))
    return stats[:4]  # max 4 to fit A4


def _weekday_zh(d_str):
    try:
        d = datetime.strptime(d_str, '%Y-%m-%d')
        names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        return names[d.weekday()]
    except Exception:
        return ''


def build_pdf(md_text, output_path, title=None):
    meta = _extract_meta(md_text)
    date_str = meta.get('date', datetime.now().strftime('%Y-%m-%d'))
    weekday = _weekday_zh(date_str)
    title_use = title or meta.get('title', 'Daily Digest')
    subtitle = meta.get('mood', 'AI 自动生成每日总结')
    stats = _parse_stats(md_text)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.6*cm, rightMargin=1.6*cm,
        topMargin=1.6*cm, bottomMargin=1.6*cm,
    )

    sections = parse_md_sections(md_text)

    flow = []
    # 1. Cover
    flow.extend(_cover_block(date_str, weekday, title_use, subtitle, stats))
    # 2. TOC
    flow.extend(_toc_block(sections))

    # 3. Body
    h2_index = 0
    skip_until_h2 = False
    in_code = False
    code_buf = []

    def flush_code():
        if not code_buf:
            return []
        # Try to render as ASCII bar chart
        bars = []
        other_lines = []
        for ln in code_buf:
            bar = _render_ascii_bar(ln)
            if bar is not None:
                bars.append(bar)
            else:
                other_lines.append(ln)
        out = []
        if bars:
            for b in bars:
                out.append(b)
        if other_lines:
            joined = '\n'.join(other_lines)
            for ln in joined.split('\n'):
                if ln.strip():
                    out.append(Paragraph(html_escape(ln) or '&nbsp;', _style_code()))
        code_buf.clear()
        return out

    for typ, content in sections:
        if typ == 'blank':
            continue
        if typ == 'hr':
            flow.append(Spacer(1, 0.2*cm))
            flow.append(HRFlowable(width='100%', thickness=0.5,
                                   color=COL_DIVIDER, spaceBefore=4, spaceAfter=4))
            continue
        if typ == 'h1':
            # skip h1 in body (already in cover)
            continue
        if typ == 'h2':
            flow.extend(flush_code())
            in_code = False
            h2_index += 1
            # Section number + title (small accent block)
            flow.append(Spacer(1, 0.3*cm))
            style_num = ParagraphStyle('sn', fontName=_FONT_BOLD, fontSize=8,
                                       textColor=COL_ACCENT, leading=10)
            flow.append(Paragraph('%02d' % h2_index, style_num))
            flow.append(Paragraph(html_escape(content), _style_h2()))
            flow.append(HRFlowable(width='40%', thickness=1.2,
                                   color=COL_ACCENT, hAlign='LEFT',
                                   spaceBefore=0, spaceAfter=8))
            continue
        if typ == 'h3':
            flow.append(Paragraph(html_escape(content), _style_h3()))
            continue
        if typ == 'text':
            if not content:
                continue
            if content.startswith('> '):
                flow.append(Paragraph(html_escape(content[2:]), _style_quote()))
            else:
                flow.append(Paragraph(html_escape(content), _style_text()))
            continue
        if typ in ('bullet', 'number'):
            prefix = '•' if typ == 'bullet' else '%d.'  # noqa
            if typ == 'number':
                # try to preserve original number
                num_m = re.match(r'^(\d+)\.', content)
                prefix = '%d.' if num_m else '•'
            text = content
            # Highlight **bold** to <b>
            text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'`([^`]+)`', r'<font name="%s" size="9" color="#5e6ad2">\1</font>' % _FONT, text)
            flow.append(Paragraph(prefix + ' &nbsp;&nbsp;' + html_escape(text).replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>'),
                                  _style_bullet()))
            continue
        if typ == 'code':
            in_code = True
            code_buf.append(content)
            continue
        if typ == 'table':
            header, rows = content
            data = [header] + rows
            n_cols = len(header)
            col_w = 16*cm / n_cols
            t = Table(data, colWidths=[col_w] * n_cols)
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), _FONT),
                ('FONTNAME', (0, 0), (-1, 0), _FONT_BOLD),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), COL_TABLE_HEADER_BG),
                ('TEXTCOLOR', (0, 0), (-1, 0), COL_TABLE_HEADER_TEXT),
                ('TEXTCOLOR', (0, 1), (-1, -1), COL_TEXT),
                ('LINEBELOW', (0, 0), (-1, 0), 1.5, COL_ACCENT),
                ('LINEABOVE', (0, 1), (-1, 1), 0.5, COL_DIVIDER),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [colors.white, colors.HexColor('#fafbfc')]),
            ]))
            flow.append(t)
            flow.append(Spacer(1, 0.3*cm))
            continue
    flow.extend(flush_code())

    # Footer with page numbers
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont(_FONT, 7)
        canvas.setFillColor(COL_TEXT_MUTED)
        canvas.drawString(1.6*cm, 1*cm, '%s · %s' % (date_str, title_use[:30]))
        canvas.drawRightString(A4[0] - 1.6*cm, 1*cm, '第 %d 页' % doc.page)
        canvas.restoreState()

    doc.build(flow, onFirstPage=on_page, onLaterPages=on_page)
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python daily_renderer.py <md_file> <pdf_output> [title]")
        sys.exit(1)
    md_path = sys.argv[1]
    pdf_path = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else None
    with open(md_path, "r", encoding="utf-8") as f:
        md = f.read()
    out = build_pdf(md, pdf_path, title=title)
    size = os.path.getsize(out)
    print("PDF generated: %s (%d bytes, %.1f KB)" % (out, size, size/1024.0))
