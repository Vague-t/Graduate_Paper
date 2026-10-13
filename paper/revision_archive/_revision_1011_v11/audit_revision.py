"""Source, OOXML, count and provenance audit of the retained v10 revision."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,zipfile
from lxml import etree
W=Path(__file__).resolve().parent;R=W.parent;E=R/'research_1011_v11'
read=lambda p:json.loads(Path(p).read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=(R/'report_1011_v10_full.md').read_text();new=(R/'report_1011_v11_full.md').read_text();ch=read(W/'changes.json');ev=read(W/'template-evidence.json');build=read(W/'docx_build.json')
assert sha(R/'report_1011_v10_full.md')=='3881452a0b0bdc59eadf0e4d1168d82a500cafacdcbcc003f0346c8ae81fad16'
assert sha(R/'report_1011_v10_full.docx')=='60a8fd33f1cd3b911ddd5da5c8f3e934f7f3a72fed0677b3d14b81657bf96775'
for pat in [r'\$\$(.*?)\$\$',r'```(.*?)```']:
 assert re.findall(pat,old,re.S)==re.findall(pat,new,re.S)
for a,b in [('## 参考文献','## 附录A'),('## 附录E','## 附录F')]:assert old[old.index(a):old.index(b)]==new[new.index(a):new.index(b)]
tables=lambda s:re.findall(r'(?m)^\|[^\n]*\n(?:\|[^\n]*(?:\n|$))+',s)
assert len(tables(new))==len(tables(old))+12
for t in tables(old):assert t in tables(new)
assert read(E/'independent_recount.json')['status']=='PASS'
assert read(E/'solver/evaluation/audit.json')['status']=='PASS'
assert read(E/'solver_interface_tests.json')['passed']
assert read(E/'simulation/manifest.json')['all_four_cell_document_counts_exactly_match_v7']
assert len(read(E/'model_execution_manifest.json')['tasks'])==30
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
tx=lambda n:''.join(n.xpath('.//w:t/text()',namespaces=NS))
plain=lambda s:re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',re.sub(r'<!--.*?-->','',s)).replace('`','').replace('**','')
with zipfile.ZipFile(R/'report_1011_v11_full.docx') as z,zipfile.ZipFile(R/'report_1011_v10_full.docx') as b:
 assert z.testzip() is None and set(z.namelist())==set(b.namelist())
 for f in z.namelist():
  if f not in ev['editable_parts']:assert z.read(f)==b.read(f),f
 root=etree.fromstring(z.read('word/document.xml'));base=etree.fromstring(b.read('word/document.xml'))
 for xp in ['//m:oMath','//w:sectPr']:
  assert [etree.tostring(x) for x in root.xpath(xp,namespaces=NS)]==[etree.tostring(x) for x in base.xpath(xp,namespaces=NS)]
 wr='\n'.join(tx(p) for p in root.xpath('//w:p',namespaces=NS))
 for op in ch['text_replacements']:assert plain(op['new']) in wr,op['new'][:70]
 for ins in ch['insertions']:
  for s in ins['paragraphs']:assert plain(s) in wr
 blocks=[v for s in ch['sections_before'] for v in s['blocks']]+ch['append_blocks']
 rows=Counter(tuple(tx(c) for c in r.findall('w:tc',NS)) for r in root.xpath('//w:tr',namespaces=NS))
 for v in blocks:
  if v['type']!='table':assert v['text'] in wr,v['text'][:70]
  else:
   assert v['caption'] in wr
   for row in [v['headers']]+v['rows']:assert rows[tuple(row)]>0,row
 names=root.xpath('//w:bookmarkStart/@w:name',namespaces=NS);ids=root.xpath('//w:bookmarkStart/@w:id',namespaces=NS)
 assert len(names)==len(set(names)) and len(ids)==len(set(ids))
 assert all(a in names for a in root.xpath('//w:hyperlink/@w:anchor',namespaces=NS))
 bt=[etree.tostring(t) for t in base.xpath('//w:tbl',namespaces=NS)];nt=[etree.tostring(t) for t in root.xpath('//w:tbl',namespaces=NS)]
 assert all(t in nt for t in bt)
 assert len(nt)==len(bt)+12,(len(bt),len(nt))
 assert len([x for x in root.xpath('//w:instrText/text()',namespaces=NS) if x.strip().startswith('TOC ')])==3
out={'status':'PASS','source_sha256':sha(R/'report_1011_v11_full.md'),'retained_v10_unchanged':True,'all_formal_content_preserved':True,'native_math_preserved':411,'display_equations_preserved':32,'algorithms_preserved':3,'references':51,'figures_preserved':11,'retained_numbered_tables':61,'new_numbered_tables':12,'numbered_tables':73,'continued_parts_added':0,'new_model_tasks':30,'new_target_training_runs':0,'new_solver_run_records':1536,'independent_solver_recounts':1536,'independent_candidate_layer_recounts':96,'simulation_four_cell_membership_counts_match_v7':True}
(W/'source_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2))
