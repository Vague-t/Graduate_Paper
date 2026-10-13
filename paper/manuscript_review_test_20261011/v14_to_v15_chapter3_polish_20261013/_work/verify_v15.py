from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from pypdf import PdfReader,PdfWriter
from PIL import Image,ImageChops
from collections import Counter
import hashlib,json,re,sys,unicodedata

O=Path(__file__).resolve().parents[1];ROOT=Path('/Users/channtang/Downloads/paper')
BASE=ROOT/'manuscript_review_test_20261011/v13_to_v14_chapter2_polish_20261013/_render_03'
M=json.loads((O/'_work/revision_manifest.json').read_text());patches=json.loads((O/'_work/patches.json').read_text())
S=Path(M['source']);D=Path(M['output']);render=O/sys.argv[1];P=render/(D.stem+'.pdf')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W='{'+N['w']+'}';X=lambda e,q:e.xpath(q,namespaces=N)
c14=lambda e:E.tostring(e,method='c14n');T=lambda e:''.join(X(e,'.//w:t/text()|.//m:t/text()'))
assert sha(S)==M['source_sha256'] and sha(D)==M['output_sha256']
scope={int(p['block_id'][1:]) for p in patches}
with ZipFile(S) as a,ZipFile(D) as b:
    assert b.testzip() is None and set(a.namelist())==set(b.namelist())
    assert [n for n in a.namelist() if a.read(n)!=b.read(n)]==['word/document.xml']
    old=E.fromstring(a.read('word/document.xml'));new=E.fromstring(b.read('word/document.xml'))
    ob=old.find(W+'body');nb=new.find(W+'body');assert len(ob)==len(nb)
    changed=[];toc_scope=set()
    # Page cache may need updates; every other part of a TOC paragraph must stay intact.
    for i,(x,y) in enumerate(zip(ob,nb)):
        if c14(x)==c14(y):continue
        changed.append(i)
        if i in scope:continue
        assert i<169 and X(x,'.//w:instrText') and X(y,'.//w:instrText'),('out_of_scope',i)
        xc=E.fromstring(E.tostring(x));yc=E.fromstring(E.tostring(y))
        nx=X(xc,'.//w:t');ny=X(yc,'.//w:t');assert len(nx)==len(ny)
        assert (nx[-1].text or '').isdigit() and (ny[-1].text or '').isdigit()
        nx[-1].text=ny[-1].text
        assert c14(xc)==c14(yc),('toc_nonpage_change',i)
        toc_scope.add(i)
    assert set(changed)==scope|toc_scope
    for p in patches:
        i=int(p['block_id'][1:]);assert T(ob[i])==p['old_text'] and T(nb[i])==p['new_text']
        assert re.findall(r'\[\d+\]',T(ob[i]))==re.findall(r'\[\d+\]',T(nb[i]))
        nums=lambda s:Counter(re.findall(r'\d+(?:\.\d+)?',s))
        assert nums(T(ob[i]))==nums(T(nb[i]))
    for kind,count in [('m:oMath',380),('w:tbl',83)]:
        x=X(old,'.//'+kind);y=X(new,'.//'+kind)
        assert len(x)==len(y)==count and [c14(e) for e in x]==[c14(e) for e in y]
    assert [c14(e) for e in ob[169:329]]==[c14(e) for e in nb[169:329]]
    assert [c14(e) for e in ob[526:]]==[c14(e) for e in nb[526:]]
    assert [c14(e) for e in X(old,'.//w:instrText|.//w:fldChar')]==[c14(e) for e in X(new,'.//w:instrText|.//w:fldChar')]
    names=X(new,'.//w:bookmarkStart/@w:name');ids=X(new,'.//w:bookmarkStart/@w:id')
    assert len(names)==len(set(names)) and Counter(ids)==Counter(X(new,'.//w:bookmarkEnd/@w:id'))
    images=[n for n in a.namelist() if n.startswith('word/media/')]
    assert all(a.read(n)==b.read(n) for n in images)

r=PdfReader(P);oldpdf=PdfReader(ROOT/'论文规范排版稿_v14.pdf');flat=[]
def walk(xs):
    for x in xs:
        if isinstance(x,list):walk(x)
        else:flat.append({'title':x.title,'page':r.get_destination_page_number(x)+1})
