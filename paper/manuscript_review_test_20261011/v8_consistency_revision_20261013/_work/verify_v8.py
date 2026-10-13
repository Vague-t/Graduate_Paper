from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from collections import Counter
from pypdf import PdfReader,PdfWriter
import json,hashlib,re,sys,pdfplumber

O=Path(__file__).resolve().parents[1];render=O/sys.argv[1]
M=json.loads((O/'_work/revision_manifest.json').read_text())
S=Path(M['source']);D=Path(M['output']);P=render/(D.stem+'.pdf')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W='{'+NS['w']+'}'; X=lambda e,q:e.xpath(q,namespaces=NS);T=lambda e:''.join(X(e,'.//w:t/text()|.//m:t/text()'))
assert sha(S)==M['source_sha256'];assert sha(D)==M['output_sha256']
with ZipFile(S) as zs,ZipFile(D) as zd:
    assert zs.testzip() is None and zd.testzip() is None
    assert zs.namelist()==zd.namelist()
    changed_parts=[n for n in zs.namelist() if zs.read(n)!=zd.read(n)]
    expected_parts=['word/document.xml']+[f'word/media/image{i}.png' for i in range(1,4)]+[f'word/media/model_architecture_{i}.svg' for i in range(1,4)]
    assert set(changed_parts)==set(expected_parts),changed_parts
    s=E.fromstring(zs.read('word/document.xml'));d=E.fromstring(zd.read('word/document.xml'))
    sb=s.find(W+'body');db=d.find(W+'body');assert len(sb)==len(db)
    edits={e['block_id']:e['after'] for e in M['edits']}
    changed=[]
    for i,(a,b) in enumerate(zip(sb,db)):
        if X(a,'./w:pPr/w:pStyle[starts-with(@w:val,"TOC")]'):continue
        bid=f'B{i:04d}';assert T(b)==edits.get(bid,T(a)),(bid,T(a),T(b))
        if T(a)!=T(b):changed.append(bid)
    om_s=X(s,'.//m:oMath');om_d=X(d,'.//m:oMath')
    sig=lambda e:tuple((n.tag,tuple(sorted(n.attrib.items())),n.text or '') for n in e.iter())
    oldcounts=Counter(sig(e) for e in om_s);newcounts=Counter(sig(e) for e in om_d)
    changed_old=X(sb[286],'.//m:oMath')[0];changed_new=X(db[286],'.//m:oMath')[0]
    oldcounts[sig(changed_old)]-=1;newcounts[sig(changed_new)]-=1
    assert not oldcounts-newcounts,'old native math was changed outside eq2-8'
    assert sum((newcounts-oldcounts).values())==5
    assert len(om_s)==375 and len(om_d)==380
    tables_s=X(s,'.//w:tbl');tables_d=X(d,'.//w:tbl');assert len(tables_s)==len(tables_d)==78
    changed_tables=[i for i,(a,b) in enumerate(zip(sb,db)) if a.tag==W+'tbl' and E.tostring(a,method='c14n')!=E.tostring(b,method='c14n')]
    expected_tables=sorted(int(e['block_id'][1:]) for e in M['edits'] if e['op'] in ['replace_cell','insert_table_rows'])
    text_changed_tables=sorted(set(expected_tables))
    expected_tables+=[int(bid[1:]) for bid in M['style_table_ids']]
    assert changed_tables==sorted(set(expected_tables)),changed_tables
    preserved_tables=len(tables_s)-len(changed_tables)
    # Primary results, development grid, and latency numbers must be byte-identical.
    for i in [750,1024]:assert E.tostring(sb[i],method='c14n')==E.tostring(db[i],method='c14n')
    bm=X(d,'.//w:bookmarkStart');ids=[b.get(W+'id') for b in bm];names=[b.get(W+'name') for b in bm]
    assert len(ids)==len(set(ids)) and len(names)==len(set(names))
    assert Counter(ids)==Counter(b.get(W+'id') for b in X(d,'.//w:bookmarkEnd'))
    assert all(a in names for a in X(d,'.//w:hyperlink/@w:anchor'))
    eqs=[n for n in names if n.startswith('Equation_')];assert len(eqs)==42
    se={p.getparent().getparent() if False else p.get(W+'name'):T(p.getparent()) for p in X(s,'.//w:bookmarkStart[starts-with(@w:name,"Equation_")]')}
    de={p.get(W+'name'):T(p.getparent()) for p in X(d,'.//w:bookmarkStart[starts-with(@w:name,"Equation_")]')}
    assert [k for k in se if se[k]!=de[k]]==['Equation_2_8']
    cache=json.loads((O/'_work/toc_pages.json').read_text())
    fields=X(d,'.//w:fldSimple[starts-with(normalize-space(@w:instr),"PAGEREF")]')
    assert len(fields)==145
    assert {f.get(W+'instr').split()[1]:T(f) for f in fields}==cache
    alltext='\n'.join(T(e) for e in db)
    for obsolete in ['替代BR-O，BR-J','以第四章的I1替代I0','I1替代继承I0','60/115','0/115','3/561']:
        assert obsolete not in alltext,obsolete
    for idx,f in enumerate(M['figures'],1):
        assert hashlib.sha256(zd.read(f'word/media/image{idx}.png')).hexdigest()==f['png_sha256']
        assert hashlib.sha256(zd.read(f'word/media/model_architecture_{idx}.svg')).hexdigest()==f['svg_sha256']
        svg=zd.read(f'word/media/model_architecture_{idx}.svg').decode()
        assert 'Qwen2.5' not in svg and 'Qwen3.8' in svg

