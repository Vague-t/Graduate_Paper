from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from collections import Counter
import json,hashlib,re,difflib

O=Path(__file__).resolve().parents[1]
S=Path('/Users/channtang/Downloads/paper/论文规范排版稿_v14.docx')
D=O/'论文规范排版稿_v15.docx'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W='{'+NS['w']+'}';MM='{'+NS['m']+'}';XML='{http://www.w3.org/XML/1998/namespace}'
X=lambda e,q:e.xpath(q,namespaces=NS)
T=lambda e:''.join(X(e,'.//w:t/text()|.//m:t/text()'))
c14=lambda e:E.tostring(e,method='c14n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S)=='dfa1c6624379f1405134a0939cb66f305d1fc536f33f8a53af5b50f7ec2987a9'
with ZipFile(S) as z:data={n:z.read(n) for n in z.namelist()}
r=E.fromstring(data['word/document.xml']);body=r.find(W+'body')
patches=json.loads((O/'_work/patches.json').read_text())

def range_edit(nodes,start,end,new):
    get=lambda:''.join(n.text or '' for n in nodes)
    before=get();pos=0
    if start==end:
        choices=[]
        for node in nodes:
            n=len(node.text or '')
            if pos<=start<=pos+n:choices.append((node,start-pos))
            pos+=n
        assert choices,(start,end,new,before)
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
    assert get()==before[:start]+new+before[end:]

segment_audit=[]
for p in patches:
    i=int(p['block_id'][1:]);e=body[i]
    assert 330<=i<=525
    assert e.tag==W+'p' and not X(e,'.//w:drawing')
    assert T(e)==p['old_text']
    assert re.findall(r'\[\d+\]',p['old_text'])==re.findall(r'\[\d+\]',p['new_text'])
    nums=lambda t:Counter(re.findall(r'\d+(?:\.\d+)?',t))
    assert nums(p['old_text'])==nums(p['new_text'])
    # Work only on ordinary runs between native equations. Math XML is never edited.
    groups=[[]];maths=[]
    for n in X(e,'.//w:t|.//m:oMath'):
        if n.tag==MM+'oMath':maths.append(T(n));groups.append([])
        else:
            assert not n.xpath('ancestor::m:oMath',namespaces=NS)
            groups[-1].append(n)
    pat=''.join('(.*?)'+re.escape(s) for s in maths)+'(.*)'
    match=re.fullmatch(pat,p['new_text'],flags=re.S)
    assert match,(p['block_id'],maths)
    new_parts=match.groups();assert len(groups)==len(new_parts)
    for nodes,new in zip(groups,new_parts):
        old=''.join(n.text or '' for n in nodes)
        for op,a,b,c,d in reversed(difflib.SequenceMatcher(a=old,b=new,autojunk=False).get_opcodes()):
            if op!='equal':range_edit(nodes,a,b,new[c:d])
    assert T(e)==p['new_text'],p['block_id']
    if maths:segment_audit.append({'block_id':p['block_id'],'math_texts':maths,'new_prose_segments':list(new_parts)})

src=E.fromstring(data['word/document.xml']);sb=src.find(W+'body')
scope={int(p['block_id'][1:]) for p in patches}
assert len(body)==len(sb)
for i,(a,b) in enumerate(zip(sb,body)):
    if i not in scope:assert c14(a)==c14(b),i
assert [c14(x) for x in X(src,'.//m:oMath')]==[c14(x) for x in X(r,'.//m:oMath')]
assert [c14(x) for x in X(src,'.//w:tbl')]==[c14(x) for x in X(r,'.//w:tbl')]
assert [c14(x) for x in X(src,'.//w:instrText|.//w:fldChar')]==[c14(x) for x in X(r,'.//w:instrText|.//w:fldChar')]
def fields(paragraph):
    result=[]
    depth=0;parts=[]
    for child in paragraph:
        begins=len(X(child,'.//w:fldChar[@w:fldCharType="begin"]'))
        ends=len(X(child,'.//w:fldChar[@w:fldCharType="end"]'))
        if begins or depth:parts.append(c14(child))
        depth+=begins-ends
        if ends and depth==0:result.append(parts);parts=[]
    assert depth==0
    return result
for i in scope:assert fields(sb[i])==fields(body[i]),('Cross-reference field changed',i)
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
   'patch_count':len(patches),'scope':'第三章 关系影响域约束的增强与成对学习',
   'native_math':len(X(r,'.//m:oMath')),'tables':len(X(r,'.//w:tbl')),
   'headings':headings,'changed_blocks':[p['block_id'] for p in patches]}
(O/'_work/revision_manifest.json').write_text(json.dumps(M,ensure_ascii=False,indent=2))
(O/'_work/math_segment_audit.json').write_text(json.dumps(segment_audit,ensure_ascii=False,indent=2))
print(json.dumps({k:M[k] for k in ['output','patch_count','native_math','tables']},ensure_ascii=False))
