from pathlib import Path
import hashlib,json,shutil,zipfile
from lxml import etree

W=Path(__file__).resolve().parent;R=W.parent;P=R/'_revision_1010_v5'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(R/'report_1010_v5_full.md')=='47aa8e2f60550877c1cd02f0e0b643b6e33a7a58546f719521f6eaa945140ff6'
assert sha(R/'report_1010_v5_full.docx')=='e0b2e7718d9c99fb2651a540d20e06975fcd17281b5df9a71197fdab386ded18'
for n in ['render_document.py','fonts.conf','cache_pages.py','algorithm_splits.json','final_audit.py','build_docx.py','audit_scenario.py']:
    s=(P/n).read_text().replace('1010_v5','1010_v6').replace('1010-v5','1010-v6')
    if n=='build_docx.py':
        s=s.replace("template=R/'report_1010_v4_full.docx'","template=R/'report_1010_v5_full.docx'").replace("'v13_'","'v14_'")
    if n=='audit_scenario.py':s=s.replace("old=(W.parent/'report_1010_v4_full.md')","old=(W.parent/'report_1010_v5_full.md')")
    (W/n).write_text(s)
raw=['generate_scenario.py','document_counts.csv','scenario_results.json','scenario_manifest.json','score_records.json','audit_judgements.json','derived_tables.json']
supp=['generate_supplement.py','supplement_manifest.json']+list(json.loads((P/'supplement_manifest.json').read_text())['files'])
for n in raw+supp:shutil.copy2(P/n,W/n)
(W/'figures').mkdir(exist_ok=True)
for f in (P/'figures').iterdir():
    if f.suffix in ['.png','.svg','.pdf']:shutil.copy2(f,W/'figures'/f.name)
c=json.loads((P/'reference_config.json').read_text());c['manuscript_version']='1010-v6'
c['production_required_unbound']+=['augmentation_model_checkpoint','semantic_verifier_checkpoint','fixed_text_encoder_checkpoint','generation_and_verification_prompts','sampling_parameters','rho','lambda_sup','lambda_C','lambda_R','coefficient_selection_protocol']
c['authoring_revision']['metadata_note']='Local prose synchronization after full manuscript reading; reference settings are illustrative, production identities and coefficient selection remain unbound; no new model or simulation runs.'
(W/'reference_config.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
old=R/'report_1010_v5_full.docx'
with zipfile.ZipFile(old) as z:
    parts=[{'name':n,'sha256':hashlib.sha256(z.read(n)).hexdigest(),'policy':'preserve-only' if n.startswith(('word/media/','word/theme/','customXml/')) or n in {'word/fontTable.xml','word/numbering.xml','word/webSettings.xml','docProps/app.xml','docProps/custom.xml'} else 'editable'} for n in z.namelist()]
    root=etree.fromstring(z.read('word/document.xml'));sections=[etree.tostring(x,encoding='unicode') for x in root.xpath('//w:sectPr',namespaces={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})]
base=['report_1010_v5_full.docx','report_1010_v5_full.md','1010_v5全局评审与完整修改建议.md']+[str((P/n).relative_to(R)) for n in raw+supp+['reference_config.json']]
(W/'template-evidence.json').write_text(json.dumps({'reference':str(old),'sha256':sha(old),'reference_render':str(P/'render_final'),'reference_render_pages':112,'parts':parts,'sections':sections,'baseline_hashes':{n:sha(R/n) for n in base}},ensure_ascii=False,indent=2)+'\n')
(W/'artifact.md').write_text('''# 1010 v6 全文润色契约

以已逐页审阅的v5 Word为保留模板，六章及附录结构不变。保留3个节及其纸张、边距、页眉页脚距离和编号机制；沿用源模板正文、标题、题注、原生公式、三线表与续表。先逐段阅读全文2099行（中英文摘要、六章、49条参考文献和附录A至H），再进行局部改写。修改槽位通过精确原文替换登记；不重新撰写未涉及段落。配置状态、采样措辞和资料核查时间表述可直接纠正；核心对照职责与第五章成本范围待作者明确选择。保持图像与32个陈列公式；算法3-1第27行仅澄清等频采样。记录全部变更及未执行事项，生成Word、Markdown和版本绑定说明。每个最终页重新渲染并检查，目录缓存与最终PDF对应。旧版本及原始情景数据不变。
''')
(W/'full_read_record.json').write_text(json.dumps({'source':str(R/'report_1010_v5_full.md'),'source_sha256':sha(R/'report_1010_v5_full.md'),'lines':2099,'read_spans':[[1,160],[161,296],[297,460],[461,610],[611,770],[771,940],[941,1125],[1126,1395],[1396,1575],[1576,1760],[1761,1945],[1946,2099]],'coverage':'Entire supplied manuscript including both abstracts, six chapters, references and appendices read before edits','review':str(R/'1010_v5全局评审与完整修改建议.md'),'review_sha256':sha(R/'1010_v5全局评审与完整修改建议.md'),'independent_literature_reverification':False},ensure_ascii=False,indent=2)+'\n')
print('Prepared v6 workspace; v5 baseline preserved.')
