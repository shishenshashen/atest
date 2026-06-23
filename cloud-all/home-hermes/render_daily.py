"""Render PDF pages to PNG @ 2x, copy to image dir, refresh token."""
import os, sys, shutil, urllib.request, json
import fitz  # PyMuPDF

PDF = r'C:\ai\obsidian-文件\ai-managed\20-经验沉淀\2026-06\Daily\_pdf\2026-06-12.pdf'
IMG_DIR_LOCAL = r'C:\hermes-daily-2026-06-12-images'
IMG_DIR_SERVER = r'C:\hermes-daily-2026-06-10-v2-images'  # server is serving this dir
SERVER = 'http://127.0.0.1:18765'

os.makedirs(IMG_DIR_LOCAL, exist_ok=True)

# Render @ 2x
doc = fitz.open(PDF)
zoom = 2.0
mat = fitz.Matrix(zoom, zoom)
pages = []
for i, page in enumerate(doc, 1):
    pix = page.get_pixmap(matrix=mat)
    out = os.path.join(IMG_DIR_LOCAL, f'page-{i:02d}.png')
    pix.save(out)
    pages.append(out)
    print(f'  rendered {out} ({pix.width}x{pix.height})')
doc.close()
print(f'Rendered {len(pages)} pages @ 2x into {IMG_DIR_LOCAL}')

# Copy to server dir
for p in pages:
    shutil.copy2(p, os.path.join(IMG_DIR_SERVER, os.path.basename(p)))
print(f'Copied to server dir: {IMG_DIR_SERVER}')

# Refresh token
req = urllib.request.Request(f'{SERVER}/refresh', method='POST')
try:
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read().decode('utf-8'))
    print('Server refresh response:')
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f'Refresh failed: {e}', file=sys.stderr)
    # fallback: GET root
    resp = urllib.request.urlopen(f'{SERVER}/', timeout=10)
    data = json.loads(resp.read().decode('utf-8'))
    print('Server root response:')
    print(json.dumps(data, indent=2, ensure_ascii=False))
