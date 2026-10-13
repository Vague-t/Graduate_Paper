from pathlib import Path
import hashlib,json,shutil,zipfile
from lxml import etree
W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1010_v4'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(R/'report_1010_v4_full.md')=='fba6b9c6891c0b27edd3a044c7f01a06a1945dbe35a1da534384ff0943ae5b77'
assert sha(R/'report_1010_v4_full.docx')=='7d4313ee697141af60c997674c471e1faee0523794bd1b39ca452aeb776e7433'
for n in ['render_document.py','fonts.conf','cache_pages.py','algorithm_splits.json','final_audit.py','build_docx.py','audit_scenario.py']:
    s=(P/n).read_text().replace('1010_v4','1010_v5').replace('1010-v4','1010-v5')
    if n=='build_docx.py':s=s.replace("template=R/'report_1010_v3_full.docx'","template=R/'report_1010_v4_full.docx'").replace("'v12_'","'v13_'")
    if n=='audit_scenario.py':s=s.replace("old=(W.parent/'report_1010_v3_full.md')","old=(W.parent/'report_1010_v4_full.md')")
    if n=='final_audit.py':s=s.replace('assert len(images) == 12','assert len(images) == 11')
    (W/n).write_text(s)
raw=['generate_scenario.py','document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json']
supp=['generate_supplement.py','supplement_manifest.json']+list(json.loads((P/'supplement_manifest.json').read_text())['files'])
for n in raw+supp:shutil.copy2(P/n,W/n)
(W/'figures').mkdir(exist_ok=True)
for f in (P/'figures').iterdir():
    if f.suffix in ['.png','.svg','.pdf']:shutil.copy2(f,W/'figures'/f.name)
c=json.loads((P/'reference_config.json').read_text());c['manuscript_version']='1010-v5'
c['authoring_revision']['metadata_note']='Editorial evidence-role revision: remove named external placeholders from thesis, relocate synthetic diagnostics, retain method configuration and original records.'
c['supplementary_simulation']['use_in_manuscript']='Template and budget examples in appendix H; abstract memberships only for non-identifiability demonstration; external placeholder scores not used.'
(W/'reference_config.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
old=R/'report_1010_v4_full.docx'
with zipfile.ZipFile(old) as z:
    parts=[{'name':n,'sha256':hashlib.sha256(z.read(n)).hexdigest(),'policy':'preserve-only' if n.startswith(('word/media/','word/theme/','customXml/')) or n in {'word/fontTable.xml','word/numbering.xml','word/webSettings.xml','docProps/app.xml','docProps/custom.xml'} else 'editable'} for n in z.namelist()]
    root=etree.fromstring(z.read('word/document.xml'));sections=[etree.tostring(x,encoding='unicode') for x in root.xpath('//w:sectPr',namespaces={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})]
base=['report_1010_v4_full.docx','report_1010_v4_full.md','1010_v4全局评审与完整修改建议.md']+[str((P/n).relative_to(R)) for n in raw+supp+['reference_config.json']]
(W/'template-evidence.json').write_text(json.dumps({'reference':str(old),'sha256':sha(old),'reference_render':str(P/'render_final'),'reference_render_pages':113,'parts':parts,'sections':sections,'baseline_hashes':{n:sha(R/n) for n in base}},ensure_ascii=False,indent=2)+'\n')
(W/'artifact.md').write_text('''# 1010 v5 评审修订契约

中文学术型硕士论文，保留v4六章框架与Word模板。正文突出关系监督保持和依赖闭合恢复；不增加实验体系。移除具名假想外部成绩；模板及预算情景移至模拟附录；对象补全只用于非唯一性说明。公式与方法配置保留，收窄T-B解释；压缩第四章实现细节、第五章重复内容。所有既有版本与原始记录留存，不生成新模型成绩。最终全页渲染复核；交付Word、Markdown及逐项已改未改说明。
''')
print('Prepared v5; v4 preserved')
