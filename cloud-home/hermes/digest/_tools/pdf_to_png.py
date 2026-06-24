"""PDF -> PNG. PyMuPDF, 1.5x zoom for WeChat readability."""
import sys, os
import fitz  # PyMuPDF

if len(sys.argv) < 3:
    print("Usage: pdf_to_png.py <pdf> <png_out>")
    sys.exit(1)

pdf_path = sys.argv[1]
png_out = sys.argv[2]
zoom = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5

doc = fitz.open(pdf_path)
print(f"PDF pages: {len(doc)}")
mat = fitz.Matrix(zoom, zoom)
# Render all pages, save each as png_NN.png
base, ext = os.path.splitext(png_out)
out_files = []
for i, page in enumerate(doc):
    pix = page.get_pixmap(matrix=mat, alpha=False)
    out_name = f"{base}_p{i+1:02d}.png"
    pix.save(out_name)
    out_files.append((out_name, os.path.getsize(out_name)))
    print(f"  page {i+1}: {out_name} ({out_files[-1][1]/1024:.1f} KB)")
doc.close()
print(f"Done. {len(out_files)} pages rendered.")
