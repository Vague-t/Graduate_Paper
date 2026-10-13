from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from pypdf import PdfReader
import json,hashlib,sys,re
O=Path(__file__).resolve().parents[1];M=json.loads((O/'_work/revision_manifest.json').read_text());D=Path(M['output']);P=O/sys.argv[1]/(D.stem+'.pdf');r=PdfReader(P);flat=[]
def walk(xs):
 for x in xs:
  if isinstance(x,list):walk(x)
  else:flat.append({'title':x.title,'page':r.get_destination_page_number(x)+1})
walk(r.outline)
assert [x['title'] for x in flat]==[h['title'] for h in M['headings']],([x['title'] for x in flat],[h['title'] for h in M['headings']])
first=next(x['page'] for x in flat if x['title']=='第一章 绪论')
def roman(n):
 s=''
 for v,c in [(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]:
  while n>=v:s+=c;n-=v
 return s
cache={h['bookmark']:roman(x['page']-1) if x['page']<first else str(x['page']-first+1) for h,x in zip(M['headings'],flat)}
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}';N={'w':W[1:-1]}
with ZipFile(D) as z:data={n:z.read(n) for n in z.namelist()}
root=E.fromstring(data['word/document.xml']);changes=[];found={}
for i,e in enumerate(root.find(W+'body')):
 instr=''.join(e.xpath('.//w:instrText/text()',namespaces=N));mt=re.search(r'HYPERLINK\s+\\l\s+"(v9_toc_\d+)"',instr)
 if not mt:continue
 anchor=mt.group(1);nodes=e.xpath('.//w:t',namespaces=N);assert len(nodes)>=2;pn=nodes[-1];found[anchor]=cache[anchor]
 if pn.text!=cache[anchor]:changes.append({'block_id':f'B{i:04d}','before':pn.text,'after':cache[anchor]});pn.text=cache[anchor]
assert len(found)==len(cache)==149
# Keep labels and page cache in sync without modifying body content or layout.
data['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(D,'w',ZIP_DEFLATED) as z:
 for n,b in data.items():z.writestr(n,b)
M['output_sha256']=hashlib.sha256(D.read_bytes()).hexdigest();M['body_first_physical_page']=first;M['toc_page_changes']=changes
(O/'_work/revision_manifest.json').write_text(json.dumps(M,ensure_ascii=False,indent=2));(O/'_work/toc_pages.json').write_text(json.dumps(cache,ensure_ascii=False,indent=2));(O/'_work/outline.json').write_text(json.dumps(flat,ensure_ascii=False,indent=2))
print(json.dumps({'pages':len(r.pages),'body_start':first,'toc_updated':len(changes)},ensure_ascii=False))
