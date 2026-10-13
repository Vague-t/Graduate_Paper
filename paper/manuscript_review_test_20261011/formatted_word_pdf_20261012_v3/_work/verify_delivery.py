from pathlib import Path
from collections import Counter
from zipfile import ZipFile
from urllib.parse import unquote
import hashlib, json, posixpath, re
from lxml import etree
from pypdf import PdfReader, PdfWriter
import pdfplumber

O = Path(__file__).resolve().parents[1]
manifest = json.loads((O/'_work/format_manifest.json').read_text())
source, output = Path(manifest['source']), Path(manifest['output'])
render_pdf = O/'_render_complete/论文规范排版稿_v3.pdf'
final_pdf = O/'论文规范排版稿_v3.pdf'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'm':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
W = '{'+ns['w']+'}'
xp = lambda e,q: e.xpath(q,namespaces=ns)
txt = lambda e: ''.join(e.xpath('.//w:t/text()|.//m:t/text()',namespaces=ns))
report = {'source':str(source),'docx':str(output),'pdf':str(final_pdf)}
assert sha(source) == manifest['source_sha256'] == 'e61243638c4a85464392054f431b59206646ec50b523d29a676d27528e19e4fc'
assert sha(output) == manifest['output_sha256']
with ZipFile(source) as zs, ZipFile(output) as zo:
    assert zs.testzip() is None and zo.testzip() is None
    s = etree.fromstring(zs.read('word/document.xml'))
    d = etree.fromstring(zo.read('word/document.xml'))
    expected = Counter(txt(p) for p in xp(s,'.//w:body//w:p') if txt(p))
    for edit in manifest['edits']:
        assert expected[edit['before']] > 0, edit
        expected[edit['before']] -= 1
        expected[edit['after']] += 1
    actual = Counter()
    for p in xp(d,'.//w:body//w:p'):
        style = p.find('./'+W+'pPr/'+W+'pStyle')
        if style is not None and (style.get(W+'val','').startswith('TOC') or style.get(W+'val') == 'FrontHeading'):
            continue
        if txt(p): actual[txt(p)] += 1
    missing, extra = expected-actual, actual-expected
    assert not missing and not extra, {'missing':list(missing.items())[:5],'extra':list(extra.items())[:5]}
    def math_signature(root):
        return [[(e.tag, sorted(e.attrib.items()), e.text or '') for e in m.iter() if e.tag.startswith('{'+ns['m']+'}')]
                for m in xp(root,'.//m:oMath')]
    assert math_signature(s) == math_signature(d)
    assert len(xp(d,'.//m:oMath')) == 382
    st, dt = xp(s,'.//w:tbl'), xp(d,'.//w:tbl')
    assert len(st) == len(dt) == 73
    assert [[txt(c) for c in xp(t,'.//w:tc')] for t in st] == [[txt(c) for c in xp(t,'.//w:tc')] for t in dt]
    media = [n for n in zs.namelist() if n.startswith('word/media/')]
    assert media == [n for n in zo.namelist() if n.startswith('word/media/')]
    assert all(zs.read(n) == zo.read(n) for n in media)
    svg_count = sum(n.endswith('.svg') for n in media)
    assert svg_count == 3
    bookmarks = xp(d,'.//w:bookmarkStart')
    names = [b.get(W+'name') for b in bookmarks]
    ids = [b.get(W+'id') for b in bookmarks]
    assert len(names) == len(set(names)) and len(ids) == len(set(ids))
    assert Counter(ids) == Counter(b.get(W+'id') for b in xp(d,'.//w:bookmarkEnd'))
    anchors = [l.get(W+'anchor') for l in xp(d,'.//w:hyperlink[@w:anchor]')]
    assert all(a in names for a in anchors)
    eqs = [b for b in names if b.startswith('Equation_')]
    assert len(eqs) == 42
    seqs = [f.get(W+'instr') for f in xp(d,'.//w:fldSimple') if 'SEQ' in f.get(W+'instr','')]
    oldseqs = [f.get(W+'instr') for f in xp(s,'.//w:fldSimple') if 'SEQ' in f.get(W+'instr','')]
    assert seqs == oldseqs and len(seqs) == 42
    cache = json.loads((O/'_work/toc_pages.json').read_text())
    pagefields = [f for f in xp(d,'.//w:fldSimple') if f.get(W+'instr','').strip().startswith('PAGEREF')]
    assert len(pagefields) == 138
    assert {f.get(W+'instr').split()[1]:txt(f) for f in pagefields} == cache
    missing_rels = []
    for name in zo.namelist():
        if not name.endswith('.rels'): continue
        root = etree.fromstring(zo.read(name))
        base = '' if name == '_rels/.rels' else posixpath.dirname(posixpath.dirname(name))
        for rel in root:
            if rel.get('TargetMode') == 'External': continue
            target = unquote(rel.get('Target','').split('#')[0])
            resolved = posixpath.normpath(posixpath.join(base,target)).lstrip('/')
            if resolved not in zo.namelist(): missing_rels.append((name,resolved))
    assert not missing_rels, missing_rels
    report['docx_integrity'] = {'paragraph_content_preserved_except_requested_edits':True,
        'requested_reference_edits':len(manifest['edits']),'native_math_objects':382,
        'numbered_equations':42,'tables':73,'svg_figures':svg_count,
        'all_media_bytes_preserved':True,'toc_entries':138,'all_internal_links_resolve':True,
        'zip_and_relationships_valid':True,'source_unchanged':True}

