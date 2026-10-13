from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from pypdf import PdfReader, PdfWriter
from PIL import Image, ImageChops
import hashlib,json,re

O=Path(__file__).resolve().parents[1]
ROOT=Path('/Users/channtang/Downloads/paper')
V11=ROOT/'manuscript_review_test_20261011/v10_to_v11_chapter_revision_20261013'
S=ROOT/'论文规范排版稿_v11.docx';D=O/'论文规范排版稿_v12.docx'
P=O/'_render_01/论文规范排版稿_v12.pdf'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm':'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'asvg':'http://schemas.microsoft.com/office/drawing/2016/SVG/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
X=lambda e,q:e.xpath(q,namespaces=NS)
c14=lambda e:E.tostring(e,method='c14n')
with ZipFile(S) as a,ZipFile(D) as b:
    assert b.testzip() is None
    added=sorted(set(b.namelist())-set(a.namelist()))
    changed=sorted(n for n in a.namelist() if a.read(n)!=b.read(n))
    assert added==[f'word/media/image{i}_v12.png' for i in [3,5,6]]
    assert changed==sorted(['word/document.xml','word/_rels/document.xml.rels']+[f'word/media/image{i}.svg' for i in [3,5,6]])
    old=E.fromstring(a.read('word/document.xml'));new=E.fromstring(b.read('word/document.xml'))
    assert X(old,'.//w:t/text()|.//m:t/text()')==X(new,'.//w:t/text()|.//m:t/text()')
    om=X(old,'.//m:oMath');nm=X(new,'.//m:oMath')
    assert len(om)==len(nm)==380 and [c14(x) for x in om]==[c14(x) for x in nm]
    ot=X(old,'.//w:tbl');nt=X(new,'.//w:tbl')
    assert len(ot)==len(nt)==83 and [c14(x) for x in ot]==[c14(x) for x in nt]
    assert X(old,'.//wp:extent/@cx|.//wp:extent/@cy')==X(new,'.//wp:extent/@cx|.//wp:extent/@cy')
    for i in [3,5,6]:
        svg=b.read(f'word/media/image{i}.svg').decode()
        assert 'Qwen3.8' not in svg and '27B' not in svg and 'Qwen3.5' in svg
        assert not any('16' in t and '注意力块' in t for t in E.fromstring(svg.encode()).xpath('//*[local-name()="text"]/text()'))
    # Only image references and alternative descriptions may differ in document.xml.
    for tree in [old,new]:
        for p in tree.findall('{'+NS['w']+'}body'):
            for node in X(p,'.//a:blip'):
                node.attrib.pop('{'+NS['r']+'}embed',None)
            for node in X(p,'.//wp:docPr'):
                node.attrib.pop('descr',None)
    assert c14(old)==c14(new)

oldpdf=PdfReader(V11/'_render_07/论文规范排版稿_v11.pdf');r=PdfReader(P)
assert len(r.pages)==len(oldpdf.pages)==127
def outline(reader):
    out=[]
    def walk(items):
        for item in items:
            if isinstance(item,list):walk(item)
            else:out.append((item.title,reader.get_destination_page_number(item)+1))
    walk(reader.outline)
    return out
assert outline(r)==outline(oldpdf) and len(outline(r))==149
texts=[p.extract_text() for p in r.pages]
for bad in ['Qwen3.8','\ufffd','¿','Error! Reference source not found','Error! Bookmark not defined','错误!未定义书签']:
    assert bad not in '\n'.join(texts),bad
pixels=[];same=[]
for i in range(1,128):
    a=Image.open(V11/f'_render_07/page-{i}.png').convert('RGB')
    b=Image.open(O/f'_render_01/page-{i}.png').convert('RGB')
    assert a.size==b.size
    box=ImageChops.difference(a,b).getbbox()
    if box:pixels.append({'page':i,'changed_bbox':box})
    else:same.append(i)
assert [v['page'] for v in pixels]==[28,39,51],pixels
fonts={}
for page in r.pages:
    for ref in page['/Resources'].get('/Font',{}).values():
        f=ref.get_object();leaf=f['/DescendantFonts'][0].get_object() if f.get('/DescendantFonts') else f
        desc=leaf.get('/FontDescriptor')
        fonts[str(f.get('/BaseFont'))]=bool(desc and any(desc.get_object().get(k) for k in ['/FontFile','/FontFile2','/FontFile3']))
assert fonts and all(fonts.values())
w=PdfWriter();w.clone_document_from_reader(r)
w.set_page_label(0,0,prefix='封面',start=1)
w.set_page_label(1,7,style='/R',start=1)
w.set_page_label(8,126,style='/D',start=1)
F=O/'论文规范排版稿_v12.pdf';w.write(F)
final=PdfReader(F)
assert final.page_labels==PdfReader(ROOT/'论文规范排版稿_v11.pdf').page_labels
assert [p.get_contents().get_data() for p in r.pages]==[p.get_contents().get_data() for p in final.pages]
M={'source_sha256':sha(S),'docx_sha256':sha(D),'pdf_sha256':sha(F),
   'source_preserved':True,'pages':127,'native_math_identical':380,'tables_identical':83,
   'all_body_text_unchanged':True,'toc_entries_same_page':149,'embedded_fonts':len(fonts),
   'changed_package_parts':changed,'added_package_parts':added,
   'pixel_identical_pages':same,'changed_pages':pixels,
   'remaining_visual_check_pages':[28,39,51],
   'configuration_source':'作者确认以正文 Qwen3.5-9B 为准；全注意力块数量与正文统一为8。',
   'runtime_configuration_independently_audited':False}
(O/'_work/verification.json').write_text(json.dumps(M,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in M.items() if k!='pixel_identical_pages'},ensure_ascii=False,indent=2))
