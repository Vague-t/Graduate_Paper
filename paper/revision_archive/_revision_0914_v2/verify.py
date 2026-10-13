from pathlib import Path
from zipfile import ZipFile
import argparse
import hashlib
import json
import re
from lxml import etree
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(__file__).resolve().parent
p = argparse.ArgumentParser(); p.add_argument('--pdf', required=True); p.add_argument('--write-toc', action='store_true')
args = p.parse_args()
digest = lambda x: hashlib.sha256(x.read_bytes()).hexdigest()
old = (ROOT/'report_0914.md').read_text(); new = (ROOT/'report_0914_v2.md').read_text()
audit = json.loads((WORK/'build_audit.json').read_text())
for name, h in audit['source_file_hashes'].items(): assert digest(ROOT/name) == h, name
rows = lambda t: [l for l in t[t.index('## 第三章'):t.index('## 第六章')].splitlines() if l.startswith('|')]
assert rows(old) == rows(new)
body, refs = new.split('## 参考文献\n')
assert refs.split('## 附录A')[0] == old.split('## 参考文献\n')[1].split('## 附录A')[0]
assert set(map(int, re.findall(r'\[(\d+)\]<!--ref:', body))) == set(range(1,31))
mapping = json.loads((ROOT/'_revision_0914/citation_map.json').read_text())
for n,k in re.findall(r'\[(\d+)\]<!--ref:([^>]+)-->', body): assert mapping[k] == int(n)
maths = re.findall(r'\$\$(.*?)\$\$|\$([^$\n]+)\$', new, re.S)
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main', 'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'}
with ZipFile(ROOT/'report_0914_v2.docx') as z:
    xml = etree.fromstring(z.read('word/document.xml'))
    plain = ''.join(xml.xpath('//w:t/text()', namespaces=ns))
    assert '$' not in plain and '<!--' not in plain
    equations = len(xml.xpath('//m:oMath', namespaces=ns)); assert equations == len(maths)
    tables = len(xml.xpath('//w:tbl', namespaces=ns)); assert tables == 13
    comments = etree.fromstring(z.read('word/comments.xml'))
    ids = comments.xpath('//w:comment/@w:id', namespaces=ns)
    assert len(ids) == len(set(ids)) == 19
    for tag in ['commentRangeStart', 'commentRangeEnd', 'commentReference']:
        assert sorted(xml.xpath('//w:'+tag+'/@w:id', namespaces=ns)) == sorted(ids)
    for pp in xml.xpath('//w:p[w:pPr]', namespaces=ns): assert pp[0].tag == '{'+ns['w']+'}pPr'
    assert b'/relationships/comments' in z.read('word/_rels/document.xml.rels')
    assert b'/word/comments.xml' in z.read('[Content_Types].xml')
texts = [page.extract_text() for page in PdfReader(args.pdf).pages]
norm = lambda t: re.sub(r'\s+', '', t)
start = next(i for i,t in enumerate(texts) if norm('第一章 绪论') in norm(t) and '1.1' in t)
heads = [l[3:] for l in new.splitlines() if l.startswith('## ') and ('章 ' in l or '附录' in l or l == '## 参考文献')]
pages = {h: next(i for i,t in enumerate(texts) if i >= start and norm(h) in norm(t))-start+1 for h in heads}
if args.write_toc: (WORK/'toc_pages.json').write_text(json.dumps(pages, ensure_ascii=False, indent=2))
else:
    assert pages == json.loads((WORK/'toc_pages.json').read_text()), 'TOC shifted'
    toc_text = norm(texts[start-1])
    for h,n in pages.items(): assert norm(h)+str(n) in toc_text, (h,n)
tests = json.loads((ROOT/'argument_mining_0914/validation/test_report.json').read_text())
assert tests['tests_run'] == 55 and tests['successful'] and tests['skipped'] == 0
result = {'source_manuscripts_unchanged': True, 'historical_table_rows_preserved': len(rows(new)),
          'references_preserved': 30, 'unresolved_items_retained': len(set(re.findall(r'待核验(R\d\d)',new))),
          'native_equations': equations, 'native_comments': len(ids), 'tables': tables,
          'rendered_pages': len(texts), 'toc_pages': pages, 'visual_review': 'pending',
          'docx_sha256': digest(ROOT/'report_0914_v2.docx'), 'md_sha256': digest(ROOT/'report_0914_v2.md'),
          'formal_experiments_rerun': False, 'software_tests_passed': 55,
          'qualification': 'New reference implementation and manuscript QA only; not historical reproduction or school-template certification.'}
(WORK/'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
print('Page text lengths:', [len(t) for t in texts])
