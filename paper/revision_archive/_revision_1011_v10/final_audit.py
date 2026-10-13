from pathlib import Path
import json,re,hashlib,zipfile
from lxml import etree
import pdfplumber
W=Path(__file__).resolve().parent;R=W.parent
read=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
word=R/'report_1011_v10_full.docx';source=R/'report_1011_v10_full.md';pdf=W/'render_final_v2/report_1011_v10_full.pdf'
build=read(W/'docx_build.json');pages=read(W/'page_map.json');audit=read(W/'page_map_audit.json');src=read(W/'source_audit.json')
assert src['status']=='PASS' and sha(source)==src['source_sha256']==build['source_sha256']
assert not audit['unresolved'] and not audit['warning_missing_pages'] and Path(audit['pdf']).resolve()==pdf.resolve()
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
with zipfile.ZipFile(word) as z:
 root=etree.fromstring(z.read('word/document.xml'))
 ps=root.xpath('//w:p[w:pPr/w:pStyle[@w:val="TOC1" or @w:val="TOC2" or @w:val="TOC3" or @w:val="FigureList" or @w:val="TableList"]]',namespaces=NS)
 labels=[h[1] for h in build['headings']]+[c for prefix in ['图','表'] for c in build['captions'] if c.startswith(prefix)]
 assert len(ps)==len(labels)
 for p,label in zip(ps,labels):
  texts=p.xpath('.//w:t/text()',namespaces=NS)
  assert texts[-1]==pages[label],(label,texts[-1],pages[label])
 assert len(root.xpath('//m:oMath',namespaces=NS))==411
 assert etree.fromstring(z.read('word/settings.xml')).xpath('//w:updateFields/@w:val',namespaces=NS)==['true']
 image_hashes={hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')}
 imgs=re.findall(r'^!\[[^]]*\]\(([^)]+)\)$',source.read_text(),re.M);assert len(imgs)==11
 for p in imgs:assert sha(R/p) in image_hashes
with pdfplumber.open(pdf) as doc:
 texts=[];overflow=[]
 for n,p in enumerate(doc.pages,1):
  text=p.extract_text() or '';assert '1011-v10' in text.replace(' ','');assert (W/'render_final_v2'/f'page-{n}.png').is_file()
  bad=[c for c in p.chars if c['text'].strip() and (c['x0']<0 or c['x1']>p.width+1 or c['top']<0 or c['bottom']>p.height+1)]
  if bad:overflow.append(n)
  texts.append(text)
 assert not overflow,overflow
 assert '估算演示版' in texts[0] and '不代表真实实验记录' in texts[0]
 n=len(doc.pages)
(W/'rendered_text.txt').write_text('\n\n'.join(f'PAGE {i+1}\n{s}' for i,s in enumerate(texts)))
out={**src,'docx_sha256':sha(word),'pdf_sha256':sha(pdf),'pages':n,'toc_entries':len(labels),'verified_page_labels':len(pages),'toc_matches_final_pdf':True,'mechanical_checks':'PASS','visual_review':('PASS' if read(W/'visual_review.json')['pdf_sha256']==sha(pdf) and read(W/'visual_review.json')['all_pages_reviewed'] else 'pending')}
(W/'final_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2))
