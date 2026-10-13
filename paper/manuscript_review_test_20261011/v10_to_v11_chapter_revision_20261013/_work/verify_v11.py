from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from collections import Counter
from pypdf import PdfReader, PdfWriter
import re, json, hashlib, sys, pdfplumber, unicodedata

O=Path(__file__).resolve().parents[1]
render=O/sys.argv[1]
M=json.loads((O/'_work/revision_manifest.json').read_text())
S=Path(M['source']);D=Path(M['output']);P=render/(D.stem+'.pdf')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W='{'+NS['w']+'}'
X=lambda e,q:e.xpath(q,namespaces=NS)
T=lambda e:''.join(X(e,'.//w:t/text()|.//m:t/text()'))
num=lambda t:re.findall(r'[-+−]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?',t)
c14=lambda e:E.tostring(e,method='c14n')
assert sha(S)==M['source_sha256']
assert sha(D)==M['output_sha256']
with ZipFile(S) as zs,ZipFile(D) as zd:
    assert zs.testzip() is None and zd.testzip() is None
    assert set(zs.namelist())<=set(zd.namelist())
    changed_parts=[n for n in zs.namelist() if zs.read(n)!=zd.read(n)]
    s=E.fromstring(zs.read('word/document.xml')); d=E.fromstring(zd.read('word/document.xml'))
    sb=s.find(W+'body');db=d.find(W+'body');assert len(sb)==len(db)
    # All source references remain verbatim; the final reference only gains formatting.
    assert [T(e) for e in sb[851:906]]==[T(e) for e in db[851:906]]
    sm=X(s,'.//m:oMath');dm=X(d,'.//m:oMath');assert len(sm)==len(dm)==380
    math_deltas=[i for i,(a,b) in enumerate(zip(sm,dm)) if c14(a)!=c14(b)]
    assert len(math_deltas)==1
    assert X(sb[420],'.//m:oMath')[0] is sm[math_deltas[0]]
    assert T(dm[math_deltas[0]]).replace(', ','')==T(sm[math_deltas[0]])
    assert len(X(s,'.//w:tbl'))==len(X(d,'.//w:tbl'))==83
    numeric_cells=0;changed_cells=[]
    for i,(a,b) in enumerate(zip(sb,db)):
        if a.tag!=W+'tbl':continue
        old=X(a,'.//w:tc');new=X(b,'.//w:tc');assert len(old)==len(new)
        for c,(x,y) in enumerate(zip(old,new)):
            if i!=1019:assert num(T(x))==num(T(y)),('cell_number_changed',i,c,T(x),T(y))
            numeric_cells+=1
            if T(x)!=T(y):changed_cells.append({'block_id':f'B{i:04d}','cell':c,'before':T(x),'after':T(y)})
    # The one exception changes references, not numerical findings.
    assert '表S2-9' not in T(db[1019])
    assert 'S2.3' in T(db[1019]) and 'S2.5' in T(db[1019]) and 'S2.6' in T(db[1019])
    names=X(d,'.//w:bookmarkStart/@w:name');ids=X(d,'.//w:bookmarkStart/@w:id')
    assert len(names)==len(set(names)) and len(ids)==len(set(ids))
    assert Counter(ids)==Counter(X(d,'.//w:bookmarkEnd/@w:id'))
    assert all(n in names for n in X(d,'.//w:hyperlink/@w:anchor'))
    cache=json.loads((O/'_work/toc_pages.json').read_text());found={}
    for p in db:
        instr=''.join(X(p,'.//w:instrText/text()'));mt=re.search(r'HYPERLINK\s+\\l\s+"(v9_toc_\d+)"',instr)
        if mt:
            assert mt.group(1) in names
            found[mt.group(1)]=X(p,'.//w:t/text()')[-1]
    assert found==cache and len(cache)==149
    equations=[n for n in names if n.startswith('Equation_')]
    assert equations==[n for n in X(s,'.//w:bookmarkStart/@w:name') if n.startswith('Equation_')]
    added_parts=set(zd.namelist())-set(zs.namelist())
    if not M['figure_changes']:
        assert changed_parts==['word/document.xml'] and not added_parts
    alltext='\n'.join(T(e) for e in db)
    assert '表S2-9' not in alltext

r=PdfReader(P);flat=[]
def walk(xs):
    for x in xs:
        if isinstance(x,list):walk(x)
        else:flat.append({'title':x.title,'page':r.get_destination_page_number(x)+1})
