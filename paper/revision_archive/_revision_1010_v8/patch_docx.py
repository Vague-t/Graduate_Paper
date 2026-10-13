"""Patch v7's retained OOXML package; add six diagnostic tables and TOC links."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import re
import zipfile
from lxml import etree

W=Path(__file__).resolve().parent
R=W.parent
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
qn=lambda s:'{'+NS[s.split(':')[0]]+'}'+s.split(':')[1]
tx=lambda node:''.join(node.xpath('.//w:t/text()',namespaces=NS))
sha=lambda b:hashlib.sha256(b).hexdigest()
changes=json.loads((W/'changes.json').read_text())
reference=R/'report_1010_v7_full.docx'
with zipfile.ZipFile(reference) as z:
    infos=z.infolist()
    parts={n:z.read(n) for n in z.namelist()}
baseline=parts.copy()
root=etree.fromstring(parts['word/document.xml'])
body=root.find('w:body',NS)
maths=[etree.tostring(x) for x in root.xpath('//m:oMath',namespaces=NS)]

def replace_visible(node,old,new):
    nodes=node.xpath('.//w:t',namespaces=NS)
    text=''.join(n.text or '' for n in nodes)
    assert text.count(old)==1,(old[:80],text.count(old))
    start=text.index(old);end=start+len(old);pos=0;first=True
    for n in nodes:
        s=n.text or '';right=pos+len(s)
        if pos<end and right>start:
            left=s[:max(0,start-pos)]
            tail=s[max(0,end-pos):] if end<right else ''
            n.text=left+(new if first else '')+tail
            first=False
        pos=right
    assert not first and tx(node)==text[:start]+new+text[end:]

body_template=next(p for p in body.findall('w:p',NS) if tx(p).startswith('轻量诊断用于'))
caption_template=next(p for p in body.findall('w:p',NS) if tx(p)=='表4-7 关系恢复与误改的累计计数（估算情景）')
table_template=caption_template.getnext()
assert table_template.tag==qn('w:tbl')
toc_template=next(p for p in body.findall('w:p',NS) if tx(p).startswith('表E-1 ') and p.find('w:pPr/w:pStyle',NS).get(qn('w:val'))=='TableList')
bookmark_id=max(int(v) for v in root.xpath('//w:bookmarkStart/@w:id',namespaces=NS))
new_bookmarks={}

def paragraph(text,template=body_template):
    p=etree.Element(qn('w:p'))
    pp=template.find('w:pPr',NS)
    if pp is not None:
        p.append(deepcopy(pp))
    r=etree.SubElement(p,qn('w:r'))
    rp=template.find('w:r/w:rPr',NS)
    if rp is not None:
        r.append(deepcopy(rp))
    etree.SubElement(r,qn('w:t')).text=text
    return p

def cell(template,text,width,is_header,first):
    c=etree.Element(qn('w:tc'))
    props=deepcopy(template.find('w:tcPr',NS))
    props.find('w:tcW',NS).set(qn('w:w'),str(width))
    for merged in props.findall('w:gridSpan',NS)+props.findall('w:vMerge',NS):
        props.remove(merged)
    c.append(props)
    p=paragraph(text,template.find('w:p',NS))
    pp=p.find('w:pPr',NS)
    if pp is None:
        pp=etree.Element(qn('w:pPr'));p.insert(0,pp)
    if not is_header:
        for k in pp.findall('w:keepNext',NS):pp.remove(k)
    jc=pp.find('w:jc',NS)
    if jc is None:jc=etree.SubElement(pp,qn('w:jc'))
    jc.set(qn('w:val'),'left' if first else 'center')
    c.append(p)
    return c

def table(block):
    t=deepcopy(table_template)
    template_rows=table_template.findall('w:tr',NS)
    for row in t.findall('w:tr',NS):t.remove(row)
    total=sum(int(v) for v in t.xpath('./w:tblGrid/w:gridCol/@w:w',namespaces=NS))
    weights=block['widths'];widths=[round(total*w/sum(weights)) for w in weights]
    widths[-1]+=total-sum(widths)
    grid=t.find('w:tblGrid',NS)
    for c in list(grid):grid.remove(c)
    for width in widths:
        c=etree.SubElement(grid,qn('w:gridCol'));c.set(qn('w:w'),str(width))
    for i,row in enumerate([block['headers']]+block['rows']):
        source=template_rows[0 if i==0 else 1]
        tr=etree.Element(qn('w:tr'))
        rp=source.find('w:trPr',NS)
        if rp is not None:tr.append(deepcopy(rp))
        cells=source.findall('w:tc',NS)
        for j,(value,width) in enumerate(zip(row,widths)):
            tr.append(cell(cells[0 if j==0 else 1],value,width,i==0,j==0))
        t.append(tr)
    return t

for op in changes['text_replacements']:
    if op.get('docx_skip'):
        continue
    matches=[p for p in body.findall('w:p',NS) if op['old'] in tx(p)]
    assert len(matches)==1,(op['old'][:70],len(matches))
    replace_visible(matches[0],op['old'],op['new'])
for ins in changes['insertions']:
    matches=[p for p in body.findall('w:p',NS) if tx(p)==ins['anchor']]
    assert len(matches)==1,ins['anchor'][:60]
    cursor=matches[0]
    for text in ins['paragraphs']:
        node=paragraph(text);cursor.addnext(node);cursor=node
for section in changes['section_replacements']:
    start=next(p for p in body.findall('w:p',NS) if tx(p)==section['start'])
    end=next(p for p in body.findall('w:p',NS) if tx(p)==section['end'])
    while start.getnext() is not end:
        node=start.getnext()
        assert node is not None and not node.xpath('.//m:oMath',namespaces=NS)
        body.remove(node)
    cursor=start
    for block in section['blocks']:
        if block['type']=='paragraph':
            node=paragraph(block['text']);cursor.addnext(node);cursor=node
        else:
            bookmark_id+=1
            name=f'v8_diagnostic_{bookmark_id}'
            cap=paragraph(block['caption'],caption_template)
            begin=etree.SubElement(cap,qn('w:bookmarkStart'))
            begin.set(qn('w:id'),str(bookmark_id));begin.set(qn('w:name'),name)
            finish=etree.SubElement(cap,qn('w:bookmarkEnd'));finish.set(qn('w:id'),str(bookmark_id))
            cursor.addnext(cap)
            node=table(block);cap.addnext(node);cursor=node
            new_bookmarks[block['caption']]=name

for label,anchor in new_bookmarks.items():
    p=deepcopy(toc_template)
    ts=p.xpath('.//w:t',namespaces=NS)
    assert len(ts)==2
    ts[0].text=label;ts[1].text='1'
    p.find('w:hyperlink',NS).set(qn('w:anchor'),anchor)
    toc_template.addprevious(p)

parts['word/document.xml']=etree.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
for name in list(parts):
    if name=='word/document.xml' or re.fullmatch(r'word/(?:header|footer)\d+\.xml',name):
        r=etree.fromstring(parts[name])
        for a,b in changes['global']:
            for p in r.xpath('//w:p',namespaces=NS):
                while a in tx(p):replace_visible(p,a,b)
        parts[name]=etree.tostring(r,encoding='UTF-8',xml_declaration=True,standalone=True)
parts['docProps/core.xml']=parts['docProps/core.xml'].replace(b'1010-v7',b'1010-v8')
new=etree.fromstring(parts['word/document.xml'])
assert [etree.tostring(x) for x in new.xpath('//m:oMath',namespaces=NS)]==maths
changed=[name for name in parts if parts[name]!=baseline[name]]
allowed={'word/document.xml','docProps/core.xml',*[n for n in parts if re.fullmatch(r'word/(?:header|footer)\d+\.xml',n)]}
assert set(changed)<=allowed,changed
output=R/'report_1010_v8_full.docx'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
    for info in infos:z.writestr(info,parts[info.filename])
evidence={'reference':str(reference),'reference_sha256':sha(reference.read_bytes()),
          'baseline_hashes':{f:sha((R/f).read_bytes()) for f in ['report_1010_v7_full.md','report_1010_v7_full.docx']},
          'editable_parts':changed,'new_bookmarks':new_bookmarks,'source_diagnostic_hash':sha((W/'diagnostic_supplement.json').read_bytes())}
(W/'template-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
(W/'package_patch_audit.json').write_text(json.dumps({'changed_parts':changed,'unchanged_parts':len(parts)-len(changed),
   'math_objects_preserved':len(maths),'new_tables':len(new_bookmarks),'all_images_unchanged':True},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(output),'changed_parts':changed,'new_tables':len(new_bookmarks),'math_objects_preserved':len(maths)},ensure_ascii=False))
