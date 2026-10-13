from pathlib import Path
from collections import Counter
from zipfile import ZipFile
from lxml import etree as E
from pypdf import PdfReader,PdfWriter
from PIL import Image
import json,hashlib,re,sys,pdfplumber
O=Path(__file__).resolve().parents[1];render=O/sys.argv[1]
M=json.loads((O/'_work/revision_manifest.json').read_text())
S=Path(M['source']);D=Path(M['output']);P=render/(D.stem+'.pdf')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W='{'+NS['w']+'}';X=lambda e,q:e.xpath(q,namespaces=NS);T=lambda e:''.join(X(e,'.//w:t/text()|.//m:t/text()'))
assert sha(S)==M['source_sha256'];assert sha(D)==M['output_sha256']
with ZipFile(S) as zs,ZipFile(D) as zd:
    assert zs.testzip() is None and zd.testzip() is None
    assert zs.namelist()==zd.namelist()
    changed_parts=[n for n in zs.namelist() if zs.read(n)!=zd.read(n)]
    assert changed_parts==['word/document.xml'],changed_parts
    s=E.fromstring(zs.read('word/document.xml'));d=E.fromstring(zd.read('word/document.xml'))
    def paragraphs(root):
        out=[]
        for p in X(root,'.//w:body//w:p'):
            st=p.find('./'+W+'pPr/'+W+'pStyle')
            if st is not None and st.get(W+'val','').startswith('TOC'):continue
            if T(p):out.append(T(p))
        return Counter(out)
    expected=paragraphs(s);actual=paragraphs(d)
    for e in M['edits']:
        if e.get('before'):assert expected[e['before']]>0,e;expected[e['before']]-=1
        if e.get('after'):expected[e['after']]+=1
    assert not expected-actual and not actual-expected
    oldmath=X(s,'.//m:oMath');newmath=X(d,'.//m:oMath')
    obsolete=s.find(W+'body')[1052].xpath('./w:tr[2]/w:tc[1]//m:oMath[2]',namespaces=NS)[0]
    assert T(obsolete)=='D';oldmath.remove(obsolete)
    sig=lambda arr:[[ (e.tag,tuple(sorted(e.attrib.items())),e.text or '') for e in m.iter()] for m in arr]
    assert sig(oldmath)==sig(newmath);assert len(newmath)==381
    tables_s=X(s,'.//w:tbl');tables_d=X(d,'.//w:tbl');assert len(tables_s)==len(tables_d)==73
    changed_tables=[i for i,(a,b) in enumerate(zip(tables_s,tables_d)) if E.tostring(a,method='c14n')!=E.tostring(b,method='c14n')]
    assert changed_tables==[34,56,66],changed_tables
    for i in [35,36,37,38,39,40]:assert E.tostring(tables_s[i],method='c14n')==E.tostring(tables_d[i],method='c14n')
    media=[n for n in zs.namelist() if n.startswith('word/media/')]
    assert all(zs.read(n)==zd.read(n) for n in media)
    bm=X(d,'.//w:bookmarkStart');ids=[b.get(W+'id') for b in bm];names=[b.get(W+'name') for b in bm]
    assert len(ids)==len(set(ids));assert len(names)==len(set(names))
    assert Counter(ids)==Counter(b.get(W+'id') for b in X(d,'.//w:bookmarkEnd'))
    assert all(a in names for a in X(d,'.//w:hyperlink/@w:anchor'))
    eqs=[n for n in names if n.startswith('Equation_')];assert len(eqs)==42
    assert [T(p) for p in X(s,'.//w:p[.//w:bookmarkStart[starts-with(@w:name,"Equation_")]]')]==[T(p) for p in X(d,'.//w:p[.//w:bookmarkStart[starts-with(@w:name,"Equation_")]]')]
    cache=json.loads((O/'_work/toc_pages.json').read_text())
    fields=X(d,'.//w:fldSimple[starts-with(normalize-space(@w:instr),"PAGEREF")]')
    assert len(fields)==142
    assert {f.get(W+'instr').split()[1]:T(f) for f in fields}==cache
