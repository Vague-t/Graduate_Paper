from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from pypdf import PdfReader
import json,hashlib,sys
O=Path(__file__).resolve().parents[1]
M=json.loads((O/'_work/revision_manifest.json').read_text())
D=Path(M['output']);P=O/sys.argv[1]/(D.stem+'.pdf')
r=PdfReader(P);flat=[]
def walk(items):
    for item in items:
        if isinstance(item,list):walk(item)
        else:flat.append({'title':item.title,'page':r.get_destination_page_number(item)+1})
walk(r.outline)
assert [x['title'] for x in flat]==[h['title'] for h in M['headings']]
body_start=next(x['page'] for x in flat if x['title']=='第一章 绪论')
def roman(n):
    result=''
    for value,s in [(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]:
        while n>=value:result+=s;n-=value
    return result
cache={h['bookmark']:roman(f['page']-1) if f['page']<body_start else str(f['page']-body_start+1) for h,f in zip(M['headings'],flat)}
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+NS['w']+'}'
with ZipFile(D) as z:data={n:z.read(n) for n in z.namelist()}
root=E.fromstring(data['word/document.xml']);changed=0
for f in root.xpath('.//w:fldSimple[starts-with(normalize-space(@w:instr),"PAGEREF")]',namespaces=NS):
    bookmark=f.get(W+'instr').split()[1];t=f.find('.//'+W+'t')
    if t.text!=cache[bookmark]:changed+=1;t.text=cache[bookmark]
data['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(D,'w',ZIP_DEFLATED) as z:
    for n,b in data.items():z.writestr(n,b)
M['output_sha256']=hashlib.sha256(D.read_bytes()).hexdigest()
M['body_first_physical_page']=body_start
(O/'_work/revision_manifest.json').write_text(json.dumps(M,ensure_ascii=False,indent=2))
(O/'_work/toc_pages.json').write_text(json.dumps(cache,ensure_ascii=False,indent=2))
(O/'_work/outline.json').write_text(json.dumps(flat,ensure_ascii=False,indent=2))
print(json.dumps({'pages':len(r.pages),'body_first_physical_page':body_start,'updated_toc_entries':changed,'chapters':[x for x in flat if x['title'].startswith(('第一章','第二章','第三章','第四章','第五章','第六章'))]},ensure_ascii=False))
