from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
from collections import Counter
import json,hashlib,re,difflib
O=Path(__file__).resolve().parents[1];S=Path('/Users/channtang/Downloads/paper/论文规范排版稿_v10.docx');D=O/'论文规范排版稿_v11.docx'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','a':'http://schemas.openxmlformats.org/drawingml/2006/main','asvg':'http://schemas.microsoft.com/office/drawing/2016/SVG/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'}
W='{'+NS['w']+'}';R='{'+NS['r']+'}';XML='{http://www.w3.org/XML/1998/namespace}'
X=lambda e,q:e.xpath(q,namespaces=NS);T=lambda e:''.join(X(e,'.//w:t/text()|.//m:t/text()'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S)=='2d694cab29d5862c9971f9d02a55843ac02cfbcb4774fdcebc2c5ded14172765'
with ZipFile(S) as z:data={n:z.read(n) for n in z.namelist()}
r=E.fromstring(data['word/document.xml']);body=r.find(W+'body');blocks={f'B{i:04d}':e for i,e in enumerate(body)}
sourceblocks=json.loads((O/'_source/blocks.json').read_text());bs={b['id']:b for b in sourceblocks}
patches=[]
for group in ['ch12','ch3','ch4','root']:
 p=O/f'_agents/{group}/patches.json';assert p.exists(),p
 for e in json.loads(p.read_text()):e['editor']=group;patches.append(e)
extra=O/'_work/global_patches.json'
if extra.exists():patches+=json.loads(extra.read_text())

# Apply character differences while preserving unaltered runs, bookmarks, fields and OMML.
def range_edit(e,start,end,new):
 nodes=X(e,'.//w:t|.//m:t');before=T(e);pos=0
 if start==end:
  choices=[]
  for node in nodes:
   n=len(node.text or '');
   if node.tag==W+'t' and pos<=start<=pos+n:choices.append((node,start-pos))
   pos+=n
  if not choices:raise ValueError(('no text insertion position',start,before,new))
  node,off=choices[-1] if choices[-1][1]==0 else choices[0]
  node.text=(node.text or '')[:off]+new+(node.text or '')[off:];node.set(XML+'space','preserve')
 else:
  inserted=False
  for node in nodes:
   txt=node.text or '';a=pos;b=pos+len(txt);pos=b
   if b<=start or a>=end:continue
   assert node.tag==W+'t',('would alter native math',before[start:end],new)
   lo=max(start-a,0);hi=min(end-a,len(txt));node.text=txt[:lo]+(new if not inserted else '')+txt[hi:];node.set(XML+'space','preserve');inserted=True
  assert inserted
 assert T(e)==before[:start]+new+before[end:]
def replace(e,old,new,all_=False):
 before=T(e);n=before.count(old)
 assert n and (all_ or n==1),(old,n,before[:100])
 if e.tag==W+'tbl':
  cells=[c for c in X(e,'.//w:tc') if old in T(c)]
  assert sum(T(c).count(old) for c in cells)==n,('replacement spans table cells',old)
  for cell in cells:replace(cell,old,new,all_)
  assert T(e)==before.replace(old,new)
  return
 starts=[];pos=0
 while True:
  at=before.find(old,pos)
  if at<0:break
  starts.append(at);pos=at+len(old)
 for at in reversed(starts):
  diffs=difflib.SequenceMatcher(a=old,b=new,autojunk=False).get_opcodes()
  for op,i,j,k,l in reversed(diffs):
   if op!='equal':range_edit(e,at+i,at+j,new[k:l])
 assert T(e)==before.replace(old,new)

edits=[]
for p in patches:
 e=blocks[p['block_id']];before=T(e);target=e
 if 'row_index' in p:
  target=e.findall(W+'tr')[p['row_index']].findall(W+'tc')[p['col_index']]
 replace(target,p['old_text'],p['new_text'],p.get('replace_all',False))
 edits.append({**p,'before':before,'after':T(e)})

# Unify only prose/table labels. Native math and bibliographic labels remain unchanged.
normalizations=[]
for bid,e in blocks.items():
 i=int(bid[1:]);
 if i<169 or 851<=i<906:continue
 for a,b in [('T0/I0','T0I0'),('T1/I0','T1I0'),('T0/I1','T0I1'),('T1/I1','T1I1'),('T0／I0','T0I0'),('T1／I0','T1I0'),('T0／I1','T0I1'),('T1／I1','T1I1')]:
  if a in T(e):
   before=T(e);replace(e,a,b,True);normalizations.append({'block_id':bid,'old_text':a,'new_text':b,'before':before,'after':T(e),'reason':'统一训练与推理组合记法。'})

# Synchronize changed heading text in the retained TOC using its existing bookmark links.
headings=[];bookmark_titles={}
for b in sourceblocks:
 if b['style_name'].lower().startswith('heading '):
  e=blocks[b['id']];marks=X(e,'./w:bookmarkStart/@w:name');mark=next((m for m in marks if m.startswith('v9_toc_')),None)
  assert mark,(b['id'],marks)
  h={'block_id':b['id'],'title':T(e),'bookmark':mark,'level':b['level']};headings.append(h);bookmark_titles[mark]=T(e)
toc_changes=[]
for bid,e in blocks.items():
 if not bs[bid]['style_name'].lower().startswith('toc'):continue
 instr=''.join(X(e,'.//w:instrText/text()'));match=re.search(r'HYPERLINK\\?\s*\\l\s+"([^"]+)"',instr)
 if not match:match=re.search(r'"(v9_toc_\d+)"',instr)
 assert match,(bid,instr)
 anchor=match.group(1)
 if anchor not in bookmark_titles:
  assert anchor=='v9_toc_145' and bid=='B0162',('unexpected orphan TOC',bid,anchor)
  before=T(e)
  for child in list(e):e.remove(child)
  pp=E.SubElement(e,W+'pPr');E.SubElement(pp,W+'spacing',{W+'before':'0',W+'after':'0',W+'line':'1',W+'lineRule':'exact'})
  toc_changes.append({'block_id':bid,'before':before,'after':'','reason':'删除正文已不存在的S2.8目录条目。'})
  continue
 tn=X(e,'.//w:t');assert len(tn)>=2,(bid,T(e))
 old=''.join(n.text or '' for n in tn[:-1]);new=bookmark_titles[anchor]
 if old!=new:replace(e,old,new);toc_changes.append({'block_id':bid,'before':old,'after':new})
 # A modest reduction of TOC spacing prevents a sixth contents page with only two lines.
 spacing=e.find('./'+W+'pPr/'+W+'spacing')
 if spacing is not None:spacing.set(W+'after','20');spacing.set(W+'line','264')

# Native math is immutable in this language-editing task.
src=E.fromstring(data['word/document.xml']);sig=lambda e:E.tostring(e,method='c14n')
assert [sig(e) for e in X(src,'.//m:oMath')]==[sig(e) for e in X(r,'.//m:oMath')]
# Check numbers in every data table, including digits in configuration identifiers.
num=lambda t:re.findall(r'[-+−]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?',t)
for i,(a,b) in enumerate(zip(src.find(W+'body'),body)):
 if a.tag==W+'tbl' and i!=1019:assert num(T(a))==num(T(b)),('numeric table delta',i,num(T(a)),num(T(b)))

from layout_v11 import apply_layout
layout_changes=apply_layout(r,blocks,X,T,NS)

# Figure patch is enabled only after the author's model confirmation.
figconfig=O/'_work/figure_decision.json';figure_changes=[]
if figconfig.exists():
 cfg=json.loads(figconfig.read_text())
 assert cfg['main_model']=='Qwen3.5-9B' and cfg['user_confirmed']
 for idx in [3,5,6]:
  name=f'word/media/image{idx}.svg';old=data[name];svg=old.decode();new=svg.replace('Qwen3.8','Qwen3.5').replace('27B','9B').replace('16全注意力块','8全注意力块').replace('仅16个全注意力块','仅8个全注意力块')
  assert new!=svg
  data[name]=new.encode();(O/'_work'/f'image{idx}_v11.svg').write_bytes(data[name]);figure_changes.append({'part':name,'replacements':['Qwen3.8-27B → Qwen3.5-9B','16个全注意力块 → 8个（适用图）']})
 # PNG fallbacks already rendered from these exact revised SVGs by prepare_figures.py.
 relroot=E.fromstring(data['word/_rels/document.xml.rels']);RN='{http://schemas.openxmlformats.org/package/2006/relationships}'
 for idx,bid in [(3,'B0322'),(5,'B0407'),(6,'B0533')]:
  png=O/'_work'/f'image{idx}_v11.png';assert png.exists(),png
  pngname=f'word/media/image{idx}_v11.png';data[pngname]=png.read_bytes();rid=f'rIdV11Fallback{idx}'
  E.SubElement(relroot,RN+'Relationship',Id=rid,Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/image',Target=f'media/image{idx}_v11.png')
  blip=X(blocks[bid],'.//a:blip')[0];blip.set(R+'embed',rid)
  for dp in X(blocks[bid],'.//wp:docPr'):dp.set('descr',dp.get('descr','').replace('；内嵌SVG矢量图，并保留PNG兼容预览。','；Qwen3.5-9B配置，内嵌SVG矢量图及PNG兼容预览。'))
 data['word/_rels/document.xml.rels']=E.tostring(relroot,xml_declaration=True,encoding='UTF-8',standalone=True)

# Figure 5-1 alternative text follows its revised caption.
for dp in X(blocks['B0801'],'.//wp:docPr'):dp.set('descr',T(blocks['B0802']))
data['word/document.xml']=E.tostring(r,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(D,'w',ZIP_DEFLATED) as z:
 for n,d in data.items():z.writestr(n,d)
changed_blocks=[]
for i,(a,b) in enumerate(zip(src.find(W+'body'),body)):
 if T(a)!=T(b):changed_blocks.append(f'B{i:04d}')
M={'source':str(S),'source_sha256':sha(S),'output':str(D),'output_sha256':sha(D),'patch_count':len(patches),'edits':edits,'normalizations':normalizations,'toc_title_changes':toc_changes,'headings':headings,'figure_changes':figure_changes,'changed_blocks':changed_blocks,'native_math':len(X(r,'.//m:oMath')),'tables':len(X(r,'.//w:tbl'))}
M['layout_changes']=layout_changes
(O/'_work/revision_manifest.json').write_text(json.dumps(M,ensure_ascii=False,indent=2))
final=[]
for b in sourceblocks:
 e=blocks[b['id']];t=T(e)
 if e.tag==W+'tbl':t='\n'.join(' | '.join(T(c) for c in row.findall(W+'tc')) for row in e.findall(W+'tr'))
 final.append({**b,'text':t})
(O/'_work/revised_blocks.json').write_text(json.dumps(final,ensure_ascii=False,indent=2))
(O/'_work/revised_fulltext.txt').write_text('\n\n'.join(f"[{b['id']}] {b['style_name']}\n{b['text']}" for b in final))
print(json.dumps({k:M[k] for k in ['output','patch_count','native_math','tables','figure_changes']},ensure_ascii=False))
