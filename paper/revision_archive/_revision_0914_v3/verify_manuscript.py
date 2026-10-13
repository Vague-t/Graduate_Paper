"""Check content preservation, bibliography, OOXML and rendered navigation."""
from collections import Counter
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import re
import sys
from lxml import etree
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
RENDER = Path(sys.argv[1]) if len(sys.argv) > 1 else WORK / 'render_deliver'
base = (ROOT / 'report_0914_v2.md').read_text()
draft = (ROOT / 'report_0914_v3.md').read_text()
tables = lambda text: re.findall(r'(?m)^\|[^\n]*\n(?:\|[^\n]*\n)+', text)
old_tables, new_tables = tables(base), tables(draft)
preserved = [t for t in old_tables if t in new_tables]
assert len(old_tables) == 13 and len(new_tables) == 14 and len(preserved) == 12
historical = [t for t in old_tables if any(s in t.splitlines()[0] for s in
              ['MajorClaim-F1', 'Support-F1', 'Reason-F1', '$\\Delta$Comp',
               'Top-1一致率', '$\\Delta$Rel', '|指标|结果|', 'Unlabeled Link-F1'])]
assert len(historical) == 8 and all(t in new_tables for t in historical)
refs = re.findall(r'^\[(\d+)\] (.+)$', draft, re.M)
assert [int(n) for n, _ in refs] == list(range(1, 34))
cites = re.findall(r'\[(\d+)\]<!--ref:([^>]+)--><!--anchor:([^>]+)-->', draft)
first_seen = list(dict.fromkeys(int(n) for n, _, _ in cites))
assert first_seen == list(range(1, 34))
slugs = {}
for n, slug, anchor in cites:
    assert slugs.setdefault(slug, n) == n
    assert anchor != 'none:'
assert len(slugs) == 33
caption_order = re.findall(r'^表4-(\d+) ', draft, re.M)
assert caption_order == [str(i) for i in range(1, 8)]

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'}
with ZipFile(ROOT / 'report_0914_v3.docx') as z:
    assert z.testzip() is None
    xml = etree.fromstring(z.read('word/document.xml'))
    comments = etree.fromstring(z.read('word/comments.xml'))
    assert len(comments) == 10
    starts = xml.xpath('//w:commentRangeStart/@w:id', namespaces=ns)
    ends = xml.xpath('//w:commentRangeEnd/@w:id', namespaces=ns)
    refs_xml = xml.xpath('//w:commentReference/@w:id', namespaces=ns)
    assert Counter(starts) == Counter(ends) == Counter(refs_xml)
    assert len(starts) == 10
    equation_count = len(xml.xpath('//m:oMath', namespaces=ns))
    assert equation_count == 154
    all_text = ''.join(xml.xpath('//w:t/text() | //m:t/text()', namespaces=ns))
    assert '<!--ref:' not in all_text
    assert '反例四' in all_text and 'N' in all_text
    assert len(xml.xpath('//w:tbl', namespaces=ns)) == 14

pdf = PdfReader(RENDER / 'report_0914_v3.pdf')
pages = [p.extract_text() for p in pdf.pages]
flat = [''.join(t.split()) for t in pages]
first = next(i for i, text in enumerate(flat) if '第一章绪论' in text and '1.1研究背景' in text)
toc = {}
heading_pages = {}
for heading in re.findall(r'^## (.+)$', draft, re.M):
    if not ('章 ' in heading or heading.startswith('附录') or heading == '参考文献'):
        continue
    target = ''.join(heading.split())
    found = [i for i in range(first, len(flat)) if target in flat[i]]
    assert found, heading
    heading_pages[heading] = found[0] + 1
    toc[heading] = found[0] - first + 1
assert len(list(RENDER.glob('page-*.png'))) == len(pdf.pages)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result = {'md_sha256': digest(ROOT / 'report_0914_v3.md'),
          'docx_sha256': digest(ROOT / 'report_0914_v3.docx'),
          'base_md_unchanged_sha256': digest(ROOT / 'report_0914_v2.md'),
          'historical_result_tables_preserved': len(historical),
          'all_unchanged_table_bodies': len(preserved),
          'references': len(refs), 'citation_occurrences': len(cites),
          'native_equations': equation_count, 'tables': 14, 'word_comments': 10,
          'rendered_pages': len(pdf.pages), 'toc': toc, 'physical_heading_pages': heading_pages,
          'visual_review': 'pending',
          'scope': 'file consistency and constructed examples; no empirical reproduction'}
print(json.dumps(result, ensure_ascii=False, indent=2))