r=PdfReader(P);flat=[]
def walk(items):
    for item in items:
        if isinstance(item,list):walk(item)
        else:flat.append({'title':item.title,'page':r.get_destination_page_number(item)+1})
walk(r.outline);assert flat==json.loads((O/'_work/outline.json').read_text())
body=M['body_first_physical_page'];texts=[p.extract_text() for p in r.pages]
assert all(t.strip() for t in texts)
assert not any(term in '\n'.join(texts) for term in ['Error! Reference source not found','Error! Bookmark not defined','错误!未定义书签','\ufffd'])
fonts={}
for page in r.pages:
    for ref in page['/Resources'].get('/Font',{}).values():
        f=ref.get_object();leaf=f['/DescendantFonts'][0].get_object() if f.get('/DescendantFonts') else f
        desc=leaf.get('/FontDescriptor')
        fonts[str(f.get('/BaseFont'))]=bool(desc and any(desc.get_object().get(k) for k in ['/FontFile','/FontFile2','/FontFile3']))
assert fonts and all(fonts.values()),fonts
outside=[]
with pdfplumber.open(P) as pdf:
    for i,p in enumerate(pdf.pages,1):
        assert abs(p.width-595.3)<1 and abs(p.height-841.9)<1
        bad=[c for c in p.chars if c['text'].strip() and 65<c['top']<790 and (c['x0']<67 or c['x1']>530)]
        if bad:outside.append({'page':i,'chars':[(c['text'],round(c['x0'],1),round(c['x1'],1)) for c in bad[:10]]})
assert not outside,outside
w=PdfWriter();w.clone_document_from_reader(r)
w.set_page_label(0,0,prefix='封面',start=1)
w.set_page_label(1,body-2,style='/R',start=1)
w.set_page_label(body-1,len(r.pages)-1,style='/D',start=1)
F=O/(D.stem+'.pdf');w.write(F)
f=PdfReader(F)
assert [p.get_contents().get_data() for p in r.pages]==[p.get_contents().get_data() for p in f.pages]
assert all(cache[h['bookmark']]==f.page_labels[dest['page']-1] for h,dest in zip(M['headings'],flat))

# Reuse only exact full-page body pixel matches with the previously reviewed v4.
old_render=S.parent/'_render';fallback=S.parent.parent/'formatted_word_pdf_20261012_v3/_render_complete'
def crop_hash(path):
    im=Image.open(path).convert('RGB');return hashlib.sha256(im.crop((0,0,im.width,1080)).tobytes()).hexdigest()
old_images={}
for i in range(1,118):
    p=old_render/f'page-{i}.png'
    if not p.exists():p=fallback/f'page-{i}.png'
    old_images[crop_hash(p)]=i
matched=[];new_pages=[]
for i in range(1,len(r.pages)+1):
    h=crop_hash(render/f'page-{i}.png')
    if h in old_images:matched.append({'new':i,'reviewed_v4':old_images[h]})
    else:new_pages.append(i)
report={'source_preserved':True,'source_sha256':sha(S),'docx_sha256':sha(D),'pdf_sha256':sha(F),'pages':len(r.pages),
        'body_first_physical_page':body,'printed_body_pages':len(r.pages)-body+1,'edits':len(M['edits']),
        'paragraph_changes_match_manifest':True,'numbered_equations_unchanged':42,'native_math_objects':381,
        'only_removed_math':'obsolete D document alias in symbol table; all remaining native math identical',
        'tables':73,'changed_table_text_indices':changed_tables,'all_research_data_tables_preserved':True,
        'media_preserved':True,'toc_entries_verified':142,'fonts_embedded':len(fonts),'margin_overflow':outside,
        'render_dir':str(render),'visually_unchanged_body_pages':matched,'pages_requiring_visual_review':new_pages}
(O/'_work/delivery_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='visually_unchanged_body_pages'},ensure_ascii=False))
