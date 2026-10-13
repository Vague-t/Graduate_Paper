"""Verify the narrow edit against the previously fully reviewed render."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

from lxml import etree
from PIL import Image, ImageChops
import pdfplumber

WORK = Path(__file__).resolve().parent
BASE = WORK.parent
ROOT = BASE.parent
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'}


def norm(text):
    return re.sub(r'[\s$`*]+', '', text).replace('（', '(').replace('）', ')')


def main():
    before = WORK / 'before/report_1008_v3_full.docx'
    current = ROOT / 'report_1008_v3_full.docx'
    with zipfile.ZipFile(before) as z:
        old = etree.fromstring(z.read('word/document.xml'))
    with zipfile.ZipFile(current) as z:
        assert z.testzip() is None
        new = etree.fromstring(z.read('word/document.xml'))
    for path in ['//m:oMath', '//w:tbl', '//w:instrText']:
        assert [etree.tostring(p) for p in old.xpath(path, namespaces=NS)] == [etree.tostring(p) for p in new.xpath(path, namespaces=NS)], path
    pages = sorted((WORK / 'render').glob('page-*.png'), key=lambda p: int(p.stem.split('-')[1]))
    assert len(pages) == 88
    changed = []
    for p in pages:
        a = Image.open(BASE / 'render_pass3' / p.name).convert('RGB')
        b = Image.open(p).convert('RGB')
        assert a.size == b.size
        if ImageChops.difference(a, b).getbbox():
            changed.append(int(p.stem.split('-')[1]))
    assert changed == [17, 79]
    expected_map = json.loads((BASE / 'page_map.json').read_text())
    extracted = []
    with pdfplumber.open(WORK / 'render/report_1008_v3_full.pdf') as pdf:
        assert len(pdf.pages) == 88
        for n, page in enumerate(pdf.pages, 1):
            lines = (page.extract_text(x_tolerance=2, y_tolerance=3) or '').splitlines()
            assert lines
            assert '含非实测占位' in norm(''.join(lines))
            assert not [c for c in page.chars if c['text'].strip() and (c['x0'] < 0 or c['x1'] > page.width + 1 or c['top'] < 0 or c['bottom'] > page.height + 1)]
            extracted.append((n, lines[-1].strip(), lines))
    for label, expected in expected_map.items():
        needle = norm(label)
        found = []
        for n, footer, lines in extracted:
            if any(norm(''.join(lines[start:start + length])) == needle for start in range(len(lines)) for length in range(1, 5)):
                found.append((n, footer))
        assert len(found) == 1 and found[0][1] == expected, (label, expected, found)
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ['report_1008_v3_full.md', 'report_1008_v3_full.docx']}
    result = {
        'pages': 88, 'changed_physical_pages': changed,
        'pixel_identical_previously_reviewed_pages': 86,
        'changed_page_visual_review': 'Both opened at original resolution; Chinese text, table, spacing and footer are clear.',
        'native_math_objects_preserved': len(new.xpath('//m:oMath', namespaces=NS)),
        'all_tables_and_fields_byte_identical_xml': True,
        'heading_and_caption_pages_reverified': len(expected_map),
        'toc_page_mapping_unchanged': True,
        'all_pages_retain_non_empirical_warning': True,
        'sha256': hashes,
        'scope': 'Document QA only; no experiment or submission certification.'
    }
    (WORK / 'render_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
