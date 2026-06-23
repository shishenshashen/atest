"""Render W25 weekly PDF to PNG @ 2x, push to self-hosted server, verify URLs."""
import os
import sys
import json
import urllib.request
import urllib.error
import fitz  # PyMuPDF

PDF = r'C:\hermes-weekly-2026-W25-v2.pdf'
IMG_DIR_SERVER = r'C:\hermes-daily-2026-06-10-v2-images'
SERVER = 'http://127.0.0.1:18765'

# Clear old PNGs in server dir (preserve anything else)
for f in os.listdir(IMG_DIR_SERVER):
    if f.lower().endswith('.png'):
        os.remove(os.path.join(IMG_DIR_SERVER, f))
print(f'Cleared old PNGs from {IMG_DIR_SERVER}')

# Render @ 2x
doc = fitz.open(PDF)
zoom = 2.0
mat = fitz.Matrix(zoom, zoom)
pages = []
for i, page in enumerate(doc, 1):
    pix = page.get_pixmap(matrix=mat)
    out = os.path.join(IMG_DIR_SERVER, f'page-{i:02d}.png')
    pix.save(out)
    pages.append(out)
    print(f'  rendered page {i:02d} -> {out} ({pix.width}x{pix.height}, {os.path.getsize(out)} bytes)')
doc.close()
print(f'Rendered {len(pages)} pages into {IMG_DIR_SERVER}')

# Fetch token from server
try:
    resp = urllib.request.urlopen(f'{SERVER}/', timeout=10)
    data = json.loads(resp.read().decode('utf-8'))
    print('Server response:')
    print(json.dumps(data, indent=2, ensure_ascii=False))
    TOKEN = data['token']
    print(f'\nToken: {TOKEN}')
except Exception as e:
    print(f'Failed to fetch token: {e}', file=sys.stderr)
    sys.exit(1)

# Verify all page URLs accessible
print('\nVerifying image URLs:')
all_ok = True
for i in range(1, len(pages) + 1):
    url = f'{SERVER}/img/page-{i:02d}.png?token={TOKEN}'
    try:
        resp = urllib.request.urlopen(url, timeout=10)
        size = len(resp.read())
        print(f'  HTTP {resp.status} {size:>8d} bytes  {url}')
    except urllib.error.HTTPError as e:
        print(f'  HTTP {e.code} FAIL  {url}')
        all_ok = False
    except Exception as e:
        print(f'  ERR  {url} ({e})')
        all_ok = False

if not all_ok:
    print('\n!! Some URLs failed', file=sys.stderr)
    sys.exit(1)
print(f'\nAll {len(pages)} URLs OK')