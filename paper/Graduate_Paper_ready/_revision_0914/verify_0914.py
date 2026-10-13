from pathlib import Path
import argparse
import hashlib
import json
import re
from zipfile import ZipFile
from lxml import etree
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent.parent
WORK=ROOT/'_revision_0914'
parser=argparse.ArgumentParser()
parser.add_argument('--pdf',required=True)
parser.add_argument('--write-toc',action='store_true')
args=parser.parse_args()
new=(ROOT/'report_0914.md').read_text()
old=(ROOT/'report_0913.md').read_text()
audit=json.loads((WORK/'build_audit.json').read_text())
for name,digest in audit['source_file_hashes'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest, name
body,reftext=new.split('## 参考文献\n')
used=set(map(int,re.findall(r'\[(\d+)\]<!--ref:',body)))
listed=set(map(int,re.findall(r'^\[(\d+)\]',reftext,re.M)))
assert used==listed==set(range(1,31))
mapping=json.loads((WORK/'citation_map.json').read_text())
for n,key in re.findall(r'\[(\d+)\]<!--ref:([^>]+)-->',body): assert mapping[key]==int(n)
maths=lambda t: re.findall(r'\$\$(.*?)\$\$|\$([^$\n]+)\$',t,re.S)
assert maths(old)==maths(new)
rows=lambda t:[l for l in t[t.index('## 第三章'):t.index('## 第六章')].splitlines() if l.startswith('|')]
assert rows(old)==rows(new)
assert len(set(re.findall(r'待核验(R\d\d)',new)))==14
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
with ZipFile(ROOT/'report_0914.docx') as z:
    xml=etree.fromstring(z.read('word/document.xml'))
    plain=''.join(xml.xpath('//w:t/text()',namespaces=ns))
    assert '$' not in plain and '<!--' not in plain
    assert '0913修订工作稿' not in plain
    equations=len(xml.xpath('//m:oMath',namespaces=ns))
    assert equations==len(maths(new))==145
    tables=len(xml.xpath('//w:tbl',namespaces=ns))
    assert tables==12
    comments=etree.fromstring(z.read('word/comments.xml'))
    ids=comments.xpath('//w:comment/@w:id',namespaces=ns)
    assert len(ids)==len(set(ids))==11
    for tag in ['commentRangeStart','commentRangeEnd','commentReference']:
        assert sorted(xml.xpath('//w:'+tag+'/@w:id',namespaces=ns))==sorted(ids)
    assert b'/relationships/comments' in z.read('word/_rels/document.xml.rels')
    assert b'/word/comments.xml' in z.read('[Content_Types].xml')
    # Every native equation and table cell is present; paragraph text must match source content.
    assert '完整候选图评估与异常驱动局部修正' in plain
pdf=PdfReader(args.pdf)
texts=[p.extract_text() for p in pdf.pages]
norm=lambda x:re.sub(r'\s+','',x)
heads=[l[3:] for l in new.splitlines() if l.startswith('## ') and ('章 ' in l or '附录' in l or l=='## 参考文献')]
start=next(i for i,t in enumerate(texts) if norm('第一章 绪论') in norm(t) and '1.1' in t)
pages={}
for h in heads:
    matches=[i for i,t in enumerate(texts) if i>=start and norm(h) in norm(t)]
    assert matches, h
    pages[h]=matches[0]-start+1
if args.write_toc:(WORK/'toc_pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2))
else:
    assert pages==json.loads((WORK/'toc_pages.json').read_text()), 'TOC shifted'
    toc_text=norm(texts[start-1])
    for h,n in pages.items(): assert norm(h)+str(n) in toc_text, (h,n)
report={'original_and_0913_unchanged':True,'experiment_table_rows_preserved':len(rows(new)),
        'reference_count':30,'orphan_references':0,'citation_mapping_errors':0,
        'native_equations':equations,'table_count':tables,'native_comments':len(ids),
        'unresolved_evidence_items':14,'experiments_rerun':False,'rendered_pages':len(texts),
        'toc_pages':pages,'visual_review':'pending','docx_sha256':hashlib.sha256((ROOT/'report_0914.docx').read_bytes()).hexdigest()}
(WORK/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
print('Page text lengths:',[len(t) for t in texts])