r=PdfReader(P);flat=[]
def walk(items):
    for item in items:
        if isinstance(item,list):walk(item)
        else:flat.append({'title':item.title,'page':r.get_destination_page_number(item)+1})
walk(r.outline);assert flat==json.loads((O/'_work/outline.json').read_text())
body=M['body_first_physical_page'];texts=[p.extract_text() for p in r.pages]
assert all(t.strip() for t in texts)
for term in ['Error! Reference source not found','Error! Bookmark not defined','错误!未定义书签','\ufffd']:
    assert term not in '\n'.join(texts),term
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
        if bad:outside.append({'page':i,'chars':[(c['text'],round(c['x0'],1),round(c['x1'],1)) for c in bad[:20]]})
# Record any detected boundary issues for visual investigation.
assert not outside,outside
w=PdfWriter();w.clone_document_from_reader(r)
w.set_page_label(0,0,prefix='封面',start=1)
w.set_page_label(1,body-2,style='/R',start=1)
w.set_page_label(body-1,len(r.pages)-1,style='/D',start=1)
F=O/(D.stem+'.pdf');w.write(F);f=PdfReader(F)
assert [p.get_contents().get_data() for p in r.pages]==[p.get_contents().get_data() for p in f.pages]
assert all(cache[h['bookmark']]==f.page_labels[dest['page']-1] for h,dest in zip(M['headings'],flat))
report={'source_preserved':True,'source_sha256':sha(S),'docx_sha256':sha(D),'pdf_sha256':sha(F),
        'pages':len(r.pages),'body_first_physical_page':body,'printed_body_pages':len(r.pages)-body+1,
        'patches':M['patches'],'changed_body_blocks':changed,'native_math_objects':len(om_d),
        'numbered_equations':42,'changed_equations':['2-8'],'other_native_math_preserved':True,'new_native_symbol_objects':5,
        'tables':78,'changed_table_blocks':[f'B{i:04d}' for i in changed_tables],
        'byte_identical_tables':preserved_tables,'text_identical_tables':78-len(text_changed_tables),
        'changed_table_text_blocks':[f'B{i:04d}' for i in text_changed_tables],
        'development_grid_and_latency_values_unchanged':True,'layout_changes':M['layout_changes'],
        'figure_pairs_verified':3,'toc_entries_verified':145,'fonts_embedded':len(fonts),'margin_overflow':outside,
        'render_dir':str(render),'changed_package_parts':changed_parts,'models_executed':False}
(O/'_work/delivery_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(O/'_work/pdf_fulltext.txt').write_text('\n'.join(f'PAGE {i}\n{t}' for i,t in enumerate(texts,1)))
print(json.dumps(report,ensure_ascii=False,indent=2))
