from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from collections import Counter
import json,hashlib,re,difflib

O=Path(__file__).resolve().parents[1]
S=Path('/Users/channtang/Downloads/paper/论文规范排版稿_v12.docx')
D=O/'论文规范排版稿_v13.docx'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W='{'+NS['w']+'}';XML='{http://www.w3.org/XML/1998/namespace}'
X=lambda e,q:e.xpath(q,namespaces=NS)
T=lambda e:''.join(X(e,'.//w:t/text()|.//m:t/text()'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S)=='5e6610144bdc1696134ffb174aab4e429d9610dbfb2be0921baeaae0bc4ce3ab'
with ZipFile(S) as z:data={n:z.read(n) for n in z.namelist()}
r=E.fromstring(data['word/document.xml']);body=r.find(W+'body')
patches=json.loads((O/'_work/patches.json').read_text())
def range_edit(e,start,end,new):
    nodes=X(e,'.//w:t');before=T(e);pos=0
    if start==end:
        choices=[]
        for node in nodes:
            n=len(node.text or '')
            if pos<=start<=pos+n:choices.append((node,start-pos))
            pos+=n
        assert choices
        node,off=choices[0]
        node.text=(node.text or '')[:off]+new+(node.text or '')[off:]
        node.set(XML+'space','preserve')
    else:
        inserted=False
        for node in nodes:
            text=node.text or '';a=pos;b=pos+len(text);pos=b
            if b<=start or a>=end:continue
            lo=max(start-a,0);hi=min(end-a,len(text))
            node.text=text[:lo]+(new if not inserted else '')+text[hi:]
            node.set(XML+'space','preserve');inserted=True
        assert inserted
    assert T(e)==before[:start]+new+before[end:]

for p in patches:
    i=int(p['block_id'][1:]);e=body[i]
    assert i in {6,7,8,11,12,13} or 171<=i<=233
    assert e.tag==W+'p' and not X(e,'.//m:oMath|.//w:drawing|.//w:instrText')
    assert T(e)==p['old_text']
    assert re.findall(r'\[\d+\]',p['old_text'])==re.findall(r'\[\d+\]',p['new_text'])
    nums=lambda t:Counter(re.findall(r'\d+(?:\.\d+)?',t))
    assert nums(p['old_text'])==nums(p['new_text'])
    for op,a,b,c,d in reversed(difflib.SequenceMatcher(a=p['old_text'],b=p['new_text'],autojunk=False).get_opcodes()):
        if op!='equal':range_edit(e,a,b,p['new_text'][c:d])
    assert T(e)==p['new_text']

src=E.fromstring(data['word/document.xml']);sb=src.find(W+'body')
c14=lambda e:E.tostring(e,method='c14n')
scope={int(p['block_id'][1:]) for p in patches}
for i,(a,b) in enumerate(zip(sb,body)):
    if i not in scope:assert c14(a)==c14(b),i
assert len(body)==len(sb)
assert [c14(x) for x in X(src,'.//m:oMath')]==[c14(x) for x in X(r,'.//m:oMath')]
assert [c14(x) for x in X(src,'.//w:tbl')]==[c14(x) for x in X(r,'.//w:tbl')]
data['word/document.xml']=E.tostring(r,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(D,'w',ZIP_DEFLATED) as z:
    for n,b in data.items():z.writestr(n,b)

blocks=json.loads((O/'_source/blocks.json').read_text());headings=[]
for b in blocks:
    if not b['style_name'].lower().startswith('heading '):continue
    e=body[b['index']];names=X(e,'./w:bookmarkStart/@w:name')
    mark=next(m for m in names if m.startswith('v9_toc_'))
    headings.append({'block_id':b['id'],'title':T(e),'bookmark':mark})
M={'source':str(S),'source_sha256':sha(S),'output':str(D),'output_sha256':sha(D),
   'patch_count':len(patches),'scope':'中英文摘要与第一章绪论',
   'native_math':len(X(r,'.//m:oMath')),'tables':len(X(r,'.//w:tbl')),
   'headings':headings,'changed_blocks':[p['block_id'] for p in patches]}
(O/'_work/revision_manifest.json').write_text(json.dumps(M,ensure_ascii=False,indent=2))
(O/'_work/revised_scope.txt').write_text('\n\n'.join(f'[{p["block_id"]}] {p["reason"]}\n{p["new_text"]}' for p in patches))
print(json.dumps({k:M[k] for k in ['output','patch_count','native_math','tables']},ensure_ascii=False))
