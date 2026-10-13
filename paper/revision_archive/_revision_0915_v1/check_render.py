from pathlib import Path
import pdfplumber, json, re, hashlib
from zipfile import ZipFile
from lxml import etree
import sys

root=Path(__file__).resolve().parent.parent
work=Path(__file__).resolve().parent
render=work/(sys.argv[1] if len(sys.argv)>1 else 'render_initial')
pdf=pdfplumber.open(render/'report_0915_v1.pdf').pages
heads=[l[3:] for l in (root/'report_0915_v1.md').read_text().splitlines() if l.startswith('## ') and ('章 ' in l or '附录' in l or l=='## 参考文献')]
normalize=lambda x:re.sub(r'\s+','',x)
page_info=[]; toc={}; body_start=None
for idx,page in enumerate(pdf):
    txt=page.extract_text() or ''; ls=[l.strip() for l in txt.splitlines() if l.strip()]
    if '第一章绪论' in normalize(txt) and '1.1研究背景' in normalize(txt):body_start=idx
    page_info.append({'physical_page':idx+1,'characters':len(txt),'first_lines':ls[:4],'last_lines':ls[-3:]})
assert body_start is not None
for idx,page in enumerate(pdf):
    if idx<body_start:continue
    top=normalize('\n'.join((page.extract_text() or '').splitlines()[:5]))
    for h in heads:
        if normalize(h) in top and h not in toc:toc[h]=idx-body_start+1
assert len(toc)==len(heads),(toc,heads)
(work/'toc_pages.json').write_text(json.dumps(toc,ensure_ascii=False,indent=2))
(render/'page_inventory.json').write_text(json.dumps(page_info,ensure_ascii=False,indent=2))
with ZipFile(root/'report_0915_v1.docx') as z:
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
    xml=etree.fromstring(z.read('word/document.xml'))
    comments=etree.fromstring(z.read('word/comments.xml'))
    result={'page_count':len(pdf),'body_start_physical_page':body_start+1,'toc':toc,'native_equations':len(xml.xpath('//m:oMath',namespaces=ns)),'tables':len(xml.xpath('//w:tbl',namespaces=ns)),'comments':len(comments),'docx_sha256':hashlib.sha256((root/'report_0915_v1.docx').read_bytes()).hexdigest()}
    visible=''.join(xml.xpath('//w:t/text()',namespaces=ns))
    assert '<!--' not in visible and 'ref:' not in visible
    assert len(comments)==10
    (render/'structural_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
for p in page_info:print(p['physical_page'],p['characters'],' / '.join(p['first_lines']), ' END ', ' / '.join(p['last_lines']))
