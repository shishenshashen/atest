"""格式 + 编码效率对比实验.
对同一张测试图, 输出 PNG/JPEG/AVIF/HEIC/WebP 的体积, 给老大拍.
"""
import os
from PIL import Image
from pillow_heif import register_heif_opener
register_heif_opener()

# 准备一张"高信息密度"的测试图（模拟日报: 大块色 + 文字 + 边）
img = Image.new('RGB', (1600, 1200), '#fafbfc')
# 模拟线性 banner + 卡片
from PIL import ImageDraw, ImageFont
draw = ImageDraw.Draw(img)
draw.rectangle([(0, 0), (1600, 200)], fill='#0f172a')
draw.rectangle([(0, 220), (1600, 600)], fill='#e6e8eb')
draw.rectangle([(0, 620), (1600, 1100)], fill='#a5b4fc')
draw.text((40, 60), "2026-06-15 Daily Digest (TEST)", fill='white')
draw.text((40, 250), "P0 / P1 / P2 task rows", fill='#1a1a1a')
draw.text((40, 660), "All metrics", fill='#1a1a1a')

formats = [
    ('PNG',  {'compress_level': 9}, None),
    ('JPEG', {'quality': 85}, None),
    ('JPEG', {'quality': 75}, None),
    ('WEBP', {'quality': 80, 'method': 6}, None),
    ('AVIF', {'quality': 80}, None),
    ('HEIC', {'quality': 80}, 'pillow_heif'),
]

print(f"{'format':10s} {'size':>9s} {'ratio':>6s}")
print('-' * 35)
png_size = None
for name, kwargs, _ in formats:
    p = f'/tmp/digest_test.{name.lower()}'
    img.save(p, **kwargs)
    size = os.path.getsize(p)
    if name == 'PNG':
        png_size = size
        ratio_str = '1.00x (基准)'
    else:
        ratio_str = f'{size/png_size:.2f}x'
    print(f'{name:10s} {size:>9d} {ratio_str:>10s}')

print(f'\nimg size: {img.size[0]}x{img.size[1]}')
print('HEIC: iOS/macOS 原生支持; Android 11+ 支持; Web 浏览器暂不支持（GitHub raw 直接展示 OK，浏览器点击会下载）')
print('AVIF: Web 主流；iOS 17+ 支持；体积与 HEIC 接近')
print('WEBP: Web 主流；体积小 30-50%')
