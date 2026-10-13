from pathlib import Path
from zipfile import ZipFile
from lxml import etree
from pypdf import PdfReader, PdfWriter
import hashlib, json, re

O=Path(__file__).resolve().parents[1]
M=json.loads((O/'_work/figure_insertion_manifest.json').read_text())
S=Path(M['source']);D=Path(M['output'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S)==M['source_sha256']
assert sha(D)==M['output_sha256']
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'm':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
xp=lambda e,q:e.xpath(q,namespaces=NS)
txt=lambda e:''.join(xp(e,'.//w:t/text()|.//m:t/text()'))
with ZipFile(S) as zs,ZipFile(D) as zd:
    assert zs.testzip() is None and zd.testzip() is None
    assert zs.namelist()==zd.namelist()
    changed_parts=[n for n in zs.namelist() if zs.read(n)!=zd.read(n)]
    assert set(changed_parts)==set(M['allowed_changed_parts'])
    s=etree.fromstring(zs.read('word/document.xml'))
    d=etree.fromstring(zd.read('word/document.xml'))
    expected=[txt(p).replace(M['caption_before'],M['caption_after']) for p in xp(s,'.//w:p')]
    assert expected==[txt(p) for p in xp(d,'.//w:p')]
    for tag,count in [('m:oMath',382),('w:tbl',73),('w:sectPr',3),('w:bookmarkStart',248),('w:bookmarkEnd',248)]:
        before=xp(s,'.//'+tag);after=xp(d,'.//'+tag)
        assert len(before)==len(after)==count,(tag,len(after))
        assert [etree.tostring(x,method='c14n') for x in before]==[etree.tostring(x,method='c14n') for x in after],tag
    media=[n for n in zd.namelist() if n.startswith('word/media/')]
    assert zd.read(M['replaced_media_part'])==Path(M['figure']).read_bytes()
    assert all(zs.read(n)==zd.read(n) for n in media if n!=M['replaced_media_part'])
old_pdf=S.with_suffix('.pdf')
new_pdf=O/'_render/论文规范排版稿_v4.pdf'
old=PdfReader(old_pdf);new=PdfReader(new_pdf)
assert len(old.pages)==len(new.pages)==117
def outline(reader):
    result=[]
    def walk(items):
        for item in items:
            if isinstance(item,list):walk(item)
            else:result.append((item.title,reader.get_destination_page_number(item)+1))
    walk(reader.outline);return result
assert outline(old)==outline(new)
changed_pages=[i for i in range(1,118) if sha(O/f'_render/page-{i}.png')!=sha(S.parent/f'_render_complete/page-{i}.png')]
texts=[p.extract_text() for p in new.pages]
norm=lambda t:re.sub(r'\s+','',t)
assert sum(norm(M['caption_after']) in norm(text) for text in texts)==1
figure_page=next(i+1 for i,text in enumerate(texts) if norm(M['caption_after']) in norm(text))
assert 9<=figure_page<18
assert all(t.strip() for t in texts)
assert all('Error! Reference source not found' not in t and '\ufffd' not in t for t in texts)
for i,(op,np) in enumerate(zip(old.pages,new.pages),1):
    if i!=figure_page:assert op.extract_text()==np.extract_text(),i
final=O/'论文规范排版稿_v4.pdf'
w=PdfWriter();w.clone_document_from_reader(new)
w.set_page_label(0,0,prefix='封面',start=1)
w.set_page_label(1,7,style='/R',start=1)
w.set_page_label(8,116,style='/D',start=1)
w.write(final)
f=PdfReader(final)
assert f.page_labels==old.page_labels
assert [p.get_contents().get_data() for p in new.pages]==[p.get_contents().get_data() for p in f.pages]
result={'passed_structural_checks':True,'source_preserved':True,'changed_parts':changed_parts,
        'changed_pages':changed_pages,'figure_physical_page':figure_page,
        'figure_printed_page':f.page_labels[figure_page-1],'pages':117,'toc_destinations_unchanged':True,
        'all_other_paragraph_text_preserved':True,'math_objects':382,'tables':73,
        'other_media_preserved':True,'section_styles_headers_footers_preserved':True,
        'docx_sha256':sha(D),'pdf_sha256':sha(final),'figure_sha256':sha(Path(M['figure']))}
(O/'_work/delivery_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