walk(r.outline)
assert flat==json.loads((O/'_work/outline.json').read_text()) and len(flat)==149
texts=[p.extract_text() for p in r.pages]
for bad in ['Qwen3.8','\ufffd','¿','Error! Reference source not found','Error! Bookmark not defined','错误!未定义书签']:
    assert bad not in '\n'.join(texts),bad
norm=lambda t:re.sub(r'\s+','',unicodedata.normalize('NFKC',t))
title='面向关系感知学习与依赖闭合修正的端到端论辩挖掘方法研究'
def prose(text):
    lines=text.splitlines()
    if lines and norm(lines[0])==title:
        lines=lines[1:]
        if lines and lines[0].strip().isdigit():lines=lines[1:]
    if lines and lines[-1].strip().isdigit():lines=lines[:-1]
    return '\n'.join(lines)
alltext=norm('\n'.join(prose(t) for t in texts));missing=[];segment_verified=[]
math_audit={p['block_id']:p for p in json.loads((O/'_work/math_segment_audit.json').read_text())}
for p in patches:
    if norm(p['new_text']) not in alltext:
        audit=math_audit.get(p['block_id'])
        assert audit,('unmatched_plain_prose',p['block_id'])
        # OMML delimiters/fractions render visible glyphs not stored in m:t.
        # Match every unchanged-math-separated prose segment in order.
        pattern='.{0,250}?'.join(re.escape(norm(t)) for t in audit['new_prose_segments'])
        if not re.search(pattern,alltext):missing.append(p['block_id'])
        else:segment_verified.append(p['block_id'])
assert not missing,missing
assert all(norm(prose(texts[i]))==norm(prose(oldpdf.pages[i].extract_text())) for i in [0,1,2,*range(8,28)])
start2=next(x['page'] for x in flat if x['title'].startswith('第三章 '))
start3=next(x['page'] for x in flat if x['title'].startswith('第四章 '))
old3=50
assert norm('\n'.join(prose(t) for t in texts[start3-1:]))==norm('\n'.join(prose(p.extract_text()) for p in oldpdf.pages[old3-1:])), 'later_pdf_text_changed'
fonts={}
for page in r.pages:
    for ref in page['/Resources'].get('/Font',{}).values():
        f=ref.get_object();leaf=f['/DescendantFonts'][0].get_object() if f.get('/DescendantFonts') else f
        desc=leaf.get('/FontDescriptor')
        fonts[str(f.get('/BaseFont'))]=bool(desc and any(desc.get_object().get(k) for k in ['/FontFile','/FontFile2','/FontFile3']))
assert all(fonts.values())
same=[];changed=[]
for i in range(1,len(r.pages)+1):
    current=Image.open(render/f'page-{i}.png').convert('RGB')
    oldn=i if i<start3 else i-start3+old3
    if not 1<=oldn<=len(oldpdf.pages):changed.append(i);continue
    base=Image.open(BASE/f'page-{oldn}.png').convert('RGB')
    if current.size==base.size and ImageChops.difference(base,current).getbbox() is None:same.append({'page':i,'v14_page':oldn})
    else:changed.append(i)
w=PdfWriter();w.clone_document_from_reader(r)
body=M['body_first_physical_page'];assert body==9
w.set_page_label(0,0,prefix='封面',start=1)
w.set_page_label(1,body-2,style='/R',start=1)
w.set_page_label(body-1,len(r.pages)-1,style='/D',start=1)
F=O/(D.stem+'.pdf');w.write(F);final=PdfReader(F)
assert [p.get_contents().get_data() for p in r.pages]==[p.get_contents().get_data() for p in final.pages]
report={'source_preserved':True,'source_sha256':sha(S),'docx_sha256':sha(D),'pdf_sha256':sha(F),
        'changed_paragraphs':len(patches),'all_citation_sequences_and_literal_numbers_preserved':True,
        'other_chapters_xml_identical':True,'native_math_identical':380,'tables_identical':83,
        'media_parts_identical':len(images),'pages':len(r.pages),'outline_entries':149,
        'toc_page_cache_changed_vs_source':len(toc_scope),'fonts_embedded':len(fonts),
        'revised_paragraphs_found_in_pdf':len(patches),'math_paragraphs_verified_by_prose_segments':segment_verified,'render_dir':str(render),
        'chapter3_physical_pages':[start2,start3-1],'pixel_identical_to_v14':same,
        'remaining_visual_check_pages':changed}
(O/'_work/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='pixel_identical_to_v14'},ensure_ascii=False,indent=2))