walk(r.outline)
assert flat==json.loads((O/'_work/outline.json').read_text()),'pagination changed after TOC synchronization'
texts=[p.extract_text() for p in r.pages]
assert all(t.strip() for t in texts)
for bad in ['Error! Reference source not found','Error! Bookmark not defined','错误!未定义书签','\ufffd','¿']:
    assert bad not in '\n'.join(texts),bad
fonts={}
for page in r.pages:
    for ref in page['/Resources'].get('/Font',{}).values():
        f=ref.get_object();leaf=f['/DescendantFonts'][0].get_object() if f.get('/DescendantFonts') else f
        desc=leaf.get('/FontDescriptor')
        fonts[str(f.get('/BaseFont'))]=bool(desc and any(desc.get_object().get(k) for k in ['/FontFile','/FontFile2','/FontFile3']))
assert fonts and all(fonts.values()),fonts
outside=[];red=[]
with pdfplumber.open(P) as pdf:
    for i,p in enumerate(pdf.pages,1):
        assert abs(p.width-595.3)<1 and abs(p.height-841.9)<1
        bad=[c for c in p.chars if c['text'].strip() and 65<c['top']<790 and (c['x0']<67 or c['x1']>530)]
        if bad:outside.append({'page':i,'chars':[(c['text'],round(c['x0'],1),round(c['x1'],1)) for c in bad[:20]]})
        bad=[c for c in p.chars if isinstance(c.get('non_stroking_color'),tuple) and c['non_stroking_color'][:3]==(0.5,0,0)]
        if bad:red.append({'page':i,'chars':''.join(c['text'] for c in bad)})
assert not outside,outside
assert not red,red
# Detect missing Chinese glyphs in continuous non-math prose in the final PDF.
norm=lambda t:re.sub(r'\s+','',unicodedata.normalize('NFKC',t))
prose=[]
for t in texts:
    lines=t.splitlines()
    if lines and norm(lines[0])=='面向关系感知学习与依赖闭合修正的端到端论辩挖掘方法研究':
        lines=lines[1:]
        if lines and lines[0].strip().isdigit():lines=lines[1:]
    prose.append('\n'.join(lines))
pdftext=norm('\n'.join(prose));unmatched=[];checked=0
for i,e in enumerate(db):
    if i<169 or e.tag!=W+'p' or X(e,'.//m:oMath|.//w:drawing'):continue
    t=norm(T(e))
    if not t or len(t)<12:continue
    checked+=1
    if t not in pdftext:unmatched.append({'block_id':f'B{i:04d}','text':t})
body=M['body_first_physical_page']
w=PdfWriter();w.clone_document_from_reader(r)
w.set_page_label(0,0,prefix='封面',start=1)
w.set_page_label(1,body-2,style='/R',start=1)
w.set_page_label(body-1,len(r.pages)-1,style='/D',start=1)
F=O/(D.stem+'.pdf');w.write(F);final=PdfReader(F)
assert [p.get_contents().get_data() for p in r.pages]==[p.get_contents().get_data() for p in final.pages]
assert all(cache[h['bookmark']]==final.page_labels[v['page']-1] for h,v in zip(M['headings'],flat))
report={'source_preserved':True,'source_sha256':sha(S),'docx_sha256':sha(D),'pdf_sha256':sha(F),'pages':len(r.pages),
        'body_first_physical_page':body,'printed_body_pages':len(r.pages)-body+1,'patch_count':M['patch_count'],
        'tables':83,'table_cells_checked':numeric_cells,'changed_table_cells':changed_cells,'all_experimental_numbers_preserved':True,
        'native_math':380,'native_math_byte_preserved':379,'math_layout_only':['3-9'],'numbered_equations':len(equations),
        'references_verbatim':54,'toc_entries':149,'fonts_embedded':len(fonts),'margin_overflow':outside,'red_error_glyphs':red,
        'plain_prose_checked':checked,'plain_prose_unmatched':unmatched,'changed_package_parts':changed_parts,
        'figure_changes':M['figure_changes'],'render_dir':str(render),'model_runs_executed_in_revision':False}
(O/'_work/delivery_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(O/'_work/pdf_fulltext.txt').write_text('\n\n'.join(f'PAGE {i}\n{t}' for i,t in enumerate(texts,1)))
print(json.dumps({k:v for k,v in report.items() if k!='changed_table_cells'},ensure_ascii=False,indent=2))
