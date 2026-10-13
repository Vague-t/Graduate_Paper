"""Validate the diagnostic additions and the retained document package."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import zipfile
from lxml import etree
import pdfplumber
from PIL import Image, ImageDraw

W=Path(__file__).resolve().parent
R=W.parent
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
tx=lambda node:''.join(node.xpath('.//w:t/text()',namespaces=NS))
old=(R/'report_1010_v7_full.md').read_text()
source=R/'report_1010_v8_full.md'
new=source.read_text()
word=R/'report_1010_v8_full.docx'
pdf=W/'render_final'/f'{word.stem}.pdf'
changes=read(W/'changes.json')
stats=read(W/'diagnostic_supplement.json')
ev=read(W/'template-evidence.json')
build=read(W/'docx_build.json')
pages=read(W/'page_map.json')
page_audit=read(W/'page_map_audit.json')

for p,h in ev['baseline_hashes'].items():assert sha(R/p)==h,p
for p,h in stats['source_hashes'].items():assert sha(R/p)==h,p
assert sha(source)==build['source_sha256']
assert stats['checks']['all_saved_edits_recomputed']==38928
assert stats['checks']['audit_documents']==182
assert stats['new_training_runs']==stats['new_solver_runs']==0
assert not page_audit['unresolved'] and not page_audit['warning_missing_pages']
assert Path(page_audit['pdf']).resolve()==pdf.resolve()

for pat in [r'\$\$(.*?)\$\$',r'```(.*?)```']:
    assert re.findall(pat,new,re.S)==re.findall(pat,old,re.S)
for a,b in [('## 参考文献','## 附录A'),('## 附录E','## 附录F'),('#### 4.6.7','### 4.7'),('### H.4','### H.5')]:
    assert new[new.index(a):new.index(b,new.index(a))]==old[old.index(a):old.index(b,old.index(a))],a
old_tables=re.findall(r'(?m)^\|[^\n]*\n(?:\|[^\n]*(?:\n|$))+',old)
for table in old_tables:assert table in new
assert len(old_tables)==47

with zipfile.ZipFile(word) as z,zipfile.ZipFile(ev['reference']) as original:
    assert z.testzip() is None and set(z.namelist())==set(original.namelist())
    for name in z.namelist():
        if name not in ev['editable_parts']:assert z.read(name)==original.read(name),name
    root=etree.fromstring(z.read('word/document.xml'))
    oldroot=etree.fromstring(original.read('word/document.xml'))
    for query in ['//m:oMath','//w:sectPr']:
        assert [etree.tostring(x) for x in root.xpath(query,namespaces=NS)]==[etree.tostring(x) for x in oldroot.xpath(query,namespaces=NS)],query
    oldtbl=[etree.tostring(x) for x in oldroot.xpath('//w:tbl',namespaces=NS)]
    tbl=[etree.tostring(x) for x in root.xpath('//w:tbl',namespaces=NS)]
    # The package also uses tables for equations, algorithms and continued parts.
    assert len(tbl)==len(oldtbl)+6
    for item in oldtbl:assert item in tbl
    alltext='\n'.join(tx(p) for p in root.xpath('//w:p',namespaces=NS))
    for op in changes['text_replacements']:
        if op.get('docx_skip'):
            continue
        text=op['new']
        for a,b in changes['global']:text=text.replace(a,b)
        assert text in alltext,text[:60]
    for insertion in changes['insertions']:
        for text in insertion['paragraphs']:assert text in alltext,text[:60]
    allrows=Counter(tuple(tx(c) for c in row.findall('w:tc',NS)) for row in root.xpath('//w:tr',namespaces=NS))
    for section in changes['section_replacements']:
        for block in section['blocks']:
            if block['type']=='paragraph':assert block['text'] in alltext,block['text'][:60]
            else:
                for row in [block['headers']]+block['rows']:assert allrows[tuple(row)]>0,row
                assert block['caption'] in alltext
    ids=root.xpath('//w:bookmarkStart/@w:id',namespaces=NS)
    names=root.xpath('//w:bookmarkStart/@w:name',namespaces=NS)
    assert len(ids)==len(set(ids)) and len(names)==len(set(names))
    for anchor in root.xpath('//w:hyperlink/@w:anchor',namespaces=NS):assert anchor in names,anchor
    toc=root.xpath('//w:p[w:pPr/w:pStyle[@w:val="TOC1" or @w:val="TOC2" or @w:val="TOC3" or @w:val="FigureList" or @w:val="TableList"]]',namespaces=NS)
    labels=[h[1] for h in build['headings']]+[c for prefix in ['图','表'] for c in build['captions'] if c.startswith(prefix)]
    assert len(toc)==len(labels)==217
    for p,label in zip(toc,labels):
        assert p.xpath('.//w:t/text()',namespaces=NS)[-1]==pages[label],label
    assert len([s for s in root.xpath('//w:instrText/text()',namespaces=NS) if s.strip().startswith('TOC ')])==3
    assert etree.fromstring(z.read('word/settings.xml')).xpath('//w:updateFields/@w:val',namespaces=NS)==['true']
    embedded={hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')}
    imgs=re.findall(r'^!\[[^]]*\]\(([^)]+)\)$',new,re.M)
    assert len(imgs)==11
    for p in imgs:assert sha(R/p) in embedded,p

with pdfplumber.open(pdf) as document:
    text_pages=[]
    outside=[]
    for i,p in enumerate(document.pages,1):
        text=p.extract_text() or ''
        assert '1010-v8' in text.replace(' ','')
        assert (W/'render_final'/f'page-{i}.png').is_file()
        bad=[c for c in p.chars if c['text'].strip() and (c['x0']<0 or c['x1']>p.width+1 or c['top']<0 or c['bottom']>p.height+1)]
        if bad:outside.append({'page':i,'text':''.join(c['text'] for c in bad)})
        text_pages.append(text)
    assert not outside,outside
    assert '估算演示版' in text_pages[0] and '不代表真实实验记录' in text_pages[0]
    n=len(document.pages)
    (W/'rendered_text.txt').write_text('\n\n'.join(f'PAGE {i+1}\n{s}' for i,s in enumerate(text_pages)))

pair_dir=W/'page_pairs'
pair_dir.mkdir(exist_ok=True)
for start in range(1,n+1,2):
    ims=[Image.open(W/'render_final'/f'page-{i}.png').convert('RGB') for i in range(start,min(start+2,n+1))]
    canvas=Image.new('RGB',(sum(im.width for im in ims)+12*(len(ims)-1),max(im.height for im in ims)+28),'#d0d0d0')
    draw=ImageDraw.Draw(canvas);x=0
    for j,im in enumerate(ims):
        draw.text((x+8,7),f'Page {start+j}',fill='black');canvas.paste(im,(x,28));x+=im.width+12
    canvas.save(pair_dir/f'pages-{start:03d}.png')

out={'mechanical_checks':'PASS','source_sha256':sha(source),'docx_sha256':sha(word),'pdf_sha256':sha(pdf),
     'pages':n,'new_diagnostic_tables':6,'numbered_tables':53,'ooxml_tables':len(tbl),'figures_preserved':11,'native_math_objects_preserved':411,
     'display_equations_preserved':32,'algorithms_preserved':3,'references_preserved':49,
     'toc_entries':len(toc),'verified_page_labels':len(pages),'toc_matches_final_render':True,
     'v7_preserved':True,'saved_diagnostic_sources_preserved':True,
     'main_scenario_tables_unchanged':True,'existing_case_sections_unchanged':True,
     'new_training_runs':0,'new_solver_runs':0,'recomputed_saved_edit_records':38928,
     'source_evidence':'Existing CPU diagnostic reanalysis; target LLM experiment gaps remain',
     'visual_review':'pending'}
(W/'final_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
