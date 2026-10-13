from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from pypdf import PdfReader,PdfWriter
from PIL import Image,ImageChops
from collections import Counter
import hashlib,json,re,sys,unicodedata

O=Path(__file__).resolve().parents[1];ROOT=Path('/Users/channtang/Downloads/paper')
BASE=ROOT/'manuscript_review_test_20261011/v11_to_v12_model_figures_20261013/_render_01'
M=json.loads((O/'_work/revision_manifest.json').read_text())
patches=json.loads((O/'_work/patches.json').read_text())
S=Path(M['source']);D=Path(M['output']);render=O/sys.argv[1];P=render/(D.stem+'.pdf')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W='{'+N['w']+'}';X=lambda e,q:e.xpath(q,namespaces=N)
c14=lambda e:E.tostring(e,method='c14n')
T=lambda e:''.join(X(e,'.//w:t/text()|.//m:t/text()'))
assert sha(S)==M['source_sha256'] and sha(D)==M['output_sha256']
scope={int(p['block_id'][1:]) for p in patches}
with ZipFile(S) as a,ZipFile(D) as b:
    assert b.testzip() is None and set(a.namelist())==set(b.namelist())
    changed_parts=[n for n in a.namelist() if a.read(n)!=b.read(n)]
    assert changed_parts==['word/document.xml']
    old=E.fromstring(a.read('word/document.xml'));new=E.fromstring(b.read('word/document.xml'))
    ob=old.find(W+'body');nb=new.find(W+'body');assert len(ob)==len(nb)
    changed_blocks=[]
    toc_scope={int(p['block_id'][1:]) for p in M['toc_page_changes']}
    for i,(x,y) in enumerate(zip(ob,nb)):
        if c14(x)!=c14(y):changed_blocks.append(i)
        if i not in scope|toc_scope:assert c14(x)==c14(y),i
    assert set(changed_blocks)==scope|toc_scope
    for p in patches:
        i=int(p['block_id'][1:]);assert T(ob[i])==p['old_text'] and T(nb[i])==p['new_text']
        assert re.findall(r'\[\d+\]',T(ob[i]))==re.findall(r'\[\d+\]',T(nb[i]))
        nums=lambda s:Counter(re.findall(r'\d+(?:\.\d+)?',s))
        assert nums(T(ob[i]))==nums(T(nb[i]))
    for kind,count in [('m:oMath',380),('w:tbl',83)]:
        x=X(old,'.//'+kind);y=X(new,'.//'+kind)
        assert len(x)==len(y)==count and [c14(e) for e in x]==[c14(e) for e in y]
    assert [c14(e) for e in ob[234:]]==[c14(e) for e in nb[234:]]
    names=X(new,'.//w:bookmarkStart/@w:name');ids=X(new,'.//w:bookmarkStart/@w:id')
    assert len(names)==len(set(names)) and Counter(ids)==Counter(X(new,'.//w:bookmarkEnd/@w:id'))
    images=[n for n in a.namelist() if n.startswith('word/media/')]
    assert all(a.read(n)==b.read(n) for n in images)

r=PdfReader(P);oldpdf=PdfReader(ROOT/'论文规范排版稿_v12.pdf')
assert len(r.pages)==len(oldpdf.pages)==127
flat=[]
def walk(xs):
    for x in xs:
        if isinstance(x,list):walk(x)
        else:flat.append({'title':x.title,'page':r.get_destination_page_number(x)+1})
walk(r.outline)
assert flat==json.loads((O/'_work/outline.json').read_text()) and len(flat)==149
texts=[p.extract_text() for p in r.pages]
for bad in ['Qwen3.8','\ufffd','¿','Error! Reference source not found','Error! Bookmark not defined','错误!未定义书签']:
    assert bad not in '\n'.join(texts),bad
assert 'Keywords:' in texts[2] and texts[3].lstrip().startswith('目录')
norm=lambda t:re.sub(r'\s+','',unicodedata.normalize('NFKC',t))
prose=[]
for text in texts:
    lines=text.splitlines()
    if lines and norm(lines[0])=='面向关系感知学习与依赖闭合修正的端到端论辩挖掘方法研究':
        lines=lines[1:]
        if lines and lines[0].strip().isdigit():lines=lines[1:]
    if lines and lines[-1].strip().isdigit():lines=lines[:-1]
    prose.append('\n'.join(lines))
alltext=norm('\n'.join(prose));missing=[]
for p in patches:
    if norm(p['new_text']) not in alltext:missing.append(p['block_id'])
assert not missing,missing
for i in range(17,127):
    assert norm(texts[i])==norm(oldpdf.pages[i].extract_text()),('later_pdf_text_changed',i+1)
fonts={}
for page in r.pages:
    for ref in page['/Resources'].get('/Font',{}).values():
        f=ref.get_object();leaf=f['/DescendantFonts'][0].get_object() if f.get('/DescendantFonts') else f
        desc=leaf.get('/FontDescriptor')
        fonts[str(f.get('/BaseFont'))]=bool(desc and any(desc.get_object().get(k) for k in ['/FontFile','/FontFile2','/FontFile3']))
assert all(fonts.values())
same=[];changed=[];needs_view=[];already_viewed=[]
reviewed_02={2,3,*range(9,18)}
for i in range(1,128):
    current=Image.open(render/f'page-{i}.png').convert('RGB')
    base=Image.open(BASE/f'page-{i}.png').convert('RGB')
    assert current.size==base.size
    if ImageChops.difference(base,current).getbbox() is None:same.append(i)
    else:
        changed.append(i)
        prev=Image.open(O/f'_render_02/page-{i}.png').convert('RGB')
        if i in reviewed_02 and ImageChops.difference(prev,current).getbbox() is None:already_viewed.append(i)
        else:needs_view.append(i)
w=PdfWriter();w.clone_document_from_reader(r)
body=M['body_first_physical_page'];assert body==9
w.set_page_label(0,0,prefix='封面',start=1)
w.set_page_label(1,body-2,style='/R',start=1)
w.set_page_label(body-1,len(r.pages)-1,style='/D',start=1)
F=O/(D.stem+'.pdf');w.write(F)
final=PdfReader(F)
assert final.page_labels==oldpdf.page_labels
assert [p.get_contents().get_data() for p in r.pages]==[p.get_contents().get_data() for p in final.pages]
report={'source_preserved':True,'source_sha256':sha(S),'docx_sha256':sha(D),'pdf_sha256':sha(F),
        'changed_paragraphs':len(patches),'abstract_paragraphs':6,'intro_paragraphs':40,
        'all_citation_sequences_and_literal_numbers_preserved':True,
        'all_later_chapters_xml_identical':True,'native_math_identical':380,'tables_identical':83,
        'media_parts_identical':len(images),'pages':127,'outline_entries':149,
        'later_pdf_pages_normalized_text_identical':110,
        'toc_pages_changed':len(M['toc_page_changes']),'fonts_embedded':len(fonts),
        'revised_paragraphs_found_in_pdf':len(patches),'render_dir':str(render),
        'pixel_identical_to_v12':same,'changed_pages':changed,
        'already_reviewed_pixel_identical_to_draft02':already_viewed,'remaining_visual_check_pages':needs_view}
(O/'_work/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='pixel_identical_to_v12'},ensure_ascii=False,indent=2))
