from pathlib import Path
import re, json, hashlib, argparse
from zipfile import ZipFile
from lxml import etree
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent.parent
WORK=ROOT/'_revision_0913'
p=argparse.ArgumentParser()
p.add_argument('--pdf',required=True)
p.add_argument('--write-toc',action='store_true')
args=p.parse_args()
src=(ROOT/'report_final.md').read_text()
new=(ROOT/'report_0913.md').read_text()
assert hashlib.sha256(src.encode()).hexdigest()=='ae11ea0635c5564d63a4600e27408940b4576ef10eff461a3b04826807915d66'
assert not any(ord(c)<32 and c!='\n' for c in new)
body,reftext=new.split('## 参考文献\n')
used=set(map(int,re.findall(r'\[(\d+)\]<!--ref:',body)))
listed=set(map(int,re.findall(r'^\[(\d+)\]',reftext,re.M)))
assert used==listed==set(range(1,22))
assert len(set(re.findall(r'待核验(R\d\d)',new)))==14
source_tables=[l for l in src[src.index('## 第三章'):src.index('## 第六章')].splitlines() if l.startswith('|')]
assert all(l in new for l in source_tables)
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
with ZipFile(ROOT/'report_0913.docx') as z:
    xml=etree.fromstring(z.read('word/document.xml'))
    style=etree.fromstring(z.read('word/styles.xml'))
    assert not xml.xpath('//w:pBdr',namespaces=ns)
    assert not style.xpath('//w:pBdr',namespaces=ns)
    plain=''.join(xml.xpath('//w:t/text()',namespaces=ns))
    assert '$' not in plain, 'Raw TeX delimiter leaked into Word'
    assert '<!--' not in plain
    eqs=len(xml.xpath('//m:oMath',namespaces=ns))
    eq_sources=list(re.finditer(r'\$\$(.*?)\$\$|\$([^$\n]+)\$',new,re.S))
    assert eqs==len(eq_sources),(eqs,len(eq_sources))
    table_count=len(xml.xpath('//w:tbl',namespaces=ns))
pdf=PdfReader(args.pdf)
norm=lambda x: re.sub(r'\s+','',x)
texts=[pg.extract_text() for pg in pdf.pages]
heads=[l[3:] for l in new.splitlines() if l.startswith('## ') and ('章 ' in l or '附录' in l or l=='## 参考文献')]
start=next(i for i,t in enumerate(texts) if norm('第一章 绪论') in norm(t) and '1.1' in t)
pages={}
for h in heads:
    matches=[i for i,t in enumerate(texts) if i>=start and norm(h) in norm(t)]
    assert matches,(h,'not found in rendered text')
    pages[h]=matches[0]-start+1
if args.write_toc:
    (WORK/'toc_pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2))
report={
 'source_md_unchanged':True,'source_table_rows_preserved':len(source_tables),
 'orphan_citations':0,'orphan_references':0,'reference_count':21,
 'unresolved_evidence_items':14,'native_equations':eqs,
 'table_count':table_count,'raw_tex_delimiters_in_docx':0,
 'title_paragraph_borders':0,'rendered_pages':len(pdf.pages),
 'toc_pages':pages,'visual_inspection':'pending',
 'experiments_rerun':False
}
(WORK/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
