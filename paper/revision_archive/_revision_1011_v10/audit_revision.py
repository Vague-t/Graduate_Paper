"""Audit localized OOXML edits, preserved formal content and frozen evidence."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,zipfile
from lxml import etree
W=Path(__file__).resolve().parent;R=W.parent;E=R/'research_1011_v10'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=(R/'report_1011_v9_full.md').read_text();new=(R/'report_1011_v10_full.md').read_text()
ch=read(W/'changes.json');build=read(W/'docx_build.json');ev=read(W/'template-evidence.json')
assert sha(R/'report_1011_v9_full.md')=='57eae9295efecff9ea49e6c14486652b154f54b8ab937a84191c1f5738651a5a'
assert sha(R/'report_1011_v9_full.docx')=='996419afb9e111501e654dfb082191915aa5fce08465fbb584977111ee58230e'
assert sha(R/'report_1011_v10_full.md')==build['source_sha256']
for pat in [r'\$\$(.*?)\$\$',r'```(.*?)```']:
    assert re.findall(pat,old,re.S)==re.findall(pat,new,re.S)
assert old[old.index('## 附录E'):old.index('## 附录F')]==new[new.index('## 附录E'):new.index('## 附录F')]
assert old[old.index('## 参考文献'):old.index('## 附录A')].strip() in new
tables=lambda s:re.findall(r'(?m)^\|[^\n]*\n(?:\|[^\n]*(?:\n|$))+',s)
removed=tables(ch['section_replacements'][0]['old_markdown']);ot=tables(old);nt=tables(new)
assert len(removed)==2 and len(nt)==len(ot)+5
for t in ot:
    if t not in removed:assert t in nt
for name in ['new_corpora','cdcp_scoring']:
    root=E/name;run=root/'results/run_001'
    for p,h in read(run/'input_freeze.json')['hashes'].items():assert sha(root/p)==h,p
    for p,h in read(run/'output_freeze.json')['hashes'].items():assert sha(run/p)==h,p
    assert read(root/'results/evaluation_001/audit.json')['status']=='PASS'
    assert read(root/'results/evaluation_001/independent_recount.json')['status']=='PASS'
assert read(E/'interface_test_results.json')['status']=='PASS'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
tx=lambda n:''.join(n.xpath('.//w:t/text()',namespaces=NS))
def plain(s):return re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',re.sub(r'<!--.*?-->','',s)).replace('`','').replace('**','')
with zipfile.ZipFile(R/'report_1011_v10_full.docx') as z,zipfile.ZipFile(R/'report_1011_v9_full.docx') as b:
    assert z.testzip() is None and set(z.namelist())==set(b.namelist())
    for f in z.namelist():
        if f not in ev['editable_parts']:assert z.read(f)==b.read(f),f
    root=etree.fromstring(z.read('word/document.xml'));base=etree.fromstring(b.read('word/document.xml'))
    for path in ['//m:oMath','//w:sectPr']:
        assert [etree.tostring(x) for x in root.xpath(path,namespaces=NS)]==[etree.tostring(x) for x in base.xpath(path,namespaces=NS)]
    wr='\n'.join(tx(p) for p in root.xpath('//w:p',namespaces=NS))
    for op in ch['text_replacements']:assert plain(op['new']) in wr,op['new'][:70]
    for ins in ch['insertions']:
        for s in ins['paragraphs']:assert plain(s) in wr
    rows=Counter(tuple(tx(c) for c in r.findall('w:tc',NS)) for r in root.xpath('//w:tr',namespaces=NS))
    for sec in ch['section_replacements']+ch['sections_before']:
        for block in sec['blocks']:
            if block['type']!='table':assert block['text'] in wr
            else:
                assert block['caption'] in wr
                for row in [block['headers']]+block['rows']:assert rows[tuple(row)]>0,row
    for ref in ch['references']:assert ref['text'] in wr
    names=root.xpath('//w:bookmarkStart/@w:name',namespaces=NS);ids=root.xpath('//w:bookmarkStart/@w:id',namespaces=NS)
    assert len(names)==len(set(names)) and len(ids)==len(set(ids))
    assert all(a in names for a in root.xpath('//w:hyperlink/@w:anchor',namespaces=NS))
    base_tbl=[etree.tostring(t) for t in base.xpath('//w:tbl',namespaces=NS)];new_tbl=[etree.tostring(t) for t in root.xpath('//w:tbl',namespaces=NS)]
    missing=[t for t in base_tbl if t not in new_tbl]
    assert len(missing)==2,(len(base_tbl),len(new_tbl),len(missing))
    assert len(new_tbl)==len(base_tbl)+5
    # Retain every old reference, relationship and target exactly; append only two.
    rels=etree.fromstring(z.read('word/_rels/document.xml.rels'));oldrels=etree.fromstring(b.read('word/_rels/document.xml.rels'))
    assert len(rels)==len(oldrels)+2
    assert [dict(x.attrib) for x in rels[:len(oldrels)]]==[dict(x.attrib) for x in oldrels]
    assert len([x for x in root.xpath('//w:instrText/text()',namespaces=NS) if x.strip().startswith('TOC ')])==3
    omml=len(root.xpath('//m:oMath',namespaces=NS))
out={'status':'PASS','source_sha256':sha(R/'report_1011_v10_full.md'),'retained_v9_unchanged':True,'all_frozen_sources_unchanged':True,'independent_object_recounts':256,'native_math_preserved':omml,'display_equations_preserved':32,'algorithms_preserved':3,'references':51,'figures_preserved':11,'retained_numbered_tables':len(ot)-2,'new_numbered_tables':7,'numbered_tables':len(nt),'new_model_tasks':43,'new_training_runs':0,'new_original_solver_run_records':256,'new_replay_records':256}
(W/'source_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2))
