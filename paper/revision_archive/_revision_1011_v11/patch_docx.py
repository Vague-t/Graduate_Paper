"""Apply local OOXML edits to the retained v9 package and preserve native math."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,re,zipfile
from lxml import etree
W=Path(__file__).resolve().parent; R=W.parent
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
qn=lambda s:'{'+NS[s.split(':')[0]]+'}'+s.split(':')[1]
tx=lambda n:''.join(n.xpath('.//w:t/text()',namespaces=NS))
sha=lambda b:hashlib.sha256(b).hexdigest()
def visible_md(s):
 s=re.sub(r'<!--.*?-->','',s)
 s=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',s)
 return s.replace('`','').replace('**','')

changes=json.loads((W/'changes.json').read_text());reference=R/'report_1011_v10_full.docx'
with zipfile.ZipFile(reference) as z:infos=z.infolist();parts={n:z.read(n) for n in z.namelist()}
baseline=parts.copy();root=etree.fromstring(parts['word/document.xml']);body=root.find('w:body',NS)
maths=[etree.tostring(x) for x in root.xpath('//m:oMath',namespaces=NS)]
def style(p):
 s=p.find('w:pPr/w:pStyle',NS);return s.get(qn('w:val')) if s is not None else ''
def body_para(label):
 found=[p for p in body.findall('w:p',NS) if tx(p)==label and style(p) not in ['TOC1','TOC2','TOC3','TableList','FigureList']]
 assert len(found)==1,(label[:80],len(found));return found[0]
def replace_visible(n,a,b):
 nodes=n.xpath('.//w:t',namespaces=NS);s=tx(n);assert s.count(a)==1,(a[:90],s.count(a))
 start=s.index(a);end=start+len(a);pos=0;first=True
 for t in nodes:
  v=t.text or '';right=pos+len(v)
  if pos<end and right>start:
   t.text=v[:max(0,start-pos)]+(b if first else '')+(v[max(0,end-pos):] if end<right else '');first=False
  pos=right
 assert not first and tx(n)==s[:start]+b+s[end:]
body_template=next(p for p in body.findall('w:p',NS) if tx(p).startswith('本节补充统计来自2026年9月20日'))
main_body_template=next(p for p in body.findall('w:p',NS) if tx(p).startswith('本章将组件集合替换'))
caption_template=body_para('表4-7 关系恢复与误改的累计计数（估算情景）')
table_template=caption_template.getnext();assert table_template.tag==qn('w:tbl')
heading_templates={3:body_para('D.6 既有接口构造材料'),4:body_para('4.6.7 案例分析')}
toc_table_template=next(p for p in body.findall('w:p',NS) if style(p)=='TableList' and tx(p).startswith('表E-1 '))
toc_heading_template=next(p for p in body.findall('w:p',NS) if style(p)=='TOC2' and tx(p).startswith('D.6 '))
bookmark_id=max(int(v) for v in root.xpath('//w:bookmarkStart/@w:id',namespaces=NS));bookmarks={}
def paragraph(s,template=body_template):
 p=etree.Element(qn('w:p'));pp=template.find('w:pPr',NS)
 if pp is not None:p.append(deepcopy(pp))
 r=etree.SubElement(p,qn('w:r'));rp=template.find('w:r/w:rPr',NS)
 if rp is not None:r.append(deepcopy(rp))
 etree.SubElement(r,qn('w:t')).text=s
 return p
def bookmark(p,label):
 global bookmark_id
 bookmark_id+=1;name=f'v11_evidence_{bookmark_id}'
 b=etree.SubElement(p,qn('w:bookmarkStart'));b.set(qn('w:id'),str(bookmark_id));b.set(qn('w:name'),name)
 e=etree.SubElement(p,qn('w:bookmarkEnd'));e.set(qn('w:id'),str(bookmark_id));bookmarks[label]=name
def cell(template,s,width,head,first):
 c=etree.Element(qn('w:tc'));props=deepcopy(template.find('w:tcPr',NS));props.find('w:tcW',NS).set(qn('w:w'),str(width))
 for n in props.findall('w:gridSpan',NS)+props.findall('w:vMerge',NS):props.remove(n)
 c.append(props);p=paragraph(s,template.find('w:p',NS));pp=p.find('w:pPr',NS)
 if pp is None:pp=etree.Element(qn('w:pPr'));p.insert(0,pp)
 if not head:
  for n in pp.findall('w:keepNext',NS):pp.remove(n)
 jc=pp.find('w:jc',NS)
 if jc is None:jc=etree.SubElement(pp,qn('w:jc'))
 jc.set(qn('w:val'),'left' if first else 'center');c.append(p);return c
def table(b,rows):
 t=deepcopy(table_template);trs=table_template.findall('w:tr',NS)
 for n in t.findall('w:tr',NS):t.remove(n)
 total=sum(int(v) for v in t.xpath('./w:tblGrid/w:gridCol/@w:w',namespaces=NS));ws=b['widths'];widths=[round(total*x/sum(ws)) for x in ws];widths[-1]+=total-sum(widths)
 grid=t.find('w:tblGrid',NS)
 for c in list(grid):grid.remove(c)
 for width in widths:n=etree.SubElement(grid,qn('w:gridCol'));n.set(qn('w:w'),str(width))
 for i,row in enumerate([b['headers']]+rows):
  source=trs[0 if i==0 else 1];tr=etree.Element(qn('w:tr'));rp=source.find('w:trPr',NS)
  if rp is not None:tr.append(deepcopy(rp))
  if i==0:
   prop=tr.find('w:trPr',NS)
   if prop is None:prop=etree.SubElement(tr,qn('w:trPr'))
   if prop.find('w:tblHeader',NS) is None:etree.SubElement(prop,qn('w:tblHeader'))
  cells=source.findall('w:tc',NS)
  for j,(value,width) in enumerate(zip(row,widths)):
   c=cell(cells[0 if j==0 else 1],value,width,i==0,j==0)
   if i<len(rows):
    pp=c.find('w:p/w:pPr',NS)
    if pp.find('w:keepNext',NS) is None:etree.SubElement(pp,qn('w:keepNext'))
   tr.append(c)
  t.append(tr)
 return t
def materialize(blocks,main=False):
 nodes=[]
 for b in blocks:
  if b['type']=='paragraph':nodes.append(paragraph(b['text'],main_body_template if main else body_template))
  elif b['type']=='heading':
   p=paragraph(b['text'],heading_templates[b.get('level',3)]);bookmark(p,b['text']);nodes.append(p)
  else:
   cuts=[0]+(b.get('split') or [])+[len(b['rows'])]
   for i,(start,end) in enumerate(zip(cuts,cuts[1:])):
    label=b['caption'] if i==0 else b['caption'].replace('表','续表',1)
    cap=paragraph(label,caption_template)
    if i==0:bookmark(cap,b['caption'])
    else:
     pp=cap.find('w:pPr',NS);s=pp.find('w:pStyle',NS)
     if s is not None:s.set(qn('w:val'),'Normal')
     jc=pp.find('w:jc',NS)
     if jc is None:jc=etree.SubElement(pp,qn('w:jc'))
     jc.set(qn('w:val'),'center')
     if pp.find('w:keepNext',NS) is None:etree.SubElement(pp,qn('w:keepNext'))
     etree.SubElement(pp,qn('w:pageBreakBefore'))
    nodes.extend([cap,table(b,b['rows'][start:end])])
 return nodes

for original_op in changes['text_replacements']:
 op={k:visible_md(v) for k,v in original_op.items()}
 matches=[p for p in body.findall('w:p',NS) if op['old'] in tx(p)]
 assert len(matches)==1,(op['old'][:80],len(matches));replace_visible(matches[0],op['old'],op['new'])
for ins in changes['insertions']:
 cursor=body_para(visible_md(ins['anchor']))
 for s in ins['paragraphs']:n=paragraph(visible_md(s));cursor.addnext(n);cursor=n
for section in changes['sections_before']:
 anchor=body_para(section['anchor'])
 for n in materialize(section['blocks'],main=section.get('main',False)):anchor.addprevious(n)
section_end=body.find('w:sectPr',NS);assert section_end is not None
for n in materialize(changes['append_blocks']):section_end.addprevious(n)
for item in changes['heading_renames']:
 for p in body.findall('w:p',NS):
  if item['old'] in tx(p):replace_visible(p,item['old'],item['new'])

# Retain all three native TOC fields and reorder only cached result paragraphs.
build=json.loads((W/'docx_build.json').read_text())
groups=[([(label,'TOC'+str(level)) for level,label in build['headings']],['TOC1','TOC2','TOC3']),
        ([(label,'FigureList') for label in build['captions'] if label.startswith('图')],['FigureList']),
        ([(label,'TableList') for label in build['captions'] if label.startswith('表')],['TableList'])]
for labels,styles in groups:
 old=[p for p in body.findall('w:p',NS) if style(p) in styles];assert old
 templates={style(p):p for p in old};lookup={}
 for p in old:
  texts=p.xpath('.//w:t',namespaces=NS);assert len(texts)==2
  lookup[texts[0].text]=p
 new=[]
 for label,sid in labels:
  if label in lookup:p=deepcopy(lookup[label])
  else:
   assert label in bookmarks,label
   p=deepcopy(templates[sid]);ts=p.xpath('.//w:t',namespaces=NS);ts[0].text=label;ts[1].text='1'
   p.find('w:hyperlink',NS).set(qn('w:anchor'),bookmarks[label])
  if sid=='TableList':
   pp=p.find('w:pPr',NS);spacing=pp.find('w:spacing',NS)
   if spacing is None:spacing=etree.SubElement(pp,qn('w:spacing'))
   spacing.set(qn('w:before'),'0');spacing.set(qn('w:after'),'20')
   spacing.set(qn('w:line'),'320');spacing.set(qn('w:lineRule'),'exact')
  new.append(p)
 index=body.index(old[0])
 for p in old:body.remove(p)
 for p in new:body.insert(index,p);index+=1

parts['word/document.xml']=etree.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
for name in list(parts):
 if name=='word/document.xml' or re.fullmatch(r'word/(?:header|footer)\d+\.xml',name):
  r=etree.fromstring(parts[name])
  for a,b in changes['global']:
   for p in r.xpath('//w:p',namespaces=NS):
    while a in tx(p):replace_visible(p,a,b)
  parts[name]=etree.tostring(r,encoding='UTF-8',xml_declaration=True,standalone=True)
parts['docProps/core.xml']=parts['docProps/core.xml'].replace(b'1011-v10',b'1011-v11')
new=etree.fromstring(parts['word/document.xml']);assert [etree.tostring(x) for x in new.xpath('//m:oMath',namespaces=NS)]==maths
changed=[n for n in parts if parts[n]!=baseline[n]]
allowed={'word/document.xml','docProps/core.xml',*[n for n in parts if re.fullmatch(r'word/(?:header|footer)\d+\.xml',n)]};assert set(changed)<=allowed
output=R/'report_1011_v11_full.docx'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
 for info in infos:z.writestr(info,parts[info.filename])
allblocks=[b for s in changes['sections_before'] for b in s['blocks']]+changes['append_blocks']
ev={'reference':str(reference),'reference_sha256':sha(reference.read_bytes()),'editable_parts':changed,'new_bookmarks':bookmarks,'native_math_preserved':len(maths),'new_numbered_tables':sum(b['type']=='table' for b in allblocks),'removed_numbered_tables':0,'continued_parts_added':sum(len(b.get('split',[])) for b in allblocks),'bibliography_added':0}
(W/'template-evidence.json').write_text(json.dumps(ev,ensure_ascii=False,indent=2)+'\n');print(json.dumps(ev,ensure_ascii=False))
