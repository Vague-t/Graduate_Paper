from pathlib import Path
import shutil,hashlib,json,zipfile
from lxml import etree
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1010_v3'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(R/'report_1010_v3_full.md')=='6e2b841f24e5a3b8011fd70ec675844c53ae90a20642dd0bcdf332a55495c867'
assert sha(R/'report_1010_v3_full.docx')=='95d171715339b4702ad4e2baac7ac32d070721f58cffb94d320c0b8934849c76'
for n in ['render_document.py','fonts.conf','cache_pages.py','algorithm_splits.json','table_splits.json','final_audit.py','build_docx.py','audit_scenario.py']:
 s=(P/n).read_text().replace('1010_v3','1010_v4').replace('1010-v3','1010-v4')
 if n=='build_docx.py':s=s.replace("template=R/'report_1010_v2_full.docx'","template=R/'report_1010_v3_full.docx'").replace("'v11_'","'v12_'")
 if n=='audit_scenario.py':s=s.replace("old=(W.parent/'report_1010_v2_full.md')","old=(W.parent/'report_1010_v3_full.md')")
 if n=='final_audit.py':s=s.replace('assert len(images) == 11','assert len(images) == 12')
 (W/n).write_text(s)
raw=['generate_scenario.py','document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json']
for n in raw:shutil.copy2(P/n,W/n)
(W/'figures').mkdir(exist_ok=True)
for f in (P/'figures').iterdir():
 if f.suffix in ['.png','.svg','.pdf']:shutil.copy2(f,W/'figures'/f.name)
c=json.loads((P/'reference_config.json').read_text());c['manuscript_version']='1010-v4';c['authoring_revision']['metadata_note']='Additional reproducible simulated evidence; no genuine training, inference, human audit, or solver runs.'
c['supplementary_simulation']={'id':'SIM-1010-V4','randomness':'SHA256 of SIM-1010-V4 plus operation keys; see generator','real_model_runs':0,'source_identity':'synthetic scenarios and abstract object memberships; not model outputs'}
(W/'reference_config.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
s=(R/'report_1010_v3_full.md').read_text().replace('_revision_1010_v3/','_revision_1010_v4/').replace('1010-v3','1010-v4');(R/'report_1010_v4_full.md').write_text(s)
old=R/'report_1010_v3_full.docx'
with zipfile.ZipFile(old) as z:
 parts=[{'name':n,'sha256':hashlib.sha256(z.read(n)).hexdigest(),'policy':'preserve-only' if n.startswith(('word/media/','word/theme/','customXml/')) or n in {'word/fontTable.xml','word/numbering.xml','word/webSettings.xml','docProps/app.xml','docProps/custom.xml'} else 'editable'} for n in z.namelist()]
 root=etree.fromstring(z.read('word/document.xml'));sections=[etree.tostring(x,encoding='unicode') for x in root.xpath('//w:sectPr',namespaces={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})]
base=['report_1010_v3_full.docx','report_1010_v3_full.md','1010_v3评审处理与图示重绘说明.md']+[str((P/n).relative_to(R)) for n in raw+['reference_config.json']]
(W/'template-evidence.json').write_text(json.dumps({'reference':str(old),'sha256':sha(old),'reference_render':str(P/'render_final'),'reference_render_pages':107,'parts':parts,'sections':sections,'baseline_hashes':{n:sha(R/n) for n in base}},ensure_ascii=False,indent=2)+'\n')
(W/'artifact.md').write_text('''# 1010 v4 模拟实验增补契约

保留v3三节页面几何、字形与原生公式、目录、题注、表格及算法模板。七张新方法图及四张定量旧图原字节继承。新增模拟表与一张预算比较图，正文与附录同步分析；原始计数和附录E保留。明确零真实训练、推理、人工审计或求解器运行；外部方法仅为占位模拟，不能归为原作者成绩。原版本保持。最终重新渲染并逐页查看。
''')
print('Prepared v4 with preserved baseline')
