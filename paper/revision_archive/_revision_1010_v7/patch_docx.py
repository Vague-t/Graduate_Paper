"""Patch only documented OOXML slots; preserve every other package part."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,re,zipfile
from lxml import etree
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1010_v6'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math','a':'http://schemas.openxmlformats.org/drawingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
qn=lambda s:'{'+NS[s.split(':')[0]]+'}'+s.split(':')[1]
tx=lambda node:''.join(node.xpath('.//w:t/text()',namespaces=NS))
sha=lambda b:hashlib.sha256(b).hexdigest()
changes=json.loads((W/'changes.json').read_text())
with zipfile.ZipFile(R/'report_1010_v6_full.docx') as z:
 infos=z.infolist();parts={n:z.read(n) for n in z.namelist()}
orig=parts.copy();root=etree.fromstring(parts['word/document.xml']);body=root.find('w:body',NS)
baseline_maths=[etree.tostring(x) for x in root.xpath('//m:oMath',namespaces=NS)]
def replace_visible(node,old,new):
 nodes=node.xpath('.//w:t',namespaces=NS);text=''.join(n.text or '' for n in nodes)
 assert text.count(old)==1,(old[:90],text[:90],text.count(old))
 start=text.index(old);end=start+len(old);pos=0;first=True
 for n in nodes:
  s=n.text or '';right=pos+len(s)
  if pos<end and right>start:
   left=s[:max(0,start-pos)];tail=s[max(0,end-pos):] if end<right else ''
   n.text=left+(new if first else '')+tail;first=False
   if n.text.startswith(' ') or n.text.endswith(' '):n.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
  pos=right
 assert not first
 assert tx(node)==text[:start]+new+text[end:]
for op in changes['text_replacements']:
 matches=[p for p in body.findall('w:p',NS) if op['old'] in tx(p)]
 assert len(matches)==1,(op['old'][:60],len(matches))
 replace_visible(matches[0],op['old'],op['new'])

done={k:set() for k in changes['tables']};current=None
for child in body:
 if child.tag==qn('w:p'):
  text=tx(child);match=re.match(r'^(表[A-H0-9]+-\d+)(?:[ （])',text)
  if match:current=match[1]
 if child.tag==qn('w:tbl') and current in changes['tables']:
  data=changes['tables'][current]
  for row in child.findall('w:tr',NS):
   cells=row.findall('w:tc',NS);texts=[tx(c) for c in cells]
   indices=[i for i,old in enumerate(data['old']) if old==texts]
   if not indices:continue
   assert len(indices)==1;idx=indices[0];assert idx not in done[current]
   for cell,old,new in zip(cells,data['old'][idx],data['new'][idx]):
    if old!=new:replace_visible(cell,old,new)
   done[current].add(idx)
for k,record in changes['tables'].items():assert len(done[k])==len(record['old']),(k,len(done[k]))

style=next(p for p in body.findall('w:p',NS) if tx(p).startswith('轻量诊断用于'))
def new_para(text):
 p=etree.Element(qn('w:p'))
 ppr=style.find('w:pPr',NS)
 if ppr is not None:p.append(deepcopy(ppr))
 run=etree.SubElement(p,qn('w:r'));oldrun=style.find('w:r',NS)
 if oldrun is not None and oldrun.find('w:rPr',NS) is not None:run.append(deepcopy(oldrun.find('w:rPr',NS)))
 etree.SubElement(run,qn('w:t')).text=text
 return p
for insertion in changes['insertions']:
 anchor=insertion['anchor'].lstrip('# ').strip()
 candidates=[p for p in body.findall('w:p',NS) if tx(p)==anchor]
 assert len(candidates)==1,(anchor[:60],len(candidates))
 prev=candidates[0]
 for s in insertion['paragraphs']:
  node=new_para(s);prev.addnext(node);prev=node

parts['word/document.xml']=etree.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
# Text-only replacement across paragraph nodes also handles header/version metadata.
for name in list(parts):
 if name=='word/document.xml' or re.fullmatch(r'word/(?:header|footer)\d+\.xml',name):
  t=etree.fromstring(parts[name])
  for old,new in changes['global']:
   if old.startswith('_revision_'):continue
   for p in t.xpath('//w:p',namespaces=NS):
    while old in tx(p):replace_visible(p,old,new)
  parts[name]=etree.tostring(t,encoding='UTF-8',xml_declaration=True,standalone=True)
for name in ['docProps/core.xml']:
 t=parts[name].decode()
 t=t.replace('1010-v6','1010-v7').replace('模拟数据演示稿','估算演示版')
 parts[name]=t.encode()
root=etree.fromstring(parts['word/document.xml'])
rels=etree.fromstring(parts['word/_rels/document.xml.rels'])
target_by_id={x.get('Id'):x.get('Target') for x in rels}
updated_media=[]
for p in root.xpath('//w:body/w:p[.//a:blip]',namespaces=NS):
 props=p.xpath('.//wp:docPr',namespaces=NS);name=props[0].get('name')
 if name in {'training_results.png','recovery_risk.png','four_cell_results.png'}:
  rid=p.xpath('.//a:blip/@r:embed',namespaces=NS)[0];part='word/'+target_by_id[rid]
  parts[part]=(W/'figures'/name).read_bytes();updated_media.append(part)
assert len(updated_media)==3
assert [etree.tostring(x) for x in root.xpath('//m:oMath',namespaces=NS)]==baseline_maths
docx=R/'report_1010_v7_full.docx'
with zipfile.ZipFile(docx,'w',zipfile.ZIP_DEFLATED) as z:
 for info in infos:z.writestr(info,parts[info.filename])
changed=[n for n in orig if orig[n]!=parts[n]]
allowed={'word/document.xml','docProps/core.xml',*updated_media,*[n for n in parts if re.fullmatch(r'word/(?:header|footer)\d+\.xml',n)]}
assert set(changed)<=allowed,changed
evidence=json.loads((W/'template-evidence.json').read_text());evidence['editable_parts']=changed
(W/'template-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
build=json.loads((P/'docx_build.json').read_text())
def translate(s):
 for old,new in changes['global']:s=s.replace(old,new)
 return s
def recursive(o):
 if isinstance(o,str):return translate(o)
 if isinstance(o,list):return [recursive(v) for v in o]
 if isinstance(o,dict):return {k:recursive(v) for k,v in o.items()}
 return o
build=recursive(build)
build.update({'source_sha256':sha((R/'report_1010_v7_full.md').read_bytes()),'retained_template_sha256':sha((R/'report_1010_v6_full.docx').read_bytes()),'output':str(docx),'patch_method':'retained package with text-only slot edits, cloned body paragraphs and three replaced media assets'})
(W/'docx_build.json').write_text(json.dumps(build,ensure_ascii=False,indent=2))
(W/'package_patch_audit.json').write_text(json.dumps({'changed_parts':changed,'unchanged_part_count':len(parts)-len(changed),'native_math_objects_unchanged':len(baseline_maths),'table_rows_updated':{k:len(v) for k,v in done.items()},'all_other_parts_preserved':True},ensure_ascii=False,indent=2))
print(json.dumps({'output':str(docx),'changed_parts':changed,'math_objects_preserved':len(baseline_maths)},ensure_ascii=False))
