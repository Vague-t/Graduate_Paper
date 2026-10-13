"""Read-only extraction of supplied thesis and existing manuscript render."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import pdfplumber

ROOT = Path('/Users/channtang/Downloads/paper')
OUT = Path(__file__).resolve().parent
inputs = {
    'reference': ROOT / '打印论文版本.pdf',
    'current': ROOT / '_revision_1007_v1/render_pass5/report_1007_v1_full.pdf',
}
for name, source in inputs.items():
    pages = []
    fonts = Counter()
    with pdfplumber.open(source) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text(x_tolerance=2, y_tolerance=3) or ''
            page_fonts = Counter((c['fontname'], round(c['size'], 2)) for c in page.chars)
            fonts.update(page_fonts)
            body = [c for c in page.chars if c['text'].strip() and 85 < c['top'] < 755]
            pages.append({
                'physical_page': i, 'text': text, 'width': page.width, 'height': page.height,
                'characters': len(text), 'images': len(page.images),
                'fonts': [{'font': k[0], 'size': k[1], 'characters': v} for k,v in page_fonts.most_common(8)],
                'body_bbox': [round(min(c['x0'] for c in body), 2), round(min(c['top'] for c in body), 2),
                              round(max(c['x1'] for c in body), 2), round(max(c['bottom'] for c in body), 2)] if body else None,
            })
    (OUT / f'{name}_pages.json').write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / f'{name}_text.txt').write_text('\n\n'.join(f"===== PHYSICAL PAGE {p['physical_page']} =====\n{p['text']}" for p in pages), encoding='utf-8')
    metadata = {
        'source': str(source), 'sha256': sha256(source.read_bytes()).hexdigest(), 'pages': len(pages),
        'fonts': [{'font': k[0], 'size': k[1], 'characters': v} for k,v in fonts.most_common(30)],
        'text_characters': sum(p['characters'] for p in pages),
    }
    (OUT / f'{name}_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(name, len(pages), metadata['text_characters'], flush=True)