r = PdfReader(render_pdf)
assert len(r.pages) == 117
def outline(reader):
    result=[]
    def walk(items):
        for item in items:
            if isinstance(item,list): walk(item)
            else: result.append({'title':item.title,'page':reader.get_destination_page_number(item)+1})
    walk(reader.outline)
    return result
flat = outline(r)
assert flat == json.loads((O/'_work/outline_v4.json').read_text())
roman = ['I','II','III','IV','V','VI','VII']
for heading,dest in zip(manifest['headings'],flat):
    assert heading['title'] == dest['title']
    label = roman[dest['page']-2] if dest['page'] < 9 else str(dest['page']-8)
    assert cache[heading['bookmark']] == label
alltext = [p.extract_text() for p in r.pages]
assert all(t.strip() for t in alltext)
assert not any(s in '\n'.join(alltext) for s in ['Error! Reference source not found','Error! Bookmark not defined','错误!未定义书签','\ufffd'])
fonts = {}
for page in r.pages:
    for ref in page['/Resources'].get('/Font',{}).values():
        f=ref.get_object(); name=str(f.get('/BaseFont'))
        leaf = f['/DescendantFonts'][0].get_object() if f.get('/DescendantFonts') else f
        descriptor = leaf.get('/FontDescriptor')
        embedded = bool(descriptor and any(descriptor.get_object().get(k) for k in ['/FontFile','/FontFile2','/FontFile3']))
        fonts[name]=embedded
assert fonts and all(fonts.values()), fonts
outside=[]
with pdfplumber.open(render_pdf) as pdf:
    for i,page in enumerate(pdf.pages,1):
        assert abs(page.width-595.3)<1 and abs(page.height-841.9)<1
        bad=[c for c in page.chars if c['text'].strip() and 65<c['top']<790 and (c['x0']<67 or c['x1']>530)]
        if bad:outside.append({'page':i,'chars':[(c['text'],round(c['x0'],1),round(c['x1'],1)) for c in bad[:10]]})
assert not outside, outside
w = PdfWriter()
w.clone_document_from_reader(r)
w.set_page_label(0,0,prefix='封面',start=1)
w.set_page_label(1,7,style='/R',start=1)
w.set_page_label(8,116,style='/D',start=1)
w.write(final_pdf)
f = PdfReader(final_pdf)
assert f.page_labels == ['封面']+roman+[str(i) for i in range(1,110)]
assert outline(f) == flat
assert [p.get_contents().get_data() for p in r.pages] == [p.get_contents().get_data() for p in f.pages]
assert [len(p.get('/Annots',[])) for p in r.pages] == [len(p.get('/Annots',[])) for p in f.pages]
report['pdf_integrity']={'pages':117,'body_pages':109,'preliminary_roman_pages':7,
    'page_labels_match_printed_numbers':True,'bookmarks':len(flat),'all_fonts_embedded':fonts,
    'a4_all_pages':True,'no_horizontal_overflow':True,'no_empty_pages':True,
    'page_content_streams_unchanged_when_labels_added':True}
render_differences = [i for i in range(1,118) if sha(O/f'_render_complete/page-{i}.png') != sha(O/f'_render_delivery/page-{i}.png')]
assert not render_differences, render_differences
report['visual_review']={'all_pages_reviewed':list(range(1,118)),
    'method':'Full-page PNG review, with byte-identical page reuse between revisions.',
    'last_render':'_render_complete','last_changed_pages_reviewed':[111,117],
    'last_bookmark_repair_visually_identical_to_reviewed_render':True}
report['sha256']={'source':sha(source),'docx':sha(output),'pdf':sha(final_pdf)}
(O/'_work/delivery_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(O/'_work/visual_review_checkpoint.json').write_text(json.dumps(report['visual_review'],ensure_ascii=False,indent=2))
print(json.dumps({'passed':True,'docx':str(output),'pdf':str(final_pdf),'pages':117,
    'native_math':382,'tables':73,'toc_entries':138,'fonts_embedded':len(fonts)},ensure_ascii=False))
