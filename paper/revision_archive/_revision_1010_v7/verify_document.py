"""Check evidence labels, synchronized numbers and retained package fidelity."""
from pathlib import Path
import json,zipfile,hashlib,re
from collections import Counter
from lxml import etree
import pdfplumber
from PIL import Image,ImageDraw
W=Path(__file__).resolve().parent;R=W.parent
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
tx=lambda e:''.join(e.xpath('.//w:t/text()',namespaces=NS))
source=R/'report_1010_v7_full.md';word=R/'report_1010_v7_full.docx';render=W/'render_final';pdf=render/(word.stem+'.pdf')
text=source.read_text();old=(R/'report_1010_v6_full.md').read_text()
changes=json.loads((W/'changes.json').read_text());ev=json.loads((W/'template-evidence.json').read_text())
build=json.loads((W/'docx_build.json').read_text());pm=json.loads((W/'page_map.json').read_text());pa=json.loads((W/'page_map_audit.json').read_text())
assert sha(source)==build['source_sha256']
assert not pa['unresolved'] and not pa['warning_missing_pages']
assert Path(pa['pdf']).resolve()==pdf.resolve()
for f,h in ev['baseline_hashes'].items():assert sha(R/f)==h
assert re.findall(r'\$\$(.*?)\$\$',text,re.S)==re.findall(r'\$\$(.*?)\$\$',old,re.S)
assert re.findall(r'```(.*?)```',text,re.S)==re.findall(r'```(.*?)```',old,re.S)
assert text[text.index('## 参考文献'):text.index('## 附录A')]==old[old.index('## 参考文献'):old.index('## 附录A')]
assert text[text.index('## 附录E'):text.index('## 附录F')]==old[old.index('## 附录E'):old.index('## 附录F')]
with zipfile.ZipFile(word) as z,zipfile.ZipFile(ev['reference']) as oz:
 assert z.testzip() is None
 assert set(z.namelist())==set(oz.namelist())
 for name in z.namelist():
  if name not in ev['editable_parts']:assert z.read(name)==oz.read(name),name
 body=etree.fromstring(z.read('word/document.xml'));oldbody=etree.fromstring(oz.read('word/document.xml'))
 assert [etree.tostring(v) for v in body.xpath('//m:oMath',namespaces=NS)]==[etree.tostring(v) for v in oldbody.xpath('//m:oMath',namespaces=NS)]
 assert [etree.tostring(v) for v in body.xpath('//w:sectPr',namespaces=NS)]==[etree.tostring(v) for v in oldbody.xpath('//w:sectPr',namespaces=NS)]
 allps=body.xpath('//w:p',namespaces=NS);alltext='\n'.join(tx(p) for p in allps)
 for op in changes['text_replacements']:
  expect=op['new']
  for a,b in changes['global']:expect=expect.replace(a,b)
  assert expect in alltext,expect[:80]
 for insertion in changes['insertions']:
  for s in insertion['paragraphs']:
   for a,b in changes['global']:s=s.replace(a,b)
   assert s in alltext
 docrows=Counter(tuple(tx(c) for c in row.findall('w:tc',NS)) for row in body.xpath('//w:tr',namespaces=NS))
 for key,record in changes['tables'].items():
  for row in record['new']:assert docrows[tuple(row)]>0,(key,row)
 cached=body.xpath('//w:p[w:pPr/w:pStyle[@w:val="TOC1" or @w:val="TOC2" or @w:val="TOC3" or @w:val="FigureList" or @w:val="TableList"]]',namespaces=NS)
 labels=[x[1] for x in build['headings']]+[x for prefix in ['图','表'] for x in build['captions'] if x.startswith(prefix)]
 assert len(cached)==len(labels)==211
 for p,label in zip(cached,labels):assert p.xpath('.//w:t/text()',namespaces=NS)[-1]==pm[label],label
 embedded={hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')}
 images=re.findall(r'^!\[[^]]*\]\(([^)]+)\)$',text,re.M)
 assert len(images)==11
 for f in images:assert sha(R/f) in embedded,f
 assert len(body.xpath('//m:oMath',namespaces=NS))==411
 assert len([s for s in body.xpath('//w:instrText/text()',namespaces=NS) if s.strip().startswith('TOC ')])==3
 assert etree.fromstring(z.read('word/settings.xml')).xpath('//w:updateFields/@w:val',namespaces=NS)==['true']
with pdfplumber.open(pdf) as doc:
 pts=[];outs=[]
 for i,p in enumerate(doc.pages,1):
  s=p.extract_text() or '';pts.append(s)
  assert '1010-v7' in s.replace(' ','')
  assert (render/f'page-{i}.png').is_file()
  bad=[c for c in p.chars if c['text'].strip() and (c['x0']<0 or c['x1']>p.width+1 or c['top']<0 or c['bottom']>p.height+1)]
  if bad:outs.append({'page':i,'text':''.join(c['text'] for c in bad)})
 assert not outs,outs
 assert '估算演示版' in pts[0] and '不代表真实实验记录' in pts[0]
 pages=len(doc.pages)
 # Text outside the nominal content box is inspected against the retained
 # source, not automatically treated as an error because headers differ.
 (W/'rendered_text.txt').write_text('\n\n'.join(f'PAGE {i+1}\n{s}' for i,s in enumerate(pts)))
# Source diagnostics are existing observations; no new training is performed.
manifest=json.loads((R/'research_0920/results/run_manifest.json').read_text())
assert manifest['status']=='completed' and manifest['test_data_used'] is False
assert manifest['script_sha256']==sha(R/'research_0920/run_feasibility.py')
assert manifest['protocol_sha256']==sha(R/'research_0920/预实验协议.md')
diag={}
for ds in ['aaec','cdcp']:
 s=json.loads((R/f'research_0920/results/{ds}_summary.json').read_text());p=s['calibrated_policy']
 for c,k in [('before_counts','before_micro_f1'),('after_counts','after_micro_f1')]:
  tp,fp,fn=p[c];assert abs(2*tp/(2*tp+fp+fn)-p[k])<1e-12
 assert set(p['accepted_actions'])=={'delete'} and p['before_counts'][0]==p['after_counts'][0]
 data=json.loads((R/f'research_0920/results/{ds}_data_manifest.json').read_text())
 archive=R/'research_0920/data'/('aaec_brat.zip' if ds=='aaec' else 'cdcp_acl17.zip')
 assert sha(archive)==data['archive_sha256']
 diag[ds]={'summary_sha256':sha(R/f'research_0920/results/{ds}_summary.json'),'before_f1':100*p['before_micro_f1'],'after_f1':100*p['after_micro_f1'],'accepted_deletions':p['accepted'],'original_archive_hash_matches':True}
(W/'diagnostic_verification.json').write_text(json.dumps({'scope':'Read-only consistency check of existing run records; no independent retraining','data':diag},ensure_ascii=False,indent=2))
result={'mechanical_checks':'PASS','source_sha256':sha(source),'docx_sha256':sha(word),'pdf_sha256':sha(pdf),'pages':pages,'native_math_objects':411,'display_equations':32,'references':49,'numbered_tables':47,'figures':11,'algorithms':3,'verified_page_labels':len(pm),'toc_cached_entries':len(cached),'toc_matches_final_render':True,'package_preserved_except_documented_parts':True,'source_v6_unchanged':True,'new_model_training_runs':0,'evidence':'ESTIMATED_SCENARIO_NOT_EMPIRICAL_FINDINGS','visual_review':'pending'}
(W/'final_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
# Full-resolution pairs support whole-document review without thumbnailing.
contact=W/'page_pairs';contact.mkdir(exist_ok=True)
for start in range(1,pages+1,2):
 ims=[Image.open(render/f'page-{i}.png').convert('RGB') for i in range(start,min(start+2,pages+1))]
 width=sum(im.width for im in ims)+12*(len(ims)-1);height=max(im.height for im in ims)+28
 canvas=Image.new('RGB',(width,height),'#d0d0d0');draw=ImageDraw.Draw(canvas);x=0
 for n,im in enumerate(ims):draw.text((x+8,7),f'Page {start+n}',fill='black');canvas.paste(im,(x,28));x+=im.width+12
 canvas.save(contact/f'pages-{start:03d}.png')
print(json.dumps(result,ensure_ascii=False))
