"""Trace final page images to pages already visually inspected in this turn."""
from pathlib import Path
from PIL import Image
from pypdf import PdfReader
import hashlib
import json

WORK = Path(__file__).resolve().parent
FINAL = WORK / 'render_deliver'
rows = []
for n in range(1, 55):
    ref_dir = 'render_layout2' if n in (23, 24) else 'render_final'
    ref_n = n + 1 if n >= 25 else n
    final_path = FINAL / f'page-{n}.png'
    reference_path = WORK / ref_dir / f'page-{ref_n}.png'
    with Image.open(final_path) as a, Image.open(reference_path) as b:
        same = a.size == b.size and a.tobytes() == b.tobytes()
        # The chapter-end spill page was removed. Test all pixels above the
        # footer separately; the footer values are checked from PDF below.
        crop = (0, 0, a.width, int(a.height * 0.93))
        same_body = a.size == b.size and a.crop(crop).tobytes() == b.crop(crop).tobytes()
    rows.append({'final_page': n, 'reference_render': ref_dir, 'reference_page': ref_n,
                 'identical_full_page': same, 'identical_above_footer': same_body,
                 'png_sha256': hashlib.sha256(final_path.read_bytes()).hexdigest()})
pdf = PdfReader(FINAL / 'report_0914_v3.pdf')
assert len(pdf.pages) == 54
footers = []
for n, page in enumerate(pdf.pages, 1):
    if n < 6:
        continue
    footer_parts = []
    def collect_footer(text, cm, tm, font, size):
        if text.strip() and 20 < tm[5] < 60:
            footer_parts.append(text.strip())
    page.extract_text(visitor_text=collect_footer)
    assert footer_parts == [str(n - 5)], (n, footer_parts)
    footers.append({'physical_page': n, 'logical_page': n - 5})
print(json.dumps({'pages': rows, 'footers': footers,
                  'needs_visual_review': [r['final_page'] for r in rows if not r['identical_above_footer']]},
                 ensure_ascii=False, indent=2))
