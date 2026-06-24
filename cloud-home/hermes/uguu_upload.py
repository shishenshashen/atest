"""Upload image to uguu.se via anonymous multipart. Returns URL or raises."""
import sys, os, json
import urllib.request
import urllib.parse

UGUU_URL = 'https://uguu.se/upload'

def upload(path, timeout=30):
    with open(path, 'rb') as f:
        data = f.read()
    boundary = '----hermes20260615'
    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="files[]"; filename="{os.path.basename(path)}"\r\n'
        f'Content-Type: image/png\r\n\r\n'
    ).encode('utf-8') + data + f'\r\n--{boundary}--\r\n'.encode('utf-8')
    req = urllib.request.Request(
        UGUU_URL,
        data=body,
        headers={
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'User-Agent': 'Mozilla/5.0 (hermes-agent)',
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode('utf-8', errors='ignore').strip()
    # uguu returns JSON {"success":true,"files":[{"url":"...","name":"..."}]}
    try:
        j = json.loads(raw)
        if j.get('success') and j.get('files'):
            return j['files'][0]['url']
        # fallback: plain text URL
        if raw.startswith('http'):
            return raw
        raise RuntimeError(f"uguu.se unexpected response: {raw[:200]}")
    except json.JSONDecodeError:
        if raw.startswith('http'):
            return raw
        raise RuntimeError(f"uguu.se non-JSON: {raw[:200]}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: uguu_upload.py <file> [more files...]")
        sys.exit(1)
    out = {}
    for path in sys.argv[1:]:
        try:
            url = upload(path)
            out[path] = {'url': url, 'size': os.path.getsize(path)}
            print(f"OK {path} -> {url}")
        except Exception as e:
            out[path] = {'error': str(e)}
            print(f"FAIL {path}: {e}")
    print(json.dumps(out, ensure_ascii=False, indent=2))
