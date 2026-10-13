"""Prepare a new review revision without altering the v3 artifacts or data."""
from pathlib import Path
import hashlib,json,zipfile,shutil
from lxml import etree
W=Path(__file__).resolve().parent; R=W.parent; P=R/'_revision_1009_v3'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name in ['render_document.py','fonts.conf','cache_pages.py','algorithm_splits.json','table_splits.json','final_audit.py','build_docx.py','audit_scenario.py']:
    text=(P/name).read_text().replace('1009_v3','1009_v4').replace('1009-v3','1009-v4')
    if name=='build_docx.py':
        text=text.replace("template=R/'report_1009_v2_full.docx'", "template=R/'report_1009_v3_full.docx'")
        text=text.replace("'v7_'", "'v8_'")
    if name=='audit_scenario.py':text=text.replace("old=(W.parent/'report_1009_v2_full.md')", "old=(W.parent/'report_1009_v3_full.md')")
    (W/name).write_text(text)
for name in ['generate_scenario.py','document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json']:
    shutil.copy2(P/name,W/name)
shutil.copytree(P/'figures',W/'figures',dirs_exist_ok=True)
cfg=json.loads((P/'reference_config.json').read_text())
cfg['configuration_id']='1009-v4-simulation-review'
cfg['simulation_runtime_assumptions']['training_side_roles']={
    'AAEC':{'source_documents':320,'scorer_fit':256,'calibration':32,'policy_selection':32,'independent_evaluation':80},
    'CDCP':{'source_documents':580,'scorer_fit':464,'calibration':58,'policy_selection':58,'independent_evaluation':148},
    'assignment':'fixed source-document groups; proportions specify the authoring protocol, not an executed manifest',
    'oof_folds':3,'oof_excludes':'held-out document and all its variants from generator and span-head fitting',
    'scorer_evaluation_objects_per_dataset':{'component':2400,'relation':4800}}
(W/'reference_config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
old=R/'report_1009_v3_full.docx'; parts=[]
with zipfile.ZipFile(old) as z:
    for name in z.namelist():
        preserve=name.startswith(('word/media/','word/theme/','customXml/')) or name in {'word/fontTable.xml','word/numbering.xml','word/webSettings.xml','docProps/app.xml','docProps/custom.xml'}
        parts.append({'name':name,'sha256':hashlib.sha256(z.read(name)).hexdigest(),'policy':'preserve-only' if preserve else 'editable'})
    body=etree.fromstring(z.read('word/document.xml'))
    sections=[etree.tostring(x,encoding='unicode') for x in body.xpath('//w:sectPr',namespaces={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})]
baseline=['report_1009_v3_full.docx','report_1009_v3_full.md','1009_v3修改与数据替换说明.md','1009_v2复审后完整修改建议与实施方案.md']
baseline += [str(p.relative_to(R)) for p in P.iterdir() if p.is_file() and p.name in ['document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json']]
record={'reference':str(old),'sha256':sha(old),'reference_render':str(P/'render_final'),'reference_render_pages':96,'parts':parts,'sections':sections,'baseline_hashes':{f:sha(R/f) for f in baseline}}
(W/'template-evidence.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
(W/'artifact.md').write_text('''# 1009 v4 复审落实稿排版契约

参考 report_1009_v3_full.docx 及96页完整渲染，沿用三节A4、原字号与行距、原生公式、可点击目录和页眉结构。保留所有历史媒体、主题、customXML及页面几何，修改页眉版本和正文内容。

用户要求参考1009_v2复审后完整修改建议与实施方案。沿用已授权的模拟数据演示稿身份和封面统一声明，不把新派生统计描述为新增真实实验。保持v3原始情景数据、32陈列公式、46文献、11幅图和附录E历史正文；新增拒绝样本审计、四格净错误变化、预算判定表，修正数据用途与论证范围，同步编号、目录、交叉引用及配置。十类生产接口的缺口在落实说明中保留，不用参考函数或排版检查替代训练和求解验收。

最终检查每一页，长表重复表头并采用语义续题，不缩字号挤页；交付新Word、Markdown和逐项落实说明，原v3全部保留。
''')
print('v4 prepared',sha(old))
